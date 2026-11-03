-- Apply against an existing empty database named saas_analytics
-- (created by scripts/seed_saas.sh). No CREATE DATABASE / \connect.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS finance;
CREATE SCHEMA IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS marketing;

CREATE TABLE IF NOT EXISTS finance.customers (
    customer_id   SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    segment       TEXT NOT NULL CHECK (segment IN ('enterprise', 'midmarket', 'smb')),
    region        TEXT NOT NULL,
    created_at    DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS finance.invoices (
    invoice_id    SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES finance.customers (customer_id),
    invoice_date  DATE NOT NULL,
    booked_amount NUMERIC(14, 2) NOT NULL,
    currency      TEXT NOT NULL DEFAULT 'USD',
    status        TEXT NOT NULL CHECK (status IN ('booked', 'void', 'draft'))
);

CREATE TABLE IF NOT EXISTS sales.opportunities (
    opportunity_id SERIAL PRIMARY KEY,
    customer_id    INT NOT NULL REFERENCES finance.customers (customer_id),
    close_date     DATE NOT NULL,
    arr_amount     NUMERIC(14, 2) NOT NULL,
    stage          TEXT NOT NULL CHECK (stage IN ('closed_won', 'closed_lost', 'pipeline'))
);

CREATE TABLE IF NOT EXISTS marketing.attribution (
    attribution_id SERIAL PRIMARY KEY,
    customer_id    INT NOT NULL REFERENCES finance.customers (customer_id),
    attributed_on  DATE NOT NULL,
    pipeline_amount NUMERIC(14, 2) NOT NULL,
    channel        TEXT NOT NULL
);

TRUNCATE marketing.attribution, sales.opportunities, finance.invoices, finance.customers
    RESTART IDENTITY CASCADE;

INSERT INTO finance.customers (name, segment, region, created_at) VALUES
    ('Acme Corp', 'enterprise', 'NA', '2024-01-15'),
    ('Globex', 'midmarket', 'EMEA', '2024-03-02'),
    ('Initech', 'smb', 'NA', '2024-06-20'),
    ('Umbrella', 'enterprise', 'APAC', '2023-11-08'),
    ('Stark Industries', 'enterprise', 'NA', '2024-02-01');

INSERT INTO finance.invoices (customer_id, invoice_date, booked_amount, status) VALUES
    (1, '2025-07-15', 120000.00, 'booked'),
    (1, '2025-08-15', 120000.00, 'booked'),
    (2, '2025-07-01', 45000.00, 'booked'),
    (2, '2025-09-01', 45000.00, 'booked'),
    (3, '2025-08-10', 12000.00, 'booked'),
    (4, '2025-07-20', 200000.00, 'booked'),
    (4, '2025-08-20', 200000.00, 'draft'),
    (5, '2025-09-05', 175000.00, 'booked'),
    (1, '2025-10-15', 120000.00, 'booked'),
    (5, '2025-10-05', 175000.00, 'void');

INSERT INTO sales.opportunities (customer_id, close_date, arr_amount, stage) VALUES
    (1, '2025-07-01', 1440000.00, 'closed_won'),
    (2, '2025-06-15', 540000.00, 'closed_won'),
    (3, '2025-08-01', 144000.00, 'closed_won'),
    (4, '2025-07-10', 2400000.00, 'closed_won'),
    (5, '2025-09-01', 2100000.00, 'closed_won'),
    (1, '2025-10-01', 500000.00, 'pipeline'),
    (2, '2025-09-20', 200000.00, 'closed_lost');

INSERT INTO marketing.attribution (customer_id, attributed_on, pipeline_amount, channel) VALUES
    (1, '2025-07-05', 3000000.00, 'webinar'),
    (2, '2025-07-12', 900000.00, 'paid_search'),
    (3, '2025-08-03', 250000.00, 'partner'),
    (4, '2025-07-18', 5000000.00, 'event'),
    (5, '2025-09-02', 4200000.00, 'outbound');

CREATE OR REPLACE VIEW finance.v_booked_revenue AS
SELECT
    date_trunc('month', invoice_date)::date AS month,
    region,
    segment,
    SUM(booked_amount) AS booked_revenue
FROM finance.invoices i
JOIN finance.customers c ON c.customer_id = i.customer_id
WHERE i.status = 'booked'
GROUP BY 1, 2, 3;

CREATE OR REPLACE VIEW sales.v_arr_revenue AS
SELECT
    date_trunc('month', close_date)::date AS month,
    SUM(arr_amount) AS arr_revenue
FROM sales.opportunities
WHERE stage = 'closed_won'
GROUP BY 1;

CREATE OR REPLACE VIEW marketing.v_pipeline_revenue AS
SELECT
    date_trunc('month', attributed_on)::date AS month,
    SUM(pipeline_amount) AS pipeline_revenue
FROM marketing.attribution
GROUP BY 1;

COMMENT ON COLUMN finance.invoices.booked_amount IS
    'Certified finance definition: invoice amount with status=booked. Use for booked_revenue.';
COMMENT ON COLUMN sales.opportunities.arr_amount IS
    'Sales ARR at close; NOT the same as booked invoice revenue.';
COMMENT ON COLUMN marketing.attribution.pipeline_amount IS
    'Attributed pipeline; marketing metric, not recognized revenue.';
