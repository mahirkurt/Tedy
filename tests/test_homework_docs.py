"""Homework documents are stored per row and retrieved only for that row.

Vectors are computed by an injected embedder here. Production calls
mbp-node; these tests must not.
"""
import os
import sys
from io import BytesIO

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402
import src.homework_docs as homework_docs  # noqa: E402
from src.assistant_tools import ODEV_BELGE, build_registry, odev_listesi_metni  # noqa: E402
from src.homework_docs import EmbedHatasi  # noqa: E402

app = dashboard_api.app


def _embed(texts):
    """'kesir' and anything else land on opposite axes, so cosine is 0 or 1."""
    out = []
    for text in texts:
        kesir = 1.0 if "kesir" in text.casefold() else 0.0
        out.append([kesir, 1.0 - kesir])
    return out


@pytest.fixture
def kok(tmp_path):
    return tmp_path / "homework_docs"


def test_belge_yalniz_kendi_odevinde_bulunur(kok):
    doc = homework_docs.ekle(kok, "matematik|kesirler|", "not.txt",
                             "Kesirlerde payda altta yazılır.".encode(), embed=_embed)
    homework_docs.ekle(kok, "turkce|okuma|", "diger.txt",
                       "Harita üzerinde yönler.".encode(), embed=_embed)
    assert doc["ready"] is True
    assert "embedding" not in doc
    bulunan = homework_docs.ara(kok, "matematik|kesirler|", "kesir paydası nedir", embed=_embed)
    assert "payda altta" in bulunan
    assert "Harita" not in bulunan
    assert "eklenmiş belge yok" in homework_docs.ara(kok, "fen|yok|", "kesir", embed=_embed)


def test_vektor_yazilamazsa_belge_durur_ve_uydurulmaz(kok):
    def patlak(_texts):
        raise EmbedHatasi("bağlantı")

    doc = homework_docs.ekle(kok, "matematik|kesirler|", "not.txt", b"Kesirler.", embed=patlak)
    assert doc["ready"] is False
    assert "vektör" in doc["error"]
    metin = homework_docs.ara(kok, "matematik|kesirler|", "kesir", embed=_embed)
    assert "vektörü yok" in metin
    assert "Kesirler" not in metin


def test_yanlis_tur_reddedilir(kok):
    with pytest.raises(homework_docs.BelgeReddedildi):
        homework_docs.ekle(kok, "matematik|kesirler|", "not.png", b"abc", embed=_embed)


def test_arac_secili_odevin_anahtarini_kullanir():
    gorulen = []

    def ara(anahtar, sorgu):
        gorulen.append((anahtar, sorgu))
        return "payda altta yazılır"

    reg = build_registry(lambda q, k: [], odev_belge_ara=ara)
    assert ODEV_BELGE in [d["name"] for d in reg.declarations()]
    assert ODEV_BELGE not in [
        d["name"] for d in build_registry(lambda q, k: []).declarations()
    ]
    bos = reg.dispatch(ODEV_BELGE, {"sorgu": "payda"})
    assert not bos.ok and gorulen == []
    oldu = reg.dispatch(ODEV_BELGE, {"sorgu": "payda"}, odev_anahtari="matematik|kesirler|")
    assert oldu.ok and "payda altta" in oldu.text
    assert gorulen == [("matematik|kesirler|", "payda")]
    assert oldu.citations[0]["label"] == "Ödev belgesi"


def test_liste_belge_adini_soyler():
    from datetime import datetime
    row = {
        "Ders Adı": "Matematik", "Ödev Başlığı": "Kesirler",
        "Ödev Son Teslim Tarihi": "02.10.2026 23:59",
        "documents": [{"id": "ab", "name": "not.txt", "ready": True, "error": ""}],
    }
    metin = odev_listesi_metni([row], datetime(2026, 9, 30, 12, 0))
    assert "belge: not.txt" in metin


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_yukleme_odeve_eklenir_ve_vektor_disari_cikmaz(client, tmp_path, monkeypatch):
    monkeypatch.setattr(dashboard_api, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(homework_docs, "ollama_embed", _embed)
    row = {
        "Ders Adı": "Matematik",
        "Ödev Başlığı": "Kesirler",
        "Ödev Son Teslim Tarihi": "02.10.2026 23:59",
        "Ödev Durumu": "Değerlendirilmemiş",
        "detail": {"description": "payda", "attachments": []},
    }
    monkeypatch.setattr(
        dashboard_api, "_scraped",
        lambda: {"odevlerim": {"homework": {"rows": [row]}}},
    )
    monkeypatch.setattr(dashboard_api, "_load_photo_homework_rows", lambda: [])
    key = dashboard_api._homework_row_key(row)
    resp = client.post(
        "/api/homework/documents",
        data={"homework_key": key, "file": (BytesIO("Kesirlerde payda.".encode()), "not.txt")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["document"]["ready"] is True
    assert "embedding" not in body["document"]
    listed = client.get("/api/homework").get_json()["homework"]
    assert listed[0]["documents"][0]["name"] == "not.txt"
    assert "embedding" not in listed[0]["documents"][0]

    indir = client.get(f"/api/homework/documents/{body['document']['id']}")
    assert indir.status_code == 200
    assert b"payda" in indir.data

    yabanci = client.post(
        "/api/homework/documents",
        data={"homework_key": "yok|yok|", "file": (BytesIO(b"x"), "a.txt")},
        content_type="multipart/form-data",
    )
    assert yabanci.status_code == 404

    sil = client.delete(f"/api/homework/documents/{body['document']['id']}")
    assert sil.status_code == 200
    assert client.get(f"/api/homework/documents/{body['document']['id']}").status_code == 404
