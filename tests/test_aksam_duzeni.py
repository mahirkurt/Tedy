"""Akşam düzeni ayarı: saf doğrulama/okuma ve uçlar."""
import json
import os

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
os.environ.setdefault("DASHBOARD_SECRET_KEY", "test-only")

from src.aksam_duzeni import VARSAYILAN, dakika, dogrula, oku  # noqa: E402


def test_varsayilan_aksam(tmp_path):
    d = oku(tmp_path / "yok.json")
    assert d["odeve_hazir"] == "17:00" and d["yatma"] == "21:00" and d["varsayilan"] is True


def test_sira_zorunlu():
    _, hata = dogrula({**VARSAYILAN, "zor_is_sonu": "16:30"}, set())
    assert hata and "sırayla" in hata


def test_yemek_hazir_ile_hazirlik_arasinda():
    _, hata = dogrula({**VARSAYILAN, "yemek": "20:45"}, set())
    assert hata


def test_haber_alacaklar_yalniz_aile(tmp_path):
    _, hata = dogrula({**VARSAYILAN, "haber_alacaklar": ["yabanci@x.com"]}, {"anne@x.com"})
    assert hata
    d, hata = dogrula({**VARSAYILAN, "haber_alacaklar": ["ANNE@x.com"]}, {"anne@x.com"})
    assert hata is None and d["haber_alacaklar"] == ["anne@x.com"]


def test_eski_bicim_okunur(tmp_path):
    p = tmp_path / "odak_penceresi.json"
    p.write_text('{"okul_bitisi":"15:45","odak_sonu":"16:00","yatma":"20:45"}')
    d = oku(tmp_path / "aksam_duzeni.json", eski=p)
    assert d["yatma"] == "20:45" and d["odeve_hazir"] == "17:00" and d["varsayilan"] is False


def test_bozuk_dosya_varsayilan(tmp_path):
    p = tmp_path / "aksam_duzeni.json"
    p.write_text("{bozuk")
    assert oku(p)["varsayilan"] is True


@pytest.mark.parametrize("alan,deger", [("yemek_dk", 5), ("yemek_dk", 61), ("baslamadi_esik_dk", 4),
                                        ("takildi_esik_dk", 61), ("yatma", "25:00")])
def test_sinirlar(alan, deger):
    _, hata = dogrula({**VARSAYILAN, alan: deger}, set())
    assert hata and hata.endswith(".")


def test_dakika():
    assert dakika("17:30") == 1050


def test_elle_duzenlenmis_alicilar_yazi_degilse_duser(tmp_path):
    """R28 küçük 10: elle düzenlenmiş dosyada yazı olmayan alıcı (sayı, null, sözlük, liste) düşer,
    okuma patlamaz ve saatler varsayılana dönmez; liste olmayan değer boş liste olur."""
    p = tmp_path / "aksam_duzeni.json"
    p.write_text(json.dumps({**VARSAYILAN, "yatma": "21:15",
                             "haber_alacaklar": [5, None, {"e": 1}, ["x"], " ANNE@x.com ", True]}), encoding="utf-8")
    d = oku(p)
    assert d["varsayilan"] is False and d["yatma"] == "21:15"
    assert d["haber_alacaklar"] == ["anne@x.com"]
    p.write_text(json.dumps({**VARSAYILAN, "yatma": "21:15", "haber_alacaklar": "anne@x.com"}), encoding="utf-8")
    d = oku(p)
    assert d["varsayilan"] is False and d["yatma"] == "21:15" and d["haber_alacaklar"] == []


# ── uçlar ──────────────────────────────────────────────────────────────

AILE = "drmahirkurt@gmail.com"
OGRENCI = "isikkurtx@gmail.com"


@pytest.fixture
def api(tmp_path, monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path))
    api.app.config["TESTING"] = True
    return api, tmp_path


def giris(c, email):
    with c.session_transaction() as s:
        s["user_email"] = email


def test_put_get_gidis_donus(api):
    api, tmp = api
    with api.app.test_client() as c:
        giris(c, AILE)
        g = c.get("/api/aksam-duzeni").get_json()
        assert g["varsayilan"] is True and g["aile_uyeleri"]
        assert all(u["email"] != "isikkurtx@gmail.com" for u in g["aile_uyeleri"])
        govde = {**{k: v for k, v in g.items() if k in VARSAYILAN}, "yatma": "21:15"}
        r = c.put("/api/aksam-duzeni", json=govde)
        assert r.status_code == 200
        g2 = c.get("/api/aksam-duzeni").get_json()
        assert g2["yatma"] == "21:15" and g2["varsayilan"] is False
        assert json.loads((tmp / "aksam_duzeni.json").read_text())["yatma"] == "21:15"
        bad = c.put("/api/aksam-duzeni", json={**govde, "zor_is_sonu": "16:00"})
        assert bad.status_code == 400 and bad.get_json()["error"].endswith(".")


