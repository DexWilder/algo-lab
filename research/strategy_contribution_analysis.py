#!/usr/bin/env python3
"""
FQL Strategy Contribution Analysis
====================================
Measures how each strategy contributes to (or dilutes) portfolio performance.

Answers:
  - Does adding strategy X improve portfolio Sharpe?
  - Does it reduce max drawdown?
  - Is it correlated with existing strategies?
  - What is its marginal contribution to risk-adjusted returns?

Metrics per strategy:
  1. Standalone Sharpe ratio
  2. Portfolio Sharpe WITH vs WITHOUT the strategy
  3. Marginal Sharpe contribution (delta)
  4. Correlation with portfolio (excluding self)
  5. Max drawdown contribution
  6. Calmar ratio (annualized return / max drawdown)
  7. Trade overlap % (days where this strategy trades same direction as others)

Usage:
    python3 research/strategy_contribution_analysis.py                    # Full report
    python3 research/strategy_contribution_analysis.py --json             # JSON output
    python3 research/strategy_contribution_analysis.py --save             # Save to reports/
    python3 research/strategy_contribution_analysis.py --candidate <name> # Test adding a candidate
"""

import argparse
import importlib.util
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "research" / "reports"

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "MGC": {"point_value": 10.0, "tick_size": 0.10,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "M2K": {"point_value": 5.0, "tick_size": 0.10,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "MCL": {"point_value": 100.0, "tick_size": 0.01,
            "commission_per_side": 0.62, "slippage_ticks": 1},
}

# Current portfolio strategies (core + probation)
# Format: (strategy_id, module_name, asset, mode)
PORTFOLIO_STRATEGIES = [
    # Core (v0.17)
    ("VWAP-MNQ-Long", "vwap_trend", "MNQ", "long"),
    ("XB-PB-EMA-MES-Short", "xb_pb_ema_timestop", "MES", "short"),
    ("ORB-MGC-Long", "orb_009", "MGC", "long"),
    ("BB-EQ-MGC-Long", "bb_equilibrium", "MGC", "long"),
    ("PB-MGC-Short", "pb_trend", "MGC", "short"),
    ("Donchian-MNQ-Long", "donchian_trend", "MNQ", "long"),
]

# Probation candidates to evaluate
PROBATION_CANDIDATES = [
    ("NoiseBoundary-MNQ-Long", "noise_boundary", "MNQ", "long"),
    ("RangeExpansion-MCL-Short", "range_expansion", "MCL", "short"),
    ("GapMom-MGC-Long", "gap_mom", "MGC", "long"),
    ("GapMom-MNQ-Long", "gap_mom", "MNQ", "long"),
]

STARTING_CAPITAL = 10_000.0


# ── Strategy Loading ──────────────────────────────────────────────────────────

def load_strategy_module(name: str):
    """Load a strategy module from strategies/<name>/strategy.py."""
    path = ROOT / "strategies" / name / "strategy.py"
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    """Load processed 5m OHLCV data for an asset."""
    csv_path = DATA_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


# ── Core Functions ────────────────────────────────────────────────────────────

def load_strategy_trades(strategy_id: str, module_name: str,
                         asset: str, mode: str) -> pd.DataFrame:
    """Load data, generate signals, run backtest, return trades DataFrame.

    Returns trades_df with an added 'date' column for daily aggregation.
    """
    df = load_data(asset)
    config = ASSET_CONFIG[asset]

    mod = load_strategy_module(module_name)
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    kwargs = {}
    if "asset" in sig.parameters:
        kwargs["asset"] = asset
    signals = mod.generate_signals(df.copy(), **kwargs)

    result = run_backtest(
        df, signals,
        mode=mode,
        point_value=config["point_value"],
        symbol=asset,
    )

    trades = result["trades_df"]
    if trades.empty:
        trades["date"] = pd.Series(dtype="object")
        return trades

    trades = trades.copy()
    trades["date"] = pd.to_datetime(trades["entry_time"]).dt.date
    return trades


def build_daily_pnl_matrix(strategies: list[tuple]) -> pd.DataFrame:
    """Build a DataFrame of daily PnL per strategy.

    Parameters
    ----------
    strategies : list of (strategy_id, module_name, asset, mode) tuples

    Returns
    -------
    pd.DataFrame with strategy_ids as columns, dates as index, daily PnL as
    values (0 for no-trade days). Uses union of all trading dates.
    """
    daily_series = {}
    for strategy_id, module_name, asset, mode in strategies:
        try:
            trades = load_strategy_trades(strategy_id, module_name, asset, mode)
            if trades.empty:
                daily_series[strategy_id] = pd.Series(dtype=float)
                continue
            daily_pnl = trades.groupby("date")["pnl"].sum()
            daily_pnl.index = pd.to_datetime(daily_pnl.index)
            daily_series[strategy_id] = daily_pnl
        except Exception as e:
            print(f"  WARNING: Failed to load {strategy_id}: {e}")
            daily_series[strategy_id] = pd.Series(dtype=float)

    if not daily_series:
        return pd.DataFrame()

    matrix = pd.DataFrame(daily_series)
    matrix = matrix.fillna(0.0)
    matrix = matrix.sort_index()
    return matrix


def compute_portfolio_metrics(daily_pnl: pd.Series) -> dict:
    """Compute standard portfolio metrics from a daily PnL series.

    Parameters
    ----------
    daily_pnl : pd.Series
        Daily profit/loss values (can include zero days).

    Returns
    -------
    dict with total_pnl, annualized_return, sharpe, max_drawdown, calmar,
    win_rate, total_trading_days.
    """
    if daily_pnl.empty or len(daily_pnl) < 2:
        return {
            "total_pnl": 0.0,
            "annualized_return": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "total_trading_days": 0,
        }

    total_pnl = daily_pnl.sum()

    # Only use days where at least one strategy traded for Sharpe
    trading_days = daily_pnl[daily_pnl != 0]
    total_trading_days = len(trading_days)

    # Annualized return (assume $10,000 starting capital)
    annualized_return = (total_pnl / STARTING_CAPITAL) * (252 / max(len(daily_pnl), 1))

    # Sharpe: annualized using only active trading days
    if total_trading_days >= 2 and trading_days.std() > 0:
        sharpe = (trading_days.mean() / trading_days.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Max drawdown from cumulative equity
    cum_equity = STARTING_CAPITAL + daily_pnl.cumsum()
    running_max = cum_equity.cummax()
    drawdown = cum_equity - running_max
    max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.0

    # Calmar ratio
    if max_drawdown > 0:
        calmar = (total_pnl / STARTING_CAPITAL) * 252 / max(len(daily_pnl), 1) / (max_drawdown / STARTING_CAPITAL)
    else:
        calmar = 0.0

    # Win rate (% of positive days out of all days with trades)
    if total_trading_days > 0:
        win_rate = len(trading_days[trading_days > 0]) / total_trading_days
    else:
        win_rate = 0.0

    return {
        "total_pnl": round(total_pnl, 2),
        "annualized_return": round(annualized_return, 4),
        "sharpe": round(sharpe, 2),
        "max_drawdown": round(max_drawdown, 2),
        "calmar": round(calmar, 2),
        "win_rate": round(win_rate, 4),
        "total_trading_days": total_trading_days,
    }


def compute_contribution(daily_matrix: pd.DataFrame) -> list[dict]:
    """Compute marginal contribution of each strategy to the portfolio.

    For each strategy:
      - Standalone metrics (just that strategy)
      - Portfolio WITH all strategies
      - Portfolio WITHOUT this strategy
      - Marginal Sharpe = with - without
      - Correlation with rest-of-portfolio
      - Trade overlap %

    Returns list of dicts, one per strategy.
    """
    if daily_matrix.empty:
        return []

    portfolio_pnl = daily_matrix.sum(axis=1)
    portfolio_metrics = compute_portfolio_metrics(portfolio_pnl)

    contributions = []
    for strat_id in daily_matrix.columns:
        strat_pnl = daily_matrix[strat_id]
        other_cols = [c for c in daily_matrix.columns if c != strat_id]

        # Standalone metrics
        standalone = compute_portfolio_metrics(strat_pnl)

        # Portfolio with all strategies (same for everyone)
        with_sharpe = portfolio_metrics["sharpe"]

        # Portfolio without this strategy
        if other_cols:
            without_pnl = daily_matrix[other_cols].sum(axis=1)
            without_metrics = compute_portfolio_metrics(without_pnl)
            without_sharpe = without_metrics["sharpe"]
        else:
            without_sharpe = 0.0

        # Marginal Sharpe contribution
        marginal_sharpe = with_sharpe - without_sharpe

        # Correlation with rest of portfolio
        if other_cols:
            rest_pnl = daily_matrix[other_cols].sum(axis=1)
            # Only correlate on days where both have activity
            mask = (strat_pnl != 0) & (rest_pnl != 0)
            if mask.sum() >= 5:
                corr = strat_pnl[mask].corr(rest_pnl[mask])
                corr = round(corr, 3) if not np.isnan(corr) else 0.0
            else:
                corr = 0.0
        else:
            corr = 0.0

        # Trade overlap: % of this strategy's trading days where rest also traded
        strat_active = strat_pnl != 0
        if other_cols and strat_active.sum() > 0:
            rest_active = daily_matrix[other_cols].sum(axis=1) != 0
            overlap = (strat_active & rest_active).sum() / strat_active.sum()
            overlap = round(overlap, 3)
        else:
            overlap = 0.0

        # Verdict
        if marginal_sharpe > 0.05:
            verdict = "ADDS VALUE"
        elif marginal_sharpe < -0.05:
            verdict = "DILUTIVE"
        else:
            verdict = "NEUTRAL"

        contributions.append({
            "strategy_id": strat_id,
            "standalone_sharpe": standalone["sharpe"],
            "standalone_pnl": standalone["total_pnl"],
            "standalone_calmar": standalone["calmar"],
            "standalone_max_dd": standalone["max_drawdown"],
            "with_sharpe": with_sharpe,
            "without_sharpe": without_sharpe,
            "marginal_sharpe": round(marginal_sharpe, 2),
            "correlation": corr,
            "trade_overlap": overlap,
            "win_rate": standalone["win_rate"],
            "trading_days": standalone["total_trading_days"],
            "verdict": verdict,
        })

    return contributions


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_report(contributions: list[dict], portfolio_metrics: dict,
                 daily_matrix: pd.DataFrame):
    """Print a formatted terminal report."""
    print()
    print("=" * 75)
    print("  STRATEGY CONTRIBUTION ANALYSIS")
    print("=" * 75)

    # Portfolio summary
    print()
    print("  PORTFOLIO SUMMARY (all strategies)")
    print("  " + "-" * 40)
    print(f"  Total PnL:        ${portfolio_metrics['total_pnl']:>12,.2f}")
    print(f"  Sharpe:           {portfolio_metrics['sharpe']:>12.2f}")
    print(f"  Max Drawdown:     ${portfolio_metrics['max_drawdown']:>12,.2f}")
    print(f"  Calmar:           {portfolio_metrics['calmar']:>12.2f}")
    print(f"  Win Rate:         {portfolio_metrics['win_rate'] * 100:>11.1f}%")
    print(f"  Trading Days:     {portfolio_metrics['total_trading_days']:>12d}")

    # Individual contributions table
    print()
    print("  INDIVIDUAL CONTRIBUTIONS")
    print("  " + "-" * 71)
    header = (
        f"  {'Strategy':<28s} {'Standalone':>10s} {'With':>7s} "
        f"{'Without':>7s} {'Marginal':>8s} {'Corr':>6s}  {'Verdict'}"
    )
    print(header)
    subheader = (
        f"  {'':<28s} {'Sharpe':>10s} {'Sharpe':>7s} "
        f"{'Sharpe':>7s} {'Sharpe':>8s} {'':<6s}"
    )
    print(subheader)
    print("  " + "-" * 71)

    for c in sorted(contributions, key=lambda x: x["marginal_sharpe"], reverse=True):
        name = c["strategy_id"]
        if len(name) > 27:
            name = name[:24] + "..."
        print(
            f"  {name:<28s} {c['standalone_sharpe']:>10.2f} "
            f"{c['with_sharpe']:>7.2f} {c['without_sharpe']:>7.2f} "
            f"{c['marginal_sharpe']:>+8.2f} {c['correlation']:>6.3f}  "
            f"{c['verdict']}"
        )

    # Rankings
    print()
    print("  CONTRIBUTION RANKINGS")
    print("  " + "-" * 40)

    if contributions:
        best = max(contributions, key=lambda x: x["marginal_sharpe"])
        worst = min(contributions, key=lambda x: x["marginal_sharpe"])
        dilutive = [c for c in contributions if c["marginal_sharpe"] < -0.05]

        print(f"  Best contributor:   {best['strategy_id']} "
              f"({best['marginal_sharpe']:+.2f})")
        print(f"  Worst contributor:  {worst['strategy_id']} "
              f"({worst['marginal_sharpe']:+.2f})")

        if dilutive:
            names = ", ".join(c["strategy_id"] for c in dilutive)
            print(f"  Dilutive strategies: {names}")
        else:
            print("  Dilutive strategies: None")

    # Correlation matrix
    print()
    print("  CORRELATION MATRIX")
    print("  " + "-" * 40)

    if not daily_matrix.empty and len(daily_matrix.columns) >= 2:
        # Compute pairwise correlations on active trading days
        corr_matrix = daily_matrix.corr()

        # Abbreviate names for display
        abbrevs = {}
        for col in daily_matrix.columns:
            abbrev = col[:12]
            abbrevs[col] = abbrev

        # Header row
        cols = list(daily_matrix.columns)
        header_parts = ["  " + " " * 14]
        for c in cols:
            header_parts.append(f"{abbrevs[c]:>12s}")
        print("".join(header_parts))

        for i, row_name in enumerate(cols):
            row_parts = [f"  {abbrevs[row_name]:<14s}"]
            for j, col_name in enumerate(cols):
                val = corr_matrix.loc[row_name, col_name]
                if i == j:
                    row_parts.append(f"{'---':>12s}")
                else:
                    flag = " *" if abs(val) > 0.5 else "  "
                    row_parts.append(f"{val:>10.3f}{flag}")
            print("".join(row_parts))

        # Flag high correlations
        high_corrs = []
        for i, r in enumerate(cols):
            for j, c in enumerate(cols):
                if i < j and abs(corr_matrix.loc[r, c]) > 0.5:
                    high_corrs.append((r, c, corr_matrix.loc[r, c]))

        if high_corrs:
            print()
            print("  * HIGH CORRELATION PAIRS (|r| > 0.5):")
            for r, c, val in high_corrs:
                print(f"    {r} <-> {c}: {val:.3f}")
    else:
        print("  Insufficient strategies for correlation matrix.")

    print()
    print("=" * 75)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FQL Strategy Contribution Analysis"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--save", action="store_true",
                        help="Save report to research/reports/")
    parser.add_argument("--candidate", type=str, default=None,
                        help="Name of a probation candidate to include "
                             "(e.g. NoiseBoundary-MNQ-Long)")
    args = parser.parse_args()

    # Build strategy list
    strategies = list(PORTFOLIO_STRATEGIES)

    if args.candidate:
        # Find candidate in PROBATION_CANDIDATES
        found = None
        for cand in PROBATION_CANDIDATES:
            if cand[0] == args.candidate:
                found = cand
                break
        if found is None:
            print(f"ERROR: Candidate '{args.candidate}' not found in "
                  f"PROBATION_CANDIDATES.")
            print(f"Available: {[c[0] for c in PROBATION_CANDIDATES]}")
            sys.exit(1)
        strategies.append(found)
        print(f"Including candidate: {found[0]}")

    # Build daily PnL matrix
    print("Running backtests for all strategies...")
    daily_matrix = build_daily_pnl_matrix(strategies)

    if daily_matrix.empty:
        print("ERROR: No trade data produced. Check strategy files and data.")
        sys.exit(1)

    # Compute
    portfolio_pnl = daily_matrix.sum(axis=1)
    portfolio_metrics = compute_portfolio_metrics(portfolio_pnl)
    contributions = compute_contribution(daily_matrix)

    # Output
    if args.json:
        output = {
            "generated": datetime.now().isoformat(),
            "portfolio": portfolio_metrics,
            "contributions": contributions,
        }
        print(json.dumps(output, indent=2))
    else:
        print_report(contributions, portfolio_metrics, daily_matrix)

    # Save
    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = REPORTS_DIR / f"contribution_analysis_{timestamp}.json"
        output = {
            "generated": datetime.now().isoformat(),
            "portfolio": portfolio_metrics,
            "contributions": contributions,
        }
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Report saved to: {out_path}")


if __name__ == "__main__":
    main()
