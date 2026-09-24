"""Household roster: the single source of who may use TEDY and with which role.

Two processes import this module: the Flask dashboard (src/dashboard_api.py) and the
MCP orchestrator (src/mcp_server). The orchestrator cannot import src.dashboard_api,
because that import chdirs, loads .env, requires DASHBOARD_SECRET_KEY and builds the
Flask app as side effects.
"""
from __future__ import annotations

GOOGLE_CLIENT_ID = "343043757928-mivqip09orvrf73m7kj9b0atohgin2ho.apps.googleusercontent.com"

# "full"   — the household dashboard: every page and every endpoint.
# "reader" — Tedy Books only. Nothing else about Işık's school life is visible.
ROLE_FULL = "full"
ROLE_READER = "reader"

USER_ROLES = {
    "isikkurtx@gmail.com": ROLE_FULL,
    "drmahirkurt@gmail.com": ROLE_FULL,
    "ozlem.murzoglu@gmail.com": ROLE_FULL,
    "huriye.murzoglu@gmail.com": ROLE_FULL,
    "murzogluhulya@gmail.com": ROLE_READER,
    "mahirkurtmd@gmail.com": ROLE_READER,
}

# Whose school life TEDY is. The assistant says "sen" to this account and speaks
# to every other full-role member about Işık (assistant_core, "## Hitap").
OGRENCI_EMAILS = frozenset({"isikkurtx@gmail.com"})

ALLOWED_EMAILS = set(USER_ROLES)
FULL_ACCESS_EMAILS = {e for e, r in USER_ROLES.items() if r == ROLE_FULL}


def role_of(email: str | None) -> str | None:
    """Role for an email, or None when the address is not on the roster."""
    if not email:
        return None
    return USER_ROLES.get(email.strip().lower())


def okur_turu(email: str | None) -> str:
    """Who is asking the assistant: "ogrenci" (Işık), "aile" (another full-role
    member) or "bilinmiyor" (an API key, the test bypass, anyone else)."""
    e = (email or "").strip().lower()
    if e in OGRENCI_EMAILS:
        return "ogrenci"
    return "aile" if USER_ROLES.get(e) == ROLE_FULL else "bilinmiyor"


def is_full(email: str | None) -> bool:
    """True only for roster members with the full role."""
    return role_of(email) == ROLE_FULL
