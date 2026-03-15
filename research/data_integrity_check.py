#!/usr/bin/env python3
"""
FQL Data Integrity Check Module
=================================
Validates backtesting data quality before research runs.

Checks:
  1. Missing bars (expected vs actual)
  2. Price anomalies (extreme spikes, bad prints)
  3. Volume anomalies (zero volume, unrealistic jumps)
  4. Session alignment (bars inside expected trading sessions)
  5. Data coverage (date range, completeness per year)

Usage:
    python3 research/data_integrity_check.py              # Check all assets
    python3 research/data_integrity_check.py MES MGC M2K  # Check specific assets
"""

import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"

ASSETS = {
    "MES": {"file": "MES_5m.csv", "name": "S&P 500 Micro"},
    "MNQ": {"file": "MNQ_5m.csv", "name": "Nasdaq 100 Micro"},
    "MGC": {"file": "MGC_5m.csv", "name": "Gold Micro"},
    "M2K": {"file": "M2K_5m.csv", "name": "Russell 2000 Micro"},
    "MCL": {"file": "MCL_5m.csv", "name": "Crude Oil Micro"},
    "MYM": {"file": "MYM_5m.csv", "name": "Dow Micro"},
    "ES":  {"file": "ES_5m.csv",  "name": "S&P 500"},
    "ZN":  {"file": "ZN_5m.csv",  "name": "10-Year Treasury"},
    "ZB":  {"file": "ZB_5m.csv",  "name": "30-Year Treasury"},
}

# RTH session hours (ET) — 5m bars
RTH_START = "09:30"
RTH_END = "16:00"
BARS_PER_RTH_DAY = 78  # (16:00 - 09:30) / 5min = 78 bars

# Anomaly thresholds
PRICE_SPIKE_THRESHOLD = 0.05   # 5% move in single bar
VOLUME_SPIKE_MULT = 20         # Volume > 20x median
ZERO_VOLUME_WARN = 0.05        # Warn if >5% bars have zero volume


def check_asset(asset: str) -> dict:
    """Run all integrity checks on a single asset."""
    cfg = ASSETS[asset]
    path = DATA_DIR / cfg["file"]

    if not path.exists():
        return {"status": "MISSING", "error": f"File not found: {path}"}

    df = pd.read_csv(path)
    if "datetime" not in df.columns and "timestamp" in df.columns:
        df.rename(columns={"timestamp": "datetime"}, inplace=True)

    df["_dt"] = pd.to_datetime(df["datetime"])
    df["_date"] = df["_dt"].dt.date
    df["_time"] = df["_dt"].dt.strftime("%H:%M")
    df["_year"] = df["_dt"].dt.year

    result = {
        "asset": asset,
        "name": cfg["name"],
        "file": str(path),
        "status": "OK",
        "warnings": [],
        "errors": [],
    }

    # ── 1. Coverage ──────────────────────────────────────────────────────
    n_bars = len(df)
    date_range_start = df["_dt"].min()
    date_range_end = df["_dt"].max()
    n_days = df["_date"].nunique()
    years = sorted(df["_year"].unique())

    result["coverage"] = {
        "total_bars": n_bars,
        "date_range": f"{date_range_start.strftime('%Y-%m-%d')} to {date_range_end.strftime('%Y-%m-%d')}",
        "trading_days": n_days,
        "years": list(int(y) for y in years),
        "years_count": len(years),
    }

    # Bars per year
    bars_per_year = df.groupby("_year").size().to_dict()
    result["coverage"]["bars_per_year"] = {int(k): int(v) for k, v in bars_per_year.items()}

    # ── 2. Missing bars ──────────────────────────────────────────────────
    expected_bars_per_day = BARS_PER_RTH_DAY
    daily_counts = df.groupby("_date").size()
    days_with_few_bars = (daily_counts < expected_bars_per_day * 0.5).sum()
    days_with_too_many = (daily_counts > expected_bars_per_day * 1.5).sum()

    result["missing_bars"] = {
        "avg_bars_per_day": round(float(daily_counts.mean()), 1),
        "min_bars_per_day": int(daily_counts.min()),
        "max_bars_per_day": int(daily_counts.max()),
        "days_with_sparse_bars": int(days_with_few_bars),
        "days_with_excess_bars": int(days_with_too_many),
    }

    if days_with_few_bars > n_days * 0.05:
        result["warnings"].append(f"{days_with_few_bars} days have <50% expected bars ({days_with_few_bars/n_days*100:.1f}%)")
    if days_with_too_many > 0:
        result["warnings"].append(f"{days_with_too_many} days have >150% expected bars (possible non-RTH data)")

    # ── 3. Price anomalies ───────────────────────────────────────────────
    close = df["close"].values
    returns = np.diff(close) / close[:-1]
    spike_count = int(np.sum(np.abs(returns) > PRICE_SPIKE_THRESHOLD))
    max_return = float(np.max(np.abs(returns))) if len(returns) > 0 else 0.0

    # Check for negative/zero prices
    bad_prices = int((df["close"] <= 0).sum() + (df["open"] <= 0).sum())

    # Check for OHLC consistency (high >= low, high >= open/close, low <= open/close)
    ohlc_violations = int(((df["high"] < df["low"]) |
                          (df["high"] < df["open"]) |
                          (df["high"] < df["close"]) |
                          (df["low"] > df["open"]) |
                          (df["low"] > df["close"])).sum())

    result["price_anomalies"] = {
        "spike_count": spike_count,
        "spike_threshold": f"{PRICE_SPIKE_THRESHOLD*100}%",
        "max_single_bar_return": f"{max_return*100:.2f}%",
        "negative_or_zero_prices": bad_prices,
        "ohlc_violations": ohlc_violations,
    }

    if spike_count > 10:
        result["warnings"].append(f"{spike_count} bars with >{PRICE_SPIKE_THRESHOLD*100}% single-bar moves")
    if bad_prices > 0:
        result["errors"].append(f"{bad_prices} bars with negative/zero prices")
    if ohlc_violations > 0:
        result["errors"].append(f"{ohlc_violations} OHLC violations (high < low, etc)")

    # ── 4. Volume anomalies ──────────────────────────────────────────────
    if "volume" in df.columns:
        vol = df["volume"].values
        zero_vol = int((vol == 0).sum())
        zero_vol_pct = zero_vol / n_bars

        vol_nonzero = vol[vol > 0]
        if len(vol_nonzero) > 0:
            median_vol = float(np.median(vol_nonzero))
            vol_spikes = int(np.sum(vol > median_vol * VOLUME_SPIKE_MULT))
        else:
            median_vol = 0
            vol_spikes = 0

        result["volume_anomalies"] = {
            "zero_volume_bars": zero_vol,
            "zero_volume_pct": f"{zero_vol_pct*100:.1f}%",
            "median_volume": round(median_vol, 0),
            "volume_spikes": vol_spikes,
            "volume_spike_threshold": f"{VOLUME_SPIKE_MULT}x median",
        }

        if zero_vol_pct > ZERO_VOLUME_WARN:
            result["warnings"].append(f"{zero_vol_pct*100:.1f}% of bars have zero volume")
    else:
        result["volume_anomalies"] = {"status": "no_volume_column"}
        result["warnings"].append("No volume data available")

    # ── 5. Session alignment ─────────────────────────────────────────────
    rth_mask = (df["_time"] >= RTH_START) & (df["_time"] < RTH_END)
    rth_bars = int(rth_mask.sum())
    non_rth_bars = n_bars - rth_bars

    result["session_alignment"] = {
        "rth_bars": rth_bars,
        "non_rth_bars": non_rth_bars,
        "rth_pct": f"{rth_bars/n_bars*100:.1f}%",
        "session_definition": f"{RTH_START}-{RTH_END} ET",
    }

    if non_rth_bars > n_bars * 0.1:
        result["warnings"].append(f"{non_rth_bars} bars ({non_rth_bars/n_bars*100:.1f}%) outside RTH — may include Globex data")

    # ── Overall status ───────────────────────────────────────────────────
    if result["errors"]:
        result["status"] = "FAIL"
    elif result["warnings"]:
        result["status"] = "WARN"
    else:
        result["status"] = "PASS"

    return result


