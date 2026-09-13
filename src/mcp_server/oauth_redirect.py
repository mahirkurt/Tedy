"""redirect_uri and CORS origin policy for the four web surfaces (fleet pattern).

Whole-origin match (scheme + netloc) against a fixed allowlist, so lookalikes such as
https://claude.ai.evil.com and scheme downgrades such as http://claude.ai are rejected.
Loopback is accepted on any port (RFC 8252): the code lands on the user's own machine.
"""
from __future__ import annotations

from urllib.parse import urlparse

ALLOWED_ORIGINS = (
    "https://claude.ai",
    "https://claude.com",
    "https://chatgpt.com",
    "https://grok.com",
    "https://oauth-redirect.googleusercontent.com",
    "https://vscode.dev",
    "https://insiders.vscode.dev",
)
_LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1")


def is_allowed_redirect(redirect_uri: str) -> bool:
    try:
        parsed = urlparse(redirect_uri)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.fragment:
        return False
    if parsed.username or parsed.password:
        return False
    if parsed.hostname in _LOOPBACK_HOSTS:
        return True
    return f"{parsed.scheme}://{parsed.netloc}" in ALLOWED_ORIGINS


def is_allowed_cors_origin(origin: str) -> bool:
    return origin in ALLOWED_ORIGINS
