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
    pdf = b"%PDF-1.4\n%%EOF"
    res = _gonder(istemci, pdf, "kagit.pdf")
    assert res.get_json()["tur"] == "pdf"
    okunan = istemci.get(f"/api/assistant/uploads/{res.get_json()['id']}")
    assert okunan.mimetype == "application/pdf"
    assert okunan.data == pdf


def test_pdf_51_sayfa_413_ve_saklanmaz(istemci, tmp_path):
    _giris(istemci, FULL)
    parca = [b"%PDF-1.4\n"]
    for i in range(51):
        parca.append(f"{i} 0 obj\n<< /Type /Page >>\nendobj\n".encode())
    parca.append(b"%%EOF\n")
    res = _gonder(istemci, b"".join(parca), "uzun.pdf")
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
    _giris(istemci, FULL)
    kayit = _gonder(istemci, b"merhaba", "a.txt").get_json()
    _giris(istemci, DIGER)
    yabanci = istemci.get(f"/api/assistant/uploads/{kayit['id']}")
    yok = istemci.get("/api/assistant/uploads/" + "ab" * 16)
    assert yabanci.status_code == yok.status_code == 404
    assert yabanci.get_json() == yok.get_json() == {"error": "Dosya bulunamadı."}


def test_dosya_parcasi_yoksa_400(istemci):
    _giris(istemci, FULL)
    res = istemci.post("/api/assistant/uploads", data={}, content_type="multipart/form-data")
    assert res.status_code == 400
    assert res.get_json() == {"error": "Dosya yok."}
