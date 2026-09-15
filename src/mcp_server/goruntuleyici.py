"""modul.tedy.online: ticketed, strictly CSP'd static module serving (spec §5.4; plan K-P2, K-P19).

Order of checks: path shape -> ticket -> catalog record and file. A bad ticket always gets the same
403 sentence, so existence is never revealed without a valid ticket. Every response, including
404/405, carries the spec security headers.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Iterable

import anyio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from src import module_store as ms
from src import module_ticket as mt
from src import roles

CSP = ("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; "
       "font-src data:; media-src data:; connect-src 'none'; frame-ancestors https://tedy.online; "
       "base-uri 'none'; form-action 'none'")
SECURITY_HEADERS = {
    "content-security-policy": CSP,
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cache-control": "private, no-store",
    "x-robots-tag": "noindex",
}
NOT_FOUND_TEXT = "Modül bulunamadı"


def full_role_hashes() -> set[str]:
    return {mt.email_hash(email) for email in roles.FULL_ACCESS_EMAILS}


class _SecurityHeaders:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                kept = [(k, v) for k, v in message.get("headers") or []
                        if k.decode("latin-1").lower() not in SECURITY_HEADERS]
                kept += [(k.encode("latin-1"), v.encode("latin-1")) for k, v in SECURITY_HEADERS.items()]
                message = {**message, "headers": kept}
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _plain(text: str, status: int) -> Response:
    return PlainTextResponse(text, status_code=status)


def build_viewer(data_dir: Path | str, secret: bytes, clock: Callable[[], float] = time.time,
                 allowed_u: Callable[[], Iterable[str]] = full_role_hashes) -> ASGIApp:
    if not isinstance(secret, (bytes, bytearray)) or len(secret) < mt.MIN_SECRET_BYTES:
        raise mt.TicketConfigError("EDUPEDIA_TICKET_SECRET must be at least 32 bytes")
    data_dir = Path(data_dir)

    async def _serve(path: Path | None) -> Response:
        if path is None or not path.is_file():
            return _plain(NOT_FOUND_TEXT, 404)
        body = await anyio.to_thread.run_sync(path.read_bytes)
        return Response(body, media_type="text/html; charset=utf-8")

    async def modul(request: Request) -> Response:
        slug = request.path_params["slug"]
        version = ms.parse_version_segment(request.path_params["surum"])
        if not ms.valid_slug(slug) or version is None:
            return _plain(NOT_FOUND_TEXT, 404)
        q = request.query_params
        if mt.verify(secret, "m", slug, version, q.get("t"), q.get("e"), q.get("u"), clock(), allowed_u()) is not None:
            return _plain(mt.EXPIRED_TEXT, 403)
        record = ms.find_record(data_dir, slug, version)
        if not record or record.get("status") != "active":
            return _plain(NOT_FOUND_TEXT, 404)
        return await _serve(ms.module_html_path(data_dir, slug, version))

    async def taslak(request: Request) -> Response:
        taslak_id = request.path_params["taslak_id"]
        if not ms.valid_taslak_id(taslak_id):
            return _plain(NOT_FOUND_TEXT, 404)
        q = request.query_params
        if mt.verify(secret, "t", taslak_id, None, q.get("t"), q.get("e"), q.get("u"), clock(), allowed_u()) is not None:
            return _plain(mt.EXPIRED_TEXT, 403)
        if ms.read_draft(data_dir, taslak_id) is None:
            return _plain(NOT_FOUND_TEXT, 404)
        return await _serve(ms.draft_html_path(data_dir, taslak_id))

    async def other(request: Request) -> Response:
        return _plain(NOT_FOUND_TEXT, 404)

    app = Starlette(routes=[
        Route("/m/{slug}/{surum}", modul, methods=["GET"]),
        Route("/taslak/{taslak_id}", taslak, methods=["GET"]),
        Route("/{rest:path}", other, methods=["GET"]),
    ])
    return _SecurityHeaders(app)


class ViewerHostRouter:
    """Outermost middleware: requests for a viewer host never reach CORS, the bearer gate or /mcp."""

    def __init__(self, app: ASGIApp, viewer: ASGIApp | None, hosts: Iterable[str]) -> None:
        self.app = app
        self.viewer = viewer
        self.hosts = {h.lower() for h in hosts}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and self.viewer is not None:
            host = ""
            for key, value in scope.get("headers") or []:
                if key == b"host":
                    host = value.decode("latin-1").rsplit(":", 1)[0].strip().lower()
                    break
            if host in self.hosts:
                await self.viewer(scope, receive, send)
                return
        await self.app(scope, receive, send)
