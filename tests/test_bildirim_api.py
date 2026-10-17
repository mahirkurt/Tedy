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
    assert r.get_json() == {"gonderilen": 1, "basarisiz": 0, "olu": 0, "cihaz": 1}
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
    monkeypatch.setattr(wp.AbonelikDeposu, "ekle", lambda self, e, a, **kw: sira.append(("ekle", 0)) or gercek_ekle(self, e, a, **kw))
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
    assert c.post("/api/bildirim/deneme").get_json() == {"gonderilen": 1, "basarisiz": 0, "olu": 0, "cihaz": 1}


# --- temizlik B: depo hatası, ortak tablet, deneme yanıtı ---------------------------------

IKINCI = {**GOVDE, "endpoint": "https://web.push.apple.com/IKI"}


def test_b2_depo_yedeklenemezse_503_ve_depo_ezilmez(ortam, monkeypatch):
    c, kok, *_ = ortam
    (kok / "output").mkdir()
    (kok / wp.ABONELIKLER).write_text("{bozuk", encoding="utf-8")
    monkeypatch.setattr(wp.os, "replace", lambda *a, **k: (_ for _ in ()).throw(PermissionError("ro")))
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 503
    assert c.delete("/api/bildirim/abonelik", json={"endpoint": GOVDE["endpoint"]}).status_code == 503
    assert (kok / wp.ABONELIKLER).read_text(encoding="utf-8") == "{bozuk"


def test_b6_sessiz_yenileme_baskasinin_cihazini_tasimaz(ortam, monkeypatch):
    c, kok, tohum, _ = ortam
    monkeypatch.setitem(api.USER_ROLES, "baska@x", api.ROLE_FULL)
    depo = wp.AbonelikDeposu(kok / wp.ABONELIKLER)
    depo.ekle("baska@x", wp.abonelik_dogrula(GOVDE))
    once = (kok / wp.ABONELIKLER).read_bytes()
    _giris(c, TAM)
    r = c.post("/api/bildirim/abonelik", json={**GOVDE, "yenile": True})
    assert r.status_code == 409 and r.get_json() == {"sahip_baska": True}
    assert (kok / wp.ABONELIKLER).read_bytes() == once            # store untouched
    assert tohum == []                                             # nothing added: nothing seeded


def test_b6_acikca_acmak_son_aboneye_gecirir(ortam):
    c, kok, tohum, _ = ortam
    depo = wp.AbonelikDeposu(kok / wp.ABONELIKLER)
    depo.ekle("baska@x", wp.abonelik_dogrula(GOVDE))
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json=GOVDE).status_code == 201     # "Bu cihazda aç"
    assert depo.kisinin("baska@x") == [] and len(depo.kisinin(TAM)) == 1
    assert tohum == [TAM]


def test_b6_sessiz_yenileme_kendi_ya_da_sahipsiz_cihazda_calisir(ortam):
    c, kok, tohum, _ = ortam
    depo = wp.AbonelikDeposu(kok / wp.ABONELIKLER)
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json={**GOVDE, "yenile": True}).status_code == 201
    assert c.post("/api/bildirim/abonelik", json={**GOVDE, "yenile": True}).status_code == 201
    assert len(depo.kisinin(TAM)) == 1 and tohum == [TAM]


def test_b6_yaris_kilit_altinda_da_reddedilir(tmp_path):
    depo = wp.AbonelikDeposu(tmp_path / "a.json")
    depo.ekle("baska@x", wp.abonelik_dogrula(GOVDE))
    with pytest.raises(wp.SahipBaska):
        depo.ekle(TAM, wp.abonelik_dogrula(GOVDE), yenile=True)
    assert len(depo.kisinin("baska@x")) == 1 and depo.kisinin(TAM) == []


def _iki_cihaz(c, kok):
    _giris(c, TAM)
    c.post("/api/bildirim/abonelik", json=GOVDE)
    c.post("/api/bildirim/abonelik", json=IKINCI)


def test_b7_deneme_sayimlari_gecici_hata_ve_olu(ortam, monkeypatch):
    c, kok, *_ = ortam
    _iki_cihaz(c, kok)
    sonuc = {GOVDE["endpoint"]: wp.GonderimSonucu("hata", 503, "geçici"),
             IKINCI["endpoint"]: wp.GonderimSonucu("olu", 410, "gone")}
    monkeypatch.setattr(wp, "gonder", lambda abonelik, yuk, vapid, webpush_fn=None: sonuc[abonelik["endpoint"]])
    r = c.post("/api/bildirim/deneme")
    assert r.status_code == 200
    assert r.get_json() == {"gonderilen": 0, "basarisiz": 1, "olu": 1, "cihaz": 2}
    kalan = [d["abonelik"]["endpoint"] for d in wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(TAM)]
    assert kalan == [GOVDE["endpoint"]]                            # the dead one is gone, the 5xx one stays


def test_b7_deneme_istisna_basarisiz_sayilir(ortam, monkeypatch):
    c, kok, *_ = ortam
    _iki_cihaz(c, kok)

    def gonder(abonelik, yuk, vapid, webpush_fn=None):
        if abonelik["endpoint"] == IKINCI["endpoint"]:
            raise RuntimeError("beklenmedik")
        return wp.GonderimSonucu("ok", 201, "")
    monkeypatch.setattr(wp, "gonder", gonder)
    assert c.post("/api/bildirim/deneme").get_json() == {"gonderilen": 1, "basarisiz": 1, "olu": 0, "cihaz": 2}


