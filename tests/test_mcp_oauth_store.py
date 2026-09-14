"""OAuth store: single-use S256 codes, rotating refresh with reuse revocation, tdyM_ keys."""
import base64
import hashlib
import sqlite3
import stat

import pytest

from src.mcp_server import keys, oauth_store
from src.mcp_server.oauth_store import OAuthStore

FULL = "drmahirkurt@gmail.com"
READER = "murzogluhulya@gmail.com"
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
LOOPBACK = "http://127.0.0.1/callback"
VERIFIER = "v" * 64


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


class Clock:
    def __init__(self) -> None:
        self.now = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def store(tmp_path, clock):
    return OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)


@pytest.fixture
def client_id(store):
    return store.register_client("Claude", [REDIRECT, LOOPBACK]).client_id


def _pair(store, client_id):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    return store.redeem_code(code, client_id, REDIRECT, VERIFIER)


def test_code_round_trip_binds_email(store, client_id):
    pair = _pair(store, client_id)
    assert pair is not None
    assert pair.email == FULL
    assert pair.expires_in == oauth_store.ACCESS_TTL_SECONDS
    assert store.principal(pair.access_token) == FULL


def test_code_is_single_use(store, client_id):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER) is not None
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER) is None


@pytest.mark.parametrize("client,redirect,verifier", [
    ("other-client", REDIRECT, VERIFIER),
    (None, "https://grok.com/cb", VERIFIER),
    (None, REDIRECT, "w" * 64),
])
def test_code_redeem_rejects_mismatch(store, client_id, client, redirect, verifier):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    assert store.redeem_code(code, client or client_id, redirect, verifier) is None


def test_code_expires_after_five_minutes(store, client_id, clock):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    clock.now += oauth_store.CODE_TTL_SECONDS + 1
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER) is None


def test_issue_code_rejects_plain_pkce_and_non_full_email(store, client_id):
    with pytest.raises(ValueError):
        store.issue_code(FULL, client_id, REDIRECT, VERIFIER, "plain")
    with pytest.raises(ValueError):
        store.issue_code(READER, client_id, REDIRECT, _challenge(VERIFIER), "S256")


def test_access_token_expires(store, client_id, clock):
    pair = _pair(store, client_id)
    clock.now += oauth_store.ACCESS_TTL_SECONDS + 1
    assert store.principal(pair.access_token) is None


def test_refresh_rotates_and_old_refresh_is_single_use(store, client_id):
    first = _pair(store, client_id)
    second = store.refresh(first.refresh_token, client_id)
    assert second is not None
    assert second.refresh_token != first.refresh_token
    assert store.principal(second.access_token) == FULL


def test_refresh_reuse_revokes_the_whole_family(store, client_id):
    first = _pair(store, client_id)
    second = store.refresh(first.refresh_token, client_id)
    assert store.refresh(first.refresh_token, client_id) is None  # replay
    assert store.principal(second.access_token) is None
    assert store.refresh(second.refresh_token, client_id) is None


def test_refresh_rejects_other_client_and_expiry(store, client_id, clock):
    first = _pair(store, client_id)
    assert store.refresh(first.refresh_token, "other-client") is None
    other = _pair(store, client_id)
    clock.now += oauth_store.REFRESH_TTL_SECONDS + 1
    assert store.refresh(other.refresh_token, client_id) is None


def test_roster_change_invalidates_existing_tokens(store, client_id, monkeypatch):
    pair = _pair(store, client_id)
    monkeypatch.setattr(oauth_store.roles, "is_full", lambda email: False)
    assert store.principal(pair.access_token) is None


def test_static_key_lifecycle(store):
    key = store.create_static_key("codex-mahir", FULL)
    assert key.startswith("tdyM_")
    assert store.principal(key) == FULL
    listed = store.list_static_keys()
    assert listed == [{"label": "codex-mahir", "email": FULL, "created_at": listed[0]["created_at"], "revoked": False}]
    assert store.revoke_static_key("codex-mahir") is True
    assert store.principal(key) is None
    assert store.revoke_static_key("codex-mahir") is False


def test_static_key_refused_for_reader_and_duplicate_label(store):
    with pytest.raises(ValueError):
        store.create_static_key("reader-key", READER)
    store.create_static_key("dup", FULL)
    with pytest.raises(ValueError):
        store.create_static_key("dup", FULL)


def test_dashboard_keys_and_garbage_are_not_principals(store):
    assert store.principal("tdyK_" + "a" * 40) is None
    assert store.principal("") is None
    assert store.principal("ünicode") is None


