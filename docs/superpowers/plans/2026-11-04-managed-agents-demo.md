# Managed Agents Demo Path Implementation Plan

> **For agentic workers:** Implement task-by-task. Prefer superpowers:subagent-driven-development or executing-plans. Steps use checkbox syntax for tracking.

**Goal:** Ship a reproducible Managed Agents path for the DataHub + Auto Ontology demo on `shutchinson-demo`, parallel to Cursor MCP, without replacing the harness.

**Architecture:** Commit a YAML recipe and a Python provisioner that talks to the experimental Aiven Managed Agents API (`/v1/organization/{org}/project/{project}/managed-agents/...`). One-time Console enablement is required (API lists `environments: []` today and has no public enable endpoint). Script upserts custom HTTP MCP integrations when URLs are present, creates/patches the `booked-revenue` agent, and prints the Console Chat URL. Presenter runs the same three prompts as Cursor.

**Tech Stack:** Aiven REST API (auth token via `avn` / `AIVEN_AUTH_TOKEN`), Python 3 + PyYAML, existing `.env` vars.

**Design:** [docs/superpowers/specs/2026-11-04-managed-agents-demo-design.md](../specs/2026-11-04-managed-agents-demo-design.md)

## Global Constraints

- Never commit PATs, AI Gateway keys, or DataHub tokens.
- No em dashes in any generated copy.
- Do not call Managed Agents session/message APIs in this plan.
- Auth: `AIVEN_AUTH_TOKEN` or `~/.config/aiven/aiven-credentials.json`; resolve `organization_id` via `GET /v1/project/{project}`.

---

## Task 1: Design + recipe

- [x] Write design spec covering goal, API surface, enablement prerequisite, DataHub HTTP URL requirement, non-goals.
- [x] Add `demo/agents/booked-revenue.yaml` with name, model, system instructions, integrations, demo prompts.
- [x] Mirror this plan to `docs/superpowers/plans/2026-11-04-managed-agents-demo.md`.

## Task 2: Provision script

- [x] Implement `scripts/provision_managed_agent.py` (load env/recipe, auth, environment gate, upsert integrations, upsert agent, print Console path).
- [x] Make script executable; document usage in module docstring.
- [x] Smoke-test empty-environment path and `--help`.

## Task 3: Docs and env

- [x] Update Act 4 in walkthrough: Path A Cursor, Path B Managed Agents, Path C harness.
- [x] Pre-flight: enable Agents; run provision script; keep harness tab.
- [x] Update short demo script + README.
- [x] Extend `.env.example` with `DATAHUB_MCP_URL` and Managed Agents notes on `AUTO_ONTOLOGY_MCP_PUBLIC_URL`.

## Verification

- [x] `python3 scripts/provision_managed_agent.py` with Agents disabled → clear enable message, non-zero exit.
- [ ] After Console enable: script creates/updates agent; re-run is idempotent (operator: enable Agents in Console, then re-run).
- [x] Walkthrough Path B documented for a second reader without Cursor.
