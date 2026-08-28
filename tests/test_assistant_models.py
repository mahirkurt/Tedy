"""GeminiClient model chain behaviour — no network."""
import pytest
from src.assistant_core import GeminiClient


class _FakeModels:
    """Records calls and replays a scripted outcome per model name."""

    def __init__(self, script):
        self.script = script          # {model_name: Exception | str}
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        outcome = self.script.get(model, "ok")
        if isinstance(outcome, Exception):
            raise outcome
        return type("R", (), {"text": outcome})()


class _FakeClient:
    def __init__(self, script):
        self.models = _FakeModels(script)


def _client(script):
    c = GeminiClient(api_key="test-key")
    c._client = _FakeClient(script)
    return c


def test_fast_chain_has_no_retired_models():
    """gemini-2.0-* were measured returning 404 on 2026-08-23."""
    chain = GeminiClient.FAST_MODELS + GeminiClient.DEEP_MODELS
    assert not [m for m in chain if m.startswith("gemini-2.0")]


def test_404_model_is_permanently_disabled_and_chain_continues():
    first = GeminiClient.FAST_MODELS[0]
    err = Exception("404 NOT_FOUND. This model is no longer available.")
    c = _client({first: err})

    assert c.chat([{"role": "user", "content": "selam"}]) == "ok"
    assert first in c._unavailable
    assert c.last_model_used == GeminiClient.FAST_MODELS[1]

    # Second call must not spend a round-trip on the dead model again.
    c._client.models.calls.clear()
    c.chat([{"role": "user", "content": "tekrar"}])
    assert first not in c._client.models.calls


def test_quota_exhaustion_is_temporary_not_permanent():
    first = GeminiClient.FAST_MODELS[0]
    err = Exception("429 RESOURCE_EXHAUSTED quota")
    c = _client({first: err})

    c.chat([{"role": "user", "content": "selam"}])
    assert first in c._exhausted
    assert first not in c._unavailable


def test_deep_tier_prefers_pro_then_falls_back_to_fast():
    c = _client({})
    c.chat([{"role": "user", "content": "plan"}], tier="deep")
    assert c.last_model_used == GeminiClient.DEEP_MODELS[0]

    c2 = _client({GeminiClient.DEEP_MODELS[0]: Exception("429 RESOURCE_EXHAUSTED")})
    c2.chat([{"role": "user", "content": "plan"}], tier="deep")
    assert c2.last_model_used == GeminiClient.FAST_MODELS[0]


def test_output_token_cap_is_passed_through():
    c = _client({})
    captured = {}
    orig = c._client.models.generate_content

    def spy(*, model, contents, config):
        captured.update(config)
        return orig(model=model, contents=contents, config=config)

    c._client.models.generate_content = spy
    c.chat([{"role": "user", "content": "x"}], max_output_tokens=8192)
    assert captured["max_output_tokens"] == 8192


from src.assistant_tools import ToolOutcome


class _Part:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text


class _FC:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _Cand:
    def __init__(self, parts):
        self.content = type("C", (), {"parts": parts})()


class _ToolResp:
    def __init__(self, parts, text=""):
        self.candidates = [_Cand(parts)]
        self.text = text


class _ScriptedModels:
    """Replays one response per generate_content call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.configs = []

    def generate_content(self, *, model, contents, config):
        self.configs.append(config)
        return self.responses.pop(0)


def _tool_client(responses):
    c = GeminiClient(api_key="test-key")
    c._client = type("C", (), {"models": _ScriptedModels(responses)})()
    return c


DECLS = [{"name": "kazanim_ara", "description": "d",
          "parameters": {"type": "object", "properties": {}, "required": []}}]


def test_tool_call_is_dispatched_and_its_citations_are_collected():
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "kesir"}))]),
        _ToolResp([_Part(text="Kesirler [S1] konusuna bak.")],
                  text="Kesirler [S1] konusuna bak."),
    ])
    seen = []

    def dispatch(name, args):
        seen.append((name, args))
        return ToolOutcome(ok=True, text="MAT.5.1.1 kesirler",
                           citations=[{"kind": "mufredat", "label": "MEB",
                                       "locator": {}, "snippet": "s", "confidence": 0.9}])

    out = c.chat_with_tools([{"role": "user", "content": "kesir"}], DECLS, dispatch)

    assert seen == [("kazanim_ara", {"q": "kesir"})]
    assert out.text == "Kesirler [S1] konusuna bak."
    assert len(out.citations) == 1
    assert out.tool_calls[0]["name"] == "kazanim_ara"
    assert out.tool_calls[0]["ok"] is True
    assert out.budget_exhausted is False


def test_a_failing_tool_is_fed_back_so_the_model_can_correct_itself():
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {}))]),
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "kesir"}))]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])
    calls = []

    def dispatch(name, args):
        calls.append(args)
        if not args:
            return ToolOutcome(ok=False, error="Field required: q")
        return ToolOutcome(ok=True, text="sonuç")

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch)

    assert calls == [{}, {"q": "kesir"}]
    assert out.text == "bitti"
    assert out.tool_calls[0]["ok"] is False


def test_round_budget_stops_a_model_that_never_stops_calling_tools():
    loop = [_ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "x"}))])
            for _ in range(6)]
    c = _tool_client(loop + [_ToolResp([_Part(text="özet")], text="özet")])

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS,
                            lambda n, a: ToolOutcome(ok=True, text="t"),
                            max_rounds=3)

    assert out.budget_exhausted is True
    assert len(out.tool_calls) == 3


def test_an_answer_with_no_tool_call_returns_immediately():
    c = _tool_client([_ToolResp([_Part(text="selam")], text="selam")])
    out = c.chat_with_tools([{"role": "user", "content": "selam"}], DECLS,
                            lambda n, a: ToolOutcome(ok=True))
    assert out.text == "selam" and out.tool_calls == []


def test_tools_are_actually_offered_to_the_model():
    c = _tool_client([_ToolResp([_Part(text="x")], text="x")])
    c.chat_with_tools([{"role": "user", "content": "q"}], DECLS,
                      lambda n, a: ToolOutcome(ok=True))
    assert "tools" in c._client.models.configs[0]
