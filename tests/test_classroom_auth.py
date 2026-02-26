"""Tests for Classroom OAuth scopes."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.google_auth import SCOPES


class TestClassroomScopes:
    def test_classroom_courses_scope(self):
        assert "https://www.googleapis.com/auth/classroom.courses" in SCOPES

    def test_classroom_coursework_scope(self):
        assert "https://www.googleapis.com/auth/classroom.coursework.students" in SCOPES

    def test_classroom_announcements_scope(self):
        assert "https://www.googleapis.com/auth/classroom.announcements" in SCOPES

    def test_classroom_rosters_scope(self):
        assert "https://www.googleapis.com/auth/classroom.rosters" in SCOPES

    def test_classroom_profile_scope(self):
        assert "https://www.googleapis.com/auth/classroom.profile.emails" in SCOPES
