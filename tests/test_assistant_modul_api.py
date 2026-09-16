"""Assistant endpoints decide module-progress permission from the caller: only a signed-in full-role person."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["TEST_AUTH_BYPASS"] = "1"

import src.dashboard_api as dashboard_api  # noqa: E402

app = dashboard_api.app
FULL = "isikkurtx@gmail.com"
READER = "murzogluhulya@gmail.com"
BODY = {"messages": [{"role": "user", "content": "modül var mı"}]}


class _Recorder:
    def __init__(self):
        self.calls = []

    @staticmethod
    def _payload(kind):
        return {"answer": kind, "citations": [], "safety_flags": [], "plan_blocks": [], "intent": "qa",
                "session_id": "", "meta": {"model": "fake"}}

    def chat(self, **kwargs):
        self.calls.append(("chat", kwargs.get("ilerleme_izni")))
        return self._payload("chat")

    def chat_events(self, **kwargs):
        self.calls.append(("stream", kwargs.get("ilerleme_izni")))
        yield {"event": "answer", "payload": self._payload("stream")}

    def study_plan(self, **kwargs):
        self.calls.append(("plan", kwargs.get("ilerleme_izni")))
        return self._payload("plan")


@pytest.fixture
def env(monkeypatch):
    recorder = _Recorder()
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", False)
    monkeypatch.setattr(dashboard_api, "API_KEYS", [("entegrasyon", "tdyK_test")])
    monkeypatch.setattr(dashboard_api, "ASSISTANT_API_KEY", "asst_test")
    monkeypatch.setattr(dashboard_api, "_assistant_runtime", lambda: recorder)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, recorder


def _sign_in(client, email):
    with client.session_transaction() as sess:
        sess["user_email"] = email


def _hit_all(client, headers=None):
    codes = [client.post("/api/assistant/chat", json=BODY, headers=headers).status_code,
             client.post("/api/assistant/plan", json=BODY, headers=headers).status_code]
    stream = client.post("/api/assistant/stream", json=BODY, headers=headers)
    stream.get_data()  # drain: the generator, and so chat_events, runs only while the body is read
    codes.append(stream.status_code)
    return codes


def test_signed_in_full_person_grants_progress_on_every_dashboard_route(env):
    client, recorder = env
    _sign_in(client, FULL)
    assert _hit_all(client) == [200, 200, 200]
    # ("stream", True) also proves the flag was decided inside the request: the stream generator
    # runs after the view returns, where the session can no longer be read.
    assert sorted(recorder.calls) == [("chat", True), ("plan", True), ("stream", True)]


def test_dashboard_api_key_never_grants_progress(env):
    client, recorder = env
    assert _hit_all(client, headers={"Authorization": "Bearer tdyK_test"}) == [200, 200, 401]
    assert recorder.calls == [("chat", False), ("plan", False)]


def test_test_bypass_is_not_a_person(env, monkeypatch):
    client, recorder = env
    monkeypatch.setattr(dashboard_api, "TEST_AUTH_BYPASS", True)
    assert _hit_all(client) == [200, 200, 200]
    assert sorted(recorder.calls) == [("chat", False), ("plan", False), ("stream", False)]


def test_reader_never_reaches_the_runtime(env):
    client, recorder = env
    _sign_in(client, READER)
    assert _hit_all(client) == [403, 403, 403]
    assert recorder.calls == []
