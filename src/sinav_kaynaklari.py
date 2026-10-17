"""Serbest metin sınav adayları (spec §5 "Adaylar", "Ön süzgeç").

Her aday metniyle, dersiyle, yayın tarihiyle ve portaldaki konum(lar)ıyla gelir.
Portal her yazıyı iki kart olarak verir (başlıklı ve başlıksız) ve yazı sonraki
haftaya taşınır: aynı katlanmış metin tek aday olur, konumları birleşir; başka
bir kartın içinde kalan kart ve öğe atılır. Ön süzgeç ücretsizdir: eşleşmeyen
parça modele gitmez."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.course_names import normalize_course
from src.portal_ekleri import KIMLIK_DESENI
from src.portal_susu import temiz_metin
from src.sinav_tarihi import hafta_etiketi_araligi, katla, okul_yili, yayin_tarihi

EK_KARAKTER_SINIRI = 4000
_SUZGEC = re.compile(
    r"\b(sinav\w*|yazili(?!m)\w*|quiz(?:zes)?|ktt|konu tarama\w*|deneme\w*|test(?:i|ler|leri|s)?"
    r"|exam(?:s|ination\w*)?|degerlendirme\b|gis)\b")
_TARIH = re.compile(r"\b(\d{2})\.(\d{2})\.(\d{4})\b")


@dataclass
class Aday:
    metin: str
    ders: str | None
    yayin: date | None
    tur: str
    konumlar: list[dict] = field(default_factory=list)

    @property
    def anahtar(self) -> str:
        """Course + folded text. De-duplication and the model cache go by `metin_anahtari`
        (one reading per text); this names a candidate together with its course."""
        return hashlib.sha256(f"{self.ders or ''}\x1f{katla(self.metin)}".encode("utf-8")).hexdigest()

    @property
    def metin_anahtari(self) -> str:
        """The folded text alone: the candidate's identity (de-duplication, model cache) and,
        beside the course, an undated record's id."""
        return hashlib.sha256(katla(self.metin).encode("utf-8")).hexdigest()


def on_suzgec(metin: str) -> bool:
    return bool(_SUZGEC.search(katla(metin)))


def _gun(deger: Any) -> date | None:
    try:
        return datetime.fromisoformat(str(deger)[:19]).date()
    except (TypeError, ValueError):
        return None


def _ilk_tarih(metin: str) -> date | None:
    m = _TARIH.search(metin)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _ders_parcalari(bolum: Any, etiket: str | None, aralik: tuple[date, date] | None,
                    bolum_adi: str) -> list[Aday]:
    sonuc: list[Aday] = []
    if not isinstance(bolum, dict):
        return sonuc
    for sekme, icerik in bolum.items():
        if not isinstance(icerik, dict):
            continue
        ders = normalize_course(sekme) or sekme
        # Only a list is a list of cards: a string would be read letter by letter, a dict by its keys.
        kartlar = icerik.get("cards") if isinstance(icerik.get("cards"), list) else []
        ogeler = icerik.get("items") if isinstance(icerik.get("items"), list) else []
        parcalar = [("kart", c) for c in kartlar] + [("oge", o) for o in ogeler]
        # `text` is every card of the tab run together: with cards it would only
        # swallow them (and their locations); without cards it is the only text.
        if not kartlar and isinstance(icerik.get("text"), str):
            parcalar.append(("metin", icerik["text"]))
        for sira, (tip, ham) in enumerate(parcalar):
            if ham is None:
                continue
            metin = temiz_metin(ham if isinstance(ham, str) else json.dumps(ham, ensure_ascii=False))
            if not metin.strip():
                continue
            yayin = yayin_tarihi(metin) or (aralik[0] if aralik else None)
            konum = {"bolum": bolum_adi, "hafta": etiket, "ders": sekme, "sira": sira}
            if tip != "kart":
                konum[tip] = True
            sonuc.append(Aday(metin, ders, yayin, "ders_karti", [konum]))
    return sonuc


def _odevler(veri: dict, ilk_gorulme: dict[str, str], yil_basi: date | None = None) -> list[Aday]:
    satirlar = ((veri.get("odevlerim") or {}).get("homework") or {}).get("rows") or []
    sonuc = []
    for r in satirlar:
        if not isinstance(r, dict):
            continue
        baslik = str(r.get("Ödev Başlığı") or "").strip()
        aciklama = temiz_metin((r.get("detail") or {}).get("description") if isinstance(r.get("detail"), dict) else "")
        metin = "\n".join(x for x in (baslik, aciklama) if x)
        if not metin:
            continue
        # first_seen is keyed by title, so last year's "Quiz" would date this year's: ignored.
        ilk = _gun(ilk_gorulme.get(baslik))
        if ilk is not None and yil_basi is not None and ilk < yil_basi:
            ilk = None
        sonuc.append(Aday(metin, normalize_course(r.get("Ders Adı") or "") or None, ilk, "odev",
                          [{"bolum": "odev", "baslik": baslik, "teslim": r.get("Ödev Son Teslim Tarihi")}]))
    return sonuc


