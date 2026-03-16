#!/usr/bin/env python3
"""
Databento CME futures data loader.

Downloads 1m OHLCV from GLBX.MDP3, resamples to 5m, and saves to
data/processed/ in the same format as TradingView exports.

Usage:
    python3 data/databento_loader.py --all --cost-only       # check cost
    python3 data/databento_loader.py --all                    # download all
    python3 data/databento_loader.py --symbol MES             # single symbol
    python3 data/databento_loader.py --all --start 2024-03-01 --end 2026-03-07
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import databento as db
import pandas as pd
from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "databento"
PROC_DIR = DATA_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────
DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
STYPE = "continuous"

SYMBOLS = {
    # Equity Index Micros
    "MES": "MES.c.0",
    "MNQ": "MNQ.c.0",
    "MGC": "MGC.c.0",
    "M2K": "M2K.c.0",
    "MCL": "MCL.c.0",
    # Rates
    "ZN": "ZN.c.0",
    "ZB": "ZB.c.0",
    "ZF": "ZF.c.0",
    # FX
    "6E": "6E.c.0",
    "6J": "6J.c.0",
    "6B": "6B.c.0",
}

DEFAULT_START = "2024-03-01"
DEFAULT_END = "2026-03-07"
EASTERN = "US/Eastern"


def get_client() -> db.Historical:
    load_dotenv(ROOT / ".env")
    key = os.getenv("DATABENTO_API_KEY")
    if not key:
        print("ERROR: DATABENTO_API_KEY not set in .env")
        sys.exit(1)
    return db.Historical(key)


def check_cost(client: db.Historical, symbol_key: str, start: str, end: str) -> float:
    db_symbol = SYMBOLS[symbol_key]
    cost = client.metadata.get_cost(
        dataset=DATASET,
        start=start,
        end=end,
        symbols=[db_symbol],
        schema=SCHEMA,
        stype_in=STYPE,
    )
    return cost


def download_1m(client: db.Historical, symbol_key: str, start: str, end: str) -> pd.DataFrame:
    db_symbol = SYMBOLS[symbol_key]
    print(f"  Downloading {db_symbol} 1m bars [{start} → {end}] ...")

    store = client.timeseries.get_range(
        dataset=DATASET,
        start=start,
        end=end,
        symbols=[db_symbol],
        schema=SCHEMA,
        stype_in=STYPE,
    )
    df = store.to_df()

    # ts_event index is UTC tz-aware — convert to Eastern, then strip tz
    df.index = df.index.tz_convert(EASTERN).tz_localize(None)
    df.index.name = "datetime"

    # Keep only OHLCV columns
    df = df[["open", "high", "low", "close", "volume"]].copy()

    # Sanity check: if mean close > 100K, likely fixed-point encoding
    if df["close"].mean() > 100_000:
        print("  WARNING: Prices appear fixed-point, dividing by 1e9")
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col] / 1e9

    print(f"  Got {len(df):,} 1m bars")
    return df


def resample_5m(df_1m: pd.DataFrame) -> pd.DataFrame:
    df_5m = df_1m.resample("5min", label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["open"])

    print(f"  Resampled to {len(df_5m):,} 5m bars")
    return df_5m


def save(symbol_key: str, df_1m: pd.DataFrame, df_5m: pd.DataFrame) -> None:
    # Save raw 1m (gitignored, re-downloadable)
    raw_path = RAW_DIR / f"{symbol_key}_1m.csv"
    df_1m.to_csv(raw_path)
    print(f"  Saved raw  → {raw_path.relative_to(ROOT)}")

    # Save processed 5m
    csv_path = PROC_DIR / f"{symbol_key}_5m.csv"
    df_5m.to_csv(csv_path)
    print(f"  Saved 5m   → {csv_path.relative_to(ROOT)}")

    # Save metadata JSON
    meta = {
        "dataset_id": f"{symbol_key}_5m",
        "symbol": symbol_key,
        "timeframe": "5m",
        "start_date": str(df_5m.index[0]),
        "end_date": str(df_5m.index[-1]),
        "bar_count": len(df_5m),
        "trading_days": df_5m.index.normalize().nunique(),
        "source": "databento",
        "source_dataset": DATASET,
        "source_schema": SCHEMA,
        "has_volume": True,
        "volume_mean": round(float(df_5m["volume"].mean()), 1),
        "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    json_path = PROC_DIR / f"{symbol_key}_5m.json"
    json_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"  Saved meta → {json_path.relative_to(ROOT)}")


def process_symbol(client: db.Historical, symbol_key: str, start: str, end: str) -> None:
    print(f"\n{'='*50}")
    print(f"Processing {symbol_key}")
    print(f"{'='*50}")

    df_1m = download_1m(client, symbol_key, start, end)
    df_5m = resample_5m(df_1m)
    save(symbol_key, df_1m, df_5m)
    print(f"  Done ✓")


def main():
    parser = argparse.ArgumentParser(description="Download CME futures data from Databento")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Download all symbols")
    group.add_argument("--symbol", type=str, choices=list(SYMBOLS.keys()), help="Download single symbol")
    parser.add_argument("--start", type=str, default=DEFAULT_START, help=f"Start date (default: {DEFAULT_START})")
    parser.add_argument("--end", type=str, default=DEFAULT_END, help=f"End date (default: {DEFAULT_END})")
    parser.add_argument("--cost-only", action="store_true", help="Only show estimated cost, don't download")

    args = parser.parse_args()
    symbols = list(SYMBOLS.keys()) if args.all else [args.symbol]
    client = get_client()

    # Cost check
    total_cost = 0.0
    print(f"\nDate range: {args.start} → {args.end}")
    print(f"Symbols: {', '.join(symbols)}\n")

    for sym in symbols:
        cost = check_cost(client, sym, args.start, args.end)
        total_cost += cost
        print(f"  {sym}: ${cost:.4f}")

    print(f"\n  Total estimated cost: ${total_cost:.4f}")

    if args.cost_only:
        return

    # Confirm if cost > $5
    if total_cost > 5.0:
        resp = input(f"\nCost exceeds $5. Continue? [y/N] ")
        if resp.lower() != "y":
            print("Aborted.")
            return

    # Download and process
    for sym in symbols:
        process_symbol(client, sym, args.start, args.end)

    print(f"\nAll done. Files in {PROC_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
