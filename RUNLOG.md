# RetainIQ India — Build Runlog

An engineering diary for the RetainIQ India project. One entry per working day, appended while the work is fresh. This file is the *narrative* of how the project evolved; the BRD, code, and docs are the *artifacts* it produced. It grows from Day 1 through Day 15.

**Conventions**
- Newest entry at the top.
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
## Day 2 — Database Design & Data Load

**Goal for today:** Design a normalized schema and load the raw BharatConnect dataset into DuckDB using an ETL pipeline. Complete the deferred documentation from Day 1 now that the dataset is available.

### Done

- Downloaded the IBM Telco Customer Churn dataset and stored it as `data/raw/telco_churn_raw.csv` (git-ignored).
- Verified the dataset contains **7,043 rows** and **21 columns**, with a base churn rate of **26.54%**.
- Designed a normalized relational schema (`sql/schema.sql`) consisting of:
  - `customer` (CRM)
  - `account` (billing + churn target)
  - `service_subscription` (provisioning, long format)
- Built the ETL pipeline (`src/load_data.py`) following the **Extract → Transform → Load (ETL)** pattern.
- Created and activated a dedicated Python **3.13** virtual environment for the project.
- Installed the required Day 2 dependencies (`pandas`, `duckdb`, `openpyxl`).
- Generated `requirements.lock` using `pip freeze` to capture the exact dependency versions for reproducibility.
- Converted the nine service columns from the raw dataset into a normalized long-format `service_subscription` table.
- Successfully loaded the dataset into DuckDB (`data/processed/retainiq.duckdb`).
- Verified successful loading:
  - **7,043** customer records
  - **7,043** account records
  - **63,387** service subscription records
  - **11** NULL values in `total_charges` (customers with tenure = 0)
  - Base churn rate: **26.54%**
- Authored the project Data Dictionary (`docs/data_dictionary.md`).
- Completed the Data Acquisition & Provenance document (`docs/data_acquisition.md`).

### Design Decisions

**D-005 — Normalize before feature engineering.**  
Customer demographics, billing information, and subscribed services are stored in separate tables. A denormalized feature layer will be created later (Day 3) specifically for analytics and modeling.

**D-006 — Long-format service table.**  
The nine service columns were converted into a `(customer_id, service_name, status)` structure. This eliminates repeating groups and makes later analyses such as service adoption, service counts, and SQL aggregations significantly simpler.

**D-007 — Honest handling of missing values.**  
The 11 blank values in `TotalCharges` are preserved as `NULL` rather than being imputed or replaced. Data quality decisions belong to the validation framework (Day 4), not the ETL loader.

**D-008 — Currency by declaration.**  
The business scenario assumes BharatConnect is a fictional Indian telecom operator, so monetary columns are treated as Indian Rupees (₹) without applying an exchange-rate conversion. This avoids introducing unnecessary assumptions while preserving analytical consistency.

### Open / Carried to Next Day

- **OPEN-4 (Day 3):** Build the SQL feature layer using advanced SQL (CTEs, advanced window functions, indexing, and execution-plan analysis).

### Commits for Today

```text
feat(db): normalized database schema
feat(etl): build ETL pipeline and load DuckDB
chore(env): create Python 3.13 virtual environment and freeze dependencies
docs: data dictionary and data acquisition
docs(runlog): day 2
```