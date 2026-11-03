#!/usr/bin/env bash
# Register and deploy a pretrained sentence-transformers model on Aiven OpenSearch.
set -euo pipefail

PROJECT="${AIVEN_PROJECT:-shutchinson-demo}"
OS_SERVICE="${OS_SERVICE:-ao-opensearch}"
MODEL_NAME="${OS_EMBED_MODEL_NAME:-huggingface/sentence-transformers/all-MiniLM-L6-v2}"
MODEL_VERSION="${OS_EMBED_MODEL_VERSION:-1.0.1}"
MODEL_FORMAT="${OS_EMBED_MODEL_FORMAT:-TORCH_SCRIPT}"

avn project switch "${PROJECT}" >/dev/null

eval "$(avn service get "${OS_SERVICE}" --project "${PROJECT}" --json | python3 -c '
import json,sys,shlex
s=json.load(sys.stdin)
info=s.get("service_uri_params") or {}
host=info.get("host")
port=info.get("port") or "443"
user=info.get("user") or "avnadmin"
password=info.get("password")
print(f"export OS_HOST={shlex.quote(host)}")
print(f"export OS_PORT={shlex.quote(str(port))}")
print(f"export OS_USER={shlex.quote(user)}")
print(f"export OS_PASSWORD={shlex.quote(password)}")
')"

BASE="https://${OS_HOST}:${OS_PORT}"
AUTH=(-u "${OS_USER}:${OS_PASSWORD}" -k)

echo "OpenSearch at ${BASE}"
echo "Registering model ${MODEL_NAME} ${MODEL_VERSION}..."

register_body=$(python3 -c "import json; print(json.dumps({
  'name': '''${MODEL_NAME}''',
  'version': '''${MODEL_VERSION}''',
  'model_format': '''${MODEL_FORMAT}'''
}))")

reg=$(curl -sS "${AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "${BASE}/_plugins/_ml/models/_register" \
  -d "${register_body}")
echo "${reg}"
task_id=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('task_id',''))" <<<"${reg}")
if [[ -z "${task_id}" ]]; then
  echo "Register did not return task_id; aborting" >&2
  exit 1
fi

echo "Waiting for register task ${task_id}..."
model_id=""
for i in $(seq 1 60); do
  task=$(curl -sS "${AUTH[@]}" "${BASE}/_plugins/_ml/tasks/${task_id}")
  state=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('state',''))" <<<"${task}")
  model_id=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('model_id') or '')" <<<"${task}")
  echo "  state=${state} model_id=${model_id}"
  if [[ "${state}" == "COMPLETED" ]]; then
    break
  fi
  if [[ "${state}" == "FAILED" ]]; then
    echo "${task}" >&2
    exit 1
  fi
  sleep 5
done

if [[ -z "${model_id}" ]]; then
  echo "No model_id after register" >&2
  exit 1
fi

echo "Deploying model ${model_id}..."
dep=$(curl -sS "${AUTH[@]}" -X POST "${BASE}/_plugins/_ml/models/${model_id}/_deploy")
echo "${dep}"
dep_task=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('task_id',''))" <<<"${dep}")

for i in $(seq 1 60); do
  task=$(curl -sS "${AUTH[@]}" "${BASE}/_plugins/_ml/tasks/${dep_task}")
  state=$(python3 -c "import json,sys; print(json.load(sys.stdin).get('state',''))" <<<"${task}")
  echo "  deploy state=${state}"
  if [[ "${state}" == "COMPLETED" ]]; then
    break
  fi
  if [[ "${state}" == "FAILED" ]]; then
    echo "${task}" >&2
    exit 1
  fi
  sleep 5
done

echo "Predict smoke test..."
curl -sS "${AUTH[@]}" -H "Content-Type: application/json" \
  -X POST "${BASE}/_plugins/_ml/_predict/text_embedding/${model_id}" \
  -d '{"text_docs":["booked revenue"],"return_number":true,"target_response":["sentence_embedding"]}' \
  | python3 -c 'import json,sys; r=json.load(sys.stdin); d=r["inference_results"][0]["output"][0]["data"]; print("dims", len(d))'

echo
echo "Set in .env:"
echo "  OS_EMBED_MODEL_ID=${model_id}"
echo "  OS_EMBED_DIMS=384"
