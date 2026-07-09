"""
test_profit.py — RetainIQ India (Days 9 & 11)

Guards the money layer: LTV construction, the profit curve's shape, and the
simulator's key invariants.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import profit_curve as PC      # noqa: E402
import simulator as S          # noqa: E402
from economics import ECON     # noqa: E402

CV = ROOT / "data" / "processed" / "customer_value.parquet"
needs_data = pytest.mark.skipif(not CV.exists(), reason="customer_value.parquet missing")


@needs_data
def test_ltv_is_positive_and_finite():
    df = PC.load_values()
    assert (df.ltv_inr > 0).all()
    assert df.ltv_inr.notna().all()


@needs_data
def test_value_at_risk_bounded_by_ltv():
    df = PC.load_values()
    # P(churn) <= 1, so value at risk can never exceed LTV
    assert (df.value_at_risk_inr <= df.ltv_inr + 1e-6).all()


@needs_data
def test_contacting_everyone_is_unprofitable():
    """The premise of the whole project: spray-and-pray loses money."""
    res = PC.run()
    assert res["contact_everyone"]["net_retained_inr"] < 0


@needs_data
def test_optimal_threshold_beats_naive_half():
    res = PC.run()
    assert (res["optimal"]["net_retained_inr"]
            >= res["at_threshold_0.5"]["net_retained_inr"])


@needs_data
def test_theoretical_ceiling_beats_any_global_threshold():
    """Break-even depends on LTV, so no single threshold is optimal."""
    res = PC.run()
    assert res["theoretical_ceiling_inr"] > res["optimal"]["net_retained_inr"]


@needs_data
def test_simulator_never_exceeds_budget():
    r = S.simulate(budget=75_000.0)
    assert r["spend_inr"] <= 75_000.0 + 1e-6


@needs_data
def test_simulator_monotonic_in_acceptance():
    lo = S.simulate(acceptance_scale=0.8)["net_retained_inr"]
    hi = S.simulate(acceptance_scale=1.2)["net_retained_inr"]
    assert hi > lo


@needs_data
def test_pessimistic_scenario_recommends_restraint():
    """A trustworthy system knows when NOT to spend."""
    r = S.simulate(**S.SCENARIOS["pessimistic"])
    assert r["n_contacted"] == 0
    assert r["net_retained_inr"] == 0


# --- CLI / offer-cost override (D-049) ---------------------------------------

@needs_data
def test_offer_cost_override_actually_changes_results():
    """Guards a real bug: the flag used to be silently ignored."""
    default = PC.run()
    expensive = PC.run(offer_cost=500.0)
    assert expensive["contact_everyone"]["net_retained_inr"] < \
        default["contact_everyone"]["net_retained_inr"]
    assert expensive["theoretical_ceiling_inr"] < default["theoretical_ceiling_inr"]


@needs_data
def test_no_positive_ev_customers_at_500_offer():
    """The published Day-9 validation: a Rs 500 offer is unprofitable for everyone."""
    res = PC.run(offer_cost=500.0)
    assert res["n_positive_ev_customers"] == 0
    assert res["theoretical_ceiling_inr"] == 0


@needs_data
def test_positive_ev_count_at_default_offer():
    res = PC.run()
    assert res["n_positive_ev_customers"] == 1730


@needs_data
def test_expected_net_never_reads_stale_column():
    """expected_net must respond to the live cost, not the parquet's materialised one."""
    df = PC.load_values()
    cheap = PC.expected_net(df, 100.0).sum()
    dear = PC.expected_net(df, 400.0).sum()
    assert cheap > dear


@needs_data
def test_override_run_does_not_overwrite_artifacts():
    before = PC.OUT.read_text() if PC.OUT.exists() else None
    PC.run(offer_cost=500.0)
    after = PC.OUT.read_text() if PC.OUT.exists() else None
    assert before == after