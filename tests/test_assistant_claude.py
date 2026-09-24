"""ClaudeClient: the assistant's model loop on the Anthropic Messages API — no network.

Replaces the Gemini chain (2026-09-24). The Gemini API terms forbid services
"likely to be accessed by individuals under the age of 18"; TEDY's assistant is
used by a 12-year-old. The behaviours below are the ones the Gemini loop was
pinned on, carried over, plus what the Messages API adds: one model at two
effort levels instead of a two-model chain, native tool_result blocks instead
of a flattened transcript, no sampling parameters (removed on Sonnet 5), and a
cached system prefix.
"""
from types import SimpleNamespace as NS

import pytest

from src.assistant_core import ClaudeClient, ToolLoopResult
from src.assistant_tools import ToolOutcome


def _metin(t):
    return NS(type="text", text=t)


def _arac(i, ad, girdi):
    return NS(type="tool_use", id=i, name=ad, input=girdi)


def _cevap(*bloklar, stop="end_turn", model="claude-sonnet-5", giris=100, cikis=20):
    return NS(content=list(bloklar), stop_reason=stop, model=model,
              usage=NS(input_tokens=giris, output_tokens=cikis,
                       cache_read_input_tokens=0, cache_creation_input_tokens=0))


class _Sahte:
    """Replays one scripted response per messages.create call, recording kwargs."""

    def __init__(self, *cevaplar):
        self.cevaplar = list(cevaplar)
        self.istekler = []
        self.messages = self

    def create(self, **kw):
        # Snapshot: the loop appends to the same list after the call returns.
        self.istekler.append({**kw, "messages": list(kw["messages"])})
        return self.cevaplar.pop(0)


def _istemci(*cevaplar, **kw):
    sahte = _Sahte(*cevaplar)
    return ClaudeClient(api_key="test", client=sahte, **kw), sahte


KONUSMA = [
    {"role": "system", "content": "SİSTEM"},
    {"role": "assistant", "content": "önceki cevap"},   # a history that opens mid-dialogue
    {"role": "user", "content": "kesir nedir"},
]
BILDIRIM = [{"name": "kazanim_ara", "description": "d",
             "parameters": {"type": "object", "properties": {"q": {"type": "string"}}}}]


def _ok(ad, girdi):
    return ToolOutcome(ok=True, text="MEB sonucu",
                       citations=[{"kind": "mufredat", "label": "MEB 7.1", "locator": {},
                                   "snippet": "s", "confidence": 0.9}])


# ── the request itself ────────────────────────────────────────────────────────

def test_varsayilan_model_sonnet_5_ve_ortamdan_degistirilebilir(monkeypatch):
    monkeypatch.delenv("ASSISTANT_CLAUDE_MODEL", raising=False)
    assert ClaudeClient(api_key="x").model == "claude-sonnet-5"
    monkeypatch.setenv("ASSISTANT_CLAUDE_MODEL", "claude-opus-5")
    assert ClaudeClient(api_key="x").model == "claude-opus-5"


def test_tek_model_iki_derinlik_efor_ile():
    for katman, efor in (("fast", "low"), ("deep", "high")):
        c, s = _istemci(_cevap(_metin("tamam")))
        c.chat_with_tools(KONUSMA, BILDIRIM, _ok, tier=katman)
        istek = s.istekler[0]
        assert istek["model"] == "claude-sonnet-5"
        assert istek["output_config"] == {"effort": efor}
        assert istek["thinking"] == {"type": "adaptive"}


def test_ornekleme_parametresi_gonderilmez():
    # temperature/top_p/top_k return a 400 on Sonnet 5 and are gone from SDK 1.x.
    c, s = _istemci(_cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, _ok)
    assert not {"temperature", "top_p", "top_k"} & set(s.istekler[0])


def test_sistem_ayri_alanda_ve_onbellekli_konusma_kullaniciyla_baslar():
    c, s = _istemci(_cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, _ok)
    istek = s.istekler[0]
    assert istek["system"] == [{"type": "text", "text": "SİSTEM",
                                "cache_control": {"type": "ephemeral"}}]
    # The API rejects a conversation that opens on the assistant.
    assert istek["messages"][0]["role"] == "user"
    assert all(m["role"] != "system" for m in istek["messages"])


