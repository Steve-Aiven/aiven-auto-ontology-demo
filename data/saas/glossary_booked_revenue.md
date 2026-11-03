# Post-ingest certification checklist

After Auto Ontology is running and has ingested `saas_analytics`:

1. Open **Catalog / Glossary** in the UI.
2. Create term **`booked_revenue`**.
3. Description: `Invoice amounts with finance.status=booked. Not ARR and not marketing pipeline.`
4. Map to `finance.invoices.booked_amount` with filter `status = 'booked'`.
5. Ask: `What was booked revenue in Q3 2025?` Expect **717000**.

This file is the durable checklist for the seed-saas todo; certification is a UI step once the app is up.
