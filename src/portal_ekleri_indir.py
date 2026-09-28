"""Portal attachments, the network half: fetch a file safely, within a budget.

What the probe measured on 2026-09-28 without a login: SharePoint share links
with `download=1` answered 200 application/pdf for 4 of 5 (two over 100 MB:
112 and 101 MB) and text/html for the fifth — a login wall or a folder;
Drive's `uc?export=download` answered octet-stream for 4 of 4 up to 28 MB,
and a large file answers with a confirm page first; docs.google.com answered
HTML until asked for `/export?format=pdf`. So: a web page where a file was
expected is never stored, the type is read from the bytes, a file over 300 MB
is refused, and a download that runs out of this run's budget is kept as a
part file and resumed with a Range request on the next run.
"""
from __future__ import annotations

import hashlib
import itertools
import os
import re
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from src.portal_ekleri import (DURUM_BEKLIYOR, DURUM_COK_BUYUK, DURUM_ERISILEMEDI, DURUM_HATA,
                               DURUM_INDIRILDI, KIMLIK_DESENI, PORTAL_HOST, indirme_adresi)

MB = 1024 * 1024
EK_BOYUT_SINIRI = 300 * MB
PARCA_BOYUTU = 1 * MB
HTML_OKUMA_SINIRI = 512 * 1024
# (connect, read) per socket operation: a stalled read is noticed in 30 s,
# which the run's reserve absorbs (run_sync.EK_YEDEK_SURE).
ZAMAN_ASIMI = (10.0, 30.0)
TARAYICI = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/129.0 Safari/537.36")
GIRIS_SAYFALARI = ("login.microsoftonline.com", "login.live.com", "accounts.google.com")
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_PNG = bytes.fromhex("89504e470d0a1a0a")
_JPG = bytes.fromhex("ffd8ff")
_OLE = bytes.fromhex("d0cf11e0a1b11ae1")
_ZIP = bytes.fromhex("504b0304")
_ARALIK = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)")
_TOPLAM = re.compile(r"bytes\s+\*/(\d+)")
_YENIDEN = "kaldığı yerden sürdürülemedi; baştan indirilecek"


class Butce:
    """One run's allowance: a monotonic deadline and a byte count. Whatever
    is left when either runs out continues on a later run."""

    def __init__(self, son_an: float, bayt: int, saat: Callable[[], float] = time.monotonic):
        self.son_an = son_an
        self.bayt = bayt
        self.saat = saat
        self.harcanan = 0

    def bayt_harca(self, n: int) -> None:
        self.harcanan += n

    def kalan_sure(self) -> float:
        return max(0.0, self.son_an - self.saat())

    def bitti(self) -> bool:
        return self.saat() >= self.son_an or self.harcanan >= self.bayt


@dataclass
class Sonuc:
    durum: str
    neden: str = ""
    dosya: str | None = None
    uzanti: str = ""
    mime: str = ""
    boyut: int = 0
    sha256: str = ""
    parca_bayt: int = 0


def portal_cerez_kavanozu(cerezler: Iterable[dict[str, Any]] | None) -> requests.cookies.RequestsCookieJar | None:
    """Selenium's cookies as a jar scoped to the portal's own domain, so a
    redirect to SharePoint or Google can never carry the portal session."""
    kavanoz = requests.cookies.RequestsCookieJar()
    for c in cerezler or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        alan = str(c.get("domain") or PORTAL_HOST).lstrip(".")
        if alan != PORTAL_HOST and not PORTAL_HOST.endswith("." + alan):
            continue
        kavanoz.set(str(c["name"]), str(c.get("value") or ""), domain=alan, path=str(c.get("path") or "/"))
    return kavanoz if len(kavanoz) else None


def html_mi(bas: bytes, icerik_turu: str) -> bool:
    tur = (icerik_turu or "").split(";")[0].strip().lower()
    if tur in ("text/html", "application/xhtml+xml"):
        return True
    return bas.lstrip()[:15].lower().startswith((b"<!doctype html", b"<html"))


