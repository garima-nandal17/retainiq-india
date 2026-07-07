# Data Quality Framework — RetainIQ India (Day 4)

A named 5-dimension data-quality framework run over the BharatConnect tables,
mirroring analytics-engineering practice (dbt-tests / data contracts). Every
check emits a **pass/fail plus a logged metric**, and each is tagged **hard**
(blocks the pipeline) or **soft** (informational warning) — the same
`error` vs `warn` split dbt uses. Implemented in `src/data_quality.py`; results
written to `reports/dq_report.json`. Latest run: **46/46 hard checks pass, 1 soft
check warns**, overall **PASS**.

## The five dimensions

| Dimension | What it asserts | Example checks (real) |
|---|---|---|
| **Freshness** | Data is recent enough to trust | Time since last load ≤ 30-day SLA. *Honesty:* the source is a static snapshot with no event timestamps, so this is the freshness **mechanism** (SLA vs load-time), proxied by the processed DB's mtime — documented, not faked. |
| **Completeness** | Required fields are populated | Null rate per column across all 33 feature columns. Only `total_charges_inr` carries nulls (11 / 0.156%), and those are the known tenure-0 rows. |
| **Uniqueness** | No unintended duplication | `customer_id` PK unique (0 dups); `(customer_id, service_name)` PK unique (0 dups). |
| **Consistency** | Cross-field logic holds | `tenure=0 ⟺ total_charges NULL` (0 violations); monthly charges > 0; internet-dependency rule for add-ons (0 violations); *soft:* `total ≈ tenure×monthly` within 5%. |
| **Accuracy** | Values sit in valid domains/ranges | tenure ∈ [0,72]; monthly ∈ range; `contract_type` / `payment_method` / `gender` in expected value sets (0 unexpected). |

## Hard vs soft — the one informative "warning"
The check `total ≈ tenure × monthly (5%)` holds for **80.5%** of customers, not
100%. This is **not** bad data: `MonthlyCharges` is the *current* rate, while
`TotalCharges` accumulated over a tenure during which the customer added or
dropped services and prices changed. A naive integrity rule would wrongly fail
the load; marking it **soft** captures the signal without blocking. The lesson: a
failing consistency check often reveals a wrong *assumption*, not corrupt data.

## Leakage scan
Two checks guard against target leakage:
1. **No near-perfect predictor** — max `|corr(feature, churned)|` across numeric
   features is **0.405** (`high_risk_contract`), far below the 0.95 alarm. No
   feature is a disguised copy of the label.
2. **Target excluded from X** — `customer_id` and `churned` are excluded from the
   model feature set, and the engineered segments (`risk_segment`,
   `customer_value_segment`) were built from **drivers**, never from the label.

A unit test plants a leaky feature (a column equal to `churned`) and confirms the
scan catches it (`tests/test_data_quality.py`).

## `total_charges` NULL — formal resolution (closes D-008)
The 11 tenure-0 nulls are **kept NULL at the data layer** (faithful to source —
a brand-new customer genuinely has no billed total). Imputation is a
**modeling-time** decision, not a data mutation: `src/model.py` imputes the
median inside the training pipeline only. Data stays honest; the model stays
robust.