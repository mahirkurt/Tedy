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

What the review of the first version measured (2026-09-28, 4f6f8ca) and what
closes it — the links are typed by teachers, so hosts and bodies are hostile:
- time: 1 byte every 0.25 s held a 1 s budget for 6 s, and requests followed
  30 redirects with 40 s of timeouts each. Now every request is waited for
  only until the budget ends, redirects are followed by hand (at most
  EK_AZAMI_YONLENDIRME), and a watchdog cuts the socket of a body still
  streaming when the budget ends. run_sync runs under `timeout 600`.
- addresses: a link at 127.0.0.1, or one redirecting there, was fetched and
  stored. Now every hop must be https and resolve only to global addresses.
- HTML behind a BOM, a comment, a bare <head> or UTF-16 was stored as `.bin`.
- a resume after the file changed glued the old head to the new tail. Now
  the first response's validator rides along as If-Range.
"""
from __future__ import annotations

import hashlib
import ipaddress
import itertools
import json
import logging
import math
import os
import re
import socket
import struct
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from src.json_utils import atomic_json_dump
from src.portal_ekleri import (DURUM_BEKLIYOR, DURUM_COK_BUYUK, DURUM_ERISILEMEDI, DURUM_HATA,
                               DURUM_INDIRILDI, KIMLIK_DESENI, PORTAL_HOST, indirme_adresi)

logger = logging.getLogger(__name__)

MB = 1024 * 1024
EK_BOYUT_SINIRI = 300 * MB
# 64 KiB: the budget is looked at, and a watchdog cut noticed, per block.
PARCA_BOYUTU = 64 * 1024
EK_AZAMI_YONLENDIRME = 5
HTML_OKUMA_SINIRI = 512 * 1024
# How much of a body's head is examined for HTML.
HTML_BAS_SINIRI = PARCA_BOYUTU
# Per socket operation, and never more than what is left of the budget.
BAGLANTI_SURESI = 10.0
OKUMA_SURESI = 30.0
TARAYICI = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/129.0 Safari/537.36")
GIRIS_SAYFALARI = ("login.microsoftonline.com", "login.live.com", "accounts.google.com")
# Where Drive's "can't scan for viruses" form may send the second request.
DRIVE_ONAY_HOSTLARI = frozenset({"drive.usercontent.google.com", "drive.google.com", "docs.google.com"})
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
_PNG = bytes.fromhex("89504e470d0a1a0a")
_JPG = bytes.fromhex("ffd8ff")
_OLE = bytes.fromhex("d0cf11e0a1b11ae1")
_ZIP = bytes.fromhex("504b0304")
_ZIP_SONU = bytes.fromhex("504b0506")          # end of central directory record
_ZIP64_BULUCU = bytes.fromhex("504b0607")      # zip64 end of central directory locator
_ZIP_SONU_BOYU = 22
_ZIP_AZAMI_GIRDI = 10_000
# A docx/xlsx/pptx directory measures in kilobytes; zipfile reads the whole
# directory into memory and makes one object per entry, whatever the entry
# count in the end record claims.
_ZIP_AZAMI_DIZIN = 1 * MB
_HTML_ETIKETLERI = ("<!doctype html", "<html", "<head", "<body", "<script", "<meta", "<title")
_GORUNMEZ = chr(0) + chr(0xFEFF)
_BOMLAR = ((bytes.fromhex("0000feff"), "utf-32-be"), (bytes.fromhex("fffe0000"), "utf-32-le"),
           (bytes.fromhex("efbbbf"), "utf-8"), (bytes.fromhex("feff"), "utf-16-be"),
           (bytes.fromhex("fffe"), "utf-16-le"))
_YONLENDIRMELER = frozenset({301, 302, 303, 307, 308})
_ARALIK = re.compile(r"bytes\s+(\d+)-(\d+)/(\d+|\*)")
_TOPLAM = re.compile(r"bytes\s+\*/(\d+)")
_YENIDEN = "kaldığı yerden sürdürülemedi; baştan indirilecek"
_BUTCE_DOLDU = "bu turun bütçesi doldu; sonraki eşitlemede kaldığı yerden sürecek"
_BOZUK_ADRES = "kaynak bozuk bir adrese yönlendirdi; indirilmedi"
_IC_ADRES = "iç adres ya da çözülemeyen bir ada gidiyor; güvenlik gereği indirilmedi"


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
    """Selenium's cookies as a jar holding only the portal host's own
    cookies, so no hop to SharePoint or Google can carry the portal session.
    A parent-domain cookie (`.k12.tr`, `tedronesans.k12.tr`) would be sent by
    the jar to every host under that domain, so it is dropped; the Secure
    flag is kept, so the session never goes out over plain http."""
    kavanoz = requests.cookies.RequestsCookieJar()
    for c in cerezler or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        alan = str(c.get("domain") or PORTAL_HOST).lstrip(".").lower()
        if alan != PORTAL_HOST:
            continue
        kavanoz.set(str(c["name"]), str(c.get("value") or ""), domain=alan,
                    path=str(c.get("path") or "/"), secure=bool(c.get("secure")))
    return kavanoz if len(kavanoz) else None


def _bilinen_ikili(bas: bytes) -> bool:
    return (bas.startswith((b"%PDF-", _PNG, _JPG, b"GIF87a", b"GIF89a", _OLE, _ZIP))
            or (bas[:4] == b"RIFF" and bas[8:12] == b"WEBP"))


def _bas_metni(bas: bytes) -> str:
    """The head as text: by its BOM (UTF-8/16/32), as BOM-less UTF-16 when
    every other byte is NUL, else byte for byte (the tags are ASCII)."""
    for bom, kodlama in _BOMLAR:
        if bas.startswith(bom):
            return bas[len(bom):].decode(kodlama, errors="replace")
    if len(bas) >= 4 and bas[0] and not bas[1] and bas[2] and not bas[3]:
        return bas.decode("utf-16-le", errors="replace")
    if len(bas) >= 4 and not bas[0] and bas[1] and not bas[2] and bas[3]:
        return bas.decode("utf-16-be", errors="replace")
    return bas.decode("latin-1")


def _html_gibi(metin: str) -> bool:
    """Skip whitespace/NUL, `<!-- … -->` comments and `<?xml … ?>`
    declarations, then require an HTML tag. Whitespace or NUL alone is not
    markup (a binary may open with 64 KiB of zero bytes). A comment or
    declaration prologue that runs to the edge of the head is: measured on
    2cb0918, 4 369 closed comments ending the 64 KiB window on a lone `<`
    hid the <html> tag behind it, and no binary file opens with a comment."""
    i, n = 0, len(metin)
    onsoz = False
    while True:
        while i < n and (metin[i].isspace() or metin[i] in _GORUNMEZ):
            i += 1
        bas = metin[i:i + 16].lower()
        if bas.startswith(("<!--", "<?")):
            kapanis = "-->" if bas.startswith("<!--") else "?>"
            son = metin.find(kapanis, i + 2)
            if son < 0:
                return True                     # unterminated: runs past the head
            i, onsoz = son + len(kapanis), True
            continue
        if bas.startswith(_HTML_ETIKETLERI):
            return True
        # After a markup prologue, a head that ends within reach of the next
        # opener may have cut it (`<`, `<!-`, `<ht`): still markup.
        return onsoz and n - i < 16


def html_mi(bas: bytes, icerik_turu: str) -> bool:
    """A web page where a file was expected. Measured on 4f6f8ca: a UTF-8
    BOM, a leading comment, a bare <head> or UTF-16 each slipped HTML past the
    old `<!doctype html`/`<html` prefix test and it was stored as `.bin`."""
    tur = (icerik_turu or "").split(";")[0].strip().lower()
    if tur in ("text/html", "application/xhtml+xml"):
        return True
    bas = bas[:HTML_BAS_SINIRI]
    if _bilinen_ikili(bas):
        return False
    return _html_gibi(_bas_metni(bas))


def _zip_dizini(yol: Path) -> tuple[int, int] | None:
    """(entry count, central directory size) from the end record, found the
    way zipfile finds it (fixed spot first, then the last 64 KiB). None when
    there is no end record. A zip64 archive reports 0xFFFFFFFF for both:
    zipfile would take its sizes from the zip64 record instead."""
    with yol.open("rb") as f:
        f.seek(0, os.SEEK_END)
        boy = f.tell()
        if boy < _ZIP_SONU_BOYU:
            return None
        okunan = min(boy, _ZIP_SONU_BOYU + 0xFFFF + 20)
        f.seek(boy - okunan)
        kuyruk = f.read(okunan)
    konum = len(kuyruk) - _ZIP_SONU_BOYU
    if not (kuyruk.startswith(_ZIP_SONU, konum) and kuyruk[-2:] == bytes(2)):
        konum = kuyruk.rfind(_ZIP_SONU, max(0, len(kuyruk) - _ZIP_SONU_BOYU - 0xFFFF))
        if konum < 0 or len(kuyruk) - konum < _ZIP_SONU_BOYU:
            return None
    _, _, _, _, girdi, dizin_boyu, _, _ = struct.unpack("<4s4H2LH", kuyruk[konum:konum + _ZIP_SONU_BOYU])
    if (konum >= 20 and kuyruk.startswith(_ZIP64_BULUCU, konum - 20)) or girdi == 0xFFFF \
            or dizin_boyu == 0xFFFFFFFF:
        return 0xFFFFFFFF, 0xFFFFFFFF
    return girdi, dizin_boyu


def _zip_turu(yol: Path) -> tuple[str, str]:
    """docx/xlsx/pptx by their marker entry. Measured on 4f6f8ca: a name
    flagged UTF-8 but not UTF-8 raised UnicodeDecodeError out of ek_indir,
    and a 400 000-entry archive (33 MB) cost 235 MB of memory in namelist()."""
    try:
        dizin = _zip_dizini(yol)
    except OSError:
        return ".bin", "application/octet-stream"
    if dizin is None:
        return ".bin", "application/octet-stream"
    girdi, dizin_boyu = dizin
    if girdi > _ZIP_AZAMI_GIRDI or dizin_boyu > _ZIP_AZAMI_DIZIN:
        return ".zip", "application/zip"
    try:
        with zipfile.ZipFile(yol) as arsiv:
            adlar = set(arsiv.namelist())
    except zipfile.BadZipFile:
        return ".bin", "application/octet-stream"
    except Exception:
        return ".zip", "application/zip"
    if "word/document.xml" in adlar:
        return ".docx", DOCX_MIME
    if "xl/workbook.xml" in adlar:
        return ".xlsx", XLSX_MIME
    if "ppt/presentation.xml" in adlar:
        return ".pptx", PPTX_MIME
    return ".zip", "application/zip"


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
        return _zip_turu(yol)
    return ".bin", "application/octet-stream"


def _onay_hostunda_mi(adres: str) -> bool:
    try:
        p = urlsplit(adres)
        return p.scheme == "https" and (p.hostname or "") in DRIVE_ONAY_HOSTLARI
    except ValueError:
        return False


def drive_onay_adresi(html: str, yanit_url: str) -> str | None:
    """The URL behind Drive's "can't scan for viruses" page: its download
    form's action plus hidden fields (id, export, confirm, uuid), or an older
    page's `confirm=<token>` link. None when the page offers neither, or when
    it points anywhere but Drive's own https hosts (measured on 4f6f8ca: a
    form action at 127.0.0.1 was requested and its answer stored)."""
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form", id="download-form") or next(
        (f for f in soup.find_all("form") if "download" in str(f.get("action") or "")), None)
    if form is not None:
        try:
            eylem = urljoin(yanit_url, str(form.get("action") or ""))
        except ValueError:                      # e.g. `https://[::1/x`: not a URL at all
            return None
        alanlar = [(str(i.get("name")), str(i.get("value") or "")) for i in form.find_all("input")
                   if i.get("type") == "hidden" and i.get("name")]
        if eylem and alanlar:
            adres = eylem + ("&" if "?" in eylem else "?") + urlencode(alanlar)
            return adres if _onay_hostunda_mi(adres) else None
    m = re.search(r"confirm=([0-9A-Za-z_-]+)", html)
    if m:
        try:
            p = urlsplit(yanit_url)
        except ValueError:
            return None
        sorgu = [(k, v) for k, v in parse_qsl(p.query) if k != "confirm"] + [("confirm", m.group(1))]
        adres = urlunsplit((p.scheme, p.netloc, p.path, urlencode(sorgu), ""))
        return adres if _onay_hostunda_mi(adres) else None
    return None


# Measured 2026-09-28 on Python 3.12.3: ipaddress calls these is_global,
# yet each can carry or reach a non-global target — IPv4-compatible ::/96
# (::10.0.0.1), the NAT64 prefix (64:ff9b::a00:1) — or is not unicast at all
# (224.0.0.1 and ff02::1 are "global" too).
_YASAK_AGLAR = (ipaddress.ip_network("::/96"), ipaddress.ip_network("64:ff9b::/96"))


def kuresel_adres_mi(host: str) -> bool:
    """The default address policy: the host is, or resolves only to, global
    unicast addresses — no loopback, private, link-local (169.254.169.254),
    CGNAT, reserved, multicast, IPv4-mapped-private, IPv4-compatible or
    NAT64 address, and not one of several. A name that does not resolve is
    refused too.

    Accepted residue: DNS rebinding between this check and requests' own
    resolution. The fetch is a blind GET into TEDY's own store of a link a
    teacher typed; a host that flips its answer within that window can at
    most have a private URL's body stored as an attachment, not read back
    anywhere but this family's dashboard."""
    try:
        adresler = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            bilgiler = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        except (OSError, UnicodeError, ValueError):
            return False
        try:
            adresler = [ipaddress.ip_address(str(b[4][0]).split("%", 1)[0]) for b in bilgiler]
        except ValueError:
            return False
    if not adresler:
        return False
    for adres in adresler:
        if adres.version == 6 and adres.ipv4_mapped is not None:
            adres = adres.ipv4_mapped
        if not adres.is_global or adres.is_multicast:
            return False
        if adres.version == 6 and any(adres in ag for ag in _YASAK_AGLAR):
            return False
    return True


