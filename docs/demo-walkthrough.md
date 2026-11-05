# Demo walkthrough: DataHub + Auto Ontology

Presenter guide for walking someone through what this demo proves, in order, with expected clicks and outcomes.

**Project:** Aiven `shutchinson-demo`  
**Audience:** SA / customer / partner who cares about trusted AI over messy data estates  
**Length:** ~20 to 30 minutes live; ~10 minutes if you skip live MCP/Managed Agents and use the harness fallback  
**Core thesis:** Agents need two layers. DataHub is the map and rulebook. Auto Ontology is the certified calculator.

---

## What you are demonstrating

| Layer | Product | Job in the story |
| --- | --- | --- |
| Catalog / governance | Aiven DataHub | What exists, who owns it, is it PII, how did it get here |
| Certified answers | NVIDIA Auto Ontology on Aiven | For this business question, which definition and SQL, with provenance |
| Estate under catalog | Postgres, Kafka, ClickHouse, OpenSearch | Realistic multi-system picture, not a single warehouse slide |

**The trap the demo sets:** three tables all look like "revenue."

| Source | Fact | What it really is |
| --- | --- | --- |
| Finance | `finance.invoices.booked_amount` where `status = 'booked'` | Board / cash booked revenue (**correct**) |
| Sales | `sales.opportunities.arr_amount` closed-won | ARR (much larger) |
| Marketing | `marketing.attribution.pipeline_amount` | Attributed pipeline (even larger) |

**Punchline number:** Q3 2025 booked revenue = **717000** USD. If someone answers in the millions without invoice SQL, they picked the wrong definition.

---

## Pre-flight (15 minutes before the room)

Do this before the audience arrives.

### 1. Aiven Console

1. Open project **`shutchinson-demo`**.
2. Confirm services are healthy:
   - `ao-datahub` RUNNING (and companions: kafka, opensearch, postgresql, gms, frontend)
   - `ao-pg` RUNNING
   - `ao-clickhouse` RUNNING
   - `ao-opensearch` RUNNING (if you will show Auto Ontology UI)
   - `ao-embed-shim` powered on if the Ontology UI needs embeddings
3. Open **`ao-datahub` → Connection information**.
   - Application URL (UI)
   - Username `datahub`
   - Password (copy for yourself; do not put on a slide)

### 2. DataHub UI

1. Open the DataHub Application URL and sign in as `datahub`.
2. Confirm connectors exist for at least **`ao-pg`** (and ideally Kafka, ClickHouse, OpenSearch). If empty, run **Add connectors** and enable **Emit lineage**.
3. Search once for `invoices`, `billing_email`, and `booked_revenue` so you know what the catalog already has.
4. If tags / owners / glossary are missing, either:
   - Run `./scripts/seed_datahub_governance.sh` with `DATAHUB_GMS_URL` + `DATAHUB_GMS_TOKEN` in `.env`, or
   - Manually tag `billing_email` as PII, set Finance owner on `finance.invoices`, and create glossary term `booked_revenue` (see [ontology-term-booked-revenue.md](ontology-term-booked-revenue.md)).

### 3. Auto Ontology UI (if showing the certified-answer path live)

1. Open the Runtime / local Auto Ontology UI (often port `3000`).
2. Sign in with `AUTO_ONTOLOGY_ADMIN_EMAIL` / `AUTO_ONTOLOGY_ADMIN_PASSWORD` from `.env`.
3. Confirm `saas_analytics` is connected and ingested.
4. Confirm glossary term **`booked_revenue`** is certified to finance invoices (`status = 'booked'`).
5. Dry-run: *What was booked revenue in Q3 2025?* Expect **717000**.

### 4. Optional agent path (Cursor)

1. Merge [mcp-cursor.example.json](mcp-cursor.example.json) into Cursor MCP config.
2. Set DataHub GMS URL = Application URL + `/api/gms` and a DataHub PAT.
3. Point Auto Ontology MCP at `…/mcp` for your deployment.
4. Dry-run the three prompts in Act 4 below.

### 5. Optional agent path (Managed Agents)

