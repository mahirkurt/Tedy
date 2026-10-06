"""OCR for PDF pages without a text layer (plan 2026-09-28-portal-ekleri, Görev 14).

pdftotext returns nothing for a scanned page: measured 2026-09-28, three
chunks of the live index were "pdf_no_text" (content/yabanci-dil), and a
scanned homework attachment would read "metin katmanı yok". Each such page is
rendered with pdftoppm and read by Claude Haiku 4.5's vision into Markdown
(headings, tables and formulas kept). A page is read once — cached by (file
sha256, page, engine, prompt version). A refusal or an API error is remembered
on that same key, so a later read in that calendar month reuses Tesseract.
A new month asks Claude again only when the page never reached it because
the cap was already full — that path writes no attempt. Spend is held
under a monthly cap in a ledger fed by each response's `usage`; at the cap,
on an API error or a refusal, the page falls back to local Tesseract
(tur+eng). An API error is not written to the ledger. Every page carries
its engine and a confidence estimate, and a low one is labelled for the model.
"""
from __future__ import annotations

import base64
import fcntl
import hashlib
import io
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator

from src.json_utils import atomic_json_dump

logger = logging.getLogger(__name__)

OCR_VARSAYILAN_MODEL = "claude-haiku-4-5"
# Anthropic first-party list price of Claude Haiku 4.5, USD per million tokens
# (claude-api reference, cached 2026-06-24). An OCR_CLAUDE_MODEL override must
# bring its own prices here, or the ledger under-counts.
GIRDI_USD_MTOK = 1.00
CIKTI_USD_MTOK = 5.00
# Part of every cache key: a new prompt re-reads pages; a new engine too.
ISTEM_SURUMU = "1"
# 2026-10-06: the French pack (tesseract-ocr-fra) is installed and in the default. Measured on three
# French textbook pages against Haiku's reading: words found tur+eng 0.76 -> tur+eng+fra 0.84,
# accented words 0.62 -> 0.87; a Turkish textbook page's CER 0.100 -> 0.099 (no loss). The language
# is part of the cache's engine name, so pages read under an older setting are read again.
TESSERACT_DILI = "tur+eng+fra"
ESKI_TESSERACT_MOTORLARI = ("tesseract-tur+eng",)


def tesseract_dili() -> str:
    return os.environ.get("ASSISTANT_OCR_LANG", "").strip() or TESSERACT_DILI


def motor_tesseract() -> str:
    return f"tesseract-{tesseract_dili()}"


MOTOR_TESSERACT = motor_tesseract()  # import-time value, kept for callers that read the name
MOTOR_BOS = "bos"
AYLIK_TAVAN_USD = float(os.environ.get("TEDY_OCR_AYLIK_USD", "10"))
# Claude downsizes an image whose long edge passes ~1568 px, so rendering
# bigger buys nothing but render time: measured 2026-09-28 on page 5 of a
# 70 MB PDF, 150 dpi rendered 1214x1650 in 3.2 s and 200 dpi 1619x2200 in
# 5.3 s. 1568 px is ~190 dpi on A4 and costs about w*h/750 ≈ 2,400 input tokens.
UZUN_KENAR = 1568
CIKTI_SINIRI = 4096
# One page's worst case: the image (≤ 1568²/750 ≈ 3,300 tokens) plus the
# prompt, rounded to 4,000 input tokens, and CIKTI_SINIRI output tokens.
# Claude is called only while this still fits under the cap.
SAYFA_TAHMINI_USD = (4000 * GIRDI_USD_MTOK + CIKTI_SINIRI * CIKTI_USD_MTOK) / 1_000_000
DUSUK_GUVEN = 0.6
# No new Claude call with less than this left (its timeout is the time left,
# no retries, so a call can overrun its deadline by at most one call); no
# Tesseract run with less than this left (~20 s a page measured at 150 dpi).
CLAUDE_EN_AZ_SURE = 15.0
TESSERACT_EN_AZ_SURE = 10.0
ONBELLEK = PurePosixPath("output/ocr_onbellek")
DEFTER = PurePosixPath("output/ocr_defteri.json")
_METIN_ESIGI = 20          # fewer non-space characters than this: no text layer
_BOS_SAPMA = 2.0           # grey-level stddev under this: a white page
_GUVEN = {"yuksek": 0.9, "orta": 0.7, "dusuk": 0.4}
_OKUNABILIRLIK = re.compile(r"\s*<!--\s*okunabilirlik:\s*(yuksek|orta|dusuk)\s*-->\s*$")

