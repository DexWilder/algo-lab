#!/usr/bin/env python3
"""XB-ORB-EMA-Ladder Stop-Only Sweep — find the true stability plateau.

After discovering that target_mult and trail_mult are ignored by
exit_profit_ladder (it uses fixed 1R/2R/3R ratchets), the only tunable
parameter is stop_mult. This sweep tests a wider range.

stop_mult affects:
  1. Initial stop distance at entry (wider stop = more room, fewer stops)
  2. Initial_risk (wider stop = bigger R unit, later ratchet triggers)

Range: 0.1 to 3.0 (fine-grained around the baseline)
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

ASSETS = ["MNQ", "MES", "MGC", "M2K"]
STOP_MULTS = [0.1, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]

OUTPUT_PATH = ROOT / "research" / "data" / "xb_orb_stop_sweep_results.json"


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
    print(f"XB-ORB stop-sweep: {len(STOP_MULTS)} values × {len(ASSETS)} assets = {len(STOP_MULTS)*len(ASSETS)} runs")
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
            profitable = sum(1 for r in row_results if r["pf"] > 1.0)
            avg_pf = np.mean([r["pf"] for r in row_results])
            total_trades = sum(r["trades"] for r in row_results)
            avg_dd = np.mean([r["dd_days"] for r in row_results])
            all_med_pos = all(r["median"] >= 0 for r in row_results)

            print(f"  stop={stop:.2f}: {profitable}/4 profitable, avg PF {avg_pf:.3f}, "
                  f"avg DD {avg_dd:.0f}d, trades {total_trades}, med+ {all_med_pos}")
            # Per-asset detail
            for r in row_results:
                print(f"      {r['asset']}: PF={r['pf']} pnl=${r['pnl']:.0f} "
                      f"top10={r['top10']}% med=${r['median']:.2f} dd={r['dd_days']}d")

            results.append({
                "stop_mult": stop,
                "profitable_count": profitable,
                "avg_pf": round(avg_pf, 3),
                "avg_dd_days": round(avg_dd, 0),
                "total_trades": total_trades,
                "all_median_positive": all_med_pos,
                "per_asset": row_results,
            })

    elapsed = time.time() - start
    print(f"\nSweep completed in {elapsed/60:.1f} minutes")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved to: {OUTPUT_PATH}")

    # Stability analysis
    print()
    print("=" * 90)
    print("  STABILITY PLATEAU ANALYSIS")
    print("=" * 90)
    clean = [r for r in results if r["profitable_count"] == 4 and r["all_median_positive"]]
    if clean:
        print(f"  Clean variants (4/4 profitable, all medians positive): {len(clean)}/{len(results)}")
        print(f"  stop_mult range: {min(r['stop_mult'] for r in clean)} to {max(r['stop_mult'] for r in clean)}")
        print(f"  avg PF range: {min(r['avg_pf'] for r in clean):.3f} to {max(r['avg_pf'] for r in clean):.3f}")
        best = max(clean, key=lambda r: r['avg_pf'])
        print(f"  Best by PF: stop={best['stop_mult']} avg_pf={best['avg_pf']} avg_dd={best['avg_dd_days']}d")
        best_dd = min(clean, key=lambda r: r['avg_dd_days'])
        print(f"  Best by DD: stop={best_dd['stop_mult']} avg_pf={best_dd['avg_pf']} avg_dd={best_dd['avg_dd_days']}d")


if __name__ == "__main__":
    main()
