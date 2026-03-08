"""Integration tests for dashboard API endpoints."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

from src.dashboard_api import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestAuthBypass:
    def test_schedule_without_login(self, client):
        resp = client.get("/api/schedule")
        assert resp.status_code == 200


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
