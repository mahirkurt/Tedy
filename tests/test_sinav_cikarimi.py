"""src/sinav_cikarimi: the Haiku reader (fake client), the cache, the monthly
ledger and the deterministic anti-fabrication gate. No test reaches the API."""
import json
from datetime import date
from types import SimpleNamespace

import pytest

import src.sinav_cikarimi as sc
from src.claude_api import ClaudeYapilandirilmamis
from src.sinav_cikarimi import (Bulgu, CikarimHatasi, ClaudeSinavOkuyucu, OkumaSonucu, SinavCikarici,
                                uydurma_kapisi)
from src.sinav_kaynaklari import Aday
from tests.sinav_fikstur import ING_KARTI, KTT_KARTI

BUGUN = date(2026, 10, 16)
KTT = Aday(KTT_KARTI, "Matematik", date(2026, 10, 5), "ders_karti", [{"bolum": "ders_icerikleri_haftalar"}])
ING = Aday(ING_KARTI, "İngilizce", date(2026, 9, 21), "ders_karti", [])


def _satir(**kw):
    s = {"ders": "Matematik", "tur": "konu_tarama", "baslik": "Matematik KTT",
         "tarih_ifadesi": "15 EKİM PERŞEMBE", "tarih": "2026-10-16", "saat": "",
         "konular": ["Tam sayılar farklı gösterimleri", "Mutlak değer", "Üslü sayılar"],
         "alinti": "15 EKİM PERŞEMBE günü yapılacak olan Matematik KTT"}
    s.update(kw)
    return s


# --- uydurma kapısı ------------------------------------------------------------

def test_kapi_bizim_tarihimiz_kazanir_konu_kaynakta_olmali():
    [b] = uydurma_kapisi([_satir()], KTT, BUGUN)
    assert (b.ders, b.tur, b.baslik, b.tarih, b.hafta, b.saat) == \
        ("Matematik", "konu_tarama", "Matematik KTT", date(2026, 10, 15), None, None)
    assert b.konular == ["Tam sayılar farklı gösterimleri", "Mutlak değer"]
    assert b.aday is KTT


def test_kapi_kaynakta_olmayan_alinti_kaydi_atar():
    assert uydurma_kapisi([_satir(alinti="Yarın Matematik yazılısı var")], KTT, BUGUN) == []


def test_kapi_kaynakta_olmayan_tarih_ifadesi_alintiya_duser():
    [b] = uydurma_kapisi([_satir(tarih_ifadesi="16 Ekim Cuma")], KTT, BUGUN)
    assert b.tarih == date(2026, 10, 15)


def test_kapi_goreli_hafta():
    [b] = uydurma_kapisi([_satir(ders="İngilizce", tur="kisa_sinav", baslik="Irregular Verbs Quiz",
                                 tarih_ifadesi="Next week", tarih="", konular=["Modal verbs"],
                                 alinti="Next week, you will have an Irregular Verbs Quiz")], ING, BUGUN)
    assert (b.tarih, b.hafta, b.konular, b.baslik) == (None, date(2026, 9, 28), [], "Irregular Verbs Quiz")


def test_kapi_yalniz_gecmis_tarih_kaydi_atar():
    aday = Aday("Öğretmen | 16.10.2026\n15 Ekim'de yapılan KTT sonuçları açıklandı.", "Matematik",
                date(2026, 10, 16), "ders_karti", [])
    satir = _satir(tarih_ifadesi="15 Ekim'de", alinti="15 Ekim'de yapılan KTT sonuçları açıklandı.", konular=[])
    assert uydurma_kapisi([satir], aday, BUGUN) == []


def test_kapi_saat_kaynakta_yoksa_atilir_varsa_tutulur():
    [b] = uydurma_kapisi([_satir(saat="09:00")], KTT, BUGUN)
    assert b.saat is None
    aday = Aday("Matematik yazılısı 20 Ekim 10.30'da", "Matematik", date(2026, 10, 12), "ders_karti", [])
    [b] = uydurma_kapisi([_satir(tur="yazili", baslik="Matematik yazılısı", tarih_ifadesi="20 Ekim",
                                 saat="10.30", konular=[], alinti="Matematik yazılısı 20 Ekim 10.30'da")],
                         aday, BUGUN)
    assert (b.tarih, b.saat) == (date(2026, 10, 20), "10:30")


