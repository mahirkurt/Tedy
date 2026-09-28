"""One attachment sync run (plan 2026-09-28-portal-ekleri, Görev 6): idempotent,
retrying, budgeted, text extracted once into <id>.txt with a .meta.json sidecar.
Fake HTTP only (tests/sahte_http.py)."""
import json
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import src.portal_ekleri_indir as indir_modulu
from src.portal_ekleri import EkDeposu, METIN_ONEKI, ek_kimligi
from src.portal_ekleri_indir import (MB, METIN_SURE_TAVANI, Butce, Sonuc, ekleri_esitle,
                                     metin_cikar)
from tests.sahte_http import (DRIVE_URL, GIRIS_DUVARI, PDF, SP_DUVAR_URL, SP_URL, YOUTUBE,
                              SahteOturum, SahteYanit, aralikli, docx_bayt)

AN = datetime(2026, 9, 28, 10, 0, 0)
SP = "https://ornekokul-my.sharepoint.com/"


def _odev(ekler):
    return {"Ders Adı": "Sosyal Bilgiler", "Ödev Başlığı": "Kitap okuma ödevi",
            "Ödev Son Teslim Tarihi": "25.09.2026 12:00",
            "detail": {"description": "Sayfa 12-13", "attachments": ekler}}


VERI = {
    "odevlerim": {"homework": {"rows": [_odev([{"name": "Sayfa 12-13.pdf", "url": SP_URL},
                                               {"name": "Konu videosu", "url": YOUTUBE}])]}},
    "ek_sayfalar": {"mla_kaynakca": {"title": "MLA Kaynakça Hazırlama Rehberi", "empty": False,
                                     "documents": [DRIVE_URL]}},
}


def _rotalar():
    return {SP: lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/pdf"}),
            "https://drive.google.com/uc?": lambda u, h: SahteYanit(200, PDF, {"Content-Type": "application/octet-stream"})}


def _metin(yol, sure):
    return "var", "Soru 1: Bumerang kitabının 12. sayfasını oku."


def _butce(bayt=100 * MB):
    return Butce(float("inf"), bayt)


def _esitle(tmp_path, oturum, veri=VERI, an=AN, butce=None, cikarici=_metin):
    return ekleri_esitle(tmp_path, veri, oturum, butce or _butce(), simdi=lambda: an,
                         metin_cikarici=cikarici)


def test_ilk_tur_indirir_izleyici_tasarimin_alanlarini_tutar(tmp_path):
    oturum = SahteOturum(_rotalar())
    ozet = _esitle(tmp_path, oturum)
    depo = EkDeposu(tmp_path)
    ekler = depo.oku()
    sp = ekler[ek_kimligi(SP_URL)]
    for alan in ("url", "id", "name", "type", "size", "sha256", "source", "status", "reason", "fetched_at"):
        assert alan in sp, alan
    assert (sp["status"], sp["type"], sp["size"], sp["text"]) == ("indirildi", "sharepoint", len(PDF), "var")
    assert sp["source"] == {"section": "odevler",
                            "item": "Sosyal Bilgiler|Kitap okuma ödevi|25.09.2026 12:00",
                            "title": "Kitap okuma ödevi", "course": "Sosyal Bilgiler"}
    assert ekler[ek_kimligi(YOUTUBE)]["status"] == "baglanti"
    assert ekler[ek_kimligi(DRIVE_URL)]["source"]["section"] == "ek_sayfalar"
    metin = depo.metin_yolu(sp["id"]).read_text(encoding="utf-8")
    assert metin.startswith(f"{METIN_ONEKI}Sayfa 12-13.pdf · Kitap okuma ödevi · Sosyal Bilgiler\n\n")
    assert "Bumerang" in metin
    assert depo.meta(sp["id"]) == {"id": sp["id"], "name": "Sayfa 12-13.pdf", "title": "Kitap okuma ödevi",
                                   "section": "odevler", "course": "Sosyal Bilgiler"}
    assert (ozet["bu_tur_indirilen"], ozet["indirildi"], ozet["baglanti"], ozet["kalan_is"]) == (2, 2, 1, 0)
    assert all("youtube" not in i["url"] for i in oturum.istekler)


def test_ikinci_tur_hicbir_istek_yapmaz(tmp_path):
    oturum = SahteOturum(_rotalar())
    _esitle(tmp_path, oturum)
    n = len(oturum.istekler)
    ozet = _esitle(tmp_path, oturum, an=AN + timedelta(minutes=15))
    assert len(oturum.istekler) == n and ozet["bu_tur_indirilen"] == 0


