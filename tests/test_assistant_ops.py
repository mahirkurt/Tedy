import argparse
import json
from pathlib import Path

from src import assistant_ops


def test_summarize_metrics_basic():
    records = [
        {
            "type": "chat",
            "latency_ms": 100,
            "citations": 2,
            "intent": "data_query",
            "safety_flags": [],
        },
        {
            "type": "chat",
            "latency_ms": 300,
            "citations": 0,
            "intent": "general",
            "safety_flags": ["warning:limited_confidence"],
        },
        {
            "type": "plan",
            "latency_ms": 500,
            "intent": "study_plan",
            "safety_flags": [],
        },
    ]

    summary = assistant_ops._summarize_metrics(records)

    assert summary["total_records"] == 3
    assert summary["latency"]["p50_ms"] > 0
    assert summary["citation"]["chat_records"] == 2
    assert summary["citation"]["coverage_ratio"] == 0.5
    assert summary["safety_flags"]["warning:limited_confidence"] == 1


def test_verify_index_fails_when_missing(tmp_path: Path):
    args = argparse.Namespace(
        index_dir=str(tmp_path / "assistant_index"),
        max_age_minutes=180,
        allow_stale=False,
    )
    rc = assistant_ops.cmd_verify_index(args)
    assert rc == 1


def test_verify_index_passes_with_valid_files(tmp_path: Path):
    idx = tmp_path / "assistant_index"
    idx.mkdir(parents=True)

    (idx / "manifest.json").write_text(
        json.dumps({"files": {}, "stats": {"files": 2, "chunks": 2}}),
        encoding="utf-8",
    )
    (idx / "chunks.json").write_text(
        json.dumps([
            {"chunk_id": "a", "text": "abc"},
            {"chunk_id": "b", "text": "def"},
        ]),
        encoding="utf-8",
    )
    (idx / "meta.json").write_text(
        json.dumps(
            {
                "generated_at": "2099-01-01T00:00:00Z",
                "files_indexed": 2,
                "chunks_indexed": 2,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        index_dir=str(idx),
        max_age_minutes=180,
        allow_stale=False,
        require_embeddings=False,
    )
    rc = assistant_ops.cmd_verify_index(args)
    assert rc == 0


def test_verify_index_requires_embeddings(tmp_path: Path):
    idx = tmp_path / "assistant_index"
    idx.mkdir(parents=True)

    (idx / "manifest.json").write_text(
        json.dumps({"files": {}, "stats": {"files": 2, "chunks": 2}}),
        encoding="utf-8",
    )
    (idx / "chunks.json").write_text(
        json.dumps([{"chunk_id": "a", "text": "abc"}]),
        encoding="utf-8",
    )
    (idx / "meta.json").write_text(
        json.dumps(
            {
                "generated_at": "2099-01-01T00:00:00Z",
                "files_indexed": 2,
                "chunks_indexed": 2,
                "embedded_chunks": 0,
            }
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        index_dir=str(idx),
        max_age_minutes=180,
        allow_stale=False,
        require_embeddings=True,
    )
    rc = assistant_ops.cmd_verify_index(args)
    assert rc == 1


def test_metrics_command_writes_summary(tmp_path: Path):
    metrics = tmp_path / "assistant_metrics.jsonl"
    metrics.write_text(
        "\n".join(
            [
                json.dumps({"type": "chat", "latency_ms": 111, "citations": 1, "intent": "data_query", "safety_flags": []}),
                json.dumps({"type": "chat", "latency_ms": 222, "citations": 0, "intent": "general", "safety_flags": ["warning:limited_confidence"]}),
            ]
        ),
        encoding="utf-8",
    )

    out = tmp_path / "summary.json"
    args = argparse.Namespace(
        metrics_path=str(metrics),
        last_n=0,
        output=str(out),
        json=False,
        balanced_gate=False,
        max_p95_ms=0.0,
        min_citation_coverage=-1.0,
        max_critical_safety=-1,
        critical_safety_prefix="risk:",
    )

    rc = assistant_ops.cmd_metrics(args)
    assert rc == 0
    assert out.exists()

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["total_records"] == 2


def test_metrics_balanced_gate_fails_on_critical_safety(tmp_path: Path):
    metrics = tmp_path / "assistant_metrics.jsonl"
    metrics.write_text(
        "\n".join(
            [
                json.dumps({"type": "chat", "latency_ms": 100, "citations": 1, "intent": "data_query", "safety_flags": ["risk:mental_health_crisis"]}),
                json.dumps({"type": "chat", "latency_ms": 200, "citations": 1, "intent": "data_query", "safety_flags": []}),
            ]
        ),
        encoding="utf-8",
    )

    args = argparse.Namespace(
        metrics_path=str(metrics),
        last_n=0,
        output="",
        json=False,
        balanced_gate=True,
        max_p95_ms=0.0,
        min_citation_coverage=-1.0,
        max_critical_safety=-1,
        critical_safety_prefix="risk:",
    )

    rc = assistant_ops.cmd_metrics(args)
    assert rc == 1
