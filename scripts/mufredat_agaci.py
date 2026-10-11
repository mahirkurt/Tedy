"""7. sınıf müfredat ağacını üretir: ders → ünite → ders kitabı alt başlığı.

Çıktı `src/mufredat_agaci.json`; elle düzenlenmez. Tek kaynak sabitlenmiş salt-okunur
müfredat veritabanıdır (spec §0). `output/modules/` altına yazılmaz — orada tek yazar ted-mcp.

Kullanım:
    .venv/bin/python scripts/mufredat_agaci.py tumu --sinif 7
"""
from __future__ import annotations

import argparse
import collections
import functools
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import mufredat_agaci as ma  # noqa: E402  (sys.path yukarıda kuruldu)

URI ="file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1"

# Program PDF'lerinin metin katmanındaki harf aralığı bozulmaları; skill_unite_haritasi.py'daki
# OCR_DUZELTME ile aynı gerekçe, ders kitabı başlıklarında ölçülen biçimler.
OCR_DUZELTME = {"SOSY AL": "SOSYAL", "DÜNY A": "DÜNYA", "YAŞAY AN": "YAŞAYAN",
                "KÜL TÜRÜ": "KÜLTÜRÜ", "ETK İSİ": "ETKİSİ", "ÜLKEM İZİN": "ÜLKEMİZİN",
                "DEVLETİ ’NİN": "DEVLETİ’NİN", "KÜRESELLEŞMEN İN": "KÜRESELLEŞMENİN"}
# Başlık düzeninde küçük kalan bağlaçlar (Türkçe yazım).
KUCUK_KALAN = {"ve", "ile", "veya", "ya", "da", "de", "ki"}
KUCUK = "a-zçğıöşüâîû"
# Satır sonu tirelemesiyle karışan GERÇEK bileşik sözcükler (skill_unite_haritasi.py'da ölçüldü).
BILESIK_KORUMA = {"yeryön": "yer-yön"}
NOKTA_ONCULU = re.compile(r"^(?P<ad>.*?[^\s.])\s*\.{4,}\s*(?P<s>\d{1,3})$")
SADECE_BASLIK = re.compile(r"^(?P<ad>.*?[^\s.])\s*\.{3,}\s*$")
GRUP_BASLIGI = re.compile(r"^\d+\.\s")
TEMA_ISARETI = re.compile(r"^(\d+)\.\s*(?:TEMA|ÖĞRENME ALANI|ÜNİTE)\b", re.IGNORECASE)
KAYMA_UYUM_ESIGI = 0.80
# Eşleme: başlığın içerik sözcüklerinin bu oranı kazanımda geçmeli. Yön önemli — kazanımın
# sözcüklerini başlıkta aramak ölçüldü ve HİÇBİR konuyu eşlemiyordu (2026-10-11).
ORTUSME_ESIGI = 0.60
# Türkçe ek budaması: iki katlanmış sözcüğün ilk ONEK harfi eşitse aynı kök sayılır
# ('organlar' ↔ 'organların'). Ek budanmadan Fen'de 5/35 kazanım eşleşiyordu, budamayla 25/35.
ONEK = 5
# Eşlemede taşıyıcılığı olmayan sözcükler.
DURAK = {"ve", "ile", "icin", "bir", "bu", "veya", "gibi", "olan", "daha"}
# Kitap aparatı: ünite içi konu değil. Katlanmış ad bunlardan birini İÇERİYORSA düşer
# ("1. Tema Ölçme ve Değerlendirme Soruları" gibi numaralı biçimleri de yakalamak için).
APARAT = ("on degerlendirme", "unite sonu degerlendirme", "neler biliyoruz", "neler ogrendik",
          "baslayalim", "ogrenelim", "kitabimizi taniyalim", "sozluk", "kaynakca",
          "cevap anahtari", "cevap anahtarlari", "icindekiler", "iz birakanlar",
          "kendimi degerlendiriyorum", "olcme ve degerlendirme sorulari", "uretim vakti",
          "oz degerlendirme formlari", "gorsel kaynakcasi", "genel ag")
KONU_ESIGI = 0.60


