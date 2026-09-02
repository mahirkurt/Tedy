"""Dashboard endpoints must present the same scraped rows the portal wrote."""
import os
import tempfile

from unittest.mock import patch

from src.course_names import normalize_course

os.environ["TEST_AUTH_BYPASS"] = "1"
import src.dashboard_api as dashboard_api
from src.dashboard_api import app


def _get_dashboard_response(endpoint, scraped_data):
    """Hit a dashboard endpoint with mocked scraped data and return JSON."""
    app.config["TESTING"] = True
    with tempfile.TemporaryDirectory() as tmp:
        with patch.multiple(
            dashboard_api,
            OUTPUT_DIR=tmp,
            PHOTO_HOMEWORK_FILE=os.path.join(tmp, "photo_homework.json"),
            STUDENT_DONE_FILE=os.path.join(tmp, "homework_student_done.json"),
            PRIVATE_LESSON_FILE=os.path.join(tmp, "private_lessons.json"),
        ), patch.object(dashboard_api, "_scraped", return_value=scraped_data):
            with app.test_client() as client:
                return client.get(endpoint).get_json()


def _homework_rows():
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


class TestHomeworkConsistency:
    def test_homework_count_matches_scraped_rows(self):
        rows = _homework_rows()
        data = _scraped_data_with_homework(rows)
        resp = _get_dashboard_response("/api/homework", data)
        assert len(resp["homework"]) == len(rows)

    def test_homework_course_normalization(self):
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
        resp = _get_dashboard_response("/api/homework", data)
        assert resp["homework"][0]["normalized_course"] == "Bilişim"
        assert normalize_course("Bilişim Teknolojileri") == "Bilişim"

    def test_homework_keeps_portal_attachment_urls(self):
        rows = [
            {
                "Ders Adı": "Matematik",
                "Ödev Başlığı": "Ekli",
                "Ödev Son Teslim Tarihi": "20.03.2026 12:00",
                "Ödev Durumu": "",
                "detail": {
                    "description": "desc",
                    "attachments": [
                        {"name": "proje_detay.pdf",
                         "url": "https://portal.ted.example/file1.pdf"},
                    ],
                },
            },
        ]
        data = _scraped_data_with_homework(rows)
        resp = _get_dashboard_response("/api/homework", data)
        atts = resp["homework"][0]["detail"]["attachments"]
        assert atts[0]["url"] == "https://portal.ted.example/file1.pdf"


class TestCalendarConsistency:
    def test_timed_and_allday_events_appear_in_dashboard(self):
        events = _takvim_events()
        data = {"takvim": events}
        resp = _get_dashboard_response("/api/calendar", data)
        timed = [e for e in resp["events"] if not e.get("allDay", False)]
        all_day = [e for e in resp["events"] if e.get("allDay", False)]
        assert len(timed) == 1
        assert timed[0]["title"] == "Veli Toplantisi"
        assert len(all_day) == 2


class TestGradesConsistency:
    def test_all_grades_shown_in_dashboard(self):
        grades = _grade_entries()
        data = {"gelisim_raporu": {"grades": grades}}
        resp = _get_dashboard_response("/api/grades", data)
        returned_grades = resp.get("grades", [])
        assert len(returned_grades) == 2
        mat = returned_grades[0]
        assert mat["2. Sınav"] == "-"
        assert mat["1. Sınav"] == "85"
        tur = returned_grades[1]
        assert tur["Performans"] == "-"
        assert tur["2. Sınav"] == "88"


class TestContentConsistency:
    def test_content_appears_in_dashboard(self):
        ders = _ders_icerikleri()
        data = {"ders_icerikleri": ders}
        resp = _get_dashboard_response("/api/content", data)
        assert "Matematik" in resp
        assert resp["Matematik"]["text"] == ders["Matematik"]["text"]
        assert "Fen Bilimleri" in resp
        assert resp["Fen Bilimleri"]["text"] == ders["Fen Bilimleri"]["text"]


class TestAnnouncementsConsistency:
    def test_announcements_appear_in_dashboard(self):
        ann = _announcements()
        data = {"duyurular": {"announcements": ann}}
        resp = _get_dashboard_response("/api/announcements", data)
        returned = resp.get("announcements", [])
        assert len(returned) == 2
        titles = {a["e-Posta Başlık"] for a in returned}
        assert titles == {"Karne Dagitimi", "Okul Gezisi"}
