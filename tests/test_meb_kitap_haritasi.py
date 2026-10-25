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


import hashlib  # noqa: E402
import json  # noqa: E402
from datetime import date  # noqa: E402

from src.sinav_senaryo import tablo_oku  # noqa: E402

DUZEN = (FIKSTUR / "fen7_1_duzen.xml").read_text(encoding="utf-8")
FEN_DUZENI = mkh.KITAPLAR["fen-bilimleri"]["kitaplar"][0]["duzen"]
FEN_CIKTILARI = tablo_oku()["dersler"]["Fen Bilimleri"]["ciktilar"]


def test_basliklar_etiket_amac_tanim_ve_gurultu():
    adaylar = [(a["pdf_sayfa"], a["tur"], a["metin"], a["amac"]) for a in mkh.basliklari_ayristir(DUZEN, FEN_DUZENI)]
    assert adaylar == [
        (24, "diger", "B- Yer Tabanlı Teleskoplar", None),
        (24, "etkinlik", "Performans Görevi: Uzay Gözlem Araçları Modeli",
         "Uzay gözlem araçları ile ilgili bilimsel model oluşturma"),
        (24, "baglanti", "Bağlantı Noktası", None),
        (25, "kontrol", "Kontrol Noktası", None),
        (25, "diger", "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki", None),
        (60, "baglanti", "Bağlantı Noktası", None),
        (61, "diger", "Fiziksel Anlamda İş", None),
        (61, "etkinlik", "Etkinlik Noktası-1", "Fiziksel anlamda yapılan işin niteliklerini tanımlama"),
        (61, "etkinlik", "Etkinlik Noktası-2", "Fiziksel anlamda iş yapma durumuna göre günlük yaşam örneklerini değerlendirme"),
        (63, "baglanti", "Bağlantı Noktası", None),
        (64, "kontrol", "Kontrol Noktası", None),
        (65, "diger", "Enerji ve Enerji Çeşitleri", None),
        (66, "etkinlik", "Etkinlik Noktası-3", "Kinetik ve potansiyel enerjiyi karşılaştırma"),
        (69, "tanim", "Potansiyel Enerji", None),
        (69, "tanim", "Çekim Potansiyel Enerjisi", None),
        (69, "tanim", "Esneklik Potansiyel Enerjisi", None),
        (69, "kontrol", "Kontrol Noktası", None),
        (70, "etkinlik", "Etkinlik Noktası-4", "Enerji çeşitlerinden kinetik ve potansiyel enerjiyi karşılaştırma"),
        (71, "ozet", "Neler Öğrendik?", None),
    ]


def test_atla_listesi_basligi_dusurur():
    duzen = {**FEN_DUZENI, "atla": ("B- Yer Tabanlı Teleskoplar",)}
    assert "B- Yer Tabanlı Teleskoplar" not in [a["metin"] for a in mkh.basliklari_ayristir(DUZEN, duzen)]


def test_basliklar_konu_sinirina_gore_yerlesir_ve_konu_bitisi_uzar():
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER)
    mkh.basliklari_yerlestir(uniteler, mkh.basliklari_ayristir(DUZEN, FEN_DUZENI), 1)
    uzay = uniteler[0]["cerceveler"][0]["konular"]
    assert [(b["tur"], b["ad"], b["sayfa"]) for b in uzay[0]["basliklar"]] == [
        ("diger", "B- Yer Tabanlı Teleskoplar", 23), ("etkinlik", "Performans Görevi: Uzay Gözlem Araçları Modeli", 23),
        ("baglanti", "Bağlantı Noktası", 23), ("kontrol", "Kontrol Noktası", 24)]
    assert uzay[0]["son_sayfa"] == 24          # İçindekiler 23 der; son blok s. 24'ün üstüne taşar
    assert uzay[1]["basliklar"] == []          # konunun kendi başlığı listeye girmez
    kuvvet = uniteler[1]["cerceveler"][0]
    assert [(b["tur"], b["ad"], b["sayfa"]) for b in kuvvet["basliklar"]] == [("baglanti", "Bağlantı Noktası", 59)]
    assert [(b["ad"], b["sayfa"]) for b in kuvvet["konular"][0]["basliklar"]] == [
        ("Etkinlik Noktası-1", 60), ("Etkinlik Noktası-2", 60), ("Bağlantı Noktası", 62), ("Kontrol Noktası", 63)]
    assert kuvvet["konular"][0]["basliklar"][0]["amac"] == "Fiziksel anlamda yapılan işin niteliklerini tanımlama"
    assert [(b["tur"], b["ad"], b["sayfa"]) for b in kuvvet["konular"][1]["basliklar"]] == [
        ("etkinlik", "Etkinlik Noktası-3", 65), ("tanim", "Potansiyel Enerji", 68),
        ("tanim", "Çekim Potansiyel Enerjisi", 68), ("tanim", "Esneklik Potansiyel Enerjisi", 68),
        ("kontrol", "Kontrol Noktası", 68), ("etkinlik", "Etkinlik Noktası-4", 69), ("ozet", "Neler Öğrendik?", 70)]


