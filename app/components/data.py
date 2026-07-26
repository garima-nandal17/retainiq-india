"""
data.py — RetainIQ cockpit data access (Day 13, UI only).

STRICTLY READ-ONLY over `reports/`. The cockpit renders governed metrics; it never
computes them. This keeps the app and the pipeline from ever disagreeing.

The one live interaction (budget slider) calls the existing, pure
`simulator.simulate()` built on Day 11. Scenario runs cannot overwrite
`reports/contact_list.csv` — that guard already lives in the optimizer (D-047).

Missing artifacts fail loudly, naming the script to run (D-048 lesson).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"
sys.path.insert(0, str(ROOT / "src"))

# artifact -> the command that regenerates it
PRODUCER = {
    "optimizer_result.json": "python src/optimizer.py",
    "contact_list.csv": "python src/optimizer.py",
    "profit_curve.json": "python src/profit_curve.py",
    "sensitivity.json": "python src/sensitivity.py",
    "scenarios.json": "python src/simulator.py",
    "evaluation.json": "python src/evaluate.py",
    "shap_drivers.json": "python src/explain.py",
    "model_metrics.json": "python src/model.py",
    "survival_factors.json": "python src/ltv.py",
    "dq_report.json": "python src/data_quality.py",
}


class MissingArtifact(FileNotFoundError):
    pass


def _require(name: str) -> Path:
    p = REPORTS / name
    if not p.exists():
        raise MissingArtifact(
            f"{p.relative_to(ROOT)} not found. Run `{PRODUCER.get(name, 'python src/run_pipeline.py')}` "
            f"(or `python src/run_pipeline.py` for the full chain).")
    return p


@st.cache_data(show_spinner=False)
def load_json(name: str) -> dict:
    return json.loads(_require(name).read_text())


@st.cache_data(show_spinner=False)
def load_contact_list() -> pd.DataFrame:
    return pd.read_csv(_require("contact_list.csv"))


@st.cache_data(show_spinner=False)
def load_customer_values() -> pd.DataFrame:
    """Per-customer LTV/risk table — for segmentation views only."""
    import duckdb
    p = ROOT / "data" / "processed" / "customer_value.parquet"
    if not p.exists():
        raise MissingArtifact(f"{p.name} not found. Run `python src/ltv.py`.")
    return duckdb.connect().execute(f"SELECT * FROM read_parquet('{p}')").df()


@st.cache_data(show_spinner=False)
def load_network_profile() -> pd.DataFrame:
    """Access-network attributes from the frozen Day-3 feature view. Read-only."""
    import duckdb
    db = ROOT / "data" / "processed" / "retainiq.duckdb"
    if not db.exists():
        raise MissingArtifact(f"{db.name} not found. Run `python src/run_pipeline.py`.")
    con = duckdb.connect(str(db), read_only=True)
    try:
        return con.execute("""
            SELECT customer_id, internet_type, has_phone, services_held,
                   protection_count, streaming_count, monthly_charges_inr
            FROM feature_customer ORDER BY customer_id
        """).df()
    finally:
        con.close()


# Contract tiers stand in for the operator's postpaid/prepaid ladder. The source
# data has NO prepaid flag, so this is a DECLARED mapping surfaced in the UI —
# never a fabricated column.
CONTRACT_TIER = {
    "Month-to-month": "Rolling · prepaid-style",
    "One year": "Postpaid · annual",
    "Two year": "Postpaid · biennial",
}
TIER_NOTE = ("Contract tiers stand in for the postpaid/prepaid ladder. The source "
             "data carries no prepaid flag, so this is a declared mapping, not a "
             "data field. Fibre, DSL and voice-line attributes are real.")


@st.cache_data(show_spinner=False)
def load_lifecycle() -> list[dict]:
    """Tenure-cohort retained/churned counts from the frozen feature view. Read-only."""
    import duckdb
    db = ROOT / "data" / "processed" / "retainiq.duckdb"
    if not db.exists():
        raise MissingArtifact(f"{db.name} not found. Run `python src/run_pipeline.py`.")
    con = duckdb.connect(str(db), read_only=True)
    try:
        df = con.execute("""
            WITH banded AS (
                SELECT churned,
                       CASE WHEN tenure_months<=12 THEN '0-12'
                            WHEN tenure_months<=24 THEN '13-24'
                            WHEN tenure_months<=48 THEN '25-48'
                            ELSE '49+' END AS tenure_bucket,
                       CASE WHEN tenure_months<=12 THEN 0
                            WHEN tenure_months<=24 THEN 1
                            WHEN tenure_months<=48 THEN 2
                            ELSE 3 END AS sort_key
                FROM feature_customer
            )
            SELECT tenure_bucket,
                   SUM((NOT churned)::INT) AS retained,
                   SUM(churned::INT)       AS churned,
                   AVG(churned::INT)       AS churn_rate
            FROM banded
            GROUP BY tenure_bucket, sort_key
            ORDER BY sort_key
        """).df()
    finally:
        con.close()
    return df.to_dict("records")


def figure(name: str) -> Path | None:
    p = FIGURES / name
    return p if p.exists() else None


@st.cache_data(show_spinner="Recomputing the decision…")
def simulate(budget: float, acceptance_scale: float,
             offer_cost_multiplier: float, gross_margin: float) -> dict:
    """Live what-if. Delegates to the Day-11 simulator — no new business logic."""
    import simulator
    return simulator.simulate(budget=budget, acceptance_scale=acceptance_scale,
                              offer_cost_multiplier=offer_cost_multiplier,
                              gross_margin=gross_margin)


# ── formatting helpers (presentation only) ───────────────────────────────────
def inr(v: float, decimals: int = 0) -> str:
    """Indian-format rupees: ₹63,133 / ₹1.36 L / ₹1.2 Cr."""
    if v is None:
        return "—"
    neg = v < 0
    v = abs(float(v))
    if v >= 1e7:
        s = f"₹{v/1e7:.2f} Cr"
    elif v >= 1e5:
        s = f"₹{v/1e5:.2f} L"
    else:
        s = f"₹{v:,.{decimals}f}"
    return ("−" + s) if neg else s


def inr_exact(v: float) -> str:
    if v is None:
        return "—"
    neg = v < 0
    n = _indian_group(abs(float(v)))
    return ("−₹" + n) if neg else ("₹" + n)


def pct(v: float, decimals: int = 1) -> str:
    return "—" if v is None else f"{v:.{decimals}f}%"


SIM_LABEL = "(simulation-based estimate)"

def _indian_group(n: float) -> str:
    """Indian digit grouping: 1358000 -> 13,58,000."""
    neg, n = n < 0, abs(int(round(n)))
    s = str(n)
    if len(s) <= 3:
        out = s
    else:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        out = ",".join(parts) + "," + tail
    return ("−" if neg else "") + out


def pct(v: float, dp: int = 1) -> str:
    """Standard percentage rendering: 26.5%. Accepts either 0.2654 or 26.54."""
    if v is None:
        return "—"
    v = float(v)
    if -1.0 <= v <= 1.0:
        v *= 100
    return f"{v:.{dp}f}%"