"""
adoption.py — RetainIQ India (Day 5)

Feature-adoption analysis computed from the service-subscription data:
adoption depth vs churn, and per-service churn lift (with vs without).
Low adoption is treated as a churn *driver* feature, not a growth study.

Run:  python src/adoption.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | adoption | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("adoption")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
FIG = ROOT / "reports" / "figures" / "adoption_depth_churn.png"

ADDONS = ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
          "StreamingTV", "StreamingMovies", "MultipleLines"]


def _con():
    con = duckdb.connect(str(DB_PATH), read_only=True)
    return con


def run() -> dict:
    con = _con()

    # 1) adoption depth vs churn
    depth = con.execute("""
        SELECT services_held,
               COUNT(*) AS customers,
               ROUND(AVG(churned::INT), 3) AS churn_rate
        FROM feature_customer GROUP BY services_held ORDER BY services_held
    """).df()
    logger.info("Adoption depth vs churn:\n%s", depth.to_string(index=False))

    # 2) per-service churn lift (with vs without), for genuine add-ons
    base = con.execute("SELECT AVG(churned::INT) FROM account").fetchone()[0]
    rows = []
    for svc in ADDONS:
        r = con.execute(f"""
            WITH j AS (
              SELECT a.churned::INT AS churned,
                     MAX(CASE WHEN s.service_name='{svc}' THEN s.status END) AS st
              FROM account a JOIN service_subscription s USING(customer_id)
              GROUP BY a.customer_id, a.churned)
            SELECT ROUND(AVG(CASE WHEN st='Yes' THEN churned END),3) AS churn_with,
                   ROUND(AVG(CASE WHEN st<>'Yes' THEN churned END),3) AS churn_without
            FROM j
        """).fetchone()
        with_, without_ = r
        lift = None if with_ is None or without_ in (None, 0) else round(with_/without_, 2)
        rows.append((svc, with_, without_, lift))
    con.close()

    logger.info("Per-service churn (base rate %.3f):", base)
    logger.info("%-18s %10s %12s %6s", "service", "churn_with", "churn_without", "ratio")
    for svc, w, wo, lift in rows:
        logger.info("%-18s %10s %12s %6s", svc, w, wo, lift)

    # 3) plot adoption depth vs churn
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(depth["services_held"], depth["churn_rate"], color="#3b6ea5")
    ax.axhline(base, ls="--", color="crimson", label=f"base rate {base:.2f}")
    ax.set_title("Churn rate by adoption depth (services held)")
    ax.set_xlabel("Services held"); ax.set_ylabel("Churn rate")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(FIG, dpi=120); plt.close(fig)
    logger.info("saved %s", FIG.relative_to(ROOT))

    return {"base_rate": round(base, 4),
            "adoption_depth": depth.to_dict("records"),
            "per_service": [{"service": s, "churn_with": w,
                             "churn_without": wo, "ratio": l}
                            for s, w, wo, l in rows]}


if __name__ == "__main__":
    run()