def test_hata_sonraki_turda_yeniden_denenir(tmp_path):
    cevaplar = [SahteYanit(503, b""), SahteYanit(200, PDF, {"Content-Type": "application/pdf"})]
    oturum = SahteOturum({SP: lambda u, h: cevaplar.pop(0)})
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL}])]}}}
    _esitle(tmp_path, oturum, veri)
    assert EkDeposu(tmp_path).kayit(ek_kimligi(SP_URL))["status"] == "hata"
    _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15))
    kayit = EkDeposu(tmp_path).kayit(ek_kimligi(SP_URL))
    assert kayit["status"] == "indirildi" and kayit["attempts"] == 2


def test_erisilemeyen_24_saat_bekler(tmp_path):
    duvar = SahteYanit(200, GIRIS_DUVARI, {"Content-Type": "text/html"}, url="https://login.microsoftonline.com/x")
    oturum = SahteOturum({SP: lambda u, h: duvar})
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "b.pdf", "url": SP_DUVAR_URL}])]}}}
    _esitle(tmp_path, oturum, veri)
    kayit = EkDeposu(tmp_path).kayit(ek_kimligi(SP_DUVAR_URL))
    assert kayit["status"] == "erisilemedi" and "giriş istiyor" in kayit["reason"]
    assert kayit["next_attempt"] == (AN + timedelta(hours=24)).isoformat(timespec="seconds")
    _esitle(tmp_path, oturum, veri, an=AN + timedelta(hours=1))
    assert len(oturum.istekler) == 1
    _esitle(tmp_path, oturum, veri, an=AN + timedelta(hours=25))
    assert len(oturum.istekler) == 2


def test_butce_tukenince_kalan_sonraki_tura_kalir(tmp_path):
    govde = PDF + b"0" * (3 * MB)
    ikinci = SP_URL.replace("EaBcDe", "EkInCi")
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL},
                                                       {"name": "b.pdf", "url": ikinci}])]}}}
    oturum = SahteOturum({SP: aralikli(govde)})
    ozet = _esitle(tmp_path, oturum, veri, butce=_butce(4 * MB))
    durumlar = sorted(k["status"] for k in EkDeposu(tmp_path).oku().values())
    assert durumlar == ["bekliyor", "indirildi"] and ozet["kalan_is"] >= 1
    ozet = _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15))
    assert sorted(k["status"] for k in EkDeposu(tmp_path).oku().values()) == ["indirildi", "indirildi"]
    assert any(i["headers"].get("Range") for i in oturum.istekler)
    assert ozet["kalan_is"] == 0


def test_silinen_kopya_yeniden_indirilir(tmp_path):
    oturum = SahteOturum(_rotalar())
    _esitle(tmp_path, oturum)
    depo = EkDeposu(tmp_path)
    depo.dosya_yolu(depo.kayit(ek_kimligi(SP_URL))).unlink()
    n = len(oturum.istekler)
    _esitle(tmp_path, oturum, an=AN + timedelta(minutes=15))
    assert len(oturum.istekler) == n + 1
    assert depo.dosya_yolu(depo.kayit(ek_kimligi(SP_URL))) is not None


def test_metin_cikarma_hatasi_uc_denemede_durur(tmp_path):
    cagrilar = []

    def bozuk(yol, sure):
        cagrilar.append(yol.name)
        return "hata", ""
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL}])]}}}
    oturum = SahteOturum(_rotalar())
    for i in range(5):
        _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15 * i), cikarici=bozuk)
    assert len(cagrilar) == 3
    kayit = EkDeposu(tmp_path).kayit(ek_kimligi(SP_URL))
    assert kayit["text"] == "hata" and not EkDeposu(tmp_path).metin_yolu(kayit["id"]).exists()


def test_metin_katmani_yoksa_baslik_ve_not_yazilir(tmp_path):
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "tarama.pdf", "url": SP_URL}])]}}}
    _esitle(tmp_path, SahteOturum(_rotalar()), veri, cikarici=lambda y, s: ("yok", ""))
    depo = EkDeposu(tmp_path)
    metin = depo.metin_yolu(ek_kimligi(SP_URL)).read_text(encoding="utf-8")
    assert metin.startswith(METIN_ONEKI) and "Metin katmanı yok" in metin


