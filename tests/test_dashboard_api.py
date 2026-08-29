"""Integration tests for dashboard API endpoints."""
import os
import sys
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
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
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

    def test_falls_back_to_gemini_when_deepl_fails(
        self, client, monkeypatch
    ):
        monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        def provider_post(url, **kwargs):
            if "deepl.com" in url:
                raise http_requests.RequestException("deepl unavailable")
            prompt = kwargs["json"]["contents"][0]["parts"][0]["text"]
            translated = (
                "tünel"
                if "dictionary headword" in prompt
                else "tünel gibiydi"
            )
            gemini_response = Mock()
            gemini_response.json.return_value = {
                "candidates": [
                    {"content": {"parts": [{"text": translated}]}}
                ]
            }
            return gemini_response

        with patch(
            "src.dashboard_api.http_requests.post",
            side_effect=provider_post,
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
        assert response.get_json()["provider"] == "Gemini 2.5 Flash"
        assert post_request.call_count == 2
        gemini_call = post_request.call_args_list[1]
        assert gemini_call.args[0].endswith(
            "/models/gemini-2.5-flash:generateContent"
        )
        assert gemini_call.kwargs["headers"] == {
            "x-goog-api-key": "test-gemini-key"
        }
        prompt = gemini_call.kwargs["json"]["contents"][0]["parts"][0]["text"]
        assert '"tunnel"' in prompt
        assert '"The hall was like a tunnel."' in prompt
        provider_get.assert_not_called()

    def test_falls_back_to_contextual_mymemory_after_deepl_and_gemini(
        self, client, monkeypatch
    ):
        monkeypatch.setenv("DEEPL_API_KEY", "test-key:fx")
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
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
        assert provider_post.call_count == 2
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
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
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
                "meta": {"model": "gemini-3.7-flash", "degraded": []}}}

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
