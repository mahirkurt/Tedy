"""Integration tests for dashboard API endpoints."""
import json
import os
import sys
from datetime import datetime
from io import BytesIO
from unittest.mock import Mock, patch

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
def client_no_auth(monkeypatch):
    """A client with TEST_AUTH_BYPASS disabled, for exercising real auth gates.

    Mirrors the inline `monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS",
    False)` pattern already used ad hoc in this file and in
    test_assistant_api.py, as a reusable fixture — request has no session and
    no API key, so anything behind @require_auth must refuse it.
    """
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
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


class TestCurrentUserRoleFailsClosed:
    """H2: no session email must yield least privilege, not full access.

    Every call site today sits behind a `session.get("user_email")` check,
    so this default is currently unreached in practice — but a future
    caller outside that guard must not silently get ROLE_FULL.
    """

    def test_no_session_email_defaults_to_reader(self):
        with app.test_request_context():
            assert dashboard_api._current_user_role() == dashboard_api.ROLE_READER

    def test_known_full_access_email_is_unaffected(self):
        with app.test_request_context():
            from flask import session as flask_session

            flask_session["user_email"] = "drmahirkurt@gmail.com"
            assert dashboard_api._current_user_role() == dashboard_api.ROLE_FULL

    def test_off_roster_email_is_still_reader(self):
        with app.test_request_context():
            from flask import session as flask_session

            flask_session["user_email"] = "stranger@example.com"
            assert dashboard_api._current_user_role() == dashboard_api.ROLE_READER


class TestSessionCookieHardening:
    """H4: session cookie flags. The site is served over HTTPS."""

    def test_defaults(self):
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        assert app.config["SESSION_COOKIE_SECURE"] is True

    def test_dashboard_cookie_secure_env_var_flips_only_that_flag(self, monkeypatch):
        monkeypatch.setenv("DASHBOARD_COOKIE_SECURE", "0")
        dashboard_api._apply_cookie_config(app)
        try:
            assert app.config["SESSION_COOKIE_SECURE"] is False
            # The other two flags are not driven by this variable at all.
            assert app.config["SESSION_COOKIE_HTTPONLY"] is True
            assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        finally:
            monkeypatch.delenv("DASHBOARD_COOKIE_SECURE", raising=False)
            dashboard_api._apply_cookie_config(app)  # restore the default


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

    def test_missing_date_is_not_invented(self):
        row = dashboard_api._to_photo_homework_row(
            {
                "ders_adi": "DKAB",
                "odev_basligi": "Sayfa 4",
                "odev_kaynagi": "Fasikül",
                "son_teslim_tarihi": "",
                "aciklama": "Kaynak: TED Connect\n1-5. sorular",
            },
            image_hash="abc",
            selected_course="Matematik",
        )
        assert row["Ders Adı"] == "Din Kültürü"
        assert row["Ödev Son Teslim Tarihi"] == ""
        assert row["detail"]["description"] == "1-5. sorular"
        assert row["Ödev Kaynağı"] == "Fotoğraf · Fasikül"
        assert row["odev_kaynagi"] == "Fasikül"
        assert row["source"] == "photo_ai_ted"

    def test_confirmed_private_course_is_the_edited_one(self):
        lesson = {"id": "abc", "course": "Matematik", "teacher": "Ayşe"}
        candidate = {"ders_adi": "Türkçe", "odev_basligi": "Okuma", "son_teslim_tarihi": ""}
        preview = dashboard_api._to_photo_homework_row(
            candidate, image_hash="h", source_type="private", private_lesson=lesson,
        )
        confirmed = dashboard_api._to_photo_homework_row(
            candidate, image_hash="h", source_type="private",
            private_lesson=lesson, confirmed=True,
        )
        assert preview["Ders Adı"] == "Matematik"
        assert confirmed["Ders Adı"] == "Türkçe"

    def test_preview_writes_nothing(self, client, isolated_output):
        candidates = [{
            "ders_adi": "Türkçe",
            "odev_basligi": "Okuma",
            "son_teslim_tarihi": "",
            "aciklama": "günlük",
        }]
        with patch(
            "src.dashboard_api._extract_homework_candidates_from_photo",
            return_value=candidates,
        ):
            resp = client.post(
                "/api/homework/photo",
                data={
                    "photo": (BytesIO(b"img"), "hw.png", "image/png"),
                    "stage": "preview",
                },
                content_type="multipart/form-data",
            )
        payload = resp.get_json()
        assert resp.status_code == 200
        assert payload["preview"] is True
        assert payload["homework"][0]["Ödev Başlığı"] == "Okuma"
        assert payload["homework"][0]["Ödev Son Teslim Tarihi"] == ""
        assert not (isolated_output / "photo_homework.json").exists()

    def test_commit_stores_the_confirmed_row_without_rereading(self, client, isolated_output):
        with patch(
            "src.dashboard_api._extract_homework_candidates_from_photo",
            side_effect=AssertionError("commit must not call the model"),
        ):
            resp = client.post(
                "/api/homework/photo",
                data={
                    "stage": "commit",
                    "photo_hash": "abc123",
                    "homework": json.dumps([{
                        "Ders Adı": "DKAB",
                        "Ödev Başlığı": "Sayfa 4",
                        "Ödev Son Teslim Tarihi": "",
                        "detail": {"description": "1-5"},
                    }]),
                },
                content_type="multipart/form-data",
            )
        payload = resp.get_json()
        assert resp.status_code == 200
        assert payload["added_count"] == 1
        stored = payload["homework"][0]
        assert stored["Ders Adı"] == "Din Kültürü"
        assert stored["Ödev Son Teslim Tarihi"] == ""
        assert stored["detail"]["description"] == "1-5"
        assert stored["photo_hash"] == "abc123"
        assert (isolated_output / "photo_homework.json").exists()

    def test_commit_keeps_the_book_name(self, client, isolated_output):
        resp = client.post(
            "/api/homework/photo",
            data={
                "stage": "commit",
                "photo_hash": "abc123",
                "homework": json.dumps([{
                    "Ders Adı": "Türkçe",
                    "Ödev Başlığı": "Okuma",
                    "Ödev Son Teslim Tarihi": "1.10.2026",
                    "odev_kaynagi": "Fasikül",
                    "detail": {"description": "günlük"},
                }]),
            },
            content_type="multipart/form-data",
        )
        stored = resp.get_json()["homework"][0]
        assert resp.status_code == 200
        assert stored["Ödev Kaynağı"] == "Fotoğraf · Fasikül"
        assert stored["Ödev Son Teslim Tarihi"] == "01.10.2026 23:59"
        assert stored["odev_kaynagi"] == "Fasikül"

    def test_commit_rejects_an_unparsed_date(self, client, isolated_output):
        resp = client.post(
            "/api/homework/photo",
            data={
                "stage": "commit",
                "homework": json.dumps([{
                    "Ders Adı": "Türkçe",
                    "Ödev Başlığı": "Okuma",
                    "Ödev Son Teslim Tarihi": "yarın",
                    "detail": {"description": ""},
                }]),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "gün.ay.yıl" in resp.get_json()["error"]
        assert not (isolated_output / "photo_homework.json").exists()

    def test_commit_remembers_an_unknown_date(self, client, isolated_output):
        resp = client.post(
            "/api/homework/photo",
            data={
                "stage": "commit",
                "homework": json.dumps([{
                    "Ders Adı": "Türkçe",
                    "Ödev Başlığı": "Okuma",
                    "Ödev Son Teslim Tarihi": "",
                    "eksik_birakilan": ["teslim", "uydurma"],
                    "detail": {"description": "günlük"},
                }]),
            },
            content_type="multipart/form-data",
        )
        stored = resp.get_json()["homework"][0]
        assert resp.status_code == 200
        assert stored["eksik_birakilan"] == ["teslim"]
        assert stored["Ödev Son Teslim Tarihi"] == ""

    def test_assistant_writes_the_readers_date_and_refuses_a_portal_row(self, isolated_output):
        row = dashboard_api._to_photo_homework_row(
            {"ders_adi": "Genel", "odev_basligi": "Sayfa 4", "son_teslim_tarihi": ""},
            image_hash="h",
        )
        dashboard_api._save_photo_homework_rows([row])
        key = dashboard_api._homework_row_key(row)
        simdi = datetime(2026, 9, 24, 16, 10)
        dashboard_api._foto_odev_tamamla(key, "teslim", "bilmiyorum", simdi=simdi)
        stored = dashboard_api._load_photo_homework_rows()[0]
        assert stored["Ödev Son Teslim Tarihi"] == ""
        assert stored["eksik_birakilan"] == ["teslim"]

        cumle = dashboard_api._foto_odev_tamamla(key, "teslim", "2 ekim", simdi=simdi)
        assert "02.10.2026 23:59" in cumle
        stored = dashboard_api._load_photo_homework_rows()[0]
        assert stored["Ödev Son Teslim Tarihi"] == "02.10.2026 23:59"
        assert stored["eksik_birakilan"] == []

        yeni = dashboard_api._homework_row_key(stored)
        dashboard_api._foto_odev_tamamla(yeni, "ders", "DKAB", simdi=simdi)
        stored = dashboard_api._load_photo_homework_rows()[0]
        assert stored["Ders Adı"] == "Din Kültürü"

        with pytest.raises(ValueError, match="fotoğraftan"):
            dashboard_api._foto_odev_tamamla("matematik|kesirler|15.03.2026 12:00", "teslim", "yarın")


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


class TestApiKeyAuth:
    """Tests for API key authentication (header and query param)."""

    @pytest.fixture(autouse=True)
    def _disable_test_bypass(self, monkeypatch):
        """Disable TEST_AUTH_BYPASS so we can test real auth paths."""
        monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)

    @pytest.fixture
    def valid_key(self, monkeypatch):
        key = "tdyK_test-valid-key-for-unit-tests"
        monkeypatch.setattr(dashboard_api, "API_KEYS", [("test", key)])
        return key

    def test_bearer_header_grants_access(self, client, valid_key):
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": f"Bearer {valid_key}"},
        )
        assert resp.status_code == 200

    def test_query_param_grants_access(self, client, valid_key):
        resp = client.get(f"/api/schedule?api_key={valid_key}")
        assert resp.status_code == 200

    def test_invalid_key_returns_401(self, client, valid_key):
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": "Bearer tdyK_wrong-key"},
        )
        assert resp.status_code == 401

    def test_no_auth_returns_401(self, client, monkeypatch):
        monkeypatch.setattr(dashboard_api, "API_KEYS", [])
        resp = client.get("/api/schedule")
        assert resp.status_code == 401

    def test_non_tdyk_prefix_rejected(self, client, valid_key):
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": "Bearer not-a-valid-prefix-key"},
        )
        assert resp.status_code == 401

    def test_empty_api_keys_disables_key_auth(self, client, monkeypatch):
        monkeypatch.setattr(dashboard_api, "API_KEYS", [])
        resp = client.get(
            "/api/schedule",
            headers={"Authorization": "Bearer tdyK_anything"},
        )
        assert resp.status_code == 401


