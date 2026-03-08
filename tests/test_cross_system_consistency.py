"""Tests verifying data consistency between Classroom sync, Calendar sync, and Dashboard API.

These tests confirm that the same scraped data appears correctly across all three
output systems: Google Classroom (sync_to_classroom), Google Calendar (sync_to_google),
and the Flask dashboard (dashboard_api).
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, call

from src.sync_to_google import normalize_course

# Set up test auth bypass before importing dashboard_api
os.environ["TEST_AUTH_BYPASS"] = "1"
from src.dashboard_api import app


def _mock_service():
    """Build a mock Classroom API service following project conventions."""
    svc = MagicMock()
    svc.courses().courseWork().list().execute.return_value = {"courseWork": []}
    svc.courses().courseWork().create.return_value.execute.return_value = {"id": "cw1"}
    svc.courses().courseWork().patch.return_value.execute.return_value = {"id": "cw1"}
    svc.courses().announcements().create.return_value.execute.return_value = {"id": "ann1"}
    svc.courses().announcements().patch.return_value.execute.return_value = {"id": "ann1"}
    return svc


def _get_dashboard_response(endpoint, scraped_data):
    """Hit a dashboard endpoint with mocked scraped data and return JSON."""
    app.config["TESTING"] = True
    with patch("src.dashboard_api._scraped", return_value=scraped_data):
        with app.test_client() as client:
            return client.get(endpoint).get_json()


# ---------------------------------------------------------------------------
# Shared test data fixtures
# ---------------------------------------------------------------------------
def _homework_rows():
    """Standard homework rows used across consistency tests."""
    return [
        {
            "Ders Adı": "Matematik",
            "Ödev Başlığı": "Denklemler",
            "Ödev Son Teslim Tarihi": "15.03.2026 12:00",
            "Ödev Durumu": "Teslim Edilmedi",
            "detail": {
                "description": "Sayfa 45-50 arası soruları çözün.",
                "attachments": [],
            },
        },
        {
            "Ders Adı": "Bilişim Teknolojileri",
            "Ödev Başlığı": "Python Projesi",
            "Ödev Son Teslim Tarihi": "20.03.2026 17:00",
            "Ödev Durumu": "Teslim Edilmedi",
            "detail": {
                "description": "Basit bir hesap makinesi yazın.",
                "attachments": [
                    {"name": "proje_detay.pdf", "url": "https://portal.ted.example/file1.pdf"},
                ],
            },
        },
        {
            "Ders Adı": "Türkçe",
            "Ödev Başlığı": "Kompozisyon",
            "Ödev Son Teslim Tarihi": "18.03.2026 09:00",
            "Ödev Durumu": "Teslim Edildi",
            "detail": {
                "description": "Serbest konu, en az 300 kelime.",
                "attachments": [],
            },
        },
    ]


def _scraped_data_with_homework(rows=None):
    return {
        "odevlerim": {
            "summary": "3 aktif odev",
            "homework": {"rows": rows or _homework_rows()},
        },
    }


def _takvim_events():
    return [
        {
            "title": "Veli Toplantisi",
            "start": "2026-03-10T14:00:00+03:00",
            "end": "2026-03-10T16:00:00+03:00",
            "allDay": False,
        },
        {
            "title": "23 Nisan Kutlamalari",
            "start": "2026-04-23",
            "end": "2026-04-23",
            "allDay": True,
        },
        {
            "title": "Bilim Fuari",
            "start": "2026-05-01",
            "end": "2026-05-02",
            "allDay": True,
        },
    ]


def _grade_entries():
    return [
        {"Ders": "Matematik", "1. Sınav": "85", "2. Sınav": "-", "Performans": "90"},
        {"Ders": "Türkçe", "1. Sınav": "72", "2. Sınav": "88", "Performans": "-"},
    ]


def _ders_icerikleri():
    return {
        "Matematik": {"tab_id": "t1", "text": "Bu hafta denklemler konusu islendi."},
        "Fen Bilimleri": {"tab_id": "t2", "text": "Isik ve ses dalgalari."},
    }


def _announcements():
    return [
        {"e-Posta Başlık": "Karne Dagitimi", "Yayın Tarihi": "01.03.2026"},
        {"e-Posta Başlık": "Okul Gezisi", "Yayın Tarihi": "05.03.2026"},
    ]


# ===========================================================================
# TestHomeworkConsistency
# ===========================================================================
class TestHomeworkConsistency:

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_homework_count_matches_across_systems(self, _mock_retry):
        """sync_odevler processes the same number of rows as dashboard /api/homework returns."""
        rows = _homework_rows()
        data = _scraped_data_with_homework(rows)

        # --- Classroom side ---
        svc = _mock_service()
        courses = {"Matematik": "c1", "Bilişim": "c2", "Türkçe": "c3", "TED Genel": "c0"}
        state = {}
        from src.sync_to_classroom import sync_odevler
        result = sync_odevler(svc, courses, data, state)
        classroom_processed = result["added"] + result["updated"] + result["skipped"]

        # --- Dashboard side ---
        resp = _get_dashboard_response("/api/homework", data)
        dashboard_count = len(resp["homework"])

        assert classroom_processed == len(rows)
        assert dashboard_count == len(rows)
        assert classroom_processed == dashboard_count

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_homework_course_normalization_consistent(self, _mock_retry):
        """Both Classroom and Dashboard normalize 'Bilisim Teknolojileri' to 'Bilisim'."""
        rows = [
            {
                "Ders Adı": "Bilişim Teknolojileri",
                "Ödev Başlığı": "Test Odev",
                "Ödev Son Teslim Tarihi": "20.03.2026 12:00",
                "Ödev Durumu": "",
                "detail": {"description": "desc", "attachments": []},
            },
        ]
        data = _scraped_data_with_homework(rows)

        # --- Classroom: _resolve_course_id calls normalize_course ---
        from src.sync_to_classroom import _resolve_course_id
        courses = {"Bilişim": "c_bilisim", "TED Genel": "c0"}
        resolved_id = _resolve_course_id(courses, "Bilişim Teknolojileri")
        assert resolved_id == "c_bilisim"

        # --- Dashboard: adds normalized_course field ---
        resp = _get_dashboard_response("/api/homework", data)
        assert resp["homework"][0]["normalized_course"] == "Bilişim"

        # Both resolve to the same canonical name
        assert normalize_course("Bilişim Teknolojileri") == "Bilişim"

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_homework_with_drive_attachments(self, _mock_retry):
        """Classroom gets Drive materials when drive_uploads is provided;
        Dashboard returns raw attachment URLs regardless."""
        rows = [
            {
                "Ders Adı": "Matematik",
                "Ödev Başlığı": "Dosyali Odev",
                "Ödev Son Teslim Tarihi": "25.03.2026 12:00",
                "Ödev Durumu": "",
                "detail": {
                    "description": "Ekteki dosyayi inceleyin.",
                    "attachments": [
                        {"name": "odev.pdf", "url": "https://portal.ted.example/att1.pdf"},
                    ],
                },
            },
        ]
        data = _scraped_data_with_homework(rows)
        drive_uploads = {
            "https://portal.ted.example/att1.pdf": {
                "id": "drive123",
                "link": "https://drive.google.com/file/d/drive123/view",
                "ders": "Matematik",
            },
        }

        # --- Classroom: should include Drive link in materials ---
        svc = _mock_service()
        courses = {"Matematik": "c1", "TED Genel": "c0"}
        state = {}
        from src.sync_to_classroom import sync_odevler
        sync_odevler(svc, courses, data, state, drive_uploads=drive_uploads)

        create_call = svc.courses().courseWork().create
        create_call.assert_called_once()
        body = create_call.call_args[1]["body"]
        assert "materials" in body
        assert "drive.google.com" in body["materials"][0]["link"]["url"]

        # --- Dashboard: returns the raw portal URL in attachments ---
        resp = _get_dashboard_response("/api/homework", data)
        att = resp["homework"][0]["detail"]["attachments"][0]
        assert att["url"] == "https://portal.ted.example/att1.pdf"


# ===========================================================================
# TestCalendarConsistency
# ===========================================================================
class TestCalendarConsistency:

    def test_timed_events_appear_in_dashboard(self):
        """Dashboard /api/calendar returns all takvim events including timed ones."""
        events = _takvim_events()
        data = {"takvim": events}
        resp = _get_dashboard_response("/api/calendar", data)
        timed = [e for e in resp["events"] if not e.get("allDay", False)]
        assert len(timed) == 1
        assert timed[0]["title"] == "Veli Toplantisi"

    def test_allday_events_in_dashboard_but_not_calendar(self):
        """All-day events appear in dashboard but sync_takvim skips them."""
        events = _takvim_events()
        data = {"takvim": events, "ogep": {"sessions": {"rows": []}}}

        # --- Dashboard: returns all events ---
        resp = _get_dashboard_response("/api/calendar", data)
        all_day = [e for e in resp["events"] if e.get("allDay", False)]
        assert len(all_day) == 2

        # --- Calendar: sync_takvim skips all-day events ---
        from src.sync_to_google import sync_takvim
        cal_svc = MagicMock()
        cal_svc.events().insert.return_value.execute.return_value = {"id": "ev1"}
        existing = {}

        with patch("src.sync_to_google._api_call_with_retry", side_effect=lambda fn: fn()):
            sync_takvim(cal_svc, data, "cal123", existing)

        # Only the timed event should have been inserted
        insert_calls = cal_svc.events().insert.call_args_list
        assert len(insert_calls) == 1
        inserted_body = insert_calls[0][1]["body"]
        assert inserted_body["summary"] == "Veli Toplantisi"

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_all_takvim_events_reach_classroom_as_announcements(self, _mock_retry):
        """sync_duyurular creates announcements for ALL takvim events (timed + all-day)."""
        events = _takvim_events()
        data = {
            "takvim": events,
            "duyurular": {"announcements": []},
            "takim_calismalari": {"activities": {"rows": []}},
            "ogep": {"sessions": {"rows": []}},
        }

        svc = _mock_service()
        courses = {"TED Genel": "c_genel"}
        state = {}

        from src.sync_to_classroom import sync_duyurular
        result = sync_duyurular(svc, courses, data, state)

        # All 3 takvim events should generate announcement creates
        assert result["added"] == 3


# ===========================================================================
# TestGradesConsistency
# ===========================================================================
class TestGradesConsistency:

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_numeric_grades_go_to_classroom(self, _mock_retry):
        """sync_notlar creates courseWork for numeric scores like '85'."""
        data = {"gelisim_raporu": {"grades": _grade_entries()}}

        svc = _mock_service()
        courses = {"Matematik": "c1", "Türkçe": "c2", "TED Genel": "c0"}
        state = {}

        from src.sync_to_classroom import sync_notlar
        result = sync_notlar(svc, courses, data, state)

        # Numeric values: Matematik 85, 90; Turkce 72, 88 => 4 added
        assert result["added"] == 4

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_dash_grades_skipped_in_classroom(self, _mock_retry):
        """sync_notlar skips '-' grade values."""
        data = {"gelisim_raporu": {"grades": _grade_entries()}}

        svc = _mock_service()
        courses = {"Matematik": "c1", "Türkçe": "c2", "TED Genel": "c0"}
        state = {}

        from src.sync_to_classroom import sync_notlar
        result = sync_notlar(svc, courses, data, state)

        # "-" values: Matematik "2. Sinav" and Turkce "Performans" => 2 skipped
        assert result["skipped"] == 2

    def test_all_grades_shown_in_dashboard(self):
        """Dashboard /api/grades returns the full dict including '-' values."""
        grades = _grade_entries()
        data = {"gelisim_raporu": {"grades": grades}}

        resp = _get_dashboard_response("/api/grades", data)
        returned_grades = resp.get("grades", [])

        assert len(returned_grades) == 2
        # Dashboard preserves "-" values
        mat = returned_grades[0]
        assert mat["2. Sınav"] == "-"
        assert mat["1. Sınav"] == "85"

        tur = returned_grades[1]
        assert tur["Performans"] == "-"
        assert tur["2. Sınav"] == "88"


# ===========================================================================
# TestContentConsistency
# ===========================================================================
class TestContentConsistency:

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_content_creates_classroom_announcements(self, _mock_retry):
        """sync_ders_icerikleri creates an announcement for each course content entry."""
        data = {"ders_icerikleri": _ders_icerikleri()}

        svc = _mock_service()
        courses = {
            "Matematik": "c1", "Fen Bilimleri": "c2", "TED Genel": "c0",
        }
        state = {}

        from src.sync_to_classroom import sync_ders_icerikleri
        result = sync_ders_icerikleri(svc, courses, data, state)

        assert result["added"] == 2

    def test_content_appears_in_dashboard(self):
        """Dashboard /api/content returns the same ders_icerikleri dict."""
        ders = _ders_icerikleri()
        data = {"ders_icerikleri": ders}

        resp = _get_dashboard_response("/api/content", data)

        assert "Matematik" in resp
        assert resp["Matematik"]["text"] == ders["Matematik"]["text"]
        assert "Fen Bilimleri" in resp
        assert resp["Fen Bilimleri"]["text"] == ders["Fen Bilimleri"]["text"]


# ===========================================================================
# TestAnnouncementsConsistency
# ===========================================================================
class TestAnnouncementsConsistency:

    @patch("src.sync_to_classroom._api_call_with_retry", side_effect=lambda fn: fn())
    def test_announcements_reach_classroom(self, _mock_retry):
        """sync_duyurular creates Classroom announcements for duyurular.announcements."""
        ann = _announcements()
        data = {
            "duyurular": {"announcements": ann},
            "takvim": [],
            "takim_calismalari": {"activities": {"rows": []}},
            "ogep": {"sessions": {"rows": []}},
        }

        svc = _mock_service()
        courses = {"TED Genel": "c_genel"}
        state = {}

        from src.sync_to_classroom import sync_duyurular
        result = sync_duyurular(svc, courses, data, state)

        assert result["added"] == 2

    def test_announcements_appear_in_dashboard(self):
        """Dashboard /api/announcements returns the same items."""
        ann = _announcements()
        data = {"duyurular": {"announcements": ann}}

        resp = _get_dashboard_response("/api/announcements", data)
        returned = resp.get("announcements", [])

        assert len(returned) == 2
        titles = {a["e-Posta Başlık"] for a in returned}
        assert titles == {"Karne Dagitimi", "Okul Gezisi"}
