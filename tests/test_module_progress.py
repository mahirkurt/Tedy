"""Module progress: strict event schema, idempotent aggregation, cross-process single writer."""
import json
import multiprocessing
import time
from contextlib import nullcontext

import pytest

from src.module_progress import ProgressEventError, ProgressStore, validate_event

SLUG, V = "fen5-su", 2
U1, U2 = "a" * 32, "b" * 32
NOW = 1_800_000_000.0  # 2027-01-15T08:00:00Z


def ev(event="answer", **over):
    base = {"type": "edupedia:progress", "v": 1, "slug": SLUG, "version": V, "event": event,
            "xp": 10, "ts": 1789400000000}
    if event == "answer":
        base.update(segmentId="q1", item=0, correct=True, attempts=1)
    if event == "segment_complete":
        base.update(segmentId="t1")
    base.update(over)
    return base


def test_valid_events_normalise():
    assert validate_event(ev(), SLUG, V) == {
        "event": "answer", "xp": 10, "segmentId": "q1", "item": 0, "correct": True, "attempts": 1}
    assert validate_event(ev("ready"), SLUG, V) == {"event": "ready", "xp": 10}
    assert validate_event(ev("segment_complete"), SLUG, V) == {"event": "segment_complete", "xp": 10, "segmentId": "t1"}


@pytest.mark.parametrize("payload,reason", [
    ("x", "nesne_degil"),
    (ev(extra=1), "bilinmeyen_alan"),
    (ev(type="edupedia:restore"), "tip"),
    (ev(v=2), "tip"),
    (ev(slug="baska"), "modul_uyusmazligi"),
    (ev(version=3), "modul_uyusmazligi"),
    (ev(event="hack"), "olay"),
    (ev(xp=-1), "xp"),
    (ev(xp=True), "xp"),
    (ev(ts="1"), "ts"),
    (ev(segmentId="q1<script>"), "segmentId"),
    (ev(item=1000), "item"),
    (ev(correct="yes"), "correct"),
    (ev(attempts=0), "attempts"),
])
def test_invalid_events_are_rejected(payload, reason):
    with pytest.raises(ProgressEventError) as exc:
        validate_event(payload, SLUG, V)
    assert exc.value.reason == reason


def test_segment_id_with_trailing_newline_is_rejected(tmp_path):
    """Control for .fullmatch(): .match() would wrongly accept 'q1\n'."""
    with pytest.raises(ProgressEventError) as exc:
        validate_event(ev(segmentId="q1\n"), SLUG, V)
    assert exc.value.reason == "segmentId"


def test_user_hash_with_trailing_newline_is_rejected(tmp_path):
    """Control for .fullmatch(): .match() would wrongly accept valid-32-hex + '\n'."""
    store = ProgressStore(tmp_path / "p.json")
    user_hash_with_newline = "a" * 32 + "\n"
    with pytest.raises(ValueError):
        store.record(user_hash_with_newline, SLUG, V, {"event": "ready", "xp": 0}, NOW)


def test_record_is_idempotent_and_monotonic(tmp_path):
    store = ProgressStore(tmp_path / "module_progress.json")
    store.record(U1, SLUG, V, validate_event(ev(correct=False, attempts=1, xp=0), SLUG, V), NOW)
    store.record(U1, SLUG, V, validate_event(ev(correct=True, attempts=2, xp=15), SLUG, V), NOW + 1)
    store.record(U1, SLUG, V, validate_event(ev(correct=True, attempts=2, xp=15), SLUG, V), NOW + 2)  # retry
    store.record(U1, SLUG, V, validate_event(ev("segment_complete", xp=15), SLUG, V), NOW + 3)
    state = store.record(U1, SLUG, V, validate_event(ev("module_complete", xp=5), SLUG, V), NOW + 4)
    assert state == {"answers": ["q1#0"], "done": ["t1"], "xp": 15}
    assert store.state_for(U2, SLUG, V) == {"answers": [], "done": [], "xp": 0}
    assert store.summary(SLUG) == {"slug": SLUG, "surumler": [{
        "version": 2, "kisi_sayisi": 1, "cevaplanan_soru": 1, "dogru_orani": 1.0,
        "deneme_toplam": 2, "tamamlayan": 1, "son_erisim": "2027-01-15T08:00:04+00:00"}]}


def test_wrong_only_answer_is_not_restored_and_ratio_is_zero(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    state = store.record(U2, SLUG, V, validate_event(ev(correct=False, attempts=3), SLUG, V), NOW)
    assert state["answers"] == []
    row = store.summary(SLUG, version=V)["surumler"][0]
    assert row["dogru_orani"] == 0.0 and row["deneme_toplam"] == 3 and row["tamamlayan"] == 0
    assert store.summary("yok") == {"slug": "yok", "surumler": []}
    assert store.summary(SLUG, version=9)["surumler"] == []


def test_record_refuses_invalid_identifiers(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    with pytest.raises(ValueError):
        store.record(U1, "../x", V, {"event": "ready", "xp": 0}, NOW)
    with pytest.raises(ValueError):
        store.record("kisa", SLUG, V, {"event": "ready", "xp": 0}, NOW)


class SlowStore(ProgressStore):
    """Widens the read-modify-write window so a missing lock loses updates."""

    def read(self):
        data = super().read()
        time.sleep(0.02)
        return data


class UnlockedSlowStore(SlowStore):
    def _locked(self):
        return nullcontext()


def _writer(cls, path, worker, count):
    store = cls(path)
    for i in range(count):
        event = validate_event(ev(segmentId=f"q{worker}", item=i), SLUG, V)
        store.record(U1, SLUG, V, event, NOW)


def _answers_after_writers(cls, path, workers=4, count=10):
    ctx = multiprocessing.get_context("fork")
    procs = [ctx.Process(target=_writer, args=(cls, path, w, count)) for w in range(workers)]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(60)
    exit_codes = [proc.exitcode for proc in procs]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        answers = len(data["moduller"][SLUG][f"v{V}"]["kisiler"][U1]["cevaplar"])
    except (OSError, ValueError, KeyError):
        answers = 0
    return answers, exit_codes


def test_concurrent_writer_processes_lose_no_updates(tmp_path):
    answers, exit_codes = _answers_after_writers(SlowStore, tmp_path / "p.json")
    assert exit_codes == [0, 0, 0, 0]
    assert answers == 40


def test_without_the_lock_updates_are_lost(tmp_path):
    # Control for the test above: the same workload without flock drops writes
    # (or corrupts the shared .tmp file), so a green lock test is not vacuous.
    answers, _ = _answers_after_writers(UnlockedSlowStore, tmp_path / "p.json")
    assert answers < 40
