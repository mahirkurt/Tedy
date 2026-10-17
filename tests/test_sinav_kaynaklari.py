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


def test_en_yeni_once_ve_eski_yayin_aday_kalir():
    sonuc = adaylar(haftalar_verisi(), BUGUN)
    assert [a.yayin for a in sonuc] == sorted([a.yayin for a in sonuc], reverse=True)
    # An exam announced early (21.09 for a date weeks ahead) must stay a candidate however old the
    # post is: the age limit only bounds new model calls (SinavCikarici), never the cached findings.
    assert {a.ders for a in adaylar(haftalar_verisi(), date(2026, 11, 10))} == \
        {"Matematik", "Fen Bilimleri", "İngilizce"}


def test_yas_suzgeci_yalniz_acikca_istenirse():
    eski = adaylar(haftalar_verisi(), date(2026, 11, 10), en_eski_gun=45)
    assert {a.ders for a in eski} == {"Matematik", "Fen Bilimleri"}


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
        {"ekler": {"0123456789abcdef": {"id": "0123456789abcdef", "first_seen": "2026-10-10T08:00:00"},
                   "fedcba9876543210": {"id": "fedcba9876543210", "first_seen": "2026-10-11T08:00:00"}}}),
        encoding="utf-8")
    (tmp_path / "content/portal-ekleri/0123456789abcdef.txt").write_text("x" * 5000, encoding="utf-8")
    (tmp_path / "output/homework_first_seen.json").write_text('{"Ödev": "2026-10-12T09:00:00"}', encoding="utf-8")
    ekler, ilk = kaynak_verisi(tmp_path)
    assert list(ekler) == ["0123456789abcdef"]
    assert ekler["0123456789abcdef"] == ("x" * 4000, date(2026, 10, 10))
    assert ilk == {"Ödev": "2026-10-12T09:00:00"}


def test_kaynak_verisi_dosya_yoksa_bos(tmp_path):
    assert kaynak_verisi(tmp_path) == ({}, {})


def test_birlestir_en_eski_yayin_alinir():
    """Fix: _birlestir must use earliest non-None yayin, not first copy's.

    Dict iteration order matters: if week 5 is iterated before week 4, the
    old code (keeping first copy's yayin) would set 2026-10-12 instead of
    2026-10-05, causing incorrect sorting and 45-day cutoff behavior.
    """
    veri = haftalar_verisi()
    # Rebuild ders_icerikleri_haftalar dict to have week 5 BEFORE week 4
    # (dicts maintain insertion order in Python 3.7+)
    old_haftalar = veri["ders_icerikleri_haftalar"]
    new_haftalar = {}
    # Add week 5 first (with unsigned Türkçe card)
    new_haftalar["5. Hafta 12 Eki. - 18 Eki."] = {
        "Türkçe": {"cards": ["Türkçe yazılı sınavı Cuma günü"], "items": [], "text": ""}}
    # Then add other weeks in original order (except week 5)
    for week, content in old_haftalar.items():
        if week != "5. Hafta 12 Eki. - 18 Eki.":
            if week == "4. Hafta 05 Eki. - 11 Eki.":
                # Add unsigned Türkçe card to week 4 too
                new_haftalar[week] = dict(content)
                new_haftalar[week]["Türkçe"] = {"cards": ["Türkçe yazılı sınavı Cuma günü"], "items": [], "text": ""}
            else:
                new_haftalar[week] = content
    veri["ders_icerikleri_haftalar"] = new_haftalar

    sonuc = adaylar(veri, BUGUN)
    tr = next(a for a in sonuc if a.ders == "Türkçe")
    # Must use earliest date (05.10), not the first-iterated occurrence (12.10)
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
            "aaaaaaaaaaaaaaaa": "not a dict",  # Should be skipped
            "bbbbbbbbbbbbbbbb": {"id": "bbbbbbbbbbbbbbbb", "first_seen": "2026-10-10T08:00:00"},
            "cccccccccccccccc": {"id": "cccccccccccccccc", "first_seen": "2026-10-11T08:00:00"},
            "dddddddddddddddd": {"id": "dddddddddddddddd", "first_seen": "2026-10-12T08:00:00"},
        }
    }), encoding="utf-8")

    # One file with valid UTF-8
    (tmp_path / "content/portal-ekleri/bbbbbbbbbbbbbbbb.txt").write_text("valid text", encoding="utf-8")

    # One file with invalid UTF-8 bytes
    (tmp_path / "content/portal-ekleri/cccccccccccccccc.txt").write_bytes(b"\xff\xfe\xfa")

    # "dddddddddddddddd" file doesn't exist

    ekler, ilk = kaynak_verisi(tmp_path)

    # Only the good record should be returned
    assert list(ekler.keys()) == ["bbbbbbbbbbbbbbbb"]
    assert ekler["bbbbbbbbbbbbbbbb"] == ("valid text", date(2026, 10, 10))

    # No exception should have been raised
    (tmp_path / "output/homework_first_seen.json").write_text("{}", encoding="utf-8")
    ekler2, ilk2 = kaynak_verisi(tmp_path)
    assert ekler2 == ekler


def test_odev_gecen_yilin_ilk_gorulmesi_yayin_sayilmaz():
    """homework_first_seen.json is keyed by title: last year's "Quiz" must not date this year's."""
    veri = haftalar_verisi()
    veri["odevlerim"]["homework"]["rows"] = [
        {"Ders Adı": "Matematik", "Ödev Başlığı": "Quiz", "Ödev Son Teslim Tarihi": "",
         "detail": {"description": "Cuma günü quiz var."}},
        {"Ders Adı": "Fen Bilimleri", "Ödev Başlığı": "Fen quiz", "Ödev Son Teslim Tarihi": "",
         "detail": {"description": "Fen quiz Cuma."}}]
    sonuc = adaylar(veri, BUGUN, odev_ilk_gorulme={"Quiz": "2026-03-02T09:00:00",
                                                   "Fen quiz": "2026-09-02T09:00:00"})
    odevler = {a.ders: a.yayin for a in sonuc if a.tur == "odev"}
    assert odevler == {"Matematik": None, "Fen Bilimleri": date(2026, 9, 2)}


def test_kaynak_verisi_ek_kimligi_desene_uymazsa_atlanir(tmp_path):
    """The tracker key becomes a path: only portal_ekleri's own id shape (16 hex) is read."""
    (tmp_path / "output").mkdir()
    (tmp_path / "content/portal-ekleri").mkdir(parents=True)
    (tmp_path / "content/gizli.txt").write_text("Fen sınavı yarın", encoding="utf-8")
    (tmp_path / "content/portal-ekleri/ABCDEF0123456789.txt").write_text("Fen sınavı yarın", encoding="utf-8")
    (tmp_path / "output/portal_ekleri.json").write_text(json.dumps({"ekler": {
        "../gizli": {"first_seen": "2026-10-10T08:00:00"},
        "ABCDEF0123456789": {"first_seen": "2026-10-10T08:00:00"},     # upper case: not ours
    }}), encoding="utf-8")
    ekler, _ = kaynak_verisi(tmp_path)
    assert ekler == {}
