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

```bash
# Pull embedding models (default + fallback challenger)
ollama pull mxbai-embed-large
ollama pull nomic-embed-text

# Incremental knowledge reindex
python src/reindex_assistant.py

# Full rebuild
python src/reindex_assistant.py --full

# Verify index (embedding-enabled go-live gate)
python src/assistant_ops.py verify-index --max-age-minutes 180 --require-embeddings
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

CPU-only öneri: `ASSISTANT_OLLAMA_CHAT_TIMEOUT_SECONDS=70`, `ASSISTANT_OLLAMA_CHAT_NUM_PREDICT=96`, `ASSISTANT_OLLAMA_KEEP_ALIVE=30m`, `ASSISTANT_ENABLE_LLM_PLAN_SUMMARY=0`, Gunicorn `--timeout 360`; `ASSISTANT_CHAT_FALLBACK_MODEL=qwen2.5:14b`.

Go-live runbook: `docs/assistant-go-live.md`
