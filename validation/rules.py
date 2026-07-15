"""Scheduled validation rules.

Runs after each model rebuild and before the Power BI refresh. Each rule is
a small function that returns the offending fact rows tagged with a rule
name and severity. All exceptions are written to ``dq_exceptions`` so a
Power BI "Data Quality" page can chart them over time, and the summary is
returned for alerting.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import pandas as pd
from sqlalchemy.engine import Engine

from etl.build_model import get_engine


@dataclass
class Rule:
    name: str
    severity: str
    description: str
    fn: Callable[[dict[str, pd.DataFrame]], pd.DataFrame]


def _load(engine: Engine) -> dict[str, pd.DataFrame]:
    return {
        t: pd.read_sql_table(t, engine)
        for t in ["fact_transaction", "dim_account", "dim_merchant", "dim_date"]
    }


# --- individual rules -------------------------------------------------------

def _orphan_merchant(t):
    f = t["fact_transaction"]
    return f[f["merchant_key"].isna()][["transaction_id"]]


def _orphan_account(t):
    f = t["fact_transaction"]
    return f[f["account_key"].isna()][["transaction_id"]]


def _missing_date(t):
    f = t["fact_transaction"]
    valid = set(t["dim_date"]["date_key"])
    bad = f[f["date_key"].isna() | ~f["date_key"].isin(valid)]
    return bad[["transaction_id"]]


def _negative_non_refund(t):
    f = t["fact_transaction"]
    return f[(f["signed_amount"] < 0) & (~f["is_refund"].astype(bool))][["transaction_id"]]


RULES = [
    Rule("orphan_merchant", "error", "fact row with no matching merchant dimension", _orphan_merchant),
    Rule("orphan_account", "error", "fact row with no matching account dimension", _orphan_account),
    Rule("missing_or_out_of_range_date", "error", "date_key absent from dim_date", _missing_date),
    Rule("negative_non_refund", "warning", "negative amount not flagged as a refund", _negative_non_refund),
]


def validate(dsn: str | None = None) -> dict:
    engine = get_engine(dsn)
    tables = _load(engine)
    frames = []
    per_rule = {}
    for rule in RULES:
        hits = rule.fn(tables)
        per_rule[rule.name] = len(hits)
        if not hits.empty:
            frames.append(hits.assign(
                rule=rule.name, severity=rule.severity,
                detected_at=datetime.now(timezone.utc).isoformat(),
            ))

    exceptions = (pd.concat(frames, ignore_index=True) if frames
                  else pd.DataFrame(columns=["transaction_id", "rule",
                                             "severity", "detected_at"]))
    exceptions.to_sql("dq_exceptions", engine, if_exists="replace", index=False)

    total_rows = len(tables["fact_transaction"])
    total_exc = int(exceptions.shape[0])
    return {
        "total_fact_rows": total_rows,
        "total_exceptions": total_exc,
        "exception_rate": round(total_exc / total_rows, 4) if total_rows else 0.0,
        "by_rule": per_rule,
        "passed": total_exc == 0,
    }
