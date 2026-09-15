"""edupedia_derle / edupedia_onizle: run anchoring, immutable drafts, honest statuses, HTTP body budget."""
import hashlib
import json

import anyio
import pytest
from starlette.testclient import TestClient

from src import module_store
from src.mcp_server import derleme, gates, http_app, ornekler, server, tools
from src.mcp_server.config import SERVER_DEFAULTS, load_settings
from src.mcp_server.derle_araci import NEXT_FAIL, NEXT_OK, Derleyici
from src.mcp_server.oauth_store import OAuthStore
from src.mcp_server.runs import RunStore
from src.mcp_server.taslak import DraftStore

BASE = "https://mcp.tedy.online"
FULL = "drmahirkurt@gmail.com"
RUN_ID = "abcdef012345"
MCP_HEADERS = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
RUN_RECORD = {
    "run_id": RUN_ID, "created_by": FULL,
    "cerceve": {"kind": "textbook", "document_id": 197, "title": "Fen Bilimleri 5", "sayfalar": "111-116"},
    "kazanimlar": [{"code": "FB.5.4.1.1", "text": "Maddenin hâllerini açıklar."}],
    "coverage": {"maarif-mufredat": "hit", "egitim-kaynak": "hit"},
}


def _sse_json(response):
    for line in response.text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return response.json()


class _Fed:
    def configured(self, name):
        return name in {"maarif-mufredat", "pexels"}

    def call(self, server_name, tool, args, beklenen, deadline=None):
        return {"ok": True}


@pytest.fixture
def derleyici(tmp_path):
    runs = RunStore(tmp_path)
    runs.save(RUN_ID, RUN_RECORD)
    return Derleyici(runs, DraftStore(tmp_path), "https://tedy.online", "https://tedy.online",
                     clock=lambda: 1_800_000_000.0)


def _teach(data):
    return next(s for s in data["segments"] if s["type"] == "teach")


def _budget_sized_quiz():
    data = ornekler.ornek("QUIZ")
    base = derleme.girdi_boyutu(data)
    _teach(data)["body"].append("<p>" + "a" * (derleme.MAX_INPUT_BYTES - base - 12) + "</p>")
    assert derleme.MAX_INPUT_BYTES - 64 <= derleme.girdi_boyutu(data) <= derleme.MAX_INPUT_BYTES
    return data


def test_sp4_fleet_and_settings(tmp_path):
    assert {"pexels", "minimax", "comfyui", "tr-literatur", "openalex"} <= set(SERVER_DEFAULTS)
    s = load_settings({"TR_LITERATUR_MCP_URL": "http://127.0.0.1:9999/mcp", "EDUPEDIA_TICKET_SECRET": "s" * 40,
                       "EDUPEDIA_MEDIA_MONTHLY_USD": "abc",
                       "TED_MCP_VIEWER_HOSTS": "modul.tedy.online, modul.test"}, project_root=tmp_path)
    assert s.servers["tr-literatur"].url == "http://127.0.0.1:9999/mcp"
    assert s.servers["openalex"].url == "https://openalex.cureonics.com/mcp"
    assert s.ticket_secret == b"s" * 40 and "s" * 40 not in repr(s)
    assert s.media_monthly_usd == 10.0 and s.viewer_hosts == ("modul.tedy.online", "modul.test")
    assert s.parent_origin == "https://tedy.online" and s.dashboard_public_url == "https://tedy.online"
    assert "pk_gizli" not in repr(load_settings({"PEXELS_MCP_API_KEY": "pk_gizli"}, project_root=tmp_path))
    assert load_settings({"EDUPEDIA_MEDIA_MONTHLY_USD": "-5"}, project_root=tmp_path).media_monthly_usd == 0.0
    assert load_settings({"EDUPEDIA_MEDIA_MONTHLY_USD": "inf"}, project_root=tmp_path).media_monthly_usd == 10.0
    assert load_settings({"EDUPEDIA_MEDIA_MONTHLY_USD": "nan"}, project_root=tmp_path).media_monthly_usd == 10.0


@pytest.mark.parametrize("value", [
    "https://tedy.online/x",
    "ftp://tedy.online",
    "tedy.online",
    "https://tedy.online" + chr(10),
])
def test_parent_origin_fails_fast_on_a_malformed_value(tmp_path, value):
    with pytest.raises(ValueError, match="EDUPEDIA_PARENT_ORIGIN") as excinfo:
        load_settings({"EDUPEDIA_PARENT_ORIGIN": value}, project_root=tmp_path)
    assert value not in str(excinfo.value)


