#!/usr/bin/env bash
# Seed DataHub governance metadata (owners, glossary, PII tags, lineage).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

: "${DATAHUB_GMS_URL:?Set DATAHUB_GMS_URL to DataHub Application URL (…/api/gms)}"
: "${DATAHUB_GMS_TOKEN:?Set DATAHUB_GMS_TOKEN to a DataHub personal access token}"

export DATAHUB_GMS_URL DATAHUB_GMS_TOKEN
export KAFKA_SERVICE="${KAFKA_SERVICE:-ao-datahub-kafka}"
export CH_SERVICE="${CH_SERVICE:-ao-clickhouse}"

python3 "${ROOT}/scripts/seed_datahub_governance.py"
