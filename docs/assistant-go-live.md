# TEDY Assistant Go-Live Runbook

Bu döküman yerel assistant için güvenli canlıya alma akışını standartlaştırır.

## 0) Önkoşullar

- Ollama çalışıyor olmalı (`OLLAMA_BASE_URL`, varsayılan `http://localhost:11434`)
- Dashboard API servisi ayağa kalkabiliyor olmalı (`src/dashboard_api.py`)
- Repo kökünde sanal ortam ve bağımlılıklar hazır olmalı

## 1) Security & Preflight

### 1.1 API key üret

```bash
python src/assistant_ops.py generate-key --bytes 48 --env-line
```

Örnek çıktı:

```bash
ASSISTANT_API_KEY=<generated-secret>
```

### 1.2 Env ayarları (server)

Aşağıdaki değişkenleri server environment'ına ekle:

```bash
ASSISTANT_API_KEY=<strong-secret>
ASSISTANT_CHAT_MODEL=qwen2.5-coder:7b
ASSISTANT_CHAT_FALLBACK_MODEL=qwen2.5:14b
ASSISTANT_EMBED_MODEL=mxbai-embed-large
ASSISTANT_AUTO_REINDEX=1
ASSISTANT_ENABLE_EMBEDDINGS=1
ASSISTANT_ENABLE_LLM_PLAN_SUMMARY=0
ASSISTANT_ENABLE_OCR=0
ASSISTANT_OLLAMA_CHAT_TIMEOUT_SECONDS=70
ASSISTANT_OLLAMA_EMBED_TIMEOUT_SECONDS=60
ASSISTANT_OLLAMA_CHAT_NUM_PREDICT=96
ASSISTANT_OLLAMA_KEEP_ALIVE=30m
```

Not: Secret değerlerini repo dosyalarına commit etme.

### 1.3 Embedding modellerini indir

```bash
ollama pull mxbai-embed-large
ollama pull nomic-embed-text
```

## 2) First Full Index Bootstrap

```bash
python src/reindex_assistant.py --full
python src/assistant_ops.py verify-index --max-age-minutes 180 --require-embeddings
```

Beklenen:

- `output/assistant_index/manifest.json`
- `output/assistant_index/chunks.json`
- `output/assistant_index/meta.json`
- `files_indexed > 0`, `chunks_indexed > 0`
- `embedded_chunks > 0`

## 3) API Bring-up & Contract Smoke

Servisi başlat/restart et (systemd user service veya local run).
CPU-only ortamda Gunicorn worker timeout değerini `>=360` tut.
Not: CPU-only canlıda `qwen2.5-coder:7b` varsayılan tutulur; `ASSISTANT_CHAT_FALLBACK_MODEL=qwen2.5:14b` challenger olarak kalır.

```bash
python src/assistant_ops.py smoke \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --model qwen2.5:14b \
  --timeout 240
```

Bu komut şunları doğrular:

- `/v1/models` keysiz `401`
- `/v1/models` key ile `200`
- `/v1/chat/completions` minimal payload `200`
- `plan=true` çağrısında `plan_blocks` dolu

## 4) CureoHub Integration Validation

CureoHub connector:

- Base URL: `https://<host>` veya `http://127.0.0.1:8085`
- Endpoint: `/v1/chat/completions`
- Auth: `Authorization: Bearer <ASSISTANT_API_KEY>`

Senaryo doğrulama:

```bash
python src/assistant_ops.py validate-cureohub \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --model qwen2.5:14b \
  --timeout 90 \
  --output output/cureohub_validation.json
```

Kontrol edilenler:

- Veri sorusunda citation
- Plan modunda plan blocks
- Kaynak-yok durumda limited-confidence sinyali
- Riskli içerikte safety flag

## 5) Traffic Observation & Tuning Loop

### 5.1 Metrik özet

```bash
python src/assistant_ops.py metrics \
  --metrics-path output/assistant_metrics.jsonl \
  --output output/assistant_metrics_report_day1.json \
  --balanced-gate
```

