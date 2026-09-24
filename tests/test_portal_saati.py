"""Takvim times are Istanbul wall clock, whatever suffix they carry.

scrape_takvim reads FullCalendar's `e.startStr`, formatted in the browser's
zone. While Chrome ran on the host's UTC, wall-clock 12:40 came out "12:40:00Z"
(measured over all 38 timed events on 2026-09-24: 18 start at the 08:00 bell,
school-day ones end at 15:45, the parent seminar is "19:00Z", the club slot is
exactly Thursday's two empty periods). Read as UTC it all landed three hours
late in a Turkish browser, and on the server an aware datetime met a naive
`datetime.now()`: the TypeError was caught and every takvim exam was filed
"past", so "Yaklaşan Sınavlar" never appeared. Since the host moved to Istanbul
time the same events arrive as "+03:00"; both forms must mean the same thing.

The old tests missed it: the upcoming-exam case built its date without the "Z"
the real data always had, and the past-exam case passed because of the
swallowed error.
"""
import hashlib
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402

app = dashboard_api.app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _portal(dt):
    """A time as the UTC-browser scrape wrote it: local clock, "Z" on the end."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"


def _veri(takvim):
    return {
        "takvim": takvim,
        "odevlerim": {"summary": "", "homework": {"rows": []}},
        "gelisim_raporu": {"semester": "1. Dönem", "grades": []},
        "ders_icerikleri": {},
    }


def _sinav(baslangic, bitis=""):
    return {"title": "5-6-7. Sınıflar Özdebir Gelişim İzleme Sınavı GİS-1",
            "start": baslangic, "end": bitis, "allDay": False,
            "backgroundColor": "", "extendedProps": {}}


class TestSinavlar:
    def test_ileriki_sinav_z_ile_gelse_de_yaklasan_sayilir(self, client):
        ileride = _portal(datetime.now() + timedelta(days=29))
        with patch.object(dashboard_api, "_scraped", return_value=_veri([_sinav(ileride)])):
            j = client.get("/api/exams").get_json()
        assert j["stats"]["upcoming"] == 1
        assert j["exams"][0]["status"] == "upcoming"

    def test_bugun_bitmis_sinav_gecmistir(self, client):
        # Same local-clock reading in the other direction: an exam two hours
        # ago is past, and not because a comparison failed.
        once = _portal(datetime.now() - timedelta(hours=2))
        with patch.object(dashboard_api, "_scraped", return_value=_veri([_sinav(once)])):
            j = client.get("/api/exams").get_json()
        assert j["exams"][0]["status"] == "past"

    def test_tarih_z_siz_cikar_kimlik_degismez(self, client):
        # Modules link to an exam by {kind: "exam", id}, and the id hashes the
        # raw start string. Changing the id would orphan every linked module.
        ham = "2026-10-23T09:00:00Z"
        with patch.object(dashboard_api, "_scraped",
                          return_value=_veri([_sinav(ham, "2026-10-23T12:10:00Z")])):
            s = client.get("/api/exams").get_json()["exams"][0]
        assert s["date"] == "2026-10-23T09:00:00"
        assert s["endDate"] == "2026-10-23T12:10:00"
        beklenen = hashlib.md5(f"{s['course']}|{s['rawTitle']}|{ham}".encode()).hexdigest()[:12]
        assert s["id"] == beklenen


class TestTakvim:
    ETKINLIK = {"title": "5,6,7,8. Sınıflar Kulüp Tanıtımları",
                "start": "2026-09-24T12:40:00Z", "end": "2026-09-24T14:10:00Z",
                "allDay": False, "extendedProps": {"description": "<p>x</p>"}}

    def test_takvim_yerel_saatle_cikar(self, client):
        with patch.object(dashboard_api, "_scraped", return_value=_veri([dict(self.ETKINLIK)])), \
             patch.object(dashboard_api, "_private_lessons_calendar_events", return_value=[]):
            ev = client.get("/api/calendar").get_json()["events"][0]
        assert ev["start"] == "2026-09-24T12:40:00"
        assert ev["end"] == "2026-09-24T14:10:00"
        # Everything else about the event is passed through untouched.
        assert ev["extendedProps"] == {"description": "<p>x</p>"}

    def test_kaynak_veri_degismez(self, client):
        # The cached scrape is shared between requests; the API must not
        # rewrite it in place.
        kaynak = [dict(self.ETKINLIK)]
        with patch.object(dashboard_api, "_scraped", return_value=_veri(kaynak)), \
             patch.object(dashboard_api, "_private_lessons_calendar_events", return_value=[]):
            client.get("/api/calendar")
        assert kaynak[0]["start"] == "2026-09-24T12:40:00Z"

    def test_birlesik_takvim_yerel_saat_kimlik_ayni(self, client):
        with patch.object(dashboard_api, "_scraped", return_value=_veri([dict(self.ETKINLIK)])):
            j = client.get("/api/calendar/unified").get_json()
        ev = next(e for e in j["events"] if e["type"] == "event")
        assert ev["start"] == "2026-09-24T12:40:00"
        assert ev["id"] == dashboard_api._make_id("event", self.ETKINLIK["title"], self.ETKINLIK["start"])


class TestKaziyiciSaatDilimi:
    """Where the "Z" really came from, found on 2026-09-24 after the host moved
    to Istanbul time: scrape_takvim reads FullCalendar's `e.startStr`, which is
    formatted in the *browser's* zone. Chrome ran on UTC, so wall-clock 12:40
    came out "12:40:00Z"; on Istanbul time the same event is "12:40:00+03:00".
    Both forms must read as the same local time, and give the same ids."""

    Z = "2026-10-23T09:00:00Z"
    IST = "2026-10-23T09:00:00+03:00"

    def test_iki_bicim_ayni_yerel_saat(self):
        assert dashboard_api._portal_yerel(self.Z) == "2026-10-23T09:00:00"
        assert dashboard_api._portal_yerel(self.IST) == "2026-10-23T09:00:00"

    def test_baska_ofset_istanbula_cevrilir(self):
        # Not seen in the data; a real offset is honoured, not stripped.
        assert dashboard_api._portal_yerel("2026-10-23T06:00:00+00:00") == "2026-10-23T09:00:00"

    def test_tarih_ve_bos_dokunulmaz(self):
        assert dashboard_api._portal_yerel("2026-10-23") == "2026-10-23"
        assert dashboard_api._portal_yerel("") == ""

    def test_sinav_kimligi_kaziyicinin_saat_diliminden_bagimsiz(self, client):
        ids = []
        for ham in (self.Z, self.IST):
            with patch.object(dashboard_api, "_scraped", return_value=_veri([_sinav(ham)])):
                ids.append(client.get("/api/exams").get_json()["exams"][0]["id"])
        assert ids[0] == ids[1]

    def test_birlesik_takvim_kimligi_de_sabit(self, client):
        ids = []
        for ham in (self.Z, self.IST):
            ev = {"title": "Kulüp", "start": ham, "end": ham, "allDay": False, "extendedProps": {}}
            with patch.object(dashboard_api, "_scraped", return_value=_veri([ev])):
                j = client.get("/api/calendar/unified").get_json()
            ids.append(next(e for e in j["events"] if e["type"] == "event")["id"])
        assert ids[0] == ids[1]
