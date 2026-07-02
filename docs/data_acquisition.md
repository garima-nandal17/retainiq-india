# Data Acquisition & Provenance — RetainIQ India

*Authored on Day 2, the day the dataset was actually downloaded. Every field
below is verifiable against the file on disk.*

## Source
- **Dataset:** IBM Telco Customer Churn (a single, well-understood telecom
  dataset). Per the thesis, **no second dataset** is used.
- **Canonical distribution:** Kaggle — `blastchar/telco-customer-churn`
  (`WA_Fn-UseC_-Telco-Customer-Churn.csv`).
- **Copy used in this build:** IBM public GitHub repository
  `IBM/telco-customer-churn-on-icp4d` (`data/Telco-Customer-Churn.csv`) — the
  identical canonical file, fetched via `raw.githubusercontent.com`.
- **License / use:** IBM sample dataset, publicly available for educational and
  analytical use.

## Provenance (verified)
| Field | Value |
|---|---|
| Local path | `data/raw/telco_churn_raw.csv` (git-ignored — never committed) |
| Download date | Day 2 |
| Rows (excl. header) | **7,043** |
| Columns | **21** |
| SHA-256 | `16320c9c1ec72448db59aa0a26a0b95401046bef5d02fd3aeb906448e3055e91` |
| Base churn rate | **26.54%** (sanity-checks against the known IBM figure) |

> If you download your own copy from Kaggle, the SHA-256 may differ by line
> endings/encoding. Verify instead against the invariants: **7,043 rows,
> 21 columns, 26.54% churn** — these must match.

## Known data quirks (handled at load)
- **`TotalCharges`** contains a blank space for **11 tenure-0 customers**
  (brand-new, no billed total yet), forcing the column to parse as text. Loaded
  as **NULL**, not imputed or dropped. Deeper handling is deferred to the Day-4
  data-quality framework.
- **Service columns** carry a 3-state value including `No phone service` /
  `No internet service` (a dependency signal), preserved rather than collapsed.

## BharatConnect relabeling map
| Source | BharatConnect | Table |
|---|---|---|
| `customerID` | `customer_id` | customer/account/service |
| `SeniorCitizen`,`Partner`,`Dependents`,`gender` | demographics (bool where 0/1 or Yes/No) | customer |
| `tenure` | `tenure_months` | account |
| `Contract` | `contract_type` | account |
| `PaperlessBilling`,`PaymentMethod` | billing attributes | account |
| `MonthlyCharges` | `monthly_charges_inr` (ARPU) | account |
| `TotalCharges` | `total_charges_inr` (nullable) | account |
| `Churn` | `churned` (TARGET) | account |
| 9 service columns | long table `(service_name, status)` | service_subscription |

## Assumptions & decisions
- **D-006 — Currency by declaration, no FX.** BharatConnect is Indian, so
  monetary values are denominated in ₹ by declaration (columns suffixed
  `_inr`). We deliberately do **not** multiply by an assumed USD→INR rate: it
  would add a spurious, distortive assumption while every downstream ratio
  (profit curve, cost-per-save, efficiency) is scale-invariant. This supersedes
  the Day-1 planning draft, which had proposed an FX multiplier.
- **Offer economics deferred.** Offer cost, acceptance rate, and margin are
  **cockpit inputs**, not data attributes and not hard-coded — introduced when
  the optimizer needs them (Day 9–10), stress-tested on Day 11. Every resulting
  rupee figure is labeled `(simulation-based estimate)`.