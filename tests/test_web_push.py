"""src/web_push: VAPID keys, subscription validation and store, sending.
No network: sending goes through a fake webpush callable."""
import base64
import json
from types import SimpleNamespace

import pytest

from src.web_push import (AbonelikDeposu, GonderimSonucu, VapidAyarlari, abonelik_dogrula, anahtar_uret, gonder,
                          vapid_ayarlari)

P256 = base64.urlsafe_b64encode(b"\x04" + b"a" * 64).rstrip(b"=").decode()
AUTH = base64.urlsafe_b64encode(b"b" * 16).rstrip(b"=").decode()


def abonelik(endpoint="https://fcm.googleapis.com/fcm/send/abc", cihaz="Android"):
    return {"endpoint": endpoint, "keys": {"p256dh": P256, "auth": AUTH}, "cihaz": cihaz}


def test_anahtar_uret_bicim():
    acik, ozel = anahtar_uret()
    assert len(base64.urlsafe_b64decode(acik + "==")) == 65
    assert len(base64.urlsafe_b64decode(ozel + "==")) == 32
    assert anahtar_uret() != (acik, ozel)


def test_vapid_anahtari_py_vapid_ile_okunur():
    py_vapid = pytest.importorskip("py_vapid")
    from cryptography.hazmat.primitives import serialization
    acik, ozel = anahtar_uret()
    v = py_vapid.Vapid01.from_string(ozel)
    nokta = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    assert base64.urlsafe_b64encode(nokta).rstrip(b"=").decode() == acik


def test_vapid_ayarlari_ortamdan(monkeypatch):
    monkeypatch.delenv("TEDY_VAPID_PUBLIC", raising=False)
    assert vapid_ayarlari() is None
    monkeypatch.setenv("TEDY_VAPID_PUBLIC", "pub")
    monkeypatch.setenv("TEDY_VAPID_PRIVATE", "priv")
    monkeypatch.delenv("TEDY_VAPID_SUBJECT", raising=False)
    assert vapid_ayarlari() == VapidAyarlari("pub", "priv", "https://tedy.online")


@pytest.mark.parametrize("endpoint", [
    "https://fcm.googleapis.com/fcm/send/x", "https://updates.push.services.mozilla.com/wpush/v2/x",
    "https://web.push.apple.com/QGx", "https://wns2-par02p.notify.windows.com/w/?token=x",
])
def test_dogrula_bilinen_servisler(endpoint):
    assert abonelik_dogrula(abonelik(endpoint))["endpoint"] == endpoint


@pytest.mark.parametrize("govde", [
    None, "x", {}, abonelik("http://fcm.googleapis.com/x"), abonelik("https://evil.example.com/x"),
    abonelik("https://fcm.googleapis.com.evil.com/x"),
    {**abonelik(), "keys": {"p256dh": "kısa", "auth": AUTH}},
    {**abonelik(), "keys": {"p256dh": P256}},
    {**abonelik(), "endpoint": "https://fcm.googleapis.com/" + "x" * 2100},
])
def test_dogrula_reddeder(govde):
    assert abonelik_dogrula(govde) is None


def test_dogrula_cihaz_adi_kirpilir():
    assert abonelik_dogrula(abonelik(cihaz="x" * 200))["cihaz"] == "x" * 80
    assert abonelik_dogrula({**abonelik(), "cihaz": None})["cihaz"] == "Tarayıcı"


def test_depo_ekle_sil_kisinin(tmp_path):
    d = AbonelikDeposu(tmp_path / "a.json")
    assert d.ekle("isik@x", abonelik_dogrula(abonelik())) is True
    assert d.ekle("isik@x", abonelik_dogrula(abonelik(cihaz="Yeni ad"))) is False   # same endpoint: replaced
    assert [c["cihaz"] for c in d.kisinin("isik@x")] == ["Yeni ad"]
    d.ekle("anne@x", abonelik_dogrula(abonelik("https://web.push.apple.com/Q")))
    assert set(d.hepsi()) == {"isik@x", "anne@x"}
    assert d.sil("anne@x", "https://fcm.googleapis.com/fcm/send/abc") is False      # not hers
    assert d.sil("isik@x", "https://fcm.googleapis.com/fcm/send/abc") is True
    assert set(d.hepsi()) == {"anne@x"}


def test_depo_iki_ornek_birbirini_ezmez(tmp_path):
    a, b = AbonelikDeposu(tmp_path / "a.json"), AbonelikDeposu(tmp_path / "a.json")
    a.ekle("isik@x", abonelik_dogrula(abonelik()))
    b.ekle("anne@x", abonelik_dogrula(abonelik("https://web.push.apple.com/Q")))
    assert set(a.hepsi()) == {"isik@x", "anne@x"}


def test_depo_endpoint_sil_her_kisiden(tmp_path):
    d = AbonelikDeposu(tmp_path / "a.json")
    d.ekle("isik@x", abonelik_dogrula(abonelik()))
    d.ekle("anne@x", abonelik_dogrula(abonelik()))
    assert d.endpoint_sil("https://fcm.googleapis.com/fcm/send/abc") == 2
    assert d.hepsi() == {}


def test_depo_bozuk_dosya_bos_sayilir(tmp_path):
    (tmp_path / "a.json").write_text("{bozuk", encoding="utf-8")
    assert AbonelikDeposu(tmp_path / "a.json").hepsi() == {}


VAPID = VapidAyarlari("pub", "priv", "https://tedy.online")


def test_gonder_basari_ve_yuk():
    cagrilar = []

    def sahte(**kw):
        cagrilar.append(kw)
        return SimpleNamespace(status_code=201)
    sonuc = gonder({"endpoint": "https://e", "keys": {"p256dh": P256, "auth": AUTH}},
                   {"baslik": "Sınav", "govde": "Yarın"}, VAPID, webpush_fn=sahte)
    assert sonuc == GonderimSonucu("ok", 201, "")
    [kw] = cagrilar
    assert json.loads(kw["data"]) == {"baslik": "Sınav", "govde": "Yarın"}
    assert kw["vapid_private_key"] == "priv" and kw["vapid_claims"] == {"sub": "https://tedy.online"}
    assert kw["ttl"] == 12 * 3600 and kw["subscription_info"]["endpoint"] == "https://e"


@pytest.mark.parametrize("kod,durum", [(410, "olu"), (404, "olu"), (403, "olu"), (500, "hata"), (None, "hata")])
def test_gonder_hata_siniflari(kod, durum):
    def sahte(**kw):
        hata = RuntimeError("push failed")
        hata.response = SimpleNamespace(status_code=kod) if kod else None
        raise hata
    sonuc = gonder({"endpoint": "https://e", "keys": {}}, {}, VAPID, webpush_fn=sahte)
    assert (sonuc.durum, sonuc.kod) == (durum, kod)
