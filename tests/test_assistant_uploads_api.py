"""POST/GET /api/assistant/uploads (spec §2). No network."""
import io
import os
import sys
import zipfile
from datetime import datetime, timezone

import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402

app = dashboard_api.app
FULL = "isikkurtx@gmail.com"
DIGER = "drmahirkurt@gmail.com"
OKUR = "murzogluhulya@gmail.com"


@pytest.fixture
def istemci(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _giris(c, email):
    with c.session_transaction() as s:
        s["user_email"] = email


def _gonder(c, veri: bytes, ad: str):
    return c.post(
        "/api/assistant/uploads",
        data={"dosya": (io.BytesIO(veri), ad)},
        content_type="multipart/form-data",
    )


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 4), (10, 20, 30)).save(buf, "PNG")
    return buf.getvalue()


def _docx() -> bytes:
    xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Payda.</w:t></w:r></w:p></w:body></w:document>"
    ).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", xml)
    return buf.getvalue()


def test_epostasiz_403_ve_dosya_yok(istemci, tmp_path):
    res = _gonder(istemci, b"merhaba", "a.txt")
    assert res.status_code == 403
    assert res.get_json() == {"error": "session_required"}
    assert list(tmp_path.rglob("*")) == []


def test_okur_403(istemci, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    _giris(istemci, OKUR)
    assert _gonder(istemci, b"merhaba", "a.txt").status_code == 403


def test_png_jpeg_olarak_saklanir_ve_sahip_okur(istemci):
    _giris(istemci, FULL)
    res = _gonder(istemci, _png(), "odev.png")
    assert res.status_code == 200
    govde = res.get_json()
    assert govde["tur"] == "gorsel" and govde["ad"] == "odev.png"
    assert "sahip_email" not in govde
    okunan = istemci.get(f"/api/assistant/uploads/{govde['id']}")
    assert okunan.status_code == 200
    assert okunan.mimetype == "image/jpeg"
    assert okunan.data.startswith(b"\xff\xd8\xff")
    assert okunan.headers["Cache-Control"] == "private, no-store"
    assert okunan.headers["X-Content-Type-Options"] == "nosniff"


def test_pdf_oldugu_gibi(istemci):
    _giris(istemci, FULL)
    from tests.test_assistant_uploads import _pdf_sayfalar
    pdf = _pdf_sayfalar(1)
    res = _gonder(istemci, pdf, "kagit.pdf")
    assert res.get_json()["tur"] == "pdf"
    okunan = istemci.get(f"/api/assistant/uploads/{res.get_json()['id']}")
    assert okunan.mimetype == "application/pdf"
    assert okunan.data == pdf


def test_pdf_51_sayfa_413_ve_saklanmaz(istemci, tmp_path):
    _giris(istemci, FULL)
    from tests.test_assistant_uploads import _pdf_sayfalar
    res = _gonder(istemci, _pdf_sayfalar(51), "uzun.pdf")
    assert res.status_code == 413
    assert res.get_json()["error"] == "PDF 50 sayfa sınırını aşıyor."
    assert list(tmp_path.rglob("*")) == []


def test_docx_duz_metin(istemci):
    _giris(istemci, FULL)
    res = _gonder(istemci, _docx(), "not.docx")
    assert res.get_json()["tur"] == "docx"
    okunan = istemci.get(f"/api/assistant/uploads/{res.get_json()['id']}")
    assert okunan.mimetype.startswith("text/plain")
    assert okunan.data.decode("utf-8") == "Payda."


def test_heic_415_ve_buyuk_jpeg_413(istemci):
    _giris(istemci, FULL)
    heic = _gonder(istemci, b"\x00\x00\x00\x18ftypheic" + b"\x00" * 8, "a.heic")
    assert heic.status_code == 415
    assert heic.get_json()["error"] == "Bu dosya biçimi okunamadı."
    buyuk = b"\xff\xd8\xff" + b"\x00" * (12 * 1024 * 1024)
    asan = _gonder(istemci, buyuk, "buyuk.jpg")
    assert asan.status_code == 413
    assert asan.get_json()["error"] == "Görsel 12 MB sınırını aşıyor."


def test_baskasi_ve_yok_ayni_404(istemci):
    _giris(istemci, DIGER)
    kayit = _gonder(istemci, b"merhaba", "a.txt").get_json()
    _giris(istemci, FULL)
    yabanci = istemci.get(f"/api/assistant/uploads/{kayit['id']}")
    yok = istemci.get("/api/assistant/uploads/" + "ab" * 16)
    assert yabanci.status_code == yok.status_code == 404
    assert yabanci.get_json() == yok.get_json() == {"error": "Dosya bulunamadı."}


def test_dosya_parcasi_yoksa_400(istemci):
    _giris(istemci, FULL)
    res = istemci.post("/api/assistant/uploads", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert res.get_json() == {"error": "Dosya yok."}


def test_chat_baskasinin_ekinde_404_ve_cagri_yok(istemci, monkeypatch):
    class _K:
        def __init__(self):
            self.cagrilar = []
        def chat(self, **kw):
            self.cagrilar.append(kw)
            return {"answer": "x", "citations": [], "safety_flags": [], "plan_blocks": [],
                    "intent": "qa", "session_id": "", "mode_suggestion": None, "meta": {}}
    k = _K()
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: k)
    _giris(istemci, FULL)
    kayit = _gonder(istemci, b"merhaba", "a.txt").get_json()
    _giris(istemci, DIGER)
    res = istemci.post("/api/assistant/chat", json={
        "messages": [{"role": "user", "content": "bak", "ekler": [kayit["id"]]}]})
    assert res.status_code == 404
    assert res.get_json() == {"error": "Dosya bulunamadı."}
    assert k.cagrilar == []


def test_chat_beste_400(istemci, monkeypatch):
    class _K:
        cagrilar = []
        def chat(self, **kw):
            self.cagrilar.append(kw)
            return {"answer": "x", "citations": [], "safety_flags": [], "plan_blocks": [],
                    "intent": "qa", "session_id": "", "mode_suggestion": None, "meta": {}}
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _K())
    _giris(istemci, FULL)
    kimlikler = []
    for i in range(5):
        kimlikler.append(_gonder(istemci, f"n{i}".encode(), f"n{i}.txt").get_json()["id"])
    res = istemci.post("/api/assistant/chat", json={
        "messages": [{"role": "user", "content": "bak", "ekler": kimlikler}]})
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bir mesaja en fazla 4 dosya eklenebilir."


