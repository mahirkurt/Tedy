"""Alıştırma günlüğünün sahipliği, atomik cevapları ve hafta sınırları."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from src.assistant_sohbet import SohbetDeposu


SIMDI = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)
SAHIP = "ogrenci@example.test"
DIGER = "diger@example.test"
SORULAR = [{"tur": "kisa_cevap", "soru": "1/2 + 1/3", "dogru": "5/6",
            "aciklama": "Paydalar eşitlenir."}] * 3


def alistirma(depo, sahip=SAHIP, simdi=SIMDI):
    sid = depo.yarat(sahip, "matematik", simdi)
    aid = depo.alistirma_yaz(sid, sahip, "matematik", "Payda", "Matematik", "Kesir",
                              " ", "orta", SORULAR, simdi)
    return sid, aid


@pytest.fixture
def depo(tmp_path):
    return SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")


def test_kod_null_sorular_sakli_mesaj_bagi_meta_degismez(depo):
    sid, aid = alistirma(depo)
    row = depo.alistirma_getir(aid)
    assert row["kazanim_kodu"] is None and row["mesaj_id"] is None
    assert row["sorular"] == SORULAR
    mid = depo.mesaj_ekle(sid, "assistant", "Alıştırma", "matematik", [], SIMDI)
    depo.alistirma_bagla(aid, mid)
    assert depo.alistirma_getir(aid)["mesaj_id"] == mid
    assert depo.alistirmalar(mid)[0]["id"] == aid
    assert depo.tum_mesajlar(sid)[0]["meta_json"] == "{}"


def test_ikinci_cevap_ilk_sonucu_korur_iki_yazici(depo):
    _, aid = alistirma(depo)
    def yaz(_):
        return SohbetDeposu(depo.yol).cevap_yaz(aid, 1, True, SIMDI)
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(yaz, range(2)))
    assert rows[0]["id"] == rows[1]["id"]
    assert depo.cevap_yaz(aid, 1, False, SIMDI)["dogru"] == 1
    assert len(depo.cevaplar(SAHIP)) == 1
    assert depo.cevaplar(DIGER) == []


def test_gunluk_kendi_haftasi_ve_kendi_puani(depo):
    sid, aid = alistirma(depo)
    _, diger = alistirma(depo, DIGER)
    _, eski = alistirma(depo, simdi=datetime(2026, 9, 27, 20, 59, tzinfo=timezone.utc))
    for sira in range(1, 4):
        depo.cevap_yaz(aid, sira, sira == 1, SIMDI)
    depo.cevap_yaz(diger, 1, True, SIMDI)
    depo.cevap_yaz(eski, 1, True, SIMDI - timedelta(days=7))
    gunluk = depo.gunluk(SAHIP, SIMDI)
    assert gunluk["hafta"] == {"baslangic": "2026-09-28", "sohbet": [{"ogretmen": "matematik", "sayi": 1}],
                                "alistirma": 1, "puan": {"dogru": 1, "toplam": 3}}
    assert gunluk["zayif"][0]["konu"] == "Kesir"
    assert gunluk["zayif"][0]["toplam"] == 4


def test_calisilan_genel_yazmaz_son_bes_ve_degerlendirme_sahibe(depo):
    sid, _ = alistirma(depo)
    mid = depo.mesaj_ekle(sid, "assistant", "Yanıt", "matematik", [], SIMDI)
    for i in range(7):
        depo.calisilan_yaz(sid, mid, SAHIP, "matematik", [
            {"label": f"Kesirler sayfa {i}", "locator": {"tool": "kitap_sayfa"}}],
            SIMDI + timedelta(seconds=i))
    depo.calisilan_yaz(sid, mid, SAHIP, "genel", [{"label": "Görünmez", "locator": {"tool": "kitap_sayfa"}}], SIMDI)
    depo.degerlendirme_yaz(sid, "ab" * 16, "matematik", "Yol açık", "yeterli", "Yeni soru çöz", "ogrenci", SIMDI)
    gunluk = depo.gunluk(SAHIP, SIMDI)
    assert len(gunluk["calisilan"]) == 5
    assert gunluk["calisilan"][0]["sayfa_basligi"] == "Kesirler sayfa 6"
    assert gunluk["degerlendirmeler"][0]["duzeyler"] == "yeterli"
    assert depo.gunluk(DIGER, SIMDI)["degerlendirmeler"] == []


def test_sohbet_silinince_bagli_ogrenme_satirlari_da_silinir(depo):
    sid, aid = alistirma(depo)
    depo.cevap_yaz(aid, 1, True, SIMDI)
    depo.degerlendirme_yaz(sid, "ab" * 16, "matematik", "Yol açık", "yeterli", "Devam", "ogrenci", SIMDI)
    depo.sil(sid)
    assert depo.alistirma_getir(aid) is None
    assert depo.cevaplar(SAHIP) == []
    assert depo.gunluk(SAHIP, SIMDI)["degerlendirmeler"] == []
