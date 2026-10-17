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


def test_kesir_ondalik_kod_ve_saat_tarih_sayilmaz():
    yayin = date(2026, 10, 5)
    bos = TarihCozumu(None, None, False)
    assert tarih_coz("Kesirler 3/4 ve 1/2 konulari KTT", yayin, YIL) == bos
    assert tarih_coz("FB.7.1.4 kazanımı quiz", yayin, YIL) == bos
    assert tarih_coz("Sınav saat 9.10 da", yayin, YIL) == bos


def test_ondalik_gun_adini_bozmaz():
    assert tarih_coz("Cuma günü 2.5 saat sınav", date(2026, 10, 5), YIL) \
        == TarihCozumu(date(2026, 10, 9), None, False)


def test_kesir_gercek_tarihi_golgelemez():
    c = tarih_coz("Sınav 1/2 kesir, 15 Ekim Perşembe", date(2026, 10, 5), YIL)
    assert c == TarihCozumu(date(2026, 10, 15), None, False)


def test_ipuculu_yilsiz_sayisal_tarih_calisir():
    assert tarih_coz("15.10 Perşembe quiz", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)
    assert tarih_coz("Sınav 15.10.26 günü", date(2026, 10, 5), YIL).gun == date(2026, 10, 15)


def test_ay_kisaltmasi_tek_basina_ay_sayilmaz():
    yayin = date(2026, 10, 5)
    assert tarih_coz("Unit 2 may 3 include", yayin, YIL) == TarihCozumu(None, None, False)
    assert tarih_coz("2 ara sınav", yayin, YIL) == TarihCozumu(None, None, False)


def test_ay_kisaltmasi_nokta_yil_ya_da_gun_adiyla_ay_sayilir():
    yayin = date(2026, 10, 5)
    assert tarih_coz("Sınav 15 Eki. günü", yayin, YIL).gun == date(2026, 10, 15)
    assert tarih_coz("15 eki 2026 sınav", yayin, YIL).gun == date(2026, 10, 15)
    assert tarih_coz("15 eki perşembe sınav", yayin, YIL).gun == date(2026, 10, 15)
    assert tarih_coz("Quiz Oct. 21", date(2026, 10, 12), YIL).gun == date(2026, 10, 21)
    assert tarih_coz("Quiz oct 21 Wednesday", date(2026, 10, 12), YIL).gun == date(2026, 10, 21)


def test_tam_ay_adi_kisaltma_kurali_disinda():
    assert tarih_coz("15 Mart sınav", date(2026, 10, 5), YIL).gun == date(2027, 3, 15)
    assert tarih_coz("March 15 exam", date(2026, 10, 5), YIL).gun == date(2027, 3, 15)


def test_gecmis_acik_tarih_gun_adini_ileriye_cozmez():
    c = tarih_coz("15 Ekim Perşembe günü yapılan KTT sonuçları açıklandı", date(2026, 10, 16), YIL)
    assert c == TarihCozumu(None, None, True)


# --- yayını bilinmeyen metin: yalnız açık tarihler (son inceleme, Important 2) ---------

def test_goreli_kapaliyken_gun_adi_ve_goreli_ifade_tarih_uydurmaz():
    bugun = date(2026, 10, 16)
    for metin in ("Cuma günü quiz", "yarın kısa sınav", "bugün quiz", "haftaya yazılı",
                  "next week exam on Monday", "bu hafta quiz"):
        assert tarih_coz(metin, bugun, YIL, goreli=False) == TarihCozumu(None, None, False), metin


def test_goreli_kapaliyken_acik_tarih_bugune_gore_cozulur():
    bugun = date(2026, 10, 16)
    assert tarih_coz("20 Kasım Cuma quiz", bugun, YIL, goreli=False) == TarihCozumu(date(2026, 11, 20), None, False)
    # An explicit date already past today is not an upcoming exam.
    assert tarih_coz("15 Ekim quiz", bugun, YIL, goreli=False) == TarihCozumu(None, None, True)


# --- temizlik A (2026-10-17) -------------------------------------------------------

def test_a3_bu_hafta_gun_adi_o_haftanin_gunu():
    # Published on Friday: "bu hafta Cuma" is that same Friday, not the next one.
    assert tarih_coz("Bu hafta Cuma quiz var", date(2026, 10, 16), YIL) == \
        TarihCozumu(date(2026, 10, 16), None, False)
    assert tarih_coz("This week on Wednesday we will have a quiz", date(2026, 10, 12), YIL).gun == \
        date(2026, 10, 14)