ISTEM = (
    "Bu görsel, bir okul belgesinin taranmış tek bir sayfası. Sayfadaki bütün metni, "
    "göründüğü sırayla ve olduğu gibi Markdown olarak yaz:\n"
    "- Başlıkları # ve ## ile, listeleri madde olarak, tabloları Markdown tablosu olarak koru.\n"
    "- Matematik ve fen ifadelerini LaTeX ile yaz ($...$ ya da $$...$$).\n"
    "- Metni özetleme, çevirme, düzeltme ya da tamamlama. Okuyamadığın yeri [okunamadı] diye işaretle.\n"
    "- Şekil ve fotoğrafları yalnız kısa bir notla an: [şekil: kısa açıklama].\n"
    "- Markdown'dan başka bir şey yazma. En son satıra, sayfanın ne kadar net okunduğunu şu "
    "biçimde ekle: <!-- okunabilirlik: yuksek --> (yuksek, orta ya da dusuk)."
)


class OcrHatasi(RuntimeError):
    """A page or file could not be rendered or measured; nothing is cached."""


def _sha256(yol: Path) -> str:
    h = hashlib.sha256()
    with yol.open("rb") as f:
        for blok in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blok)
    return h.hexdigest()


def _kos(komut: list[str], sure: float) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(komut, capture_output=True, timeout=max(1.0, sure), check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise OcrHatasi(f"{komut[0]}: {type(exc).__name__}") from exc


def pdf_sayfa_sayisi(pdf: Path, sure: float) -> int:
    proc = _kos(["pdfinfo", str(pdf)], sure)
    m = re.search(r"^Pages:\s+(\d+)", proc.stdout.decode("utf-8", "replace"), re.M)
    if proc.returncode != 0 or not m:
        raise OcrHatasi("pdfinfo sayfa sayısını okuyamadı")
    return int(m.group(1))


def pdf_sayfa_metinleri(pdf: Path, sure: float) -> list[str]:
    """One string per page, as pdftotext renders it (pages end in a form feed)."""
    n = pdf_sayfa_sayisi(pdf, sure)
    proc = _kos(["pdftotext", "-layout", str(pdf), "-"], sure)
    if proc.returncode != 0:
        raise OcrHatasi("pdftotext okuyamadı")
    sayfalar = proc.stdout.decode("utf-8", "replace").split(chr(12))
    return (sayfalar + [""] * n)[:n]


def metin_katmani_var(metin: str) -> bool:
    return len("".join(str(metin or "").split())) >= _METIN_ESIGI


def sayfa_gorseli(pdf: Path, sayfa: int, sure: float) -> bytes:
    """Page `sayfa` (1-based) as a JPEG whose long edge is UZUN_KENAR."""
    with tempfile.TemporaryDirectory() as dizin:
        kok = os.path.join(dizin, "sayfa")
        proc = _kos(["pdftoppm", "-f", str(sayfa), "-l", str(sayfa), "-scale-to", str(UZUN_KENAR),
                     "-jpeg", "-jpegopt", "quality=85", "-singlefile", str(pdf), kok], sure)
        yol = Path(kok + ".jpg")
        if proc.returncode != 0 or not yol.is_file():
            raise OcrHatasi("pdftoppm sayfayı çizemedi")
        return yol.read_bytes()


def bos_sayfa_mi(jpeg: bytes) -> bool:
    from PIL import Image, ImageStat
    with Image.open(io.BytesIO(jpeg)) as img:
        return ImageStat.Stat(img.convert("L")).stddev[0] < _BOS_SAPMA


@dataclass
class GorselOkuma:
    markdown: str
    okunabilirlik: str
    girdi_token: int
    cikti_token: int
    kesildi: bool = False
    reddedildi: bool = False


class ClaudeGorselOkuyucu:
    """One page image → Markdown, through src/claude_api.py with TEDY's key.

    No thinking and no temperature (Haiku 4.5 needs neither for transcription).
    Markdown rather than structured JSON output: a reply cut at CIKTI_SINIRI
    keeps the part it read, where a cut JSON would lose the page. The model
    rates its own reading on the last line; a cut reply is rated low."""

    def __init__(self, model: str | None = None):
        self.model = model or os.environ.get("OCR_CLAUDE_MODEL", "").strip() or OCR_VARSAYILAN_MODEL

    @property
    def motor(self) -> str:
        return f"claude:{self.model}"

    def oku(self, jpeg: bytes, sure: float) -> GorselOkuma:
        from src import claude_api
        istemci = claude_api.istemci(timeout=max(10.0, sure), max_retries=0)
        yanit = istemci.messages.create(
            model=self.model,
            max_tokens=CIKTI_SINIRI,
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(jpeg).decode("ascii")}},
                {"type": "text", "text": ISTEM},
            ]}],
        )
        kullanim = getattr(yanit, "usage", None)
        durdu = str(getattr(yanit, "stop_reason", "") or "")
        metin = claude_api.metin(yanit)
        m = _OKUNABILIRLIK.search(metin)
        okunabilirlik = "dusuk" if durdu == "max_tokens" else (m.group(1) if m else "orta")
        return GorselOkuma(markdown=_OKUNABILIRLIK.sub("", metin).strip(), okunabilirlik=okunabilirlik,
                           girdi_token=int(getattr(kullanim, "input_tokens", 0) or 0),
                           cikti_token=int(getattr(kullanim, "output_tokens", 0) or 0),
                           kesildi=durdu == "max_tokens", reddedildi=durdu == "refusal")


