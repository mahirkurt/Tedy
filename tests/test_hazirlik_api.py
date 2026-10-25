"""Sınav hazırlığı uçları ve işaret deposu (plan Görev 8): yetki, 404'ler, senaryo parametresi, işaretler."""
import json
import os
from datetime import date

import pytest

os.environ.setdefault("TEST_AUTH_BYPASS", "1")
import src.dashboard_api as api  # noqa: E402
from src import sinav_kilavuzu  # noqa: E402
from src.hazirlik_isaretleri import HazirlikIsaretleri  # noqa: E402
from tests.hazirlik_fikstur import FEN_KONULARI, fen_haritasi, sinav_kaydi  # noqa: E402

# Kadrodaki tam rollü kişiler listeden türetilir; test dosyasında gerçek ad ya da e-posta yazmaz.
_TAM_ROLLU = [e for e, r in api.USER_ROLES.items() if r == api.ROLE_FULL and e not in api.OGRENCI_EMAILS]
AILE, AILE_DIGER = _TAM_ROLLU[0], _TAM_ROLLU[1]
OGRENCI = next(iter(api.OGRENCI_EMAILS))
OKUYUCU = next(e for e, r in api.USER_ROLES.items() if r == api.ROLE_READER)


@pytest.fixture
def c(tmp_path, monkeypatch):
    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(api, "OUTPUT_DIR", str(out))
    monkeypatch.setattr(api, "PHOTO_HOMEWORK_FILE", str(out / "photo_homework.json"))
    monkeypatch.setattr(api, "_ek_kayitlari", lambda: {})
    monkeypatch.setattr(api, "_scraped", lambda: {})
    monkeypatch.setattr(api, "_hazirlik_bugun", lambda: date(2026, 10, 25))
    monkeypatch.setattr(api, "_hazirlik_sinavlari", lambda: [sinav_kaydi(konular=FEN_KONULARI)])
    monkeypatch.setattr(sinav_kilavuzu, "harita_oku",
                        lambda anahtar, dizin=None: fen_haritasi() if anahtar == "fen-bilimleri" else None)
    api.app.config["TESTING"] = True
    with api.app.test_client() as istemci:
        yield istemci


def giris(c, email, ad=None):
    with c.session_transaction() as s:
        s["user_email"] = email
        if ad:
            s["user_name"] = ad


def isaret_koy(c, kod, durum, ders="fen-bilimleri"):
    return c.put("/api/hazirlik/isaret", json={"ders": ders, "kod": kod, "durum": durum})


def test_genel_bakis_ucu(c):
    giris(c, AILE)
    r = c.get("/api/hazirlik")
    assert r.status_code == 200
    j = r.get_json()
    assert j["durum"] == "hazir" and j["yaklasan"][0]["anahtar"] == "fen-bilimleri"
    assert len(j["dersler"]) == 6


def test_ders_ucu_ve_404ler(c):
    giris(c, AILE)
    assert c.get("/api/hazirlik/fen-bilimleri/1").get_json()["toplamlar"] == {"1": 9, "2": 7, "3": 8, "4": 6}
    r = c.get("/api/hazirlik/fizik/1")
    assert (r.status_code, r.get_json()["error"]) == (404, "bilinmeyen_ders")
    assert c.get("/api/hazirlik/fen-bilimleri/3").status_code == 404
    assert c.get("/api/hazirlik/fen-bilimleri/x").status_code == 404


def test_kilavuz_ucu_senaryo_ve_secenek_parametreleri(c):
    giris(c, AILE)
    assert c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").get_json()["senaryo"] == 2
    j = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?senaryo=3&ebeveyn=1&isaret=0").get_json()
    assert (j["senaryo"], j["secilen_duyurulan_degil"], j["secenekler"]) == (3, True, {"ebeveyn": True, "isaret": False})
    for kotu in ("9", "abc", "-1"):
        r = c.get(f"/api/hazirlik/fen-bilimleri/1/kilavuz?senaryo={kotu}")
        assert (r.status_code, r.get_json()["error"]) == (404, "bilinmeyen_senaryo")


