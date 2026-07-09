"""
sensitivity.py — RetainIQ India (Day 11)

Stress-test the decision against the assumptions it rests on.

The Day-9/10 result is only as good as four declared assumptions: acceptance
rate, offer cost, gross margin, and budget. This module sweeps each one, reports
how net revenue retained responds, and — most importantly — finds the
**break-even acceptance rate** at which the campaign stops being worth running.

Deliverables: one-way sensitivity tables, a tornado chart of assumption
influence, and a two-way (acceptance x offer-cost) grid.

Run:  python src/sensitivity.py
"""
from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import decision_engine as DE
import economics
import optimizer as O
from economics import ECON

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | sensitivity | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("sensitivity")

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "reports" / "figures"
OUT = ROOT / "reports" / "sensitivity.json"


def _net_under(**overrides) -> float:
    """Re-run assignment + optimizer with patched economics. Returns net retained."""
    base = dataclasses.replace(ECON, **{k: v for k, v in overrides.items()
                                        if k != "acceptance_scale"})
    orig = economics.ECON
    try:
        # patch the shared constant everywhere it is read
        economics.ECON = base
        DE.ECON = base
        O.ECON = base
        df = DE.load_candidates()

        # BUGFIX (D-040): ltv_inr is precomputed in the parquet at the BASE margin,
        # so patching ECON.gross_margin alone left the margin sweep flat. LTV is
        # linear in margin, so rescale it explicitly here. Also rescale the derived
        # value columns that depend on it.
        if base.gross_margin != orig.gross_margin:
            k = base.gross_margin / orig.gross_margin
            df = df.assign(ltv_inr=df.ltv_inr * k)

        # acceptance is an offer property; scale it coherently
        scale = overrides.get("acceptance_scale", 1.0)
        offers = [dataclasses.replace(o, base_acceptance=min(o.base_acceptance * scale, 0.95))
                  for o in DE.OFFERS]
        orig_offers = DE.OFFERS
        DE.OFFERS = offers
        try:
            assigned = DE.assign_offers(df, verbose=False)
            sel = O.greedy_roi(assigned, base.budget_inr)
            return float(sel.offer_net_inr.sum())
        finally:
            DE.OFFERS = orig_offers
    finally:
        economics.ECON = orig
        DE.ECON = orig
        O.ECON = orig


def one_way() -> dict:
    baseline = _net_under()
    logger.info("baseline net retained = ₹%.0f", baseline)
    tables = {}

    # acceptance rate (as a multiplicative scale on every offer's acceptance)
    rows = []
    for s in [0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6]:
        rows.append({"acceptance_scale": s,
                     "net_retained_inr": round(_net_under(acceptance_scale=s), 0)})
    tables["acceptance_scale"] = rows
    logger.info("acceptance sweep: %s",
                {r["acceptance_scale"]: r["net_retained_inr"] for r in rows})

    # offer cost multiplier
    rows = []
    for m in [0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        orig_offers = DE.OFFERS
        DE.OFFERS = [dataclasses.replace(o, cost_inr=o.cost_inr * m) for o in orig_offers]
        try:
            df = DE.load_candidates()
            assigned = DE.assign_offers(df, verbose=False)
            sel = O.greedy_roi(assigned, ECON.budget_inr)
            rows.append({"offer_cost_multiplier": m,
                         "net_retained_inr": round(float(sel.offer_net_inr.sum()), 0)})
        finally:
            DE.OFFERS = orig_offers
    tables["offer_cost_multiplier"] = rows
    logger.info("offer-cost sweep: %s",
                {r["offer_cost_multiplier"]: r["net_retained_inr"] for r in rows})

    # gross margin
    rows = [{"gross_margin": g,
             "net_retained_inr": round(_net_under(gross_margin=g), 0)}
            for g in [0.4, 0.5, 0.6, 0.7, 0.8]]
    tables["gross_margin"] = rows
    logger.info("margin sweep: %s", {r["gross_margin"]: r["net_retained_inr"] for r in rows})

    # budget
    rows = [{"budget_inr": b, "net_retained_inr": round(_net_under(budget_inr=b), 0)}
            for b in [25_000, 50_000, 100_000, 150_000, 200_000, 400_000]]
    tables["budget_inr"] = rows
    logger.info("budget sweep: %s", {r["budget_inr"]: r["net_retained_inr"] for r in rows})

    return baseline, tables


def break_even_acceptance() -> float:
    """Lowest acceptance scale at which net retained is still > 0."""
    lo, hi = 0.01, 1.0
    if _net_under(acceptance_scale=lo) > 0:
        return lo
    for _ in range(40):
        mid = (lo + hi) / 2
        if _net_under(acceptance_scale=mid) > 0:
            hi = mid
        else:
            lo = mid
    return hi


def two_way() -> pd.DataFrame:
    scales = [0.4, 0.7, 1.0, 1.3, 1.6]
    mults = [0.5, 1.0, 1.5, 2.0, 3.0]
    grid = np.zeros((len(scales), len(mults)))
    for i, s in enumerate(scales):
        for j, m in enumerate(mults):
            orig_offers = DE.OFFERS
            DE.OFFERS = [dataclasses.replace(o, cost_inr=o.cost_inr * m,
                                             base_acceptance=min(o.base_acceptance * s, 0.95))
                         for o in orig_offers]
            try:
                assigned = DE.assign_offers(DE.load_candidates(), verbose=False)
                sel = O.greedy_roi(assigned, ECON.budget_inr)
                grid[i, j] = float(sel.offer_net_inr.sum())
            finally:
                DE.OFFERS = orig_offers
    df = pd.DataFrame(grid, index=[f"acc x{s}" for s in scales],
                      columns=[f"cost x{m}" for m in mults]).round(0)
    logger.info("two-way grid (net retained ₹):\n%s", df.to_string())
    return df


def tornado(baseline: float, tables: dict) -> None:
    spans = {}
    for k, rows in tables.items():
        vals = [r["net_retained_inr"] for r in rows]
        spans[k] = (min(vals) - baseline, max(vals) - baseline)
    order = sorted(spans, key=lambda k: (spans[k][1] - spans[k][0]))
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, k in enumerate(order):
        lo, hi = spans[k]
        ax.barh(i, hi - lo, left=lo, color="#3b6ea5", alpha=0.85)
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order)
    ax.axvline(0, color="crimson", ls="--")
    ax.set_title("Tornado — swing in net revenue retained around baseline\n(simulation-based)")
    ax.set_xlabel("Δ net retained (₹) vs baseline")
    FIGDIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(FIGDIR / "tornado_sensitivity.png", dpi=120); plt.close(fig)
    logger.info("most influential assumption: %s", order[-1])


def run() -> dict:
    baseline, tables = one_way()
    be = break_even_acceptance()
    logger.info("BREAK-EVEN acceptance scale = %.3f "
                "(i.e. protection-bundle acceptance ≈ %.1f%%)",
                be, be * 0.35 * 100)
    grid = two_way()
    tornado(baseline, tables)

    out = {"baseline_net_inr": round(baseline, 2),
           "one_way": tables,
           "break_even_acceptance_scale": round(be, 3),
           "break_even_protection_acceptance_pct": round(be * 0.35 * 100, 1),
           "two_way_grid": grid.to_dict(),
           "note": "All figures (simulation-based). Acceptance is the most "
                   "load-bearing assumption and is only measurable via the Day-12 A/B test."}
    OUT.write_text(json.dumps(out, indent=2))
    logger.info("saved %s + tornado_sensitivity.png", OUT.relative_to(ROOT))
    return out


if __name__ == "__main__":
    run()