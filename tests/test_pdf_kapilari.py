"""Kapsam kılavuzu PDF kapıları (Kanun K1, K3, K5, K10): araç çıktısı ayrıştırıcıları, PDF'siz fikstürlerle."""
from src import pdf_kapilari as pk

PDFFONTS = """name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
AAAAAA+IBMPlexSans-Regular           CID TrueType      Identity-H       yes yes yes      4  0
BAAAAA+IBMPlexMono-Regular           CID TrueType      Identity-H       yes yes yes      5  0
DejaVuSans                           TrueType          WinAnsi          no  no  yes      6  0
"""

PDFINFO = """Title:           Fen Bilimleri · 1. yazılı
Tagged:          yes
Pages:           9
"""

QPDF = {"qpdf": [{"jsonversion": 2}, {
    "trailer": {"value": {"/Root": "23 0 R", "/Size": 32}},
    "obj:23 0 R": {"value": {"/Lang": "u:tr", "/Type": "/Catalog"}}}]}

# qpdf --json --json-key=outlines: her yer imi bir başlık öğesinden (h1–h6) doğar; destpageposfrom1 gösterdiği sayfa.
ANAHATLAR = {"outlines": [{"title": "Kapsam Kılavuzu", "destpageposfrom1": 1, "kids": [
    {"title": "Senaryo Karşılaştırması", "destpageposfrom1": 3, "kids": []},
    {"title": "1. Ünite · Uzay Çağı", "destpageposfrom1": 3, "kids": []}]}]}

SAYFALAR = (
    "Kapsam Kılavuzu\nFen Bilimleri · 1. yazılı · 2. senaryo\nTEDY · MEB tablosu 10.09.2026      s. 1/4\f"
    "İçindekiler\nSenaryo karşılaştırması 3\n1. Ünite · Uzay Çağı 3\n2. Ünite · Kuvvet ve Enerjiyi Keşfedelim 9\n"
    "TEDY · MEB tablosu 10.09.2026      s. 2/4\f"
    "Senaryo karşılaştırması\ntablo satırları\n1. Ünite · Uzay Çağı\nTEDY · MEB tablosu 10.09.2026      s. 3/4\f"
    "FB.7.1.1 Uzay Teknolojileri\nKitapta: s. 16–24\nTEDY · MEB tablosu 10.09.2026      s. 4/4\f")


def test_pdffonts_gomulu_ve_onek_atilir():
    assert pk.pdffonts_ayristir(PDFFONTS) == [
        {"ad": "IBMPlexSans-Regular", "gomulu": True}, {"ad": "IBMPlexMono-Regular", "gomulu": True},
        {"ad": "DejaVuSans", "gomulu": False}]
    assert pk.pdffonts_ayristir("") == []


def test_pdfinfo_etiket_ve_sayfa():
    assert pk.etiketli_mi(PDFINFO) is True
    assert pk.sayfa_sayisi(PDFINFO) == 9
    assert pk.etiketli_mi("Tagged:          no\n") is False
    assert pk.sayfa_sayisi("") == 0


def test_qpdf_dil_ve_yer_imleri():
    assert pk.pdf_dili(QPDF) == "tr"
    assert pk.pdf_dili({"qpdf": [{}]}) is None
    assert pk.yer_imleri(ANAHATLAR) == ["Kapsam Kılavuzu", "Senaryo Karşılaştırması", "1. Ünite · Uzay Çağı"]


def test_yer_imi_baslik_ve_sayfalari_okunur():
    assert pk.yer_imi_sayfalari(ANAHATLAR) == [(1, "Kapsam Kılavuzu"), (3, "Senaryo Karşılaştırması"),
                                               (3, "1. Ünite · Uzay Çağı")]
    # Gösterdiği sayfa belli olmayan yer imi başlık yeri vermez.
    assert pk.yer_imi_sayfalari({"outlines": [{"title": "x", "kids": []}]}) == []
    assert pk.yer_imi_sayfalari({}) == []


def test_sayfa_metinleri_son_bos_parca_atilir():
    assert len(pk.sayfa_metinleri(SAYFALAR)) == 4


def test_eksik_baslik_katlamayla_aranir():
    sayfalar = pk.sayfa_metinleri(SAYFALAR)
    assert pk.eksik_basliklar(sayfalar, ["Uzay Teknolojileri", "uzay çağı"]) == []
    assert pk.eksik_basliklar(sayfalar, ["Fiziksel Anlamda İş"]) == ["Fiziksel Anlamda İş"]


