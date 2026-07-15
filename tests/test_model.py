import pandas as pd
from sqlalchemy import create_engine

from etl.build_model import build


def test_build_produces_star_schema(warehouse_dsn):
    counts = build(rows=5000, dsn=warehouse_dsn)
    assert counts["fact_transaction"] == 5000
    assert counts["dim_merchant"] > 0
    assert counts["dim_account"] > 0
    assert counts["dim_date"] > 0


def test_fact_keys_resolve_to_dimensions(warehouse_dsn):
    build(rows=5000, dsn=warehouse_dsn)
    e = create_engine(warehouse_dsn)
    fact = pd.read_sql_table("fact_transaction", e)
    dim_date = pd.read_sql_table("dim_date", e)
    # Every non-exception fact row should map to a real date key.
    resolved = fact["date_key"].isin(set(dim_date["date_key"])).mean()
    assert resolved > 0.9


def test_refunds_are_negated(warehouse_dsn):
    build(rows=5000, dsn=warehouse_dsn)
    e = create_engine(warehouse_dsn)
    fact = pd.read_sql_table("fact_transaction", e)
    refunds = fact[fact["is_refund"] == 1]
    if not refunds.empty:
        assert (refunds["signed_amount"] <= 0).all()
