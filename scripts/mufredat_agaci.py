"""7. sınıf müfredat ağacını üretir: ders → ünite → ders kitabı alt başlığı.

Çıktı `src/mufredat_agaci.json`; elle düzenlenmez. Tek kaynak sabitlenmiş salt-okunur
müfredat veritabanıdır (spec §0). `output/modules/` altına yazılmaz — orada tek yazar ted-mcp.

Kullanım:
    .venv/bin/python scripts/mufredat_agaci.py tumu --sinif 7
"""
from __future__ import annotations

import collections
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import NamedTuple

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


# ── Veritabanı katmanı ──────────────────────────────────────────────────────


class Ders(NamedTuple):
    ad: str
    subject_slug: str
    program_id: int
    sayfa_araligi: tuple[int, int]
    unite_deseni: str
    kazanim_deseni: str
    kitaplar: tuple[int, ...]


# Program kimlikleri, sayfa aralıkları ve desenler scripts/skill_unite_haritasi.py'ın DERSLER
# tablosundan birebir alındı (orada "ölçüldü 2026-09-27"); yeniden ölçülmez. Kitap kimlikleri
# 2026-10-11'de ölçüldü (spec §0).
DERSLER = {
    "matematik": Ders("Matematik", "ortaokul-matematik-dersi", 24, (115, 172),
                      r"^\s*(\d+)\.\s*TEMA:\s*(.+)$", r"^MAT\.7\.(\d+)\.(\d+)$", (346, 506)),
    "fen": Ders("Fen Bilimleri", "fen-bilimleri-dersi", 54, (146, 183),
                r"^\s*(\d+)\.\s*ÜNİTE:\s*(.+)$", r"^FB\.7\.(\d+)\.(\d+)$", (439, 473)),
    "sosyal": Ders("Sosyal Bilgiler", "sosyal-bilgiler-dersi", 100, (93, 122),
                   r"^\s*(\d+)\.\s*ÖĞRENME ALANI:\s*(.+)$", r"^SB\.7\.(\d+)\.(\d+)$", (491, 361)),
    "turkce": Ders("Türkçe", "ortaokul-turkce-dersi", 51, (126, 161),
                   r"^\s*(\d+)\.\s*TEMA:\s*(.+)$", r"^(T\.[DOKY]|DYS\.(?:DO|KY))\.7\.(\d+)$",
                   (460, 340)),
}
ICINDEKILER_ARAMA_SINIRI = 14


def baglan() -> sqlite3.Connection:
    return sqlite3.connect(URI, uri=True)


def _program_sayfalari(baglanti: sqlite3.Connection, ders: Ders) -> list[tuple[int, str]]:
    ilk, son = ders.sayfa_araligi
    return list(baglanti.execute(
        "select page_no, text from document_page where document_id=? and page_no between ? and ?"
        " order by page_no", (ders.program_id, ilk, son)))


def program_uniteleri(baglanti: sqlite3.Connection, ders: Ders) -> list[dict]:
    """Programın 7. sınıf sayfalarındaki ünite/tema başlıkları, görüldükleri sayfayla."""
    desen = re.compile(ders.unite_deseni)
    gorulen: dict[int, dict] = {}
    for sayfa_no, metin in _program_sayfalari(baglanti, ders):
        for satir in (metin or "").splitlines():
            eslesme = desen.match(" ".join(satir.split()))
            if not eslesme:
                continue
            no = int(eslesme.group(1))
            if no not in gorulen:
                gorulen[no] = {"no": no, "ad": baslik_duzeni(eslesme.group(2).strip(" :")),
                               "program_sayfa": sayfa_no}
    return [gorulen[no] for no in sorted(gorulen)]


def program_kazanimlari(baglanti: sqlite3.Connection, ders: Ders) -> list[dict]:
    """7. sınıf kazanımları. `unite_no`, kodun ortasındaki sayıdır; Türkçe'de None."""
    desen = re.compile(ders.kazanim_deseni)
    cikti: dict[str, dict] = {}
    satirlar = baglanti.execute(
        "select lo.code, lo.text from learning_outcome lo join subject s on s.id = lo.subject_id"
        " where s.slug = ? and lo.grade_label like '%7%' and lo.fragment_type = 'outcome'",
        (ders.subject_slug,))
    for kod, metin in satirlar:
        eslesme = desen.match(kod or "")
        if not eslesme or kod in cikti:
            continue
        gruplar = eslesme.groups()
        # Türkçe deseni beceri alanı + sıra verir; ünite numarası taşımaz.
        unite_no = int(gruplar[0]) if len(gruplar) == 2 and gruplar[0].isdigit() else None
        cikti[kod] = {"kod": kod, "unite_no": unite_no, "metin": " ".join((metin or "").split())}
    return [cikti[kod] for kod in sorted(cikti)]


def kitap_sayfalari(baglanti: sqlite3.Connection, document_id: int) -> dict[int, str]:
    return {no: (metin or "") for no, metin in baglanti.execute(
        "select page_no, text from document_page where document_id=?", (document_id,))}


def icindekiler_satirlari(baglanti: sqlite3.Connection, document_id: int) -> list[tuple[str, int]]:
    """Kitabın ilk sayfalarındaki nokta öncüllü içindekiler satırları, görüldükleri sırada."""
    cikti: list[tuple[str, int]] = []
    for _, metin in baglanti.execute(
            "select page_no, text from document_page where document_id=? and page_no<=?"
            " order by page_no", (document_id, ICINDEKILER_ARAMA_SINIRI)):
        for satir in (metin or "").splitlines():
            ayristi = nokta_onculu(satir)
            if ayristi and len(harf_katla(ayristi[0])) >= 8:
                cikti.append(ayristi)
    return cikti
