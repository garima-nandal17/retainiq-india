"""
test_data_quality.py — RetainIQ India (Day 4)

Integration test on the real database plus a focused unit test that the leakage
scan actually catches a planted leaky feature.
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import data_quality as dq  # noqa: E402

DB = ROOT / "data" / "processed" / "retainiq.duckdb"
needs_db = pytest.mark.skipif(not DB.exists(),
                              reason="built DB not present; run the pipeline first")


@needs_db
def test_overall_pass_on_real_db():
    report = dq.run()
    assert report["overall_pass"] is True
    # every HARD check must pass; soft checks may warn
    hard = [c for c in report["checks"] if c["severity"] == "hard"]
    assert all(c["passed"] for c in hard)


@needs_db
def test_no_target_leakage():
    con = dq._con()
    try:
        results = dq.leakage_scan(con)
    finally:
        con.close()
    near_perfect = next(r for r in results if r.name == "no_near_perfect_predictor")
    assert near_perfect.passed
    assert near_perfect.metric < 0.95


def test_leakage_scan_flags_planted_leak():
    """If a feature equals the target, the scan must fail."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE feature_customer AS
        SELECT (i)::VARCHAR                       AS customer_id,
               (i % 2 = 0)                        AS churned,
               (i % 2)                            AS leaky_feature,   -- == churned
               random()                           AS benign_feature
        FROM range(1, 201) t(i)
    """)
    results = dq.leakage_scan(con)
    con.close()
    near_perfect = next(r for r in results if r.name == "no_near_perfect_predictor")
    assert near_perfect.passed is False
    assert near_perfect.metric >= 0.95