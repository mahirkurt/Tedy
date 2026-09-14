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
CLIENT = "ted-mcp-public"
REDIRECT = "https://claude.ai/api/mcp/auth_callback"
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


def _pair(store):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    return store.redeem_code(code, CLIENT, REDIRECT, VERIFIER)


def test_code_round_trip_binds_email(store):
    pair = _pair(store)
    assert pair is not None
    assert pair.email == FULL
    assert pair.expires_in == oauth_store.ACCESS_TTL_SECONDS
    assert store.principal(pair.access_token) == FULL


def test_code_is_single_use(store):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    assert store.redeem_code(code, CLIENT, REDIRECT, VERIFIER) is not None
    assert store.redeem_code(code, CLIENT, REDIRECT, VERIFIER) is None


@pytest.mark.parametrize("client,redirect,verifier", [
    ("other-client", REDIRECT, VERIFIER),
    (CLIENT, "https://grok.com/cb", VERIFIER),
    (CLIENT, REDIRECT, "w" * 64),
])
def test_code_redeem_rejects_mismatch(store, client, redirect, verifier):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    assert store.redeem_code(code, client, redirect, verifier) is None


def test_code_expires_after_five_minutes(store, clock):
    code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
    clock.now += oauth_store.CODE_TTL_SECONDS + 1
    assert store.redeem_code(code, CLIENT, REDIRECT, VERIFIER) is None


def test_issue_code_rejects_plain_pkce_and_non_full_email(store):
    with pytest.raises(ValueError):
        store.issue_code(FULL, CLIENT, REDIRECT, VERIFIER, "plain")
    with pytest.raises(ValueError):
        store.issue_code(READER, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")


def test_access_token_expires(store, clock):
    pair = _pair(store)
    clock.now += oauth_store.ACCESS_TTL_SECONDS + 1
    assert store.principal(pair.access_token) is None


def test_refresh_rotates_and_old_refresh_is_single_use(store):
    first = _pair(store)
    second = store.refresh(first.refresh_token, CLIENT)
    assert second is not None
    assert second.refresh_token != first.refresh_token
    assert store.principal(second.access_token) == FULL


def test_refresh_reuse_revokes_the_whole_family(store):
    first = _pair(store)
    second = store.refresh(first.refresh_token, CLIENT)
    assert store.refresh(first.refresh_token, CLIENT) is None  # replay
    assert store.principal(second.access_token) is None
    assert store.refresh(second.refresh_token, CLIENT) is None


def test_refresh_rejects_other_client_and_expiry(store, clock):
    first = _pair(store)
    assert store.refresh(first.refresh_token, "other-client") is None
    other = _pair(store)
    clock.now += oauth_store.REFRESH_TTL_SECONDS + 1
    assert store.refresh(other.refresh_token, CLIENT) is None


def test_roster_change_invalidates_existing_tokens(store, monkeypatch):
    pair = _pair(store)
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


def test_writer_commits_while_another_connection_holds_a_read_transaction(tmp_path, store):
    reader = sqlite3.connect(tmp_path / "oauth.sqlite3", isolation_level=None, timeout=0)
    try:
        reader.execute("BEGIN")
        assert reader.execute("SELECT COUNT(*) FROM oauth_code").fetchone()[0] == 0
        code = store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")  # must not wait
        assert reader.execute("SELECT COUNT(*) FROM oauth_code").fetchone()[0] == 0  # reader keeps its snapshot
        reader.execute("COMMIT")
    finally:
        reader.close()
    assert store.redeem_code(code, CLIENT, REDIRECT, VERIFIER) is not None


def test_reader_is_not_blocked_by_an_open_write_transaction(tmp_path, store):
    pair = _pair(store)
    writer = sqlite3.connect(tmp_path / "oauth.sqlite3", isolation_level=None, timeout=0)
    try:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE oauth_access SET revoked_at = 1")  # uncommitted
        assert store.principal(pair.access_token) == FULL
        writer.execute("ROLLBACK")
    finally:
        writer.close()
    assert store.principal(pair.access_token) == FULL


def test_wal_side_files_are_private(tmp_path, store):
    path = tmp_path / "oauth.sqlite3"
    with store._connect() as held:  # WAL and SHM exist only while a connection is open
        held.execute("SELECT COUNT(*) FROM oauth_code").fetchone()
        store.issue_code(FULL, CLIENT, REDIRECT, _challenge(VERIFIER), "S256")
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