def test_a4_pazar_yalniz_gun_ekiyle_gun_adi():
    yayin = date(2026, 10, 12)
    assert tarih_coz("pazar araştırması quiz", yayin, YIL) == TarihCozumu(None, None, False)
    assert tarih_coz("Pazar günü deneme", yayin, YIL).gun == date(2026, 10, 18)
    assert tarih_coz("Deneme Pazar'a ertelendi", yayin, YIL).gun == date(2026, 10, 18)
    assert tarih_coz("Pazar'dan sonra quiz yok", yayin, YIL).gun == date(2026, 10, 18)
    # Beside an explicit date it is the weekday (short-month guard).
    assert tarih_coz("18 Eki Pazar deneme", yayin, YIL).gun == date(2026, 10, 18)


def test_a5_kisa_gun_adi_kisa_ay_korumasinda():
    yayin = date(2026, 10, 5)
    assert tarih_coz("15 Eki Per sınav", yayin, YIL).gun == date(2026, 10, 15)
    assert tarih_coz("16 Eki Cum quiz", yayin, YIL).gun == date(2026, 10, 16)
    # Alone a short weekday resolves nothing.
    assert tarih_coz("Per quiz", yayin, YIL) == TarihCozumu(None, None, False)
    assert tarih_coz("sal quiz", yayin, YIL) == TarihCozumu(None, None, False)


def test_a6_cok_imzali_metinde_ilk_imza():
    metin = "Öğretmen A | 05.10.2026\nKTT konuları\nÖğretmen B | 12.10.2026\nEk duyuru"
    assert yayin_tarihi(metin) == date(2026, 10, 5)


# --- düzeltme turu (temizlik A inceleme) ---------------------------------------------

def test_d1_hafta_sonu_yayininda_bu_hafta_sonraki_haftadir():
    for yayin in (date(2026, 10, 17), date(2026, 10, 18)):   # Cumartesi, Pazar
        assert tarih_coz("Bu hafta Cuma günü quiz olacak", yayin, YIL) == \
            TarihCozumu(date(2026, 10, 23), None, False), yayin
        assert tarih_coz("This week on Friday we will have a quiz", yayin, YIL).gun == date(2026, 10, 23)
        assert tarih_coz("Bu hafta quiz olacak", yayin, YIL) == TarihCozumu(None, date(2026, 10, 19), False)
    # A weekday publication keeps its own week.
    assert tarih_coz("Bu hafta quiz olacak", date(2026, 10, 16), YIL).hafta == date(2026, 10, 12)


def test_d7_belirsiz_kisa_gun_adlari_ay_korumasini_acmaz():
    yayin = date(2026, 10, 5)
    for metin in ("15 Mar sal quiz", "15 Eki car sınav", "15 Eki paz deneme"):
        assert tarih_coz(metin, yayin, YIL) == TarihCozumu(None, None, False), metin
    assert tarih_coz("12 Eki Pzt quiz", yayin, YIL).gun == date(2026, 10, 12)
    assert tarih_coz("17 Eki Cmt deneme", yayin, YIL).gun == date(2026, 10, 17)


# --- düzeltme turu 2 ---------------------------------------------------------------

def test_d2_1_hafta_sonu_yayinin_kendi_haftasinin_hafta_sonudur():
    cmt, paz, cars = date(2026, 10, 17), date(2026, 10, 18), date(2026, 10, 14)
    for yayin in (cmt, paz, cars):
        assert tarih_coz("Bu hafta sonu Pazar günü deneme sınavı", yayin, YIL).gun == date(2026, 10, 18), yayin
        assert tarih_coz("Bu hafta sonu deneme sınavı yapılacak", yayin, YIL) == \
            TarihCozumu(None, date(2026, 10, 12), False), yayin
        assert tarih_coz("Hafta sonunda Cumartesi deneme var", yayin, YIL).gun == date(2026, 10, 17), yayin
        assert tarih_coz("Hafta sonu deneme olacak", yayin, YIL).hafta == date(2026, 10, 12), yayin
    # Plain "bu hafta" at the weekend still means the coming week.
    assert tarih_coz("Bu hafta quiz olacak", cmt, YIL).hafta == date(2026, 10, 19)
    assert tarih_coz("Bu hafta Cuma günü quiz olacak", paz, YIL).gun == date(2026, 10, 23)