def nokta_onculu(satir: str) -> tuple[str, int] | None:
    """"Ad ....... 96" satırını (ad, 96) yapar; eşleşmezse None."""
    eslesme = NOKTA_ONCULU.match(" ".join((satir or "").split()))
    return (eslesme.group("ad"), int(eslesme.group("s"))) if eslesme else None


@functools.lru_cache(maxsize=1)
def _aparat_katli() -> tuple[str, ...]:
    """`harf_katla` bu sabitlerden sonra tanımlandığı için katlama tembeldir."""
    return tuple(harf_katla(a) for a in APARAT)


@functools.lru_cache(maxsize=1)
def _durak_katli() -> frozenset[str]:
    return frozenset(harf_katla(d) for d in DURAK)


def aparat_mi(ad: str) -> bool:
    """Kitap aparatı mı (ünite içi konu değil). İçerme ile bakar: "1. Tema Ölçme ve
    Değerlendirme Soruları" gibi numaralı biçimler de yakalanır."""
    katlanmis = harf_katla(ad)
    return bool(katlanmis) and any(parca in katlanmis for parca in _aparat_katli())


def grup_basligi_mi(ad: str) -> bool:
    """Numaralı içindekiler satırı alt ünite başlığıdır, konu değil.

    Ölçüldü 2026-10-11: Fen kitaplarında "1. Sindirim Sistemi" satırı kendi alt başlıklarının
    üstünde duruyor; konu sayılırsa aynı konu iki kez çıkıyor ve iki kazanıma eşleşiyor.
    """
    return bool(GRUP_BASLIGI.match((ad or "").strip()))


def baslik_duzelt(ad: str) -> str | None:
    """İki sütunlu içindekilerden gelen düzen artığını ayıklar; ayıklanamazsa None.

    İki artık ölçüldü (doc 460, 491, 361): kapanmamış parantezle kesilen başlık
    ("… Hedefe Odaklan (Dinleme") ve iki başlığın nokta öncülleriyle yapışması
    ("KARA VE DENİZ … ..... TÜRK DÜ").
    """
    ad = " ".join((ad or "").split())
    if ".." in ad:
        return None
    if ad.count("(") > ad.count(")"):
        ad = ad[:ad.rfind("(")].strip()
    return ad or None


def temizle(metin: str) -> str:
    """Satır sonu tirelemesi ve fazla boşluk: 'lis- teler' -> 'listeler'.

    `scripts/skill_unite_haritasi.py`'ın aynı adlı işlevinden taşındı (orada ölçüldü);
    gerçek bileşik sözcüklerin tiresi BILESIK_KORUMA ile geri konur.
    """
    metin = " ".join((metin or "").split())
    metin = re.sub(rf"(?<=[{KUCUK}])\s?-\s+(?=[{KUCUK}])", "", metin)
    for yanlis, dogru in BILESIK_KORUMA.items():
        metin = metin.replace(yanlis, dogru)
    return metin


def ana_cumle(metin: str) -> str:
    """Kazanımın ana ifadesi: ' a) ' ile başlayan süreç bileşenlerinden önceki kısım.

    Ölçüldü 2026-10-11: `learning_outcome.text` süreç bileşenlerini de taşıyor (FB.7.1.1
    349 karakter), bu yüzden ham metinle örtüşme araması hiçbir konuyu eşlemiyordu.
    """
    return re.split(r"\s[a-zç]\)\s", temizle(metin), maxsplit=1)[0].strip()


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
        # `metin` ana ifadedir: süreç bileşenleri eşlemeyi boğuyordu (bkz. ana_cumle).
        cikti[kod] = {"kod": kod, "unite_no": unite_no, "metin": ana_cumle(metin),
                      "tam_metin": temizle(metin)}
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


def icindekiler_basliklari(baglanti: sqlite3.Connection, document_id: int) -> list[str]:
    """Numarasız içindekiler başlıkları, görüldükleri sırada.

    Türkçe ve Sosyal kitaplarının içindekileri iki sütunlu: başlık okunur ama sayfa numarası
    ondan kopuk düşer (ölçüldü 2026-10-11, doc 460/340/491/361 → 0 nokta öncüllü satır).
    """
    cikti: list[str] = []
    for _, metin in baglanti.execute(
            "select page_no, text from document_page where document_id=? and page_no<=?"
            " order by page_no", (document_id, ICINDEKILER_ARAMA_SINIRI)):
        for satir in (metin or "").splitlines():
            eslesme = SADECE_BASLIK.match(" ".join(satir.split()))
            if eslesme and len(harf_katla(eslesme.group("ad"))) >= 8:
                cikti.append(eslesme.group("ad"))
    return cikti


