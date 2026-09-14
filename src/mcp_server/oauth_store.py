"""SQLite store for ted-mcp OAuth: codes, rotating refresh tokens and tdyM_ static keys.

Only SHA-256 hashes of issued values are stored. Every principal lookup re-checks the
household roster, so removing someone from src/roles.py invalidates their tokens at once.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Sequence

from src import roles
from src.mcp_server.oauth_redirect import redirect_matches

CODE_TTL_SECONDS = 300
ACCESS_TTL_SECONDS = 3600
REFRESH_TTL_SECONDS = 30 * 24 * 3600
# Rotation would otherwise keep a family alive forever; after this, the person consents again.
FAMILY_MAX_AGE_SECONDS = 90 * 24 * 3600
# Expired codes, tokens and consumed form states are deleted at startup once this long past expiry.
PURGE_GRACE_SECONDS = 24 * 3600
STATIC_KEY_PREFIX = "tdyM_"
# Dynamic client registration is open to anyone, so the table is capped. When it is full, clients
# that never produced a code and are more than a day old make room; otherwise registration is refused.
MAX_CLIENTS = 500
STALE_CLIENT_SECONDS = 24 * 3600
BUSY_TIMEOUT_MS = 5000

# RFC 7636 §4.1-4.2: an S256 challenge is 43 base64url characters; a verifier 43-128 unreserved ones.
_CODE_CHALLENGE = re.compile(r"[A-Za-z0-9_-]{43}")
_CODE_VERIFIER = re.compile(r"[A-Za-z0-9._~-]{43,128}")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS oauth_code (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    challenge TEXT NOT NULL,
    challenge_method TEXT NOT NULL CHECK (challenge_method = 'S256'),
    expires_at INTEGER NOT NULL,
    used_at INTEGER,
    family_id TEXT,
    resource TEXT
);
CREATE TABLE IF NOT EXISTS oauth_access (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    family_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    revoked_at INTEGER,
    resource TEXT
);
CREATE TABLE IF NOT EXISTS oauth_refresh (
    value_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    family_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    used_at INTEGER,
    revoked_at INTEGER,
    family_created_at INTEGER,
    resource TEXT
);
CREATE TABLE IF NOT EXISTS oauth_client (
    client_id TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    redirect_uris TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    code_issued_at INTEGER
);
CREATE TABLE IF NOT EXISTS consumed_form_state (
    nonce_hash TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS static_key (
    value_hash TEXT PRIMARY KEY,
    label TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    revoked_at INTEGER
);
"""

# Columns added after the first schema. CREATE TABLE IF NOT EXISTS leaves an existing file alone, so
# these are added one by one (only when missing) for a store created by an earlier version.
_ADDED_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "oauth_code": (("family_id", "TEXT"), ("resource", "TEXT")),
    "oauth_access": (("resource", "TEXT"),),
    "oauth_refresh": (("family_created_at", "INTEGER"), ("resource", "TEXT")),
}


def is_valid_code_challenge(code_challenge: str, code_challenge_method: str) -> bool:
    """Exactly S256 (case-sensitive) with a 43-character base64url challenge."""
    return (code_challenge_method == "S256" and isinstance(code_challenge, str)
            and _CODE_CHALLENGE.fullmatch(code_challenge) is not None)


class ClientLimitReached(Exception):
    """The client table is full and none of its clients may be purged yet."""


