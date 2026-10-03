"""netlestir (D1, spec "netlestir aracı"): a terminating, interactive-only tool.

- Declared only when etkilesimli is true (/stream, /chat), in every mode.
- A valid call alone in its round ends the loop: answer = round text + question;
  the clarify event carries the question and 2–4 options.
- Called beside another tool it is refused (not dispatched) and the loop goes on.
- Invalid arguments are a HATA result; the loop goes on.
"""
from types import SimpleNamespace

import pytest

from src import assistant_skills
from src.assistant_core import ClaudeClient
from src.assistant_tools import (NETLESTIR_TOOL, SONLANDIRICI_ARACLAR, McpRegistry,
                                 ToolOutcome)

GECERLI = {"soru": "Kesirlerin hangi yönüyle başlayalım?",
           "secenekler": ["Karşılaştırma", "Toplama", "Ondalık gösterim"]}


def _metin(t):
    return SimpleNamespace(type="text", text=t)


def _arac(ad, girdi, kimlik="tu_1"):
    return SimpleNamespace(type="tool_use", id=kimlik, name=ad, input=girdi)


def _yanit(*bloklar):
    return SimpleNamespace(content=list(bloklar), stop_reason="tool_use",
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1,
                                                 cache_read_input_tokens=0,
                                                 cache_creation_input_tokens=0))


class _Senaryo:
    """ClaudeClient._request stand-in: returns scripted responses in order."""

    def __init__(self, *yanitlar):
        self.yanitlar = list(yanitlar)
        self.istekler = []

    def __call__(self, system, turns, tier, usage, tools=None, tool_choice=None, on_delta=None):
        self.istekler.append({"turns": [dict(t) for t in turns], "tool_choice": tool_choice})
        yanit = self.yanitlar.pop(0)
        if on_delta is not None:
            for b in yanit.content:
                if getattr(b, "type", "") == "text" and b.text:
                    on_delta(b.text)
        return yanit


def _istemci(monkeypatch, senaryo):
    c = ClaudeClient(client=object())
    monkeypatch.setattr(c, "_request", senaryo, raising=False)
    return c


def _dispatch(ad, args):
    if ad == NETLESTIR_TOOL:
        return McpRegistry._dispatch_netlestir(None, args)
    return ToolOutcome(ok=True, text="kayıt", citations=[])


DECL = [{"name": NETLESTIR_TOOL, "parameters": {"type": "object"}},
        {"name": "odev_listesi", "parameters": {"type": "object"}}]


def test_netlestir_sonlandirici_kumede():
    assert SONLANDIRICI_ARACLAR == {NETLESTIR_TOOL}


@pytest.mark.parametrize("args,hata", [
    ({}, "soru"),
    ({"soru": "x" * 141, "secenekler": ["a", "b"]}, "soru"),
    ({"soru": "Hangisi?", "secenekler": ["a"]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", "b", "c", "d", "e"]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", ""]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", "x" * 61]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": ["a", "A"]}, "secenek"),
    ({"soru": "Hangisi?", "secenekler": "a,b"}, "secenek"),
])
def test_gecersiz_arguman_hata(args, hata):
    sonuc = McpRegistry._dispatch_netlestir(None, args)
    assert not sonuc.ok and hata in sonuc.error.lower()


def test_gecerli_cagri_olay_uretir():
    sonuc = McpRegistry._dispatch_netlestir(None, dict(GECERLI))
    assert sonuc.ok
    assert sonuc.olay == {"event": "clarify", **GECERLI}


def test_yalniz_netlestir_dongüyu_bitirir(monkeypatch):
    s = _Senaryo(_yanit(_metin("Önce bir şey sorayım."), _arac(NETLESTIR_TOOL, dict(GECERLI))))
    c = _istemci(monkeypatch, s)
    akis, sifirlama = [], []
    out = c.chat_with_tools(messages=[{"role": "user", "content": "kesirleri anlat"}],
                            declarations=DECL, dispatch=_dispatch, tier="medium",
                            on_delta=akis.append, on_reset=lambda: sifirlama.append(1))
    assert len(s.istekler) == 1
    assert out.text == "Önce bir şey sorayım.\n\n" + GECERLI["soru"]
    assert "".join(akis) == out.text
    assert not sifirlama
    assert out.olaylar == [{"event": "clarify", **GECERLI}]


def test_metinsiz_netlestir_yalniz_soruyu_doner(monkeypatch):
    s = _Senaryo(_yanit(_arac(NETLESTIR_TOOL, dict(GECERLI))))
    out = _istemci(monkeypatch, s).chat_with_tools(
        messages=[{"role": "user", "content": "kesir"}], declarations=DECL,
        dispatch=_dispatch, tier="medium")
    assert out.text == GECERLI["soru"]
    assert len(s.istekler) == 1


