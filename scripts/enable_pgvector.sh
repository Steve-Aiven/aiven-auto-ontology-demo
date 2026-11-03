#!/usr/bin/env bash
set -euo pipefail

PROJECT="${AIVEN_PROJECT:-shutchinson-demo}"
PG_SERVICE="${PG_SERVICE:-ao-pg}"

avn project switch "${PROJECT}" >/dev/null

uri=$(avn service get "${PG_SERVICE}" --project "${PROJECT}" --json | python3 -c '
import json,sys
s=json.load(sys.stdin)
info=s.get("service_uri_params") or {}
user=info.get("user") or "avnadmin"
password=info.get("password")
host=info.get("host")
port=info.get("port") or "5432"
dbname=info.get("dbname") or "defaultdb"
print(f"postgresql://{user}:{password}@{host}:{port}/{dbname}?sslmode=require")
')

echo "Enabling vector extension on defaultdb..."
psql "${uri}" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS vector;"
echo "pgvector enabled."
