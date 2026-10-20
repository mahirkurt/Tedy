"""ÖDSGM konu-soru dağılım tablosu betiği (spec 2026-10-19 §2): LibreOffice HTML'i ızgaraya,
ızgarayı senaryo verisine çevirir; yapı beklenenden farklıysa yazmayı reddeder."""
from pathlib import Path

import pytest

from scripts.odsgm_senaryo_tablolari import YapiHatasi, ders_sayfasi, tablolar

FIKSTUR = Path(__file__).parent / "fixtures" / "odsgm" / "ornek_tablo.html"


def _html():
    return FIKSTUR.read_text(encoding="utf-8")


def test_izgara_birlesik_hucreleri_cozer():
    t = tablolar(_html())
    assert len(t) == 2
    yedi = t[1]
    # rowspan="2" başlık iki satırda da görünür; colspan senaryo sütunlarına yayılır
    assert yedi[3][0] == yedi[4][0] == "Alan Becerileri"
    assert yedi[3][2:5] == ["1. Dönem 1. Ortak Yazılı Sınav"] * 3
    assert yedi[4][2:5] == ["Senaryo 1", "Senaryo 2", "Senaryo 3"]
    # rowspan="3" alan hücresi sonraki iki veri satırında da var; boş hücre boş kalır
    assert yedi[6][0] == "OKUMA" and yedi[6][1].startswith("T.O.7.5.")
    assert yedi[5][2:5] == ["1", "", "1"]
    # ülke geneli birleşik hücresi veri satırlarına da yayılır
    assert "Ülke Geneli" in yedi[6][5]


def test_yedinci_sinif_sayfasi_senaryo_verisine_cevrilir():
    ders, sayfa = ders_sayfasi(tablolar(_html()), 7)
    assert ders == "Türkçe"
    kodlar = [c["kod"] for c in sayfa["ciktilar"]]
    assert kodlar == ["T.O.7.4", "T.O.7.5", "T.O.7.8", "T.Y.7.21"]
    assert sayfa["ciktilar"][1] == {"kod": "T.O.7.5", "metin": "Metnin yüzey anlamını belirleyebilme",
                                    "alan": "OKUMA", "konu": None}
    birinci = sayfa["sinavlar"]["1"]
    assert birinci["tur"] == "senaryolu"
    assert birinci["senaryolar"] == {"1": {"T.O.7.4": 1, "T.O.7.5": 1, "T.Y.7.21": 1},
                                     "2": {"T.O.7.5": 2, "T.Y.7.21": 1},
                                     "3": {"T.O.7.4": 1, "T.O.7.5": 2}}
    ikinci = sayfa["sinavlar"]["2"]
    assert ikinci["tur"] == "ulke_geneli" and "Ülke Geneli" in ikinci["not"]


def test_istenen_sinif_yoksa_reddeder():
    with pytest.raises(YapiHatasi, match="8. sınıf"):
        ders_sayfasi(tablolar(_html()), 8)


def test_basliksiz_tablo_reddedilir():
    html = _html().replace("Öğrenme Çıktıları", "Açıklama")
    with pytest.raises(YapiHatasi, match="başlık"):
        ders_sayfasi(tablolar(html), 7)


def test_sayi_olmayan_hucre_reddedilir():
    html = _html().replace("<td>1</td><td>2</td><td>2</td>", "<td>1</td><td>iki</td><td>2</td>")
    with pytest.raises(YapiHatasi, match="iki"):
        ders_sayfasi(tablolar(html), 7)


def test_toplami_sifir_senaryo_reddedilir():
    html = (_html().replace("<td>1</td><td></td><td>1</td>", "<td>1</td><td></td><td></td>")
            .replace("<td>1</td><td>2</td><td>2</td>", "<td>1</td><td>2</td><td></td>"))
    with pytest.raises(YapiHatasi, match="Senaryo 3"):
        ders_sayfasi(tablolar(html), 7)


def test_ayni_kod_iki_kez_reddedilir():
    html = _html().replace("T.O.7.8. Metnin derin", "T.O.7.5. Metnin derin")
    with pytest.raises(YapiHatasi, match="T.O.7.5"):
        ders_sayfasi(tablolar(html), 7)


def test_bilinmeyen_ders_reddedilir():
    html = _html().replace("7. SINIF TÜRKÇE DERSİ", "7. SINIF SEÇMELİ ASTRONOMİ DERSİ")
    with pytest.raises(YapiHatasi, match="ders"):
        ders_sayfasi(tablolar(html), 7)


def test_kodu_okunamayan_satir_reddedilir():
    # kod ile metin arasında boşluk yok: satır sessizce atılırsa Senaryo 2/3 toplamları eksik kalırdı
    html = _html().replace("T.O.7.5. Metnin", "T.O.7.5.Metnin")
    with pytest.raises(YapiHatasi, match="kodu okunamayan"):
        ders_sayfasi(tablolar(html), 7)


def test_toplam_satiri_atlanir():
    # fikstürün son satırı TOPLAM (kodsuz, senaryo sütunları dolu): çıktı sayılmaz, reddedilmez
    _, sayfa = ders_sayfasi(tablolar(_html()), 7)
    assert len(sayfa["ciktilar"]) == 4
    assert sayfa["sinavlar"]["1"]["senaryolar"]["1"] == {"T.O.7.4": 1, "T.O.7.5": 1, "T.Y.7.21": 1}
