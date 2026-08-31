import json
import os
import threading
import time
from types import SimpleNamespace
from pathlib import Path

from src.assistant_core import AssistantRuntime, GeminiClient


class _DummyOllama:
    def __init__(self):
        self.chat_model = "dummy-chat"
        self.embed_model = "dummy-embed"

    def available_models(self):
        return [self.chat_model, self.embed_model]

    def embed(self, text: str):
        if not text.strip():
            return None
        # Deterministic tiny embedding for tests
        s = sum(ord(c) for c in text[:64])
        return [float((s % 97) / 97.0), float(len(text) % 13), 1.0]

    def chat(self, messages, temperature=0.2):
        last_user = ""
        for m in messages[::-1]:
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        return f"TEST_ANSWER::{last_user[:40]}"


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_project(tmp_path: Path):
    # Only output/ is indexed (whitelist approach)
    _write(
        tmp_path / "output" / "scraped_data.json",
        json.dumps(
            {
                "scraped_at": "2026-03-14T17:00:00",
                "odevlerim": {
                    "homework": {
                        "rows": [
                            {
                                "Ders Adı": "Matematik",
                                "Ödev Başlığı": "Kesirler Tekrar",
                                "Ödev Son Teslim Tarihi": "16.03.2026 18:00",
                                "Ödev Durumu": "Değerlendirilmemiş",
                            }
                        ]
                    }
                },
                "gelisim_raporu": {"grades": []},
                "takvim": [],
                "ders_programi": [],
            },
            ensure_ascii=False,
        ),
    )
    _write(
        tmp_path / "output" / "enrichment_cache.json",
        json.dumps(
            {"hw:mat:1": {"type": "odev", "note": "Kesirler çalışma notu"}},
            ensure_ascii=False,
        ),
    )
    _write(
        tmp_path / "output" / "eba_textbooks_uploaded.json",
        json.dumps(
            {"mat_7": {"title": "Matematik 7", "course": "Matematik"}},
            ensure_ascii=False,
        ),
    )
    # These should NOT be indexed
    _write(tmp_path / "src" / "module.py", "def add(a,b): return a+b\n")
    _write(tmp_path / "docs" / "note.md", "# Dev docs\n")
    _write(tmp_path / "CLAUDE.md", "# Project instructions\n")


def test_reindex_creates_manifest_and_chunks(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)

    stats = runtime.reindex(incremental=False)

    assert stats["files_indexed"] >= 3
    assert stats["chunks_indexed"] >= 3
    assert runtime.config.manifest_path.exists()
    assert runtime.config.chunks_path.exists()
    # Verify no project docs/src/root files indexed
    manifest = json.loads(
        runtime.config.manifest_path.read_text())
    for path in manifest:
        assert not path.startswith("src/"), \
            f"Source file indexed: {path}"
        assert not path.startswith("docs/"), \
            f"Docs file indexed: {path}"
        assert path != "CLAUDE.md", \
            "CLAUDE.md should not be indexed"


def test_incremental_reindex_detects_changes(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)

    first = runtime.reindex(incremental=False)
    assert first["files_indexed"] == 3

    # Modify an indexed output file
    _write(
        tmp_path / "output" / "enrichment_cache.json",
        json.dumps(
            {"hw:mat:1": {"type": "odev", "note": "Güncellenmiş not"}},
            ensure_ascii=False,
        ),
    )

    second = runtime.reindex(incremental=True)
    assert second["changed_files"] >= 1
    assert second["unchanged_files"] >= 1