def test_gercek_metin_cikarici(tmp_path, monkeypatch):
    monkeypatch.setenv("ASSISTANT_ENABLE_OCR", "0")
    docx = tmp_path / "a.docx"
    docx.write_bytes(docx_bayt(["Bumerang kitabı", "Soru 1"]))
    assert metin_cikar(docx, 30) == ("var", "Bumerang kitabı\n\nSoru 1")
    ikili = tmp_path / "b.bin"
    ikili.write_bytes(b"xx")
    assert metin_cikar(ikili, 30) == ("desteklenmiyor", "")
    gorsel = tmp_path / "c.png"
    gorsel.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"0" * 32)
    assert metin_cikar(gorsel, 30) == ("yok", "")


# ── Beyond the brief: the bounds the run relies on, each exercised for real ──

def _iki_ek():
    ikinci = SP_URL.replace("EaBcDe", "EkInCi")
    return ikinci, {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL},
                                                               {"name": "b.pdf", "url": ikinci}])]}}}


def test_bekliyor_donen_indirmeden_sonra_tur_durur(tmp_path, monkeypatch):
    """ek_indir answers `bekliyor` when it abandoned a request thread or cut a
    socket at the budget's end; that thread may still be inside the shared
    requests.Session (not thread-safe). No second download may start on the
    session this run, even if the budget, read a moment later, looks open."""
    cagrilar = []

    def sahte_indir(oturum, kayit, dizin, butce, cerezler=None):
        cagrilar.append(kayit["id"])
        return Sonuc("bekliyor", "bu turun bütçesi doldu", parca_bayt=10)
    monkeypatch.setattr(indir_modulu, "ek_indir", sahte_indir)
    ikinci, veri = _iki_ek()
    butce = _butce()
    ozet = _esitle(tmp_path, SahteOturum({}), veri, butce=butce)
    assert not butce.bitti()
    assert len(cagrilar) == 1
    ekler = EkDeposu(tmp_path).oku()
    assert sorted(k["attempts"] for k in ekler.values()) == [0, 1]
    assert ozet["kalan_is"] == 2


def test_asili_istek_turu_butcede_bitirir_ve_ikinci_istek_yapilmaz(tmp_path):
    """A host that never answers: the whole run returns at the budget's end
    (the request thread is abandoned, not waited for) and the next
    attachment is never requested on the same session."""
    serbest = threading.Event()

    def asili(url, headers):
        serbest.wait(20)
        return SahteYanit(200, PDF, {"Content-Type": "application/pdf"})
    oturum = SahteOturum({SP: asili})
    _, veri = _iki_ek()
    try:
        bas = time.monotonic()
        ozet = _esitle(tmp_path, oturum, veri, butce=Butce(time.monotonic() + 0.5, 100 * MB))
        gecen = time.monotonic() - bas
    finally:
        serbest.set()
    # Unbounded, the host holds the run for its full 20 s; bounded, it ends
    # at the 0.5 s budget. 8 s separates the two even at load 9.
    assert gecen < 8.0, gecen
    assert len(oturum.istekler) == 1
    assert ozet["bekliyor"] == 2 and ozet["bu_tur_indirilen"] == 0


def test_butce_bitmisse_hic_istek_yapilmaz(tmp_path):
    oturum = SahteOturum(_rotalar())
    ozet = _esitle(tmp_path, oturum, butce=_butce(0))
    assert oturum.istekler == []
    assert ozet["bekliyor"] == 2 and ozet["kalan_is"] == 2


def test_metin_suresi_butcenin_kalanidir(tmp_path):
    sureler = []

    def olcen(yol, sure):
        sureler.append(sure)
        return "var", "metin"
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL}])]}}}
    _esitle(tmp_path, SahteOturum(_rotalar()), veri, cikarici=olcen)
    ekleri_esitle(tmp_path / "iki", veri, SahteOturum(_rotalar()), Butce(time.monotonic() + 40, 100 * MB),
                  simdi=lambda: AN, metin_cikarici=olcen)
    assert sureler[0] == METIN_SURE_TAVANI
    assert 0 < sureler[1] <= 40


