"""Where the residue cleaner runs (plan 2026-09-28-portal-ekleri, Görev 2):
storage (scrape_all, run_sync's merge), the API boundary and the BM25 text.
Invented names only — see tests/test_portal_susu.py."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.run_sync as run_sync  # noqa: E402
import src.scrape_all as scrape_all  # noqa: E402
from src.assistant_core import _fmt_scraped_data  # noqa: E402
from tests.test_portal_susu import GENEL, sizinti  # noqa: E402

HAFTA = "2. Hafta 21 Eyl. - 27 Eyl."


def _kayit(metin=GENEL):
    return {"tab_id": "tab_genel", "text": metin, "tables": [], "items": [], "cards": [metin]}


# ── (a) storage ──────────────────────────────────────────────────────────────

def test_sekme_kaydi_saklanmadan_once_temizlenir_tavanlar_kalir():
    uzun = "Gövde cümlesi. " * 700                     # ~10,500 chars
    kayit = scrape_all._icerik_kaydi("tab_genel", uzun + "\n" + GENEL, [],
                                     ["Kurgu madde"], [GENEL, "x" * 3000])
    assert sizinti(json.dumps(kayit, ensure_ascii=False)) == []
    assert len(kayit["text"]) == 8000
    assert kayit["items"] == ["Kurgu madde"]
    assert [len(k) for k in kayit["cards"]][1] == 2000


class _Popup:
    """The homework popup: a description after <hr>, no links."""
    def __init__(self, html):
        self.page_source = html

    def get(self, url):
        pass

    def find_elements(self, by, sel):
        return []


def test_odev_aciklamasi_temiz_saklanir(monkeypatch):
    monkeypatch.setattr(scrape_all.time, "sleep", lambda *_: None)
    html = ('<div class="col-md-12"><label>Ödev Detayı</label><hr>'
            "<p>Sayfa 12-13 okunacak.</p><p>Daha fazla oku</p><p>Kurgu Öğrenci Bir</p>"
            "<p>Yorum Ekle</p></div>")
    detay = scrape_all._scrape_homework_detail(_Popup(html), "1", "2")
    assert detay["description"] == "Sayfa 12-13 okunacak."


def test_onceki_turlarin_haftalari_birlestirirken_temizlenir():
    onceki = {"ders_icerikleri_haftalar": {"1. Hafta 14 Eyl. - 20 Eyl.": {"Genel": _kayit()}}}
    data = {"ders_icerikleri": {"guncel": {"Genel": _kayit()}, "guncel_hafta": HAFTA,
                                "haftalar": {HAFTA: {"Genel": _kayit()}}}}
    run_sync._icerik_birlestir(data, onceki)
    assert set(data["ders_icerikleri_haftalar"]) == {"1. Hafta 14 Eyl. - 20 Eyl.", HAFTA}
    assert data["ders_icerikleri"]["Genel"]["text"].startswith("Okulumuzda")
    assert sizinti(json.dumps(data, ensure_ascii=False)) == []


def test_okunamayan_icerik_onceki_okumayi_temiz_tutar():
    # A failed tab keeps last run's reading (_son_okuma) in the split shape.
    onceki = {"ders_icerikleri": {"Genel": _kayit()},
              "ders_icerikleri_haftalar": {HAFTA: {"Genel": _kayit()}}}
    data = {"ders_icerikleri": onceki["ders_icerikleri"]}
    run_sync._icerik_birlestir(data, onceki)
    assert sizinti(json.dumps(data, ensure_ascii=False)) == []
    assert list(data["ders_icerikleri_haftalar"]) == [HAFTA]


# ── (b) API boundary ─────────────────────────────────────────────────────────

VERI = {
    "ders_programi": [],
    "ders_icerikleri": {"Genel": _kayit()},
    "ders_icerikleri_haftalar": {HAFTA: {"Genel": _kayit()}},
    "odevlerim": {"summary": "", "homework": {"headers": [], "rows": [{
        "Ders Adı": "Türkçe", "Ödev Başlığı": "Okuma", "Ödev Son Teslim Tarihi": "30.09.2026 12:00",
        "Ödev Durumu": "Değerlendirilmemiş",
        "detail": {"description": "Sayfa 12\n  Daha fazla oku\nKurgu Öğrenci Bir\nYorum Ekle",
                   "attachments": []}}]}},
    "duyurular": {"announcements": [{"e-Posta Başlık": "Gezi",
                                     "e-Posta İçerik": "Gezi cuma.\n  Daha fazla oku\nKurgu Öğrenci Bir\nYorum Ekle",
                                     "Ekleri": "-", "Yayın Tarihi": "22.09.2026"}]},
    "ek_sayfalar": {"mla_kaynakca": {"title": "MLA", "empty": False, "documents": [],
                                     "text": "Rehber\n  Daha fazla oku\nKurgu Öğrenci Bir\nYorum Ekle"}},
}


@pytest.fixture
def api(monkeypatch, tmp_path):
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_scraped", lambda: json.loads(json.dumps(VERI)))
    monkeypatch.setattr(api, "_load_photo_homework_rows", lambda: [])
    monkeypatch.setattr(api, "OUTPUT_DIR", str(tmp_path))
    api.app.config["TESTING"] = True
    return api


@pytest.mark.parametrize("yol", ["/api/content", "/api/content/weeks", "/api/homework",
                                 "/api/announcements", "/api/pages"])
def test_api_ham_veriyi_temiz_sunar(api, yol):
    with api.app.test_client() as c:
        cevap = c.get(yol)
    assert cevap.status_code == 200
    assert sizinti(cevap.get_data(as_text=True)) == []
    assert sizinti(json.dumps(cevap.get_json(), ensure_ascii=False)) == []


def test_okul_gonderisi_api_de_kalir(api):
    with api.app.test_client() as c:
        genel = c.get("/api/content").get_json()["Genel"]
    assert genel["text"].startswith("Okulumuzda Bilim Şenliği Başlıyor")


def test_asistanin_canli_kaynaklari_da_temiz(api):
    assert sizinti(json.dumps(api._canli_ders_icerikleri(), ensure_ascii=False)) == []
    assert sizinti(json.dumps(api._canli_odevler(), ensure_ascii=False)) == []


# ── the BM25 text ───────────────────────────────────────────────────────────

def test_indeks_metni_odev_ve_sayfa_susunu_tasimaz():
    assert sizinti(_fmt_scraped_data(json.loads(json.dumps(VERI)))) == []
