"""Synthetic operational source for the reporting model.

Emits a flat transactions table plus small reference tables (accounts,
merchants). A configurable slice is deliberately imperfect — negative-only
accounts, unknown merchant ids, out-of-range dates — so scheduled validation
has real exceptions to surface.
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta

import pandas as pd

from .config import settings

REGIONS = ["London", "Manchester", "Leeds", "Bristol", "Glasgow"]
SEGMENTS = ["Retail", "SME", "Corporate", "Private"]
MERCHANTS = {
    1: ("Amazon", "E-commerce"), 2: ("Tesco", "Groceries"),
    3: ("Shell", "Fuel"), 4: ("Uber", "Transport"),
    5: ("Spotify", "Subscriptions"), 6: ("British Gas", "Utilities"),
    7: ("Netflix", "Subscriptions"), 8: ("Costa", "Food & Drink"),
}


def generate(rows: int = None, seed: int = None) -> dict[str, pd.DataFrame]:
    rows = rows or settings.default_rows
    rng = random.Random(seed or settings.seed)

    accounts = pd.DataFrame([
        {"account_id": f"AC{i:06d}",
         "region": rng.choice(REGIONS),
         "segment": rng.choice(SEGMENTS),
         "opened_on": (date(2018, 1, 1) + timedelta(days=rng.randint(0, 2500))).isoformat()}
        for i in range(1, 5001)
    ])

    merchants = pd.DataFrame([
        {"merchant_id": mid, "merchant_name": name, "category": cat}
        for mid, (name, cat) in MERCHANTS.items()
    ])

    start = date(2024, 1, 1)
    txns = []
    for i in range(1, rows + 1):
        d = start + timedelta(days=rng.randint(0, 364))
        merchant_id = rng.randint(1, len(MERCHANTS))
        row = {
            "transaction_id": f"T{i:09d}",
            "account_id": f"AC{rng.randint(1, 5000):06d}",
            "merchant_id": merchant_id,
            "txn_date": d.isoformat(),
            "amount": round(rng.uniform(1, 900), 2),
            "is_refund": rng.random() < 0.06,
        }
        # ~2% deliberate exceptions for validation to catch.
        if rng.random() < 0.02:
            pick = rng.random()
            if pick < 0.4:
                row["merchant_id"] = 999          # unknown merchant FK
            elif pick < 0.7:
                row["amount"] = -row["amount"]     # negative non-refund
                row["is_refund"] = False
            else:
                row["txn_date"] = "2099-01-01"     # out-of-range date
        txns.append(row)

    return {
        "accounts": accounts,
        "merchants": merchants,
        "transactions": pd.DataFrame(txns),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=settings.default_rows)
    args = p.parse_args()
    data = generate(args.rows)
    print({k: len(v) for k, v in data.items()})


if __name__ == "__main__":
    main()