# ── Eşleme ve kimlik ────────────────────────────────────────────────────────


def _icerik_sozcukleri(metin: str) -> set[str]:
    sozcukler = {harf_katla(s) for s in (metin or "").split()}
    return {s for s in sozcukler if len(s) >= 4 and s not in _durak_katli()}


def _ayni_kok(a: str, b: str) -> bool:
    """Türkçe ek budaması: biri ötekinin öneki ya da ilk ONEK harfi eşit."""
    return a.startswith(b) or b.startswith(a) or (
        len(a) >= ONEK and len(b) >= ONEK and a[:ONEK] == b[:ONEK])


def _ortusme_orani(ad: str, kazanim_metni: str) -> float:
    basliktaki = _icerik_sozcukleri(ad)
    if not basliktaki:
        return 0.0
    hedef = _icerik_sozcukleri(kazanim_metni)
    tutan = sum(1 for s in basliktaki if any(_ayni_kok(s, h) for h in hedef))
    return tutan / len(basliktaki)


def kazanim_esle(konu_metni: str, kazanimlar: list[dict]) -> tuple[list[str], str]:
    """Kanıta dayalı eşleme: başlığın içerik sözcükleri kazanımda geçiyor mu.

    Kod sırasına göre eşleme YASAK (spec §3): Fen'de 1:1 görünmesi Matematik'te yanlış olur.
    En yüksek skoru alan kazanım(lar) döner; eşik altındaysa boş liste ve "eslenmedi".
    """
    skorlar = [(_ortusme_orani(konu_metni, k["metin"]), k["kod"]) for k in kazanimlar]
    en_iyi = max((skor for skor, _ in skorlar), default=0.0)
    if en_iyi < ORTUSME_ESIGI:
        return [], "eslenmedi"
    return sorted(kod for skor, kod in skorlar if skor == en_iyi), "metin-ortusmesi"


BILME_SONU = re.compile(r"(?:[ae]bilme|bilme)$", re.IGNORECASE)


def i_hasarli_mi(basliklar: list[str]) -> bool:
    """İçindekiler metni noktalı/noktasız I ayrımını yitirmiş mi.

    Ölçüldü 2026-10-11, altı kitabın içindekileri: Sosyal Bilgiler 2. Kitap (doc 361) `İ`
    hiç taşımıyor ama `I`'yı 57 kez taşıyor — oradaki her büyük I belirsizdir. Öbür beş kitapta
    iki harf de bulunuyor, yani I'ları gerçekten noktasızdır. Bu ayrım kurtarılamaz: aynı
    kitapta "NITELIKLERI" noktalı, "KALKINMA" noktasız olmalıdır ve kaynak ikisini aynı harfe
    çökertmiştir. Harf uydurmak yerine (D4) o kitabın adları programın temiz metninden alınır.
    """
    metin = " ".join(basliklar)
    return "İ" not in metin and "I" in metin


def kazanimdan_ad(kazanim_metni: str) -> str:
    """Kazanımın ana ifadesinden okunabilir konu adı: sondaki '-abilme' fiili atılır."""
    sozcukler = (kazanim_metni or "").split()
    if len(sozcukler) > 1 and BILME_SONU.search(sozcukler[-1]):
        sozcukler = sozcukler[:-1]
    return " ".join(sozcukler).strip(" ,;:")