def tur_bul(bas: bytes, yol: Path) -> tuple[str, str]:
    """(extension, mime) from the first bytes — never from the host's
    Content-Type, which SharePoint and Drive set to octet-stream at will.
    Unknown bytes are `.bin`, which the dashboard only ever serves as a
    download."""
    if bas.startswith(b"%PDF-"):
        return ".pdf", "application/pdf"
    if bas.startswith(_PNG):
        return ".png", "image/png"
    if bas.startswith(_JPG):
        return ".jpg", "image/jpeg"
    if bas.startswith((b"GIF87a", b"GIF89a")):
        return ".gif", "image/gif"
    if bas[:4] == b"RIFF" and bas[8:12] == b"WEBP":
        return ".webp", "image/webp"
    if bas.startswith(_OLE):
        return ".doc", "application/msword"      # legacy Office; may be .xls/.ppt
    if bas.startswith(_ZIP):
        try:
            with zipfile.ZipFile(yol) as arsiv:
                adlar = set(arsiv.namelist())
        except (zipfile.BadZipFile, OSError):
            return ".bin", "application/octet-stream"
        if "word/document.xml" in adlar:
            return ".docx", DOCX_MIME
        if "xl/workbook.xml" in adlar:
            return ".xlsx", XLSX_MIME
        if "ppt/presentation.xml" in adlar:
            return ".pptx", PPTX_MIME
        return ".zip", "application/zip"
    return ".bin", "application/octet-stream"


def drive_onay_adresi(html: str, yanit_url: str) -> str | None:
    """The URL behind Drive's "can't scan for viruses" page: its download
    form's action plus hidden fields (id, export, confirm, uuid), or an older
    page's `confirm=<token>` link. None when the page offers neither."""
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", id="download-form") or next(
        (f for f in soup.find_all("form") if "download" in str(f.get("action") or "")), None)
    if form is not None:
        eylem = urljoin(yanit_url, str(form.get("action") or ""))
        alanlar = [(str(i.get("name")), str(i.get("value") or "")) for i in form.find_all("input")
                   if i.get("type") == "hidden" and i.get("name")]
        if eylem and alanlar:
            return eylem + ("&" if "?" in eylem else "?") + urlencode(alanlar)
    m = re.search(r"confirm=([0-9A-Za-z_-]+)", html)
    if m:
        p = urlsplit(yanit_url)
        sorgu = [(k, v) for k, v in parse_qsl(p.query) if k != "confirm"] + [("confirm", m.group(1))]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(sorgu), ""))
    return None


def _html_nedeni(son_url: str) -> str:
    host = (urlsplit(son_url).hostname or "").lower()
    if any(host == g or host.endswith("." + g) for g in GIRIS_SAYFALARI):
        return "kaynak giriş istiyor; paylaşım herkese açık değil"
    return "dosya yerine bir web sayfası döndü (klasör ya da erişim sayfası)"


def _boyut(yol: Path) -> int:
    try:
        return yol.stat().st_size
    except OSError:
        return 0


def _iste(oturum: Any, url: str, baslangic: int, kavanoz: Any) -> Any:
    basliklar = {"User-Agent": TARAYICI}
    if baslangic:
        basliklar["Range"] = f"bytes={baslangic}-"
    return oturum.get(url, headers=basliklar, stream=True, timeout=ZAMAN_ASIMI,
                      allow_redirects=True, cookies=kavanoz)


def _html_oku(ilk: bytes, akis: Any) -> str:
    parcalar, toplam = [ilk], len(ilk)
    for blok in akis:
        if toplam >= HTML_OKUMA_SINIRI:
            break
        parcalar.append(blok)
        toplam += len(blok)
    return b"".join(parcalar)[:HTML_OKUMA_SINIRI].decode("utf-8", errors="replace")


def ek_indir(oturum: Any, kayit: dict[str, Any], dizin: Path, butce: Butce,
             cerezler: Any = None, sinir: int = EK_BOYUT_SINIRI) -> Sonuc:
    """Fetch one attachment into `dizin` as `<id><ext>`. Never raises for a
    network or HTTP problem — that is a Sonuc the tracker records. The portal
    cookie jar goes only to a `portal` record's request."""
    kimlik = str(kayit.get("id") or "")
    if not KIMLIK_DESENI.fullmatch(kimlik):
        # kayit['id'] drives every path built below (.parca/<id>.part,
        # <id><uzanti>); an unvalidated id could carry `../` and escape
        # `dizin` entirely. A caller always derives it with ek_kimligi(), so
        # this only ever fires on a caller bug — but it must fire, not walk
        # the filesystem with an attacker-shaped string.
        return Sonuc(DURUM_HATA, "geçersiz ek kimliği")
    url = indirme_adresi(kayit.get("url"))
    if url is None:
        return Sonuc(DURUM_ERISILEMEDI, "dosya bağlantısı değil")
    dizin = Path(dizin)
    parca = dizin / ".parca" / f"{kimlik}.part"
    parca.parent.mkdir(parents=True, exist_ok=True)
    kavanoz = cerezler if kayit.get("type") == "portal" else None
    try:
        return _indir(oturum, kayit, url, parca, dizin, butce, kavanoz, sinir, onaylandi=False)
    except (requests.RequestException, OSError) as exc:
        return Sonuc(DURUM_HATA, f"ağ hatası ({type(exc).__name__})", parca_bayt=_boyut(parca))


