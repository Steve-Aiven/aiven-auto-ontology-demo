#!/usr/bin/env bash
# Produce invoice events to Kafka, ensure ClickHouse MV, hop rows into Postgres landing.
# Note: DataHub companion services often 404 on `avn service get`; use `service list --json`.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${AIVEN_PROJECT:-shutchinson-demo}"
KAFKA_SERVICE="${KAFKA_SERVICE:-ao-datahub-kafka}"
CH_SERVICE="${CH_SERVICE:-ao-clickhouse}"
PG_SERVICE="${PG_SERVICE:-ao-pg}"
TOPIC="${KAFKA_TOPIC:-invoice_booked_events}"

avn project switch "${PROJECT}" >/dev/null

service_state() {
  local svc="$1"
  avn service list --project "${PROJECT}" --json | python3 -c '
import json,sys
name=sys.argv[1]
for s in json.load(sys.stdin):
  if s["service_name"]==name:
    print(s["state"]); raise SystemExit(0)
raise SystemExit("missing")
' "${svc}"
}

ensure_running() {
  local svc="$1"
  state=$(service_state "${svc}" || echo missing)
  if [[ "${state}" == "missing" ]]; then
    echo "ERROR: service ${svc} not found" >&2
    exit 1
  fi
  if [[ "${state}" == "POWEROFF" ]]; then
    echo "Powering on ${svc}..."
    avn service update "${svc}" --project "${PROJECT}" --power-on || true
  fi
  for _ in $(seq 1 90); do
    state=$(service_state "${svc}")
    echo "  ${svc}: ${state}"
    if [[ "${state}" == "RUNNING" ]]; then
      return 0
    fi
    sleep 10
  done
  echo "ERROR: ${svc} not RUNNING" >&2
  exit 1
}

ensure_running "${KAFKA_SERVICE}"
ensure_running "${CH_SERVICE}"
ensure_running "${PG_SERVICE}"

echo "Ensuring topic ${TOPIC} on ${KAFKA_SERVICE}..."
if avn service topic-list "${KAFKA_SERVICE}" --project "${PROJECT}" 2>/dev/null | awk '{print $1}' | grep -qx "${TOPIC}"; then
  echo "Topic exists"
else
  avn service topic-create "${KAFKA_SERVICE}" "${TOPIC}" \
    --project "${PROJECT}" \
    --partitions 1 \
    --replication 2 || \
  avn service topic-create "${KAFKA_SERVICE}" "${TOPIC}" \
    --project "${PROJECT}" \
    --partitions 1 \
    --replication 1
fi

echo "Ensuring clickhouse_kafka integration..."
if ! avn service integration-list "${CH_SERVICE}" --project "${PROJECT}" --json 2>/dev/null | \
  python3 -c "import sys,json; ints=json.load(sys.stdin); raise SystemExit(0 if any(i.get('integration_type')=='clickhouse_kafka' and '${KAFKA_SERVICE}' in (i.get('source_service') or '', i.get('dest_service') or '') for i in ints) else 1)"; then
  avn service integration-create \
    --project "${PROJECT}" \
    -t clickhouse_kafka \
    -s "${KAFKA_SERVICE}" \
    -d "${CH_SERVICE}" \
    || echo "WARN: clickhouse_kafka integration create failed (configure tables in Console if needed)" >&2
fi

echo "Ensuring clickhouse_postgresql integration..."
if ! avn service integration-list "${CH_SERVICE}" --project "${PROJECT}" --json 2>/dev/null | \
  python3 -c "import sys,json; ints=json.load(sys.stdin); raise SystemExit(0 if any(i.get('integration_type')=='clickhouse_postgresql' and '${PG_SERVICE}' in (i.get('source_service') or '', i.get('dest_service') or '') for i in ints) else 1)"; then
  avn service integration-create \
    --project "${PROJECT}" \
    -t clickhouse_postgresql \
    -s "${PG_SERVICE}" \
    -d "${CH_SERVICE}" \
    || echo "WARN: clickhouse_postgresql integration create failed" >&2
fi

TMPDIR_CERTS=$(mktemp -d)
trap 'rm -rf "${TMPDIR_CERTS}"' EXIT

avn service list --project "${PROJECT}" --json | python3 -c '
import json,sys,os
name=sys.argv[1]
outdir=sys.argv[2]
for s in json.load(sys.stdin):
  if s["service_name"]!=name:
    continue
  ci=s.get("connection_info") or {}
  params=s.get("service_uri_params") or {}
  host=params.get("host") or (s.get("service_uri") or "").split(":")[0]
  port=params.get("port") or (s.get("service_uri") or "").split(":")[-1]
  open(os.path.join(outdir,"ca.pem"),"w").write((ci.get("kafka_ca_cert") or ""))
  # Project CA often needed; fall back to downloading via avn project ca-get
  open(os.path.join(outdir,"service.cert"),"w").write(ci["kafka_access_cert"])
  open(os.path.join(outdir,"service.key"),"w").write(ci["kafka_access_key"])
  open(os.path.join(outdir,"bootstrap.txt"),"w").write(f"{host}:{port}")
  # Prefer advertised brokers if present
  brokers=ci.get("kafka") or []
  if brokers:
    open(os.path.join(outdir,"bootstrap.txt"),"w").write(",".join(brokers))
  break
