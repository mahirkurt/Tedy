"""Role gate and per-profile reading position.

A "reader" account is only allowed into Tedy Books. These tests hold the gate
shut from the API side — the frontend hides the other pages, but hiding is not
access control.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402

app = dashboard_api.app

READER = "murzogluhulya@gmail.com"
READERS = ["murzogluhulya@gmail.com", "mahirkurtmd@gmail.com"]
STUDENT = "isikkurtx@gmail.com"

# Every dashboard surface a reader must not reach.
DASHBOARD_ENDPOINTS = [
    "/api/schedule",
    "/api/homework",
    "/api/grades",
    "/api/exams",
    "/api/calendar",
    "/api/calendar/unified",
    "/api/teams",
    "/api/content",
    "/api/announcements",
    "/api/enrichment",
    "/api/student/profile",
    "/api/private-lessons",
    "/api/progress/ec",
    "/api/progress/a3k",
    "/api/health",
    "/api/sebit",
]


@pytest.fixture
def client(monkeypatch):
    app.config["TESTING"] = True
    # The role gate is skipped under the bypass, so these tests run without it.
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    with app.test_client() as c:
        yield c


def sign_in(client, email):
    with client.session_transaction() as sess:
        sess["user_email"] = email
        sess["user_name"] = email.split("@")[0]


@pytest.fixture
def progress_file(tmp_path, monkeypatch):
    path = str(tmp_path / "book_progress.json")
    monkeypatch.setattr(dashboard_api, "BOOK_PROGRESS_FILE", path)
    return path


# ── Role roster ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("email", READERS)
def test_reader_is_on_the_roster_as_reader(email):
    assert dashboard_api.USER_ROLES[email] == dashboard_api.ROLE_READER
    assert email in dashboard_api.ALLOWED_EMAILS
    assert email not in dashboard_api.FULL_ACCESS_EMAILS


@pytest.mark.parametrize("email", READERS)
def test_reader_is_not_an_assistant_admin_by_default(email):
    assert email not in dashboard_api.ASSISTANT_ADMIN_EMAILS


@pytest.mark.parametrize("email", READERS)
def test_each_reader_is_gated_and_may_read_books(client, email):
    sign_in(client, email)
    assert client.get("/api/homework").status_code == 403
    assert client.get("/api/books").status_code == 200


def test_the_two_mahir_addresses_do_not_share_a_role():
    # drmahirkurt@ runs the dashboard; mahirkurtmd@ only reads.
    assert dashboard_api.USER_ROLES["drmahirkurt@gmail.com"] == dashboard_api.ROLE_FULL
    assert dashboard_api.USER_ROLES["mahirkurtmd@gmail.com"] == dashboard_api.ROLE_READER


def test_readers_do_not_see_each_others_position(client, progress_file):
    sign_in(client, READERS[0])
    client.post("/api/books/progress", json={"books": {"bir-kitap": {
        "lastChapterId": "B04", "updatedAt": "2026-08-16T09:00:00.000Z",
        "chapters": {"B04": {"ratio": 0.3, "done": False}},
    }}})

    sign_in(client, READERS[1])
    assert client.get("/api/books/progress").get_json()["books"] == {}


def test_auth_me_reports_the_role(client):
    sign_in(client, READER)
    assert client.get("/api/auth/me").get_json()["role"] == "reader"

    sign_in(client, STUDENT)
    assert client.get("/api/auth/me").get_json()["role"] == "full"


# ── The gate ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("endpoint", DASHBOARD_ENDPOINTS)
def test_reader_is_refused_dashboard_endpoints(client, endpoint):
    sign_in(client, READER)
    resp = client.get(endpoint)
    assert resp.status_code == 403, endpoint
    assert resp.get_json()["error"] == "forbidden"


def test_reader_is_refused_the_assistant(client):
    sign_in(client, READER)
    assert client.post(
        "/api/assistant/chat", json={"messages": []}
    ).status_code == 403
    # The OpenAI-compatible surface is API-key-only, so a session of any role
    # is turned away there before the role is even consulted.
    assert client.get("/v1/models").status_code == 401


def test_reader_may_read_books(client):
    sign_in(client, READER)
    assert client.get("/api/books").status_code == 200


def test_full_access_account_still_reaches_the_dashboard(client):
    sign_in(client, STUDENT)
    assert client.get("/api/homework").status_code == 200


def test_an_email_off_the_roster_gets_the_least_privilege(client):
    sign_in(client, "stranger@example.com")
    assert client.get("/api/homework").status_code == 403


# ── Per-profile reading position ─────────────────────────────────────────────

def test_progress_round_trips_for_one_profile(client, progress_file):
    sign_in(client, READER)
    payload = {"books": {"kayip-zamanin-izinde": {
        "lastChapterId": "B03",
        "updatedAt": "2026-08-16T09:00:00.000Z",
        "chapters": {"B03": {"ratio": 0.42, "done": False}},
    }}}
    assert client.post("/api/books/progress", json=payload).status_code == 200

    books = client.get("/api/books/progress").get_json()["books"]
    assert books["kayip-zamanin-izinde"]["lastChapterId"] == "B03"
    assert books["kayip-zamanin-izinde"]["chapters"]["B03"]["ratio"] == 0.42


def test_profiles_do_not_see_each_others_position(client, progress_file):
    sign_in(client, READER)
    client.post("/api/books/progress", json={"books": {"bir-kitap": {
        "lastChapterId": "B01", "updatedAt": "2026-08-16T09:00:00.000Z",
        "chapters": {"B01": {"ratio": 0.9, "done": True}},
    }}})

    sign_in(client, STUDENT)
    assert client.get("/api/books/progress").get_json()["books"] == {}

    client.post("/api/books/progress", json={"books": {"bir-kitap": {
        "lastChapterId": "B07", "updatedAt": "2026-08-16T10:00:00.000Z",
        "chapters": {"B07": {"ratio": 0.1, "done": False}},
    }}})

    sign_in(client, READER)
    mine = client.get("/api/books/progress").get_json()["books"]
    assert mine["bir-kitap"]["lastChapterId"] == "B01"


def test_the_newer_copy_of_a_book_wins(client, progress_file):
    sign_in(client, READER)
    client.post("/api/books/progress", json={"books": {"bir-kitap": {
        "lastChapterId": "B02", "updatedAt": "2026-08-16T12:00:00.000Z",
        "chapters": {"B02": {"ratio": 0.5, "done": False}},
    }}})

    # An older device replays a stale bookmark; it must not roll the reader back.
    client.post("/api/books/progress", json={"books": {"bir-kitap": {
        "lastChapterId": "B01", "updatedAt": "2026-08-16T08:00:00.000Z",
        "chapters": {"B01": {"ratio": 0.2, "done": False}},
    }}})

    books = client.get("/api/books/progress").get_json()["books"]
    assert books["bir-kitap"]["lastChapterId"] == "B02"


def test_junk_from_a_client_is_dropped_not_stored(client, progress_file):
    sign_in(client, READER)
    resp = client.post("/api/books/progress", json={"books": {
        "../../etc": {"lastChapterId": "B01", "updatedAt": "2026-08-16T09:00:00Z"},
        "iyi-kitap": {
            "lastChapterId": "B01",
            "updatedAt": "2026-08-16T09:00:00Z",
            "chapters": {
                "B01": {"ratio": 12, "done": "evet"},
                "bad id!": {"ratio": 0.5},
            },
        },
    }})
    books = resp.get_json()["books"]
    assert "../../etc" not in books
    assert list(books["iyi-kitap"]["chapters"]) == ["B01"]
    assert books["iyi-kitap"]["chapters"]["B01"] == {"ratio": 1.0, "done": True}


def test_progress_needs_a_session_not_an_api_key(client, progress_file, monkeypatch):
    monkeypatch.setattr(dashboard_api, "API_KEYS", [("test", "tdyK_testkey")])
    resp = client.get("/api/books/progress?api_key=tdyK_testkey")
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "session_required"