def test_b7_deneme_cihazlara_paralel_gider(ortam, monkeypatch):
    import threading
    c, kok, *_ = ortam
    _iki_cihaz(c, kok)
    engel = threading.Barrier(2, timeout=3)

    def gonder(abonelik, yuk, vapid, webpush_fn=None):
        engel.wait()                   # sequential sending would break the barrier
        return wp.GonderimSonucu("ok", 201, "")
    monkeypatch.setattr(wp, "gonder", gonder)
    assert c.post("/api/bildirim/deneme").get_json() == {"gonderilen": 2, "basarisiz": 0, "olu": 0, "cihaz": 2}


def test_b7_deneme_toplam_sureyi_asmaz(ortam, monkeypatch):
    import threading
    import time as _time
    c, kok, *_ = ortam
    _iki_cihaz(c, kok)
    serbest = threading.Event()
    monkeypatch.setattr(api, "_DENEME_TOPLAM_SN", 0.3)

    def gonder(abonelik, yuk, vapid, webpush_fn=None):
        if abonelik["endpoint"] == IKINCI["endpoint"]:
            serbest.wait(5)                # a push service that hangs
        return wp.GonderimSonucu("ok", 201, "")
    monkeypatch.setattr(wp, "gonder", gonder)
    bas = _time.monotonic()
    try:
        r = c.post("/api/bildirim/deneme")
        sure = _time.monotonic() - bas
    finally:
        serbest.set()
    assert r.get_json() == {"gonderilen": 1, "basarisiz": 1, "olu": 0, "cihaz": 2}
    assert sure < 2


def test_b7_toplam_sure_gunicorn_zaman_asimindan_kisa():
    import re as _re
    from pathlib import Path as _P
    birim = (_P(__file__).resolve().parents[1] / "ted-dashboard.service").read_text(encoding="utf-8")
    zaman_asimi = int(_re.search(r"--timeout (\d+)", birim).group(1))
    assert api._DENEME_TOPLAM_SN <= 15 < zaman_asimi


def test_b5_deneme_gecersiz_kayitli_ucu_gondermez_siler(ortam):
    import json as _json
    c, kok, _, gonderilen = ortam
    (kok / "output").mkdir()
    kotu = {"abonelik": {"endpoint": "https://evil.example/x", "keys": GOVDE["keys"]}, "cihaz": "?"}
    iyi = {"abonelik": {"endpoint": GOVDE["endpoint"], "keys": GOVDE["keys"]}, "cihaz": "Android"}
    (kok / wp.ABONELIKLER).write_text(_json.dumps({"kisiler": {TAM: [kotu, iyi]}}), encoding="utf-8")
    _giris(c, TAM)
    assert c.post("/api/bildirim/deneme").get_json() == {"gonderilen": 1, "basarisiz": 0, "olu": 1, "cihaz": 2}
    assert [e for e, _ in gonderilen] == [GOVDE["endpoint"]]
    assert [d["abonelik"]["endpoint"] for d in wp.AbonelikDeposu(kok / wp.ABONELIKLER).kisinin(TAM)] == [
        GOVDE["endpoint"]]


# --- temizlik B düzeltme 1 -------------------------------------------------------------------

def test_d1_rolden_cikmis_sahip_sessiz_yenilemeyi_engellemez(ortam, monkeypatch):
    c, kok, tohum, _ = ortam
    monkeypatch.delitem(api.USER_ROLES, "eski@x", raising=False)
    depo = wp.AbonelikDeposu(kok / wp.ABONELIKLER)
    depo.ekle("eski@x", wp.abonelik_dogrula(GOVDE))
    _giris(c, TAM)
    assert c.post("/api/bildirim/abonelik", json={**GOVDE, "yenile": True}).status_code == 201
    assert depo.kisinin("eski@x") == [] and len(depo.kisinin(TAM)) == 1


def test_d1_deneme_tek_sinirli_havuzu_kullanir(ortam, monkeypatch):
    import threading
    import time as _time
    c, kok, *_ = ortam
    _giris(c, TAM)
    for i in range(wp.CIHAZ_SINIRI):
        c.post("/api/bildirim/abonelik", json={**GOVDE, "endpoint": f"https://web.push.apple.com/{i}"})
    kilit, simdi, en_cok, isimler = threading.Lock(), [0], [0], set()

    def gonder(abonelik, yuk, vapid, webpush_fn=None):
        with kilit:
            simdi[0] += 1
            en_cok[0] = max(en_cok[0], simdi[0])
            isimler.add(threading.current_thread().name)
        _time.sleep(0.05)
        with kilit:
            simdi[0] -= 1
        return wp.GonderimSonucu("ok", 201, "")
    monkeypatch.setattr(wp, "gonder", gonder)
    havuz = api._DENEME_HAVUZU
    for _ in range(2):
        assert c.post("/api/bildirim/deneme").get_json()["gonderilen"] == wp.CIHAZ_SINIRI
    assert api._DENEME_HAVUZU is havuz
    assert 1 < en_cok[0] <= api._DENEME_ESZAMANLI == 8
    assert len(isimler) <= 8 and all(n.startswith("bildirim-deneme") for n in isimler)
