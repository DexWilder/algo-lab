#!/usr/bin/env python3
"""XB-ORB-EMA-Ladder Parameter Sweep — stability-first search.

Goal: understand whether xb_orb_ema_ladder is a robust family or a single
magic setting. Evaluates variants on cross-asset consistency, positive
median trade, low concentration, and parameter-neighborhood stability.

We do NOT rank by PF alone. Ranking is:
  1. Cross-asset consistency (# of profitable assets)
  2. Median trade PnL (positive required)
  3. Top-10 concentration (lower is better)
  4. Parameter-neighborhood stability (PF variance across nearby settings)
  5. Drawdown duration (shorter is better)
  6. PF (secondary tiebreaker only)

Sweep dimensions:
  - stop_mult:    [0.25, 0.5, 0.75, 1.0, 1.5]
  - target_mult:  [2.0, 3.0, 4.0, 5.0, 6.0]
  - trail_mult:   [1.5, 2.0, 2.5, 3.0, 4.0]

Default (baseline): stop=0.5, target=4.0, trail=2.5

Assets tested: MNQ, MES, MGC, M2K (the 4 confirmed cross-assets from validation)
"""

import itertools
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
from research.crossbreeding.crossbreeding_engine import (
    compute_features,
    generate_crossbred_signals,
)

ASSETS = ["MNQ", "MES", "MGC", "M2K"]

# Focused neighborhood sweep around baseline (0.5, 4.0, 2.5)
# 3×3×3 = 27 combos × 4 assets = 108 runs (~30-60 min)
STOP_MULTS = [0.25, 0.5, 1.0]
TARGET_MULTS = [3.0, 4.0, 5.0]
TRAIL_MULTS = [2.0, 2.5, 3.0]

OUTPUT_PATH = ROOT / "research" / "data" / "xb_orb_sweep_results.json"


def concentration_metrics(trades_df):
    """Compute top-N concentration and median trade."""
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
    return float(wins / losses) if losses > 0 else float("inf")


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
    # Find longest stretch
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


def run_variant(asset, stop_mult, target_mult, trail_mult):
    """Run one parameter combination on one asset."""
    cfg = get_asset(asset)
    df = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    params = {
        "stop_mult": stop_mult,
        "target_mult": target_mult,
        "trail_mult": trail_mult,
    }
    signals = generate_crossbred_signals(
        df,
        entry_name="orb_breakout",
        exit_name="profit_ladder",
        filter_name="ema_slope",
        params=params,
    )
    result = run_backtest(
        df, signals, mode="both",
        point_value=cfg["point_value"],
        tick_size=cfg["tick_size"],
        commission_per_side=cfg["commission_per_side"],
        slippage_ticks=cfg["slippage_ticks"],
    )
    trades = result["trades_df"]

    pf = compute_pf(trades)
    pnl = float(trades["pnl"].sum()) if len(trades) else 0
    n = len(trades)
    conc = concentration_metrics(trades)
    dd_days = max_dd_duration_days(trades)

    return {
        "asset": asset,
        "stop_mult": stop_mult,
        "target_mult": target_mult,
        "trail_mult": trail_mult,
        "trades": n,
        "pf": round(pf, 3),
        "pnl": round(pnl, 0),
        "top3": round(conc["top3"] * 100, 1),
        "top10": round(conc["top10"] * 100, 1),
        "median": round(conc["median"], 2),
        "dd_days": dd_days,
    }


def main():
    combos = list(itertools.product(STOP_MULTS, TARGET_MULTS, TRAIL_MULTS))
    total_runs = len(combos) * len(ASSETS)
    print(f"XB-ORB-EMA-Ladder sweep: {len(combos)} combos × {len(ASSETS)} assets = {total_runs} runs")
    print()

    results = []
    start = time.time()
    run_num = 0

    for stop, target, trail in combos:
        variant_results = []
        for asset in ASSETS:
            run_num += 1
            try:
                r = run_variant(asset, stop, target, trail)
                variant_results.append(r)
            except Exception as e:
                print(f"  [{run_num}/{total_runs}] {asset} stop={stop} tgt={target} trail={trail} ERROR: {e}")
                continue

        # Aggregate across assets
        if variant_results:
            profitable_assets = sum(1 for r in variant_results if r["pf"] > 1.0)
            avg_pf = np.mean([r["pf"] for r in variant_results])
            avg_top10 = np.mean([r["top10"] for r in variant_results])
            all_median_positive = all(r["median"] >= 0 for r in variant_results)
            total_trades = sum(r["trades"] for r in variant_results)

            summary = {
                "stop_mult": stop,
                "target_mult": target,
                "trail_mult": trail,
                "assets_profitable": profitable_assets,
                "assets_tested": len(variant_results),
                "avg_pf": round(avg_pf, 3),
                "avg_top10": round(avg_top10, 1),
                "all_median_positive": all_median_positive,
                "total_trades": total_trades,
                "per_asset": variant_results,
            }
            results.append(summary)

            marker = "**" if profitable_assets == 4 and all_median_positive else "  "
            print(f"  {marker}stop={stop:.2f} tgt={target:.1f} trl={trail:.1f} | "
                  f"{profitable_assets}/4 profitable, avg PF {avg_pf:.2f}, "
                  f"top10 {avg_top10:.0f}%, median+ {all_median_positive}, "
                  f"trades {total_trades}")

    elapsed = time.time() - start
    print(f"\nSweep completed in {elapsed/60:.1f} minutes")

    # Save raw results
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved to: {OUTPUT_PATH}")

    # Print stability rankings
    print()
    print("=" * 90)
    print("  TIER 1: ALL-ASSET WINNERS (4/4 profitable, all medians positive)")
    print("=" * 90)
    tier1 = [r for r in results if r["assets_profitable"] == 4 and r["all_median_positive"]]
    tier1.sort(key=lambda r: (r["avg_top10"], -r["avg_pf"]))
    print(f"  {'stop':>5s} {'target':>7s} {'trail':>7s} {'avg_pf':>7s} {'top10%':>7s} {'trades':>8s}")
    for r in tier1[:20]:
        print(f"  {r['stop_mult']:>5.2f} {r['target_mult']:>7.1f} {r['trail_mult']:>7.1f} "
              f"{r['avg_pf']:>7.2f} {r['avg_top10']:>7.1f} {r['total_trades']:>8d}")
    print(f"\n  Tier 1 count: {len(tier1)} / {len(results)} ({len(tier1)/len(results)*100:.0f}%)")

    print()
    print("=" * 90)
    print("  TIER 2: 3/4 assets profitable, medians positive")
    print("=" * 90)
    tier2 = [r for r in results if r["assets_profitable"] == 3 and r["all_median_positive"]]
    tier2.sort(key=lambda r: -r["avg_pf"])
    for r in tier2[:10]:
        print(f"  stop={r['stop_mult']} tgt={r['target_mult']} trl={r['trail_mult']} "
              f"avg_pf={r['avg_pf']} top10={r['avg_top10']}% n={r['total_trades']}")

    # Neighborhood stability check on the baseline (0.5, 4.0, 2.5)
    print()
    print("=" * 90)
    print("  BASELINE NEIGHBORHOOD STABILITY")
    print("=" * 90)
    baseline = next((r for r in results if r["stop_mult"] == 0.5
                     and r["target_mult"] == 4.0 and r["trail_mult"] == 2.5), None)
    if baseline:
        print(f"  Baseline: {baseline['assets_profitable']}/4 profitable, "
              f"avg PF {baseline['avg_pf']}, median+ {baseline['all_median_positive']}")

    return results


if __name__ == "__main__":
    main()
