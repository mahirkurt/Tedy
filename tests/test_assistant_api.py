"""API tests for assistant endpoints."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402

app = dashboard_api.app


class _FakeRuntime:
    def chat(self, messages, session_id="", context_filters=None, temperature=0.2, ilerleme_izni=False,
             okur="bilinmiyor"):
        return {
            "answer": "chat ok",
            "citations": [{"id": "S1", "path": "output/scraped_data.json", "snippet": "..."}],
            "safety_flags": [],
            "plan_blocks": [],
            "intent": "data_query",
            "session_id": session_id,
            "meta": {"model": "fake", "latency_ms": 5},
        }

    def study_plan(self, messages, session_id="", context_filters=None, ilerleme_izni=False,
                   okur="bilinmiyor"):
        return {
            "answer": "plan ok",
            "citations": [],
            "safety_flags": [],
            "plan_blocks": [{
                "type": "homework",
                "title": "Matematik",
                "day": "2026-03-15",
                "estimated_minutes": 45,
                "actions": ["tekrar", "soru"],
                "rationale": "test",
            }],
            "intent": "study_plan",
            "session_id": session_id,
            "meta": {"model": "fake", "latency_ms": 8},
        }

    def reindex(self, incremental=True):
        return {"files_indexed": 10, "chunks_indexed": 30, "incremental": incremental}

    def models(self):
        return [{"id": "fake-model", "object": "model", "created": 1, "owned_by": "local"}]

    def openai_chat_completion(self, payload):
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 1,
            "model": "fake-model",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            "citations": [],
            "safety_flags": [],
            "plan_blocks": [],
            "intent": "general",
            "meta": {"model": "fake-model"},
        }


@pytest.fixture
def client(monkeypatch):
    app.config["TESTING"] = True
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: _FakeRuntime())
    with app.test_client() as c:
        yield c


def test_assistant_chat_endpoint(client):
    resp = client.post("/api/assistant/chat", json={"messages": [{"role": "user", "content": "test"}]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["answer"] == "chat ok"
    assert isinstance(data["citations"], list)


def test_assistant_plan_endpoint(client):
    resp = client.post("/api/assistant/plan", json={"messages": [{"role": "user", "content": "plan"}]})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["answer"] == "plan ok"
    assert len(data["plan_blocks"]) == 1


def test_assistant_reindex_endpoint(client):
    resp = client.post("/api/assistant/reindex", json={"full": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["stats"]["incremental"] is False


def test_openai_compatible_chat_completion(client):
    resp = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "merhaba"}]},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "ok"


def test_openai_models_endpoint(client):
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["object"] == "list"
    assert data["data"][0]["id"] == "fake-model"


def test_v1_models_requires_api_key_when_no_session(client, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "ASSISTANT_API_KEY", "test-key")

    resp = client.get("/v1/models")
    assert resp.status_code == 401


def test_v1_models_accepts_valid_api_key(client, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "ASSISTANT_API_KEY", "test-key")

    resp = client.get(
        "/v1/models",
        headers={"Authorization": "Bearer test-key"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["object"] == "list"


def test_assistant_reindex_forbidden_for_non_admin_session(client, monkeypatch):
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "ASSISTANT_API_KEY", "another-key")
    monkeypatch.setattr(dashboard_api, "ASSISTANT_ADMIN_EMAILS", {"admin@example.com"})

    with client.session_transaction() as sess:
        sess["user_email"] = "normal@example.com"

    resp = client.post("/api/assistant/reindex", json={"full": True})
    assert resp.status_code == 403