def test_kapi_baslik_kaynakta_yoksa_turden_kurulur():
    [b] = uydurma_kapisi([_satir(baslik="Matematik 2. Yazılı")], KTT, BUGUN)
    assert b.baslik == "Matematik KTT"


def test_kapi_bilinmeyen_tur_diger():
    [b] = uydurma_kapisi([_satir(tur="quiz")], KTT, BUGUN)
    assert b.tur == "diger"


def test_kapi_ek_dersi_metinde_gecmeli():
    ek = Aday("Fen yazılı konuları 20 Ekim: Uzay Çağı", None, date(2026, 10, 12), "ek", [])
    satir = _satir(ders="Fen Bilimleri", tur="yazili", baslik="Fen yazılı", tarih_ifadesi="20 Ekim",
                   konular=["Uzay Çağı"], alinti="Fen yazılı konuları 20 Ekim")
    [b] = uydurma_kapisi([satir], ek, BUGUN)
    assert b.ders == "Fen Bilimleri"
    [b] = uydurma_kapisi([dict(satir, ders="Matematik")], ek, BUGUN)
    assert b.ders == "Genel"


def test_kapi_ders_kartinin_dersi_esastir():
    [b] = uydurma_kapisi([_satir(ders="Fen Bilimleri")], KTT, BUGUN)
    assert b.ders == "Matematik"


# --- okuyucu -------------------------------------------------------------------

class SahteIstemci:
    def __init__(self, yanit=None, hata=None):
        self.cagrilar, self.yanit, self.hata = [], yanit, hata
        self.messages = self

    def create(self, **kw):
        self.cagrilar.append(kw)
        if self.hata:
            raise self.hata
        return self.yanit


def _yanit(satirlar, stop="end_turn"):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"sinavlar": satirlar}))],
                           stop_reason=stop, usage=SimpleNamespace(input_tokens=2000, output_tokens=300))


def test_okuyucu_yapilandirilmis_cikti_ister(monkeypatch):
    monkeypatch.delenv("TEDY_SINAV_MODEL", raising=False)
    istemci = SahteIstemci(_yanit([_satir()]))
    okuyucu = ClaudeSinavOkuyucu(istemci_fabrikasi=lambda timeout, max_retries: istemci)
    sonuc = okuyucu.oku(KTT, BUGUN, zaman_asimi=20)
    assert sonuc == OkumaSonucu([_satir()], 2000, 300)
    [cagri] = istemci.cagrilar
    assert cagri["model"] == "claude-haiku-4-5" == okuyucu.model
    assert cagri["output_config"] == {"format": {"type": "json_schema", "schema": sc.CIKARIM_SEMASI}}
    istem = cagri["messages"][0]["content"]
    assert "2026-10-16" in istem and "2026-10-05" in istem and "Matematik" in istem and "MUTLAK DEĞER" in istem


def test_okuyucu_model_ortamdan(monkeypatch):
    monkeypatch.setenv("TEDY_SINAV_MODEL", "baska-model")
    assert ClaudeSinavOkuyucu(istemci_fabrikasi=lambda **k: None).model == "baska-model"


@pytest.mark.parametrize("istemci", [
    SahteIstemci(_yanit([], stop="refusal")),
    SahteIstemci(SimpleNamespace(content=[SimpleNamespace(type="text", text="json değil")],
                                 stop_reason="end_turn", usage=SimpleNamespace(input_tokens=1, output_tokens=1))),
])
def test_okuyucu_hatasi_cikarim_hatasi(istemci):
    okuyucu = ClaudeSinavOkuyucu(istemci_fabrikasi=lambda timeout, max_retries: istemci)
    with pytest.raises(CikarimHatasi):
        okuyucu.oku(KTT, BUGUN, zaman_asimi=20)


def test_okuyucu_anahtar_yoksa_cikarim_hatasi():
    def fabrika(timeout, max_retries):
        raise ClaudeYapilandirilmamis("ANTHROPIC_API_KEY ayarlı değil")
    with pytest.raises(CikarimHatasi):
        ClaudeSinavOkuyucu(istemci_fabrikasi=fabrika).oku(KTT, BUGUN, zaman_asimi=20)


# --- çıkarıcı: önbellek, defter, süre ---------------------------------------------