def tesseract_verisinden(veri: dict[str, Any]) -> tuple[str, float]:
    """pytesseract's image_to_data dict → (text, mean word confidence 0..1).
    Lines keep their words; a new block or paragraph starts after a blank line."""
    satirlar: dict[tuple[Any, Any, Any], list[str]] = {}
    guvenler: list[float] = []
    for i, kelime in enumerate(veri.get("text") or []):
        kelime = str(kelime or "").strip()
        if not kelime:
            continue
        try:
            guven = float(veri["conf"][i])
        except (KeyError, IndexError, TypeError, ValueError):
            guven = -1.0
        if guven >= 0:
            guvenler.append(guven)
        anahtar = (veri["block_num"][i], veri["par_num"][i], veri["line_num"][i])
        satirlar.setdefault(anahtar, []).append(kelime)
    parcalar: list[str] = []
    onceki = None
    for (blok, par, _satir), kelimeler in satirlar.items():
        if onceki is not None and (blok, par) != onceki:
            parcalar.append("")
        parcalar.append(" ".join(kelimeler))
        onceki = (blok, par)
    return "\n".join(parcalar).strip(), (sum(guvenler) / len(guvenler) / 100.0 if guvenler else 0.0)


def tesseract_oku(jpeg: bytes, sure: float) -> tuple[str, float]:
    """The existing local path (FileAdapters' images use it too), tur+eng."""
    import pytesseract
    from PIL import Image
    with Image.open(io.BytesIO(jpeg)) as img:
        veri = pytesseract.image_to_data(img, lang=tesseract_dili(),
                                         output_type=pytesseract.Output.DICT, timeout=max(5, int(sure)))
    return tesseract_verisinden(veri)


@dataclass
class SayfaOkumasi:
    sayfa: int
    metin: str
    motor: str
    guven: float
    usd: float = 0.0

    @property
    def dusuk_guven(self) -> bool:
        return self.guven < DUSUK_GUVEN

    def etiket(self) -> str:
        """The line the model reads above an OCR'd page."""
        if self.motor.startswith("claude:"):
            from src.claude_api import okunur_ad
            ad = okunur_ad(self.motor.split(":", 1)[1])
        else:
            ad = "Tesseract"
        if self.dusuk_guven:
            return f"[PDF s.{self.sayfa} · OCR, güven düşük · {ad}]"
        return f"[PDF s.{self.sayfa} · OCR · {ad} · güven %{round(self.guven * 100)}]"


