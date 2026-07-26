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

---

## Day 8 — Evaluation, SHAP & Business Read · work completed  ◆ MILESTONE (STAR #2)

**Goal for today:** Evaluate the churn engine beyond accuracy, explain *why* it flags a customer, translate that for Priya, and append the second STAR story.

### Done
- **Evaluation beyond accuracy** (`src/evaluate.py`, reuses the deterministic Day-7 model → figures + `reports/evaluation.json`):
  - Headline (reconciles with `model_metrics.json`): ROC-AUC **0.8441**, PR-AUC **0.6595**, Brier **0.1367**.
  - Reliability curve: max calibration gap across deciles **0.055** — probabilities are trustworthy as rupee weights.
  - Confusion @0.5: TN=933, FP=102, FN=180, TP=194 (recall only 51.9% at the naïve cut).
  - Threshold sweep: **F1-max at 0.30** (P=0.530, R=0.757, F1=0.623) — a retention campaign should run *below* 0.5.
  - **Decile lift:** the **top 3 risk deciles (30% of customers) capture 65% of all churners** (decile-1 lift ×2.86).
- **Explainability** (`src/explain.py` → `reports/shap_drivers.json` + SHAP beeswarm/bar): odds ratios and SHAP agree. Strongest drivers — **tenure** (OR 0.25, protective), services_held (OR 2.40), two-year contract (OR 0.43), no-internet (OR 0.44), phone-only (OR 0.44), protection add-ons (OR 0.51, protective), total_charges (OR 1.92), fiber (OR 1.88), month-to-month (OR 1.72). SHAP top by mean|value|: tenure, services_held, protection_count, total_charges, fiber, two-year.
- **Business read** (`docs/model_business_read.md`): plain-English drivers + targeting rule for Priya, with all impact figures labelled `(simulation-based)`.
- **Notebook** `notebooks/04_explainability.ipynb` (executed) orchestrates evaluation + explanation.
- **Tests** (`tests/test_explainability.py`): 5 tests (headline reconciliation, calibration bound, top-3 capture, tenure-is-top-driver, protection-lowers-churn) — green. Full suite now **13 passed**.
- **STAR #2** appended to `docs/portfolio/STAR.md`.

### Design decisions
- **D-031 — Evaluate on ranking + calibration + business lift, not accuracy.** On a 26.5%-churn base, accuracy rewards predicting "no churn"; the decile-lift gains table is the decision-relevant view. The operating threshold is *deferred to the Day 9-10 profit curve* — this module only exposes the precision/recall trade-off.
- **D-032 — Explain the base logistic (calibration is monotonic).** Sigmoid calibration preserves score ordering, so SHAP + odds ratios on the underlying logistic give valid driver direction and ranking for the calibrated production model. SHAP and coefficients agree, which is the cross-check.
- **D-033 — Honest collinearity caveat.** Coefficients are *conditional* effects; correlated inputs (e.g. `total_charges` with tenure) are not read in isolation. The narrative is anchored on the drivers all three methods agree on — tenure, contract type, protection adoption — corroborated by the Day-6 marginal tests.
- **D-034 — STAR #2 appended → modeling milestone locked.** Evaluation and explanation ship as reproducible artifacts, not slideware.

### Open / carried
- **OPEN-10 (Day 9):** LTV + rupee-denominated profit curve.
- **OPEN-1 (still open):** `requirements.lock` after clean install.

### Commits for today
```
feat(eval): evaluation beyond accuracy (curves, calibration, decile lift)
feat(explain): SHAP + odds-ratio drivers + business read
docs(star): milestone 2 + model business read
test(explain): evaluation/driver reconciliation tests
docs(runlog): day 8
```

---

## Day 9 — LTV & Rupee-Denominated Profit Curve · work completed

**Goal for today:** Attach money to every customer, then build the rupee profit curve that exposes the cost-sensitive threshold.

### Done
- **Economics module** (`src/economics.py`): a single source of truth for every rupee assumption (gross margin 0.60, monthly discount 0.008, 24-month horizon, offer cost, acceptance rate, budget). Nothing downstream hardcodes a constant. Ships with an `ASSUMPTION_NOTE` that travels with every number.
- **LTV** (`src/ltv.py` → `data/processed/customer_value.parquet`): survival-weighted, not naive. `LTV_i = Σ ARPU_i × margin × S_c(t) / (1+r)^t` using the Day-5 Kaplan-Meier curve for the customer's contract type. Survival-discount factors: **Month-to-month 15.56 effective months, One year 21.56, Two year 21.76**.
  - Mean LTV **₹708**, median ₹714. Mean value-at-risk by contract: M2M **₹291**, one-year ₹117, two-year ₹33.
  - Total portfolio value at risk = **₹13.6 L** `(simulation-based)`.
- **Profit curve** (`src/profit_curve.py` → `reports/profit_curve.json` + figure): net retained across all contact thresholds.
  - **Contact-everyone loses ₹3,69,938** — the premise of the project, now measured.
  - Profit-maximising global threshold **0.50**, contacting 1,529 → net **₹74,527**.
  - **Per-customer +EV rule earns ₹89,549 (+20.2%)** — strictly better than *any* global threshold.
- **Notebook** `notebooks/05_profit.ipynb` (executed) covers Days 9–11.

