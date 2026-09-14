"""FastMCP registration for ted-mcp. Tool bodies live in tools.Tools."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations

from src import roles
from src.mcp_server import __version__
from src.mcp_server.tools import Tools

_RO = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

INSTRUCTIONS = (
    "TEDY edupedia orkestratörü. Türkiye Yüzyılı Maarif Modeli'ne hizalı etkileşimli öğrenim modülleri "
    "için müfredat doğrulama, ders kitabı çerçevesi ve açık eğitsel kaynakları sunar. Her zaman "
    "edupedia_rehber('akis') ile başla ve araç sırasını izle. Boş sonuç yokluk kanıtı değildir; "
    "coverage manifestosunu kullanıcıya bildir. Tüm çıktılar mcp_verified=false."
)


def caller_email(ctx: Context) -> str:
    """Roster email set by the bearer gate; tools refuse to run without it."""
    request = getattr(ctx.request_context, "request", None)
    state = getattr(request, "state", None)
    email = getattr(state, "ted_email", None) if state is not None else None
    if not email or not roles.is_full(email):
        raise ToolError("yetkisiz: bu araç yalnız TEDY aile listesindeki tam yetkili hesaplarla çalışır")
    return email


def build_server(tools: Tools) -> FastMCP:
    mcp = FastMCP(
        "TEDY edupedia",
        instructions=INSTRUCTIONS,
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    # FastMCP drops `version`; without this serverInfo.version reports the SDK version.
    mcp._mcp_server.version = __version__

    @mcp.tool(annotations=_RO)
    def edupedia_durum(ctx: Context, canli: bool = False) -> dict[str, Any]:
        """Sunucu sürümü, kullanıcı, kapı sayısı ve filo yapılandırması. canli=true filo sağlığını yoklar."""
        return tools.durum(caller_email(ctx), canli=canli)

    return mcp
