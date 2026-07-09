"""
simulator.py — RetainIQ India (Day 11)

A what-if simulator: change any assumption, get the resulting decision and net
revenue retained. Powers the Day-13 Streamlit cockpit's sliders and gives Priya
named scenarios (pessimistic / base / optimistic) rather than one point estimate.

    simulate(budget=..., acceptance_scale=..., offer_cost_multiplier=..., gross_margin=...)

Returns the contact count, spend, budget utilisation, offer mix, and net retained.
All figures are (simulation-based estimates).

Run:  python src/simulator.py
"""
from __future__ import annotations

import dataclasses
import json
import logging
from pathlib import Path

import pandas as pd

import decision_engine as DE
import economics
import optimizer as O
from economics import ECON, ASSUMPTION_NOTE

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | simulator | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("simulator")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "scenarios.json"

SCENARIOS = {
    "pessimistic": dict(acceptance_scale=0.6, offer_cost_multiplier=1.5, gross_margin=0.50),
    "base":        dict(acceptance_scale=1.0, offer_cost_multiplier=1.0, gross_margin=0.60),
    "optimistic":  dict(acceptance_scale=1.3, offer_cost_multiplier=0.75, gross_margin=0.70),
}


def simulate(budget: float | None = None, acceptance_scale: float = 1.0,
             offer_cost_multiplier: float = 1.0,
             gross_margin: float | None = None) -> dict:
    """Run the full decision chain under patched assumptions. Pure: restores state."""
    budget = ECON.budget_inr if budget is None else budget
    gross_margin = ECON.gross_margin if gross_margin is None else gross_margin

    patched = dataclasses.replace(ECON, budget_inr=budget, gross_margin=gross_margin)
    orig_econ, orig_offers = economics.ECON, DE.OFFERS
    try:
        economics.ECON = DE.ECON = O.ECON = patched
        DE.OFFERS = [dataclasses.replace(
            o, cost_inr=o.cost_inr * offer_cost_multiplier,
            base_acceptance=min(o.base_acceptance * acceptance_scale, 0.95))
            for o in orig_offers]

        df = DE.load_candidates()
        if gross_margin != orig_econ.gross_margin:      # LTV is linear in margin (D-040)
            df = df.assign(ltv_inr=df.ltv_inr * (gross_margin / orig_econ.gross_margin))

        assigned = DE.assign_offers(df, verbose=False)
        sel = O.greedy_roi(assigned, budget)

        spend = float(sel.offer_cost_inr.sum())
        net = float(sel.offer_net_inr.sum())
        mix = (sel.groupby("offer").size().to_dict() if len(sel) else {})
        return {"inputs": {"budget_inr": budget, "acceptance_scale": acceptance_scale,
                           "offer_cost_multiplier": offer_cost_multiplier,
                           "gross_margin": gross_margin},
                "n_contacted": int(len(sel)),
                "spend_inr": round(spend, 2),
                "budget_utilisation_pct": round(100 * spend / budget, 1) if budget else 0.0,
                "net_retained_inr": round(net, 2),
                "cost_per_save_inr": (round(spend / (len(sel) * 0.35), 2) if len(sel) else None),
                "offer_mix": mix}
    finally:
        economics.ECON = DE.ECON = O.ECON = orig_econ
        DE.OFFERS = orig_offers


def run() -> dict:
    out = {"assumption_note": ASSUMPTION_NOTE, "scenarios": {}}
    for name, kw in SCENARIOS.items():
        r = simulate(**kw)
        out["scenarios"][name] = r
        logger.info("%-12s net=₹%9.0f | contacted=%5d | util=%5.1f%% | mix=%s",
                    name, r["net_retained_inr"], r["n_contacted"],
                    r["budget_utilisation_pct"], r["offer_mix"])

    # budget response curve (what the cockpit slider will draw)
    curve = []
    for b in [10_000, 25_000, 50_000, 75_000, 100_000, 150_000, 200_000, 300_000]:
        r = simulate(budget=b)
        curve.append({"budget_inr": b, "net_retained_inr": r["net_retained_inr"],
                      "n_contacted": r["n_contacted"],
                      "budget_utilisation_pct": r["budget_utilisation_pct"]})
    out["budget_response_curve"] = curve
    logger.info("budget response:\n%s", pd.DataFrame(curve).to_string(index=False))

    sat = next((c for c in curve if c["budget_utilisation_pct"] < 99.0), None)
    if sat:
        logger.info("budget saturates near ₹%s — beyond this, extra budget buys nothing "
                    "(no +EV customers left)", f"{sat['budget_inr']:,}")
        out["saturation_budget_inr"] = sat["budget_inr"]

    OUT.write_text(json.dumps(out, indent=2))
    logger.info("saved %s", OUT.relative_to(ROOT))
    return out


if __name__ == "__main__":
    run()