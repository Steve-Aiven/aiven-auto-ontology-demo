# Verification transcript

Date: 2026-11-03

## Aiven project `shutchinson-demo`

| Service | Name | State |
| --- | --- | --- |
| PostgreSQL | `ao-pg` | RUNNING (pgvector enabled on `defaultdb` and `saas_analytics`) |
| OpenSearch | `ao-opensearch` | RUNNING (`ml_commons_only_run_on_ml_node=false`) |
| AI Gateway | project tab | Chat OK (`nemotron-nano-3-30b` replied `pong`) |

## OpenSearch ML Commons

- Model: `huggingface/sentence-transformers/all-MiniLM-L6-v2` v1.0.1
- Model ID: `_HFvoqEBhFU2okjlVtw0`
- Predict smoke: **384** dims

## os-embed-shim (local against Aiven OS)

```text
GET /health -> {"status":"ok"}
POST /v1/embeddings {"input":"booked revenue"} -> dims 384
```

## SaaS seed

- Database `saas_analytics` loaded with finance / sales / marketing conflicting revenue tables
- Expected Q3 2025 booked revenue: **717000** USD

## Auto Ontology UI / Runtime

- NGC `nvcr.io/nvidia/auto-ontology:latest` is not publicly pullable; images build from `vendor/nvidia-auto-ontology` via `Dockerfile.aiven` (Ubuntu base).
- Local `docker build -f vendor/nvidia-auto-ontology/Dockerfile.aiven` → **success** (`auto-ontology:aiven`).
- GitHub: https://github.com/Steve-Aiven/aiven-auto-ontology-demo (public)
- Runtime app **`ao-embed-shim`** created (OpenSearch integration + `OS_EMBED_MODEL_ID`); redeploy in progress after connection-string fix.
- Full UI: deploy `compose.aiven.yaml` from Console Runtime, or run `docker compose` with `.env` pointing at Aiven PG/OS/Gateway.

## Smoke script

`./scripts/smoke_test.sh` with Gateway key + local shim: Gateway OK, shim OK.
