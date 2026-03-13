#!/usr/bin/env python3
"""Track 3 — Tail Engine Discovery

Tests low-frequency, high-convexity strategy families designed to produce
large winners ("tail engines") and improve portfolio Sharpe via upside spikes.

READ-ONLY research tool. Does NOT modify any frozen execution files.

Strategies tested:
  - vol_compression_breakout_v2: BB squeeze → expansion breakout
  - momentum_ignition: VWAP cross + volume surge + RSI momentum
  - range_expansion: narrow range day → expansion bar breakout
  - trend_continuation: EMA stack + pullback consolidation → breakout

Target assets: MNQ, M2K, MES (trend-friendly indices)

Success criteria for tail engines:
  - PnL efficiency: PnL share >> trade share (>2x ratio = tail engine)
  - Large winners: top 10% of trades > 40% of strategy PnL
  - Low frequency: <100 trades per 2.5 years is fine
  - PF >= 1.25 (lower bar than workhorses, because fewer trades)
  - Near-zero correlation vs existing portfolio (r < 0.15)

Usage:
    python3 research/track3_tail_engine_discovery.py
    python3 research/track3_tail_engine_discovery.py --save
"""

import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest

PROCESSED_DIR = ROOT / "data" / "processed"
STARTING_CAPITAL = 50_000.0

ASSET_CONFIG = {
    "MNQ": {"point_value": 2.0, "tick_size": 0.25, "name": "Micro Nasdaq-100"},
    "M2K": {"point_value": 5.0, "tick_size": 0.10, "name": "Micro Russell 2000"},
    "MES": {"point_value": 5.0, "tick_size": 0.25, "name": "Micro S&P 500"},
    "MGC": {"point_value": 10.0, "tick_size": 0.10, "name": "Micro Gold"},
}

# ── Test matrix: each tail-engine strategy × target assets ────────────────────

TAIL_ENGINE_STRATEGIES = [
    "vol_compression_breakout_v2",
    "momentum_ignition",
    "range_expansion",
    "trend_continuation",
]

TARGET_ASSETS = ["MNQ", "M2K", "MES"]

# Build full test matrix
TEST_MATRIX = []
for strat in TAIL_ENGINE_STRATEGIES:
    for asset in TARGET_ASSETS:
        TEST_MATRIX.append({"strategy": strat, "asset": asset, "modes": ["long", "short"]})