### Design decisions
- **D-035 — Single source of truth for economics.** Every monetary constant lives in `economics.py`; Day-11 sweeps it as scenarios. Makes the decision chain auditable and prevents assumption drift across modules.
- **D-036 — ₹500 offer cost REJECTED after measurement.** At ₹500, expected net was negative for **0 of 7,043** customers — mean LTV is only ₹708, so the offer consumed ~70% of a customer's entire lifetime margin. Recalibrated to **₹120** (call-centre contact ≈ ₹40 + discount value ≈ ₹80). An assumption that makes every action unprofitable is an implausible assumption, not a finding. Documented rather than silently tuned.
- **D-037 — Survival-weighted LTV, not ARPU × horizon.** Reuses the Day-5 KM curves so a month-to-month customer isn't credited with months they'll never pay for. Ties the "supporting" survival work into the load-bearing spine.
- **KEY FINDING — no single threshold can be optimal.** Break-even churn probability depends on LTV and ranges **0.221 → 1.959** across customers (median 0.480). The global profit-max threshold landing near 0.50 here is a coincidence of these assumptions, *not* a justification for the default. This is precisely what the Day-10 optimizer exploits.

### Post-review hardening (implicit-dependency fix)
A reader inspecting `feature_customer` (33 cols) correctly observed it contains **no** `churn_probability`, `km_expected_months`, or `ltv` column, and concluded Day 9 was unrunnable. The code in fact already regenerated both prerequisites in-process — but that design was **implicit and undocumented**, which is a defect in its own right.

- **Made the contract explicit.** `ltv.check_prerequisites()` validates only the Day 2-3 foundation (DB present; `account` + `feature_customer` tables; required raw columns) and states plainly that churn probabilities and survival factors are *generated*, not read.
- **Persisted the Day-5 artifact.** Survival factors now written to `reports/survival_factors.json` (M2M 15.56 / one-year 21.56 / two-year 21.76 expected months) so they are inspectable rather than transient.
- **Model loading, not blind retraining.** `_churn_probabilities()` loads `models/churn_model.pkl` when present and retrains deterministically only as a fallback (safe because of D-029).
- **Self-documenting columns.** `eff_months` → `km_expected_months`; `churn_proba` → `churn_probability` (alias retained for downstream compatibility).
- **One-command entrypoint** `src/run_pipeline.py` encodes the stage order and fails fast with a resume hint (`--from <stage>`).
- **Log noise fixed:** `assign_offers(verbose=False)` for the ~90 repeated sweep calls.

**Verified:** deleting `customer_value.parquet`, `churn_model.pkl` and `model_metrics.json`, then running `python src/run_pipeline.py --from ltv`, reproduces mean LTV **₹708**, **1,730** +EV customers at ₹120 (and **0** at ₹500), optimizer net **₹63,133**, uplift **+23.9%**, DP gap **0.000%** — with no manually invented columns.

- **D-048 — Generated prerequisites must be declared, validated, and persisted.** An implicit dependency that happens to work is still a defect: it is unauditable and invites someone to "fix" it by hand-adding columns. `tests/test_pipeline_deps.py` now pins the contract — asserting `feature_customer` does **not** store derived columns, that `build()` generates them, that a missing DB raises an *actionable* `PrerequisiteError`, and that the published Day-9 figures reproduce. (Writing that test exposed a second bug: the error handler called `relative_to()` on a path outside the repo and crashed while reporting the original error.)

- **D-049 — Phantom CLI flag + stale-column bug (found by a reader, not by the tests).** `python src/profit_curve.py --offer-cost 500` produced output *identical* to the default. Two independent defects:
  1. **`profit_curve.py` had no `argparse` at all.** Python silently accepted and discarded any flag (`--this-flag-is-nonsense` too). The ₹500 validation reported earlier had actually been produced by editing `economics.py`, not by that command — the command was never implemented. A real CLI now exists, and **unknown flags error out** instead of being ignored.
  2. **`theoretical_ceiling` read `expected_net_inr` straight from the parquet**, a column materialised by `ltv.py` at *its* offer cost. It therefore reported ₹89,549 at **every** offer cost. Same failure class as D-040 (silently-flat margin sweep): a precomputed column shadowing a parameter that was supposed to vary. `expected_net()` now derives from the cost-independent `expected_benefit_inr` at call time.

  **Corrected, verified figures:** ₹120 → 1,730 +EV customers, ceiling ₹89,549. ₹200 → 348, ₹8,297. **₹300 and ₹500 → 0 customers, ceiling ₹0**; at ₹500 the contact-everyone baseline is **−₹30,46,278**. Note the true break point is between ₹200 and ₹300, not at ₹500.

  Guards added: override runs never overwrite artifacts (extends D-047); `--budget` CLI added to `optimizer.py` for the same reason; five regression tests pin that the flag changes results, that ₹500 yields zero +EV customers, and that `expected_net` never reads the stale column. **Lesson: "the flag had no effect" and "the parameter has no effect" look identical from the outside — a silently-ignored input is indistinguishable from a genuinely insensitive model. Both must fail loudly.**

### Open / carried
- **OPEN-11 (Day 10):** budget-constrained optimizer + offer assignment + STAR #3.
- **OPEN-1 (still open):** `requirements.lock` after clean install.

### Commits for today
```
feat(econ): single source of truth for rupee assumptions
feat(ltv): survival-weighted per-customer LTV + expected value
feat(profit): rupee profit curve + cost-sensitive threshold
docs(runlog): day 9
```

---

## Day 10 — Cost-Sensitive Threshold & Budget Optimizer · work completed  ★ CORE WOW ◆ MILESTONE (STAR #3)

**Goal for today:** The headline — decide *whom to contact, with which offer, under a fixed budget* to maximise net revenue retained.

### Done
- **Offer catalogue + assignment** (`src/decision_engine.py`): three declared offers — Courtesy call (₹40, 15% acceptance), Protection bundle (₹120, 35%), Bill discount (₹220, 45%). Acceptance is modified by a **data-grounded** rule, not invented per customer: Day-5 adoption analysis showed protection add-ons roughly halve churn, so already-protected customers are modelled as less responsive (×0.6) to a protection bundle. Each customer receives the offer maximising expected net; **2,138 / 7,043 are +EV**.
- **Optimizer** (`src/optimizer.py` → `reports/optimizer_result.json`, `reports/contact_list.csv`): 0/1 knapsack — maximise Σ(benefit − cost) s.t. Σcost ≤ budget — solved greedily by **ROI per rupee** over +EV customers only.
- **Results under a binding ₹1,00,000 budget** `(simulation-based)`:

