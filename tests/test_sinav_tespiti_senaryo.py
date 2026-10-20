"""Tespit, sınav kaydına MEB senaryo bloğunu yazar (spec §3.5)."""
from datetime import date, datetime

from src import sinav_senaryo
from src.sinav_cikarimi import Bulgu
from src.sinav_kaynaklari import Aday
from src.sinav_tespiti import birlestir, kuru_rapor
# Taken at collection, before conftest's autouse fixture replaces sinav_tespiti.tespit_et with a refusal.
from src.sinav_tespiti import tespit_et as GERCEK_TESPIT

SIMDI = datetime(2026, 10, 19, 10, 0)
TABLO = sinav_senaryo.tablo_oku()
METIN = ("22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz. Sınavınızın içeriği, "
         "MEB konu soru dağılım tablosu 4. senaryo ağırlıklı olacaktır. Konu başlıklarınız:\n"
         "Metnin yüzey anlamını belirleyebilme")
ALINTI = "22 Ekim Perşembe Günü 1.1 Ara Değerlendirme Sınavınızı gerçekleştireceğiz."


def _bulgu():
    aday = Aday(METIN, "Türkçe", date(2026, 10, 19), "ders_karti",
                [{"bolum": "ders_icerikleri_haftalar", "hafta": "6. Hafta", "ders": "Türkçe", "sira": 1}])
    return Bulgu("Türkçe", "ortak_sinav", "1.1 Ara Değerlendirme Sınavı", date(2026, 10, 22), None, None,
                 ["Metnin yüzey anlamını belirleyebilme"], ALINTI, aday)


def test_blok_yazilir_ve_icerik_surumu_degismez():
    duz = birlestir([], [_bulgu()], None, SIMDI)
    ile = birlestir([], [_bulgu()], None, SIMDI, senaryolar=TABLO)
    assert "senaryo" not in duz[0]
    assert ile[0]["senaryo"]["durum"] == "dogrulandi" and ile[0]["senaryo"]["senaryo"] == 4
    assert ile[0]["icerik_surumu"] == duz[0]["icerik_surumu"]


def test_sutun_cozulmezse_anahtar_yazilmaz():
    b = _bulgu()
    b = Bulgu(b.ders, "kisa_sinav", "Büyük Quiz", b.tarih, None, None, [], b.alinti, b.aday)
    assert "senaryo" not in birlestir([], [b], None, SIMDI, senaryolar=TABLO)[0]


def test_tablo_yoksa_not_duser(tmp_path, monkeypatch):
    class Okuyucu:
        def oku(self, *a, **k):
            raise AssertionError("model çağrılmamalı")
    monkeypatch.setattr(sinav_senaryo, "tablo_oku", lambda yol=None: None)
    belge = GERCEK_TESPIT(tmp_path, {}, [], SIMDI, bitis=0.0, okuyucu=Okuyucu())
    assert belge["ozet"]["hatalar"][0] == "senaryo tablosu okunamadı"


def test_kuru_rapor_senaryo_satiri():
    belge = {"sinavlar": birlestir([], [_bulgu()], None, SIMDI, senaryolar=TABLO), "ozet": {}}
    assert "  Senaryo: dogrulandi · Türkçe 1. yazılı · 4. senaryo · 7 soru" in kuru_rapor(belge).splitlines()