def test_yetim_baslik_alt_bilgi_sayilmaz_son_sayfa_yetim_degil():
    sayfalar = pk.sayfa_metinleri(SAYFALAR)
    basliklar = pk.yer_imi_sayfalari(ANAHATLAR)
    # 3. sayfanın son anlamlı satırı bir ünite başlığı: yetim. 4. (son) sayfa sayılmaz.
    assert pk.yetim_basliklar(sayfalar, basliklar) == [(3, "1. Ünite · Uzay Çağı")]
    assert pk.yetim_basliklar(sayfalar, [(4, "FB.7.1.1 Uzay Teknolojileri"), (4, "Kitapta: s. 16–24")]) == []


def test_yetim_baslik_yalniz_baslik_olarak_isaretli_ogeyi_sayar():
    """D5: konu adıyla biten düz satır (çalışma planı, duyuru doğrulaması, ebeveyn özeti) sayfa sonunda olsa da
    kusur değildir; yetimlik başlık işaretinden (PDF yer imi = h öğesi) gelir, metnin kendisinden değil."""
    duz_satir_sayfa_sonunda = ("Çalışma planı\nPazartesi: Tekrar\nÇarşamba · Uzay Teknolojileri\n"
                               "TEDY · MEB tablosu 10.09.2026      s. 1/3\f"
                               "Devam eden sayfa\nTEDY · MEB tablosu 10.09.2026      s. 2/3\f"
                               "Son sayfa\nTEDY · MEB tablosu 10.09.2026      s. 3/3\f")
    sayfalar = pk.sayfa_metinleri(duz_satir_sayfa_sonunda)
    # "Uzay Teknolojileri" başka bir sayfada gerçek başlıktır; 1. sayfadaki düz satır bu başlığın yetimi sayılmaz.
    assert pk.yetim_basliklar(sayfalar, [(2, "Uzay Teknolojileri")]) == []
    # Başlık işareti olmayan metin hiçbir zaman yetim değildir.
    assert pk.yetim_basliklar(sayfalar, []) == []
    # Aynı satır gerçekten başlık olarak işaretliyse (ör. bir h4) sayfa sonundaki başlık yetimdir.
    assert pk.yetim_basliklar(sayfalar, [(1, "Çarşamba · Uzay Teknolojileri")]) == [(1, "Çarşamba · Uzay Teknolojileri")]


def test_yetim_baslik_iki_satira_bolunen_baslik_son_satirlardan_bulunur():
    sayfalar = pk.sayfa_metinleri(
        "Gövde\nFB.7.1.1 Uzay araştırmaları için geliştirilen\nteknolojileri karşılaştırabilme · 2 soru\n"
        "TEDY · damga      s. 1/2\fSon\f")
    baslik = "FB.7.1.1 Uzay araştırmaları için geliştirilen teknolojileri karşılaştırabilme · 2 soru"
    assert pk.yetim_basliklar(sayfalar, [(1, baslik)]) == [(1, baslik)]


def test_icindekiler_gosterilen_sayfada_baslik_olmali():
    sayfalar = pk.sayfa_metinleri(SAYFALAR)
    assert pk.icindekiler_hatalari(sayfalar, ["Senaryo karşılaştırması", "1. Ünite · Uzay Çağı"]) == []
    hatalar = pk.icindekiler_hatalari(sayfalar, ["2. Ünite · Kuvvet ve Enerjiyi Keşfedelim", "Kaynaklar"])
    assert hatalar == ["2. Ünite · Kuvvet ve Enerjiyi Keşfedelim: İçindekiler s. 9 diyor, başlık o sayfada yok",
                       "İçindekiler'de sayfa numarası yok: Kaynaklar"]
    assert pk.icindekiler_hatalari(["metin"], ["x"]) == ["İçindekiler sayfası yok"]


def test_en_kucuk_punto_kullanilan_yazi_tiplerinden():
    xml = ('<page number="1"><fontspec id="0" size="10" family="A" color="#000"/>'
           '<fontspec id="1" size="6" family="A" color="#000"/><fontspec id="2" size="8" family="A" color="#000"/>'
           '<text top="1" left="1" width="1" height="1" font="0">a</text>'
           '<text top="2" left="1" width="1" height="1" font="2">b</text></page>')
    assert pk.en_kucuk_punto(xml) == 8
    assert pk.en_kucuk_punto("<page/>") is None


