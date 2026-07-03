# SQL Performance Notes — RetainIQ India (Day 3)

Engine: **DuckDB 1.5.4** (columnar, vectorized, single-node). All timings below
are measured on this repo's database (7,043 customers · 63,387 service rows),
median of repeated runs. Absolute times are small at this scale — the point is
**plan reading and knowing what scales**, not shaving microseconds off a 7k-row
query.

---

## 1. Reading the `feature_customer` plan (`EXPLAIN ANALYZE`)

Total wall time: **~0.042 s**. Bottom-up, the physical plan is:

```
TABLE_SCAN service_subscription (63,387 rows, sequential)
  └─ HASH_GROUP_BY  ...................... service_agg CTE (per-customer rollup)
       └─ HASH_JOIN INNER (account ⋈ customer on customer_id)
            └─ HASH_JOIN RIGHT (⋈ service_agg)
                 └─ WINDOW  NTILE(10) OVER (ORDER BY monthly_charges_inr)
                 └─ WINDOW  NTILE(4)  OVER (ORDER BY tenure_months)
                 └─ WINDOW  RANK() + AVG() OVER (PARTITION BY contract_type ...)
                 └─ WINDOW  PERCENT_RANK() OVER (PARTITION BY contract_type ...)
                      └─ PROJECTION (CASE buckets, flags, deviation)
```

**What the plan tells us**
- Every base table is read by a **sequential scan** — expected and optimal for a
  columnar store doing a full-population feature build. No index would be used
  here (confirmed in §2).
- The `account` scan shows an automatic **min-max (zonemap) dynamic filter**
  (`customer_id >= '0002-ORFBO' AND <= '9995-HOTOH'`). DuckDB prunes row groups
  by min/max **without any index** — a key reason secondary indexes rarely help
  analytical scans.
- Joins are **hash joins** (set-based), not nested loops — good.
- The four `WINDOW` operators are the feature-engineering core; they are cheap
  here because each partition is small.

---

## 2. Indexing decision — measured, not assumed

**Question tested:** does a secondary index speed up a representative
range-aggregate (`... WHERE monthly_charges_inr > 80`)?

| Query | Median time |
|---|---|
| PK point lookup (`customer_id = ...`) — PK auto-indexed | 0.447 ms |
| Range aggregate — **no** secondary index | **0.549 ms** |
| Range aggregate — **with** index on `monthly_charges_inr` | **1.163 ms** |
| Planner actually used the index? | **No** (sequential scan + zonemap) |

**Decision: do not add secondary indexes for this workload.** On a columnar,
single-node analytical engine, full-scan aggregations are served by vectorized
sequential scans plus automatic zonemaps. The explicit index was **not chosen by
the planner and made the query slower** (build + maintenance overhead, zero read
benefit).

**When an index *does* help (documented, not just dismissed):**
- **Highly selective point lookups / joins on high-cardinality keys.** DuckDB
  already builds an **ART index** for the `PRIMARY KEY`, which is why the
  `customer_id` point lookup is fast and why FK checks at load are cheap.
- In a **row-store OLTP** engine (Postgres/MySQL), a B-tree on a selective
  filter column would help far more than it does here — the right answer is
  **engine-dependent**, which is the real interview point.

### Why DuckDB ignored the index (a level deeper)
The optimizer is cost-based: it compares the estimated cost of an index scan
(random-access probes into the ART index, then row fetches) against a plain
sequential scan. For `monthly_charges_inr > 80` roughly a third of rows match —
a **low-selectivity** filter — so an index would touch most of the table anyway,
via slow random access, while the columnar sequential scan reads the single
`monthly_charges_inr` column contiguously and skips whole row groups using its
**min-max zonemap**. The planner correctly prices the sequential scan cheaper and
discards the index. Indexes win only when a filter is **highly selective** (returns
a small fraction of rows), which this one is not.

### Why columnar ≠ row-oriented OLTP
A **row-store** (Postgres/MySQL) stores each record's fields together on a page,
optimised for "fetch/modify one whole row" (OLTP). To answer an aggregate it must
read every row — including columns it doesn't need — so a B-tree index that
narrows *which rows* are read pays off. A **columnar** store (DuckDB) stores each
column separately and compressed, so an aggregate reads only the needed columns,
vectorised in batches, with per-block min-max metadata for free pruning. That
design already does what an index would do for analytics, which is why secondary
indexes rarely help columnar scans but remain essential for OLTP point work.

---

## 3. Before/after query optimization — set-based beats row-by-row

**Task:** compute `services_held` per customer.

- **Before (naive):** nine correlated scalar subqueries against
  `service_subscription`, one per service, summed per customer row.