def test_cikti_eslemesi_cerceve_adindan_ve_konu_benzerliginden():
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER)
    eslesme, eslesmedi = mkh.ciktilari_esle(uniteler, FEN_CIKTILARI, 0)
    assert eslesmedi == []
    konular = {kod: [e["konu"] for e in yollar] for kod, yollar in eslesme.items()}
    assert konular["FB.7.1.1"] == ["Uzay Teknolojileri", "Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"]
    assert konular["FB.7.1.3"] == ["Teknoloji ile Uzay Araştırmaları Arasındaki İlişki"]
    assert konular["FB.7.2.1"] == ["Fiziksel Anlamda İş"]
    assert konular["FB.7.2.2"] == ["Enerji ve Enerji Çeşitleri"]
    assert konular["FB.7.3.4"] == ["Kan Bağışının Toplum Açısından Önemi"]
    assert eslesme["FB.7.2.1"] == [{"kitap": 0, "unite": 2, "cerceve": 1, "konu": "Fiziksel Anlamda İş"}]
    assert uniteler[1]["cerceveler"][0]["ciktilar"] == ["FB.7.2.1", "FB.7.2.2"]


def test_konu_adi_cercevede_yoksa_eslesmedi_ve_denetim_reddeder():
    """Review Focus: kitapta karşılığı bulunamayan çıktı açıkça eslesmedi'ye yazılır; beklenmiyorsa harita yazılmaz."""
    uniteler = mkh.icindekiler_ayristir(ICINDEKILER)
    ciktilar = [dict(c, konu="Olmayan Çerçeve") if c["kod"] == "FB.7.1.3" else c for c in FEN_CIKTILARI]
    eslesme, eslesmedi = mkh.ciktilari_esle(uniteler, ciktilar, 0)
    assert eslesmedi == ["FB.7.1.3"] and "FB.7.1.3" not in eslesme
    harita = {"kitaplar": [], "eslesme": eslesme, "eslesmedi": eslesmedi}
    assert mkh.yapi_denetimi(harita, ciktilar) == ["beklenmeyen eşleşmeyen çıktı: FB.7.1.3"]
    assert mkh.yapi_denetimi(harita, ciktilar, beklenen_eslesmeyen=("FB.7.1.3",)) == []


def _mini_harita(**konu_degisikligi):
    konu = {"ad": "Konu A", "sayfa": 10, "son_sayfa": 12,
            "basliklar": [{"ad": "Kontrol Noktası", "tur": "kontrol", "amac": None, "sayfa": 11}], **konu_degisikligi}
    return {"kitaplar": [{"toplam_sayfa": 100, "sayfa_kaymasi": 1, "uniteler": [{"no": 1, "ad": "Ü", "sayfa": 9, "son_sayfa": 20,
            "cerceveler": [{"no": 1, "ad": "Ç", "sayfa": 9, "son_sayfa": 20, "ciktilar": ["X.7.1.1"], "basliklar": [],
                            "konular": [konu]}]}]}],
            "eslesme": {"X.7.1.1": [{"kitap": 0, "unite": 1, "cerceve": 1, "konu": "Konu A"}]}, "eslesmedi": []}


