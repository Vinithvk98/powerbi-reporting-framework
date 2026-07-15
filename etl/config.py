"""Configuration for the reporting framework.

Environment-driven so the same ETL feeds a local SQLite model for the demo
or a PostgreSQL/Azure SQL warehouse that Power BI connects to via DirectQuery
or scheduled refresh.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


@dataclass(frozen=True)
class Settings:
    # Point at Postgres/Azure SQL for a real Power BI source.
    warehouse_dsn: str = os.getenv(
        "BI_WAREHOUSE_DSN", f"sqlite:///{DATA_DIR / 'reporting.db'}"
    )
    default_rows: int = int(os.getenv("BI_ROWS", "250000"))
    seed: int = int(os.getenv("BI_SEED", "7"))


settings = Settings()
