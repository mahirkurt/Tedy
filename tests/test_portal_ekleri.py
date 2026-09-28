"""Attachment links: recognise, name, locate, collect (plan 2026-09-28-portal-ekleri,
Görev 3). Hosts, paths and ids are invented; the shapes are the measured ones."""
import json
from pathlib import Path

import pytest

from src.portal_ekleri import (DURUM_BAGLANTI, DURUM_BEKLIYOR, DURUM_ERISILEMEDI,
                               DURUM_INDIRILDI, KIMLIK_DESENI, METIN_ONEKI, EkDeposu,
                               ek_basligi, ek_kimligi, ek_ozeti, ek_turu, ekleri_topla,
                               indirme_adresi, metin_govdesi, sayfa_belgesi_adi)

SP_URL = ("https://ornekokul-my.sharepoint.com/:b:/g/personal/ogretmen_ornekokul_k12_tr/"
          "EaBcDeFgHiJkLmNoPqRsTuV?e=AbC123")
DRIVE_KIMLIK = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
DRIVE_URL = f"https://drive.google.com/file/d/{DRIVE_KIMLIK}/preview"
DOCS_URL = ("https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/edit"
            "?usp=sharing&ouid=100000000000000000000")
PORTAL_URL = "https://portal.tedronesans.k12.tr/dosyalar/odev/ornek-calisma.pdf"
YOUTUBE = "https://www.youtube.com/watch?v=ornekvideo01"


@pytest.mark.parametrize("url,tur", [
    (SP_URL, "sharepoint"),
    ("https://ornekokul-my.sharepoint.com/:f:/g/personal/ogretmen_ornekokul_k12_tr/EkLaSoR?e=q1", "baglanti"),
    ("https://ornekokul-my.sharepoint.com/personal/ogretmen/Documents/calisma.docx", "sharepoint"),
    (DRIVE_URL, "drive"),
    (f"https://drive.google.com/open?id={DRIVE_KIMLIK}", "drive"),
    ("https://drive.google.com/drive/folders/1KlAsOr0000000000", "baglanti"),
    (DOCS_URL, "google-docs"),
    ("https://docs.google.com/presentation/d/1SuNuM0000000000000/edit", "google-docs"),
    ("https://docs.google.com/forms/d/e/1FAIpQLSornek/viewform", "baglanti"),
    (PORTAL_URL, "portal"),
    ("https://portal.tedronesans.k12.tr/pages/proje_istekler/p_ders_projeler", "baglanti"),
    ("https://ornek.edu.tr/belgeler/K%C4%B1lavuz%20Sayfa.pdf", "dosya"),
    ("https://teams.microsoft.com/l/meetup-join/19%3aornek", "baglanti"),
    (YOUTUBE, "baglanti"),
    ("javascript:void(0)", "baglanti"),
    ("", "baglanti"),
])
def test_ek_turu(url, tur):
    assert ek_turu(url) == tur


def test_ayni_drive_dosyasinin_her_bicimi_ayni_kimlik():
    bicimler = [DRIVE_URL, DRIVE_URL.replace("/preview", "/view?usp=sharing"),
                f"https://drive.google.com/open?id={DRIVE_KIMLIK}",
                f"https://drive.google.com/uc?export=download&id={DRIVE_KIMLIK}"]
    assert len({ek_kimligi(u) for u in bicimler}) == 1
    assert KIMLIK_DESENI.match(ek_kimligi(DRIVE_URL))


def test_sharepoint_kimligi_e_parametresinden_bagimsiz():
    assert ek_kimligi(SP_URL) == ek_kimligi(SP_URL.replace("e=AbC123", "e=ZzZ999"))
    assert ek_kimligi(SP_URL) != ek_kimligi(SP_URL.replace("EaBcDe", "EzYxWv"))


def test_indirme_adresleri():
    assert indirme_adresi(SP_URL) == SP_URL + "&download=1"
    assert indirme_adresi(SP_URL + "&download=1") == SP_URL + "&download=1"
    assert indirme_adresi(DRIVE_URL) == f"https://drive.google.com/uc?export=download&id={DRIVE_KIMLIK}"
    assert indirme_adresi(DOCS_URL) == ("https://docs.google.com/document/d/"
                                        "1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/export?format=pdf")
    assert indirme_adresi(PORTAL_URL) == PORTAL_URL
    assert indirme_adresi(YOUTUBE) is None


