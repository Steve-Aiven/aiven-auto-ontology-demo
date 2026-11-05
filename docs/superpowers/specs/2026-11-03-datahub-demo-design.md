# Design: DataHub + estate for Auto Ontology demo

Date: 2026-11-03

## Goal

Pair Aiven DataHub (map/rulebook) with NVIDIA Auto Ontology (certified calculator) in project `shutchinson-demo`, with a light real lineage path and an agent loop that shows PII and ownership gates before a certified answer.

## Decisions

- Approach: catalog-centric + thin real lineage (Kafka -> ClickHouse -> Postgres landing).
- Plans: DataHub `startup-1`, ClickHouse `startup-8`, Kafka via DataHub companion `ao-datahub-kafka` (`startup-4`) because a second estate Kafka exceeded project node quota. Optional `CREATE_ESTATE_KAFKA=1` for dedicated `ao-kafka`.
- Project node quota raised to `node_count:*=20` via Admin API `PUT /v1/projects/shutchinson-demo/node-quota` so DataHub companion Postgres + ClickHouse fit.
- Agent surface: Cursor MCP (live) + Managed Agents `booked-revenue` (parallel) + `scripts/agent_demo_harness.py` (backup). See 2026-11-04-managed-agents-demo-design.md.
- Governance: PII on `finance.customers.billing_email`; Finance owns certified `booked_revenue`; Sales/Marketing marked non-certified.
- Cloud: `google-us-east1`.


## Architecture

- Estate: `ao-datahub` (+ companions), `ao-datahub-kafka`, `ao-clickhouse`, `ao-pg`, `ao-opensearch`, `ao-embed-shim`.
- Pipeline: producer -> topic `invoice_booked_events` -> CH `invoice_events` -> `finance.invoice_events_landing` -> conceptual hop to `finance.invoices`.
- Auto Ontology unchanged for certified Q3 total **717000**.

## Non-goals

- Runtime-hosted agent product UI.
- Production ETL.
- Committing PATs or passwords.
