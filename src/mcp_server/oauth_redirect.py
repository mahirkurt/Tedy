"""redirect_uri and CORS origin policy for the four web surfaces.

A redirect_uri is accepted only when it is canonical (no whitespace, controls, userinfo, fragment,
upper-case scheme or host, or odd port; it re-serializes to itself), carries none of the
authorization response's own query keys, and is one of:

- an exact callback URL: DEFAULT_REDIRECT_URIS or TED_MCP_EXTRA_REDIRECT_URIS;
- Gemini's per-connector callback, whose last segment is this server's own public host;
- http loopback (localhost, 127.0.0.1, [::1]) on any port and path (RFC 8252): the code lands on
  the user's own machine.

Whole origins are never trusted: any other path on claude.ai, chatgpt.com, … could hand the query
string (and the code in it) to someone else. Neither is an exact URL whose page forwards the code on.
"""
from __future__ import annotations

import ipaddress
import re
from typing import Iterable
from urllib.parse import parse_qsl, urlsplit, urlunsplit

# Callback URLs measured from real connection attempts or taken from vendor documentation, 2026-09-14.
DEFAULT_REDIRECT_URIS = (
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
    "https://chatgpt.com/connector_platform_oauth_redirect",
    # Grok: from xAI's documentation only, not yet confirmed by a live connection (checked in sub-project 6).
    "https://grok.com/connectors/oauth/callback",
    # Deliberately absent: https://vscode.dev/redirect and https://insiders.vscode.dev/redirect. Measured
    # 2026-09-14, both forward the code to a destination taken from `state` (a *.github.dev host, for
    # instance), so with open DCR anyone could show a genuine Microsoft URL on the consent page. They can
    # still be added through TED_MCP_EXTRA_REDIRECT_URIS; VS Code desktop uses loopback.
)
# Gemini: .../r/user_bound_custom-mcp-<digits>-<public host with dots as underscores>.
GEMINI_REDIRECT_PREFIX = "https://oauth-redirect.googleusercontent.com/r/user_bound_custom-mcp-"

# Browser origins allowed to call /mcp directly (CORS). This says nothing about where codes may go.
CORS_ORIGINS = (
    "https://claude.ai",
    "https://claude.com",
    "https://chatgpt.com",
    "https://grok.com",
    "https://oauth-redirect.googleusercontent.com",
    "https://vscode.dev",
    "https://insiders.vscode.dev",
)
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
# Keys the authorization response itself appends; a redirect_uri already carrying one could make a
# client read the attacker's value instead of ours.
RESERVED_QUERY_KEYS = frozenset({"code", "state", "iss", "error", "error_description", "error_uri"})
EXTRA_REDIRECT_URIS_ENV = "TED_MCP_EXTRA_REDIRECT_URIS"


def redirect_uri_problem(uri: str) -> str | None:
    """Why uri is not a canonical, collision-free redirect_uri, or None when it is."""
    if not isinstance(uri, str) or not uri:
        return "empty"
    if uri != uri.strip():
        return "surrounding_whitespace"
    if not uri.isascii() or any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in uri):
        return "control_or_whitespace"
    try:
        parts = urlsplit(uri)
        port = parts.port  # ValueError for a non-numeric or out-of-range port
    except ValueError:
        return "unparseable"
    if parts.scheme not in ("http", "https") or not uri.startswith(parts.scheme + "://"):
        return "scheme"  # urlsplit lower-cases the scheme, so HTTPS:// is caught by the prefix check
    if "@" in parts.netloc:
        return "userinfo"
    if parts.fragment or "#" in uri:
        return "fragment"
    host = parts.hostname
    if not host:
        return "host"
    if host in LOOPBACK_HOSTS:
        if port is not None and not 1 <= port <= 65535:
            return "port"
    elif port is not None:
        return "port"
    # Rebuilt from the parsed pieces: refuses upper-case hosts, "host:" and "host:+80"-style ports.
    if parts.netloc != (f"[{host}]" if ":" in host else host) + ("" if port is None else f":{port}"):
        return "host"
    if urlunsplit(parts) != uri:
        return "not_canonical"
    if {key for key, _ in parse_qsl(parts.query, keep_blank_values=True)} & RESERVED_QUERY_KEYS:
        return "reserved_query_key"
    return None


def is_loopback(uri: str) -> bool:
    try:
        return urlsplit(uri).hostname in LOOPBACK_HOSTS
    except ValueError:
        return False


def _scheme_problem(uri: str) -> str | None:
    scheme = urlsplit(uri).scheme
    if is_loopback(uri):
        return None if scheme == "http" else "loopback_requires_http"
    return None if scheme == "https" else "https_required"