- **After (set-based):** a single `GROUP BY` with a `FILTER` aggregate, joined
  back once.

| Version | Median time | Relative |
|---|---|---|
| Before — 9 correlated subqueries | 56.25 ms | 1.0× |
| After — 1 `GROUP BY` + join | **7.67 ms** | **7.3× faster** |

**Why:** the naive version expresses the work as repeated per-row lookups
(logically 9 × 7,043 probes). Even with DuckDB's subquery decorrelation, that is
materially heavier than reading the service table **once** and rolling it up with
a single hash aggregate. This is the set-based-thinking lesson: describe *what*
you want as one aggregation, not *how* to fetch it row by row. The gap widens
with data size — at warehouse scale this is the difference between seconds and
minutes.

**Why the rewrite was ~7× faster (a level deeper):** the naive version re-reads
and re-filters `service_subscription` conceptually once per service per customer,
so total work scales with `customers × services`. The set-based version reads the
service table **once**, builds a single hash table keyed by `customer_id`, and
increments counters in one pass — work scales with `rows read`, not
`rows × probes`. Same answer, far fewer passes over the data. This is why
"describe the result set" (declarative, set-based) beats "loop and look up"
(imperative, row-based) on any analytical engine.

---

## Takeaways 
1. **Read the plan before tuning.** The `feature_customer` plan is already
   optimal (sequential scans + hash joins + windows); there is nothing to index.
2. **Indexes are not free and not universal.** Measured here: the index was
   unused and slower. Know the storage model before adding one.
3. **Set-based > row-based.** The one real optimization was a rewrite (7.3×), not
   an index — the biggest SQL wins are usually structural, not physical.
   # RetainIQ India — Build Runlog

An engineering diary for the RetainIQ India project. One entry per working day, appended while the work is fresh. This file is the *narrative* of how the project evolved; the BRD, code, and docs are the *artifacts* it produced. It grows from Day 1 through Day 15.

**Conventions**
- Newest entry at the top.
- Each entry: what I set out to do, what I decided, what I built, what's still open.
- Design decisions are logged inline with a short rationale (lightweight ADR style).

---

## Day 3 — Advanced SQL Feature Engineering + Performance

**Goal for today:** Build the feature layer in SQL on top of the normalized schema, then prove I can reason about performance (indexing, execution plans, a rewrite).

### Done
- **Feature layer** (`sql/features.sql`): a denormalized per-customer view `feature_customer` (7,043 rows × 27 cols) + a cohort view `tenure_churn_gradient`.
- **Window functions used genuinely:** `NTILE` (ARPU decile, tenure quartile), `RANK` / `PERCENT_RANK` (position within contract cohort), partition `AVG` (deviation from cohort ARPU). `LAG`, a running `SUM` frame, and a `ROWS`-framed moving average are used **only** on the ordered tenure dimension (the gradient view), not forced onto cross-sectional customer rows.
- **Build driver** (`src/build_features.py`): creates the views, validates 1-row-per-customer, exports `data/processed/feature_customer.parquet` for the modeling days.
- **Performance notes** (`sql/performance_notes.md`) with **measured** results:
  - `EXPLAIN ANALYZE` of the feature view read (~0.042 s): all sequential scans + hash joins + 4 window ops; automatic zonemap pushdown visible.
  - Indexing experiment: a secondary index on `monthly_charges_inr` was **not used by the planner and made a range-aggregate slower** (0.55 → 1.16 ms). Decision: no secondary indexes for this columnar full-scan workload; documented where an index *would* help (selective point lookups / row-store engines).
  - Rewrite: 9 correlated subqueries (56.3 ms) → 1 `GROUP BY` + join (7.7 ms) = **7.3× faster**.

### Design decisions (rationale logged)
- **D-009 — Window functions applied only where order is real.** Cross-sectional data has no per-customer sequence, so `LAG`/running aggregates live on the tenure dimension, not customer rows. Same discipline as the roadmap's recursive-CTE rule. Prevents "SQL theatre".
- **D-010 — No true recency feature; tenure is the temporal proxy.** The dataset has no last-interaction timestamp. Stated honestly rather than fabricating a recency field.
- **D-011 — "Active service" definition for `services_held`.** Counts services the customer actually holds (excludes the three negative sentinels; internet counts whether DSL or Fibre), superseding the Day-2 preview's `status='Yes'` shortcut which undercounted internet.
- **D-012 — No secondary indexes.** Measured, not assumed (see performance notes).

### Open / carried to next day
- **OPEN-5 (Day 4):** 5-dimension data-quality framework + leakage scan + EDA + STAR #1. The `total_charges_inr` NULLs (D-008) get formally handled here.
- **OPEN-1 (still open):** freeze `requirements.lock` after clean install.

