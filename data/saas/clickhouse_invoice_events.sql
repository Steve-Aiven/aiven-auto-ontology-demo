-- Apply on ao-clickhouse after clickhouse_kafka integration exposes the Kafka engine table.
-- Table/database names may vary; adjust service_* database to match Console.

CREATE TABLE IF NOT EXISTS default.invoice_events
(
    event_id String,
    invoice_id Int32,
    customer_id Int32,
    booked_amount Float64,
    event_ts String,
    source_topic String
)
ENGINE = MergeTree
ORDER BY (event_id);

-- Example MV once the Kafka engine table exists (name from integration):
-- CREATE MATERIALIZED VIEW IF NOT EXISTS default.invoice_events_mv
-- TO default.invoice_events AS
-- SELECT event_id, invoice_id, customer_id, booked_amount, event_ts, source_topic
-- FROM service_ao_datahub_kafka.invoice_booked_events_kafka;