def test_butcenin_sonunda_kesilen_metin_deneme_sayilmaz(tmp_path):
    """A timeout forced by this run's end, on less than METIN_ADIL_SURE (60 s)
    of time, says nothing about the file: it is not one of the
    METIN_DENEME_SINIRI attempts, and the next run retries."""
    saat = [0.0]

    def uzun(yol, sure):
        saat[0] = 1000.0          # the extraction ran to the budget's end
        return "hata", ""
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL}])]}}}
    _esitle(tmp_path, SahteOturum(_rotalar()), veri, butce=Butce(30.0, 100 * MB, saat=lambda: saat[0]),
            cikarici=uzun)
    depo = EkDeposu(tmp_path)
    kayit = depo.kayit(ek_kimligi(SP_URL))
    assert kayit["status"] == "indirildi"
    assert kayit["text"] == "bekliyor" and int(kayit.get("text_attempts") or 0) == 0
    assert not depo.metin_yolu(kayit["id"]).exists()
    ozet = _esitle(tmp_path, SahteOturum(_rotalar()), veri, an=AN + timedelta(minutes=15))
    assert depo.kayit(kayit["id"])["text"] == "var" and ozet["bu_tur_metin"] == 1


def test_metin_cikarici_istisnasi_turu_durdurmaz(tmp_path):
    def patlayan(yol, sure):
        raise RuntimeError("beklenmeyen")
    _, veri = _iki_ek()
    ozet = _esitle(tmp_path, SahteOturum(_rotalar()), veri, cikarici=patlayan)
    ekler = EkDeposu(tmp_path).oku()
    assert ozet["bu_tur_indirilen"] == 2
    assert [(k["text"], k["text_attempts"]) for k in ekler.values()] == [("hata", 1), ("hata", 1)]


def test_izleyicideki_kimlik_anahtardan_gelir(tmp_path):
    """A tracker record's `id` field is never trusted for a path: the key
    (checked against KIMLIK_DESENI by EkDeposu.oku) is the id."""
    kimlik = ek_kimligi(SP_URL)
    kok = tmp_path / "kok"            # content/portal-ekleri/../../../ is tmp_path
    depo = EkDeposu(kok)
    depo.yaz({kimlik: {"id": "../../../kacak-g6", "status": "bekliyor", "attempts": 0, "text": ""}})
    veri = {"odevlerim": {"homework": {"rows": [_odev([{"name": "a.pdf", "url": SP_URL}])]}}}
    _esitle(kok, SahteOturum(_rotalar()), veri)
    kayit = depo.kayit(kimlik)
    assert kayit["id"] == kimlik and kayit["status"] == "indirildi"
    assert depo.metin_yolu(kimlik).exists() and depo.meta(kimlik)["id"] == kimlik
    assert not list(tmp_path.rglob("*kacak-g6*"))


def test_yan_dosyalar_gecici_dosya_birakmaz(tmp_path):
    _esitle(tmp_path, SahteOturum(_rotalar()))
    depo = EkDeposu(tmp_path)
    adlar = sorted(y.name for y in depo.dizin.iterdir() if y.is_file())
    assert not [a for a in adlar if a.endswith(".tmp") or a.startswith(".")]
    kimlik = ek_kimligi(SP_URL)
    assert {f"{kimlik}.pdf", f"{kimlik}.txt", f"{kimlik}.meta.json"} <= set(adlar)


# ── metin_cikar: pdftotext is a child process bounded by the wall clock ──

def _sahte_pdftotext(tmp_path, monkeypatch, govde):
    """A shell script named pdftotext, first on PATH: the real subprocess
    mechanism runs, only the program is a stand-in."""
    bin_dizini = tmp_path / "bin"
    bin_dizini.mkdir(exist_ok=True)
    betik = bin_dizini / "pdftotext"
    betik.write_text("#!/bin/sh\n" + govde, encoding="utf-8")
    betik.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dizini}{os.pathsep}{os.environ.get('PATH', '')}")
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(PDF)
    return pdf


def _yasiyor(pid):
    try:
        durum = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except OSError:
        return False
    return "\nState:\tZ" not in durum


def test_yavas_pdftotext_sureyle_kesilir_torunu_da_olur(tmp_path, monkeypatch):
    pid_dosyasi = tmp_path / "torun.pid"
    pdf = _sahte_pdftotext(tmp_path, monkeypatch,
                           f"sleep 30 &\necho $! > '{pid_dosyasi}'\nprintf 'yarim metin'\nsleep 30\n")
    bas = time.monotonic()
    sonuc = metin_cikar(pdf, 1.0)
    gecen = time.monotonic() - bas
    assert sonuc[0] == "hata" and "süre" in sonuc[1]
    assert 0.9 <= gecen < 10.0, gecen          # unbounded: 30 s
    torun = int(pid_dosyasi.read_text().strip())
    son = time.monotonic() + 10
    while _yasiyor(torun) and time.monotonic() < son:
        time.sleep(0.05)
    assert not _yasiyor(torun)


