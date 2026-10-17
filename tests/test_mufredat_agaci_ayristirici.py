"""Üreticinin saf ayrıştırıcıları (spec §2.2, §2.3). Veritabanına dokunmaz."""
import sys
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "scripts"))

import mufredat_agaci as u  # noqa: E402  (scripts/mufredat_agaci.py)


# Ölçülmüş gerçek satırlar: doc 439 s.8 ve doc 346 s.7 (spec §0).
@pytest.mark.parametrize("satir,beklenen", [
    ("Sindirim Sisteminin Sağlığı  .....................................................96",
     ("Sindirim Sisteminin Sağlığı", 96)),
    ("TAM SAYILAR.................................................................................17",
     ("TAM SAYILAR", 17)),
    ("1. Sindirim Sistemi  ..................................................................89 ",
     ("1. Sindirim Sistemi", 89)),
])
def test_nokta_onculu_ad_ve_sayfayi_ayirir(satir, beklenen):
    assert u.nokta_onculu(" ".join(satir.split())) == beklenen


@pytest.mark.parametrize("satir", [
    "KÜRESELLEŞMEN İN İNSAN VE TOPLUM HAYATINA ETK İSİ ...............",  # numara kopuk
    "İÇİNDEKİLER",
    "",
    "Sözlük ... 149",  # üç noktadan az
])
def test_nokta_onculu_eslesmeyen_satirda_none(satir):
    assert u.nokta_onculu(satir) is None


# Türkçe harf tuzağı: str.title() 'İ'yi 'i'+birleşen noktaya, 'I'yı 'i'ye çevirir.
@pytest.mark.parametrize("ham,beklenen", [
    ("TAM SAYILAR", "Tam Sayılar"),
    ("SİNDİRİM SİSTEMİNİN SAĞLIĞI", "Sindirim Sisteminin Sağlığı"),
    ("IŞIĞIN KIRILMASI", "Işığın Kırılması"),
    ("MİLLÎ MESELELER VE TÜRK TOPLUMU", "Millî Meseleler ve Türk Toplumu"),
    ("Sindirim Sisteminin Sağlığı", "Sindirim Sisteminin Sağlığı"),
])
def test_baslik_duzeni(ham, beklenen):
    assert u.baslik_duzeni(ham) == beklenen


def test_baslik_duzeni_harf_araligi_bozulmasini_duzeltir():
    assert u.baslik_duzeni("SOSY AL BİLİMLER") == "Sosyal Bilimler"


def test_kayma_bul_modu_ve_uyumu_dondurur():
    # (basılı, gövdede bulunan) çiftleri: 21 tanesi +1, biri -2, biri +2 (doc 439 ölçümü).
    adaylar = [(n, n + 1) for n in range(10, 31)] + [(40, 38), (50, 52)]
    assert u.kayma_bul(adaylar) == (1, "21/23")


def test_kayma_bul_uyum_esigin_altindaysa_kaymasiz():
    adaylar = [(10, 11), (20, 25), (30, 37), (40, 44), (50, 59)]
    kayma, uyum = u.kayma_bul(adaylar)
    assert kayma is None and uyum == "1/5"


def test_kayma_bul_bos_listede_kaymasiz():
    assert u.kayma_bul([]) == (None, "0/0")


def test_konu_slug_turkce_harfleri_katlar():
    assert u.konu_slug("Sindirim Sisteminin Sağlığı") == "sindirim-sisteminin-sagligi"
    assert u.konu_slug("IŞIĞIN KIRILMASI") == "isigin-kirilmasi"


def test_konu_slug_noktalamayi_duser_ve_tireyi_sadelestirir():
    assert u.konu_slug("1. Tema — Ölçme ve Değerlendirme!") == "1-tema-olcme-ve-degerlendirme"
