"""The five portal pages nothing was reading, and the calendar's year group.

Measured 2026-09-20 on the live portal: Ders Projeleri lists no project yet
(selection opens 1 November), Rehberlik Formları reports "toplam 0 kayıt",
Kulüp Seçimi's dropdowns carry no options, and the two policy pages are
Google Drive previews with no text of their own. So the scraper records what
is there and marks the rest empty — and the API does not offer a reader five
pages with nothing on them.
"""
import pytest
from unittest.mock import patch

import src.dashboard_api as dashboard_api
from src.dashboard_api import app
from src.scrape_all import EK_SAYFALAR, _tablo_kayit_tasiyor, seviye_kodu


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestSeviyeKodu:
    """The calendar filter was hardcoded to "60" — 6. Sınıf — from the day it
    was written, while Işık is in 7-D. It follows the class now.
    """

    def test_yedinci_sinif(self):
        assert seviye_kodu("7-D") == "70"

    def test_sube_olmadan(self):
        assert seviye_kodu("7") == "70"

    def test_cift_haneli_sinif(self):
        assert seviye_kodu("10-A") == "100"

    def test_sinif_bilinmiyorsa_none(self):
        # scrape_takvim falls back to "70" and then to the option's text;
        # inventing a level here would silently filter the wrong year group.
        assert seviye_kodu("") is None
        assert seviye_kodu(None) is None
        assert seviye_kodu("bilinmiyor") is None


class TestEkSayfaListesi:
    def test_bes_sayfa_tanimli(self):
        assert len(EK_SAYFALAR) == 5

    def test_her_kayit_anahtar_baslik_yol(self):
        for anahtar, baslik, yol in EK_SAYFALAR:
            assert anahtar and baslik
            assert yol.startswith("/pages/")


class TestTabloKayitTasiyor:
    """Measured 2026-09-20: the guidance-forms page reports "toplam 0 kayıt"
    yet renders DataTable chrome, and how much of it exists varies between
    runs — four tables on one run, none a minute later. Counting that as
    content would have announced an empty grid as a page worth opening.
    """

    def test_baslik_yankisi_kayit_sayilmaz(self):
        cikti = {"headers": ["Ölçek", "Adı Soyadı", "Birim"],
                 "rows": [["Ölçek", "Adı Soyadı", "Birim"]]}
        assert _tablo_kayit_tasiyor(cikti) is False

    def test_gercek_kayit_sayilir(self):
        cikti = {"headers": ["Ölçek", "Adı Soyadı", "Birim"],
                 "rows": [["Ölçek", "Adı Soyadı", "Birim"],
                          ["Kariyer Ölçeği", "Işık Kurt", "Rehberlik"]]}
        assert _tablo_kayit_tasiyor(cikti) is True

    def test_tek_hucrelik_bos_durum_sayilmaz(self):
        # "Kayıt bulunamadı" spans the table as one cell.
        cikti = {"headers": ["Ölçek", "Adı"], "rows": [["Kayıt bulunamadı", ""]]}
        assert _tablo_kayit_tasiyor(cikti) is False

    def test_bos_ve_eksik_girdi(self):
        assert _tablo_kayit_tasiyor({"headers": [], "rows": []}) is False
        assert _tablo_kayit_tasiyor(None) is False

    def test_basliksiz_tabloda_tek_satir_baslik_sayilir(self):
        # Measured on the live page: the table declared no headers and put
        # its column names in the body while reporting "toplam 0 kayıt".
        cikti = {"headers": [], "rows": [
            ["", "Ölçek", "Adı Soyadı", "Birim", "Atama Yapan"],
        ]}
        assert _tablo_kayit_tasiyor(cikti) is False

    def test_basliksiz_tabloda_ikinci_satir_kayittir(self):
        cikti = {"headers": [], "rows": [
            ["", "Ölçek", "Adı Soyadı"],
            ["", "Kariyer Ölçeği", "Işık Kurt"],
        ]}
        assert _tablo_kayit_tasiyor(cikti) is True

    def test_sayfalama_cubugu_kayit_sayilmaz(self):
        # The pager renders as its own table: "10 20 30 40 50", "Sayfa", "/ 0".
        cikti = {"headers": [], "rows": [
            ["10\n20\n30\n40\n50", "", "Sayfa", "/ 0"],
            ["0 ile 0 arası gösteriliyor, toplam 0 kayıt", "", "", ""],
        ]}
        assert _tablo_kayit_tasiyor(cikti) is False


class TestSayfalarUcu:
    def _sayfa(self, empty=False, **ek):
        return {"title": "X", "url": "u", "text": "", "tables": [],
                "documents": [], "options": [], "empty": empty, **ek}

    def test_bos_sayfalar_sunulmaz(self, client):
        scraped = {"ek_sayfalar": {
            "dolu": self._sayfa(documents=["https://drive/x"]),
            "bos": self._sayfa(empty=True),
        }}
        with patch("src.dashboard_api._scraped", return_value=scraped):
            data = client.get("/api/pages").get_json()
        assert list(data["pages"]) == ["dolu"]
        # The empty one is still named, so the absence can be explained
        # rather than looking like a page that was never scraped.
        assert data["known"] == ["bos", "dolu"]

    def test_portalin_reddi_korunur(self, client):
        scraped = {"ek_sayfalar": {
            "kulup": self._sayfa(
                empty=True,
                unavailable={"reason": "yetkisiz",
                             "detail": "portal bu sayfaya yetki vermiyor"}),
        }}
        with patch("src.dashboard_api._scraped", return_value=scraped):
            data = client.get("/api/pages").get_json()
        assert data["pages"] == {}
        assert data["unavailable"]["kulup"]["reason"] == "yetkisiz"

    def test_hic_veri_yoksa_bos_doner(self, client):
        with patch("src.dashboard_api._scraped", return_value={}):
            data = client.get("/api/pages").get_json()
        assert data == {"pages": {}, "unavailable": {}, "known": []}