def _on_kayit(istemci):
    _giris(istemci, FULL)
    return _gonder(istemci, b"merhaba", "a.txt").get_json()["id"]


def test_istek_on_ek_kabul_on_bir_400(istemci, monkeypatch):
    class _K:
        def __init__(self):
            self.cagrilar = []
        def chat(self, **kw):
            self.cagrilar.append(kw)
            return {"answer": "x", "citations": [], "safety_flags": [], "plan_blocks": [],
                    "intent": "qa", "session_id": "", "mode_suggestion": None, "meta": {}}
    k = _K()
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: k)
    kimlik = _on_kayit(istemci)
    on = [
        {"role": "user", "content": "a", "ekler": [kimlik] * 4},
        {"role": "user", "content": "b", "ekler": [kimlik] * 4},
        {"role": "user", "content": "c", "ekler": [kimlik] * 2},
    ]
    assert istemci.post("/api/assistant/chat", json={"messages": on}).status_code == 200
    assert len(k.cagrilar) == 1
    on_bir = on[:-1] + [{"role": "user", "content": "c", "ekler": [kimlik] * 3}]
    res = istemci.post("/api/assistant/chat", json={"messages": on_bir})
    assert res.status_code == 400
    assert res.get_json()["error"] == "Bir istekte en fazla 10 dosya olabilir."
    assert len(k.cagrilar) == 1


def test_stream_sahibi_ve_baytlari_uretecten_once_tasir(istemci, monkeypatch):
    import inspect
    kimlik = _on_kayit(istemci)
    gercek = dashboard_api._module_person

    def izlenen():
        # assistant_stream's comment: generate() runs after the view returns,
        # where the session is gone. The test client still has a session
        # while it reads the body, so an unguarded _module_person() inside
        # generate() would pass. Treat that frame as no person.
        for f in inspect.stack():
            if f.function == "generate" and f.filename.endswith("dashboard_api.py"):
                return None
        return gercek()

    monkeypatch.setattr(dashboard_api, "_module_person", izlenen)

    class _K:
        def __init__(self):
            self.kw = None
        def chat_events(self, **kw):
            self.kw = kw
            yield {"event": "answer", "payload": {
                "answer": "x", "citations": [], "safety_flags": [], "plan_blocks": [],
                "intent": "qa", "session_id": "", "mode_suggestion": None, "meta": {}}}
        def chat(self, **kw):
            raise AssertionError("stream fell through to chat")
    k = _K()
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: k)
    res = istemci.post("/api/assistant/stream", json={
        "messages": [{"role": "user", "content": "bak", "ekler": [kimlik]}]})
    govde = res.get_data().decode()
    assert res.status_code == 200
    assert "event: answer" in govde
    assert k.kw is not None
    assert k.kw["sahip_email"] == FULL
    assert k.kw["messages"][0]["ek_govde"][0]["veri"] == b"merhaba"