def _indir(oturum: Any, kayit: dict[str, Any], url: str, parca: Path, dizin: Path, butce: Butce,
           kavanoz: Any, sinir: int, onaylandi: bool) -> Sonuc:
    baslangic = _boyut(parca)
    yanit = _iste(oturum, url, baslangic, kavanoz)
    try:
        kod = yanit.status_code
        aralik = str(yanit.headers.get("Content-Range", ""))
        if baslangic and kod == 416:
            m = _TOPLAM.match(aralik)
            if m and int(m.group(1)) == baslangic:
                yanit.close()
                return _tamamla(kayit, parca, dizin)   # the last run stopped exactly at the end
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_HATA, _YENIDEN)
        if baslangic and kod == 206:
            m = _ARALIK.match(aralik)
            if not m or int(m.group(1)) != baslangic:
                parca.unlink(missing_ok=True)
                return Sonuc(DURUM_HATA, _YENIDEN)
            kip = "ab"
        elif kod == 200:
            baslangic, kip = 0, "wb"                   # a host that ignores Range starts over
        elif kod in (401, 403, 404, 410):
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_ERISILEMEDI, f"kaynak {kod} döndü (paylaşım kapalı ya da dosya kaldırılmış)")
        else:
            return Sonuc(DURUM_HATA, f"kaynak {kod} döndü", parca_bayt=baslangic)

        try:
            uzunluk = int(yanit.headers.get("Content-Length") or 0)
        except ValueError:
            uzunluk = 0
        if baslangic + uzunluk > sinir:
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_COK_BUYUK, f"dosya {(baslangic + uzunluk) // MB} MB; sınır {sinir // MB} MB")

        akis = yanit.iter_content(PARCA_BOYUTU)
        ilk = next(akis, b"") if kip == "wb" else b""
        if kip == "wb" and html_mi(ilk, str(yanit.headers.get("Content-Type", ""))):
            html = _html_oku(ilk, akis)
            if kayit.get("type") == "drive" and not onaylandi:
                onay = drive_onay_adresi(html, yanit.url or url)
                if onay:
                    yanit.close()
                    return _indir(oturum, kayit, onay, parca, dizin, butce, kavanoz, sinir, onaylandi=True)
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_ERISILEMEDI, _html_nedeni(yanit.url or url))

        yazilan = baslangic
        tasti = False
        with parca.open(kip) as f:
            for blok in itertools.chain((ilk,), akis):
                if not blok:
                    continue
                if butce.bitti():
                    return Sonuc(DURUM_BEKLIYOR, "bu turun bütçesi doldu; sonraki eşitlemede "
                                                 "kaldığı yerden sürecek", parca_bayt=yazilan)
                yazilan += len(blok)
                if yazilan > sinir:
                    tasti = True
                    break
                f.write(blok)
                butce.bayt_harca(len(blok))
        if tasti:
            parca.unlink(missing_ok=True)
            return Sonuc(DURUM_COK_BUYUK, f"dosya {sinir // MB} MB sınırını aştı")
    finally:
        yanit.close()
    return _tamamla(kayit, parca, dizin)


def _tamamla(kayit: dict[str, Any], parca: Path, dizin: Path) -> Sonuc:
    """Check the finished part file and rename it into place atomically."""
    kimlik = kayit["id"]
    boyut = _boyut(parca)
    if boyut == 0:
        parca.unlink(missing_ok=True)
        return Sonuc(DURUM_HATA, "kaynak boş bir dosya döndü")
    with parca.open("rb") as f:
        bas = f.read(4096)
    if html_mi(bas, ""):
        parca.unlink(missing_ok=True)
        return Sonuc(DURUM_ERISILEMEDI, "dosya yerine bir web sayfası döndü")
    uzanti, mime = tur_bul(bas, parca)
    ozet = hashlib.sha256()
    with parca.open("rb") as f:
        for blok in iter(lambda: f.read(PARCA_BOYUTU), b""):
            ozet.update(blok)
    hedef = dizin / f"{kimlik}{uzanti}"
    for eski in dizin.glob(f"{kimlik}.*"):
        if eski != hedef and not eski.name.endswith((".txt", ".meta.json")):
            eski.unlink(missing_ok=True)
    os.replace(parca, hedef)
    return Sonuc(DURUM_INDIRILDI, "", dosya=hedef.name, uzanti=uzanti, mime=mime,
                 boyut=boyut, sha256=ozet.hexdigest())
