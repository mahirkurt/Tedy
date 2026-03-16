"""Integration tests for dashboard API endpoints."""
import os
import sys
from io import BytesIO
from unittest.mock import patch

import pytest
import requests as http_requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402

app = dashboard_api.app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def isolated_output(tmp_path, monkeypatch):
    """Isolate filesystem writes for API write-flow tests."""
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(
        dashboard_api,
        "PRIVATE_LESSON_FILE",
        os.path.join(str(tmp_path), "private_lessons.json"),
    )
    monkeypatch.setattr(
        dashboard_api,
        "STUDENT_DONE_FILE",
        os.path.join(str(tmp_path), "homework_student_done.json"),
    )
    monkeypatch.setattr(
        dashboard_api,
        "PHOTO_HOMEWORK_FILE",
        os.path.join(str(tmp_path), "photo_homework.json"),
    )
    return tmp_path


def _sample_homework_row(status="Değerlendirilmemiş"):
    return {
        "Ders Adı": "Matematik",
        "Ödev Başlığı": "Kesirler",
        "Ödev Son Teslim Tarihi": "15.03.2026 12:00",
        "Ödev Durumu": status,
        "detail": {"description": "Sayfa 10-12", "attachments": []},
    }


def _sample_scraped_homework(status="Değerlendirilmemiş"):
    return {
        "odevlerim": {
            "summary": "1 ödev",
            "homework": {"rows": [_sample_homework_row(status=status)]},
        }
    }


