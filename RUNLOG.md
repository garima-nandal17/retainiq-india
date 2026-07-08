# RetainIQ India — Build Runlog

An engineering diary for the RetainIQ India project. One entry per working day, appended while the work is fresh. This file is the *narrative* of how the project evolved; the BRD, code, and docs are the *artifacts* it produced. It grows from Day 1 through Day 15.

**Conventions**
- Chronological order — Day 1 first, most recent day last.
- Each entry: what I set out to do, what I decided, what I built, what's still open.
- Design decisions are logged inline with a short rationale (lightweight ADR style).

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

## Day 4 — Data Quality Framework + EDA · work completed  ◆ MILESTONE (STAR #1)

**Goal for today:** Replace ad-hoc validation with a real 5-dimension data-quality framework, scan for leakage, do honest EDA, and append the first STAR story.

### Done
- **5-dimension DQ framework** (`src/data_quality.py`): freshness, completeness, uniqueness, consistency, accuracy — **47 checks**, each with pass/fail + logged metric, tagged **hard** (blocking) or **soft** (informational). Report written to `reports/dq_report.json`. Result: **46/46 hard pass, 1 soft warn → overall PASS**.
  - Completeness: only `total_charges_inr` carries nulls (11 / 0.156%, the tenure-0 rows); all 33 columns otherwise complete.
  - Uniqueness: 0 duplicate `customer_id`; 0 duplicate `(customer_id, service_name)`.
  - Consistency: `tenure=0 ⟺ null total` (0 violations), internet-dependency rule (0 violations); soft check `total≈tenure×monthly` holds for **80.5%** — diagnosed as a correct-but-evolving-rate effect, not bad data.
  - Accuracy: all domain/range checks pass (0 unexpected categories, 0 out-of-range).
- **Leakage scan:** max `|corr(feature, churned)|` = **0.405** (`high_risk_contract`) — no near-perfect predictor; `customer_id`/`churned` excluded from X; segments built from drivers.
- **EDA notebook** (`notebooks/01_eda.ipynb`, executed): honest base churn rate **26.54%**; churn by contract/payment/internet/tenure/adoption with charts.
- **Tests** (`tests/test_data_quality.py`): 3 tests incl. a planted-leak test — green.
- **STAR #1** appended to `docs/portfolio/STAR.md`; framework documented in `docs/data_quality_framework.md`.

### Design decisions
- **D-017 — Hard/soft check severity.** Mirrors dbt `error`/`warn`; overall pass depends only on hard checks. Prevents a wrong assumption from blocking a good load.
- **D-018 — `total_charges` NULLs resolved (closes D-008).** Kept NULL at the data layer (faithful to source); median-imputed only inside the model pipeline. Data stays honest, model stays robust.
- **D-019 — Leakage scan with plant-a-leak test.** Alarm at `|corr|≥0.95`; a unit test injects a column equal to the target to prove the scan fires.
- **D-020 — Freshness implemented as a mechanism, not faked.** Static snapshot has no event timestamps, so freshness = SLA vs last-load time (DB mtime), with the limitation documented.

### Open / carried
- **OPEN-6 (Day 5):** survival + segmentation + adoption + product-metrics doc.
- **OPEN-1 (still open):** `requirements.lock` after clean install.

### Commits for today
```
feat(dq): 5-dimension data-quality framework + hard/soft severity + tests
analysis: EDA notebook + honest 26.54% base rate
docs(star): milestone 1 + data-quality framework doc
docs(runlog): day 4
```

---

## Day 5 — Survival, Segmentation & Product Analytics · work completed

**Goal for today:** Model *when* customers churn, segment them, analyse feature adoption, and define the product-metrics layer under the North Star.

