from datetime import datetime, timedelta, timezone

import pytest

from src.assistant_sohbet import GERI_BILDIRIM_KATEGORILERI, SohbetDeposu

ISIK = "student@example.test"
SIMDI = datetime(2026, 10, 8, 9, 0, tzinfo=timezone.utc)  # Perşembe


@pytest.fixture
def depo(tmp_path):
    return SohbetDeposu(tmp_path / "s.sqlite")


def _cevap(depo):
    sid = depo.yarat(ISIK, "genel", SIMDI)
    depo.mesaj_ekle(sid, "user", "soru", "genel", [], SIMDI)
    mid = depo.mesaj_ekle(sid, "assistant", "cevap", "genel", [], SIMDI)
    return sid, mid


def test_kategoriler_sabit():
    assert GERI_BILDIRIM_KATEGORILERI == ("Yanlış bilgi", "Anlamadım", "Seviyeme uygun değil", "Kaynak göstermedi", "Diğer")


def test_yaz_guncelle_oku_sil(depo):
    sid, mid = _cevap(depo)
    assert depo.mesaj_sahibi(mid) == {"mesaj_id": mid, "sohbet_id": sid, "rol": "assistant",
                                      "ogretmen": "genel", "sahip_email": ISIK}
    depo.geri_bildirim_yaz(mid, ISIK, "olumlu", None, "", SIMDI)
    depo.geri_bildirim_yaz(mid, ISIK, "olumsuz", "Anlamadım", "  çok hızlı  ", SIMDI)
    assert depo.geri_bildirimler(sid, ISIK) == {mid: {"deger": "olumsuz", "kategori": "Anlamadım", "metin": "çok hızlı"}}
    assert depo.geri_bildirim_sil(mid, ISIK) is True
    assert depo.geri_bildirim_sil(mid, ISIK) is False
    assert depo.geri_bildirimler(sid, ISIK) == {}


@pytest.mark.parametrize("deger,kategori,metin", [
    ("iyi", None, ""), ("olumlu", "Anlamadım", ""), ("olumsuz", "Başka", ""), ("olumsuz", None, "x" * 501),
])
def test_gecersiz_girdi(depo, deger, kategori, metin):
    _, mid = _cevap(depo)
    with pytest.raises(ValueError):
        depo.geri_bildirim_yaz(mid, ISIK, deger, kategori, metin, SIMDI)


def test_sohbet_silinince_geri_bildirim_gider(depo):
    sid, mid = _cevap(depo)
    depo.geri_bildirim_yaz(mid, ISIK, "olumsuz", "Diğer", "neden", SIMDI)
    depo.sil(sid)
    assert depo.mesaj_sahibi(mid) is None
    assert depo.geri_bildirim_ozeti({ISIK}, SIMDI) == {"hafta": {"olumlu": 0, "olumsuz": 0}, "son_olumsuz": []}


def test_ozet_hafta_ve_son_bes(depo):
    for i in range(7):
        _, mid = _cevap(depo)
        depo.geri_bildirim_yaz(mid, ISIK, "olumsuz", "Yanlış bilgi", f"not {i}", SIMDI + timedelta(minutes=i))
    _, mid = _cevap(depo)
    depo.geri_bildirim_yaz(mid, ISIK, "olumlu", None, "", SIMDI)
    _, eski = _cevap(depo)
    depo.geri_bildirim_yaz(eski, ISIK, "olumsuz", "Diğer", "geçen hafta", SIMDI - timedelta(days=7))
    ozet = depo.geri_bildirim_ozeti({ISIK}, SIMDI)
    assert ozet["hafta"] == {"olumlu": 1, "olumsuz": 7}
    assert [n["metin"] for n in ozet["son_olumsuz"]] == ["not 6", "not 5", "not 4", "not 3", "not 2"]
    assert ozet["son_olumsuz"][0]["kategori"] == "Yanlış bilgi"
    assert depo.geri_bildirim_ozeti({"baska@example.test"}, SIMDI)["hafta"] == {"olumlu": 0, "olumsuz": 0}
