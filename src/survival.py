"""
survival.py — RetainIQ India (Day 5)

Kaplan-Meier retention (survival) curves for BharatConnect customers, overall
and by contract type, plus a log-rank test across contracts.

Survival framing:
  duration T = tenure_months
  event    E = churned  (1 = churn observed; 0 = censored / still active)

This complements the classifier: a churn model says *who*; survival says *when*,
which drives intervention urgency and expected value (Day 9-10).

Run:  python src/survival.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
from lifelines.statistics import multivariate_logrank_test

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | survival | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("survival")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
FIG = ROOT / "reports" / "figures" / "km_by_contract.png"
HORIZONS = [12, 24, 48, 72]


def _load():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute("""
        SELECT tenure_months, churned::INT AS event, contract_type
        FROM account
    """).df()
    con.close()
    return df


def _at(kmf: KaplanMeierFitter, t: int) -> float:
    return float(kmf.predict(t))


def run() -> dict:
    df = _load()
    kmf = KaplanMeierFitter()

    # overall
    kmf.fit(df["tenure_months"], df["event"], label="All customers")
    overall = {f"S({h})": round(_at(kmf, h), 3) for h in HORIZONS}
    overall["median"] = kmf.median_survival_time_
    logger.info("Overall retention: %s | median=%s", overall,
                overall["median"])

    # by contract + plot
    fig, ax = plt.subplots(figsize=(8, 5))
    by_contract = {}
    for contract, grp in df.groupby("contract_type"):
        k = KaplanMeierFitter()
        k.fit(grp["tenure_months"], grp["event"], label=contract)
        k.plot_survival_function(ax=ax, ci_show=False)
        med = k.median_survival_time_
        by_contract[contract] = {
            **{f"S({h})": round(_at(k, h), 3) for h in HORIZONS},
            "median": (None if med != med or med == float("inf") else float(med)),
            "median_note": ("undefined — retention never drops below 50% "
                            "within the 72-month window"
                            if med == float("inf") else "months"),
            "n": int(len(grp)),
        }
        logger.info("[%s] n=%d S(12)=%.3f S(48)=%.3f median=%s",
                    contract, len(grp), _at(k, 12), _at(k, 48), med)

    ax.set_title("BharatConnect retention (Kaplan-Meier) by contract type")
    ax.set_xlabel("Tenure (months)"); ax.set_ylabel("Retention probability S(t)")
    ax.set_ylim(0, 1); ax.grid(alpha=0.3)
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(FIG, dpi=120); plt.close(fig)
    logger.info("saved %s", FIG.relative_to(ROOT))

    # log-rank across contracts
    lr = multivariate_logrank_test(df["tenure_months"], df["contract_type"], df["event"])
    logger.info("log-rank across contracts: chi2=%.1f  p=%.2e",
                lr.test_statistic, lr.p_value)

    return {"overall": overall, "by_contract": by_contract,
            "logrank_chi2": round(float(lr.test_statistic), 1),
            "logrank_p": float(lr.p_value)}


if __name__ == "__main__":
    run()