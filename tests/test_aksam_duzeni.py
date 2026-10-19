"""Akşam düzeni ayarı: saf doğrulama/okuma ve uçlar."""
import json

import pytest

from src.aksam_duzeni import VARSAYILAN, dakika, dogrula, oku


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


# ── uçlar ──────────────────────────────────────────────────────────────

@pytest.fixture
def api(tmp_path, monkeypatch):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path))
    api.app.config["TESTING"] = True
    return api, tmp_path


def test_put_get_gidis_donus(api):
    api, tmp = api
    with api.app.test_client() as c:
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
        o = c.get("/api/odak-penceresi").get_json()
        d = c.get("/api/aksam-duzeni").get_json()
        assert o["odak_sonu"] == d["zor_is_sonu"] == "19:00"
        r = c.put("/api/odak-penceresi", json={"okul_bitisi": "15:30", "odak_sonu": "19:15", "yatma": "21:30"})
        assert r.status_code == 200
        assert c.get("/api/aksam-duzeni").get_json()["zor_is_sonu"] == "19:15"
        assert c.get("/api/odak-penceresi").get_json()["odak_sonu"] == "19:15"