### Post-review hardening (pre-lock)
Targeted improvements before locking Day 3 — architecture, CTE structure, and docs left unchanged.

- **Feature layer expanded with 6 reusable business features** (all point-in-time, none use `churned` → no leakage): `monthly_charge_per_service`, `family_flag`, `high_risk_contract`, `customer_value_segment`, `is_high_value_customer`, `risk_segment`. Now 33 columns. Canonical segments (`tenure_bucket`, `customer_value_segment`, `risk_segment`) are engineered once for downstream reuse.
- **`build_features.py` hardened:** `logging` throughout; dataset-size-agnostic validation (non-empty, one-row-per-customer, no null `customer_id`/`churned`, no dup keys) — row count is logged, never asserted; typed error handling via `FeatureBuildError` with informative messages; export round-trip check.
- **`performance_notes.md` deepened** (structure unchanged): why the planner ignored the index (cost-based, low selectivity), columnar vs row-store internals, why the GROUP BY rewrite scales with rows-read not rows×probes.

**Decisions**
- **D-013 — Added `monthly_charge_per_service`.** Genuine interaction of charges×services (corr with parents −0.11 / −0.56), not a rescaling. Value-density signal.
- **D-014 — Added canonical segments `customer_value_segment` + `risk_segment`.** `risk_segment` is built from drivers (contract/payment/tenure), never the label; validated directionally (churn 5.2%→49.0% across Low→High) — signal, not leakage. `customer_value_segment` is ARPU-tier now; Day-9 LTV enriches it.
- **D-015 — Added convenience flags** `family_flag`, `is_high_value_customer`, `high_risk_contract` — justified by downstream reuse (optimizer/dashboard reference them repeatedly).
- **D-016 — Rejected `service_adoption_ratio`, `protection_ratio`, `streaming_ratio`.** Each is a perfect linear rescaling of an existing count (measured corr = 1.000): zero information gain, invites collinearity. Documented in `features.sql` header (honesty principle preserved). Dashboards can normalize on display.

### Commits for today
```
feat(features): SQL feature layer w/ advanced window fns
perf(sql): indexing decision + EXPLAIN walkthrough + rewrite (7.3x)
feat(features): reusable business features + segments (no-leakage)
refactor(build): logging, robust size-agnostic validation, error handling
docs(perf): deeper columnar/index/rewrite explanations
docs(runlog): day 3 + post-review hardening
```

---

## Day 2 — Database Design & Data Load

**Goal for today:** Design a normalized schema and load the raw BharatConnect data into SQL. Also: the dataset is now real, so promote and complete the deferred `data_acquisition.md`.

### Done
- **Dataset acquired** into `data/raw/telco_churn_raw.csv` (git-ignored). Verified provenance: 7,043 rows, 21 columns, SHA-256 recorded, base churn rate **26.54%** (matches the known IBM figure). See `docs/data_acquisition.md`.
- **Normalized schema designed** (`sql/schema.sql`): three tables mirroring real telecom systems — `customer` (CRM), `account` (billing + churn target), `service_subscription` (provisioning, long format).
- **Load script** (`src/load_data.py`): extract → transform (relabel + typing) → load into DuckDB (`data/processed/retainiq.duckdb`). Idempotent; self-verifies row counts and FK integrity. Ran clean: 7,043 / 7,043 / 63,387 rows, 11 NULL `total_charges` (tenure-0), 0 FK orphans.
- **Data dictionary** authored (`docs/data_dictionary.md`): every column, type, source mapping, and transform.
- **`data_acquisition.md` promoted** from the Day-1 planning draft and filled with real, verifiable provenance (OPEN-3 from Day 1 closed).

### Design decisions (rationale logged)
- **D-005 — `models/` folder deferred.** Removed the speculative `models/` scaffold. Folders are created on the day an artifact first needs one (e.g. serialized `.pkl` on the modeling days), not scaffolded empty. Consistent with the "structure evolves, not backfilled" principle (D-003).
- **D-006 — Currency by declaration, no FX multiplier.** Monetary values are denominated in ₹ by declaration rather than converted via an assumed USD→INR rate. An FX multiply adds a spurious, distortive assumption for zero analytical gain (downstream ratios are scale-invariant). Supersedes the Day-1 draft's FX idea.
- **D-007 — Long `service_subscription` table.** The 9 wide service columns collapse into one tidy `(customer_id, service_name, status)` fact, removing the repeating column group and making service-count / adoption-depth simple aggregations. The 3-state `status` (incl. "No internet service") is preserved as a dependency signal. Early payoff confirmed: churn falls from 43.8% (0 services) to 5.3% (8 services).
- **D-008 — `total_charges` NULLs kept honest.** The 11 tenure-0 blanks load as NULL, not imputed/dropped; handling is the Day-4 DQ framework's decision, not the loader's.