class TestBooksApi:
    """Tedy Books — the shelf is driven purely by what is on disk."""

    @pytest.fixture
    def shelf(self, tmp_path, monkeypatch):
        """A two-chapter book whose second chapter is declared but not written."""
        import json

        book = tmp_path / "ornek-kitap"
        book.mkdir()
        (book / "book.json").write_text(
            json.dumps({
                "slug": "ornek-kitap",
                "title": "Örnek Kitap",
                "author": "Bir Yazar",
                "language": "en",
                "chapters": [
                    {"id": "B01", "order": 1, "volume": "BİRİNCİ CİLT",
                     "part": "BİRİNCİ KİTAP", "numeral": "I",
                     "label": "Bölüm I", "title": "İlk Bölüm"},
                    {"id": "B02", "order": 2, "volume": "BİRİNCİ CİLT",
                     "part": "BİRİNCİ KİTAP", "numeral": "II",
                     "label": "Bölüm II", "title": "İkinci Bölüm"},
                ],
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        (book / "B01_Ilk_Bolum.md").write_text(
            "# BİRİNCİ KİTAP\n\n## BÖLÜM I — İLK BÖLÜM\n\n*künye satırı*\n\n---\n\nGövde metni.\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(dashboard_api, "BOOKS_DIR", str(tmp_path))
        return book

    def test_list_reports_available_vs_declared(self, client, shelf):
        resp = client.get("/api/books")
        assert resp.status_code == 200
        books = resp.get_json()["books"]
        assert len(books) == 1
        assert books[0]["slug"] == "ornek-kitap"
        assert books[0]["language"] == "en"
        assert books[0]["totalChapters"] == 2
        assert books[0]["availableChapters"] == 1

    def test_detail_marks_missing_chapter_unavailable(self, client, shelf):
        resp = client.get("/api/books/ornek-kitap")
        assert resp.status_code == 200
        chapters = resp.get_json()["chapters"]
        assert [c["available"] for c in chapters] == [True, False]
        assert chapters[0]["words"] > 0

    def test_chapter_strips_front_matter(self, client, shelf):
        resp = client.get("/api/books/ornek-kitap/chapters/B01")
        assert resp.status_code == 200
        payload = resp.get_json()
        assert payload["chapter"]["content"].strip() == "Gövde metni."
        assert payload["chapter"]["credit"] == "künye satırı"
        assert payload["chapter"]["partHeading"] == "BİRİNCİ KİTAP"
        assert payload["prev"] is None
        assert payload["next"] is None

    def test_declared_but_unwritten_chapter_is_404(self, client, shelf):
        assert client.get("/api/books/ornek-kitap/chapters/B02").status_code == 404

    def test_dropping_a_file_publishes_the_chapter(self, client, shelf):
        (shelf / "B02_Ikinci_Bolum.md").write_text("İkinci gövde.\n", encoding="utf-8")

        assert client.get("/api/books/ornek-kitap").get_json()["availableChapters"] == 2

        first = client.get("/api/books/ornek-kitap/chapters/B01").get_json()
        assert first["next"]["id"] == "B02"
        assert first["position"] == {"index": 1, "total": 2}

        second = client.get("/api/books/ornek-kitap/chapters/B02").get_json()
        assert second["prev"]["id"] == "B01"
        assert second["chapter"]["title"] == "İkinci Bölüm"

    def test_unlisted_markdown_still_shows_up(self, client, shelf):
        (shelf / "Ek_Notlar.md").write_text("Ek metin.\n", encoding="utf-8")
        chapters = client.get("/api/books/ornek-kitap").get_json()["chapters"]
        extra = [c for c in chapters if c["id"] == "Ek_Notlar"]
        assert len(extra) == 1
        assert extra[0]["available"] is True

    def test_unknown_book_is_404(self, client, shelf):
        assert client.get("/api/books/olmayan-kitap").status_code == 404

    @pytest.mark.parametrize("slug", ["..", "../etc", "Ornek-Kitap", "ornek_kitap"])
    def test_slug_traversal_and_case_rejected(self, client, shelf, slug):
        assert client.get(f"/api/books/{slug}").status_code == 404

    def test_chapter_id_cannot_escape_book_dir(self, client, shelf, tmp_path):
        (tmp_path / "gizli.md").write_text("sır", encoding="utf-8")
        assert client.get("/api/books/ornek-kitap/chapters/..%2Fgizli").status_code == 404

    def test_ruleless_front_matter_is_stripped(self, client, shelf):
        """`### BÖLÜM III` + a bare shouted title, no rule — the other house style."""
        (shelf / "B02_Ikinci_Bolum.md").write_text(
            "### BÖLÜM II\n\nİKİNCİ BÖLÜM\n\n\"Gövde burada başlar,\" dedi Gandalf.\n",
            encoding="utf-8",
        )
        chapter = client.get("/api/books/ornek-kitap/chapters/B02").get_json()["chapter"]
        assert chapter["content"].strip() == '"Gövde burada başlar," dedi Gandalf.'

    def test_part_heading_falls_back_to_manifest(self, client, shelf):
        (shelf / "B02_Ikinci_Bolum.md").write_text(
            "### BÖLÜM II\n\nGövde.\n", encoding="utf-8"
        )
        chapter = client.get("/api/books/ornek-kitap/chapters/B02").get_json()["chapter"]
        assert chapter["partHeading"] == "BİRİNCİ KİTAP"

    def test_prose_opening_is_never_stripped(self, client, shelf):
        """A chapter that dives straight into prose must survive intact."""
        body = "Söylentiler ne dokuz, ne de doksan dokuz günde dindi.\n\nİkinci paragraf.\n"
        (shelf / "B02_Ikinci_Bolum.md").write_text(body, encoding="utf-8")
        chapter = client.get("/api/books/ornek-kitap/chapters/B02").get_json()["chapter"]
        assert chapter["content"] == body

    def test_shouted_opening_line_without_heading_is_body(self, client, shelf):
        """All-caps only counts as a title when a heading introduced it."""
        body = "HAYIR\n\ndiye bağırdı Frodo.\n"
        (shelf / "B02_Ikinci_Bolum.md").write_text(body, encoding="utf-8")
        chapter = client.get("/api/books/ornek-kitap/chapters/B02").get_json()["chapter"]
        assert chapter["content"] == body

    def test_book_without_manifest_is_still_readable(self, client, tmp_path, monkeypatch):
        bare = tmp_path / "sade-kitap"
        bare.mkdir()
        (bare / "B01_Giris.md").write_text("Sade gövde.\n", encoding="utf-8")
        monkeypatch.setattr(dashboard_api, "BOOKS_DIR", str(tmp_path))

        listing = client.get("/api/books").get_json()["books"]
        assert listing[0]["slug"] == "sade-kitap"
        assert listing[0]["availableChapters"] == 1

        chapter = client.get("/api/books/sade-kitap/chapters/B01_Giris").get_json()
        assert chapter["chapter"]["content"].strip() == "Sade gövde."


class TestBookTranslationApi:
    def test_uses_deepl_with_sentence_context_first(
        self, client, monkeypatch
    ):
        monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")
        provider_response = Mock()
        provider_response.json.return_value = {
            "translations": [
                {"detected_source_language": "EN", "text": "tünel"}
            ]
        }

        with patch(
            "src.dashboard_api.http_requests.post",
            return_value=provider_response,
        ) as provider_post, patch(
            "src.dashboard_api.http_requests.get"
        ) as provider_get:
            response = client.post(
                "/api/books/translate",
                json={
                    "text": "tunnel",
                    "context": "The hall was like a tunnel.",
                },
            )

        assert response.status_code == 200
        assert response.get_json() == {
            "sourceText": "tunnel",
            "translatedText": "tünel",
            "sourceLanguage": "en",
            "targetLanguage": "tr",
            "provider": "DeepL",
        }
        provider_post.assert_called_once_with(
            "https://api-free.deepl.com/v2/translate",
            headers={"Authorization": "DeepL-Auth-Key test-key:fx"},
            json={
                "text": ["tunnel"],
                "source_lang": "EN",
                "target_lang": "TR",
                "context": "The hall was like a tunnel.",
            },
            timeout=8,
        )
        provider_get.assert_not_called()

    def test_falls_back_to_claude_when_deepl_fails(
        self, client, monkeypatch
    ):
        # The middle step was Gemini until 2026-09-24; the Gemini API terms
        # forbid services likely to be used by under-18s.
        import src.dashboard_api as api
        from types import SimpleNamespace as NS
        monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")
        istekler = []

        def create(**kw):
            istekler.append(kw)
            prompt = kw["messages"][0]["content"]
            translated = "tünel" if "dictionary headword" in prompt else "tünel gibiydi"
            return NS(content=[NS(type="text", text=translated)], stop_reason="end_turn")

        monkeypatch.setattr(api.claude_api, "istemci",
                            lambda **k: NS(messages=NS(create=create)))
        with patch(
            "src.dashboard_api.http_requests.post",
            side_effect=http_requests.RequestException("deepl unavailable"),
        ) as post_request, patch(
            "src.dashboard_api.http_requests.get"
        ) as provider_get:
            response = client.post(
                "/api/books/translate",
                json={
                    "text": "tunnel",
                    "context": "The hall was like a tunnel.",
                },
            )

        assert response.status_code == 200
        assert response.get_json()["translatedText"] == "tünel"
        assert response.get_json()["provider"] == "Claude Sonnet 5"
        # DeepL over HTTP; Claude through its SDK.
        assert post_request.call_count == 1
        assert istekler[0]["model"] == "claude-sonnet-5"
        assert istekler[0]["output_config"] == {"effort": "low"}
        assert not {"temperature", "top_p", "top_k"} & set(istekler[0])
        prompt = istekler[0]["messages"][0]["content"]
        assert '"tunnel"' in prompt
        assert '"The hall was like a tunnel."' in prompt
        provider_get.assert_not_called()

    def test_falls_back_to_contextual_mymemory_after_deepl_and_claude(
        self, client, monkeypatch
    ):
        import anthropic
        import src.dashboard_api as api
        from types import SimpleNamespace as NS
        from unittest.mock import Mock as _Mock
        monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")

        def claude_down(**kw):
            raise anthropic.APIConnectionError(request=_Mock())

        # An SDK error is not one the chain used to catch; it must still fall
        # through to MyMemory rather than surface as a 500.
        monkeypatch.setattr(api.claude_api, "istemci",
                            lambda **k: NS(messages=NS(create=claude_down)))
        provider_payload = {
            "responseData": {
                "translatedText": "Salon bir tünel gibiydi."
            }
        }

        with patch(
            "src.dashboard_api.http_requests.post",
            side_effect=http_requests.RequestException("provider unavailable"),
        ) as provider_post, patch(
            "src.dashboard_api.http_requests.get"
        ) as provider_get:
            provider_get.return_value.json.return_value = provider_payload
            response = client.post(
                "/api/books/translate",
                json={
                    "text": "tunnel",
                    "context": "The hall was like a tunnel.",
                },
            )

        assert response.status_code == 200
        assert response.get_json()["translatedText"] == "Salon bir tünel gibiydi."
        assert response.get_json()["provider"] == "MyMemory"
        assert provider_post.call_count == 1
        provider_get.assert_called_once_with(
            "https://api.mymemory.translated.net/get",
            params={
                "q": "The hall was like a tunnel.",
                "langpair": "en|tr",
                "mt": "1",
            },
            timeout=8,
        )

    def test_rejects_selection_larger_than_provider_limit(self, client):
        with patch("src.dashboard_api.http_requests.post") as provider_post, patch(
            "src.dashboard_api.http_requests.get"
        ) as provider_get:
            response = client.post(
                "/api/books/translate",
                json={"text": "a" * 501},
            )

        assert response.status_code == 413
        assert response.get_json() == {"error": "selection_too_long", "maxBytes": 500}
        provider_post.assert_not_called()
        provider_get.assert_not_called()

    def test_rejects_context_larger_than_context_limit(self, client):
        with patch("src.dashboard_api.http_requests.post") as provider_post, patch(
            "src.dashboard_api.http_requests.get"
        ) as provider_get:
            response = client.post(
                "/api/books/translate",
                json={"text": "tunnel", "context": "a" * 1501},
            )

        assert response.status_code == 413
        assert response.get_json() == {
            "error": "context_too_long",
            "maxBytes": 1500,
        }
        provider_post.assert_not_called()
        provider_get.assert_not_called()

    def test_rejects_empty_selection_without_calling_provider(self, client):
        with patch("src.dashboard_api.http_requests.post") as provider_post, patch(
            "src.dashboard_api.http_requests.get"
        ) as provider_get:
            response = client.post("/api/books/translate", json={"text": "  "})

        assert response.status_code == 400
        assert response.get_json() == {"error": "selection_required"}
        provider_post.assert_not_called()
        provider_get.assert_not_called()

    def test_reports_all_provider_failures_without_leaking_details(
        self, client, monkeypatch
    ):
        monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")
        with patch(
            "src.dashboard_api.http_requests.post",
            side_effect=http_requests.RequestException("private upstream detail"),
        ), patch(
            "src.dashboard_api.http_requests.get",
            side_effect=http_requests.RequestException("private upstream detail"),
        ):
            response = client.post(
                "/api/books/translate",
                json={
                    "text": "tunnel",
                    "context": "The hall was like a tunnel.",
                },
            )

        assert response.status_code == 502
        assert response.get_json() == {"error": "translation_provider_unavailable"}


def test_assistant_stream_emits_tool_events_then_the_answer(client, monkeypatch):
    import src.dashboard_api as api

    class _Rt:
        def chat_events(self, **kwargs):
            yield {"event": "tool_start", "name": "kazanim_ara"}
            yield {"event": "tool_end", "name": "kazanim_ara", "ok": True, "ms": 40}
            yield {"event": "answer", "payload": {
                "answer": "cevap", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "meta": {"model": "claude-sonnet-5", "degraded": []}}}

    monkeypatch.setattr(api, "_assistant_runtime", lambda: _Rt())

    res = client.post("/api/assistant/stream", json={"messages": [
        {"role": "user", "content": "kesir"}]})

    assert res.status_code == 200
    assert res.headers["Content-Type"].startswith("text/event-stream")
    body = res.get_data(as_text=True)
    assert "event: tool_start" in body
    assert "event: answer" in body
    assert body.rstrip().endswith("event: done\ndata: {}")


def test_assistant_stream_requires_auth(client_no_auth):
    res = client_no_auth.post("/api/assistant/stream", json={"messages": []})
    assert res.status_code in (401, 403)


# ── B63: "Yaptım" can be taken back (talimatname §13, S40) ───────────────────

class TestHomeworkUnmarkDoneEndpoint:
    def _isaretle(self, client, scraped, key):
        with patch("src.dashboard_api._scraped", return_value=scraped):
            assert client.post("/api/homework/mark-done", json={"homework_key": key}).status_code == 200

    def test_requires_identifier(self, client, isolated_output):
        resp = client.post("/api/homework/unmark-done", json={})
        assert resp.status_code == 400
        assert "gerekli" in resp.get_json()["error"]

    def test_unmarks_by_key_and_listing_shows_it_active_again(self, client, isolated_output):
        scraped = _sample_scraped_homework()
        key = dashboard_api._homework_row_key(scraped["odevlerim"]["homework"]["rows"][0])
        self._isaretle(client, scraped, key)

        with patch("src.dashboard_api._scraped", return_value=scraped):
            resp = client.post("/api/homework/unmark-done", json={"homework_key": key})
            assert resp.status_code == 200
            payload = resp.get_json()
            assert payload == {"ok": True, "homework_key": key, "removed": True}
            listing = client.get("/api/homework").get_json()
        assert listing["homework"][0]["student_marked_done"] is False
        stored = json.loads((isolated_output / "homework_student_done.json").read_text("utf-8"))
        assert key not in stored["marks"]

    def test_is_idempotent(self, client, isolated_output):
        scraped = _sample_scraped_homework()
        key = dashboard_api._homework_row_key(scraped["odevlerim"]["homework"]["rows"][0])
        self._isaretle(client, scraped, key)
        with patch("src.dashboard_api._scraped", return_value=scraped):
            first = client.post("/api/homework/unmark-done", json={"homework_key": key})
            second = client.post("/api/homework/unmark-done", json={"homework_key": key})
        assert first.status_code == second.status_code == 200
        assert first.get_json()["removed"] is True
        assert second.get_json() == {"ok": True, "homework_key": key, "removed": False}

    def test_unmarks_by_title_and_due_like_mark_done(self, client, isolated_output):
        scraped = _sample_scraped_homework()
        row = scraped["odevlerim"]["homework"]["rows"][0]
        key = dashboard_api._homework_row_key(row)
        self._isaretle(client, scraped, key)
        with patch("src.dashboard_api._scraped", return_value=scraped):
            resp = client.post("/api/homework/unmark-done", json={
                "Ödev Başlığı": row["Ödev Başlığı"],
                "Ödev Son Teslim Tarihi": row["Ödev Son Teslim Tarihi"],
                "Ders Adı": row["Ders Adı"],
            })
        assert resp.status_code == 200
        assert resp.get_json()["homework_key"] == key
        assert resp.get_json()["removed"] is True

    def test_unknown_title_is_404(self, client, isolated_output):
        with patch("src.dashboard_api._scraped", return_value=_sample_scraped_homework()):
            resp = client.post("/api/homework/unmark-done", json={
                "Ödev Başlığı": "Bilinmeyen", "Ödev Son Teslim Tarihi": "20.03.2026 12:00"})
        assert resp.status_code == 404

    def test_other_marks_are_kept(self, client, isolated_output):
        dashboard_api._save_student_done_marks({"baska|is|x": "2026-10-01T10:00:00"})
        scraped = _sample_scraped_homework()
        key = dashboard_api._homework_row_key(scraped["odevlerim"]["homework"]["rows"][0])
        self._isaretle(client, scraped, key)
        with patch("src.dashboard_api._scraped", return_value=scraped):
            client.post("/api/homework/unmark-done", json={"homework_key": key})
        assert dashboard_api._load_student_done_marks() == {"baska|is|x": "2026-10-01T10:00:00"}

    def test_unmark_by_key_works_after_the_row_left_the_list(self, client, isolated_output):
        dashboard_api._save_student_done_marks({"gecmis|is|x": "2026-10-01T10:00:00"})
        with patch("src.dashboard_api._scraped", return_value={}):
            resp = client.post("/api/homework/unmark-done", json={"homework_key": "gecmis|is|x"})
        assert resp.status_code == 200 and resp.get_json()["removed"] is True
        assert dashboard_api._load_student_done_marks() == {}

    def test_teacher_verdict_pruning_keeps_a_mark_written_meanwhile(
        self, client, isolated_output, monkeypatch
    ):
        # /api/homework drops a mark the teacher's verdict made obsolete. It
        # used to write back its own copy of the marks, losing a "Yaptım"
        # another worker stored between its read and its write.
        scraped = _sample_scraped_homework(status="Yaptı")
        cozulen = dashboard_api._homework_row_key(scraped["odevlerim"]["homework"]["rows"][0])
        dashboard_api._save_student_done_marks({cozulen: "2026-10-01T10:00:00"})
        gercek_kilit = dashboard_api._isaret_kilidi

        def araya_giren_kilit():
            dashboard_api._save_student_done_marks({
                **dashboard_api._load_student_done_marks(), "yeni|is|y": "2026-10-11T09:00:00"})
            return gercek_kilit()

        monkeypatch.setattr(dashboard_api, "_isaret_kilidi", araya_giren_kilit)
        with patch("src.dashboard_api._scraped", return_value=scraped):
            client.get("/api/homework")
        assert dashboard_api._load_student_done_marks() == {"yeni|is|y": "2026-10-11T09:00:00"}

    def test_requires_auth_and_refuses_a_reader(self, isolated_output, monkeypatch):
        monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
        okur = next(e for e, r in dashboard_api.USER_ROLES.items() if r == dashboard_api.ROLE_READER)
        with app.test_client() as c:
            assert c.post("/api/homework/unmark-done", json={"homework_key": "k"}).status_code == 401
            with c.session_transaction() as s:
                s["user_email"] = okur
            assert c.post("/api/homework/unmark-done", json={"homework_key": "k"}).status_code == 403
        assert "homework_unmark_done" not in dashboard_api.READER_ENDPOINTS


# ── B29: the focus window is a parameter in output/ (anayasa §2) ─────────────

class TestOdakPenceresiEndpoint:
    def test_defaults_are_todays_values(self, client, isolated_output):
        resp = client.get("/api/odak-penceresi")
        assert resp.status_code == 200
        assert resp.get_json() == {
            "okul_bitisi": "15:45", "odak_sonu": "16:00", "yatma": "22:30", "varsayilan": True}

    def test_put_stores_atomically_and_get_reads_it(self, client, isolated_output):
        resp = client.put("/api/odak-penceresi", json={
            "okul_bitisi": "15:30", "odak_sonu": "16:15", "yatma": "22:00"})
        assert resp.status_code == 200
        assert resp.get_json() == {
            "okul_bitisi": "15:30", "odak_sonu": "16:15", "yatma": "22:00", "varsayilan": False}
        stored = json.loads((isolated_output / "odak_penceresi.json").read_text("utf-8"))
        assert stored["okul_bitisi"] == "15:30" and stored["yatma"] == "22:00"
        assert not list(isolated_output.glob("*.tmp"))
        assert client.get("/api/odak-penceresi").get_json()["odak_sonu"] == "16:15"

    @pytest.mark.parametrize("govde", [
        {"okul_bitisi": "15:45", "odak_sonu": "16:00"},                     # missing
        {"okul_bitisi": "25:00", "odak_sonu": "16:00", "yatma": "22:30"},   # not a time
        {"okul_bitisi": "15:45", "odak_sonu": "4pm", "yatma": "22:30"},
        {"okul_bitisi": "16:30", "odak_sonu": "16:00", "yatma": "22:30"},   # window ends before school
        {"okul_bitisi": "15:45", "odak_sonu": "23:00", "yatma": "22:30"},   # bedtime before window
        ["15:45"],
    ])
    def test_put_rejects_a_bad_window_with_a_sentence(self, client, isolated_output, govde):
        resp = client.put("/api/odak-penceresi", json=govde)
        assert resp.status_code == 400
        assert resp.get_json()["error"].endswith(".")
        assert not (isolated_output / "odak_penceresi.json").exists()

    def test_unreadable_file_reads_as_defaults(self, client, isolated_output):
        (isolated_output / "odak_penceresi.json").write_text("{bozuk", "utf-8")
        assert client.get("/api/odak-penceresi").get_json()["varsayilan"] is True
        (isolated_output / "odak_penceresi.json").write_text(
            json.dumps({"okul_bitisi": "99:00", "odak_sonu": "16:00", "yatma": "22:30"}), "utf-8")
        assert client.get("/api/odak-penceresi").get_json()["okul_bitisi"] == "15:45"

    def test_requires_auth_and_refuses_a_reader(self, isolated_output, monkeypatch):
        monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
        okur = next(e for e, r in dashboard_api.USER_ROLES.items() if r == dashboard_api.ROLE_READER)
        govde = {"okul_bitisi": "15:45", "odak_sonu": "16:00", "yatma": "22:30"}
        with app.test_client() as c:
            assert c.get("/api/odak-penceresi").status_code == 401
            assert c.put("/api/odak-penceresi", json=govde).status_code == 401
            with c.session_transaction() as s:
                s["user_email"] = okur
            assert c.get("/api/odak-penceresi").status_code == 403
            assert c.put("/api/odak-penceresi", json=govde).status_code == 403
        assert not (isolated_output / "odak_penceresi.json").exists()


# ── B41 (backend half): "Özel ders" in sentence case at the source (S38) ─────

class TestOzelDersCumleDuzeni:
    DERS = {"id": "pl1", "course": "Fen Bilimleri", "teacher": "Deneme Hoca",
            "is_recurring": True, "weekday": "Cumartesi",
            "start_time": "12:00", "end_time": "13:00", "active": True}

    def test_week_events_say_ozel_ders(self):
        from datetime import date, timedelta
        pzt = date(2026, 9, 21)
        gunler = [pzt + timedelta(days=i) for i in range(7)]
        olaylar = dashboard_api._private_lessons_for_week(gunler, [self.DERS])
        assert olaylar and olaylar[0]["status"] == "Özel ders"
        assert olaylar[0]["subtitle"] == "Özel ders • Deneme Hoca"
        isimsiz = dashboard_api._private_lessons_for_week(gunler, [{**self.DERS, "teacher": ""}])
        assert isimsiz[0]["subtitle"] == "Özel ders"

    def test_bugun_calendar_badge_and_description(self, client, monkeypatch):
        monkeypatch.setattr(dashboard_api, "_load_private_lessons", lambda: [self.DERS])
        olaylar = client.get("/api/calendar").get_json()["events"]
        ozel = [e for e in olaylar if e["extendedProps"].get("kind") == "private_lesson"]
        assert ozel
        assert {e["extendedProps"]["badge"] for e in ozel} == {"Özel ders"}
        assert {e["extendedProps"]["description"] for e in ozel} == {"Özel ders • Deneme Hoca"}

    def test_no_title_case_left_in_the_api_source(self):
        kaynak = open(dashboard_api.__file__, encoding="utf-8").read()
        satirlar = [s for s in kaynak.splitlines() if "Özel Ders" in s and "ESKI_OZEL_DERS" not in s]
        assert satirlar == []

    def test_photo_row_from_a_private_lesson_says_ozel_ders(self):
        ders = {"id": "abc", "course": "", "teacher": "Ayşe"}
        aday = {"ders_adi": "", "odev_basligi": "Okuma", "son_teslim_tarihi": ""}
        row = dashboard_api._to_photo_homework_row(
            aday, image_hash="h", source_type="private", private_lesson=ders)
        assert row["Ders Adı"] == "Özel ders"
        assert row["Ödev Kaynağı"] == "Özel ders (Ayşe)"

    def test_stored_title_case_rows_are_mapped_at_the_boundary(self, client, isolated_output):
        eski = {"Ders Adı": "Özel Ders", "Ödev Başlığı": "Okuma", "Ödev Kaynağı": "Özel Ders (Ayşe)",
                "Ödev Son Teslim Tarihi": "", "Ödev Durumu": "Değerlendirilmemiş",
                "source": "photo_ai_private", "detail": {"description": "", "attachments": []}}
        dashboard_api._save_photo_homework_rows([eski])
        with patch("src.dashboard_api._scraped", return_value={}):
            rows = client.get("/api/homework").get_json()["homework"]
        assert rows[0]["normalized_course"] == "Özel ders"
        assert rows[0]["Ödev Kaynağı"] == "Özel ders (Ayşe)"
        # The file itself is not rewritten.
        stored = json.loads((isolated_output / "photo_homework.json").read_text("utf-8"))
        assert stored["homework"][0]["Ders Adı"] == "Özel Ders"
        # And the key a "Yaptım" mark is stored under does not move.
        assert rows[0]["homework_key"] == dashboard_api._homework_row_key(eski)

    @pytest.mark.parametrize("ders", ["Özel ders", "Özel Ders"])
    def test_assistant_still_asks_for_the_course_of_a_placeholder_row(self, ders):
        from src.assistant_tools import foto_eksik_alanlar
        row = {"source": "photo_ai_private", "Ders Adı": ders,
               "Ödev Son Teslim Tarihi": "25.09.2026 12:00"}
        assert foto_eksik_alanlar(row) == ["ders"]


# ── Müfredat ağacı ucu (spec §4) ────────────────────────────────────────────

_AGAC_GOVDESI = {
    "surum": 1, "korpus_surumu": "1.6", "sinif": "7. Sınıf",
    "dersler": [{
        "ders": "Matematik", "slug": "matematik",
        "program": {"document_id": 24, "sayfa": "115-172"},
        "kitaplar": [{"document_id": 346, "kisa": "1. Kitap",
                      "sayfa_kaymasi": 0, "kayma_uyumu": "35/35"}],
        "uniteler": [{
            "no": 1, "ad": "Sayılar ve Nicelikler", "program_sayfa": 115,
            "konular": [
                {"id": "matematik-u1-tam-sayilar", "ad": "Tam Sayılar",
                 "ad_kaynak": "TAM SAYILAR", "kitap": 346, "sayfa": [17, 24],
                 "sayfa_kaynak": "icindekiler", "kazanimlar": ["MAT.7.1.1"],
                 "kazanim_kaynak": "metin-ortusmesi"},
                {"id": "matematik-u1-mutlak-deger", "ad": "Mutlak Değer",
                 "ad_kaynak": "MUTLAK DEĞER", "kitap": 346,
                 "sayfa_kaynak": "yok", "kazanimlar": [],
                 "kazanim_kaynak": "eslenmedi"},
            ],
        }],
    }],
    "kapsam": {"matematik": {"konu": 2, "sayfasi_olan": 1, "kazanimi_eslenen": 1}},
}


def _modul_satiri(slug, outcomes, **ustune):
    satir = {"slug": slug, "version": 1, "status": "active", "title": slug,
             "subject": "Matematik", "gradeLevel": "7. Sınıf", "mode": "MODULE",
             "outcomes": outcomes, "ted_link": None,
             "gates": {"pass": 17, "warn": 0, "fail": 0},
             "created_at": "2026-09-19T19:32:46+00:00"}
    satir.update(ustune)
    return satir


@pytest.fixture
def agac_dosyasi(tmp_path, monkeypatch):
    """Ağaç dosyasını ve modül kataloğunu testin kendisi kurar.

    Worktree'de `output/` yok (gitignore'lu) ve canlı kataloğa dayanan bir test başka bir
    makinede sessizce başka bir şey ölçer.
    """
    def yaz(govde, moduller=None):
        yol = tmp_path / "mufredat_agaci.json"
        yol.write_text(json.dumps(govde) if not isinstance(govde, str) else govde,
                       encoding="utf-8")
        monkeypatch.setattr(dashboard_api, "MUFREDAT_AGACI_PATH", str(yol))
        katalog = tmp_path / "modules"
        katalog.mkdir(exist_ok=True)
        satirlar = moduller if moduller is not None else [
            _modul_satiri("mat7-tam-sayilar", ["MAT.7.1.1"],
                          title="Tam Sayılar: Sıfırın İki Yanı"),
            _modul_satiri("fen7-turkiye-ve-uzay-arastirmalari", ["FB.7.1.1"],
                          subject="Fen Bilimleri", mode="CURRICULUM"),
        ]
        (katalog / "index.json").write_text(
            json.dumps({"surum": 1, "moduller": satirlar}), encoding="utf-8")
        monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
        return yol
    return yaz


def test_agac_ucu_dersleri_ve_kapsami_dondurur(client, agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    govde = client.get("/api/modules/agac").get_json()
    assert govde["hata"] is None
    assert [d["slug"] for d in govde["dersler"]] == ["matematik"]
    assert govde["kapsam"]["matematik"]["konu"] == 2


def test_agac_ucu_yayinlanmis_modulu_kazanimiyla_konuya_bagliyor(client, agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    govde = client.get("/api/modules/agac").get_json()
    konular = govde["dersler"][0]["uniteler"][0]["konular"]
    tam_sayilar = next(k for k in konular if k["id"] == "matematik-u1-tam-sayilar")
    mutlak = next(k for k in konular if k["id"] == "matematik-u1-mutlak-deger")
    assert tam_sayilar["modul"]["slug"] == "mat7-tam-sayilar"
    assert mutlak["modul"] is None


def test_agac_ucu_hazir_sayaclarini_veriyor(client, agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    ders = client.get("/api/modules/agac").get_json()["dersler"][0]
    assert (ders["konu_sayisi"], ders["hazir_sayisi"]) == (2, 1)
    assert ders["uniteler"][0]["hazir_sayisi"] == 1


def test_agac_ucu_hazir_listesinde_agaca_eslenmeyen_modul_de_var(client, agac_dosyasi):
    """Katalogdaki her yayınlanmış modül listede görünür; ağaca eşlenmeyen de (spec §4)."""
    agac_dosyasi(_AGAC_GOVDESI)
    sluglar = {m["slug"] for m in client.get("/api/modules/agac").get_json()["hazir"]}
    assert sluglar == {"mat7-tam-sayilar", "fen7-turkiye-ve-uzay-arastirmalari"}


def test_agac_ucu_ayni_modulu_iki_konuya_baglamaz(client, agac_dosyasi):
    """Bir kazanım birkaç konuya düşerse modül TEK konuya bağlanır (spec §3.1)."""
    govde = json.loads(json.dumps(_AGAC_GOVDESI))
    konular = govde["dersler"][0]["uniteler"][0]["konular"]
    konular[1]["kazanimlar"] = ["MAT.7.1.1"]
    konular[1]["kazanim_kaynak"] = "metin-ortusmesi"
    agac_dosyasi(govde, moduller=[_modul_satiri("mat7-tam-sayilar", ["MAT.7.1.1"])])
    cevap = client.get("/api/modules/agac").get_json()["dersler"][0]["uniteler"][0]["konular"]
    bagli = [k["id"] for k in cevap if k["modul"]]
    assert len(bagli) == 1


def test_agac_ucu_sayfa_ortusmesine_gore_en_iyi_konuya_bagliyor(client, agac_dosyasi):
    """Aynı kazanımı taşıyan iki konudan, frame_source sayfalarıyla örtüşeni kazanır."""
    govde = json.loads(json.dumps(_AGAC_GOVDESI))
    konular = govde["dersler"][0]["uniteler"][0]["konular"]
    konular[1]["kazanimlar"] = ["MAT.7.1.1"]
    konular[1]["kazanim_kaynak"] = "metin-ortusmesi"
    konular[1]["sayfa"] = [40, 48]
    konular[1]["sayfa_kaynak"] = "icindekiler"
    agac_dosyasi(govde, moduller=[_modul_satiri(
        "mat7-tam-sayilar", ["MAT.7.1.1"],
        frame_source={"kind": "textbook", "document_id": 346, "pages": "41-45"})])
    cevap = client.get("/api/modules/agac").get_json()["dersler"][0]["uniteler"][0]["konular"]
    bagli = next(k["id"] for k in cevap if k["modul"])
    assert bagli == "matematik-u1-mutlak-deger"


# Review Focus 1: geçerli JSON ama şema dışı → 500 değil.
@pytest.mark.parametrize("govde", ['{ bu json degil', '{"surum": 1, "dersler": {}}', '{}'])
def test_agac_ucu_bozuk_dosyada_500_vermiyor(client, agac_dosyasi, govde):
    agac_dosyasi(govde)
    yanit = client.get("/api/modules/agac")
    assert yanit.status_code == 200
    payload = yanit.get_json()
    assert payload["dersler"] == [] and payload["hata"] == "harita_okunamadi"
    assert payload["kapsam"] == {}


def test_agac_ucu_dosya_yokken_de_hazir_listesi_veriyor(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "MUFREDAT_AGACI_PATH", str(tmp_path / "yok.json"))
    payload = client.get("/api/modules/agac").get_json()
    assert payload["hata"] == "harita_okunamadi" and isinstance(payload["hazir"], list)


# Review Focus 4: yetkisiz çağrı.
def test_agac_ucu_oturumsuz_cagriyi_reddediyor(client_no_auth):
    assert client_no_auth.get("/api/modules/agac").status_code in (401, 403)


def test_agac_ucu_okur_rolunde_reddediyor(monkeypatch):
    """Varsayılan-reddet: ucun adı READER_ENDPOINTS'te olmadığı için okur 403 alır."""
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    okur = next(e for e, r in dashboard_api.USER_ROLES.items() if r == dashboard_api.ROLE_READER)
    with app.test_client() as c:
        assert c.get("/api/modules/agac").status_code == 401
        with c.session_transaction() as oturum:
            oturum["user_email"] = okur
        assert c.get("/api/modules/agac").status_code == 403
    assert "modules_agac" not in dashboard_api.READER_ENDPOINTS


# ── Asistan bağlamında konu öğesi (spec §4.1) ───────────────────────────────


def test_konu_turu_sayfa_oge_turlerinde():
    assert "konu" in dashboard_api.SAYFA_OGE_TURLERI


def test_konu_basligi_dersi_ve_konuyu_adlandiriyor(agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    baslik = dashboard_api._sayfa_ogesi_basligi("konu", "matematik-u1-tam-sayilar")
    assert baslik == "Matematik · Tam Sayılar"


# Review Focus 5: kötü konu kimliği.
def test_konu_basligi_bilinmeyen_kimlikte_bos(agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    assert dashboard_api._sayfa_ogesi_basligi("konu", "matematik-u9-olmayan") == ""


def test_konu_basligi_harita_okunamazken_bos(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "MUFREDAT_AGACI_PATH", str(tmp_path / "yok.json"))
    assert dashboard_api._sayfa_ogesi_basligi("konu", "matematik-u1-tam-sayilar") == ""


def test_istek_sayfasi_konu_ogesini_kabul_ediyor(agac_dosyasi):
    agac_dosyasi(_AGAC_GOVDESI)
    # `_istek_sayfasi` hata demetini koşulsuz kurduğu için her çağrı uygulama bağlamı ister.
    with app.test_request_context():
        satir, hata = dashboard_api._istek_sayfasi(
            {"sayfa": {"ad": "moduller",
                       "oge": {"tur": "konu", "id": "matematik-u1-tam-sayilar"}}})
    assert hata is None and "Matematik · Tam Sayılar" in satir


@pytest.mark.parametrize("kimlik", ["x" * 401, "konu\nid", ""])
def test_istek_sayfasi_bozuk_konu_kimligini_400_yapiyor(kimlik):
    with app.test_request_context():
        _, hata = dashboard_api._istek_sayfasi(
            {"sayfa": {"ad": "moduller", "oge": {"tur": "konu", "id": kimlik}}})
    assert hata is not None and hata[1] == 400


def test_istek_sayfasi_bilinmeyen_konuda_sayfa_satirini_koruyor(agac_dosyasi):
    """Bağlam satırı hiçbir zaman cevabı düşürmez: başlık çözülemese de sayfa adı kalır."""
    agac_dosyasi(_AGAC_GOVDESI)
    with app.test_request_context():
        satir, hata = dashboard_api._istek_sayfasi(
            {"sayfa": {"ad": "moduller", "oge": {"tur": "konu", "id": "matematik-u9-olmayan"}}})
    assert hata is None and satir == "Bulunduğu sayfa: Modüller"


# ── Denetim turu: eşiğe takılan ders ve bozuk katalog ────────────────────────


def test_agac_ucu_esige_takilan_dersi_yine_listeliyor(client, agac_dosyasi):
    """I2 (D3): üretilmeyen ders sessizce eksilmez.

    Spec §5.5, yüzey tasarımı §4.12 ve CLAUDE.md aynı sözü veriyor: eşiğe takılan ders
    ağaçta YİNE listelenir ve bir cümle söyler. `ders_uret` böyle bir ders için kayıt
    döndürmüyor, o yüzden kaydı uç `kapsam`daki `yazilmadi` işaretinden kurar.
    """
    govde = json.loads(json.dumps(_AGAC_GOVDESI))
    govde["kapsam"]["turkce"] = {"konu": 3, "kazanim": 121, "yazilmadi": "konu_esigi"}
    agac_dosyasi(govde)
    dersler = client.get("/api/modules/agac").get_json()["dersler"]
    turkce = next((d for d in dersler if d["slug"] == "turkce"), None)
    assert turkce is not None, "eşiğe takılan ders ağaçtan düşmüş"
    assert turkce["uniteler"] == [] and turkce["konu_sayisi"] == 0
    assert turkce["ders"] == "Türkçe"


def test_agac_ucu_bilinmeyen_slugu_ders_adi_olarak_uydurmuyor(client, agac_dosyasi):
    """Ad bilinmiyorsa slug okura gitmez; ders adı tablodan gelir, uydurulmaz (D4)."""
    govde = json.loads(json.dumps(_AGAC_GOVDESI))
    govde["kapsam"]["bilinmeyen"] = {"yazilmadi": "konu_esigi"}
    agac_dosyasi(govde)
    sluglar = {d["slug"] for d in client.get("/api/modules/agac").get_json()["dersler"]}
    assert "bilinmeyen" not in sluglar


def test_agac_ucu_bozuk_katalogu_bos_liste_gibi_gostermiyor(client, agac_dosyasi, tmp_path):
    """I8: yarım yazılmış katalog "hiç modül yok" diye okunmaz ("empty is never blank")."""
    agac_dosyasi(_AGAC_GOVDESI)
    (tmp_path / "modules" / "index.json").write_text("{ yarim", encoding="utf-8")
    payload = client.get("/api/modules/agac").get_json()
    assert payload["hazir"] == [] and payload["hata"] == "katalog_okunamadi"
    # Harita okunabildiği için ağaç yine gelir.
    assert [d["slug"] for d in payload["dersler"]] == ["matematik"]


def test_agac_ucu_modulu_baska_kitaptaki_konuya_baglamiyor(client, agac_dosyasi):
    """C1: sayfa örtüşmesi kitap kimliğini de denetler.

    İki kitabın sayfa numaraları aynı aralıkta olabilir; `frame_source.document_id`
    bakılmazsa 2. kitaptaki bir modül 1. kitabın konusuna bağlanır.
    """
    govde = json.loads(json.dumps(_AGAC_GOVDESI))
    ders = govde["dersler"][0]
    ders["kitaplar"].append({"document_id": 506, "kisa": "2. Kitap",
                             "sayfa_kaymasi": 0, "kayma_uyumu": "32/32"})
    konular = ders["uniteler"][0]["konular"]
    konular[1]["kitap"] = 506
    konular[1]["sayfa"] = [17, 24]
    konular[1]["sayfa_kaynak"] = "icindekiler"
    konular[1]["kazanimlar"] = ["MAT.7.1.1"]
    konular[1]["kazanim_kaynak"] = "metin-ortusmesi"
    agac_dosyasi(govde, moduller=[_modul_satiri(
        "mat7-tam-sayilar", ["MAT.7.1.1"],
        frame_source={"kind": "textbook", "document_id": 506, "pages": "18-20"})])
    cevap = client.get("/api/modules/agac").get_json()["dersler"][0]["uniteler"][0]["konular"]
    bagli = next(k["id"] for k in cevap if k["modul"])
    assert bagli == "matematik-u1-mutlak-deger"


def test_agac_ucu_program_cercevesini_sayfa_kaniti_saymiyor(client, agac_dosyasi):
    """`kind: "program"` çerçevesinin sayfaları PROGRAMın sayfalarıdır, kitabın değil."""
    govde = json.loads(json.dumps(_AGAC_GOVDESI))
    konular = govde["dersler"][0]["uniteler"][0]["konular"]
    konular[1]["kazanimlar"] = ["MAT.7.1.1"]
    konular[1]["kazanim_kaynak"] = "metin-ortusmesi"
    konular[1]["sayfa"] = [110, 120]
    konular[1]["sayfa_kaynak"] = "icindekiler"
    agac_dosyasi(govde, moduller=[_modul_satiri(
        "mat7-tam-sayilar", ["MAT.7.1.1"],
        frame_source={"kind": "program", "document_id": 24, "pages": "110"})])
    cevap = client.get("/api/modules/agac").get_json()["dersler"][0]["uniteler"][0]["konular"]
    # Program sayfası kanıt sayılmaz; sıradaki ilk konu kazanır.
    assert next(k["id"] for k in cevap if k["modul"]) == "matematik-u1-tam-sayilar"
