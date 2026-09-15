"""Dashboard module endpoints: role and session gates, tickets, progress schema, per-person state, CSP."""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402
from src import module_store as ms  # noqa: E402
from src import module_ticket as mt  # noqa: E402

app = dashboard_api.app
SECRET = "t" * 40
FULL = "isikkurtx@gmail.com"
FULL_2 = "drmahirkurt@gmail.com"
READER = "murzogluhulya@gmail.com"
TASLAK = "0123456789abcdef"
FRAME_CSP = "frame-src https://modul.tedy.online https://accounts.google.com"


def _row(slug, version, status="active", created="2026-09-14T10:00:00+00:00"):
    return {"slug": slug, "version": version, "status": status, "title": f"{slug} v{version}",
            "subject": "Fen Bilimleri", "gradeLevel": "5. Sınıf", "mode": "QUIZ", "outcomes": ["FB.5.4.1.1"],
            "ted_link": {"kind": "exam", "id": "ex-1"} if slug == "fen5-su" else None, "created_at": created,
            "gates": {"pass": 17, "warn": 1, "fail": 0}, "sha256": "x", "created_by": FULL_2}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(dashboard_api, "API_KEYS", [("entegrasyon", "tdyK_test")])
    monkeypatch.setenv("EDUPEDIA_TICKET_SECRET", SECRET)
    rows = [_row("fen5-su", 1), _row("fen5-su", 2, created="2026-09-14T11:00:00+00:00"), _row("eski", 1, "removed")]
    path = ms.catalog_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"surum": 1, "moduller": rows}), encoding="utf-8")
    draft = ms.drafts_root(tmp_path) / TASLAK
    draft.mkdir(parents=True)
    (draft / "taslak.json").write_text(json.dumps({"taslak_id": TASLAK}), encoding="utf-8")
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def sign_in(client, email):
    with client.session_transaction() as sess:
        sess["user_email"] = email
        sess["user_name"] = email.split("@")[0]


def _event(**over):
    body = {"type": "edupedia:progress", "v": 1, "slug": "fen5-su", "version": 2, "event": "answer",
            "segmentId": "q1", "item": 0, "correct": True, "attempts": 1, "xp": 15, "ts": 1789400000000}
    body.update(over)
    return body


def test_module_endpoints_are_not_reader_endpoints():
    names = {"modules_list", "module_ticket_issue", "module_draft_ticket_issue", "module_progress_get",
             "module_progress_save"}
    assert not names & dashboard_api.READER_ENDPOINTS


def test_catalog_list_gates_and_shape(client):
    assert client.get("/api/modules").status_code == 401
    sign_in(client, READER)
    assert client.get("/api/modules").status_code == 403
    sign_in(client, FULL)
    body = client.get("/api/modules").get_json()
    assert [(m["slug"], m["version"]) for m in body["moduller"]] == [("fen5-su", 2)]
    assert set(body["moduller"][0]) == {"slug", "version", "title", "subject", "gradeLevel", "mode", "outcomes",
                                        "ted_link", "created_at", "gates"}


def test_api_key_may_list_but_never_gets_tickets_or_progress(client):
    headers = {"Authorization": "Bearer tdyK_test"}
    assert client.get("/api/modules", headers=headers).status_code == 200
    assert client.get("/api/modules/fen5-su/v2/ticket", headers=headers).get_json() == {"error": "session_required"}
    assert client.get("/api/modules/fen5-su/progress?version=2", headers=headers).status_code == 403
    assert client.post("/api/modules/fen5-su/progress", json=_event(), headers=headers).status_code == 403


def test_ticket_issue_and_verification(client):
    sign_in(client, FULL)
    response = client.get("/api/modules/fen5-su/v2/ticket")
    assert response.status_code == 200 and response.headers["Cache-Control"] == "no-store"
    body = response.get_json()
    assert body["url"].startswith("https://modul.tedy.online/m/fen5-su/v2?t=")
    query = dict(part.split("=", 1) for part in body["url"].split("?", 1)[1].split("&"))
    assert mt.verify(SECRET.encode(), "m", "fen5-su", 2, query["t"], query["e"], query["u"], body["exp"] - 1,
                     {mt.email_hash(FULL)}) is None