def test_sure_yuvarlanmaz_ve_sisirilmez(tmp_path, monkeypatch):
    """The brief passed max(5, int(sure)): 0.3 s left became 5 s."""
    pdf = _sahte_pdftotext(tmp_path, monkeypatch, "sleep 30\n")
    bas = time.monotonic()
    assert metin_cikar(pdf, 0.3)[0] == "hata"
    assert time.monotonic() - bas < 3.0        # the plan's version: 5 s
    assert metin_cikar(pdf, 0.0)[0] == "hata"


def test_pdftotext_ciktisi_tavanda_kesilir(tmp_path, monkeypatch):
    monkeypatch.setattr(indir_modulu, "METIN_AZAMI_BAYT", 4096)
    pdf = _sahte_pdftotext(tmp_path, monkeypatch, "exec yes Bumerang\n")
    bas = time.monotonic()
    durum, metin = metin_cikar(pdf, 30.0)
    assert time.monotonic() - bas < 15.0       # uncapped: the 30 s timeout
    # One byte past the cap is kept, so _metni_hazirla can tell it was cut.
    assert durum == "var" and metin.startswith("Bumerang") and 4096 < len(metin.encode()) <= 4097


@pytest.mark.parametrize("govde, beklenen", [
    ("printf 'Soru 1\\fSoru 2\\n'\n", ("var", "Soru 1\fSoru 2")),
    ("printf '  \\n\\f'\n", ("yok", "")),
    ("echo bozuk >&2\nexit 1\n", ("hata", "PDF okunamadı (bozuk ya da şifreli)")),
])
def test_pdftotext_sonucu(tmp_path, monkeypatch, govde, beklenen):
    pdf = _sahte_pdftotext(tmp_path, monkeypatch, govde)
    assert metin_cikar(pdf, 10.0) == beklenen


def test_pdftotext_yoksa_hata(tmp_path, monkeypatch):
    bos = tmp_path / "bos"
    bos.mkdir()
    monkeypatch.setenv("PATH", str(bos))
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(PDF)
    assert metin_cikar(pdf, 10.0) == ("hata", "pdftotext çalıştırılamadı")
    (bos / "timeout").symlink_to(shutil.which("timeout", path=os.defpath) or "/usr/bin/timeout")
    assert metin_cikar(pdf, 10.0) == ("hata", "pdftotext çalıştırılamadı")


def test_gorsel_ocr_acikken_de_okunmaz(tmp_path, monkeypatch):
    """OCR is Görev 14–15; FileAdapters' tesseract call has no time bound."""
    monkeypatch.setenv("ASSISTANT_ENABLE_OCR", "1")
    gorsel = tmp_path / "c.png"
    gorsel.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"0" * 32)
    assert metin_cikar(gorsel, 30) == ("yok", "")


def _pdf(icerik: bytes) -> bytes:
    nesneler = [b"<< /Type /Catalog /Pages 2 0 R >>",
                b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] /Contents 4 0 R"
                b" /Resources << /Font << /F1 5 0 R >> >> >>",
                b"<< /Length %d >>\nstream\n" % len(icerik) + icerik + b"\nendstream",
                b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    govde, ofsetler = b"%PDF-1.4\n", []
    for i, nesne in enumerate(nesneler, 1):
        ofsetler.append(len(govde))
        govde += b"%d 0 obj\n" % i + nesne + b"\nendobj\n"
    xref = len(govde)
    govde += b"xref\n0 %d\n0000000000 65535 f \n" % (len(nesneler) + 1)
    govde += b"".join(b"%010d 00000 n \n" % o for o in ofsetler)
    return govde + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(nesneler) + 1, xref)


@pytest.mark.skipif(shutil.which("pdftotext") is None, reason="poppler pdftotext yok")
def test_gercek_pdftotext(tmp_path):
    metinli = tmp_path / "a.pdf"
    metinli.write_bytes(_pdf(b"BT /F1 18 Tf 20 50 Td (Bumerang sayfa 12) Tj ET"))
    durum, metin = metin_cikar(metinli, 30.0)
    assert durum == "var" and "Bumerang sayfa 12" in metin
    taranmis = tmp_path / "b.pdf"
    taranmis.write_bytes(_pdf(b""))
    assert metin_cikar(taranmis, 30.0) == ("yok", "")


