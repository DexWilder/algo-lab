#!/usr/bin/env python3
"""Track 2 — Strategy Expansion Study

Tests NEW asset-specific strategy families against their target markets.
READ-ONLY research tool. Does NOT modify any frozen execution files.

Strategies tested:
  M2K:  vol_compression_breakout, orb_enhanced
  MCL:  vwap_mean_reversion, atr_expansion_breakout
  ZN:   donchian_trend_breakout, momentum_pullback_trend
  ZB:   donchian_trend_breakout, momentum_pullback_trend

Usage:
    python3 research/track2_strategy_expansion.py
    python3 research/track2_strategy_expansion.py --save
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
from engine.metrics import compute_extended_metrics

PROCESSED_DIR = ROOT / "data" / "processed"
STARTING_CAPITAL = 50_000.0

# ── Asset configs for expansion assets ──────────────────────────────────────

ASSET_CONFIG = {
    "M2K": {"point_value": 5.0, "tick_size": 0.10, "name": "Micro Russell 2000"},
    "MCL": {"point_value": 100.0, "tick_size": 0.01, "name": "Micro Crude Oil"},
    "ZN":  {"point_value": 1000.0, "tick_size": 0.015625, "name": "10-Year Treasury Note"},
    "ZB":  {"point_value": 1000.0, "tick_size": 0.03125, "name": "30-Year Treasury Bond"},
    # Core assets for correlation baseline
    "MES": {"point_value": 5.0, "tick_size": 0.25, "name": "Micro E-mini S&P 500"},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25, "name": "Micro E-mini Nasdaq-100"},
    "MGC": {"point_value": 10.0, "tick_size": 0.10, "name": "Micro Gold"},
}

# ── Strategy × Asset test matrix ────────────────────────────────────────────

TEST_MATRIX = [
    # M2K strategies
    {"strategy": "vol_compression_breakout", "asset": "M2K", "modes": ["long", "short"]},
    {"strategy": "orb_enhanced",             "asset": "M2K", "modes": ["long", "short"]},
    # MCL strategies
    {"strategy": "vwap_mean_reversion",      "asset": "MCL", "modes": ["long", "short"]},
    {"strategy": "atr_expansion_breakout",   "asset": "MCL", "modes": ["long", "short"]},
    # ZN strategies
    {"strategy": "donchian_trend_breakout",  "asset": "ZN",  "modes": ["long", "short"]},
    {"strategy": "momentum_pullback_trend",  "asset": "ZN",  "modes": ["long", "short"]},
    # ZB strategies
    {"strategy": "donchian_trend_breakout",  "asset": "ZB",  "modes": ["long", "short"]},
    {"strategy": "momentum_pullback_trend",  "asset": "ZB",  "modes": ["long", "short"]},
]

# Also test new strategies on their "wrong" assets to check generality
CROSS_TESTS = [
    {"strategy": "vol_compression_breakout", "asset": "MCL", "modes": ["long", "short"]},
    {"strategy": "vol_compression_breakout", "asset": "ZN",  "modes": ["long"]},
    {"strategy": "atr_expansion_breakout",   "asset": "M2K", "modes": ["long", "short"]},
    {"strategy": "vwap_mean_reversion",      "asset": "M2K", "modes": ["long", "short"]},
]


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    csv = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv.exists():
        raise FileNotFoundError(f"Data file not found: {csv}")
    df = pd.read_csv(csv)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def run_test(strategy_name: str, asset: str, mode: str) -> dict:
    """Run a single strategy/asset/mode backtest and return summary."""
    mod = load_strategy(strategy_name)
    config = ASSET_CONFIG[asset]
    df = load_data(asset)

    # Patch tick size if module has it
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]

    # Generate signals — check if asset kwarg is accepted
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
            "strategy": strategy_name,
            "asset": asset,
            "mode": mode,
            "label": f"{strategy_name}-{asset}-{mode.title()}",
            "trades": 0,
            "pf": 0.0,
            "sharpe": 0.0,
            "pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "max_dd": 0.0,
            "daily_series": pd.Series(dtype=float),
        }

    # Compute metrics
    equity = STARTING_CAPITAL + trades["pnl"].cumsum()
    hwm = equity.cummax()
    dd = hwm - equity
    max_dd = dd.max()

    winners = trades[trades["pnl"] > 0]
    losers = trades[trades["pnl"] <= 0]
    gross_profit = winners["pnl"].sum() if len(winners) > 0 else 0
    gross_loss = abs(losers["pnl"].sum()) if len(losers) > 0 else 0.001
    pf = gross_profit / gross_loss

    # Daily PnL series for correlation
    trades_c = trades.copy()
    trades_c["exit_date"] = pd.to_datetime(trades_c["exit_time"]).dt.date
    daily_pnl = trades_c.groupby("exit_date")["pnl"].sum()

    # Sharpe (annualized from daily)
    if len(daily_pnl) > 1 and daily_pnl.std() > 0:
        sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    return {
        "strategy": strategy_name,
        "asset": asset,
        "mode": mode,
        "label": f"{strategy_name}-{asset}-{mode.title()}",
        "trades": len(trades),
        "pf": round(pf, 2),
        "sharpe": round(sharpe, 2),
        "pnl": round(trades["pnl"].sum(), 2),
        "win_rate": round(len(winners) / len(trades) * 100, 1),
        "avg_pnl": round(trades["pnl"].mean(), 2),
        "max_dd": round(max_dd, 2),
        "daily_series": daily_pnl,
    }


def compute_correlation(series_a: pd.Series, series_b: pd.Series) -> float:
    """Correlation between two daily PnL series."""
    combined = pd.DataFrame({"a": series_a, "b": series_b}).fillna(0)
    if len(combined) < 10:
        return 0.0
    return round(combined["a"].corr(combined["b"]), 3)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Track 2 Strategy Expansion")
    parser.add_argument("--save", action="store_true", help="Save results JSON")
    parser.add_argument("--cross", action="store_true", help="Include cross-asset tests")
    args = parser.parse_args()

    tests = TEST_MATRIX.copy()
    if args.cross:
        tests.extend(CROSS_TESTS)

    print()
    print("=" * 70)
    print("  TRACK 2 — STRATEGY EXPANSION STUDY")
    print("  Asset-specific strategy families")
    print("=" * 70)

    # ── Run all tests ──
    results = []
    current_asset = None

    for test in tests:
        strategy = test["strategy"]
        asset = test["asset"]

        if asset != current_asset:
            current_asset = asset
            print(f"\n  {asset} ({ASSET_CONFIG[asset]['name']})")
            print("  " + "─" * 50)

        for mode in test["modes"]:
            label = f"{strategy}-{asset}-{mode.title()}"
            try:
                r = run_test(strategy, asset, mode)
                results.append(r)
                flag = "★" if r["pf"] >= 1.3 and r["trades"] >= 30 else " "
                print(f"    {flag} {label}... {r['trades']} trades, "
                      f"PF={r['pf']:.2f}, Sharpe={r['sharpe']:.2f}, "
                      f"PnL=${r['pnl']:,.0f}, WR={r['win_rate']}%")
            except Exception as e:
                print(f"    ✗ {label}... ERROR: {e}")
                results.append({
                    "strategy": strategy, "asset": asset, "mode": mode,
                    "label": label, "trades": 0, "pf": 0, "sharpe": 0,
                    "pnl": 0, "win_rate": 0, "avg_pnl": 0, "max_dd": 0,
                    "daily_series": pd.Series(dtype=float),
                })

    # ── Filter viable combos ──
    viable = [r for r in results if r["pf"] >= 1.3 and r["trades"] >= 30]

    print()
    print("=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)

    # ── Strategy × Asset matrix ──
    print("\n  STRATEGY × ASSET MATRIX")
    print("  " + "═" * 66)

    # Group by asset
    by_asset = {}
    for r in results:
        by_asset.setdefault(r["asset"], []).append(r)

    for asset, asset_results in by_asset.items():
        print(f"\n  {asset} ({ASSET_CONFIG[asset]['name']}):")
        for r in asset_results:
            flag = "★" if r in viable else " "
            print(f"    {flag} {r['strategy']}-{r['mode'].title():5s}  "
                  f"PF={r['pf']:5.2f}  Sharpe={r['sharpe']:6.2f}  "
                  f"Trades={r['trades']:4d}  PnL=${r['pnl']:>10,.0f}  "
                  f"WR={r['win_rate']:5.1f}%  MaxDD=${r['max_dd']:>8,.0f}")

    # ── Viable combos ──
    print(f"\n  VIABLE COMBOS (PF >= 1.3, trades >= 30): {len(viable)}")
    print("  " + "─" * 66)

    if not viable:
        print("    None found.")
    else:
        for r in sorted(viable, key=lambda x: x["sharpe"], reverse=True):
            print(f"    {r['label']:40s}  PF={r['pf']:5.2f}  "
                  f"Sharpe={r['sharpe']:6.2f}  Trades={r['trades']:4d}  "
                  f"PnL=${r['pnl']:>10,.0f}")

    # ── Correlation analysis for viable combos ──
    if viable:
        # Load baseline portfolio daily PnL
        print(f"\n  CORRELATION vs EXISTING PORTFOLIO")
        print("  " + "─" * 66)

        # Run existing portfolio strategies for correlation
        from engine.regime_engine import RegimeEngine
        regime_engine = RegimeEngine()

        CORE_STRATS = [
            {"name": "pb_trend", "asset": "MGC", "mode": "short"},
            {"name": "orb_009", "asset": "MGC", "mode": "long"},
            {"name": "vwap_trend", "asset": "MNQ", "mode": "long"},
            {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short"},
            {"name": "bb_equilibrium", "asset": "MGC", "mode": "long"},
        ]

        core_daily = {}
        for cs in CORE_STRATS:
            try:
                cr = run_test(cs["name"], cs["asset"], cs["mode"])
                core_daily[f"{cs['name']}-{cs['asset']}"] = cr["daily_series"]
            except Exception:
                pass

        for v in viable:
            print(f"\n    {v['label']}:")
            for core_name, core_series in core_daily.items():
                corr = compute_correlation(v["daily_series"], core_series)
                flag = "*** HIGH ***" if abs(corr) > 0.3 else ""
                print(f"      vs {core_name:35s}  r={corr:+.3f} {flag}")

    # ── Recommendations ──
    print(f"\n  RECOMMENDATIONS")
    print("  " + "─" * 66)

    if viable:
        print("  Promote to validation battery:")
        for r in sorted(viable, key=lambda x: x["sharpe"], reverse=True):
            print(f"    → {r['label']} (PF={r['pf']}, Sharpe={r['sharpe']}, {r['trades']} trades)")
    else:
        print("    No strategies met the viability threshold.")
        print("    Consider parameter tuning or alternative strategy designs.")

    # By asset - best performer even if not viable
    print(f"\n  BEST PER ASSET (even if below threshold):")
    for asset in ["M2K", "MCL", "ZN", "ZB"]:
        asset_r = [r for r in results if r["asset"] == asset and r["trades"] > 0]
        if asset_r:
            best = max(asset_r, key=lambda x: x["pf"])
            status = "VIABLE" if best in viable else "below threshold"
            print(f"    {asset}: {best['label']} — PF={best['pf']}, "
                  f"Sharpe={best['sharpe']}, {best['trades']} trades ({status})")

    # ── Save results ──
    if args.save:
        save_path = ROOT / "research" / "track2_expansion_results.json"
        save_data = {
            "run_date": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": [
                {k: v for k, v in r.items() if k != "daily_series"}
                for r in results
            ],
            "viable": [
                {k: v for k, v in r.items() if k != "daily_series"}
                for r in viable
            ],
        }
        with open(save_path, "w") as f:
            json.dump(save_data, f, indent=2)
        print(f"\n  Results saved to {save_path}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
