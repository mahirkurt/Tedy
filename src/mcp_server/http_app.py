"""Starlette app for ted-mcp: OAuth 2.1 discovery, DCR, CORS, host guard, bearer gate, MCP."""
from __future__ import annotations

import base64
import contextlib
import functools
import hashlib
import hmac
import html
import json
import secrets
import time
import unicodedata
from typing import Any, Callable, Mapping
from urllib.parse import urlencode, urlparse, urlsplit, urlunparse, parse_qsl

import anyio
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.datastructures import FormData
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from src.mcp_server import __version__
from src.mcp_server.config import Settings
from src.mcp_server.google_identity import IdentityVerifier, is_well_formed_credential, verify_google_credential
from src.mcp_server.oauth_redirect import RedirectPolicy, is_allowed_cors_origin, redirect_matches
from src.mcp_server.oauth_store import Client, ClientLimitReached, OAuthStore, is_valid_code_challenge
from src import roles
from src.mcp_server.google_identity import IdentityError
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse

REALM = "ted-mcp"
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}

FORM_TTL_SECONDS = 600
OAUTH_MAX_BODY_BYTES = 16_384
# Google verification gets its own worker-thread budget, so a burst of consents (or a slow cert
# fetch) can never take the threads the bearer gate and the token endpoint need.
VERIFY_LIMITER_TOKENS = 4
_VERIFY_LIMITER = anyio.CapacityLimiter(VERIFY_LIMITER_TOKENS)
MAX_REDIRECT_URIS = 5
MAX_CLIENT_NAME_CHARS = 100
# Controls, format characters (bidi overrides, zero-width joiners), lone surrogates and line/paragraph
# separators: none belong in a name shown to a family member deciding whether to grant access.
_UNSAFE_NAME_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Zl", "Zp"})
_FORM_KEYS = ("client_id", "redirect_uri", "state", "code_challenge", "code_challenge_method", "scope", "resource")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# A signed state names its step, so the sign-in state can never be posted as the decision state
# (which carries a verified email) or the other way round.
PURPOSE_SIGN_IN = "authorize"
PURPOSE_DECISION = "consent"


def sign_form_state(params: dict[str, str], secret: bytes, now: float, purpose: str = PURPOSE_SIGN_IN) -> str:
    # "n" makes every issued state unique: single use is keyed on the state, so two identical
    # requests in the same second (a retry, a reloaded page) must not share one.
    body = {"p": params, "exp": int(now) + FORM_TTL_SECONDS, "u": purpose, "n": secrets.token_urlsafe(16)}
    payload = _b64u(json.dumps(body, sort_keys=True).encode())
    sig = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def read_form_state(token: str, secret: bytes, now: float, purpose: str = PURPOSE_SIGN_IN) -> dict[str, str]:
    try:
        payload, sig = token.split(".", 1)
        expected = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig.encode("utf-8"), expected.encode("ascii")):
            raise ValueError("form_state_invalid")
        data = json.loads(_b64u_decode(payload))
    except (ValueError, UnicodeEncodeError) as exc:
        if str(exc) == "form_state_invalid":
            raise
        raise ValueError("form_state_invalid") from exc
    if not isinstance(data, dict) or data.get("u") != purpose:
        raise ValueError("form_state_invalid")
    if int(data.get("exp", 0)) < int(now):
        raise ValueError("form_state_expired")
    return {k: str(v) for k, v in (data.get("p") or {}).items()}


def nonce_for(form_state: str) -> str:
    return hashlib.sha256(form_state.encode("ascii")).hexdigest()


def _with_query(uri: str, extra: dict[str, str]) -> str:
    parts = urlparse(uri)
    query = parse_qsl(parts.query, keep_blank_values=True) + list(extra.items())
    return urlunparse(parts._replace(query=urlencode(query)))


