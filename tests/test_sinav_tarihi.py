"""src/sinav_tarihi: kaynak metindeki sınav zamanını yayın bağlamıyla çözer.
Tarihler 2026-2027 okul yılından; 2026-10-12 pazartesi, 2026-10-16 cuma."""
from datetime import date

from src.sinav_tarihi import (TarihCozumu, hafta_etiketi_araligi, katla, okul_yili, pazartesi,
                              tarih_coz, yayin_tarihi)

YIL = (date(2026, 9, 1), date(2027, 7, 15))


def test_okul_yili_eylulden_temmuza():
    assert okul_yili(date(2026, 10, 16)) == YIL
    assert okul_yili(date(2027, 3, 2)) == YIL
    assert okul_yili(date(2026, 8, 20)) == YIL


def test_pazartesi():
    assert pazartesi(date(2026, 10, 16)) == date(2026, 10, 12)
    assert pazartesi(date(2026, 10, 12)) == date(2026, 10, 12)


def test_katla_turkce_ve_bosluk():
    assert katla("  MATEMATİK  KONU\nTARAMA ") == "matematik konu tarama"
    assert katla("Işık'ın SINAVI") == "isik'in sinavi"


def test_hafta_etiketi_ay_adlarindan_aralik():
    assert hafta_etiketi_araligi("4. Hafta 05 Eki. - 11 Eki.", 2026) == (date(2026, 10, 5), date(2026, 10, 11))


def test_hafta_etiketi_yil_sinirini_asar():
    assert hafta_etiketi_araligi("15. Hafta 28 Ara. - 03 Oca.", 2026) == (date(2026, 12, 28), date(2027, 1, 3))
    assert hafta_etiketi_araligi("19. Hafta 08 Şub. - 14 Şub.", 2026) == (date(2027, 2, 8), date(2027, 2, 14))


def test_hafta_etiketi_okunamazsa_none():
    assert hafta_etiketi_araligi("Bu hafta", 2026) is None


def test_yayin_tarihi_imza_satirindan():
    assert yayin_tarihi("KTT-1 KONULARI\nÖğretmen A | 05.10.2026\nMATEMATİK") == date(2026, 10, 5)
    assert yayin_tarihi("tarihsiz metin") is None


def test_turkce_gun_ay_buyuk_harf():
    c = tarih_coz("15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT", date(2026, 10, 5), YIL)
    assert c == TarihCozumu(gun=date(2026, 10, 15), hafta=None, gecersiz=False)


def test_ay_adi_yilsiz_ocak_sonraki_yila_duser():
    assert tarih_coz("5 Ocak Salı ortak yazılı", date(2026, 12, 20), YIL).gun == date(2027, 1, 5)


def test_sayisal_bicimler():
    assert tarih_coz("Sınav 15.10 tarihinde", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)
    assert tarih_coz("Sınav 15/10'da", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)
    assert tarih_coz("Exam on 15.10.2026", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)


def test_ingilizce_ay_gun():
    assert tarih_coz("The quiz is on October 21st", date(2026, 10, 12), YIL).gun == date(2026, 10, 21)


def test_yayindan_onceki_tarih_gecersiz():
    assert tarih_coz("15 Ekim'de yapılan KTT", date(2026, 10, 16), YIL) == TarihCozumu(None, None, True)


def test_okul_yili_disi_gecersiz():
    c = tarih_coz("Sınav 15.08.2027", date(2026, 10, 1), YIL)
    assert c.gun is None and c.gecersiz


def test_gecersiz_acik_tarih_goreli_ifadeyi_engellemez():
    c = tarih_coz("15 Ekim'deki KTT'nin ardından haftaya yeni quiz", date(2026, 10, 16), YIL)
    assert c == TarihCozumu(None, date(2026, 10, 19), False)


def test_haftaya_ve_next_week_hafta_dondurur():
    assert tarih_coz("Next week, you will have an Irregular Verbs Quiz", date(2026, 9, 21), YIL) \
        == TarihCozumu(None, date(2026, 9, 28), False)
    assert tarih_coz("haftaya kısa sınav var", date(2026, 9, 24), YIL).hafta == date(2026, 9, 28)


def test_bu_hafta():
    c = tarih_coz("Bu hafta ilk ünitemizin tamamını kapsayan bir quiz", date(2026, 10, 5), YIL)
    assert c == TarihCozumu(None, date(2026, 10, 5), False)


def test_haftaya_gun_adi_gun_verir():
    assert tarih_coz("haftaya Salı quiz", date(2026, 10, 7), YIL).gun == date(2026, 10, 13)


def test_yalniz_gun_adi_sonraki_o_gun():
    assert tarih_coz("Cuma günü kısa sınav", date(2026, 10, 12), YIL).gun == date(2026, 10, 16)
    assert tarih_coz("Cuma günü kısa sınav", date(2026, 10, 16), YIL).gun == date(2026, 10, 23)


def test_cumartesi_cuma_ile_karismaz():
    assert tarih_coz("Cumartesi deneme sınavı", date(2026, 10, 12), YIL).gun == date(2026, 10, 17)


def test_yarin_ve_bugun():
    assert tarih_coz("Yarın quiz var", date(2026, 10, 12), YIL).gun == date(2026, 10, 13)
    assert tarih_coz("tomorrow's quiz", date(2026, 10, 12), YIL).gun == date(2026, 10, 13)
    assert tarih_coz("Bugün kısa sınav", date(2026, 10, 12), YIL).gun == date(2026, 10, 12)


def test_ara_sozcugu_ay_sanilmaz():
    assert tarih_coz("20 arasında soru", date(2026, 10, 12), YIL) == TarihCozumu(None, None, False)


def test_cozulemeyen_ifade_tarih_uydurmaz():
    assert tarih_coz("Yakında bir quiz olacak", date(2026, 10, 12), YIL) == TarihCozumu(None, None, False)
