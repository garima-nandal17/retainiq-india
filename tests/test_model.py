"""
test_model.py — RetainIQ India (Day 7)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import model as M  # noqa: E402

DB = ROOT / "data" / "processed" / "retainiq.duckdb"
needs_db = pytest.mark.skipif(not DB.exists(), reason="built DB not present")


@pytest.fixture(scope="module")
def trained():
    return M.train()


@needs_db
def test_features_exclude_id_and_target():
    assert "customer_id" not in M.FEATURES
    assert M.TARGET not in M.FEATURES


@needs_db
def test_probabilities_are_valid(trained):
    p = trained["proba_test"]
    assert np.all((p >= 0) & (p <= 1))


@needs_db
def test_auc_above_floor(trained):
    assert trained["metrics"]["logistic_calibrated"]["roc_auc"] > 0.78


@needs_db
def test_interpretable_matches_challenger(trained):
    # the whole thesis: logistic should be within ~3 AUC points of the forest
    lr = trained["metrics"]["logistic_calibrated"]["roc_auc"]
    rf = trained["metrics"]["random_forest"]["roc_auc"]
    assert rf - lr < 0.03


@needs_db
def test_reproducible(trained):
    again = M.train()
    assert (again["metrics"]["logistic_calibrated"]["roc_auc"]
            == trained["metrics"]["logistic_calibrated"]["roc_auc"])