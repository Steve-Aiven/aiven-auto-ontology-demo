# Design: Managed Agents demo path

Date: 2026-11-04

## Goal

Add Aiven Managed Agents as a **parallel** Act 4 agent surface beside Cursor MCP for the DataHub + Auto Ontology demo on project `shutchinson-demo`. Same tools, same three prompts, same punchline (**717000**). Offline `scripts/agent_demo_harness.py` stays the backup.

## Decisions

- Approach: committed recipe (`demo/agents/booked-revenue.yaml`) + idempotent `scripts/provision_managed_agent.py` against the experimental Managed Agents REST API.
- Tools on the agent: DataHub MCP + Auto Ontology MCP only (no Aiven MCP in this path).
- Live interaction: Console Agents chat (not the session/message API).
- Enablement: one-time Console step (Request access → Enable agents). The public API lists environments but has no enable endpoint; empty `environments` is a hard failure with clear instructions.
- Auto Ontology integration: HTTP `custom_url` from `AUTO_ONTOLOGY_MCP_PUBLIC_URL` (append `/mcp` when needed).
- DataHub integration: HTTP `DATAHUB_MCP_URL` when set (Managed Agents custom integrations are URL-based). Cursor continues to use local `uvx mcp-server-datahub@latest` with `DATAHUB_GMS_*`. No new DataHub HTTP shim in this design; if `DATAHUB_MCP_URL` is unset, the script still creates/updates the agent and prints Console steps to attach DataHub.
- Auth: `AIVEN_AUTH_TOKEN` or `~/.config/aiven/aiven-credentials.json`; resolve `organization_id` via `GET /v1/project/{project}`.

## API surface (experimental)

Base: `/v1/organization/{organization_id}/project/{project}/managed-agents/`

| Call | Purpose |
| --- | --- |
| `GET .../environment` | Resolve environment name; fail if empty |
| `GET .../integration/catalog` | Discover catalog types (custom HTTP via `custom_url`) |
| `POST .../environment/{env}/integration` | Connect MCP integration |
| `GET` / `POST` / `PATCH .../agent` | List, create, update agent |

## Architecture

```text
.env + booked-revenue.yaml
        |
        v
provision_managed_agent.py  -->  Managed Agents API
        |                            |
        |                            +--> custom AO MCP
        |                            +--> custom DataHub MCP (if URL set)
        |                            +--> agent booked-revenue
        v
Console: Agents -> booked-revenue -> Chat  (Act 4 Path B)
Cursor MCP (Act 4 Path A) | harness (Path C)
```

## Non-goals

- API chat harness / session message automation
- Schedules, webhooks, Aiven MCP on this agent
- KubeCon video beat changes
- DataHub stdio-to-HTTP shim application
- Committing PATs or passwords
