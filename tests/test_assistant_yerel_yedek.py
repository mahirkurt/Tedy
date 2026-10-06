"""Claude'a ulaşılamazsa evdeki modelle kaynaksız yedek cevap (2026-10-06). Ağ yok."""
import json

import pytest

from src import yerel_llm as yl


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    from src.assistant_core import AssistantRuntime

    rt = AssistantRuntime(tmp_path)
    monkeypatch.setattr(rt.registry, "declarations", lambda *args, **kw: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])

    def dusen(**kw):
        if kw.get("on_delta"):
            kw["on_delta"]("Yarım kalan taslak")
        raise ConnectionError("api.anthropic.com yok")
    monkeypatch.setattr(rt.llm, "chat_with_tools", dusen)
    return rt


def _yerel(monkeypatch, parcalar=("Kesirleri ", "toplamak için paydaları eşitle."), gorulen=None):
    monkeypatch.setenv("ASSISTANT_YEREL_LLM", "1")

    def istek(url, govde, zaman_asimi):
        if gorulen is not None:
            gorulen.append(govde)
        satirlar = [json.dumps({"message": {"content": p}, "done": False}) for p in parcalar]
        return iter(satirlar + [json.dumps({"message": {"content": ""}, "done": True})])
    monkeypatch.setattr(yl, "_istek", istek)


def test_claude_dusunce_yerel_model_kaynaksiz_oldugunu_soyleyerek_cevaplar(runtime, monkeypatch):
    gorulen = []
    _yerel(monkeypatch, gorulen=gorulen)
    payload = runtime.chat([{"role": "user", "content": "Kesir nasıl toplanır?"}], ogretmen="matematik",
                           okur="ogrenci", denetle=lambda *a: pytest.fail("yedek cevap denetlenmez"))
    assert payload["answer"].startswith("Kesirleri toplamak için paydaları eşitle.")
    assert "yedek" in payload["answer"] and "kaynaklara bakılamadı" in payload["answer"]
    assert "warning:yerel_yedek" in payload["safety_flags"]
    assert "error:model_unavailable" not in payload["safety_flags"]
    assert payload["meta"]["model"] == "gemma4-e4b-cpu" and payload["meta"]["provider"] == "yerel"
    assert payload["meta"]["denetim"]["neden"] == "yerel_yedek"
    sistem = gorulen[0]["messages"][0]["content"]
    assert gorulen[0]["messages"][0]["role"] == "system"
    assert "sen" in sistem and "cevap anahtarı" in sistem and "uydurma" in sistem
    assert gorulen[0]["messages"][-1] == {"role": "user", "content": "Kesir nasıl toplanır?"}


def test_akista_yarim_taslak_sifirlanir_ve_yedek_akar(runtime, monkeypatch):
    _yerel(monkeypatch)
    olaylar = list(runtime.chat_events(messages=[{"role": "user", "content": "Kesir?"}], ogretmen="matematik",
                                      okur="ogrenci"))
    adlar = [o["event"] for o in olaylar]
    assert adlar.index("answer_reset") < adlar.index("answer")
    sonrasi = adlar[adlar.index("answer_reset"):]
    assert "answer_delta" in sonrasi
    akan = "".join(o["text"] for o in olaylar[adlar.index("answer_reset"):] if o["event"] == "answer_delta")
    assert akan.startswith("Kesirleri toplamak")
    assert olaylar[-1]["payload"]["answer"].startswith("Kesirleri toplamak")


def test_yerel_de_duserse_eski_hata_cumlesi(runtime, monkeypatch):
    monkeypatch.setenv("ASSISTANT_YEREL_LLM", "1")

    def istek(*a):
        raise OSError("mbp kapalı")
    monkeypatch.setattr(yl, "_istek", istek)
    payload = runtime.chat([{"role": "user", "content": "Kesir?"}], ogretmen="fen")
    assert payload["answer"].startswith(runtime._model_hata_cevabi())
    assert "error:model_unavailable" in payload["safety_flags"]
    assert "warning:yerel_yedek" not in payload["safety_flags"]


def test_kapaliyken_yerel_model_cagrilmaz(runtime, monkeypatch):
    monkeypatch.setattr(yl, "_istek", lambda *a: pytest.fail("kapalıyken ağ yok"))
    payload = runtime.chat([{"role": "user", "content": "Kesir?"}], ogretmen="fen")
    assert "error:model_unavailable" in payload["safety_flags"]


def test_aile_icin_siz_ve_isik_ucuncu_sahis(runtime, monkeypatch):
    gorulen = []
    _yerel(monkeypatch, gorulen=gorulen)
    payload = runtime.chat([{"role": "user", "content": "Işık uykusuz"}], okur="aile")
    sistem = gorulen[0]["messages"][0]["content"]
    assert "siz" in sistem and "üçüncü" in sistem
    assert "sorun" in payload["answer"]  # "biraz sonra yeniden sorun"


def test_yalniz_son_turlarin_metni_gider(runtime, monkeypatch):
    gorulen = []
    _yerel(monkeypatch, gorulen=gorulen)
    mesajlar = []
    for i in range(10):
        mesajlar += [{"role": "user", "content": f"soru {i}"}, {"role": "assistant", "content": f"cevap {i}"}]
    mesajlar.append({"role": "user", "content": [{"type": "text", "text": "son soru"},
                                                 {"type": "image", "source": {"data": "xx"}}]})
    runtime.chat(mesajlar)
    giden = gorulen[0]["messages"][1:]
    assert len(giden) <= 6 and giden[-1] == {"role": "user", "content": "son soru"}
    assert all(isinstance(m["content"], str) for m in giden)
