"""B6 chat entegrasyonu; ücretli istemci yerine denetle enjekte edilir."""
import json

import pytest

from src.assistant_denetim import DENETIM_ISTEMI, DENETIM_MODEL


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    from src.assistant_core import AssistantRuntime, ToolLoopResult

    rt = AssistantRuntime(tmp_path)
    monkeypatch.setattr(rt.registry, "declarations", lambda *args, **kw: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])

    def taslak(**kw):
        if kw.get("on_delta"):
            kw["on_delta"]("taslak ")
        return ToolLoopResult(text="taslak [S1].", citations=[{
            "kind": "mufredat", "label": "Payda", "locator": {},
            "snippet": "Payda eşitlenir.", "confidence": 0.9,
        }], usage={"input_tokens": 10, "output_tokens": 4})

    monkeypatch.setattr(rt.llm, "chat_with_tools", taslak)
    return rt


def test_akis_taslagi_akar_denetim_son_cevabi_degistirir(runtime):
    gorulen = []
    runtime.llm.last_model_used = "cevap-modeli"

    def denetle(istem, kullanici):
        gorulen.append(json.loads(kullanici))
        assert istem == DENETIM_ISTEMI
        return '{"ciddi": true, "sorun": ["kaynak"], "cevap": "Payda eşitlenir [S1]."}'

    olaylar = list(runtime.chat_events(messages=[{"role": "user", "content": "Payda"}],
                                      ogretmen="matematik", okur="ogrenci", denetle=denetle))
    assert [olay["event"] for olay in olaylar] == ["answer_delta", "answer"]
    assert olaylar[0]["text"] == "taslak "
    payload = olaylar[1]["payload"]
    assert payload["answer"] == "Payda eşitlenir [S1]."
    assert payload["meta"]["model"] == runtime.llm.last_model_used == "cevap-modeli"
    assert payload["meta"]["usage"] == {"input_tokens": 10, "output_tokens": 4}
    assert payload["meta"]["denetim"] == {
        "durum": "duzeltildi", "neden": None, "sorun": ["kaynak"], "model": DENETIM_MODEL,
    }
    assert len(gorulen) == 1
    assert gorulen[0]["cevap"] == "taslak [S1]."
    assert gorulen[0]["sinif"] == "7. sınıf"
    assert gorulen[0]["kaynaklar"] == [{"id": "S1", "label": "Payda", "snippet": "Payda eşitlenir."}]
    assert "cevap anahtarı" in gorulen[0]["kurallar"]
    metric = json.loads(runtime.config.metrics_path.read_text().splitlines()[-1])
    assert metric["denetim"] == "duzeltildi"
    assert "cevap" not in metric


def test_denetim_cagri_hatasi_taslagi_korur(runtime):
    sayac = []

    def denetle(*args):
        sayac.append(1)
        raise RuntimeError("gizli istisna metni")

    payload = runtime.chat([{"role": "user", "content": "Payda"}], ogretmen="fen", denetle=denetle)
    assert payload["answer"] == "taslak [S1]."
    assert payload["meta"]["denetim"]["durum"] == "hata"
    assert payload["meta"]["denetim"]["neden"] == "cagri"
    assert "RuntimeError" not in str(payload) and "gizli" not in str(payload)
    assert sayac == [1]


@pytest.mark.parametrize("ham,durum,neden", [
    ('{"ciddi": false}', "gecti", None),
    ('bozuk', "hata", "bicim"),
    ('{"ciddi": true, "sorun": ["hitap"], "cevap": "  "}', "hata", "bos"),
    ('{"ciddi": true, "sorun": ["hitap"], "cevap": "taslak [S1]."}', "hata", "ayni"),
])
def test_denetim_tek_cagri_taslagi_korur(runtime, ham, durum, neden):
    sayac = []

    def denetle(*args):
        sayac.append(1)
        return ham

    payload = runtime.chat([{"role": "user", "content": "Payda"}], ogretmen="fen", denetle=denetle)
    assert payload["answer"] == "taslak [S1]."
    assert payload["meta"]["denetim"]["durum"] == durum
    assert payload["meta"]["denetim"]["neden"] == neden
    assert sayac == [1]


def test_denetim_kisa_genel_icin_cagrilmaz(runtime):
    payload = runtime.chat([{"role": "user", "content": "Merhaba"}],
                           denetle=lambda *args: pytest.fail("kısa genel cevap"))
    assert payload["meta"]["denetim"] == {
        "durum": "atlandi", "neden": "genel_kisa", "sorun": [], "model": None,
    }


