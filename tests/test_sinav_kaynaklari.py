"""src/sinav_kaynaklari: free-text exam candidates with their source location and
publication date; the free keyword prefilter; the portal's duplicate cards merged."""
import json
from datetime import date

import pytest

from src.sinav_kaynaklari import Aday, adaylar, kaynak_verisi, on_suzgec
from tests.sinav_fikstur import FEN_KARTI, ING_KARTI, KTT_KARTI, haftalar_verisi

BUGUN = date(2026, 10, 16)


@pytest.mark.parametrize("metin", [
    "Matematik KTT konuları", "Büyük Quiz Zamanı!", "Cuma kısa sınav", "SINAV haftası",
    "Türkçe Ortak Yazılı", "Irregular Verbs Quiz", "20 soru test olacaktır", "GİS-1 uygulaması",
    "final exam", "konu tarama testi", "deneme sınavı", "ünite değerlendirme",
    "Matematik yazılısı", "exams next week",
])
def test_on_suzgec_sinav_dili(metin):
    assert on_suzgec(metin)


@pytest.mark.parametrize("metin", [
    "Quizlet için linke tıkla", "Ödev Durumu: Değerlendirilmemiş", "Ders kitabını getirin", "contest",
    "for example, use the verb", "yazılım dersi", "We will examine the text",
])
def test_on_suzgec_sinav_dili_degil(metin):
    assert not on_suzgec(metin)


def test_ktt_kopyalari_tek_aday():
    sonuc = [a for a in adaylar(haftalar_verisi(), BUGUN) if a.ders == "Matematik"]
    assert len(sonuc) == 1
    assert sonuc[0].metin == KTT_KARTI
    assert sonuc[0].tur == "ders_karti"
    assert sonuc[0].yayin == date(2026, 10, 5)
    assert sonuc[0].konumlar == [
        {"bolum": "ders_icerikleri_haftalar", "hafta": "4. Hafta 05 Eki. - 11 Eki.", "ders": "Matematik", "sira": 1},
        {"bolum": "ders_icerikleri_haftalar", "hafta": "5. Hafta 12 Eki. - 18 Eki.", "ders": "Matematik", "sira": 1},
    ]


def test_fen_ogesi_kartin_icinde_kalir():
    fen = [a for a in adaylar(haftalar_verisi(), BUGUN) if a.ders == "Fen Bilimleri"]
    assert [a.metin for a in fen] == [FEN_KARTI]


def test_ders_adi_normalize_ve_quizlet_suzulur():
    sonuc = adaylar(haftalar_verisi(), BUGUN)
    assert {a.ders for a in sonuc} == {"Matematik", "Fen Bilimleri", "İngilizce"}
    ing = next(a for a in sonuc if a.ders == "İngilizce")
    assert ing.metin == ING_KARTI and ing.yayin == date(2026, 9, 21)


def test_en_yeni_once_ve_eski_yayin_atlanir():
    sonuc = adaylar(haftalar_verisi(), BUGUN)
    assert [a.yayin for a in sonuc] == sorted([a.yayin for a in sonuc], reverse=True)
    # 2026-11-10 − 45 gün = 2026-09-26: 21.09'daki İngilizce kartı düşer, 05.10'dakiler kalır.
    assert {a.ders for a in adaylar(haftalar_verisi(), date(2026, 11, 10))} == {"Matematik", "Fen Bilimleri"}


def test_imzasiz_kart_hafta_baslangicini_yayin_sayar():
    veri = haftalar_verisi()
    veri["ders_icerikleri_haftalar"]["4. Hafta 05 Eki. - 11 Eki."]["Türkçe"] = {
        "cards": ["Türkçe yazılı sınavı Cuma günü"], "items": [], "text": ""}
    tr = next(a for a in adaylar(veri, BUGUN) if a.ders == "Türkçe")
    assert tr.yayin == date(2026, 10, 5)


def test_kartsiz_sekmenin_metni_aday_kartliysa_degil():
    veri = haftalar_verisi()
    hafta = veri["ders_icerikleri_haftalar"]["4. Hafta 05 Eki. - 11 Eki."]
    hafta["Sosyal Bilgiler"] = {"cards": [], "items": [], "text": "Sosyal yazılı sınavı haftaya"}
    hafta["Matematik"]["text"] = KTT_KARTI + "\nBaşka bir duyuru"
    sonuc = adaylar(veri, BUGUN)
    sosyal = next(a for a in sonuc if a.ders == "Sosyal Bilgiler")
    assert sosyal.konumlar[0]["metin"] is True and sosyal.yayin == date(2026, 10, 5)
    assert [a.metin for a in sonuc if a.ders == "Matematik"] == [KTT_KARTI]


def test_odev_duyuru_ek_adaylari():
    veri = haftalar_verisi()
    veri["odevlerim"]["homework"]["rows"] = [{
        "Ders Adı": "Matematik", "Ödev Başlığı": "KTT Hazırlık", "Ödev Son Teslim Tarihi": "16.10.2026 08:00",
        "detail": {"description": "Cuma günü kısa sınav var.", "attachments": []}}]
    veri["duyurular"]["announcements"] = [{"Başlık": "7. sınıflar deneme sınavı", "Tarih": "10.10.2026",
                                          "Başlık_url": "https://x"}]
    sonuc = adaylar(veri, BUGUN,
                    ek_metinleri={"abc": ("Fen yazılı konuları: Uzay Çağı", date(2026, 10, 10))},
                    odev_ilk_gorulme={"KTT Hazırlık": "2026-10-12T09:00:00"})
    odev = next(a for a in sonuc if a.tur == "odev")
    assert (odev.ders, odev.yayin) == ("Matematik", date(2026, 10, 12))
    assert odev.konumlar == [{"bolum": "odev", "baslik": "KTT Hazırlık", "teslim": "16.10.2026 08:00"}]
    duyuru = next(a for a in sonuc if a.tur == "duyuru")
    assert duyuru.yayin == date(2026, 10, 10) and "https://x" not in duyuru.metin
    ek = next(a for a in sonuc if a.tur == "ek")
    assert (ek.ders, ek.yayin, ek.konumlar) == (None, date(2026, 10, 10), [{"bolum": "ek", "id": "abc"}])