def _sema_reddi(adres: str) -> str | None:
    try:
        p = urlsplit(adres)
        host = p.hostname
    except ValueError:
        return "geçersiz adres; indirilmedi"
    if p.scheme != "https":
        return "güvenli bağlantı (https) değil; indirilmedi"
    if not host:
        return "geçersiz adres; indirilmedi"
    return None


def _izinli_mi(izin: Callable[[str], bool], host: str) -> bool:
    try:
        return bool(izin(host))
    except Exception:
        return False


def _kapat(nesne: Any) -> None:
    kapat = getattr(nesne, "close", None)
    if callable(kapat):
        try:
            kapat()
        except Exception:
            pass


def _sureli(islem: Callable[[], Any], sure: float) -> tuple[bool, Any]:
    """Run `islem` and wait for it at most `sure` seconds: (True, result),
    the exception it raised, or (False, None) when time ran out. Measured on
    4f6f8ca: a host can drip the status line and headers a byte at a time —
    each byte resets the socket timeout and there is no response yet for the
    watchdog to close — and name resolution has no timeout at all. The
    abandoned call runs on in a daemon thread until its socket timeout or the
    host gives up; a response it still gets is closed there."""
    if not math.isfinite(sure):
        return True, islem()
    kutu: dict[str, Any] = {}
    kilit = threading.Lock()

    def calis() -> None:
        try:
            deger = islem()
        except BaseException as exc:    # handed to the waiting thread
            with kilit:
                kutu["hata"] = exc
            return
        with kilit:
            terk = kutu.get("terk", False)
            if not terk:
                kutu["deger"] = deger
        if terk:
            _kapat(deger)

    is_parcacigi = threading.Thread(target=calis, name="ek-indir-istek", daemon=True)
    is_parcacigi.start()
    is_parcacigi.join(max(0.0, min(sure, threading.TIMEOUT_MAX)))
    with kilit:
        if "deger" in kutu:
            return True, kutu["deger"]
        if "hata" in kutu:
            raise kutu["hata"]
        kutu["terk"] = True
    return False, None


