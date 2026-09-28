"""scripts/skill_unite_haritasi.py'nin saf işlevleri — veritabanına dokunmadan.

Harita canlı müfredat veritabanından üretilir; o dosya bu makinenin dışında ve testlerin
erişimi yok. Burada yalnız metni temizleyen ve sıralayan işlevler denetlenir.
"""
import importlib.util
from pathlib import Path

import pytest

YOL = Path(__file__).resolve().parents[1] / "scripts" / "skill_unite_haritasi.py"


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
