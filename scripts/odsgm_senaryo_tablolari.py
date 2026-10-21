"""MEB ÖDSGM konu-soru dağılım tablolarını src/sinav_senaryolari.json'a çevirir (spec 2026-10-19 §2).

Elle koşulur; senkron ağa çıkmaz. Her ders bir LibreOffice HTML dışa aktarımıdır (meb.ai kısa
bağlantısı). Bu makine MEB'e TLS'te takıldığı için (spec §1) sayfalar Jina Reader'dan ham HTML
olarak alınır; --dosya ile tarayıcıdan kaydedilmiş HTML okunur.

    .venv/bin/python scripts/odsgm_senaryo_tablolari.py
    .venv/bin/python scripts/odsgm_senaryo_tablolari.py --dosya Türkçe=/tmp/tr.html --meb-guncelleme 2026-09-10T17:27
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

CIKTI = KOK / "src" / "sinav_senaryolari.json"
SAYFA = "https://odsgm.meb.gov.tr/www/1donem-konu-soru-dagilim-tablolari-2026-2027/icerik/1724"
SAYFA_BASLIGI = "1. Dönem Konu Soru Dağılım Tabloları (2026-2027)"
OGRETIM_YILI = "2026-2027"
DONEM = 1
OKUYUCU = "https://r.jina.ai/"
DERS_ADRESLERI = {
    "Din Kültürü": "https://meb.ai/ankmeb1",
    "Fen Bilimleri": "https://meb.ai/ankmeb2",
    "Matematik": "https://meb.ai/ankmeb3",
    "Türkçe": "https://meb.ai/ankmeb4",
    "Sosyal Bilgiler": "https://meb.ai/ankmeb5",
    "İngilizce": "https://meb.ai/ankmeb6",
}
# Tablo başlığındaki ad → TEDY'nin kanonik ders adı (course_names.normalize_course ile aynı).
_BASLIK_DERSLERI = (("DİN KÜLTÜRÜ", "Din Kültürü"), ("FEN BİLİMLERİ", "Fen Bilimleri"),
                    ("MATEMATİK", "Matematik"), ("TÜRKÇE", "Türkçe"),
                    ("SOSYAL BİLGİLER", "Sosyal Bilgiler"), ("İNGİLİZCE", "İngilizce"))
_CIKTI_BASLIKLARI = ("Öğrenme Çıktıları", "Kazanımlar", "Kazanım")
# Çıktı kodunun gerçek tablolarda ölçülen iki biçimi (2026-10-20):
#  - "DKAB.7.1.1." (ön ek.sınıf.sıra); Sosyal'in bir satırında nokta yerine boşluk var ("SB 7.1.1.", kardeşleri "SB.7.1.2."):
#    noktalı biçime çevrilir.
#  - "E7.1.R1." (İngilizce: sınıf rakamı harfe bitişik, son parça beceri harfi + sıra): olduğu gibi tutulur.
_KOD = re.compile(r"^([A-ZÇĞİÖŞÜ]{1,5}(?:\.[A-ZÇĞİÖŞÜ]{1,5})*)[. ](\d{1,2})\.(\d{1,2}(?:\.\d{1,2})?)\.?\s+(\S.*)$")
_KOD_BITISIK = re.compile(r"^([A-ZÇĞİÖŞÜ]{1,5}(\d{1,2})\.\d{1,2}\.[A-ZÇĞİÖŞÜ]\d{1,2})\.?\s+(\S.*)$")
_SINAV = re.compile(r"Dönem\s*(\d)\s*\.\s*Ortak")
_SENARYO = re.compile(r"^Senaryo\s*(\d{1,2})$")
_GUNCELLEME = re.compile(r"Güncelleme\s*:\s*(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})")


class YapiHatasi(ValueError):
    """Tablo beklenen yapıda değil; dosya yazılmaz."""


# Hücre içinde satır/paragraf ayıran etiketler: metinleri birbirine yapıştırmasın ("yansıtabilmea) Bölme").
# Satır içi etiketler (span, b, font) kelimeyi bölebilir; onlara boşluk eklenmez.
_BLOK_ETIKETLERI = frozenset({"p", "div", "li", "br"})


class _Tablolar(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tablolar: list[list[list[tuple[str, int, int]]]] = []
        self._derinlik = 0
        self._satir: list[tuple[str, int, int]] | None = None
        self._hucre: list | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._derinlik += 1
            if self._derinlik == 1:
                self.tablolar.append([])
        elif tag == "tr" and self._derinlik == 1:
            self._satir = []
            self.tablolar[-1].append(self._satir)
        elif tag in ("td", "th") and self._satir is not None:
            self._hucre = ["", int(a.get("colspan") or 1), int(a.get("rowspan") or 1)]
        elif tag in _BLOK_ETIKETLERI and self._hucre is not None:
            self._hucre[0] += " "

    def handle_endtag(self, tag):
        if tag in _BLOK_ETIKETLERI and self._hucre is not None:
            self._hucre[0] += " "
        if tag == "table":
            self._derinlik -= 1
        elif tag in ("td", "th") and self._hucre is not None and self._satir is not None:
            metin, cs, rs = self._hucre
            # NFC: Türkçe tablosunda 9 hücre "ü"yü u + birleşik ünlem noktası olarak yazıyor (ölçüldü 2026-10-20)
            self._satir.append((unicodedata.normalize("NFC", " ".join(metin.split())), cs, rs))
            self._hucre = None

    def handle_data(self, data):
        if self._hucre is not None:
            self._hucre[0] += data


def _izgara(satirlar: list[list[tuple[str, int, int]]]) -> list[list[str]]:
    izgara: list[list[str]] = []
    bekleyen: dict[tuple[int, int], str] = {}
    for r, satir in enumerate(satirlar):
        cikti: list[str] = []
        c = i = 0
        while True:
            if (r, c) in bekleyen:
                cikti.append(bekleyen.pop((r, c)))
                c += 1
            elif i < len(satir):
                metin, cs, rs = satir[i]
                i += 1
                for dc in range(cs):
                    cikti.append(metin)
                    for dr in range(1, rs):
                        bekleyen[(r + dr, c + dc)] = metin
                c += cs
            elif any(k[0] == r for k in bekleyen):
                cikti.append("")
                c += 1
            else:
                break
        izgara.append(cikti)
    return izgara


def tablolar(html: str) -> list[list[list[str]]]:
    p = _Tablolar()
    p.feed(html)
    return [_izgara(t) for t in p.tablolar]


def _ders(baslik: str) -> str:
    for parca, ad in _BASLIK_DERSLERI:
        if parca in baslik:
            return ad
    raise YapiHatasi(f"tablo başlığındaki ders tanınmadı: {baslik!r}")


def _kod_oku(hucre: str) -> tuple[str, str, str] | None:
    """Çıktı hücresi → (kod, kodun sınıfı, metin); kod biçimi tanınmazsa None."""
    m = _KOD.match(hucre)
    if m:
        return f"{m.group(1)}.{m.group(2)}.{m.group(3)}", m.group(2), m.group(4).strip()
    m = _KOD_BITISIK.match(hucre)
    if m:
        return m.group(1), m.group(2), m.group(3).strip()
    return None


def ders_sayfasi(izgaralar: list[list[list[str]]], sinif: int) -> tuple[str, dict]:
    isaret = re.compile(rf"(?<!\d){sinif}\.\s*SINIF")   # "7. SINIF" (Din Kültürü ve Matematik'te "7.SINIF")
    izgara = next((g for g in izgaralar if any(isaret.search(h) for r in g[:3] for h in r)), None)
    if izgara is None:
        raise YapiHatasi(f"{sinif}. sınıf tablosu yok")
    ders = _ders(next(h for r in izgara[:3] for h in r if isaret.search(h)))
    h = next((i for i, r in enumerate(izgara) if any(x in _CIKTI_BASLIKLARI for x in r)), None)
    if h is None or h + 1 >= len(izgara):
        raise YapiHatasi("başlık satırı (Öğrenme Çıktıları) bulunamadı")
    ust, alt = izgara[h], izgara[h + 1]
    cikti_s = next(i for i, x in enumerate(ust) if x in _CIKTI_BASLIKLARI)
    alan_s = next((i for i, x in enumerate(ust) if x.startswith("Alan Becerileri") or x == "Öğrenme Alanı"), None)
    konu_s = next((i for i, x in enumerate(ust) if x.startswith("Konu")), None)

    sutunlar: dict[int, tuple[str, str | None]] = {}   # sütun → (sınav no, senaryo no | None=ülke geneli)
    ulke_notu: dict[str, str] = {}
    for c in range(cikti_s + 1, len(ust)):
        m = _SINAV.search(ust[c])
        if not m:
            continue
        no = m.group(1)
        alt_metin = alt[c] if c < len(alt) else ""
        s = _SENARYO.match(alt_metin)
        if s:
            sutunlar[c] = (no, s.group(1))
        elif "Ülke Geneli" in alt_metin:
            sutunlar[c] = (no, None)
            ulke_notu[no] = alt_metin[:200]
        else:
            raise YapiHatasi(f"{ust[c]!r} altında senaryo başlığı yok: {alt_metin!r}")
    if not sutunlar:
        raise YapiHatasi("başlık satırında ortak yazılı sütunu yok")

    ciktilar: list[dict] = []
    senaryolar: dict[str, dict[str, dict[str, int]]] = {}
    for r in izgara[h + 2:]:
        if cikti_s >= len(r):
            continue
        okunan = _kod_oku(r[cikti_s])
        if okunan is None:
            # Kodsuz satır: bölüm/ünite başlığı (senaryo hücreleri boş) ya da TOPLAM altbilgisi atlanır;
            # senaryo hücresi dolu başka bir kodsuz satır, okunamayan bir çıktıdır ve sayıları sessizce düşerdi.
            dolu = any(c < len(r) and r[c].strip() for c, (_, sen) in sutunlar.items() if sen is not None)
            if dolu and not any("TOPLAM" in x for x in r[:cikti_s + 1]):
                raise YapiHatasi(f"kodu okunamayan satır: {r[cikti_s]!r}")
            continue
        kod, kod_sinifi, metin = okunan
        if kod_sinifi != str(sinif):
            raise YapiHatasi(f"{kod}: {sinif}. sınıf kodu değil")
        if any(c["kod"] == kod for c in ciktilar):
            raise YapiHatasi(f"{kod} iki kez geçiyor")
        ciktilar.append({"kod": kod, "metin": metin,
                         "alan": (r[alan_s] or None) if alan_s is not None else None,
                         "konu": (r[konu_s] or None) if konu_s is not None else None})
        for c, (no, sen) in sutunlar.items():
            if sen is None:
                continue
            hucre = r[c].strip() if c < len(r) else ""
            if not hucre:
                continue
            if not hucre.isdigit():
                raise YapiHatasi(f"{kod} · {no}. yazılı Senaryo {sen}: sayı değil: {hucre!r}")
            senaryolar.setdefault(no, {}).setdefault(sen, {})
            if int(hucre) > 0:
                senaryolar[no][sen][kod] = int(hucre)
    if not ciktilar:
        raise YapiHatasi("hiç öğrenme çıktısı okunamadı")

    sinavlar: dict[str, dict] = {}
    for no in sorted({n for n, _ in sutunlar.values()}):
        if no in ulke_notu:
            sinavlar[no] = {"tur": "ulke_geneli", "not": ulke_notu[no]}
            continue
        adlar = sorted({s for n, s in sutunlar.values() if n == no and s}, key=int)
        sen = {s: senaryolar.get(no, {}).get(s, {}) for s in adlar}
        for s, dagilim in sen.items():
            if sum(dagilim.values()) < 1:
                raise YapiHatasi(f"{no}. yazılı Senaryo {s}: toplam soru 0")
        sinavlar[no] = {"tur": "senaryolu", "senaryolar": sen}
    return ders, {"ciktilar": ciktilar, "sinavlar": sinavlar}


def _getir(adres: str) -> str:
    import requests

    yanit = requests.get(OKUYUCU + adres, headers={"X-Return-Format": "html"}, timeout=90)
    yanit.raise_for_status()
    yanit.encoding = "utf-8"
    return yanit.text


def main(argv: list[str] | None = None) -> int:
    from src.json_utils import atomic_json_dump

    p = argparse.ArgumentParser(description="ÖDSGM senaryo tablolarını src/sinav_senaryolari.json'a çevirir")
    p.add_argument("--sinif", type=int, default=7)
    p.add_argument("--dosya", action="append", default=[], help="DERS=yol (tarayıcıdan kaydedilmiş HTML)")
    p.add_argument("--meb-guncelleme", help="YYYY-MM-DDTHH:MM (verilmezse ÖDSGM sayfasından okunur)")
    p.add_argument("--cikti", type=Path, default=CIKTI)
    a = p.parse_args(argv)
    dosyalar = dict(x.split("=", 1) for x in a.dosya)

    guncelleme = a.meb_guncelleme
    if not guncelleme:
        m = _GUNCELLEME.search(_getir(SAYFA))
        if not m:
            print("hata: ÖDSGM sayfasında güncelleme tarihi bulunamadı; --meb-guncelleme ver", file=sys.stderr)
            return 1
        g, ay, y, sa, dk = m.groups()
        guncelleme = f"{y}-{ay}-{g}T{sa}:{dk}"

    dersler: dict[str, dict] = {}
    for ad, adres in DERS_ADRESLERI.items():
        html = Path(dosyalar[ad]).read_text(encoding="utf-8") if ad in dosyalar else _getir(adres)
        try:
            okunan, sayfa = ders_sayfasi(tablolar(html), a.sinif)
        except YapiHatasi as hata:
            print(f"hata: {ad}: {hata} — dosya yazılmadı", file=sys.stderr)
            return 1
        if okunan != ad:
            print(f"hata: {adres} {okunan} tablosu çıktı, {ad} bekleniyordu — dosya yazılmadı", file=sys.stderr)
            return 1
        dersler[ad] = {"adres": adres, "sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(), **sayfa}

    atomic_json_dump({"surum": 1,
                      "kaynak": {"sayfa": SAYFA, "baslik": SAYFA_BASLIGI, "meb_guncelleme": guncelleme,
                                 "alindi": date.today().isoformat(), "ogretim_yili": OGRETIM_YILI,
                                 "donem": DONEM, "sinif": a.sinif},
                      "dersler": dersler}, str(a.cikti))
    for ad, d in dersler.items():
        ozet = ", ".join(f"{no}. yazılı: " + (f"{len(s['senaryolar'])} senaryo" if s["tur"] == "senaryolu" else "ülke geneli")
                         for no, s in d["sinavlar"].items())
        print(f"{ad}: {len(d['ciktilar'])} çıktı · {ozet}")
    print(f"yazıldı: {a.cikti}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
