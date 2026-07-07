"""
model.py — RetainIQ India (Day 7)

The churn PROBABILITY engine. Interpretable-first: a calibrated logistic
regression is the primary model; a random-forest is a challenger for a sanity
ceiling. Full evaluation + SHAP is Day 8; here we train, calibrate, verify a
leakage-free split, and persist.

Why interpretable-first: a retention head must trust *why* a customer is flagged
before spending budget, and the downstream budget optimizer (Day 10) needs
*calibrated* probabilities — a well-ranked but miscalibrated score would mis-size
every rupee decision.

Feature policy (leakage + redundancy control):
  - EXCLUDED: customer_id (id), churned (target).
  - EXCLUDED from the model: the engineered segments/flags that merely re-encode
    a categorical already present (risk_segment, customer_value_segment,
    contract_risk, high_risk_contract, elec_check_flag, family_flag, has_internet,
    fiber_flag, the NTILE/RANK columns). They serve the optimizer/dashboard, not
    the classifier, and would double-count signal.

Run:  python src/model.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import duckdb
import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score,
                             brier_score_loss, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | model | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("model")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
MODEL_PATH = ROOT / "models" / "churn_model.pkl"
METRICS_PATH = ROOT / "reports" / "model_metrics.json"
SEED = 42

NUMERIC = ["tenure_months", "monthly_charges_inr", "total_charges_inr",
           "services_held", "streaming_count", "protection_count",
           "monthly_charge_per_service", "arpu_vs_contract_avg"]
FLAGS = ["senior_citizen", "has_partner", "has_dependents",
         "paperless_billing", "has_phone"]
CATEG = ["contract_type", "payment_method", "internet_type"]
TARGET = "churned"
FEATURES = NUMERIC + FLAGS + CATEG


def load_xy():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(
    f"""
    SELECT {', '.join(FEATURES + [TARGET])}
    FROM feature_customer
    ORDER BY customer_id
    """
).df()
    con.close()
    # leakage guard: identifiers/target must not be in X
    assert "customer_id" not in FEATURES and TARGET not in FEATURES
    for f in FLAGS:
        df[f] = df[f].astype(int)
    X = df[FEATURES]
    y = df[TARGET].astype(int)
    return X, y


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")),
                          ("scale", StandardScaler())]), NUMERIC),
        ("flag", "passthrough", FLAGS),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEG),
    ])


def _metrics(y_true, proba, thr=0.5) -> dict:
    pred = (proba >= thr).astype(int)
    return {
        "roc_auc": round(roc_auc_score(y_true, proba), 4),
        "pr_auc": round(average_precision_score(y_true, proba), 4),
        "brier": round(brier_score_loss(y_true, proba), 4),
        "accuracy": round(accuracy_score(y_true, pred), 4),
        "precision": round(precision_score(y_true, pred), 4),
        "recall": round(recall_score(y_true, pred), 4),
        "f1": round(f1_score(y_true, pred), 4),
    }


def train() -> dict:
    X, y = load_xy()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=SEED)
    logger.info("leakage-free split: train=%d test=%d (stratified, seed=%d)",
                len(X_tr), len(X_te), SEED)

    pre = _preprocessor()

    # primary: logistic regression, then probability calibration (Platt/sigmoid)
    lr = Pipeline([
        ("pre", pre),
        ("clf", LogisticRegression(
            max_iter=1000,
            random_state=SEED
        ))
    ])
    lr.fit(X_tr, y_tr)
    raw_brier = brier_score_loss(y_te, lr.predict_proba(X_te)[:, 1])

    cal = CalibratedClassifierCV(lr, method="sigmoid", cv=5)
    cal.fit(X_tr, y_tr)
    p_lr = cal.predict_proba(X_te)[:, 1]
    m_lr = _metrics(y_te, p_lr)
    logger.info("Logistic (calibrated): %s", m_lr)
    logger.info("Brier raw=%.4f -> calibrated=%.4f", raw_brier, m_lr["brier"])

    # challenger: random forest (ceiling check only)
    rf = Pipeline([("pre", pre),
                   ("clf", RandomForestClassifier(
                       n_estimators=300, max_depth=8, random_state=SEED, n_jobs=-1))])
    rf.fit(X_tr, y_tr)
    m_rf = _metrics(y_te, rf.predict_proba(X_te)[:, 1])
    logger.info("RandomForest (challenger): %s", m_rf)

    # persist the PRIMARY (interpretable, calibrated) model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(cal, MODEL_PATH)
    logger.info("saved primary model -> %s", MODEL_PATH.relative_to(ROOT))

    metrics = {"seed": SEED, "n_train": len(X_tr), "n_test": len(X_te),
               "features": FEATURES, "primary": "logistic_calibrated",
               "logistic_calibrated": m_lr, "logistic_raw_brier": round(raw_brier, 4),
               "random_forest": m_rf}
    METRICS_PATH.parent.mkdir(exist_ok=True)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    return {"model": cal, "metrics": metrics, "X_test": X_te, "y_test": y_te,
            "proba_test": p_lr}


if __name__ == "__main__":
    train()