class SahteOkuyucu:
    model = "claude-haiku-4-5"

    def __init__(self, satirlar=None, hata_metni=None):
        self.cagrilar, self.satirlar, self.hata_metni = [], satirlar, hata_metni

    def oku(self, aday, bugun, zaman_asimi):
        self.cagrilar.append(aday.anahtar)
        if self.hata_metni and self.hata_metni in aday.metin:
            raise CikarimHatasi("ağ")
        return OkumaSonucu(self.satirlar if self.satirlar is not None else [_satir()], 2000, 300)


class Saat:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def _cikarici(tmp_path, okuyucu, tavan=2.0):
    return SinavCikarici(tmp_path, okuyucu, tavan=tavan, saat=Saat())


def test_cikarici_onbellek_ikinci_turda_ucret_yok(tmp_path):
    okuyucu = SahteOkuyucu()
    ilk = _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    assert (ilk.aday, ilk.incelenen, ilk.incelenmedi, len(ilk.bulgular)) == (1, 1, 0, 1)
    assert ilk.butce_usd == pytest.approx((2000 * 1.0 + 300 * 5.0) / 1_000_000)
    ikinci = _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    assert len(okuyucu.cagrilar) == 1
    assert (ikinci.incelenen, len(ikinci.bulgular)) == (1, 1)
    assert ikinci.butce_usd == pytest.approx(ilk.butce_usd)


def test_cikarici_istem_surumu_degisince_yeniden_sorar(tmp_path, monkeypatch):
    okuyucu = SahteOkuyucu()
    _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    monkeypatch.setattr(sc, "ISTEM_SURUMU", sc.ISTEM_SURUMU + 1)
    _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    assert len(okuyucu.cagrilar) == 2


def test_cikarici_tavan_dolunca_incelenmedi(tmp_path):
    okuyucu = SahteOkuyucu()
    sonuc = _cikarici(tmp_path, okuyucu, tavan=0.0).cikar([KTT, ING], BUGUN, bitis=2000)
    assert (okuyucu.cagrilar, sonuc.incelenen, sonuc.incelenmedi, sonuc.bulgular) == ([], 0, 2, [])


def test_cikarici_sure_bitince_incelenmedi(tmp_path):
    okuyucu = SahteOkuyucu()
    sonuc = _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=1005)
    assert (okuyucu.cagrilar, sonuc.incelenmedi) == ([], 1)


def test_cikarici_model_hatasi_digerlerini_durdurmaz(tmp_path):
    okuyucu = SahteOkuyucu(satirlar=[], hata_metni="KTT-1")
    sonuc = _cikarici(tmp_path, okuyucu).cikar([KTT, ING], BUGUN, bitis=2000)
    assert (sonuc.incelenen, sonuc.incelenmedi, sonuc.hatalar) == (1, 1, ["ağ"])
    assert not (tmp_path / "output/sinav_cikarim_onbellegi.json").read_text(encoding="utf-8").count(KTT.anahtar)


# --- düzeltme turu 1 ---------------------------------------------------------------

def _gercek_cikarici(tmp_path, istemci):
    okuyucu = ClaudeSinavOkuyucu(istemci_fabrikasi=lambda timeout, max_retries: istemci)
    return SinavCikarici(tmp_path, okuyucu, tavan=2.0, saat=Saat()), okuyucu


@pytest.mark.parametrize("yanit", [
    _yanit([], stop="refusal"),
    _yanit([], stop="max_tokens"),
    SimpleNamespace(content=[SimpleNamespace(type="text", text="json değil")],
                    stop_reason="end_turn", usage=SimpleNamespace(input_tokens=2000, output_tokens=300)),
])
def test_faturalanan_hatali_yanit_deftere_yazilir_ve_tekrar_sorulmaz(tmp_path, yanit):
    istemci = SahteIstemci(yanit)
    cikarici, _ = _gercek_cikarici(tmp_path, istemci)
    ilk = cikarici.cikar([KTT], BUGUN, bitis=2000)
    assert (ilk.incelenen, ilk.incelenmedi, ilk.bulgular, len(ilk.hatalar)) == (0, 1, [], 1)
    assert ilk.butce_usd == pytest.approx((2000 * 1.0 + 300 * 5.0) / 1_000_000)
    ikinci, _ = _gercek_cikarici(tmp_path, istemci)
    sonuc = ikinci.cikar([KTT], BUGUN, bitis=2000)
    assert len(istemci.cagrilar) == 1
    assert (sonuc.incelenen, sonuc.incelenmedi, sonuc.bulgular) == (0, 1, [])
    assert sonuc.butce_usd == pytest.approx(ilk.butce_usd)


