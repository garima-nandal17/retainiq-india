"""
test_optimizer.py — RetainIQ India (Day 10)

The optimizer is the thesis, so it gets the strictest tests: budget feasibility,
near-optimality vs a DP bound, dominance over baselines, and +EV-only selection.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import optimizer as O          # noqa: E402
from economics import ECON     # noqa: E402

DB = ROOT / "data" / "processed" / "retainiq.duckdb"
CV = ROOT / "data" / "processed" / "customer_value.parquet"
needs_data = pytest.mark.skipif(not (DB.exists() and CV.exists()),
                                reason="pipeline artifacts not present")


@pytest.fixture(scope="module")
def res():
    return O.run()


@needs_data
def test_budget_never_exceeded(res):
    assert res["results"]["optimizer_roi"]["spend_inr"] <= res["budget_inr"] + 1e-6


@needs_data
def test_greedy_is_near_optimal(res):
    # greedy must be within 1% of the DP knapsack bound
    assert res["greedy_gap_pct"] < 1.0


@needs_data
def test_beats_probability_ranking(res):
    ours = res["results"]["optimizer_roi"]["net_retained_inr"]
    prob = res["results"]["rank_by_probability"]["net_retained_inr"]
    assert ours > prob


@needs_data
def test_beats_contact_everyone(res):
    ours = res["results"]["optimizer_roi"]["net_retained_inr"]
    spray = res["results"]["contact_everyone"]["net_retained_inr"]
    assert ours > spray


@needs_data
def test_only_positive_ev_customers_selected():
    df = O.assign_offers()
    sel = O.greedy_roi(df, ECON.budget_inr)
    assert (sel.offer_net_inr > 0).all()


@needs_data
def test_smaller_budget_never_earns_more(res):
    """Monotonicity: relaxing the budget cannot reduce net retained."""
    small = O.run(budget=50_000.0)["results"]["optimizer_roi"]["net_retained_inr"]
    big = res["results"]["optimizer_roi"]["net_retained_inr"]
    assert big >= small