class TestAuthBypass:
    def test_schedule_without_login(self, client):
        resp = client.get("/api/schedule")
        assert resp.status_code == 200

    def test_auth_me_returns_test_user(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["email"] == "test@tedy.online"
        assert data["name"] == "Test User"


class TestScheduleEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/schedule")
        assert resp.status_code == 200

    def test_has_expected_keys(self, client):
        data = client.get("/api/schedule").get_json()
        assert "weeks" in data
        assert "latest" in data
        assert "today" in data

    def test_weeks_is_list(self, client):
        data = client.get("/api/schedule").get_json()
        assert isinstance(data["weeks"], list)


class TestHomeworkEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/homework")
        assert resp.status_code == 200

    def test_has_expected_keys(self, client):
        data = client.get("/api/homework").get_json()
        assert "summary" in data
        assert "homework" in data


class TestHomeworkMarkDoneEndpoint:
    def test_requires_identifier(self, client):
        resp = client.post("/api/homework/mark-done", json={})
        assert resp.status_code == 400
        assert "gerekli" in resp.get_json()["error"]

    def test_returns_404_when_homework_not_found(
        self, client, isolated_output
    ):
        with patch(
            "src.dashboard_api._scraped",
            return_value=_sample_scraped_homework(),
        ):
            resp = client.post(
                "/api/homework/mark-done",
                json={
                    "Ödev Başlığı": "Bilinmeyen Ödev",
                    "Ödev Son Teslim Tarihi": "20.03.2026 12:00",
                    "Ders Adı": "Matematik",
                },
            )
        assert resp.status_code == 404

    def test_marks_homework_done_by_key(self, client, isolated_output):
        scraped = _sample_scraped_homework(status="Değerlendirilmemiş")
        row = scraped["odevlerim"]["homework"]["rows"][0]
        key = dashboard_api._homework_row_key(row)

        with patch("src.dashboard_api._scraped", return_value=scraped):
            resp = client.post(
                "/api/homework/mark-done",
                json={"homework_key": key},
            )
            assert resp.status_code == 200
            assert resp.get_json()["ok"] is True

        with patch("src.dashboard_api._scraped", return_value=scraped):
            listing = client.get("/api/homework").get_json()
        assert listing["homework"][0]["student_marked_done"] is True

    def test_skips_when_teacher_status_already_resolved(
        self, client, isolated_output
    ):
        scraped = _sample_scraped_homework(status="Yaptı")
        row = scraped["odevlerim"]["homework"]["rows"][0]
        key = dashboard_api._homework_row_key(row)

        with patch("src.dashboard_api._scraped", return_value=scraped):
            resp = client.post(
                "/api/homework/mark-done",
                json={"homework_key": key},
            )

        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["ok"] is True
        assert payload["skipped"] is True
        assert payload["reason"] == "teacher_status_resolved"


class TestHomeworkPhotoEndpoint:
    def test_missing_photo_returns_400(self, client):
        resp = client.post("/api/homework/photo", data={})
        assert resp.status_code == 400

    def test_rejects_non_image_file(self, client):
        resp = client.post(
            "/api/homework/photo",
            data={"photo": (BytesIO(b"abc"), "note.txt", "text/plain")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_rejects_empty_image(self, client):
        resp = client.post(
            "/api/homework/photo",
            data={"photo": (BytesIO(b""), "hw.png", "image/png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_rejects_too_large_image(self, client, monkeypatch):
        monkeypatch.setattr(dashboard_api, "MAX_PHOTO_SIZE_BYTES", 1)
        resp = client.post(
            "/api/homework/photo",
            data={"photo": (BytesIO(b"12"), "hw.png", "image/png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 413

    def test_rejects_invalid_source_type(self, client):
        resp = client.post(
            "/api/homework/photo",
            data={
                "photo": (BytesIO(b"img"), "hw.png", "image/png"),
                "source_type": "invalid",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_private_source_requires_private_lesson_id(self, client):
        resp = client.post(
            "/api/homework/photo",
            data={
                "photo": (BytesIO(b"img"), "hw.png", "image/png"),
                "source_type": "private",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        ("error", "expected_status"),
        [
            (RuntimeError("ai runtime"), 503),
            (http_requests.HTTPError("ai http"), 502),
            (Exception("unknown"), 500),
        ],
    )
    def test_maps_ai_errors_to_status(self, client, error, expected_status):
        with patch(
            "src.dashboard_api._extract_homework_candidates_from_photo",
            side_effect=error,
        ):
            resp = client.post(
                "/api/homework/photo",
                data={"photo": (BytesIO(b"img"), "hw.png", "image/png")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == expected_status

    def test_success_and_dedup_behavior(self, client, isolated_output):
        candidates = [
            {
                "ders_adi": "Matematik",
                "odev_basligi": "Kesirler Tekrar",
                "odev_kaynagi": "TED Connect",
                "son_teslim_tarihi": "16.03.2026 18:00",
                "odev_durumu": "Değerlendirilmemiş",
                "aciklama": "Defter soruları",
            }
        ]
        with patch(
            "src.dashboard_api._scraped",
            return_value={"odevlerim": {"homework": {"rows": []}}},
        ):
            with patch(
                "src.dashboard_api._extract_homework_candidates_from_photo",
                return_value=candidates,
            ):
                first = client.post(
                    "/api/homework/photo",
                    data={"photo": (BytesIO(b"img"), "hw.png", "image/png")},
                    content_type="multipart/form-data",
                )
                second = client.post(
                    "/api/homework/photo",
                    data={"photo": (BytesIO(b"img"), "hw.png", "image/png")},
                    content_type="multipart/form-data",
                )

        first_payload = first.get_json()
        second_payload = second.get_json()
        assert first.status_code == 200
        assert first_payload["added_count"] == 1
        assert first_payload["skipped_count"] == 0
        assert second.status_code == 200
        assert second_payload["added_count"] == 0
        assert second_payload["skipped_count"] == 1


class TestPrivateLessonsEndpoint:
    def test_get_returns_lessons_key(self, client, isolated_output):
        resp = client.get("/api/private-lessons")
        assert resp.status_code == 200
        assert "lessons" in resp.get_json()

    def test_create_requires_course(self, client, isolated_output):
        resp = client.post(
            "/api/private-lessons",
            json={
                "teacher": "Öğretmen",
                "is_recurring": True,
                "weekday": "Pazartesi",
                "start_time": "18:00",
                "end_time": "19:00",
            },
        )
        assert resp.status_code == 400

    def test_create_rejects_invalid_time_format(self, client, isolated_output):
        resp = client.post(
            "/api/private-lessons",
            json={
                "course": "Matematik",
                "teacher": "Öğretmen",
                "is_recurring": True,
                "weekday": "Pazartesi",
                "start_time": "99:00",
                "end_time": "19:00",
            },
        )
        assert resp.status_code == 400

    def test_create_recurring_requires_weekday(self, client, isolated_output):
        resp = client.post(
            "/api/private-lessons",
            json={
                "course": "Matematik",
                "teacher": "Öğretmen",
                "is_recurring": True,
                "weekday": "",
                "start_time": "18:00",
                "end_time": "19:00",
            },
        )
        assert resp.status_code == 400

    def test_create_single_lesson_requires_valid_date(
        self, client, isolated_output
    ):
        resp = client.post(
            "/api/private-lessons",
            json={
                "course": "Matematik",
                "teacher": "Öğretmen",
                "is_recurring": False,
                "date": "2026/03/12",
                "start_time": "18:00",
                "end_time": "19:00",
            },
        )
        assert resp.status_code == 400

    def test_create_success_persists_and_lists(self, client, isolated_output):
        create_resp = client.post(
            "/api/private-lessons",
            json={
                "course": "Bilişim Teknolojileri",
                "teacher": "A. Öğretmen",
                "is_recurring": True,
                "weekday": "Pazartesi",
                "start_time": "18:00",
                "end_time": "19:00",
            },
        )
        assert create_resp.status_code == 200
        payload = create_resp.get_json()
        assert payload["ok"] is True
        assert payload["lesson"]["course"] == "Bilişim"
        assert payload["lesson"]["active"] is True

        list_resp = client.get("/api/private-lessons")
        lessons = list_resp.get_json()["lessons"]
        assert len(lessons) == 1
        assert lessons[0]["teacher"] == "A. Öğretmen"


class TestGradesEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/grades")
        assert resp.status_code == 200


class TestCalendarEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/calendar")
        assert resp.status_code == 200

    def test_has_events_key(self, client):
        data = client.get("/api/calendar").get_json()
        assert "events" in data


class TestUnifiedCalendarEndpoint:
    def test_returns_aggregated_event_types(self, client):
        scraped = {
            "ders_programi": [
                {
                    "schedule": {
                        "rows": [
                            ["", "Pazartesi"],
                            [
                                "1. Ders\n08:00 - 08:40",
                                "Matematik\nA Öğretmen",
                            ],
                        ]
                    }
                }
            ],
            "odevlerim": {
                "homework": {
                    "rows": [
                        {
                            "Ders Adı": "Matematik",
                            "Ödev Başlığı": "Kesirler",
                            "Ödev Son Teslim Tarihi": "15.03.2026 12:00",
                            "Ödev Durumu": "Teslim Edilmedi",
                        }
                    ]
                }
            },
            "ogep": {
                "sessions": {
                    "rows": [
                        {
                            "ÖGEP (Öğrenci Gelişim Programı)": "Etüt",
                            "Çalışma Başlangıç": "14.03.2026 10:00",
                            "Çalışma Bitiş": "14.03.2026 11:00",
                            "Katılım Durumu": "Bekliyor",
                        }
                    ]
                }
            },
            "takim_calismalari": {
                "activities": {
                    "rows": [
                        {
                            "Academy+": "Robotik",
                            "Çalışma Başlangıç": "14.03.2026 13:00",
                            "Çalışma Bitiş": "14.03.2026 14:00",
                            "Katılım Durumu": "Bekliyor",
                        }
                    ]
                }
            },
            "takvim": [
                {
                    "title": "Veli Toplantısı",
                    "start": "2026-03-14T15:00:00",
                    "end": "2026-03-14T16:00:00",
                }
            ],
        }
        with patch("src.dashboard_api._scraped", return_value=scraped):
            resp = client.get("/api/calendar/unified")

        assert resp.status_code == 200
        payload = resp.get_json()
        assert "events" in payload
        assert isinstance(payload["events"], list)
        event_types = {e.get("type") for e in payload["events"]}
        assert {
            "lesson",
            "homework",
            "ogep",
            "team",
            "event",
        }.issubset(event_types)


class TestTeamsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/teams")
        assert resp.status_code == 200

    def test_has_expected_keys(self, client):
        data = client.get("/api/teams").get_json()
        assert "activities" in data
        assert "ogep" in data


class TestContentEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/content")
        assert resp.status_code == 200


class TestAnnouncementsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/announcements")
        assert resp.status_code == 200

    def test_has_announcements_key(self, client):
        data = client.get("/api/announcements").get_json()
        assert "announcements" in data


class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_fills_default_health_fields(self, client):
        with patch("src.dashboard_api._load_json", return_value={}):
            with patch(
                "src.dashboard_api._scraped",
                return_value={"scraped_at": "2026-03-12T10:00:00+00:00"},
            ):
                resp = client.get("/api/health")

        assert resp.status_code == 200
        payload = resp.get_json()
        assert "timestamp" in payload
        assert "success" in payload
        assert "scrape_errors" in payload
        assert "duration_seconds" in payload
        assert "staleness" in payload
        assert isinstance(payload["staleness"].get("stale_sections"), list)


class TestProgressEndpoints:
    def test_ec_returns_200(self, client):
        resp = client.get("/api/progress/ec")
        assert resp.status_code == 200

    def test_a3k_returns_200(self, client):
        resp = client.get("/api/progress/a3k")
        assert resp.status_code == 200


class TestSebitEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/sebit")
        assert resp.status_code == 200


class TestStaticServing:
    def test_root_serves_something(self, client):
        resp = client.get("/")
        # Either serves SPA (200) or returns "not built" message (404)
        assert resp.status_code in (200, 404)