def parca_basligi_mi(ad: str, kazanim_metni: str) -> bool:
    """Başlık, eşleştiği kazanımın bir parçası mı (iki sütunlu içindekiden gelen kuyruk).

    Ölçüldü 2026-10-11: doc 491'in içindekilerinde iki satıra bölünmüş başlıkların kuyruğu
    ayrı satır gibi görünüyor ("… TUTUM VE / DAVRANIŞLARI", "… GELMESİNİ SAĞLAYAN /
    POLİTİKALAR"). En çok iki içerik sözcüğü olan ve hepsi kazanımda geçen başlık kuyruktur.
    """
    basliktaki = _icerik_sozcukleri(ad)
    if not basliktaki or len(basliktaki) > 2:
        return False
    hedef = _icerik_sozcukleri(kazanim_metni)
    return all(any(_ayni_kok(s, h) for h in hedef) for s in basliktaki)


def gecersiz_sayfa(sayfa: object, sayfa_sayisi: int) -> bool:
    """Bozuk aralık sessizce yazılmaz: sayfa uydurmamak kuralının aritmetik yüzü (spec §2.1)."""
    if not isinstance(sayfa, list) or len(sayfa) != 2:
        return True
    if not all(isinstance(s, int) and not isinstance(s, bool) for s in sayfa):
        return True
    bas, son = sayfa
    return bas < 1 or son < bas or son > sayfa_sayisi


def kimlik_ver(ders_slug: str, unite_no: int, ad: str, kullanilan: set[str]) -> tuple[str, bool]:
    """`<ders>-u<no>-<ad slug'ı>`; sırasal sayı yok. Çakışmada `-2`, `-3`… ve çakıştı bayrağı."""
    taban = f"{ders_slug}-u{unite_no}-{konu_slug(ad)}"
    if taban not in kullanilan:
        kullanilan.add(taban)
        return taban, False
    sira = 2
    while f"{taban}-{sira}" in kullanilan:
        sira += 1
    kimlik = f"{taban}-{sira}"
    kullanilan.add(kimlik)
    return kimlik, True


def kitap_kaymasi(baglanti: sqlite3.Connection, kitap_id: int) -> tuple[int | None, str]:
    """İçindekilerdeki basılı numara ↔ başlığın gövdede geçtiği sayfadan kaymayı türetir."""
    satirlar = icindekiler_satirlari(baglanti, kitap_id)
    sayfalar = {no: harf_katla(metin) for no, metin in kitap_sayfalari(baglanti, kitap_id).items()}
    adaylar: list[tuple[int, int]] = []
    for ad, basili in satirlar:
        anahtar = harf_katla(ad)
        for fark in (0, 1, -1, 2, -2, 3, -3):
            aday = basili + fark
            if anahtar and anahtar in sayfalar.get(aday, ""):
                adaylar.append((basili, aday))
                break
    return kayma_bul(adaylar)


# ── Üretim ──────────────────────────────────────────────────────────────────


def _kitap_kayitlari(baglanti: sqlite3.Connection, ders: Ders) -> list[dict]:
    kayitlar = []
    for sira, kitap_id in enumerate(ders.kitaplar, start=1):
        kayma, uyum = kitap_kaymasi(baglanti, kitap_id)
        nokta = icindekiler_satirlari(baglanti, kitap_id)
        basliklar = icindekiler_basliklari(baglanti, kitap_id)
        kayitlar.append({
            "document_id": kitap_id, "kisa": f"{sira}. Kitap",
            "sayfa_kaymasi": kayma, "kayma_uyumu": uyum,
            "_sayfa_sayisi": len(kitap_sayfalari(baglanti, kitap_id)),
            "_nokta": nokta, "_basliklar": basliklar,
            "_i_hasarli": i_hasarli_mi([ad for ad, _ in nokta] or basliklar),
        })
    return kayitlar


def _sayfa_araliklari(basililar: list[int]) -> dict[int, tuple[int, int]]:
    """Basılı başlangıç sayfalarından aralık: bitiş, bir sonraki başlangıcın bir eksiği.

    Tek başına bir başlangıç tek sayfalık aralıktır; kitabın arka maddesi bilinmediği için
    son başlığın bitişi uydurulmaz.
    """
    sirali = sorted(set(basililar))
    sonraki = {bas: sirali[i + 1] for i, bas in enumerate(sirali) if i + 1 < len(sirali)}
    return {bas: (bas, max(bas, sonraki[bas] - 1) if bas in sonraki else bas) for bas in sirali}


