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


# ── B71 (S41): what the module frame's AI label explains ─────────────────────

RUN = "a1b2c3d4e5f6"
YAYIN_TASLAK = "fedcba9876543210"


def _asset(tmp_path, asset_id, tur, kaynak):
    folder = tmp_path / "edupedia_runs" / RUN / "assets"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{asset_id}.json").write_text(json.dumps({"asset_id": asset_id, "tur": tur, "kaynak": kaynak}),
                                             encoding="utf-8")


def _published_with_draft(tmp_path, sha="s" * 64, draft_sha="s" * 64):
    rows = [{**_row("fen5-su", 2), "sha256": sha, "taslak_id": YAYIN_TASLAK, "run_id": RUN,
             "frame_source": {"kind": "textbook", "document_id": 439, "pages": "112-120"}}]
    ms.catalog_path(tmp_path).write_text(json.dumps({"surum": 1, "moduller": rows}), encoding="utf-8")
    folder = ms.drafts_root(tmp_path) / YAYIN_TASLAK
    folder.mkdir(parents=True)
    (folder / "taslak.json").write_text(json.dumps({
        "taslak_id": YAYIN_TASLAK, "run_id": RUN, "sha256": draft_sha,
        "frame_source": {"kind": "textbook", "document_id": 439, "pages": "112-120", "title": "Fen Bilimleri 5"},
        "dogrulama": {"surum": 1, "iddialar": [
            {"iddia": "Madde katı, sıvı ve gaz hâllerinde bulunur.", "karar": "supported",
             "dayanak": {"document_id": 439, "page": 112}},
            {"iddia": "Isı alan buz erir.", "karar": "supported",
             "dayanak": {"kaynak": "OpenStax Kimya", "lisans": "CC BY 4.0"}}]},
        "assets": ["00000000000000a1", "00000000000000a2", "00000000000000a3", "0000000000000bad"],
    }), encoding="utf-8")
    _asset(tmp_path, "00000000000000a1", "image", "minimax")
    _asset(tmp_path, "00000000000000a2", "image", "mufredat")
    _asset(tmp_path, "00000000000000a3", "image", "pexels")


def test_module_explanation_names_what_ai_wrote_and_what_it_rests_on(client, tmp_path):
    _published_with_draft(tmp_path)
    assert client.get("/api/modules/fen5-su/v2/aciklama").status_code == 401
    sign_in(client, READER)
    assert client.get("/api/modules/fen5-su/v2/aciklama").status_code == 403
    sign_in(client, FULL)
    body = client.get("/api/modules/fen5-su/v2/aciklama").get_json()
    assert body["baslik"] == "fen5-su v2"
    assert body["ders"] == "Fen Bilimleri" and body["sinif"] == "5. Sınıf"
    assert body["kazanimlar"] == ["FB.5.4.1.1"]
    assert body["kitap"] == {"ad": "Fen Bilimleri 5", "sayfalar": "112-120"}
    assert body["iddia_durumu"] == "ok"
    assert body["iddialar"] == [
        {"iddia": "Madde katı, sıvı ve gaz hâllerinde bulunur.", "sayfa": 112, "kaynak": None},
        {"iddia": "Isı alan buz erir.", "sayfa": None, "kaynak": "OpenStax Kimya"}]
    assert body["medya"] == {"yapay_zeka": 1, "ders_kitabi": 1, "fotograf_arsivi": 1}
    # internal identifiers never reach the reader (D4)
    metin = json.dumps(body)
    for ic in ("439", RUN, YAYIN_TASLAK, "sha256", "document_id", "minimax", "pexels"):
        assert ic not in metin


def test_module_explanation_drops_claims_of_a_different_build(client, tmp_path):
    _published_with_draft(tmp_path, sha="s" * 64, draft_sha="d" * 64)
    sign_in(client, FULL)
    body = client.get("/api/modules/fen5-su/v2/aciklama").get_json()
    assert body["iddia_durumu"] == "uyusmazlik" and body["iddialar"] == []


def test_module_explanation_for_drafts_and_refusals(client, tmp_path):
    sign_in(client, FULL)
    assert client.get("/api/modules/eski/v1/aciklama").status_code == 404
    assert client.get("/api/modules/yok/v1/aciklama").status_code == 404
    assert client.get("/api/modules/taslak/ffffffffffffffff/aciklama").status_code == 404
    body = client.get(f"/api/modules/taslak/{TASLAK}/aciklama").get_json()
    assert body["iddia_durumu"] == "kayit_yok" and body["medya"] == {"yapay_zeka": 0, "ders_kitabi": 0,
                                                                     "fotograf_arsivi": 0}
    assert not {"module_explanation", "module_draft_explanation"} & dashboard_api.READER_ENDPOINTS


# ── 2026-10-19: the module page's head shows each outcome's wording in a dialog ──────────────

def test_module_explanation_carries_outcome_wording_and_time_from_the_draft(client, tmp_path):
    _published_with_draft(tmp_path)
    taslak = ms.drafts_root(tmp_path) / YAYIN_TASLAK / "taslak.json"
    kayit = json.loads(taslak.read_text(encoding="utf-8"))
    kayit["sure_dk"] = 20
    kayit["kazanim_ayrintilari"] = [
        {"kod": "FB.5.4.1.1", "metin": "Maddenin hâllerini açıklar.", "beceri": "KB2.7 Karşılaştırma Becerisi"},
        {"kod": "XX.9.9.9", "metin": "Kataloğun kazanımlarında olmayan kod yazılmaz."}]
    taslak.write_text(json.dumps(kayit), encoding="utf-8")
    sign_in(client, FULL)
    body = client.get("/api/modules/fen5-su/v2/aciklama").get_json()
    assert body["sure_dk"] == 20
    assert body["kazanim_ayrintilari"] == [
        {"kod": "FB.5.4.1.1", "metin": "Maddenin hâllerini açıklar.", "beceri": "KB2.7 Karşılaştırma Becerisi"}]


def test_module_explanation_for_an_older_build_has_codes_without_wording(client, tmp_path):
    _published_with_draft(tmp_path)
    sign_in(client, FULL)
    body = client.get("/api/modules/fen5-su/v2/aciklama").get_json()
    assert body["sure_dk"] is None
    assert body["kazanim_ayrintilari"] == [{"kod": "FB.5.4.1.1", "metin": None, "beceri": None}]