def test_parent_origin_accepts_loopback_and_the_default(tmp_path):
    assert load_settings({"EDUPEDIA_PARENT_ORIGIN": "http://127.0.0.1:8286"},
                         project_root=tmp_path).parent_origin == "http://127.0.0.1:8286"
    assert load_settings({}, project_root=tmp_path).parent_origin == "https://tedy.online"


def test_durum_skips_servers_without_a_health_call(tmp_path):
    body = tools.Tools(load_settings({}, project_root=tmp_path), _Fed()).durum(FULL, canli=True)
    assert body["coverage"]["pexels"] == "skipped:saglik_cagrisi_yok"
    assert body["coverage"]["maarif-mufredat"] == "hit"


def test_compile_saves_an_immutable_draft_and_returns_no_html(tmp_path, derleyici):
    body = derleyici.derle(FULL, RUN_ID, ornekler.ornek("QUIZ"))
    assert body["status"] == "ok" and body["kapi_ozeti"]["fail"] == 0
    assert len(body["kapilar"]) == 18 and body["sonraki_adim"] == NEXT_OK
    dumped = json.dumps(body, ensure_ascii=False)
    assert "<html" not in dumped and "data:" not in dumped and "const MODULE_DATA" not in dumped
    drafts = DraftStore(tmp_path)
    record, html = drafts.load(body["taslak_id"]), drafts.html_bytes(body["taslak_id"])
    assert record["sha256"] == hashlib.sha256(html).hexdigest() and record["bayt"] == body["bayt"] == len(html)
    assert record["created_by"] == FULL and record["run_id"] == RUN_ID
    assert record["meta"]["mode"] == "QUIZ" and record["outcomes"] == ["FB.5.4.1.1"]
    assert record["frame_source"]["document_id"] == 197 and record["coverage"] == RUN_RECORD["coverage"]
    with pytest.raises(FileExistsError):
        drafts.save(body["taslak_id"], "<html></html>", {})


def test_failing_gates_still_produce_a_draft_with_repair_guidance(derleyici):
    data = ornekler.ornek("MODULE")
    data["verification"]["scope"]["in_frame"] = False
    body = derleyici.derle(FULL, RUN_ID, data)
    assert body["status"] == "ok" and body["kapi_ozeti"]["fail"] >= 1
    assert body["kapilar"]["G-VERIFY"]["status"] == "FAIL" and body["kapilar"]["G-VERIFY"]["detay"]
    assert body["sonraki_adim"] == NEXT_FAIL
    dumped = json.dumps(body, ensure_ascii=False)
    assert "<html" not in dumped and "data:" not in dumped and "const MODULE_DATA" not in dumped


def test_module_data_may_arrive_as_json_text(derleyici):
    assert derleyici.derle(FULL, RUN_ID, json.dumps(ornekler.ornek("QUIZ"), ensure_ascii=False))["status"] == "ok"
    assert derleyici.derle(FULL, RUN_ID, "{bozuk")["status"] == "sema_hatasi"


@pytest.mark.parametrize("run_id", ["ffffffffffff", "../../etc", ""])
def test_unknown_run_is_refused(derleyici, run_id):
    body = derleyici.derle(FULL, run_id, ornekler.ornek("QUIZ"))
    assert body["status"] == "run_bulunamadi" and "edupedia_kapsam" in body["not"]


def test_frame_and_outcomes_must_match_the_run(derleyici):
    data = ornekler.ornek("QUIZ")
    data["verification"]["frame_source"]["document_id"] = 198
    for claim in data["verification"]["claims"]:
        claim["grounding"]["document_id"] = 198
    assert derleyici.derle(FULL, RUN_ID, data)["status"] == "cerceve_uyusmazligi"
    data = ornekler.ornek("QUIZ")
    data["curriculum"]["outcomes"][0]["code"] = "FB.5.9.9.9"
    body = derleyici.derle(FULL, RUN_ID, data)
    assert body["status"] == "kazanim_run_disi" and body["kodlar"] == ["FB.5.9.9.9"]


def test_oversize_and_schema_statuses_are_honest(derleyici):
    data = ornekler.ornek("QUIZ")
    _teach(data)["body"] = ["a" * (derleme.MAX_INPUT_BYTES + 1)]
    body = derleyici.derle(FULL, RUN_ID, data)
    assert body["status"] == "cok_buyuk" and body["sinir"] == 400_000 and body["bayt"] > 400_000
    data = ornekler.ornek("QUIZ")
    data.pop("verification")
    assert derleyici.derle(FULL, RUN_ID, data)["status"] == "sema_hatasi"


