"""Asistanın akşam planı araçları (Görev 8): `aksam_plani` okur, `plani_degistir` Işık'ın isteğiyle düzenler.

Gerçek motor ve gerçek depolar (tmp); model yok. Kurallar yapıyı plan kartıyla paylaşır: "şimdi değil"
blok başına bir kez, yarın teslim iş akşamdan çıkmaz; aile ikisini de aşar ve kayda geçer."""
import os
from datetime import date, datetime
from types import SimpleNamespace

import pytest

os.environ["TEST_AUTH_BYPASS"] = "1"

from src.aksam_duzeni import VARSAYILAN  # noqa: E402
from src.aksam_plani import PlanDeposu, plan_kur  # noqa: E402
from src.assistant_tools import (AKSAM_TOOL, PLAN_DEGISTIR_TOOL, PlanYazici,  # noqa: E402
                                 build_registry)
from src.odev_tahmini import TahminDeposu  # noqa: E402

SIMDI = datetime(2026, 10, 19, 16, 30)
GUN = SIMDI.date().isoformat()


def _hw(anahtar, ders, baslik, teslim):
    return {"homework_key": anahtar, "Ders Adı": ders, "Ödev Başlığı": baslik,
            "Ödev Son Teslim Tarihi": teslim, "detail": {"description": "", "attachments": []},
            "teacher_resolved": False, "student_marked_done": False}


ROWS = [
    _hw("mat", "Matematik", "Problemler Çalışma Kâğıdı", "20.10.2026 23:59"),   # yarın
    _hw("fen", "Fen Bilimleri", "Hücre Özeti", "23.10.2026 23:59"),
    _hw("tur", "Türkçe", "Kitap Notu", "24.10.2026 23:59"),
]


@pytest.fixture
def kur(tmp_path, monkeypatch):
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "1")
    depo = PlanDeposu(tmp_path)
    tahmin = TahminDeposu(tmp_path, SimpleNamespace(model="yok"))
    satirlar = list(ROWS)

    def plan():
        return plan_kur(satirlar, lambda s: tahmin.tahmin(s, date(2026, 10, 19)), VARSAYILAN, SIMDI, [],
                        depo.gunluk(GUN), True)

    def registry(**kw):
        return build_registry(lambda q, k: [], odev_kaynagi=lambda: satirlar, plan_kaynagi=plan,
                              plan_yazici=PlanYazici(depo, tahmin), saat=lambda: SIMDI, **kw)
    return SimpleNamespace(registry=registry, depo=depo, plan=plan, satirlar=satirlar)


def _cagri(reg, okur, **args):
    return reg.dispatch(PLAN_DEGISTIR_TOOL, args, okur=okur)


def test_bayrak_kapaliyken_ve_kaynaksiz_arac_bildirilmez(kur, monkeypatch):
    adlar = lambda r, okur="ogrenci": {d["name"] for d in r.declarations(okur=okur)}  # noqa: E731
    assert {AKSAM_TOOL, PLAN_DEGISTIR_TOOL} <= adlar(kur.registry())
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "0")
    assert not {AKSAM_TOOL, PLAN_DEGISTIR_TOOL} & adlar(kur.registry())
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "1")
    assert not {AKSAM_TOOL, PLAN_DEGISTIR_TOOL} & adlar(build_registry(lambda q, k: [], odev_kaynagi=lambda: ROWS))


def test_bayrak_kapaliyken_dispatch_reddeder(kur, monkeypatch):
    monkeypatch.setenv("TEDY_AKSAM_PLANI", "0")
    reg = kur.registry()
    assert not reg.dispatch(AKSAM_TOOL, {}, okur="ogrenci").ok
    assert not _cagri(reg, "ogrenci", islem="sona_al", odev="fen").ok


def test_degistirme_araci_yalniz_ogrenci_ve_aileye(kur):
    adlar = {d["name"] for d in kur.registry().declarations(okur="bilinmiyor")}
    assert AKSAM_TOOL in adlar and PLAN_DEGISTIR_TOOL not in adlar
    assert not _cagri(kur.registry(), "bilinmiyor", islem="sona_al", odev="fen").ok


def test_aksam_plani_metni_saatleri_ve_tahmin_sozcugunu_tasir(kur):
    r = kur.registry().dispatch(AKSAM_TOOL, {}, okur="ogrenci")
    assert r.ok and "17:00" in r.text and "tahmin" in r.text
    assert "Problemler Çalışma Kâğıdı" in r.text and "Yemek" in r.text


def test_yarina_at_ogrenci_icin_yarin_teslimde_reddedilir(kur):
    r = _cagri(kur.registry(), "ogrenci", islem="yarina_at", odev="mat")
    assert "Bu ödev yarın teslim; bu akşamdan çıkaramam." in (r.text + (r.error or ""))
    assert "yarina" not in kur.depo.gunluk(GUN)


