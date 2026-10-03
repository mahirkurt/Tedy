"""Alıştırma doğrulaması ve puanı; yalnız yerel, yapay veriler."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.assistant_alistirma import (
    alistirma_hata, calisilan_konular, cevap_dogru, hafta_araligi,
    yanlis_esle, zayif_konular,
)


def _soru(**fazla):
    return {"tur": "kisa_cevap", "soru": "1/2 + 1/3", "dogru": "5/6",
            "aciklama": "Paydalar eşitlenir.", **fazla}


def _govde(sorular=None, **fazla):
    return {"baslik": "Payda", "ders": "Matematik", "konu": "Kesir",
            "zorluk": "orta", "sorular": sorular if sorular is not None else [_soru()] * 3,
            **fazla}


@pytest.mark.parametrize("adet", [3, 10])
@pytest.mark.parametrize("zorluk", ["kolay", "orta", "zor"])
@pytest.mark.parametrize("kod", [None, "", "  ", "MAT.7.1.1"])
def test_gecerli_soru_sinirlari_ve_istege_bagli_kod(adet, zorluk, kod):
    assert alistirma_hata(_govde([_soru()] * adet, zorluk=zorluk, kazanim_kodu=kod)) is None


@pytest.mark.parametrize("alan,deger", [
    ("baslik", "  "), ("ders", None), ("konu", []), ("zorluk", "asiri"),
    ("zorluk", ""), ("sorular", []), ("sorular", [_soru()] * 2),
    ("sorular", [_soru()] * 11), ("sorular", "abc"), ("kazanim_kodu", 7),
])
def test_gecersiz_govde_yazilamaz(alan, deger):
    govde = _govde()
    govde[alan] = deger
    assert alistirma_hata(govde)


@pytest.mark.parametrize("govde", [None, [], "", 1])
def test_nesne_olmayan_govde_red(govde):
    assert alistirma_hata(govde)


@pytest.mark.parametrize("alan", ["baslik", "ders", "konu", "zorluk", "sorular"])
def test_zorunlu_alan_yoksa_red(alan):
    govde = _govde()
    del govde[alan]
    assert alistirma_hata(govde)


@pytest.mark.parametrize("degisiklik", [
    {"tur": "acik_uclu"}, {"tur": []}, {"tur": {}}, {"soru": " "}, {"dogru": ""}, {"aciklama": " "},
    {"dogru": True}, {"kabul_edilenler": "0,5"}, {"kabul_edilenler": [""]},
    {"kabul_edilenler": [2]}, {"kaynak": 2},
])
def test_gecersiz_soru_red(degisiklik):
    assert alistirma_hata(_govde([_soru(**degisiklik), _soru(), _soru()]))


def test_soru_nesne_olmali():
    assert alistirma_hata(_govde([None, _soru(), _soru()]))


def test_turler_ve_kaynak_sozlesmesi():
    sorular = [_soru(tur="dogru_yanlis", dogru="Doğru"),
               _soru(kabul_edilenler=["0,833"], kaynak=""),
               _soru(tur="coktan_secmeli", secenekler=["5/6", "2/5", "1/2", "3/4"])]
    assert alistirma_hata(_govde(sorular)) is None


@pytest.mark.parametrize("secenekler", [
    ["5/6", "2/5", "1/2"], ["5/6", "2/5", "1/2", "3/4", "1"],
    ["5/6", "2/5", "1/2", " "], ["5/6", "2/5", "1/2", 1],
    ["1", "2", "3", "4"], "1234", None,
])
def test_coktan_secmeli_tam_dort_dizgi_ve_birebir_dogru_ister(secenekler):
    assert alistirma_hata(_govde([_soru(tur="coktan_secmeli", secenekler=secenekler)] * 3))


@pytest.mark.parametrize("verilen,dogru,beklenen", [
    ("  Beş   bölü ALTI ", "beş bölü altı", True),
    ("İstanbul", "istanbul", True), ("IŞIK", "ışık", True),
    ("‘İstanbul!’", "istanbul", True), ("1/2.", "1/2", True),
    ("1/2", "12", False), ("0,5", "1/2", True),
    ("0.51", "1/2", True), ("0,51001", "1/2", False),
    ("-0,5", "-1/2", True), ("-0.5", "1/2", False),
    ("0", "1/0", False), ("5 elma", "5 armut", False),
    ("1.000", "1000", False), ("5/6", "0,833333333", True),
    ("", "", False), ("...", "!!!", False),
])
def test_katlama_noktalama_ve_sayisal_tolerans(verilen, dogru, beklenen):
    assert cevap_dogru(verilen, dogru, None) is beklenen


def test_kabul_edilen_cevaplar_da_katlanir_ve_sayiya_donusur():
    assert cevap_dogru("yarım", "1/2", ["YARIM"])
    assert cevap_dogru("0.50", "yarım", ["1/2"])
    assert not cevap_dogru("", "yanıt", [" "])


def _satir(konu, kod, dogru, gun, dakika):
    return {"konu": konu, "kazanim_kodu": kod, "dogru": dogru,
            "zaman": f"2026-10-{gun:02d}T08:{dakika:02d}:00Z"}


def test_zayif_yuzde_altmis_haric_en_az_uc_ve_son_on():
    satirlar = [_satir("Kesir", "MAT.7.1.1", i == 0, 1, i) for i in range(3)]
    satirlar += [_satir("Oran", "MAT.7.1.5", i < 3, 2, i) for i in range(5)]
    satirlar += [_satir("Denklem", "", False, 3, i) for i in range(2)]
    assert zayif_konular(satirlar) == [{"konu": "Kesir", "kazanim_kodu": "MAT.7.1.1", "dogru": 1, "toplam": 3}]
    eski = [_satir("Kesir", "MAT.7.2.1", True, 4, i) for i in range(20)]
    yeni = [_satir("Kesir", "MAT.7.2.1", False, 5, i) for i in range(10)]
    assert zayif_konular(list(reversed(eski + yeni))) == [
        {"konu": "Kesir", "kazanim_kodu": "MAT.7.2.1", "dogru": 0, "toplam": 10}]


def test_zayif_siralama_kod_grubu_ve_eksik_zaman():
    satirlar = [{"konu": "B", "dogru": False}] * 3
    satirlar += [_satir("A", "B", False, 1, i) for i in range(4)]
    satirlar += [_satir("A", "A", False, 1, i) for i in range(4)]
    assert [(x["konu"], x["kazanim_kodu"], x["toplam"]) for x in zayif_konular(satirlar)] == [
        ("A", "A", 4), ("A", "B", 4), ("B", "", 3)]
    eski = [{"konu": "C", "kazanim_kodu": None, "dogru": True}] * 20
    yeni = [_satir("C", None, False, 2, i) for i in range(10)]
    assert zayif_konular(yeni + eski)[0]["dogru"] == 0


def test_atif_kod_ve_sayfa_kaynaklari_tekillestirilir():
    atiflar = [
        {"label": "MAT.7.1.1 kesir", "locator": {"tool": "kazanim_ara", "args": {"kazanim_kodu": "MAT.7.1.1"}}},
        {"label": "MAT.7.1.1 kesir", "locator": {}},
        {"label": " Kesirler sayfa 12 ", "locator": {"tool": "kitap_sayfa", "args": {}}},
        {"label": "not", "locator": {"tool": "notlar"}},
        {"label": "başka", "locator": {"args": {"kod": "FEN.7.1.2"}}},
        {"label": "MAT.7.1.1. nokta", "locator": {}},
    ]
    assert calisilan_konular(atiflar) == [
        {"kazanim_kodu": "MAT.7.1.1", "sayfa_basligi": ""},
        {"kazanim_kodu": "", "sayfa_basligi": "Kesirler sayfa 12"},
        {"kazanim_kodu": "FEN.7.1.2", "sayfa_basligi": ""},
    ]


@pytest.mark.parametrize("simdi,bas,son", [
    (datetime(2026, 10, 3, 8, tzinfo=timezone.utc), datetime(2026, 9, 27, 21, tzinfo=timezone.utc), datetime(2026, 10, 4, 21, tzinfo=timezone.utc)),
    (datetime(2026, 10, 4, 20, 59, tzinfo=timezone.utc), datetime(2026, 9, 27, 21, tzinfo=timezone.utc), datetime(2026, 10, 4, 21, tzinfo=timezone.utc)),
    (datetime(2026, 10, 4, 21, tzinfo=timezone.utc), datetime(2026, 10, 4, 21, tzinfo=timezone.utc), datetime(2026, 10, 11, 21, tzinfo=timezone.utc)),
])
def test_hafta_istanbul_pazartesi_sinirlari(simdi, bas, son):
    assert hafta_araligi(simdi) == (bas, son)


def test_yanlis_katalog_esigi_ve_esitlikte_dosya_sirasi():
    katalog = (
        "### Paydalar toplanır\n\n**Doğrusu:** Paydalar eşitlenir.\n"
        "**Kontrol sorusu:** 1/4 + 1/2?\n\n"
        "### Paydalar yine toplanır\n\n**Doğrusu:** Toplama değil.\n"
        "**Kontrol sorusu:** Başka?\n"
    )
    assert yanlis_esle("paydalar toplanir", "paydalar toplanir", katalog) == {
        "baslik": "Paydalar toplanır", "dogrusu": "Paydalar eşitlenir.", "kontrol": "1/4 + 1/2?"}
    assert yanlis_esle("mavi", "kalem", katalog) is None
    assert yanlis_esle("paydalar", "ve", katalog) is None


def test_yanlis_gercek_katalog_kesir_eslesmesi():
    katalog = (Path(__file__).parents[1] / "src/assistant_skills/matematik/references/kavram-yanilgilari.md").read_text()
    assert yanlis_esle("paydalar toplanir", "paydalar toplanir", katalog)["baslik"] == "Kesirleri toplarken paylar ve paydalar ayrı ayrı toplanır"


@pytest.mark.parametrize("skill,olcut", [
    ("matematik", "çözüm yolu ve gösterim"),
    ("turkce", "yazma ve okuma-anlama"),
    ("fen", "deney tasarımı ve bilimsel açıklama"),
    ("sosyal", "kaynak ve kanıt kullanımı, neden-sonuç"),
])
def test_ogretmen_rubrikleri_surec_olcutlerini_tasir(skill, olcut):
    rubrik = (Path(__file__).parents[1] / "src/assistant_skills" / skill / "references/degerlendirme-rubrigi.md").read_text()
    assert "not vermez" in rubrik
    assert f"Ölçüt: {olcut}" in rubrik
    for duzey in ("baslangic", "gelisiyor", "yeterli"):
        assert f"- {duzey}: " in rubrik
