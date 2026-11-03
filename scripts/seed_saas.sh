#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${AIVEN_PROJECT:-shutchinson-demo}"
PG_SERVICE="${PG_SERVICE:-ao-pg}"

avn project switch "${PROJECT}" >/dev/null

read -r ADMIN_URI SAAS_URI < <(avn service get "${PG_SERVICE}" --project "${PROJECT}" --json | python3 -c '
import json,sys
s=json.load(sys.stdin)
info=s.get("service_uri_params") or {}
user=info.get("user") or "avnadmin"
password=info.get("password")
host=info.get("host")
port=info.get("port") or "5432"
base=f"postgresql://{user}:{password}@{host}:{port}"
print(f"{base}/defaultdb?sslmode=require {base}/saas_analytics?sslmode=require")
')

echo "Ensuring database saas_analytics exists..."
psql "${ADMIN_URI}" -v ON_ERROR_STOP=1 -c "SELECT 1 FROM pg_database WHERE datname='saas_analytics'" | grep -q 1 \
  || psql "${ADMIN_URI}" -v ON_ERROR_STOP=1 -c "CREATE DATABASE saas_analytics;"

echo "Enabling vector on both databases..."
psql "${ADMIN_URI}" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql "${SAAS_URI}" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "Loading SaaS schema and seed data..."
psql "${SAAS_URI}" -v ON_ERROR_STOP=1 -f "${ROOT}/data/saas/saas_analytics_only.sql"

echo "Seed complete. CONNECTION_STRINGS should use saas_analytics."
echo "Example:"
echo "  CONNECTION_STRINGS=${SAAS_URI}"