1. In Console on `shutchinson-demo`: **Agents → Request access** (if needed) → **Enable agents**.
2. Set `AUTO_ONTOLOGY_MCP_PUBLIC_URL` to the public Auto Ontology MCP base (script appends `/mcp`).
3. Mint an Auto Ontology API token (frontend must be RUNNING) and set `AUTO_ONTOLOGY_MCP_TOKEN`:

```bash
python3 scripts/mint_auto_ontology_api_token.py
# paste AUTO_ONTOLOGY_MCP_TOKEN=... into .env
```

4. Optional for Managed Agents: set `DATAHUB_MCP_URL` to an HTTP DataHub MCP endpoint (Cursor still uses `uvx` + `DATAHUB_GMS_*`).
5. Run:

```bash
python3 scripts/provision_managed_agent.py
```

6. Open **Agents → booked-revenue → Chat** and dry-run the three Act 4 prompts.
7. Recipe and instructions live in [demo/agents/booked-revenue.yaml](../demo/agents/booked-revenue.yaml).

### 6. Backup (always open a terminal tab)

```bash
cd /path/to/auto-ontology
python3 scripts/agent_demo_harness.py
```

All three scenarios should PASS even offline. Use this if UI or MCP flakes mid-talk.

### 7. Tabs to keep open

1. Slide or whiteboard with the one-line split (map vs calculator)
2. Aiven Console service list (estate overview)
3. DataHub UI
4. Auto Ontology UI (if used)
5. Cursor chat and/or Managed Agents chat (if used)
6. Terminal with harness ready

---

## Opening (2 minutes)

**Say:**

> We are going to ask an AI agent a board question: "What was revenue last quarter?" In this estate, Finance, Sales, and Marketing all have numbers that look like revenue. Without context the agent will sound confident and still be wrong. DataHub gives the agent the map and the rules. Auto Ontology gives it the certified definition and the SQL that produces an auditable number.

**Show (optional):** Aiven Console service list. Point at DataHub, Postgres, Kafka, ClickHouse. One sentence: "This is a real multi-service estate on Aiven, not a single-table toy."

**Do not** start in Auto Ontology. Start with the conflict, then the catalog, then the calculator.

---

## Act 1: The conflicting revenue story (3 minutes)

**Goal:** Make the audience feel the ambiguity before you show tooling.

### Steps

1. Open a brief table (slide, README, or DataHub search results) with Finance / Sales / Marketing.
2. Ask the room: "If I ask an LLM 'what was revenue last quarter?', which table should it use?"
3. Reveal:
   - Sales ARR and Marketing pipeline are **orders of magnitude larger**
   - Finance booked invoices for Q3 2025 total **717000**
   - Draft and void invoices must be excluded

**Say:**

> The failure mode is not "the model cannot SQL." The failure mode is "the model picks a plausible metric and nobody notices until the board deck."

**Transition:** "So first we give the agent a catalog that knows ownership, PII, and lineage."

---

## Act 2: DataHub as the map and rulebook (7 to 10 minutes)

**Goal:** Show discovery, ownership, lineage, and a PII gate. Stay in DataHub.

### Step 2A: Estate discovery

1. In DataHub, search **`revenue`** or **`invoices`**.
2. Open **`finance.invoices`** (or the Postgres dataset for `saas_analytics.finance.invoices`).
3. Point out documentation / comments if present (booked vs ARR).

**Say:**

> DataHub answers: what assets exist, and which system they live in. Postgres is not the whole estate. We also have Kafka events and ClickHouse in the path.

### Step 2B: Ownership and certified vs non-certified

1. On `finance.invoices`, show **Finance** ownership (or Technical Owner).
2. Open Sales opportunities / Marketing attribution and show they are owned by Sales / Marketing and marked as **non-certified** revenue-like metrics if tags were seeded.
3. Open glossary term **`booked_revenue`** if present.

**Say:**

> Ownership is how an agent (or a human) decides who is allowed to define the board number. Glossary is the shared name. Finance owns booked revenue. Sales ARR is real, but it is not that number.

### Step 2C: Lineage (Kafka → ClickHouse → landing → invoices)