@dataclass(frozen=True)
class Client:
    client_id: str
    client_name: str
    redirect_uris: tuple[str, ...]
    created_at: int


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    email: str


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _s256(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class OAuthStore:
    def __init__(self, path: Path, clock: Callable[[], float] = time.time) -> None:
        self._path = Path(path)
        self._clock = clock
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        os.chmod(self._path, 0o600)
        with self._connect() as conn:
            # WAL is a property of the database file: set once, every later connection inherits it.
            # Readers then never block the writer (or the reverse), e.g. the keys CLI vs the server.
            mode = str(conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]).lower()
            # SQLite answers with the mode it actually kept (e.g. "delete" on a filesystem without
            # shared memory); silently staying in rollback mode would bring back reader/writer stalls.
            if mode != "wal" and not (mode == "memory" and str(self._path) == ":memory:"):
                raise RuntimeError(f"OAuth store could not enable WAL: journal_mode={mode!r}")
            conn.executescript(_SCHEMA)
            self._add_missing_columns(conn)

    @staticmethod
    def _add_missing_columns(conn: sqlite3.Connection) -> None:
        # Under the write lock, so a server and the keys CLI opening an old file at once cannot both
        # try to add the same column.
        conn.execute("BEGIN IMMEDIATE")
        try:
            for table, columns in _ADDED_COLUMNS.items():
                present = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
                for name, declaration in columns:
                    if name not in present:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # A plain sqlite3.Connection's own context manager only commits/rolls back a
        # transaction on exit — it never closes the connection. Wrap it ourselves so
        # every `with self._connect() as conn:` call site closes its connection too.
        conn = sqlite3.connect(self._path, timeout=BUSY_TIMEOUT_MS / 1000, isolation_level=None)
        conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _now(self) -> int:
        return int(self._clock())

    # -- registered clients (RFC 7591) ---------------------------------------------
    def register_client(self, client_name: str, redirect_uris: Sequence[str]) -> Client:
        """Persist a validated registration under a fresh random client_id."""
        client = Client(secrets.token_urlsafe(24), client_name, tuple(redirect_uris), self._now())
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if self._client_count(conn) >= MAX_CLIENTS:
                    conn.execute(
                        "DELETE FROM oauth_client WHERE code_issued_at IS NULL AND created_at < ?",
                        (client.created_at - STALE_CLIENT_SECONDS,),
                    )
                    if self._client_count(conn) >= MAX_CLIENTS:
                        raise ClientLimitReached(f"{MAX_CLIENTS} registered clients and none is purgeable")
                conn.execute(
                    "INSERT INTO oauth_client (client_id, client_name, redirect_uris, created_at) VALUES (?, ?, ?, ?)",
                    (client.client_id, client.client_name, json.dumps(list(client.redirect_uris)), client.created_at),
                )
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return client

    @staticmethod
    def _client_count(conn: sqlite3.Connection) -> int:
        return int(conn.execute("SELECT COUNT(*) FROM oauth_client").fetchone()[0])

    def get_client(self, client_id: str) -> Client | None:
        if not client_id or not client_id.isascii():
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT client_id, client_name, redirect_uris, created_at FROM oauth_client WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        if row is None:
            return None
        return Client(row["client_id"], row["client_name"], tuple(json.loads(row["redirect_uris"])), row["created_at"])

    # -- single-use consent form states ---------------------------------------------
    def consume_form_state(self, nonce_hash: str, expires_at: int) -> bool:
        """Mark a signed consent form state as used; False when it was already used.

        One INSERT is atomic, so of two concurrent posts of the same state exactly one wins.
        """
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO consumed_form_state (nonce_hash, expires_at) VALUES (?, ?)"
                " ON CONFLICT(nonce_hash) DO NOTHING",
                (nonce_hash, int(expires_at)),
            )
            return cur.rowcount == 1

    # -- authorization codes -------------------------------------------------------
    def issue_code(self, email: str, client_id: str, redirect_uri: str,
                   code_challenge: str, code_challenge_method: str, resource: str | None = None) -> str:
        if not is_valid_code_challenge(code_challenge, code_challenge_method):
            raise ValueError("only PKCE S256 with a 43-character challenge is accepted")
        if not roles.is_full(email):
            raise ValueError("email is not a full-role roster member")
        code = secrets.token_urlsafe(32)
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT redirect_uris FROM oauth_client WHERE client_id = ?", (client_id,)).fetchone()
            if row is None or not any(redirect_matches(r, redirect_uri) for r in json.loads(row["redirect_uris"])):
                conn.execute("ROLLBACK")
                raise ValueError("client_id is not registered for this redirect_uri")
            # A client that has produced a code is never purged to make room for new registrations.
            conn.execute("UPDATE oauth_client SET code_issued_at = ? WHERE client_id = ?", (now, client_id))
            conn.execute(
                "INSERT INTO oauth_code (value_hash, email, client_id, redirect_uri, challenge,"
                " challenge_method, expires_at, resource) VALUES (?, ?, ?, ?, ?, 'S256', ?, ?)",
                (_hash(code), email.strip().lower(), client_id, redirect_uri, code_challenge,
                 now + CODE_TTL_SECONDS, resource),
            )
            conn.execute("COMMIT")
        return code

    def redeem_code(self, code: str, client_id: str, redirect_uri: str,
                    code_verifier: str, resource: str | None = None) -> TokenPair | None:
        if not (code and client_id and redirect_uri):
            return None
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT email, client_id, redirect_uri, challenge, expires_at, used_at, family_id, resource"
                " FROM oauth_code WHERE value_hash = ?",
                (_hash(code),),
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return None
            if row["used_at"] is not None:
                # A redeemed code came back: it leaked. Revoke what it issued (OAuth 2.1 §4.1.3).
                if row["family_id"] is not None:
                    self._revoke_family(conn, row["family_id"], now)
                conn.execute("COMMIT")
                return None
            # The verifier is checked before it is hashed; a malformed one does not consume the code.
            if (_CODE_VERIFIER.fullmatch(code_verifier or "") is None
                    or not hmac.compare_digest(row["challenge"], _s256(code_verifier))
                    or row["client_id"] != client_id or row["redirect_uri"] != redirect_uri
                    or (resource is not None and row["resource"] != resource)
                    or row["expires_at"] <= now):
                conn.execute("ROLLBACK")
                return None
            family_id = secrets.token_hex(8)
            conn.execute("UPDATE oauth_code SET used_at = ?, family_id = ? WHERE value_hash = ?",
                         (now, family_id, _hash(code)))
            pair = self._issue_pair(conn, row["email"], client_id, family_id, now, family_created_at=now,
                                    resource=row["resource"])
            conn.execute("COMMIT")
        return pair

    # -- tokens --------------------------------------------------------------------
    @staticmethod
    def _revoke_family(conn: sqlite3.Connection, family_id: str, now: int) -> None:
        conn.execute("UPDATE oauth_access SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
                     (now, family_id))
        conn.execute("UPDATE oauth_refresh SET revoked_at = ? WHERE family_id = ? AND revoked_at IS NULL",
                     (now, family_id))

    def _issue_pair(self, conn: sqlite3.Connection, email: str, client_id: str,
                    family_id: str, now: int, family_created_at: int, resource: str | None) -> TokenPair:
        # The resource (audience) of the grant travels with every token of its family.
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO oauth_access (value_hash, email, family_id, expires_at, resource) VALUES (?, ?, ?, ?, ?)",
            (_hash(access), email, family_id, now + ACCESS_TTL_SECONDS, resource),
        )
        conn.execute(
            "INSERT INTO oauth_refresh (value_hash, email, family_id, client_id, expires_at, family_created_at,"
            " resource) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_hash(refresh), email, family_id, client_id, now + REFRESH_TTL_SECONDS, family_created_at, resource),
        )
        return TokenPair(access, refresh, ACCESS_TTL_SECONDS, email)

    def refresh(self, refresh_token: str, client_id: str, resource: str | None = None) -> TokenPair | None:
        if not (refresh_token and client_id):
            return None
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT email, family_id, client_id, expires_at, used_at, revoked_at, family_created_at, resource"
                " FROM oauth_refresh WHERE value_hash = ?",
                (_hash(refresh_token),),
            ).fetchone()
            if row is None or row["client_id"] != client_id or row["revoked_at"] is not None:
                conn.execute("ROLLBACK")
                return None
            if row["used_at"] is not None:
                # Replay of a rotated refresh token: treat the family as stolen.
                self._revoke_family(conn, row["family_id"], now)
                conn.execute("COMMIT")
                return None
            # A row without family_created_at (written before S1b) has no known age: fail closed.
            family_created_at = row["family_created_at"]
            if (row["expires_at"] <= now or family_created_at is None
                    or now >= family_created_at + FAMILY_MAX_AGE_SECONDS
                    or (resource is not None and row["resource"] != resource) or not roles.is_full(row["email"])):
                conn.execute("ROLLBACK")
                return None
            conn.execute("UPDATE oauth_refresh SET used_at = ? WHERE value_hash = ?", (now, _hash(refresh_token)))
            pair = self._issue_pair(conn, row["email"], client_id, row["family_id"], now, family_created_at,
                                    resource=row["resource"])
            conn.execute("COMMIT")
        return pair

    def revoke_email(self, email: str) -> dict[str, int]:
        """Kill switch for one person: revoke every access and refresh row, expire their pending codes."""
        address = (email or "").strip().lower()
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            access = conn.execute("UPDATE oauth_access SET revoked_at = ? WHERE email = ? AND revoked_at IS NULL",
                                  (now, address)).rowcount
            refresh = conn.execute("UPDATE oauth_refresh SET revoked_at = ? WHERE email = ? AND revoked_at IS NULL",
                                   (now, address)).rowcount
            # A code minted moments before the kill switch must not start a new family afterwards.
            codes = conn.execute("UPDATE oauth_code SET expires_at = ? WHERE email = ? AND used_at IS NULL"
                                 " AND expires_at > ?", (now, address, now)).rowcount
            conn.execute("COMMIT")
        return {"access": access, "refresh": refresh, "codes": codes}

    def purge_expired(self) -> int:
        """Delete codes, tokens and consumed form states more than a day past expiry (clients excepted)."""
        cutoff = self._now() - PURGE_GRACE_SECONDS
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            deleted = sum(conn.execute(f"DELETE FROM {table} WHERE expires_at < ?", (cutoff,)).rowcount
                          for table in ("oauth_code", "oauth_access", "oauth_refresh", "consumed_form_state"))
            conn.execute("COMMIT")
        return deleted

    def principal(self, bearer: str) -> str | None:
        if not bearer or not bearer.isascii():
            return None
        digest = _hash(bearer)
        with self._connect() as conn:
            if bearer.startswith(STATIC_KEY_PREFIX):
                row = conn.execute(
                    "SELECT email FROM static_key WHERE value_hash = ? AND revoked_at IS NULL", (digest,)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT email FROM oauth_access WHERE value_hash = ? AND expires_at > ? AND revoked_at IS NULL",
                    (digest, self._now()),
                ).fetchone()
        if row is None or not roles.is_full(row["email"]):
            return None
        return row["email"]

    # -- static keys ---------------------------------------------------------------
    def create_static_key(self, label: str, email: str) -> str:
        if not label or not roles.is_full(email):
            raise ValueError("static keys are issued only to full-role roster members")
        key = STATIC_KEY_PREFIX + secrets.token_urlsafe(32)
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO static_key (value_hash, label, email, created_at) VALUES (?, ?, ?, ?)",
                    (_hash(key), label, email.strip().lower(), self._now()),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"label already exists: {label}") from exc
        return key

    def revoke_static_key(self, label: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE static_key SET revoked_at = ? WHERE label = ? AND revoked_at IS NULL",
                (self._now(), label),
            )
            changed = cur.rowcount == 1
        return changed

    def list_static_keys(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT label, email, created_at, revoked_at FROM static_key ORDER BY created_at, label"
            ).fetchall()
        return [
            {"label": r["label"], "email": r["email"], "created_at": r["created_at"], "revoked": r["revoked_at"] is not None}
            for r in rows
        ]
