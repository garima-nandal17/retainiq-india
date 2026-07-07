# Product Metrics — RetainIQ India (Day 5)

The product-analytics layer, subordinated to the thesis. There is **one North
Star** and a **retention** KPI tree beneath it. There is deliberately **no growth
/ acquisition funnel** — this system optimises *retained* revenue, and a signup
funnel answers a different question (see README "Out of Scope").

## North Star — Net Revenue Retained
> **Net Revenue Retained** = (expected revenue saved from retained customers)
> − (cost of offers deployed), subject to total offer cost ≤ budget.
> Always reported as a `(simulation-based estimate)`.

Chosen because it is the only metric that is simultaneously (a) what Finance
pays for, (b) directly optimised by the Day-10 budget optimizer, and (c) honest
about the budget constraint. Accuracy/AUC are diagnostics, not the North Star.

## Retention KPI tree
```
Net Revenue Retained (North Star)
├── At-risk revenue identified      = Σ ARPU × churn-probability of flagged customers
├── Save rate                       = retained ÷ targeted at-risk customers
├── Cost per save (₹)               = budget spent ÷ customers retained
├── Budget utilisation              = spend ÷ budget ceiling (near, not over, 100%)
└── Efficiency vs contact-everyone  = NRR(optimized) ÷ NRR(spray)   [Day 10 headline]
```

## The retention funnel (not a growth funnel)
```
At-risk identified → Contacted (under budget) → Offer accepted → Retained
```
Each stage has a KPI: identification quality (model AUC 0.833), targeting
efficiency (optimizer, Day 10), acceptance rate (assumed, stress-tested Day 11),
and realised retention (A/B design, Day 12).

## What the data says (evidence backing the metrics — all computed, real)

**Retention timing (Kaplan-Meier, `src/survival.py`).** Contract type dominates
*when* customers leave. Median survival: **month-to-month = 35 months**; one-year
and two-year **never fall below 50% retention** in the 72-month window (median
undefined). Log-rank across contracts χ²=2352.9, p≈0. → intervention urgency is
highest for month-to-month, early-tenure customers.

**Adoption depth (`src/adoption.py`).** Protection add-ons are genuine retention
levers: churn-with vs churn-without ratios — OnlineSecurity **0.47**, TechSupport
**0.49**, OnlineBackup 0.74, DeviceProtection 0.78. Streaming slightly *raises*
churn (StreamingTV 1.24). → offer design should favour protection bundles, not
streaming.

**Segments (`src/cohorts.py`).** The priority segment is **"New high-value
(watch)"**: 1,449 customers, avg ARPU ₹85, churn **58.3%** — high value, not yet
sticky. The value×loyalty matrix shows high-value *new* customers churn 62.6% vs
high-value *tenured* 21.3%. → the optimizer should weight new high-ARPU customers
heavily.

**Drivers (`src/hypothesis_tests.py`).** Ranked by effect size: tenure
(d=−0.85), monthly charges (d=+0.45), contract type (V=0.41), internet type
(V=0.32), payment method (V=0.30), senior citizen (V=0.15). → tenure and contract
are the load-bearing features; senior-citizen status is real but minor.