def _soket(yanit: Any) -> socket.socket | None:
    """The socket under a streaming requests.Response (urllib3 2.x)."""
    ham = getattr(yanit, "raw", None)
    for yol in (("_connection", "sock"), ("_fp", "fp", "raw", "_sock")):
        nesne = ham
        for ad in yol:
            nesne = getattr(nesne, ad, None)
        if isinstance(nesne, socket.socket):
            return nesne
    return None


class _Nobetci:
    """A timer armed at the budget's end that shuts the response's socket
    down, so a body dripping a byte at a time cannot hold iter_content past
    the budget (measured on 4f6f8ca: 6 s against a 1 s budget). Shutting the
    socket wakes the blocked read with EOF or an error; whatever the stream
    then does, `dustu` tells the caller the read was cut, not finished."""

    def __init__(self, yanit: Any, sure: float):
        self._yanit = yanit
        self.dustu = False
        self._zamanlayici = None
        if math.isfinite(sure):
            self._zamanlayici = threading.Timer(max(0.0, min(sure, threading.TIMEOUT_MAX)), self._kes)
            self._zamanlayici.name = "ek-indir-nobetci"
            self._zamanlayici.daemon = True

    def __enter__(self) -> "_Nobetci":
        if self._zamanlayici is not None:
            self._zamanlayici.start()
        return self

    def __exit__(self, *hata: Any) -> bool:
        if self._zamanlayici is not None:
            self._zamanlayici.cancel()
            self._zamanlayici.join()
        return False

    def _kes(self) -> None:
        self.dustu = True
        soket = _soket(self._yanit)
        if soket is None:
            _kapat(self._yanit)
            return
        try:
            soket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


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


