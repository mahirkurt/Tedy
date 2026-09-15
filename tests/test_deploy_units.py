"""Tracked systemd user units: loopback-only ted-mcp on the spec port, no drift toward system-unit syntax."""
from pathlib import Path

import pytest

from src.mcp_server import env_prep, http_app

ROOT = Path(__file__).resolve().parents[1]
TED = "/mnt/thunderbolt/workspaces/TED"


def _directives(name):
    section, rows, pending = "", [], ""
    for raw in (ROOT / name).read_text(encoding="utf-8").splitlines():
        line = pending + raw.strip()
        if line.endswith("\\"):
            pending = line[:-1] + " "
            continue
        pending = ""
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("["):
            section = line.strip("[]")
            continue
        key, _, value = line.partition("=")
        rows.append((section, key.strip(), value.strip()))
    return rows


def _environment(rows):
    return dict(v.split("=", 1) for s, k, v in rows if s == "Service" and k == "Environment")


@pytest.mark.parametrize("name", ["ted-dashboard.service", "ted-mcp.service"])
def test_units_are_user_units_run_from_the_main_checkout(name):
    rows = _directives(name)
    keys = {(s, k) for s, k, _ in rows}
    assert ("Service", "User") not in keys and ("Service", "Group") not in keys
    assert ("Install", "WantedBy", "default.target") in rows
    assert ("Service", "WorkingDirectory", TED) in rows
    assert ("Service", "EnvironmentFile", f"{TED}/.env") in rows
    assert ("Service", "Restart", "on-failure") in rows


def test_ted_mcp_binds_loopback_on_the_code_default_port():
    rows = _directives("ted-mcp.service")
    env = _environment(rows)
    assert env["TED_MCP_HOST"] == http_app.DEFAULT_HOST == "127.0.0.1"
    assert int(env["TED_MCP_PORT"]) == http_app.DEFAULT_PORT
    assert "0.0.0.0" not in (ROOT / "ted-mcp.service").read_text(encoding="utf-8")
    assert "TED_MCP_PROJECT_ROOT" not in env
    exec_start = next(v for s, k, v in rows if k == "ExecStart")
    assert exec_start == f"{TED}/.venv/bin/python -m src.mcp_server.http_app"


def test_ted_mcp_public_host_is_allowed_and_dashboard_url_matches_dashboard_bind():
    env = _environment(_directives("ted-mcp.service"))
    assert env["TED_MCP_PUBLIC_BASE_URL"] == "https://mcp.tedy.online"
    assert env["TED_MCP_ALLOWED_HOSTS"].split(",") == ["mcp.tedy.online"]
    dash_exec = next(v for s, k, v in _directives("ted-dashboard.service") if k == "ExecStart")
    port = dash_exec.split("--bind", 1)[1].split()[0].rsplit(":", 1)[1]
    assert env["TED_DASHBOARD_API_URL"] == f"http://127.0.0.1:{port}"


def test_unit_sets_topology_and_nothing_the_env_file_may_override():
    env = _environment(_directives("ted-mcp.service"))
    assert set(env_prep.TOPOLOGY) <= set(env)
    assert set(env) - {"PATH", "PYTHONUNBUFFERED"} <= set(env_prep.UNIT_ONLY)
