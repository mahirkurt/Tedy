"""Verify a Google Identity Services credential for the OAuth consent step."""
from __future__ import annotations

from typing import Callable

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from src import roles

IdentityVerifier = Callable[[str, str], str]


class IdentityError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def verify_google_credential(credential: str, expected_nonce: str) -> str:
    """Return the verified, lower-cased email or raise IdentityError."""
    try:
        info = id_token.verify_oauth2_token(credential, google_requests.Request(), roles.GOOGLE_CLIENT_ID)
    except ValueError as exc:
        raise IdentityError("invalid_token") from exc
    if not info.get("email_verified"):
        raise IdentityError("email_not_verified")
    if not expected_nonce or info.get("nonce") != expected_nonce:
        raise IdentityError("nonce_mismatch")
    return str(info.get("email", "")).strip().lower()
