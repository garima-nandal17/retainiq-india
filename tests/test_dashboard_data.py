"""
test_dashboard_data.py — RetainIQ cockpit (Day 13)

The cockpit is UI-only, so these tests guard the two things a UI can silently get
wrong:

1. **A dead control.** A slider that doesn't change the output is invisible to the
   eye. This is the D-049 lesson (a silently-ignored input is indistinguishable
   from a genuinely insensitive model), applied to the interface.
2. **A mutating dashboard.** Exploring scenarios must never overwrite the canonical
   contact list (D-047).

Plus: every artifact the cockpit binds to must exist and expose the keys it reads.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

REPORTS = ROOT / "reports"
CONTACT_LIST = REPORTS / "contact_list.csv"
needs_reports = pytest.mark.skipif(
    not (REPORTS / "optimizer_result.json").exists(),
    reason="pipeline reports not present")


@needs_reports
def test_every_bound_artifact_exists():
    import json
    required = ["optimizer_result.json", "profit_curve.json", "sensitivity.json",
                "scenarios.json", "evaluation.json", "shap_drivers.json",
                "model_metrics.json", "survival_factors.json", "dq_report.json"]
    for name in required:
        p = REPORTS / name
        assert p.exists(), f"{name} missing — cockpit would fail to render"
        json.loads(p.read_text())          # must be valid JSON
    assert CONTACT_LIST.exists()


@needs_reports
def test_artifacts_expose_the_keys_the_ui_reads():
    import json
    opt = json.loads((REPORTS / "optimizer_result.json").read_text())
    for k in ["budget_inr", "results", "uplift_pct", "budget_utilisation_pct",
              "greedy_gap_pct"]:
        assert k in opt
    assert "optimizer_roi" in opt["results"]
    ev = json.loads((REPORTS / "evaluation.json").read_text())
    for k in ["max_calibration_gap", "top3_decile_capture", "decile_lift",
              "confusion_at_0.5", "f1_max_threshold"]:
        assert k in ev
    sh = json.loads((REPORTS / "shap_drivers.json").read_text())
    assert sh["narrative"]["raises_churn"] and sh["narrative"]["lowers_churn"]


@needs_reports
def test_budget_slider_actually_changes_the_decision():
    """Manipulation check: a dead slider is invisible. Prove the input reaches the model."""
    import simulator
    lo = simulator.simulate(budget=50_000.0)
    hi = simulator.simulate(budget=150_000.0)
    assert lo["net_retained_inr"] != hi["net_retained_inr"]
    assert lo["n_contacted"] != hi["n_contacted"]
    assert hi["net_retained_inr"] > lo["net_retained_inr"]


@needs_reports
def test_acceptance_and_cost_sliders_are_wired():
    import simulator
    base = simulator.simulate()["net_retained_inr"]
    assert simulator.simulate(acceptance_scale=1.4)["net_retained_inr"] > base
    assert simulator.simulate(offer_cost_multiplier=2.0)["net_retained_inr"] < base
    assert simulator.simulate(gross_margin=0.8)["net_retained_inr"] > base


@needs_reports
def test_cockpit_never_mutates_the_contact_list():
    """Scenario exploration must not overwrite the canonical deliverable (D-047)."""
    import simulator
    before = CONTACT_LIST.read_bytes()
    for b in (25_000.0, 75_000.0, 250_000.0):
        simulator.simulate(budget=b)
    assert CONTACT_LIST.read_bytes() == before


@needs_reports
def test_missing_artifact_error_names_the_fix():
    """An empty screen is an invitation to act: the error must say what to run."""
    from app.components import data as D
    with pytest.raises(D.MissingArtifact) as e:
        D._require("does_not_exist.json")
    assert "run_pipeline.py" in str(e.value)


def test_currency_formatting():
    from app.components import data as D
    assert D.inr_exact(63132.68) == "₹63,133"
    assert D.inr_exact(-60009) == "−₹60,009"
    assert D.inr(1_360_000) == "₹13.60 L"
    assert D.inr(0) == "₹0"


# --- v2 cockpit: five pages, telecom vocabulary, honest tier mapping ---------

@needs_reports
def test_five_pages_all_render():
    """Each page is a separate view; none may raise."""
    from streamlit.testing.v1 import AppTest
    pages = ["Executive Dashboard", "Customer Intelligence", "Decision Intelligence",
             "Scenario Simulator", "Executive Brief"]
    for i, p in enumerate(pages):
        at = AppTest.from_file(str(ROOT / "app" / "dashboard.py"),
                               default_timeout=240).run()
        if i:
            at.radio[0].set_value(p).run()
        assert not at.exception, f"{p} raised: {[e.value for e in at.exception]}"


@needs_reports
def test_revenue_bridge_reconciles_with_artifact():
    """Gross recovery − offer cost must equal the stored net retained."""
    import json
    o = json.loads((REPORTS / "optimizer_result.json").read_text())["results"]["optimizer_roi"]
    assert abs((o["expected_benefit_inr"] - o["spend_inr"]) - o["net_retained_inr"]) < 0.01


def test_contract_tier_mapping_is_declared_not_fabricated():
    """No prepaid flag exists in the data; the tier label must be a declared mapping."""
    from app.components import data as D
    assert set(D.CONTRACT_TIER) == {"Month-to-month", "One year", "Two year"}
    assert "declared mapping" in D.TIER_NOTE
    assert "no prepaid flag" in D.TIER_NOTE


@needs_reports
def test_network_profile_is_read_only_and_has_real_fibre():
    from app.components import data as D
    net = D.load_network_profile()
    assert set(net.internet_type.unique()) == {"No", "DSL", "Fiber optic"}
    assert 0.3 < (net.internet_type == "Fiber optic").mean() < 0.6