VERI = {
    "odevlerim": {"summary": "", "homework": {"headers": [], "rows": [{
        "Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
        "Ödev Son Teslim Tarihi": "25.09.2026 12:00",
        "detail": {"description": "Sayfa 12-13", "attachments": [
            {"name": "Sayfa 12-13.pdf", "url": SP_URL},
            {"name": "Konu videosu", "url": YOUTUBE}]}}]}},
    "ek_sayfalar": {
        "mla_kaynakca": {"title": "MLA Kaynakça Hazırlama Rehberi", "empty": False,
                         "url": "https://portal.tedronesans.k12.tr/pages/proje_istekler/p_kaynakca",
                         "documents": [DRIVE_URL, DRIVE_URL.replace("/preview", "/view")]},
        "akademik_durustluk": {"title": "Akademik Dürüstlük Politikası", "empty": False,
                               "documents": [DRIVE_URL]},
    },
    "duyurular": {"announcements": [{"e-Posta Başlık": "Gezi izni", "Yayın Tarihi": "22.09.2026",
                                     "Ekleri": "izin-formu.pdf",
                                     "Ekleri_url": "https://ornek.edu.tr/formlar/izin-formu.pdf"}]},
    "takim_calismalari": {"activities": {"rows": [
        {"Teams Link": "https://teams.microsoft.com/l/meetup-join/19%3aornek"}]}},
    "ders_icerikleri": {"Matematik": {"tab_id": "ders_2", "text":
                        "Çalışma kağıdı: https://ornek.edu.tr/kagitlar/kesirler.pdf, iyi çalışmalar.",
                        "cards": [], "items": [], "tables": []}},
}


def test_toplayici_her_bolumu_okur_bir_kimlige_bir_aday():
    adaylar = {a.kimlik: a for a in ekleri_topla(VERI)}
    sp = adaylar[ek_kimligi(SP_URL)]
    assert sp.ad == "Sayfa 12-13.pdf" and sp.tur == "sharepoint"
    assert sp.kaynaklar == [{"section": "odevler",
                             "item": "Sosyal Bilgiler|Kitap okuma ödevi|25.09.2026 12:00",
                             "title": "Kitap okuma ödevi", "course": "Sosyal Bilgiler"}]
    assert adaylar[ek_kimligi(YOUTUBE)].tur == "baglanti"       # the teacher put it there
    drive = adaylar[ek_kimligi(DRIVE_URL)]
    # Two URL shapes on one page and the same file on a second page: one candidate.
    assert drive.ad == "MLA Kaynakça Hazırlama Rehberi (1. belge)"
    assert [k["item"] for k in drive.kaynaklar] == ["mla_kaynakca", "akademik_durustluk"]
    duyuru = adaylar[ek_kimligi("https://ornek.edu.tr/formlar/izin-formu.pdf")]
    assert duyuru.ad == "izin-formu.pdf" and duyuru.kaynaklar[0]["section"] == "duyurular"
    genel = adaylar[ek_kimligi("https://ornek.edu.tr/kagitlar/kesirler.pdf")]
    assert genel.ad == "kesirler.pdf"
    assert genel.kaynaklar[0] == {"section": "ders_icerikleri", "item": "ders_icerikleri/Matematik/text",
                                  "title": "Matematik", "course": "Matematik"}
    # The generic scan takes files only: no Teams meeting, no portal page.
    assert all("teams.microsoft.com" not in a.url and "/pages/" not in a.url for a in adaylar.values())
    assert len(adaylar) == 5


def test_toplayici_bicimsiz_veride_patlamaz():
    assert ekleri_topla(None) == []
    assert ekleri_topla({"odevlerim": [], "ek_sayfalar": "x", "duyurular": None}) == []


def test_sayfa_belgesi_adi():
    assert sayfa_belgesi_adi("MLA", 1, 1) == "MLA"
    assert sayfa_belgesi_adi("MLA", 2, 3) == "MLA (2. belge)"


