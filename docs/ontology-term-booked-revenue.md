# Certify `booked_revenue` after ingest

After Auto Ontology has ingested `saas_analytics`, create (or confirm) a glossary term:

- **Term:** `booked_revenue`
- **Description:** Invoice amounts with finance status booked. Not ARR and not marketing pipeline.
- **Physical mapping:** `finance.invoices.booked_amount` filtered by `status = 'booked'`
- **Join path:** `finance.invoices.customer_id` → `finance.customers.customer_id` for region/segment breakdowns

## Demo questions

1. "What was booked revenue in Q3 2025?"
2. "What was revenue last quarter?" (should resolve to booked after certification)
3. "Booked revenue by region for July through September 2025"
4. Follow-up: "What about October?"

## Expected finance total (Q3 2025 booked only)

July–September 2025 booked invoices:

- Jul: 120000 + 45000 + 200000 = 365000
- Aug: 120000 + 12000 = 132000 (draft Umbrella excluded)
- Sep: 45000 + 175000 = 220000

**Q3 booked revenue = 717000 USD**

Sales closed-won ARR and marketing pipeline are much larger; if the agent returns millions without invoice SQL, the ontology is not grounding the answer.