def test_database_file_is_private(tmp_path, clock):
    path = tmp_path / "oauth.sqlite3"
    OAuthStore(path, clock=clock)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_keys_cli_create_list_revoke(store, capsys):
    assert keys.main(["olustur", "--etiket", "grok", "--email", FULL], store=store) == 0
    created = capsys.readouterr().out.strip().splitlines()[-1]
    assert created.startswith("tdyM_")
    assert keys.main(["listele"], store=store) == 0
    assert "grok" in capsys.readouterr().out
    assert keys.main(["iptal", "--etiket", "grok"], store=store) == 0
    assert store.principal(created) is None
    assert keys.main(["olustur", "--etiket", "x", "--email", READER], store=store) == 2


# -- S1a / R4: WAL and busy_timeout -------------------------------------------------------

def test_connections_use_wal_and_a_five_second_busy_timeout(store):
    with store._connect() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000


def test_writer_commits_while_another_connection_holds_a_read_transaction(tmp_path, store, client_id):
    reader = sqlite3.connect(tmp_path / "oauth.sqlite3", isolation_level=None, timeout=0)
    try:
        reader.execute("BEGIN")
        assert reader.execute("SELECT COUNT(*) FROM oauth_code").fetchone()[0] == 0
        code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")  # must not wait
        assert reader.execute("SELECT COUNT(*) FROM oauth_code").fetchone()[0] == 0  # reader keeps its snapshot
        reader.execute("COMMIT")
    finally:
        reader.close()
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER) is not None


def test_reader_is_not_blocked_by_an_open_write_transaction(tmp_path, store, client_id):
    pair = _pair(store, client_id)
    writer = sqlite3.connect(tmp_path / "oauth.sqlite3", isolation_level=None, timeout=0)
    try:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE oauth_access SET revoked_at = 1")  # uncommitted
        assert store.principal(pair.access_token) == FULL
        writer.execute("ROLLBACK")
    finally:
        writer.close()
    assert store.principal(pair.access_token) == FULL


def test_wal_side_files_are_private(tmp_path, store, client_id):
    path = tmp_path / "oauth.sqlite3"
    with store._connect() as held:  # WAL and SHM exist only while a connection is open
        held.execute("SELECT COUNT(*) FROM oauth_code").fetchone()
        store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
        for suffix in ("-wal", "-shm"):
            side = path.with_name(path.name + suffix)
            assert stat.S_IMODE(side.stat().st_mode) == 0o600, suffix


# -- S1b / T5: the store refuses to run outside WAL ------------------------------------------

@pytest.mark.parametrize("reported", ["delete", "memory", "truncate"])
def test_store_refuses_to_open_when_wal_cannot_be_enabled(tmp_path, monkeypatch, reported):
    class JournalModeStuck(sqlite3.Connection):
        def execute(self, sql, *args):
            if sql.replace(" ", "").upper() == "PRAGMAJOURNAL_MODE=WAL":
                return super().execute("SELECT ?", (reported,))
            return super().execute(sql, *args)

    real_connect = sqlite3.connect
    monkeypatch.setattr(oauth_store.sqlite3, "connect",
                        lambda *args, **kwargs: real_connect(*args, factory=JournalModeStuck, **kwargs))
    with pytest.raises(RuntimeError, match="journal_mode"):
        OAuthStore(tmp_path / "oauth.sqlite3")


def test_store_accepts_wal_case_insensitively(tmp_path, monkeypatch):
    class UpperCaseWal(sqlite3.Connection):
        def execute(self, sql, *args):
            if sql.replace(" ", "").upper() == "PRAGMAJOURNAL_MODE=WAL":
                super().execute(sql, *args)
                return super().execute("SELECT 'WAL'")
            return super().execute(sql, *args)

    real_connect = sqlite3.connect
    monkeypatch.setattr(oauth_store.sqlite3, "connect",
                        lambda *args, **kwargs: real_connect(*args, factory=UpperCaseWal, **kwargs))
    OAuthStore(tmp_path / "oauth.sqlite3")


# -- S1b / F5: PKCE bounds (RFC 7636 §4.1) -------------------------------------------------

@pytest.mark.parametrize("challenge,method", [
    (_challenge(VERIFIER), "s256"),
    (_challenge(VERIFIER), "S256 "),
    ("x", "S256"),
    (_challenge(VERIFIER)[:42], "S256"),
    (_challenge(VERIFIER) + "A", "S256"),
    (_challenge(VERIFIER)[:42] + "=", "S256"),
    (_challenge(VERIFIER)[:42] + "+", "S256"),
])
def test_issue_code_requires_exact_s256_and_a_43_character_challenge(store, client_id, challenge, method):
    with pytest.raises(ValueError):
        store.issue_code(FULL, client_id, REDIRECT, challenge, method)