def test_tablo_eski_409(c, monkeypatch):
    giris(c, AILE)
    monkeypatch.setattr(api, "_hazirlik_bugun", lambda: date(2027, 2, 10))
    assert c.get("/api/hazirlik").get_json()["durum"] == "tablo_eski"
    r = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz")
    assert (r.status_code, r.get_json()["mesaj"]) == (409, "Yeni yılın tabloları bekleniyor.")
    r = c.get("/api/hazirlik/fen-bilimleri/1")
    assert (r.status_code, r.get_json()["error"]) == (409, "tablo_eski")


def test_tablo_yok_503(c, monkeypatch):
    giris(c, AILE)
    monkeypatch.setattr("src.sinav_senaryo.tablo_oku", lambda *a, **k: None)
    assert c.get("/api/hazirlik").get_json()["durum"] == "tablo_yok"
    r = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz")
    assert (r.status_code, r.get_json()["error"]) == (503, "tablo_yok")


def test_okuyucu_hazirlik_uclarina_erisemez(c):
    """Review Focus: okuma yetkili hesap hazırlık uçlarına erişemez, işaret koyamaz (default-deny)."""
    giris(c, OKUYUCU)
    assert c.get("/api/hazirlik").status_code == 403
    assert c.get("/api/hazirlik/fen-bilimleri/1").status_code == 403
    assert c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").status_code == 403
    r = c.put("/api/hazirlik/isaret", json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "hazirim"})
    assert r.status_code == 403
    assert not os.path.exists(os.path.join(api.OUTPUT_DIR, "hazirlik_isaretleri.json"))
    assert not {"hazirlik_genel", "hazirlik_ders", "hazirlik_kilavuz", "hazirlik_isaret"} & api.READER_ENDPOINTS


def test_api_anahtari_okur_ama_isaret_koyamaz(c, monkeypatch):
    """Review Focus: anahtarın kişisi yok — okuyabilir, işaret koyamaz."""
    monkeypatch.setattr(api, "API_KEYS", [("test", "tdyK_deneme")])
    baslik = {"Authorization": "Bearer tdyK_deneme"}
    assert c.get("/api/hazirlik", headers=baslik).status_code == 200
    r = c.put("/api/hazirlik/isaret", headers=baslik, json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "hazirim"})
    assert (r.status_code, r.get_json()["error"]) == (403, "yalnız oturumla")


def test_oturumsuz_istek_401(c):
    assert c.get("/api/hazirlik").status_code == 401
    assert c.put("/api/hazirlik/isaret", json={}).status_code == 401


def test_isaret_yaz_kilavuzda_gorunur_ve_kaldirilir(c):
    giris(c, AILE)
    r = c.put("/api/hazirlik/isaret", json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "tekrar"})
    assert r.get_json() == {"ders": "fen-bilimleri", "isaretler": {"FB.7.2.1": "tekrar"}}
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").get_json()
    blok = next(b for u in m["uniteler"] for cer in u["cerceveler"] for b in cer["bloklar"] if b["kod"] == "FB.7.2.1")
    assert blok["isaret"] == "tekrar"
    r = c.put("/api/hazirlik/isaret", json={"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": None})
    assert r.get_json()["isaretler"] == {}


@pytest.mark.parametrize("govde", [
    {"ders": "fizik", "kod": "FB.7.2.1", "durum": "tekrar"}, {"ders": "fen-bilimleri", "kod": "MAT.7.1.1", "durum": "tekrar"},
    {"ders": "fen-bilimleri", "kod": "FB.7.2.1", "durum": "belki"}, {"ders": "fen-bilimleri", "kod": ["FB.7.2.1"]}, {},
    {"ders": "fen-bilimleri", "kod": "FB.7.2.1"},          # durum anahtarı yok: sessizce işaret kaldırmaz
    ["FB.7.2.1"], "metin", {"ders": ["fen-bilimleri"], "kod": "FB.7.2.1", "durum": "tekrar"}])
def test_isaret_gecersiz_girdi_400(c, govde):
    giris(c, AILE)
    assert c.put("/api/hazirlik/isaret", json=govde).status_code == 400
    assert not os.path.exists(os.path.join(api.OUTPUT_DIR, "hazirlik_isaretleri.json"))


def test_isaret_yazilamayan_dosya_503(c, monkeypatch):
    giris(c, AILE)

    def yazamaz(self, *a, **k):
        raise OSError("disk dolu")
    monkeypatch.setattr(HazirlikIsaretleri, "yaz", yazamaz)
    r = isaret_koy(c, "FB.7.2.1", "tekrar")
    assert (r.status_code, r.get_json()["error"]) == (503, "yazilamadi")


