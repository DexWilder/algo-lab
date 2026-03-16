#!/usr/bin/env python3
"""FQL Batch First-Pass — Factory tool for rapid strategy evaluation.

Runs one strategy across multiple assets, modes, and a walk-forward split.
Produces a standardized JSON report with automatic classification.

This replaces the manual 50-line ad-hoc scripts used during prototyping.
It is the primary throughput tool for the strategy factory pipeline.

Classification rules:
  ADVANCE    — PF > 1.2, trades >= 30, walk-forward both halves PF > 1.0
  SALVAGE    — PF > 1.0, trades >= 20, one mode PF > 1.2 or one WF half PF > 1.3
  MONITOR    — PF > 1.0 but trades < 20, or PF > 1.2 but WF unstable
  REJECT     — PF < 1.0 on all modes, or trades >= 30 with PF < 1.1

Usage:
    # Test on specific assets
    python3 research/batch_first_pass.py --strategy fx_session_breakout --assets 6J,6E,6B

    # Test on all compatible assets (from asset_config)
    python3 research/batch_first_pass.py --strategy momentum_pullback_trend --assets all

    # Test with US-session filter
    python3 research/batch_first_pass.py --strategy momentum_pullback_trend --assets 6J --session us

    # Dry run (show what would be tested)
    python3 research/batch_first_pass.py --strategy vwap_trend --assets all --dry-run
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.asset_config import ASSETS, get_asset, get_assets_by_status
from research.utils.atomic_io import atomic_write_json

OUTPUT_DIR = ROOT / "research" / "data" / "first_pass"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Classification Rules ─────────────────────────────────────────────────────

def classify(pf, trades, wf_h1_pf, wf_h2_pf, mode_results):
    """Apply deterministic classification rules.

    Returns (classification, reasons) tuple.
    """
    reasons = []

    # Check if any single mode shows strong edge
    best_mode_pf = max((m["pf"] for m in mode_results if m["trades"] >= 15), default=0)
    any_mode_above_1_2 = any(m["pf"] > 1.2 and m["trades"] >= 15 for m in mode_results)

    # ADVANCE: strong across the board
    if pf > 1.2 and trades >= 30 and wf_h1_pf > 1.0 and wf_h2_pf > 1.0:
        reasons.append(f"PF {pf:.2f} > 1.2 with {trades} trades")
        reasons.append(f"Walk-forward stable: H1={wf_h1_pf:.2f}, H2={wf_h2_pf:.2f}")
        return "ADVANCE", reasons

    # SALVAGE: partial edge worth one follow-up
    if pf > 1.0 and trades >= 20:
        if any_mode_above_1_2:
            reasons.append(f"Overall PF {pf:.2f}, but directional split shows PF > 1.2")
            return "SALVAGE", reasons
        if wf_h1_pf > 1.3 or wf_h2_pf > 1.3:
            reasons.append(f"Period-specific edge: H1={wf_h1_pf:.2f}, H2={wf_h2_pf:.2f}")
            return "SALVAGE", reasons

    # MONITOR: signal but insufficient data
    if pf > 1.0 and trades < 20:
        reasons.append(f"PF {pf:.2f} > 1.0 but only {trades} trades — insufficient sample")
        return "MONITOR", reasons
    if pf > 1.2 and (wf_h1_pf < 0.8 or wf_h2_pf < 0.8):
        reasons.append(f"PF {pf:.2f} > 1.2 but walk-forward unstable: H1={wf_h1_pf:.2f}, H2={wf_h2_pf:.2f}")
        return "MONITOR", reasons

    # REJECT: no viable edge
    if trades >= 30 and pf < 1.1:
        reasons.append(f"Sufficient trades ({trades}) but PF {pf:.2f} < 1.1")
    elif pf < 1.0:
        reasons.append(f"Negative edge: PF {pf:.2f}")
    else:
        reasons.append(f"PF {pf:.2f}, {trades} trades — below all advancement thresholds")
    return "REJECT", reasons


# ── Metrics ──────────────────────────────────────────────────────────────────

def compute_metrics(trades_df):
    """Compute standard metrics from trades DataFrame."""
    if trades_df.empty:
        return {"trades": 0, "pnl": 0, "pf": 0, "sharpe": 0, "maxdd": 0, "wr": 0, "avg_pnl": 0}

    n = len(trades_df)
    pnl = trades_df["pnl"].sum()
    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] < 0]
    gw = wins["pnl"].sum() if len(wins) else 0
    gl = abs(losses["pnl"].sum()) if len(losses) else 0
    pf = gw / gl if gl > 0 else (99.0 if gw > 0 else 0.0)
    wr = len(wins) / n * 100

    daily_pnl = trades_df.groupby(
        pd.to_datetime(trades_df["entry_time"]).dt.date
    )["pnl"].sum()
    sharpe = (daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)
              if len(daily_pnl) > 1 and daily_pnl.std() > 0 else 0)

    eq = 50000 + trades_df["pnl"].cumsum()
    maxdd = (eq.cummax() - eq).max()

    return {
        "trades": n,
        "pnl": round(float(pnl), 2),
        "pf": round(float(pf), 3),
        "sharpe": round(float(sharpe), 2),
        "maxdd": round(float(maxdd), 2),
        "wr": round(float(wr), 1),
        "avg_pnl": round(float(pnl / n), 2),
    }


# ── Strategy Loader ──────────────────────────────────────────────────────────

def load_strategy(strategy_name, tick_size):
    """Load a strategy module by name."""
    path = ROOT / "strategies" / strategy_name / "strategy.py"
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {path}")
    spec = importlib.util.spec_from_file_location(strategy_name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.TICK_SIZE = tick_size
    spec.loader.exec_module(mod)
    return mod


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_data(asset, session_filter=None):
    """Load 5m data for an asset, optionally filtering to a session."""
    path = ROOT / "data" / "processed" / f"{asset}_5m.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    if session_filter == "us":
        df = df[df["datetime"].dt.hour.between(8, 16)].reset_index(drop=True)
    elif session_filter == "london":
        df = df[df["datetime"].dt.hour.between(3, 11)].reset_index(drop=True)
    elif session_filter == "tokyo":
        df = df[(df["datetime"].dt.hour >= 18) | (df["datetime"].dt.hour < 3)].reset_index(drop=True)

    return df


# ── Core Runner ──────────────────────────────────────────────────────────────

def run_first_pass(strategy_name, assets, session_filter=None):
    """Run first-pass evaluation across assets and modes.

    Returns structured report dict.
    """
    report = {
        "strategy": strategy_name,
        "run_date": datetime.now().isoformat(),
        "session_filter": session_filter,
        "asset_results": {},
        "best_result": None,
        "overall_classification": "REJECT",
        "overall_reasons": [],
    }

    all_results = []

    for asset in assets:
        cfg = get_asset(asset)
        df = load_data(asset, session_filter)
        if df is None or len(df) < 1000:
            report["asset_results"][asset] = {"error": "No data or insufficient bars"}
            continue

        try:
            mod = load_strategy(strategy_name, cfg["tick_size"])
        except Exception as e:
            report["asset_results"][asset] = {"error": str(e)}
            continue

        asset_report = {"asset": asset, "bars": len(df), "modes": {}, "walk_forward": {}}

        # Run each mode
        mode_results = []
        for mode in ["both", "long", "short"]:
            try:
                signals = mod.generate_signals(df.copy(), mode=mode)
                r = run_backtest(
                    df, signals, mode=mode,
                    point_value=cfg["point_value"],
                    tick_size=cfg["tick_size"],
                    commission_per_side=cfg["commission_per_side"],
                    slippage_ticks=cfg["slippage_ticks"],
                )
                m = compute_metrics(r["trades_df"])
                m["mode"] = mode
                asset_report["modes"][mode] = m
                mode_results.append(m)
            except Exception as e:
                asset_report["modes"][mode] = {"error": str(e), "trades": 0, "pf": 0}
                mode_results.append({"pf": 0, "trades": 0, "mode": mode})

        # Walk-forward on "both" mode
        mid = len(df) // 2
        wf = {}
        for label, sub in [("H1", df.iloc[:mid]), ("H2", df.iloc[mid:])]:
            try:
                mod = load_strategy(strategy_name, cfg["tick_size"])
                signals = mod.generate_signals(sub.copy().reset_index(drop=True), mode="both")
                r = run_backtest(
                    sub.reset_index(drop=True), signals, mode="both",
                    point_value=cfg["point_value"],
                    tick_size=cfg["tick_size"],
                    commission_per_side=cfg["commission_per_side"],
                    slippage_ticks=cfg["slippage_ticks"],
                )
                wf[label] = compute_metrics(r["trades_df"])
            except Exception as e:
                wf[label] = {"error": str(e), "pf": 0, "trades": 0}
        asset_report["walk_forward"] = wf

        # Classify this asset
        both = asset_report["modes"].get("both", {"pf": 0, "trades": 0})
        h1_pf = wf.get("H1", {}).get("pf", 0)
        h2_pf = wf.get("H2", {}).get("pf", 0)
        cls, reasons = classify(
            both.get("pf", 0), both.get("trades", 0),
            h1_pf, h2_pf, mode_results,
        )
        asset_report["classification"] = cls
        asset_report["classification_reasons"] = reasons

        report["asset_results"][asset] = asset_report
        all_results.append((asset, cls, both.get("pf", 0), both.get("trades", 0)))

    # Overall classification: best asset determines overall
    cls_rank = {"ADVANCE": 4, "SALVAGE": 3, "MONITOR": 2, "REJECT": 1}
    if all_results:
        best = max(all_results, key=lambda x: (cls_rank.get(x[1], 0), x[2]))
        report["best_result"] = {
            "asset": best[0],
            "classification": best[1],
            "pf": best[2],
            "trades": best[3],
        }
        report["overall_classification"] = best[1]
        report["overall_reasons"] = report["asset_results"][best[0]].get("classification_reasons", [])

    return report


# ── Output ───────────────────────────────────────────────────────────────────

def print_report(report):
    """Print formatted terminal report."""
    W = 70
    print()
    print("=" * W)
    print(f"  FQL FIRST-PASS: {report['strategy']}")
    print(f"  {report['run_date'][:19]}")
    if report["session_filter"]:
        print(f"  Session filter: {report['session_filter']}")
    print("=" * W)

    for asset, ar in report["asset_results"].items():
        if "error" in ar:
            print(f"\n  {asset}: ERROR — {ar['error']}")
            continue

        cls = ar.get("classification", "?")
        icon = {"ADVANCE": "+", "SALVAGE": "~", "MONITOR": "?", "REJECT": "X"}.get(cls, "!")
        print(f"\n  [{icon}] {asset} — {cls}")
        print(f"  {'':4s}{'Mode':<7s} {'Trades':>7s} {'PnL':>10s} {'PF':>6s} {'Sharpe':>7s} {'WR':>5s}")
        print(f"  {'':4s}{'-' * 45}")
        for mode in ["both", "long", "short"]:
            m = ar["modes"].get(mode, {})
            if "error" in m:
                print(f"  {'':4s}{mode:<7s} ERROR")
                continue
            print(f"  {'':4s}{mode:<7s} {m['trades']:>7d} {m['pnl']:>10,.0f} {m['pf']:>6.2f} {m['sharpe']:>7.2f} {m['wr']:>4.0f}%")

        wf = ar.get("walk_forward", {})
        h1 = wf.get("H1", {})
        h2 = wf.get("H2", {})
        print(f"  {'':4s}WF: H1={h1.get('pf', 0):.2f} ({h1.get('trades', 0)}t)  H2={h2.get('pf', 0):.2f} ({h2.get('trades', 0)}t)")

        for reason in ar.get("classification_reasons", []):
            print(f"  {'':4s}  > {reason}")

    best = report.get("best_result")
    if best:
        print(f"\n{'=' * W}")
        print(f"  OVERALL: {report['overall_classification']}")
        print(f"  Best: {best['asset']} — PF {best['pf']:.2f}, {best['trades']} trades")
        print(f"{'=' * W}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FQL Batch First-Pass — rapid strategy evaluation")
    parser.add_argument("--strategy", required=True,
                        help="Strategy directory name (e.g., fx_session_breakout)")
    parser.add_argument("--assets", required=True,
                        help="Comma-separated assets or 'all' for all with data")
    parser.add_argument("--session", default=None, choices=["us", "london", "tokyo"],
                        help="Session filter (optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be tested, don't run")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON only")
    args = parser.parse_args()

    # Resolve assets
    if args.assets.lower() == "all":
        # All assets with data files
        assets = [sym for sym in ASSETS
                  if (ROOT / "data" / "processed" / f"{sym}_5m.csv").exists()]
    else:
        assets = [a.strip().upper() for a in args.assets.split(",")]

    if args.dry_run:
        print(f"Strategy: {args.strategy}")
        print(f"Assets: {', '.join(assets)}")
        print(f"Session: {args.session or 'none'}")
        print(f"Modes: both, long, short")
        print(f"Walk-forward: 50/50 split per asset")
        print(f"Output: {OUTPUT_DIR}/")
        return

    # Run
    report = run_first_pass(args.strategy, assets, args.session)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    session_tag = f"_{args.session}" if args.session else ""
    filename = f"{args.strategy}{session_tag}_{timestamp}.json"
    out_path = OUTPUT_DIR / filename
    atomic_write_json(out_path, report)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(report)
        print(f"\n  Report saved: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