# Existing portfolio for correlation baseline
CORE_PORTFOLIO = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short", "label": "PB-MGC-Short"},
    {"name": "orb_009", "asset": "MGC", "mode": "long", "label": "ORB-MGC-Long"},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long", "label": "VWAP-MNQ-Long"},
    {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short", "label": "XB-PB-EMA-MES-Short"},
    {"name": "bb_equilibrium", "asset": "MGC", "mode": "long", "label": "BB-EQ-MGC-Long"},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long", "label": "Donchian-MNQ-Long"},
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def run_test(strategy_name: str, asset: str, mode: str) -> dict:
    """Run a single strategy/asset/mode backtest and return summary."""
    mod = load_strategy(strategy_name)
    config = ASSET_CONFIG[asset]
    df = load_data(asset)

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    params = list(sig.parameters.keys())
    kwargs = {}
    if "asset" in params:
        kwargs["asset"] = asset
    if "mode" in params:
        kwargs["mode"] = mode

    signals = mod.generate_signals(df, **kwargs)

    result = run_backtest(
        df, signals,
        mode=mode,
        point_value=config["point_value"],
        symbol=asset,
    )

    trades = result["trades_df"]
    if trades.empty:
        return {
            "strategy": strategy_name, "asset": asset, "mode": mode,
            "label": f"{strategy_name}-{asset}-{mode.title()}",
            "trades": 0, "pf": 0.0, "sharpe": 0.0, "pnl": 0.0,
            "win_rate": 0.0, "avg_pnl": 0.0, "max_dd": 0.0,
            "median_hold": 0, "top10_pct": 0.0, "tail_ratio": 0.0,
            "daily_series": pd.Series(dtype=float),
        }

    # Standard metrics
    pnl = trades["pnl"]
    winners = pnl[pnl > 0]
    losers = pnl[pnl <= 0]
    gross_profit = winners.sum() if len(winners) > 0 else 0
    gross_loss = abs(losers.sum()) if len(losers) > 0 else 0.001
    pf = gross_profit / gross_loss

    equity = STARTING_CAPITAL + pnl.cumsum()
    max_dd = (equity.cummax() - equity).max()

    # Daily PnL for correlation
    trades_c = trades.copy()
    trades_c["exit_date"] = pd.to_datetime(trades_c["exit_time"]).dt.date
    daily_pnl = trades_c.groupby("exit_date")["pnl"].sum()

    sharpe = 0.0
    if len(daily_pnl) > 1 and daily_pnl.std() > 0:
        sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)

    # Tail engine metrics
    n = len(trades)

    # Median hold time (bars)
    median_hold = 0
    if "entry_bar" in trades.columns and "exit_bar" in trades.columns:
        holds = trades["exit_bar"] - trades["entry_bar"]
        median_hold = int(holds.median())

    # Top 10% trades PnL share
    top10_pct = 0.0
    if n >= 10:
        top_n = max(1, n // 10)
        sorted_pnl = pnl.sort_values(ascending=False)
        top10_pnl = sorted_pnl.head(top_n).sum()
        total_pnl = pnl.sum()
        top10_pct = top10_pnl / total_pnl * 100 if total_pnl > 0 else 0

    # Tail ratio: avg winner / |avg loser|
    avg_win = winners.mean() if len(winners) > 0 else 0
    avg_loss = abs(losers.mean()) if len(losers) > 0 else 0.001
    tail_ratio = avg_win / avg_loss

    return {
        "strategy": strategy_name, "asset": asset, "mode": mode,
        "label": f"{strategy_name}-{asset}-{mode.title()}",
        "trades": n,
        "pf": round(pf, 2),
        "sharpe": round(sharpe, 2),
        "pnl": round(pnl.sum(), 2),
        "win_rate": round(len(winners) / n * 100, 1),
        "avg_pnl": round(pnl.mean(), 2),
        "max_dd": round(max_dd, 2),
        "median_hold": median_hold,
        "top10_pct": round(top10_pct, 1),
        "tail_ratio": round(tail_ratio, 2),
        "daily_series": daily_pnl,
    }


def compute_correlation(series_a: pd.Series, series_b: pd.Series) -> float:
    combined = pd.DataFrame({"a": series_a, "b": series_b}).fillna(0)
    if len(combined) < 10:
        return 0.0
    return round(combined["a"].corr(combined["b"]), 3)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Track 3 — Tail Engine Discovery")
    parser.add_argument("--save", action="store_true", help="Save results JSON")
    args = parser.parse_args()

    print()
    print("=" * 72)
    print("  TRACK 3 — TAIL ENGINE DISCOVERY")
    print("  Low-frequency convex strategies for portfolio upside")
    print("=" * 72)

    # ── Run all tests ──
    results = []
    current_asset = None

    for test in TEST_MATRIX:
        strategy = test["strategy"]
        asset = test["asset"]

        if asset != current_asset:
            current_asset = asset
            print(f"\n  {asset} ({ASSET_CONFIG[asset]['name']})")
            print("  " + "\u2500" * 60)

        for mode in test["modes"]:
            label = f"{strategy}-{asset}-{mode.title()}"
            try:
                r = run_test(strategy, asset, mode)
                results.append(r)
                flag = "\u2605" if r["pf"] >= 1.25 and r["trades"] >= 15 else " "
                print(f"    {flag} {label}")
                print(f"        {r['trades']} trades, PF={r['pf']:.2f}, "
                      f"Sharpe={r['sharpe']:.2f}, PnL=${r['pnl']:,.0f}, "
                      f"WR={r['win_rate']}%")
                if r["trades"] > 0:
                    print(f"        Hold={r['median_hold']}bars, "
                          f"Top10%={r['top10_pct']:.0f}%PnL, "
                          f"TailRatio={r['tail_ratio']:.1f}x")
            except Exception as e:
                print(f"    \u2717 {label}... ERROR: {e}")
                results.append({
                    "strategy": strategy, "asset": asset, "mode": mode,
                    "label": label, "trades": 0, "pf": 0, "sharpe": 0,
                    "pnl": 0, "win_rate": 0, "avg_pnl": 0, "max_dd": 0,
                    "median_hold": 0, "top10_pct": 0, "tail_ratio": 0,
                    "daily_series": pd.Series(dtype=float),
                })

    # ── Filter: tail engine criteria ──
    # More lenient on trade count (low-freq is OK), but need edge + tail shape
    viable = [
        r for r in results
        if r["pf"] >= 1.25 and r["trades"] >= 15
    ]

    # Further classify: true tail engines vs regular edges
    tail_engines = [r for r in viable if r["top10_pct"] >= 35 or r["tail_ratio"] >= 1.5]

    print()
    print("=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)

    # ── Tail engine scorecard ──
    print(f"\n  TAIL ENGINE SCORECARD")
    print("  " + "\u2550" * 68)

    if not viable:
        print("    No strategies met minimum viability (PF >= 1.25, trades >= 15)")
    else:
        print(f"\n    {'Label':<42} {'PF':>5} {'Sharpe':>7} {'Trades':>6} "
              f"{'Top10%':>7} {'Tail':>5} {'Class'}")
        print(f"    {'-'*42} {'-'*5} {'-'*7} {'-'*6} {'-'*7} {'-'*5} {'-'*12}")

        for r in sorted(viable, key=lambda x: x["sharpe"], reverse=True):
            is_tail = r in tail_engines
            cls = "TAIL ENGINE" if is_tail else "edge"
            print(f"    {r['label']:<42} {r['pf']:>5.2f} {r['sharpe']:>7.2f} "
                  f"{r['trades']:>6} {r['top10_pct']:>6.0f}% "
                  f"{r['tail_ratio']:>4.1f}x {cls}")

    # ── Compare to existing BB-EQ (the benchmark tail engine) ──
    print(f"\n  BENCHMARK: BB-EQ-MGC-Long (existing tail engine)")
    print("  " + "\u2500" * 68)
    try:
        bb_result = run_test("bb_equilibrium", "MGC", "long")
        print(f"    Trades={bb_result['trades']}, PF={bb_result['pf']:.2f}, "
              f"Sharpe={bb_result['sharpe']:.2f}, PnL=${bb_result['pnl']:,.0f}")
        print(f"    Top10%={bb_result['top10_pct']:.0f}%PnL, "
              f"TailRatio={bb_result['tail_ratio']:.1f}x, "
              f"Hold={bb_result['median_hold']}bars")
    except Exception as e:
        print(f"    ERROR: {e}")
        bb_result = None

    # ── Correlation analysis ──
    if viable:
        print(f"\n  CORRELATION vs EXISTING PORTFOLIO")
        print("  " + "\u2500" * 68)

        # Build core portfolio daily PnL series
        core_daily = {}
        for cs in CORE_PORTFOLIO:
            try:
                cr = run_test(cs["name"], cs["asset"], cs["mode"])
                core_daily[cs["label"]] = cr["daily_series"]
            except Exception:
                pass

        for v in sorted(viable, key=lambda x: x["sharpe"], reverse=True):
            max_corr = 0
            max_corr_name = ""
            corr_details = []

            for core_name, core_series in core_daily.items():
                corr = compute_correlation(v["daily_series"], core_series)
                corr_details.append((core_name, corr))
                if abs(corr) > abs(max_corr):
                    max_corr = corr
                    max_corr_name = core_name

            flag = "LOW" if abs(max_corr) < 0.15 else ("OK" if abs(max_corr) < 0.30 else "HIGH")
            print(f"\n    {v['label']}:")
            print(f"      Max |r| = {abs(max_corr):.3f} vs {max_corr_name} [{flag}]")

            for name, corr in sorted(corr_details, key=lambda x: abs(x[1]), reverse=True):
                bar = "\u2588" * int(abs(corr) * 30)
                print(f"        vs {name:<28s} r={corr:+.3f} {bar}")

    # ── Strategy family breakdown ──
    print(f"\n  STRATEGY FAMILY BREAKDOWN")
    print("  " + "\u2500" * 68)

    families = {}
    for r in results:
        strat = r["strategy"]
        families.setdefault(strat, []).append(r)

    for strat, strat_results in families.items():
        active = [r for r in strat_results if r["trades"] > 0]
        best = max(active, key=lambda x: x["pf"]) if active else None

        if best:
            is_viable = best in viable
            is_tail = best in tail_engines
            status = "TAIL ENGINE" if is_tail else ("VIABLE" if is_viable else "below threshold")
            print(f"  {strat}:")
            print(f"    Best: {best['label']} — PF={best['pf']:.2f}, "
                  f"Sharpe={best['sharpe']:.2f}, {best['trades']} trades [{status}]")
            print(f"    Assets with edge: {', '.join(r['asset']+'-'+r['mode'].title() for r in active if r['pf'] >= 1.0)}")
        else:
            print(f"  {strat}: no trades generated")

    # ── Recommendations ──
    print(f"\n  RECOMMENDATIONS")
    print("  " + "\u2550" * 68)

    if tail_engines:
        print("\n  Promote to validation battery (tail engine profile):")
        for r in sorted(tail_engines, key=lambda x: x["sharpe"], reverse=True):
            print(f"    \u2192 {r['label']} (PF={r['pf']}, Sharpe={r['sharpe']}, "
                  f"{r['trades']} trades, tail ratio {r['tail_ratio']:.1f}x)")

    if viable and not tail_engines:
        print("\n  Viable but not tail-shaped (regular edge):")
        for r in sorted(viable, key=lambda x: x["sharpe"], reverse=True):
            print(f"    \u2192 {r['label']} (PF={r['pf']}, Sharpe={r['sharpe']}, "
                  f"{r['trades']} trades)")
        print("\n  Consider: adjust targets/exits to increase tail capture")

    if not viable:
        print("\n  No viable strategies found.")
        print("  Consider:")
        print("    - Adjusting compression detection thresholds")
        print("    - Testing on 15m/30m timeframes for longer holds")
        print("    - Different entry confirmation filters")

    # ── Save ──
    if args.save:
        save_path = ROOT / "research" / "track3_tail_engine_results.json"
        save_data = {
            "run_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategy_count": len(TAIL_ENGINE_STRATEGIES),
            "asset_count": len(TARGET_ASSETS),
            "total_tests": len(results),
            "viable_count": len(viable),
            "tail_engine_count": len(tail_engines),
            "results": [
                {k: v for k, v in r.items() if k != "daily_series"}
                for r in results
            ],
            "viable": [
                {k: v for k, v in r.items() if k != "daily_series"}
                for r in viable
            ],
            "tail_engines": [
                {k: v for k, v in r.items() if k != "daily_series"}
                for r in tail_engines
            ],
        }
        with open(save_path, "w") as f:
            json.dump(save_data, f, indent=2)
        print(f"\n  Results saved to {save_path.relative_to(ROOT)}")

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()
