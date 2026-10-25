"""MEB kitap haritası betiği (spec 2026-10-25 §2.2, plan Görev 3–4): PDF'ten bağımsız fikstürlerle."""
from pathlib import Path

import pytest

from scripts import meb_kitap_haritasi as mkh

FIKSTUR = Path(__file__).parent / "fixtures" / "kitap_haritasi"
ICINDEKILER = (FIKSTUR / "fen7_1_icindekiler.txt").read_text(encoding="utf-8")


def _ozet(uniteler):
    return [(u["no"], u["ad"], u["sayfa"], u["son_sayfa"],
             [(c["no"], c["ad"], c["sayfa"], c["son_sayfa"], [(k["ad"], k["sayfa"], k["son_sayfa"]) for k in c["konular"]])
              for c in u["cerceveler"]]) for u in uniteler]


def test_icindekiler_fen_yapisi_ve_sinirlari():
    # Sonraki sayfanın metni form besleme karakterinden sonra gelir ve okunmaz.
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER + "\f\nKitabımızı Tanıyalım\n1. Ünite Numarası ve Adı .... 9\n")
    o = _ozet(uniteler)
    assert [u[:4] for u in o] == [(1, "Uzay Çağı", 14, 57), (2, "Kuvvet ve Enerjiyi Keşfedelim", 58, 87),
                                  (3, "Vücudumuzdaki Sistemler", 88, 148)]
    assert o[0][4] == [
        (1, "Türkiye ve Uzay Araştırmaları", 15, 33,
         [("Uzay Teknolojileri", 16, 23), ("Teknoloji ile Uzay Araştırmaları Arasındaki İlişki", 24, 33)]),
        (2, "Uzayda Neler Var?", 34, 49, [("Yıldız Oluşumu", 35, 49)])]
    assert o[1][4] == [
        (1, "Kuvvet, İş ve Enerji İlişkisi", 59, 70, [("Fiziksel Anlamda İş", 60, 63), ("Enerji ve Enerji Çeşitleri", 64, 70)]),
        (2, "Enerji Dönüşümleri", 71, 79, [("Enerjinin Korunumu", 72, 79)])]
    assert o[2][4][1] == (2, "Dolaşım Sistemi", 101, 116,
                          [("Dolaşım Sistemini Oluşturan Yapı ve Organlar", 102, 108),
                           ("Kan Bağışının Toplum Açısından Önemi", 109, 112), ("Dolaşım Sisteminin Sağlığı", 113, 116)])
    assert o[2][4][3][:4] == (4, "Boşaltım Sistemi", 129, 139)
    # Ünite ekleri ve ön/arka kısım haritaya girmez.
    adlar = {k[0] for u in o for c in u[4] for k in c[4]} | {c[1] for u in o for c in u[4]}
    assert not adlar & {"Ön Değerlendirme", "İz Bırakanlar", "Ünite Sonu Değerlendirme", "Sözlük", "Kitabımızı Tanıyalım"}
    assert uniteler[0]["cerceveler"][0]["ciktilar"] == [] and uniteler[0]["cerceveler"][0]["basliklar"] == []


def test_iki_satira_bolunen_girdi_birlesir():
    metin = ("İçindekiler\n1. Ünite      Deneme\n1. Uzun Bir İçerik Çerçevesi Adı ki\n"
             "İki Satıra Bölünmüş ............ 15\nKonu Bir ..... 16\nÜnite Sonu Değerlendirme ...... 20\nSözlük ..... 21\n")
    u = mkh.icindekiler_ayristir(metin)[0]
    assert (u["sayfa"], u["son_sayfa"]) == (15, 20)
    c = u["cerceveler"][0]
    assert (c["no"], c["ad"], c["sayfa"], c["son_sayfa"]) == (1, "Uzun Bir İçerik Çerçevesi Adı ki İki Satıra Bölünmüş", 15, 19)
    assert [(k["ad"], k["sayfa"], k["son_sayfa"]) for k in c["konular"]] == [("Konu Bir", 16, 19)]


@pytest.mark.parametrize("metin,ileti", [
    ("Sayfa yok\n", "İçindekiler başlığı yok"),
    ("İçindekiler\n1. Ünite   A\n1. Ç ..... 10\nK ..... 9\n", "geriye gidiyor"),
    ("İçindekiler\n1. Ünite   A\nanlamsız satır\nbir anlamsız satır daha\n", "tanınmayan İçindekiler satırı"),
    ("İçindekiler\n1. Ünite   A\nK ..... 9\n", "çerçevesiz konu"),
    ("İçindekiler\nSözlük ..... 9\n", "ünite yok"),
])
def test_bozuk_icindekiler_reddedilir(metin, ileti):
    with pytest.raises(mkh.YapiHatasi, match=ileti):
        mkh.icindekiler_ayristir(metin)