| Strategy | Contacted | Spend | Net retained |
|---|---:|---:|---:|
| **Optimizer (ROI-ranked)** | **1,349** | **₹1,00,000** | **₹63,133** |
| Rank by churn probability | 843 | ₹99,980 | ₹50,934 |
| Random selection | 1,993 | ₹99,980 | −₹18,351 |
| Contact everyone *(ignores budget)* | 7,043 | ₹3,59,060 | −₹60,009 |

  - **Uplift vs probability-ranking: +23.9%.** vs random: +444.0%. vs contact-everyone: +205.2%.
  - **Budget utilisation 100.0%.** Selected offer mix: 836 courtesy calls, 463 protection bundles, 50 bill discounts.
- **Optimality verified:** DP knapsack bound on a scaled cost grid = **₹63,133**, greedy = ₹63,133 → **gap 0.000%**.
- **Tests** (`tests/test_optimizer.py`): 6 tests — budget never exceeded, greedy within 1% of DP, beats probability-ranking, beats contact-everyone, only +EV customers selected, monotonic in budget — green.
- **STAR #3** appended (*thesis proven*).

### Design decisions
- **D-038 — Budget set to be BINDING (₹1,00,000).** At the original ₹5,00,000 the budget bound nothing (contacting the entire base costs ₹3.59 L), so every strategy collapsed to the same answer and the optimizer was meaningless. A budget-constrained optimizer must actually be constrained. Documented as a scenario assumption.
- **D-039 — Greedy by benefit/cost, verified against DP.** Item costs (₹40–220) are tiny relative to the budget, so the fractional-knapsack bound is tight. Rather than assert near-optimality, we *measured* it: gap 0.000%.
- **Offer-mix optimisation delivered** (roadmap stretch goal): multi-tier offers under budget, with expensive bill discounts reserved for the highest value-at-risk customers (avg churn 0.70, avg LTV ₹935).

- **D-047 — Scenario runs must not overwrite production artifacts.** A test calling `run(budget=50_000)` silently truncated `reports/contact_list.csv` from 1,349 to 767 rows. Persistence is now guarded behind a canonical-budget check; scenario runs (tests, sensitivity, cockpit sliders) compute but never write. Caught by asserting the artifact's row count after the suite, not by trusting it.

### Open / carried
- **OPEN-12 (Day 11):** sensitivity + what-if simulator.

### Commits for today
```
feat(decision): offer catalogue + expected-value offer assignment
feat(decision): budget-constrained retention optimizer (knapsack, DP-verified)
test(optimizer): budget feasibility, optimality gap, baseline dominance
docs(star): milestone 3 — thesis proven
docs(runlog): day 10
```

---

## Day 11 — Sensitivity Analysis & What-If Simulator · work completed

**Goal for today:** Stress-test the decision against the assumptions it rests on, and expose the levers as a simulator.

### Done
- **Sensitivity** (`src/sensitivity.py` → `reports/sensitivity.json` + tornado chart): one-way sweeps on acceptance, offer cost, gross margin, and budget; a two-way acceptance × offer-cost grid.
  - **Break-even acceptance scale = 0.350** → the campaign stops paying below a **≈12.2% protection-bundle acceptance rate**. Baseline assumes 35%, so there is roughly a **3× cushion** `(simulation-based)`.
  - **Offer cost is the most influential assumption** (tornado): at 3× cost, net retained falls to ₹0.
  - Margin sweep: ₹17,622 (0.40) → ₹1,03,963 (0.80). Budget sweep saturates at **₹2,00,000** — beyond it, extra budget buys nothing (no +EV customers left).
- **Simulator** (`src/simulator.py` → `reports/scenarios.json`): pure, state-restoring `simulate(budget, acceptance_scale, offer_cost_multiplier, gross_margin)`; powers the Day-13 cockpit sliders. Named scenarios:
  - **pessimistic → 0 customers contacted, ₹0 net.** Under weak acceptance, expensive offers and thin margin, *no* customer is +EV, so the system recommends **not running the campaign**.
  - base → 1,349 contacted, ₹63,133 net. optimistic → 741 contacted, ₹1,58,925 net.
- **Tests** (`tests/test_profit.py`): 8 tests across Days 9 & 11 — LTV positive/finite, value-at-risk ≤ LTV, contact-everyone unprofitable, optimal ≥ naive-0.5, +EV ceiling beats any global threshold, simulator respects budget, monotonic in acceptance, pessimistic scenario recommends restraint. Full suite now **27 passed**.

### Design decisions
- **D-040 — Margin-sensitivity bug found and fixed.** The first sweep returned an identical ₹63,133 at every margin: `ltv_inr` is precomputed into the parquet at the base margin, so patching `ECON.gross_margin` alone had no effect. LTV is linear in margin, so it is now explicitly rescaled. *A sensitivity analysis that silently fails to vary its input is worse than none* — caught only because the flat output looked implausible.
- **D-041 — The system may recommend inaction.** The pessimistic scenario contacting nobody is a feature, not a bug: a decision tool that knows when *not* to spend is more trustworthy than one that always spends. Encoded as a test.
- **D-042 — Acceptance rate named as the load-bearing assumption.** It is the one input that cannot be estimated from this dataset at all, and only the Day-12 A/B design can measure it.

### Open / carried
- **OPEN-13 (Day 12):** A/B experiment design doc.

