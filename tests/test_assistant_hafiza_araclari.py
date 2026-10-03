"""İstek kapsamındaki hafıza araçları; geçici depo ve ağsız arama."""
from datetime import datetime, timezone

import pytest

from src.assistant_sohbet import SohbetDeposu
from src.assistant_tools import McpRegistry, _sorguya


SIMDI = datetime(2026, 10, 3, 8, tzinfo=timezone.utc)


@pytest.fixture
def depo(tmp_path):
    return SohbetDeposu(tmp_path / "assistant_sohbetler.sqlite")


def _reg(**kwargs):
    return McpRegistry({}, lambda q, k: [], saat=lambda: SIMDI, **kwargs)


@pytest.mark.parametrize("okur,hafiza,izin", [
    ("ogrenci", True, True), ("aile", True, True),
    ("bilinmiyor", True, False), ("ogrenci", False, False),
])
def test_bildirim_ve_yazma_ayni_kapiya_bakar(depo, okur, hafiza, izin):
    reg = _reg()
    adlar = {d["name"] for d in reg.declarations(okur=okur, hafiza=hafiza, not_deposu=depo)}
    assert ("hafiza_yaz" in adlar) is izin
    assert ("hafiza_duzelt" in adlar) is izin
    sonuc = reg.dispatch("hafiza_yaz", {"metin": "Paydada zorlanıyor"},
                         okur=okur, hafiza=hafiza, not_deposu=depo, sohbet_id="ab" * 16)
    assert sonuc.ok is izin
    assert len(depo.notlar()) == int(izin)
    if izin:
        assert depo.notlar()[0]["kaynak_sohbet"] == "ab" * 16


def test_deposuz_ilan_yok_yazma_yok_dosya_yok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reg = _reg()
    assert "hafiza_yaz" not in {d["name"] for d in reg.declarations(okur="ogrenci")}
    assert not reg.dispatch("hafiza_yaz", {"metin": "Paydada zorlanıyor"}, okur="ogrenci").ok
    assert not list(tmp_path.rglob("*.sqlite"))


@pytest.mark.parametrize("metin", ["İlaç kullanıyor", "Boşanma konuşuldu", "05321112233", "veli@example.com", "", " "])
def test_hassas_ve_bos_not_yazilmaz(depo, metin):
    sonuc = _reg().dispatch("hafiza_yaz", {"metin": metin}, okur="ogrenci", not_deposu=depo)
    assert not sonuc.ok
    assert sonuc.error == "Bu not yazılmadı."
    assert depo.notlar() == []


def test_not_duzeltme_izinli_metin_ve_hassas_red(depo):
    reg = _reg(not_deposu=depo)
    assert reg.dispatch("hafiza_yaz", {"metin": "Paydada zorlanıyor"}, okur="ogrenci").ok
    nid = depo.notlar()[0]["id"]
    assert reg.dispatch("hafiza_duzelt", {"id": nid, "metin": "Şerit modelini tercih ediyor"}, okur="aile").ok
    assert depo.notlar()[0]["metin"] == "Şerit modelini tercih ediyor"
    assert not reg.dispatch("hafiza_duzelt", {"id": nid, "metin": "İlaç kullanıyor"}, okur="aile").ok
    assert depo.notlar()[0]["metin"] == "Şerit modelini tercih ediyor"
    assert not reg.dispatch("hafiza_duzelt", {"id": "ab" * 16, "metin": "Payda"}, okur="aile").ok


def test_istek_deposu_registry_uzerinde_kalmaz(depo):
    reg = _reg()
    assert reg.dispatch("hafiza_yaz", {"metin": "Paydada zorlanıyor"}, okur="ogrenci", not_deposu=depo).ok
    assert not reg.dispatch("hafiza_yaz", {"metin": "Sonraki istek"}, okur="ogrenci").ok
    assert len(depo.notlar()) == 1


@pytest.mark.parametrize("metin,beklenen", [
    ("Payda neden eşitlenir?", "Payda eşitlenir"),
    ("Paydada zorlanıyor", "Paydada zorlanıyor"),
    ("Nasıl! Hangi kesir kaç parçadır?", "kesir parçadır"),
    ("Nedir?", "Nedir"),
])
def test_sorguya_soru_sozcuklerini_model_cagirmadan_dusurur(metin, beklenen):
    assert _sorguya(metin) == beklenen


def test_sorguya_yalniz_iki_yerel_arama_yolunda_uygulanir():
    gorulen = []
    def ara(q, k):
        gorulen.append(q)
        return []
    reg = McpRegistry({}, ara, aile_kaynak_arama=ara)
    assert reg.dispatch("ogrenci_verisi_ara", {"query": "Payda neden eşitlenir?"}).ok
    assert reg.dispatch("aile_kaynak_ara", {"sorgu": "Payda neden eşitlenir?"}, okur="aile").ok
    assert gorulen == ["Payda eşitlenir", "Payda eşitlenir"]
