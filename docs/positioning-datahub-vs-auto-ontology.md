# DataHub vs Auto Ontology (demo talk track)

## One-line split

- **Aiven DataHub** is the map and rulebook: what data exists, lineage, ownership, glossary, who may use it.
- **NVIDIA Auto Ontology** is the certified calculator: for this business question, which definition and SQL to run, with provenance.

DataHub helps an agent not wander blindly. Auto Ontology helps it not invent a wrong number.

## This demo's conflicting revenue story

The `saas_analytics` database intentionally exposes three "revenue-like" facts:

| Source | Column / view | Meaning |
| --- | --- | --- |
| Finance | `finance.invoices.booked_amount` (status=`booked`) | Cash / invoice booked revenue (**certified**) |
| Sales | `sales.opportunities.arr_amount` (stage=`closed_won`) | Annualized ARR at close |
| Marketing | `marketing.attribution.pipeline_amount` | Attributed pipeline |

Without a semantic layer, an agent asked "What was revenue last quarter?" can pick any of the three and sound confident.

In Auto Ontology, certify a glossary term such as `booked_revenue` mapped to finance invoices with `status = 'booked'`. Then `ask_question` should use that definition and return SQL + rows.

## Where DataHub still matters (v1 narrative only)

DataHub is **not deployed** in this demo. In a fuller estate it would:

- Catalog Kafka, ClickHouse, dashboards, and dbt models beside Postgres
- Show lineage into `finance.invoices`
- Attach ownership and PII tags before an agent queries

Pairing later: DataHub MCP for discovery and governance, Auto Ontology MCP for certified answers.

## Real-world parallels

1. Board deck asks for "revenue" while Finance, Sales, and Marketing disagree.
2. Text-to-SQL must be auditable (answer + SQL + rows).
3. Agent harnesses (Cursor / Claude) should inherit RBAC without holding DB credentials (Auto Ontology MCP).