# ── Fix round 1: cross-run starvation, memory, tampered trackers ─────────────

def _veri(*ekler):
    return {"odevlerim": {"homework": {"rows": [_odev([{"name": ad, "url": url} for ad, url in ekler])]}}}


def test_patolojik_pdf_adil_sureden_sonra_deneme_sayilir(tmp_path, monkeypatch):
    """Görev 7 gives min(180 s, …), so `sure` always equals what is left and a
    PDF that never finishes was cut, uncounted, on every run forever. Cut
    after a fair share of time (METIN_ADIL_SURE) it is an attempt."""
    monkeypatch.setattr(indir_modulu, "METIN_ADIL_SURE", 0.3)
    _sahte_pdftotext(tmp_path, monkeypatch, "sleep 1000\n")
    kok = tmp_path / "kok"
    veri = _veri(("a.pdf", SP_URL))
    for i in range(4):
        bas = time.monotonic()
        ozet = ekleri_esitle(kok, veri, SahteOturum(_rotalar()), Butce(time.monotonic() + 1.0, 100 * MB),
                             simdi=lambda i=i: AN + timedelta(minutes=15 * i))
        gecen = time.monotonic() - bas
    kayit = EkDeposu(kok).kayit(ek_kimligi(SP_URL))
    assert (kayit["text"], kayit["text_attempts"]) == ("hata", 3)
    assert "süre" in kayit["text_reason"]
    assert gecen < 0.9 and ozet["bu_tur_metin"] == 0 and ozet["kalan_is"] == 0


def test_kesilen_metin_taze_isin_arkasina_gecer(tmp_path, monkeypatch):
    """Under METIN_ADIL_SURE a cut is not counted, but the PDF it was cut on
    waits behind fresh work instead of eating every run's budget first."""
    _sahte_pdftotext(tmp_path, monkeypatch, "sleep 1000\n")
    kok = tmp_path / "kok"
    ikinci, veri = _iki_ek()
    for i in range(2):
        ekleri_esitle(kok, veri, SahteOturum(_rotalar()), Butce(time.monotonic() + 1.0, 100 * MB),
                      simdi=lambda i=i: AN + timedelta(minutes=15 * i))
    ekler = EkDeposu(kok).oku()
    assert ekler[ek_kimligi(SP_URL)]["text_attempts"] == 0
    assert ekler[ek_kimligi(SP_URL)]["text_cut"] is True
    assert ekler[ek_kimligi(ikinci)]["status"] == "indirildi"


def test_araligi_yok_sayan_buyuk_dosya_kuyrugu_tikamaz(tmp_path):
    """A host that ignores Range restarts at 0 on every run; a file larger
    than one run's byte budget then never finishes and, as a part file,
    went first forever. Two runs without net progress end it."""
    govde = PDF + b"0" * (3 * MB)
    oturum_rotasi = {SP: lambda u, h: SahteYanit(200, govde, {"Content-Type": "application/pdf",
                                                              "Content-Length": str(len(govde))}),
                     "https://drive.google.com/uc?": lambda u, h: SahteYanit(
                         200, PDF, {"Content-Type": "application/octet-stream"})}
    veri = _veri(("a.pdf", SP_URL), ("b.pdf", DRIVE_URL))
    istekler = []
    for i in range(4):
        oturum = SahteOturum(oturum_rotasi)
        _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15 * i), butce=_butce(2 * MB))
        istekler.append([x["url"][:30] for x in oturum.istekler])
    depo = EkDeposu(tmp_path)
    a, b = depo.kayit(ek_kimligi(SP_URL)), depo.kayit(ek_kimligi(DRIVE_URL))
    assert b["status"] == "indirildi"
    assert a["status"] == "cok_buyuk"
    assert a["reason"] == "kaynak sürdürmeyi desteklemiyor ve dosya bir turun bayt bütçesinden büyük"
    assert istekler[3] == []
    assert not (depo.dizin / ".parca" / f"{a['id']}.part").exists()


def test_yavas_ama_ilerleyen_indirme_cok_buyuk_olmaz(tmp_path):
    govde = PDF + b"0" * (5 * MB)
    oturum = SahteOturum({SP: aralikli(govde)})
    veri = _veri(("a.pdf", SP_URL))
    for i in range(4):
        _esitle(tmp_path, oturum, veri, an=AN + timedelta(minutes=15 * i), butce=_butce(2 * MB))
    assert EkDeposu(tmp_path).kayit(ek_kimligi(SP_URL))["status"] == "indirildi"


