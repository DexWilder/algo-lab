#!/usr/bin/env python3
"""Incremental data updater — fetches only new bars since last update.

Reads the last timestamp in each processed CSV, fetches new 1m bars
from Databento, resamples to 5m, and appends to the existing file.

Usage:
    python3 scripts/update_daily_data.py           # update all symbols
    python3 scripts/update_daily_data.py --symbol MES   # single symbol
    python3 scripts/update_daily_data.py --cost-only    # check cost only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.databento_loader import (
    get_client, SYMBOLS, DATASET, SCHEMA, STYPE, EASTERN,
    check_cost,
)

PROC_DIR = ROOT / "data" / "processed"
STATE_DIR = ROOT / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_last_timestamp(symbol: str) -> str:
    """Get the last timestamp in the processed CSV."""
    csv_path = PROC_DIR / f"{symbol}_5m.csv"
    if not csv_path.exists():
        return "2024-03-01"

    df = pd.read_csv(csv_path, usecols=["datetime"], nrows=0)
    # Read just the last few lines efficiently
    import subprocess
    result = subprocess.run(
        ["tail", "-1", str(csv_path)],
        capture_output=True, text=True,
    )
    last_line = result.stdout.strip()
    if not last_line:
        return "2024-03-01"

    # Parse first field (datetime)
    last_dt = last_line.split(",")[0]
    return last_dt


def fetch_incremental(client, symbol: str, start_after: str, end: str) -> pd.DataFrame:
    """Fetch new 1m bars after the given timestamp."""
    db_symbol = SYMBOLS[symbol]

    # Start from midnight of the last bar's date to ensure no gaps
    start_dt = pd.Timestamp(start_after)
    fetch_start = (start_dt - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")

    print(f"  Fetching {symbol} from {fetch_start} to {end}...")

    store = client.timeseries.get_range(
        dataset=DATASET,
        start=fetch_start,
        end=end,
        symbols=[db_symbol],
        schema=SCHEMA,
        stype_in=STYPE,
    )
    df = store.to_df()

    if df.empty:
        return pd.DataFrame()

    # Convert to Eastern, strip tz
    df.index = df.index.tz_convert(EASTERN).tz_localize(None)
    df.index.name = "datetime"
    df = df[["open", "high", "low", "close", "volume"]].copy()

    # Fixed-point check
    if df["close"].mean() > 100_000:
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col] / 1e9

    return df


def resample_and_append(symbol: str, df_1m: pd.DataFrame, last_ts: str) -> int:
    """Resample new 1m bars to 5m and append to existing CSV."""
    if df_1m.empty:
        return 0

    # Resample to 5m
    df_5m = df_1m.resample("5min", label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["open"])

    # Filter to only bars AFTER the last existing timestamp
    last_dt = pd.Timestamp(last_ts)
    new_bars = df_5m[df_5m.index > last_dt]

    if new_bars.empty:
        return 0

    # Append to CSV
    csv_path = PROC_DIR / f"{symbol}_5m.csv"
    new_bars.to_csv(csv_path, mode="a", header=False)

    # Update metadata
    meta_path = PROC_DIR / f"{symbol}_5m.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        meta["end_date"] = str(new_bars.index[-1])
        meta["bar_count"] = meta.get("bar_count", 0) + len(new_bars)
        meta["processed_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    return len(new_bars)


def save_update_state(results: dict):
    """Save update state for the forward runner to read."""
    state = {
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbols": results,
    }
    state_path = STATE_DIR / "data_update_state.json"
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    return state_path


def main():
    parser = argparse.ArgumentParser(description="Incremental data update")
    parser.add_argument("--symbol", type=str, choices=list(SYMBOLS.keys()))
    parser.add_argument("--cost-only", action="store_true")
    parser.add_argument("--end", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    symbols = [args.symbol] if args.symbol else list(SYMBOLS.keys())
    end_date = args.end

    print("=" * 60)
    print("  INCREMENTAL DATA UPDATE")
    print("=" * 60)

    # Check what we have
    results = {}
    for sym in symbols:
        last_ts = get_last_timestamp(sym)
        last_date = pd.Timestamp(last_ts).strftime("%Y-%m-%d")
        print(f"\n  {sym}: last bar = {last_ts}")

        if last_date >= end_date:
            print(f"  {sym}: already up to date")
            results[sym] = {"status": "up_to_date", "new_bars": 0, "last_bar": last_ts}
            continue

        results[sym] = {"last_bar": last_ts, "fetch_to": end_date}

    if args.cost_only:
        client = get_client()
        total_cost = 0
        for sym in symbols:
            if results[sym].get("status") == "up_to_date":
                continue
            last_ts = results[sym]["last_bar"]
            last_date = pd.Timestamp(last_ts).strftime("%Y-%m-%d")
            cost = check_cost(client, sym, last_date, end_date)
            total_cost += cost
            print(f"  {sym}: ${cost:.4f}")
        print(f"\n  Total estimated cost: ${total_cost:.4f}")
        return

    # Fetch and append
    client = get_client()
    for sym in symbols:
        if results[sym].get("status") == "up_to_date":
            continue

        last_ts = results[sym]["last_bar"]
        try:
            df_1m = fetch_incremental(client, sym, last_ts, end_date)
            n_new = resample_and_append(sym, df_1m, last_ts)
            new_last = get_last_timestamp(sym)
            results[sym] = {
                "status": "updated",
                "new_bars": n_new,
                "last_bar": new_last,
            }
            print(f"  {sym}: +{n_new} new 5m bars (now through {new_last})")
        except Exception as e:
            results[sym] = {"status": "error", "error": str(e)}
            print(f"  {sym}: ERROR — {e}")

    # Save state
    state_path = save_update_state(results)

    print(f"\n{'='*60}")
    print(f"  Update complete. State saved to: {state_path.relative_to(ROOT)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
