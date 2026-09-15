"""Fleet contract probe: tools/list only, missing tools reported, no key is honest, ERIC probed without a key."""
import importlib.util
from pathlib import Path

import pytest

from src.mcp_server.config import load_settings

SPEC = importlib.util.spec_from_file_location("filo", Path(__file__).resolve().parents[1] / "scripts" / "edupedia_filo_sozlesme.py")
filo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(filo)


class FakeClient:
    listed: dict = {}

    def __init__(self, name, url, api_key):
        self.name = name

    def list_tools(self):
        return [{"name": n} for n in self.listed.get(self.name, [])]

    def call_tool(self, *args, **kwargs):
        raise AssertionError("the probe must never call a tool")


class FakeResponse:
    status_code = 200

    def json(self):
        return {"response": {"docs": [{"id": "EJ1"}]}}


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(params)
        return FakeResponse()


def test_probe_reports_ok_missing_and_absent_keys(tmp_path):
    FakeClient.listed = {name: sorted(tools) for name, tools in filo.BEKLENEN.items()}
    FakeClient.listed["minimax"] = ["text_to_audio"]
    env = {f"{k}": "x" for k in ("MUFREDAT_MCP_API_KEY", "EGITIM_KAYNAK_MCP_API_KEY", "ANAMNESIS_MCP_API_KEY",
                                  "PEXELS_MCP_API_KEY", "MINIMAX_MCP_API_KEY", "TR_LITERATUR_MCP_API_KEY")}
    session = FakeSession()
    results = filo.yokla(load_settings(env, project_root=tmp_path), client_factory=FakeClient, session=session)
    assert results["maarif-mufredat"] == "ok" and results["pexels"] == "ok"
    assert results["minimax"].startswith("eksik: ") and "text_to_image" in results["minimax"]
    assert results["comfyui"] == "anahtar yok" and results["openalex"] == "anahtar yok"
    assert results["eric"] == "ok" and session.calls[0]["rows"] == 1


def test_voice_tools_are_not_expected_anywhere():
    assert not {"voice_clone", "voice_design"} & set().union(*filo.BEKLENEN.values())


def test_eksikler():
    assert filo.eksikler([{"name": "a"}, {"name": "b"}], {"a", "c"}) == ["c"]
