"""
decision_engine.py — RetainIQ India (Day 10)

Offer assignment: for each customer, which offer (if any) maximises expected net
value? This sits between the profit curve (Day 9) and the budget optimizer.

Offer catalogue — all ASSUMPTIONS (see economics.py honesty note). Costs and
acceptance rates are declared, not learned; uplift modeling (which offer *causes*
a save) is deliberately out of scope until the Day-12 A/B test generates data.

Acceptance rates are differentiated by a defensible, data-grounded rule rather
than invented per customer: Day-5 adoption analysis showed protection add-ons
roughly HALVE churn (OnlineSecurity ratio 0.47, TechSupport 0.49), so a
protection bundle is modelled as the most effective offer for customers who lack
protection. Customers already protected are assumed less responsive to it.

Run:  python src/decision_engine.py
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from economics import ECON

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | decision | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("decision_engine")

ROOT = Path(__file__).resolve().parents[1]
CV = ROOT / "data" / "processed" / "customer_value.parquet"
DB = ROOT / "data" / "processed" / "retainiq.duckdb"


@dataclass(frozen=True)
class Offer:
    name: str
    cost_inr: float
    base_acceptance: float
    note: str


# Costs are small relative to the margin they protect (see D-036).
OFFERS: list[Offer] = [
    Offer("Courtesy call", 40.0, 0.15,
          "Contact only, no discount. Cheapest; lowest acceptance."),
    Offer("Protection bundle", 120.0, 0.35,
          "Free OnlineSecurity/TechSupport for 3 months. Day-5 evidence: "
          "protection add-ons roughly halve churn."),
    Offer("Bill discount", 220.0, 0.45,
          "Direct monetary discount. Highest acceptance, highest cost."),
]


def load_candidates() -> pd.DataFrame:
    df = duckdb.connect().execute(f"SELECT * FROM read_parquet('{CV}')").df()
    con = duckdb.connect(str(DB), read_only=True)
    prot = con.execute(
        "SELECT customer_id, protection_count FROM feature_customer ORDER BY customer_id"
    ).df()
    con.close()
    return df.merge(prot, on="customer_id", how="left")


def _acceptance(offer: Offer, row) -> float:
    """Data-grounded modifier, not a per-customer invention."""
    a = offer.base_acceptance
    if offer.name == "Protection bundle" and row.protection_count > 0:
        a *= 0.6   # already protected -> less responsive to more protection
    return min(a, 0.95)


def assign_offers(df: pd.DataFrame | None = None, verbose: bool = True) -> pd.DataFrame:
    """For each customer choose the offer with the highest expected net value.

    `verbose=False` for the ~90 repeated calls made by sensitivity/simulator sweeps,
    which would otherwise drown the pipeline log.
    """
    if df is None:
        df = load_candidates()

    best_name, best_cost, best_net, best_benefit, best_roi = [], [], [], [], []
    for row in df.itertuples():
        cands = []
        for o in OFFERS:
            acc = _acceptance(o, row)
            benefit = row.churn_proba * row.ltv_inr * acc
            cands.append((benefit - o.cost_inr, benefit, o, acc))
        net, benefit, o, acc = max(cands, key=lambda x: x[0])
        best_name.append(o.name); best_cost.append(o.cost_inr)
        best_net.append(round(net, 2)); best_benefit.append(round(benefit, 2))
        best_roi.append(round(benefit / o.cost_inr, 3))

    df = df.assign(offer=best_name, offer_cost_inr=best_cost,
                   offer_benefit_inr=best_benefit, offer_net_inr=best_net,
                   roi_per_rupee=best_roi)
    # Only positive-expected-value customers are ever worth contacting.
    df["eligible"] = df.offer_net_inr > 0

    if verbose:
        logger.info("Offer assignment (%s customers):", f"{len(df):,}")
        summary = (df[df.eligible].groupby("offer")
                   .agg(customers=("customer_id", "size"),
                        avg_churn=("churn_proba", "mean"),
                        avg_ltv=("ltv_inr", "mean"),
                        avg_net=("offer_net_inr", "mean"),
                        total_cost=("offer_cost_inr", "sum"))
                   .round(2))
        logger.info("\n%s", summary.to_string())
        logger.info("eligible (+EV under best offer): %d / %d",
                    df.eligible.sum(), len(df))
    return df


if __name__ == "__main__":
    assign_offers()