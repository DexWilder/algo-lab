"""Phase 6.3 — Paper Trade Simulation.

Simulates the gated portfolio through prop account rules:
- Regime gate (skip low-vol days)
- Transaction costs (commission + slippage)
- Prop controller enforcement (trailing DD, daily limits, phases)

Tests against Lucid 100K and Generic $50K configs.

Outputs:
- paper_sim_results.json (full accounting)
- paper_sim_equity.csv (daily equity under prop rules)

Usage:
    python3 research/paper_trade_sim/run_paper_sim.py
"""

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime import classify_regimes
from controllers.prop_controller import load_prop_config, PropController

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CONFIGS_DIR = PROJECT_ROOT / "controllers" / "prop_configs"

STRATEGIES = [
    {
        "name": "pb_trend",
        "asset": "MGC",
        "mode": "short",
        "label": "PB-MGC-Short",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
    {
        "name": "orb_009",
        "asset": "MGC",
        "mode": "long",
        "label": "ORB-009 MGC-Long",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
]

CONFIGS_TO_TEST = [
    {"path": CONFIGS_DIR / "lucid_100k.json", "label": "Lucid 100K"},
    {"path": CONFIGS_DIR / "generic.json", "label": "Generic $50K"},
]


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


def get_gated_portfolio_trades():
    """Run both strategies with regime gate and costs, return combined trades_df."""
    all_trades = []

    for strat in STRATEGIES:
        mod = load_strategy(strat["name"])
        df = load_data(strat["asset"])
        df_regime = classify_regimes(df)

        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = strat["tick_size"]

        sig = inspect.signature(mod.generate_signals)
        if "asset" in sig.parameters:
            signals = mod.generate_signals(df_regime, asset=strat["asset"])
        else:
            signals = mod.generate_signals(df_regime)

        # Apply regime gate
        signals = signals.copy()
        low_mask = df_regime["regime"] == "low"
        signals.loc[low_mask, "signal"] = 0

        result = run_backtest(
            df_regime, signals,
            mode=strat["mode"],
            point_value=strat["point_value"],
            symbol=strat["asset"],
        )

        trades = result["trades_df"]
        if not trades.empty:
            trades = trades.copy()
            trades["strategy"] = strat["label"]
            all_trades.append(trades)
            print(f"    {strat['label']}: {len(trades)} trades, PnL=${trades['pnl'].sum():,.2f}")

    if all_trades:
        combined = pd.concat(all_trades, ignore_index=True)
        # Sort by exit_time for chronological processing
        combined = combined.sort_values("exit_time").reset_index(drop=True)
        return combined
    return pd.DataFrame()


def run_prop_simulation(trades_df, config_path, label):
    """Run trades through a prop controller and report results."""
    config = load_prop_config(config_path)
    ctrl = PropController(config)

    result = ctrl.simulate(trades_df)

    print(f"\n  {'─' * 60}")
    print(f"  {label} ({config.name})")
    print(f"  Account: ${config.account_size:,.0f} | Trailing DD: ${config.trailing_drawdown:,.0f}")
    if config.lock_profit:
        print(f"  Lock at: ${config.lock_profit:,.0f}")
    print(f"  {'─' * 60}")

    print(f"  Passed: {'YES' if result['passed'] else 'NO'}")
    if result['busted']:
        print(f"  BUSTED on: {result['bust_date']}")
    print(f"  Final equity: ${result['final_equity']:,.2f}")
    print(f"  Final profit: ${result['final_profit']:,.2f}")
    print(f"  Trailing floor: ${result['trailing_floor_final']:,.2f}")
    print(f"  EOD HWM: ${result['eod_hwm']:,.2f}")
    print(f"  Locked: {'YES' if result['locked'] else 'NO'}")
    if result['locked']:
        print(f"  Lock date: {result['lock_date']}")
    print(f"  Trades: {result['total_trades_executed']}/{result['total_trades_input']}")
    print(f"  Skipped total: {result['skipped_trades']}")
    print(f"  Skipped (daily loss): {result['skipped_by_daily_loss']}")
    print(f"  Skipped (contract cap): {result['skipped_by_contract_cap']}")
    print(f"  Halted days: {len(result['halted_days'])}")

    if result['phase_transitions']:
        print(f"\n  Phase Transitions:")
        for pt in result['phase_transitions']:
            print(f"    {pt['from']} → {pt['to']} on {pt['date']} (profit: ${pt['profit_at_transition']:,.2f})")

    if result['halted_days']:
        print(f"\n  Halted Days:")
        for hd in result['halted_days'][:10]:  # show first 10
            print(f"    {hd}")
        if len(result['halted_days']) > 10:
            print(f"    ... and {len(result['halted_days'])-10} more")

    # Monthly pass/fail summary
    daily = result['daily_summaries']
    if daily:
        daily_df = pd.DataFrame(daily)
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        daily_df['month'] = daily_df['date'].dt.to_period('M')

        monthly = daily_df.groupby('month').agg(
            pnl=('day_pnl', 'sum'),
            trades_taken=('trades_taken', 'sum'),
            trades_skipped=('trades_skipped', 'sum'),
            halted=('halted', 'sum'),
        )

        print(f"\n  Monthly Summary:")
        print(f"  {'Month':<10} {'PnL':>10} {'Trades':>8} {'Skipped':>9} {'Halted':>8}")
        print(f"  {'─' * 50}")
        for idx, row in monthly.iterrows():
            status = "PASS" if row['pnl'] > 0 else "FAIL"
            print(f"  {str(idx):<10} ${row['pnl']:>9.2f} {row['trades_taken']:>8} "
                  f"{row['trades_skipped']:>9} {row['halted']:>8}  {status}")

        profitable = (monthly['pnl'] > 0).sum()
        total = len(monthly)
        print(f"\n  Monthly pass rate: {profitable}/{total} ({profitable/total*100:.0f}%)")

    # Notes
    if result['notes']:
        print(f"\n  Notes:")
        for note in result['notes']:
            print(f"    {note}")

    return result


def main():
    print("=" * 70)
    print("  PHASE 6.3 — PAPER TRADE SIMULATION")
    print("  (Regime-Gated Portfolio + Prop Rules)")
    print("=" * 70)

    # ── Get gated portfolio trades ───────────────────────────────────────────
    print("\n  Loading gated portfolio trades...")
    trades_df = get_gated_portfolio_trades()
    print(f"\n  Combined: {len(trades_df)} trades, PnL=${trades_df['pnl'].sum():,.2f}")

    # ── Run through each prop config ─────────────────────────────────────────
    all_results = {}

    for cfg in CONFIGS_TO_TEST:
        result = run_prop_simulation(trades_df, cfg["path"], cfg["label"])

        # Serialize for JSON (drop DataFrame)
        serializable = {k: v for k, v in result.items() if k != "filtered_trades_df"}
        serializable["filtered_trades_count"] = len(result["filtered_trades_df"])
        all_results[cfg["label"]] = serializable

    # ── Save ─────────────────────────────────────────────────────────────────
    with open(OUTPUT_DIR / "paper_sim_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # Save equity curve from Lucid config
    lucid_result = all_results.get("Lucid 100K", {})
    if lucid_result.get("daily_summaries"):
        eq_df = pd.DataFrame(lucid_result["daily_summaries"])
        eq_df.to_csv(OUTPUT_DIR / "paper_sim_equity.csv", index=False)

    print(f"\n{'=' * 70}")
    print(f"  Saved to: {OUTPUT_DIR}")
    print(f"    paper_sim_results.json")
    print(f"    paper_sim_equity.csv")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