def test_yapi_denetimi_sayfa_baslik_ve_eksik_cikti():
    ciktilar = [{"kod": "X.7.1.1"}]
    assert mkh.yapi_denetimi(_mini_harita(), ciktilar) == []
    assert mkh.yapi_denetimi(_mini_harita(basliklar=[]), ciktilar) == ["konunun başlığı yok: Konu A"]
    assert mkh.yapi_denetimi(_mini_harita(basliklar=[]), ciktilar, basliksiz_konular=("Konu A",)) == []
    assert mkh.yapi_denetimi(_mini_harita(son_sayfa=30), ciktilar) == ["konu çerçevenin dışında: Konu A"]
    assert mkh.yapi_denetimi(_mini_harita(), [{"kod": "X.7.1.1"}, {"kod": "X.7.1.2"}]) == ["çıktı haritada yok: X.7.1.2"]
    yarim = {**_mini_harita(), "eslesme": {}, "eslesmedi": ["X.7.1.1"]}
    assert mkh.yapi_denetimi(yarim, ciktilar, beklenen_eslesmeyen=("X.7.1.1",)) == [
        "çıktıların yarısından çoğu eşleşmedi (1/1)"]


MINI_ICINDEKILER = ("İçindekiler\n1. Ünite      Deneme Ünitesi\nÖn Değerlendirme ........ 9\n1. Çerçeve Bir ......... 10\n"
                    "Konu Bir Anlama ........ 11\nÜnite Sonu Değerlendirme ....... 15\nSözlük ...... 16\n")
MINI_DUZEN = ('<?xml version="1.0" encoding="UTF-8"?>\n<pdf2xml>\n<page number="12" position="absolute" top="0" left="0" '
              'height="1169" width="829">\n<fontspec id="3" size="20" family="IUJFYC+Arial" color="#ffffff"/>\n'
              '<text top="80" left="119" width="200" height="26" font="3"><b>Konu Bir Anlama</b></text>\n'
              '<text top="400" left="119" width="140" height="26" font="3"><b>Kontrol Noktası</b></text>\n</page>\n</pdf2xml>\n')


@pytest.fixture
def deneme_kitabi(monkeypatch):
    ayar = {"ders": "Deneme", "beklenen_eslesmeyen": (), "basliksiz_konular": (), "kitaplar": [{
        "baslik": "Deneme 7", "pdf_url": "https://ornek.invalid/d.pdf", "kaynak_sayfa": None, "baski": "2026-2027",
        "sayfa_kaymasi": 1, "icindekiler_pdf_sayfalari": (8, 8), "duzen": {**FEN_DUZENI, "atla": ()}}]}
    monkeypatch.setitem(mkh.KITAPLAR, "deneme", ayar)
    monkeypatch.setattr(mkh, "tablo_oku", lambda: {
        "kaynak": {"meb_guncelleme": "2026-09-10T17:27"},
        "dersler": {"Deneme": {"sha256": "ab" * 32, "ciktilar": [
            {"kod": "D.7.1.1", "metin": "Konu bir anlama", "alan": None, "konu": "Çerçeve Bir"}]}}})
    return ayar


def test_main_haritayi_yazar_ve_onayi_kaydeder(deneme_kitabi, monkeypatch, tmp_path):
    monkeypatch.setattr(mkh, "pdf_girdisi", lambda yol, kitap: {
        "sha256": "f" * 64, "toplam_sayfa": 30, "icindekiler": MINI_ICINDEKILER, "xml": MINI_DUZEN})
    cikti = tmp_path / "deneme.json"
    assert mkh.main(["deneme", "--pdf", "1=/yok.pdf", "--cikti", str(cikti), "--denetim-kim", "Test"]) == 0
    h = json.loads(cikti.read_text(encoding="utf-8"))
    assert h["surum"] == 1 and h["anahtar"] == "deneme" and h["ders"] == "Deneme"
    assert h["denetim"] == {"kim": "Test", "tarih": date.today().isoformat()}
    assert h["senaryo_tablosu"] == {"meb_guncelleme": "2026-09-10T17:27", "ders_sha256": "ab" * 32}
    assert h["eslesme"] == {"D.7.1.1": [{"kitap": 0, "unite": 1, "cerceve": 1, "konu": "Konu Bir Anlama"}]}
    kitap = h["kitaplar"][0]
    assert (kitap["sha256"], kitap["toplam_sayfa"], kitap["sayfa_kaymasi"]) == ("f" * 64, 30, 1)
    konu = kitap["uniteler"][0]["cerceveler"][0]["konular"][0]
    assert konu["basliklar"] == [{"ad": "Kontrol Noktası", "tur": "kontrol", "amac": None, "sayfa": 11}]