def _surum_yolu(parca: Path) -> Path:
    return parca.with_name(parca.name.removesuffix(".part") + ".meta.json")


def _parcayi_sil(parca: Path) -> None:
    parca.unlink(missing_ok=True)
    _surum_yolu(parca).unlink(missing_ok=True)


def _bekliyor(parca_bayt: int) -> Sonuc:
    return Sonuc(DURUM_BEKLIYOR, _BUTCE_DOLDU, parca_bayt=parca_bayt)


def _kodlamasiz(yanit: Any) -> bool:
    return str(yanit.headers.get("Content-Encoding", "") or "").strip().lower() in ("", "identity")


def _surum_yaz(parca: Path, yanit: Any) -> int | None:
    """Keep what names this version — a strong ETag, Last-Modified, the
    length — next to the part file; returns the length. A content-coded body
    (gzip) gets none: its ranges count coded bytes, not the file's."""
    etag = lm = toplam = None
    if _kodlamasiz(yanit):
        e = str(yanit.headers.get("ETag") or "")
        etag = e if e and not e.startswith("W/") else None
        lm = str(yanit.headers.get("Last-Modified") or "") or None
        try:
            toplam = int(yanit.headers.get("Content-Length"))
        except (TypeError, ValueError):
            toplam = None
        if toplam is not None and toplam < 0:
            toplam = None
    atomic_json_dump({"etag": etag, "last_modified": lm, "toplam": toplam}, os.fspath(_surum_yolu(parca)))
    return toplam


