"""scripts/skill_unite_haritasi.py'nin saf işlevleri, artı (DB varsa) uçtan uca yeniden üretim.

Harita canlı müfredat veritabanından üretilir; o veritabanı BU MAKİNEDE, salt okunur ve
değişmez bir URI ile bulunur (bkz. `URI`). Çoğu test yalnız metni temizleyen ve sıralayan saf
işlevleri denetler, veritabanına dokunmaz. `test_mevcut_haritalar_betikle_ayni` DB'ye dokunur;
DB'nin bulunmadığı bir ortamda (ör. farklı bir makinede çalışan CI) atlanır.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

YOL = Path(__file__).resolve().parents[1] / "scripts" / "skill_unite_haritasi.py"
DB_YOLU = Path("/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite")
SKILL_KOK = Path(__file__).resolve().parents[1] / "src" / "assistant_skills"


@pytest.fixture(scope="module")
def h():
    spec = importlib.util.spec_from_file_location("skill_unite_haritasi", YOL)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.mark.parametrize("ham,beklenen", [
    ("SAYILAR VE NİCELİKLER (1)", "Sayılar ve Nicelikler"),
    ("EVİMİZ DÜNY A", "Evimiz Dünya"),
    ("TEKNOLOJİ VE SOSY AL BİLİMLER", "Teknoloji ve Sosyal Bilimler"),
    ("OKUMA KÜL TÜRÜ", "Okuma Kültürü"),
    ("IŞIĞIN KIRILMASI VE MERCEKLER", "Işığın Kırılması ve Mercekler"),
])
def test_baslik_yaz(h, ham, beklenen):
    assert h.baslik_yaz(ham) == beklenen


def test_ana_cumle_surec_bilesenlerini_ve_tirelemeyi_atar(h):
    ham = ("Gerçek yaşam durumları üzerinden oran ilişkileri hakkında muhakeme yapa - bilme "
           "a) Gerçek yaşam durumları üzerinden iki niceliğin karşılaştırılmasında toplamsal")
    assert h.ana_cumle(ham) == ("Gerçek yaşam durumları üzerinden oran ilişkileri hakkında "
                                "muhakeme yapabilme")


def test_kod_sirasi_sayisal(h):
    kodlar = ["MAT.7.4.10", "MAT.7.4.9", "MAT.7.1.2", "T.O.7.12", "T.O.7.4"]
    assert sorted(kodlar, key=h.kod_sirasi) == ["MAT.7.1.2", "MAT.7.4.9", "MAT.7.4.10",
                                                  "T.O.7.4", "T.O.7.12"]


def test_uri_salt_okunur_ve_degismez(h):
    assert h.URI == "file:/home/mahirkurt/mcp-data/mufredat/mufredat.sqlite?mode=ro&immutable=1"


def test_temizle_gercek_bilesigin_tiresini_korur(h):
    """'yer- yön' satır kırığı genel tireleme temizliğinde 'yeryön'e dönüşmemeli — bu gerçek
    bir bileşik sözcüktür (DYS.DO.7.6, korpus 1.6), 'yapa - bilme' gibi bir satır kırığı değil."""
    ham = ("Fiilleri çeşitli yönlerden belirten söz varlığının cümlenin anlamına katkısını "
           "(durum, zaman, yer- yön ve soru) belirler.")
    assert "yer-yön" in h.temizle(ham)
    assert "yeryön" not in h.temizle(ham)


def test_temizle_normal_tirelemeyi_hala_birlestirir(h):
    """Bileşik-koruma özel durumu, sıradan satır-kırığı tirelemesini bozmamalı."""
    assert h.temizle("söz varlı- ğını") == "söz varlığını"


# --- Yanlış gövde seçimi reddi (issue 1: T.Y.7.1) -----------------------------------------
#
# Ölçüldü (korpus 1.6, learning_outcome tablosu): T.Y.7.1'in 'outcome' satırı (id 6285, s.159)
# iki fıkralı bir açıklama metninin ortasından kesik ve açık parantezle biter; doğru ifade
# 'heading' satırında (id 6286, s.127) kendi başına duruyor. Betik artık heading'i tercih eder
# ve çok-fıkralı/parantez-kesik satırları aday olarak reddeder.
_TY71_OUTCOME_SATIRI = ("Yazılı üretimlerinde ve yazı- lı etkileşimlerinde tartışabilme, "
                        "yazma sürecini değerlendirebilme (")
_TY71_HEADING_SATIRI = "Yazma sürecini yönetebilme"


def test_aciklama_ifadesi_coklu_bilme_ve_acik_parantezi_reddeder(h):
    """T.Y.7.1'in gerçek outcome satırı (iki '-bilme' fıkrası + açık parantez) aday olamaz."""
    assert h.aciklama_ifadesi(_TY71_OUTCOME_SATIRI) is None


def test_aciklama_ifadesi_tek_fikrayi_kabul_eder(h):
    assert h.aciklama_ifadesi("Metni özetleyebilme a) ilk cümleyi kullanır") == "Metni özetleyebilme"


def test_baslik_ifadesi_tek_fikrayi_kabul_eder(h):
    assert h.baslik_ifadesi(_TY71_HEADING_SATIRI) == _TY71_HEADING_SATIRI


def test_baslik_ifadesi_baska_baslikla_yapisik_satiri_reddeder(h):
    """'Dinleme/izleme sürecini değerlendirebilme Okuma' iki ayrı başlığın korpusta yan yana
    düşmesinden oluşan bir korpus artefaktıdır (T.D.7.25); 'bilme' ile bitmediği için (bir
    başka becerinin adıyla, 'Okuma' ile bitiyor) reddedilir."""
    assert h.baslik_ifadesi("Dinleme/izleme sürecini değerlendirebilme Okuma") is None


def test_aciklama_ifadesi_bilmedigi_yanlis_pozitifi_saymaz(h):
    """'bilmediği' içindeki rastlantısal 'bilme' geçişi (sözcük sonunda değil) bir ikinci
    fıkra sayılmamalı — T.O.7.4'ün gerçek, tek fıkralı outcome satırı kabul edilmeli."""
    satir = ("Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin "
             "edebilme a) bağlamdan yararlanır")
    assert h.aciklama_ifadesi(satir) == (
        "Metinde geçen anlamını bilmediği söz varlığı unsurlarının anlamını tahmin edebilme")


# --- Mevcut haritaların betikle aynı olduğunu doğrula (yalnız DB varsa) --------------------

def _mevcut_haritali_dersler() -> list[str]:
    """references/unite-haritasi.md dosyası olan skill dizinleri (dosya sisteminden; DB'ye
    dokunmaz — parametrize listesi collection sırasında, DB'siz bir ortamda da kurulabilmeli)."""
    if not SKILL_KOK.is_dir():
        return []
    return sorted(p.name for p in SKILL_KOK.iterdir()
                  if p.is_dir() and (p / "references" / "unite-haritasi.md").is_file())


@pytest.mark.skipif(not DB_YOLU.exists(), reason="müfredat veritabanı bu makinede yok")
@pytest.mark.parametrize("ad", _mevcut_haritali_dersler())
def test_mevcut_haritalar_betikle_ayni(ad):
    """Committed references/unite-haritasi.md, betiğin şu anki çıktısıyla bayt bayt aynı
    olmalı — harita üretilir, elle düzenlenmez."""
    guncel = subprocess.run([sys.executable, str(YOL), ad], capture_output=True, text=True,
                             check=True, timeout=30).stdout
    committed = (SKILL_KOK / ad / "references" / "unite-haritasi.md").read_text(encoding="utf-8")
    assert guncel == committed