def test_depo_gidis_donus_ve_bozuk_izleyici(tmp_path):
    depo = EkDeposu(tmp_path)
    assert depo.oku() == {}
    kimlik = ek_kimligi(SP_URL)
    depo.yaz({kimlik: {"id": kimlik, "status": DURUM_BEKLIYOR}, "../kotu": {"id": "x"}})
    assert list(depo.oku()) == [kimlik]
    assert depo.kayit(kimlik)["status"] == DURUM_BEKLIYOR
    assert depo.kayit("../kotu") is None
    depo.izleyici_yolu.write_text("{bozuk", encoding="utf-8")
    assert depo.oku() == {}


def test_dosya_yolu_yalniz_kendi_dosyasini_verir(tmp_path):
    depo = EkDeposu(tmp_path)
    kimlik = ek_kimligi(SP_URL)
    depo.dizin.mkdir(parents=True)
    (depo.dizin / f"{kimlik}.pdf").write_bytes(b"%PDF-1.7")
    assert depo.dosya_yolu({"id": kimlik, "file": f"{kimlik}.pdf"}) == depo.dizin / f"{kimlik}.pdf"
    for kotu in ("../../etc/passwd", f"{kimlik}.pdf/../x", "0123456789abcdef.pdf", f"{kimlik}.pdfx1"):
        assert depo.dosya_yolu({"id": kimlik, "file": kotu}) is None
    assert depo.dosya_yolu({"id": kimlik, "file": f"{kimlik}.docx"}) is None     # not on disk
    assert depo.dosya_yolu(None) is None


def test_meta_ve_baslik(tmp_path):
    depo = EkDeposu(tmp_path)
    kimlik = ek_kimligi(SP_URL)
    depo.dizin.mkdir(parents=True)
    depo.meta_yolu(kimlik).write_text(json.dumps(
        {"id": kimlik, "name": "Sayfa 12-13.pdf", "title": "Kitap okuma ödevi"}), encoding="utf-8")
    assert ek_basligi(depo.meta(kimlik)) == "Sayfa 12-13.pdf · Kitap okuma ödevi"
    assert depo.meta("../x") == {}
    assert ek_basligi({"name": "Rehber", "source": {"title": "Rehber"}}) == "Rehber"
    assert ek_basligi({}) == "Portal eki"


def test_ek_ozeti_durumlari():
    kimlik = ek_kimligi(SP_URL)
    ekler = {kimlik: {"id": kimlik, "status": DURUM_INDIRILDI, "file": f"{kimlik}.pdf"}}
    assert ek_ozeti(ekler, SP_URL, "Sayfa 12-13.pdf") == {
        "name": "Sayfa 12-13.pdf", "url": SP_URL, "id": kimlik,
        "tedyUrl": f"/api/ekler/{kimlik}", "status": DURUM_INDIRILDI}
    ekler[kimlik] = {"id": kimlik, "status": DURUM_ERISILEMEDI, "reason": "kaynak giriş istiyor"}
    ozet = ek_ozeti(ekler, SP_URL, "Sayfa 12-13.pdf")
    assert ozet["tedyUrl"] is None and ozet["status"] == DURUM_ERISILEMEDI
    assert ozet["reason"] == "kaynak giriş istiyor"
    assert ek_ozeti({}, SP_URL, "x")["status"] == DURUM_BEKLIYOR          # not collected yet
    assert ek_ozeti({}, YOUTUBE, "Video") == {"name": "Video", "url": YOUTUBE, "id": None,
                                               "tedyUrl": None, "status": DURUM_BAGLANTI}


def test_metin_govdesi_baslik_paragrafini_atar():
    assert metin_govdesi(f"{METIN_ONEKI}Ek · Ödev\n\nSoru 1\n\nSoru 2\n") == "Soru 1\n\nSoru 2"
    assert metin_govdesi(f"{METIN_ONEKI}Ek · Ödev\n(Metin katmanı yok.)\n") == ""
    assert metin_govdesi("başlıksız metin") == "başlıksız metin"


def test_ek_kopyalari_git_disinda():
    kurallar = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "content/portal-ekleri/" in kurallar