### Done
- **Kaplan-Meier survival** (`src/survival.py`, figure saved): duration = tenure, event = churned. Median survival **month-to-month = 35 months**; one-year and two-year **never fall below 50% retention** in the 72-month window (median undefined — reported honestly). Overall S(12)=0.843, S(24)=0.789, S(48)=0.709. **Log-rank across contracts χ²=2352.9, p≈0.**
- **Cohorts + RFM-style segments** (`src/cohorts.py`): tenure-cohort churn 47.4% (0-12m) → 9.5% (49m+). RFM adapted to **T-E-M** (Tenure–Engagement–Monetary; Recency unavailable, proxied by tenure, stated). Priority segment **"New high-value (watch)"** = 1,449 customers, ARPU ₹85.4, churn **58.3%**. Value×loyalty: high-value *new* 62.6% vs high-value *tenured* 21.3%.
- **Adoption analysis** (`src/adoption.py`, figure saved): per-service churn ratio (with/without) — OnlineSecurity **0.47**, TechSupport **0.49**, OnlineBackup 0.74, DeviceProtection 0.78 (protective); StreamingTV 1.24, StreamingMovies 1.23 (adverse). Adoption depth vs churn is non-linear.
- **Product-metrics doc** (`docs/product_metrics.md`): North Star = Net Revenue Retained + retention KPI tree (at-risk revenue, save rate, cost-per-save, budget utilisation) + retention funnel. **No growth funnel** (out of scope).
- **Notebook** `notebooks/02_survival_product.ipynb` (executed) orchestrates all three modules.

### Design decisions
- **D-021 — Survival framing + honest undefined medians.** 1/2-year medians reported as "undefined (retention > 50% throughout window)" rather than coerced to a number.
- **D-022 — RFM adapted to T-E-M.** Classic Recency/Frequency unavailable in a snapshot; documented the proxy mapping instead of faking transactional recency.
- **D-023 — Adoption as churn-driver analysis, not growth study.** Per-service lift feeds offer design, subordinated to the thesis.

### Open / carried
- **OPEN-7 (Day 6):** hypothesis tests with effect sizes.

### Commits for today
```
feat(survival): Kaplan-Meier curves + log-rank
feat(product): cohorts + RFM-style segments + adoption analysis
docs(product): North Star + retention KPI tree
docs(runlog): day 5
```

---

## Day 6 — Hypothesis Testing · work completed

**Goal for today:** Statistically test which factors drive churn, always paired with effect sizes and a written verdict.

### Done
- **Tests** (`src/hypothesis_tests.py`): chi-square + Cramér's V for categoricals, Welch t-test + Cohen's d for numerics. Real results:
  - contract_type: χ²=1184.6, p≈6e-258, **V=0.410 (large)**
  - internet_type: χ²=732.3, **V=0.322 (large)**
  - payment_method: χ²=648.1, **V=0.303 (large)**
  - senior_citizen: χ²=159.4, **V=0.151 (moderate)**
  - tenure_months: t=−34.8, **d=−0.852 (large)** — churn mean 18.0m vs retained 37.6m
  - monthly_charges_inr: t=18.4, **d=+0.446 (small)** — churn ₹74.4 vs retained ₹61.3
- **Ranked by |effect size|:** tenure > monthly charges > contract > internet > payment > senior.
- **Notebook** `notebooks/03_hypothesis.ipynb` (executed) with the test table and ranking.

