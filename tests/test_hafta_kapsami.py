"""Weeks: how many are scraped, and which one is "now".

Measured on 2026-09-20: the portal offers the whole school year at once (36
weeks in the selector) and the scraper read only the week that happened to be
open, so course content the school had already published stayed invisible
until its week arrived. The timetable is the exception — every week renders
the identical grid, so only the content walks the selector.
"""
import pytest
from unittest.mock import patch

import src.dashboard_api as dashboard_api
from src.dashboard_api import app
from src.scrape_all import hafta_indeksleri


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestHaftaKapsami:
    def test_guncel_kapsam_ileri_iki_haftayi_alir(self):
        assert hafta_indeksleri(36, 0, "guncel") == [0, 1, 2]

    def test_yil_sonunda_listenin_disina_tasmaz(self):
        assert hafta_indeksleri(36, 34, "guncel") == [34, 35]
        assert hafta_indeksleri(36, 35, "guncel") == [35]

    def test_tum_kapsam_her_haftayi_alir(self):
        assert hafta_indeksleri(36, 7, "tum") == list(range(36))

    def test_secici_bossa_hafta_yok(self):
        assert hafta_indeksleri(0, 0, "tum") == []


class TestIcerikHaftalariUcu:
    """/api/content stays the open week; the rest are served beside it.

    Course content genuinely differs week to week — measured 2026-09-20: 12
    of 17 courses had different cards in week 2 than in week 1 — so the weeks
    are worth keeping. They are a separate endpoint because /api/content's
    shape (course → data) is what the SPA and the assistant index already
    read, and merging weeks into it would change that contract.
    """

    def test_haftalar_ve_guncel_hafta_dondurulur(self, client):
        scraped = {
            "ders_programi": [
                {"week_label": "1. Hafta", "is_current": True},
                {"week_label": "2. Hafta", "is_current": False},
            ],
            "ders_icerikleri_haftalar": {
                "1. Hafta": {"Türkçe": {"cards": ["a"]}},
                "2. Hafta": {"Türkçe": {"cards": ["b"]}},
            },
        }
        with patch("src.dashboard_api._scraped", return_value=scraped):
            data = client.get("/api/content/weeks").get_json()
        assert set(data["weeks"]) == {"1. Hafta", "2. Hafta"}
        assert data["current"] == "1. Hafta"

    def test_isaretli_hafta_icerikte_yoksa_ilkine_duser(self, client):
        scraped = {
            "ders_programi": [{"week_label": "36. Hafta", "is_current": True}],
            "ders_icerikleri_haftalar": {"1. Hafta": {"Türkçe": {"cards": ["a"]}}},
        }
        with patch("src.dashboard_api._scraped", return_value=scraped):
            data = client.get("/api/content/weeks").get_json()
        assert data["current"] == "1. Hafta"

    def test_hic_hafta_yoksa_bos_doner(self, client):
        with patch("src.dashboard_api._scraped", return_value={}):
            data = client.get("/api/content/weeks").get_json()
        assert data == {"weeks": {}, "current": ""}


class TestPanoGuncelHaftayiSecer:
    """`latest = weeks[-1]` was correct while the list held only past weeks.

    With the whole year stored the last element is a week in June, so the
    dashboard would have opened on an empty summer grid.
    """

    def _hafta(self, idx, etiket, guncel=False):
        return {
            "week_index": idx, "week_label": etiket, "is_current": guncel,
            "schedule": {"rows": [["", "Pazartesi"], ["1. Ders", f"Ders {idx}"]]},
        }

    def test_son_hafta_degil_isaretli_hafta_sunulur(self, client):
        weeks = [self._hafta(0, "1. Hafta", guncel=True),
                 self._hafta(35, "36. Hafta")]
        with patch("src.dashboard_api._scraped",
                   return_value={"ders_programi": weeks}):
            data = client.get("/api/schedule").get_json()
        assert data["latest"]["week_label"] == "1. Hafta"
        assert len(data["weeks"]) == 2

    def test_isaret_yoksa_onceki_davranis_surer(self, client):
        # Data written before the mark existed must still resolve to a week.
        weeks = [{"week_label": "1. Hafta", "schedule": {"rows": []}},
                 {"week_label": "2. Hafta", "schedule": {"rows": []}}]
        with patch("src.dashboard_api._scraped",
                   return_value={"ders_programi": weeks}):
            data = client.get("/api/schedule").get_json()
        assert data["latest"]["week_label"] == "2. Hafta"