### Commits for today
```
feat(sim): one/two-way sensitivity + tornado + break-even acceptance
fix(sim): rescale LTV under margin sweep (was silently flat)
feat(sim): what-if simulator + named scenarios + budget response curve
test(profit): LTV, profit-curve and simulator invariants
docs(runlog): day 11
```

---

## Day 12 — A/B Experiment Design Doc · work completed

**Goal for today:** Design how BharatConnect would *causally validate* the campaign in production — replacing the acceptance assumption with a measurement.

### Done
- **`docs/AB_experiment_design.md`** authored: hypothesis, unit of randomisation, population, stratified assignment, power analysis, guardrails, pre-registered decision rule, threats to validity.
  - **Randomisation happens inside the optimizer's eligible pool** (the 1,349-customer contact list), 50/50 stratified by `risk_segment` and `offer` tier → ≈674 per arm.
  - **Power analysis computed, not asserted** (α=0.05 two-sided, power=0.80; baseline churn among *targeted* customers = **0.600**):

| Relative churn reduction | Required n/arm | Feasible at 674/arm |
|---|---:|---|
| 5% | 4,229 | underpowered |
| 10% | 1,067 | underpowered |
| 15% | 477 | ✓ |
| 20% | 270 | ✓ |
| 30% | 120 | ✓ |

  - **MDE at 674/arm = a 12.6% relative churn reduction** — stated as the design's honest limit. A single monthly cohort *cannot* detect a 10% effect; pooling 2–3 cohorts is the pre-committed remedy.
  - **Guardrails:** ARPU in treatment (>5% drop), cost-per-save (>₹350), opt-out rate (>2× control), support-ticket volume (>1.5× control).
  - **Decision rule pre-registered** before data is seen: ship / iterate / kill, with effect sizes reported alongside p-values (same discipline as Day 6).