### Open / carried to next day
- **OPEN-4 (Day 3):** Build the SQL feature layer on top of this schema (denormalized feature view; advanced window functions; indexing + EXPLAIN walkthrough).
- **OPEN-1 (still open):** freeze `requirements.lock` after clean install.

### Commits for today
```
feat(db): normalized schema (customer / account / service_subscription)
feat(etl): load script with typing + relabeling into DuckDB
docs: data dictionary + real data acquisition/provenance
docs(runlog): day 2
```

---

## Day 1 — Problem Framing, BRD & Repo Scaffold

**Goal for today:** Establish the business problem and decision frame *before* touching data, and scaffold a clean repository. Deliberately no modeling, no data download.

### Done
- **Project objective finalized.** Positioned as a *Customer Decision Intelligence Platform*, not a churn-prediction project. The product is a budget-constrained contact decision, not a probability.
- **Business problem finalized.** BharatConnect spends a fixed monthly retention budget by intuition; the question is reframed from *"who churns?"* to *"given a fixed budget, whom do we contact, with which offer, to maximize net revenue retained?"*
- **North Star metric fixed:** Net Revenue Retained `(simulation-based estimate)` — explicitly *not* model accuracy.
- **BRD authored** (`docs/BRD.md` v1.1): problem, stakeholders (primary: Priya Menon, Head of Retention), success metric, scope, constraints, assumptions, risks, decision-frame chain, glossary.
- **Repository scaffolded.** Folder tree created with `.gitkeep` placeholders: `src/`, `sql/`, `data/{raw,processed}/`, `tests/`, `notebooks/`, `app/components/`, `docs/portfolio/`, `.github/workflows/`, `models/`.
- **`.gitignore`** in place — raw and processed data are never committed; models excluded; secrets excluded.
- **`requirements.txt`** prepared with the intended stack (see decision D-002).

### Design decisions (rationale logged)
- **D-001 — Project naming.** GitHub repo `retainiq-india`; local folder `RetainIQ_India`. Tagline: *Customer Decision Intelligence Platform for Budget-Constrained Retention Optimization*. Reason: consistent naming across docs/commands prevents drift; the tagline forces the "platform, not predictor" framing everywhere.
- **D-002 — Python 3.13 locked.** Verified every planned dependency (pandas, numpy, duckdb, scikit-learn, lifelines, shap, scipy, statsmodels, streamlit, matplotlib, seaborn, jupyter, pytest) supports Python 3.13 on current releases. Chose 3.13 to match the existing dev machine and the prior MacroPulse project — no reason to maintain a second interpreter. `requirements.txt` now uses 3.13-safe version *floors*; exact versions to be frozen into `requirements.lock` after first clean install (see OPEN-1).
- **D-003 — Documentation evolves, not backfilled.** The polished production README is reserved as the Day-15 target and staged at `docs/planning/README_final_target.md` (git-ignored). The live `README.md` is a minimal Day-1 stub. Reason: a repo whose first commit is the final README reads as a portfolio prop, not a real build.
- **D-004 — `data_acquisition.md` deferred to data-download day (Day 2).** It documents a source, a relabeling, and assumptions for data not yet downloaded — documentation ahead of reality, the exact anti-pattern we're avoiding. The *intent* (use the IBM Telco Customer Churn dataset, relabel to BharatConnect, rupee-denominate charges) is captured here in the runlog and as an assumption in the BRD. The full provenance doc — with actual download date, row count, and file hash — will be written when the file is really on disk. Draft staged at `docs/planning/data_acquisition_draft.md`.

### Open / carried to next day
- **OPEN-1:** Create the Python 3.13 venv, `pip install -r requirements.txt`, then `pip freeze > requirements.lock`; commit both. (Owner: me, before Day 2 coding.)
- **OPEN-2:** Create the GitHub repo `retainiq-india` and push the Day-1 commits below.
- **OPEN-3 (Day 2):** Download IBM Telco dataset into `data/raw/`, record its provenance, and *then* author the real `docs/data_acquisition.md` + `docs/data_dictionary.md`.

### Commits for today
```
init: repo scaffold + .gitignore
docs: BRD with net-revenue-retained success metric
docs: add build runlog (day 1)
```

---

<!-- Day 2 entry goes here, above this line stays at bottom. Template:

## Day N — <title>
**Goal for today:** ...
### Done
- ...
### Design decisions
- D-00X — ...
### Open / carried to next day
- ...
### Commits for today
```
...
```
-->