"""env_prep: .env edits for ted-mcp that never print a value and keep both parsers in agreement."""
import io
import os
import stat

import pytest

from src.mcp_server import env_prep

OLD_KEY = "tdyK_" + "o" * 43


def _env(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _run(path, *argv, stdin=""):
    out = io.StringIO()
    rc = env_prep.main(["--env", str(path), *argv], stdin=io.StringIO(stdin), out=out)
    return rc, out.getvalue()


def _values(path):
    return env_prep.parse(path.read_text(encoding="utf-8").splitlines(keepends=True))


def test_generated_secret_is_written_but_never_printed(tmp_path, capsys):
    path = _env(tmp_path, "DASHBOARD_SECRET_KEY=abc\n")
    rc, out = _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret")
    assert rc == 0 and out == "yazıldı: TED_MCP_FORM_SECRET\n"
    secret = _values(path)["TED_MCP_FORM_SECRET"][0]
    assert len(secret) == 64 and secret not in out + capsys.readouterr().err
    assert _values(path)["DASHBOARD_SECRET_KEY"] == ["abc"]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_existing_name_is_refused_unless_replace(tmp_path):
    original = "TED_MCP_FORM_SECRET=" + "a" * 64 + "\n"
    path = _env(tmp_path, original)
    assert _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret")[0] == 2
    assert path.read_text() == original
    assert _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret", "--degistir")[0] == 0
    assert "a" * 64 not in path.read_text()


def test_stdin_value_is_validated(tmp_path):
    path = _env(tmp_path, "")
    assert _run(path, "ayarla", "ANAMNESIS_MCP_API_KEY", "--stdin", stdin="anm_live-KEY.1\n")[0] == 0
    assert _values(path)["ANAMNESIS_MCP_API_KEY"] == ["anm_live-KEY.1"]
    for bad in ("", "has space", 'quo"te', "a#b", "$HOME"):
        assert _run(path, "ayarla", "MINIMAX_MCP_API_KEY", "--stdin", stdin=bad)[0] == 2
    assert "MINIMAX_MCP_API_KEY" not in path.read_text()


@pytest.mark.parametrize("name", env_prep.UNIT_ONLY)
def test_unit_only_names_are_refused(tmp_path, name):
    path = _env(tmp_path, "")
    assert _run(path, "ayarla", name, "--stdin", stdin="127.0.0.1\n")[0] == 2
    assert path.read_text() == ""


def test_dashboard_key_is_appended_without_touching_existing_entries(tmp_path, capsys):
    path = _env(tmp_path, f"API_KEYS=default:{OLD_KEY}\nGEMINI_API_KEY=g\n")
    rc, out = _run(path, "dashboard-anahtari")
    assert rc == 0
    values = _values(path)
    new_key = values["TED_DASHBOARD_API_KEY"][0]
    assert new_key.startswith("tdyK_") and len(new_key) == 48
    assert values["API_KEYS"] == [f"default:{OLD_KEY},ted-mcp:{new_key}"]
    assert values["GEMINI_API_KEY"] == ["g"]
    assert new_key not in out + capsys.readouterr().err
    assert _run(path, "dashboard-anahtari")[0] == 2


def test_dashboard_key_removal_restores_previous_state(tmp_path):
    original = f"API_KEYS=default:{OLD_KEY}\n"
    path = _env(tmp_path, original)
    assert _run(path, "dashboard-anahtari")[0] == 0
    assert _run(path, "dashboard-anahtari-kaldir")[0] == 0
    assert path.read_text() == original
    assert _run(path, "dashboard-anahtari-kaldir")[0] == 2


def test_status_reports_names_only(tmp_path):
    path = _env(tmp_path, "")
    _run(path, "ayarla", "TED_MCP_FORM_SECRET", "--uret")
    _run(path, "dashboard-anahtari")
    rc, out = _run(path, "durum")
    assert rc == 0
    assert out.splitlines() == ["TAMAM TED_MCP_FORM_SECRET", "TAMAM TED_DASHBOARD_API_KEY",
                                "YOK ANAMNESIS_MCP_API_KEY", "YOK MUFREDAT_MCP_API_KEY",
                                "YOK EGITIM_KAYNAK_MCP_API_KEY"]
    for found in _values(path).values():
        assert found[0] not in out


@pytest.mark.parametrize("text,flag", [
    ("TED_MCP_FORM_SECRET=" + "a" * 64 + "\nTED_MCP_PORT=8090\n", "HATA TED_MCP_PORT"),
    ("TED_MCP_FORM_SECRET=short\n", "HATA TED_MCP_FORM_SECRET"),
    ("TED_MCP_FORM_SECRET=" + "a" * 64 + "\nTED_MCP_FORM_SECRET=" + "b" * 64 + "\n", "HATA TED_MCP_FORM_SECRET: 2 kez"),
    (f"TED_MCP_FORM_SECRET={'a' * 64}\nTED_DASHBOARD_API_KEY={OLD_KEY}\nAPI_KEYS=default:{OLD_KEY}\n",
     "HATA TED_DASHBOARD_API_KEY"),
])
def test_status_fails_on_misconfiguration(tmp_path, text, flag):
    rc, out = _run(_env(tmp_path, text), "durum")
    assert rc == 1 and flag in out


def test_symlinked_env_is_updated_through_the_link(tmp_path):
    real = _env(tmp_path, "A=1\n")
    worktree = tmp_path / "wt"
    worktree.mkdir()
    link = worktree / ".env"
    link.symlink_to(real)
    assert _run(link, "ayarla", "TED_MCP_FORM_SECRET", "--uret")[0] == 0
    assert link.is_symlink()
    assert "TED_MCP_FORM_SECRET=" in real.read_text()