İzlenen metrikler:

- `latency` p50/p95
- citation coverage ratio
- safety flag dağılımı
- intent dağılımı

### 5.2 A/B prompt replay

Prompt set: `docs/assistant_prompt_set.json`

Profil A (hız):

```bash
ASSISTANT_CHAT_MODEL=qwen2.5:7b \
ASSISTANT_EMBED_MODEL=mxbai-embed-large \
python src/assistant_ops.py replay \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --model qwen2.5:7b \
  --prompt-set docs/assistant_prompt_set.json \
  --tag profile_a_7b_mxbai \
  --timeout 90
```

Profil B (denge):

```bash
ASSISTANT_CHAT_MODEL=qwen2.5:14b \
ASSISTANT_EMBED_MODEL=mxbai-embed-large \
python src/assistant_ops.py replay \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --model qwen2.5:14b \
  --prompt-set docs/assistant_prompt_set.json \
  --tag profile_b_14b_mxbai \
  --timeout 90
```

Embed challenger (nomic) için indeks değiştir:

```bash
ASSISTANT_EMBED_MODEL=nomic-embed-text python src/reindex_assistant.py --full
python src/assistant_ops.py verify-index --max-age-minutes 180 --require-embeddings
```

Profil C (hız, nomic):

```bash
ASSISTANT_CHAT_MODEL=qwen2.5:7b \
ASSISTANT_EMBED_MODEL=nomic-embed-text \
python src/assistant_ops.py replay \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --model qwen2.5:7b \
  --prompt-set docs/assistant_prompt_set.json \
  --tag profile_c_7b_nomic \
  --timeout 90
```

Profil D (denge, nomic):

```bash
ASSISTANT_CHAT_MODEL=qwen2.5:14b \
ASSISTANT_EMBED_MODEL=nomic-embed-text \
python src/assistant_ops.py replay \
  --base-url http://127.0.0.1:8085 \
  --api-key "$ASSISTANT_API_KEY" \
  --model qwen2.5:14b \
  --prompt-set docs/assistant_prompt_set.json \
  --tag profile_d_14b_nomic \
  --timeout 90
```

Dört profil için `output/assistant_eval_*.json` dosyalarını karşılaştır.

Karar sırası:

1. Kritik safety ihlali = 0
2. Yüksek citation coverage
3. Düşük p95 latency
4. TR öğrenci+veli okunabilirliği

## 6) Rollback & Failure Playbook

- Chat model sorunu:

```bash
export ASSISTANT_CHAT_MODEL=qwen2.5:7b
# service restart
```

- Embed sorunu:

```bash
export ASSISTANT_EMBED_MODEL=nomic-embed-text
python src/reindex_assistant.py --full
# service restart
```

- Kritik arıza (geçici BM25-only):

```bash
export ASSISTANT_ENABLE_EMBEDDINGS=0
python src/reindex_assistant.py --full
# service restart
```

- İndeks bozulması:

```bash
python src/reindex_assistant.py --full
python src/assistant_ops.py verify-index
```

- Auth sorunu:

```bash
curl -i http://127.0.0.1:8085/v1/models
curl -i -H "Authorization: Bearer $ASSISTANT_API_KEY" http://127.0.0.1:8085/v1/models
```

## 7) OpenAI-Compatible Request/Response örneği

Request:

```json
{
  "model": "qwen2.5:14b",
  "messages": [
    {"role": "user", "content": "Bu hafta ödev önceliğim ne?"}
  ],
  "temperature": 0.2,
  "session_id": "cureohub-session-1",
  "context_filters": {},
  "plan": false
}
```

Response (özet):

```json
{
  "object": "chat.completion",
  "choices": [{"message": {"role": "assistant", "content": "..."}}],
  "citations": [{"id": "S1", "path": "..."}],
  "safety_flags": [],
  "plan_blocks": [],
  "meta": {"model": "qwen2.5:14b", "latency_ms": 1234}
}
```