def test_isaret_tablo_yoksa_503(c, monkeypatch):
    giris(c, AILE)
    monkeypatch.setattr("src.sinav_senaryo.tablo_oku", lambda *a, **k: None)
    r = isaret_koy(c, "FB.7.2.1", "tekrar")
    assert (r.status_code, r.get_json()["error"]) == (503, "tablo_yok")


# --- D16: ekran kılavuzu oturumdaki kişinin işaretleriyle, ebeveyn özeti öğrencinin işaretleriyle ---

def test_isaretler_kisiye_ozel_ekranda(c):
    giris(c, AILE)
    isaret_koy(c, "FB.7.2.1", "tekrar")
    giris(c, AILE_DIGER)
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").get_json()
    assert all(b["isaret"] is None for u in m["uniteler"] for cer in u["cerceveler"] for b in cer["bloklar"])


def test_ebeveyn_ozeti_ogrencinin_isaretlerinden_gelir_ekran_baskasinin(c, monkeypatch):
    """Ebeveyn kendi işaretiyle ekranı kurar; özetin sayıları yine öğrencinin işaretlerinden gelir."""
    monkeypatch.setattr(api, "_scraped", lambda: {"ogrenci_profili": {"name": "Deneme Öğrenci"}})
    giris(c, OGRENCI, "Deneme Öğrenci")
    isaret_koy(c, "FB.7.2.1", "tekrar")
    isaret_koy(c, "FB.7.1.1", "hazirim")
    giris(c, AILE, "Deneme Veli")
    isaret_koy(c, "FB.7.1.3", "hazirim")
    isaret_koy(c, "FB.7.1.5", "hazirim")
    isaret_koy(c, "FB.7.2.2", "hazirim")
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?ebeveyn=1").get_json()
    eb = m["ebeveyn"]
    assert (eb["hazirim"], eb["tekrar"]) == (1, 1)
    assert eb["hazirim"] + eb["tekrar"] + eb["isaretsiz"] == eb["cikti_sayisi"]
    # ekran bloklarında ise bakanın kendi işaretleri
    blok = {b["kod"]: b for u in m["uniteler"] for cer in u["cerceveler"] for b in cer["bloklar"]}
    assert blok["FB.7.1.3"]["isaret"] == "hazirim" and blok["FB.7.2.1"]["isaret"] is None
    assert m["isaret_sahibi"] == "Deneme Veli" and eb["isaret_sahibi"] == "Deneme Öğrenci"
    assert m["secenekler"]["ebeveyn"] is True
    # içerik özeti birleşik modelin özeti
    assert m["icerik_ozeti"] == sinav_kilavuzu.icerik_ozeti(m)


def test_ebeveyn_ozeti_isaret_kapaliyken_de_ogrencinin_sayilari(c, monkeypatch):
    monkeypatch.setattr(api, "_scraped", lambda: {"ogrenci_profili": {"name": "Deneme Öğrenci"}})
    giris(c, OGRENCI, "Deneme Öğrenci")
    isaret_koy(c, "FB.7.2.1", "tekrar")
    giris(c, AILE, "Deneme Veli")
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?ebeveyn=1&isaret=0").get_json()
    assert m["ebeveyn"]["tekrar"] == 1 and m["isaret_sahibi"] is None
    assert m["ebeveyn"]["isaret_sahibi"] == "Deneme Öğrenci"


def test_ogrencinin_kendi_oturumunda_ebeveyn_ozeti_kendi_isaretleri(c):
    giris(c, OGRENCI, "Deneme Öğrenci")
    isaret_koy(c, "FB.7.2.1", "tekrar")
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?ebeveyn=1").get_json()
    assert m["ebeveyn"]["tekrar"] == 1 and m["ebeveyn"]["isaret_sahibi"] == m["isaret_sahibi"] == "Deneme Öğrenci"


