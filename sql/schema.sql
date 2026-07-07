-- ============================================================================
-- RetainIQ India — BharatConnect normalized schema (DuckDB)
-- Day 2: Database Design & Data Load
--
-- Design rationale
--   The source is a single flat CSV (one row per customer). We normalize it
--   into three tables that mirror how a real telecom operator's systems split:
--     customer            -> CRM master (who the customer is)
--     account             -> billing system (commercial relationship + target)
--     service_subscription-> provisioning system (what they actually use)
--
--   The service_subscription table is intentionally LONG/narrow. It replaces
--   nine wide, repeating "service" columns with one tidy fact table, so
--   service count and feature-adoption depth (Day 5) become simple GROUP BYs
--   instead of nine CASE expressions.
--
--   Normalization vs denormalization: this schema is the normalized source of
--   truth (integrity, no repeating groups). Day 3 builds a DENORMALIZED
--   feature view on top of it for modeling. Normalize to store, denormalize to
--   analyze.
--
--   Currency: BharatConnect is an Indian operator, so monetary values are
--   denominated in rupees by declaration (columns suffixed _inr). We do NOT
--   apply an FX multiplier — that would add a spurious, distortive assumption
--   for zero analytical gain (all downstream ratios are scale-invariant).
--   See docs/data_acquisition.md (decision D-006).
-- ============================================================================

-- Idempotent: safe to re-run. Drop children before parents (FK order).
DROP TABLE IF EXISTS service_subscription;
DROP TABLE IF EXISTS account;
DROP TABLE IF EXISTS customer;

-- ---------------------------------------------------------------------------
-- customer  — CRM master. One row per customer. Stable identity/demographics.
-- ---------------------------------------------------------------------------
CREATE TABLE customer (
    customer_id     VARCHAR      NOT NULL,   -- source: customerID (e.g. 7590-VHVEG)
    gender          VARCHAR      NOT NULL,   -- 'Female' | 'Male'
    senior_citizen  BOOLEAN      NOT NULL,   -- source: SeniorCitizen 0/1 -> bool
    has_partner     BOOLEAN      NOT NULL,   -- source: Partner Yes/No
    has_dependents  BOOLEAN      NOT NULL,   -- source: Dependents Yes/No
    PRIMARY KEY (customer_id)
);

-- ---------------------------------------------------------------------------
-- account  — billing/commercial relationship + the churn target.
-- 1:1 with customer.
-- ---------------------------------------------------------------------------
CREATE TABLE account (
    customer_id         VARCHAR   NOT NULL,  -- FK -> customer
    tenure_months       INTEGER   NOT NULL,  -- source: tenure (0..72)
    contract_type       VARCHAR   NOT NULL,  -- 'Month-to-month' | 'One year' | 'Two year'
    paperless_billing   BOOLEAN   NOT NULL,  -- source: PaperlessBilling Yes/No
    payment_method      VARCHAR   NOT NULL,  -- 4 categories
    monthly_charges_inr DOUBLE    NOT NULL,  -- source: MonthlyCharges (ARPU), ₹ by declaration
    total_charges_inr   DOUBLE,              -- source: TotalCharges; NULL for 11 tenure-0 rows
    churned             BOOLEAN   NOT NULL,  -- source: Churn Yes/No  (TARGET)
    PRIMARY KEY (customer_id),
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
);

-- ---------------------------------------------------------------------------
-- service_subscription  — provisioning. LONG format: one row per
-- (customer, service). Replaces 9 wide service columns.
-- status preserves the 3-state source value, including the analytically
-- meaningful "No phone service" / "No internet service" (a dependency signal:
-- you cannot have OnlineSecurity without InternetService).
-- ---------------------------------------------------------------------------
CREATE TABLE service_subscription (
    customer_id  VARCHAR  NOT NULL,          -- FK -> customer
    service_name VARCHAR  NOT NULL,          -- e.g. 'PhoneService','InternetService','StreamingTV'
    status       VARCHAR  NOT NULL,          -- 'Yes' | 'No' | 'No phone service' | 'No internet service'
    PRIMARY KEY (customer_id, service_name),
    FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
);
CRAETE TABLE service subscription ()