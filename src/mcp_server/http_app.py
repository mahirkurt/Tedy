"""Starlette app for ted-mcp: OAuth 2.1 discovery, DCR, CORS, host guard, bearer gate, MCP."""
from __future__ import annotations

import json
import time
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

from src.mcp_server import __version__
from src.mcp_server.config import Settings
from src.mcp_server.google_identity import IdentityVerifier, verify_google_credential
from src.mcp_server.oauth_redirect import is_allowed_cors_origin, is_allowed_redirect
from src.mcp_server.oauth_store import OAuthStore

CLIENT_ID = "ted-mcp-public"
REALM = "ted-mcp"
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


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


class HostGuardMiddleware:
    """DNS-rebinding guard for /mcp: only the public host(s) and loopback."""

    def __init__(self, app: ASGIApp, allowed_hosts: tuple[str, ...]) -> None:
        self.app = app
        self.allowed = set(allowed_hosts) | _LOOPBACK_HOSTS

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/mcp"):
            host = _header(scope, b"host").rsplit(":", 1)[0].strip("[]").lower()
            if host not in self.allowed:
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
            email = self.store.principal(token) if token else None
            if email is None:
                await _send_json(send, 401, {"error": "unauthorized"},
                                 [(b"www-authenticate", self.challenge.encode("latin-1"))])
                return
            scope.setdefault("state", {})["ted_email"] = email
        await self.app(scope, receive, send)


def build_app(
    settings: Settings,
    store: OAuthStore,
    mcp: FastMCP,
    verify_identity: IdentityVerifier = verify_google_credential,
    form_secret: bytes = b"",
    clock: Callable[[], float] = time.time,
) -> Starlette:
    # verify_identity, form_secret and clock are used by the consent/token routes (Task 6).
    base = settings.public_base_url

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

    streamable = mcp.streamable_http_app()
    routes = [
        Route("/health", health),
        Route("/.well-known/oauth-protected-resource", protected_resource),
        Route("/.well-known/oauth-protected-resource/mcp", protected_resource),
        Route("/.well-known/oauth-authorization-server", authorization_server),
        Route("/oauth/register", register, methods=["POST"]),
        Mount("/", app=streamable),
    ]
    # Middleware order: first entry is outermost. Pure ASGI classes keep SSE unbuffered and
    # share scope["state"] with the streamable transport's Request (identity contract).
    return Starlette(
        routes=routes,
        lifespan=streamable.router.lifespan_context,
        middleware=[
            Middleware(CorsMiddleware),
            Middleware(HostGuardMiddleware, allowed_hosts=settings.allowed_hosts),
            Middleware(BearerGateMiddleware, store=store, base_url=base),
        ],
    )
