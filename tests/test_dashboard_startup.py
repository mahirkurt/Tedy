"""Startup regressions for the dashboard process boundary."""

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_import_survives_broken_optional_assistant_module():
    """The dashboard must stay available when the assistant cannot import."""
    env = os.environ.copy()
    env["TEST_AUTH_BYPASS"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", "import src.dashboard_api"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_broken_optional_assistant_returns_service_unavailable(monkeypatch):
    """Assistant failure is isolated behind a stable API response."""
    monkeypatch.setenv("TEST_AUTH_BYPASS", "1")
    from src import dashboard_api

    def unavailable_runtime():
        raise dashboard_api.AssistantUnavailableError("test")

    monkeypatch.setattr(
        dashboard_api,
        "_assistant_runtime",
        unavailable_runtime,
    )
    with dashboard_api.app.test_client() as client:
        response = client.post(
            "/api/assistant/chat",
            json={"messages": [{"role": "user", "content": "test"}]},
        )

    assert response.status_code == 503
    assert response.get_json() == {"error": "assistant_unavailable"}


# --- H3: app.secret_key must fail loudly, not silently fall back ---

def test_missing_secret_key_raises_at_import():
    """No DASHBOARD_SECRET_KEY (env or .env) must abort the process.

    With 2 gunicorn workers, a silent fallback (secrets.token_hex(32)) means
    each worker mints its own key, so sessions signed by one worker are
    rejected by the other -- users get logged out at random with no error
    anywhere. A dead service with a clear reason beats that.

    load_env() is stubbed out here (not just DASHBOARD_SECRET_KEY removed
    from the subprocess env) because the real .env on this machine legitimately
    has the key set -- without stubbing, load_env() would just refill the gap
    and this test would never observe the "truly absent" case it exists to check.
    """
    env = os.environ.copy()
    env.pop("DASHBOARD_SECRET_KEY", None)
    script = (
        "import sys; sys.path.insert(0, " + repr(str(PROJECT_ROOT)) + "); "
        "import src.env_loader as _el; "
        "_el.load_env = lambda *a, **k: None; "  # keep the real .env's key out of this
        "import src.dashboard_api"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode != 0
    assert "DASHBOARD_SECRET_KEY" in result.stderr


def test_secret_key_present_imports_cleanly():
    env = os.environ.copy()
    env["DASHBOARD_SECRET_KEY"] = "a" * 64
    env["TEST_AUTH_BYPASS"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", "import src.dashboard_api; print('imported-ok')"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "imported-ok" in result.stdout


# --- H5: TEST_AUTH_BYPASS must announce itself loudly when active ---

def test_auth_bypass_emits_warning_when_active():
    env = os.environ.copy()
    env["TEST_AUTH_BYPASS"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", "import src.dashboard_api"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "AUTH BYPASS ACTIVE" in result.stderr


def test_no_warning_when_bypass_is_not_active():
    env = os.environ.copy()
    env.pop("TEST_AUTH_BYPASS", None)
    result = subprocess.run(
        [sys.executable, "-c", "import src.dashboard_api"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "AUTH BYPASS ACTIVE" not in result.stderr
