"""Phase 10 — New Parent Strategy Evaluation Script.

Runs full evaluation pipeline for trend-following candidates:
1. Backtest across 3 assets × 3 modes
2. Regime breakdown (including GRINDING analysis)
3. GRINDING-filtered metrics
4. Portfolio fitness scoring
5. Correlation with existing portfolio
6. Trade duration fingerprint

Usage:
    python3 research/phase10_eval.py --strategy donchian_trend
    python3 research/phase10_eval.py --strategy keltner_channel
    python3 research/phase10_eval.py --strategy donchian_trend --grinding-only
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_strategy(strategy_name: str):
    """Load a strategy module by name."""
    module_path = PROJECT_ROOT / "strategies" / strategy_name / "strategy.py"
    if not module_path.exists():
        print(f"ERROR: Strategy not found at {module_path}")
        sys.exit(1)
    spec = importlib.util.spec_from_file_location(strategy_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_full_evaluation(strategy_name: str, grinding_only: bool = False):
    """Run complete evaluation pipeline."""
    print(f"\n{'='*70}")
    print(f"  PHASE 10 EVALUATION: {strategy_name.upper()}")
    if grinding_only:
        print(f"  MODE: GRINDING-ONLY FILTER")
    print(f"{'='*70}")

    strategy = load_strategy(strategy_name)
    engine = RegimeEngine()

    assets = ["MES", "MNQ", "MGC"]
    modes = ["both", "long", "short"]
    all_results = {}
    all_trades = {}

    # ── Step 1: Run backtests ────────────────────────────────────────────────
    print(f"\n  Step 1: Running backtests...")
    for symbol in assets:
        data_path = PROCESSED_DIR / f"{symbol}_5m.csv"
        if not data_path.exists():
            print(f"  SKIP: No data for {symbol}")
            continue

        config = ASSET_CONFIG[symbol]
        df = pd.read_csv(data_path)
        df["datetime"] = pd.to_datetime(df["datetime"])

        # Patch tick size
        strategy.TICK_SIZE = config["tick_size"]

        # Generate signals
        signals_df = strategy.generate_signals(df)

        # Get regime data for this asset
        regime_daily = engine.get_daily_regimes(df)

        for mode in modes:
            result = run_backtest(
                df, signals_df,
                mode=mode,
                point_value=config["point_value"],
                symbol=symbol,
            )
            trades_df = result["trades_df"]

            if trades_df.empty:
                continue

            # Merge regime data onto trades
            trades_df["entry_date"] = pd.to_datetime(trades_df["entry_time"]).dt.date
            regime_daily["_date"] = pd.to_datetime(regime_daily["_date"]).values
            regime_daily["_date_date"] = pd.to_datetime(regime_daily["_date"]).dt.date

            trades_merged = trades_df.merge(
                regime_daily[["_date_date", "vol_regime", "trend_regime", "rv_regime",
                              "trend_persistence", "persistence_score", "composite_regime"]],
                left_on="entry_date",
                right_on="_date_date",
                how="left",
            )

            # If GRINDING-only, filter trades
            if grinding_only:
                grinding_trades = trades_merged[trades_merged["trend_persistence"] == "GRINDING"]
                if len(grinding_trades) == 0:
                    continue
                # Rebuild equity curve from filtered trades
                filtered_pnl = grinding_trades["pnl"].values
                equity = pd.Series(
                    50000.0 + np.cumsum(np.concatenate([[0], filtered_pnl])),
                    name="equity"
                )
                trades_df_eval = grinding_trades.copy()
                equity_eval = equity
            else:
                trades_df_eval = trades_merged
                equity_eval = result["equity_curve"]

            # Compute metrics
            metrics = compute_extended_metrics(
                trades_df_eval, equity_eval, config["point_value"]
            )
            metrics["symbol"] = symbol
            metrics["mode"] = mode

            key = f"{symbol}-{mode}"
            all_results[key] = metrics
            all_trades[key] = trades_df_eval

    if not all_results:
        print("  No results generated!")
        return

    # ── Step 2: Print baseline results ───────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  BASELINE RESULTS{' (GRINDING-ONLY)' if grinding_only else ''}")
    print(f"{'='*70}")
    print(f"  {'Combo':<12} {'Trades':>7} {'PF':>7} {'WR%':>7} {'Sharpe':>8} "
          f"{'PnL':>10} {'MaxDD':>10} {'MedHold':>8}")
    print(f"  {'-'*12} {'-'*7} {'-'*7} {'-'*7} {'-'*8} {'-'*10} {'-'*10} {'-'*8}")

    for key in sorted(all_results.keys()):
        m = all_results[key]
        tc = m["trade_count"]
        if tc == 0:
            continue
        med_hold = m.get("median_trade_duration_bars", 0)
        print(f"  {key:<12} {tc:>7} {m['profit_factor']:>7.2f} "
              f"{m['win_rate']*100:>6.1f}% {m['sharpe']:>8.2f} "
              f"{'${:,.0f}'.format(m['total_pnl']):>10} "
              f"{'${:,.0f}'.format(m['max_drawdown']):>10} "
              f"{med_hold:>7.0f}b")

    # ── Step 3: Find best combo ──────────────────────────────────────────────
    # Best = highest PF with ≥30 trades
    qualified = {k: v for k, v in all_results.items() if v["trade_count"] >= 30}
    if not qualified:
        print("\n  No qualified combos (≥30 trades)")
        return

    best_key = max(qualified, key=lambda k: qualified[k]["profit_factor"])
    best = qualified[best_key]
    print(f"\n  BEST COMBO: {best_key} — PF={best['profit_factor']}, "
          f"{best['trade_count']} trades, Sharpe={best['sharpe']}")

    # ── Step 4: Regime breakdown for best combo ──────────────────────────────
    if best_key in all_trades and not grinding_only:
        print(f"\n{'='*70}")
        print(f"  REGIME BREAKDOWN — {best_key}")
        print(f"{'='*70}")

        trades = all_trades[best_key]

        # Full composite + RV breakdown
        trades["regime_cell"] = trades["composite_regime"] + "_" + trades["rv_regime"]
        regime_groups = trades.groupby("regime_cell").agg(
            trades=("pnl", "count"),
            pnl=("pnl", "sum"),
            win_rate=("pnl", lambda x: (x > 0).mean()),
        ).sort_values("pnl", ascending=False)

        print(f"\n  {'Regime Cell':<35} {'Trades':>7} {'PnL':>10} {'WR%':>7}")
        print(f"  {'-'*35} {'-'*7} {'-'*10} {'-'*7}")
        for cell, row in regime_groups.iterrows():
            print(f"  {cell:<35} {int(row['trades']):>7} "
                  f"{'${:,.0f}'.format(row['pnl']):>10} "
                  f"{row['win_rate']*100:>6.1f}%")

        # TARGET CELL: HIGH_VOL_TRENDING_LOW_RV
        target_mask = (
            (trades["vol_regime"] == "HIGH_VOL") &
            (trades["trend_regime"] == "TRENDING") &
            (trades["rv_regime"] == "LOW_RV")
        )
        target_trades = trades[target_mask]
        print(f"\n  TARGET CELL (HIGH_VOL_TRENDING_LOW_RV):")
        if len(target_trades) > 0:
            print(f"    Trades: {len(target_trades)}")
            print(f"    PnL: ${target_trades['pnl'].sum():,.0f}")
            print(f"    Win rate: {(target_trades['pnl'] > 0).mean()*100:.1f}%")
            print(f"    Avg PnL: ${target_trades['pnl'].mean():,.0f}")
        else:
            print(f"    No trades in this cell")

        # GRINDING analysis
        print(f"\n  TREND PERSISTENCE BREAKDOWN:")
        for persist in ["GRINDING", "CHOPPY"]:
            mask = trades["trend_persistence"] == persist
            subset = trades[mask]
            if len(subset) > 0:
                print(f"    {persist}: {len(subset)} trades, "
                      f"PnL=${subset['pnl'].sum():,.0f}, "
                      f"WR={( subset['pnl'] > 0).mean()*100:.1f}%")

    # ── Step 5: Portfolio correlation ────────────────────────────────────────
    if best_key in all_trades:
        print(f"\n{'='*70}")
        print(f"  PORTFOLIO CORRELATION")
        print(f"{'='*70}")

        # Load existing strategy trades for correlation
        symbol = best_key.split("-")[0]
        existing_strats = {
            "PB-MGC-Short": ("pb_trend", "MGC", "short"),
            "ORB-MGC-Long": ("orb_009", "MGC", "long"),
        }

        candidate_trades = all_trades[best_key].copy()
        candidate_trades["date"] = pd.to_datetime(candidate_trades["entry_time"]).dt.date
        cand_daily = candidate_trades.groupby("date")["pnl"].sum()

        for strat_label, (strat_name, strat_asset, strat_mode) in existing_strats.items():
            strat_path = PROJECT_ROOT / "strategies" / strat_name / "strategy.py"
            if not strat_path.exists():
                continue

            data_path = PROCESSED_DIR / f"{strat_asset}_5m.csv"
            if not data_path.exists():
                continue

            strat_config = ASSET_CONFIG[strat_asset]
            strat_df = pd.read_csv(data_path)
            strat_df["datetime"] = pd.to_datetime(strat_df["datetime"])

            strat_mod = load_strategy(strat_name)
            strat_mod.TICK_SIZE = strat_config["tick_size"]
            strat_signals = strat_mod.generate_signals(strat_df)

            strat_result = run_backtest(
                strat_df, strat_signals,
                mode=strat_mode,
                point_value=strat_config["point_value"],
                symbol=strat_asset,
            )

            if strat_result["trades_df"].empty:
                continue

            strat_trades = strat_result["trades_df"]
            strat_trades["date"] = pd.to_datetime(strat_trades["exit_time"]).dt.date
            strat_daily = strat_trades.groupby("date")["pnl"].sum()

            # Align on common dates
            common = cand_daily.index.intersection(strat_daily.index)
            if len(common) > 5:
                corr = cand_daily.loc[common].corr(strat_daily.loc[common])
                print(f"  vs {strat_label}: r = {corr:.3f}")
            else:
                print(f"  vs {strat_label}: insufficient overlap")

    # ── Step 6: Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  SUMMARY — {strategy_name.upper()}{' (GRINDING-ONLY)' if grinding_only else ''}")
    print(f"{'='*70}")
    print(f"  Best combo: {best_key}")
    print(f"  PF: {best['profit_factor']}")
    print(f"  Trades: {best['trade_count']}")
    print(f"  Sharpe: {best['sharpe']}")
    print(f"  PnL: ${best['total_pnl']:,.0f}")
    print(f"  MaxDD: ${best['max_drawdown']:,.0f}")
    print(f"  Win rate: {best['win_rate']*100:.1f}%")
    print(f"  Median hold: {best.get('median_trade_duration_bars', 0):.0f} bars")
    print(f"  Avg hold: {best.get('avg_trade_duration_bars', 0):.0f} bars")
    print()

    return all_results, all_trades


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 10 Strategy Evaluator")
    parser.add_argument("--strategy", required=True, help="Strategy directory name")
    parser.add_argument("--grinding-only", action="store_true",
                        help="Filter to GRINDING persistence only")
    args = parser.parse_args()

    run_full_evaluation(args.strategy, args.grinding_only)
