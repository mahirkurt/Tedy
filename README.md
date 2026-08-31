# TED

A Python project.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python -m src.main
```

## Test

```bash
pytest
```

## Assistant

The chat path runs on the Gemini API and needs no local model server. The
knowledge index is BM25 only — `reindex_assistant.py` writes
`embeddings_enabled: false`, so no embedding model is pulled or called.

```bash
# Incremental knowledge reindex
python src/reindex_assistant.py

# Full rebuild
python src/reindex_assistant.py --full

# Verify index (omit --require-embeddings: embedded_chunks is always 0 here)
python src/assistant_ops.py verify-index --max-age-minutes 180
```

```bash
# Generate strong assistant API key
python src/assistant_ops.py generate-key --bytes 48 --env-line

# Smoke-test OpenAI-compatible endpoints
python src/assistant_ops.py smoke --base-url http://127.0.0.1:8085 --api-key "$ASSISTANT_API_KEY" --timeout 240

# CureoHub scenario validation
python src/assistant_ops.py validate-cureohub --base-url http://127.0.0.1:8085 --api-key "$ASSISTANT_API_KEY"

# Metrics summary + balanced SLO gate (p95<=10s, citation>=75%, critical safety=0)
python src/assistant_ops.py metrics --metrics-path output/assistant_metrics.jsonl --balanced-gate
```

MCP curriculum tools need `MUFREDAT_MCP_API_KEY` and `EGITIM_KAYNAK_MCP_API_KEY`
**in `.env`** — the service reads `EnvironmentFile=.env` and never sees your
shell. Without them the assistant still answers, from local records only, and
reports both servers as degraded.

Go-live runbook: `docs/assistant-go-live.md`
