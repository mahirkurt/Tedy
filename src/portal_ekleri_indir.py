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
- HTML behind a BOM, a comment, a bare <head>, UTF-16 or a leading hidden
  character was stored as `.bin`.
- a resume after the file changed glued the old head to the new tail. Now
  the first response's validator rides along as If-Range, and a 206 that
  does not echo that same validator is not appended.
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
import selectors
import shutil
import signal
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from src.json_utils import atomic_json_dump
from src.portal_ekleri import (DURUM_BAGLANTI, DURUM_BEKLIYOR, DURUM_COK_BUYUK, DURUM_ERISILEMEDI,
                               DURUM_HATA, DURUM_INDIRILDI, KIMLIK_DESENI, METIN_BEKLIYOR,
                               METIN_DESTEKLENMIYOR, METIN_HATA, METIN_ONEKI, METIN_VAR, METIN_YOK,
                               PORTAL_HOST, EkDeposu, ek_basligi, ekleri_topla, indirme_adresi,
                               kanonik_adres)

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


def _portal_alani(alan: str) -> str:
    return alan.lstrip(".").lower().rstrip(".")


def portal_cerez_kavanozu(cerezler: Iterable[dict[str, Any]] | None) -> requests.cookies.RequestsCookieJar | None:
    """Selenium's cookies as a jar holding only the portal host's own
    cookies. A parent-domain cookie (`.k12.tr`, `tedronesans.k12.tr`) would
    be sent to every host under that name, so it is dropped. Secure is
    forced on: a cookie that arrived without the flag would otherwise leave
    on plain http. Netscape's suffix match would still send a version-0
    cookie to subdomains, so the request path attaches the jar only for
    https on exactly PORTAL_HOST."""
    kavanoz = requests.cookies.RequestsCookieJar()
    for c in cerezler or []:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        alan = _portal_alani(str(c.get("domain") or PORTAL_HOST))
        if alan != PORTAL_HOST:
            continue
        try:
            kavanoz.set_cookie(requests.cookies.create_cookie(
                str(c["name"]), str(c.get("value") or ""), domain=PORTAL_HOST,
                path=str(c.get("path") or "/") or "/", secure=True))
        except (TypeError, ValueError):
            continue
    return kavanoz if len(kavanoz) else None


def _istek_cerezleri(kavanoz: Any, adres: str) -> Any:
    """The portal jar, and only when this hop is https to the portal host itself."""
    if not kavanoz:
        return None
    try:
        p = urlsplit(adres)
    except ValueError:
        return None
    if p.scheme != "https" or _portal_alani(p.hostname or "") != PORTAL_HOST:
        return None
    return kavanoz


def _cerez_guvenli(cerez: Any) -> bool:
    return bool(getattr(cerez, "secure", False)) and _portal_alani(getattr(cerez, "domain", "") or "") == PORTAL_HOST


def _oturum_cerezlerini_kis(oturum: Any, adres: str) -> list[Any]:
    """Take off the session every cookie this hop must not carry.

    Unsafe cookies (not Secure, or not exactly the portal host — a parent
    domain such as `.k12.tr`) are discarded. Safe portal cookies are
    returned when this hop is not the portal, so they can be put back
    afterwards: left in the jar, Netscape would send them to a subdomain.
    A session with no cookie jar is left alone (the fake HTTP layer)."""
    kavanoz = getattr(oturum, "cookies", None)
    if kavanoz is None or not hasattr(kavanoz, "clear"):
        return []
    try:
        p = urlsplit(adres)
        portal_hop = p.scheme == "https" and _portal_alani(p.hostname or "") == PORTAL_HOST
    except ValueError:
        portal_hop = False
    geri: list[Any] = []
    for cerez in list(kavanoz):
        guvenli = _cerez_guvenli(cerez)
        if portal_hop and guvenli:
            continue
        try:
            kavanoz.clear(cerez.domain, cerez.path, cerez.name)
        except (KeyError, ValueError):
            continue
        if guvenli:
            geri.append(cerez)
    return geri


