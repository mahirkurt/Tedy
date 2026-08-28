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
        self.contents = []

    def generate_content(self, *, model, contents, config):
        self.configs.append(config)
        self.contents.append(contents)
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


def test_calls_beyond_the_round_budget_are_skipped_not_dropped():
    """Finding 2: one turn returning more calls than the remaining budget
    must not dispatch the excess, and must not drop them silently either."""
    c = _tool_client([
        _ToolResp([
            _Part(function_call=_FC("kazanim_ara", {"q": "a"})),
            _Part(function_call=_FC("kitap_listele", {"q": "b"})),
        ]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])
    dispatched = []

    def dispatch(name, args):
        dispatched.append(name)
        return ToolOutcome(ok=True, text="ok")

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch,
                            max_rounds=1)

    assert dispatched == ["kazanim_ara"]
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0]["name"] == "kazanim_ara"
    assert out.budget_exhausted is True
    # The skipped call must still be named in what the model sees next.
    final_contents = c._client.models.contents[-1]
    assert "kitap_listele" in final_contents


def test_non_mapping_args_from_the_model_are_rejected_not_dispatched():
    """Finding 1: call.args is model-supplied, untrusted input. A truthy
    non-mapping value must not be dispatched or silently coerced to {}."""
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", ["not", "a", "dict"]))]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])
    calls = []

    def dispatch(name, args):
        calls.append(args)
        return ToolOutcome(ok=True, text="ok")

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch)

    assert calls == []  # never dispatched
    assert out.tool_calls[0]["name"] == "kazanim_ara"
    assert out.tool_calls[0]["ok"] is False
    assert out.text == "bitti"


def test_none_args_from_the_model_still_dispatch_as_a_normal_empty_call():
    """The SDK's ordinary way of saying "no arguments" (args=None) is not
    the malformed case Finding 1 targets, and must keep working as before."""
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", None))]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])
    calls = []

    def dispatch(name, args):
        calls.append(args)
        return ToolOutcome(ok=True, text="ok")

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch)

    assert calls == [{}]
    assert out.tool_calls[0]["ok"] is True


def test_generate_falls_through_an_empty_response_to_the_next_model():
    """Finding 3: an empty-text, no-function-call response must not be
    handed back as a successful blank answer — the chain must move on."""
    first = GeminiClient.FAST_MODELS[0]
    second = GeminiClient.FAST_MODELS[1]
    c = _client({first: ""})

    assert c.chat([{"role": "user", "content": "x"}]) == "ok"
    assert c.last_model_used == second


def test_generate_raises_only_once_every_model_is_truly_exhausted():
    script = {m: "" for m in GeminiClient.FAST_MODELS}
    c = _client(script)

    with pytest.raises(RuntimeError):
        c.chat([{"role": "user", "content": "x"}])


def test_the_model_is_shown_which_number_each_source_will_get():
    """Numbering is assigned by _finalize_citations in accumulation order. If the
    model never sees those numbers it cites by guesswork, and a wrong-but-real
    source is worse than a dropped marker: it looks verified."""
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "kesir"}))]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])

    def dispatch(name, args):
        return ToolOutcome(ok=True, text="gövde", citations=[
            {"kind": "mufredat", "label": "kazanım A", "locator": {},
             "snippet": "s", "confidence": 0.9},
            {"kind": "mufredat", "label": "kazanım B", "locator": {},
             "snippet": "s", "confidence": 0.9},
        ])

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch)
    shown = c._client.models.contents[-1]
    assert "[S1] kazanım A" in shown
    assert "[S2] kazanım B" in shown
    # Ve gösterilen numaralar finalize'ın atayacağıyla aynı olmalı.
    assert [x["label"] for x in out.citations] == ["kazanım A", "kazanım B"]


def test_a_tool_only_response_with_no_text_is_not_treated_as_empty():
    """A response carrying function calls but no text is the normal
    tool-calling case and must not be skipped as an empty response."""
    c = _tool_client([
        _ToolResp([_Part(function_call=_FC("kazanim_ara", {"q": "kesir"}))]),
        _ToolResp([_Part(text="bitti")], text="bitti"),
    ])
    dispatched = []

    def dispatch(name, args):
        dispatched.append(name)
        return ToolOutcome(ok=True, text="t")

    out = c.chat_with_tools([{"role": "user", "content": "x"}], DECLS, dispatch)

    # The load-bearing assertion: the tool-only round was actually acted on.
    # Without it this test passes even when _generate stops treating a
    # function-call-only response as usable, because the scripted models
    # happen to yield the same call count and final text either way.
    assert dispatched == ["kazanim_ara"]
    assert len(out.tool_calls) == 1
    # Only two generate_content calls total — the tool-only round was not
    # skipped and retried against a second model.
    assert len(c._client.models.contents) == 2
    assert out.text == "bitti"
