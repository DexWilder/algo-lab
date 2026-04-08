#!/usr/bin/env python3
"""XB-ORB-EMA-Ladder Stop Sweep on MCL — validate MCL probation baseline.

The MNQ stop sweep (research/data/xb_orb_stop_sweep_results.json) showed
a broad stability plateau across stop_mult 0.1 to 3.0, with stop=2.0
being the empirical optimum for MNQ by PF and drawdown duration.

We promoted MCL to probation at stop=2.0 (MNQ's optimum), but we never
verified that crude has the same stability plateau or the same optimum.
This sweep answers both questions.

Same methodology, single asset (MCL).
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals

ASSETS = ["MCL"]
STOP_MULTS = [0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]

OUTPUT_PATH = ROOT / "research" / "data" / "xb_orb_mcl_stop_sweep_results.json"


def concentration_metrics(trades_df):
    if trades_df is None or len(trades_df) == 0:
        return {"top3": 0, "top10": 0, "median": 0}
    total_pnl = trades_df["pnl"].sum()
    if total_pnl <= 0:
        return {"top3": 0, "top10": 0, "median": float(trades_df["pnl"].median())}
    sorted_pnl = trades_df["pnl"].sort_values(ascending=False)
    return {
        "top3": float(sorted_pnl.head(3).sum() / total_pnl),
        "top10": float(sorted_pnl.head(10).sum() / total_pnl),
        "median": float(trades_df["pnl"].median()),
    }


def compute_pf(trades_df):
    if trades_df is None or len(trades_df) == 0:
        return 0
    wins = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    losses = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
    return float(wins / losses) if losses > 0 else 99.0


def max_dd_duration_days(trades_df):
    if trades_df is None or len(trades_df) == 0:
        return 0
    trades_df = trades_df.copy()
    trades_df["entry_time"] = pd.to_datetime(trades_df["entry_time"])
    trades_df = trades_df.sort_values("entry_time")
    eq = trades_df["pnl"].cumsum()
    peak = eq.cummax()
    underwater = eq < peak
    if not underwater.any():
        return 0
    max_days = 0
    current_start = None
    for i, uw in enumerate(underwater.values):
        if uw:
            if current_start is None:
                current_start = trades_df["entry_time"].iloc[i]
        else:
            if current_start is not None:
                days = (trades_df["entry_time"].iloc[i] - current_start).days
                max_days = max(max_days, days)
                current_start = None
    if current_start is not None:
        days = (trades_df["entry_time"].iloc[-1] - current_start).days
        max_days = max(max_days, days)
    return max_days


def run_variant(asset, stop_mult):
    cfg = get_asset(asset)
    df = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    params = {"stop_mult": stop_mult, "target_mult": 4.0, "trail_mult": 2.5}
    signals = generate_crossbred_signals(
        df, entry_name="orb_breakout", exit_name="profit_ladder",
        filter_name="ema_slope", params=params,
    )
    result = run_backtest(
        df, signals, mode="both",
        point_value=cfg["point_value"],
        tick_size=cfg["tick_size"],
        commission_per_side=cfg["commission_per_side"],
        slippage_ticks=cfg["slippage_ticks"],
    )
    trades = result["trades_df"]
    conc = concentration_metrics(trades)
    return {
        "asset": asset,
        "stop_mult": stop_mult,
        "trades": len(trades),
        "pf": round(compute_pf(trades), 3),
        "pnl": round(float(trades["pnl"].sum()) if len(trades) else 0, 0),
        "top3": round(conc["top3"] * 100, 1),
        "top10": round(conc["top10"] * 100, 1),
        "median": round(conc["median"], 2),
        "dd_days": max_dd_duration_days(trades),
    }


def main():
    print(f"XB-ORB MCL stop-sweep: {len(STOP_MULTS)} values x 1 asset = {len(STOP_MULTS)} runs")
    print()

    results = []
    start = time.time()
    for stop in STOP_MULTS:
        row_results = []
        for asset in ASSETS:
            try:
                r = run_variant(asset, stop)
                row_results.append(r)
            except Exception as e:
                print(f"  stop={stop} {asset} ERROR: {e}")

        if row_results:
            r = row_results[0]
            print(f"  stop={stop:.2f}: PF {r['pf']:.3f}, PnL ${r['pnl']:.0f}, "
                  f"top10 {r['top10']}%, median ${r['median']:.2f}, DD {r['dd_days']}d, "
                  f"trades {r['trades']}")
            results.append({
                "stop_mult": stop,
                "per_asset": row_results,
                "mcl_pf": r["pf"],
                "mcl_dd_days": r["dd_days"],
                "mcl_pnl": r["pnl"],
                "mcl_top10": r["top10"],
                "mcl_median": r["median"],
            })

    elapsed = time.time() - start
    print(f"\nSweep completed in {elapsed/60:.1f} minutes")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved to: {OUTPUT_PATH}")

    # Plateau analysis
    print()
    print("=" * 90)
    print("  MCL STABILITY PLATEAU ANALYSIS")
    print("=" * 90)
    clean = [r for r in results if r["mcl_pf"] > 1.0 and r["mcl_median"] >= 0]
    print(f"  Clean variants (PF > 1.0 and positive median): {len(clean)}/{len(results)}")
    if clean:
        print(f"  stop_mult range: {min(r['stop_mult'] for r in clean)} to {max(r['stop_mult'] for r in clean)}")
        print(f"  PF range: {min(r['mcl_pf'] for r in clean):.3f} to {max(r['mcl_pf'] for r in clean):.3f}")
        best = max(clean, key=lambda r: r['mcl_pf'])
        print(f"  Best by PF: stop={best['stop_mult']} pf={best['mcl_pf']} dd={best['mcl_dd_days']}d pnl=${best['mcl_pnl']:.0f}")
        best_dd = min(clean, key=lambda r: r['mcl_dd_days'])
        print(f"  Best by DD: stop={best_dd['stop_mult']} pf={best_dd['mcl_pf']} dd={best_dd['mcl_dd_days']}d")
        # Current probation baseline
        baseline = next((r for r in results if r['stop_mult'] == 2.0), None)
        if baseline:
            print(f"  Current baseline (stop=2.0): pf={baseline['mcl_pf']} dd={baseline['mcl_dd_days']}d")


if __name__ == "__main__":
    main()
