"""Viewing tickets for modul.tedy.online (spec §5.4, plan decision K-P2).

The dashboard signs and ted-mcp verifies; both read EDUPEDIA_TICKET_SECRET. The verifier
never sees the email, so the MAC binds u = sha256(lowercased email)[:32], and ted-mcp also
requires u to belong to a current full-role roster member. Module and draft tickets are
domain-separated ("m|" vs "t|") so one can never open the other.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from typing import Iterable

from src.module_store import valid_slug, valid_taslak_id, valid_version

TTL_SECONDS = 600
SKEW_SECONDS = 60
MIN_SECRET_BYTES = 32
EXPIRED_TEXT = "Bağlantının süresi doldu; tedy.online'dan yeniden açın"
_HEX32 = re.compile(r"^[0-9a-f]{32}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_EXP = re.compile(r"^[0-9]{1,12}$")


class TicketConfigError(ValueError):
    """The ticket secret is missing or too short."""


def email_hash(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()[:32]


def _key(secret: bytes) -> bytes:
    if not isinstance(secret, (bytes, bytearray)) or len(secret) < MIN_SECRET_BYTES:
        raise TicketConfigError("EDUPEDIA_TICKET_SECRET must be at least 32 bytes")
    return bytes(secret)


def _message(kind: str, ident: str, version: int | None, u: str, exp: int) -> bytes:
    if kind == "m":
        return f"m|{ident}|v{version}|{u}|{exp}".encode("utf-8")
    if kind == "t":
        return f"t|{ident}|{u}|{exp}".encode("utf-8")
    raise ValueError("kind must be 'm' or 't'")


def sign(secret: bytes, kind: str, ident: str, version: int | None, u: str, exp: int) -> str:
    return hmac.new(_key(secret), _message(kind, ident, version, u, exp), hashlib.sha256).hexdigest()


def issue_module(secret: bytes, base_url: str, email: str, slug: str, version: int, now: float) -> dict:
    if not valid_slug(slug) or not valid_version(version):
        raise ValueError("gecersiz_modul")
    exp = int(now) + TTL_SECONDS
    u = email_hash(email)
    t = sign(secret, "m", slug, version, u, exp)
    return {"url": f"{base_url.rstrip('/')}/m/{slug}/v{version}?t={t}&e={exp}&u={u}", "exp": exp}


def issue_draft(secret: bytes, base_url: str, email: str, taslak_id: str, now: float) -> dict:
    if not valid_taslak_id(taslak_id):
        raise ValueError("gecersiz_taslak")
    exp = int(now) + TTL_SECONDS
    u = email_hash(email)
    t = sign(secret, "t", taslak_id, None, u, exp)
    return {"url": f"{base_url.rstrip('/')}/taslak/{taslak_id}?t={t}&e={exp}&u={u}", "exp": exp}


def verify(secret: bytes, kind: str, ident: str, version: int | None, t: object, e: object, u: object,
           now: float, allowed_u: Iterable[str]) -> str | None:
    """None when the ticket is valid; otherwise a short internal reason (never shown to viewers)."""
    if not isinstance(t, str) or not _HEX64.fullmatch(t):
        return "imza_bicimi"
    if not isinstance(u, str) or not _HEX32.fullmatch(u):
        return "u_bicimi"
    if not isinstance(e, str) or not _EXP.fullmatch(e):
        return "exp_bicimi"
    exp = int(e)
    if exp < int(now):
        return "suresi_doldu"
    if exp > int(now) + TTL_SECONDS + SKEW_SECONDS:
        return "exp_ileri"
    if u not in set(allowed_u):
        return "yetkisiz"
    if not hmac.compare_digest(sign(secret, kind, ident, version, u, exp), t):
        return "imza"
    return None
