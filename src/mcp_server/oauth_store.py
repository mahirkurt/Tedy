"""SQLite store for ted-mcp OAuth: codes, rotating refresh tokens and tdyM_ static keys.

Only SHA-256 hashes of issued values are stored. Every principal lookup re-checks the
household roster, so removing someone from src/roles.py invalidates their tokens at once.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

from src import roles

CODE_TTL_SECONDS = 300
ACCESS_TTL_SECONDS = 3600
REFRESH_TTL_SECONDS = 30 * 24 * 3600
STATIC_KEY_PREFIX = "tdyM_"

_SCHEMA = """
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
            conn.executescript(_SCHEMA)

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        # A plain sqlite3.Connection's own context manager only commits/rolls back a
        # transaction on exit — it never closes the connection. Wrap it ourselves so
        # every `with self._connect() as conn:` call site closes its connection too.
        conn = sqlite3.connect(self._path, timeout=5.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _now(self) -> int:
        return int(self._clock())

    # -- authorization codes -------------------------------------------------------
    def issue_code(self, email: str, client_id: str, redirect_uri: str,
                   code_challenge: str, code_challenge_method: str) -> str:
        if (code_challenge_method or "").upper() != "S256" or not code_challenge:
            raise ValueError("only PKCE S256 is accepted")
        if not roles.is_full(email):
            raise ValueError("email is not a full-role roster member")
        code = secrets.token_urlsafe(32)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO oauth_code (value_hash, email, client_id, redirect_uri, challenge,"
                " challenge_method, expires_at) VALUES (?, ?, ?, ?, ?, 'S256', ?)",
                (_hash(code), email.strip().lower(), client_id, redirect_uri, code_challenge,
                 self._now() + CODE_TTL_SECONDS),
            )
        return code

    def redeem_code(self, code: str, client_id: str, redirect_uri: str,
                    code_verifier: str) -> TokenPair | None:
        if not (code and client_id and redirect_uri and code_verifier):
            return None
        try:
            challenge = _s256(code_verifier)
        except UnicodeEncodeError:
            return None
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT email FROM oauth_code WHERE value_hash = ? AND client_id = ? AND redirect_uri = ?"
                " AND challenge = ? AND expires_at > ? AND used_at IS NULL",
                (_hash(code), client_id, redirect_uri, challenge, now),
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return None
            conn.execute("UPDATE oauth_code SET used_at = ? WHERE value_hash = ?", (now, _hash(code)))
            pair = self._issue_pair(conn, row["email"], client_id, secrets.token_hex(8), now)
            conn.execute("COMMIT")
        return pair

    # -- tokens --------------------------------------------------------------------
    def _issue_pair(self, conn: sqlite3.Connection, email: str, client_id: str,
                    family_id: str, now: int) -> TokenPair:
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO oauth_access (value_hash, email, family_id, expires_at) VALUES (?, ?, ?, ?)",
            (_hash(access), email, family_id, now + ACCESS_TTL_SECONDS),
        )
        conn.execute(
            "INSERT INTO oauth_refresh (value_hash, email, family_id, client_id, expires_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (_hash(refresh), email, family_id, client_id, now + REFRESH_TTL_SECONDS),
        )
        return TokenPair(access, refresh, ACCESS_TTL_SECONDS, email)

    def refresh(self, refresh_token: str, client_id: str) -> TokenPair | None:
        if not (refresh_token and client_id):
            return None
        now = self._now()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT email, family_id, client_id, expires_at, used_at, revoked_at"
                " FROM oauth_refresh WHERE value_hash = ?",
                (_hash(refresh_token),),
            ).fetchone()
            if row is None or row["client_id"] != client_id or row["revoked_at"] is not None:
                conn.execute("ROLLBACK")
                return None
            if row["used_at"] is not None:
                # Replay of a rotated refresh token: treat the family as stolen.
                conn.execute("UPDATE oauth_access SET revoked_at = ? WHERE family_id = ?", (now, row["family_id"]))
                conn.execute("UPDATE oauth_refresh SET revoked_at = ? WHERE family_id = ?", (now, row["family_id"]))
                conn.execute("COMMIT")
                return None
            if row["expires_at"] <= now or not roles.is_full(row["email"]):
                conn.execute("ROLLBACK")
                return None
            conn.execute("UPDATE oauth_refresh SET used_at = ? WHERE value_hash = ?", (now, _hash(refresh_token)))
            pair = self._issue_pair(conn, row["email"], client_id, row["family_id"], now)
            conn.execute("COMMIT")
        return pair

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