def ders_uret(baglanti: sqlite3.Connection, slug: str) -> tuple[dict | None, dict]:
    """Bir dersin kaydı ve kapsamı. Eşiğe takılırsa (None, kapsam) — yarım yazılmaz (spec §2.2)."""
    ders = DERSLER[slug]
    uniteler = program_uniteleri(baglanti, ders)
    kazanimlar = program_kazanimlari(baglanti, ders)
    kitaplar = _kitap_kayitlari(baglanti, ders)
    kazanim_unitesi = {k["kod"]: k["unite_no"] for k in kazanimlar}
    unite_konulari: dict[int, list[dict]] = {unite["no"]: [] for unite in uniteler}
    # Türkçe kazanımı ünite numarası taşımaz; ünite yalnız o derste içindekiler sırasından
    # gelir. Bu, ders adından değil kazanım kodlarından türetilir (spec §3).
    tema_sirasi_kullan = bool(kazanimlar) and all(k["unite_no"] is None for k in kazanimlar)
    kullanilan: set[str] = set()
    cakisma = aday = 0

    for kitap in kitaplar:
        ham = ([(ad, basili) for ad, basili in kitap["_nokta"]] if kitap["_nokta"]
               else [(ad, None) for ad in kitap["_basliklar"]])
        araliklar = _sayfa_araliklari([b for _, b in ham if b is not None])
        acik_tema: int | None = None
        for ham_ad, basili in ham:
            isaret = TEMA_ISARETI.match(ham_ad)
            if isaret:
                no = int(isaret.group(1))
                if no in unite_konulari:
                    acik_tema = no
                continue  # işaret satırının kendisi konu değil
            ad = baslik_duzelt(ham_ad)
            if ad is None or aparat_mi(ad):
                continue
            aday += 1
            kodlar, kaynak = kazanim_esle(baslik_duzeni(ad), kazanimlar)
            kazanim_metni = next((k["metin"] for k in kazanimlar if k["kod"] in kodlar), "")
            # Numarasız yolda (Türkçe, Sosyal) iki sütunlu düzenin bıraktığı kuyruk başlık düşer.
            if basili is None and kazanim_metni and parca_basligi_mi(ad, kazanim_metni):
                continue
            # I ayrımını yitirmiş kitapta ad programın temiz metninden gelir; kazanımı
            # eşleşmeyen başlık o kitapta hiç yazılmaz — harf uydurulmaz (D4).
            if kitap["_i_hasarli"]:
                if not kazanim_metni:
                    continue
                duzgun = kazanimdan_ad(kazanim_metni)
            else:
                duzgun = baslik_duzeni(ad)
            unite_no = next((kazanim_unitesi[kod] for kod in kodlar
                             if kazanim_unitesi.get(kod) is not None), None)
            if unite_no is None and tema_sirasi_kullan:
                unite_no = acik_tema
            if unite_no not in unite_konulari:
                continue
            kimlik, cakisti = kimlik_ver(slug, unite_no, duzgun, kullanilan)
            cakisma += int(cakisti)
            konu = {"id": kimlik, "ad": duzgun, "ad_kaynak": " ".join(ham_ad.split()),
                    "kitap": kitap["document_id"], "kazanimlar": kodlar,
                    "kazanim_kaynak": kaynak, "_grup": grup_basligi_mi(ad)}
            sayfa = None
            if basili is not None and kitap["sayfa_kaymasi"] is not None:
                bas, son = araliklar[basili]
                aday_sayfa = [bas + kitap["sayfa_kaymasi"], son + kitap["sayfa_kaymasi"]]
                if not gecersiz_sayfa(aday_sayfa, kitap["_sayfa_sayisi"]):
                    sayfa = aday_sayfa
            if sayfa is None:
                konu["sayfa_kaynak"] = "yok"
            else:
                konu["sayfa"], konu["sayfa_kaynak"] = sayfa, "icindekiler"
            unite_konulari[unite_no].append(konu)

    # Grup başlığı ("1. Sindirim Sistemi") yalnız kendi kazanımını başka bir konu kapsamıyorsa
    # kalır. Ölçüldü 2026-10-11: hepsini düşürmek Fen'de FB.7.4.1, FB.7.5.4, FB.7.6.3 gibi
    # yalnız grup satırında geçen kazanımları kaybediyordu (17/35); hepsini tutmak aynı konuyu
    # iki kez ve iki kazanımla yazıyordu.
    for no, liste in unite_konulari.items():
        yapragin_kapsadigi = {kod for konu in liste if not konu["_grup"]
                              for kod in konu["kazanimlar"]}
        unite_konulari[no] = [
            konu for konu in liste
            if not konu["_grup"] or not (set(konu["kazanimlar"]) & yapragin_kapsadigi)]
    for liste in unite_konulari.values():
        for konu in liste:
            konu.pop("_grup", None)

    tum_konular = [konu for liste in unite_konulari.values() for konu in liste]
    kapsanan = {kod for konu in tum_konular for kod in konu["kazanimlar"]}
    kazanimli = [k for k in kazanimlar if k["unite_no"] is not None]
    kapsam = {
        "konu": len(tum_konular), "aday": aday, "kazanim": len(kazanimlar),
        "kazanimi_eslenen": len(kapsanan),
        "sayfasi_olan": sum(1 for k in tum_konular if k["sayfa_kaynak"] == "icindekiler"),
        "kimlik_cakismasi": cakisma,
    }
    # Eşik: kazanım kodlu derste kazanım kapsaması, Türkçe'de her temanın en az bir konusu.
    if kazanimli:
        yeterli = len(kapsanan) / len(kazanimli) >= KONU_ESIGI
    else:
        yeterli = bool(uniteler) and all(unite_konulari[u["no"]] for u in uniteler)
    if not yeterli:
        kapsam["yazilmadi"] = "konu_esigi"
        return None, kapsam
    kayit = {
        "ders": ders.ad, "slug": slug,
        "program": {"document_id": ders.program_id,
                    "sayfa": f"{ders.sayfa_araligi[0]}-{ders.sayfa_araligi[1]}"},
        "kitaplar": [{k: v for k, v in kitap.items() if not k.startswith("_")}
                     for kitap in kitaplar],
        "uniteler": [{**unite, "konular": unite_konulari[unite["no"]]} for unite in uniteler],
    }
    return kayit, kapsam