class OcrOnbellegi:
    """output/ocr_onbellek/<sha[:2]>/<sha[:16]>-s<page>-<key>.json, key over
    (file sha256, page, engine, ISTEM_SURUMU)."""

    def __init__(self, dizin: str | Path):
        self.dizin = Path(dizin)

    def _yol(self, sha: str, sayfa: int, motor: str) -> Path:
        anahtar = hashlib.sha256(f"{sha}|{sayfa}|{motor}|{ISTEM_SURUMU}".encode("utf-8")).hexdigest()[:24]
        return self.dizin / sha[:2] / f"{sha[:16]}-s{sayfa}-{anahtar}.json"

    def al(self, sha: str, sayfa: int, motor: str) -> SayfaOkumasi | None:
        try:
            veri = json.loads(self._yol(sha, sayfa, motor).read_text(encoding="utf-8"))
            return SayfaOkumasi(int(veri["sayfa"]), str(veri["metin"]), str(veri["motor"]),
                                float(veri["guven"]), float(veri.get("usd", 0.0)))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def koy(self, sha: str, okuma: SayfaOkumasi) -> None:
        atomic_json_dump({"sayfa": okuma.sayfa, "metin": okuma.metin, "motor": okuma.motor,
                          "guven": okuma.guven, "usd": okuma.usd, "istem_surumu": ISTEM_SURUMU,
                          "okundu": datetime.now().isoformat(timespec="seconds")},
                         str(self._yol(sha, okuma.sayfa, okuma.motor)))

    def _deneme_yol(self, sha: str, sayfa: int, motor: str) -> Path:
        """Claude was asked for (file, page, engine, prompt version).

        The calendar month of the attempt is stored in the file, from the
        ledger clock. The marker is not dropped when the month changes: a
        new month asks Claude only for a page that has no marker, which is
        a page the cap kept from reaching Claude.
        """
        anahtar = hashlib.sha256(
            f"{sha}|{sayfa}|{motor}|{ISTEM_SURUMU}|deneme".encode("utf-8")
        ).hexdigest()[:24]
        return self.dizin / sha[:2] / f"{sha[:16]}-s{sayfa}-deneme-{anahtar}.json"

    def denendi(self, sha: str, sayfa: int, motor: str) -> bool:
        return self._deneme_yol(sha, sayfa, motor).is_file()

    def deneme_kaydet(self, sha: str, sayfa: int, motor: str, ay: str) -> None:
        atomic_json_dump(
            {"sayfa": sayfa, "motor": motor, "ay": ay, "istem_surumu": ISTEM_SURUMU},
            str(self._deneme_yol(sha, sayfa, motor)),
        )


