"""Sınav tarihini kaynak metinden, yayın bağlamıyla çözer (saf: dosya, ağ, saat yok).

Öğretmen tarihi nadiren yılıyla yazar ("15 EKİM PERŞEMBE", "15.10") ve sık sık
göreli konuşur ("haftaya", "Next week", "Cuma günü"). Yıl okul yılından, göreli
ifade yayın tarihinden gelir. Çözülemeyen ifade tarih uydurmaz: gun ve hafta
None kalır. Metindeki açık tarihlerin hepsi yayından önce ya da okul yılı
dışındaysa (başka çözüm de yoksa) `gecersiz` True olur — o metin geçmiş bir
sınavı anlatıyordur (spec §5 kural 4)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from src.assistant_core import turkce_kucult_katla

_AYLAR = {
    "ocak": 1, "oca": 1, "subat": 2, "sub": 2, "mart": 3, "mar": 3, "nisan": 4, "nis": 4,
    "mayis": 5, "may": 5, "haziran": 6, "haz": 6, "temmuz": 7, "tem": 7, "agustos": 8, "agu": 8,
    "eylul": 9, "eyl": 9, "ekim": 10, "eki": 10, "kasim": 11, "kas": 11, "aralik": 12, "ara": 12,
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "april": 4, "apr": 4,
    "june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sept": 9,
    "sep": 9, "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_GUNLER = {
    "pazartesi": 0, "sali": 1, "carsamba": 2, "persembe": 3, "cumartesi": 5, "cuma": 4, "pazar": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}


def _alternatif(sozluk: dict[str, int]) -> str:
    return "|".join(sorted(sozluk, key=len, reverse=True))


# Kısa biçimler ("ara", "may", "eki"...) gündelik sözcükle çakışır; yalnızca nokta, yıl ya da
# gün adı eşlik ederse ay sayılır. Hafta etiketleri (_ETIKET) kısaltmaları olduğu gibi kabul eder.
_KISA_AYLAR = frozenset({
    "oca", "sub", "mar", "nis", "may", "haz", "tem", "agu", "eyl", "eki", "kas", "ara",
    "jan", "feb", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
})
_AY = _alternatif(_AYLAR)
_GUN = _alternatif(_GUNLER)
_GUN_AY = re.compile(rf"\b(\d{{1,2}})\s+({_AY})\b(\.)?(?:\s+(\d{{4}}))?")
_AY_GUN = re.compile(rf"\b({_AY})\b(\.)?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}}))?")
# Kod/ondalık zincirinin (FB.7.1.4, 2.5, 3/4,5) parçası olan sayılar tarih sayılmaz.
_SAYISAL = re.compile(r"(?<![\w./])(\d{1,2})[./](\d{1,2})(?:[./](\d{4}|\d{2}))?(?!\w)(?![./,]\d)")
# Kısa gün adları ("15 Eki Per") yalnız kısa ay korumasında gün adı sayılır; tek başına tarih çözmez.
# "sal", "çar" ve "paz" gündelik sözcüklerle çakıştığı için ("15 Mar sal") korumayı açmaz.
_KISA_GUN = "pzt|per|cum|cmt"
_GUN_ADI_SONRA = re.compile(rf"\s*(?:{_GUN}|{_KISA_GUN})\b")
# Yılsız d.m / d/m için tarih ipucu: kesme ekli ('de/'da/'te/'ta), "tarih", "günü" ya da gün adı.
_TARIH_IPUCU = re.compile(rf"\s*(?:['\u2019](?:de|da|te|ta)|tarih|gunu\b|(?:{_GUN})\b)")
_GUN_ADI = re.compile(rf"\b({_GUN})\b")
# "pazar" is also the market ("pazar araştırması"): alone it is a weekday only with a day suffix.
_PAZAR_EKI = re.compile(r"(?:\s+gunu\b|['\u2019](?:dan|da|a|i)\b)")
_GELECEK_HAFTA = re.compile(r"\b(haftaya|gelecek hafta|onumuzdeki hafta|next week)\b")
_BU_HAFTA = re.compile(r"\b(bu hafta|this week)\b")
# "(bu) hafta sonu", "hafta sonunda": the weekend of the post's own week.
_HAFTA_SONU = re.compile(r"\bhafta ?sonu\w*\b")
_YARIN = re.compile(r"\b(yarin|tomorrow)\b")
_BUGUN = re.compile(r"\b(bugun|today)\b")
_IMZA = re.compile(r"\|\s*(\d{2})\.(\d{2})\.(\d{4})")
_ETIKET = re.compile(rf"(\d{{1,2}})\s+({_AY})\.?\s*-\s*(\d{{1,2}})\s+({_AY})\.?")


# Stored dates are read strictly: Python's fromisoformat also takes "20261023" and "2026-W43-5",
# which no TEDY writer produces — such a value is an unreadable date, never a day.
GUN_DESENI = re.compile(r"\d{4}-\d{2}-\d{2}")
TARIH_SAAT_DESENI = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?)?")


_ISTANBUL = ZoneInfo("Europe/Istanbul")
_OFSET = re.compile(r"T.*[+-]\d{2}:\d{2}$")


def yerel_saat(deger: object) -> str:
    """A takvim time as naive Istanbul wall clock — the rule of dashboard_api._portal_yerel, kept
    here so the sync step need not import the Flask app for it (a test holds the two equal):
    "Z" is the old UTC-browser artefact (the digits are already local) and is dropped; a real
    offset is converted to Istanbul time; anything else is returned as it is."""
    s = str(deger or "").strip()
    if s.endswith("Z"):
        return s[:-1]
    if _OFSET.search(s):
        try:
            return datetime.fromisoformat(s).astimezone(_ISTANBUL).replace(tzinfo=None).isoformat()
        except ValueError:
            return s
    return s


def kati_gun(deger: object) -> date | None:
    """Exactly YYYY-MM-DD as a date, else None."""
    if not isinstance(deger, str) or not GUN_DESENI.fullmatch(deger):
        return None
    try:
        return date.fromisoformat(deger)
    except ValueError:
        return None


def kati_tarih_saat(deger: object) -> datetime | None:
    """Exactly YYYY-MM-DD or YYYY-MM-DDTHH:MM[:SS[.ffffff]] as a naive datetime, else None."""
    if not isinstance(deger, str) or not TARIH_SAAT_DESENI.fullmatch(deger):
        return None
    try:
        return datetime.fromisoformat(deger)
    except ValueError:
        return None


@dataclass(frozen=True)
class TarihCozumu:
    gun: date | None
    hafta: date | None
    gecersiz: bool


def katla(metin: str) -> str:
    return " ".join(turkce_kucult_katla(str(metin or "")).split())


def okul_yili(bugun: date) -> tuple[date, date]:
    y = bugun.year if bugun.month >= 8 else bugun.year - 1
    return date(y, 9, 1), date(y + 1, 7, 15)


def pazartesi(gun: date) -> date:
    return gun - timedelta(days=gun.weekday())


def _yil(ay: int, baslangic_yili: int) -> int:
    return baslangic_yili if ay >= 8 else baslangic_yili + 1


def _gun_kur(y: int, a: int, g: int) -> date | None:
    try:
        return date(y, a, g)
    except ValueError:
        return None


def hafta_etiketi_araligi(etiket: str, baslangic_yili: int) -> tuple[date, date] | None:
    m = _ETIKET.search(katla(etiket))
    if not m:
        return None
    a1, a2 = _AYLAR[m.group(2)], _AYLAR[m.group(4)]
    bas = _gun_kur(_yil(a1, baslangic_yili), a1, int(m.group(1)))
    son = _gun_kur(_yil(a2, baslangic_yili), a2, int(m.group(3)))
    return (bas, son) if bas and son else None


def yayin_tarihi(metin: str) -> date | None:
    m = _IMZA.search(str(metin or ""))
    return _gun_kur(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def _acik_tarihler(k: str, baslangic_yili: int) -> list[tuple[int, date]]:
    """Katlanmış metindeki her açık tarih, konumuyla birlikte."""
    bulunan: list[tuple[int, date]] = []

    def yil_sec(ham: str | None, ay: int) -> int:
        if ham:
            y = int(ham)
            return y + 2000 if y < 100 else y
        return _yil(ay, baslangic_yili)

    for m in _GUN_AY.finditer(k):
        if (m.group(2) in _KISA_AYLAR and not m.group(3) and not m.group(4)
                and not _GUN_ADI_SONRA.match(k, m.end())):
            continue
        ay = _AYLAR[m.group(2)]
        g = _gun_kur(yil_sec(m.group(4), ay), ay, int(m.group(1)))
        if g:
            bulunan.append((m.start(), g))
    for m in _AY_GUN.finditer(k):
        if (m.group(1) in _KISA_AYLAR and not m.group(2) and not m.group(4)
                and not _GUN_ADI_SONRA.match(k, m.end())):
            continue
        ay = _AYLAR[m.group(1)]
        g = _gun_kur(yil_sec(m.group(4), ay), ay, int(m.group(3)))
        if g:
            bulunan.append((m.start(), g))
    for m in _SAYISAL.finditer(k):
        gun, ay = int(m.group(1)), int(m.group(2))
        if not m.group(3) and not _TARIH_IPUCU.match(k, m.end()):
            continue
        if 1 <= ay <= 12:
            g = _gun_kur(yil_sec(m.group(3), ay), ay, gun)
            if g:
                bulunan.append((m.start(), g))
    return sorted(bulunan)


def _gun_adi(k: str) -> re.Match | None:
    for m in _GUN_ADI.finditer(k):
        if m.group(1) != "pazar" or _PAZAR_EKI.match(k, m.end()):
            return m
    return None


def bu_haftanin_pazartesisi(yayin: date) -> date:
    """"Bu hafta" in a post: its own week on a weekday, the coming week at the weekend (a Sunday
    post's "bu hafta Cuma" is five days ahead, never two days back)."""
    return pazartesi(yayin) + timedelta(days=7 if yayin.weekday() >= 5 else 0)


def tarih_coz(metin: str, yayin: date, okul_araligi: tuple[date, date], goreli: bool = True) -> TarihCozumu:
    """`goreli=False` when the text's publication date is unknown: only explicit dates count
    ("Cuma günü", "yarın", "haftaya" are relative to a day we do not know — resolving them
    against today would move the exam to a new date every week). `yayin` is then today."""
    k = katla(metin)
    bas, son = okul_araligi
    acik = _acik_tarihler(k, bas.year)
    for _, g in acik:
        if bas <= g <= son and g >= yayin:
            return TarihCozumu(g, None, False)
    if not goreli:
        return TarihCozumu(None, None, bool(acik))

    gun_adi = _gun_adi(k)
    if _YARIN.search(k):
        return TarihCozumu(yayin + timedelta(days=1), None, False)
    if _BUGUN.search(k):
        return TarihCozumu(yayin, None, False)
    if _GELECEK_HAFTA.search(k):
        haftabasi = pazartesi(yayin) + timedelta(days=7)
        if gun_adi:
            return TarihCozumu(haftabasi + timedelta(days=_GUNLER[gun_adi.group(1)]), None, False)
        return TarihCozumu(None, haftabasi, False)
    # Açık tarih var ama hiçbiri geçerli değilse (geçmiş sınav anlatısı) yalnız gün adı
    # ileriye çözülmez: "15 Ekim Perşembe günü yapılan KTT" bir sonraki Perşembe'yi göstermez.
    if _HAFTA_SONU.search(k) and not acik:
        # Never shifted to the next week like "bu hafta" at the weekend: a Saturday post's
        # "bu hafta sonu Pazar" is tomorrow. With no day name it is the post's own week.
        if gun_adi:
            return TarihCozumu(pazartesi(yayin) + timedelta(days=_GUNLER[gun_adi.group(1)]), None, False)
        return TarihCozumu(None, pazartesi(yayin), False)
    if gun_adi and not acik and _BU_HAFTA.search(k):
        # "bu hafta Cuma" on a Friday is that Friday, not the next one.
        return TarihCozumu(bu_haftanin_pazartesisi(yayin) + timedelta(days=_GUNLER[gun_adi.group(1)]), None, False)
    if gun_adi and not acik:
        fark = (_GUNLER[gun_adi.group(1)] - yayin.weekday()) % 7 or 7
        return TarihCozumu(yayin + timedelta(days=fark), None, False)
    if _BU_HAFTA.search(k):
        return TarihCozumu(None, bu_haftanin_pazartesisi(yayin), False)
    return TarihCozumu(None, None, bool(acik))
