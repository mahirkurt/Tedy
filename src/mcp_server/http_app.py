"""Starlette app for ted-mcp: OAuth 2.1 discovery, DCR, CORS, host guard, bearer gate, MCP."""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import time
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
from src.mcp_server.oauth_redirect import is_allowed_cors_origin, is_allowed_redirect
from src.mcp_server.oauth_store import OAuthStore
from src import roles
from src.mcp_server.google_identity import IdentityError
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse

CLIENT_ID = "ted-mcp-public"
REALM = "ted-mcp"
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}

FORM_TTL_SECONDS = 600
OAUTH_MAX_BODY_BYTES = 16_384
_FORM_KEYS = ("client_id", "redirect_uri", "state", "code_challenge", "code_challenge_method", "scope", "resource")


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_form_state(params: dict[str, str], secret: bytes, now: float) -> str:
    payload = _b64u(json.dumps({"p": params, "exp": int(now) + FORM_TTL_SECONDS}, sort_keys=True).encode())
    sig = hmac.new(secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def read_form_state(token: str, secret: bytes, now: float) -> dict[str, str]:
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
    if int(data.get("exp", 0)) < int(now):
        raise ValueError("form_state_expired")
    return {k: str(v) for k, v in (data.get("p") or {}).items()}


def nonce_for(form_state: str) -> str:
    return hashlib.sha256(form_state.encode("ascii")).hexdigest()


def _with_query(uri: str, extra: dict[str, str]) -> str:
    parts = urlparse(uri)
    query = parse_qsl(parts.query, keep_blank_values=True) + list(extra.items())
    return urlunparse(parts._replace(query=urlencode(query)))


_CONSENT_PAGE = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>TEDY edupedia bağlantısı</title>
<style>
body{{font-family:"IBM Plex Sans",system-ui,sans-serif;background:#f4f4f4;color:#161616;margin:0;padding:48px 16px}}
main{{max-width:480px;margin:auto;background:#fff;padding:32px;border-top:4px solid #0f62fe}}
h1{{font-size:1.5rem;font-weight:400;margin:0 0 16px}} p{{line-height:1.5}} code{{background:#e0e0e0;padding:2px 4px}}
</style>
<script src="https://accounts.google.com/gsi/client" async></script></head>
<body><main>
<h1>edupedia'yı TEDY hesabına bağla</h1>
<p><code>{origin}</code> uygulaması, Google hesabınızla TEDY edupedia araçlarını kullanmak için izin istiyor.
Yalnız TEDY aile listesindeki tam yetkili hesaplar onay verebilir.</p>
<form id="consent" method="post" action="/oauth/authorize">
<input type="hidden" name="form_state" value="{form_state}">
<input type="hidden" name="credential" id="credential" value="">
</form>
<div id="g_id_onload" data-client_id="{client_id}" data-nonce="{nonce}" data-callback="tedyConsent"
     data-auto_prompt="false"></div>
<div class="g_id_signin" data-type="standard" data-text="continue_with" data-locale="tr"></div>
<script>function tedyConsent(r){{document.getElementById("credential").value=r.credential;document.getElementById("consent").submit();}}</script>
</main></body></html>"""


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

    async def health(request: Request) -> Response:
        return JSONResponse({"status": "ok", "version": __version__})

    async def protected_resource(request: Request) -> Response:
        return JSONResponse({
            "resource": f"{base}/mcp",
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

    async def register(request: Request) -> Response:
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse({"error": "invalid_client_metadata"}, status_code=400)
        uris = body.get("redirect_uris") if isinstance(body, dict) else None
        if not isinstance(uris, list) or not uris or not all(isinstance(u, str) and is_allowed_redirect(u) for u in uris):
            return JSONResponse({"error": "invalid_redirect_uri"}, status_code=400)
        return JSONResponse({
            "client_id": CLIENT_ID,
            "redirect_uris": uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
        }, status_code=201)

    def _bad(reason: str) -> Response:
        return PlainTextResponse(f"Geçersiz yetkilendirme isteği: {reason}", status_code=400)

    async def authorize(request: Request) -> Response:
        if request.method == "GET":
            q = request.query_params
            if q.get("response_type") != "code":
                return _bad("response_type")
            if q.get("client_id") != CLIENT_ID:
                return _bad("client_id")
            redirect_uri = q.get("redirect_uri", "")
            if not is_allowed_redirect(redirect_uri):
                return _bad("redirect_uri")
            if not q.get("code_challenge"):
                return _bad("code_challenge")
            if (q.get("code_challenge_method") or "").upper() != "S256":
                return _bad("code_challenge_method must be S256")
            params = {k: q.get(k, "") for k in _FORM_KEYS}
            form_state = sign_form_state(params, form_secret, clock())
            parsed = urlparse(redirect_uri)
            page = _CONSENT_PAGE.format(
                origin=html.escape(f"{parsed.scheme}://{parsed.netloc}"),
                form_state=html.escape(form_state),
                client_id=html.escape(roles.GOOGLE_CLIENT_ID),
                nonce=html.escape(nonce_for(form_state)),
            )
            return HTMLResponse(page, headers={"cache-control": "no-store", "x-frame-options": "DENY"})

        form = await _limited_form(request)
        form_state = str(form.get("form_state", ""))
        try:
            params = read_form_state(form_state, form_secret, clock())
        except ValueError as exc:
            return PlainTextResponse(str(exc), status_code=400)
        credential = str(form.get("credential", ""))
        try:
            # Garbage never reaches the verifier (or Google); a real credential is verified in a
            # worker thread because the default verifier may block on a cert fetch.
            if not is_well_formed_credential(credential):
                raise IdentityError("invalid_token")
            email = await anyio.to_thread.run_sync(verify_identity, credential, nonce_for(form_state))
        except IdentityError as exc:
            return PlainTextResponse(f"Google kimliği doğrulanamadı: {exc.reason}", status_code=401)
        if not roles.is_full(email):
            return PlainTextResponse("Bu hesap TEDY edupedia bağlantısını onaylayamaz.", status_code=403)
        code = await anyio.to_thread.run_sync(store.issue_code, email, params["client_id"], params["redirect_uri"],
                                              params["code_challenge"], params["code_challenge_method"])
        extra = {"code": code}
        if params.get("state"):
            extra["state"] = params["state"]
        return RedirectResponse(_with_query(params["redirect_uri"], extra), status_code=302)

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
        client_id = str(form.get("client_id", ""))
        if grant == "authorization_code":
            redirect_uri = str(form.get("redirect_uri", ""))
            if client_id != CLIENT_ID or not is_allowed_redirect(redirect_uri):
                return _grant_error("invalid_grant")
            pair = await anyio.to_thread.run_sync(store.redeem_code, str(form.get("code", "")), client_id,
                                                  redirect_uri, str(form.get("code_verifier", "")))
            return _token_response(pair) if pair else _grant_error("invalid_grant")
        if grant == "refresh_token":
            if client_id != CLIENT_ID:
                return _grant_error("invalid_grant")
            pair = await anyio.to_thread.run_sync(store.refresh, str(form.get("refresh_token", "")), client_id)
            return _token_response(pair) if pair else _grant_error("invalid_grant")
        return _grant_error("unsupported_grant_type")

    streamable = mcp.streamable_http_app()
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
        lifespan=streamable.router.lifespan_context,
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
