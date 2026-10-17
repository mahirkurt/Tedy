"""Notification endpoints: session + full role only, own devices only,
validated bodies, and a new person's devices seeded so they get no backlog."""
import base64
import os

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
import src.dashboard_api as api  # noqa: E402
import src.web_push as wp  # noqa: E402

P256 = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).rstrip(b"=").decode()
AUTH = base64.urlsafe_b64encode(b"b" * 16).rstrip(b"=").decode()
GOVDE = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": P256, "auth": AUTH},
         "cihaz": "Android"}
TAM = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_FULL)
OKUR = next((e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER), None)


@pytest.fixture
def ortam(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(api, "PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("TEDY_VAPID_PUBLIC", "PUB")
    monkeypatch.setenv("TEDY_VAPID_PRIVATE", "PRIV")
    tohum = []
    import src.sinav_uyari as su
    monkeypatch.setattr(su, "kisiyi_tohumla", lambda kok, email, simdi: tohum.append(email) or 0)
    gonderilen = []
    monkeypatch.setattr(wp, "gonder", lambda abonelik, yuk, vapid, webpush_fn=None:
                        gonderilen.append((abonelik["endpoint"], yuk)) or wp.GonderimSonucu("ok", 201, ""))
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c, tmp_path, tohum, gonderilen


def _giris(c, email):
    with c.session_transaction() as s:
        s["user_email"] = email


def test_anahtar_oturumsuz_401(ortam):
    c, *_ = ortam
    assert c.get("/api/bildirim/anahtar").status_code == 401


def test_anahtar_tam_rol(ortam, monkeypatch):
    c, *_ = ortam
    _giris(c, TAM)
    monkeypatch.setenv("TEDY_SINAV_UYARI", "1")
    assert c.get("/api/bildirim/anahtar").get_json() == {"anahtar": "PUB", "acik": True}


@pytest.mark.skipif(OKUR is None, reason="kadroda okuyucu yok")
def test_okuyucu_403(ortam):
    c, *_ = ortam
    _giris(c, OKUR)
    assert c.get("/api/bildirim/anahtar").status_code == 403
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 403


def test_api_anahtari_ile_reddedilir(ortam, monkeypatch):
    c, *_ = ortam
    monkeypatch.setattr(api, "_validate_api_key", lambda k: "etiket")
    r = c.post("/api/bildirim/abonelik", json=GOVDE, headers={"Authorization": "Bearer x"})
    assert r.status_code == 403


def test_ilk_abonelik_kisiyi_tohumlar(ortam):
    c, kok, tohum, _ = ortam
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 201
    assert tohum == [TAM]
    assert c.post("/api/bildirim/abonelik", json={**GOVDE, "endpoint": GOVDE["endpoint"] + "2"}).status_code == 201
    assert tohum == [TAM]                       # second device of the same person: no reseed
    assert len(wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(TAM)) == 2


def test_gecersiz_govde_400(ortam):
    c, *_ = ortam
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json={**GOVDE, "endpoint": "https://evil.example/x"}).status_code == 400


def test_baskasinin_aboneligi_silinemez(ortam):
    c, kok, *_ = ortam
    wp.AbonelikDeposu(kok / wp.ABONELIKLER).ekle("baska@x", wp.abonelik_dogrula(GOVDE))
    _giris(c, TAM)
    assert c.delete("/api/bildirim/abonelik", json={"endpoint": GOVDE["endpoint"]}).status_code == 404
    assert wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin("baska@x")


def test_kendi_aboneligini_siler(ortam):
    c, kok, *_ = ortam
    _giris(c, TAM)
    c.post("/api/bildirim/abonelik", json=GOVDE)
    assert c.delete("/api/bildirim/abonelik", json={"endpoint": GOVDE["endpoint"]}).status_code == 200
    assert wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(TAM) == []


def test_deneme_yalniz_kendi_cihazlarina(ortam):
    c, kok, _, gonderilen = ortam
    wp.AbonelikDeposu(kok / wp.ABONELIKLER).ekle("baska@x", wp.abonelik_dogrula(
        {**GOVDE, "endpoint": "https://web.push.apple.com/Q"}))
    _giris(c, TAM)
    assert c.post("/api/bildirim/deneme").status_code == 404           # no device yet
    c.post("/api/bildirim/abonelik", json=GOVDE)
    r = c.post("/api/bildirim/deneme")
    assert r.get_json() == {"gonderilen": 1}
    assert [e for e, _ in gonderilen] == [GOVDE["endpoint"]]
    assert gonderilen[0][1]["url"] == "/sinavlar#uyarilar"


def test_deneme_vapid_yoksa_503(ortam, monkeypatch):
    c, *_ = ortam
    monkeypatch.delenv("TEDY_VAPID_PUBLIC")
    _giris(c, TAM)
    c.post("/api/bildirim/abonelik", json=GOVDE)
    assert c.post("/api/bildirim/deneme").status_code == 503


def test_okuyucu_uc_listesinde_degil():
    assert not any("bildirim" in e for e in api.READER_ENDPOINTS)


def test_bypass_kimligi_current_user_email_ile_ayni(monkeypatch):
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", True)
    with api.app.test_request_context("/api/bildirim/anahtar"):
        assert api._bildirim_kisisi() == api._current_user_email() == "test@tedy.online"


def test_tohumlama_eklemeden_once(ortam, monkeypatch):
    """Seed first, then add: if the device were added first and seeding then failed, the next try
    would no longer be a first device and the whole backlog would flood in (final review, Minor 1).
    Two workers may both seed a first device: harmless, the ledger skips what is already there."""
    c, kok, _, _ = ortam
    _giris(c, TAM)
    sira = []
    import src.sinav_uyari as su
    monkeypatch.setattr(su, "kisiyi_tohumla", lambda k, email, simdi: sira.append(
        ("tohum", len(wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(email)))) or 0)
    gercek_ekle = wp.AbonelikDeposu.ekle
    monkeypatch.setattr(wp.AbonelikDeposu, "ekle", lambda self, e, a: sira.append(("ekle", 0)) or gercek_ekle(self, e, a))
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 201
    assert sira == [("tohum", 0), ("ekle", 0)]


def test_tohumlama_hatasinda_cihaz_eklenmez_sonraki_deneme_ilk_sayilir(ortam, monkeypatch):
    c, kok, tohum, _ = ortam
    _giris(c, TAM)
    import src.sinav_uyari as su
    gercek = su.kisiyi_tohumla

    def bozuk(k, email, simdi):
        raise OSError("defter yazılamadı")
    monkeypatch.setattr(su, "kisiyi_tohumla", bozuk)
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 503
    assert wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(TAM) == []
    monkeypatch.setattr(su, "kisiyi_tohumla", gercek)
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 201
    assert tohum == [TAM]


def test_deneme_bozuk_kayitla_patlamaz(ortam):
    c, kok, _, gonderilen = ortam
    (kok / "output").mkdir()
    (kok / wp.ABONELIKLER).write_text('{"kisiler": {"%s": [{"abonelik": "x"}, {"abonelik": %s}]}}' % (
        TAM, __import__("json").dumps(wp.abonelik_dogrula(GOVDE) and {"endpoint": GOVDE["endpoint"], "keys": GOVDE["keys"]})),
        encoding="utf-8")
    _giris(c, TAM)
    assert c.post("/api/bildirim/deneme").get_json() == {"gonderilen": 1}
