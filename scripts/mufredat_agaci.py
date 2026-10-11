"""7. sınıf müfredat ağacını üretir: ders → ünite → ders kitabı alt başlığı.

Çıktı `src/mufredat_agaci.json`; elle düzenlenmez. Tek kaynak sabitlenmiş salt-okunur
müfredat veritabanıdır (spec §0). `output/modules/` altına yazılmaz — orada tek yazar ted-mcp.

Kullanım:
    .venv/bin/python scripts/mufredat_agaci.py tumu --sinif 7
"""
from __future__ import annotations

import collections
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

URI = "file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1"

# Program PDF'lerinin metin katmanındaki harf aralığı bozulmaları; skill_unite_haritasi.py'daki
# OCR_DUZELTME ile aynı gerekçe, ders kitabı başlıklarında ölçülen biçimler.
OCR_DUZELTME = {"SOSY AL": "SOSYAL", "DÜNY A": "DÜNYA", "YAŞAY AN": "YAŞAYAN",
                "KÜL TÜRÜ": "KÜLTÜRÜ", "ETK İSİ": "ETKİSİ", "ÜLKEM İZİN": "ÜLKEMİZİN",
                "DEVLETİ ’NİN": "DEVLETİ’NİN"}
# Başlık düzeninde küçük kalan bağlaçlar (Türkçe yazım).
KUCUK_KALAN = {"ve", "ile", "veya", "ya", "da", "de", "ki"}
NOKTA_ONCULU = re.compile(r"^(?P<ad>.*?[^\s.])\s*\.{4,}\s*(?P<s>\d{1,3})$")
KAYMA_UYUM_ESIGI = 0.80


def nokta_onculu(satir: str) -> tuple[str, int] | None:
    """"Ad ....... 96" satırını (ad, 96) yapar; eşleşmezse None."""
    eslesme = NOKTA_ONCULU.match(" ".join((satir or "").split()))
    return (eslesme.group("ad"), int(eslesme.group("s"))) if eslesme else None


def harf_katla(metin: str) -> str:
    """Karşılaştırma için harf dizisi: Türkçe İ/I önce çevrilir, sonra küçültülüp aksan atılır."""
    metin = (metin or "").replace("İ", "i").replace("I", "ı").replace("ı", "i").lower()
    metin = unicodedata.normalize("NFKD", metin)
    metin = "".join(ch for ch in metin if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", metin)


def _sozcuk_duzeni(sozcuk: str) -> str:
    """Türkçe'ye duyarlı tek sözcük: 'I' → 'ı', 'İ' → 'i'; str.title() bunu bozar."""
    if not sozcuk:
        return sozcuk
    bas = sozcuk[0].replace("i", "İ")
    govde = sozcuk[1:].replace("I", "ı").replace("İ", "i").lower()
    return (bas if bas.isupper() or not bas.isalpha() else bas.upper()) + govde


def baslik_duzeni(metin: str) -> str:
    """Kitaptaki büyük harfli başlığı okunabilir başlık düzenine çevirir (spec §2.3)."""
    metin = " ".join((metin or "").split())
    for yanlis, dogru in OCR_DUZELTME.items():
        metin = metin.replace(yanlis, dogru)
    cikti = []
    for sira, sozcuk in enumerate(metin.split(" ")):
        duzenli = _sozcuk_duzeni(sozcuk)
        if sira and duzenli.lower() in KUCUK_KALAN:
            duzenli = duzenli.lower()
        cikti.append(duzenli)
    return " ".join(cikti)


def konu_slug(ad: str) -> str:
    """module_store.SLUG_RE alfabesinde kimlik gövdesi."""
    katlanmis = (ad or "").replace("İ", "i").replace("I", "ı").replace("ı", "i").lower()
    katlanmis = unicodedata.normalize("NFKD", katlanmis)
    katlanmis = "".join(ch for ch in katlanmis if not unicodedata.combining(ch))
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", katlanmis)).strip("-")


def kayma_bul(adaylar: list[tuple[int, int]]) -> tuple[int | None, str]:
    """(basılı, gövdede bulunan) çiftlerinden basılı→PDF kaymasının modunu türetir.

    Kayma uydurulmaz: uyum oranı KAYMA_UYUM_ESIGI'nin altındaysa kayma None döner ve
    çağıran o kitabın bütün konularını `sayfa_kaynak: "yok"` yazar (spec §2.2).
    """
    if not adaylar:
        return None, "0/0"
    sayac = collections.Counter(bulunan - basili for basili, bulunan in adaylar)
    kayma, adet = sayac.most_common(1)[0]
    uyum = f"{adet}/{len(adaylar)}"
    return (kayma if adet / len(adaylar) >= KAYMA_UYUM_ESIGI else None), uyum
