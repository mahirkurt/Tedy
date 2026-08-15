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
