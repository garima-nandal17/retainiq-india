"""
profit_curve.py — RetainIQ India (Day 9)

The rupee-denominated profit curve: for every possible contact threshold, what is
the net revenue retained if we contact everyone above it?

    contacted(t)   = customers with churn_proba >= t
    benefit        = sum over contacted of  P(churn) * LTV * acceptance_rate
    cost           = n_contacted * offer_cost
    net_retained   = benefit - cost

This converts a probability ranking into money and exposes the **cost-sensitive
threshold** — the profit-maximising cut-off, which is emphatically NOT 0.5.

All figures are (simulation-based estimates); assumptions live in economics.py.

Run:  python src/profit_curve.py
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from economics import ECON, ASSUMPTION_NOTE

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | profit | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("profit_curve")

ROOT = Path(__file__).resolve().parents[1]
CV = ROOT / "data" / "processed" / "customer_value.parquet"
FIG = ROOT / "reports" / "figures" / "profit_curve.png"
OUT = ROOT / "reports" / "profit_curve.json"


def load_values() -> pd.DataFrame:
    if not CV.exists():
        raise FileNotFoundError(f"{CV} missing — run src/ltv.py first.")
    return duckdb.connect().execute(f"SELECT * FROM read_parquet('{CV}')").df()


def expected_net(df: pd.DataFrame, offer_cost: float | None = None) -> pd.Series:
    """Expected net value per customer AT THE CURRENT offer cost.

    BUGFIX (D-049): never read the parquet's `expected_net_inr` column here. It was
    materialised by ltv.py at *that run's* offer cost, so any override (CLI flag,
    sensitivity sweep, cockpit slider) would be silently ignored — the same failure
    class as the flat margin sweep (D-040). `expected_benefit_inr` is genuinely
    cost-independent, so we subtract the live cost from it instead.
    """
    cost = ECON.offer_cost_inr if offer_cost is None else offer_cost
    return df.expected_benefit_inr - cost


def curve(df: pd.DataFrame, thresholds=None, offer_cost: float | None = None) -> pd.DataFrame:
    cost = ECON.offer_cost_inr if offer_cost is None else offer_cost
    if thresholds is None:
        thresholds = np.round(np.arange(0.00, 1.001, 0.01), 2)
    rows = []
    for t in thresholds:
        sel = df[df.churn_proba >= t]
        n = len(sel)
        benefit = float(sel.expected_benefit_inr.sum())
        total_cost = n * cost
        rows.append({"threshold": float(t), "n_contacted": int(n),
                     "benefit_inr": round(benefit, 2),
                     "cost_inr": round(total_cost, 2),
                     "net_retained_inr": round(benefit - total_cost, 2)})
    return pd.DataFrame(rows)


def run(offer_cost: float | None = None, persist: bool | None = None) -> dict:
    cost = ECON.offer_cost_inr if offer_cost is None else float(offer_cost)
    # Only the canonical cost writes artifacts (same guard as the optimizer, D-047).
    is_canonical = abs(cost - ECON.offer_cost_inr) < 1e-9
    persist = is_canonical if persist is None else persist

    df = load_values()
    c = curve(df, offer_cost=cost)
    logger.info("offer cost in force: ₹%.0f%s", cost,
                "" if is_canonical else "  (override — artifacts not written)")

    best = c.loc[c.net_retained_inr.idxmax()]
    contact_all = c.iloc[0]           # threshold 0.00 -> spray
    # recomputed at the live cost, never read from the stale parquet column (D-049)
    net_i = expected_net(df, cost)
    n_positive = int((net_i > 0).sum())
    theoretical = float(net_i[net_i > 0].sum())

    logger.info("Contact-everyone baseline: n=%d net=₹%.0f",
                contact_all.n_contacted, contact_all.net_retained_inr)
    logger.info("PROFIT-MAXIMISING threshold = %.2f | contact %d | net ₹%.0f",
                best.threshold, best.n_contacted, best.net_retained_inr)
    logger.info("positive-EV customers at ₹%.0f offer: %d / %d", cost, n_positive, len(df))
    logger.info("Theoretical ceiling (contact every +EV customer): ₹%.0f", theoretical)
    denom = abs(contact_all.net_retained_inr)
    uplift = (((best.net_retained_inr - contact_all.net_retained_inr) / denom * 100)
              if denom else 0.0)
    logger.info("Uplift vs contact-everyone: %+.1f%%  (simulation-based)", uplift)

    # naive 0.5 threshold, for the "why not 0.5?" interview answer
    at_half = c[c.threshold == 0.50].iloc[0]
    logger.info("At the naive 0.50 cut: contact %d | net ₹%.0f (leaves ₹%.0f on the table)",
                at_half.n_contacted, at_half.net_retained_inr,
                best.net_retained_inr - at_half.net_retained_inr)

    # plot
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(c.threshold, c.net_retained_inr, color="#3b6ea5", lw=2, label="Net revenue retained")
    ax.axvline(best.threshold, ls="--", color="#2e8b57",
               label=f"profit-max threshold {best.threshold:.2f}")
    ax.axvline(0.5, ls=":", color="crimson", label="naive 0.50")
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_title("Rupee profit curve — net revenue retained vs contact threshold\n(simulation-based)")
    ax.set_xlabel("Contact threshold (churn probability)")
    ax.set_ylabel("Net revenue retained (₹)")
    ax.legend(); ax.grid(alpha=0.3)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(FIG, dpi=120); plt.close(fig)

    out = {
        "assumptions": {**ECON.as_dict(), "offer_cost_inr": cost},
        "offer_cost_override": (None if is_canonical else cost),
        "n_positive_ev_customers": n_positive,
        "assumption_note": ASSUMPTION_NOTE,
        "optimal_threshold": float(best.threshold),
        "optimal": {"n_contacted": int(best.n_contacted),
                    "benefit_inr": float(best.benefit_inr),
                    "cost_inr": float(best.cost_inr),
                    "net_retained_inr": float(best.net_retained_inr)},
        "contact_everyone": {"n_contacted": int(contact_all.n_contacted),
                             "net_retained_inr": float(contact_all.net_retained_inr)},
        "at_threshold_0.5": {"n_contacted": int(at_half.n_contacted),
                             "net_retained_inr": float(at_half.net_retained_inr)},
        "theoretical_ceiling_inr": round(theoretical, 2),
        "uplift_vs_contact_everyone_pct": round(float(uplift), 1),
        "curve": c.to_dict("records"),
    }
    if persist:
        OUT.write_text(json.dumps(out, indent=2))
        logger.info("saved %s + %s", OUT.relative_to(ROOT), FIG.relative_to(ROOT))
    else:
        logger.info("override run — %s not overwritten", OUT.name)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Rupee profit curve. Override the offer-cost assumption to "
                    "stress the decision (e.g. --offer-cost 500).")
    ap.add_argument("--offer-cost", type=float, default=None, metavar="INR",
                    help=f"offer cost in rupees (default: {ECON.offer_cost_inr:.0f} "
                         f"from src/economics.py)")
    ap.add_argument("--persist", action="store_true",
                    help="write artifacts even for an override run")
    args = ap.parse_args()   # unknown flags now ERROR instead of being ignored
    run(offer_cost=args.offer_cost, persist=(True if args.persist else None))


if __name__ == "__main__":
    main()