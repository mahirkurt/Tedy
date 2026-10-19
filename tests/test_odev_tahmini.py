"""Ödev tahmini (akşam çalışma planı, Görev 3): yedek, kapı, önbellek, bütçe, okur düzeltmesi."""
import json
import time
from datetime import date

from src.odev_tahmini import (OdevTahmini, TahminDeposu, YEDEK_ILK_ADIM, kural_tahmini,
                              odev_metni, uydurma_kapisi)

BUGUN = date(2026, 10, 19)
SATIR = {"Ders Adı": "Matematik", "Ödev Başlığı": "Kesirler", "Ödev Son Teslim Tarihi": "22.10.2026 08:00",
         "homework_key": "mat|kesirler|22.10", "detail": {"description": "Sayfa 32, 1-10 arası", "attachments": [{"name": "kesir.pdf"}]}}


class SahteOkuyucu:
    model = "sahte-model"

    def __init__(self, sonuc):
        self.sonuc, self.cagri = sonuc, 0

    def oku(self, metin, bugun, zaman_asimi):
        self.cagri += 1
        from src.odev_tahmini import OkumaSonucu
        return OkumaSonucu(self.sonuc, 1000, 100)


def test_odev_metni_icerir():
    m = odev_metni(SATIR)
    assert "Matematik" in m and "Kesirler" in m and "Sayfa 32" in m and "kesir.pdf" in m


def test_kural_tahmini_yarin_teslim_30dk_orta():
    t = kural_tahmini({"Ödev Son Teslim Tarihi": "20.10.2026 08:00", "Ders Adı": "Matematik"}, BUGUN)
    assert (t.dakika, t.zorluk, t.kaynak) == (30, "orta", "yedek")


def test_kural_tahmini_uzak_teslim_20dk():
    t = kural_tahmini({"Ödev Son Teslim Tarihi": "30.10.2026 08:00"}, BUGUN)
    assert t.dakika == 20


def test_kapi_metinde_olmayan_sayiyi_reddeder():
    t = OdevTahmini(25, "zor", "Sayfa 47'deki 5 soruyu çöz", ["…"], "model")
    assert uydurma_kapisi(t, "Kesirler alıştırması, sayfa 32").ilk_adim == YEDEK_ILK_ADIM


def test_kapi_metindeki_sayiyi_kabul():
    t = OdevTahmini(25, "zor", "Sayfa 32'deki ilk 3 soruyu çöz", [], "model")
    assert "32" in uydurma_kapisi(t, "Kesirler, sayfa 32, 3 soru").ilk_adim


def test_kapi_gecmeyen_parcayi_dusurur():
    t = OdevTahmini(25, "orta", "Yönergeyi oku", ["Sayfa 32'yi oku", "99. soruyu çöz"], "model")
    s = uydurma_kapisi(t, "sayfa 32")
    assert s.parcalar == ["Sayfa 32'yi oku"] and s.ilk_adim == "Yönergeyi oku"


def test_bos_aciklama_yedek_ilk_adim():
    t = kural_tahmini({"Ödev Başlığı": "", "detail": {"description": ""}}, BUGUN)
    assert t.ilk_adim == "Ödevin yönergesini ve ekini aç"


def test_onbellek_ikinci_cagri_modeli_cagirmaz(tmp_path):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte)
    d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    assert sahte.cagri == 1 and d.tahmin(SATIR, BUGUN).dakika == 40
    assert d.tahmin(SATIR, BUGUN).kaynak == "model"


def test_yeni_depo_ayni_onbellegi_okur(tmp_path):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    TahminDeposu(tmp_path, sahte).isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    d2 = TahminDeposu(tmp_path, SahteOkuyucu(None))
    assert d2.tahmin(SATIR, BUGUN).dakika == 40


def test_tavan_dolunca_cagri_yok(tmp_path):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte, tavan=0.0)
    d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    assert sahte.cagri == 0 and d.tahmin(SATIR, BUGUN).kaynak == "yedek"


def test_sure_yoksa_cagri_yok(tmp_path):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte)
    d.isit([SATIR], BUGUN, bitis=time.monotonic() + 1)
    assert sahte.cagri == 0


def test_okur_suresi_modeli_ezer(tmp_path):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte)
    d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    d.okur_suresi_yaz(SATIR["homework_key"], 55)
    t = d.tahmin(SATIR, BUGUN)
    assert t.kaynak == "okur" and t.dakika == 55 and t.ilk_adim == "Yönergeyi oku"
    assert json.loads((tmp_path / "output/odev_tahmin_okur.json").read_text()) == {SATIR["homework_key"]: 55}


def test_tahmin_dakikasi_sinirli(tmp_path):
    for ham, beklenen in ((0, 5), (400, 120)):
        sahte = SahteOkuyucu(OdevTahmini(ham, "zor", "Yönergeyi oku", [], "model"))
        d = TahminDeposu(tmp_path / str(ham), sahte)
        d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
        assert d.tahmin(SATIR, BUGUN).dakika == beklenen


