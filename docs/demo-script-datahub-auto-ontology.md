# Demo script: DataHub + Auto Ontology

Full presenter walkthrough (timing, talk track, prompts, fallbacks): [demo-walkthrough.md](demo-walkthrough.md).

## Estate (Aiven project `shutchinson-demo`)

| Service | Role |
| --- | --- |
| `ao-datahub` (+ companions) | Catalog, lineage, owners, PII tags, glossary |
| `ao-datahub-kafka` | Demo topic `invoice_booked_events` (shared under node quota) |
| `ao-clickhouse` | Warehouse hop for invoice events |
| `ao-pg` / `saas_analytics` | Ontology store + certified finance facts |
| `ao-opensearch` + `ao-embed-shim` | Embeddings for Auto Ontology |

Under project node quota, a separate `ao-kafka` is optional (`CREATE_ESTATE_KAFKA=1`). Default demos use `ao-datahub-kafka` for business events.

## Live URLs

- DataHub UI: Console → `ao-datahub` → Application URL (login user `datahub`, password from Connection info).
- GMS for MCP: Application URL + `/api/gms`.

## One-time setup

```bash
./scripts/provision_datahub_estate.sh
./scripts/seed_saas.sh
./scripts/seed_lineage_pipeline.sh
```

### DataHub connectors (Console)

1. Open the DataHub UI for `ao-datahub`.
2. Add connectors for `ao-pg`, `ao-datahub-kafka`, `ao-clickhouse`, and `ao-opensearch`.
3. Enable **Emit lineage** where offered.
4. Create a Personal Access Token (Generate / Manage Access Tokens).
5. Connection info: Application URL + `/api/gms` -> `DATAHUB_GMS_URL`.

```bash
# .env
DATAHUB_GMS_URL=https://YOUR-HOST/api/gms
DATAHUB_GMS_TOKEN=YOUR_PAT

./scripts/seed_datahub_governance.sh
```

### Cursor MCP

Copy [mcp-cursor.example.json](mcp-cursor.example.json) into `.cursor/mcp.json` (or merge), replace PAT/URL, and point Auto Ontology at your Runtime/local MCP URL (`…/mcp`).

### Managed Agents (parallel agent chat)

1. Console → **Agents → Enable agents** on `shutchinson-demo`.
2. Set `AUTO_ONTOLOGY_MCP_PUBLIC_URL` (and optional `DATAHUB_MCP_URL` for HTTP DataHub MCP).
3. `python3 scripts/provision_managed_agent.py`
4. Chat at **Agents → booked-revenue** with the same three Act 4 prompts as Cursor.

Recipe: [demo/agents/booked-revenue.yaml](../demo/agents/booked-revenue.yaml).

## Live talk track

1. **Without governance:** ask an agent “what was revenue last quarter?” Risk: ARR or pipeline.
2. **DataHub discovery:** search revenue / invoices. Show Finance ownership on `finance.invoices`, NonCertified on Sales/Marketing, lineage Kafka -> ClickHouse -> landing -> invoices.
3. **PII gate:** search `billing_email`. Show PII/Sensitive tags. Agent must refuse dumping emails.
4. **Certified answer:** Auto Ontology, term `booked_revenue`. Ask “What was booked revenue in Q3 2025?” Expect **717000** USD and SQL on `finance.invoices` where `status = 'booked'`.

## Agent surfaces

| Path | When to use |
| --- | --- |
| Cursor + both MCPs | Laptop agent loop |
| Managed Agents Console chat | Same loop hosted on Aiven |
| `python3 scripts/agent_demo_harness.py` | Offline / flake backup |

Harness runs three scenarios (PII fail, uncertified fail, certified success). Uses live GMS/AO APIs when env is set; otherwise offline evidence in `data/datahub_governance_evidence.json`.