def test_onizle(derleyici):
    taslak_id = derleyici.derle(FULL, RUN_ID, ornekler.ornek("QUIZ"))["taslak_id"]
    body = derleyici.onizle(FULL, taslak_id)
    assert body["status"] == "ok" and body["url"] == f"https://tedy.online/moduller/taslak/{taslak_id}"
    assert derleyici.onizle(FULL, "ffffffffffffffff")["status"] == "taslak_bulunamadi"
    assert derleyici.onizle(FULL, "../x")["status"] == "taslak_bulunamadi"


def test_gate_crash_returns_a_closed_status_and_creates_no_draft(tmp_path, derleyici, monkeypatch):
    def _boom(html):
        raise RuntimeError("secret internal detail /home/x")

    monkeypatch.setattr(gates, "run_gates", _boom)
    body = derleyici.derle(FULL, RUN_ID, ornekler.ornek("QUIZ"))
    assert body["status"] == "sunucu_hatasi"
    dumped = json.dumps(body, ensure_ascii=False)
    assert "secret internal detail" not in dumped and "RuntimeError" not in dumped
    assert not module_store.drafts_root(tmp_path).exists()


def test_derle_closes_a_bad_parent_origin_set_directly_bypassing_load_settings(tmp_path):
    runs = RunStore(tmp_path)
    runs.save(RUN_ID, RUN_RECORD)
    bad = Derleyici(runs, DraftStore(tmp_path), "https://tedy.online/x", "https://tedy.online",
                    clock=lambda: 1_800_000_000.0)
    assert bad.derle(FULL, RUN_ID, ornekler.ornek("QUIZ"))["status"] == "sunucu_hatasi"


def test_draft_save_crash_returns_a_closed_status(derleyici, monkeypatch):
    def _boom(self, taslak_id, html, record):
        raise FileExistsError("taslak zaten var")

    monkeypatch.setattr(DraftStore, "save", _boom)
    body = derleyici.derle(FULL, RUN_ID, ornekler.ornek("QUIZ"))
    assert body["status"] == "sunucu_hatasi"


def test_derle_and_onizle_are_registered(tmp_path):
    mcp = server.build_server(tools.Tools(load_settings({}, project_root=tmp_path), _Fed()))
    listed = {t.name: t for t in anyio.run(mcp.list_tools)}
    assert listed["edupedia_derle"].annotations.readOnlyHint is False
    assert listed["edupedia_onizle"].annotations.readOnlyHint is True


def _http_env(tmp_path, **extra):
    (tmp_path / "output").mkdir(exist_ok=True)
    RunStore(tmp_path / "output").save(RUN_ID, RUN_RECORD)
    key = OAuthStore(tmp_path / "output" / "ted_mcp_oauth.sqlite3").create_static_key("t", FULL)
    env = {"TED_MCP_PUBLIC_BASE_URL": BASE, "TED_MCP_PROJECT_ROOT": str(tmp_path), "TED_MCP_FORM_SECRET": "f" * 40}
    env.update(extra)
    return env, {**MCP_HEADERS, "authorization": f"Bearer {key}"}


def _call(arguments):
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "edupedia_derle", "arguments": arguments}}


def test_http_layer_admits_a_budget_sized_module_and_refuses_an_oversize_body(tmp_path):
    env, headers = _http_env(tmp_path, TED_MCP_MAX_BODY_BYTES="2097152")
    with TestClient(http_app.create_app_from_env(env), base_url=BASE) as client:
        ok = client.post("/mcp", headers=headers, json=_call({"run_id": RUN_ID, "module_data": _budget_sized_quiz()}))
        assert ok.status_code == 200
        assert json.loads(_sse_json(ok)["result"]["content"][0]["text"])["status"] == "ok"
        oversize = json.dumps(_call({"run_id": RUN_ID, "module_data": "a" * 2_500_000})).encode()
        assert client.post("/mcp", headers=headers, content=oversize).status_code == 413


def test_default_body_limit_covers_the_module_data_budget(tmp_path):
    env, headers = _http_env(tmp_path)
    with TestClient(http_app.create_app_from_env(env), base_url=BASE) as client:
        response = client.post("/mcp", headers=headers,
                               json=_call({"run_id": RUN_ID, "module_data": json.dumps(_budget_sized_quiz(), ensure_ascii=False)}))
    assert response.status_code == 200
