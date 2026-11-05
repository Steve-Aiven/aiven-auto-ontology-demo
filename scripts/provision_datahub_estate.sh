#!/usr/bin/env bash
# Provision DataHub (+ companions) and ClickHouse for the Auto Ontology / DataHub demo estate.
#
# Project node quota note:
#   Aiven DataHub startup-1 brings companion Kafka + OpenSearch + apps.
#   A separate estate Kafka (ao-kafka) often exceeds project node quota.
#   This script uses ao-datahub-kafka for the demo invoice_booked_events topic.
#   Optional: set CREATE_ESTATE_KAFKA=1 to also try ao-kafka (startup-4).
set -euo pipefail

PROJECT="${AIVEN_PROJECT:-shutchinson-demo}"
CLOUD="${AIVEN_CLOUD:-google-us-east1}"
DH_SERVICE="${DH_SERVICE:-ao-datahub}"
KAFKA_SERVICE="${KAFKA_SERVICE:-ao-datahub-kafka}"
ESTATE_KAFKA_SERVICE="${ESTATE_KAFKA_SERVICE:-ao-kafka}"
CH_SERVICE="${CH_SERVICE:-ao-clickhouse}"
PG_SERVICE="${PG_SERVICE:-ao-pg}"
DH_PLAN="${DH_PLAN:-startup-1}"
KAFKA_PLAN="${KAFKA_PLAN:-startup-4}"
CH_PLAN="${CH_PLAN:-startup-8}"
TOPIC="${KAFKA_TOPIC:-invoice_booked_events}"
CREATE_ESTATE_KAFKA="${CREATE_ESTATE_KAFKA:-0}"

echo "Using project=${PROJECT} cloud=${CLOUD}"

avn project switch "${PROJECT}" >/dev/null

create_if_missing() {
  local name="$1" type="$2" plan="$3"
  if avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${name}"; then
    echo "Service ${name} already exists"
    return 0
  fi
  echo "Creating ${type} ${name} (${plan})..."
  if ! avn service create "${name}" \
    --project "${PROJECT}" \
    -t "${type}" \
    --cloud "${CLOUD}" \
    --plan "${plan}"; then
    echo "WARN: failed to create ${name} (often node quota). Continue and inspect." >&2
    return 1
  fi
}

wait_running() {
  local svc="$1"
  for _ in $(seq 1 120); do
    if ! avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${svc}"; then
      echo "  ${svc}: not present yet"
      sleep 10
      continue
    fi
    state=$(avn service get "${svc}" --project "${PROJECT}" --json | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
    echo "  ${svc}: ${state}"
    if [[ "${state}" == "RUNNING" ]]; then
      return 0
    fi
    if [[ "${state}" == "POWEROFF" ]]; then
      echo "Powering on ${svc}..."
      avn service update "${svc}" --project "${PROJECT}" --power-on || true
    fi
    sleep 10
  done
  echo "ERROR: ${svc} did not reach RUNNING" >&2
  return 1
}

create_if_missing "${DH_SERVICE}" datahub "${DH_PLAN}" || true
create_if_missing "${CH_SERVICE}" clickhouse "${CH_PLAN}" || true

if [[ "${CREATE_ESTATE_KAFKA}" == "1" ]]; then
  create_if_missing "${ESTATE_KAFKA_SERVICE}" kafka "${KAFKA_PLAN}" || true
fi

echo "Waiting for DataHub control plane and companions..."
wait_running "${DH_SERVICE}" || true
# Companions are created by the DataHub service
for svc in ao-datahub-gms ao-datahub-frontend ao-datahub-kafka ao-datahub-opensearch; do
  if avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${svc}"; then
    wait_running "${svc}" || true
  fi
done

wait_running "${CH_SERVICE}" || true

echo "Ensuring Kafka topic ${TOPIC} on ${KAFKA_SERVICE}..."
if avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${KAFKA_SERVICE}"; then
  wait_running "${KAFKA_SERVICE}" || true
  if avn service topic-list "${KAFKA_SERVICE}" --project "${PROJECT}" 2>/dev/null | awk '{print $1}' | grep -qx "${TOPIC}"; then
    echo "Topic ${TOPIC} already exists"
  else
    avn service topic-create "${KAFKA_SERVICE}" "${TOPIC}" \
      --project "${PROJECT}" \
      --partitions 1 \
      --replication 2 || \
    avn service topic-create "${KAFKA_SERVICE}" "${TOPIC}" \
      --project "${PROJECT}" \
      --partitions 1 \
      --replication 1 || true
  fi
else
  echo "WARN: ${KAFKA_SERVICE} missing; skip topic create" >&2
fi

echo "Ensuring ClickHouse <-> Kafka integration (${KAFKA_SERVICE} -> ${CH_SERVICE})..."
if avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${CH_SERVICE}" \
  && avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${KAFKA_SERVICE}"; then
  if avn service integration-list "${CH_SERVICE}" --project "${PROJECT}" --json 2>/dev/null | \
    python3 -c "import sys,json; ints=json.load(sys.stdin); raise SystemExit(0 if any(i.get('integration_type')=='clickhouse_kafka' and '${KAFKA_SERVICE}' in (i.get('source_service') or '', i.get('dest_service') or '') for i in ints) else 1)"; then
    echo "clickhouse_kafka integration already present"
  else
    avn service integration-create \
      --project "${PROJECT}" \
      -t clickhouse_kafka \
      -s "${KAFKA_SERVICE}" \
      -d "${CH_SERVICE}" \
      || echo "WARN: clickhouse_kafka integration create failed" >&2
  fi
fi

echo "Ensuring ClickHouse <-> Postgres integration..."
if avn service list --project "${PROJECT}" | awk '{print $1}' | grep -qx "${CH_SERVICE}"; then
  if avn service integration-list "${CH_SERVICE}" --project "${PROJECT}" --json 2>/dev/null | \
    python3 -c "import sys,json; ints=json.load(sys.stdin); raise SystemExit(0 if any(i.get('integration_type')=='clickhouse_postgresql' and '${PG_SERVICE}' in (i.get('source_service') or '', i.get('dest_service') or '') for i in ints) else 1)"; then
    echo "clickhouse_postgresql integration already present"
  else
    avn service integration-create \
      --project "${PROJECT}" \
      -t clickhouse_postgresql \
      -s "${PG_SERVICE}" \
      -d "${CH_SERVICE}" \
      || echo "WARN: clickhouse_postgresql integration create failed" >&2
  fi
fi

cat <<EOF

Done (or partially done under node quota).

Next:
  1. DataHub Console -> Add connectors for ao-pg, ${KAFKA_SERVICE}, ${CH_SERVICE}, ao-opensearch (Emit lineage)
  2. ./scripts/seed_saas.sh
  3. ./scripts/seed_lineage_pipeline.sh
  4. Set DATAHUB_GMS_URL + DATAHUB_GMS_TOKEN in .env, then ./scripts/seed_datahub_governance.sh
  5. Power on ao-opensearch / ao-embed-shim when running Auto Ontology UI

Kafka topic for demo events: ${TOPIC} on ${KAFKA_SERVICE}
EOF
avn service list --project "${PROJECT}"