def main():
    assets_to_check = sys.argv[1:] if len(sys.argv) > 1 else list(ASSETS.keys())

    print("=" * 70)
    print("  FQL DATA INTEGRITY CHECK")
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    all_results = {}
    for asset in assets_to_check:
        if asset not in ASSETS:
            print(f"\n  UNKNOWN ASSET: {asset}")
            continue

        result = check_asset(asset)
        all_results[asset] = result

        status_icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX", "MISSING": "--"}
        icon = status_icon.get(result["status"], "??")

        print(f"\n  [{icon}] {asset} ({result.get('name', '')})")
        print("  " + "-" * 55)

        if result["status"] == "MISSING":
            print(f"    {result['error']}")
            continue

        cov = result["coverage"]
        print(f"    Range:  {cov['date_range']}")
        print(f"    Bars:   {cov['total_bars']:,}  Days: {cov['trading_days']}  Years: {cov['years_count']}")

        mb = result["missing_bars"]
        print(f"    Bars/day: avg={mb['avg_bars_per_day']}  min={mb['min_bars_per_day']}  max={mb['max_bars_per_day']}")

        pa = result["price_anomalies"]
        print(f"    Price: max_return={pa['max_single_bar_return']}  spikes={pa['spike_count']}  OHLC_violations={pa['ohlc_violations']}")

        if "volume" in result["volume_anomalies"]:
            va = result["volume_anomalies"]
            print(f"    Volume: zero={va.get('zero_volume_pct', '?')}  spikes={va.get('volume_spikes', '?')}  median={va.get('median_volume', '?')}")

        if result["warnings"]:
            for w in result["warnings"]:
                print(f"    ⚠ {w}")
        if result["errors"]:
            for e in result["errors"]:
                print(f"    ✗ {e}")

    # Summary
    print(f"\n" + "=" * 70)
    print(f"  SUMMARY")
    print("=" * 70)
    for asset, result in all_results.items():
        status = result.get("status", "?")
        warns = len(result.get("warnings", []))
        errs = len(result.get("errors", []))
        cov = result.get("coverage", {})
        print(f"  {asset:6s}  {status:6s}  {cov.get('total_bars', 0):>8,} bars  "
              f"{cov.get('trading_days', 0):>5} days  "
              f"{cov.get('years_count', 0)} yrs  "
              f"warnings={warns}  errors={errs}")

    print("=" * 70)


if __name__ == "__main__":
    main()