def test_chat_returns_citations_and_answer(tmp_path: Path, monkeypatch):
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    # runtime.router IS runtime.gemini (same object) — patching a fresh object
    # onto runtime.router leaves runtime.gemini untouched and chat() would hit
    # the real Gemini API over the network. Patch the method on the real
    # object instead.
    monkeypatch.setattr(
        runtime.gemini, "chat_with_tools",
        lambda *a, **k: ToolLoopResult(
            text="TEST_ANSWER::kesir çalışması [S1]",
            citations=[{"kind": "ogrenci", "label": "scraped_data.json",
                        "locator": {}, "snippet": "s", "confidence": 0.9}]))

    runtime.reindex(incremental=False)

    response = runtime.chat(
        messages=[
            {"role": "user",
             "content": "Matematik ödevim ne?"}
        ],
        session_id="test-session",
        context_filters={},
    )

    assert "answer" in response
    assert response["answer"].startswith(
        "TEST_ANSWER::")
    assert isinstance(response.get("citations"), list)
    assert len(response["citations"]) == 1
    assert response.get("intent") in {
        "data_query", "general",
        "expert_guidance", "study_plan"}


def test_chat_marks_limited_confidence_when_retrieval_weak(tmp_path: Path, monkeypatch):
    """The flag's source changed in Task 6: chat() no longer runs retrieval
    ahead of the prompt, so "weak retrieval" no longer exists as a signal.
    Its honest replacement is an empty *resolved* citation list — the model
    answered but nothing it said was backed by a tool-returned source. The
    flag must still fire; only the mechanism producing an empty citation
    list changed (here: the model emits no [S] markers at all)."""
    _prepare_project(tmp_path)
    monkeypatch.setenv("ASSISTANT_ENABLE_EMBEDDINGS", "0")

    runtime = AssistantRuntime(tmp_path)
    monkeypatch.setattr(
        runtime.gemini, "chat_with_tools",
        lambda *a, **k: ToolLoopResult(text="TEST", citations=[]))

    runtime.reindex(incremental=False)

    response = runtime.chat(
        messages=[{"role": "user",
                   "content": "no_source_probe_abcdef"}],
        session_id="test-limited",
        context_filters={},
    )

    assert "warning:limited_confidence" in response.get("safety_flags", [])
    assert response.get("citations") == []


def test_gemini_only_no_ollama(tmp_path: Path):
    """Verify Ollama is fully removed."""
    runtime = AssistantRuntime(tmp_path)
    assert not hasattr(runtime, "ollama")
    assert not hasattr(runtime.config, "ollama_base_url")
    assert [model["id"] for model in runtime.models()] == GeminiClient.FAST_MODELS
    assert all(model["owned_by"] == "google" for model in runtime.models())


def test_openai_completion_uses_gemini_default_model(tmp_path: Path):
    """When chat() reports no explicit model, the OpenAI-compatible endpoint
    must still report a real, current model — not a stale/retired literal."""
    runtime = AssistantRuntime(tmp_path)
    runtime.chat = lambda **_kwargs: {"answer": "ok"}

    completion = runtime.openai_chat_completion({
        "messages": [{"role": "user", "content": "test"}],
    })

    assert completion["model"] == GeminiClient.FAST_MODELS[0]


from src.assistant_core import AssistantRuntime, ToolLoopResult


DEEP_INTENTS = ("study_plan", "grade_analysis", "exam_solving")


def test_deep_tier_is_chosen_by_intent_not_by_the_model():
    """Tier selection is deterministic so cost and latency stay predictable."""
    for intent in DEEP_INTENTS:
        assert AssistantRuntime._tier_for(intent, force_deep=False) == "deep"
    assert AssistantRuntime._tier_for("qa", force_deep=False) == "fast"


def test_explicit_user_request_forces_the_deep_tier():
    assert AssistantRuntime._tier_for("qa", force_deep=True) == "deep"


def test_chat_reports_degraded_servers_in_meta(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "degraded", lambda: ["maarif-mufredat"])
    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(
        rt.gemini, "chat_with_tools",
        lambda *a, **k: ToolLoopResult(text="cevap", citations=[]))

    out = rt.chat([{"role": "user", "content": "merhaba"}])
    assert out["meta"]["degraded"] == ["maarif-mufredat"]


