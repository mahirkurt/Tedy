"""Alıştırma ve rubrik araçları, gerçek geçici SQLite/ek deposuyla."""
from datetime import datetime, timezone
import json

import pytest

from src.assistant_skills import yukle
from src.assistant_sohbet import SohbetDeposu
from src.assistant_tools import McpRegistry, sinavlar_metni
from src.assistant_uploads import EkDeposu


SIMDI = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
SAHIP = "ogrenci@example.test"
SORU = {"tur": "kisa_cevap", "soru": "1/2 + 1/3", "dogru": "5/6", "aciklama": "Paydalar eşitlenir."}
GOVDE = {"baslik": "Payda", "ders": "Matematik", "konu": "Kesir", "kazanim_kodu": "",
         "zorluk": "orta", "sorular": [SORU] * 3}


@pytest.fixture
def baglam(tmp_path):
    depo = SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")
    sid = depo.yarat(SAHIP, "matematik", SIMDI)
    reg = McpRegistry({}, lambda q, k: [], skills=yukle(), saat=lambda: SIMDI)
    return reg, depo, dict(not_deposu=depo, sohbet_id=sid, sahip_email=SAHIP, okur="ogrenci", ogretmen="matematik")


def test_ilan_depo_sohbet_ve_ogretmen_ister(baglam):
    reg, depo, kw = baglam
    for sid, ogretmen, beklenen in [("", "matematik", set()),
            (kw["sohbet_id"], "genel", {"alistirma_olustur"}),
            (kw["sohbet_id"], "matematik", {"alistirma_olustur", "ogrenme_gunlugu", "calisma_degerlendir"})]:
        adlar = {s["name"] for s in reg.declarations(not_deposu=depo, sohbet_id=sid, ogretmen=ogretmen)}
        assert adlar & {"alistirma_olustur", "ogrenme_gunlugu", "calisma_degerlendir"} == beklenen
    assert "alistirma_olustur" not in {s["name"] for s in reg.declarations(sohbet_id=kw["sohbet_id"])}


def test_quiz_dogru_cevapsiz_ve_tum_kimlikler_istege_eklenir(baglam):
    reg, depo, kw = baglam
    kimlikler = []
    bir = reg.dispatch("alistirma_olustur", GOVDE, **kw, alistirma_kimlikleri=kimlikler)
    iki = reg.dispatch("alistirma_olustur", GOVDE, **kw, alistirma_kimlikleri=kimlikler)
    assert bir.ok and iki.ok
    assert bir.olay["event"] == "quiz" and bir.olay["zorluk"] == "orta"
    assert bir.olay["kazanim_kodu"] is None
    assert bir.olay["sorular"] == [{"tur": "kisa_cevap", "soru": SORU["soru"]}] * 3
    assert not any(s in json.dumps(bir.olay) for s in ("dogru", "aciklama", "kabul_edilenler"))
    assert kimlikler == [bir.olay["id"], iki.olay["id"]]
    assert depo.alistirma_getir(kimlikler[0])["sorular"][0]["dogru"] == "5/6"


@pytest.mark.parametrize("degisiklik", [{"zorluk": None}, {"sorular": [SORU] * 2},
    {"sorular": [{**SORU, "tur": "coktan_secmeli", "secenekler": ["5/6", "1", "2"]}] * 3}])
def test_gecersiz_alistirma_satir_yazmaz(baglam, degisiklik):
    reg, depo, kw = baglam
    assert not reg.dispatch("alistirma_olustur", {**GOVDE, **degisiklik}, **kw).ok
    assert depo.gunluk(SAHIP, SIMDI)["hafta"]["alistirma"] == 0


def test_sohbet_yoksa_ve_baskasinin_sohbetiyse_yazmaz(baglam):
    reg, depo, kw = baglam
    assert not reg.dispatch("alistirma_olustur", GOVDE, **{**kw, "sohbet_id": ""}).ok
    assert not reg.dispatch("alistirma_olustur", GOVDE, **{**kw, "sahip_email": "diger@example.test"}).ok
    assert depo.gunluk(SAHIP, SIMDI)["hafta"]["alistirma"] == 0


def test_gunluk_araci_zayif_ve_calisilan_verir(baglam):
    reg, depo, kw = baglam
    aid = reg.dispatch("alistirma_olustur", GOVDE, **kw).olay["id"]
    for i in range(1, 4):
        depo.cevap_yaz(aid, i, False, SIMDI)
    mid = depo.mesaj_ekle(kw["sohbet_id"], "assistant", "Yanıt", "matematik", [], SIMDI)
    depo.calisilan_yaz(kw["sohbet_id"], mid, SAHIP, "matematik", [{"label": "Kesirler sayfa 12", "locator": {"tool": "kitap_sayfa"}}], SIMDI)
    sonuc = reg.dispatch("ogrenme_gunlugu", {}, **kw)
    assert sonuc.ok and "Kesirler sayfa 12" in sonuc.text and "zayif_konular" in sonuc.text
    assert not reg.dispatch("ogrenme_gunlugu", {}, **{**kw, "ogretmen": "genel"}).ok


def test_degerlendirme_kendi_eki_ve_rubrik_duzeyi_ister(baglam, tmp_path):
    reg, depo, kw = baglam
    ekler = EkDeposu(tmp_path)
    ek = ekler.kaydet(SAHIP, "cozum.txt", "text/plain", 3, b"1+2", SIMDI)
    baska = ekler.kaydet("diger@example.test", "cozum.txt", "text/plain", 3, b"1+2", SIMDI)
    args = {"ek": ek["id"], "guclu_yanlar": "Yol açık", "duzeyler": "yeterli", "sonraki_adim": "Yeni bir örnek çöz"}
    assert reg.dispatch("calisma_degerlendir", args, **kw, yukleme_deposu=ekler).ok
    for degisiklik in [{"duzeyler": "5"}, {"duzeyler": "iyi"}, {"ek": baska["id"]}, {"guclu_yanlar": " "}]:
        assert not reg.dispatch("calisma_degerlendir", {**args, **degisiklik}, **kw, yukleme_deposu=ekler).ok
    assert not reg.dispatch("calisma_degerlendir", args, **{**kw, "ogretmen": "genel"}, yukleme_deposu=ekler).ok
    assert len(depo.gunluk(SAHIP, SIMDI)["degerlendirmeler"]) == 1


def test_sinav_konulari_yalniz_yaklasanlarda_ve_en_fazla_on():
    metin = sinavlar_metni([
        {"course": "Matematik", "status": "upcoming", "relatedContent": [{"title": "Rasyonel sayılar"}, {"title": "Kesirler"}]},
        {"course": "Fen", "status": "upcoming"},
        {"course": "Sosyal", "status": "past", "relatedContent": [{"title": "Eski konu"}]},
    ], SIMDI.replace(tzinfo=None))
    assert "Konular: Rasyonel sayılar; Kesirler" in metin
    assert "Konular: yok" in metin
    assert "Konular:" not in metin.split("GEÇMİŞ SINAVLAR", 1)[1]
    cok = sinavlar_metni([{"course": "Matematik", "status": "upcoming", "relatedContent": [{"title": f"Konu-{i}"} for i in range(12)]}], SIMDI.replace(tzinfo=None))
    assert "Konu-9" in cok and "Konu-10" not in cok