### Design decisions
- **D-024 — Effect size mandatory.** At n=7,043 significance is nearly automatic, so every test carries Cramér's V or Cohen's d, and drivers are ranked by magnitude (with the caveat that V and d aren't on the same scale).

### Open / carried
- **OPEN-8 (Day 7):** interpretable-first churn engine.

### Commits for today
```
analysis: hypothesis tests on churn drivers (effect sizes + verdicts)
docs(runlog): day 6
```

---

## Day 7 — Churn Engine (Interpretable-First) · work completed

**Goal for today:** Build the churn *probability* engine — calibrated logistic first, tree challenger — on a leakage-free split, and persist it.

### Done
- **Model** (`src/model.py`): stratified 80/20 split (train 5,634 / test 1,409, seed 42). Primary = **calibrated logistic regression** (sigmoid/Platt, cv=5); challenger = random forest.
  - Logistic (calibrated): **ROC-AUC 0.8441**, PR-AUC 0.6595, Brier 0.1367, accuracy 0.7999, precision 0.6554, recall 0.5187, F1 0.5791.
  - Random forest (challenger): ROC-AUC **0.8460**, PR-AUC 0.6705, Brier 0.1357, accuracy 0.7999, precision 0.6523, recall 0.5267, F1 0.5828 — only **0.002** ROC-AUC above logistic, so the **calibrated logistic regression remains the production model**.
  - Logistic was already well-calibrated: Brier **0.1367 → 0.1367** after calibration (no change).
- **Persisted:** `models/churn_model.pkl` (the calibrated logistic) + `reports/model_metrics.json`.
- **Model feature set (16):** `tenure_months`, `monthly_charges_inr`, `total_charges_inr`, `services_held`, `streaming_count`, `protection_count`, `monthly_charge_per_service`, `arpu_vs_contract_avg`, `senior_citizen`, `has_partner`, `has_dependents`, `paperless_billing`, `has_phone`, `contract_type`, `payment_method`, `internet_type`.
- **Tests** (`tests/test_model.py`): 5 tests — valid probabilities, AUC > 0.78 floor, logistic within 3 AUC points of the forest, leakage-free features, reproducibility — all green. Full suite **8 passed**.

### Design decisions
- **D-025 — Interpretable-first, empirically justified.** The RF ceiling is 0.8460 vs 0.8441 for logistic (Δ **0.002**) → no accuracy case for a black box; the transparent, calibrated logistic wins on stakeholder trust and stays the production model.
- **D-026 — Curated leakage-free feature set.** `customer_id`/`churned` excluded; engineered segments/flags that merely re-encode an existing categorical excluded from the model (they serve the optimizer/dashboard). Prevents double-counting. Final set is the 16 features listed above.
- **D-027 — Calibration for budget decisions.** The Day-10 optimizer needs calibrated probabilities to size rupee decisions; sigmoid calibration applied — the logistic was already near-calibrated, so Brier is unchanged at 0.1367.
- **D-028 — `models/` folder recreated (closes D-005 deferral).** Created on the day serialized artifacts first exist, exactly as planned (tracking policy later amended by D-030).

### Post-validation hardening (reproducibility fix)
Running the suite surfaced a genuine non-determinism bug: `test_reproducible` failed because consecutive `train()` calls produced **different ROC-AUC values despite a fixed seed**. **Root cause:** `load_xy()` read the feature matrix without an `ORDER BY`, and DuckDB does not guarantee row order, so `train_test_split(random_state=42)` received rows in a different order each run and cut a different split.

Fix — both in `src/model.py`:
- **Deterministic ordering** — added `ORDER BY customer_id` to the feature query, so the split is identical every run.
- **Explicit LR seed** — `LogisticRegression(max_iter=1000, random_state=SEED)`, making the model config deterministic and future-proof against solver changes.

**Effect:** two consecutive runs now return byte-identical metrics, `test_reproducible` passes, and the values above (ROC-AUC **0.8441**) are the stable, canonical output — consistent with `src/model.py`, `reports/model_metrics.json`, and the passing test suite. Before the fix the metrics were split-dependent (they varied run to run), which is exactly the fragility this removes.

- **D-029 — Deterministic training pipeline.** Reproducibility is enforced structurally (ordered read + explicit seeds), not assumed. A reproducibility claim you can't re-run is worthless.
- **D-030 — Track model + reports as portfolio artifacts (amends D-028).** `models/`, `reports/`, and executed notebooks are committed so the repo is demoable without a retrain; `.gitignore` hardened for Python/OS/IDE noise while keeping raw/processed **data** ignored. Trade-off: a committed `.pkl` is only loadable against the scikit-learn version it was trained on, so `scikit-learn` should be pinned in `requirements.txt` (see OPEN-1).

### Open / carried
- **OPEN-9 (Day 8):** evaluation + SHAP + business read + STAR #2.
- **OPEN-1 (still open):** `requirements.lock` after clean install.

### Commits for today
```
feat(model): calibrated interpretable-first churn engine + leakage-free split
test(model): probability/AUC/leakage/reproducibility suite
fix(model): deterministic ordering (ORDER BY customer_id) + explicit seeds
chore(repo): production-ready .gitignore; track models/reports as artifacts
docs(runlog): day 7 + post-validation hardening
```