def agac_uret(baglanti: sqlite3.Connection, sluglar: list[str]) -> dict:
    dersler, kapsam = [], {}
    for slug in sluglar:
        kayit, ders_kapsami = ders_uret(baglanti, slug)
        kapsam[slug] = ders_kapsami
        if kayit is not None:
            dersler.append(kayit)
    surum = baglanti.execute(
        "select value from manifest where key like '%version%' limit 1").fetchone()
    return {"surum": 1, "korpus_surumu": str(surum[0]) if surum else "bilinmiyor",
            "sinif": "7. Sınıf", "dersler": dersler, "kapsam": kapsam}


def main(argv: list[str] | None = None) -> int:
    ayristirici = argparse.ArgumentParser(description="7. sınıf müfredat ağacını üretir.")
    ayristirici.add_argument("ders", choices=[*DERSLER, "tumu"])
    ayristirici.add_argument("--sinif", default="7")
    ayristirici.add_argument("--cikti", default=str(
        Path(__file__).resolve().parents[1] / "src" / ma.AGAC_ADI))
    secenekler = ayristirici.parse_args(argv)
    if secenekler.sinif != "7":
        print("Bu dalda yalnız 7. sınıf üretilir (spec §1).", file=sys.stderr)
        return 2
    sluglar = list(DERSLER) if secenekler.ders == "tumu" else [secenekler.ders]
    agac = agac_uret(baglan(), sluglar)
    hatalar = ma.dogrula(agac)
    if hatalar:
        print("Üretilen ağaç şemaya uymuyor:", file=sys.stderr)
        for hata in hatalar[:20]:
            print(f"  {hata}", file=sys.stderr)
        return 1
    Path(secenekler.cikti).write_text(
        json.dumps(agac, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for slug, kapsam in agac["kapsam"].items():
        print(f"{slug:<10} {kapsam}")
    yazilmayan = [s for s, k in agac["kapsam"].items() if k.get("yazilmadi")]
    if yazilmayan:
        print(f"Eşiğe takılan ders(ler): {', '.join(yazilmayan)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