def test_empty_model_output_becomes_an_honest_message_not_a_blank_reply(tmp_path, monkeypatch):
    """A budget-exhausted loop can return text="" — measured in Task 4. The
    reader must never receive a blank answer."""
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])
    monkeypatch.setattr(rt.gemini, "chat_with_tools",
                        lambda *a, **k: ToolLoopResult(text="   ", budget_exhausted=True))

    out = rt.chat([{"role": "user", "content": "kesir nedir"}])
    assert out["answer"].strip()
    assert "kesir nedir" in out["answer"]


def test_chat_meta_carries_the_tool_ledger_and_dropped_count(tmp_path, monkeypatch):
    (tmp_path / "output").mkdir()
    rt = AssistantRuntime(tmp_path)

    monkeypatch.setattr(rt.registry, "declarations", lambda: [])
    monkeypatch.setattr(rt.registry, "degraded", lambda: [])
    monkeypatch.setattr(rt.gemini, "chat_with_tools", lambda *a, **k: ToolLoopResult(
        text="Kaynaklı [S1] ve uydurma [S5].",
        citations=[{"kind": "mufredat", "label": "MEB", "locator": {},
                    "snippet": "s", "confidence": 0.9}],
        tool_calls=[{"name": "kazanim_ara", "ms": 40, "ok": True}]))

    out = rt.chat([{"role": "user", "content": "kesir"}])

    assert out["meta"]["dropped_citations"] == 1
    assert out["meta"]["tool_calls"][0]["name"] == "kazanim_ara"
    assert "[S5]" not in out["answer"]
    assert len(out["citations"]) == 1


def test_system_prompt_forbids_inventing_locators():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "uydurma" in p.lower()
    for token in ("kazanım kodu", "sayfa numarası"):
        assert token in p.lower()


def test_system_prompt_names_the_authority_split():
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "ogrenci_verisi_ara" in p
    assert "kazanim_ara" in p


def test_system_prompt_keeps_the_citation_contract():
    assert "[S1]" in AssistantRuntime.SYSTEM_PROMPT


def test_system_prompt_no_longer_bans_citation_markers():
    """The old prompt ended with 'never finish with a Kaynaklar list' AND the
    frontend stripped markers — together they made citation impossible."""
    assert "Kaynaklar:' listesiyle bitirme" not in AssistantRuntime.SYSTEM_PROMPT


def test_system_prompt_calls_both_tools_for_hybrid_questions():
    """A question like 'ödevimdeki kesir konusunu anlat' touches both Işık's
    own record and a curriculum topic — the prompt must say to call both
    tools in sequence, not silently pick one bucket."""
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "iki aracı da çağır" in p
    assert "kaynakların karışmaması demektir, aracın tekliği değil" in p


def test_system_prompt_allows_general_knowledge_without_fabricated_citation():
    """Out-of-scope general-knowledge questions must be answerable, but the
    answer must not carry a [S] marker implying it came from a tool."""
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "genel bilgi sorulursa yanıtla" in p
    assert "o cümleye [S] atıfı ekleme" in p


def test_no_fabrication_rule_does_not_forbid_general_knowledge():
    """The fabrication ban and the general-knowledge permission sit in different
    sections, and read together the ban can cancel the permission — leaving a
    child's ordinary question refused. The ban is scoped to tool-backed claims."""
    p = AssistantRuntime.SYSTEM_PROMPT
    assert "Bu madde araç çıktısına dayanan cümleler içindir" in p
    assert "genel bilgi" in p


