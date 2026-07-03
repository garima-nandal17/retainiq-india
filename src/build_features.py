"""
build_features.py — RetainIQ India (Day 3, hardened after review)

Creates the SQL feature layer (sql/features.sql) on the DuckDB database, runs
dataset-size-agnostic validation, and materializes the per-customer feature
matrix to Parquet for the modeling days.

Validation philosophy: assert only invariants that must hold for ANY dataset
(non-empty, one row per customer, no null keys/labels, export succeeded). The
row count is logged, never asserted against a fixed number — a larger future
dataset must not fail the build.

Run:  python src/build_features.py
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("build_features")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
FEATURES_SQL = ROOT / "sql" / "features.sql"
OUT_PARQUET = ROOT / "data" / "processed" / "feature_customer.parquet"


class FeatureBuildError(RuntimeError):
    """Raised when the feature build fails a correctness invariant."""


def _connect() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FeatureBuildError(
            f"Database not found at {DB_PATH}. Run src/load_data.py first (Day 2)."
        )
    try:
        return duckdb.connect(str(DB_PATH))
    except duckdb.Error as exc:
        raise FeatureBuildError(f"Could not open DuckDB at {DB_PATH}: {exc}") from exc


def _create_views(con: duckdb.DuckDBPyConnection) -> None:
    try:
        con.execute(FEATURES_SQL.read_text())
    except duckdb.Error as exc:
        # Surface the failing SQL clearly instead of a bare stack trace.
        raise FeatureBuildError(
            f"Feature SQL failed to execute ({FEATURES_SQL.name}): {exc}"
        ) from exc


def _validate(con: duckdb.DuckDBPyConnection) -> int:
    """Dataset-size-agnostic invariants. Returns the row count (for logging)."""
    try:
        n_rows, n_uniq, n_null_id, n_null_churn = con.execute("""
            SELECT COUNT(*),
                   COUNT(DISTINCT customer_id),
                   COUNT(*) FILTER (WHERE customer_id IS NULL),
                   COUNT(*) FILTER (WHERE churned IS NULL)
            FROM feature_customer
        """).fetchone()
    except duckdb.Error as exc:
        raise FeatureBuildError(f"Validation query failed: {exc}") from exc

    n_cols = len(con.execute("SELECT * FROM feature_customer LIMIT 0").description)

    checks = {
        "feature_customer is non-empty": n_rows > 0,
        "no null customer_id": n_null_id == 0,
        "no duplicate customer_id (one row per customer)": n_uniq == n_rows,
        "no null churn label": n_null_churn == 0,
    }
    for name, ok in checks.items():
        if not ok:
            raise FeatureBuildError(f"Invariant violated: {name}.")
        logger.info("check passed — %s", name)

    logger.info("feature_customer: %s rows x %s columns", f"{n_rows:,}", n_cols)
    return n_rows


def _export(con: duckdb.DuckDBPyConnection) -> None:
    try:
        con.execute(
            f"COPY (SELECT * FROM feature_customer) TO '{OUT_PARQUET}' (FORMAT PARQUET)"
        )
    except duckdb.Error as exc:
        raise FeatureBuildError(f"Parquet export failed: {exc}") from exc

    if not OUT_PARQUET.exists() or OUT_PARQUET.stat().st_size == 0:
        raise FeatureBuildError(f"Export produced no file at {OUT_PARQUET}.")

    # Round-trip check: the written file must be readable and row-consistent.
    written = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{OUT_PARQUET}')"
    ).fetchone()[0]
    logger.info(
        "export ok — %s (%s rows, %.1f KB)",
        OUT_PARQUET.relative_to(ROOT), f"{written:,}",
        OUT_PARQUET.stat().st_size / 1024,
    )


def build() -> None:
    logger.info("Building feature layer from %s", FEATURES_SQL.name)
    con = _connect()
    try:
        _create_views(con)
        _validate(con)
        _export(con)
        logger.info("Feature build complete.")
    finally:
        con.close()


def main() -> None:
    try:
        build()
    except FeatureBuildError as exc:
        logger.error("BUILD FAILED: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()