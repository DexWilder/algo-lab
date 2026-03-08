"""Hardened baseline runner — re-runs core strategies WITH transaction costs.

Compares gross (zero friction) vs net (commission + slippage) results.
Outputs to backtests/hardened_baselines/.

Usage:
    python3 backtests/run_hardened_baselines.py
"""

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest, SYMBOL_DEFAULTS
from backtests.run_baseline import compute_extended_metrics

OUTPUT_DIR = PROJECT_ROOT / "backtests" / "hardened_baselines"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── Strategies to test ────────────────────────────────────────────────────────

TARGETS = [
    {"strategy": "pb_trend",  "asset": "MGC", "mode": "short", "label": "PB-MGC-Short"},
    {"strategy": "pb_trend",  "asset": "MNQ", "mode": "long",  "label": "PB-MNQ-Long"},
    {"strategy": "orb_009",   "asset": "MGC", "mode": "long",  "label": "ORB009-MGC-Long"},
    {"strategy": "vwap_006",  "asset": "MES", "mode": "long",  "label": "VWAP006-MES-Long"},
]

ASSET_CONFIG = {
    "MES": {"point_value": 5.0,  "tick_size": 0.25},
    "MNQ": {"point_value": 2.0,  "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
}


def load_strategy(name):
    path = PROJECT_ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset):
    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def run_one(strategy_name, asset, mode, with_costs=False):
    """Run a single strategy/asset/mode combo. Returns (metrics, trades_df)."""
    mod = load_strategy(strategy_name)
    df = load_data(asset)
    config = ASSET_CONFIG[asset]

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    if "asset" in sig.parameters:
        signals = mod.generate_signals(df, asset=asset)
    else:
        signals = mod.generate_signals(df)

    kwargs = {
        "mode": mode,
        "point_value": config["point_value"],
    }
    if with_costs:
        kwargs["symbol"] = asset

    result = run_backtest(df, signals, **kwargs)
    metrics = compute_extended_metrics(
        result["trades_df"], result["equity_curve"], config["point_value"]
    )
    return metrics, result["trades_df"], result["stats"]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("  HARDENED BASELINES — Gross vs Net (with transaction costs)")
    print("=" * 70)

    rows = []
    all_trades = {}

    for target in TARGETS:
        label = target["label"]
        print(f"\n  {label}...")

        # Gross (no costs)
        m_gross, trades_gross, stats_gross = run_one(
            target["strategy"], target["asset"], target["mode"], with_costs=False
        )
        # Net (with costs)
        m_net, trades_net, stats_net = run_one(
            target["strategy"], target["asset"], target["mode"], with_costs=True
        )

        costs = stats_net["costs"]
        pnl_diff = m_net["total_pnl"] - m_gross["total_pnl"]

        row = {
            "strategy": label,
            "asset": target["asset"],
            "mode": target["mode"],
            "trades": m_gross["trade_count"],
            # Gross
            "gross_pf": m_gross["profit_factor"],
            "gross_sharpe": m_gross["sharpe"],
            "gross_pnl": m_gross["total_pnl"],
            "gross_maxdd": m_gross["max_drawdown"],
            "gross_wr": round(m_gross["win_rate"] * 100, 1),
            "gross_exp": m_gross["expectancy"],
            # Net
            "net_pf": m_net["profit_factor"],
            "net_sharpe": m_net["sharpe"],
            "net_pnl": m_net["total_pnl"],
            "net_maxdd": m_net["max_drawdown"],
            "net_wr": round(m_net["win_rate"] * 100, 1),
            "net_exp": m_net["expectancy"],
            # Cost impact
            "total_friction": costs["total_friction"],
            "pnl_impact": round(pnl_diff, 2),
            "pnl_impact_pct": round(pnl_diff / max(abs(m_gross["total_pnl"]), 0.01) * 100, 1),
            "cost_per_trade": round(costs["total_friction"] / max(m_gross["trade_count"], 1), 2),
        }
        rows.append(row)

        # Save net trades
        trades_net.to_csv(OUTPUT_DIR / f"{label}_trades.csv", index=False)
        all_trades[label] = {"gross": m_gross, "net": m_net, "costs": costs}

        print(f"    Gross: PF={m_gross['profit_factor']}, Sharpe={m_gross['sharpe']}, "
              f"PnL=${m_gross['total_pnl']:,.2f}")
        print(f"    Net:   PF={m_net['profit_factor']}, Sharpe={m_net['sharpe']}, "
              f"PnL=${m_net['total_pnl']:,.2f}")
        print(f"    Cost:  ${abs(pnl_diff):,.2f} total friction "
              f"({abs(row['pnl_impact_pct']):.1f}% of gross PnL), "
              f"${row['cost_per_trade']:.2f}/trade")

    # Save summary
    summary = pd.DataFrame(rows)
    summary.to_csv(OUTPUT_DIR / "gross_vs_net.csv", index=False)

    # Save full metrics JSON
    with open(OUTPUT_DIR / "hardened_metrics.json", "w") as f:
        json.dump(all_trades, f, indent=2, default=str)

    # Print final table
    print(f"\n{'='*70}")
    print("  GROSS vs NET COMPARISON")
    print(f"{'='*70}")
    print(f"  {'Strategy':<20} {'Trades':>6} {'Gross PF':>9} {'Net PF':>9} "
          f"{'Gross PnL':>10} {'Net PnL':>10} {'Friction':>9} {'Impact%':>8}")
    print(f"  {'-'*20} {'-'*6} {'-'*9} {'-'*9} {'-'*10} {'-'*10} {'-'*9} {'-'*8}")
    for r in rows:
        print(f"  {r['strategy']:<20} {r['trades']:>6} "
              f"{r['gross_pf']:>9.3f} {r['net_pf']:>9.3f} "
              f"{'${:,.0f}'.format(r['gross_pnl']):>10} "
              f"{'${:,.0f}'.format(r['net_pnl']):>10} "
              f"{'${:,.0f}'.format(r['total_friction']):>9} "
              f"{r['pnl_impact_pct']:>7.1f}%")

    # Verdict
    print(f"\n  VERDICT:")
    for r in rows:
        status = "SURVIVES" if r["net_pf"] > 1.0 else "KILLED BY COSTS"
        print(f"    {r['strategy']}: {status} (Net PF={r['net_pf']})")

    print(f"\n  Results saved to: {OUTPUT_DIR}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