_PAGE_STYLE = (
    'body{font-family:"IBM Plex Sans",system-ui,sans-serif;background:#f4f4f4;color:#161616;margin:0;padding:48px 16px}'
    "main{max-width:480px;margin:auto;background:#fff;padding:32px;border-top:4px solid #0f62fe}"
    "h1{font-size:1.5rem;font-weight:400;margin:0 0 16px} p{line-height:1.5}"
    "code{background:#e0e0e0;padding:2px 4px;word-break:break-all}"
    "button{font:inherit;padding:12px 24px;margin:8px 8px 0 0;border:0;cursor:pointer}"
    "button[value=onayla]{background:#0f62fe;color:#fff} button[value=reddet]{background:#e0e0e0;color:#161616}"
)
# The only inline script. Its hash goes into script-src, so it must stay byte-for-byte static.
_CONSENT_SCRIPT = ('function tedyConsent(r){document.getElementById("credential").value=r.credential;'
                   'document.getElementById("consent").submit();}')
_CONSENT_SCRIPT_HASH = "'sha256-" + base64.b64encode(hashlib.sha256(_CONSENT_SCRIPT.encode("utf-8")).digest()).decode() + "'"
_UNNAMED_CLIENT = "Adı belirtilmemiş bir uygulama"

_CONSENT_PAGE = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TEDY edupedia bağlantısı</title>
<style>{style}</style>
<script src="https://accounts.google.com/gsi/client" async></script></head>
<body><main>
<h1>edupedia'yı TEDY hesabına bağla</h1>
<p><strong>{client_name}</strong> uygulaması, Google hesabınızla TEDY edupedia araçlarını kullanmak için izin istiyor.</p>
<p>Onay verilirse yetki yalnız şu adrese gönderilir:<br><code>{redirect_uri}</code></p>
<p>Yalnız TEDY aile listesindeki tam yetkili hesaplar onay verebilir. Google ile giriş yaptıktan sonra
ayrıca Onayla ya da Reddet seçmeniz istenir.</p>
<form id="consent" method="post" action="/oauth/authorize">
<input type="hidden" name="form_state" value="{form_state}">
<input type="hidden" name="credential" id="credential" value="">
</form>
<div id="g_id_onload" data-client_id="{google_client_id}" data-nonce="{nonce}" data-callback="tedyConsent"
     data-auto_prompt="false"></div>
<div class="g_id_signin" data-type="standard" data-text="continue_with" data-locale="tr"></div>
<script>{script}</script>
</main></body></html>"""

_DECISION_PAGE = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TEDY edupedia bağlantısı</title>
<style>{style}</style></head>
<body><main>
<h1>Bağlantıyı onaylıyor musunuz?</h1>
<p><strong>{client_name}</strong> uygulaması, <strong>{email}</strong> hesabıyla TEDY edupedia araçlarını
kullanmak istiyor.</p>
<p>Onaylarsanız yetki yalnız şu adrese gönderilir:<br><code>{redirect_uri}</code></p>
<form method="post" action="/oauth/authorize">
<input type="hidden" name="consent_state" value="{consent_state}">
<button type="submit" name="karar" value="onayla">Onayla</button>
<button type="submit" name="karar" value="reddet">Reddet</button>
</form>
</main></body></html>"""


def _csp_origin(uri: str) -> str:
    """CSP source for the origin of an already validated URI.

    An IPv6 literal is not a valid CSP host-source, so [::1] falls back to its scheme; the redirect
    target itself is still the exact, server-validated URI.
    """
    parts = urlsplit(uri)
    if ":" in (parts.hostname or ""):
        return f"{parts.scheme}:"
    return f"{parts.scheme}://{parts.netloc}"