def test_odak_penceresi_duzenle_uyumlu(api):
    api, _ = api
    with api.app.test_client() as c:
        giris(c, AILE)
        o = c.get("/api/odak-penceresi").get_json()
        d = c.get("/api/aksam-duzeni").get_json()
        assert o["odak_sonu"] == d["zor_is_sonu"] == "19:00"
        r = c.put("/api/odak-penceresi", json={"okul_bitisi": "15:30", "odak_sonu": "19:15", "yatma": "21:30"})
        assert r.status_code == 200
        assert c.get("/api/aksam-duzeni").get_json()["zor_is_sonu"] == "19:15"
        assert c.get("/api/odak-penceresi").get_json()["odak_sonu"] == "19:15"


# ── R28 I2: ayarı yalnız aile değiştirir; aile listesi yalnız aileye gider ─────────────────

def _govde():
    return {k: v for k, v in VARSAYILAN.items()}


def test_ogrenci_ayari_okur_ama_degistiremez(api):
    api, tmp = api
    with api.app.test_client() as c:
        giris(c, OGRENCI)
        g = c.get("/api/aksam-duzeni")
        assert g.status_code == 200 and g.get_json()["yatma"] == "21:00"
        assert "aile_uyeleri" not in g.get_json()                    # Işık listeyi görmez
        r = c.put("/api/aksam-duzeni", json={**_govde(), "baslamadi_esik_dk": 60, "haber_alacaklar": []})
        assert r.status_code == 403 and r.get_json() == {"error": "Bu ayarı yalnız aile değiştirebilir."}
    assert not (tmp / "aksam_duzeni.json").exists()


def test_api_anahtari_ve_oturumsuz_bypass_degistiremez(api, monkeypatch):
    api, tmp = api
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", True)
    with api.app.test_client() as c:                               # bypass, oturum yok: kişi değil
        assert "aile_uyeleri" not in c.get("/api/aksam-duzeni").get_json()
        r = c.put("/api/aksam-duzeni", json=_govde())
        assert r.status_code == 403 and r.get_json()["error"] == "Bu ayarı yalnız aile değiştirebilir."
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(api, "_validate_api_key", lambda k: "etiket")
    with api.app.test_client() as c:
        h = {"Authorization": "Bearer tdyK_x"}
        g = c.get("/api/aksam-duzeni", headers=h)
        assert g.status_code == 200 and "aile_uyeleri" not in g.get_json()
        assert c.put("/api/aksam-duzeni", json=_govde(), headers=h).status_code == 403
    assert not (tmp / "aksam_duzeni.json").exists()


def test_okuyucu_reddedilir(api, monkeypatch):
    api, tmp = api
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    okuyucu = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER)
    with api.app.test_client() as c:
        giris(c, okuyucu)
        assert c.get("/api/aksam-duzeni").status_code == 403
        assert c.put("/api/aksam-duzeni", json=_govde()).status_code == 403
    assert not (tmp / "aksam_duzeni.json").exists()


def test_aile_listeyi_gorur_ve_kaydeder(api, monkeypatch):
    api, tmp = api
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    with api.app.test_client() as c:
        giris(c, AILE)
        g = c.get("/api/aksam-duzeni").get_json()
        assert g["aile_uyeleri"] and all(u["email"] != OGRENCI for u in g["aile_uyeleri"])
        r = c.put("/api/aksam-duzeni", json={**_govde(), "haber_alacaklar": [AILE]})
        assert r.status_code == 200 and r.get_json()["haber_alacaklar"] == [AILE]


def test_alicilar_gonderilmezse_kayitli_liste_korunur(api, monkeypatch):
    """R28 I3 (arka uç yarısı): listeyi okuyamamış bir istemci onu göndermez; kayıtlı liste silinmez,
    yalnız aileden çıkmış adresler düşer (kaydı bozmasın)."""
    api, tmp = api
    (tmp / "aksam_duzeni.json").write_text(json.dumps({**_govde(), "haber_alacaklar": [AILE, "eski@x.com"]}),
                                           encoding="utf-8")
    with api.app.test_client() as c:
        giris(c, AILE)
        govde = {k: v for k, v in _govde().items() if k != "haber_alacaklar"}
        r = c.put("/api/aksam-duzeni", json={**govde, "yatma": "21:15"})
        assert r.status_code == 200
    kayit = json.loads((tmp / "aksam_duzeni.json").read_text(encoding="utf-8"))
    assert kayit["yatma"] == "21:15" and kayit["haber_alacaklar"] == [AILE]
