"""FastMCP registration for ted-mcp. Tool bodies live in tools.Tools."""
from __future__ import annotations

import functools
from typing import Any

import anyio
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
    async def edupedia_durum(ctx: Context, canli: bool = False) -> dict[str, Any]:
        """Sunucu sürümü, kullanıcı, kapı sayısı ve filo yapılandırması. canli=true filo sağlığını yoklar."""
        email = caller_email(ctx)
        return await anyio.to_thread.run_sync(functools.partial(tools.durum, email, canli=canli))

    @mcp.tool(annotations=_RO)
    async def edupedia_rehber(ctx: Context, bolum: str | None = None, parca: int = 1, ara: str | None = None) -> dict[str, Any]:
        """edupedia üretim rehberi. bolum: akis, modlar, segmentler, etkilesim, pedagoji, carbon, svg, ses,
        mufredat, soru, sinav, zenginlestirme, kalite. Uzun bölümler parca ile gezilir; ara serbest metin arar.
        Her üretime edupedia_rehber('akis') ile başla."""
        caller_email(ctx)
        return await anyio.to_thread.run_sync(functools.partial(tools.rehber, bolum=bolum, parca=parca, ara=ara))

    @mcp.tool(annotations=_RO)
    async def edupedia_baglam(ctx: Context, gun: int = 7) -> dict[str, Any]:
        """TEDY'den önümüzdeki gün sayısı (1-60) içindeki sınav ve ödevleri, sınıf düzeyini döner.
        Öğrenci adı ve kişisel alanlar dönmez. Konu seçerken bu listeyi kullan."""
        email = caller_email(ctx)
        return await anyio.to_thread.run_sync(functools.partial(tools.baglam, email, gun=gun))

    @mcp.tool(annotations=_RO)
    async def edupedia_kapsam(ctx: Context, ders: str, sinif: str, konu: str | None = None,
                              kazanim_kodu: str | None = None) -> dict[str, Any]:
        """Ders + sınıf + (konu veya kazanım kodu) için müfredatı doğrular; ders kitabı çerçevesini, sayfa özetlerini,
        figür adaylarını ve açık kaynak özetini döner. Sınıf ve ders koddan tahmin edilmez; otorite müfredattır.
        Modül üretiminden önce ZORUNLU; dönen run_id sonraki araçlara verilir."""
        email = caller_email(ctx)
        return await anyio.to_thread.run_sync(
            functools.partial(tools.kapsam, email, ders=ders, sinif=sinif, konu=konu, kazanim_kodu=kazanim_kodu))

    return mcp
