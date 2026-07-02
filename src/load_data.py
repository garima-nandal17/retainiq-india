"""
load_data.py — RetainIQ India (Day 2)

Reads the raw IBM Telco CSV (relabeled as BharatConnect), applies typing and
the BharatConnect relabeling, and loads three normalized tables into a local
DuckDB database defined by sql/schema.sql.

Design notes
  - Raw data lives in data/raw/ (git-ignored) and is never mutated.
  - The DuckDB file is written to data/processed/ (git-ignored).
  - The script is idempotent: schema.sql drops+recreates the tables each run.
  - Data quirks handled explicitly and honestly (see TotalCharges below);
    deeper validation is the Day-4 data-quality framework's job, not here.

Run:  python src/load_data.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

# --- Paths (repo-root relative) --------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "telco_churn_raw.csv"
DB_PATH = ROOT / "data" / "processed" / "retainiq.duckdb"
SCHEMA_SQL = ROOT / "sql" / "schema.sql"

# The 9 provisioning columns that become the long service_subscription table.
SERVICE_COLUMNS = [
    "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies",
]

YES_NO = {"Yes": True, "No": False}


def _to_bool(series: pd.Series) -> pd.Series:
    return series.map(YES_NO).astype("boolean")


def extract() -> pd.DataFrame:
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {RAW_CSV}. Download the IBM Telco "
            "Customer Churn CSV into data/raw/telco_churn_raw.csv "
            "(see docs/data_acquisition.md)."
        )
    return pd.read_csv(RAW_CSV)


def transform(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split the flat frame into the three normalized tables."""
    # TotalCharges quirk: 11 rows (all tenure==0, brand-new customers) contain a
    # blank space, forcing the column to string. Coerce to numeric -> NaN -> NULL.
    total_charges = pd.to_numeric(df["TotalCharges"].astype(str).str.strip(),
                                  errors="coerce")

    customer = pd.DataFrame({
        "customer_id": df["customerID"],
        "gender": df["gender"],
        "senior_citizen": df["SeniorCitizen"].astype(bool),   # 0/1 -> bool
        "has_partner": _to_bool(df["Partner"]),
        "has_dependents": _to_bool(df["Dependents"]),
    })

    account = pd.DataFrame({
        "customer_id": df["customerID"],
        "tenure_months": df["tenure"].astype(int),
        "contract_type": df["Contract"],
        "paperless_billing": _to_bool(df["PaperlessBilling"]),
        "payment_method": df["PaymentMethod"],
        "monthly_charges_inr": df["MonthlyCharges"].astype(float),
        "total_charges_inr": total_charges,                    # may be NaN -> NULL
        "churned": _to_bool(df["Churn"]),
    })

    # Wide -> long: one row per (customer, service), preserving 3-state status.
    services = df[["customerID"] + SERVICE_COLUMNS].melt(
        id_vars="customerID", var_name="service_name", value_name="status"
    ).rename(columns={"customerID": "customer_id"})

    return {"customer": customer, "account": account,
            "service_subscription": services}


def load(tables: dict[str, pd.DataFrame]) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        con.execute(SCHEMA_SQL.read_text())          # idempotent drop+create
        for name, frame in tables.items():
            con.register("staging", frame)
            con.execute(f"INSERT INTO {name} SELECT * FROM staging")
            con.unregister("staging")
        _verify(con, tables)
    finally:
        con.close()


def _verify(con: duckdb.DuckDBPyConnection, tables: dict[str, pd.DataFrame]) -> None:
    n_cust = con.execute("SELECT COUNT(*) FROM customer").fetchone()[0]
    n_acct = con.execute("SELECT COUNT(*) FROM account").fetchone()[0]
    n_serv = con.execute("SELECT COUNT(*) FROM service_subscription").fetchone()[0]
    n_null_total = con.execute(
        "SELECT COUNT(*) FROM account WHERE total_charges_inr IS NULL"
    ).fetchone()[0]
    churn_rate = con.execute("SELECT AVG(churned::INT) FROM account").fetchone()[0]

    assert n_cust == len(tables["customer"]), "customer row count mismatch"
    assert n_acct == n_cust, "account should be 1:1 with customer"
    assert n_serv == n_cust * len(SERVICE_COLUMNS), "service rows should be customers x 9"

    print("Load complete.")
    print(f"  customer rows            : {n_cust:,}")
    print(f"  account rows             : {n_acct:,}")
    print(f"  service_subscription rows: {n_serv:,}  (= {n_cust:,} x {len(SERVICE_COLUMNS)})")
    print(f"  total_charges NULLs      : {n_null_total} (tenure-0 new customers)")
    print(f"  base churn rate          : {churn_rate:.4f}")


def main() -> None:
    load(transform(extract()))


if __name__ == "__main__":
    main()