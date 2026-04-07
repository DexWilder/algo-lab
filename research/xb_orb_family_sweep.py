#!/usr/bin/env python3
"""XB-ORB Family Sweep — find siblings around the winning template.

Strategy: use xb_orb_ema_ladder (ORB entry + EMA filter + profit_ladder exit)
as the anchor and systematically swap one component at a time. This searches
the neighborhood of a known winner rather than random recipes.

Three axes explored:
  1. Entry swap: keep EMA filter + profit_ladder exit, try other entries
     - orb_breakout (anchor)
     - donchian_breakout
     - pb_pullback
     - vwap_continuation
     - bb_reversion

  2. Filter swap: keep ORB entry + profit_ladder exit, try other filters
     - ema_slope (anchor)
     - vwap_slope
     - bandwidth_squeeze
     - session_morning
     - session_afternoon
     - none

  3. Exit swap: keep ORB entry + EMA filter, try other exits
     - profit_ladder (anchor)
     - atr_trail
     - midline_target (bb)
     - midline_target (vwap)
     - chandelier
     - time_stop

Uses stop_mult=2.0 (proven baseline from stop sweep).
Evaluated against concentration-aware gates.
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
BASE_PARAMS = {
    "stop_mult": 2.0,
    "target_mult": 4.0,  # currently ignored by profit_ladder but used by other exits
    "trail_mult": 2.5,   # used by atr_trail, chandelier
    "vwap_proximity": 0.5,
    "pb_proximity": 0.5,
    "bw_threshold": 50,
    "max_bars": 30,
    "min_hold": 3,
}

# Variant recipes to test (all variations on the xb_orb_ema_ladder anchor)
VARIANTS = [
    # ── ANCHOR: our known winner ────────────────────────────────────────
    {"id": "anchor", "entry": "orb_breakout", "exit": "profit_ladder", "filter": "ema_slope"},

    # ── Entry swaps (keep EMA + profit_ladder) ──────────────────────────
    {"id": "entry_donchian", "entry": "donchian_breakout", "exit": "profit_ladder", "filter": "ema_slope"},
    {"id": "entry_pb_pullback", "entry": "pb_pullback", "exit": "profit_ladder", "filter": "ema_slope"},
    {"id": "entry_vwap_cont", "entry": "vwap_continuation", "exit": "profit_ladder", "filter": "ema_slope"},
    {"id": "entry_bb_reversion", "entry": "bb_reversion", "exit": "profit_ladder", "filter": "ema_slope"},

    # ── Filter swaps (keep ORB + profit_ladder) ─────────────────────────
    {"id": "filter_vwap_slope", "entry": "orb_breakout", "exit": "profit_ladder", "filter": "vwap_slope"},
    {"id": "filter_bw_squeeze", "entry": "orb_breakout", "exit": "profit_ladder", "filter": "bandwidth_squeeze"},
    {"id": "filter_morning", "entry": "orb_breakout", "exit": "profit_ladder", "filter": "session_morning"},
    {"id": "filter_afternoon", "entry": "orb_breakout", "exit": "profit_ladder", "filter": "session_afternoon"},
    {"id": "filter_none", "entry": "orb_breakout", "exit": "profit_ladder", "filter": "none"},

    # ── Exit swaps (keep ORB + EMA) ─────────────────────────────────────
    {"id": "exit_atr_trail", "entry": "orb_breakout", "exit": "atr_trail", "filter": "ema_slope"},
    {"id": "exit_midline_bb", "entry": "orb_breakout", "exit": "midline_target", "filter": "ema_slope",
     "extra_params": {"midline_type": "bb"}},
    {"id": "exit_midline_vwap", "entry": "orb_breakout", "exit": "midline_target", "filter": "ema_slope",
     "extra_params": {"midline_type": "vwap"}},
    {"id": "exit_chandelier", "entry": "orb_breakout", "exit": "chandelier", "filter": "ema_slope",
     "extra_params": {"chandelier_mult": 3.0}},
    {"id": "exit_time_stop", "entry": "orb_breakout", "exit": "time_stop", "filter": "ema_slope"},
]

OUTPUT_PATH = ROOT / "research" / "data" / "xb_orb_family_sweep_results.json"


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

    # Year share
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


def run_variant(variant, asset):
    cfg = get_asset(asset)
    df = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    params = dict(BASE_PARAMS)
    if "extra_params" in variant:
        params.update(variant["extra_params"])

    signals = generate_crossbred_signals(
        df,
        entry_name=variant["entry"],
        exit_name=variant["exit"],
        filter_name=variant["filter"],
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
        "trades": len(trades),
        "pf": round(compute_pf(trades), 3),
        "pnl": round(float(trades["pnl"].sum()) if len(trades) else 0, 0),
        "top3": round(conc["top3"] * 100, 1),
        "top10": round(conc["top10"] * 100, 1),
        "median": round(conc["median"], 2),
        "max_year": round(conc["max_year"] * 100, 1),
        "dd_days": max_dd_duration_days(trades),
    }


def classify_variant(per_asset):
    """Apply the 4 edge signals to determine if a variant is viable."""
    # Gate 1: cross-asset (≥50% profitable)
    profitable = sum(1 for a in per_asset if a["pf"] > 1.0)
    if profitable < len(per_asset) // 2 + 1:
        return "REJECT", f"{profitable}/{len(per_asset)} profitable (need majority)"

    # Gate 2: all medians positive
    if not all(a["median"] >= 0 for a in per_asset):
        bad = [a["asset"] for a in per_asset if a["median"] < 0]
        return "REJECT", f"negative median on {bad}"

    # Gate 3: sample size (workhorse density)
    total_trades = sum(a["trades"] for a in per_asset)
    if total_trades < 500:
        return "REJECT", f"total trades {total_trades} < 500"

    # Gate 4: concentration (top-10 < 55% on best asset)
    best = max(per_asset, key=lambda a: a["pf"])
    if best["top10"] > 55:
        return "REJECT", f"best-asset top-10 {best['top10']}% > 55%"

    # Gate 5: max year share
    if best["max_year"] > 40:
        return "SALVAGE", f"best-asset max year {best['max_year']}% > 40%"

    # Gate 6: drawdown duration (< 500 days on best asset)
    if best["dd_days"] > 500:
        return "SALVAGE", f"best-asset DD {best['dd_days']}d > 500"

    avg_pf = np.mean([a["pf"] for a in per_asset])
    if avg_pf >= 1.3 and profitable == len(per_asset):
        return "ADVANCE", f"all {len(per_asset)} profitable, avg PF {avg_pf:.2f}"

    return "SALVAGE", f"avg PF {avg_pf:.2f}, profitable {profitable}/{len(per_asset)}"


def main():
    print(f"XB-ORB family sweep: {len(VARIANTS)} variants × {len(ASSETS)} assets = {len(VARIANTS)*len(ASSETS)} runs")
    print(f"Using proven baseline stop_mult={BASE_PARAMS['stop_mult']}")
    print()

    all_results = []
    start = time.time()

    for variant in VARIANTS:
        print(f"  [{variant['id']}] {variant['entry']} / {variant['filter']} / {variant['exit']}...")
        per_asset = []
        for asset in ASSETS:
            try:
                r = run_variant(variant, asset)
                per_asset.append(r)
            except Exception as e:
                print(f"    {asset}: ERROR {e}")

        if not per_asset:
            continue

        classification, reason = classify_variant(per_asset)

        profitable = sum(1 for a in per_asset if a["pf"] > 1.0)
        avg_pf = np.mean([a["pf"] for a in per_asset])
        total_trades = sum(a["trades"] for a in per_asset)
        best = max(per_asset, key=lambda a: a["pf"])

        print(f"    → {classification}: {profitable}/{len(per_asset)} profitable, "
              f"avg PF {avg_pf:.2f}, trades {total_trades}, best {best['asset']} PF {best['pf']}")
        print(f"      {reason}")

        all_results.append({
            "id": variant["id"],
            "entry": variant["entry"],
            "filter": variant["filter"],
            "exit": variant["exit"],
            "classification": classification,
            "reason": reason,
            "profitable": profitable,
            "avg_pf": round(avg_pf, 3),
            "total_trades": total_trades,
            "best_asset": best["asset"],
            "best_pf": best["pf"],
            "per_asset": per_asset,
        })

    elapsed = time.time() - start
    print(f"\nSweep completed in {elapsed/60:.1f} minutes")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved to: {OUTPUT_PATH}")

    # Ranked summary
    print()
    print("=" * 90)
    print("  XB-ORB FAMILY SWEEP — RANKED RESULTS")
    print("=" * 90)

    order = {"ADVANCE": 0, "SALVAGE": 1, "REJECT": 2}
    all_results.sort(key=lambda r: (order.get(r["classification"], 9), -r["avg_pf"]))

    print(f"  {'Variant ID':<22s} {'Class':10s} {'avg PF':>7s} {'Prof':>5s} {'Trades':>7s} {'Best':>6s} {'Best PF':>8s}")
    print(f"  {'-'*22} {'-'*10} {'-'*7} {'-'*5} {'-'*7} {'-'*6} {'-'*8}")
    for r in all_results:
        print(f"  {r['id']:<22s} {r['classification']:10s} {r['avg_pf']:>7.2f} "
              f"{r['profitable']:>5d} {r['total_trades']:>7d} {r['best_asset']:>6s} {r['best_pf']:>8.2f}")

    advances = [r for r in all_results if r["classification"] == "ADVANCE"]
    if advances:
        print()
        print(f"  >> {len(advances)} ADVANCE candidates found in ORB family:")
        for r in advances:
            print(f"     {r['id']}: {r['entry']}/{r['filter']}/{r['exit']}")


if __name__ == "__main__":
    main()
