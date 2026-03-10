"""Baseline backtest runner for ALGO-CORE-TREND-001 (Lucid v6.3).

Processes TradingView CSV exports, runs the Lucid strategy on each asset,
generates full performance reports, and saves to backtests/lucid_baseline/.

Usage:
    python3 backtests/run_baseline.py              # run all assets found in data/raw/
    python3 backtests/run_baseline.py --asset MES   # run single asset
    python3 backtests/run_baseline.py --skip-load   # skip TV CSV processing (use existing)

Prerequisites:
    Drop TradingView 5m CSV exports into data/raw/:
      MES_5m_TV.csv   (MES1! 5-minute chart export)
      MNQ_5m_TV.csv   (MNQ1! 5-minute chart export)
      MGC_5m_TV.csv   (MGC1! 5-minute chart export)
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.load_tv import load_and_normalize, save_processed
from engine.backtest import run_backtest
from engine.metrics import compute_extended_metrics  # noqa: F401 — re-exported for backwards compat

# ── Asset Configuration ──────────────────────────────────────────────────────

ASSET_CONFIG = {
    "MES": {
        "point_value": 5.0,
        "tick_size": 0.25,
        "name": "Micro E-mini S&P 500",
    },
    "MNQ": {
        "point_value": 2.0,
        "tick_size": 0.25,
        "name": "Micro E-mini Nasdaq-100",
    },
    "MGC": {
        "point_value": 10.0,
        "tick_size": 0.10,
        "name": "Micro Gold",
    },
}

RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "backtests" / "lucid_baseline"
STRATEGY_DIR = PROJECT_ROOT / "strategies" / "lucid-100k"


# ── Strategy Loading ─────────────────────────────────────────────────────────

def load_strategy():
    """Load the Lucid 100K strategy module."""
    module_path = STRATEGY_DIR / "strategy.py"
    spec = importlib.util.spec_from_file_location("lucid_100k", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Main Runner ──────────────────────────────────────────────────────────────

def find_processed_data() -> dict[str, Path]:
    """Find processed 5m CSVs, keyed by symbol."""
    found = {}
    if PROCESSED_DIR.exists():
        for p in PROCESSED_DIR.glob("*_5m.csv"):
            symbol = p.stem.split("_")[0].upper()
            found[symbol] = p
    return found


def process_raw_csvs():
    """Run TV CSV loader on all raw files."""
    raw_files = sorted(RAW_DIR.glob("*.csv"))
    if not raw_files:
        print(f"\nNo CSV files in {RAW_DIR}")
        print("Export 5m charts from TradingView and drop them here:")
        print("  MES_5m_TV.csv")
        print("  MNQ_5m_TV.csv")
        print("  MGC_5m_TV.csv")
        return

    for f in raw_files:
        name = f.stem.upper()
        if "MES" in name:
            symbol = "MES"
        elif "MNQ" in name:
            symbol = "MNQ"
        elif "MGC" in name:
            symbol = "MGC"
        elif "ES" in name:
            symbol = "MES"
        elif "NQ" in name:
            symbol = "MNQ"
        elif "GC" in name:
            symbol = "MGC"
        else:
            print(f"  SKIP: Can't detect symbol from '{f.name}'")
            continue

        print(f"\n  Processing {f.name} → {symbol} 5m")
        df = load_and_normalize(f, symbol)
        save_processed(df, symbol)
        print(f"  ✓ {len(df):,} bars ({df['datetime'].dt.date.nunique()} days)")


def run_single_asset(
    symbol: str,
    data_path: Path,
    strategy_module,
    modes: list[str] = ("both", "long", "short"),
) -> dict:
    """Run backtest for a single asset across modes. Returns results dict."""
    config = ASSET_CONFIG.get(symbol, ASSET_CONFIG["MES"])
    print(f"\n{'='*60}")
    print(f"  {symbol} — {config['name']}")
    print(f"  Point value: ${config['point_value']}/pt  |  Tick: {config['tick_size']}")
    print(f"{'='*60}")

    # Load data
    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    print(f"  Data: {len(df):,} bars  |  {df['datetime'].dt.date.nunique()} days")
    print(f"  Range: {df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]}")

    # Patch strategy tick size for this asset
    strategy_module.TICK_SIZE = config["tick_size"]

    # Generate signals
    signals_df = strategy_module.generate_signals(df)
    sig_counts = signals_df["signal"].value_counts()
    print(f"  Signals: {sig_counts.get(1, 0)} long, {sig_counts.get(-1, 0)} short")

    exit_counts = signals_df["exit_signal"].value_counts()
    print(f"  Exits:   {exit_counts.get(1, 0)} exit-long, {exit_counts.get(-1, 0)} exit-short")

    # Signal type breakdown
    sig_types = signals_df.loc[signals_df["signal"] != 0, "signal_type"].value_counts()
    if len(sig_types) > 0:
        print(f"  Types:   {sig_types.to_dict()}")

    results = {}
    for mode in modes:
        result = run_backtest(
            df, signals_df,
            mode=mode,
            point_value=config["point_value"],
        )
        trades_df = result["trades_df"]
        equity_curve = result["equity_curve"]

        metrics = compute_extended_metrics(
            trades_df, equity_curve, config["point_value"],
        )
        metrics["symbol"] = symbol
        metrics["mode"] = mode

        results[mode] = {
            "metrics": metrics,
            "trades_df": trades_df,
            "equity_curve": equity_curve,
        }

        # Print summary
        tc = metrics["trade_count"]
        if tc > 0:
            print(f"\n  [{mode.upper()}] {tc} trades  |  "
                  f"PF={metrics['profit_factor']}  |  "
                  f"WR={metrics['win_rate']*100:.1f}%  |  "
                  f"Sharpe={metrics['sharpe']}  |  "
                  f"PnL=${metrics['total_pnl']:,.2f}  |  "
                  f"MaxDD=${metrics['max_drawdown']:,.2f}")
        else:
            print(f"\n  [{mode.upper()}] No trades")

    return results


def save_results(all_results: dict, timestamp: str):
    """Save all results to backtests/lucid_baseline/."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Summary report
    summary_rows = []
    for symbol, mode_results in all_results.items():
        for mode, data in mode_results.items():
            m = data["metrics"]
            row = {
                "symbol": symbol,
                "mode": mode,
                "trade_count": m["trade_count"],
                "profit_factor": m["profit_factor"],
                "win_rate": m["win_rate"],
                "sharpe": m["sharpe"],
                "expectancy": m["expectancy"],
                "max_drawdown": m["max_drawdown"],
                "max_drawdown_pct": m["max_drawdown_pct"],
                "total_pnl": m["total_pnl"],
                "roi_pct": m["roi_pct"],
                "avg_R": m["avg_R"],
                "avg_trades_per_day": m["avg_trades_per_day"],
                "long_trades": m["long_trades"],
                "short_trades": m["short_trades"],
                "long_win_rate": m["long_win_rate"],
                "short_win_rate": m["short_win_rate"],
                "best_trade": m["best_trade"],
                "worst_trade": m["worst_trade"],
                "max_consecutive_wins": m["max_consecutive_wins"],
                "max_consecutive_losses": m["max_consecutive_losses"],
                "trading_days": m["trading_days"],
            }
            summary_rows.append(row)

    # Save summary CSV
    summary_df = pd.DataFrame(summary_rows)
    summary_path = OUTPUT_DIR / "summary.csv"
    summary_df.to_csv(summary_path, index=False)

    # Save per-asset detail files
    for symbol, mode_results in all_results.items():
        # Save trade logs
        for mode, data in mode_results.items():
            if not data["trades_df"].empty:
                trades_path = OUTPUT_DIR / f"{symbol}_{mode}_trades.csv"
                data["trades_df"].to_csv(trades_path, index=False)

        # Save full metrics JSON
        metrics_path = OUTPUT_DIR / f"{symbol}_metrics.json"
        metrics_out = {}
        for mode, data in mode_results.items():
            metrics_out[mode] = data["metrics"]
        with open(metrics_path, "w") as f:
            json.dump(metrics_out, f, indent=2, default=str)

    # Save run metadata
    meta = {
        "strategy": "lucid-100k",
        "version": "v6.3 (Python v1.0)",
        "roster_target": "ALGO-CORE-TREND-001",
        "run_date": timestamp,
        "assets": list(all_results.keys()),
        "modes": ["both", "long", "short"],
        "engine": "fill-at-next-open",
        "notes": "Baseline run — pure signal logic, no prop rules, no phase sizing",
    }
    with open(OUTPUT_DIR / "run_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n{'='*60}")
    print(f"  Results saved to: {OUTPUT_DIR}")
    print(f"    summary.csv          — cross-asset performance table")
    for symbol in all_results:
        print(f"    {symbol}_metrics.json  — full metrics (all modes)")
        print(f"    {symbol}_*_trades.csv  — trade logs per mode")
    print(f"    run_meta.json        — run metadata")
    print(f"{'='*60}")

    return summary_path


