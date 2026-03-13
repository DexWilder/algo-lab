#!/usr/bin/env python3
"""Portfolio Correlation Matrix — pairwise correlation analysis across all strategies.

READ-ONLY analysis tool. Does NOT modify any execution pipeline files.

Computes three types of correlation:
  1. Daily PnL correlation (Pearson)
  2. Weekly PnL correlation (Pearson)
  3. Drawdown overlap (% of days both strategies in drawdown simultaneously)

Also computes:
  - Eigenvalue concentration ratio (top eigenvalue / sum of eigenvalues)
  - Portfolio diversification score (average |r| across all pairs)

Usage:
    python3 research/portfolio_correlation_matrix.py
    python3 research/portfolio_correlation_matrix.py --include-probation
    python3 research/portfolio_correlation_matrix.py --save
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
from engine.regime_engine import RegimeEngine

# ── Asset Configs ────────────────────────────────────────────────────────────

ASSET_CONFIG = {
    "MES": {"point_value": 5.0,   "tick_size": 0.25,  "commission_per_side": 0.62, "slippage_ticks": 1},
    "MNQ": {"point_value": 2.0,   "tick_size": 0.25,  "commission_per_side": 0.62, "slippage_ticks": 1},
    "MGC": {"point_value": 10.0,  "tick_size": 0.10,  "commission_per_side": 0.62, "slippage_ticks": 1},
    "M2K": {"point_value": 5.0,   "tick_size": 0.10,  "commission_per_side": 0.62, "slippage_ticks": 1},
    "MCL": {"point_value": 100.0, "tick_size": 0.01,  "commission_per_side": 0.62, "slippage_ticks": 1},
}

PROCESSED_DIR = ROOT / "data" / "processed"
FORWARD_LOG = ROOT / "logs" / "trade_log.csv"

# ── Strategy Definitions ─────────────────────────────────────────────────────
# Mirrors engine/strategy_controller.py PORTFOLIO_CONFIG

CORE_STRATEGIES = [
    {"key": "PB-MGC-Short",              "name": "pb_trend",           "asset": "MGC", "mode": "short",
     "grinding_filter": False, "exit_variant": None},
    {"key": "ORB-MGC-Long",              "name": "orb_009",            "asset": "MGC", "mode": "long",
     "grinding_filter": False, "exit_variant": None},
    {"key": "VWAP-MNQ-Long",             "name": "vwap_trend",         "asset": "MNQ", "mode": "long",
     "grinding_filter": False, "exit_variant": None},
    {"key": "XB-PB-EMA-MES-Short",       "name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short",
     "grinding_filter": False, "exit_variant": None},
    {"key": "BB-EQ-MGC-Long",            "name": "bb_equilibrium",     "asset": "MGC", "mode": "long",
     "grinding_filter": False, "exit_variant": None},
    {"key": "Donchian-MNQ-Long-GRINDING","name": "donchian_trend",     "asset": "MNQ", "mode": "long",
     "grinding_filter": True,  "exit_variant": "profit_ladder"},
]

PROBATION_STRATEGIES = [
    {"key": "ORB-Enhanced-M2K-Short",    "name": "orb_enhanced",        "asset": "M2K", "mode": "short",
     "grinding_filter": False, "exit_variant": None},
    {"key": "VWAP-MR-MCL-Short",         "name": "vwap_mean_reversion", "asset": "MCL", "mode": "short",
     "grinding_filter": False, "exit_variant": None},
]


# ── Strategy / Data Loading ──────────────────────────────────────────────────

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
    """Load 5m OHLCV data for an asset."""
    csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def generate_signals_for_strategy(strat: dict, df: pd.DataFrame):
    """Generate signals, handling exit_variant (profit_ladder) and asset kwarg."""
    asset = strat["asset"]
    tick_size = ASSET_CONFIG[asset]["tick_size"]

    if strat["exit_variant"] == "profit_ladder":
        from research.exit_evolution import apply_profit_ladder
        from research.asset_expansion_study import _donchian_entries_for_asset
        data = _donchian_entries_for_asset(df, tick_size)
        return apply_profit_ladder(data)

    mod = load_strategy_module(strat["name"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = tick_size

    sig = inspect.signature(mod.generate_signals)
    if "asset" in sig.parameters:
        return mod.generate_signals(df, asset=asset)
    return mod.generate_signals(df)


def apply_grinding_filter(trades_df: pd.DataFrame, regime_daily: pd.DataFrame) -> pd.DataFrame:
    """Filter trades to GRINDING days only."""
    if trades_df.empty:
        return trades_df
    rd = regime_daily.copy()
    rd["_date"] = pd.to_datetime(rd["_date"])
    rd["_date_date"] = rd["_date"].dt.date

    trades = trades_df.copy()
    trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
    trades = trades.merge(
        rd[["_date_date", "trend_persistence"]],
        left_on="entry_date", right_on="_date_date", how="left",
    )
    trades = trades[trades["trend_persistence"] == "GRINDING"]
    return trades.drop(
        columns=["entry_date", "_date_date", "trend_persistence"], errors="ignore",
    ).reset_index(drop=True)


# ── Backtest Runner ──────────────────────────────────────────────────────────

def run_strategy(strat: dict, engine: RegimeEngine) -> pd.DataFrame:
    """Run a single strategy backtest and return trades DataFrame."""
    asset = strat["asset"]
    cfg = ASSET_CONFIG[asset]
    df = load_data(asset)

    signals = generate_signals_for_strategy(strat, df.copy())
    result = run_backtest(
        df, signals,
        mode=strat["mode"],
        point_value=cfg["point_value"],
        symbol=asset,
        commission_per_side=cfg["commission_per_side"],
        slippage_ticks=cfg["slippage_ticks"],
        tick_size=cfg["tick_size"],
    )
    trades = result["trades_df"]

    # Apply GRINDING filter if needed
    if strat.get("grinding_filter") and not trades.empty:
        regime_daily = engine.get_daily_regimes(df)
        trades = apply_grinding_filter(trades, regime_daily)

    return trades


# ── PnL Aggregation ──────────────────────────────────────────────────────────

def trades_to_daily_pnl(trades: pd.DataFrame) -> pd.Series:
    """Aggregate trades into daily PnL series (indexed by date)."""
    if trades.empty:
        return pd.Series(dtype=float, name="pnl")
    tmp = trades.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def trades_to_weekly_pnl(trades: pd.DataFrame) -> pd.Series:
    """Aggregate trades into weekly PnL series."""
    daily = trades_to_daily_pnl(trades)
    if daily.empty:
        return pd.Series(dtype=float, name="pnl")
    return daily.resample("W-FRI").sum()


def daily_pnl_to_drawdown_mask(daily_pnl: pd.Series) -> pd.Series:
    """Return boolean Series: True on days where strategy is in drawdown.

    A strategy is 'in drawdown' when its cumulative equity is below its
    running high-water mark.
    """
    if daily_pnl.empty:
        return pd.Series(dtype=bool)
    equity = daily_pnl.cumsum()
    hwm = equity.cummax()
    return equity < hwm


# ── Correlation Computation ──────────────────────────────────────────────────

def compute_pairwise_correlations(pnl_dict: dict) -> pd.DataFrame:
    """Compute pairwise Pearson correlations from a dict of {key: pd.Series}.

    Aligns all series on their union of dates, filling missing days with 0.
    Returns a symmetric correlation matrix DataFrame.
    """
    df = pd.DataFrame(pnl_dict).fillna(0)
    if df.empty or len(df.columns) < 2:
        return pd.DataFrame()
    return df.corr()


def compute_drawdown_overlap(dd_masks: dict) -> pd.DataFrame:
    """Compute pairwise drawdown overlap percentage.

    For each pair (A, B): % of days where BOTH are in drawdown simultaneously,
    relative to the total number of days where EITHER is in drawdown.
    """
    keys = list(dd_masks.keys())
    n = len(keys)
    overlap = pd.DataFrame(np.zeros((n, n)), index=keys, columns=keys)

    df = pd.DataFrame(dd_masks).fillna(False)

    for i in range(n):
        for j in range(i, n):
            a = df[keys[i]]
            b = df[keys[j]]
            both = (a & b).sum()
            either = (a | b).sum()
            pct = both / either if either > 0 else 0.0
            overlap.iloc[i, j] = pct
            overlap.iloc[j, i] = pct

    return overlap


def eigenvalue_concentration(corr_matrix: pd.DataFrame) -> float:
    """Compute eigenvalue concentration ratio: largest eigenvalue / sum.

    A ratio of 1/N means perfectly diversified. A ratio near 1.0 means
    all strategies move together (concentrated risk).
    """
    if corr_matrix.empty:
        return 0.0
    eigenvalues = np.linalg.eigvalsh(corr_matrix.values)
    eigenvalues = np.abs(eigenvalues)  # guard against tiny negatives from float
    total = eigenvalues.sum()
    if total == 0:
        return 0.0
    return float(eigenvalues.max() / total)


def diversification_score(corr_matrix: pd.DataFrame) -> float:
    """Average absolute pairwise correlation (lower is better).

    Excludes diagonal. Range: 0 (perfectly independent) to 1 (perfectly correlated).
    """
    if corr_matrix.empty or len(corr_matrix) < 2:
        return 0.0
    n = len(corr_matrix)
    mask = ~np.eye(n, dtype=bool)
    return float(np.abs(corr_matrix.values[mask]).mean())


# ── Forward Data ─────────────────────────────────────────────────────────────

def load_forward_trades() -> dict:
    """Load forward paper-trading log and split by strategy.

    Returns {strategy_key: trades_df} or empty dict if no log exists.
    Expected columns: strategy, entry_time, exit_time, pnl, ...
    """
    if not FORWARD_LOG.exists():
        return {}

    df = pd.read_csv(FORWARD_LOG)
    if "strategy" not in df.columns or "pnl" not in df.columns:
        return {}
    if "exit_time" not in df.columns:
        return {}

    result = {}
    for strat_key, group in df.groupby("strategy"):
        result[strat_key] = group.reset_index(drop=True)
    return result


# ── Reporting ────────────────────────────────────────────────────────────────

def format_corr_matrix(matrix: pd.DataFrame, title: str) -> str:
    """Format a correlation matrix as a readable table string."""
    lines = []
    W = 78
    lines.append(f"\n{'=' * W}")
    lines.append(f"  {title}")
    lines.append(f"{'=' * W}\n")

    if matrix.empty:
        lines.append("  (no data)")
        return "\n".join(lines)

    # Abbreviate long keys for display
    abbrev = {}
    for key in matrix.columns:
        parts = key.split("-")
        if len(parts) >= 3:
            abbrev[key] = f"{parts[0]}-{parts[1]}"
        else:
            abbrev[key] = key[:12]

    short_keys = [abbrev[k] for k in matrix.columns]
    col_w = max(len(s) for s in short_keys) + 2
    col_w = max(col_w, 10)

    # Header
    header = f"  {'':>{col_w}}"
    for sk in short_keys:
        header += f"  {sk:>{col_w}}"
    lines.append(header)
    lines.append(f"  {'':>{col_w}}" + f"  {'─' * col_w}" * len(short_keys))

    # Rows
    for i, (key, row) in enumerate(matrix.iterrows()):
        row_str = f"  {short_keys[i]:>{col_w}}"
        for j, val in enumerate(row):
            if i == j:
                cell = "  ---"
            else:
                cell = f"  {val:>{col_w}.3f}"
            row_str += cell
        lines.append(row_str)

    return "\n".join(lines)


def format_pair_flags(corr_matrix: pd.DataFrame) -> str:
    """Flag pairs with HIGH (|r| > 0.3) or INDEPENDENT (|r| < 0.05) correlation."""
    lines = []
    keys = list(corr_matrix.columns)
    n = len(keys)

    high_pairs = []
    indep_pairs = []

    for i in range(n):
        for j in range(i + 1, n):
            r = corr_matrix.iloc[i, j]
            if abs(r) > 0.3:
                high_pairs.append((keys[i], keys[j], r))
            elif abs(r) < 0.05:
                indep_pairs.append((keys[i], keys[j], r))

    if high_pairs:
        lines.append("  HIGH CORRELATION (|r| > 0.3) — potential redundancy:")
        for a, b, r in sorted(high_pairs, key=lambda x: -abs(x[2])):
            lines.append(f"    {a} vs {b}: r = {r:.3f}")
    else:
        lines.append("  HIGH CORRELATION: None (all pairs |r| <= 0.3)")

    lines.append("")

    if indep_pairs:
        lines.append(f"  INDEPENDENT (|r| < 0.05) — {len(indep_pairs)} pairs:")
        for a, b, r in indep_pairs:
            lines.append(f"    {a} vs {b}: r = {r:.3f}")
    else:
        lines.append("  INDEPENDENT: None (all pairs |r| >= 0.05)")

    return "\n".join(lines)


def format_drawdown_overlap(dd_matrix: pd.DataFrame) -> str:
    """Format drawdown overlap matrix."""
    lines = []
    keys = list(dd_matrix.columns)
    n = len(keys)

    # Only show upper triangle pairs sorted by overlap
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((keys[i], keys[j], dd_matrix.iloc[i, j]))

    pairs.sort(key=lambda x: -x[2])

    lines.append("  Pair Drawdown Overlap (% of days both in DD when either is):")
    lines.append(f"  {'─' * 60}")
    for a, b, pct in pairs:
        bar = "#" * int(pct * 40)
        a_short = a.split("-")[0] + "-" + a.split("-")[1] if "-" in a else a[:12]
        b_short = b.split("-")[0] + "-" + b.split("-")[1] if "-" in b else b[:12]
        lines.append(f"    {a_short:>14} vs {b_short:<14}  {pct:5.1%}  {bar}")

    return "\n".join(lines)


def print_report(
    daily_corr: pd.DataFrame,
    weekly_corr: pd.DataFrame,
    dd_overlap: pd.DataFrame,
    trade_counts: dict,
    include_probation: bool,
    fwd_daily_corr: pd.DataFrame | None = None,
):
    """Print the full correlation analysis report."""
    W = 78

    print()
    print("=" * W)
    print("  PORTFOLIO CORRELATION MATRIX")
    scope = "6 core + 2 probation" if include_probation else "6 core strategies"
    print(f"  Scope: {scope}")
    print("=" * W)

    # Strategy summary
    print(f"\n  STRATEGIES ANALYZED")
    print(f"  {'─' * 50}")
    for key, count in trade_counts.items():
        print(f"    {key:<40} {count:>5} trades")

    # Daily PnL correlation
    print(format_corr_matrix(daily_corr, "DAILY PnL CORRELATION (Pearson)"))
    print()
    print(format_pair_flags(daily_corr))

    # Weekly PnL correlation
    print(format_corr_matrix(weekly_corr, "WEEKLY PnL CORRELATION (Pearson)"))

    # Drawdown overlap
    print(f"\n{'=' * W}")
    print(f"  DRAWDOWN OVERLAP")
    print(f"{'=' * W}\n")
    print(format_drawdown_overlap(dd_overlap))

    # Portfolio-level metrics
    print(f"\n{'=' * W}")
    print(f"  PORTFOLIO DIVERSIFICATION METRICS")
    print(f"{'=' * W}\n")

    div_score = diversification_score(daily_corr)
    eig_ratio = eigenvalue_concentration(daily_corr)
    n = len(daily_corr)
    ideal_eig = 1.0 / n if n > 0 else 0

    print(f"  Diversification Score (avg |r|):    {div_score:.4f}")
    if div_score < 0.05:
        quality = "EXCELLENT — near-zero cross-correlation"
    elif div_score < 0.10:
        quality = "VERY GOOD — minimal cross-correlation"
    elif div_score < 0.20:
        quality = "GOOD — low cross-correlation"
    elif div_score < 0.30:
        quality = "MODERATE — some shared variance"
    else:
        quality = "POOR — significant shared variance"
    print(f"  Quality:                            {quality}")

    print(f"\n  Eigenvalue Concentration:           {eig_ratio:.4f}")
    print(f"  Ideal (perfect diversification):    {ideal_eig:.4f}")
    print(f"  Concentration ratio:                {eig_ratio / ideal_eig:.2f}x ideal")
    if eig_ratio < ideal_eig * 1.5:
        eig_quality = "EXCELLENT — risk well-distributed"
    elif eig_ratio < ideal_eig * 2.0:
        eig_quality = "GOOD — mild concentration"
    elif eig_ratio < ideal_eig * 3.0:
        eig_quality = "MODERATE — some risk concentration"
    else:
        eig_quality = "POOR — risk concentrated in one factor"
    print(f"  Quality:                            {eig_quality}")

    # Forward correlations
    if fwd_daily_corr is not None and not fwd_daily_corr.empty:
        print(format_corr_matrix(fwd_daily_corr, "FORWARD (PAPER TRADING) DAILY PnL CORRELATION"))
        print()
        print(format_pair_flags(fwd_daily_corr))

        fwd_div = diversification_score(fwd_daily_corr)
        print(f"\n  Forward Diversification Score:      {fwd_div:.4f}")
    elif FORWARD_LOG.exists():
        print(f"\n  Forward log found but insufficient data for correlation analysis.")
    else:
        print(f"\n  No forward data (logs/trade_log.csv not found). Skipping forward analysis.")

    print(f"\n{'=' * W}")
    print(f"  DONE")
    print(f"{'=' * W}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Portfolio Correlation Matrix")
    parser.add_argument("--include-probation", action="store_true",
                        help="Include 2 probation strategies (ORB Enhanced M2K, VWAP MR MCL)")
    parser.add_argument("--save", action="store_true",
                        help="Save results to JSON")
    args = parser.parse_args()

    strategies = list(CORE_STRATEGIES)
    if args.include_probation:
        strategies.extend(PROBATION_STRATEGIES)

    print()
    print("=" * 78)
    print("  PORTFOLIO CORRELATION MATRIX")
    scope = f"{len(strategies)} strategies"
    if args.include_probation:
        scope += " (including probation)"
    print(f"  Scope: {scope}")
    print("=" * 78)

    # ── Run backtests ─────────────────────────────────────────────────────
    print(f"\n  RUNNING BACKTESTS")
    print(f"  {'─' * 50}")

    engine = RegimeEngine()
    daily_pnls = {}
    weekly_pnls = {}
    dd_masks = {}
    trade_counts = {}

    for strat in strategies:
        key = strat["key"]
        print(f"    {key}...", end=" ", flush=True)

        try:
            trades = run_strategy(strat, engine)
            n_trades = len(trades)
            trade_counts[key] = n_trades

            if n_trades == 0:
                print("0 trades")
                daily_pnls[key] = pd.Series(dtype=float)
                weekly_pnls[key] = pd.Series(dtype=float)
                dd_masks[key] = pd.Series(dtype=bool)
                continue

            daily_pnls[key] = trades_to_daily_pnl(trades)
            weekly_pnls[key] = trades_to_weekly_pnl(trades)
            dd_masks[key] = daily_pnl_to_drawdown_mask(daily_pnls[key])

            total_pnl = trades["pnl"].sum()
            print(f"{n_trades} trades, PnL=${total_pnl:,.0f}")

        except Exception as e:
            print(f"ERROR: {e}")
            trade_counts[key] = 0
            daily_pnls[key] = pd.Series(dtype=float)
            weekly_pnls[key] = pd.Series(dtype=float)
            dd_masks[key] = pd.Series(dtype=bool)

    # ── Compute correlations ──────────────────────────────────────────────
    print(f"\n  COMPUTING CORRELATIONS")
    print(f"  {'─' * 50}")

    # Filter to strategies with trades
    active_keys = [k for k, v in trade_counts.items() if v > 0]

    active_daily = {k: daily_pnls[k] for k in active_keys}
    active_weekly = {k: weekly_pnls[k] for k in active_keys}
    active_dd = {k: dd_masks[k] for k in active_keys}

    daily_corr = compute_pairwise_correlations(active_daily)
    weekly_corr = compute_pairwise_correlations(active_weekly)
    dd_overlap = compute_drawdown_overlap(active_dd)

    print(f"    Daily correlation matrix:  {len(daily_corr)}x{len(daily_corr)}")
    print(f"    Weekly correlation matrix: {len(weekly_corr)}x{len(weekly_corr)}")
    print(f"    Drawdown overlap matrix:   {len(dd_overlap)}x{len(dd_overlap)}")

    # ── Forward data ──────────────────────────────────────────────────────
    fwd_daily_corr = None
    fwd_trades = load_forward_trades()
    if fwd_trades:
        print(f"\n  FORWARD DATA DETECTED ({len(fwd_trades)} strategies)")
        print(f"  {'─' * 50}")

        fwd_daily_pnls = {}
        for fwd_key, fwd_df in fwd_trades.items():
            fwd_daily = trades_to_daily_pnl(fwd_df)
            if not fwd_daily.empty:
                fwd_daily_pnls[fwd_key] = fwd_daily
                print(f"    {fwd_key}: {len(fwd_df)} trades, {len(fwd_daily)} trading days")

        if len(fwd_daily_pnls) >= 2:
            fwd_daily_corr = compute_pairwise_correlations(fwd_daily_pnls)

    # ── Report ────────────────────────────────────────────────────────────
    print_report(
        daily_corr=daily_corr,
        weekly_corr=weekly_corr,
        dd_overlap=dd_overlap,
        trade_counts={k: trade_counts[k] for k in active_keys},
        include_probation=args.include_probation,
        fwd_daily_corr=fwd_daily_corr,
    )

    # ── Save ──────────────────────────────────────────────────────────────
    if args.save:
        output_path = ROOT / "research" / "portfolio_correlation_results.json"
        save_data = {
            "scope": "core+probation" if args.include_probation else "core",
            "strategies": active_keys,
            "trade_counts": {k: trade_counts[k] for k in active_keys},
            "daily_correlation": daily_corr.to_dict() if not daily_corr.empty else {},
            "weekly_correlation": weekly_corr.to_dict() if not weekly_corr.empty else {},
            "drawdown_overlap": dd_overlap.to_dict() if not dd_overlap.empty else {},
            "diversification_score": round(diversification_score(daily_corr), 4),
            "eigenvalue_concentration": round(eigenvalue_concentration(daily_corr), 4),
            "ideal_eigenvalue_ratio": round(1.0 / len(daily_corr), 4) if len(daily_corr) > 0 else 0,
        }
        if fwd_daily_corr is not None and not fwd_daily_corr.empty:
            save_data["forward_daily_correlation"] = fwd_daily_corr.to_dict()
            save_data["forward_diversification_score"] = round(
                diversification_score(fwd_daily_corr), 4
            )

        output_path.write_text(json.dumps(save_data, indent=2, default=str) + "\n")
        print(f"\n  Results saved to {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
