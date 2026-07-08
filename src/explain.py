"""
explain.py — RetainIQ India (Day 8)

Explainability for the interpretable-first churn engine: coefficient reading
(odds ratios) + SHAP. Because the production model is a *calibrated* logistic and
calibration is a monotonic transform of the base logistic's scores, driver
*direction and ranking* are preserved by explaining the underlying logistic —
which is exactly the architecture the calibrated model wraps.

Outputs: SHAP beeswarm + bar (`reports/figures/`), odds-ratio table
(`reports/shap_drivers.json`), and a plain-English driver narrative for Priya.

Run:  python src/explain.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shap
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

import model as M

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | explain | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("explain")

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "reports" / "figures"
DRIVERS_PATH = ROOT / "reports" / "shap_drivers.json"


def _clean(name: str) -> str:
    """Turn 'cat__contract_type_Month-to-month' into 'contract_type = Month-to-month'."""
    n = name.split("__", 1)[-1]
    for col in M.CATEG:
        if n.startswith(col + "_"):
            return f"{col} = {n[len(col) + 1:]}"
    return n


def run() -> dict:
    X, y = M.load_xy()
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=M.SEED)

    pre = M._preprocessor()
    Xtr = pre.fit_transform(X_tr)
    Xte = pre.transform(X_te)
    Xtr = Xtr.toarray() if hasattr(Xtr, "toarray") else np.asarray(Xtr)
    Xte = Xte.toarray() if hasattr(Xte, "toarray") else np.asarray(Xte)
    names = [_clean(n) for n in pre.get_feature_names_out()]

    lr = LogisticRegression(max_iter=1000, random_state=M.SEED).fit(Xtr, y_tr)

    # --- coefficient reading (odds ratios) ---
    coefs = lr.coef_[0]
    order = np.argsort(-np.abs(coefs))
    drivers = [{"feature": names[i], "coef": round(float(coefs[i]), 3),
                "odds_ratio": round(float(np.exp(coefs[i])), 3)} for i in order]
    logger.info("Top drivers by |coef| (odds ratio = multiplicative effect on churn odds):")
    for d in drivers[:10]:
        logger.info("   %-38s coef=%+.3f  OR=%.3f", d["feature"], d["coef"], d["odds_ratio"])

    # --- SHAP ---
    explainer = shap.LinearExplainer(lr, Xtr)
    sv = explainer.shap_values(Xte)
    for kind, fn in [("beeswarm", "shap_summary.png"), ("bar", "shap_bar.png")]:
        plt.figure()
        shap.summary_plot(sv, Xte, feature_names=names, show=False,
                          plot_type=("bar" if kind == "bar" else "dot"), max_display=12)
        FIGDIR.mkdir(parents=True, exist_ok=True)
        plt.tight_layout(); plt.savefig(FIGDIR / fn, dpi=120, bbox_inches="tight"); plt.close()
    mean_abs = np.abs(sv).mean(axis=0)
    shap_rank = [{"feature": names[i], "mean_abs_shap": round(float(mean_abs[i]), 4)}
                 for i in np.argsort(-mean_abs)[:12]]
    logger.info("Top drivers by mean |SHAP|: %s",
                ", ".join(f"{d['feature']}" for d in shap_rank[:6]))

    # --- plain-English narrative for Priya ---
    up = [d for d in drivers if d["coef"] > 0][:5]
    down = [d for d in drivers if d["coef"] < 0][:5]
    narrative = {
        "raises_churn": [f"{d['feature']} (×{d['odds_ratio']:.2f} odds)" for d in up],
        "lowers_churn": [f"{d['feature']} (×{d['odds_ratio']:.2f} odds)" for d in down],
    }
    logger.info("RAISES churn: %s", "; ".join(narrative["raises_churn"]))
    logger.info("LOWERS churn: %s", "; ".join(narrative["lowers_churn"]))

    out = {"coef_drivers": drivers, "shap_top": shap_rank, "narrative": narrative}
    DRIVERS_PATH.write_text(json.dumps(out, indent=2))
    logger.info("saved %s + shap_summary.png + shap_bar.png",
                DRIVERS_PATH.relative_to(ROOT))
    return out


if __name__ == "__main__":
    run()