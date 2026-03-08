"""Generic baseline backtest runner for converted strategies.

Loads any strategy from strategies/<name>/strategy.py via importlib,
runs on MES/MNQ/MGC in both/long/short modes, and saves full reports.

Usage:
    python3 backtests/run_conversion_baseline.py --strategy orb_009
    python3 backtests/run_conversion_baseline.py --strategy vwap_006 --asset MES
    python3 backtests/run_conversion_baseline.py --strategy ict_010 --modes both,long

Output:
    backtests/<strategy>_baseline/
      metrics.json, trades.csv, equity_curve.csv, summary.csv, conversion_notes.md
"""

import argparse
import importlib.util
import json
import inspect
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from backtests.run_baseline import compute_extended_metrics

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

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# ── Strategy Loading ─────────────────────────────────────────────────────────

def load_strategy(strategy_name: str):
    """Load a strategy module from strategies/<name>/strategy.py."""
    module_path = PROJECT_ROOT / "strategies" / strategy_name / "strategy.py"
    if not module_path.exists():
        print(f"ERROR: Strategy not found: {module_path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location(strategy_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_meta(strategy_name: str) -> dict:
    """Load strategy metadata from meta.json."""
    meta_path = PROJECT_ROOT / "strategies" / strategy_name / "meta.json"
    if meta_path.exists():
        with open(meta_path) as f:
            return json.load(f)
    return {}


# ── Data Loading ─────────────────────────────────────────────────────────────

def find_processed_data() -> dict[str, Path]:
    """Find processed 5m CSVs, keyed by symbol."""
    found = {}
    if PROCESSED_DIR.exists():
        for p in PROCESSED_DIR.glob("*_5m.csv"):
            symbol = p.stem.split("_")[0].upper()
            found[symbol] = p
    return found


# ── Runner ───────────────────────────────────────────────────────────────────

def run_single_asset(
    symbol: str,
    data_path: Path,
    strategy_module,
    modes: list[str],
) -> dict:
    """Run backtest for a single asset across modes."""
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

    # Patch tick size if strategy supports it
    if hasattr(strategy_module, "TICK_SIZE"):
        strategy_module.TICK_SIZE = config["tick_size"]

    # Generate signals — check if generate_signals accepts asset param
    sig = inspect.signature(strategy_module.generate_signals)
    if "asset" in sig.parameters:
        signals_df = strategy_module.generate_signals(df, asset=symbol)
    else:
        signals_df = strategy_module.generate_signals(df)

    sig_counts = signals_df["signal"].value_counts()
    print(f"  Signals: {sig_counts.get(1, 0)} long, {sig_counts.get(-1, 0)} short")

    exit_counts = signals_df["exit_signal"].value_counts()
    print(f"  Exits:   {exit_counts.get(1, 0)} exit-long, {exit_counts.get(-1, 0)} exit-short")

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


def save_results(strategy_name: str, all_results: dict, meta: dict, timestamp: str):
    """Save all results to backtests/<strategy>_baseline/."""
    output_dir = PROJECT_ROOT / "backtests" / f"{strategy_name}_baseline"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Summary CSV
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
                "trading_days": m["trading_days"],
            }
            summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(output_dir / "summary.csv", index=False)

    # Per-asset trade logs and metrics
    for symbol, mode_results in all_results.items():
        for mode, data in mode_results.items():
            if not data["trades_df"].empty:
                data["trades_df"].to_csv(
                    output_dir / f"{symbol}_{mode}_trades.csv", index=False
                )
            # Equity curve
            eq_df = pd.DataFrame({
                "equity": data["equity_curve"].values,
            })
            eq_df.to_csv(
                output_dir / f"{symbol}_{mode}_equity.csv", index=False
            )

        # Metrics JSON per asset
        metrics_out = {}
        for mode, data in mode_results.items():
            metrics_out[mode] = data["metrics"]
        with open(output_dir / f"{symbol}_metrics.json", "w") as f:
            json.dump(metrics_out, f, indent=2, default=str)

    # Combined metrics.json
    all_metrics = {}
    for symbol, mode_results in all_results.items():
        all_metrics[symbol] = {}
        for mode, data in mode_results.items():
            all_metrics[symbol][mode] = data["metrics"]
    with open(output_dir / "metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2, default=str)

    # Run metadata
    run_meta = {
        "strategy": strategy_name,
        "strategy_name": meta.get("name", strategy_name),
        "family": meta.get("family", "unknown"),
        "source_url": meta.get("source_url", ""),
        "conversion_type": meta.get("conversion_type", "faithful"),
        "run_date": timestamp,
        "assets": list(all_results.keys()),
        "modes": list(set(m for r in all_results.values() for m in r.keys())),
        "engine": "fill-at-next-open",
        "notes": "Baseline run — faithful conversion, no optimization",
    }
    with open(output_dir / "run_meta.json", "w") as f:
        json.dump(run_meta, f, indent=2)

    # Conversion notes
    notes_lines = [
        f"# {meta.get('name', strategy_name)} — Conversion Baseline",
        f"",
        f"**Strategy:** {strategy_name}",
        f"**Family:** {meta.get('family', 'unknown')}",
        f"**Source:** {meta.get('source_url', 'N/A')}",
        f"**Run date:** {timestamp}",
        f"**Conversion type:** Faithful (no optimization)",
        f"",
        f"## Results Summary",
        f"",
    ]
    for symbol in sorted(all_results.keys()):
        for mode in ("both", "long", "short"):
            if mode not in all_results[symbol]:
                continue
            m = all_results[symbol][mode]["metrics"]
            tc = m["trade_count"]
            if tc > 0:
                notes_lines.append(
                    f"- **{symbol} {mode}**: {tc} trades, "
                    f"PF={m['profit_factor']}, WR={m['win_rate']*100:.1f}%, "
                    f"Sharpe={m['sharpe']}, PnL=${m['total_pnl']:,.2f}, "
                    f"MaxDD=${m['max_drawdown']:,.2f}"
                )
            else:
                notes_lines.append(f"- **{symbol} {mode}**: No trades")

    notes_lines.extend([
        f"",
        f"## Notes",
        f"",
        f"- Faithful conversion from Pine Script v5",
        f"- No parameter optimization applied",
        f"- Engine: fill-at-next-open (same as PB baseline)",
        f"- Data: Databento CME 5m",
    ])

    with open(output_dir / "conversion_notes.md", "w") as f:
        f.write("\n".join(notes_lines) + "\n")

    print(f"\n{'='*60}")
    print(f"  Results saved to: {output_dir}")
    print(f"    summary.csv           — cross-asset performance table")
    print(f"    metrics.json          — all metrics combined")
    print(f"    conversion_notes.md   — conversion report")
    for symbol in all_results:
        print(f"    {symbol}_metrics.json   — per-asset metrics")
        print(f"    {symbol}_*_trades.csv   — trade logs per mode")
    print(f"{'='*60}")


def print_final_summary(strategy_name: str, all_results: dict):
    """Print a clean final summary table."""
    print(f"\n{'='*60}")
    print(f"  {strategy_name.upper()} BASELINE")
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
        description="Generic Conversion Baseline Runner"
    )
    parser.add_argument("--strategy", required=True,
                        help="Strategy directory name (e.g. orb_009, vwap_006, ict_010)")
    parser.add_argument("--asset", default=None,
                        help="Run single asset (MES, MNQ, MGC)")
    parser.add_argument("--modes", default="both,long,short",
                        help="Comma-separated modes (default: both,long,short)")
    args = parser.parse_args()

    strategy_name = args.strategy
    modes = [m.strip() for m in args.modes.split(",")]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Load strategy
    meta = load_meta(strategy_name)
    print(f"\n{'='*60}")
    print(f"  Conversion Baseline Runner")
    print(f"  Strategy: {meta.get('name', strategy_name)}")
    print(f"  Family: {meta.get('family', 'unknown')}")
    print(f"  Time: {timestamp}")
    print(f"{'='*60}")

    strategy_module = load_strategy(strategy_name)
    print(f"  Strategy loaded from strategies/{strategy_name}/strategy.py")

    # Find data
    data_files = find_processed_data()
    if args.asset:
        asset = args.asset.upper()
        if asset not in data_files:
            print(f"\n  ERROR: No processed data for {asset}")
            sys.exit(1)
        data_files = {asset: data_files[asset]}

    if not data_files:
        print(f"\n  No processed data found in {PROCESSED_DIR}")
        sys.exit(1)

    print(f"  Assets: {', '.join(sorted(data_files.keys()))}")
    print(f"  Modes: {', '.join(modes)}")

    # Run backtests
    all_results = {}
    for symbol in sorted(data_files.keys()):
        results = run_single_asset(
            symbol, data_files[symbol], strategy_module, modes
        )
        all_results[symbol] = results

    # Save results
    save_results(strategy_name, all_results, meta, timestamp)
    print_final_summary(strategy_name, all_results)


if __name__ == "__main__":
    main()
