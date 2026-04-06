#!/usr/bin/env python3
"""Walk-Forward Robustness Matrix — compact visual for promotion decisions.

Runs key robustness checks on a strategy and outputs a single-page matrix
showing pass/fail across regimes, time periods, and parameters.

Designed for use before promotion gates. Shows whether a strategy's edge
is robust or fragile in one view.

Usage:
    python3 scripts/robustness_matrix.py --strategy zn_afternoon_reversion --asset ZN
    python3 scripts/robustness_matrix.py --strategy vol_managed_equity --asset MES
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.asset_config import get_execution_params


def load_strategy(name):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compute_stats(trades):
    """Compute core stats from a trades DataFrame."""
    if trades.empty or len(trades) < 3:
        return {"n": len(trades), "pf": None, "wr": None, "avg": None}
    n = len(trades)
    w = trades[trades["pnl"] > 0]["pnl"].sum()
    l = abs(trades[trades["pnl"] < 0]["pnl"].sum())
    pf = round(w / l, 2) if l > 0 else 99.0
    wr = round((trades["pnl"] > 0).sum() / n * 100, 1)
    avg = round(trades["pnl"].mean(), 2)
    return {"n": n, "pf": pf, "wr": wr, "avg": avg}


def run_matrix(strategy_name, asset, mode="both"):
    """Run robustness checks and return matrix data."""
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    config = get_execution_params(asset)

    mod = load_strategy(strategy_name)
    signals = mod.generate_signals(df, mode=mode) if "mode" in str(
        importlib.util.spec_from_file_location("", ROOT / "strategies" / strategy_name / "strategy.py")
    ) else mod.generate_signals(df)

    bt_df = signals if len(signals) < len(df) else df
    result = run_backtest(bt_df, signals, mode=mode,
                          point_value=config["point_value"], symbol=asset)
    trades = result["trades_df"]

    if trades.empty:
        return None

    # Add time metadata
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    trades["year"] = trades["entry_dt"].dt.year
    trades["month"] = trades["entry_dt"].dt.month
    trades["dow"] = trades["entry_dt"].dt.dayofweek
    trades["hour"] = trades["entry_dt"].dt.hour

    matrix = {}

    # ── 1. Walk-Forward Time Splits ──
    mid = len(trades) // 2
    h1, h2 = trades.iloc[:mid], trades.iloc[mid:]
    matrix["walk_forward"] = {
        "H1": compute_stats(h1),
        "H2": compute_stats(h2),
    }

    # ── 2. Year-by-Year ──
    matrix["by_year"] = {}
    for year in sorted(trades["year"].unique()):
        yt = trades[trades["year"] == year]
        matrix["by_year"][str(year)] = compute_stats(yt)

    # ── 3. Rolling Windows (12-month, 6-month step) ──
    matrix["rolling"] = []
    if not trades.empty:
        min_date = trades["entry_dt"].min()
        max_date = trades["entry_dt"].max()
        window_start = min_date
        while window_start < max_date:
            window_end = window_start + pd.DateOffset(months=12)
            wt = trades[(trades["entry_dt"] >= window_start) & (trades["entry_dt"] < window_end)]
            if len(wt) >= 5:
                s = compute_stats(wt)
                s["start"] = window_start.strftime("%Y-%m")
                matrix["rolling"].append(s)
            window_start += pd.DateOffset(months=6)

    # ── 4. Regime Proxy (ATR percentile) ──
    # Compute daily ATR from the source data
    daily = df.groupby(df["datetime"].dt.date).agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last")
    ).reset_index()
    daily.columns = ["date", "high", "low", "close"]
    daily["date"] = pd.to_datetime(daily["date"])
    prev_c = daily["close"].shift(1)
    tr = pd.concat([daily["high"] - daily["low"],
                     (daily["high"] - prev_c).abs(),
                     (daily["low"] - prev_c).abs()], axis=1).max(axis=1)
    daily["atr20"] = tr.rolling(20, min_periods=20).mean()
    daily["atr_pctile"] = daily["atr20"].rank(pct=True)

    trades["entry_date"] = trades["entry_dt"].dt.normalize()
    trades_merged = trades.merge(daily[["date", "atr_pctile"]],
                                  left_on="entry_date", right_on="date", how="left")

    matrix["by_regime"] = {}
    for name, lo, hi in [("LOW_VOL", 0, 0.33), ("NORMAL", 0.33, 0.67), ("HIGH_VOL", 0.67, 1.01)]:
        rt = trades_merged[(trades_merged["atr_pctile"] >= lo) & (trades_merged["atr_pctile"] < hi)]
        matrix["by_regime"][name] = compute_stats(rt)

    # ── 5. Direction Split ──
    if "side" in trades.columns:
        matrix["by_direction"] = {}
        for d in ["long", "short"]:
            dt = trades[trades["side"] == d]
            if not dt.empty:
                matrix["by_direction"][d] = compute_stats(dt)

    # ── 6. Day of Week ──
    matrix["by_dow"] = {}
    for dow, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        dt = trades[trades["dow"] == dow]
        if len(dt) >= 3:
            matrix["by_dow"][name] = compute_stats(dt)

    # ── 7. Overall ──
    matrix["overall"] = compute_stats(trades)

    return matrix


def format_matrix(matrix, strategy_name, asset):
    """Format the matrix as a readable report."""
    lines = []
    lines.append(f"# Robustness Matrix: {strategy_name} on {asset}")
    lines.append("")

    o = matrix["overall"]
    lines.append(f"**Overall:** {o['n']} trades, PF {o['pf']}, WR {o['wr']}%")
    lines.append("")

    # Walk-forward
    lines.append("## Walk-Forward")
    lines.append("")
    lines.append("| Split | Trades | PF | WR | Verdict |")
    lines.append("|-------|--------|----|----|---------|")
    for split, s in matrix["walk_forward"].items():
        verdict = "PASS" if s["pf"] and s["pf"] > 1.0 else ("FAIL" if s["pf"] else "—")
        pf = f"{s['pf']:.2f}" if s["pf"] else "—"
        wr = f"{s['wr']}%" if s["wr"] else "—"
        lines.append(f"| {split} | {s['n']} | {pf} | {wr} | {verdict} |")

    # Year-by-year
    lines.append("")
    lines.append("## Year-by-Year")
    lines.append("")
    lines.append("| Year | Trades | PF | WR | Verdict |")
    lines.append("|------|--------|----|----|---------|")
    for year, s in sorted(matrix["by_year"].items()):
        verdict = "PASS" if s["pf"] and s["pf"] > 1.0 else ("FAIL" if s["pf"] else "LOW_SAMPLE")
        pf = f"{s['pf']:.2f}" if s["pf"] else "—"
        wr = f"{s['wr']}%" if s["wr"] else "—"
        lines.append(f"| {year} | {s['n']} | {pf} | {wr} | {verdict} |")

    # Rolling windows
    if matrix.get("rolling"):
        lines.append("")
        lines.append("## Rolling 12-Month Windows")
        lines.append("")
        passing = sum(1 for r in matrix["rolling"] if r.get("pf") and r["pf"] > 1.0)
        total = len(matrix["rolling"])
        pct = passing / total * 100 if total > 0 else 0
        lines.append(f"**{passing}/{total} windows PF > 1.0 ({pct:.0f}%)**")
        lines.append(f"Gate: ≥ 75% required. {'PASS' if pct >= 75 else 'FAIL'}")

    # Regime
    lines.append("")
    lines.append("## Regime (ATR Percentile)")
    lines.append("")
    lines.append("| Regime | Trades | PF | WR | Verdict |")
    lines.append("|--------|--------|----|----|---------|")
    for regime, s in matrix.get("by_regime", {}).items():
        pf = f"{s['pf']:.2f}" if s["pf"] else "—"
        wr = f"{s['wr']}%" if s["wr"] else "—"
        verdict = "PASS" if s["pf"] and s["pf"] > 0.5 else ("FAIL" if s["n"] >= 10 else "LOW_SAMPLE")
        lines.append(f"| {regime} | {s['n']} | {pf} | {wr} | {verdict} |")

    # Direction
    if matrix.get("by_direction"):
        lines.append("")
        lines.append("## Direction")
        lines.append("")
        for d, s in matrix["by_direction"].items():
            pf = f"{s['pf']:.2f}" if s["pf"] else "—"
            lines.append(f"- **{d.upper()}:** {s['n']} trades, PF {pf}, WR {s['wr']}%")

    # Day of week
    if matrix.get("by_dow"):
        lines.append("")
        lines.append("## Day of Week")
        lines.append("")
        lines.append("| Day | Trades | PF | WR |")
        lines.append("|-----|--------|----|----|")
        for day, s in matrix["by_dow"].items():
            pf = f"{s['pf']:.2f}" if s["pf"] else "—"
            wr = f"{s['wr']}%" if s["wr"] else "—"
            lines.append(f"| {day} | {s['n']} | {pf} | {wr} |")

    # Summary verdict
    lines.append("")
    lines.append("## Promotion Readiness")
    lines.append("")

    wf = matrix["walk_forward"]
    wf_pass = all(s.get("pf") and s["pf"] > 1.0 for s in wf.values())
    regime_pass = all(s.get("pf") and s["pf"] > 0.5 for s in matrix.get("by_regime", {}).values() if s["n"] >= 10)
    rolling_pass = matrix.get("rolling") and sum(1 for r in matrix["rolling"] if r.get("pf") and r["pf"] > 1.0) / len(matrix["rolling"]) >= 0.75 if matrix.get("rolling") else False
    year_pass = sum(1 for s in matrix["by_year"].values() if s.get("pf") and s["pf"] > 1.0) / len(matrix["by_year"]) >= 0.6 if matrix["by_year"] else False

    lines.append(f"| Check | Result |")
    lines.append(f"|-------|--------|")
    lines.append(f"| Walk-forward both halves > 1.0 | {'PASS' if wf_pass else 'FAIL'} |")
    lines.append(f"| No regime cell PF < 0.5 (≥10 trades) | {'PASS' if regime_pass else 'FAIL'} |")
    lines.append(f"| ≥75% rolling windows PF > 1.0 | {'PASS' if rolling_pass else 'FAIL'} |")
    lines.append(f"| ≥60% of years PF > 1.0 | {'PASS' if year_pass else 'FAIL'} |")

    total_pass = sum([wf_pass, regime_pass, rolling_pass, year_pass])
    lines.append(f"\n**Score: {total_pass}/4 robustness checks passed.**")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Walk-Forward Robustness Matrix")
    parser.add_argument("--strategy", required=True, help="Strategy module name")
    parser.add_argument("--asset", required=True, help="Asset symbol")
    parser.add_argument("--mode", default="both", help="Trading mode: long, short, both")
    args = parser.parse_args()

    print(f"Running robustness matrix for {args.strategy} on {args.asset}...")
    matrix = run_matrix(args.strategy, args.asset, args.mode)

    if matrix is None:
        print("No trades generated. Cannot produce matrix.")
        return

    report = format_matrix(matrix, args.strategy, args.asset)
    print(report)


if __name__ == "__main__":
    main()
