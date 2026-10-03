"""Portal UI residue (plan docs/superpowers/plans/2026-09-28-portal-ekleri.md, Görev 1).

The shapes are the real ones measured in output/scraped_data.json on
2026-09-28 — "N Yorum yapıldı!" / "Daha fazla oku", then per comment a name
line, a like-count line and the comment, then "Yorum Ekle" — with invented
names and words. No real student appears here.
"""
import json

from src.portal_susu import (SUS_ISARETLERI, temiz_dersler, temiz_haftalar,
                             temiz_icerik_kaydi, temiz_metin)

YORUMCULAR = ("Kurgu Öğrenci Bir", "Uydurma Öğrenci İki", "Deneme Öğrenci Üç")
YORUMLAR = ("çok güzel olmuş", "harika bir etkinlik", "ben de katılacağım")

GENEL = (
    "Okulumuzda Bilim Şenliği Başlıyor\n"
    "TED Rönesans Koleji | 22.09.2026\n"
    "  3 Yorum yapıldı!\n"
    "  Daha fazla oku\n"
    "Kurgu Öğrenci Bir\n3\nçok güzel olmuş\n"
    "Uydurma Öğrenci İki\n0\nharika bir etkinlik \n"
    "Deneme Öğrenci Üç\n1\nben de katılacağım\n"
    "Yorum Ekle\n"
    "\n"
    "Veli Toplantısı Duyurusu\n"
    "TED Rönesans Koleji | 21.09.2026\n"
    "Toplantı perşembe 19:00'da konferans salonunda.\n"
    "  İlk yorum yapan sen olmak ister misin?\n"
    "  Daha fazla oku\n"
    "Yorum Ekle"
)


def sizinti(metin):
    """Every name, comment or chrome string still present in `metin`."""
    return [s for s in (*YORUMCULAR, *YORUMLAR, *SUS_ISARETLERI) if s in metin]


def test_okul_gonderisi_kalir_yorum_blogu_gider():
    temiz = temiz_metin(GENEL)
    assert sizinti(temiz) == []
    assert temiz == (
        "Okulumuzda Bilim Şenliği Başlıyor\n"
        "TED Rönesans Koleji | 22.09.2026\n"
        "\n"
        "Veli Toplantısı Duyurusu\n"
        "TED Rönesans Koleji | 21.09.2026\n"
        "Toplantı perşembe 19:00'da konferans salonunda."
    )


def test_kapanmayan_yorum_blogu_metnin_sonuna_kadar_atilir():
    # 87 cards were measured ending right at "Daha fazla oku", and the scraper
    # cuts a tab's text at 8,000 characters: an unclosed block is a cut one.
    kesik = ("Kitap Fuarı\nTED Rönesans Koleji | 23.09.2026\n  2 Yorum yapıldı!\n"
             "  Daha fazla oku\nKurgu Öğrenci Bir\n4\nçok güz")
    assert temiz_metin(kesik) == "Kitap Fuarı\nTED Rönesans Koleji | 23.09.2026"


def test_yorum_icindeki_bos_satir_blogu_bitirmez():
    # The old rule ended the block at any blank line; a comment holding one
    # leaked every comment after it.
    metin = ("Duyuru\n  Daha fazla oku\nKurgu Öğrenci Bir\n2\nilk satır\n\n"
             "Uydurma Öğrenci İki\n1\nharika bir etkinlik\nYorum Ekle\nSonraki paragraf")
    temiz = temiz_metin(metin)
    assert sizinti(temiz) == []
    assert temiz == "Duyuru\nSonraki paragraf"


def test_bosluk_farki_isareti_gizlemez():
    # Selenium hands over rendered text: NBSPs and doubled spaces included.
    nbsp = chr(0xA0)
    metin = f"Başlık\n{nbsp} Daha  fazla oku{nbsp}\nKurgu Öğrenci Bir\nYorum{nbsp}Ekle\nGövde"
    assert temiz_metin(metin) == "Başlık\nGövde"


def test_iki_kez_uygulamak_degistirmez():
    bir = temiz_metin(GENEL)
    assert temiz_metin(bir) == bir


def test_bos_ve_metin_olmayan_girdi():
    assert temiz_metin(None) == ""
    assert temiz_metin("") == ""
    assert temiz_metin(42) == "42"


def test_icerik_kaydi_her_metin_alanini_temizler_yalniz_yorum_karti_atar():
    kayit = {
        "tab_id": "tab_genel",
        "text": GENEL,
        "cards": [GENEL,
                  "  Daha fazla oku\nKurgu Öğrenci Bir\n3\nçok güzel olmuş\nYorum Ekle",
                  "TED Rönesans Koleji | 22.09.2026"],
        "items": ["Kurgu madde", "  Daha fazla oku\nUydurma Öğrenci İki\nYorum Ekle"],
        "tables": [{"headers": ["Başlık"],
                    "rows": [["Şenlik\n  Daha fazla oku\nDeneme Öğrenci Üç\nYorum Ekle"]]}],
    }
    temiz = temiz_icerik_kaydi(kayit)
    assert sizinti(json.dumps(temiz, ensure_ascii=False)) == []
    assert temiz["tab_id"] == "tab_genel"
    assert len(temiz["cards"]) == 2          # the comments-only card is gone
    assert temiz["items"] == ["Kurgu madde"]
    assert temiz["tables"][0]["rows"] == [["Şenlik"]]
    assert kayit["cards"][0] == GENEL        # the input is not mutated


def test_hata_kaydi_ve_bicimsiz_girdi_oldugu_gibi_doner():
    assert temiz_icerik_kaydi({"tab_id": "ders_2", "error": "x"}) == {"tab_id": "ders_2", "error": "x"}
    assert temiz_icerik_kaydi("x") == "x"


def test_dersler_ve_haftalar():
    haftalar = {"1. Hafta 14 Eyl. - 20 Eyl.": {
        "Genel": {"tab_id": "tab_genel", "text": GENEL, "cards": [GENEL], "items": [], "tables": []}}}
    temiz = temiz_haftalar(haftalar)
    assert sizinti(json.dumps(temiz, ensure_ascii=False)) == []
    assert temiz_dersler({"Genel": {"text": GENEL}})["Genel"]["text"].startswith("Okulumuzda")
    assert temiz_haftalar([]) == []
    assert temiz_dersler(None) is None