@pytest.mark.parametrize("path,status", [
    ("/api/modules/eski/v1/ticket", 404), ("/api/modules/fen5-su/v9/ticket", 404),
    ("/api/modules/FEN/v1/ticket", 404), ("/api/modules/taslak/ffffffffffffffff/ticket", 404),
    ("/api/modules/taslak/zz/ticket", 404),
])
def test_ticket_refusals(client, path, status):
    sign_in(client, FULL)
    assert client.get(path).status_code == status


def test_ticket_requires_full_role_and_configured_secret(client, monkeypatch):
    sign_in(client, READER)
    assert client.get("/api/modules/fen5-su/v2/ticket").status_code == 403
    sign_in(client, FULL)
    draft = client.get(f"/api/modules/taslak/{TASLAK}/ticket").get_json()
    assert draft["url"].startswith(f"https://modul.tedy.online/taslak/{TASLAK}?t=")
    monkeypatch.delenv("EDUPEDIA_TICKET_SECRET")
    assert client.get("/api/modules/fen5-su/v2/ticket").get_json() == {"error": "ticket_unconfigured"}


def test_progress_round_trip_is_per_person(client, tmp_path):
    sign_in(client, FULL)
    saved = client.post("/api/modules/fen5-su/progress", json=_event())
    assert saved.status_code == 200 and saved.get_json()["state"] == {"answers": ["q1#0"], "done": [], "xp": 15}
    assert client.get("/api/modules/fen5-su/progress?version=2").get_json() == {
        "state": {"answers": ["q1#0"], "done": [], "xp": 15}}
    assert (tmp_path / "module_progress.json").is_file() and (tmp_path / "module_progress.json.lock").exists()
    sign_in(client, FULL_2)
    assert client.get("/api/modules/fen5-su/progress?version=2").get_json() == {
        "state": {"answers": [], "done": [], "xp": 0}}


@pytest.mark.parametrize("kwargs,status,error", [
    ({"json": _event(slug="baska")}, 400, "gecersiz_olay:modul_uyusmazligi"),
    ({"json": _event(extra=1)}, 400, "gecersiz_olay:bilinmeyen_alan"),
    ({"json": _event(segmentId="<img>")}, 400, "gecersiz_olay:segmentId"),
    ({"json": _event(version=0)}, 400, "gecersiz_olay:modul"),
    ({"data": "type=edupedia:progress", "content_type": "text/plain"}, 400, "gecersiz_olay:json"),
    ({"data": json.dumps(_event(segmentId="a" * 5000)), "content_type": "application/json"}, 413, "cok_buyuk"),
])
def test_progress_refusals(client, kwargs, status, error):
    sign_in(client, FULL)
    response = client.post("/api/modules/fen5-su/progress", **kwargs)
    assert response.status_code == status and response.get_json()["error"] == error


def test_progress_for_removed_or_unknown_module_is_not_found(client):
    sign_in(client, FULL)
    assert client.post("/api/modules/eski/progress", json=_event(slug="eski", version=1)).status_code == 404
    assert client.get("/api/modules/fen5-su/progress").status_code == 400
    sign_in(client, READER)
    assert client.post("/api/modules/fen5-su/progress", json=_event()).status_code == 403


def test_concurrent_progress_posts_keep_every_answer(client, tmp_path):
    def post(item):
        with app.test_client() as c:
            sign_in(c, FULL)
            return c.post("/api/modules/fen5-su/progress", json=_event(item=item)).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert set(pool.map(post, range(24))) == {200}
    data = json.loads((tmp_path / "module_progress.json").read_text(encoding="utf-8"))
    assert len(data["moduller"]["fen5-su"]["v2"]["kisiler"][mt.email_hash(FULL)]["cevaplar"]) == 24


def test_frame_src_policy_on_api_and_spa(client):
    assert client.get("/api/modules").headers["Content-Security-Policy"] == FRAME_CSP
    assert client.get("/").headers["Content-Security-Policy"] == FRAME_CSP
