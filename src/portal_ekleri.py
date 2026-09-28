"""Portal attachments: what the portal links to, and where TEDY keeps its copies.

Measured 2026-09-28 in output/scraped_data.json: homework details carry
`detail.attachments[] = {name, url}` — SharePoint personal share links
(`…-my.sharepoint.com/:b:/g/personal/…?e=…`) and one Google Docs link — and
two ek_sayfalar pages carry Google Drive `/file/d/<id>/preview` iframes.
Announcements can carry `<column>_url` (0 announcements that day). Nothing
was downloaded: every surface linked straight to the host.

This module is the pure half: it recognises a link, names it with a stable
id (a hash of its canonical URL), says how to fetch it, collects every link
the scrape holds and reads/writes the tracker (output/portal_ekleri.json).
The network half is src/portal_ekleri_indir.py.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterator
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

from src.json_utils import atomic_json_dump

EK_DIZINI = PurePosixPath("content/portal-ekleri")
IZLEYICI = PurePosixPath("output/portal_ekleri.json")
PORTAL_HOST = "portal.tedronesans.k12.tr"
KIMLIK_DESENI = re.compile(r"^[0-9a-f]{16}$")
_DOSYA_ADI = re.compile(r"^([0-9a-f]{16})\.[a-z0-9]{1,5}$")

DURUM_BEKLIYOR = "bekliyor"
DURUM_INDIRILDI = "indirildi"
DURUM_ERISILEMEDI = "erisilemedi"
DURUM_COK_BUYUK = "cok_buyuk"
DURUM_HATA = "hata"
DURUM_BAGLANTI = "baglanti"

METIN_VAR = "var"
METIN_YOK = "yok"
METIN_DESTEKLENMIYOR = "desteklenmiyor"
METIN_BEKLIYOR = "bekliyor"
METIN_HATA = "hata"
# First line of every <id>.txt: the index finds an attachment by its name
# too, and ek_oku drops this paragraph before paging the body.
METIN_ONEKI = "PORTAL EKİ · "

DOSYA_UZANTILARI = frozenset({".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
                              ".odt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".zip"})
_DRIVE_DOSYA = re.compile(r"^/file/d/([A-Za-z0-9_-]{10,})")
_DRIVE_KIMLIK = re.compile(r"^[A-Za-z0-9_-]{10,}$")
_DOCS = re.compile(r"^/(document|presentation|spreadsheets)/d/([A-Za-z0-9_-]{10,})")
_SP_PAYLASIM = re.compile(r"^/:([a-z]):/")
_URL = re.compile(r"https?://[^\s\"'<>]+")
_KAYNAK_SINIRI = 5
_TUR_ADI = {"sharepoint": "SharePoint dosyası", "drive": "Google Drive dosyası",
            "google-docs": "Google dokümanı", "portal": "Portal dosyası", "dosya": "Dosya"}


def _drive_kimligi(p) -> str | None:
    m = _DRIVE_DOSYA.match(p.path)
    if m:
        return m.group(1)
    if p.path in ("/open", "/uc"):
        kimlik = dict(parse_qsl(p.query)).get("id", "")
        return kimlik if _DRIVE_KIMLIK.match(kimlik) else None
    return None


def ek_turu(url: Any) -> str:
    """What a link is, decided from the URL alone. `baglanti` is a link that
    is not one file — a folder share, a form, a video page — opened at its
    source and never downloaded."""
    p = urlsplit(str(url or "").strip())
    if p.scheme not in ("http", "https") or not p.hostname:
        return "baglanti"
    host = p.hostname
    uzanti = PurePosixPath(unquote(p.path)).suffix.lower()
    if host.endswith(".sharepoint.com"):
        m = _SP_PAYLASIM.match(p.path)
        if m:
            # ":f:" is a folder share: many files, not one.
            return "baglanti" if m.group(1) == "f" else "sharepoint"
        return "sharepoint" if uzanti in DOSYA_UZANTILARI else "baglanti"
    if host == "drive.google.com":
        return "drive" if _drive_kimligi(p) else "baglanti"
    if host == "docs.google.com":
        if _DOCS.match(p.path):
            return "google-docs"
        return "drive" if _DRIVE_DOSYA.match(p.path) else "baglanti"
    if uzanti in DOSYA_UZANTILARI:
        return "portal" if host == PORTAL_HOST else "dosya"
    return "baglanti"


def kanonik_adres(url: Any) -> str:
    """One spelling per file: Drive's preview/view/open/uc forms collapse to
    /file/d/<id>, a Docs link loses /edit and its query, a SharePoint share
    link loses `?e=` (a per-recipient token; the path names the file)."""
    ham = str(url or "").strip()
    p = urlsplit(ham)
    tur = ek_turu(ham)
    if tur == "drive":
        return f"https://drive.google.com/file/d/{_drive_kimligi(p)}"
    if tur == "google-docs":
        m = _DOCS.match(p.path)
        return f"https://docs.google.com/{m.group(1)}/d/{m.group(2)}"
    if tur == "sharepoint":
        return urlunsplit(("https", p.netloc.lower(), p.path, "", ""))
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ""))


def ek_kimligi(url: Any) -> str:
    return hashlib.sha256(kanonik_adres(url).encode("utf-8")).hexdigest()[:16]


def indirme_adresi(url: Any) -> str | None:
    """Where the file itself answers (probe 2026-09-28): SharePoint with
    `download=1`, Drive's `uc?export=download`, Docs/Slides/Sheets as
    `/export?format=pdf`, anything else as it is. None for a `baglanti`."""
    ham = str(url or "").strip()
    p = urlsplit(ham)
    tur = ek_turu(ham)
    if tur == "sharepoint":
        sorgu = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k != "download"]
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(sorgu + [("download", "1")]), ""))
    if tur == "drive":
        return f"https://drive.google.com/uc?export=download&id={_drive_kimligi(p)}"
    if tur == "google-docs":
        m = _DOCS.match(p.path)
        return f"https://docs.google.com/{m.group(1)}/d/{m.group(2)}/export?format=pdf"
    if tur in ("portal", "dosya"):
        return urlunsplit((p.scheme, p.netloc, p.path, p.query, ""))
    return None


def tahmini_ad(url: Any) -> str:
    son = PurePosixPath(unquote(urlsplit(str(url or "")).path)).name
    if PurePosixPath(son).suffix.lower() in DOSYA_UZANTILARI:
        return son
    return _TUR_ADI.get(ek_turu(url), "Bağlantı")


def sayfa_belgesi_adi(baslik: str, sira: int, toplam: int) -> str:
    baslik = " ".join(str(baslik or "").split()) or "Portal sayfası"
    return baslik if toplam <= 1 else f"{baslik} ({sira}. belge)"


def duyuru_eki_adi(satir: dict[str, Any], anahtar: str) -> str:
    sutun = anahtar[: -len("_url")]
    deger = " ".join(str(satir.get(sutun) or "").split())
    return deger if deger and deger != "-" else (sutun or "Duyuru eki")


def odev_kaynagi(satir: dict[str, Any]) -> dict[str, str]:
    ders = str(satir.get("Ders Adı") or "").strip()
    baslik = str(satir.get("Ödev Başlığı") or "").strip()
    teslim = str(satir.get("Ödev Son Teslim Tarihi") or "").strip()
    return {"section": "odevler", "item": f"{ders}|{baslik}|{teslim}", "title": baslik, "course": ders}


@dataclass
class EkAdayi:
    url: str
    ad: str
    kaynaklar: list[dict[str, str]] = field(default_factory=list)

    @property
    def kimlik(self) -> str:
        return ek_kimligi(self.url)

    @property
    def tur(self) -> str:
        return ek_turu(self.url)


def _metinler(deger: Any, yol: list[str]) -> Iterator[tuple[list[str], str]]:
    if isinstance(deger, str):
        yield yol, deger
    elif isinstance(deger, dict):
        for k, v in deger.items():
            yield from _metinler(v, yol + [str(k)])
    elif isinstance(deger, list):
        for i, v in enumerate(deger):
            yield from _metinler(v, yol + [str(i)])


def _genel_kaynak(yol: list[str]) -> dict[str, str]:
    bolum, ders, baslik = yol[0], "", ""
    if bolum == "ders_icerikleri" and len(yol) > 1:
        ders = baslik = yol[1]
    elif bolum == "ders_icerikleri_haftalar" and len(yol) > 2:
        ders, baslik = yol[2], f"{yol[2]} · {yol[1]}"
    return {"section": bolum, "item": "/".join(yol), "title": baslik, "course": ders}


def ekleri_topla(veri: Any) -> list[EkAdayi]:
    """Every attachment link the scrape holds, one candidate per id: homework
    first, then portal pages, announcements, and whatever a generic scan of
    every other string finds (so a future section's files are caught).
    Homework, page and announcement links are taken whatever they point at —
    the teacher put them there — and a non-file one becomes `baglanti`; the
    generic scan takes file-looking links only, so a Teams meeting or a
    portal page is never mistaken for a document."""
    veri = veri if isinstance(veri, dict) else {}
    adaylar: dict[str, EkAdayi] = {}

    def ekle(url: Any, ad: Any, kaynak: dict[str, str], yalniz_dosya: bool) -> None:
        url = str(url or "").strip().rstrip(".,;:)")
        if not url.lower().startswith(("http://", "https://")):
            return
        if yalniz_dosya and ek_turu(url) == "baglanti":
            return
        kimlik = ek_kimligi(url)
        aday = adaylar.get(kimlik)
        if aday is None:
            adaylar[kimlik] = EkAdayi(url=url, ad=" ".join(str(ad or "").split()) or tahmini_ad(url),
                                      kaynaklar=[kaynak])
        elif kaynak not in aday.kaynaklar and len(aday.kaynaklar) < _KAYNAK_SINIRI:
            aday.kaynaklar.append(kaynak)

    odevlerim = veri.get("odevlerim") if isinstance(veri.get("odevlerim"), dict) else {}
    odevler = odevlerim.get("homework") if isinstance(odevlerim.get("homework"), dict) else {}
    for satir in odevler.get("rows") or []:
        if not isinstance(satir, dict):
            continue
        detay = satir.get("detail") if isinstance(satir.get("detail"), dict) else {}
        for ek in detay.get("attachments") or []:
            if isinstance(ek, dict):
                ekle(ek.get("url"), ek.get("name"), odev_kaynagi(satir), yalniz_dosya=False)

    sayfalar = veri.get("ek_sayfalar") if isinstance(veri.get("ek_sayfalar"), dict) else {}
    for anahtar, sayfa in sayfalar.items():
        if not isinstance(sayfa, dict):
            continue
        belgeler = [b for b in sayfa.get("documents") or [] if isinstance(b, str)]
        baslik = str(sayfa.get("title") or anahtar)
        for i, url in enumerate(belgeler, 1):
            ekle(url, sayfa_belgesi_adi(baslik, i, len(belgeler)),
                 {"section": "ek_sayfalar", "item": str(anahtar), "title": baslik, "course": ""},
                 yalniz_dosya=False)

    duyurular = veri.get("duyurular") if isinstance(veri.get("duyurular"), dict) else {}
    for satir in duyurular.get("announcements") or []:
        if not isinstance(satir, dict):
            continue
        baslik = str(satir.get("e-Posta Başlık") or satir.get("Başlık") or "").strip()
        oge = f"{satir.get('Yayın Tarihi', '')}|{baslik}"
        for anahtar, url in satir.items():
            if str(anahtar).endswith("_url"):
                ekle(url, duyuru_eki_adi(satir, str(anahtar)),
                     {"section": "duyurular", "item": oge, "title": baslik, "course": ""},
                     yalniz_dosya=False)

    bilinen = set(adaylar)
    for bolum, deger in veri.items():
        for yol, metin in _metinler(deger, [str(bolum)]):
            for url in _URL.findall(metin):
                url = url.rstrip(".,;:)")
                if ek_turu(url) == "baglanti" or ek_kimligi(url) in bilinen:
                    continue
                ekle(url, tahmini_ad(url), _genel_kaynak(yol), yalniz_dosya=True)
    return list(adaylar.values())


class EkDeposu:
    """content/portal-ekleri (the copies, <id>.txt text, <id>.meta.json
    sidecars, .parca/ part files) and output/portal_ekleri.json (the
    tracker), resolved under one project root."""

    def __init__(self, proje_koku: str | Path):
        self.koku = Path(proje_koku)
        self.dizin = self.koku / EK_DIZINI
        self.izleyici_yolu = self.koku / IZLEYICI

    def oku(self) -> dict[str, dict[str, Any]]:
        try:
            veri = json.loads(self.izleyici_yolu.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        ekler = veri.get("ekler") if isinstance(veri, dict) else None
        if not isinstance(ekler, dict):
            return {}
        return {k: v for k, v in ekler.items() if KIMLIK_DESENI.match(str(k)) and isinstance(v, dict)}

    def yaz(self, ekler: dict[str, dict[str, Any]]) -> None:
        atomic_json_dump({"surum": 1, "guncellendi": datetime.now().isoformat(timespec="seconds"),
                          "ekler": ekler}, str(self.izleyici_yolu))

    def kayit(self, kimlik: Any) -> dict[str, Any] | None:
        kimlik = str(kimlik or "")
        return self.oku().get(kimlik) if KIMLIK_DESENI.match(kimlik) else None

    def dosya_yolu(self, kayit: dict[str, Any] | None) -> Path | None:
        """The record's own copy, or None. The name is checked against the
        record's id and a strict pattern, so no stored value can point
        outside the directory."""
        kayit = kayit if isinstance(kayit, dict) else {}
        m = _DOSYA_ADI.match(str(kayit.get("file") or ""))
        if not m or m.group(1) != kayit.get("id"):
            return None
        yol = self.dizin / m.group(0)
        return yol if yol.is_file() else None

    def metin_yolu(self, kimlik: str) -> Path:
        return self.dizin / f"{kimlik}.txt"

    def meta_yolu(self, kimlik: str) -> Path:
        return self.dizin / f"{kimlik}.meta.json"

    def meta(self, kimlik: Any) -> dict[str, Any]:
        if not KIMLIK_DESENI.match(str(kimlik or "")):
            return {}
        try:
            veri = json.loads(self.meta_yolu(str(kimlik)).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return veri if isinstance(veri, dict) else {}


def ek_basligi(kayit: dict[str, Any]) -> str:
    """"<ek adı> · <ödev başlığı>" — how a citation and ek_oku name an
    attachment; never a path. Takes a tracker record or a .meta.json."""
    kayit = kayit if isinstance(kayit, dict) else {}
    ad = " ".join(str(kayit.get("name") or "").split()) or "Portal eki"
    kaynak = kayit.get("source") if isinstance(kayit.get("source"), dict) else {}
    baglam = " ".join(str(kaynak.get("title") or kayit.get("title") or "").split())
    return f"{ad} · {baglam}" if baglam and baglam != ad else ad


def ek_ozeti(ekler: dict[str, dict[str, Any]], url: Any, ad: Any) -> dict[str, Any]:
    """One attachment as an API payload carries it: `tedyUrl` only when TEDY
    holds the copy; `status` always, so a surface can say why there is none."""
    url = str(url or "")
    ozet: dict[str, Any] = {"name": str(ad or ""), "url": url, "id": None,
                            "tedyUrl": None, "status": DURUM_BAGLANTI}
    if ek_turu(url) == "baglanti":
        return ozet
    kimlik = ek_kimligi(url)
    kayit = ekler.get(kimlik) or {}
    durum = str(kayit.get("status") or DURUM_BEKLIYOR)
    ozet.update(id=kimlik, status=durum)
    if durum == DURUM_INDIRILDI and kayit.get("file"):
        ozet["tedyUrl"] = f"/api/ekler/{kimlik}"
    elif kayit.get("reason"):
        ozet["reason"] = str(kayit["reason"])
    return ozet


def metin_govdesi(ham: str) -> str:
    """An <id>.txt without its METIN_ONEKI header paragraph."""
    if ham.startswith(METIN_ONEKI):
        return ham.partition("\n\n")[2].strip("\n")
    return ham