def test_api_anahtarinda_isaret_yok_ama_ebeveyn_ozeti_ogrencinin(c, monkeypatch):
    giris(c, OGRENCI, "Deneme Öğrenci")
    isaret_koy(c, "FB.7.2.1", "tekrar")
    with c.session_transaction() as s:
        s.clear()
    monkeypatch.setattr(api, "API_KEYS", [("test", "tdyK_deneme")])
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?ebeveyn=1", headers={"Authorization": "Bearer tdyK_deneme"}).get_json()
    assert m["isaret_sahibi"] is None and m["ebeveyn"]["tekrar"] == 1
    assert all(b["isaret"] is None for u in m["uniteler"] for cer in u["cerceveler"] for b in cer["bloklar"])


def test_isaret_sahibi_gosterim_adidir_eposta_degil(c):
    """PDF'e e-posta girmemeli: ad oturumun görünen adından ya da öğrenci profilinden gelir; yoksa None (uydurma yok)."""
    giris(c, AILE)                                   # oturumda ad yok
    assert c.get("/api/hazirlik/fen-bilimleri/1/kilavuz").get_json()["isaret_sahibi"] is None
    giris(c, AILE, "Deneme Veli")
    yanit = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?ebeveyn=1")
    assert yanit.get_json()["isaret_sahibi"] == "Deneme Veli"
    metin = yanit.get_data(as_text=True)
    assert "@" not in metin                                  # model metninde e-posta yok
    assert AILE not in metin and OGRENCI not in metin


def test_ogrenci_adi_profilden(c, monkeypatch):
    monkeypatch.setattr(api, "_scraped", lambda: {"ogrenci_profili": {"name": "Deneme Öğrenci"}})
    giris(c, AILE, "Deneme Veli")
    m = c.get("/api/hazirlik/fen-bilimleri/1/kilavuz?ebeveyn=1").get_json()
    assert m["ebeveyn"]["isaret_sahibi"] == "Deneme Öğrenci"


def test_kilavuz_isaretleri_yardimcisi(c):
    """Görev 14'ün çağıracağı tek yardımcı: ekran → oturumdaki kişi; baski/ebeveyn → öğrenci."""
    from flask import session as flask_session
    with api.app.test_request_context("/"):
        flask_session["user_email"] = AILE
        flask_session["user_name"] = "Deneme Veli"
        assert api._kilavuz_isaretleri("oturum") == (AILE, "Deneme Veli")
        email, ad = api._kilavuz_isaretleri("ogrenci")
        assert email == OGRENCI and ad != OGRENCI and "@" not in (ad or "")
        with pytest.raises(ValueError):
            api._kilavuz_isaretleri("baska")


def test_isaret_deposu_kisi_ayri_ve_bozuk_dosya_kenara_alinir(tmp_path):
    yol = tmp_path / "hazirlik_isaretleri.json"
    d = HazirlikIsaretleri(yol)
    assert d.yaz("A@x.com", "fen-bilimleri", "FB.7.2.1", "hazirim") == {"FB.7.2.1": "hazirim"}
    d.yaz("b@x.com", "fen-bilimleri", "FB.7.1.1", "tekrar")
    assert d.kisi("a@x.com") == {"fen-bilimleri": {"FB.7.2.1": "hazirim"}}
    with pytest.raises(ValueError):
        d.yaz("a@x.com", "fen-bilimleri", "FB.7.2.1", "belki")
    yol.write_text("{", encoding="utf-8")
    assert d.kisi("a@x.com") == {}
    d.yaz("a@x.com", "fen-bilimleri", "FB.7.2.2", "tekrar")
    assert len(list(tmp_path.glob("hazirlik_isaretleri.json.bozuk-*"))) == 1
    assert json.loads(yol.read_text(encoding="utf-8"))["kisiler"] == {"a@x.com": {"fen-bilimleri": {"FB.7.2.2": "tekrar"}}}


def test_isaret_deposu_eszamanli_yazimlar_kaybolmaz(tmp_path):
    """İki gunicorn işçisi: flock altında okuma-değiştirme-yazma, hiçbir işaret ezilmez."""
    import threading
    d = HazirlikIsaretleri(tmp_path / "hazirlik_isaretleri.json")
    kodlar = [f"FB.7.{u}.{n}" for u in range(1, 4) for n in range(1, 6)]
    isler = [threading.Thread(target=d.yaz, args=("a@x.com", "fen-bilimleri", k, "tekrar")) for k in kodlar]
    [t.start() for t in isler]
    [t.join() for t in isler]
    assert set(d.kisi("a@x.com")["fen-bilimleri"]) == set(kodlar)
