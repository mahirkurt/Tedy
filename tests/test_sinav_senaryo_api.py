"""/api/exams senaryo bloğunu geçirir; sinavlar aracı özetini yazar (spec §4, §6)."""
import os
from datetime import datetime

# dashboard_api freezes the bypass flag at import; every module that imports it sets this first, so
# collecting this file before the route tests of another one cannot switch their auth back on.
os.environ["TEST_AUTH_BYPASS"] = "1"
from src import dashboard_api  # noqa: E402
from src.assistant_tools import sinavlar_metni  # noqa: E402

BLOK = {"durum": "dogrulandi", "ders": "Türkçe", "sinav_no": 1, "donem": 1, "anilan": [4], "cumle": "4. senaryo",
        "senaryo": 4, "toplam": 7, "dagilim": [], "eslesen_konu_sayisi": 2, "eslesmeyen_konular": [],
        "senaryo_disi_konular": [], "adaylar": [], "senaryo_sayisi": 6,
        "kaynak": "https://odsgm.meb.gov.tr/x", "meb_guncelleme": "2026-09-10T17:27"}


def _belge(senaryo):
    k = {"id": "a1", "ders": "Türkçe", "tur": "ortak_sinav", "baslik": "1.1 Ara Değerlendirme Sınavı",
         "tarih": "2026-10-22", "saat": None, "hafta": None, "konular": [], "kaynaklar": [],
         "sentetik": False, "taban": None, "son_yayin": "2026-10-19", "icerik_surumu": "x",
         "ilk_tespit": None, "degisti": None}
    if senaryo is not None:
        k["senaryo"] = senaryo
    return {"surum": 1, "uretildi": "2026-10-19T00:00:00", "sinavlar": [k], "ozet": {"incelenmedi": 0}}


def test_api_blogu_gecirir(monkeypatch):
    monkeypatch.setattr(dashboard_api, "_sinavlar_belgesi", lambda: _belge(BLOK))
    e = dashboard_api._sinav_api_listesi({}, now=datetime(2026, 10, 19, 10))["exams"][0]
    assert e["senaryo"] == BLOK


def test_api_blok_yoksa_null(monkeypatch):
    monkeypatch.setattr(dashboard_api, "_sinavlar_belgesi", lambda: _belge(None))
    assert dashboard_api._sinav_api_listesi({}, now=datetime(2026, 10, 19, 10))["exams"][0]["senaryo"] is None
    monkeypatch.setattr(dashboard_api, "_sinavlar_belgesi", lambda: None)
    eski = dashboard_api._sinav_api_listesi({"takvim": []}, now=datetime(2026, 10, 19, 10))
    assert all(e["senaryo"] is None for e in eski["exams"])


def test_sinavlar_araci_ozet_satiri():
    e = {"course": "Türkçe", "title": "1.1 Ara Değerlendirme Sınavı", "rawTitle": "1.1 Ara Değerlendirme Sınavı",
         "date": "2026-10-22", "allDay": True, "status": "upcoming", "konular": [], "kaynaklar": [], "senaryo": BLOK}
    metin = sinavlar_metni([e], datetime(2026, 10, 19, 10))
    assert "MEB senaryosu: 4. senaryo doğrulandı · 7 soru — ayrıntı için sinav_senaryosu" in metin