def _consent_page_headers(issuer: str, redirect_uri: str, google_sign_in: bool) -> dict[str, str]:
    directives = ["default-src 'none'"]
    if google_sign_in:
        directives += [
            f"script-src https://accounts.google.com/gsi/client {_CONSENT_SCRIPT_HASH}",
            "frame-src https://accounts.google.com/gsi/",
            "connect-src https://accounts.google.com/gsi/",
            "style-src 'unsafe-inline' https://accounts.google.com/gsi/style",
        ]
    else:
        directives.append("style-src 'unsafe-inline'")
    # 'self' alone is not enough (measured in a sibling server): the page may sit in an opaque origin,
    # and Chrome applies form-action along the redirect chain, so both origins are named explicitly.
    directives += [
        f"form-action 'self' {_csp_origin(issuer)} {_csp_origin(redirect_uri)}",
        "frame-ancestors 'none'",
        "base-uri 'none'",
    ]
    return {
        "content-security-policy": "; ".join(directives),
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
        "cache-control": "no-store",
        "x-content-type-options": "nosniff",
    }


def is_acceptable_client_name(name: object) -> bool:
    return (isinstance(name, str) and len(name) <= MAX_CLIENT_NAME_CHARS
            and not any(unicodedata.category(c) in _UNSAFE_NAME_CATEGORIES for c in name))


def _header(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers") or []:
        if key == name:
            return value.decode("latin-1")
    return ""


async def _send_json(send: Send, status: int, body: dict[str, Any], extra: list[tuple[bytes, bytes]] | None = None) -> None:
    payload = json.dumps(body).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())]
    await send({"type": "http.response.start", "status": status, "headers": headers + (extra or [])})
    await send({"type": "http.response.body", "body": payload})