@pytest.mark.parametrize("verifier", ["a", "v" * 42, "v" * 129, "v" * 42 + "+", "v" * 42 + "=", "v" * 42 + "ü"])
def test_redeem_refuses_verifiers_outside_rfc7636_bounds(store, client_id, verifier):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(verifier), "S256")
    assert store.redeem_code(code, client_id, REDIRECT, verifier) is None


def test_verifier_bounds_and_alphabet_edges_are_accepted(store, client_id):
    for verifier in ["v" * 43, "v" * 128, "Az09-._~" * 6]:
        code = store.issue_code(FULL, client_id, REDIRECT, _challenge(verifier), "S256")
        assert store.redeem_code(code, client_id, REDIRECT, verifier) is not None


def test_malformed_verifier_does_not_consume_the_code(store, client_id):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    assert store.redeem_code(code, client_id, REDIRECT, "short") is None
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER) is not None


# -- S1b / F6: replaying a redeemed code revokes the family it issued -------------------------

def test_code_replay_revokes_the_tokens_it_issued(tmp_path, store, client_id):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    pair = store.redeem_code(code, client_id, REDIRECT, VERIFIER)
    assert store.principal(pair.access_token) == FULL
    other = _pair(store, client_id)  # a different grant for the same person must survive
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER) is None
    assert store.principal(pair.access_token) is None
    assert store.refresh(pair.refresh_token, client_id) is None
    assert store.principal(other.access_token) == FULL
    with sqlite3.connect(tmp_path / "oauth.sqlite3") as conn:
        family = conn.execute("SELECT family_id FROM oauth_code WHERE used_at IS NOT NULL LIMIT 1").fetchone()[0]
        assert family
        revoked = conn.execute("SELECT COUNT(*) FROM oauth_refresh WHERE family_id = ? AND revoked_at IS NOT NULL",
                               (family,)).fetchone()[0]
    assert revoked == 1


def test_replay_revokes_the_family_even_after_it_refreshed(store, client_id):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    first = store.redeem_code(code, client_id, REDIRECT, VERIFIER)
    second = store.refresh(first.refresh_token, client_id)
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER) is None
    assert store.principal(second.access_token) is None
    assert store.refresh(second.refresh_token, client_id) is None


# -- S1b: a store file created by the pre-S1b schema still opens ------------------------------

