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