def test_baska_aracla_birlikte_reddedilir_dongu_surer(monkeypatch):
    s = _Senaryo(
        _yanit(_arac(NETLESTIR_TOOL, dict(GECERLI), "tu_1"), _arac("odev_listesi", {}, "tu_2")),
        _yanit(_metin("Cevap.")),
    )
    cagrilan = []

    def izle(ad, args):
        cagrilan.append(ad)
        return _dispatch(ad, args)

    out = _istemci(monkeypatch, s).chat_with_tools(
        messages=[{"role": "user", "content": "x"}], declarations=DECL, dispatch=izle,
        tier="medium")
    assert cagrilan == ["odev_listesi"]
    assert out.text == "Cevap."
    assert out.olaylar == []
    sonuclar = s.istekler[1]["turns"][-1]["content"]
    ret = next(r for r in sonuclar if r["tool_use_id"] == "tu_1")
    assert ret["is_error"] and "yalnız başına" in str(ret["content"])


def test_gecersiz_netlestir_hata_alir_dongu_surer(monkeypatch):
    s = _Senaryo(_yanit(_arac(NETLESTIR_TOOL, {"soru": "?", "secenekler": ["a"]})),
                 _yanit(_metin("Düz cevap.")))
    out = _istemci(monkeypatch, s).chat_with_tools(
        messages=[{"role": "user", "content": "x"}], declarations=DECL,
        dispatch=_dispatch, tier="medium")
    assert out.text == "Düz cevap."
    assert out.olaylar == []


def test_etkilesimsiz_bildirilmez_ve_reddedilir(tmp_path):
    reg = McpRegistry.__new__(McpRegistry)
    reg.skills = {}
    adlar = [d["name"] for d in reg._ogretmen_bildirimleri(assistant_skills.GENEL, etkilesimli=False)]
    assert NETLESTIR_TOOL not in adlar
    adlar = [d["name"] for d in reg._ogretmen_bildirimleri(assistant_skills.GENEL, etkilesimli=True)]
    assert NETLESTIR_TOOL in adlar


def test_etkilesimsiz_dogrudan_dispatch_de_reddedilir():
    reg = McpRegistry.__new__(McpRegistry)
    out = reg.dispatch(NETLESTIR_TOOL, dict(GECERLI), etkilesimli=False)
    assert not out.ok
    assert out.olay is None


def test_ogretmen_bildirimleri_netlestir_once_mod_araci_sonda():
    reg = McpRegistry.__new__(McpRegistry)
    reg.skills = assistant_skills.yukle()
    for ogretmen, son in [('genel', 'mod_oner'), ('matematik', 'skill_kaynagi')]:
        adlar = [d['name'] for d in reg._ogretmen_bildirimleri(ogretmen)]
        assert adlar == [NETLESTIR_TOOL, son]
        assert NETLESTIR_TOOL not in [d['name'] for d in reg._ogretmen_bildirimleri(
            ogretmen, etkilesimli=False)]


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    from src.assistant_core import AssistantRuntime, ToolLoopResult

    rt = AssistantRuntime(tmp_path)
    monkeypatch.setattr(rt.registry, 'declarations', lambda *args, **kw: DECL)
    monkeypatch.setattr(rt.registry, 'degraded', lambda: [])

    def tur(*, dispatch, **kw):
        outcome = dispatch(NETLESTIR_TOOL, dict(GECERLI))
        return ToolLoopResult(text=GECERLI['soru'], olaylar=[outcome.olay])

    monkeypatch.setattr(rt.llm, 'chat_with_tools', tur)
    return rt


def test_chat_netlestirme_yuku(runtime):
    payload = runtime.chat([{'role': 'user', 'content': 'Kesirleri anlat'}])
    assert payload['netlestirme'] == GECERLI
    assert payload['answer'] == GECERLI['soru']


def test_chat_akista_tek_netlestirme(runtime):
    events = list(runtime.chat_events(messages=[{'role': 'user', 'content': 'Kesirleri anlat'}]))
    assert [e for e in events if e['event'] == 'clarify'] == [{'event': 'clarify', **GECERLI}]
    assert events[-1]['event'] == 'answer'
    assert events[-1]['payload']['netlestirme'] == GECERLI


def test_gecersiz_sonlandirici_taslagi_sifirlar(monkeypatch):
    s = _Senaryo(_yanit(_metin('Geçici açıklama.'),
                       _arac(NETLESTIR_TOOL, {'soru': '?', 'secenekler': ['a']})),
                 _yanit(_metin('Son cevap.')))
    akis, reset = [], []
    out = _istemci(monkeypatch, s).chat_with_tools(
        messages=[{'role': 'user', 'content': 'kesir'}], declarations=DECL,
        dispatch=_dispatch, on_delta=akis.append, on_reset=lambda: reset.append(1))
    assert reset == [1]
    assert out.text == 'Son cevap.'
    assert out.olaylar == []