def test_araclar_modele_input_schema_ile_sunulur():
    c, s = _istemci(_cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, _ok)
    assert s.istekler[0]["tools"] == [{
        "name": "kazanim_ara", "description": "d",
        "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}}}]


def test_anahtar_yoksa_acik_hata():
    c = ClaudeClient(api_key="")
    c.api_key = ""
    with pytest.raises(RuntimeError, match="anthropic_no_api_key"):
        c.chat_with_tools(KONUSMA, BILDIRIM, _ok)


def test_reddetme_sessiz_bos_cevap_olmaz():
    c, _ = _istemci(_cevap(stop="refusal"))
    with pytest.raises(RuntimeError, match="claude_refusal"):
        c.chat_with_tools(KONUSMA, BILDIRIM, _ok)


# ── the loop ──────────────────────────────────────────────────────────────────

def test_arac_cagrilir_atiflari_toplanir_ve_cevap_doner():
    c, s = _istemci(
        _cevap(_arac("t1", "kazanim_ara", {"q": "kesir"}), stop="tool_use"),
        _cevap(_metin("Kesir bir bütünün parçasıdır [S1]."), model="claude-sonnet-5"),
    )
    gorulen = []
    out = c.chat_with_tools(KONUSMA, BILDIRIM, lambda ad, g: (gorulen.append((ad, g)), _ok(ad, g))[1])
    assert gorulen == [("kazanim_ara", {"q": "kesir"})]
    assert out.text == "Kesir bir bütünün parçasıdır [S1]."
    assert [c["label"] for c in out.citations] == ["MEB 7.1"]
    assert out.tool_calls[0]["name"] == "kazanim_ara" and out.tool_calls[0]["ok"] is True
    assert c.last_model_used == "claude-sonnet-5"


def test_asistan_turu_degismeden_geri_verilir_sonuc_yerel_blokla():
    # Thinking blocks must go back exactly as received; the result is a native
    # tool_result tied to the call's id, not text pasted into a transcript.
    ilk = _cevap(NS(type="thinking", thinking="", signature="imza"),
                 _arac("t1", "kazanim_ara", {"q": "kesir"}), stop="tool_use")
    c, s = _istemci(ilk, _cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, _ok)
    ikinci = s.istekler[1]["messages"]
    assert ikinci[-2] == {"role": "assistant", "content": ilk.content}
    sonuc = ikinci[-1]["content"][0]
    assert sonuc["type"] == "tool_result" and sonuc["tool_use_id"] == "t1"
    assert sonuc["is_error"] is False


def test_modele_gosterilen_numara_panelin_numarasiyla_ayni():
    c, s = _istemci(
        _cevap(_arac("t1", "kazanim_ara", {"q": "a"}), _arac("t2", "kazanim_ara", {"q": "b"}),
               stop="tool_use"),
        _cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, _ok)
    sonuclar = s.istekler[1]["messages"][-1]["content"]
    assert sonuclar[0]["content"].startswith("[S1] MEB 7.1")
    assert sonuclar[1]["content"].startswith("[S2] MEB 7.1")


def test_basarisiz_arac_modele_hata_olarak_doner():
    c, s = _istemci(_cevap(_arac("t1", "kazanim_ara", {"q": 1}), stop="tool_use"),
                    _cevap(_metin("düzelttim")))
    out = c.chat_with_tools(KONUSMA, BILDIRIM, lambda a, g: ToolOutcome(ok=False, error="q metin olmalı"))
    sonuc = s.istekler[1]["messages"][-1]["content"][0]
    assert sonuc["is_error"] is True and "q metin olmalı" in sonuc["content"]
    assert out.tool_calls[0]["ok"] is False


def test_butce_dolunca_arac_kapali_son_tur_ve_fazla_cagri_kaybolmaz():
    c, s = _istemci(
        _cevap(_arac("t1", "kazanim_ara", {"q": "a"}), _arac("t2", "kazanim_ara", {"q": "b"}),
               stop="tool_use"),
        _cevap(_metin("eldekiyle cevap")))
    out = c.chat_with_tools(KONUSMA, BILDIRIM, _ok, max_rounds=1)
    assert out.budget_exhausted is True
    assert len(out.tool_calls) == 1
    # Every tool_use gets its tool_result — the API requires it — and the one
    # past the budget says so instead of vanishing.
    sonuclar = s.istekler[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in sonuclar] == ["t1", "t2"]
    assert sonuclar[1]["is_error"] is True and "bütçe" in sonuclar[1]["content"]
    # The last word is asked for with tools withdrawn, not with tools removed:
    # the tool list stays, so the cached prefix does too.
    assert s.istekler[1]["tool_choice"] == {"type": "none"}
    assert out.text == "eldekiyle cevap"


def test_sozluk_olmayan_girdi_calistirilmaz():
    cagrildi = []
    c, s = _istemci(_cevap(_arac("t1", "kazanim_ara", "bozuk"), stop="tool_use"),
                    _cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, lambda a, g: cagrildi.append(1))
    assert cagrildi == []
    assert s.istekler[1]["messages"][-1]["content"][0]["is_error"] is True


def test_bos_girdi_normal_cagridir():
    gorulen = []
    c, _ = _istemci(_cevap(_arac("t1", "kazanim_ara", None), stop="tool_use"),
                    _cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, lambda a, g: (gorulen.append(g), _ok(a, g))[1])
    assert gorulen == [{}]


def test_arac_yokken_tek_istek_arac_listesi_gonderilmez():
    c, s = _istemci(_cevap(_metin("merhaba")))
    out = c.chat_with_tools(KONUSMA, [], _ok)
    assert out.text == "merhaba" and "tools" not in s.istekler[0]


def test_token_kullanimi_toplanir():
    c, _ = _istemci(_cevap(_arac("t1", "kazanim_ara", {"q": "a"}), stop="tool_use", giris=300, cikis=40),
                    _cevap(_metin("tamam"), giris=500, cikis=60))
    out = c.chat_with_tools(KONUSMA, BILDIRIM, _ok)
    assert out.usage["input_tokens"] == 800 and out.usage["output_tokens"] == 100


def test_arac_sonucu_hic_bos_gitmez():
    # The API rejects an empty tool_result text.
    c, s = _istemci(_cevap(_arac("t1", "kazanim_ara", {"q": "a"}), stop="tool_use"),
                    _cevap(_metin("tamam")))
    c.chat_with_tools(KONUSMA, BILDIRIM, lambda a, g: ToolOutcome(ok=True, text="", citations=[]))
    assert s.istekler[1]["messages"][-1]["content"][0]["content"].strip()


def test_loop_sonucu_toolloopresult():
    c, _ = _istemci(_cevap(_metin("tamam")))
    assert isinstance(c.chat_with_tools(KONUSMA, BILDIRIM, _ok), ToolLoopResult)
