"""Tests for Google Classroom sync module."""
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch, call
import time


class TestComputeHash:
    def test_same_input_same_hash(self):
        from src.sync_to_classroom import compute_hash
        item = {"title": "Test", "description": "Desc"}
        assert compute_hash(item) == compute_hash(item)

    def test_different_input_different_hash(self):
        from src.sync_to_classroom import compute_hash
        a = {"title": "Test A"}
        b = {"title": "Test B"}
        assert compute_hash(a) != compute_hash(b)

    def test_order_independent(self):
        from src.sync_to_classroom import compute_hash
        a = {"b": 2, "a": 1}
        b = {"a": 1, "b": 2}
        assert compute_hash(a) == compute_hash(b)

    def test_string_input(self):
        from src.sync_to_classroom import compute_hash
        h = compute_hash("simple string")
        assert isinstance(h, str) and len(h) == 16


class TestSyncState:
    def test_load_missing_file(self, tmp_path):
        from src.sync_to_classroom import load_sync_state
        state = load_sync_state(str(tmp_path / "nonexistent.json"))
        assert state == {}

    def test_save_and_load(self, tmp_path):
        from src.sync_to_classroom import load_sync_state, save_sync_state
        path = str(tmp_path / "state.json")
        data = {"key1": {"classroom_id": "abc", "last_hash": "def"}}
        save_sync_state(data, path)
        loaded = load_sync_state(path)
        assert loaded == data


class TestEnsureCourses:
    def _mock_service(self, existing_courses=None):
        """Build a mock Classroom service with optional existing courses."""
        svc = MagicMock()
        courses_list = existing_courses or []
        svc.courses().list().execute.return_value = {
            "courses": courses_list
        }
        svc.courses().create.return_value.execute.side_effect = lambda: {
            "id": f"new_{time.time()}",
            "name": "mock",
            "courseState": "ACTIVE",
        }
        svc.invitations().create.return_value.execute.return_value = {}
        return svc

    def test_creates_missing_courses(self):
        from src.sync_to_classroom import ensure_courses, GENERAL_COURSE
        svc = self._mock_service(existing_courses=[])
        ders_listesi = ["Matematik", "Türkçe"]

        courses = ensure_courses(svc, ders_listesi)

        assert "Matematik" in courses
        assert "Türkçe" in courses
        assert GENERAL_COURSE in courses
        assert svc.courses().create.call_count == 3  # 2 courses + TED Genel

    def test_reuses_existing_courses(self):
        from src.sync_to_classroom import ensure_courses, COURSE_SECTION, GENERAL_COURSE
        existing = [
            {"id": "c1", "name": "Matematik", "section": COURSE_SECTION, "courseState": "ACTIVE"},
            {"id": "c2", "name": GENERAL_COURSE, "section": COURSE_SECTION, "courseState": "ACTIVE"},
        ]
        svc = self._mock_service(existing_courses=existing)

        courses = ensure_courses(svc, ["Matematik"])

        assert courses["Matematik"] == "c1"
        assert svc.courses().create.call_count == 0

    def test_invites_student(self):
        from src.sync_to_classroom import ensure_courses, STUDENT_EMAIL
        svc = self._mock_service(existing_courses=[])

        ensure_courses(svc, ["Matematik"])

        inv_calls = svc.invitations().create.call_args_list
        assert len(inv_calls) >= 2  # Matematik + TED Genel
