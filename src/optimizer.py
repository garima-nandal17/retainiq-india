"""
optimizer.py — RetainIQ India (Day 10)  ★ THE THESIS

Given a fixed retention budget, decide WHOM to contact and WITH WHICH OFFER to
maximise net revenue retained.

Formally a 0/1 knapsack: each customer i has an offer with cost c_i and expected
benefit b_i = P(churn)_i * LTV_i * acceptance_i; choose S maximising
sum(b_i - c_i) subject to sum(c_i) <= B.

We solve it greedily by **benefit-to-cost ratio** (ROI per rupee), restricted to
customers whose expected net is positive. Justification: item costs (Rs 40-220)
are tiny relative to the budget (Rs 5,00,000), so the fractional-knapsack bound
is tight — the greedy solution is provably within one item's value of optimal.
We verify this empirically against a DP solve on a scaled cost grid.

Baselines compared (this is what makes the number meaningful):
  1. contact-everyone (spray)
  2. random selection under the same budget
  3. rank by churn probability only (the "typical churn project")
  4. rank by ROI per rupee (ours)

All figures are (simulation-based estimates) — assumptions in economics.py.

Run:  python src/optimizer.py
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from decision_engine import assign_offers
from economics import ECON, ASSUMPTION_NOTE

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | optimizer | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("optimizer")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "optimizer_result.json"
CONTACT_LIST = ROOT / "reports" / "contact_list.csv"
SEED = 42


# ---------------------------------------------------------------- strategies
def _evaluate(sel: pd.DataFrame) -> dict:
    return {"n_contacted": int(len(sel)),
            "spend_inr": round(float(sel.offer_cost_inr.sum()), 2),
            "expected_benefit_inr": round(float(sel.offer_benefit_inr.sum()), 2),
            "net_retained_inr": round(float(sel.offer_net_inr.sum()), 2)}


def greedy_roi(df: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Ours: +EV customers ranked by benefit/cost, filled until budget exhausted."""
    cand = df[df.eligible].sort_values("roi_per_rupee", ascending=False)
    cum = cand.offer_cost_inr.cumsum()
    return cand[cum <= budget]


def rank_by_probability(df: pd.DataFrame, budget: float) -> pd.DataFrame:
    """The typical churn project: contact the riskiest, ignore value and cost."""
    cand = df.sort_values("churn_proba", ascending=False)
    cum = cand.offer_cost_inr.cumsum()
    return cand[cum <= budget]


def random_selection(df: pd.DataFrame, budget: float, seed: int = SEED) -> pd.DataFrame:
    cand = df.sample(frac=1.0, random_state=seed)
    cum = cand.offer_cost_inr.cumsum()
    return cand[cum <= budget]


def contact_everyone(df: pd.DataFrame) -> pd.DataFrame:
    return df  # ignores the budget entirely — shown for contrast


def dp_optimal(df: pd.DataFrame, budget: float, scale: int = 20) -> float:
    """DP knapsack on a coarsened cost grid, to bound the greedy gap."""
    cand = df[df.eligible]
    costs = (cand.offer_cost_inr.values / scale).astype(int)
    vals = cand.offer_net_inr.values
    cap = int(budget // scale)
    dp = np.zeros(cap + 1)
    for c, v in zip(costs, vals):
        if c <= cap:
            dp[c:] = np.maximum(dp[c:], dp[:cap - c + 1] + v)
    return float(dp[cap])


# ---------------------------------------------------------------- driver
def run(budget: float | None = None) -> dict:
    budget = ECON.budget_inr if budget is None else budget
    df = assign_offers()

    strategies = {
        "optimizer_roi": greedy_roi(df, budget),
        "rank_by_probability": rank_by_probability(df, budget),
        "random": random_selection(df, budget),
        "contact_everyone": contact_everyone(df),
    }
    results = {k: _evaluate(v) for k, v in strategies.items()}
    for k, v in results.items():
        flag = " (ignores budget)" if k == "contact_everyone" else ""
        logger.info("%-20s n=%5d spend=₹%9.0f net=₹%10.0f%s",
                    k, v["n_contacted"], v["spend_inr"], v["net_retained_inr"], flag)

    ours = results["optimizer_roi"]
    logger.info("budget utilisation: %.1f%% of ₹%.0f",
                100 * ours["spend_inr"] / budget, budget)

    # uplift vs each baseline
    uplift = {}
    for k in ["rank_by_probability", "random", "contact_everyone"]:
        b = results[k]["net_retained_inr"]
        uplift[k] = round((ours["net_retained_inr"] - b) / abs(b) * 100, 1)
        logger.info("uplift vs %-20s %+8.1f%%  (simulation-based)", k, uplift[k])

    # optimality check
    dp = dp_optimal(df, budget)
    gap = (dp - ours["net_retained_inr"]) / dp * 100 if dp else 0.0
    logger.info("DP knapsack bound ₹%.0f vs greedy ₹%.0f -> gap %.3f%%",
                dp, ours["net_retained_inr"], gap)

    sel = strategies["optimizer_roi"]
    cols = ["customer_id", "churn_proba", "ltv_inr", "offer", "offer_cost_inr",
            "offer_benefit_inr", "offer_net_inr", "roi_per_rupee", "risk_segment",
            "customer_value_segment"]

    # Persist ONLY for the canonical budget. Scenario runs (tests, sensitivity,
    # the cockpit's sliders) must never overwrite the production contact list.
    # Found when a test's run(budget=50_000) silently truncated contact_list.csv.
    is_canonical = abs(budget - ECON.budget_inr) < 1e-9

    mix = sel.groupby("offer").agg(n=("customer_id", "size"),
                                   spend=("offer_cost_inr", "sum"),
                                   net=("offer_net_inr", "sum")).round(0)
    logger.info("selected offer mix:\n%s", mix.to_string())

    out = {"assumptions": ECON.as_dict(), "assumption_note": ASSUMPTION_NOTE,
           "budget_inr": budget, "results": results, "uplift_pct": uplift,
           "budget_utilisation_pct": round(100 * ours["spend_inr"] / budget, 1),
           "dp_bound_inr": round(dp, 2), "greedy_gap_pct": round(gap, 3),
           "offer_mix": mix.reset_index().to_dict("records")}
    if is_canonical:
        sel[cols].to_csv(CONTACT_LIST, index=False)
        OUT.write_text(json.dumps(out, indent=2))
        logger.info("saved %s + %s", OUT.relative_to(ROOT), CONTACT_LIST.relative_to(ROOT))
    else:
        logger.info("scenario run (budget ₹%.0f) — artifacts NOT overwritten", budget)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Budget-constrained retention optimizer. Override the budget "
                    "to explore scenarios (e.g. --budget 50000).")
    ap.add_argument("--budget", type=float, default=None, metavar="INR",
                    help=f"retention budget in rupees (default: {ECON.budget_inr:.0f} "
                         f"from src/economics.py). Non-canonical budgets do NOT "
                         f"overwrite reports/contact_list.csv (D-047).")
    args = ap.parse_args()   # unknown flags error out rather than being ignored
    run(budget=args.budget)


if __name__ == "__main__":
    main()
    