def test_anahtar_katlanmis_metnin_ozeti():
    a = Aday("Matematik  KTT", "Matematik", None, "ders_karti", [])
    b = Aday("MATEMATİK KTT", "Matematik", None, "ders_karti", [])
    assert a.anahtar == b.anahtar and len(a.anahtar) == 64


def test_kaynak_verisi_dosyalardan(tmp_path):
    (tmp_path / "output").mkdir()
    (tmp_path / "content/portal-ekleri").mkdir(parents=True)
    (tmp_path / "output/portal_ekleri.json").write_text(json.dumps(
        {"ekler": {"abc": {"id": "abc", "first_seen": "2026-10-10T08:00:00"},
                   "yok": {"id": "yok", "first_seen": "2026-10-11T08:00:00"}}}), encoding="utf-8")
    (tmp_path / "content/portal-ekleri/abc.txt").write_text("x" * 5000, encoding="utf-8")
    (tmp_path / "output/homework_first_seen.json").write_text('{"Ödev": "2026-10-12T09:00:00"}', encoding="utf-8")
    ekler, ilk = kaynak_verisi(tmp_path)
    assert list(ekler) == ["abc"]
    assert ekler["abc"] == ("x" * 4000, date(2026, 10, 10))
    assert ilk == {"Ödev": "2026-10-12T09:00:00"}


def test_kaynak_verisi_dosya_yoksa_bos(tmp_path):
    assert kaynak_verisi(tmp_path) == ({}, {})


def test_birlestir_en_eski_yayin_alinir():
    """Fix: _birlestir must use earliest non-None yayin, not first copy's.

    When an unsigned card moves from week 4 to week 5, dict iteration may
    hit week 5 first. Without the fix, merged candidate gets week 5's date
    and sorts wrong or survives the 45-day cutoff incorrectly.
    """
    veri = haftalar_verisi()
    # Insert unsigned exam card into week 5 BEFORE week 4 in the dict
    # (dicts maintain insertion order in Python 3.7+)
    veri["ders_icerikleri_haftalar"]["5. Hafta 12 Eki. - 18 Eki."]["Türkçe"] = {
        "cards": ["Türkçe yazılı sınavı Cuma günü"], "items": [], "text": ""}
    veri["ders_icerikleri_haftalar"]["4. Hafta 05 Eki. - 11 Eki."]["Türkçe"] = {
        "cards": ["Türkçe yazılı sınavı Cuma günü"], "items": [], "text": ""}
    sonuc = adaylar(veri, BUGUN)
    tr = next(a for a in sonuc if a.ders == "Türkçe")
    # Must use earliest date (05.10), not the second occurrence (12.10)
    assert tr.yayin == date(2026, 10, 5)
    # Both locations must be preserved
    assert len(tr.konumlar) == 2
    assert {"bolum": "ders_icerikleri_haftalar", "hafta": "4. Hafta 05 Eki. - 11 Eki.", "ders": "Türkçe", "sira": 0} in tr.konumlar
    assert {"bolum": "ders_icerikleri_haftalar", "hafta": "5. Hafta 12 Eki. - 18 Eki.", "ders": "Türkçe", "sira": 0} in tr.konumlar


def test_kaynak_verisi_bad_records_ve_encoding_hatalari(tmp_path):
    """Fix: kaynak_verisi must skip malformed records and encoding errors.

    Non-dict tracker records, invalid UTF-8 files, missing files should be
    skipped without aborting collection.
    """
    (tmp_path / "output").mkdir()
    (tmp_path / "content/portal-ekleri").mkdir(parents=True)

    # Tracker with one string (bad), one dict (good), one dict without file
    (tmp_path / "output/portal_ekleri.json").write_text(json.dumps({
        "ekler": {
            "bad_string": "not a dict",  # Should be skipped
            "good": {"id": "good", "first_seen": "2026-10-10T08:00:00"},
            "bad_encoding": {"id": "bad_encoding", "first_seen": "2026-10-11T08:00:00"},
            "missing": {"id": "missing", "first_seen": "2026-10-12T08:00:00"},
        }
    }), encoding="utf-8")

    # One file with valid UTF-8
    (tmp_path / "content/portal-ekleri/good.txt").write_text("valid text", encoding="utf-8")

    # One file with invalid UTF-8 bytes
    (tmp_path / "content/portal-ekleri/bad_encoding.txt").write_bytes(b"\xff\xfe\xfa")

    # "missing" file doesn't exist

    ekler, ilk = kaynak_verisi(tmp_path)

    # Only the good record should be returned
    assert list(ekler.keys()) == ["good"]
    assert ekler["good"] == ("valid text", date(2026, 10, 10))

    # No exception should have been raised
    (tmp_path / "output/homework_first_seen.json").write_text("{}", encoding="utf-8")
    ekler2, ilk2 = kaynak_verisi(tmp_path)
    assert ekler2 == ekler
