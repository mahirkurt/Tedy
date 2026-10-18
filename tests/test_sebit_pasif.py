"""SEBİT homework can be switched off (TEDY_SEBIT=0, asked 2026-10-18).

Off means: the sync makes no SEBİT login and does not count it as a failure,
and no surface shows the last reading (2026-09-24) as if it were current —
/api/sebit, the unified calendar and the assistant all say it is not tracked.
"""
import os
from datetime import datetime

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
os.environ.setdefault("DASHBOARD_SECRET_KEY", "test-only")

from src.platform_ayarlari import sebit_aktif  # noqa: E402

ESKI_SEBIT = {
    "scraped_at": "2026-09-24T11:34:00",
    "total_homework": 1,
    "completed_count": 0,
    "homework": [{
        "title": "Eski SEBİT ödevi",
        "course": "Matematik",
        "start_date": "2026-09-20 08:00",
        "end_date": "2026-09-30 23:59",
        "completed": False,
        "progress": 0,
    }],
}


@pytest.mark.parametrize("deger, beklenen", [
    (None, True), ("1", True), ("", True), ("0", False), (" 0 ", False),
])
def test_sebit_aktif_ayardan_okunur(monkeypatch, deger, beklenen):
    if deger is None:
        monkeypatch.delenv("TEDY_SEBIT", raising=False)
    else:
        monkeypatch.setenv("TEDY_SEBIT", deger)
    assert sebit_aktif() is beklenen


def _sahte_adim(cagrilar):
    def adim(ad, modul_adi, hatalar):
        cagrilar.append(ad)
    return adim


def test_pasif_sebit_senkronda_cagrilmaz_ve_hata_sayilmaz(monkeypatch):
    import src.run_sync as rs

    monkeypatch.setenv("TEDY_SEBIT", "0")
    cagrilar, hatalar = [], []
    monkeypatch.setattr(rs, "_platform_adimi", _sahte_adim(cagrilar))

    pasif = rs._yan_platformlar(hatalar)

    assert cagrilar == ["englishcentral", "achieve3000"]
    assert pasif == ["sebit_homework"]
    assert hatalar == []


def test_aktif_sebit_eskisi_gibi_calisir(monkeypatch):
    import src.run_sync as rs

    monkeypatch.delenv("TEDY_SEBIT", raising=False)
    cagrilar = []
    monkeypatch.setattr(rs, "_platform_adimi", _sahte_adim(cagrilar))

    assert rs._yan_platformlar([]) == []
    assert cagrilar == ["englishcentral", "achieve3000", "sebit_homework"]


@pytest.fixture
def api(monkeypatch):
    import src.dashboard_api as api

    gercek = api._load_json

    def yukle(ad, *a, **k):
        if ad == "sebit_homework.json":
            return ESKI_SEBIT
        return gercek(ad, *a, **k)

    monkeypatch.setattr(api, "_load_json", yukle)
    api.app.config["TESTING"] = True
    return api


def test_pasif_sebit_api_eski_okumayi_gostermez(api, monkeypatch):
    monkeypatch.setenv("TEDY_SEBIT", "0")
    with api.app.test_client() as c:
        veri = c.get("/api/sebit").get_json()
    assert veri == {"pasif": True}


def test_aktif_sebit_api_dosyayi_verir(api, monkeypatch):
    monkeypatch.delenv("TEDY_SEBIT", raising=False)
    with api.app.test_client() as c:
        veri = c.get("/api/sebit").get_json()
    assert veri["homework"][0]["title"] == "Eski SEBİT ödevi"


def _sebit_olaylari(api):
    with api.app.test_client() as c:
        olaylar = c.get("/api/calendar/unified").get_json()
    olaylar = olaylar.get("events", olaylar) if isinstance(olaylar, dict) else olaylar
    return [o for o in olaylar if o.get("type") == "sebit"]


def test_birlesik_takvim_pasif_sebiti_cizmez(api, monkeypatch):
    monkeypatch.delenv("TEDY_SEBIT", raising=False)
    assert _sebit_olaylari(api), "test düzeni: aktifken SEBİT olayı görünmeli"
    monkeypatch.setenv("TEDY_SEBIT", "0")
    assert _sebit_olaylari(api) == []


def test_asistan_pasif_sebiti_soyler():
    from src.assistant_tools import odev_listesi_metni

    metin = odev_listesi_metni([], datetime(2026, 10, 18, 15, 0), sebit={"pasif": True})
    assert "SEBİT" in metin and "takip edilmiyor" in metin
    assert "Eski SEBİT ödevi" not in metin
