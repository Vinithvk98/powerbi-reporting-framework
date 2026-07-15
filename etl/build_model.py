"""Dimensional model builder.

Transforms the flat operational source into a Kimball-style star schema that
Power BI consumes directly: conformed dimensions (date, account, merchant)
around a single transaction fact. A generated date dimension gives Power BI
proper time-intelligence (YTD, MoM, same-period-last-year) without DAX
gymnastics.

The model is written to the warehouse via SQLAlchemy; point ``BI_WAREHOUSE_DSN``
at Postgres/Azure SQL to build the real Power BI source.
"""
from __future__ import annotations

import os

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import settings
from .generate_source import generate


def get_engine(dsn: str | None = None) -> Engine:
    dsn = dsn or os.getenv("BI_WAREHOUSE_DSN", settings.warehouse_dsn)
    return create_engine(dsn, future=True)


def build_dim_date(txns: pd.DataFrame) -> pd.DataFrame:
    # Build a bounded reporting calendar from the dominant (modal) years so
    # dirty outliers (e.g. a stray 2099 date) fall OUTSIDE dim_date and are
    # correctly flagged by validation instead of silently expanding the model.
    dates = pd.to_datetime(txns["txn_date"], errors="coerce").dropna()
    year_counts = dates.dt.year.value_counts()
    dominant = year_counts[year_counts >= 0.01 * len(dates)].index
    lo = pd.Timestamp(year=int(dominant.min()), month=1, day=1)
    hi = pd.Timestamp(year=int(dominant.max()), month=12, day=31)
    rng = pd.date_range(lo, hi, freq="D")
    d = pd.DataFrame({"date": rng})
    d["date_key"] = d["date"].dt.strftime("%Y%m%d").astype(int)
    d["year"] = d["date"].dt.year
    d["quarter"] = d["date"].dt.quarter
    d["month"] = d["date"].dt.month
    d["month_name"] = d["date"].dt.strftime("%b")
    d["day"] = d["date"].dt.day
    d["day_of_week"] = d["date"].dt.day_name()
    d["is_weekend"] = d["date"].dt.dayofweek >= 5
    return d[["date_key", "date", "year", "quarter", "month",
              "month_name", "day", "day_of_week", "is_weekend"]]


def build_dim_account(accounts: pd.DataFrame) -> pd.DataFrame:
    a = accounts.copy()
    a.insert(0, "account_key", range(1, len(a) + 1))
    return a


def build_dim_merchant(merchants: pd.DataFrame) -> pd.DataFrame:
    m = merchants.copy()
    m.insert(0, "merchant_key", range(1, len(m) + 1))
    return m


def build_fact(txns: pd.DataFrame, dim_account: pd.DataFrame,
               dim_merchant: pd.DataFrame) -> pd.DataFrame:
    f = txns.copy()
    f["txn_date"] = pd.to_datetime(f["txn_date"], errors="coerce")
    f["date_key"] = f["txn_date"].dt.strftime("%Y%m%d")
    f["date_key"] = pd.to_numeric(f["date_key"], errors="coerce").astype("Int64")

    f = f.merge(dim_account[["account_key", "account_id"]], on="account_id", how="left")
    f = f.merge(dim_merchant[["merchant_key", "merchant_id"]], on="merchant_id", how="left")

    f["signed_amount"] = f.apply(
        lambda r: -abs(r["amount"]) if r["is_refund"] else r["amount"], axis=1
    )
    return f[["transaction_id", "date_key", "account_key", "merchant_key",
              "amount", "signed_amount", "is_refund"]]


def build(rows: int | None = None, dsn: str | None = None) -> dict[str, int]:
    """Build the full star schema and persist it. Returns row counts."""
    src = generate(rows)
    dim_date = build_dim_date(src["transactions"])
    dim_account = build_dim_account(src["accounts"])
    dim_merchant = build_dim_merchant(src["merchants"])
    fact = build_fact(src["transactions"], dim_account, dim_merchant)

    engine = get_engine(dsn)
    tables = {
        "dim_date": dim_date,
        "dim_account": dim_account,
        "dim_merchant": dim_merchant,
        "fact_transaction": fact,
        "stg_transactions": src["transactions"],  # kept for validation lineage
    }
    for name, df in tables.items():
        df.to_sql(name, engine, if_exists="replace", index=False)
    return {name: len(df) for name, df in tables.items()}