def parse_extra_redirect_uris(raw: str | None) -> tuple[str, ...]:
    """Comma-separated exact callbacks; any invalid entry stops startup with a ValueError."""
    uris: list[str] = []
    for entry in (raw or "").split(","):
        uri = entry.strip()
        if not uri:
            continue
        problem = redirect_uri_problem(uri) or _scheme_problem(uri)
        if problem:
            raise ValueError(f"{EXTRA_REDIRECT_URIS_ENV}: {uri!r} is not an acceptable redirect_uri ({problem})")
        uris.append(uri)
    return tuple(dict.fromkeys(uris))


EXTRA_FORM_ACTION_ORIGINS_ENV = "TED_MCP_EXTRA_FORM_ACTION_ORIGINS"
_DNS_HOST_RE = re.compile(r"^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$")


def form_action_origin_problem(origin: str) -> str | None:
    """Why origin is not an exact, canonical https origin for the consent pages' CSP form-action, or None."""
    if not isinstance(origin, str) or not origin:
        return "empty"
    if not origin.isascii() or any(c.isspace() or ord(c) < 0x20 or ord(c) == 0x7F for c in origin):
        return "control_or_whitespace"
    if "*" in origin:
        return "wildcard"
    if not origin.startswith("https://"):
        return "https_required"  # http://, HTTPS:// and every other scheme
    rest = origin[len("https://"):]
    if "@" in rest:
        return "userinfo"
    if "#" in rest:
        return "fragment"
    if "?" in rest:
        return "query"
    if "/" in rest:
        return "trailing_slash" if rest.index("/") == len(rest) - 1 else "path"
    if rest.startswith("["):
        return "loopback" if rest.split("]", 1)[0] == "[::1" else "ip_literal"
    host, sep, port = rest.partition(":")
    if sep:
        if not (port.isdigit() and port == str(int(port)) and 1 <= int(port) <= 65535):
            return "port"
        if int(port) == 443:
            return "default_port"  # https://host:443 is https://host; only the short form is canonical
    if host != host.lower():
        return "uppercase"
    if host == "localhost" or host.endswith(".localhost"):
        return "loopback"
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        return "loopback" if address.is_loopback else "ip_literal"
    if not _DNS_HOST_RE.match(host):
        return "host"
    return None


def parse_extra_form_action_origins(raw: str | None) -> tuple[str, ...]:
    """Comma-separated exact https origins appended to the consent pages' CSP form-action.

    Any invalid entry stops startup with a ValueError (same fail-closed style as
    TED_MCP_EXTRA_REDIRECT_URIS). An extra origin only widens the form's redirect chain;
    where the code may go is still the exact redirect_uri allowlist.
    """
    origins: list[str] = []
    for entry in (raw or "").split(","):
        origin = entry.strip()
        if not origin:
            continue
        problem = form_action_origin_problem(origin)
        if problem:
            raise ValueError(f"{EXTRA_FORM_ACTION_ORIGINS_ENV}: {origin!r} is not an exact canonical https origin ({problem})")
        origins.append(origin)
    return tuple(dict.fromkeys(origins))


class RedirectPolicy:
    """The redirect_uri allowlist for one deployment (its public host and extra callbacks)."""

    def __init__(self, public_base_url: str, extra_uris: Iterable[str] = ()) -> None:
        self._exact = frozenset(DEFAULT_REDIRECT_URIS) | frozenset(extra_uris)
        host = (urlsplit(public_base_url).hostname or "").replace(".", "_")
        self._gemini = re.compile(re.escape(GEMINI_REDIRECT_PREFIX) + "[0-9]+-" + re.escape(host)) if host else None

    def allows(self, uri: str) -> bool:
        if redirect_uri_problem(uri) is not None or _scheme_problem(uri) is not None:
            return False
        if is_loopback(uri) or uri in self._exact:
            return True
        return self._gemini is not None and self._gemini.fullmatch(uri) is not None


def redirect_matches(registered: str, requested: str) -> bool:
    """Exact string equality, except that a loopback redirect may use any port (RFC 8252 §7.3)."""
    if registered == requested:
        return True
    try:
        a, b = urlsplit(registered), urlsplit(requested)
    except ValueError:
        return False
    if a.hostname not in LOOPBACK_HOSTS or a.fragment or b.fragment:
        return False
    return (a.scheme, a.hostname, a.path, a.query) == (b.scheme, b.hostname, b.path, b.query)


def is_allowed_cors_origin(origin: str) -> bool:
    return origin in CORS_ORIGINS
