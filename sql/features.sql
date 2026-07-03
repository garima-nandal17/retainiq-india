-- ============================================================================
-- RetainIQ India — SQL feature layer (DuckDB)
-- Day 3: Advanced SQL Feature Engineering
--
-- Two views on top of the normalized schema (customer / account /
-- service_subscription):
--
--   1. feature_customer      -> the DENORMALIZED per-customer feature matrix
--                               (one row per customer) for modeling.
--   2. tenure_churn_gradient -> a cohort-level view where ORDERED window
--                               functions (LAG, running frame, moving avg) are
--                               genuine, because tenure IS an ordered dimension.
--
-- Window-function honesty: this dataset is cross-sectional (one row/customer,
-- no event timeline). LAG/running aggregates are NOT forced onto customer rows
-- — there is no natural per-customer order. They are used only on the tenure
-- dimension, where order is real. On customer rows we use the window functions
-- that ARE meaningful cross-sectionally: NTILE (banding), RANK / PERCENT_RANK
-- (position within a cohort), and partition aggregates (deviation from cohort).
-- True "recency" (last-interaction date) does not exist here; tenure_months is
-- the temporal proxy, and this is stated rather than faked.
--
-- Intentionally OMITTED (documented for honesty, same discipline as above):
--   service_adoption_ratio (= services_held/9), protection_ratio
--   (= protection_count/4), streaming_ratio (= streaming_count/2). Each is a
--   PERFECT linear rescaling of an existing count (measured corr = 1.000), so it
--   carries zero additional information and would only invite collinearity in the
--   Day-7 model. A dashboard can trivially normalize these on display instead.
--   monthly_charge_per_service was kept because it is a genuine interaction of
--   two different columns (corr with parents -0.11 / -0.56), not a rescaling.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1) Per-customer feature matrix
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW feature_customer AS
WITH service_agg AS (
    -- Collapse the long provisioning table back to one row/customer.
    -- "Active" = the customer actually holds the service (exclude the three
    -- negative sentinels). Internet counts as active whether DSL or Fibre.
    SELECT
        customer_id,
        COUNT(*) FILTER (
            WHERE status NOT IN ('No', 'No phone service', 'No internet service')
        )                                                        AS services_held,
        MAX(CASE WHEN service_name = 'InternetService' THEN status END)
                                                                 AS internet_type,
        MAX(CASE WHEN service_name = 'PhoneService'  AND status = 'Yes'
                 THEN 1 ELSE 0 END)                              AS has_phone,
        COUNT(*) FILTER (
            WHERE service_name IN ('StreamingTV', 'StreamingMovies')
              AND status = 'Yes'
        )                                                        AS streaming_count,
        COUNT(*) FILTER (
            WHERE service_name IN ('OnlineSecurity', 'OnlineBackup',
                                   'DeviceProtection', 'TechSupport')
              AND status = 'Yes'
        )                                                        AS protection_count
    FROM service_subscription
    GROUP BY customer_id
),
base AS (
    SELECT
        a.customer_id,
        a.tenure_months,
        a.contract_type,
        a.payment_method,
        a.paperless_billing,
        a.monthly_charges_inr,
        a.total_charges_inr,
        a.churned,
        c.senior_citizen,
        c.has_partner,
        c.has_dependents,
        COALESCE(s.services_held, 0)    AS services_held,
        s.internet_type,
        COALESCE(s.has_phone, 0)        AS has_phone,
        COALESCE(s.streaming_count, 0)  AS streaming_count,
        COALESCE(s.protection_count, 0) AS protection_count
    FROM account a
    JOIN customer c USING (customer_id)
    LEFT JOIN service_agg s USING (customer_id)
),
windowed AS (
    SELECT
        *,
        -- NTILE: risk/value banding (genuine cross-sectionally)
        NTILE(10) OVER (ORDER BY monthly_charges_inr)                     AS arpu_decile,
        NTILE(4)  OVER (ORDER BY tenure_months)                          AS tenure_quartile,
        -- RANK / PERCENT_RANK: position within the customer's contract cohort
        RANK() OVER (PARTITION BY contract_type
                     ORDER BY monthly_charges_inr DESC)                   AS arpu_rank_in_contract,
        PERCENT_RANK() OVER (PARTITION BY contract_type
                             ORDER BY monthly_charges_inr)                AS arpu_pctile_in_contract,
        -- Partition aggregate (frame = whole partition): cohort mean broadcast
        AVG(monthly_charges_inr) OVER (PARTITION BY contract_type)        AS contract_avg_arpu
    FROM base
)
SELECT
    *,
    -- Deviation feature: how far above/below the customer sits vs its cohort
    ROUND(monthly_charges_inr - contract_avg_arpu, 2)                     AS arpu_vs_contract_avg,
    -- Interpretable buckets / risk encodings
    CASE
        WHEN tenure_months <= 12 THEN '00-12'
        WHEN tenure_months <= 24 THEN '13-24'
        WHEN tenure_months <= 48 THEN '25-48'
        ELSE '49+'
    END                                                                  AS tenure_bucket,
    CASE contract_type
        WHEN 'Month-to-month' THEN 3
        WHEN 'One year'       THEN 2
        WHEN 'Two year'       THEN 1
    END                                                                  AS contract_risk,
    CASE WHEN payment_method = 'Electronic check' THEN 1 ELSE 0 END       AS elec_check_flag,
    CASE WHEN internet_type = 'Fiber optic'      THEN 1 ELSE 0 END        AS fiber_flag,
    CASE WHEN internet_type IN ('DSL', 'Fiber optic') THEN 1 ELSE 0 END   AS has_internet,

    -- === Reusable business features (added after Day-3 review) ===
    -- All derived from point-in-time customer state; NONE use the churned label
    -- (no target leakage). See docs/runlog.md D-013..D-016.

    -- Genuine interaction (corr with parents only -0.11 / -0.56, not a rescaling):
    -- "am I paying a lot for few services?" — a value-density / over-pay signal.
    ROUND(monthly_charges_inr / services_held, 2)                         AS monthly_charge_per_service,

    -- Household stability signal (combines two booleans -> not collinear with either).
    CASE WHEN has_partner OR has_dependents THEN 1 ELSE 0 END             AS family_flag,

    -- Convenience boolean the optimizer/dashboard reference repeatedly.
    CASE WHEN contract_type = 'Month-to-month' THEN 1 ELSE 0 END          AS high_risk_contract,

    -- Canonical VALUE segment (current ARPU tiers; Day-9 LTV enriches this later).
    CASE
        WHEN monthly_charges_inr <= 40 THEN 'Low'
        WHEN monthly_charges_inr <= 80 THEN 'Mid'
        ELSE 'High'
    END                                                                  AS customer_value_segment,
    CASE WHEN monthly_charges_inr > 80 THEN 1 ELSE 0 END                  AS is_high_value_customer,

    -- Canonical a-priori RISK segment built from DRIVERS (contract, payment,
    -- tenure) — deliberately NOT from churned, so it is safe as a model input.
    CASE
        WHEN ( (contract_type = 'Month-to-month')::INT * 2
             + (payment_method = 'Electronic check')::INT
             + (tenure_months <= 12)::INT ) >= 3 THEN 'High'
        WHEN ( (contract_type = 'Month-to-month')::INT * 2
             + (payment_method = 'Electronic check')::INT
             + (tenure_months <= 12)::INT ) >= 1 THEN 'Medium'
        ELSE 'Low'
    END                                                                  AS risk_segment
FROM windowed;

-- ---------------------------------------------------------------------------
-- 2) Tenure churn gradient — ORDERED window functions used honestly.
--    LAG (period-over-period delta), a running frame (cumulative base), and a
--    ROWS-framed moving average all operate on tenure, which is truly ordered.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW tenure_churn_gradient AS
WITH by_tenure AS (
    SELECT
        tenure_months,
        COUNT(*)              AS customers,
        AVG(churned::INT)     AS churn_rate
    FROM account
    GROUP BY tenure_months
)
SELECT
    tenure_months,
    customers,
    ROUND(churn_rate, 4)                                                  AS churn_rate,
    ROUND(churn_rate - LAG(churn_rate) OVER (ORDER BY tenure_months), 4)  AS churn_rate_delta,
    SUM(customers) OVER (ORDER BY tenure_months
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)                AS cum_customers,
    ROUND(AVG(churn_rate) OVER (ORDER BY tenure_months
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 4)                    AS churn_rate_ma3
FROM by_tenure
ORDER BY tenure_months;