def test_denetim_model_yoksa_cagrilmaz(runtime, monkeypatch):
    assert not runtime.llm.available
    monkeypatch.setattr(runtime.llm, "_get_client", lambda: pytest.fail("model yok"))
    payload = runtime.chat([{"role": "user", "content": "Payda"}], ogretmen="matematik")
    assert payload["answer"] == "taslak [S1]."
    assert payload["meta"]["denetim"]["neden"] == "model_yok"


@pytest.mark.parametrize("hata", ["bos", "model"])
def test_denetim_hata_yaniti_icin_cagrilmaz(runtime, monkeypatch, hata):
    from src.assistant_core import ToolLoopResult

    metin = "" if hata == "bos" else runtime._model_hata_cevabi()
    monkeypatch.setattr(runtime.llm, "chat_with_tools", lambda **kw: ToolLoopResult(text=metin))
    payload = runtime.chat([{"role": "user", "content": "Payda"}], ogretmen="matematik",
                           denetle=lambda *args: pytest.fail("hata cevabı"))
    assert payload["answer"] == (runtime._fallback_answer("Payda") if hata == "bos" else metin)
    assert payload["meta"]["denetim"]["neden"] == "hata_cevabi"


def test_denetim_guvenlik_son_ekini_goremez_ve_silemez(runtime):
    def denetle(istem, kullanici):
        assert "Klinik" not in json.loads(kullanici)["cevap"]
        return '{"ciddi": true, "sorun": ["kaynak"], "cevap": "Yeni cevap [S1]."}'

    payload = runtime.chat([{"role": "user", "content": "Bana tanı koy"}],
                           ogretmen="fen", denetle=denetle)
    son = runtime.policy.guidance_suffix(["risk:clinical_request"])
    assert payload["answer"] == "Yeni cevap [S1]." + son
    assert "lisanslı uzmanla değerlendirin." in son


def test_denetim_iki_geciste_gecersiz_atiflar_toplanir(runtime, monkeypatch):
    from src.assistant_core import ToolLoopResult

    monkeypatch.setattr(runtime.llm, "chat_with_tools", lambda **kw: ToolLoopResult(
        text="Kaynak [S1]. Yanlış [S9].", citations=[{
            "kind": "mufredat", "label": "Payda", "locator": {}, "snippet": "Payda",
        }]))
    payload = runtime.chat([{"role": "user", "content": "Payda"}], ogretmen="matematik",
                           denetle=lambda *args: '{"ciddi": true, "sorun": ["kaynak"], "cevap": "Yeni [S9]."}')
    assert payload["answer"] == "Yeni."
    assert payload["meta"]["dropped_citations"] == 2
    assert payload["citations"] == []
    assert "warning:limited_confidence" in payload["safety_flags"]


def test_uzun_genel_cevap_ogretmen_bakisi_almaz(runtime, monkeypatch):
    from src.assistant_core import ToolLoopResult

    cevap = "a" * 800
    monkeypatch.setattr(runtime.llm, "chat_with_tools", lambda **kw: ToolLoopResult(text=cevap))

    def denetle(istem, kullanici):
        assert json.loads(kullanici)["kurallar"] is None
        return '{"ciddi": true, "sorun": ["ogretmen"], "cevap": "yeni"}'

    payload = runtime.chat([{"role": "user", "content": "Payda"}], denetle=denetle)
    assert payload["answer"] == cevap
    assert payload["meta"]["denetim"]["neden"] == "bicim"


def test_denetim_isaretten_ibaret_duzeltme_bos_yanit_yapmaz(runtime):
    payload = runtime.chat([{"role": "user", "content": "Payda"}], ogretmen="fen",
                           denetle=lambda *args: '{"ciddi": true, "sorun": ["kaynak"], "cevap": "[S9]"}')
    assert payload["answer"] == "taslak [S1]."
    assert len(payload["citations"]) == 1
    assert payload["meta"]["denetim"]["neden"] == "bos"


def test_fallback_sorudaki_atif_temizlense_de_denetlenmez(runtime, monkeypatch):
    from src.assistant_core import ToolLoopResult

    monkeypatch.setattr(runtime.llm, "chat_with_tools", lambda **kw: ToolLoopResult())
    payload = runtime.chat([{"role": "user", "content": "Payda [S9]"}], ogretmen="fen",
                           denetle=lambda *args: pytest.fail("yedek cevap denetlenmez"))
    assert payload["meta"]["denetim"]["neden"] == "hata_cevabi"