class CorsMiddleware:
    """Outermost: answers preflight before auth and exposes WWW-Authenticate to browsers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        origin = _header(scope, b"origin")
        allowed = bool(origin) and is_allowed_cors_origin(origin)
        cors = [
            (b"access-control-allow-origin", origin.encode("latin-1")),
            (b"access-control-expose-headers", b"mcp-session-id, www-authenticate"),
            (b"vary", b"Origin"),
        ] if allowed else []
        if scope["method"] == "OPTIONS" and _header(scope, b"access-control-request-method"):
            headers = cors + ([
                (b"access-control-allow-methods", b"GET, POST, DELETE, OPTIONS"),
                (b"access-control-allow-headers", b"authorization, content-type, mcp-session-id, mcp-protocol-version"),
                (b"access-control-max-age", b"600"),
            ] if allowed else [])
            await send({"type": "http.response.start", "status": 204, "headers": headers})
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_with_cors(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start" and cors:
                message = {**message, "headers": list(message.get("headers") or []) + cors}
            await send(message)

        await self.app(scope, receive, send_with_cors)


def _host_name(host_header: str) -> str | None:
    """Lower-cased host of a Host header that is exactly host[:port] with port 1-65535, else None."""
    if not host_header or not host_header.isascii() or host_header.endswith(":"):
        return None
    # urlsplit silently drops tabs and newlines, so refuse whitespace and control bytes first.
    if any(c.isspace() or not c.isprintable() for c in host_header):
        return None
    try:
        parts = urlsplit("//" + host_header)
        port = parts.port  # ValueError for a non-numeric or out-of-range port
    except ValueError:
        return None
    if parts.hostname is None or "@" in parts.netloc or parts.path or parts.query or parts.fragment:
        return None
    if port is not None and not 1 <= port <= 65535:
        return None
    return parts.hostname


class HostGuardMiddleware:
    """DNS-rebinding guard for /mcp: only the public host(s) and loopback."""

    def __init__(self, app: ASGIApp, allowed_hosts: tuple[str, ...]) -> None:
        self.app = app
        self.allowed = {h.lower() for h in allowed_hosts} | _LOOPBACK_HOSTS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            host = _host_name(_header(scope, b"host"))
            if host is None or host not in self.allowed:
                await _send_json(send, 400, {"error": "host_not_allowed"})
                return
        await self.app(scope, receive, send)


class BearerGateMiddleware:
    """Resolves the bearer to a roster email and hands it to tools via scope['state']."""

    def __init__(self, app: ASGIApp, store: OAuthStore, base_url: str) -> None:
        self.app = app
        self.store = store
        self.challenge = f'Bearer realm="{REALM}", resource_metadata="{base_url}/.well-known/oauth-protected-resource"'

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            auth = _header(scope, b"authorization")
            token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
            # SQLite lookup off the event loop: a lock held elsewhere must not stall every request.
            email = await anyio.to_thread.run_sync(self.store.principal, token) if token else None
            if email is None:
                await _send_json(send, 401, {"error": "unauthorized"},
                                 [(b"www-authenticate", self.challenge.encode("latin-1"))])
                return
            scope.setdefault("state", {})["ted_email"] = email
        await self.app(scope, receive, send)


class BodyLimitMiddleware:
    """Caps request bodies before anything buffers them: 16 KiB on /oauth/*, a setting on /mcp.

    A declared Content-Length over the cap is refused without calling the app. Streamed bytes are
    counted too, so a missing or understated Content-Length cannot slip past: once the cap is
    crossed the client gets 413 and the app sees a disconnect; anything the app still tries to
    send, or raises because its body was cut off, is dropped because the 413 owns the response.
    """

    def __init__(self, app: ASGIApp, mcp_max_body_bytes: int) -> None:
        self.app = app
        self.mcp_max_body_bytes = mcp_max_body_bytes

    def _limit_for(self, path: str) -> int | None:
        if path == "/oauth" or path.startswith("/oauth/"):
            return OAUTH_MAX_BODY_BYTES
        if path.startswith("/mcp"):
            return self.mcp_max_body_bytes
        return None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = self._limit_for(scope["path"]) if scope["type"] == "http" else None
        if limit is None:
            await self.app(scope, receive, send)
            return
        declared = _header(scope, b"content-length")
        if declared.isascii() and declared.isdigit() and int(declared) > limit:
            await _send_too_large(send)
            return

        received = 0
        rejected = False
        response_started = False

        async def limited_receive() -> dict[str, Any]:
            nonlocal received, rejected
            if rejected:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    rejected = True
                    if not response_started:
                        await _send_too_large(send)
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: dict[str, Any]) -> None:
            nonlocal response_started
            if rejected:
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not rejected:
                raise


async def _send_too_large(send: Send) -> None:
    # The unread remainder of the body is never consumed, so the connection is not reusable.
    await _send_json(send, 413, {"error": "payload_too_large"}, [(b"connection", b"close")])


async def _limited_form(request: Request) -> FormData:
    return await request.form(max_files=0, max_fields=20, max_part_size=8192)


def build_app(
    settings: Settings,
    store: OAuthStore,
    mcp: FastMCP,
    verify_identity: IdentityVerifier = verify_google_credential,
    form_secret: bytes = b"",
    clock: Callable[[], float] = time.time,
) -> Starlette:
    base = settings.public_base_url
    if len(form_secret) < 32:
        raise ValueError("form_secret must be at least 32 bytes")
    redirect_policy = RedirectPolicy(base, settings.extra_redirect_uris)
    # The one resource (audience) this server protects: exactly what its protected-resource metadata says.
    resource_uri = f"{base}/mcp"

    async def health(request: Request) -> Response:
        return JSONResponse({"status": "ok", "version": __version__})

    async def protected_resource(request: Request) -> Response:
        return JSONResponse({
            "resource": resource_uri,
            "authorization_servers": [base],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["edupedia"],
        })

    async def authorization_server(request: Request) -> Response:
        return JSONResponse({
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["edupedia"],
        })

    def _registration_error(error: str) -> Response:
        return JSONResponse({"error": error}, status_code=400)

    async def register(request: Request) -> Response:
        try:
            body = await request.json()
        except ValueError:
            return _registration_error("invalid_client_metadata")
        if not isinstance(body, dict):
            return _registration_error("invalid_client_metadata")
        uris = body.get("redirect_uris")
        if (not isinstance(uris, list) or not 1 <= len(uris) <= MAX_REDIRECT_URIS
                or not all(isinstance(u, str) and redirect_policy.allows(u) for u in uris)):
            return _registration_error("invalid_redirect_uri")
        name = "" if body.get("client_name") is None else body["client_name"]
        if not is_acceptable_client_name(name):
            return _registration_error("invalid_client_metadata")
        try:
            client = await anyio.to_thread.run_sync(store.register_client, name, uris)
        except ClientLimitReached:
            return _registration_error("invalid_client_metadata")
        registered: dict[str, Any] = {
            "client_id": client.client_id,
            "client_id_issued_at": client.created_at,
            "redirect_uris": list(client.redirect_uris),
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        }
        if client.client_name:
            registered["client_name"] = client.client_name
        return JSONResponse(registered, status_code=201)

    async def _registered_client(client_id: str) -> Client | None:
        return await anyio.to_thread.run_sync(store.get_client, client_id) if client_id else None

    def _is_registered_redirect(client: Client, redirect_uri: str) -> bool:
        # Still inside today's policy (canonical, allowlisted) and equal to one the client registered.
        return redirect_policy.allows(redirect_uri) and any(
            redirect_matches(registered, redirect_uri) for registered in client.redirect_uris)

    def _bad(reason: str) -> Response:
        return PlainTextResponse(f"Geçersiz yetkilendirme isteği: {reason}", status_code=400)

    async def authorize(request: Request) -> Response:
        if request.method == "GET":
            q = request.query_params
            # An unknown client or redirect gets an error page here, never a redirect (RFC 6749 §4.1.2.1).
            client = await _registered_client(q.get("client_id", ""))
            if client is None:
                return _bad("invalid_client")
            redirect_uri = q.get("redirect_uri", "")
            if not _is_registered_redirect(client, redirect_uri):
                return _bad("redirect_uri")
            if q.get("response_type") != "code":
                return _bad("response_type")
            # RFC 7636: exactly "S256" and a 43-character base64url challenge; "s256" is refused.
            if not is_valid_code_challenge(q.get("code_challenge", ""), q.get("code_challenge_method", "")):
                return _bad("code_challenge / code_challenge_method must be S256")
            # RFC 8707: a resource indicator, when given (even empty or repeated), must name this server.
            if any(value != resource_uri for value in q.getlist("resource")):
                return _bad("invalid_target")
            params = {k: q.get(k, "") for k in _FORM_KEYS}
            form_state = sign_form_state(params, form_secret, clock())
            page = _CONSENT_PAGE.format(
                style=_PAGE_STYLE,
                client_name=html.escape(client.client_name or _UNNAMED_CLIENT),
                redirect_uri=html.escape(redirect_uri),
                form_state=html.escape(form_state),
                google_client_id=html.escape(roles.GOOGLE_CLIENT_ID),
                nonce=html.escape(nonce_for(form_state)),
                script=_CONSENT_SCRIPT,
            )
            return HTMLResponse(page, headers=_consent_page_headers(base, redirect_uri, google_sign_in=True))

        form = await _limited_form(request)
        if "consent_state" in form:
            return await decide(form)
        form_state = str(form.get("form_state", ""))
        try:
            params = read_form_state(form_state, form_secret, clock(), PURPOSE_SIGN_IN)
        except ValueError as exc:
            return PlainTextResponse(str(exc), status_code=400)
        credential = str(form.get("credential", ""))
        try:
            # Garbage never reaches the verifier (or Google); a real credential is verified in a
            # worker thread because the default verifier may block on a cert fetch.
            if not is_well_formed_credential(credential):
                raise IdentityError("invalid_token")
            email = await anyio.to_thread.run_sync(verify_identity, credential, nonce_for(form_state),
                                                   limiter=_VERIFY_LIMITER)
        except IdentityError as exc:
            return PlainTextResponse(f"Google kimliği doğrulanamadı: {exc.reason}", status_code=401)
        if not roles.is_full(email):
            return PlainTextResponse("Bu hesap TEDY edupedia bağlantısını onaylayamaz.", status_code=403)
        client = await _registered_client(params.get("client_id", ""))
        if client is None or not _is_registered_redirect(client, params.get("redirect_uri", "")):
            return _bad("invalid_client")
        # Single use, and only once the sign-in succeeded: a transient Google failure does not burn it.
        if not await anyio.to_thread.run_sync(store.consume_form_state, nonce_for(form_state),
                                              int(clock()) + FORM_TTL_SECONDS):
            return _bad("form_state_used")
        consent_state = sign_form_state({**params, "email": email}, form_secret, clock(), PURPOSE_DECISION)
        page = _DECISION_PAGE.format(
            style=_PAGE_STYLE,
            client_name=html.escape(client.client_name or _UNNAMED_CLIENT),
            email=html.escape(email),
            redirect_uri=html.escape(params["redirect_uri"]),
            consent_state=html.escape(consent_state),
        )
        return HTMLResponse(page, headers=_consent_page_headers(base, params["redirect_uri"], google_sign_in=False))

    async def decide(form: FormData) -> Response:
        """Onayla issues the code; Reddet sends access_denied. Either way the state is spent."""
        consent_state = str(form.get("consent_state", ""))
        try:
            params = read_form_state(consent_state, form_secret, clock(), PURPOSE_DECISION)
        except ValueError as exc:
            return PlainTextResponse(str(exc), status_code=400)
        karar = str(form.get("karar", ""))
        if karar not in ("onayla", "reddet"):
            return _bad("karar")
        redirect_uri = params.get("redirect_uri", "")
        client = await _registered_client(params.get("client_id", ""))
        if client is None or not _is_registered_redirect(client, redirect_uri):
            return _bad("invalid_client")
        email = params.get("email", "")
        if karar == "onayla" and not roles.is_full(email):
            # The roster may have changed since sign-in.
            return PlainTextResponse("Bu hesap TEDY edupedia bağlantısını onaylayamaz.", status_code=403)
        if not await anyio.to_thread.run_sync(store.consume_form_state, nonce_for(consent_state),
                                              int(clock()) + FORM_TTL_SECONDS):
            return _bad("consent_state_used")
        if karar == "reddet":
            extra = {"error": "access_denied"}
        else:
            try:
                # Every code is bound to this server's resource, whether or not the client named it.
                code = await anyio.to_thread.run_sync(
                    functools.partial(store.issue_code, resource=resource_uri), email, params["client_id"],
                    redirect_uri, params["code_challenge"], params["code_challenge_method"])
            except ValueError:
                return _bad("invalid_client")  # the registration is gone (purged) since the page was shown
            extra = {"code": code}
        if params.get("state"):
            extra["state"] = params["state"]
        return RedirectResponse(_with_query(redirect_uri, extra), status_code=302,
                                headers={"cache-control": "no-store", "referrer-policy": "no-referrer"})

    def _token_response(pair: Any) -> Response:
        return JSONResponse(
            {"access_token": pair.access_token, "token_type": "Bearer", "expires_in": pair.expires_in,
             "refresh_token": pair.refresh_token, "scope": "edupedia"},
            headers={"cache-control": "no-store", "pragma": "no-cache"},
        )

    def _grant_error(error: str) -> Response:
        return JSONResponse({"error": error}, status_code=400, headers={"cache-control": "no-store"})

    async def token(request: Request) -> Response:
        form = await _limited_form(request)
        grant = form.get("grant_type")
        if grant not in ("authorization_code", "refresh_token"):
            return _grant_error("unsupported_grant_type")
        client_id = str(form.get("client_id", ""))
        if await _registered_client(client_id) is None:
            return _grant_error("invalid_client")
        resources = form.getlist("resource")
        if any(value != resource_uri for value in resources):
            return _grant_error("invalid_target")
        # Omitted: the grant's own binding applies. Given: it must match what the code or family carries.
        resource = resource_uri if resources else None
        if grant == "authorization_code":
            # Must equal the redirect_uri the code is bound to (compared in the store).
            redirect_uri = str(form.get("redirect_uri", ""))
            if not redirect_policy.allows(redirect_uri):
                return _grant_error("invalid_grant")
            pair = await anyio.to_thread.run_sync(functools.partial(store.redeem_code, resource=resource),
                                                  str(form.get("code", "")), client_id,
                                                  redirect_uri, str(form.get("code_verifier", "")))
            return _token_response(pair) if pair else _grant_error("invalid_grant")
        pair = await anyio.to_thread.run_sync(functools.partial(store.refresh, resource=resource),
                                              str(form.get("refresh_token", "")), client_id)
        return _token_response(pair) if pair else _grant_error("invalid_grant")

    streamable = mcp.streamable_http_app()

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> Any:
        # Startup housekeeping, in a worker thread like every other store call: expired codes, tokens
        # and consumed form states go; registered clients follow their own cap policy.
        await anyio.to_thread.run_sync(store.purge_expired)
        async with streamable.router.lifespan_context(app) as state:
            yield state

    routes = [
        Route("/health", health),
        Route("/.well-known/oauth-protected-resource", protected_resource),
        Route("/.well-known/oauth-protected-resource/mcp", protected_resource),
        Route("/.well-known/oauth-authorization-server", authorization_server),
        Route("/oauth/register", register, methods=["POST"]),
        Route("/oauth/authorize", authorize, methods=["GET", "POST"]),
        Route("/oauth/token", token, methods=["POST"]),
        Mount("/", app=streamable),
    ]
    # Middleware order: first entry is outermost. Pure ASGI classes keep SSE unbuffered and
    # share scope["state"] with the streamable transport's Request (identity contract).
    # CORS stays outermost so 400/401/413 all carry CORS headers. The body limit sits innermost:
    # nothing above it reads the body, and an unauthenticated /mcp call still gets its 401 challenge.
    return Starlette(
        routes=routes,
        lifespan=lifespan,
        middleware=[
            Middleware(CorsMiddleware),
            Middleware(HostGuardMiddleware, allowed_hosts=settings.allowed_hosts),
            Middleware(BearerGateMiddleware, store=store, base_url=base),
            Middleware(BodyLimitMiddleware, mcp_max_body_bytes=settings.mcp_max_body_bytes),
        ],
    )


def create_app_from_env(env: Mapping[str, str] | None = None) -> Starlette:
    """Wire settings, store, federation, tools and server from the environment."""
    import os
    from pathlib import Path

    from src.mcp_server.config import load_settings
    from src.mcp_server.dashboard_context import DashboardContext
    from src.mcp_server.federation import Federation
    from src.mcp_server.server import build_server
    from src.mcp_server.tools import Tools

    env = os.environ if env is None else env
    secret = (env.get("TED_MCP_FORM_SECRET") or "").encode("utf-8")
    if len(secret) < 32:
        raise ValueError("TED_MCP_FORM_SECRET must be set to at least 32 bytes")
    root = Path(env["TED_MCP_PROJECT_ROOT"]) if env.get("TED_MCP_PROJECT_ROOT") else None
    settings = load_settings(env, project_root=root)
    store = OAuthStore(settings.oauth_db_path)
    dashboard = DashboardContext(settings.dashboard_api_url, settings.dashboard_api_key)
    tools = Tools(settings, Federation(settings), dashboard=dashboard)
    return build_app(settings, store, build_server(tools), form_secret=secret)


def main() -> None:
    import os

    import uvicorn

    from src.env_loader import load_env

    load_env()
    app = create_app_from_env()
    uvicorn.run(app, host=os.environ.get("TED_MCP_HOST", "127.0.0.1"),
                port=int(os.environ.get("TED_MCP_PORT", "8087")), log_level="info")


if __name__ == "__main__":
    main()