class OcrDefteri:
    """output/ocr_defteri.json: measured spend per month (Istanbul wall clock).

    A Claude call is made only while the month's spend plus one page's worst
    case (SAYFA_TAHMINI_USD) fits under the cap, and the real cost is written
    from response.usage afterwards. Two processes checking at once (the cron
    reindex and a dashboard reindex) can pass the cap by at most one page each
    (≤ 0.025 USD); a reservation scheme would instead let a crashed process
    eat the cap for the rest of the month."""

    def __init__(self, yol: str | Path, tavan: float = AYLIK_TAVAN_USD,
                 simdi: Callable[[], datetime] = datetime.now):
        self.yol = Path(yol)
        self.tavan = float(tavan)
        self.simdi = simdi

    @contextmanager
    def _kilitli(self) -> Iterator[None]:
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        with open(self.yol.with_name(self.yol.name + ".lock"), "a") as kilit:
            fcntl.flock(kilit, fcntl.LOCK_EX)
            yield

    def _oku(self) -> dict[str, Any]:
        try:
            veri = json.loads(self.yol.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return veri if isinstance(veri, dict) else {}

    def _ay(self) -> str:
        return self.simdi().strftime("%Y-%m")

    def harcanan(self) -> float:
        ay = (self._oku().get("aylar") or {}).get(self._ay()) or {}
        return float(ay.get("usd", 0.0))

    def izin_var(self) -> bool:
        return self.harcanan() + SAYFA_TAHMINI_USD <= self.tavan

    def yaz(self, motor: str, girdi_token: int, cikti_token: int) -> float:
        usd = (girdi_token * GIRDI_USD_MTOK + cikti_token * CIKTI_USD_MTOK) / 1_000_000
        with self._kilitli():
            veri = self._oku()
            ay = veri.setdefault("aylar", {}).setdefault(
                self._ay(), {"usd": 0.0, "sayfa": 0, "girdi_token": 0, "cikti_token": 0})
            ay["usd"] = round(float(ay.get("usd", 0.0)) + usd, 6)
            ay["sayfa"] = int(ay.get("sayfa", 0)) + 1
            ay["girdi_token"] = int(ay.get("girdi_token", 0)) + int(girdi_token)
            ay["cikti_token"] = int(ay.get("cikti_token", 0)) + int(cikti_token)
            veri["tavan_usd"] = self.tavan
            veri["son_motor"] = motor
            atomic_json_dump(veri, str(self.yol))
        return usd


@dataclass
class PdfOcrSonucu:
    metin: str
    toplam_sayfa: int
    metinsiz: int
    ocr_sayfalari: list[int] = field(default_factory=list)
    eksik: list[int] = field(default_factory=list)
    dusuk_guvenli: list[int] = field(default_factory=list)

    @property
    def ilerleme(self) -> str:
        return f"{self.metinsiz - len(self.eksik)}/{self.metinsiz}"


class OcrKatmani:
    """The shared layer: the attachment sync and the BM25 indexer both call
    pdf_oku with a deadline on `saat`; whatever is not read by then stays
    `eksik` and is read on a later run, the pages done coming from the cache."""

    def __init__(self, proje_koku: str | Path, okuyucu: Any = None,
                 tesseract: Callable[[bytes, float], tuple[str, float]] = tesseract_oku,
                 saat: Callable[[], float] = time.monotonic,
                 simdi: Callable[[], datetime] = datetime.now,
                 tavan: float | None = None):
        kok = Path(proje_koku)
        self.onbellek = OcrOnbellegi(kok / ONBELLEK)
        self.defter = OcrDefteri(kok / DEFTER, tavan=AYLIK_TAVAN_USD if tavan is None else tavan, simdi=simdi)
        self.okuyucu = okuyucu if okuyucu is not None else ClaudeGorselOkuyucu()
        self.tesseract = tesseract
        self.saat = saat

    def _kalan(self, son_an: float) -> float:
        return son_an - self.saat()

    def pdf_oku(self, pdf: str | Path, son_an: float,
                sayfa_metinleri: list[str] | None = None) -> PdfOcrSonucu:
        pdf = Path(pdf)
        if sayfa_metinleri is None:
            sayfa_metinleri = pdf_sayfa_metinleri(pdf, max(5.0, self._kalan(son_an)))
        sha = _sha256(pdf)
        parcalar: list[str] = []
        ocr_sayfalari: list[int] = []
        eksik: list[int] = []
        dusuk: list[int] = []
        metinsiz = 0
        for i, metin in enumerate(sayfa_metinleri, 1):
            if metin_katmani_var(metin):
                parcalar.append(metin)
                continue
            metinsiz += 1
            okuma = self._sayfa(pdf, sha, i, son_an)
            if okuma is None:
                eksik.append(i)
                parcalar.append("")
                continue
            if okuma.motor == MOTOR_BOS or not okuma.metin.strip():
                parcalar.append("")
                continue
            ocr_sayfalari.append(i)
            if okuma.dusuk_guven:
                dusuk.append(i)
            parcalar.append(f"{okuma.etiket()}\n{okuma.metin.strip()}")
        return PdfOcrSonucu(chr(12).join(parcalar), len(sayfa_metinleri), metinsiz,
                            ocr_sayfalari, eksik, dusuk)

    def _sayfa(self, pdf: Path, sha: str, sayfa: int, son_an: float) -> SayfaOkumasi | None:
        for motor in (self.okuyucu.motor, MOTOR_BOS):
            okuma = self.onbellek.al(sha, sayfa, motor)
            if okuma is not None:
                return okuma
        tesseract = self.onbellek.al(sha, sayfa, motor_tesseract())
        # A reading under an older Tesseract language setting is only a stand-in: used when this run
        # cannot read the page again, never kept in place of a new reading.
        eski = None if tesseract is not None else next(
            (o for m in ESKI_TESSERACT_MOTORLARI if m != motor_tesseract()
             for o in [self.onbellek.al(sha, sayfa, m)] if o is not None), None)
        # Claude was already asked for this file, page, engine and prompt
        # version (refusal or API error). Reuse Tesseract for the rest of
        # this calendar month and after, even when confidence is low and
        # budget remains. A page that never reached Claude because the cap
        # was full has no attempt, so a new month may still ask — checked
        # before rendering, so a full cap does not cost a render per low page.
        if self.onbellek.denendi(sha, sayfa, self.okuyucu.motor):
            if tesseract is not None:
                return tesseract
            # The language changed since: read it again locally, never by asking Claude again.
            return self._tesseract_ile(pdf, sha, sayfa, son_an) or eski
        if tesseract is not None and (not tesseract.dusuk_guven or not self.defter.izin_var()):
            return tesseract
        if self._kalan(son_an) <= 0:
            return tesseract or eski
        return self._oku(pdf, sha, sayfa, son_an, tesseract) or eski

    def _sakla(self, sha: str, okuma: SayfaOkumasi) -> SayfaOkumasi:
        self.onbellek.koy(sha, okuma)
        return okuma

    def _oku(self, pdf: Path, sha: str, sayfa: int, son_an: float,
             onceki: SayfaOkumasi | None) -> SayfaOkumasi | None:
        try:
            jpeg = sayfa_gorseli(pdf, sayfa, max(5.0, self._kalan(son_an)))
        except OcrHatasi as exc:
            logger.warning("OCR: %s s.%d çizilemedi (%s)", pdf.name, sayfa, exc)
            return onceki
        if bos_sayfa_mi(jpeg):
            return self._sakla(sha, SayfaOkumasi(sayfa, "", MOTOR_BOS, 1.0))
        if self._kalan(son_an) >= CLAUDE_EN_AZ_SURE and self.defter.izin_var():
            okuma = self._claude(jpeg, sha, sayfa, son_an)
            if okuma is not None:
                return okuma
        if onceki is not None:
            return onceki
        return self._tesseract_oku(pdf, sha, sayfa, son_an, jpeg)

    def _tesseract_ile(self, pdf: Path, sha: str, sayfa: int, son_an: float) -> SayfaOkumasi | None:
        """Render and read one page with Tesseract only (no Claude); None if there is no time."""
        if self._kalan(son_an) < TESSERACT_EN_AZ_SURE:
            return None
        try:
            jpeg = sayfa_gorseli(pdf, sayfa, max(5.0, self._kalan(son_an)))
        except OcrHatasi as exc:
            logger.warning("OCR: %s s.%d çizilemedi (%s)", pdf.name, sayfa, exc)
            return None
        return self._tesseract_oku(pdf, sha, sayfa, son_an, jpeg)

    def _tesseract_oku(self, pdf: Path, sha: str, sayfa: int, son_an: float, jpeg: bytes) -> SayfaOkumasi | None:
        if self._kalan(son_an) < TESSERACT_EN_AZ_SURE:
            return None
        try:
            metin, guven = self.tesseract(jpeg, self._kalan(son_an))
        except Exception as exc:  # noqa: BLE001 — a page left unread is retried next run
            logger.warning("OCR: Tesseract %s s.%d okuyamadı (%s)", pdf.name, sayfa, type(exc).__name__)
            return None
        return self._sakla(sha, SayfaOkumasi(sayfa, metin, motor_tesseract(), guven))

    def _claude(self, jpeg: bytes, sha: str, sayfa: int, son_an: float) -> SayfaOkumasi | None:
        try:
            sonuc = self.okuyucu.oku(jpeg, self._kalan(son_an))
        except Exception as exc:  # noqa: BLE001 — API error, no key, network: fall back
            logger.warning("OCR: Claude okuyamadı (%s); Tesseract'a düşülüyor", type(exc).__name__)
            self._denemeyi_yaz(sha, sayfa)
            return None
        usd = self.defter.yaz(self.okuyucu.motor, sonuc.girdi_token, sonuc.cikti_token)
        if sonuc.reddedildi:
            self._denemeyi_yaz(sha, sayfa)
            return None
        return self._sakla(sha, SayfaOkumasi(sayfa, sonuc.markdown, self.okuyucu.motor,
                                             _GUVEN.get(sonuc.okunabilirlik, 0.7), usd))

    def _denemeyi_yaz(self, sha: str, sayfa: int) -> None:
        self.onbellek.deneme_kaydet(sha, sayfa, self.okuyucu.motor, self.defter._ay())