def test_kusurlar_rapordan_okunur():
    temiz = {"sayfa": 4, "yazi_tipleri": ["IBMPlexSans"], "gomulu_degil": [], "yabanci_yazi_tipi": [], "etiketli": True,
             "dil": "tr", "yer_imi": 3, "yetim": [], "icindekiler": [], "eksik_baslik": [], "en_kucuk_punto": 8}
    assert pk.kusurlar(temiz) == []
    kirli = {**temiz, "gomulu_degil": ["DejaVuSans"], "yabanci_yazi_tipi": ["DejaVuSans"], "etiketli": False,
             "dil": None, "yer_imi": 0, "yetim": [(3, "1. Ünite")], "icindekiler": ["x"], "en_kucuk_punto": 7}
    assert pk.kusurlar(kirli) == [
        "gömülmemiş yazı tipi: DejaVuSans", "Plex dışı yazı tipi: DejaVuSans", "PDF etiketli değil",
        "PDF dili tr değil: None", "yer imi yok", "yetim başlık s. 3: 1. Ünite", "x", "en küçük punto 7 < 7,5"]
    assert pk.kusurlar({**temiz, "icindekiler": ["x"]}, icindekiler_beklenir=False) == []


def test_kusurlar_olculemeyen_deger_gecer_sayilmaz():
    """Ölçülemeyen değer kusurdur (Görev 2 ertelemesi): boş pdffonts, okunamayan punto ya da 0 sayfa geçer sayılmaz."""
    temiz = {"sayfa": 4, "yazi_tipleri": ["IBMPlexSans"], "gomulu_degil": [], "yabanci_yazi_tipi": [], "etiketli": True,
             "dil": "tr", "yer_imi": 3, "yetim": [], "icindekiler": [], "eksik_baslik": [], "en_kucuk_punto": 8}
    assert pk.kusurlar({**temiz, "sayfa": 0, "yazi_tipleri": [], "en_kucuk_punto": None}) == [
        "sayfa sayısı okunamadı", "yazı tipi okunamadı", "en küçük punto ölçülemedi"]


# pdftohtml -xml -zoom 1: konumlar punto (A4 = 595 × 842). Kenar boşlukları 18 mm (≈ 51 pt) üstte, 20 mm (≈ 57 pt) altta.
def _xml(*metinler: tuple[int, str]) -> str:
    """(üst konum, yazı tipi kimliği) çiftlerinden tek sayfalık pdftohtml çıktısı."""
    return ('<page number="1" position="absolute" top="0" left="0" height="841" width="594">'
            '<fontspec id="0" size="10" family="AAAAAA+IBMPlexSans" color="#000"/>'
            '<fontspec id="1" size="8" family="DejaVuSans" color="#000"/>'
            + "".join(f'<text top="{t}" left="45" width="40" height="11" font="{f}">x</text>' for t, f in metinler)
            + "</page>")


def test_yabanci_yazi_tipi_kenarda_izinli_olan_yalniz_ust_alt_bilgide():
    """Düz yolda (B) Chrome'un üst/alt bilgi şablonu DejaVu Sans'a düşer (web yazı tipi okuyamaz); yalnız kenar
    boşluğundaki metinde izinlidir. Gövde metni DejaVu'ya düşerse kusurdur."""
    fontlar = [{"ad": "IBMPlexSans", "gomulu": True}, {"ad": "DejaVuSans", "gomulu": True}]
    kenarda = _xml((20, 1), (400, 0), (815, 1))
    assert pk.yabanci_yazi_tipleri(fontlar, kenarda) == ["DejaVuSans"]
    assert pk.yabanci_yazi_tipleri(fontlar, kenarda, kenarda_izinli=("DejaVuSans",)) == []
    govdede = _xml((20, 1), (400, 1), (815, 1))
    assert pk.yabanci_yazi_tipleri(fontlar, govdede, kenarda_izinli=("DejaVuSans",)) == ["DejaVuSans"]


def test_arac_zaman_asimi_anlamli_hata(monkeypatch):
    def takil(*a, **k):
        raise pk.subprocess.TimeoutExpired(cmd=a[0], timeout=k.get("timeout"))
    monkeypatch.setattr(pk.subprocess, "run", takil)
    try:
        pk._calistir("pdftohtml", "/tmp/x.pdf")
    except pk.DenetimHatasi as e:
        assert str(e) == "pdftohtml 120 s içinde bitmedi"
    else:
        raise AssertionError("DenetimHatasi bekleniyordu")