def _docx_xml(tmp_path, ad, mb):
    import zipfile
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    p = "<w:p><w:r><w:t>Bumerang kitabi sayfa 12 soru</w:t></w:r></w:p>"
    govde = p * ((mb * MB - 200) // len(p))
    yol = tmp_path / ad
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml",
                   f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}"><w:body>{govde}</w:body></w:document>')
    return yol


def test_buyuk_docx_bellek_ve_sureyle_sinirli(tmp_path):
    """Measured on f29062c: 49 MB of document.xml took 4.4 s and 554 MB RSS
    and wrote a 25.7 M-character text. Run in a child so its peak RSS is its
    own (VmHWM: ru_maxrss would carry the forking pytest's peak across
    exec); 30 MB of XML was ~300 MB there, the capped read stays near
    import."""
    import subprocess
    import sys
    yol = _docx_xml(tmp_path, "b.docx", 30)
    betik = ("import json, sys, time\n"
             "from pathlib import Path\n"
             "import src.portal_ekleri_indir as m\n"
             "t = time.monotonic()\n"
             "d, metin = m.metin_cikar(Path(sys.argv[1]), 30.0)\n"
             "hwm = [s for s in open('/proc/self/status') if s.startswith('VmHWM')][0]\n"
             "print(json.dumps([d, metin, time.monotonic() - t, int(hwm.split()[1]) // 1024]))\n")
    kok = Path(indir_modulu.__file__).resolve().parents[1]
    cikti = subprocess.run([sys.executable, "-c", betik, str(yol)], cwd=kok, capture_output=True,
                           text=True, timeout=120, env={**os.environ, "PYTHONPATH": str(kok)})
    durum, neden, gecen, rss_mb = json.loads(cikti.stdout.strip().splitlines()[-1])
    assert durum == "hata" and "8 MB" in neden
    assert rss_mb < 150, rss_mb
    assert gecen < 5.0, gecen


def test_sinirin_altindaki_docx_okunur(tmp_path):
    durum, metin = metin_cikar(_docx_xml(tmp_path, "a.docx", 2), 30.0)
    assert durum == "var" and metin.startswith("Bumerang kitabi sayfa 12 soru")


@pytest.mark.parametrize("ad, govde, neden", [
    ("bozuk.docx", bytes.fromhex("504b0304") + b"bozuk", "bozuk"),
    ("dtd.docx", None, "güvenlik"),
])
def test_bozuk_docx_hata_ve_durust_neden(tmp_path, ad, govde, neden):
    if govde is None:
        import io
        import zipfile
        tampon = io.BytesIO()
        with zipfile.ZipFile(tampon, "w") as z:
            z.writestr("word/document.xml", '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "b">]><x>&a;</x>')
        govde = tampon.getvalue()
    yol = tmp_path / ad
    yol.write_bytes(govde)
    durum, metin = metin_cikar(yol, 30.0)
    assert durum == "hata" and neden in metin


def test_metinsiz_gercek_docx_yok(tmp_path):
    yol = tmp_path / "bos.docx"
    yol.write_bytes(docx_bayt([]))
    assert metin_cikar(yol, 30.0) == ("yok", "")


def test_metin_tavani_her_metne_uygulanir_ve_isaretlenir(tmp_path, monkeypatch):
    monkeypatch.setattr(indir_modulu, "METIN_AZAMI_BAYT", 4096)
    _esitle(tmp_path, SahteOturum(_rotalar()), _veri(("a.pdf", SP_URL)),
            cikarici=lambda y, s: ("var", "Bumerang " * 2000))
    depo = EkDeposu(tmp_path)
    kimlik = ek_kimligi(SP_URL)
    metin = depo.metin_yolu(kimlik).read_text(encoding="utf-8")
    assert "Metin burada kesildi" in metin
    assert len(metin.encode()) < 4096 + 1024
    assert depo.meta(kimlik)["text_truncated"] is True
    assert depo.kayit(kimlik)["text_truncated"] is True


def test_cocuk_cikinca_boruyu_tutan_torun_da_olur(tmp_path, monkeypatch):
    pid_dosyasi = tmp_path / "torun.pid"
    pdf = _sahte_pdftotext(tmp_path, monkeypatch, f"sleep 30 &\necho $! > '{pid_dosyasi}'\nexit 0\n")
    assert metin_cikar(pdf, 1.0)[0] == "hata"
    torun = int(pid_dosyasi.read_text().strip())
    son = time.monotonic() + 10
    while _yasiyor(torun) and time.monotonic() < son:
        time.sleep(0.05)
    assert not _yasiyor(torun)