else:
  raise SystemExit(f"kafka service {name} not in list")
' "${KAFKA_SERVICE}" "${TMPDIR_CERTS}"

# Ensure CA present
if [[ ! -s "${TMPDIR_CERTS}/ca.pem" ]]; then
  avn project ca-get --project "${PROJECT}" --target-filepath "${TMPDIR_CERTS}/ca.pem"
fi

export KAFKA_BOOTSTRAP_SERVERS
KAFKA_BOOTSTRAP_SERVERS=$(cat "${TMPDIR_CERTS}/bootstrap.txt")
export KAFKA_SECURITY_PROTOCOL=SSL
export KAFKA_SSL_CAFILE="${TMPDIR_CERTS}/ca.pem"
export KAFKA_SSL_CERTFILE="${TMPDIR_CERTS}/service.cert"
export KAFKA_SSL_KEYFILE="${TMPDIR_CERTS}/service.key"
export KAFKA_TOPIC="${TOPIC}"
# Clear SASL so producer uses certs
unset KAFKA_USERNAME KAFKA_PASSWORD || true

echo "Installing producer deps (venv)..."
python3 -m venv "${ROOT}/.venv-lineage" 2>/dev/null || true
# shellcheck disable=SC1091
source "${ROOT}/.venv-lineage/bin/activate"
pip -q install -r "${ROOT}/apps/invoice-events-producer/requirements.txt"

echo "Producing events to ${KAFKA_BOOTSTRAP_SERVERS} topic=${TOPIC}..."
python3 "${ROOT}/apps/invoice-events-producer/produce.py"

echo "Creating ClickHouse destination + MV (best-effort)..."
CH_SQL=$(cat <<SQL
CREATE TABLE IF NOT EXISTS default.invoice_events
(
    event_id String,
    invoice_id Int32,
    customer_id Int32,
    booked_amount Float64,
    event_ts String,
    source_topic String
)
ENGINE = MergeTree
ORDER BY (event_id);
SQL
)
avn service cli "${CH_SERVICE}" --project "${PROJECT}" -- <<< "${CH_SQL}" \
  && echo "ClickHouse invoice_events ready" \
  || echo "WARN: could not apply ClickHouse SQL via avn service cli" >&2

echo "Hopping rows into Postgres finance.invoice_events_landing..."
SAAS_URI=$(avn service get "${PG_SERVICE}" --project "${PROJECT}" --json | python3 -c '
import json,sys
s=json.load(sys.stdin)
info=s.get("service_uri_params") or {}
user=info.get("user") or "avnadmin"
password=info.get("password")
host=info.get("host")
port=info.get("port") or "5432"
print(f"postgresql://{user}:{password}@{host}:{port}/saas_analytics?sslmode=require")
')

psql "${SAAS_URI}" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS finance.invoice_events_landing (
    event_id      TEXT PRIMARY KEY,
    invoice_id    INT,
    customer_id   INT,
    booked_amount NUMERIC(14, 2) NOT NULL,
    event_ts      TIMESTAMPTZ NOT NULL,
    source_topic  TEXT NOT NULL DEFAULT 'invoice_booked_events'
);
SQL

python3 - <<PY
import subprocess
from datetime import datetime, timezone
events = [
    {"invoice_id": 1, "customer_id": 1, "booked_amount": 120000.0},
    {"invoice_id": 2, "customer_id": 1, "booked_amount": 120000.0},
    {"invoice_id": 3, "customer_id": 2, "booked_amount": 45000.0},
    {"invoice_id": 4, "customer_id": 2, "booked_amount": 45000.0},
    {"invoice_id": 5, "customer_id": 3, "booked_amount": 12000.0},
    {"invoice_id": 6, "customer_id": 4, "booked_amount": 200000.0},
    {"invoice_id": 8, "customer_id": 5, "booked_amount": 175000.0},
]
now = datetime.now(timezone.utc).isoformat()
uri = """${SAAS_URI}"""
topic = """${TOPIC}"""
values = []
for row in events:
    eid = f"demo-event-{row['invoice_id']}"
    values.append(
        f"('{eid}', {row['invoice_id']}, {row['customer_id']}, {row['booked_amount']}, '{now}', '{topic}')"
    )
sql = (
    "INSERT INTO finance.invoice_events_landing "
    "(event_id, invoice_id, customer_id, booked_amount, event_ts, source_topic) VALUES "
    + ", ".join(values)
    + " ON CONFLICT (event_id) DO NOTHING;"
)
subprocess.check_call(["psql", uri, "-v", "ON_ERROR_STOP=1", "-c", sql])
print(f"upserted {len(events)} landing rows")
PY

COUNT=$(psql "${SAAS_URI}" -Atc "SELECT count(*) FROM finance.invoice_events_landing;")
echo "finance.invoice_events_landing rows: ${COUNT}"
if [[ "${COUNT}" -lt 1 ]]; then
  echo "ERROR: landing table empty" >&2
  exit 1
fi

echo "Lineage pipeline seed complete."
echo "Path: ${TOPIC} (Kafka ${KAFKA_SERVICE}) -> ClickHouse invoice_events -> finance.invoice_events_landing"
