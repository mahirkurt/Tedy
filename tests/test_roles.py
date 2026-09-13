"""Roster extraction: one source of roles for the dashboard and ted-mcp."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_role_of_known_and_unknown_emails():
    from src import roles

    assert roles.role_of("drmahirkurt@gmail.com") == roles.ROLE_FULL
    assert roles.role_of("murzogluhulya@gmail.com") == roles.ROLE_READER
    assert roles.role_of("stranger@example.com") is None
    assert roles.role_of(None) is None
    assert roles.role_of("") is None


def test_role_of_normalises_case_and_whitespace():
    from src import roles

    assert roles.role_of("  DrMahirKurt@Gmail.com ") == roles.ROLE_FULL


def test_is_full_only_for_full_role():
    from src import roles

    assert roles.is_full("isikkurtx@gmail.com") is True
    assert roles.is_full("mahirkurtmd@gmail.com") is False
    assert roles.is_full("stranger@example.com") is False


def test_derived_sets_match_roster():
    from src import roles

    assert roles.ALLOWED_EMAILS == set(roles.USER_ROLES)
    assert roles.FULL_ACCESS_EMAILS == {
        e for e, r in roles.USER_ROLES.items() if r == roles.ROLE_FULL
    }


def test_dashboard_reexports_the_same_objects(monkeypatch):
    monkeypatch.setenv("TEST_AUTH_BYPASS", "1")
    monkeypatch.setenv("DASHBOARD_SECRET_KEY", os.environ.get("DASHBOARD_SECRET_KEY") or "test-secret")
    from src import dashboard_api, roles

    assert dashboard_api.USER_ROLES is roles.USER_ROLES
    assert dashboard_api.ALLOWED_EMAILS is roles.ALLOWED_EMAILS
    assert dashboard_api.FULL_ACCESS_EMAILS is roles.FULL_ACCESS_EMAILS
    assert dashboard_api.GOOGLE_CLIENT_ID == roles.GOOGLE_CLIENT_ID
    assert dashboard_api.ROLE_FULL == roles.ROLE_FULL


def test_importing_roles_does_not_pull_in_flask():
    code = "import sys; import src.roles; print('flask' in sys.modules)"
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False"
