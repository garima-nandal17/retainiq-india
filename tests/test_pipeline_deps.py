"""
test_pipeline_deps.py — RetainIQ India

Regression guard for a real confusion: `feature_customer` does NOT store
`churn_probability`, `km_expected_months`, or `ltv`. Day 9 regenerates them.
These tests pin that contract so nobody "fixes" it by hand-adding columns.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import ltv as L  # noqa: E402

DB = ROOT / "data" / "processed" / "retainiq.duckdb"
needs_db = pytest.mark.skipif(not DB.exists(), reason="built DB not present")

DERIVED = ["churn_probability", "predicted_churn", "expected_survival_months",
           "km_expected_months", "ltv"]


@needs_db
def test_feature_customer_does_not_store_derived_columns():
    """The feature layer is Day-3 output only; model/survival outputs are NOT in it."""
    con = duckdb.connect(str(DB), read_only=True)
    cols = {r[0] for r in con.execute("DESCRIBE feature_customer").fetchall()}
    con.close()
    assert not (cols & set(DERIVED)), (
        "feature_customer must not store model/survival outputs — Day 9 generates them")


@needs_db
def test_prerequisites_pass_on_current_repo():
    L.check_prerequisites()  # must not raise


@needs_db
def test_ltv_generates_its_own_prerequisites():
    """Day 9 is self-sufficient above the Day 2-3 foundation."""
    df = L.build()
    for c in ["churn_probability", "km_expected_months", "ltv_inr"]:
        assert c in df.columns
    assert df.churn_probability.between(0, 1).all()
    assert (df.km_expected_months > 0).all()


@needs_db
def test_prerequisite_error_is_actionable(tmp_path, monkeypatch):
    """A missing DB must fail loudly with a fix instruction, not a KeyError."""
    monkeypatch.setattr(L, "DB_PATH", tmp_path / "nonexistent.duckdb")
    with pytest.raises(L.PrerequisiteError) as e:
        L.check_prerequisites()
    assert "load_data.py" in str(e.value)


@needs_db
def test_reported_day9_figures_reproduce():
    """Pins the published Day-9 numbers to the actual pipeline."""
    df = L.build()
    assert round(df.ltv_inr.mean()) == 708
    # positive-EV counts at two offer costs (expected_benefit is cost-independent)
    assert int((df.expected_benefit_inr - 120 > 0).sum()) == 1730
    assert int((df.expected_benefit_inr - 500 > 0).sum()) == 0