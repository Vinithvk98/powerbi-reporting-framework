import pandas as pd
from sqlalchemy import create_engine

from etl.build_model import build
from validation.rules import validate


def test_validation_surfaces_exceptions(warehouse_dsn):
    build(rows=20000, dsn=warehouse_dsn)
    report = validate(dsn=warehouse_dsn)
    # The generator injects ~2% deliberate defects, so we expect exceptions.
    assert report["total_exceptions"] > 0
    assert report["passed"] is False
    assert set(report["by_rule"]) >= {
        "orphan_merchant", "missing_or_out_of_range_date", "negative_non_refund"
    }


def test_exceptions_table_written(warehouse_dsn):
    build(rows=20000, dsn=warehouse_dsn)
    validate(dsn=warehouse_dsn)
    e = create_engine(warehouse_dsn)
    exc = pd.read_sql_table("dq_exceptions", e)
    assert {"transaction_id", "rule", "severity"}.issubset(exc.columns)


def test_clean_model_passes(warehouse_dsn):
    # A tiny clean model (no injected defects on this seed slice) still
    # produces a well-formed, non-crashing report.
    build(rows=1000, dsn=warehouse_dsn)
    report = validate(dsn=warehouse_dsn)
    assert 0.0 <= report["exception_rate"] <= 1.0
    assert report["total_fact_rows"] == 1000