def test_ebeveyn_olurse_timeout_pdftotexti_sinirlar(tmp_path, monkeypatch):
    """cron's `timeout 600` kills run_sync, not the pdftotext session it
    started; `timeout -s KILL` in front of the command bounds that orphan."""
    import subprocess
    import sys
    pid_dosyasi = tmp_path / "pdftotext.pid"
    pdf = _sahte_pdftotext(tmp_path, monkeypatch, f"echo $$ > '{pid_dosyasi}'\nexec sleep 60\n")
    kok = Path(indir_modulu.__file__).resolve().parents[1]
    betik = ("import sys\nfrom pathlib import Path\nimport src.portal_ekleri_indir as m\n"
             "m.metin_cikar(Path(sys.argv[1]), 1.0)\n")
    ebeveyn = subprocess.Popen([sys.executable, "-c", betik, str(pdf)], cwd=kok,
                               env={**os.environ, "PYTHONPATH": str(kok)})
    son = time.monotonic() + 20
    while not pid_dosyasi.exists() and time.monotonic() < son:
        time.sleep(0.02)
    ebeveyn.kill()
    ebeveyn.wait()
    oksuz = int(pid_dosyasi.read_text().strip())
    son = time.monotonic() + 15            # ceil(1.0) + 1 = 2 s; unbounded: 60 s
    while _yasiyor(oksuz) and time.monotonic() < son:
        time.sleep(0.05)
    assert not _yasiyor(oksuz)


@pytest.mark.parametrize("bozuk", [
    {"status": "bekliyor", "partial_bytes": [1]},
    {"status": "bekliyor", "source": "x"},
    {"status": "erisilemedi", "next_attempt": "2026-09-28T09:00:00+03:00"},
    {"status": "erisilemedi", "next_attempt": "dün"},
    {"status": "bekliyor", "attempts": "x"},
    {"status": "indirildi", "file": "0123456789abcdef.pdf", "text_attempts": "abc", "text": "hata"},
])
def test_bozuk_izleyici_degerleri_turu_dusurmez(tmp_path, bozuk):
    """A record no longer in the scrape keeps whatever the tracker holds, so
    its values are read defensively (probe D on f29062c: four crashes)."""
    depo = EkDeposu(tmp_path)
    eski = "0123456789abcdef"
    depo.dizin.mkdir(parents=True)
    (depo.dizin / f"{eski}.pdf").write_bytes(PDF)
    depo.yaz({eski: dict(bozuk, id=eski, url=DRIVE_URL, type="drive")})
    _esitle(tmp_path, SahteOturum(_rotalar()), _veri(("a.pdf", SP_URL)))
    assert depo.kayit(ek_kimligi(SP_URL))["status"] == "indirildi"


def test_sonu_satir_sonlu_anahtar_okunmaz(tmp_path):
    depo = EkDeposu(tmp_path)
    depo.yaz({"0123456789abcdef\n": {"status": "bekliyor", "url": SP_URL, "type": "sharepoint"}})
    assert depo.oku() == {}
    assert depo.kayit("0123456789abcdef\n") is None and depo.meta("0123456789abcdef\n") == {}


def test_eksik_txt_yeniden_cikarilir(tmp_path):
    cagrilar = []

    def say(yol, sure):
        cagrilar.append(1)
        return "var", "Bumerang"
    veri = _veri(("a.pdf", SP_URL))
    _esitle(tmp_path, SahteOturum(_rotalar()), veri, cikarici=say)
    depo = EkDeposu(tmp_path)
    depo.metin_yolu(ek_kimligi(SP_URL)).unlink()
    ozet = _esitle(tmp_path, SahteOturum(_rotalar()), veri, an=AN + timedelta(minutes=15), cikarici=say)
    assert len(cagrilar) == 2 and ozet["bu_tur_metin"] == 1
    assert depo.metin_yolu(ek_kimligi(SP_URL)).exists()


def test_txt_izinleri_0644(tmp_path):
    _esitle(tmp_path, SahteOturum(_rotalar()), _veri(("a.pdf", SP_URL)))
    depo = EkDeposu(tmp_path)
    assert depo.metin_yolu(ek_kimligi(SP_URL)).stat().st_mode & 0o777 == 0o644
