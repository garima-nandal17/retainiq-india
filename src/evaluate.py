"""
evaluate.py — RetainIQ India (Day 8)

Evaluation *beyond accuracy* for the calibrated churn engine. Accuracy is a trap
on a 26.5%-churn base (predicting "nobody churns" scores ~73%), so the headline
metrics here are ranking (ROC-AUC, PR-AUC), probability quality (Brier +
reliability curve), and the business-facing decile lift / gains table.

Reuses the deterministic Day-7 pipeline (`model.train()`) so every number
reconciles with `reports/model_metrics.json`. The *operating threshold* is
deliberately NOT fixed here — it is set by the rupee profit curve on Day 9-10.
This module only exposes the precision/recall trade-off across thresholds.

Run:  python src/evaluate.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (confusion_matrix, precision_recall_curve,
                             precision_score, recall_score, f1_score,
                             roc_curve)

import model as M

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | evaluate | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("evaluate")

ROOT = Path(__file__).resolve().parents[1]
FIGDIR = ROOT / "reports" / "figures"
EVAL_PATH = ROOT / "reports" / "evaluation.json"


def _curves(y, p):
    fpr, tpr, _ = roc_curve(y, p)
    prec, rec, _ = precision_recall_curve(y, p)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    ax[0].plot(fpr, tpr, color="#3b6ea5"); ax[0].plot([0, 1], [0, 1], "--", color="grey")
    ax[0].set_title("ROC curve"); ax[0].set_xlabel("FPR"); ax[0].set_ylabel("TPR")
    ax[1].plot(rec, prec, color="#3b6ea5")
    ax[1].axhline(y.mean(), ls="--", color="crimson", label=f"base rate {y.mean():.3f}")
    ax[1].set_title("Precision-Recall curve"); ax[1].set_xlabel("Recall")
    ax[1].set_ylabel("Precision"); ax[1].legend()
    fig.tight_layout(); fig.savefig(FIGDIR / "roc_pr_curves.png", dpi=120); plt.close(fig)


def _calibration(y, p):
    frac_pos, mean_pred = calibration_curve(y, p, n_bins=10, strategy="quantile")
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "--", color="grey", label="perfectly calibrated")
    ax.plot(mean_pred, frac_pos, "o-", color="#3b6ea5", label="calibrated logistic")
    ax.set_title("Reliability curve"); ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed churn fraction"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGDIR / "calibration_curve.png", dpi=120); plt.close(fig)
    # max calibration gap across bins
    return float(np.max(np.abs(frac_pos - mean_pred)))


def _threshold_sweep(y, p):
    rows = []
    for thr in np.round(np.arange(0.1, 0.91, 0.05), 2):
        pred = (p >= thr).astype(int)
        rows.append({"threshold": float(thr),
                     "precision": round(precision_score(y, pred, zero_division=0), 4),
                     "recall": round(recall_score(y, pred, zero_division=0), 4),
                     "f1": round(f1_score(y, pred, zero_division=0), 4)})
    df = pd.DataFrame(rows)
    best = df.loc[df.f1.idxmax()]
    fig, ax = plt.subplots(figsize=(8, 5))
    for c, col in [("precision", "#3b6ea5"), ("recall", "#e08a1e"), ("f1", "#2e8b57")]:
        ax.plot(df.threshold, df[c], "o-", label=c, color=col)
    ax.axvline(best.threshold, ls="--", color="grey",
               label=f"F1-max @ {best.threshold:.2f}")
    ax.set_title("Precision / recall / F1 vs threshold")
    ax.set_xlabel("Decision threshold"); ax.set_ylabel("Score"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGDIR / "threshold_sweep.png", dpi=120); plt.close(fig)
    return df, best


def _decile_lift(y, p):
    """Business gains table: sort by risk, split into deciles, cumulative capture."""
    d = pd.DataFrame({"y": y.values if hasattr(y, "values") else y, "p": p})
    d = d.sort_values("p", ascending=False).reset_index(drop=True)
    d["decile"] = (np.floor(np.arange(len(d)) / (len(d) / 10)).astype(int) + 1).clip(1, 10)
    base = d.y.mean()
    g = (d.groupby("decile")
           .agg(customers=("y", "size"), churners=("y", "sum"),
                churn_rate=("y", "mean")).reset_index())
    g["lift"] = (g.churn_rate / base).round(2)
    g["cum_churners"] = g.churners.cumsum()
    g["cum_capture"] = (g.cum_churners / d.y.sum()).round(3)
    return g, base


def run() -> dict:
    art = M.train()
    y, p = art["y_test"], art["proba_test"]
    FIGDIR.mkdir(parents=True, exist_ok=True)

    cm = confusion_matrix(y, (p >= 0.5).astype(int))
    tn, fp, fn, tp = cm.ravel()
    logger.info("Confusion @0.5: TN=%d FP=%d FN=%d TP=%d", tn, fp, fn, tp)

    _curves(y, p)
    cal_gap = _calibration(y, p)
    logger.info("Max calibration gap across deciles: %.3f", cal_gap)

    sweep, best = _threshold_sweep(y, p)
    logger.info("F1-max threshold = %.2f (P=%.3f R=%.3f F1=%.3f)",
                best.threshold, best.precision, best.recall, best.f1)

    lift, base = _decile_lift(y, p)
    logger.info("Decile lift / cumulative capture:\n%s", lift.to_string(index=False))
    top3 = float(lift.loc[lift.decile <= 3, "churners"].sum() / (y.sum()))
    logger.info("Top-3 deciles (30%% of base) capture %.1f%% of all churners", top3 * 100)

    out = {
        "headline": art["metrics"]["logistic_calibrated"],
        "confusion_at_0.5": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "max_calibration_gap": round(cal_gap, 4),
        "f1_max_threshold": {"threshold": float(best.threshold),
                             "precision": float(best.precision),
                             "recall": float(best.recall), "f1": float(best.f1)},
        "top3_decile_capture": round(top3, 3),
        "decile_lift": lift.to_dict("records"),
        "note": "operating threshold is set by the Day 9-10 profit curve, not F1",
    }
    EVAL_PATH.write_text(json.dumps(out, indent=2))
    logger.info("saved %s + 3 figures", EVAL_PATH.relative_to(ROOT))
    return out


if __name__ == "__main__":
    run()