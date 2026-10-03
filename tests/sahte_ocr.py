"""Fakes for the OCR layer (plan 2026-09-28-portal-ekleri, Görev 14–15).

No test calls the paid API or spends ~20 s in real Tesseract (measured
2026-09-28 per A4 page at 150 dpi). A scanned PDF is made with Pillow: image
pages, no text layer — exactly what pdftotext returns nothing for.
"""
from __future__ import annotations

from pathlib import Path

from src.ocr_katmani import GorselOkuma

MARKDOWN = "# Soru 1\n\nKesirleri topla: $x^2 + y^2$\n\n| a | b |\n|---|---|\n| 1 | 2 |"


class Saat:
    """A monotonic clock that moves only when a test moves it."""

    def __init__(self, an: float = 0.0):
        self.an = an

    def __call__(self) -> float:
        return self.an


class SahteOkuyucu:
    """Stands in for ClaudeGorselOkuyucu: records calls, returns a fixed page."""

    motor = "claude:claude-haiku-4-5"

    def __init__(self, markdown: str = MARKDOWN, okunabilirlik: str = "yuksek", girdi: int = 2400,
                 cikti: int = 300, hata: Exception | None = None, reddet: bool = False,
                 saat: Saat | None = None, adim: float = 0.0):
        self.markdown, self.okunabilirlik = markdown, okunabilirlik
        self.girdi, self.cikti = girdi, cikti
        self.hata, self.reddet = hata, reddet
        self.saat, self.adim = saat, adim
        self.cagrilar: list[int] = []

    def oku(self, jpeg: bytes, sure: float) -> GorselOkuma:
        self.cagrilar.append(len(jpeg))
        if self.saat is not None:
            self.saat.an += self.adim
        if self.hata is not None:
            raise self.hata
        return GorselOkuma(markdown="" if self.reddet else self.markdown,
                           okunabilirlik=self.okunabilirlik, girdi_token=self.girdi,
                           cikti_token=self.cikti, kesildi=False, reddedildi=self.reddet)


class SahteTesseract:
    def __init__(self, metin: str = "Soru 1 kesirleri topla", guven: float = 0.45):
        self.metin, self.guven = metin, guven
        self.cagrilar = 0

    def __call__(self, jpeg: bytes, sure: float) -> tuple[str, float]:
        self.cagrilar += 1
        return self.metin, self.guven


def taranmis_pdf(yol: Path, icerikli: int = 1, bos: int = 0) -> Path:
    """`icerikli` drawn pages, then `bos` white ones; no text layer at all."""
    from PIL import Image, ImageDraw
    sayfalar = []
    for i in range(icerikli):
        img = Image.new("RGB", (620, 877), "white")
        cizim = ImageDraw.Draw(img)
        cizim.rectangle([40, 40, 580, 120], outline="black", width=3)
        cizim.text((60, 70), f"Soru {i + 1}: Kesirleri topla.", fill="black")
        for y in range(160, 800, 40):
            cizim.line([60, y, 560, y], fill="black", width=2)
        sayfalar.append(img)
    sayfalar += [Image.new("RGB", (620, 877), "white") for _ in range(bos)]
    sayfalar[0].save(yol, "PDF", save_all=True, append_images=sayfalar[1:], resolution=72)
    return Path(yol)
