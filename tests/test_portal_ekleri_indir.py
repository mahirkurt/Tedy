"""One attachment download (plan 2026-09-28-portal-ekleri, Görev 5), against the
fake HTTP layer in tests/sahte_http.py only."""
import hashlib

import pytest
import requests

from src.portal_ekleri import ek_kimligi, ek_turu
from src.portal_ekleri_indir import (DOCX_MIME, EK_BOYUT_SINIRI, MB, Butce, ek_indir,
                                     portal_cerez_kavanozu)
from tests.sahte_http import (DOCS_URL, DRIVE_KIMLIK, DRIVE_ONAY, DRIVE_URL, GIRIS_DUVARI, PDF,
                              PORTAL_URL, SP_DUVAR_URL, SP_URL, SahteOturum, SahteSaat,
                              SahteYanit, aralikli, docx_bayt)

SP = "https://ornekokul-my.sharepoint.com/"


def _kayit(url):
    return {"id": ek_kimligi(url), "url": url, "type": ek_turu(url)}


def _sinirsiz():
    return Butce(son_an=float("inf"), bayt=10 * EK_BOYUT_SINIRI)


def _bol(govde, n=MB):
    return [govde[i:i + n] for i in range(0, len(govde), n)]


def _parcalar(dizin):
    return sorted((dizin / ".parca").iterdir()) if (dizin / ".parca").exists() else []


def test_sharepoint_download_1_ile_istenir_pdf_saklanir(tmp_path):
    oturum = SahteOturum({SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf",
                                                                 "Content-Length": str(len(PDF))})})
    sonuc = ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti, sonuc.mime) == ("indirildi", ".pdf", "application/pdf")
    assert sonuc.sha256 == hashlib.sha256(PDF).hexdigest() and sonuc.boyut == len(PDF)
    istek = oturum.istekler[0]
    assert "download=1" in istek["url"] and "e=AbC123" in istek["url"]
    assert istek["cookies"] is None and istek["stream"] is True and "Range" not in istek["headers"]
    assert (tmp_path / sonuc.dosya).read_bytes() == PDF
    assert _parcalar(tmp_path) == []