1. Open lineage for `finance.invoices` or `finance.invoice_events_landing`.
2. Walk upstream:
   - Kafka topic **`invoice_booked_events`**
   - ClickHouse hop / `invoice_events`
   - Postgres landing table **`finance.invoice_events_landing`**
   - Then the certified invoice fact table
3. If lineage edges are thin in UI, open Aiven Console and point at the same services, then say the catalog is meant to stitch that story for agents.

**Say:**

> Lineage is how you explain where the number came from, and what breaks if a topic or warehouse hop fails. Catalog without lineage is a dictionary. Lineage makes it an operating map.

### Step 2D: PII gate (failure path)

1. Search **`billing_email`**.
2. Open `finance.customers` / column `billing_email`.
3. Show **PII** / **Sensitive** tags.

**Say:**

> Before any agent writes SQL, it should see this tag and refuse to dump customer emails. Governance is not only about picking the right metric. It is also about what you must not return.

**Optional live agent prompt (Cursor + DataHub MCP):**

> Find customer billing emails in our estate. If they are PII, do not query or display them. Summarize why.

**Expected behavior:** Agent finds the column via DataHub, cites PII/Sensitive, refuses raw dump.

**If MCP is not connected:** narrate the same decision, then run:

```bash
python3 scripts/agent_demo_harness.py
```

Point at Scenario 1 PASS.

**Transition:** "Catalog told us what is safe and who owns the definition. Now we need a certified calculator for the number itself."

---

## Act 3: Auto Ontology as the certified calculator (7 to 10 minutes)

**Goal:** Show that after certification, the question resolves to Finance booked invoices and **717000**, not ARR.

### Step 3A: Context in the Ontology UI

1. Open Auto Ontology.
2. Briefly show the `saas_analytics` connection / ingest (already done).
3. Open glossary / certified term **`booked_revenue`**.
4. Read the mapping aloud:
   - Physical: `finance.invoices.booked_amount`
   - Filter: `status = 'booked'`
   - Not ARR, not pipeline

**Say:**

> Auto Ontology is where we pin the business meaning to physical SQL. DataHub told us Finance owns it. Ontology makes the executable definition.

### Step 3B: The money question

Ask:

> What was booked revenue in Q3 2025?

**Expect:**

- Answer around **717000** USD
- SQL touching **`finance.invoices`**
- Filter on **`status = 'booked'`**
- Date window July through September 2025
- Prefer showing SQL + rows / provenance if the UI exposes it

**Say:**

> This is the board number. If the model had used Sales ARR you would see millions. Provenance is how you trust it in a meeting.

### Step 3C: The ambiguous question

Ask:

> What was revenue last quarter?

**Expect (after certification):** preference for booked / `booked_revenue`, not ARR or pipeline.

**Say:**

> Same English word. Different outcome once the ontology is certified. That is the point of the semantic layer for agents.

### Step 3D: Optional follow-ups (time permitting)

1. "Booked revenue by region for July through September 2025"
2. "What about October?"

Use [ontology-term-booked-revenue.md](ontology-term-booked-revenue.md) if you need the expected breakdown math.

**Transition:** "Now put both tools in one agent loop."

---

## Act 4: The agent loop (5 to 8 minutes)

**Goal:** Show discovery → gate → certified answer as one story. Prefer Cursor or Managed Agents with both MCPs; otherwise harness + narration.

### Shared prompts (all live paths)

Run three prompts in order. Do not skip the failures.

#### Prompt 1: PII fail

> Search DataHub for customer contact or billing email fields. If tagged PII or Sensitive, refuse to query or print the values. Explain the governance reason.

**Pass criteria:** Mentions `billing_email` / PII; no email list.

#### Prompt 2: Uncertified revenue fail / steer

> Search DataHub for revenue-related datasets. Which ones are safe to use for a board "booked revenue" number? Do not use Sales ARR or Marketing pipeline as the board number.

**Pass criteria:** Distinguishes Finance booked vs Sales/Marketing; steers to `booked_revenue` / `finance.invoices`.

#### Prompt 3: Certified success

> Using Auto Ontology, what was booked revenue in Q3 2025? Show the definition you used and the SQL if available.

