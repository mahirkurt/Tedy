#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/mnt/thunderbolt/workspaces/TED"
cd "$ROOT_DIR"

if [ -f .env ]; then
  # shellcheck disable=SC1091
  source .env
fi

LOG_PATH="output/assistant_postdeploy.log"
STATUS_PATH="output/assistant_postdeploy_status.json"
mkdir -p output

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

{
  echo "[$(ts)] postdeploy watcher started"
  echo "[$(ts)] waiting for tedy-assistant-reindex.service to finish..."
} >> "$LOG_PATH"

while systemctl --user is-active --quiet tedy-assistant-reindex.service; do
  sleep 20
done

echo "[$(ts)] reindex service inactive, running deployment checks" >> "$LOG_PATH"

set +e
.venv/bin/python src/assistant_ops.py verify-index --max-age-minutes 180 --require-embeddings >> "$LOG_PATH" 2>&1
verify_rc=$?
smoke_rc=0

if [ "$verify_rc" -eq 0 ]; then
  .venv/bin/python src/assistant_ops.py smoke \
    --base-url "${ASSISTANT_BASE_URL:-http://127.0.0.1:8085}" \
    --api-key "${ASSISTANT_API_KEY:-}" \
    --model "${ASSISTANT_CHAT_MODEL:-qwen2.5:14b}" \
    --timeout 180 >> "$LOG_PATH" 2>&1
  smoke_rc=$?
fi
set -e

python3 - <<PY
import json, datetime
out = {
    "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    "verify_rc": int(${verify_rc}),
    "smoke_rc": int(${smoke_rc}),
    "success": bool(${verify_rc} == 0 and ${smoke_rc} == 0),
}
with open("${STATUS_PATH}", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
PY

if [ "$verify_rc" -eq 0 ] && [ "$smoke_rc" -eq 0 ]; then
  echo "[$(ts)] deployment checks passed" >> "$LOG_PATH"
  exit 0
fi

echo "[$(ts)] deployment checks failed verify_rc=$verify_rc smoke_rc=$smoke_rc" >> "$LOG_PATH"
exit 1
