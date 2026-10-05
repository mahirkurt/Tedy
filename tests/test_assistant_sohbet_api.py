"""Session-owned conversations and family read access; no model network calls."""
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"

from src import dashboard_api
from src.assistant_sohbet import SohbetDeposu

ISIK = "student@example.test"
AILE = "parent@example.test"
DIGER = "other-parent@example.test"
OKUR = "reader@example.test"
SIMDI = datetime(2026, 10, 3, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def istemci(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    monkeypatch.setattr(dashboard_api, "USER_ROLES", {
        ISIK: "full", AILE: "full", DIGER: "full", OKUR: "reader",
    })
    monkeypatch.setattr(dashboard_api, "OGRENCI_EMAILS", {ISIK}, raising=False)
    monkeypatch.setattr(dashboard_api, "okur_turu", lambda e:
        "ogrenci" if e == ISIK else "aile" if e in {AILE, DIGER} else "bilinmiyor")
    monkeypatch.setattr(dashboard_api, "_asistan_simdi", lambda: SIMDI, raising=False)
    dashboard_api.app.config["TESTING"] = True
    with dashboard_api.app.test_client() as c:
        yield c


def _giris(c, email):
    with c.session_transaction() as ses:
        ses["user_email"] = email


def _sohbet_deposu():
    return SohbetDeposu(Path(dashboard_api.OUTPUT_DIR) / "assistant_sohbetler.sqlite")


def test_sahip_yazar_aile_okur_yazamaz(istemci):
    _giris(istemci, ISIK)
    yarat = istemci.post("/api/assistant/sohbetler", json={"ogretmen": "matematik"})
    assert yarat.status_code == 200
    sid = yarat.get_json()["id"]
    assert "sahip_email" not in yarat.get_json()
    mesaj = istemci.post("/api/assistant/sohbetler/" + sid + "/mesaj",
                         json={"icerik": "Payda eşitle", "ogretmen": "matematik"})
    assert mesaj.status_code == 200
    liste = istemci.get("/api/assistant/sohbetler").get_json()["sohbetler"]
    assert liste[0]["baslik"] == "Payda eşitle"
    _giris(istemci, AILE)
    assert istemci.get("/api/assistant/sohbetler").get_json()["sohbetler"] == []
    aile = istemci.get("/api/assistant/sohbetler?kisi=ogrenci")
    assert aile.status_code == 200
    assert aile.get_json()["sohbetler"][0]["id"] == sid
    oku = istemci.get("/api/assistant/sohbetler/" + sid)
    assert oku.status_code == 200
    assert "sahip_email" not in oku.get_json()["sohbet"]
    yaz = istemci.patch("/api/assistant/sohbetler/" + sid, json={"baslik": "X"})
    assert yaz.status_code == 403
    assert yaz.get_json()["error"] == "Bu sohbet salt okunur."
    assert istemci.delete("/api/assistant/sohbetler/" + sid).status_code == 403


def test_yabanci_ve_yok_ayni_404(istemci):
    _giris(istemci, AILE)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    _giris(istemci, "other-parent@example.test")
    diger = istemci.get("/api/assistant/sohbetler/" + sid)
    _giris(istemci, ISIK)
    yok = istemci.get("/api/assistant/sohbetler/" + "ab" * 16)
    yabanci = istemci.get("/api/assistant/sohbetler/" + sid)
    assert yok.status_code == yabanci.status_code == diger.status_code == 404
    assert yok.get_json() == yabanci.get_json() == diger.get_json() == {"error": "Sohbet bulunamadı."}


def test_okur_403(istemci, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    _giris(istemci, OKUR)
    assert istemci.get("/api/assistant/sohbetler").status_code == 403


def test_bilinmeyen_kisi_400(istemci):
    _giris(istemci, AILE)
    res = istemci.get("/api/assistant/sohbetler?kisi=aile")
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bilinmeyen kişi."


def test_akis_yirmiyi_yukler_yarim_cevabi_yazmaz(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    for i in range(21):
        istemci.post(f"/api/assistant/sohbetler/{sid}/mesaj",
                     json={"icerik": f"eski{i}", "ogretmen": "genel"})
    gorulen = {}

    class _K:
        def chat_events(self, **kw):
            gorulen.update(kw)
            yield {"event": "answer", "payload": {
                "answer": "tamam", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "mode_suggestion": None, "meta": {"ogretmen": "genel"}}}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    res = istemci.post("/api/assistant/stream", json={
        "sohbet_id": sid,
        "messages": [
            {"role": "user", "content": "sahte geçmiş"},
            {"role": "user", "content": "yeni soru"},
        ],
    })
    assert "event: answer" in res.get_data().decode()
    icerikler = [m["content"] for m in gorulen["messages"] if isinstance(m, dict)]
    assert "sahte geçmiş" not in icerikler
    assert icerikler[0] == "eski2"          # 21 eski + yeni = 22; son 20 eski2'den başlar
    assert icerikler[-1] == "yeni soru"
    assert gorulen["pencere"] == 20
    depo = _sohbet_deposu()
    roller = [m["rol"] for m in depo.tum_mesajlar(sid)]
    assert roller[-2:] == ["user", "assistant"]


def test_akis_koparsa_cevap_satiri_yok(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]

    class _K:
        def chat_events(self, **kw):
            raise RuntimeError("koptu")
            yield {}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    istemci.post("/api/assistant/stream", json={
        "sohbet_id": sid, "messages": [{"role": "user", "content": "kaldı"}]})
    roller = [m["rol"] for m in _sohbet_deposu().tum_mesajlar(sid)]
    assert roller == ["user"]


def test_v1_ve_plansiz_depo_acmadi(istemci, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    # /v1 api_key_only. Bypass anahtarsız 401 bırakır; depo dosyası yine yok.
    istemci.post("/v1/chat/completions", json={"messages": [{"role": "user", "content": "x"}]})
    assert not (tmp_path / "assistant_sohbetler.sqlite").exists()


def test_plan_depo_acmadi(istemci, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    gorulen = {}

    class _K:
        def study_plan(self, **kw):
            gorulen.update(kw)
            return {"blocks": []}

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    _giris(istemci, ISIK)
    res = istemci.post("/api/assistant/plan", json={
        "messages": [{"role": "user", "content": "plan"}]})
    assert res.status_code == 200
    assert "sohbet_id" not in gorulen
    assert gorulen.get("hafiza") is not True
    assert not (tmp_path / "assistant_sohbetler.sqlite").exists()


def test_sohbet_id_yoksa_dosya_yok(istemci, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))

    class _K:
        def chat_events(self, **kw):
            yield {"event": "answer", "payload": {
                "answer": "tamam", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "mode_suggestion": None, "meta": {"ogretmen": "genel"}}}
        def chat(self, **kw):
            return {"answer": "tamam", "citations": [], "safety_flags": [],
                    "plan_blocks": [], "intent": "qa", "session_id": "",
                    "mode_suggestion": None, "meta": {"ogretmen": "genel"}}

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    _giris(istemci, ISIK)
    istemci.post("/api/assistant/stream", json={
        "messages": [{"role": "user", "content": "x"}]})
    istemci.post("/api/assistant/chat", json={
        "messages": [{"role": "user", "content": "x"}]})
    assert not (tmp_path / "assistant_sohbetler.sqlite").exists()


def test_eski_ekler_on_tavanina_girer(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    depo = _sohbet_deposu()
    for i in range(9):
        depo.mesaj_ekle(sid, "user", f"eski{i}", "genel", ["ab" * 15 + f"{i:02x}"], SIMDI)
    cagrildi = {"n": 0}

    class _K:
        def chat_events(self, **kw):
            cagrildi["n"] += 1
            yield {"event": "answer", "payload": {
                "answer": "tamam", "citations": [], "safety_flags": [],
                "plan_blocks": [], "intent": "qa", "session_id": "",
                "mode_suggestion": None, "meta": {}}}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    res = istemci.post("/api/assistant/stream", json={
        "sohbet_id": sid,
        "messages": [{"role": "user", "content": "yeni", "ekler": ["cd" * 16, "ef" * 16]}],
    })
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bir istekte en fazla 10 dosya olabilir."
    assert cagrildi["n"] == 0
    assert [m["icerik"] for m in depo.tum_mesajlar(sid)] == [f"eski{i}" for i in range(9)]


def _answer():
    return {"answer": "Tamam [S1]", "citations": [{"kind": "kitap", "label": "Kaynak"}],
            "safety_flags": [], "plan_blocks": [], "intent": "qa", "session_id": "",
            "mode_suggestion": None, "meta": {"private-tool-body": "do not persist"}}


def test_stream_retry_keeps_one_user_and_replays_complete_answer(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    calls = []

    class Runtime:
        def chat_events(self, **kw):
            calls.append("stream")
            raise RuntimeError("upstream failed")
            yield {}
        def chat(self, **kw):
            calls.append("chat")
            return _answer()

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: Runtime())
    payload = {"sohbet_id": sid, "request_id": "ab" * 16,
               "messages": [{"role": "user", "content": "Soru"}]}
    response = istemci.post("/api/assistant/stream", json=payload)
    assert "event: error" in response.get_data(as_text=True)
    response = istemci.post("/api/assistant/chat", json=payload)
    assert response.status_code == 200
    repeated = istemci.post("/api/assistant/chat", json=payload)
    assert repeated.get_json()["answer"] == _answer()["answer"]
    assert repeated.get_json()["citations"] == _answer()["citations"]
    assert calls == ["stream", "chat"]
    rows = _sohbet_deposu().tum_mesajlar(sid)
    assert [r["rol"] for r in rows] == ["user", "assistant"]
    assert all(r["meta_json"] == "{}" for r in rows)
    assert json.loads(rows[-1]["atiflar_json"]) == _answer()["citations"]
    # The same wording, deliberately sent again, is a different request.
    payload["request_id"] = "cd" * 16
    assert istemci.post("/api/assistant/chat", json=payload).status_code == 200
    assert len(_sohbet_deposu().tum_mesajlar(sid)) == 4


def test_family_cannot_send_to_child_chat_or_open_parent_chat(istemci):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    _giris(istemci, AILE)
    for endpoint in ("chat", "stream"):
        res = istemci.post("/api/assistant/" + endpoint, json={
            "sohbet_id": sid, "messages": [{"role": "user", "content": "write"}]})
        assert res.status_code == 403
        assert res.get_json()["error"] == "Bu sohbet salt okunur."
    assert _sohbet_deposu().tum_mesajlar(sid) == []


def test_api_key_cannot_open_storage(istemci, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "API_KEYS", [("synthetic", "tdyK_unit-test")])
    res = istemci.post("/api/assistant/sohbetler", json={},
                       headers={"Authorization": "Bearer tdyK_unit-test"})
    assert res.status_code in (401, 403)
    assert not (tmp_path / "assistant_sohbetler.sqlite").exists()


def test_family_notes_endpoint_and_sensitive_gate(istemci):
    nid = _sohbet_deposu().not_yaz("Paydada zorlanıyor", None, SIMDI)
    _giris(istemci, ISIK)
    assert istemci.get("/api/assistant/notlar").status_code == 403
    assert istemci.patch("/api/assistant/notlar/" + nid, json={"metin": "değişti"}).status_code == 403
    assert istemci.delete("/api/assistant/notlar/" + nid).status_code == 403
    _giris(istemci, AILE)
    assert len(istemci.get("/api/assistant/notlar").get_json()["notlar"]) == 1
    for metin in ("İlaç kullanıyor", "Boşanma", "parent@example.test", "01234567890"):
        res = istemci.patch("/api/assistant/notlar/" + nid, json={"metin": metin})
        assert res.status_code == 400
        assert res.get_json()["error"] == "Bu not yazılmadı."
    assert istemci.patch("/api/assistant/notlar/" + nid, json={"metin": "Örnekle öğreniyor"}).status_code == 200
    assert istemci.delete("/api/assistant/notlar/" + nid).status_code == 200
    assert istemci.delete("/api/assistant/notlar/" + nid).status_code == 404


def test_family_upload_read_is_one_way(istemci):
    _giris(istemci, ISIK)
    child = istemci.post("/api/assistant/uploads", data={"dosya": (io.BytesIO(b"child"), "note.txt")}).get_json()
    _giris(istemci, AILE)
    assert istemci.get("/api/assistant/uploads/" + child["id"]).data == b"child"
    parent = istemci.post("/api/assistant/uploads", data={"dosya": (io.BytesIO(b"parent"), "note.txt")}).get_json()
    _giris(istemci, DIGER)
    assert istemci.get("/api/assistant/uploads/" + child["id"]).status_code == 200
    assert istemci.get("/api/assistant/uploads/" + parent["id"]).status_code == 404
    _giris(istemci, ISIK)
    assert istemci.get("/api/assistant/uploads/" + parent["id"]).status_code == 404


def test_delete_removes_bound_upload_and_chat(istemci, monkeypatch):
    from src.assistant_uploads import EkDeposu
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    upload = istemci.post("/api/assistant/uploads", data={"dosya": (io.BytesIO(b"lesson"), "note.txt")}).get_json()

    class Runtime:
        def chat(self, **kw):
            return _answer()

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: Runtime())
    assert istemci.post("/api/assistant/chat", json={"sohbet_id": sid,
        "messages": [{"role": "user", "content": "Oku", "ekler": [upload["id"]]}]}).status_code == 200
    uploads = EkDeposu(dashboard_api.OUTPUT_DIR)
    assert uploads.oku(ISIK, upload["id"])[0]["bagli_sohbet"] == sid
    assert istemci.delete("/api/assistant/sohbetler/" + sid).status_code == 200
    assert uploads.oku(ISIK, upload["id"]) is None
    assert istemci.get("/api/assistant/sohbetler/" + sid).status_code == 404


def test_ten_historical_uploads_are_captured_before_stream(istemci, monkeypatch):
    import inspect
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    upload = istemci.post("/api/assistant/uploads", data={"dosya": (io.BytesIO(b"lesson"), "note.txt")}).get_json()
    depo = _sohbet_deposu()
    for i in range(8):
        depo.mesaj_ekle(sid, "user", f"old{i}", "genel", [upload], SIMDI)
    original = dashboard_api._module_person

    def person():
        if any(f.function == "generate" and f.filename.endswith("dashboard_api.py") for f in inspect.stack()):
            raise AssertionError("session accessed inside stream")
        return original()

    seen = {}
    class Runtime:
        def chat_events(self, **kw):
            seen.update(kw)
            yield {"event": "answer", "payload": _answer()}

    monkeypatch.setattr(dashboard_api, "_module_person", person)
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: Runtime())
    res = istemci.post("/api/assistant/stream", json={"sohbet_id": sid,
        "messages": [{"role": "user", "content": "new", "ekler": [upload["id"]] * 2}]})
    assert "event: answer" in res.get_data(as_text=True)
    assert sum(len(m.get("ek_govde", [])) for m in seen["messages"]) == 10
    assert seen["pencere"] == 20
    assert seen["sohbet_id"] == sid


def test_storage_failure_is_redacted(istemci, monkeypatch):
    _giris(istemci, ISIK)
    def broken():
        raise sqlite3.OperationalError("private-path-and-person")
    monkeypatch.setattr(dashboard_api, "_sohbet_deposu", broken)
    for method, path, body in [("get", "/api/assistant/sohbetler", None),
                               ("post", "/api/assistant/chat", {"sohbet_id": "ab" * 16, "messages": []})]:
        res = getattr(istemci, method)(path, json=body)
        assert res.status_code == 500
        assert res.get_json() == {"error": "Sohbet kaydedilemedi."}


def test_completed_retry_restores_only_visible_cards(istemci, monkeypatch):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    photo = {"ek_id": "ab" * 16, "photo_hash": "ab" * 8, "adaylar": [
        {"ders": "Matematik", "baslik": "Kesirler", "teslim": "", "aciklama": "Sayfa 3", "eksik": ["teslim"]}]}
    clarify = {"soru": "Hangi konu?", "secenekler": ["Kesir", "Oran"]}
    class Runtime:
        def chat(self, **kwargs):
            assert kwargs["force_deep"] is True
            return {**_answer(), "odev_onerisi": {**photo, "private_trace": "gizli"},
                    "netlestirme": {**clarify, "private_trace": "gizli"}, "meta": {"private_trace": "gizli"}}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: Runtime())
    body = {"sohbet_id": sid, "request_id": "ab" * 16, "force_deep": True,
            "messages": [{"role": "user", "content": "Ödeve ekle"}]}
    assert istemci.post("/api/assistant/chat", json=body).status_code == 200
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: pytest.fail("replay must not call model"))
    replay = istemci.post("/api/assistant/chat", json=body).get_json()
    assert replay["odev_onerisi"] == photo
    assert replay["netlestirme"] == clarify
    assert "gizli" not in str(replay)
    rows = _sohbet_deposu().tum_mesajlar(sid)
    assert len(rows) == 2 and all(r["meta_json"] == "{}" for r in rows)
    _giris(istemci, AILE)
    history = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()
    assert history["read_only"] is True
    assert history["mesajlar"][1]["odev_onerisi"] == photo
    assert history["mesajlar"][1]["netlestirme"] == clarify
    assert "gizli" not in str(history)
    assert istemci.post("/api/assistant/chat", json=body).status_code == 403


# -- 2026-10-05: denetim kararı mesajın yanında saklanır, geçmiş API'sine çıkmaz ----------------------

@pytest.mark.parametrize("denetim,beklenen", [
    ({"durum": "hata", "neden": "denetim_dili", "sorun": ["kaynak"], "model": "claude-haiku-4-5",
      "gizli": "x"}, {"durum": "hata", "neden": "denetim_dili", "sorun": ["kaynak"]}),
    ({"durum": "duzeltildi", "neden": None, "sorun": ["hitap"], "model": "claude-haiku-4-5"},
     {"durum": "duzeltildi", "neden": None, "sorun": ["hitap"]}),
    ({"durum": "gecti", "neden": None, "sorun": [], "model": "claude-haiku-4-5"}, None),
    ({"durum": "atlandi", "neden": "genel_kisa", "sorun": [], "model": None}, None),
])
def test_denetim_karari_saklanir_ve_gecmise_cikmaz(istemci, monkeypatch, denetim, beklenen):
    _giris(istemci, ISIK)
    sid = istemci.post("/api/assistant/sohbetler", json={}).get_json()["id"]
    cevap = _answer()
    cevap["meta"] = {**cevap["meta"], "denetim": denetim}

    class Runtime:
        def chat(self, **kw):
            return cevap

    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: Runtime())
    body = {"sohbet_id": sid, "request_id": "ef" * 16, "messages": [{"role": "user", "content": "Soru"}]}
    assert istemci.post("/api/assistant/chat", json=body).status_code == 200
    satir = _sohbet_deposu().tum_mesajlar(sid)[-1]
    assert json.loads(satir["meta_json"]) == ({"denetim": beklenen} if beklenen else {})
    assert "private-tool-body" not in satir["meta_json"]
    gecmis = istemci.get(f"/api/assistant/sohbetler/{sid}").get_json()["mesajlar"]
    assert all("meta_json" not in m for m in gecmis)
