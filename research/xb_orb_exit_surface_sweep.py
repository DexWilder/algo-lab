#!/usr/bin/env python3
"""XB-ORB Exit Surface Sweep — now that target_mult and trail_mult work.

After fixing the exit_profit_ladder bug (ladder_style="configurable" enables
real tuning), this sweep explores the true exit surface on the xb_orb_ema_ladder
anchor. We keep the winning entry + filter + stop_mult=2.0 and vary only the
ladder parameters.

Grid:
  target_mult: [2.0, 3.0, 4.0, 5.0, 6.0]       (ladder length)
  trail_mult:  [0.5, 1.0, 1.5, 2.0, 3.0]       (lock tightness)

= 25 combinations × 4 assets = 100 runs.

We're looking for:
  - PF improvement over the classic baseline (1.55 avg across 4 assets)
  - Shorter drawdown duration (especially MGC, currently 363d)
  - Better median trade (currently $43 on MNQ)
  - Any variant that meaningfully extends the anchor

The classic baseline reference:
  MNQ: PF 1.62 | MES: PF 1.58 | MGC: PF 1.65 | M2K: PF 1.34 | avg 1.55

The classic ladder is: (1R→0.25R, 2R→1R, 3R→2R) — doesn't fit the formula exactly.
The closest configurable approximation is target_mult=3.0, trail_mult=1.0 which
gives (1R→0R, 2R→1R, 3R→2R). The 1R lock level differs slightly.
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
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals

ASSETS = ["MNQ", "MES", "MGC", "M2K"]

TARGET_MULTS = [2.0, 3.0, 4.0, 5.0, 6.0]
TRAIL_MULTS = [0.5, 1.0, 1.5, 2.0, 3.0]

OUTPUT_PATH = ROOT / "research" / "data" / "xb_orb_exit_surface_results.json"


def concentration_metrics(trades_df):
    if trades_df is None or len(trades_df) == 0:
        return {"top3": 0, "top10": 0, "median": 0, "max_year": 0}
    total_pnl = trades_df["pnl"].sum()
    median_trade = float(trades_df["pnl"].median())
    if total_pnl <= 0:
        return {"top3": 0, "top10": 0, "median": median_trade, "max_year": 0}
    sorted_pnl = trades_df["pnl"].sort_values(ascending=False)
    top3 = float(sorted_pnl.head(3).sum() / total_pnl)
    top10 = float(sorted_pnl.head(10).sum() / total_pnl)

    year_share = 0
    try:
        td = trades_df.copy()
        td["year"] = pd.to_datetime(td["entry_time"]).dt.year
        yearly = td.groupby("year")["pnl"].sum()
        if yearly.sum() > 0:
            year_share = float(yearly.max() / yearly.sum())
    except Exception:
        pass

    return {"top3": top3, "top10": top10, "median": median_trade, "max_year": year_share}


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


def run_variant(asset, target_mult, trail_mult):
    cfg = get_asset(asset)
    df = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    params = {
        "stop_mult": 2.0,  # proven baseline
        "target_mult": target_mult,
        "trail_mult": trail_mult,
        "ladder_style": "configurable",  # enable the tunable ladder
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
    conc = concentration_metrics(trades)
    return {
        "asset": asset,
        "target_mult": target_mult,
        "trail_mult": trail_mult,
        "trades": len(trades),
        "pf": round(compute_pf(trades), 3),
        "pnl": round(float(trades["pnl"].sum()) if len(trades) else 0, 0),
        "top3": round(conc["top3"] * 100, 1),
        "top10": round(conc["top10"] * 100, 1),
        "median": round(conc["median"], 2),
        "max_year": round(conc["max_year"] * 100, 1),
        "dd_days": max_dd_duration_days(trades),
    }


def main():
    combos = list(itertools.product(TARGET_MULTS, TRAIL_MULTS))
    total = len(combos) * len(ASSETS)
    print(f"XB-ORB exit surface sweep: {len(combos)} combos × {len(ASSETS)} assets = {total} runs")
    print(f"All variants use stop_mult=2.0 (proven), ladder_style='configurable'")
    print()

    results = []
    start = time.time()

    # Reference: classic baseline for comparison
    classic_ref = {
        "MNQ": {"pf": 1.62, "dd_days": 143, "median": 43.26},
        "MES": {"pf": 1.58, "dd_days": 228, "median": 23.76},
        "MGC": {"pf": 1.65, "dd_days": 363, "median": 9.26},
        "M2K": {"pf": 1.34, "dd_days": 265, "median": 7.76},
    }

    for target, trail in combos:
        per_asset = []
        for asset in ASSETS:
            try:
                r = run_variant(asset, target, trail)
                per_asset.append(r)
            except Exception as e:
                print(f"  ERR target={target} trail={trail} {asset}: {e}")

        if not per_asset:
            continue

        profitable = sum(1 for r in per_asset if r["pf"] > 1.0)
        avg_pf = np.mean([r["pf"] for r in per_asset])
        all_med_pos = all(r["median"] >= 0 for r in per_asset)
        total_trades = sum(r["trades"] for r in per_asset)
        avg_dd = np.mean([r["dd_days"] for r in per_asset])

        # Delta vs classic
        mnq = next((r for r in per_asset if r["asset"] == "MNQ"), None)
        mgc = next((r for r in per_asset if r["asset"] == "MGC"), None)
        mnq_pf_delta = (mnq["pf"] - classic_ref["MNQ"]["pf"]) if mnq else 0
        mgc_dd_delta = (mgc["dd_days"] - classic_ref["MGC"]["dd_days"]) if mgc else 0

        marker = "**" if profitable == 4 and all_med_pos and avg_pf > 1.55 else "  "
        print(f"  {marker}tgt={target:.1f} trl={trail:.1f}: "
              f"{profitable}/4 prof, avg PF {avg_pf:.3f} ({'+' if mnq_pf_delta >= 0 else ''}{mnq_pf_delta:.3f} MNQ), "
              f"avg DD {avg_dd:.0f}d, med+ {all_med_pos}, trades {total_trades}, "
              f"MGC DD delta {mgc_dd_delta:+.0f}d")

        results.append({
            "target_mult": target,
            "trail_mult": trail,
            "profitable": profitable,
            "avg_pf": round(avg_pf, 3),
            "total_trades": total_trades,
            "avg_dd_days": round(avg_dd, 0),
            "all_median_positive": all_med_pos,
            "mnq_pf_delta_vs_classic": round(mnq_pf_delta, 3),
            "mgc_dd_delta_vs_classic": mgc_dd_delta,
            "per_asset": per_asset,
        })

    elapsed = time.time() - start
    print(f"\nSweep completed in {elapsed/60:.1f} minutes")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved to: {OUTPUT_PATH}")

    print()
    print("=" * 100)
    print("  RANKED RESULTS — looking for improvements over classic baseline")
    print("=" * 100)

    # Filter to clean variants
    clean = [r for r in results if r["profitable"] == 4 and r["all_median_positive"]]
    clean.sort(key=lambda r: -r["avg_pf"])

    print(f"\n  Clean variants (4/4 profitable, positive medians): {len(clean)}/{len(results)}")
    print(f"  Classic reference: avg PF 1.548 (measured in earlier stop sweep)")
    print()
    print(f"  {'target':>7s} {'trail':>6s} {'avg_pf':>8s} {'MNQ dPF':>8s} {'MGC dDD':>8s} {'trades':>7s}")
    print(f"  {'-'*7} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*7}")
    for r in clean[:15]:
        print(f"  {r['target_mult']:>7.1f} {r['trail_mult']:>6.1f} "
              f"{r['avg_pf']:>8.3f} {r['mnq_pf_delta_vs_classic']:>+8.3f} "
              f"{r['mgc_dd_delta_vs_classic']:>+8d} {r['total_trades']:>7d}")

    # Best PF
    if clean:
        best_pf = max(clean, key=lambda r: r["avg_pf"])
        print(f"\n  BEST BY PF: target={best_pf['target_mult']} trail={best_pf['trail_mult']}")
        print(f"    avg PF {best_pf['avg_pf']} (vs classic ~1.548, delta {best_pf['avg_pf']-1.548:+.3f})")
        for a in best_pf["per_asset"]:
            print(f"    {a['asset']}: PF={a['pf']} PnL=${a['pnl']:.0f} DD={a['dd_days']}d median=${a['median']:.2f}")

        # Best DD
        best_dd = min(clean, key=lambda r: r["avg_dd_days"])
        if best_dd != best_pf:
            print(f"\n  BEST BY DRAWDOWN: target={best_dd['target_mult']} trail={best_dd['trail_mult']}")
            print(f"    avg PF {best_dd['avg_pf']} avg DD {best_dd['avg_dd_days']}d")
            for a in best_dd["per_asset"]:
                print(f"    {a['asset']}: PF={a['pf']} PnL=${a['pnl']:.0f} DD={a['dd_days']}d median=${a['median']:.2f}")


if __name__ == "__main__":
    main()