def print_final_summary(all_results: dict):
    """Print a clean final summary table."""
    print(f"\n{'='*60}")
    print(f"  LUCID v6.3 BASELINE — ALGO-CORE-TREND-001")
    print(f"{'='*60}")
    print(f"  {'Asset':<6} {'Mode':<6} {'Trades':>7} {'PF':>7} {'WR%':>7} "
          f"{'Sharpe':>8} {'PnL':>10} {'MaxDD':>10} {'AvgR':>7}")
    print(f"  {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*7} {'-'*8} {'-'*10} {'-'*10} {'-'*7}")

    for symbol in sorted(all_results.keys()):
        for mode in ("both", "long", "short"):
            if mode not in all_results[symbol]:
                continue
            m = all_results[symbol][mode]["metrics"]
            tc = m["trade_count"]
            if tc == 0:
                print(f"  {symbol:<6} {mode:<6} {'—':>7}")
                continue
            print(f"  {symbol:<6} {mode:<6} {tc:>7} "
                  f"{m['profit_factor']:>7.2f} "
                  f"{m['win_rate']*100:>6.1f}% "
                  f"{m['sharpe']:>8.2f} "
                  f"{'${:,.0f}'.format(m['total_pnl']):>10} "
                  f"{'${:,.0f}'.format(m['max_drawdown']):>10} "
                  f"{m['avg_R']:>7.3f}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Lucid v6.3 Baseline Backtest Runner"
    )
    parser.add_argument("--asset", default=None, help="Run single asset (MES, MNQ, MGC)")
    parser.add_argument("--skip-load", action="store_true", help="Skip TV CSV processing")
    parser.add_argument("--modes", default="both,long,short", help="Comma-separated modes")
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",")]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'='*60}")
    print(f"  ALGO-CORE-TREND-001 Baseline Runner")
    print(f"  Strategy: Lucid v6.3 (Python v1.0)")
    print(f"  Time: {timestamp}")
    print(f"{'='*60}")

    # Step 1: Process raw TV CSVs
    if not args.skip_load:
        print("\n  Step 1: Processing TradingView exports...")
        process_raw_csvs()
    else:
        print("\n  Step 1: Skipped (--skip-load)")

    # Step 2: Find processed data
    data_files = find_processed_data()
    if args.asset:
        asset = args.asset.upper()
        if asset not in data_files:
            print(f"\n  ERROR: No processed data for {asset}")
            print(f"  Available: {list(data_files.keys()) or 'none'}")
            print(f"  Drop {asset}_5m_TV.csv into {RAW_DIR} and re-run")
            sys.exit(1)
        data_files = {asset: data_files[asset]}

    if not data_files:
        print(f"\n  No processed data found in {PROCESSED_DIR}")
        print(f"  Drop TradingView CSV exports into {RAW_DIR}:")
        print(f"    MES_5m_TV.csv  MNQ_5m_TV.csv  MGC_5m_TV.csv")
        sys.exit(1)

    print(f"\n  Step 2: Found {len(data_files)} asset(s): {', '.join(sorted(data_files.keys()))}")

    # Step 3: Load strategy
    print(f"\n  Step 3: Loading Lucid v6.3 strategy...")
    strategy_module = load_strategy()
    print(f"  ✓ Strategy loaded")

    # Step 4: Run backtests
    print(f"\n  Step 4: Running backtests...")
    all_results = {}
    for symbol in sorted(data_files.keys()):
        results = run_single_asset(
            symbol, data_files[symbol], strategy_module, modes
        )
        all_results[symbol] = results

    # Step 5: Save results
    print(f"\n  Step 5: Saving results...")
    save_results(all_results, timestamp)

    # Final summary
    print_final_summary(all_results)


if __name__ == "__main__":
    main()
