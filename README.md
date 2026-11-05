# Aiven Auto Ontology Demo

End-to-end demo of [NVIDIA Auto Ontology](https://github.com/NVIDIA/auto-ontology) paired with [Aiven DataHub](https://aiven.io/docs/products/datahub) on Aiven project **`shutchinson-demo`**.

| Concern | Aiven piece |
| --- | --- |
| Catalog / lineage / governance | DataHub (`ao-datahub`) + MCP |
| Chat / NL-to-SQL | AI Gateway (`https://ai.aiven.io/v1`) |
| Embeddings | OpenSearch ML Commons via `apps/os-embed-shim` |
| Ontology store + vectors | PostgreSQL + pgvector |
| Analytics source | `saas_analytics` (conflicting revenue defs + PII email) |
| Light lineage path | Kafka `invoice_booked_events` -> ClickHouse -> `finance.invoice_events_landing` |
| Apps | Aiven Runtime (`compose.aiven.yaml`) |
| Agent chat (parallel) | Cursor MCP, or Managed Agents (`booked-revenue`) |

See [docs/demo-walkthrough.md](docs/demo-walkthrough.md) for the full presenter walkthrough, plus [docs/positioning-datahub-vs-auto-ontology.md](docs/positioning-datahub-vs-auto-ontology.md) and [docs/demo-script-datahub-auto-ontology.md](docs/demo-script-datahub-auto-ontology.md). For the KubeCon TTS screenshot teaser: [docs/demo-video.md](docs/demo-video.md).

## Quick path

```bash
cp .env.example .env
# Create an AI Gateway key in Console -> AI Gateway, paste into AIVEN_AI_GATEWAY_API_KEY

chmod +x scripts/*.sh scripts/*.py
./scripts/provision_aiven.sh
./scripts/provision_datahub_estate.sh
./scripts/enable_pgvector.sh
./scripts/seed_saas.sh
./scripts/seed_lineage_pipeline.sh
./scripts/deploy_os_embed_model.sh   # prints OS_EMBED_MODEL_ID
./scripts/write_env_from_aiven.sh
# Edit .env: AIVEN_AI_GATEWAY_API_KEY, OS_EMBED_MODEL_ID, DATAHUB_GMS_URL, DATAHUB_GMS_TOKEN

./scripts/seed_datahub_governance.sh
python3 scripts/agent_demo_harness.py

# Optional Managed Agents path (Console: Agents -> Enable agents first):
# Edit .env: AUTO_ONTOLOGY_MCP_PUBLIC_URL, AUTO_ONTOLOGY_MCP_TOKEN
# python3 scripts/mint_auto_ontology_api_token.py   # once frontend is up
python3 scripts/provision_managed_agent.py

# Local smoke of shim against Aiven OpenSearch (optional):
docker compose up -d --build os-embed-shim
./scripts/smoke_test.sh
```

### Runtime apps

- Embeddings shim service: **`ao-embed-shim`** (deployed from this repo’s `apps/os-embed-shim`, integrated with `ao-opensearch`).
- Full Auto Ontology UI stack: Console → Runtime → Deploy → select [`compose.aiven.yaml`](compose.aiven.yaml), then set `AIVEN_AI_GATEWAY_API_KEY`, `AUTH_SECRET`, `OS_EMBED_MODEL_ID`, and Postgres `CONNECTION_STRINGS` for `saas_analytics`.

### Agent surfaces

- **Cursor MCP:** [docs/mcp-cursor.example.json](docs/mcp-cursor.example.json) (DataHub via `uvx mcp-server-datahub@latest`, Auto Ontology at `…/mcp`).
- **Managed Agents:** recipe [demo/agents/booked-revenue.yaml](demo/agents/booked-revenue.yaml), provision with `python3 scripts/provision_managed_agent.py`, then Console → Agents → `booked-revenue` → Chat.
- **Harness backup:** `python3 scripts/agent_demo_harness.py`.

GitHub: https://github.com/Steve-Aiven/aiven-auto-ontology-demo

To connect a private fork for Runtime scanning, install the Aiven GitHub app for org **Solutions Architecture**: https://github.com/apps/aiven-platform/installations/select_target

## Demo script

1. Open DataHub UI; show lineage Kafka -> CH -> landing -> invoices; PII on `billing_email`; Finance ownership.
2. Open Auto Ontology UI (Runtime public URL or `localhost:3000`).
3. Sign in with `AUTO_ONTOLOGY_ADMIN_EMAIL` / `AUTO_ONTOLOGY_ADMIN_PASSWORD`.
4. Confirm `saas_analytics` connection and run ingest.
5. Certify glossary term `booked_revenue` per [docs/ontology-term-booked-revenue.md](docs/ontology-term-booked-revenue.md).
6. Ask: **What was booked revenue in Q3 2025?** Expected total **717000** USD from finance invoices only.
7. Ask: **What was revenue last quarter?** Should prefer booked after certification, not ARR/pipeline.
8. Optional agent loop: Cursor MCP, Managed Agents Console chat (`provision_managed_agent.py`), or `python3 scripts/agent_demo_harness.py`.

## Talk track

- Without ontology: Sales ARR and Marketing pipeline look like "revenue" and are orders of magnitude larger.
- With DataHub: estate catalog, lineage, owners, PII gates for agents.
- With Auto Ontology: certified `booked_revenue` -> SQL on `finance.invoices` where `status = 'booked'`.

## Layout

```
apps/os-embed-shim/          OpenAI /v1/embeddings -> OS ML Commons
apps/invoice-events-producer/ Kafka producer for lineage demo
apps/auto-ontology-*/        Thin Dockerfiles FROM nvcr.io/nvidia/...
compose.aiven.yaml           Runtime Compose
docker-compose.yml           Local helper
data/saas/                   Sample schema + seed
scripts/                     Provision, seed, lineage, governance, harness, Managed Agents
demo/agents/                 Managed Agents recipe (booked-revenue)
docs/                        Positioning + demo script + MCP example
```

## Notes

- Auto Ontology expects OpenAI-compatible embeddings; OS ML Commons does not. The shim bridges them.
- AI Gateway is chat-only today ([AIG-416](https://aiven.atlassian.net/browse/AIG-416) for embeddings). This demo uses Gateway for LLM and OpenSearch for vectors.
- Rerank is disabled in v1 (API shape mismatch). Chat still works.
- App images build from `vendor/nvidia-auto-ontology` using `Dockerfile.aiven` (public Ubuntu base). NGC app tags were not publicly pullable without auth.
- DataHub companion stack is large; under node quota the demo Kafka topic lives on `ao-datahub-kafka` by default (see `scripts/provision_datahub_estate.sh`).
- Provisioned demo services: see `scripts/verify_transcript.md`.
