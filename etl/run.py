"""Build the reporting model then run validation — the nightly refresh job.

This is what a scheduler (cron, Airflow, Azure Data Factory) invokes ahead
of the Power BI scheduled refresh: rebuild the star schema over the latest
transformed data, then validate it and emit an exceptions report.
"""
from __future__ import annotations

import argparse
import json

from .build_model import build
from .config import settings
from validation.rules import validate


def main() -> None:
    p = argparse.ArgumentParser(description="Rebuild model + validate")
    p.add_argument("--rows", type=int, default=settings.default_rows)
    args = p.parse_args()

    counts = build(args.rows)
    print("Model built:")
    for name, n in counts.items():
        print(f"  {name}: {n:,}")

    report = validate()
    print("\nValidation:")
    print(json.dumps(report, indent=2))
    if report["total_exceptions"]:
        print(f"\n{report['total_exceptions']:,} exceptions written to dq_exceptions")


if __name__ == "__main__":
    main()