def _surum_oku(parca: Path) -> dict[str, Any] | None:
    try:
        veri = json.loads(_surum_yolu(parca).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(veri, dict):
        return None
    etag, lm, toplam = veri.get("etag"), veri.get("last_modified"), veri.get("toplam")
    if not isinstance(etag, (str, type(None))) or not isinstance(lm, (str, type(None))):
        return None
    if not (isinstance(toplam, int) and not isinstance(toplam, bool) and toplam > 0):
        return None
    if not (etag or lm):
        return None
    return {"etag": etag, "last_modified": lm, "toplam": toplam}


def _surdurme(parca: Path) -> tuple[int, dict[str, Any] | None]:
    """Where to resume: the part file's size and its version — or (0, None)
    after clearing a part that has no usable version beside it (measured on
    4f6f8ca: a bare Range resume after the file changed mixed two versions)."""
    baslangic = _boyut(parca)
    surum = _surum_oku(parca) if baslangic else None
    if not baslangic or surum is None or baslangic > surum["toplam"]:
        _parcayi_sil(parca)
        return 0, None
    return baslangic, surum


def _ayni_surumun_devami(yanit: Any, aralik: str, baslangic: int, surum: dict[str, Any]) -> bool:
    """A 206 continues the stored version only if it starts where the part
    ends, the total is the stored total, and nothing names another version."""
    m = _ARALIK.match(aralik)
    if not m or int(m.group(1)) != baslangic or m.group(3) == "*" or int(m.group(3)) != surum["toplam"]:
        return False
    if not _kodlamasiz(yanit):
        return False
    etag, lm = yanit.headers.get("ETag"), yanit.headers.get("Last-Modified")
    if etag and surum["etag"] and etag != surum["etag"]:
        return False
    if lm and surum["last_modified"] and lm != surum["last_modified"]:
        return False
    return True


def _html_oku(ilk: bytes, akis: Any) -> str:
    parcalar, toplam = [ilk], len(ilk)
    for blok in akis:
        if toplam >= HTML_OKUMA_SINIRI:
            break
        parcalar.append(blok)
        toplam += len(blok)
    return b"".join(parcalar)[:HTML_OKUMA_SINIRI].decode("utf-8", errors="replace")


def ek_indir(oturum: Any, kayit: dict[str, Any], dizin: Path, butce: Butce,
             cerezler: Any = None, sinir: int = EK_BOYUT_SINIRI,
             adres_izni: Callable[[str], bool] | None = None) -> Sonuc:
    """Fetch one attachment into `dizin` as `<id><ext>`. Never raises for a
    network or HTTP problem — that is a Sonuc the tracker records — and never
    outlasts the budget. The portal cookie jar goes only to a `portal`
    record's request. The address policy is `adres_izni`, else the session's
    own `adres_izni` (the fake HTTP layer's, which never resolves a name),
    else kuresel_adres_mi."""
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
    izin = adres_izni or getattr(oturum, "adres_izni", None) or kuresel_adres_mi
    dizin = Path(dizin)
    parca = dizin / ".parca" / f"{kimlik}.part"
    parca.parent.mkdir(parents=True, exist_ok=True)
    kavanoz = cerezler if kayit.get("type") == "portal" else None
    try:
        return _indir(oturum, kayit, url, parca, dizin, butce, kavanoz, sinir, izin)
    except (requests.RequestException, OSError) as exc:
        if butce.bitti():
            return _bekliyor(_boyut(parca))     # a timeout cut to the budget's end
        return Sonuc(DURUM_HATA, f"ağ hatası ({type(exc).__name__})", parca_bayt=_boyut(parca))
    except Exception as exc:
        # The contract is "never raises": ekleri_esitle calls this per
        # attachment without a try, so a bug or an input nobody foresaw
        # (measured on 2cb0918: `Location: https://[::1/x` → ValueError)
        # must cost this one attachment, not the run's attachment step. The
        # log names the id and the error, never the URL (it can carry a
        # per-recipient token).
        logger.warning("portal eki %s: beklenmeyen hata (%s)", kimlik, type(exc).__name__, exc_info=True)
        return Sonuc(DURUM_HATA, f"beklenmeyen hata ({type(exc).__name__})", parca_bayt=_boyut(parca))


def _indir(oturum: Any, kayit: dict[str, Any], url: str, parca: Path, dizin: Path, butce: Butce,
           kavanoz: Any, sinir: int, izin: Callable[[str], bool]) -> Sonuc:
    """The request loop: redirects by hand, each hop checked (https, a
    permitted address, the budget) before it is sent."""
    baslangic, surum = _surdurme(parca)
    basliklar = {"User-Agent": TARAYICI}
    if surum is not None:
        basliklar["Range"] = f"bytes={baslangic}-"
        basliklar["If-Range"] = surum["etag"] or surum["last_modified"]
    adres, atlama, onaylandi = url, 0, False
    while True:
        red = _sema_reddi(adres)
        if red:
            return Sonuc(DURUM_ERISILEMEDI, red, parca_bayt=baslangic)
        if butce.bitti():
            return _bekliyor(baslangic)
        kalan = butce.kalan_sure()
        if kalan <= 0:
            return _bekliyor(baslangic)
        son_an = time.monotonic() + kalan
        host = urlsplit(adres).hostname or ""
        bitti, izinli = _sureli(lambda: _izinli_mi(izin, host), kalan)
        if not bitti:
            return _bekliyor(baslangic)
        if not izinli:
            return Sonuc(DURUM_ERISILEMEDI, _IC_ADRES, parca_bayt=baslangic)
        zaman = (min(BAGLANTI_SURESI, kalan), min(OKUMA_SURESI, kalan))
        istek_adresi, istek_basliklari = adres, dict(basliklar)
        try:
            bitti, yanit = _sureli(lambda: oturum.get(istek_adresi, headers=istek_basliklari, stream=True,
                                                      timeout=zaman, allow_redirects=False, cookies=kavanoz),
                                   son_an - time.monotonic())
        except ValueError as exc:
            if isinstance(exc, requests.RequestException):
                raise
            # Measured on 2cb0918: even with allow_redirects=False, requests
            # parses a 3xx Location up front (Session.send → resolve_redirects
            # for `r._next`); `https://[::1/x` raises a plain ValueError there.
            return Sonuc(DURUM_ERISILEMEDI, _BOZUK_ADRES, parca_bayt=baslangic)
        if not bitti:
            return _bekliyor(baslangic)
        if yanit.status_code in _YONLENDIRMELER:
            konum = yanit.headers.get("Location")
            onceki = yanit.url or adres
            yanit.close()
            atlama += 1
            if not konum:
                return Sonuc(DURUM_HATA, f"kaynak {yanit.status_code} döndü ama yeni adres vermedi",
                             parca_bayt=baslangic)
            if atlama > EK_AZAMI_YONLENDIRME:
                return Sonuc(DURUM_ERISILEMEDI, f"{EK_AZAMI_YONLENDIRME} adımdan uzun yönlendirme; indirilmedi",
                             parca_bayt=baslangic)
            try:
                adres = urljoin(onceki, str(konum))
                urlsplit(adres).hostname        # an invalid IPv6 host raises only here
            except ValueError:
                return Sonuc(DURUM_ERISILEMEDI, _BOZUK_ADRES, parca_bayt=baslangic)
            continue
        sonuc = _yaniti_isle(yanit, kayit, adres, parca, dizin, butce, sinir, baslangic, surum,
                             onaylandi, son_an)
        if isinstance(sonuc, Sonuc):
            return sonuc
        adres, onaylandi = sonuc, True      # Drive's confirm form: one more request


def _yaniti_isle(yanit: Any, kayit: dict[str, Any], adres: str, parca: Path, dizin: Path,
                 butce: Butce, sinir: int, baslangic: int, surum: dict[str, Any] | None,
                 onaylandi: bool, son_an: float) -> Sonuc | str:
    """One final (non-redirect) response: a Sonuc, or Drive's confirm URL."""
    try:
        kod = yanit.status_code
        aralik = str(yanit.headers.get("Content-Range", ""))
        if baslangic and kod == 416:
            m = _TOPLAM.match(aralik)
            if m and int(m.group(1)) == baslangic == surum["toplam"]:
                return _tamamla(kayit, parca, dizin)   # the last run stopped exactly at the end
            _parcayi_sil(parca)
            return Sonuc(DURUM_HATA, _YENIDEN)
        if baslangic and kod == 206:
            if not _ayni_surumun_devami(yanit, aralik, baslangic, surum):
                _parcayi_sil(parca)
                return Sonuc(DURUM_HATA, _YENIDEN)
            kip = "ab"
        elif kod == 200:
            baslangic, kip = 0, "wb"                   # a new version, or a host ignoring Range
        elif kod in (401, 403, 404, 410):
            _parcayi_sil(parca)
            return Sonuc(DURUM_ERISILEMEDI, f"kaynak {kod} döndü (paylaşım kapalı ya da dosya kaldırılmış)")
        else:
            return Sonuc(DURUM_HATA, f"kaynak {kod} döndü", parca_bayt=baslangic)

        try:
            uzunluk = int(yanit.headers.get("Content-Length") or 0)
        except ValueError:
            uzunluk = 0
        if baslangic + uzunluk > sinir:
            _parcayi_sil(parca)
            return Sonuc(DURUM_COK_BUYUK, f"dosya {(baslangic + uzunluk) // MB} MB; sınır {sinir // MB} MB")

        with _Nobetci(yanit, son_an - time.monotonic()) as nobetci:
            try:
                sonuc = _govdeyi_yaz(yanit, kayit, adres, parca, butce, sinir, baslangic, kip,
                                     surum, onaylandi)
            except Exception:
                if nobetci.dustu:
                    return _bekliyor(_boyut(parca))
                raise
        if nobetci.dustu:
            # Cut at the budget's end: the stream may have ended "cleanly" on
            # the shut socket, so nothing it produced is trusted as finished.
            return _bekliyor(_boyut(parca))
    finally:
        yanit.close()
    return _tamamla(kayit, parca, dizin) if sonuc is None else sonuc


def _govdeyi_yaz(yanit: Any, kayit: dict[str, Any], adres: str, parca: Path, butce: Butce,
                 sinir: int, baslangic: int, kip: str, surum: dict[str, Any] | None,
                 onaylandi: bool) -> Sonuc | str | None:
    """Stream the body into the part file; None when it is complete."""
    akis = yanit.iter_content(PARCA_BOYUTU)
    ilk = next(akis, b"") if kip == "wb" else b""
    if kip == "wb" and html_mi(ilk, str(yanit.headers.get("Content-Type", ""))):
        html = _html_oku(ilk, akis)
        if kayit.get("type") == "drive" and not onaylandi:
            onay = drive_onay_adresi(html, yanit.url or adres)
            if onay:
                return onay
        _parcayi_sil(parca)
        return Sonuc(DURUM_ERISILEMEDI, _html_nedeni(yanit.url or adres))
    toplam = _surum_yaz(parca, yanit) if kip == "wb" else surum["toplam"]

    yazilan = baslangic
    with parca.open(kip) as f:
        for blok in itertools.chain((ilk,), akis):
            if not blok:
                continue
            if butce.bitti():
                return _bekliyor(yazilan)
            yazilan += len(blok)
            if yazilan > sinir:
                break
            f.write(blok)
            butce.bayt_harca(len(blok))
    if yazilan > sinir:
        _parcayi_sil(parca)
        return Sonuc(DURUM_COK_BUYUK, f"dosya {sinir // MB} MB sınırını aştı")
    if toplam is not None and yazilan != toplam:
        return Sonuc(DURUM_HATA, "kaynak dosyanın tamamını göndermedi; sonraki eşitlemede sürecek",
                     parca_bayt=_boyut(parca))
    return None


def _tamamla(kayit: dict[str, Any], parca: Path, dizin: Path) -> Sonuc:
    """Check the finished part file and rename it into place atomically."""
    kimlik = kayit["id"]
    boyut = _boyut(parca)
    if boyut == 0:
        _parcayi_sil(parca)
        return Sonuc(DURUM_HATA, "kaynak boş bir dosya döndü")
    with parca.open("rb") as f:
        bas = f.read(HTML_BAS_SINIRI)
    if html_mi(bas, ""):
        _parcayi_sil(parca)
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
    _surum_yolu(parca).unlink(missing_ok=True)
    return Sonuc(DURUM_INDIRILDI, "", dosya=hedef.name, uzanti=uzanti, mime=mime,
                 boyut=boyut, sha256=ozet.hexdigest())
