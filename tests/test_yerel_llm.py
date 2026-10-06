"""Evdeki dil modeli istemcisi (2026-10-06). Ağ yok: taşıma (`_istek`) her testte sahte."""
import json

import pytest

from src import yerel_llm as yl


def _ayar(**kw):
    return yl.YerelAyar(**{"acik": True, "url": "http://mbp:11435", "model": "gemma4-e4b-cpu", **kw})


def _akis(parcalar, son=True):
    satirlar = [json.dumps({"message": {"content": p}, "done": False}) for p in parcalar]
    if son:
        satirlar.append(json.dumps({"message": {"content": ""}, "done": True}))
    return satirlar


def test_akisi_birlestirir_ve_her_parcayi_verir(monkeypatch):
    gonderilen = {}

    def istek(url, govde, zaman_asimi):
        gonderilen.update(url=url, govde=govde, zaman_asimi=zaman_asimi)
        return iter(_akis(["Merhaba", ", Işık", "!"]))

    monkeypatch.setattr(yl, "_istek", istek)
    parcalar = []
    metin = yl.sohbet([{"role": "user", "content": "selam"}], sistem="kısa yaz", ayar=_ayar(),
                      on_delta=parcalar.append)
    assert metin == "Merhaba, Işık!" and parcalar == ["Merhaba", ", Işık", "!"]
    assert gonderilen["url"] == "http://mbp:11435/api/chat"
    g = gonderilen["govde"]
    assert g["model"] == "gemma4-e4b-cpu" and g["stream"] is True and g["think"] is False
    assert g["messages"][0] == {"role": "system", "content": "kısa yaz"}
    assert g["options"]["num_predict"] == yl.VARSAYILAN_TOKEN


@pytest.mark.parametrize("satirlar", [_akis([], son=True), _akis(["yarım"], son=False), ["bozuk json"]])
def test_bos_yarim_ya_da_bozuk_akis_hatadir(monkeypatch, satirlar):
    monkeypatch.setattr(yl, "_istek", lambda *a: iter(satirlar))
    with pytest.raises(yl.YerelHata):
        yl.sohbet([{"role": "user", "content": "x"}], ayar=_ayar())


def test_kapaliyken_cagrilmaz(monkeypatch):
    monkeypatch.setattr(yl, "_istek", lambda *a: pytest.fail("ağ"))
    with pytest.raises(yl.YerelHata):
        yl.sohbet([{"role": "user", "content": "x"}], ayar=_ayar(acik=False))


def test_baglanti_hatasi_yerel_hataya_doner(monkeypatch):
    def istek(*a):
        raise OSError("mbp kapalı")
    monkeypatch.setattr(yl, "_istek", istek)
    with pytest.raises(yl.YerelHata):
        yl.sohbet([{"role": "user", "content": "x"}], ayar=_ayar())


def test_arka_plan_isi_sirayla_calisir_ve_hatasi_disari_tasmaz():
    sira = []

    def is_(n):
        sira.append(n)
        if n == 2:
            raise RuntimeError("bozuk")

    futures = [yl.arka_planda(is_, n) for n in (1, 2, 3)]
    for f in futures:
        f.result(timeout=5)
    assert sira == [1, 2, 3]


def test_ayarlar_ortamdan(monkeypatch):
    for k in ("ASSISTANT_YEREL_LLM", "ASSISTANT_YEREL_LLM_URL", "ASSISTANT_YEREL_LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    a = yl.ayarlar()
    assert a.acik is False and a.url == "http://mbp.lan:11435" and a.model == "gemma4-e4b-cpu"
    monkeypatch.setenv("ASSISTANT_YEREL_LLM", "1")
    monkeypatch.setenv("ASSISTANT_YEREL_LLM_URL", "http://x:1/")
    assert yl.ayarlar() == yl.YerelAyar(acik=True, url="http://x:1", model="gemma4-e4b-cpu")


@pytest.mark.parametrize("ham,beklenen", [
    ('"Kesirlerde Payda Eşitleme"', "Kesirlerde Payda Eşitleme"),
    ("**Başlık:** Galaksiler ve Evren\n\nAçıklama...", "Galaksiler ve Evren"),
    ("# Yıldızların yaşamı.", "Yıldızların yaşamı"),
    ("", None),
    ("a" * 200, None),
])
def test_baslik_temizlenir(ham, beklenen):
    assert yl.baslik_temizle(ham) == beklenen