def test_ag_hatasi_deftere_yazmaz_ve_yeniden_denenir(tmp_path):
    istemci = SahteIstemci(hata=OSError("bağlantı koptu"))
    cikarici, _ = _gercek_cikarici(tmp_path, istemci)
    ilk = cikarici.cikar([KTT], BUGUN, bitis=2000)
    assert (ilk.incelenmedi, ilk.butce_usd) == (1, 0)
    ikinci, _ = _gercek_cikarici(tmp_path, istemci)
    ikinci.cikar([KTT], BUGUN, bitis=2000)
    assert len(istemci.cagrilar) == 2


def test_kapi_saat_tarih_ya_da_baska_saatin_parcasi_olamaz():
    aday = Aday("Matematik KTT 16.10.2026 günü. Veli toplantısı 19:00", "Matematik", date(2026, 10, 12),
                "ders_karti", [])
    alinti = "Matematik KTT 16.10.2026 günü. Veli toplantısı 19:00"
    for ham in ("16.10", "10.20", "9:00", "25:00", "19:60"):
        [b] = uydurma_kapisi([_satir(saat=ham, tarih_ifadesi="16.10.2026 günü", alinti=alinti)], aday, BUGUN)
        assert b.saat is None, ham
    [b] = uydurma_kapisi([_satir(saat="19:00", tarih_ifadesi="16.10.2026 günü", alinti=alinti)], aday, BUGUN)
    assert b.saat == "19:00"


def test_kapi_saat_kaynakta_olsa_da_alintida_degilse_atilir():
    aday = Aday("Matematik KTT 15 Ekim. Veli toplantısı 19:00", "Matematik", date(2026, 10, 12), "ders_karti", [])
    [b] = uydurma_kapisi([_satir(saat="19:00", tarih_ifadesi="15 Ekim", alinti="Matematik KTT 15 Ekim")],
                         aday, BUGUN)
    assert b.saat is None


def test_kapi_baska_cumledeki_tarih_sinava_baglanmaz():
    aday = Aday("Matematik KTT yapılacaktır. Veli toplantısı 20 Ekim.", "Matematik", date(2026, 10, 12),
                "ders_karti", [])
    [b] = uydurma_kapisi([_satir(tarih_ifadesi="20 Ekim", tarih="2026-10-20", konular=[],
                                 alinti="Matematik KTT yapılacaktır")], aday, BUGUN)
    assert (b.tarih, b.hafta) == (None, None)


def test_kapi_sinav_duyurmayan_alinti_atilir():
    aday = Aday("Quizlet uygulamasında kelime çalışın", "İngilizce", date(2026, 10, 12), "ders_karti", [])
    satir = _satir(ders="İngilizce", tur="kisa_sinav", baslik="Quiz", tarih_ifadesi="", tarih="", konular=[],
                   alinti="Quizlet uygulamasında kelime çalışın")
    assert uydurma_kapisi([satir], aday, BUGUN) == []


def test_kapi_dict_olmayan_satir_ve_dizge_konular():
    sonuc = uydurma_kapisi(["metin", None, 3, _satir(konular="Mutlak değer")], KTT, BUGUN)
    assert [b.konular for b in sonuc] == [[]]


def test_cikarici_istisnada_odenmis_sonuclar_onbellekte_kalir(tmp_path):
    class Patlayan(SahteOkuyucu):
        def oku(self, aday, bugun, zaman_asimi):
            if aday is ING:
                raise RuntimeError("beklenmeyen")
            return super().oku(aday, bugun, zaman_asimi)

    with pytest.raises(RuntimeError):
        _cikarici(tmp_path, Patlayan()).cikar([KTT, ING], BUGUN, bitis=2000)
    okuyucu = SahteOkuyucu()
    sonuc = _cikarici(tmp_path, okuyucu).cikar([KTT], BUGUN, bitis=2000)
    assert (okuyucu.cagrilar, sonuc.incelenen) == ([], 1)
