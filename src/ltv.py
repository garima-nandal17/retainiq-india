"""
ltv.py — RetainIQ India (Day 9)

Attach money to every customer.

LTV (24-month, discounted, margin-adjusted) is built from ARPU and *survival*,
not a naive `ARPU x horizon`. We reuse the Day-5 Kaplan-Meier curves fitted per
contract type, so a month-to-month customer's future months are discounted by
their real probability of still being there:

    LTV_i = sum_{t=1..H}  ARPU_i * margin * S_c(t) / (1 + r)^t

where S_c(t) is the KM retention curve for customer i's contract type c.

Then the decision-relevant quantity:

    value_at_risk_i = P(churn)_i * LTV_i        # expected margin lost if we do nothing
    expected_benefit_i = P(churn)_i * LTV_i * acceptance_rate   # if we contact & they accept
    expected_net_i     = expected_benefit_i - offer_cost

All figures are (simulation-based estimates) — see src/economics.py.

Run:  python src/ltv.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from lifelines import KaplanMeierFitter

import model as M
from economics import ECON

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | ltv | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("ltv")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
MODEL_PATH = ROOT / "models" / "churn_model.pkl"
OUT = ROOT / "data" / "processed" / "customer_value.parquet"
FACTORS_OUT = ROOT / "reports" / "survival_factors.json"

# Raw engineered columns this module needs. It does NOT require churn_probability,
# km_expected_months, or ltv to pre-exist — it GENERATES them (see check_prerequisites).
REQUIRED_FEATURE_COLS = ["customer_id", "monthly_charges_inr", "contract_type",
                         "tenure_months", "customer_value_segment", "risk_segment",
                         "churned"]
REQUIRED_ACCOUNT_COLS = ["tenure_months", "churned", "contract_type"]


class PrerequisiteError(RuntimeError):
    """Raised when an upstream (Day 2-3) artifact is missing."""


def check_prerequisites() -> None:
    """Fail loudly and helpfully if the Day 2-3 foundation isn't built.

    Day 9 is SELF-SUFFICIENT above that line: churn probabilities (Day 7) and
    Kaplan-Meier survival factors (Day 5) are regenerated here from the schema,
    deterministically. They are not read as pre-existing columns.
    """
    if not DB_PATH.exists():
        # NB: don't call relative_to() here — DB_PATH may sit outside ROOT (tests),
        # and an error handler that itself raises is worse than the original error.
        raise PrerequisiteError(
            f"{DB_PATH} missing. Run: python src/load_data.py "
            f"(Day 2) then python src/build_features.py (Day 3).")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        for t in ("account", "feature_customer"):
            if t not in tables:
                raise PrerequisiteError(
                    f"table '{t}' not found in the database. Run src/build_features.py.")
        fcols = {r[0] for r in con.execute("DESCRIBE feature_customer").fetchall()}
        missing = [c for c in REQUIRED_FEATURE_COLS if c not in fcols]
        if missing:
            raise PrerequisiteError(
                f"feature_customer is missing required column(s): {missing}. "
                f"Re-run src/build_features.py (Day 3).")
        acols = {r[0] for r in con.execute("DESCRIBE account").fetchall()}
        missing = [c for c in REQUIRED_ACCOUNT_COLS if c not in acols]
        if missing:
            raise PrerequisiteError(f"account is missing column(s): {missing}.")
    finally:
        con.close()
    logger.info("prerequisites OK — churn probabilities and survival factors "
                "will be generated in-process (they are not stored columns)")


def _survival_factors() -> dict[str, float]:
    """Discounted survival weights sum_t S_c(t)/(1+r)^t, per contract type.

    This IS the Day-5 Kaplan-Meier analysis, refitted here rather than read from a
    stored `km_expected_months` column. Fitting is deterministic, so the result is
    identical every run. Persisted to reports/survival_factors.json for inspection.
    """
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(
        "SELECT tenure_months, churned::INT AS event, contract_type FROM account "
        "ORDER BY customer_id").df()
    con.close()

    factors = {}
    for contract, g in df.groupby("contract_type"):
        km = KaplanMeierFitter().fit(g.tenure_months, g.event)
        s = np.array([float(km.predict(t)) for t in range(1, ECON.horizon_months + 1)])
        disc = np.array([(1 + ECON.monthly_discount_rate) ** -t
                         for t in range(1, ECON.horizon_months + 1)])
        factors[contract] = float((s * disc).sum())
        logger.info("survival-discount factor [%-14s] = %.2f effective months",
                    contract, factors[contract])

    FACTORS_OUT.parent.mkdir(parents=True, exist_ok=True)
    FACTORS_OUT.write_text(json.dumps(
        {"horizon_months": ECON.horizon_months,
         "monthly_discount_rate": ECON.monthly_discount_rate,
         "km_expected_months_by_contract": {k: round(v, 4) for k, v in factors.items()},
         "note": "Discounted expected months alive within the horizon, from the "
                 "Day-5 Kaplan-Meier curve fitted per contract type."},
        indent=2))
    return factors


def _churn_probabilities(X) -> np.ndarray:
    """Day-7 churn probabilities: load the persisted model, else train it.

    Training is deterministic (ORDER BY customer_id + fixed seeds, D-029), so the
    fallback path yields identical probabilities to the persisted artifact.
    """
    if MODEL_PATH.exists():
        try:
            clf = joblib.load(MODEL_PATH)
            logger.info("loaded persisted churn model -> %s", MODEL_PATH.relative_to(ROOT))
            return clf.predict_proba(X)[:, 1]
        except Exception as exc:                     # version skew, corrupt pickle
            logger.warning("could not load %s (%s) — retraining deterministically",
                           MODEL_PATH.name, exc)
    else:
        logger.info("no persisted model at %s — training it now (Day 7)",
                    MODEL_PATH.relative_to(ROOT))
    return M.train()["model"].predict_proba(X)[:, 1]


def build() -> pd.DataFrame:
    """Per-customer LTV + churn probability + expected value, for ALL customers.

    Self-sufficient above the Day 2-3 foundation: it regenerates the Day-5 survival
    factors and Day-7 churn probabilities in-process. Nothing needs to be manually
    added to feature_customer.
    """
    check_prerequisites()

    # Day-7 churn probabilities for the FULL population.
    # M.load_xy() applies ORDER BY customer_id (D-029), and the DuckDB read below
    # uses the same ordering, so the two frames align row-for-row.
    X, _ = M.load_xy()
    proba_all = _churn_probabilities(X)

    con = duckdb.connect(str(DB_PATH), read_only=True)
    base = con.execute("""
        SELECT customer_id, monthly_charges_inr, contract_type, tenure_months,
               customer_value_segment, risk_segment, churned::INT AS churned
        FROM feature_customer ORDER BY customer_id
    """).df()
    con.close()

    if len(base) != len(proba_all):
        raise PrerequisiteError(
            f"row mismatch: feature_customer has {len(base)} rows but the model "
            f"scored {len(proba_all)}. Re-run src/build_features.py.")

    factors = _survival_factors()
    base["churn_probability"] = proba_all              # Day-7 output, generated here
    base["km_expected_months"] = base.contract_type.map(factors)   # Day-5 output
    # back-compat alias used by decision_engine / optimizer / sensitivity
    base["churn_proba"] = base["churn_probability"]
    base["ltv_inr"] = (base.monthly_charges_inr * ECON.gross_margin
                       * base.km_expected_months).round(2)

    base["value_at_risk_inr"] = (base.churn_probability * base.ltv_inr).round(2)
    base["expected_benefit_inr"] = (base.value_at_risk_inr * ECON.acceptance_rate).round(2)
    base["expected_net_inr"] = (base.expected_benefit_inr - ECON.offer_cost_inr).round(2)
    # rupees of expected net per rupee spent — the optimizer's ranking key
    base["roi_per_rupee"] = (base.expected_benefit_inr / ECON.offer_cost_inr).round(3)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    # DuckDB writes parquet natively — avoids a pyarrow/fastparquet dependency.
    _w = duckdb.connect()
    _w.register("cv", base)
    _w.execute(f"COPY (SELECT * FROM cv) TO '{OUT}' (FORMAT PARQUET)")
    _w.close()

    logger.info("LTV built for %s customers -> %s", f"{len(base):,}", OUT.relative_to(ROOT))
    logger.info("mean LTV ₹%.0f | median ₹%.0f | total portfolio ₹%.1f Cr",
                base.ltv_inr.mean(), base.ltv_inr.median(), base.ltv_inr.sum() / 1e7)
    logger.info("total value at risk = ₹%.1f L  (simulation-based)",
                base.value_at_risk_inr.sum() / 1e5)
    logger.info("customers with positive expected_net at ₹%.0f offer: %d / %d",
                ECON.offer_cost_inr, (base.expected_net_inr > 0).sum(), len(base))

    logger.info("LTV by contract:\n%s", base.groupby("contract_type")
                .agg(n=("customer_id", "size"), mean_ltv=("ltv_inr", "mean"),
                     mean_churn=("churn_probability", "mean"),
                     mean_var=("value_at_risk_inr", "mean")).round(2).to_string())
    return base


if __name__ == "__main__":
    build()