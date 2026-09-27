"""Panonun bilinen dört sorunu (plan docs/superpowers/plans/2026-09-28-pano-eksiklikleri.md).

The assistant's live tools already read the portal's real shapes; the
dashboard's own routes did not. Every fixture here has the real shape of
output/scraped_data.json and invented values — no real names or grades.
"""
import json
import os
import sys
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

from src import assistant_tools as at  # noqa: E402
# The portal's weekly grid in its real shape: headers empty, upper-case
# dotless day names in rows[0], Mon–Thu and Fri–Sun as two blocks, each with
# its own time column (Friday's later bell). Invented lessons and teachers.
from tests.test_assistant_ogrenci_araclari import HAFTA, SATIRLAR  # noqa: E402

PAZARTESI = date(2026, 9, 21)


def _kopya(x):
    return json.loads(json.dumps(x))


@pytest.fixture
def api(monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(api, "_load_private_lessons", lambda: [])
    api.app.config["TESTING"] = True
    return api


def _haftayi_sabitle(api, monkeypatch):
    """Pin the unified calendar's week to Mon 21.09.2026 – Sun 27.09.2026."""
    gunler = [PAZARTESI + timedelta(days=i) for i in range(7)]
    monkeypatch.setattr(api, "_current_week_dates", lambda: gunler)
    return gunler


def _birlesik(api):
    with api.app.test_client() as c:
        return c.get("/api/calendar/unified").get_json()["events"]


# ── 1. Lessons: the real two-block grid ──────────────────────────────────────

def test_birlesik_takvim_gercek_iki_bloklu_tablodan_ders_cizer(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA)]})
    dersler = [e for e in _birlesik(api) if e["type"] == "lesson"]
    # Before: "Pazartesi" in "PAZARTESI" never matched — zero lessons, always.
    assert dersler
    cuma = [(e["start"], e["end"], e["title"]) for e in dersler if e["start"].startswith("2026-09-25")]
    # Friday reads its own block's bell (09:00, not Monday's 08:55).
    assert cuma == [
        ("2026-09-25T08:00:00", "2026-09-25T08:40:00", "Sosyal Bilgiler"),
        ("2026-09-25T09:00:00", "2026-09-25T09:40:00", "Fen Bilimleri"),
        ("2026-09-25T09:50:00", "2026-09-25T10:30:00", "Matematik"),
    ]
    pazartesi = sorted((e["start"], e["title"], e["subtitle"]) for e in dersler
                       if e["start"].startswith("2026-09-21"))
    assert pazartesi[0] == ("2026-09-21T08:00:00", "Türkçe", "Deneme Öğretmen")
    assert pazartesi[1][:2] == ("2026-09-21T08:55:00", "Fransızca")      # normalised name
    assert not any(e["title"] in ("Kahvaltı", "Öğle yemeği", "Çıkış") for e in dersler)
    assert all(e["courseFamily"] for e in dersler)                        # coloured by course


def test_birlesik_takvim_ders_programi_araciyla_ayni_dersleri_verir(api, monkeypatch):
    gunler = _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": [_kopya(HAFTA)]})
    dersler = [e for e in _birlesik(api) if e["type"] == "lesson"]
    for i, gun in enumerate(("Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma")):
        tarih = gunler[i].isoformat()
        rota = sorted((e["start"][11:16], e["title"]) for e in dersler if e["start"].startswith(tarih))
        arac = sorted((d["baslangic"], d["ders"]) for d in at.gunun_dersleri(SATIRLAR, gun))
        assert rota == arac, gun


def test_programsiz_birlesik_takvim_ders_uydurmaz(api, monkeypatch):
    _haftayi_sabitle(api, monkeypatch)
    monkeypatch.setattr(api, "_scraped", lambda: {"ders_programi": []})
    assert not [e for e in _birlesik(api) if e["type"] == "lesson"]
