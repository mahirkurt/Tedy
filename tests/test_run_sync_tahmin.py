"""run_sync's homework-estimate warming step (evening plan, Görev 6). Nothing here reaches the model."""
import time
from datetime import date

import src.run_sync as run_sync
# Taken at collection, before conftest's autouse fixture swaps in a stub.
GERCEK_ADIM = run_sync._tahmin_isitma_adimi

SATIR = {"Ders Adı": "Matematik", "Ödev Başlığı": "Alıştırma", "Ödev Son Teslim Tarihi": "01.01.2099"}


class SahteDefter:
    def harcanan(self):
        return 0.0123456


class SahteDepo:
    def __init__(self, ozet=None, istisna=None):
        self.cagrilar = []
        self.defter = SahteDefter()
        self.ozet = ozet or {"cagri": 2, "onbellekte": 1, "hata": 0, "durdu": None, "son_hata": None}
        self.istisna = istisna

    def isit(self, satirlar, bugun, bitis):
        self.cagrilar.append((list(satirlar), bugun, bitis - time.monotonic()))
        if self.istisna:
            raise self.istisna
        return self.ozet

    def tahmin(self, satir, bugun):
        class T:
            kaynak = "yedek"
        return T()


def _plan_acik(monkeypatch):
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "1")
    monkeypatch.setattr("src.aksam_plani.planlanacak", lambda s, b: (list(s), 0))


def test_bayrak_kapaliyken_atlar(monkeypatch):
    monkeypatch.delenv("TEDY_AKSAM_PLANI", raising=False)
    depo = SahteDepo()
    assert GERCEK_ADIM(time.time(), depo=depo, satirlar=[SATIR]) == {"atlandi": "bayrak"}
    assert depo.cagrilar == []


def test_sure_5_saniyenin_altindaysa_atlar(monkeypatch):
    _plan_acik(monkeypatch)
    depo = SahteDepo()
    assert GERCEK_ADIM(time.time() - 600 + 150 + 4, depo=depo, satirlar=[SATIR]) == {"atlandi": "sure"}
    assert depo.cagrilar == []


def test_isit_bir_kez_cagrilir_ozet_health_bicimindedir(monkeypatch):
    _plan_acik(monkeypatch)
    depo = SahteDepo()
    ozet = GERCEK_ADIM(time.time(), depo=depo, satirlar=[SATIR])
    assert len(depo.cagrilar) == 1
    secilen, bugun, kalan = depo.cagrilar[0]
    assert secilen == [SATIR] and isinstance(bugun, date) and 25 < kalan <= 30
    assert ozet == {"isitilan": 2, "onbellekte": 1, "yedekte": 1, "harcanan_usd": 0.0123,
                    "durdu": None, "hata": None}


def test_butce_30_saniyeyi_gecmez_ve_kalana_gore_kisalir(monkeypatch):
    _plan_acik(monkeypatch)
    depo = SahteDepo()
    GERCEK_ADIM(time.time() - 600 + 150 + 12, depo=depo, satirlar=[])
    assert 8 < depo.cagrilar[0][2] <= 12


def test_isit_istisna_firlatirsa_hata_doner_senkron_surer(monkeypatch):
    _plan_acik(monkeypatch)
    depo = SahteDepo(istisna=RuntimeError("anahtar patladı"))
    assert GERCEK_ADIM(time.time(), depo=depo, satirlar=[SATIR]) == {"hata": "anahtar patladı"}


def test_satir_kaynagi_istisna_firlatirsa_hata_doner(monkeypatch):
    _plan_acik(monkeypatch)
    import src.dashboard_api as api
    monkeypatch.setattr(api, "_canli_odevler", lambda: (_ for _ in ()).throw(ValueError("satır yok")))
    assert GERCEK_ADIM(time.time(), depo=SahteDepo()) == {"hata": "satır yok"}


def test_isit_hatasi_ozete_gecer(monkeypatch):
    _plan_acik(monkeypatch)
    depo = SahteDepo({"cagri": 0, "onbellekte": 0, "hata": 1, "durdu": "butce", "son_hata": "okuma: X: y"})
    ozet = GERCEK_ADIM(time.time(), depo=depo, satirlar=[SATIR])
    assert ozet["durdu"] == "butce" and ozet["hata"] == "okuma: X: y"


def test_conftest_gercek_adimi_varsayilan_olarak_degistirir():
    assert run_sync._tahmin_isitma_adimi(time.time()) == {"atlandi": "test"}