def test_main_yapi_denetiminde_yazmaz(deneme_kitabi, monkeypatch, tmp_path, capsys):
    bos_duzen = MINI_DUZEN.replace("Kontrol Noktası", "Haber")
    monkeypatch.setattr(mkh, "pdf_girdisi", lambda yol, kitap: {
        "sha256": "f" * 64, "toplam_sayfa": 30, "icindekiler": MINI_ICINDEKILER, "xml": bos_duzen})
    cikti = tmp_path / "deneme.json"
    assert mkh.main(["deneme", "--pdf", "1=/yok.pdf", "--cikti", str(cikti)]) == 1
    assert not cikti.exists()
    assert "konunun başlığı yok: Konu Bir Anlama" in capsys.readouterr().err


def test_denetle_sha256_degisimini_yazar(tmp_path, capsys):
    """Review Focus (K12): MEB kitabı sessizce değişirse denetim dosyası yeni sha256'yı taşır."""
    pdf = tmp_path / "k.pdf"
    pdf.write_bytes(b"%PDF yeni baski")
    harita = tmp_path / "h.json"
    harita.write_text(json.dumps({"kitaplar": [{"baslik": "Fen 7", "pdf_url": "https://ornek.invalid/fen.pdf",
                                                "sha256": "0" * 64}]}), encoding="utf-8")
    denetim = tmp_path / "out" / "kitap_denetimi.json"
    assert mkh.denetle("fen-bilimleri", [pdf], harita, denetim) == 0
    kayit = json.loads(denetim.read_text(encoding="utf-8"))["fen-bilimleri"]
    assert kayit["kitaplar"] == [{"pdf_url": "https://ornek.invalid/fen.pdf",
                                  "sha256": hashlib.sha256(b"%PDF yeni baski").hexdigest()}]
    assert kayit["denetlendi"] == date.today().isoformat()
    assert "değişti: Fen 7" in capsys.readouterr().out


# --- 1. düzeltme turu: gerçek Fen 7-1'de ölçülen iki sessiz kaçak (PDF s. 95 ve s. 44) -----------------------------

def _sayfa_xml(*ogeler: str, fontlar: str = "") -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<pdf2xml>\n<page number="95" position="absolute" top="0" left="0" '
            'height="1169" width="829">\n<fontspec id="1" size="17" family="IUJFYC+Arial" color="#231f20"/>\n'
            '<fontspec id="2" size="17" family="EXFSOK+Arial" color="#231f20"/>\n'
            '<fontspec id="3" size="17" family="EXFSOK+ArialMT" color="#231f20"/>\n'
            '<fontspec id="6" size="20" family="EXFSOK+Arial" color="#ffffff"/>\n' + fontlar
            + "\n".join(ogeler) + "\n</page>\n</pdf2xml>\n")


def test_amac_etiketi_iki_kutuya_bolunmusse_okunur():
    """PDF s. 95: "Amaç:" etiketi "A" (sol 120) ve "maç:" (sol 132) olarak iki kutu gelir; amaç kaybolmamalı."""
    xml = _sayfa_xml(
        '<text top="74" left="119" width="300" height="26" font="6"><b>Performans Görevi: Sindirim Sistemini Tanıyalım</b></text>',
        '<text top="113" left="120" width="12" height="23" font="1"><b>A</b></text>',
        '<text top="113" left="132" width="43" height="23" font="2"><b>maç: </b></text>',
        '<text top="113" left="175" width="567" height="22" font="3">Sindirim sistemini oluşturan yapı ve organların '
        'görevlerine ait verileri açıklama</text>',
        '<text top="177" left="511" width="61" height="23" font="2"><b>Adımlar</b></text>')
    adaylar = mkh.basliklari_ayristir(xml, FEN_DUZENI)
    assert [(a["tur"], a["amac"]) for a in adaylar] == [
        ("etkinlik", "Sindirim sistemini oluşturan yapı ve organların görevlerine ait verileri açıklama")]
    # Bölünmüş etiketin "maç:" parçası amaç metnine karışmaz; aynı satırdaki başka kalın sözcük etikete yapışmaz.


