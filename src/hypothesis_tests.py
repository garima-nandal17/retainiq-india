"""
hypothesis_tests.py — RetainIQ India (Day 6)

Tests which factors are statistically associated with churn, always paired with
an EFFECT SIZE (significance alone is cheap at n=7,043 — almost everything is
"significant"; effect size tells us what actually matters).

  categorical vs churn -> chi-square + Cramer's V
  numeric by churn     -> Welch t-test + Cohen's d

Run:  python src/hypothesis_tests.py
"""
from __future__ import annotations

import logging
from math import sqrt
from pathlib import Path

import duckdb
import numpy as np
from scipy import stats

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | htest | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("hypothesis")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
ALPHA = 0.05


def _df():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("""
        SELECT churned::INT AS churned, contract_type, payment_method,
               internet_type, senior_citizen::INT AS senior_citizen,
               tenure_months, monthly_charges_inr
        FROM feature_customer
    """).df()
    con.close()
    return df


def cramers_v(table: np.ndarray) -> float:
    chi2 = stats.chi2_contingency(table, correction=False)[0]
    n = table.sum()
    r, k = table.shape
    return sqrt((chi2 / n) / (min(r, k) - 1))


def cohens_d(a, b) -> float:
    na, nb = len(a), len(b)
    sp = sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    return (a.mean() - b.mean()) / sp


def _v_size(v):  # Cramer's V interpretation (df-agnostic rough bands)
    return "small" if v < 0.1 else "moderate" if v < 0.3 else "large"


def _d_size(d):
    d = abs(d)
    return "negligible" if d < 0.2 else "small" if d < 0.5 else "moderate" if d < 0.8 else "large"


def run() -> dict:
    df = _df()
    results = []

    # --- categorical drivers: chi-square + Cramer's V ---
    for col in ["contract_type", "payment_method", "internet_type", "senior_citizen"]:
        table = df.groupby(col)["churned"].value_counts().unstack(fill_value=0).values
        chi2, p, dof, _ = stats.chi2_contingency(table)
        v = cramers_v(table)
        verdict = ("reject H0" if p < ALPHA else "fail to reject") + \
                  f"; effect {_v_size(v)}"
        results.append({"test": "chi-square", "factor": col, "stat": round(chi2, 1),
                        "p": p, "effect": "Cramer's V", "effect_size": round(v, 3),
                        "verdict": verdict})
        logger.info("[chi2] %-16s chi2=%8.1f p=%.2e V=%.3f (%s)",
                    col, chi2, p, v, _v_size(v))

    # --- numeric drivers: Welch t-test + Cohen's d ---
    for col in ["tenure_months", "monthly_charges_inr"]:
        a = df.loc[df.churned == 1, col]
        b = df.loc[df.churned == 0, col]
        t, p = stats.ttest_ind(a, b, equal_var=False)
        d = cohens_d(a, b)
        verdict = ("reject H0" if p < ALPHA else "fail to reject") + \
                  f"; effect {_d_size(d)}"
        results.append({"test": "Welch t-test", "factor": col, "stat": round(t, 1),
                        "p": p, "effect": "Cohen's d", "effect_size": round(d, 3),
                        "verdict": verdict})
        logger.info("[t]    %-16s t=%8.1f p=%.2e d=%+.3f (%s)  churn_mean=%.1f retain_mean=%.1f",
                    col, t, p, d, _d_size(d), a.mean(), b.mean())

    # rank drivers by |effect size| (magnitude). NB: Cramer's V and Cohen's d
    # live on different scales, so this ordering is a heuristic, not exact.
    ranked = sorted(results, key=lambda r: abs(r["effect_size"]), reverse=True)
    logger.info("Drivers ranked by EFFECT SIZE:")
    for r in ranked:
        logger.info("   %-18s %-12s size=%.3f", r["factor"], r["effect"], r["effect_size"])

    return {"alpha": ALPHA, "tests": results, "ranked_by_effect": [r["factor"] for r in ranked]}


if __name__ == "__main__":
    run()