### Design decisions
- **D-043 — Randomise within the eligible pool → estimand is a CATE, not an ATE.** The effect is measured on the population the decision actually applies to. Stated openly rather than mislabelled as a population-wide effect.
- **D-044 — ITT primary, CACE/LATE secondary.** Non-compliance (customers who don't answer) is handled by reporting intention-to-treat as the unbiased primary, with an IV-based complier estimate as support.
- **D-045 — No peeking.** Fixed sample size, single 90-day read; O'Brien-Fleming alpha-spending if interim monitoring becomes necessary.
- **D-046 — Uplift modeling explicitly deferred, with the reason.** Identifying *persuadables* (vs sleeping dogs) requires randomised data this very experiment is designed to generate. You cannot honestly train an uplift model before running the trial that produces its training data. Named as future work, not omitted.
- **Ethical note recorded:** withholding contact from a control arm has a real expected cost (~half of one cycle's benefit); it is the price of knowing whether the campaign works at all, and must be an explicit, time-boxed decision by the stakeholder.

### Open / carried
- **OPEN-14 (Day 13):** Streamlit decision cockpit.
- **OPEN-1 (still open):** `requirements.lock` after clean install.

### Commits for today
```
docs: A/B experiment design for retention campaign (power, guardrails, decision rule)
docs(runlog): day 12
```
---
## Day 13 — Enterprise Edition redesign (v4, final)

Prior iterations drifted toward a console/cyberpunk aesthetic. Rebuilt the presentation layer against a measured audit. Analytics untouched throughout: net ₹63,132.68 · uplift +23.9% · AUC 0.8441 · 1,349 rows. Integrity audit ✓ · suite 68 passed.

Diagnosis (measured, not opinion)

The audit found the root cause was the design system, not the pages: the palette was literally VIOLET #8B5CF6 + MAGENTA #EC4899 (the banned purple/pink), with 11 gradients, 4 animations, and Rajdhani — an esports display face doing more to create the "gaming UI" read than the colours were. Page-level: Executive carried 8 KPI cards (no hierarchy); Customer carried 8 charts (chart dump); Scenario Simulator had no live controls at all — structurally backwards, since it is the page meant to be interactive.

Step 0 — design system

Deep-navy enterprise console (Azure Portal / Datadog / Cisco Control Center). Canvas 
#0A0F1A, surface 
#111A2B, raised 
#16213A, steel hairlines. One brand accent (blue 
#3B82F6); teal secondary; green/amber/red semantic only. Inter exclusively, tabular-nums on every figure. 8pt grid · 6px radius · one shadow · zero gradients · zero keyframe animation (150ms hover only). Hero numeral 3.05rem → 2.0rem: hierarchy from placement and whitespace, not size.

Steps 1–5 — modules
Executive Dashboard — lead card (recommendation) + four-tile portfolio row; churn trend by tenure; revenue bridge; action summary. 8 KPIs → 6, one clear entry point.
Decision Engine (flagship, renamed) — live budget optimizer as st.fragment; offer-strategy decision cards; priority queue ranked by return per rupee with three filters, queue summary and CSV export; evidence moved into tabs (uplift · profit curve · optimality).
Scenario Simulator — live assumption controls moved here (budget, acceptance, offer cost, margin); impact cards vs plan of record; side-by-side comparison panels; tornado; acceptance × cost heatmap; named scenarios.
Customer Intelligence — contract-mix and internet-mix donuts; segment matrix table ranked by revenue at risk; leakage treemap; ARPU-by-risk; subscriber archetype cards built from the real base; churn funnel; validation in an expander.
Executive Briefing (renamed from "AI Briefing") — narrative composed from live state; risk register; sequenced actions; changes-from-plan; business insights; CSV + TXT export.
Design decisions
D-063 — "AI Briefing" renamed to "Executive Briefing". No language model writes this page; the narrative is composed deterministically from the campaign state and governed metrics. Labelling a template "AI" would be the first overclaim in 13 days of honest labelling, and the Out-of-Scope register already rules out an LLM layer. "Deterministically generated from governed metrics, every figure traceable" is the stronger claim.
D-064 — Colour is information, not decoration. Green/amber/red are reserved for retained / caution / alert. One brand accent. This is why an amber cell now means something.
D-065 — Assumption controls belong on the Simulator. The budget lever stays on the Decision Engine (it is the thesis); acceptance, cost and margin moved to the Simulator. State persists, so either page drives the whole platform.
D-066 — Evidence behind tabs, decisions in front. Operational software surfaces the action and keeps the proof one click away.
Honest limitation

Verified programmatically (AppTest render × 5, AST audit, CSS structural + compliance checks). Not visually inspected — no browser installs in the build sandbox. Run streamlit run app/dashboard.py and review spacing, alignment and contrast on a real display before demoing.

Day 13 — Enterprise Edition, fix pass (v4.1)

Two issues from live testing on the user's machine (stricter DuckDB build than the sandbox).

D-067 — DuckDB binder crash in load_lifecycle. GROUP BY 1 with ORDER BY MIN(tenure_months) raised BinderException on the user's DuckDB (the sandbox build tolerated it — a false pass). Rewrote with an explicit WITH banded AS (...) subquery carrying both the label and an integer sort_key, grouping and ordering on real columns. Reconciles to 1,869 churned / 26.54%, matching frozen.
D-068 — Data-loader smoke tests. Three DuckDB errors have now slipped past AppTest because cached DB calls don't always surface under the render harness. Added test_all_data_loaders_execute: clears caches and calls every loader directly against the real DB, asserting row counts and the churn reconciliation. This is the test that would have caught all three. Suite now 69.
D-069 — Executive silhouette de-MacroPulse'd. User identified the opening (full-width ribbon → full-width banner → one oversized hero card) as MacroPulse's shape. Confirmed by inspection. Replaced with a Datadog/Azure-Portal pattern: compact one-line status strip (page question left, live campaign figures inline right) then a dense six-tile equal KPI strip, then straight into the content grid. Removed the full-width campaign_banner (dead code) and dropped hero=True from the Executive landing entirely. Other pages inherit the compact strip via the shared header.

Analytics frozen throughout: net ₹63,132.68 · uplift +23.9% · AUC 0.8441 · 1,349 rows. Audit ✓ · 69 passed.

 Day 14 — Reproducibility, CI, executive memo, STAR #4 ◆ MILESTONE (portfolio-grade)

Made the project senior: one-command reproducibility, an automated integrity + drift gate, and the portfolio-facing documents. No analytics touched — verified by rebuilding from raw.

Done
requirements.lock (14 pinned packages) — closes OPEN-1, carried since Day 1.
Makefile — setup · pipeline · test · audit · verify · app · all · clean. verify chains audit → tests → frozen-number check (the CI gate).
tools/check_frozen.py — asserts the four headline figures (net ₹63,132.68, uplift 23.9%, AUC 0.8441, 1,349 rows) against the produced artifacts; fails loudly on drift.
.github/workflows/ci.yml — on every push: pinned install → rebuild pipeline from source → audit → 69 tests → frozen check. Reproducibility is proven on a clean Ubuntu checkout, not asserted.
docs/executive_memo.md — one-page decision memo (recommendation, ₹ impact, risks, validation plan, deliberate non-decisions).
STAR #4 appended (reproducibility, integrity, product layer) — the set is now complete (4 milestones).
README.md — replaced the Day-1 stub with the final front door: results table, make quickstart, the thesis, the 5-page platform, reproducibility/integrity section, out-of-scope table, honesty pattern, doc index. All links verified.
Proven, not asserted
End-to-end reproducibility: wiped data/processed/ + reports/ + models/, ran python src/run_pipeline.py from raw, and it regenerated the frozen figures to the rupee (net ₹63,132.68, AUC 0.8441, 1,349 contacts). This is the day's real result.
Un-ignored the public IBM Telco raw CSV (data/raw/telco_churn_raw.csv) so CI can rebuild from source — it's a public dataset, no privacy concern.
Design decisions
D-070 — CI rebuilds from source rather than trusting committed artifacts. A CI that only reads committed reports/ proves nothing about reproducibility. Rebuilding the pipeline on a clean runner and then asserting the frozen numbers is the stronger guarantee.
D-071 — needs_data vs needs_reports test guards. Data-dependent tests (DuckDB/parquet) now skip cleanly when data/processed/ is absent (a bare checkout) and run when CI rebuilds it. Clean checkout: 20 pass / 49 skip, no crash. Full run: 69 pass.
D-072 — frozen numbers are a committed contract. check_frozen.py encodes the four headline figures as the drift gate; changing them requires changing the guard, deliberately.

Suite 69 passed · audit ✓ · frozen ✓. Remaining: Day 15 (deploy, résumé bullets, demo script, LinkedIn) and the product-experience pass discussed (onboarding, state-change feedback, empty/hold states).

Day 13 — product-experience pass + polish (v5)

Closed the "70% analytics / 30% product" gap the reviewer identified, and tightened the visual system. Analytics frozen: net ₹63,132.68 · uplift +23.9% · AUC 0.8441 · 1,349 rows. Audit ✓ · 71 passed.

Polish (measured, not eyeballed)
Type scale collapsed 17 → 7 sizes. An audit found 17 distinct font-size values — the reason the type read as unsystematic. Snapped to a disciplined ramp (.68 / .78 / .875 / 1 / 1.375 / 1.5 / 2 rem). Hardcoded 2/3px radii unified to a single 4px chip radius alongside var(--r) 6px for cards.
Product layer (the 30%)
D-073 — First-run onboarding. ui.onboarding() shows once per session at the top of the app: what the platform is, and "start on the Decision Engine." Dismissed to session_state.onboarded. A cold-open user now gets a start line instead of a mid-workflow drop.
D-074 — State-change feedback made legible. ui.scenario_flag() on every stateful page shows either "Plan of record" (locked) or "Custom scenario active — budget ₹X · acceptance Y× … Carried across every page." Backed by state.changes_from_plan(). The propagation that was always happening is now visible — the difference between a workflow that works and one you can see working.
D-075 — Designed empty/hold states. ui.empty_state() replaces bare st.error/blank panels: (a) the budget-hold recommendation ("hold the budget — no subscriber has positive expected value"), and (b) the priority queue when filters match nothing. Edge states are where student projects fall back to a traceback; these are crafted.
Tests

Added test_product_primitives_exist and test_hold_state_triggers_on_tiny_budget (asserts the hold state actually engages at a tiny budget and the custom-scenario diff is correct). Suite 69 → 71.

Honest limitation

Tabler icon webfont loads from a CDN (jsdelivr); if a demo machine is offline the empty-state glyphs won't render, though the text still does. Not visually inspected in-sandbox — run streamlit run app/dashboard.py and confirm the onboarding card, the custom-scenario flag (move a budget slider), and the hold state (drop the budget to ₹10,000) on a real display.

Fix — Streamlit auto-pages collision (app/pages/ → app/views/)

User reported seeing one long scroll with no navigation rail. Root cause: Streamlit auto-detects a folder literally named pages/ sitting beside the entrypoint (app/dashboard.py → app/pages/) and builds its own implicit multipage nav from it, which collides with the explicit st.navigation() router. Renamed app/pages/ → app/views/ so the auto-magic can never trigger and st.navigation is unambiguously the only navigation. Updated all imports, the AST auditor's package set and wiring check, and docs. Audit ✓, 71 passed, server boots with no auto-pages message, frozen intact.

D-076 — page modules live in app/views/, never app/pages/. The name pages/ is reserved by Streamlit's automatic multipage feature; using it beside an entrypoint that also calls st.navigation produces duplicate/broken navigation.

Fix — chart palette (semantic vs categorical separation)

User: "the colours of the charts are really bad." Correct — the charts mixed saturated semantic colours (red/green/amber) into categorical roles, so a churn funnel lit up like a traffic light and read meaning where there was none, clashing with the restrained navy shell.

D-077 — two-track chart palette. Split colour into (a) a muted categorical ramp (CAT — soft blue, muted teal, slate, dusty indigo, clay, sky) for "just different things" where colour must not imply valence, and (b) reserved semantic tones used only where valence is real, and softened (recovery 
#4E9E7E, cost/loss 
#C77B72) so they no longer glare against the dark surface. Ordered charts now use single-hue sequential ramps: the churn funnel went from five competing colours to one deepening blue; risk-ordered charts (treemap, ARPU violins, sankey nodes/links) route through a calm RISK ramp (teal → soft amber → soft coral). Donuts use CAT. The waterfall keeps green/coral for valence but muted, with the total in brand blue. Full-saturation RED/GREEN/AMBER remain only as UI state tokens (tags, alerts), never in chart fills.

71 passed · audit ✓ · frozen intact (net ₹63,132.68, AUC 0.8441, 1,349 rows). Not visually inspected in-sandbox — confirm on a real display.

Refine — muted brand fill for large chart areas (D-077 follow-up)

Screenshots after D-077 confirmed the categorical/semantic split landed, but full-saturation brand blue 
#3B82F6 in large filled bars (waterfall totals, strategy winner, tornado, offer bars, sankey offer nodes) was now the only remaining glare against the muted coral/teal. Added BLUE_FILL #4E7FC2 (muted brand) for large filled areas; vivid BLUE stays for lines, markers and thin accents where it doesn't overpower. 71 passed · frozen intact.

Day 13+ — Palette A (single plum-rose family) + telecom page identity + narrative spine

Full visual overhaul on user direction. Analytics frozen: net ₹63,132.68 · uplift +23.9% · AUC 0.8441 · 1,349 rows. Audit ✓ · 71 passed.

D-078 — Palette A, single tonal family. Replaced the enterprise-navy system with a plum-charcoal identity where every semantic accent lives in ONE rose/plum hue band, separated by lightness + warmth, not by unrelated hues: RISK_C deep rose 
#B0537A · OPP_C light mauve 
#D9A5C0 · REVENUE_C plum-violet 
#8E6BA8 · RECO_C brand rose 
#C77DA0 · ALERT_C coral-rose 
#D96B84 · NEUTRAL_C plum-grey. Back-compat aliases (BLUE→RECO_C etc.) so chart code kept working; CAT ramp = lightness steps within family + one neutral for busy charts. Surfaces CANVAS 
#0E0B12 / SURFACE 
#171320 / SURFACE_2 
#201A2E, plum-tinted borders, TEXT 
#F2EEF5. Streamlit config + :root semantic vars updated. Rationale: user wanted a unique premium identity (not the earlier rejected neon magenta); single-family reads as intentional/executive (cf. Radix Colors, Linear, Vercel Geist).

D-079 — Colour legend, Executive only. Full legend (risk/opportunity/revenue/recommendation/alert, each with business meaning) on the landing page only; other pages use small family-coloured ui.badge() status chips. Colour becomes an intuitive language after first contact rather than repeated chrome.

D-080 — Telecom page identity + narrative spine. Renamed pages to telecom-native labels: Network Command · Subscriber Intelligence · Retention Campaigns · Scenario Lab · Executive Brief (module filenames unchanged, so imports/tests/auditor stable). Added ui.next_step(question, target) closing every page except the terminus, forming a guided decision journey: Network Command → (revenue leaking, who?) → Subscriber Intelligence → (whom to contact?) → Retention Campaigns → (what breaks it?) → Scenario Lab → (summarise) → Executive Brief. Reads as a workflow, not disconnected pages.

Not visually inspected in-sandbox — confirm the plum family, legend, badges, and next-step flow on a real display.

Fix — sidebar invisible (hidden header removed the expand control)

User on Streamlit 1.59 reported NO sidebar at all, launched correctly. Root cause: the enterprise-redesign CSS hid the whole header element (header {display:none}) to remove Streamlit chrome — but the sidebar's collapse/expand toggle lives inside that header, so if the sidebar was collapsed there was no control to reopen it. Fixed: hide only #MainMenu/toolbar/decoration, keep header[data-testid=stHeader] present (transparent, height:0), and force the sidebar + collapsedControl visible. Also added a version-proof custom button rail fallback for Streamlit <1.36 (D-081). 71 passed, frozen intact.

D-081 — never hide the whole Streamlit header. It contains the sidebar expand control; hiding it can strand users with no navigation. Hide individual chrome testids instead.

Fix — navigation rebuilt as top tabs (sidebar approach abandoned)

User on Streamlit 1.59 still had NO navigation after the header-CSS fix, and the next-step link was a dead div. Root problem: sidebar-based nav kept failing on the user's machine for reasons not reproducible in-sandbox (collapsed rail / diverged tree). Decision: stop depending on the sidebar entirely.

D-082 — navigation moved to top-of-main-content tabs. Rebuilt main() around st.session_state.page + a row of st.button tabs rendered at the TOP of the main pane (brand row → 5 tab buttons → rule). This renders where it cannot be hidden by sidebar CSS or a collapsed rail. Dropped the st.navigation/st.Page dependency. Added goto(key) for programmatic navigation.

D-083 — next_step is now a real button. Consolidated two duplicate next_step defs into one that renders the next question + a real st.button; each page wires it to goto(next_key), so the narrative spine actually moves you page-to-page. Proven via AppTest simulated clicks: tab click switches page ✓, next-step button navigates ✓.

71 passed · audit ✓ · frozen intact.

## DAY 14 — Reproducibility, CI & executive reporting ◆ MILESTONE

Objective: move from "analysis that runs on my machine" to a reproducible, drift-proof repo another engineer can clone and trust.

Shipped

requirements.lock — 14 pinned packages, closes OPEN-1 (open since Day 1).
Makefile — setup · pipeline · test · audit · verify · app · all · clean; verify chains audit → tests → frozen check.
tools/check_frozen.py — asserts the four headline figures against produced artifacts, fails loudly on drift.
.github/workflows/ci.yml — clean checkout → pinned install → rebuild pipeline from source → audit → tests → frozen check.
docs/executive_memo.md — one-page decision memo (recommendation, ₹ impact, risks, validation plan, deliberate non-decisions).
STAR #4 appended — the interview set is complete (4 milestones).
README.md — replaced the Day-1 stub with the real front door.

Proven, not asserted. Wiped data/processed/, reports/, models/; ran src/run_pipeline.py from raw CSV; it regenerated the frozen figures to the rupee (net ₹63,132.68 · uplift 23.9% · AUC 0.8441 · 1,349 contacts). That reproduction is the day's real result.

Decisions

D-070 — CI rebuilds from source rather than trusting committed artifacts; reading back committed reports proves nothing about reproducibility.
D-071 — needs_data vs needs_reports test guards, so data-dependent tests skip cleanly on a bare checkout (20 pass / 49 skip) and run fully when CI rebuilds (69 pass).
D-072 — the frozen numbers are a committed contract; changing them requires changing the guard, deliberately.
DAY 15 — Product experience, visual identity & deployment ◆ FINAL

Objective: close the product gap, give the platform a distinct telecom identity, and ship it publicly.

Product experience
D-073/074/075 — first-run onboarding; scenario_flag making state propagation visible ("Plan of record" vs "Custom scenario active — carried across every page"); designed empty/hold states replacing bare errors (budget-hold recommendation, "no subscribers match these filters").
Type scale collapsed 17 → 7 sizes; small radii unified. Polish by subtraction.
Visual identity — Palette A, single tonal family
D-078 — replaced the enterprise-navy system with a plum-charcoal identity where every semantic accent lives in one rose/plum hue band, separated by lightness and warmth rather than unrelated hues: risk 
#B0537A · opportunity 
#D9A5C0 · revenue 
#8E6BA8 · recommendation 
#C77DA0 · alert 
#D96B84 · neutral 
#6E6479. Surfaces #0E0B12 / #171320 / #201A2E. Rationale: the earlier neon magenta read as gaming; a single family reads as intentional and executive (cf. Radix Colors, Linear, Vercel Geist).
D-077 — two-track chart colour: muted categorical vs reserved semantic; ordered charts use single-hue sequential ramps (the funnel went from five competing colours to one deepening ramp). BLUE_FILL added so large filled bars don't glare.
D-079 — full colour legend on the landing page only; other pages use small family-coloured badges. Colour becomes a language after first contact rather than repeated chrome.
Telecom identity & narrative
D-080 — pages renamed to telecom-native labels: Network Command · Subscriber Intelligence · Retention Campaigns · Scenario Lab · Executive Brief (module filenames unchanged, so imports/tests/auditor stayed stable). Each page closes by posing the next business question, forming a guided journey: network health → revenue leaking, who? → whom do we contact? → what breaks it? → summarise for leadership.
Navigation — the hard-won fix

Three separate causes, found in order:

D-076 — page modules must never live in a folder named pages/; Streamlit auto-builds an implicit nav from it that collides with an explicit router. Moved to app/views/.
D-081 — never hide the whole Streamlit header; the sidebar's expand control lives inside it, so hiding it can strand the user with no navigation. Hide individual chrome testids instead.
D-082 — after the sidebar still failed to render on the user's machine, abandoned sidebar navigation entirely. Rebuilt main() around st.session_state.page plus a row of tab buttons at the top of the main content area, where no sidebar CSS or collapsed rail can hide them. Dropped the st.navigation/st.Page dependency; added goto(key).
D-083 — next_step was a decorative div, not a control. Consolidated two duplicate definitions into one real button wired to goto(). Verified by simulated clicks: tab click switches page ✓, next-step button navigates ✓.

Lesson: when a framework's behaviour contradicts correct-looking code, suspect a framework convention before suspecting the logic — and when a mechanism keeps failing in an environment you cannot observe, replace the mechanism rather than continue debugging it blind.

Deployment
Processed data (DuckDB + parquet, 8.6 MB) un-ignored — the app reads it at runtime, so a cloud deploy without it would crash on boot.
requirements.txt re-pinned to the verified versions and pyarrow added (parquet reads would have failed); runtime.txt → Python 3.13.
Verified: no secrets, venv/cache ignored, theme config present, repo 12 MB.

Final state: 5-page decision platform · 71 tests · audit ✓ · frozen ✓ (net ₹63,132.68 · uplift +23.9% · AUC 0.8441 · 1,349 contacts) · reproducible from raw with one command · CI-gated.

Remaining is a human step only: push to GitHub and connect Streamlit Community Cloud (app/dashboard.py), then drop the live URL into the README, résumé bullets, and demo script.

Final — README rebuilt as the portfolio front door

Replaced the functional README with a recruiter-facing one: badge row (live app · CI · Python · tests), a hero screenshot slot, the problem stated as a business dilemma before any metric, a centred results table, the core insight (break-even churn probability spans 0.22–1.96, so no fixed threshold can be optimal) given its own section, a five-page platform tour with one screenshot slot each, tech-stack rationale table, reproducibility section, the design-system colour key, the deliberate non-decisions table, the honesty pattern, a "what I'd build next" section, and a documentation index. Seven screenshot slots and an optional demo-GIF slot are marked with HTML comments specifying exactly what to capture. Corrected stale facts carried from earlier drafts (69 → 71 tests; sidebar rail → top-tab routing; app/pages → app/views). Also fixed the same stale routing claim in the dashboard.py module docstring.

Production polish pass — enterprise refinement

UI/UX only. Architecture, business logic, ML pipeline, optimizer, calculations and data flow untouched — confirmed by check_frozen (net ₹63,132.68 · uplift 23.9% · AUC 0.8441 · 1,349 rows) and the full suite. Audit ✓ · 71 passed.

D-084 — persistent global command bar; page chrome de-duplicated. Platform health (Subscriber feed · Risk engine AUC · Mode), live campaign KPIs (Budget · Targeted · Net retained · Utilisation), scenario state and build metadata (Refreshed · Model v1.2 · Data v1.0 · Pipeline v1.4) now render once in the app chrome. _shell.header() was rendering all of it on every page — and calling ui.workflow() twice — with two further mid-page breadcrumbs in brief.py and decision.py. That repetition was the main reason five pages read as one long scroll. header() is now page identity only (title + the question the page answers); workflow_step/banner are retained as ignored parameters for call-site compatibility.

D-085 — typography hierarchy in four distinct levels. Page title 1.6rem/600/tight tracking → section heading .8rem/600/uppercase-tracked with a rule → KPI value 1.5rem tabular → supporting text .73–.83rem muted. Sections previously competed with page titles at similar weight.

D-086 — density increased ~25%. Block padding 1.25/2/3rem → .9/1.75/2rem; vertical block gap → .55rem; horizontal gap → .65rem; card padding 1/1.1rem → .8/.9rem; section margins 1.75/.8 → 1.35/.6rem.

D-087 — card and table treatment. Cards: inset top highlight, layered shadow, 1px lift and border brighten on hover. Tables: sticky uppercase headers, zebra striping, rose hover highlight, tabular numerals, rounded clipped corners.

D-088 — micro-interactions. 280ms fade-and-rise on cards, charts, tables and the command bar; button hover glow and 1px active depression; all transitions ≤180ms. No looping animation.

D-089 — scroll reset on navigation. Streamlit preserves scroll offset across reruns, so switching pages landed mid-document. _scroll_top_if_page_changed() injects a one-shot scroll-to-top when the page key changes, guarded in try/except — a cosmetic feature must never break navigation.

D-090 — number formatting standardised. Added data._indian_group() so inr_exact renders Indian digit grouping (₹13,58,000 not ₹1,358,000) and data.pct() for consistent percentages. Presentation only; no computed value changes.

D-091 — loading and empty states. Meaningful spinners: "Updating optimizer — re-solving the budget allocation…", "Running simulation — re-pricing every subscriber…", "Loading subscribers — reading the governed feed…". Designed empty states already covered the hold and no-match cases.

D-092 — recommendation cards explain themselves. New ui.recommendation() renders the verdict with confidence (derived from the break-even acceptance cushion), return per rupee, and four evidence bullets (uplift vs both baselines, DP optimality gap, decile capture and AUC, break-even cushion), plus the acceptance caveat. A recommendation without reasoning is an assertion.

D-093 — Executive Brief as a consulting deliverable. Six numbered sections: Executive summary · Financial impact · Key risks · Recommendation · Approval required · Expected outcome. Still composed deterministically from live campaign state — no LLM.

D-094 — scenario presets. Conservative · Expected · Aggressive · Worst case · Best case, each setting the four existing assumption sliders with a one-line rationale. Presets move declared assumptions only; the simulation path is unchanged.

D-095 — chart takeaways. Captions on the highest-traffic charts promoted to styled ui.takeaway() blocks — accent rule, marker glyph — so the business conclusion reads as a deliberate statement rather than fine print.