def _duyurular(veri: dict) -> list[Aday]:
    satirlar = (veri.get("duyurular") or {}).get("announcements") or []
    sonuc = []
    for sira, r in enumerate(satirlar):
        if not isinstance(r, dict):
            continue
        degerler = [str(v) for k, v in r.items() if not str(k).endswith("_url") and v]
        metin = temiz_metin("\n".join(degerler))
        if metin.strip():
            sonuc.append(Aday(metin, None, _ilk_tarih(metin), "duyuru", [{"bolum": "duyuru", "sira": sira}]))
    return sonuc


def _birlestir(liste: list[Aday]) -> list[Aday]:
    # One candidate per text and course (copies across weeks keep the earliest date). The same
    # text in two course tabs on the same date is a shared announcement: its course is None, so
    # the gate takes the course from the model when its word is in the text. Posted on different
    # dates it is two exams ("Yarın quiz" on Monday and on Wednesday) and stays two candidates —
    # still one model call, since the cache is keyed by the text.
    gruplar: dict[str, list[Aday]] = {}
    for a in liste:
        grup = gruplar.setdefault(a.metin_anahtari, [])
        o = next((x for x in grup if x.ders == a.ders), None) or next(
            (x for x in grup if x.yayin == a.yayin), None)
        if o is None:
            grup.append(Aday(a.metin, a.ders, a.yayin, a.tur, list(a.konumlar)))
            continue
        o.konumlar.extend(k for k in a.konumlar if k not in o.konumlar)
        if o.ders != a.ders:
            o.ders = None
        if a.yayin is not None and (o.yayin is None or a.yayin < o.yayin):   # earliest known date
            o.yayin = a.yayin
    kalan = [a for grup in gruplar.values() for a in grup]
    katli = {id(a): katla(a.metin) for a in kalan}
    sonuc = []
    for a in kalan:
        kapsayan = any(b is not a and b.ders == a.ders and katli[id(a)] in katli[id(b)]
                       and len(katli[id(b)]) > len(katli[id(a)]) for b in kalan)
        if not kapsayan:
            sonuc.append(a)
    return sonuc


def adaylar(veri: dict, bugun: date, ek_metinleri: dict[str, tuple[str, date | None]] | None = None,
            odev_ilk_gorulme: dict[str, str] | None = None, en_eski_gun: int | None = None) -> list[Aday]:
    """Every pre-filtered candidate, newest first. No age limit by default: an exam announced
    weeks ahead must keep its (cached) finding until the exam is past — the age limit bounds
    only new model calls, in `SinavCikarici.cikar`. `en_eski_gun` exists for ad-hoc reads."""
    yil_basi = okul_yili(bugun)[0]
    bas_yil = yil_basi.year
    ham: list[Aday] = []
    haftalar = veri.get("ders_icerikleri_haftalar") or {}
    if isinstance(haftalar, dict):
        for etiket, bolum in haftalar.items():
            ham += _ders_parcalari(bolum, etiket, hafta_etiketi_araligi(etiket, bas_yil), "ders_icerikleri_haftalar")
    ham += _ders_parcalari(veri.get("ders_icerikleri"), None, None, "ders_icerikleri")
    ham += _odevler(veri, odev_ilk_gorulme or {}, yil_basi)
    ham += _duyurular(veri)
    for ek_id, (metin, ilk) in (ek_metinleri or {}).items():
        ham.append(Aday(metin, None, ilk, "ek", [{"bolum": "ek", "id": ek_id}]))

    sinir = bugun - timedelta(days=en_eski_gun) if en_eski_gun is not None else None
    suzulmus = [a for a in ham if on_suzgec(a.metin) and (sinir is None or a.yayin is None or a.yayin >= sinir)]
    sonuc = _birlestir(suzulmus)
    return sorted(sonuc, key=lambda a: a.yayin or bugun, reverse=True)


def _json(yol: Path) -> Any:
    try:
        return json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def kaynak_verisi(kok: Path) -> tuple[dict[str, tuple[str, date | None]], dict[str, str]]:
    ekler: dict[str, tuple[str, date | None]] = {}
    dizin = _json(kok / "output/portal_ekleri.json")
    kayitlar = (dizin or {}).get("ekler") if isinstance(dizin, dict) else None
    for ek_id, kayit in (kayitlar or {}).items():
        # The key becomes a file name: only portal_ekleri's own id shape is read (no traversal).
        if not isinstance(kayit, dict) or not KIMLIK_DESENI.fullmatch(str(ek_id)):
            continue
        yol = kok / "content/portal-ekleri" / f"{ek_id}.txt"
        try:
            with open(yol, encoding="utf-8") as f:
                metin = f.read(EK_KARAKTER_SINIRI)
        except (OSError, UnicodeDecodeError):
            continue
        if metin.strip():
            ekler[ek_id] = (metin, _gun(kayit.get("first_seen")))
    ilk = _json(kok / "output/homework_first_seen.json")
    return ekler, (ilk if isinstance(ilk, dict) else {})
