# Verification transcript

Date: 2026-11-03 (updated after DataHub estate)

## Aiven project `shutchinson-demo`

Node quota ACL: `node_count:*=20` (set via Admin API for DataHub + ClickHouse estate).

| Service | Name | State |
| --- | --- | --- |
| DataHub | `ao-datahub` | RUNNING (companions: kafka, opensearch, postgresql, gms, frontend, actions) |
| ClickHouse | `ao-clickhouse` | RUNNING |
| PostgreSQL | `ao-pg` | RUNNING (pgvector; `saas_analytics`) |
| OpenSearch | `ao-opensearch` | recreated (embeddings); may need ML model redeploy |
| Application | `ao-embed-shim` | POWEROFF until needed |
| AI Gateway | project tab | Chat OK earlier (`nemotron-nano-3-30b`) |

## Lineage path

- Topic `invoice_booked_events` on `ao-datahub-kafka`
- Producer: 7/7 events delivered
- Postgres `finance.invoice_events_landing`: **7** rows
- ClickHouse table SQL: [data/saas/clickhouse_invoice_events.sql](../data/saas/clickhouse_invoice_events.sql) (apply via Console / clickhouse-client; `avn service cli` does not support ClickHouse)

## SaaS seed

- `billing_email` PII column + `invoice_events_landing` present
- Expected Q3 2025 booked revenue: **717000** USD

## Agent harness

`python3 scripts/agent_demo_harness.py` — offline evidence scenarios (PII / uncertified / certified). Live GMS/AO when `DATAHUB_GMS_*` and `AUTO_ONTOLOGY_API_URL` are set.

## DataHub console next steps

1. Open DataHub Application URL from Console Connection info (user `datahub`).
2. Add connectors for `ao-pg`, `ao-datahub-kafka`, `ao-clickhouse`, `ao-opensearch` (Emit lineage).
3. Create PAT; set `DATAHUB_GMS_URL` (= Application URL + `/api/gms`) and `DATAHUB_GMS_TOKEN` in `.env`.
4. `./scripts/seed_datahub_governance.sh`

## Notes

- Separate estate Kafka (`ao-kafka`) was dropped under quota; demo events use `ao-datahub-kafka`.
- Companion services often 404 on `avn service get`; scripts use `avn service list --json`.
