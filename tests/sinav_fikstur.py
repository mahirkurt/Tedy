"""Real-shape fixtures for the exam detector, measured on live data 2026-10-16.
Teacher names are replaced; the texts are otherwise the portal's own."""

KTT_KARTI = (
    "KTT-1 KONULARI\nÖğretmen A | 05.10.2026\nMATEMATİK KONU TARAMA TESTİ (KTT) KONULARI\n"
    "Sevgili Öğrencilerim,\n"
    "15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT konu başlıkları aşağıdaki gibidir:\n"
    "TAM SAYILAR FARKLI GÖSTERİMLERİ\nRASYONEL SAYILAR VE FARKLI GÖSTERİMLERİ\n"
    "RASYONEL SAYILARIN SAYI DOĞRUSU ÜZERİNDE GÖSTERİMİ\nMUTLAK DEĞER\n"
    "RASYONEL SAYILARDA KARŞILAŞTIRMA VE SIRALAMA\nKısa sınav 20 soru test olacaktır.\n"
    "Hepinize iyi çalışmalar ve başarılar dilerim.")
# The portal renders each post twice: once with its title, once without.
KTT_GOVDE = KTT_KARTI.split("\n", 1)[1]
FEN_KARTI = (
    "5. hafta\nÖğretmen B | 05.10.2026\nSevgili Öğrenciler, 🌟\n"
    "Geçtiğimiz hafta hep birlikte keyifli bir yolculuğa çıkarak \"Uzay Çağı\" ünitemizi başarıyla tamamladık.\n"
    "Büyük Quiz Zamanı! 📝\nBu hafta ilk ünitemizin tamamını kapsayan bir quiz olacaksınız. "
    "Sınavda en yüksek başarıyı yakalamak için konu tekrarlarınızı düzenli yapmayı ve bol bol soru "
    "çözmeyi sakın unutmayın.")
FEN_OGESI = "Büyük Quiz Zamanı! 📝"
ING_KARTI = (
    "Week 2 / QUIZ\nÖğretmen C | 21.09.2026\nDear Students,\n\nThis week, we started the Present "
    "Perfect Tense. We learned the rules and practiced using common time expressions.\n"
    "Next week, you will have an Irregular Verbs Quiz, so please study the list that I shared on PORTAL.")
FR_KARTI = "Semaine 3 - Logements\nÖğretmen D | 28.09.2026\n\nQuizlet için linke tıkla : https://quizlet.com/join/x"


def haftalar_verisi() -> dict:
    return {
        "ders_icerikleri_haftalar": {
            "2. Hafta 21 Eyl. - 27 Eyl.": {
                "İngilizce Language": {"cards": [ING_KARTI, ING_KARTI.split("\n", 1)[1]], "items": [], "text": ""}},
            "3. Hafta 28 Eyl. - 04 Eki.": {
                "2. Yabancı Dil (F)": {"cards": [FR_KARTI], "items": [], "text": ""}},
            "4. Hafta 05 Eki. - 11 Eki.": {
                "Matematik": {"cards": ["Başka bir duyuru", KTT_KARTI, KTT_GOVDE], "items": [], "text": ""},
                "Fen Bilimleri": {"cards": [FEN_KARTI], "items": [FEN_OGESI], "text": ""}},
            "5. Hafta 12 Eki. - 18 Eki.": {
                "Matematik": {"cards": ["Başka bir duyuru", KTT_KARTI, KTT_GOVDE], "items": [], "text": ""}},
        },
        # The live open-week section carries a Selenium error for "Genel": no cards.
        "ders_icerikleri": {"Genel": {"tab_id": "tab_genel", "error": "Message: no such element"}},
        "odevlerim": {"homework": {"rows": []}},
        "duyurular": {"announcements": []},
        "takvim": [],
    }


def _takvim(baslik, bas, son="", tur="sinav"):
    return {"title": baslik, "start": bas, "end": son, "allDay": False, "backgroundColor": "",
            "extendedProps": {"calendar": tur}}


TAKVIM_SINAV = [
    _takvim("5-6-7. Sınıflar Özdebir Gelişim İzleme Sınavı GİS-1 (Türkiye Geneli) / 5-6-7th Grades "
            "Özdebir Monitoring Exam (Türkiye-wide)", "2026-10-23T09:00:00+03:00", "2026-10-23T12:10:00+03:00"),
    _takvim("5-6-7-8. Sınıflar Sebit Vcloud Kazanım Değerlendirme Uygulaması-1_TM / 5-6-7-8th Grades "
            "Sebit Vcloud Learning Outcome Assessment Application-1_TM", "2027-01-14T08:55:00+03:00",
            "2027-01-14T12:00:00+03:00"),
    _takvim("5-6-7-8. Sınıflar MEB 1. Dönem 2. Yazılı Sınav Haftası Başlangıcı / 5-6-7-8th Grades "
            "Beginning of MEB 1st Term 2nd Written Exam Week", "2027-01-04T08:00:00+03:00"),
    _takvim("Grade 7 English  (English Language)", "2026-10-13T16:00:00+03:00", tur="kisisel"),
]