def test_giris_duvari_dosya_olarak_saklanmaz(tmp_path):
    duvar = SahteYanit(200, GIRIS_DUVARI, {"Content-Type": "text/html; charset=utf-8"},
                       url="https://login.microsoftonline.com/common/oauth2/authorize?client_id=ornek")
    sonuc = ek_indir(SahteOturum({SP: duvar}), _kayit(SP_DUVAR_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "giriş istiyor" in sonuc.neden
    assert [p.name for p in tmp_path.iterdir()] == [".parca"] and _parcalar(tmp_path) == []


def test_octet_stream_diyen_html_de_web_sayfasidir(tmp_path):
    sayfa = SahteYanit(200, b"  <!DOCTYPE html><html>klasor</html>", {"Content-Type": "application/octet-stream"})
    sonuc = ek_indir(SahteOturum({SP: sayfa}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and "web sayfası" in sonuc.neden


def test_drive_onay_sayfasi_formdaki_ikinci_istekle_gecilir(tmp_path):
    oturum = SahteOturum({
        f"https://drive.google.com/uc?export=download&id={DRIVE_KIMLIK}":
            lambda u, h: SahteYanit(200, DRIVE_ONAY, {"Content-Type": "text/html; charset=utf-8"}),
        "https://drive.usercontent.google.com/download?":
            lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/octet-stream"}),
    })
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and sonuc.uzanti == ".pdf"
    ikinci = oturum.istekler[1]["url"]
    assert f"id={DRIVE_KIMLIK}" in ikinci and "confirm=t" in ikinci and "uuid=" in ikinci


def test_drive_onay_sayfasi_ikinci_kez_gelirse_dongu_yok(tmp_path):
    def onay(u, h):
        return SahteYanit(200, DRIVE_ONAY, {"Content-Type": "text/html"})
    oturum = SahteOturum({"https://drive.google.com/": onay, "https://drive.usercontent.google.com/": onay})
    sonuc = ek_indir(oturum, _kayit(DRIVE_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi" and len(oturum.istekler) == 2


def test_google_dokumani_pdf_olarak_disari_aktarilir(tmp_path):
    oturum = SahteOturum({
        "https://docs.google.com/document/d/1ZyXwVuTsRqPoNmLkJiHgFeDcBa98765/export?format=pdf":
            SahteYanit(200, PDF, {"Content-Type": "application/pdf"})})
    sonuc = ek_indir(oturum, _kayit(DOCS_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and sonuc.uzanti == ".pdf"


@pytest.mark.parametrize("govde,uzanti,mime", [
    (docx_bayt(["Soru 1"]), ".docx", DOCX_MIME),
    (bytes.fromhex("89504e470d0a1a0a") + b"0" * 64, ".png", "image/png"),
    (bytes.fromhex("ffd8ffe0") + b"0" * 64, ".jpg", "image/jpeg"),
    (b"GIF89a" + b"0" * 64, ".gif", "image/gif"),
    (b"bilinmeyen ikili veri", ".bin", "application/octet-stream"),
])
def test_tur_basliktan_degil_baytlardan_okunur(tmp_path, govde, uzanti, mime):
    yanit = SahteYanit(200, govde, {"Content-Type": "application/pdf"})
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert (sonuc.durum, sonuc.uzanti, sonuc.mime) == ("indirildi", uzanti, mime)
    assert (tmp_path / f"{ek_kimligi(SP_URL)}{uzanti}").is_file()


@pytest.mark.parametrize("kod,durum", [(403, "erisilemedi"), (404, "erisilemedi"), (503, "hata")])
def test_http_hatalari(tmp_path, kod, durum):
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(kod, b"")}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == durum and str(kod) in sonuc.neden


def test_ag_hatasi_hata_olur_istisna_kacmaz(tmp_path):
    def kopuk(u, h):
        raise requests.ConnectionError("bağlantı koptu")
    sonuc = ek_indir(SahteOturum({SP: kopuk}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and "ConnectionError" in sonuc.neden


def test_baglanti_indirilmez(tmp_path):
    kayit = {"id": "0" * 16, "url": "https://www.youtube.com/watch?v=x", "type": "baglanti"}
    sonuc = ek_indir(SahteOturum({}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "erisilemedi"


def test_300_mb_ustu_govdesi_okunmadan_reddedilir(tmp_path):
    def patla():
        raise AssertionError("gövde okunmamalıydı")
    yanit = SahteYanit(200, headers={"Content-Type": "application/pdf",
                                     "Content-Length": str(EK_BOYUT_SINIRI + 1)}, bloklar=[patla])
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz())
    assert EK_BOYUT_SINIRI == 300 * MB
    assert sonuc.durum == "cok_buyuk" and "300 MB" in sonuc.neden
    assert yanit.kapandi


def test_uzunluk_bildirmeyen_akis_sinirda_kesilir_parca_silinir(tmp_path):
    yanit = SahteYanit(200, headers={"Content-Type": "application/pdf"},
                       bloklar=_bol(PDF + b"0" * (4 * MB)))
    sonuc = ek_indir(SahteOturum({SP: yanit}), _kayit(SP_URL), tmp_path, _sinirsiz(), sinir=3 * MB)
    assert sonuc.durum == "cok_buyuk" and _parcalar(tmp_path) == []


def test_bayt_butcesi_dolunca_parca_kalir_sonraki_tur_range_ile_surer(tmp_path):
    govde = PDF + bytes(range(256)) * (4 * 4096)          # ~4 MB after a PDF head
    kayit = _kayit(SP_URL)
    oturum = SahteOturum({SP: aralikli(govde)})
    ilk = ek_indir(oturum, kayit, tmp_path, Butce(float("inf"), 2 * MB))
    assert ilk.durum == "bekliyor" and ilk.parca_bayt == 2 * MB
    assert "Range" not in oturum.istekler[0]["headers"]
    ikinci = ek_indir(oturum, kayit, tmp_path, Butce(float("inf"), 100 * MB))
    assert ikinci.durum == "indirildi"
    assert oturum.istekler[1]["headers"]["Range"] == f"bytes={2 * MB}-"
    assert (tmp_path / ikinci.dosya).read_bytes() == govde
    assert ikinci.sha256 == hashlib.sha256(govde).hexdigest() and _parcalar(tmp_path) == []


def test_sure_butcesi_dolunca_da_durur(tmp_path):
    butce = Butce(son_an=3.5, bayt=10 ** 12, saat=SahteSaat(adim=1.0))
    govde = PDF + b"0" * (5 * MB)
    sonuc = ek_indir(SahteOturum({SP: aralikli(govde)}), _kayit(SP_URL), tmp_path, butce)
    assert sonuc.durum == "bekliyor" and 0 < sonuc.parca_bayt < len(govde)


def test_onceki_tur_tam_sonda_durduysa_416_dosyayi_tamamlar(tmp_path):
    kayit = _kayit(SP_URL)
    (tmp_path / ".parca").mkdir(parents=True)
    (tmp_path / ".parca" / f"{kayit['id']}.part").write_bytes(PDF)
    sonuc = ek_indir(SahteOturum({SP: aralikli(PDF)}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == PDF


def test_uyusmayan_aralik_parcayi_atar(tmp_path):
    kayit = _kayit(SP_URL)
    (tmp_path / ".parca").mkdir(parents=True)
    (tmp_path / ".parca" / f"{kayit['id']}.part").write_bytes(PDF[:100])
    yanlis = SahteYanit(206, PDF[:100], {"Content-Range": f"bytes 0-99/{len(PDF)}"})
    sonuc = ek_indir(SahteOturum({SP: yanlis}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and _parcalar(tmp_path) == []


def test_range_yok_sayilirsa_bastan_yazilir(tmp_path):
    kayit = _kayit(SP_URL)
    (tmp_path / ".parca").mkdir(parents=True)
    (tmp_path / ".parca" / f"{kayit['id']}.part").write_bytes(b"eski yarim")
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})}),
                     kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "indirildi" and (tmp_path / sonuc.dosya).read_bytes() == PDF


def test_gecersiz_kimlik_dizin_disina_yazmaz(tmp_path):
    """kayit['id'] drives every path ek_indir builds (.parca/<id>.part,
    <id><uzanti>); an unvalidated id can carry `../` — confirmed by direct
    reproduction: sandbox/.parca/../../disari/evil.part's mkdir(parents=True)
    really does create `disari` next to `sandbox`, outside the run's own
    directory. A future caller bug (or an id built by hand instead of
    ek_kimligi()) must be refused before any path is touched, not exploited."""
    disari = tmp_path.parent / "disari-yazilmamali"
    assert not disari.exists()
    kayit = {"id": "../../disari-yazilmamali/evil", "url": SP_URL, "type": ek_turu(SP_URL)}
    sonuc = ek_indir(SahteOturum({SP: SahteYanit(200, PDF, {"Content-Type": "application/pdf"})}),
                     kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "hata" and "kimli" in sonuc.neden.lower()
    assert not disari.exists()
    assert list(tmp_path.iterdir()) == []


def test_bos_kimlik_de_reddedilir(tmp_path):
    kayit = {"id": "", "url": SP_URL, "type": ek_turu(SP_URL)}
    sonuc = ek_indir(SahteOturum({}), kayit, tmp_path, _sinirsiz())
    assert sonuc.durum == "hata"
    assert list(tmp_path.iterdir()) == []


def test_portal_cerezleri_yalniz_portal_istegine_gider(tmp_path):
    kavanoz = portal_cerez_kavanozu([
        {"name": "ASP.NET_SessionId", "value": "ornek-oturum", "domain": "portal.tedronesans.k12.tr", "path": "/"},
        {"name": "izci", "value": "x", "domain": ".google.com", "path": "/"},
    ])
    assert [c.name for c in kavanoz] == ["ASP.NET_SessionId"]
    oturum = SahteOturum({
        "https://portal.tedronesans.k12.tr/": lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
        SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
    })
    ek_indir(oturum, _kayit(PORTAL_URL), tmp_path, _sinirsiz(), cerezler=kavanoz)
    ek_indir(oturum, _kayit(SP_URL), tmp_path, _sinirsiz(), cerezler=kavanoz)
    assert oturum.istekler[0]["cookies"] is kavanoz
    assert oturum.istekler[1]["cookies"] is None
    assert portal_cerez_kavanozu([]) is None and portal_cerez_kavanozu(None) is None
