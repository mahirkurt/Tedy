"""A fake HTTP layer for src/portal_ekleri_indir.py — no test reaches the network.

Response shapes follow what the 2026-09-28 probe measured, with invented hosts
and ids: SharePoint `download=1` (200 application/pdf, or a login wall that
ends on login.microsoftonline.com as text/html), Drive `uc?export=download`
(octet-stream, or the virus-scan confirm page with a download form), Google
Docs `/export?format=pdf`. An unplanned URL fails the test.
"""
from __future__ import annotations

import io
import zipfile
from typing import Any, Callable

from requests.structures import CaseInsensitiveDict

MB = 1024 * 1024
PDF = b"%PDF-1.7\n" + b"1 0 obj << /Type /Catalog >> endobj\n" * 60 + b"%%EOF\n"

SP_URL = ("https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/"
          "EaBcDeFgHiJkLmNoPqRsTuV?e=AbC123")
SP_DUVAR_URL = ("https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/"
                "EzYxWvUtSrQpOnMlKjIhGfE?e=XyZ789")
DRIVE_KIMLIK = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
DRIVE_URL = f"https://drive.google.com/file/d/{DRIVE_KIMLIK}/preview"
DOCS_URL = ("https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/edit"
            "?usp=sharing&ouid=100000000000000000000")
PORTAL_URL = "https://portal.tedronesans.k12.tr/dosyalar/odev/ornek-calisma.pdf"
YOUTUBE = "https://www.youtube.com/watch?v=ornekvideo01"

GIRIS_DUVARI = ("<!DOCTYPE html><html><head><title>Hesabınızda oturum açın</title></head>"
                "<body>Microsoft</body></html>").encode("utf-8")
DRIVE_ONAY = (
    "<!DOCTYPE html><html><body><p>Google Drive bu dosyayı virüs için tarayamıyor.</p>"
    '<form id="download-form" action="https://drive.usercontent.google.com/download" method="get">'
    '<input type="submit" value="Yine de indir">'
    f'<input type="hidden" name="id" value="{DRIVE_KIMLIK}">'
    '<input type="hidden" name="export" value="download">'
    '<input type="hidden" name="confirm" value="t">'
    '<input type="hidden" name="uuid" value="0000aaaa-11bb-22cc-33dd-444444eeeeee">'
    "</form></body></html>").encode("utf-8")


class SahteYanit:
    """What ek_indir reads from a requests.Response, and nothing more."""

    def __init__(self, status_code: int = 200, govde: bytes = b"",
                 headers: dict[str, str] | None = None, url: str = "",
                 bloklar: list[Any] | None = None):
        self.status_code = status_code
        self.govde = govde
        self.headers = CaseInsensitiveDict(headers or {})
        self.url = url
        # Explicit chunks; a callable in the list is called (to raise).
        self.bloklar = bloklar
        self.kapandi = False

    def iter_content(self, chunk_size: int = 1):
        if self.bloklar is not None:
            for blok in self.bloklar:
                yield blok() if callable(blok) else blok
            return
        for i in range(0, len(self.govde), chunk_size):
            yield self.govde[i:i + chunk_size]

    def close(self) -> None:
        self.kapandi = True


class SahteOturum:
    """Routes by URL prefix, in insertion order; records every request."""

    def __init__(self, rotalar: dict[str, Any]):
        self.rotalar = rotalar
        self.istekler: list[dict[str, Any]] = []

    def get(self, url, headers=None, stream=False, timeout=None, allow_redirects=True, cookies=None):
        self.istekler.append({"url": url, "headers": dict(headers or {}), "cookies": cookies,
                              "stream": stream, "timeout": timeout})
        for onek, yanit in self.rotalar.items():
            if url.startswith(onek):
                y = yanit(url, headers or {}) if callable(yanit) else yanit
                if not y.url:
                    y.url = url
                return y
        raise AssertionError(f"beklenmeyen istek: {url}")


class SahteSaat:
    """A monotonic clock that moves `adim` seconds every time it is read."""

    def __init__(self, adim: float):
        self.adim = adim
        self.an = 0.0

    def __call__(self) -> float:
        self.an += self.adim
        return self.an


def aralikli(govde: bytes, icerik_turu: str = "application/pdf") -> Callable[[str, dict], SahteYanit]:
    """A host that honours `Range: bytes=<n>-` (206) and says 416 past the end."""
    def yanitla(url: str, headers: dict) -> SahteYanit:
        aralik = headers.get("Range")
        if aralik:
            bas = int(aralik.split("=", 1)[1].rstrip("-"))
            if bas >= len(govde):
                return SahteYanit(416, b"", {"Content-Range": f"bytes */{len(govde)}"})
            parca = govde[bas:]
            return SahteYanit(206, parca, {"Content-Type": icerik_turu, "Content-Length": str(len(parca)),
                                           "Content-Range": f"bytes {bas}-{len(govde) - 1}/{len(govde)}"})
        return SahteYanit(200, govde, {"Content-Type": icerik_turu, "Content-Length": str(len(govde))})
    return yanitla


def docx_bayt(paragraflar: list[str]) -> bytes:
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    govde = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraflar)
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}"><w:body>{govde}</w:body></w:document>')
    return tampon.getvalue()