def test_amac_etiketi_ayrik_kalin_sozcukle_birlesmez():
    xml = _sayfa_xml(
        '<text top="74" left="119" width="300" height="26" font="6"><b>Etkinlik Noktası-1</b></text>',
        '<text top="113" left="120" width="55" height="23" font="2"><b>Adımlar</b></text>',
        '<text top="113" left="300" width="40" height="23" font="2"><b>Amaç:</b></text>',
        '<text top="113" left="345" width="300" height="22" font="3">Bir şey yapma</text>')
    assert [a["amac"] for a in mkh.basliklari_ayristir(xml, FEN_DUZENI)] == ["Bir şey yapma"]


def test_baslik_boyu_bir_punto_buyuk_tolerans_gurultu_getirmez():
    """PDF s. 44: "Takımyıldızlar" size 21. Tolerans yalnız +1: 19 (tablo hücresi, s. 97), 22 (şekil), genişliği 0 olan
    (döndürülmüş şekil etiketi, s. 122) ve atla listesindeki şekil etiketi ("Sağlık Alanında", s. 25) başlık sayılmaz."""
    xml = _sayfa_xml(
        '<text top="79" left="122" width="139" height="29" font="5"><b>Takımyıldızlar</b></text>',
        '<text top="300" left="122" width="139" height="29" font="7"><b>Büyük Gürültü</b></text>',
        '<text top="500" left="122" width="139" height="29" font="8"><b>Küçük Gürültü</b></text>',
        '<text top="600" left="122" width="0" height="29" font="5"><b>Dönük Gürültü</b></text>',
        '<text top="700" left="110" width="156" height="29" font="5"><b>Sağlık Alanında</b></text>',
        fontlar='<fontspec id="5" size="21" family="IUJFYC+Arial" color="#fbcc2f"/>\n'
                '<fontspec id="7" size="22" family="IUJFYC+Arial" color="#fbcc2f"/>\n'
                '<fontspec id="8" size="19" family="IUJFYC+Arial" color="#231f20"/>\n')
    assert [(a["tur"], a["metin"]) for a in mkh.basliklari_ayristir(xml, FEN_DUZENI)] == [("diger", "Takımyıldızlar")]


def _etkinlikli_harita(*basliklar):
    harita = _mini_harita(basliklar=[dict(ad=ad, tur="etkinlik", amac=amac, sayfa=11) for ad, amac in basliklar])
    return harita


def test_yapi_denetimi_amacsiz_etkinlik_ve_performans_gorevini_bildirir_kesfi_bildirmez():
    ciktilar = [{"kod": "X.7.1.1"}]
    assert mkh.yapi_denetimi(_etkinlikli_harita(("Keşif Noktası: Konu", None), ("Etkinlik Noktası-1", "Bir amaç")), ciktilar) == []
    assert mkh.yapi_denetimi(_etkinlikli_harita(("Etkinlik Noktası-2", None)), ciktilar) == [
        "etkinliğin amacı yok: Etkinlik Noktası-2 s. 11"]
    assert mkh.yapi_denetimi(_etkinlikli_harita(("Performans Görevi: Sindirim Sistemini Tanıyalım", None)), ciktilar) == [
        "etkinliğin amacı yok: Performans Görevi: Sindirim Sistemini Tanıyalım s. 11"]
    # Çerçeve düzeyindeki başlıklar da denetlenir.
    harita = _etkinlikli_harita()
    harita["kitaplar"][0]["uniteler"][0]["cerceveler"][0]["basliklar"] = [
        {"ad": "Etkinlik Noktası-3", "tur": "etkinlik", "amac": None, "sayfa": 10}]
    assert mkh.yapi_denetimi(harita, ciktilar) == ["konunun başlığı yok: Konu A", "etkinliğin amacı yok: Etkinlik Noktası-3 s. 10"]


