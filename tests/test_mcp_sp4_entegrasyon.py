"""SP4 integration: progress summary tool, durum budget and gates, fourteen tools over real HTTP wiring."""
import json

import pytest
from starlette.testclient import TestClient

from src import module_progress as mp
from src.mcp_server import http_app, server, tools
from src.mcp_server.config import load_settings
from src.mcp_server.katalog import CatalogWriter
from src.mcp_server.oauth_store import OAuthStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"
FOURTEEN = {"edupedia_durum", "edupedia_rehber", "edupedia_baglam", "edupedia_kapsam", "edupedia_kaynak_oku",
            "edupedia_derle", "edupedia_gorsel", "edupedia_medya", "edupedia_pedagoji_kaniti", "edupedia_onizle",
            "edupedia_yayinla", "edupedia_katalog", "edupedia_ilerleme", "edupedia_kaldir"}
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}


class _NoFed:
    def configured(self, name):
        return False


def _sse_json(response):
    for line in response.text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return response.json()


@pytest.fixture
def t(tmp_path):
    settings = load_settings({}, project_root=tmp_path)
    writer = CatalogWriter(settings.data_dir)
    draft = {"meta": {"title": "t", "subject": "Fen Bilimleri", "gradeLevel": "5. Sınıf", "mode": "QUIZ"},
             "gates": {"pass": 18, "warn": 0, "fail": 0}}
    writer.yayinla(FULL, draft, b"<html></html>", "fen5-su", None)
    store = mp.ProgressStore(settings.data_dir / "module_progress.json")
    event = mp.validate_event({"type": "edupedia:progress", "v": 1, "slug": "fen5-su", "version": 1, "event": "answer",
                               "segmentId": "q1", "item": 0, "correct": True, "attempts": 2, "xp": 15, "ts": 1}, "fen5-su", 1)
    store.record("a" * 32, "fen5-su", 1, event, 1_800_000_000.0)
    return tools.Tools(settings, _NoFed())


def test_ilerleme_returns_aggregates_without_identities(t):
    body = t.ilerleme(FULL, "fen5-su")
    assert body["status"] == "ok" and body["mcp_verified"] is False
    assert body["surumler"] == [{"version": 1, "kisi_sayisi": 1, "cevaplanan_soru": 1, "dogru_orani": 1.0,
                                 "deneme_toplam": 2, "tamamlayan": 0, "son_erisim": "2027-01-15T08:00:00+00:00"}]
    assert "a" * 32 not in json.dumps(body) and FULL not in json.dumps(body)
    assert t.ilerleme(FULL, "fen5-su", version=1)["surumler"][0]["version"] == 1
    assert t.ilerleme(FULL, "../x")["status"] == "gecersiz_slug"
    assert t.ilerleme(FULL, "fen5-su", version=0)["status"] == "gecersiz_surum"
    assert t.ilerleme(FULL, "yok-boyle")["status"] == "bulunamadi"


def test_durum_reports_eighteen_gates_and_no_budget_without_ledger(t):
    body = t.durum(FULL)
    assert body["kapi_sayisi"] == 18 and body["medya_butcesi"] is None
    assert not any("sonraki alt projede" in note for note in body["notlar"])


def test_instructions_name_the_flow_and_kaynak_verisi():
    for fragment in ("edupedia_rehber('akis')", "edupedia_derle", "edupedia_yayinla", "kaynak_verisi",
                     "HTML'i kendin yazma"):
        assert fragment in server.INSTRUCTIONS


def test_fourteen_tools_and_budget_over_real_wiring(tmp_path):
    (tmp_path / "output").mkdir()
    key = OAuthStore(tmp_path / "output" / "ted_mcp_oauth.sqlite3").create_static_key("t", FULL)
    env = {"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_PROJECT_ROOT": str(tmp_path), "TED_MCP_FORM_SECRET": "f" * 40,
           "EDUPEDIA_TICKET_SECRET": "t" * 40, "EDUPEDIA_MEDIA_MONTHLY_USD": "10"}
    headers = {**MCP_HEADERS, "authorization": f"Bearer {key}"}
    with TestClient(http_app.create_app_from_env(env), base_url=BASE) as client:
        listed = _sse_json(client.post("/mcp", headers=headers,
                                       json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}))
        assert {tool["name"] for tool in listed["result"]["tools"]} == FOURTEEN
        durum = _sse_json(client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "edupedia_durum", "arguments": {}}}))
    body = json.loads(durum["result"]["content"][0]["text"])
    assert body["kapi_sayisi"] == 18
    assert body["medya_butcesi"]["tavan_usd"] == 10.0 and "TAHMİN" in body["medya_butcesi"]["not"]
