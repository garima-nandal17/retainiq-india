"""
test_explainability.py — RetainIQ India (Day 8)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import evaluate as E  # noqa: E402
import explain as X    # noqa: E402

DB = ROOT / "data" / "processed" / "retainiq.duckdb"
needs_db = pytest.mark.skipif(not DB.exists(), reason="built DB not present")


@pytest.fixture(scope="module")
def ev():
    return E.run()


@pytest.fixture(scope="module")
def ex():
    return X.run()


@needs_db
def test_evaluation_headline_reconciles(ev):
    # evaluation must report the same calibrated AUC as the model artifact
    assert ev["headline"]["roc_auc"] == 0.8441


@needs_db
def test_calibration_is_reasonable(ev):
    assert ev["max_calibration_gap"] < 0.15


@needs_db
def test_top3_deciles_capture_majority(ev):
    # a usable targeting model concentrates churners in the top deciles
    assert ev["top3_decile_capture"] > 0.5


@needs_db
def test_tenure_is_strongest_driver(ex):
    # tenure should be the largest-magnitude coefficient (matches Day-6 effect size)
    assert "tenure" in ex["coef_drivers"][0]["feature"]


@needs_db
def test_protection_lowers_churn(ex):
    prot = next(d for d in ex["coef_drivers"] if d["feature"] == "protection_count")
    assert prot["coef"] < 0  # protection add-ons reduce churn odds