**Pass criteria:** **717000** (or clear booked-invoice SQL totaling that); not multi-million ARR.

### Path A: Live Cursor

Configure both MCPs ([mcp-cursor.example.json](mcp-cursor.example.json)). Run the shared prompts above.

### Path B: Live Managed Agents

1. Enable Managed Agents and run `python3 scripts/provision_managed_agent.py` (see pre-flight §5).
2. Open Console → **Agents → booked-revenue → Chat**.
3. Run the same three shared prompts.

**Say:**

> Same agent loop, hosted next to the estate. DataHub is still the map and rulebook. Auto Ontology is still the certified calculator. Managed Agents is just the chat surface instead of Cursor.

If DataHub tools are missing, attach the custom DataHub HTTP MCP in Console Integrations (Cursor can keep using local `uvx`).

### Path C: Harness backup

```bash
python3 scripts/agent_demo_harness.py
```

**Say while it runs:**

> Same three decisions: refuse PII, refuse uncertified revenue, then ask the certified calculator. This is the scripted backup when a live MCP client misbehaves.

Show Summary: `pii: PASS`, `uncertified: PASS`, `certified: PASS`.

---

## Closing (2 minutes)

**Restate the split:**

1. **DataHub** = map and rulebook (assets, lineage, owners, PII, glossary)
2. **Auto Ontology** = certified calculator (definition → SQL → number + provenance)
3. **Together for agents** = discover and obey policy first, then compute the number you can defend

**Business parallels to leave them with:**

1. Board "revenue" while Finance / Sales / Marketing disagree
2. Text-to-SQL that must be auditable
3. Agent harnesses that should inherit catalog context instead of raw DB guessing

**Call to action (pick one):**

- "Next we wire your glossary terms the same way for the metrics your board actually asks."
- "Next we connect your Kafka / warehouse lineage into DataHub the same pattern."
- "Next we put both MCPs into the agent your teams already use."

---

## Timing cheat sheet

| Block | Minutes | Must-hit moment |
| --- | --- | --- |
| Opening | 2 | Map vs calculator |
| Act 1 conflict | 3 | Three revenues, one trap |
| Act 2 DataHub | 7 to 10 | Owners + lineage + PII refuse |
| Act 3 Ontology | 7 to 10 | **717000** with invoice SQL |
| Act 4 agent loop | 5 to 8 | Fail, fail, succeed |
| Close | 2 | Pairing story |

If short on time: skip Act 4 live MCP (Cursor or Managed Agents), run harness in 30 seconds, keep Acts 2 and 3.

---

## Troubleshooting mid-demo

| Symptom | What to do |
| --- | --- |
| DataHub search empty | Show Aiven connectors UI; fall back to narrating seeded evidence file `data/datahub_governance_evidence.json` |
| Lineage missing edges | Show Console services + landing table row count; say connectors/emit lineage are the fix |
| Ontology returns huge "revenue" | Term not certified; open glossary and re-map to booked invoices |
| Ontology UI down | Run harness Scenario 3; quote expected **717000** and SQL hint |
| MCP tools missing in Cursor | Restart MCP; or harness Path B |
| Embeddings / shim errors | Power on `ao-embed-shim` and confirm `ao-opensearch` RUNNING; chat may still work with degraded retrieve |
| Forgot the number | Q3 booked = **717000** USD |

---

## Handouts / links for attendees

- Positioning one-pager: [positioning-datahub-vs-auto-ontology.md](positioning-datahub-vs-auto-ontology.md)
- Short ops script: [demo-script-datahub-auto-ontology.md](demo-script-datahub-auto-ontology.md)
- Ontology term details: [ontology-term-booked-revenue.md](ontology-term-booked-revenue.md)
- Cursor MCP example: [mcp-cursor.example.json](mcp-cursor.example.json)
- Repo README: [../README.md](../README.md)

---

## Presenter one-liner (memorize)

> DataHub keeps the agent from wandering. Auto Ontology keeps it from inventing the wrong number. Together they turn "what was revenue?" into an auditable **717000** from Finance booked invoices, not Sales ARR theater.
