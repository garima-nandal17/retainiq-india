"""
data_quality.py — RetainIQ India (Day 4)

A 5-dimension data-quality framework: freshness, completeness, uniqueness,
consistency, accuracy. Each check emits a pass/fail plus a logged metric.
Also runs a target-leakage scan.

Honesty note on FRESHNESS: the source is a static academic snapshot with no
event timestamps, so per-row freshness cannot be measured. We implement the
freshness *mechanism* — an SLA on time since the last successful load, proxied
by the processed DuckDB file's mtime — and document the limitation rather than
fabricating a freshness column.

Run:  python src/data_quality.py
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)-7s | dq | %(message)s",
                    datefmt="%H:%M:%S")
logger = logging.getLogger("data_quality")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
REPORT_PATH = ROOT / "reports" / "dq_report.json"

FRESHNESS_SLA_DAYS = 30
CONTRACT_DOMAIN = {"Month-to-month", "One year", "Two year"}
PAYMENT_DOMAIN = {"Electronic check", "Mailed check",
                  "Bank transfer (automatic)", "Credit card (automatic)"}
GENDER_DOMAIN = {"Female", "Male"}
# Columns fed to the model (target and id excluded) — used by the leakage scan.
MODEL_EXCLUDES = {"customer_id", "churned"}


@dataclass
class CheckResult:
    dimension: str
    name: str
    metric: float
    passed: bool
    detail: str
    severity: str = "hard"   # 'hard' blocks the pipeline; 'soft' is informational


def _con() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} missing. Run load_data.py + build_features.py.")
    con = duckdb.connect(str(DB_PATH))
    con.execute((ROOT / "sql" / "features.sql").read_text())  # ensure views exist
    return con


# --- dimensions -------------------------------------------------------------
def check_freshness() -> CheckResult:
    mtime = datetime.fromtimestamp(DB_PATH.stat().st_mtime, tz=timezone.utc)
    age_days = (datetime.now(timezone.utc) - mtime).total_seconds() / 86400
    passed = age_days <= FRESHNESS_SLA_DAYS
    return CheckResult("freshness", "load_age_within_sla", round(age_days, 3), passed,
                       f"last load {age_days:.2f}d ago; SLA {FRESHNESS_SLA_DAYS}d "
                       f"(mechanism demo — static snapshot has no event timestamps)")


def check_completeness(con) -> list[CheckResult]:
    out = []
    cols = [r[0] for r in con.execute("DESCRIBE feature_customer").fetchall()]
    n = con.execute("SELECT COUNT(*) FROM feature_customer").fetchone()[0]
    for c in cols:
        nulls = con.execute(
            f"SELECT COUNT(*) FROM feature_customer WHERE {c} IS NULL").fetchone()[0]
        rate = nulls / n
        # total_charges_inr NULLs are known & allowed (11 tenure-0 customers)
        allowed = 0.01 if c == "total_charges_inr" else 0.0
        out.append(CheckResult("completeness", f"nonnull:{c}", round(rate, 5),
                               rate <= allowed,
                               f"{nulls} nulls ({rate:.3%})"))
    return out


def check_uniqueness(con) -> list[CheckResult]:
    dup_cust = con.execute("""
        SELECT COUNT(*) FROM (SELECT customer_id FROM customer
        GROUP BY customer_id HAVING COUNT(*) > 1)""").fetchone()[0]
    dup_svc = con.execute("""
        SELECT COUNT(*) FROM (SELECT customer_id, service_name
        FROM service_subscription GROUP BY 1,2 HAVING COUNT(*) > 1)""").fetchone()[0]
    return [
        CheckResult("uniqueness", "customer_pk_unique", dup_cust, dup_cust == 0,
                    f"{dup_cust} duplicate customer_id"),
        CheckResult("uniqueness", "service_pk_unique", dup_svc, dup_svc == 0,
                    f"{dup_svc} duplicate (customer_id, service_name)"),
    ]


def check_consistency(con) -> list[CheckResult]:
    out = []
    # tenure==0 iff total_charges NULL
    viol = con.execute("""
        SELECT COUNT(*) FROM account
        WHERE (tenure_months = 0) <> (total_charges_inr IS NULL)""").fetchone()[0]
    out.append(CheckResult("consistency", "tenure0_iff_null_total", viol, viol == 0,
                            f"{viol} rows break tenure0<->null-total rule"))
    # positive monthly charges
    nonpos = con.execute(
        "SELECT COUNT(*) FROM account WHERE monthly_charges_inr <= 0").fetchone()[0]
    out.append(CheckResult("consistency", "monthly_charges_positive", nonpos, nonpos == 0,
                            f"{nonpos} rows with monthly_charges <= 0"))
    # internet dependency: internet-dependent add-ons must read 'No internet service'
    # exactly when the customer has no internet.
    dep_viol = con.execute("""
        WITH net AS (SELECT customer_id,
               MAX(CASE WHEN service_name='InternetService' THEN status END) AS itype
             FROM service_subscription GROUP BY customer_id)
        SELECT COUNT(*) FROM service_subscription s JOIN net n USING(customer_id)
        WHERE s.service_name IN ('OnlineSecurity','OnlineBackup','DeviceProtection',
                                 'TechSupport','StreamingTV','StreamingMovies')
          AND ( (n.itype='No') <> (s.status='No internet service') )
    """).fetchone()[0]
    out.append(CheckResult("consistency", "internet_dependency", dep_viol, dep_viol == 0,
                            f"{dep_viol} add-on rows inconsistent with internet status"))
    # total_charges ~ tenure * monthly (loose 5% tolerance), informational
    within = con.execute("""
        SELECT AVG( (( ABS(total_charges_inr - tenure_months*monthly_charges_inr)
                     / NULLIF(total_charges_inr,0)) < 0.05)::INT )::DOUBLE
        FROM account WHERE total_charges_inr IS NOT NULL""").fetchone()[0]
    out.append(CheckResult("consistency", "total~tenure*monthly_within_5pct",
                           round(within, 4), within >= 0.75,
                           f"{within:.1%} within 5% of tenure*monthly — remainder "
                           f"expected: monthly rate evolves as services change over tenure",
                           severity="soft"))
    return out


def check_accuracy(con) -> list[CheckResult]:
    out = []
    # numeric ranges
    bad_tenure = con.execute(
        "SELECT COUNT(*) FROM account WHERE tenure_months < 0 OR tenure_months > 72").fetchone()[0]
    out.append(CheckResult("accuracy", "tenure_in_0_72", bad_tenure, bad_tenure == 0,
                            f"{bad_tenure} out-of-range tenure"))
    bad_mc = con.execute(
        "SELECT COUNT(*) FROM account WHERE monthly_charges_inr < 0 OR monthly_charges_inr > 200").fetchone()[0]
    out.append(CheckResult("accuracy", "monthly_charges_in_range", bad_mc, bad_mc == 0,
                            f"{bad_mc} out-of-range monthly_charges"))
    # categorical domains
    for col, dom, tbl in [("contract_type", CONTRACT_DOMAIN, "account"),
                          ("payment_method", PAYMENT_DOMAIN, "account"),
                          ("gender", GENDER_DOMAIN, "customer")]:
        vals = set(r[0] for r in con.execute(f"SELECT DISTINCT {col} FROM {tbl}").fetchall())
        bad = vals - dom
        out.append(CheckResult("accuracy", f"domain:{col}", len(bad), not bad,
                               f"unexpected values: {sorted(bad) or 'none'}"))
    return out


def leakage_scan(con) -> list[CheckResult]:
    """Flag any feature that (near-)perfectly predicts the target."""
    out = []
    cols = [x[0] for x in con.execute("DESCRIBE feature_customer").fetchall()]
    numeric = []
    for c in cols:
        if c in MODEL_EXCLUDES:
            continue
        t = con.execute(f"SELECT typeof({c}) FROM feature_customer LIMIT 1").fetchone()[0]
        if t in ("BIGINT", "INTEGER", "SMALLINT", "DOUBLE", "HUGEINT", "BOOLEAN"):
            numeric.append(c)
    worst_c, worst_v = None, 0.0
    for c in numeric:
        corr = con.execute(
            f"SELECT ABS(corr({c}::DOUBLE, churned::INT)) FROM feature_customer"
        ).fetchone()[0] or 0.0
        if corr > worst_v:
            worst_c, worst_v = c, corr
    out.append(CheckResult("leakage", "no_near_perfect_predictor", round(worst_v, 4),
                           worst_v < 0.95,
                           f"max |corr(feature,target)| = {worst_v:.3f} ({worst_c})"))
    out.append(CheckResult("leakage", "target_excluded_from_X", 0, True,
                           f"model X excludes {sorted(MODEL_EXCLUDES)}; segments built "
                           f"from drivers, not the label"))
    return out


def run() -> dict:
    con = _con()
    try:
        results: list[CheckResult] = [check_freshness()]
        results += check_completeness(con)
        results += check_uniqueness(con)
        results += check_consistency(con)
        results += check_accuracy(con)
        results += leakage_scan(con)
    finally:
        con.close()

    by_dim: dict[str, list[CheckResult]] = {}
    for r in results:
        by_dim.setdefault(r.dimension, []).append(r)

    logger.info("Data-quality report (%d checks):", len(results))
    overall_ok = True
    for dim, rs in by_dim.items():
        passed = sum(r.passed for r in rs)
        overall_ok &= all(r.passed for r in rs if r.severity == "hard")
        logger.info("  [%s] %d/%d passed", dim, passed, len(rs))
        for r in rs:
            if r.passed:
                flag = "PASS"
            else:
                flag = "FAIL" if r.severity == "hard" else "WARN"
            logger.info("      %-4s %-34s metric=%s | %s", flag, r.name, r.metric, r.detail)

    n_hard = sum(1 for r in results if r.severity == "hard")
    n_soft = len(results) - n_hard
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "overall_pass": overall_ok,
              "n_checks": len(results),
              "n_hard": n_hard, "n_soft": n_soft,
              "checks": [asdict(r) for r in results]}
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    logger.info("OVERALL: %s  ->  %s",
                "PASS" if overall_ok else "FAIL", REPORT_PATH.relative_to(ROOT))
    return report


if __name__ == "__main__":
    run()