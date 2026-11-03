#!/usr/bin/env bash
# Provision Postgres + OpenSearch in shutchinson-demo for the Auto Ontology demo.
set -euo pipefail

PROJECT="${AIVEN_PROJECT:-shutchinson-demo}"
CLOUD="${AIVEN_CLOUD:-google-us-east1}"
PG_SERVICE="${PG_SERVICE:-ao-pg}"
OS_SERVICE="${OS_SERVICE:-ao-opensearch}"
PG_PLAN="${PG_PLAN:-startup-4}"
OS_PLAN="${OS_PLAN:-startup-4}"

echo "Using project=${PROJECT} cloud=${CLOUD}"

avn project switch "${PROJECT}" >/dev/null

if avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${PG_SERVICE}"; then
  echo "Postgres service ${PG_SERVICE} already exists"
else
  echo "Creating Postgres ${PG_SERVICE}..."
  avn service create "${PG_SERVICE}" \
    --project "${PROJECT}" \
    -t pg \
    --cloud "${CLOUD}" \
    --plan "${PG_PLAN}"
fi

if avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${OS_SERVICE}"; then
  echo "OpenSearch service ${OS_SERVICE} already exists"
else
  echo "Creating OpenSearch ${OS_SERVICE}..."
  avn service create "${OS_SERVICE}" \
    --project "${PROJECT}" \
    -t opensearch \
    --cloud "${CLOUD}" \
    --plan "${OS_PLAN}"
fi

echo "Waiting for services to leave REBUILDING/REBALANCING..."
for svc in "${PG_SERVICE}" "${OS_SERVICE}"; do
  for i in $(seq 1 90); do
    state=$(avn service get "${svc}" --project "${PROJECT}" --json | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
    echo "  ${svc}: ${state}"
    if [[ "${state}" == "RUNNING" ]]; then
      break
    fi
    sleep 10
  done
done

echo "Allow ML Commons on data nodes (no dedicated ML node on startup plans)..."
avn service update "${OS_SERVICE}" --project "${PROJECT}" \
  -c opensearch.ml_commons_only_run_on_ml_node=false || true

echo "Done. Next: scripts/enable_pgvector.sh && scripts/deploy_os_embed_model.sh && scripts/seed_saas.sh"
avn service list --project "${PROJECT}"