def test_chat_events_streams_tool_progress_in_real_time(tmp_path, monkeypatch):
    """Fix round 3, Bulgu 1. Measured before this fix: five events for two
    dispatch() calls 0.3s apart all landed within 0.9s of each other — i.e.
    chat_events() buffered every event until chat() had already returned
    and replayed them in one burst. That makes the commit's own claim
    ("stream the assistant's progress while it consults sources") false in
    production: the reader sees a flicker right before the answer, not
    live progress.

    This pins the fix: the first tool_start event must arrive almost
    immediately (long before the two 0.3s sleeps have elapsed), and the
    final answer must trail it by roughly the full elapsed delay — proof
    the generator is actually being fed through the worker-thread queue as
    chat() runs, not replaying a list assembled after the fact.
    """
    (tmp_path / "output").mkdir()
    runtime = AssistantRuntime(tmp_path)

    SLEEP = 0.3

    def slow_chat_with_tools(*, dispatch, **kwargs):
        dispatch("kazanim_ara", {"q": "kesir"})
        time.sleep(SLEEP)
        dispatch("mufredat_ara", {"q": "kesir"})
        time.sleep(SLEEP)
        return ToolLoopResult(text="TEST_ANSWER [S1]", citations=[])

    monkeypatch.setattr(runtime.registry, "declarations", lambda: [])
    monkeypatch.setattr(runtime.registry, "degraded", lambda: [])
    monkeypatch.setattr(runtime.gemini, "chat_with_tools", slow_chat_with_tools)

    start = time.perf_counter()
    timestamps: list[tuple[str, float]] = []
    for event in runtime.chat_events(
        messages=[{"role": "user", "content": "kesir"}],
        session_id="s1",
    ):
        timestamps.append((event["event"], time.perf_counter() - start))

    names = [t[0] for t in timestamps]
    assert names == ["tool_start", "tool_end", "tool_start", "tool_end", "answer"]

    first_tool_start_t = timestamps[0][1]
    answer_t = timestamps[-1][1]

    # A buffered implementation would deliver every event clustered near
    # answer_t, all at once, after both sleeps have already elapsed. A
    # genuinely streamed one delivers the first tool_start almost
    # immediately — well under one sleep interval.
    assert first_tool_start_t < SLEEP / 2, (
        f"first tool_start arrived at {first_tool_start_t:.3f}s — "
        "events are still being buffered, not streamed"
    )
    # And the final answer must trail the first event by roughly the full
    # dispatched delay (two 0.3s sleeps), not land in the same instant.
    assert answer_t - first_tool_start_t >= SLEEP * 1.5, (
        f"answer arrived only {answer_t - first_tool_start_t:.3f}s after "
        "the first tool_start — events were not actually interleaved with "
        "chat() running"
    )


def test_concurrent_chat_events_do_not_leak_dispatch_between_calls(tmp_path, monkeypatch):
    """Fix round 3, Bulgu 2. chat_events() used to monkey-patch the shared
    self.registry.dispatch — safe only if calls never overlap. gthread
    workers (this task) make real concurrency possible for the first time,
    and the reviewer measured the leak directly: with threading.Event used
    to force interleaving, thread A's own event stream showed thread B's
    tool name.

    This test forces the same interleaving deterministically (one shared
    AssistantRuntime — the same shape as the process-wide singleton in
    production — with two concurrent chat_events() calls, coordinated so
    the second call's dispatch runs strictly inside the window where the
    first call's chat() is still executing) and asserts each call's stream
    contains only its own tool name, never the other's.
    """
    (tmp_path / "output").mkdir()
    runtime = AssistantRuntime(tmp_path)
    monkeypatch.setattr(runtime.registry, "declarations", lambda: [])
    monkeypatch.setattr(runtime.registry, "degraded", lambda: [])

    first_dispatched = threading.Event()
    second_done = threading.Event()
    call_order_lock = threading.Lock()
    call_counter = {"n": 0}

    def shared_chat_with_tools(*, dispatch, **kwargs):
        with call_order_lock:
            call_counter["n"] += 1
            is_first = call_counter["n"] == 1
        if is_first:
            dispatch("TOOL_FIRST", {})
            first_dispatched.set()
            # Hold this call's chat() open until the second call has also
            # dispatched its own tool — exactly the window in which a
            # shared self.registry.dispatch mutation would let the second
            # call's tool name leak into this stream (or vice versa).
            assert second_done.wait(timeout=5), "second call never dispatched"
            return ToolLoopResult(text="ANSWER_FIRST", citations=[])
        else:
            assert first_dispatched.wait(timeout=5), "first call never dispatched"
            dispatch("TOOL_SECOND", {})
            second_done.set()
            return ToolLoopResult(text="ANSWER_SECOND", citations=[])

    monkeypatch.setattr(runtime.gemini, "chat_with_tools", shared_chat_with_tools)

    events_by_thread: dict[str, list[dict]] = {}
    errors: list[BaseException] = []

    def worker(key: str) -> None:
        try:
            events_by_thread[key] = list(runtime.chat_events(
                messages=[{"role": "user", "content": key}], session_id=key))
        except BaseException as exc:  # noqa: BLE001 - surfaced via `errors`
            errors.append(exc)

    t1 = threading.Thread(target=worker, args=("thread1",))
    t2 = threading.Thread(target=worker, args=("thread2",))
    t1.start()
    # Give thread1 a head start so it deterministically becomes "first" in
    # shared_chat_with_tools — not load-bearing for the assertion itself,
    # only for which key maps to which tool name below.
    time.sleep(0.05)
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors, f"worker thread raised: {errors}"
    assert set(events_by_thread) == {"thread1", "thread2"}

    # The load-bearing assertion: whichever call ran "first" vs "second"
    # internally, each thread's own event stream must contain only the one
    # tool name it dispatched — never the other thread's — even though
    # both calls shared one AssistantRuntime/one McpRegistry instance.
    for key, events in events_by_thread.items():
        tool_names = {e["name"] for e in events if e["event"] in ("tool_start", "tool_end")}
        assert len(tool_names) == 1, (
            f"{key}'s stream saw {tool_names} — a shared-registry mutation "
            "leaked another call's tool name into this one"
        )

    seen_tools = {
        next(iter({e["name"] for e in events if e["event"] in ("tool_start", "tool_end")}))
        for events in events_by_thread.values()
    }
    assert seen_tools == {"TOOL_FIRST", "TOOL_SECOND"}