def test_etiketin_iki_satira_bolunmus_adi_birlesir():
    """PDF s. 128 (basılı 127): "Performans Görevi" (üst 146, sol 119) adının ilk satırı etiketin 18 px üstünde
    ("Solunum Sisteminin Sağlığı İçin", sol 362), ikinci satırı 5 px altında ("Neler Yapabiliriz?", sol 429). Ad kitaptaki
    satır sırasıyla birleşir; üst satır sol eşiğine takılıp düşmez, ayrı başlık da olmaz (K1)."""
    xml = _sayfa_xml(
        '<text top="128" left="362" width="301" height="26" font="6"><b>Solunum Sisteminin Sağlığı İçin</b></text>',
        '<text top="146" left="119" width="176" height="26" font="6"><b>Performans Görevi</b></text>',
        '<text top="151" left="429" width="162" height="26" font="6"><b>Neler Yapabiliriz?</b></text>',
        '<text top="186" left="120" width="55" height="23" font="2"><b>Amaç:</b></text>',
        '<text top="186" left="180" width="400" height="22" font="3">Solunum sisteminin sağlığını korumak için '
        'farkındalık oluşturma</text>',
        '<text top="400" left="119" width="153" height="26" font="6"><b>Bağlantı Noktası</b></text>')
    assert [(a["tur"], a["metin"], a["amac"]) for a in mkh.basliklari_ayristir(xml, FEN_DUZENI)] == [
        ("etkinlik", "Performans Görevi: Solunum Sisteminin Sağlığı İçin Neler Yapabiliriz?",
         "Solunum sisteminin sağlığını korumak için farkındalık oluşturma"),
        ("baglanti", "Bağlantı Noktası", None)]


def test_tek_satirlik_ad_iki_kutuya_bolunse_de_sozcuk_sirasi_korunur():
    """Adın kutuları aynı satırda ama üstleri 1–3 px farklı olabilir: satır içinde sıra sol'a göredir, üst'e göre değil."""
    xml = _sayfa_xml(
        '<text top="146" left="119" width="176" height="26" font="6"><b>Performans Görevi</b></text>',
        '<text top="149" left="429" width="100" height="26" font="6"><b>Sindirim</b></text>',
        '<text top="146" left="540" width="80" height="26" font="6"><b>Sistemi</b></text>',
        '<text top="186" left="120" width="55" height="23" font="2"><b>Amaç:</b></text>',
        '<text top="186" left="180" width="300" height="22" font="3">Bir şey yapma</text>')
    assert [a["metin"] for a in mkh.basliklari_ayristir(xml, FEN_DUZENI)] == ["Performans Görevi: Sindirim Sistemi"]


def test_etiketten_30_pxden_uzak_komsu_baslik_ada_karismaz():
    """Etiketin sağında ama üstü 31 px uzaktaki başlık boyu satır adın parçası değildir; ada katılmaz (sol eşiğinin
    sağında kaldığı için kendisi de başlık olmaz)."""
    xml = _sayfa_xml(
        '<text top="146" left="119" width="176" height="26" font="6"><b>Performans Görevi</b></text>',
        '<text top="146" left="354" width="200" height="26" font="6"><b>Asıl Ad</b></text>',
        '<text top="177" left="354" width="200" height="26" font="6"><b>Komşu Başlık</b></text>',
        '<text top="115" left="354" width="200" height="26" font="6"><b>Üst Komşu</b></text>',
        '<text top="200" left="120" width="55" height="23" font="2"><b>Amaç:</b></text>',
        '<text top="200" left="180" width="300" height="22" font="3">Bir şey yapma</text>')
    assert [a["metin"] for a in mkh.basliklari_ayristir(xml, FEN_DUZENI)] == ["Performans Görevi: Asıl Ad"]
