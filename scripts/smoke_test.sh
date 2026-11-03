#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ROOT}/.env"
  set +a
fi

fail=0

echo "== AI Gateway chat =="
if [[ -z "${AIVEN_AI_GATEWAY_API_KEY:-}" ]]; then
  echo "SKIP: AIVEN_AI_GATEWAY_API_KEY not set"
else
  if curl -sS "https://ai.aiven.io/v1/chat/completions" \
    -H "Authorization: Bearer ${AIVEN_AI_GATEWAY_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"'"${DEFAULT_MODELS_MODEL:-nemotron-nano-3-30b}"'","messages":[{"role":"user","content":"Reply with the word pong only."}],"max_tokens":16}' \
    | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r["choices"][0]["message"]["content"][:200])'; then
    echo "OK gateway"
  else
    echo "FAIL gateway"
    fail=1
  fi
fi

echo "== Embed shim =="
SHIM_URL="${SHIM_URL:-http://127.0.0.1:8080}"
if curl -sf "${SHIM_URL}/health" >/dev/null; then
  if curl -sS "${SHIM_URL}/v1/embeddings" \
    -H "Content-Type: application/json" \
    -d '{"input":"booked revenue","model":"os-embed"}' \
    | python3 -c 'import json,sys; r=json.load(sys.stdin); print("dims", len(r["data"][0]["embedding"]))'; then
    echo "OK shim"
  else
    echo "FAIL shim embeddings (is OS_EMBED_MODEL_ID set and model deployed?)"
    fail=1
  fi
else
  echo "SKIP: shim not reachable at ${SHIM_URL}"
fi

echo "== Auto Ontology health (optional) =="
AO_URL="${AO_URL:-http://127.0.0.1:3001}"
if curl -sf "${AO_URL}/api/health/live" >/dev/null 2>&1 || curl -sf "${AO_URL}/health/live" >/dev/null 2>&1; then
  echo "OK backend live"
else
  echo "SKIP: Auto Ontology backend not reachable at ${AO_URL}"
fi

exit "${fail}"
