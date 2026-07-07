"""
cohorts.py — RetainIQ India (Day 5)

Tenure cohorts and an RFM-style retention segmentation adapted to the signals
this dataset actually has.

Honesty note on RFM: classic RFM needs transactional **Recency** and
**Frequency**, which a cross-sectional snapshot lacks. We therefore build an
RFM-*inspired* T-E-M scheme from available proxies and say so:
  Monetary   = monthly_charges_inr (ARPU)        -> genuine
  Engagement = services_held (breadth of use)     -> Frequency proxy
  Tenure     = tenure_months (longevity)          -> replaces Recency (stated)

Run:  python src/cohorts.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | cohorts | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("cohorts")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"


def _load() -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("""
        SELECT customer_id, tenure_months, services_held, monthly_charges_inr,
               customer_value_segment, churned::INT AS churned
        FROM feature_customer
    """).df()
    con.close()
    return df


def _q4(s: pd.Series) -> pd.Series:
    # rank-based quartile score 1..4 (robust to ties)
    return pd.qcut(s.rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)


def run() -> dict:
    df = _load()

    # 1) tenure-cohort retention
    df["tenure_bucket"] = pd.cut(df["tenure_months"], [-1, 12, 24, 48, 100],
                                 labels=["00-12", "13-24", "25-48", "49+"])
    cohort = (df.groupby("tenure_bucket", observed=True)
                .agg(customers=("customer_id", "size"),
                     churn_rate=("churned", "mean"))
                .assign(churn_rate=lambda x: x.churn_rate.round(3)))
    logger.info("Tenure-cohort retention:\n%s", cohort.to_string())

    # 2) RFM-style T-E-M scores
    df["tenure_score"] = _q4(df["tenure_months"])
    df["engagement_score"] = _q4(df["services_held"])
    df["monetary_score"] = _q4(df["monthly_charges_inr"])
    df["tem_score"] = df[["tenure_score", "engagement_score", "monetary_score"]].sum(axis=1)

    # named actionable segments (retention lens)
    def label(r):
        if r.tenure_score >= 3 and r.monetary_score >= 3:
            return "Loyal high-value"
        if r.tenure_score <= 2 and r.monetary_score >= 3:
            return "New high-value (watch)"
        if r.engagement_score <= 1:
            return "Low-engagement"
        if r.tenure_score <= 2:
            return "New / unproven"
        return "Stable mid"
    df["rfm_segment"] = df.apply(label, axis=1)

    seg = (df.groupby("rfm_segment")
             .agg(customers=("customer_id", "size"),
                  avg_arpu=("monthly_charges_inr", "mean"),
                  churn_rate=("churned", "mean"))
             .round({"avg_arpu": 1, "churn_rate": 3})
             .sort_values("churn_rate", ascending=False))
    logger.info("RFM-style segments (churn desc):\n%s", seg.to_string())

    # 3) value x loyalty matrix (feeds the optimizer's prioritization)
    df["loyalty"] = pd.cut(df["tenure_months"], [-1, 24, 100], labels=["New(<=24m)", "Tenured(>24m)"])
    matrix = (df.pivot_table(index="customer_value_segment", columns="loyalty",
                             values="churned", aggfunc="mean", observed=True)
                .round(3))
    logger.info("Churn by value x loyalty:\n%s", matrix.to_string())

    return {"tenure_cohort": cohort.reset_index().to_dict("records"),
            "rfm_segments": seg.reset_index().to_dict("records"),
            "value_loyalty_matrix": matrix.reset_index().to_dict("records")}


if __name__ == "__main__":
    run()