PRE_S1B_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_code (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    challenge TEXT NOT NULL,
    challenge_method TEXT NOT NULL CHECK (challenge_method = 'S256'),
    expires_at INTEGER NOT NULL,
    used_at INTEGER
);
CREATE TABLE IF NOT EXISTS oauth_access (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    family_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS oauth_refresh (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    family_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER,
    revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS static_key (
    value_hash TEXT PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);
"""


def _columns(path, table):
    with sqlite3.connect(path) as conn:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_store_created_by_the_pre_s1b_schema_opens_and_migrates(tmp_path, clock):
    path = tmp_path / "oauth.sqlite3"
    old_key = "tdyM_" + "k" * 43
    conn = sqlite3.connect(path)
    conn.executescript(PRE_S1B_SCHEMA)
    conn.execute("INSERT INTO static_key (value_hash, label, email, created_at) VALUES (?, 'eski', ?, 1)",
                 (hashlib.sha256(old_key.encode()).hexdigest(), FULL))
    conn.commit()
    conn.close()

    store = OAuthStore(path, clock=clock)
    assert store.principal(old_key) == FULL  # existing rows survive the migration
    reopened = OAuthStore(path, clock=clock)  # idempotent: a second open adds nothing and does not fail
    fresh = tmp_path / "fresh.sqlite3"
    OAuthStore(fresh, clock=clock)
    with sqlite3.connect(fresh) as conn:
        tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    for table in tables:  # the migrated file ends up with exactly the columns of a fresh store
        assert _columns(path, table) == _columns(fresh, table), table
    assert "family_id" in _columns(path, "oauth_code")
    assert _pair(reopened, reopened.register_client("x", [REDIRECT]).client_id) is not None


# -- S1b / F2.2: persistent dynamic client registration ---------------------------------------

def test_register_client_persists_name_and_redirect_uris(tmp_path, store, clock):
    client = store.register_client("Claude", [REDIRECT, LOOPBACK])
    assert len(client.client_id) >= 20
    assert (client.client_name, client.redirect_uris, client.created_at) == ("Claude", (REDIRECT, LOOPBACK), int(clock.now))
    restarted = OAuthStore(tmp_path / "oauth.sqlite3", clock=clock)
    assert restarted.get_client(client.client_id) == client
    assert store.register_client("Claude", [REDIRECT]).client_id != client.client_id
    assert store.get_client("ted-mcp-public") is None
    assert store.get_client("") is None


def test_issue_code_requires_a_registered_client_and_one_of_its_redirects(store, client_id):
    challenge = _challenge(VERIFIER)
    with pytest.raises(ValueError):
        store.issue_code(FULL, "ted-mcp-public", REDIRECT, challenge, "S256")
    with pytest.raises(ValueError):
        store.issue_code(FULL, client_id, "https://claude.com/api/mcp/auth_callback", challenge, "S256")
    with pytest.raises(ValueError):
        store.issue_code(FULL, client_id, "http://127.0.0.1:53712/other", challenge, "S256")
    code = store.issue_code(FULL, client_id, "http://127.0.0.1:53712/callback", challenge, "S256")  # loopback: any port
    assert store.redeem_code(code, client_id, "http://127.0.0.1:53712/callback", VERIFIER) is not None


def _fill_clients(path, count, created_at, code_issued_at=None):
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO oauth_client (client_id, client_name, redirect_uris, created_at, code_issued_at)"
            " VALUES (?, '', ?, ?, ?)",
            [(f"filler-{created_at}-{i}", f'["{REDIRECT}"]', created_at, code_issued_at) for i in range(count)])


def _client_ids(path):
    with sqlite3.connect(path) as conn:
        return {row[0] for row in conn.execute("SELECT client_id FROM oauth_client")}


def test_client_cap_purges_only_clients_older_than_a_day_that_never_issued_a_code(tmp_path, store, clock):
    path = tmp_path / "oauth.sqlite3"
    used = store.register_client("used", [REDIRECT])
    store.issue_code(FULL, used.client_id, REDIRECT, _challenge(VERIFIER), "S256")
    _fill_clients(path, oauth_store.MAX_CLIENTS - 1, int(clock.now))
    clock.now += oauth_store.STALE_CLIENT_SECONDS  # exactly a day old: not stale yet
    with pytest.raises(oauth_store.ClientLimitReached):
        store.register_client("new", [REDIRECT])
    assert len(_client_ids(path)) == oauth_store.MAX_CLIENTS
    clock.now += 1
    fresh = store.register_client("new", [REDIRECT])
    assert _client_ids(path) == {used.client_id, fresh.client_id}


def test_client_cap_refuses_when_no_client_is_purgeable(tmp_path, store, clock):
    path = tmp_path / "oauth.sqlite3"
    old = int(clock.now) - 7 * 24 * 3600
    _fill_clients(path, oauth_store.MAX_CLIENTS // 2, old, code_issued_at=old)       # old but used
    _fill_clients(path, oauth_store.MAX_CLIENTS // 2, int(clock.now) - 60)            # unused but fresh
    with pytest.raises(oauth_store.ClientLimitReached):
        store.register_client("new", [REDIRECT])
    assert len(_client_ids(path)) == oauth_store.MAX_CLIENTS


# -- S1b / F7: single-use form states --------------------------------------------------------

def test_form_state_is_consumed_exactly_once(store, clock):
    nonce = hashlib.sha256(b"form-state").hexdigest()
    expires = int(clock.now) + 600
    assert store.consume_form_state(nonce, expires) is True
    assert store.consume_form_state(nonce, expires) is False
    assert store.consume_form_state(hashlib.sha256(b"other").hexdigest(), expires) is True


def test_concurrent_consumption_has_one_winner(store, clock):
    import threading

    nonce = hashlib.sha256(b"raced").hexdigest()
    barrier, results = threading.Barrier(8), []

    def consume():
        barrier.wait()
        results.append(store.consume_form_state(nonce, int(clock.now) + 600))

    threads = [threading.Thread(target=consume) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert sorted(results) == [False] * 7 + [True]


# -- S1b / F8: absolute family lifetime, revocation by email, startup purge ----------------------

DAY = 24 * 3600


def test_refresh_family_has_an_absolute_ninety_day_lifetime(store, client_id, clock):
    pair = _pair(store, client_id)
    for _ in range(3):  # keep refreshing inside each 30-day refresh window
        clock.now += 29 * DAY
        pair = store.refresh(pair.refresh_token, client_id)
        assert pair is not None
    clock.now += 3 * DAY - 1  # 90 days minus one second after the family was created
    pair = store.refresh(pair.refresh_token, client_id)
    assert pair is not None
    clock.now += 1  # exactly 90 days: refused although this refresh token is fresh
    assert store.refresh(pair.refresh_token, client_id) is None
    assert store.principal(pair.access_token) == FULL  # the last access token lives out its hour


def _revoked_rows(path, email):
    with sqlite3.connect(path) as conn:
        return sum(conn.execute(f"SELECT COUNT(*) FROM {table} WHERE email = ? AND revoked_at IS NOT NULL",
                                (email,)).fetchone()[0] for table in ("oauth_access", "oauth_refresh"))


def test_oauth_iptal_revokes_every_family_of_one_person(tmp_path, store, client_id, clock, capsys):
    other = "isikkurtx@gmail.com"
    first = _pair(store, client_id)
    second = store.refresh(_pair(store, client_id).refresh_token, client_id)
    code = store.issue_code(other, client_id, REDIRECT, _challenge(VERIFIER), "S256")
    theirs = store.redeem_code(code, client_id, REDIRECT, VERIFIER)
    pending = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")

    assert keys.main(["oauth-iptal", "--email", " DrMahirKurt@gmail.com "], store=store) == 0
    out = capsys.readouterr().out
    assert f"iptal edilen satır: {_revoked_rows(tmp_path / 'oauth.sqlite3', FULL)}" in out
    assert _revoked_rows(tmp_path / "oauth.sqlite3", FULL) >= 5
    for token in (first, second):
        assert store.principal(token.access_token) is None
        assert store.refresh(token.refresh_token, client_id) is None
    assert store.redeem_code(pending, client_id, REDIRECT, VERIFIER) is None  # a code minted before the kill switch
    assert store.principal(theirs.access_token) == other  # nobody else is touched

    assert keys.main(["oauth-iptal", "--email", FULL], store=store) == 0
    assert "iptal edilen satır: 0" in capsys.readouterr().out


def _count(path, table):
    with sqlite3.connect(path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_startup_purge_removes_rows_expired_for_more_than_a_day(tmp_path, store, client_id, clock):
    path = tmp_path / "oauth.sqlite3"
    t0 = int(clock.now)
    store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256")       # expires t0 + 300
    _pair(store, client_id)                                                         # access t0+3600, refresh t0+30d
    store.consume_form_state(hashlib.sha256(b"s").hexdigest(), t0 + 600)
    store.create_static_key("kalici", FULL)

    clock.now = t0 + oauth_store.CODE_TTL_SECONDS + DAY  # exactly a day past the code's expiry: kept
    store.purge_expired()
    assert _count(path, "oauth_code") == 2
    clock.now += 1
    store.purge_expired()
    assert _count(path, "oauth_code") == 0
    assert (_count(path, "oauth_access"), _count(path, "consumed_form_state")) == (1, 1)

    clock.now = t0 + oauth_store.ACCESS_TTL_SECONDS + DAY + 1
    store.purge_expired()
    assert (_count(path, "oauth_access"), _count(path, "consumed_form_state"), _count(path, "oauth_refresh")) == (0, 0, 1)

    clock.now = t0 + oauth_store.REFRESH_TTL_SECONDS + DAY + 1
    store.purge_expired()
    assert _count(path, "oauth_refresh") == 0
    assert (_count(path, "oauth_client"), _count(path, "static_key")) == (1, 1)  # never purged here


# -- S1b / R1: the resource travels from the code to every token of the family -------------------

RESOURCE = "https://mcp.tedy.online/mcp"


def test_resource_is_bound_to_the_code_and_every_token_of_its_family(store, client_id):
    code = store.issue_code(FULL, client_id, REDIRECT, _challenge(VERIFIER), "S256", resource=RESOURCE)
    assert store.redeem_code(code, client_id, REDIRECT, VERIFIER, resource="https://evil.example/rs") is None
    pair = store.redeem_code(code, client_id, REDIRECT, VERIFIER, resource=RESOURCE)  # not consumed above
    assert pair is not None
    assert store.refresh(pair.refresh_token, client_id, resource="https://evil.example/rs") is None
    second = store.refresh(pair.refresh_token, client_id, resource=RESOURCE)
    assert second is not None
    assert store.refresh(second.refresh_token, client_id) is not None  # omitted: the family's binding applies