def test_anahtarsiz_satir_icin_turetilmis_anahtar(tmp_path):
    satir = {k: v for k, v in SATIR.items() if k != "homework_key"}
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte)
    d.isit([satir], BUGUN, bitis=time.monotonic() + 30)
    d.isit([satir], BUGUN, bitis=time.monotonic() + 30)
    assert sahte.cagri == 1


def test_okuyucu_hatasi_yedege_duser_ve_yutulur(tmp_path):
    class Bozuk:
        model = "x"
        def oku(self, *a):
            raise RuntimeError("ağ")
    d = TahminDeposu(tmp_path, Bozuk())
    ozet = d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    assert d.tahmin(SATIR, BUGUN).kaynak == "yedek" and ozet["hata"] == 1 and ozet["son_hata"]


def test_gercek_okuyucu_testte_yasak():
    import pytest
    from src.odev_tahmini import ClaudeTahminOkuyucu
    with pytest.raises(AssertionError):
        ClaudeTahminOkuyucu().oku("x", BUGUN, 5)


def test_claude_okuyucu_yaniti_ayristirir(monkeypatch):
    from types import SimpleNamespace as N
    from src import odev_tahmini as m
    govde = json.dumps({"dakika": 35, "zorluk": "orta", "ilk_adim": "Defterini aç", "parcalar": ["a"]})
    yanit = N(content=[N(type="text", text=govde)], usage=N(input_tokens=300, output_tokens=40), stop_reason="end_turn")
    istemci = N(messages=N(create=lambda **k: yanit))
    # conftest yasağını yalnız bu testte kaldır: ağ yok, sahte istemci
    monkeypatch.undo()
    o = m.ClaudeTahminOkuyucu(istemci_fabrikasi=lambda **k: istemci)
    s = o.oku("Ders: Fen", BUGUN, 10)
    assert (s.tahmin.dakika, s.tahmin.kaynak, s.girdi, s.cikti) == (35, "model", 300, 40)


def test_okuyucu_hata_nedeni_ozette(tmp_path):
    class Bozuk:
        model = "x"
        def oku(self, *a):
            raise RuntimeError("401 anahtar geçersiz")
    ozet = TahminDeposu(tmp_path, Bozuk()).isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    assert "RuntimeError" in ozet["son_hata"] and "401" in ozet["son_hata"]


def test_yazma_hatasi_isit_disina_cikmaz(tmp_path, monkeypatch):
    from src import odev_tahmini as m
    def patla(yol, degisiklik):
        if degisiklik:  # ön sınama (boş yazım) geçer, asıl kayıt düşer
            raise OSError("disk dolu")
    monkeypatch.setattr(m, "_birlestir_yaz", patla)
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    satir2 = dict(SATIR, homework_key="baska")
    ozet = TahminDeposu(tmp_path, sahte).isit([SATIR, satir2], BUGUN, bitis=time.monotonic() + 30)
    assert ozet["durdu"] == "yazma" and "disk dolu" in ozet["son_hata"] and sahte.cagri == 1


def test_kapi_kesmeden_sonra_sinar():
    # Sınanan, saklanan metindir. Kesilen kuyruktaki sayı saklanmaz, o yüzden reddetmez...
    t = OdevTahmini(25, "orta", "a" * 80 + " 99", ["b" * 60 + " 99"], "model")
    s = uydurma_kapisi(t, "sayfa 32")
    assert s.ilk_adim == "a" * 80 and s.parcalar == ["b" * 60]
    # ...ve kesim sayıyı bölerse ("320" -> "32") saklanan "32" ya da "3" metinde aranır.
    t = OdevTahmini(25, "orta", "a" * 77 + " 320", ["b" * 57 + " 320"], "model")
    s = uydurma_kapisi(t, "sayfa 7")
    assert s.ilk_adim == YEDEK_ILK_ADIM and s.parcalar == []
    assert len(s.ilk_adim) <= 80


def test_yazilamayan_onbellek_model_cagirmaz(tmp_path, monkeypatch):
    from src import odev_tahmini as m
    def patla(*a, **k):
        raise OSError("salt okunur")
    monkeypatch.setattr(m, "_birlestir_yaz", patla)
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    ozet = TahminDeposu(tmp_path, sahte).isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    assert sahte.cagri == 0 and ozet["durdu"] == "yazma" and "salt okunur" in ozet["son_hata"]


def test_onbellek_okuma_hatasi_isit_disina_cikmaz(tmp_path, monkeypatch):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte)
    def patla():
        raise ValueError("bozuk")
    monkeypatch.setattr(d, "_onbellek", patla)
    ozet = d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    assert sahte.cagri == 0 and "bozuk" in ozet["son_hata"]


def test_defter_hatasi_isit_disina_cikmaz(tmp_path, monkeypatch):
    sahte = SahteOkuyucu(OdevTahmini(40, "zor", "Yönergeyi oku", [], "model"))
    d = TahminDeposu(tmp_path, sahte)
    def patla():
        raise OSError("kilit")
    monkeypatch.setattr(d.defter, "izin_var", patla)
    ozet = d.isit([SATIR], BUGUN, bitis=time.monotonic() + 30)
    assert sahte.cagri == 0 and ozet["durdu"] == "defter" and "kilit" in ozet["son_hata"]