def test_abandoned_stream_stops_the_worker_at_the_next_tool_boundary(tmp_path, monkeypatch):
    """A reader who thinks the assistant is stuck presses "yeniden üret" or
    navigates away. The SSE response is torn down, but the worker thread
    running chat() is a daemon that nobody was telling to stop — so it kept
    going through the whole remaining tool loop, spending Gemini turns and
    MCP calls on an answer no one would ever see. With four gthread workers
    and an impatient reader that compounds into several abandoned loops at
    once.

    Cancellation is cooperative and checked at tool boundaries, which is the
    only hook chat_events() actually has: an HTTP call already in flight
    still finishes. This pins the bound — after the consumer stops reading,
    at most the in-flight tool completes and no further tool runs.
    """
    (tmp_path / "output").mkdir()
    runtime = AssistantRuntime(tmp_path)

    dispatched: list[str] = []
    reached_end = threading.Event()

    def many_tools(*, dispatch, **kwargs):
        for i in range(6):
            dispatch(f"tool_{i}", {})
            time.sleep(0.05)
        reached_end.set()
        return ToolLoopResult(text="TEST_ANSWER", citations=[])

    def counting_dispatch(name, args):
        dispatched.append(name)
        return SimpleNamespace(ok=True, payload={}, error=None)

    monkeypatch.setattr(runtime.registry, "declarations", lambda: [])
    monkeypatch.setattr(runtime.registry, "degraded", lambda: [])
    monkeypatch.setattr(runtime.registry, "dispatch", counting_dispatch)
    monkeypatch.setattr(runtime.gemini, "chat_with_tools", many_tools)

    stream = runtime.chat_events(
        messages=[{"role": "user", "content": "kesir"}], session_id="s1")

    # Consume just the first event, then abandon the generator the way a
    # disconnected SSE client does.
    first = next(stream)
    assert first["event"] == "tool_start"
    stream.close()

    # Give the worker more than enough time to have run the remaining five
    # tools had nothing stopped it.
    time.sleep(0.6)

    assert not reached_end.is_set(), (
        "chat() ran to completion after the client went away — "
        "the abandoned stream is still spending model turns")
    assert len(dispatched) <= 2, (
        f"{len(dispatched)} tools ran after the client disconnected "
        f"({dispatched}); cancellation should stop at the next boundary")