def _cerezleri_geri_koy(oturum: Any, cerezler: list[Any]) -> None:
    kavanoz = getattr(oturum, "cookies", None)
    if kavanoz is None:
        return
    for cerez in cerezler:
        try:
            kavanoz.set_cookie(cerez)
        except (TypeError, ValueError):
            continue


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


def _atlanan_bas(ch: str) -> bool:
    """A character a login page can hide behind and a binary file can open
    with. Whitespace and NUL alone are not markup. Format characters
    (U+200B and the other Cf set) and the C0/C1 controls are: measured after
    4f6f8ca, one leading U+200B or 0x01 in front of `<html>` was stored."""
    if ch.isspace() or ch in _GORUNMEZ:
        return True
    o = ord(ch)
    if o < 32 or o == 0x7F or 0x80 <= o <= 0x9F:
        return True
    return unicodedata.category(ch) == "Cf"


def _html_gibi(metin: str) -> bool:
    """Skip whitespace, hidden characters, `<!-- … -->` comments and
    `<?xml … ?>` declarations, then require an HTML tag. Whitespace or NUL
    alone is not markup (a binary may open with 64 KiB of zero bytes). A
    comment or declaration prologue that runs to the edge of the head is:
    measured on 2cb0918, 4 369 closed comments ending the 64 KiB window on a
    lone `<` hid the <html> tag behind it, and no binary file opens with a
    comment."""
    i, n = 0, len(metin)
    onsoz = False
    while True:
        while i < n and _atlanan_bas(metin[i]):
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
    BOM, a leading comment, a bare <head>, UTF-16 or a leading U+200B (the
    bytes e2 80 8b, invisible only once read as UTF-8) each slipped HTML
    past the old `<!doctype html`/`<html` prefix test and it was stored."""
    tur = (icerik_turu or "").split(";")[0].strip().lower()
    if tur in ("text/html", "application/xhtml+xml"):
        return True
    bas = bas[:HTML_BAS_SINIRI]
    if _bilinen_ikili(bas):
        return False
    if _html_gibi(_bas_metni(bas)):
        return True
    # UTF-8 without a BOM. U+200B is the bytes e2 80 8b; read as latin-1
    # those are ordinary characters and the tag behind them is missed.
    try:
        utf8 = bas.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return _html_gibi(utf8)


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
    except Exception:
        # MemoryError and struct.error included: a corrupt directory must
        # cost this file its Office type, not the sync turn.
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
    """Drive's own https hosts, with nothing in front of them. Userinfo
    (`https://evil.example@drive.google.com/...`) and a backslash both
    survive a hostname allow-list and are how a confirm form left Google."""
    try:
        p = urlsplit(adres)
    except ValueError:
        return False
    if p.scheme != "https" or p.username is not None or p.password is not None:
        return False
    if "\\" in adres or "@" in (p.netloc or ""):
        return False
    return (p.hostname or "").rstrip(".").lower() in DRIVE_ONAY_HOSTLARI


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
    # The stored validator has to come back on the 206. A host that ignores
    # If-Range and omits ETag/Last-Modified would otherwise glue the old
    # head to a new tail of the same length and mark the mix downloaded.
    etag, lm = yanit.headers.get("ETag"), yanit.headers.get("Last-Modified")
    if surum.get("etag"):
        return etag == surum["etag"]
    if surum.get("last_modified"):
        return lm == surum["last_modified"]
    return False


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
        gonderilecek = _istek_cerezleri(kavanoz, istek_adresi)
        geri = _oturum_cerezlerini_kis(oturum, istek_adresi)
        bitti = None
        try:
            try:
                bitti, yanit = _sureli(lambda: oturum.get(istek_adresi, headers=istek_basliklari, stream=True,
                                                          timeout=zaman, allow_redirects=False,
                                                          cookies=gonderilecek),
                                       son_an - time.monotonic())
            except ValueError as exc:
                if isinstance(exc, requests.RequestException):
                    raise
                # Measured on 2cb0918: even with allow_redirects=False, requests
                # parses a 3xx Location up front (Session.send → resolve_redirects
                # for `r._next`); `https://[::1/x` raises a plain ValueError there.
                return Sonuc(DURUM_ERISILEMEDI, _BOZUK_ADRES, parca_bayt=baslangic)
            if not bitti:
                # The request thread is still inside `oturum`. The jar stays
                # as this hop left it; ekleri_esitle stops on bekliyor.
                return _bekliyor(baslangic)
        finally:
            if bitti is not False:
                # Drop a Set-Cookie this response just stored (a parent domain,
                # or one without Secure), then put the portal's own cookies back.
                _oturum_cerezlerini_kis(oturum, istek_adresi)
                _cerezleri_geri_koy(oturum, geri)
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


# ── One sync run (plan 2026-09-28-portal-ekleri, Görev 6) ────────────────────
# A link that answered a login wall is tried again a day later: a teacher can
# open the share. A failed request (hata) is tried on the next run; a file
# over the cap, or a plain link, never.
EK_YENIDEN_DENEME = timedelta(hours=24)
METIN_SURE_TAVANI = 180.0
METIN_DENEME_SINIRI = 3
# An extraction cut by the run's end is an attempt only if it was given at
# least this long. Görev 7's budget is min(180 s, …), so `sure` always equals
# what is left: measured on f29062c (probe C), a PDF pdftotext never finishes
# was cut, uncounted and retried first on every run, forever.
METIN_ADIL_SURE = 60.0
# The most text one attachment keeps. A 400-page textbook is a few MB; a
# crafted PDF can emit text for as long as it runs, so pdftotext is killed
# one byte past this and _metni_hazirla cuts every text here, marked.
METIN_AZAMI_BAYT = 16 * MB
# word/document.xml read for an attachment. FileAdapters' own cap is 50 MB:
# measured on f29062c, 49 MB cost 4.4 s, 554 MB RSS and a 25.7 M-character
# text; 8 MB cost 0.73 s and 116 MB RSS.
METIN_DOCX_XML_SINIRI = 8 * MB
# Runs in a row in which a download received bytes but its part file did
# not grow: a host that ignores Range restarts at 0 every run, and a file
# larger than one run's byte budget never finishes (probe B on f29062c).
EK_ILERLEMESIZ_SINIRI = 2
_ILERLEMESIZ = "kaynak sürdürmeyi desteklemiyor ve dosya bir turun bayt bütçesinden büyük"
_PDF = frozenset({".pdf"})
_DOCX = frozenset({".docx"})
_GORSEL = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
_METIN_NOTU = {METIN_YOK: "(Metin katmanı yok: taranmış belge ya da görsel.)",
               METIN_DESTEKLENMIYOR: "(Bu ek türünün metni okunmuyor.)"}
_KESILDI_NOTU = "(Metin burada kesildi: bu ekin metni {mb} MB sınırını aşıyor; devamı okunmadı.)"
_NEDEN_SURE = "metin çıkarma süresi doldu"
_NEDEN_PDFTOTEXT = "pdftotext çalıştırılamadı"
_NEDEN_PDF_BOZUK = "PDF okunamadı (bozuk ya da şifreli)"
_DOCX_NEDENLERI = {"bozuk": "Word belgesi okunamadı (bozuk dosya)",
                   "dtd": "Word belgesi güvenlik gereği okunmadı (DTD ya da varlık bildirimi var)",
                   "sinir": f"Word belgesinin metni {METIN_DOCX_XML_SINIRI // MB} MB sınırından büyük"}


class KesikMetin(str):
    """A text its producer cut at METIN_AZAMI_BAYT. The flag travels with the
    text, so _metni_hazirla marks the cut whatever the text's length ends up
    being — measured on 9294c7f, a newline as the one byte past the cap was
    stripped away and a cut text was stored as if complete."""


@dataclass
class _CikarmaAyari:
    """The settings FileAdapters reads, without building an AssistantConfig
    (which creates the index directory as a side effect)."""
    max_file_size_mb: int
    pdf_max_pages: int
    pdf_timeout: float
    enable_ocr: bool


def _grubu_oldur(surec: subprocess.Popen) -> None:
    """SIGKILL the child's whole process group (it was started in a session
    of its own), so a helper it forked cannot outlive the cap either."""
    try:
        os.killpg(surec.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _alt_surec_metni(komut: list[str], sure: float) -> tuple[int | None, bytes, bool]:
    """(exit code, stdout, cut) of `komut`, waited for at most `sure` seconds
    of wall clock: (None, b"", False) when time ran out. Stdout is read
    through a selector against the deadline, not by communicate(), so neither
    a silent child nor a grandchild holding the pipe open can stretch the
    wait. Past METIN_AZAMI_BAYT the child is killed, the first
    METIN_AZAMI_BAYT bytes are kept and `cut` is True.

    The process group is always killed at the end, even after the child
    exited: measured on f29062c (probe A), `sleep 20 & exit 0` left the
    grandchild alive. The command also runs under `timeout -s KILL`, so if
    this process is killed first (cron's `timeout 600` kills run_sync, not
    the session started here) the orphan still ends ceil(sure) + 1 s later."""
    if not (sure > 0):
        return None, b"", False
    son_an = time.monotonic() + sure
    if shutil.which("timeout"):
        komut = ["timeout", "-s", "KILL", str(math.ceil(min(sure, 1e9)) + 1)] + komut
    surec = subprocess.Popen(komut, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    parcalar: list[bytes] = []
    toplam = 0
    try:
        fd = surec.stdout.fileno()
        with selectors.DefaultSelector() as secici:
            secici.register(fd, selectors.EVENT_READ)
            while True:
                kalan = son_an - time.monotonic()
                if kalan <= 0:
                    return None, b"", False
                if not secici.select(min(kalan, threading.TIMEOUT_MAX)):
                    continue
                blok = os.read(fd, PARCA_BOYUTU)
                if not blok:
                    break                                   # EOF
                parcalar.append(blok)
                toplam += len(blok)
                if toplam > METIN_AZAMI_BAYT:
                    return 0, b"".join(parcalar)[:METIN_AZAMI_BAYT], True
        try:
            kod = surec.wait(timeout=max(0.0, son_an - time.monotonic()))
        except subprocess.TimeoutExpired:
            return None, b"", False
        return kod, b"".join(parcalar), False
    finally:
        # The group outlives its reaped leader while any member is alive, and
        # Linux does not hand out a pid still in use as a process group id.
        _grubu_oldur(surec)
        surec.wait()
        surec.stdout.close()


def _pdf_metni(yol: Path, sure: float) -> tuple[str, str]:
    """pdftotext as a child bounded by `sure`, not FileAdapters' PDF path:
    that one tries pypdf first (pure Python, no time bound at all, when it
    is installed) and, in the plan's version, was given max(5, int(sure))
    seconds — measured 2026-09-28, 0.3 s of budget left became a 5 s wait."""
    try:
        kod, ham, kesildi = _alt_surec_metni(["pdftotext", "-layout", os.fspath(yol), "-"], sure)
    except OSError as exc:
        logger.warning("portal eki metni: pdftotext başlatılamadı (%s)", type(exc).__name__)
        return METIN_HATA, _NEDEN_PDFTOTEXT
    if kod is None:
        return METIN_HATA, _NEDEN_SURE
    if kesildi:
        # errors="ignore": the cut may split the last UTF-8 sequence.
        return METIN_VAR, KesikMetin(ham.decode("utf-8", errors="ignore").strip())
    metin = ham.decode("utf-8", errors="replace")
    if metin.strip():
        return METIN_VAR, metin.strip()
    # Exit 0 with nothing printed: a scan with no text layer (OCR is Görev
    # 14–15). 126/127 is `timeout` saying pdftotext could not be run; any
    # other non-zero exit is a damaged or locked PDF.
    if kod == 0:
        return METIN_YOK, ""
    return METIN_HATA, _NEDEN_PDFTOTEXT if kod in (126, 127) else _NEDEN_PDF_BOZUK


def metin_cikar(yol: Path, sure: float) -> tuple[str, str]:
    """(text status, text) for one downloaded copy, within `sure` seconds.
    For METIN_HATA the second element is the reason, in Turkish, for the
    tracker's `text_reason` — never written as the attachment's text.

    - PDF: pdftotext, a child process killed at `sure` (see _pdf_metni). A
      PDF without a text layer is METIN_YOK — reported, never OCR'd here:
      rasterising and OCR'ing a scan costs seconds per page, and one
      100-page book would outlast the whole 600 s cron run (plan 2026-09-28,
      decision 2; OCR arrives in Görev 14–15).
    - .docx: the assistant's own reader, in process, reading at most
      METIN_DOCX_XML_SINIRI of word/document.xml. An archive it cannot read
      (not a zip, a DTD, over the cap) is METIN_HATA with its reason;
      METIN_YOK is only a real document with no text in it.
    - Images: METIN_YOK. FileAdapters' tesseract call has no timeout, so it
      is not run here even with ASSISTANT_ENABLE_OCR=1.
    - Anything else: METIN_DESTEKLENMIYOR."""
    uzanti = yol.suffix.lower()
    if uzanti in _PDF:
        return _pdf_metni(yol, sure)
    if uzanti in _GORSEL:
        return METIN_YOK, ""
    if uzanti not in _DOCX:
        return METIN_DESTEKLENMIYOR, ""
    from src.assistant_core import DocxExtractionError, FileAdapters
    ayar = _CikarmaAyari(max_file_size_mb=EK_BOYUT_SINIRI // MB + 1, pdf_max_pages=400,
                         pdf_timeout=sure, enable_ocr=False)
    try:
        metin = FileAdapters(ayar)._extract_docx_text(yol, sinir=METIN_DOCX_XML_SINIRI, hata_bildir=True)
    except DocxExtractionError as exc:
        return METIN_HATA, _DOCX_NEDENLERI.get(exc.reason, _DOCX_NEDENLERI["bozuk"])
    return (METIN_VAR, metin) if metin.strip() else (METIN_YOK, "")


def metin_dosyasi(kayit: dict[str, Any], durum: str, metin: str) -> str:
    """<id>.txt: a METIN_ONEKI header paragraph (so the index finds an
    attachment by its name), a note when there is no text, then the text."""
    kaynak = _kaynak(kayit)
    parcalar = [ek_basligi(kayit)] + ([kaynak["course"]] if kaynak.get("course") else [])
    bas = METIN_ONEKI + " · ".join(parcalar)
    not_ = _METIN_NOTU.get(durum, "")
    govde = metin.strip()
    return "\n".join(x for x in (bas, not_) if x) + (f"\n\n{govde}" if govde else "") + "\n"


# The tracker is a file on disk, and a record the scrape no longer carries
# keeps whatever it holds, so every value is read defensively. Measured on
# f29062c (probe D): `partial_bytes: [1]`, `source: "x"`, an aware
# `next_attempt` and `attempts: "x"` each crashed every run.
def _tamsayi(deger: Any) -> int:
    if isinstance(deger, bool):
        return 0
    if isinstance(deger, (int, float, str)):
        try:
            return max(0, int(deger))
        except (ValueError, OverflowError):
            return 0
    return 0


def _kaynak(kayit: dict[str, Any]) -> dict[str, Any]:
    kaynak = kayit.get("source")
    return kaynak if isinstance(kaynak, dict) else {}


def _yerel(an: datetime) -> datetime:
    return an.astimezone().replace(tzinfo=None) if an.tzinfo else an


def _zaman(deger: Any) -> datetime | None:
    """Naive local time, or None — which means "retry now", never "never"."""
    if not isinstance(deger, str) or not deger:
        return None
    try:
        return _yerel(datetime.fromisoformat(deger))
    except ValueError:
        return None


def _indirilmeli(kayit: dict[str, Any], depo: EkDeposu, an: datetime) -> bool:
    durum = kayit.get("status")
    if durum in (DURUM_BEKLIYOR, DURUM_HATA):
        return True
    if durum == DURUM_INDIRILDI:
        return depo.dosya_yolu(kayit) is None          # the copy went missing
    if durum == DURUM_ERISILEMEDI:
        sonraki = _zaman(kayit.get("next_attempt"))
        return sonraki is None or an >= sonraki
    return False                                       # cok_buyuk, baglanti


def _metin_gerekli(kayit: dict[str, Any], depo: EkDeposu) -> bool:
    if kayit.get("status") != DURUM_INDIRILDI or depo.dosya_yolu(kayit) is None:
        return False
    metin = kayit.get("text")
    if metin in (METIN_VAR, METIN_YOK, METIN_DESTEKLENMIYOR):
        return not depo.metin_yolu(kayit["id"]).exists()   # the .txt went missing
    return (metin in (None, "", METIN_BEKLIYOR, METIN_HATA)
            and _tamsayi(kayit.get("text_attempts")) < METIN_DENEME_SINIRI)


def _geride(kayit: dict[str, Any], depo: EkDeposu, an: datetime) -> bool:
    """Work that already lost a run — a part file its last run did not grow,
    a counted stall, or a text extraction cut at the run's end — waits
    behind fresh work, so one pathological file cannot take every run's
    budget first. Independent of stall counting: a Range-ignoring host cut
    by the time budget fetches less each run (alinan < onceki), which
    counts no stall, yet the part does not grow (round 3 on f300a9c)."""
    if _tamsayi(kayit.get("stalled_runs")) > 0:
        return True
    if _tamsayi(kayit.get("partial_bytes")) > 0 and kayit.get("partial_grew") is not True:
        return True
    return kayit.get("text_cut") is True and not _indirilmeli(kayit, depo, an)


def _is_sirasi(ekler: dict[str, dict[str, Any]], depo: EkDeposu, an: datetime) -> list[dict[str, Any]]:
    """Fresh work before work that lost a run; within each, part files first
    (finish what is started — a part is fresh only while its runs grow it),
    then homework, newest first."""
    isler = [k for k in ekler.values() if _indirilmeli(k, depo, an) or _metin_gerekli(k, depo)]
    isler.sort(key=lambda k: str(k.get("first_seen") or ""), reverse=True)
    isler.sort(key=lambda k: (_geride(k, depo, an),
                              0 if _tamsayi(k.get("partial_bytes")) > 0 else 1,
                              0 if _kaynak(k).get("section") == "odevler" else 1))
    return isler


def _ilerlemeyi_denetle(kayit: dict[str, Any], sonuc: Sonuc, onceki: int, alinan: int,
                        depo: EkDeposu) -> Sonuc:
    """A `bekliyor` that received at least as many bytes this run as the
    part file already held, yet left it no longer, has restarted at 0 and
    got nowhere: a stall. EK_ILERLEMESIZ_SINIRI stalls make the attachment
    terminal `cok_buyuk`. A part that grew resets the count. A run that
    received less than the part held (a smaller budget, or other files took
    part of it) says nothing either way: measured on 9294c7f, budgets of
    2.5, 2.0 and 1.5 MB made a 3 MB file terminal, though it would finish
    in any run given 3 MB."""
    if sonuc.durum != DURUM_BEKLIYOR:
        kayit.pop("stalled_runs", None)
        return sonuc
    if onceki > 0 and sonuc.parca_bayt > onceki:
        kayit.pop("stalled_runs", None)                 # progress
        return sonuc
    if onceki <= 0 or alinan < onceki:
        return sonuc
    sayi = _tamsayi(kayit.get("stalled_runs")) + 1
    if sayi < EK_ILERLEMESIZ_SINIRI:
        if sayi:
            kayit["stalled_runs"] = sayi
        else:
            kayit.pop("stalled_runs", None)
        return sonuc
    kayit.pop("stalled_runs", None)
    _parcayi_sil(depo.dizin / ".parca" / f"{kayit['id']}.part")
    return Sonuc(DURUM_COK_BUYUK, _ILERLEMESIZ)


def _sonucu_yaz(kayit: dict[str, Any], sonuc: Sonuc, an: datetime) -> None:
    zaman = an.isoformat(timespec="seconds")
    kayit["attempts"] = _tamsayi(kayit.get("attempts")) + 1
    kayit.update(status=sonuc.durum, reason=sonuc.neden, last_attempt=zaman, partial_bytes=sonuc.parca_bayt)
    if sonuc.durum == DURUM_INDIRILDI:
        kayit.update(file=sonuc.dosya, ext=sonuc.uzanti, mime=sonuc.mime, size=sonuc.boyut,
                     sha256=sonuc.sha256, fetched_at=zaman, text=METIN_BEKLIYOR, text_attempts=0,
                     next_attempt=None, partial_bytes=0)
        for alan in ("text_cut", "text_reason", "text_truncated"):
            kayit.pop(alan, None)
        return
    kayit["file"] = None
    kayit["next_attempt"] = ((an + EK_YENIDEN_DENEME).isoformat(timespec="seconds")
                             if sonuc.durum == DURUM_ERISILEMEDI else None)


def _atomik_yaz(yol: Path, metin: str) -> None:
    """tmp + rename in the same directory. The temporary name is unique and
    dot-prefixed, so two overlapping runs never share it and _tamamla's
    `<id>.*` sweep never sees it. mkstemp creates 0600; the .txt is made
    0644 like the .meta.json beside it (open() under umask 022)."""
    fd, gecici = tempfile.mkstemp(prefix=".", suffix=".tmp", dir=yol.parent)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(metin)
        os.replace(gecici, yol)
    except BaseException:
        Path(gecici).unlink(missing_ok=True)
        raise


def _metni_hazirla(depo: EkDeposu, kayit: dict[str, Any], butce: Butce,
                   cikarici: Callable[[Path, float], tuple[str, str]]) -> bool:
    """Extract once into <id>.txt and <id>.meta.json. False when the run's
    end cut an extraction given less than METIN_ADIL_SURE: that says nothing
    about the file, so it is not an attempt; the record stays METIN_BEKLIYOR
    and, marked `text_cut`, waits behind fresh work next run. Given at least
    METIN_ADIL_SURE, a cut is an attempt like any failure."""
    kimlik = kayit["id"]
    yol = depo.dosya_yolu(kayit)
    sure = min(METIN_SURE_TAVANI, butce.kalan_sure())
    try:
        durum, metin = cikarici(yol, sure)
    except Exception as exc:
        logger.warning("portal eki %s: metin çıkarılamadı (%s)", kimlik, type(exc).__name__, exc_info=True)
        durum, metin = METIN_HATA, f"metin çıkarılırken beklenmeyen hata ({type(exc).__name__})"
    if durum not in (METIN_VAR, METIN_YOK, METIN_DESTEKLENMIYOR, METIN_HATA) or not isinstance(metin, str):
        durum, metin = METIN_HATA, ""
    if durum == METIN_HATA and butce.bitti():
        kayit["text_cut"] = True
        if sure < METIN_ADIL_SURE:
            return False
        metin = metin or _NEDEN_SURE
    elif durum != METIN_HATA:
        kayit.pop("text_cut", None)
    kayit["text_attempts"] = _tamsayi(kayit.get("text_attempts")) + 1
    kaynak = _kaynak(kayit)
    meta = {"id": kimlik, "name": kayit.get("name", ""), "title": kaynak.get("title", ""),
            "section": kaynak.get("section", ""), "course": kaynak.get("course", "")}
    kayit.pop("text_truncated", None)
    if durum == METIN_HATA:
        kayit.update(text=durum, text_chars=0, text_reason=metin)
        atomic_json_dump(meta, os.fspath(depo.meta_yolu(kimlik)))
        # A .txt left from an earlier copy or an older run would be indexed
        # and served as this attachment's text; with no text there is none.
        depo.metin_yolu(kimlik).unlink(missing_ok=True)
        return True
    kayit.pop("text_reason", None)
    ham = metin.encode("utf-8")
    if isinstance(metin, KesikMetin) or len(ham) > METIN_AZAMI_BAYT:
        # Never stored as if complete: the .txt says where it stops, the
        # sidecar and the tracker carry the flag.
        metin = ham[:METIN_AZAMI_BAYT].decode("utf-8", errors="ignore").rstrip()
        metin += "\n\n" + _KESILDI_NOTU.format(mb=max(1, METIN_AZAMI_BAYT // MB))
        kayit["text_truncated"] = meta["text_truncated"] = True
    kayit.update(text=durum, text_chars=len(metin))
    atomic_json_dump(meta, os.fspath(depo.meta_yolu(kimlik)))
    _atomik_yaz(depo.metin_yolu(kimlik), metin_dosyasi(kayit, durum, metin))
    return True


def ekleri_esitle(proje_koku: str | Path, veri: Any, oturum: Any, butce: Butce, cerezler: Any = None,
                  simdi: Callable[[], datetime] = datetime.now,
                  metin_cikarici: Callable[[Path, float], tuple[str, str]] = metin_cikar) -> dict[str, Any]:
    """One run: collect every link in `veri`, merge into the tracker, then
    download and extract text in priority order until the budget runs out.
    The tracker is written after every file, so a run killed mid-way keeps
    what it finished. Idempotent: a second run over the same data with the
    copies in place makes no request.

    The run stops at the first `bekliyor` download: ek_indir answers that
    when it abandoned a request thread or cut a socket at the budget's end,
    and that daemon thread may still be inside `oturum` — a requests.Session
    is not thread-safe, so no second download may start on it this run."""
    depo = EkDeposu(proje_koku)
    an = _yerel(simdi())
    zaman = an.isoformat(timespec="seconds")
    ekler = depo.oku()
    for kimlik, kayit in ekler.items():
        # The key is checked against KIMLIK_DESENI by EkDeposu.oku; the
        # stored `id` field is not, and every path below is built from it.
        kayit["id"] = kimlik
    for aday in ekleri_topla(veri):
        kayit = ekler.setdefault(aday.kimlik, {"id": aday.kimlik, "status": DURUM_BEKLIYOR, "reason": "",
                                               "attempts": 0, "first_seen": zaman, "text": ""})
        kayit.update(url=aday.url, canonical=kanonik_adres(aday.url), type=aday.tur, name=aday.ad,
                     source=aday.kaynaklar[0], sources=aday.kaynaklar, last_seen=zaman)
        if aday.tur == "baglanti":
            kayit.update(status=DURUM_BAGLANTI, reason="dosya değil, bir bağlantı")
    depo.dizin.mkdir(parents=True, exist_ok=True)
    depo.yaz(ekler)

    bu_tur = {"indirilen": 0, "bayt": 0, "metin": 0}
    for kayit in _is_sirasi(ekler, depo, an):
        if butce.bitti():
            break
        if _indirilmeli(kayit, depo, an):
            onceki, harcanan = _tamsayi(kayit.get("partial_bytes")), butce.harcanan
            ham = ek_indir(oturum, kayit, depo.dizin, butce, cerezler)
            sonuc = _ilerlemeyi_denetle(kayit, ham, onceki, butce.harcanan - harcanan, depo)
            _sonucu_yaz(kayit, sonuc, an)
            # Queue order only: a part goes first next run if this run grew it.
            if sonuc.parca_bayt > 0:
                kayit["partial_grew"] = sonuc.parca_bayt > onceki
            else:
                kayit.pop("partial_grew", None)
            depo.yaz(ekler)
            if ham.durum == DURUM_BEKLIYOR:
                break
            if sonuc.durum == DURUM_INDIRILDI:
                # New bytes: the old <id>.txt describes the previous copy.
                depo.metin_yolu(kayit["id"]).unlink(missing_ok=True)
                bu_tur["indirilen"] += 1
                bu_tur["bayt"] += sonuc.boyut
        if _metin_gerekli(kayit, depo) and not butce.bitti():
            if not _metni_hazirla(depo, kayit, butce, metin_cikarici):
                depo.yaz(ekler)
                break
            depo.yaz(ekler)
            bu_tur["metin"] += 1

    sayim = Counter(str(k.get("status")) for k in ekler.values())
    return {"toplam": len(ekler),
            **{d: sayim.get(d, 0) for d in (DURUM_INDIRILDI, DURUM_BEKLIYOR, DURUM_ERISILEMEDI,
                                            DURUM_COK_BUYUK, DURUM_HATA, DURUM_BAGLANTI)},
            "bu_tur_indirilen": bu_tur["indirilen"], "bu_tur_bayt": bu_tur["bayt"],
            "bu_tur_metin": bu_tur["metin"],
            "kalan_is": sum(1 for k in ekler.values()
                            if (_indirilmeli(k, depo, an) and k.get("status") != DURUM_ERISILEMEDI)
                            or _metin_gerekli(k, depo))}