def test_yarina_at_aile_kabul_eder_ve_asimi_kaydeder(kur):
    r = _cagri(kur.registry(), "aile", islem="yarina_at", odev="mat")
    assert r.ok
    g = kur.depo.gunluk(GUN)
    assert g["yarina"] == ["mat"]
    assert g["asimlar"][0]["asan"] == "aile" and g["asimlar"][0]["islem"] == "yarina_at"
    assert g["asimlar"][0]["odev"] == "mat" and g["asimlar"][0]["zaman"]
    assert all(b.odev_anahtari != "mat" for b in kur.plan().bloklar)
    assert any(t["odev_anahtari"] == "mat" for t in kur.plan().tasinan)


def test_yarina_at_uzak_odevde_ogrenciye_de_calisir(kur):
    assert _cagri(kur.registry(), "ogrenci", islem="yarina_at", odev="tur").ok
    assert kur.depo.gunluk(GUN)["yarina"] == ["tur"]
    assert "asimlar" not in kur.depo.gunluk(GUN)


def test_sona_al_bir_kez_ikincisi_reddedilir_aile_asar(kur):
    del kur.satirlar[0]                      # akşam boş kalsın: ertelenen parça yine de yerleşir
    reg = kur.registry()
    assert _cagri(reg, "ogrenci", islem="sure", odev="fen", dakika=60).ok     # birden çok parça
    assert _cagri(reg, "ogrenci", islem="sona_al", odev="fen").ok
    assert kur.depo.gunluk(GUN)["ertelenen"]
    r = _cagri(reg, "ogrenci", islem="sona_al", odev="fen")
    assert "bir kez" in (r.text + (r.error or ""))
    assert len(kur.depo.gunluk(GUN)["ertelenen"]) == 1
    assert "asimlar" not in kur.depo.gunluk(GUN)
    assert _cagri(reg, "aile", islem="sona_al", odev="fen").ok
    assert kur.depo.gunluk(GUN)["asimlar"][0]["asan"] == "aile"


def test_kartin_ertelemesi_asistan_hakkini_da_harcar(kur):
    blok = next(b for b in kur.plan().bloklar if b.odev_anahtari == "fen" and b.tur == "calisma")
    kur.depo.degistir(GUN, lambda g: g.update(ertelenen=[blok.id]))
    r = _cagri(kur.registry(), "ogrenci", islem="one_al", odev="fen")
    assert "bir kez" in (r.text + (r.error or ""))
    assert "one_al" not in kur.depo.gunluk(GUN)


def test_one_al_ilk_sira_ve_ikinci_kez_reddi(kur):
    reg = kur.registry()
    assert _cagri(reg, "ogrenci", islem="one_al", odev="tur").ok
    assert [b for b in kur.plan().bloklar if b.tur == "calisma"][0].odev_anahtari == "tur"
    assert "bir kez" in (lambda r: r.text + (r.error or ""))(_cagri(reg, "ogrenci", islem="sona_al", odev="tur"))


def test_sure_okur_duzeltmesini_yazar_ve_plan_metni_degisir(kur):
    reg = kur.registry()
    once = reg.dispatch(AKSAM_TOOL, {}, okur="ogrenci").text
    r = _cagri(reg, "ogrenci", islem="sure", odev="fen", dakika=60)
    assert r.ok and "60" in r.text
    sonra = reg.dispatch(AKSAM_TOOL, {}, okur="ogrenci").text
    assert sonra != once


def test_sure_aralik_disinda_reddedilir(kur):
    assert not _cagri(kur.registry(), "ogrenci", islem="sure", odev="fen", dakika=3).ok
    assert not _cagri(kur.registry(), "ogrenci", islem="sure", odev="fen").ok


def test_odev_eslesmesi_katlanmis_altdize_belirsizse_hicbir_sey_degismez(kur):
    kur.satirlar.append(_hw("fen2", "Fen Bilimleri", "Hücre Testi", "23.10.2026 23:59"))
    r = _cagri(kur.registry(), "ogrenci", islem="sona_al", odev="HÜCRE")
    assert r.ok and "Hücre Özeti" in r.text and "Hücre Testi" in r.text
    assert "ertelenen" not in kur.depo.gunluk(GUN)
    assert _cagri(kur.registry(), "ogrenci", islem="one_al", odev="turkce kitap").ok   # katlama
    assert kur.depo.gunluk(GUN)["one_al"] == ["tur"]


def test_odev_bulunamazsa_adaylar_listelenir(kur):
    r = _cagri(kur.registry(), "ogrenci", islem="sona_al", odev="olmayan ödev")
    assert "Hücre Özeti" in r.text and "ertelenen" not in kur.depo.gunluk(GUN)


def test_yaptim_isaretli_odev_plan_metninde_yok(kur):
    kur.satirlar[1]["student_marked_done"] = True
    assert "Hücre Özeti" not in kur.registry().dispatch(AKSAM_TOOL, {}, okur="ogrenci").text


def test_bilinmeyen_islem_reddedilir(kur):
    assert not _cagri(kur.registry(), "ogrenci", islem="sil", odev="fen").ok
