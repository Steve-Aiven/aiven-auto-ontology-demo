# Aiven Auto Ontology Demo

End-to-end demo of [NVIDIA Auto Ontology](https://github.com/NVIDIA/auto-ontology) on Aiven project **`shutchinson-demo`**.

| Concern | Aiven piece |
| --- | --- |
| Chat / NL-to-SQL | AI Gateway (`https://ai.aiven.io/v1`) |
| Embeddings | OpenSearch ML Commons via `apps/os-embed-shim` |
| Ontology store + vectors | PostgreSQL + pgvector |
| Analytics source | `saas_analytics` database (conflicting revenue defs) |
| Apps | Aiven Runtime (`compose.aiven.yaml`) |

DataHub is **not** deployed in v1. See [docs/positioning-datahub-vs-auto-ontology.md](docs/positioning-datahub-vs-auto-ontology.md).

## Quick path

```bash
cp .env.example .env
# Create an AI Gateway key in Console -> AI Gateway, paste into AIVEN_AI_GATEWAY_API_KEY

chmod +x scripts/*.sh
./scripts/provision_aiven.sh
./scripts/enable_pgvector.sh
./scripts/seed_saas.sh
./scripts/deploy_os_embed_model.sh   # prints OS_EMBED_MODEL_ID
./scripts/write_env_from_aiven.sh
# Edit .env: AIVEN_AI_GATEWAY_API_KEY + OS_EMBED_MODEL_ID from above

# Local smoke of shim against Aiven OpenSearch (optional):
docker compose up -d --build os-embed-shim
# point OPENSEARCH_* in compose env at Aiven, or run uvicorn with .env
./scripts/smoke_test.sh
```

Deploy apps on **Aiven Runtime**: Console → Runtime → Deploy application → this repo → select `compose.aiven.yaml` → Deploy. Set secrets/`OS_EMBED_MODEL_ID` in the application env.

## Demo script

1. Open Auto Ontology UI (Runtime public URL or `localhost:3000`).
2. Sign in with `AUTO_ONTOLOGY_ADMIN_EMAIL` / `AUTO_ONTOLOGY_ADMIN_PASSWORD`.
3. Confirm `saas_analytics` connection and run ingest.
4. Certify glossary term `booked_revenue` per [docs/ontology-term-booked-revenue.md](docs/ontology-term-booked-revenue.md).
5. Ask: **What was booked revenue in Q3 2025?** Expected total **717000** USD from finance invoices only.
6. Ask: **What was revenue last quarter?** Should prefer booked after certification, not ARR/pipeline.

## Talk track

- Without ontology: Sales ARR and Marketing pipeline look like "revenue" and are orders of magnitude larger.
- With Auto Ontology: certified `booked_revenue` → SQL on `finance.invoices` where `status = 'booked'`.
- DataHub (later): estate catalog/lineage; Auto Ontology: certified answers.

## Layout

```
apps/os-embed-shim/          OpenAI /v1/embeddings -> OS ML Commons
apps/auto-ontology-*/        Thin Dockerfiles FROM nvcr.io/nvidia/...
compose.aiven.yaml           Runtime Compose
docker-compose.yml           Local helper
data/saas/                   Sample schema + seed
scripts/                     Provision, seed, model deploy, smoke
docs/                        Positioning + ontology term notes
```

## Notes

- Auto Ontology expects OpenAI-compatible embeddings; OS ML Commons does not. The shim bridges them.
- AI Gateway is chat-only today ([AIG-416](https://aiven.atlassian.net/browse/AIG-416) for embeddings). This demo uses Gateway for LLM and OpenSearch for vectors.
- Rerank is disabled in v1 (API shape mismatch). Chat still works.
- App images build from `vendor/nvidia-auto-ontology` using `Dockerfile.aiven` (public Ubuntu base). NGC app tags were not publicly pullable without auth.
- Provisioned demo services in `shutchinson-demo`: `ao-pg`, `ao-opensearch`. See `scripts/verify_transcript.md`.
