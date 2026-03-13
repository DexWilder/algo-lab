"""Strategy Contribution Analyzer — per-strategy performance breakdown.

READ-ONLY analysis tool. Does NOT modify any execution pipeline files.

Computes per-strategy contribution metrics from both backtest (Phase 17
portfolio simulation) and forward trading data (logs/trade_log.csv).
Flags strategies whose forward performance deviates >2 sigma from backtest.

Usage:
    python3 research/strategy_contribution_analyzer.py            # backtest + forward
    python3 research/strategy_contribution_analyzer.py --forward-only
    python3 research/strategy_contribution_analyzer.py --days 30  # last 30 days forward
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_backtest_trades() -> dict[str, pd.DataFrame]:
    """Run the 6-strategy portfolio backtest and return controlled trades.

    Uses the same pipeline as Phase 17: strategy signals -> backtest ->
    strategy controller.  Returns {strategy_key: trades_df}.
    """
    from engine.paper_trading_engine import PaperTradingEngine

    print("  Running backtest portfolio (Phase 17 pipeline)...")
    engine = PaperTradingEngine()
    results = engine.run()

    # Reconstruct per-strategy controlled trades from daily_states
    # The engine stores controlled_trades internally but doesn't expose them
    # in the results dict.  Re-derive from the engine object.
    controlled = {}
    for strat_key in engine.config["strategies"]:
        # Access via the strategy_controller simulate result cached during run
        pass  # placeholder — see below

    # The engine doesn't expose controlled_trades externally.  Instead of
    # monkey-patching, run the pipeline the same way the engine does.
    from engine.backtest import run_backtest
    from engine.regime_engine import RegimeEngine
    from engine.strategy_controller import StrategyController, PORTFOLIO_CONFIG

    try:
        from backtests.run_baseline import ASSET_CONFIG
    except ImportError:
        ASSET_CONFIG = {
            "MES": {"point_value": 5.0, "tick_size": 0.25,
                     "commission_per_side": 0.62, "slippage_ticks": 1},
            "MNQ": {"point_value": 2.0, "tick_size": 0.25,
                     "commission_per_side": 0.62, "slippage_ticks": 1},
            "MGC": {"point_value": 10.0, "tick_size": 0.10,
                     "commission_per_side": 0.62, "slippage_ticks": 1},
        }

    import importlib.util

    PROCESSED_DIR = ROOT / "data" / "processed"
    strat_configs = PORTFOLIO_CONFIG["strategies"]
    regime_engine = RegimeEngine()

    data_cache = {}
    regime_daily_cache = {}
    baseline_trades = {}

    for strat_key, strat in strat_configs.items():
        asset = strat["asset"]
        config = ASSET_CONFIG[asset]

        if asset not in data_cache:
            df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
            df["datetime"] = pd.to_datetime(df["datetime"])
            data_cache[asset] = df
            regime_daily_cache[asset] = regime_engine.get_daily_regimes(df)

        df = data_cache[asset]
        path = ROOT / "strategies" / strat["name"] / "strategy.py"
        spec = importlib.util.spec_from_file_location(strat["name"], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = config["tick_size"]

        if strat.get("exit_variant") == "profit_ladder":
            from research.exit_evolution import donchian_entries, apply_profit_ladder
            data = donchian_entries(df)
            signals = apply_profit_ladder(data)
        else:
            signals = mod.generate_signals(df)

        result = run_backtest(
            df, signals,
            mode=strat["mode"],
            point_value=config["point_value"],
            symbol=asset,
        )
        trades = result["trades_df"]

        # GRINDING filter
        if strat.get("grinding_filter") and not trades.empty:
            rd = regime_daily_cache[asset].copy()
            rd["_date"] = pd.to_datetime(rd["_date"])
            rd["_date_date"] = rd["_date"].dt.date
            trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
            trades = trades.merge(
                rd[["_date_date", "trend_persistence"]],
                left_on="entry_date", right_on="_date_date", how="left",
            )
            trades = trades[trades["trend_persistence"] == "GRINDING"]
            trades = trades.drop(
                columns=["entry_date", "_date_date", "trend_persistence"],
                errors="ignore",
            ).reset_index(drop=True)

        baseline_trades[strat_key] = trades

    # Apply strategy controller
    controller = StrategyController(PORTFOLIO_CONFIG)
    ctrl_result = controller.simulate(baseline_trades, regime_daily_cache)
    controlled_trades = ctrl_result["filtered_trades"]

    # Tag each trade with its strategy key
    for strat_key, trades in controlled_trades.items():
        if not trades.empty:
            controlled_trades[strat_key] = trades.copy()
            controlled_trades[strat_key]["strategy"] = strat_key

    print("  Backtest portfolio loaded.\n")
    return controlled_trades


def load_forward_trades(days: int = 0) -> pd.DataFrame | None:
    """Load forward trade log from logs/trade_log.csv.

    Expected columns: date, strategy, pnl  (at minimum).
    Returns None if the file does not exist.
    """
    path = ROOT / "logs" / "trade_log.csv"
    if not path.exists():
        print(f"  [MISSING] {path.relative_to(ROOT)} — no forward data available.")
        return None

    df = pd.read_csv(path, parse_dates=["date"])
    print(f"  Loaded forward trades: {len(df)} rows from {path.relative_to(ROOT)}")

    if days > 0:
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
        df = df[df["date"] >= cutoff]
        print(f"  Filtered to last {days} days: {len(df)} rows")

    return df


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_strategy_metrics(trades: pd.DataFrame,
                             strategy_col: str = "strategy",
                             pnl_col: str = "pnl") -> pd.DataFrame:
    """Compute per-strategy contribution metrics.

    Parameters
    ----------
    trades : DataFrame
        Must have at least ``strategy_col`` and ``pnl_col`` columns.
        Optionally ``exit_time`` (for daily Sharpe) and ``side``.
    strategy_col : str
        Column name identifying the strategy.
    pnl_col : str
        Column name with trade-level PnL.

    Returns
    -------
    DataFrame with one row per strategy and an "ALL" totals row.
    """
    if trades.empty:
        return pd.DataFrame()

    rows = []
    total_trades = len(trades)
    total_pnl = trades[pnl_col].sum()

    for strat, grp in trades.groupby(strategy_col):
        rows.append(_metrics_for_group(grp, strat, pnl_col,
                                       total_trades, total_pnl))

    # Portfolio total
    rows.append(_metrics_for_group(trades, "ALL", pnl_col,
                                   total_trades, total_pnl))

    df = pd.DataFrame(rows)
    # Sort: ALL last, rest by net PnL descending
    df["_sort"] = df["strategy"].apply(lambda x: 1 if x == "ALL" else 0)
    df = df.sort_values(["_sort", "net_pnl"], ascending=[True, False])
    df = df.drop(columns=["_sort"]).reset_index(drop=True)
    return df


def _metrics_for_group(grp: pd.DataFrame, name: str, pnl_col: str,
                       total_trades: int, total_pnl: float) -> dict:
    """Compute metrics for a single strategy group."""
    n = len(grp)
    pnl = grp[pnl_col]
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]

    net = pnl.sum()
    avg = pnl.mean()
    wr = len(wins) / n if n > 0 else 0.0
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = losses.mean() if len(losses) > 0 else 0.0
    payoff = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")
    pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")

    # Annualized Sharpe from daily PnL series
    sharpe = _daily_sharpe(grp, pnl_col)

    # Max drawdown contribution (cumulative PnL drawdown for this strategy)
    cum = pnl.cumsum()
    peak = cum.cummax()
    dd = peak - cum
    maxdd = dd.max() if len(dd) > 0 else 0.0

    # Trade share and PnL share
    trade_share = n / total_trades if total_trades > 0 else 0.0
    pnl_share = net / total_pnl if total_pnl != 0 else 0.0

    # Role classification
    if trade_share > 0.30:
        role = "backbone"
    elif trade_share >= 0.10:
        role = "consistent"
    else:
        role = "tail engine"

    if name == "ALL":
        role = ""

    return {
        "strategy": name,
        "trades": n,
        "trade_share": trade_share,
        "win_rate": wr,
        "avg_pnl": avg,
        "net_pnl": net,
        "pnl_share": pnl_share,
        "sharpe": sharpe,
        "profit_factor": pf,
        "avg_winner": avg_win,
        "avg_loser": avg_loss,
        "payoff_ratio": payoff,
        "max_dd": maxdd,
        "role": role,
    }


def _daily_sharpe(grp: pd.DataFrame, pnl_col: str) -> float:
    """Annualized Sharpe from daily PnL aggregation.

    If exit_time is available, uses it for daily grouping.
    Otherwise falls back to sequential trade PnL.
    """
    if "exit_time" in grp.columns:
        try:
            daily = grp.copy()
            daily["_date"] = pd.to_datetime(daily["exit_time"]).dt.date
            daily_pnl = daily.groupby("_date")[pnl_col].sum()
        except Exception:
            daily_pnl = grp[pnl_col]
    else:
        daily_pnl = grp[pnl_col]

    if len(daily_pnl) < 2 or daily_pnl.std() == 0:
        return 0.0
    return float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(252))


# ---------------------------------------------------------------------------
# Deviation detection
# ---------------------------------------------------------------------------

def flag_deviations(bt_metrics: pd.DataFrame,
                    fwd_metrics: pd.DataFrame,
                    sigma_threshold: float = 2.0) -> list[dict]:
    """Flag strategies where forward performance deviates from backtest.

    Uses bootstrapped standard error of key backtest metrics to define
    sigma bands.  Returns list of flagged items.
    """
    flags = []
    check_cols = ["win_rate", "avg_pnl", "profit_factor", "sharpe"]

    for _, bt_row in bt_metrics.iterrows():
        strat = bt_row["strategy"]
        if strat == "ALL":
            continue
        fwd_row = fwd_metrics[fwd_metrics["strategy"] == strat]
        if fwd_row.empty:
            flags.append({
                "strategy": strat,
                "metric": "presence",
                "note": "Strategy missing from forward data",
            })
            continue
        fwd_row = fwd_row.iloc[0]

        for col in check_cols:
            bt_val = bt_row[col]
            fwd_val = fwd_row[col]

            if bt_val == 0 or not np.isfinite(bt_val):
                continue

            # Standard error estimate: use backtest metric * coefficient of
            # variation approximation.  For win_rate, SE = sqrt(p(1-p)/n).
            if col == "win_rate":
                n = bt_row["trades"]
                se = np.sqrt(bt_val * (1 - bt_val) / n) if n > 0 else 0
            else:
                # Rough SE: |mean| / sqrt(n)
                n = bt_row["trades"]
                se = abs(bt_val) / np.sqrt(n) if n > 0 else 0

            if se > 0:
                z = (fwd_val - bt_val) / se
                if abs(z) > sigma_threshold:
                    flags.append({
                        "strategy": strat,
                        "metric": col,
                        "backtest": bt_val,
                        "forward": fwd_val,
                        "z_score": z,
                        "note": f"{col} deviates {z:+.1f} sigma",
                    })
    return flags


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_metrics_table(df: pd.DataFrame, title: str):
    """Print a formatted metrics table."""
    if df.empty:
        print(f"\n  {title}: No data.\n")
        return

    sep = "-" * 138
    print(f"\n{'=' * 138}")
    print(f"  {title}")
    print(f"{'=' * 138}")
    print()

    header = (
        f"  {'Strategy':<32} | {'Trades':>6} | {'Share':>6} | {'WR':>6} "
        f"| {'Avg PnL':>9} | {'Net PnL':>10} | {'PnL %':>6} "
        f"| {'Sharpe':>6} | {'PF':>6} | {'AvgW':>8} | {'AvgL':>8} "
        f"| {'Payoff':>6} | {'MaxDD':>8} | {'Role':<12}"
    )
    print(header)
    print(f"  {sep}")

    for _, r in df.iterrows():
        pf_str = f"{r['profit_factor']:.2f}" if np.isfinite(r['profit_factor']) else "inf"
        po_str = f"{r['payoff_ratio']:.2f}" if np.isfinite(r['payoff_ratio']) else "inf"

        line = (
            f"  {r['strategy']:<32} "
            f"| {r['trades']:>6} "
            f"| {r['trade_share']*100:>5.1f}% "
            f"| {r['win_rate']*100:>5.1f}% "
            f"| ${r['avg_pnl']:>8.2f} "
            f"| ${r['net_pnl']:>9,.0f} "
            f"| {r['pnl_share']*100:>5.1f}% "
            f"| {r['sharpe']:>6.2f} "
            f"| {pf_str:>6} "
            f"| ${r['avg_winner']:>7.2f} "
            f"| ${r['avg_loser']:>7.2f} "
            f"| {po_str:>6} "
            f"| ${r['max_dd']:>7,.0f} "
            f"| {r['role']:<12}"
        )
        print(line)

    print()


def print_deviation_flags(flags: list[dict]):
    """Print deviation flags."""
    if not flags:
        print("  No significant deviations detected (all within 2 sigma).\n")
        return

    print(f"\n{'=' * 90}")
    print(f"  DEVIATION FLAGS (>2 sigma from backtest)")
    print(f"{'=' * 90}\n")

    for f in flags:
        if "z_score" in f:
            print(f"  [FLAG] {f['strategy']:32s}  {f['metric']:<16s}  "
                  f"BT={f['backtest']:.3f}  FWD={f['forward']:.3f}  "
                  f"z={f['z_score']:+.1f}")
        else:
            print(f"  [FLAG] {f['strategy']:32s}  {f['note']}")

    print()


def print_comparison(bt_metrics: pd.DataFrame, fwd_metrics: pd.DataFrame):
    """Print side-by-side comparison of key metrics."""
    print(f"\n{'=' * 100}")
    print(f"  BACKTEST vs FORWARD — KEY METRICS COMPARISON")
    print(f"{'=' * 100}\n")

    header = (
        f"  {'Strategy':<32} | {'BT WR':>6} {'FW WR':>6} "
        f"| {'BT Avg':>8} {'FW Avg':>8} "
        f"| {'BT PF':>6} {'FW PF':>6} "
        f"| {'BT Sharpe':>9} {'FW Sharpe':>9}"
    )
    print(header)
    print(f"  {'-' * 96}")

    all_strats = set(bt_metrics["strategy"]) | set(fwd_metrics["strategy"])
    all_strats.discard("ALL")

    for strat in sorted(all_strats):
        bt = bt_metrics[bt_metrics["strategy"] == strat]
        fw = fwd_metrics[fwd_metrics["strategy"] == strat]

        bt_wr = f"{bt.iloc[0]['win_rate']*100:.1f}%" if not bt.empty else "  n/a"
        fw_wr = f"{fw.iloc[0]['win_rate']*100:.1f}%" if not fw.empty else "  n/a"
        bt_avg = f"${bt.iloc[0]['avg_pnl']:.2f}" if not bt.empty else "    n/a"
        fw_avg = f"${fw.iloc[0]['avg_pnl']:.2f}" if not fw.empty else "    n/a"

        bt_pf_val = bt.iloc[0]['profit_factor'] if not bt.empty else 0
        fw_pf_val = fw.iloc[0]['profit_factor'] if not fw.empty else 0
        bt_pf = f"{bt_pf_val:.2f}" if not bt.empty and np.isfinite(bt_pf_val) else "  n/a"
        fw_pf = f"{fw_pf_val:.2f}" if not fw.empty and np.isfinite(fw_pf_val) else "  n/a"

        bt_sh = f"{bt.iloc[0]['sharpe']:.2f}" if not bt.empty else "    n/a"
        fw_sh = f"{fw.iloc[0]['sharpe']:.2f}" if not fw.empty else "    n/a"

        print(f"  {strat:<32} | {bt_wr:>6} {fw_wr:>6} "
              f"| {bt_avg:>8} {fw_avg:>8} "
              f"| {bt_pf:>6} {fw_pf:>6} "
              f"| {bt_sh:>9} {fw_sh:>9}")

    # ALL row
    for label, metrics in [("BACKTEST TOTAL", bt_metrics), ("FORWARD TOTAL", fwd_metrics)]:
        total = metrics[metrics["strategy"] == "ALL"]
        if not total.empty:
            t = total.iloc[0]
            pf_str = f"{t['profit_factor']:.2f}" if np.isfinite(t['profit_factor']) else "inf"
            print(f"\n  {label}: {t['trades']} trades, WR={t['win_rate']*100:.1f}%, "
                  f"Avg=${t['avg_pnl']:.2f}, Net=${t['net_pnl']:,.0f}, "
                  f"PF={pf_str}, Sharpe={t['sharpe']:.2f}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Strategy Contribution Analyzer — per-strategy performance breakdown"
    )
    parser.add_argument("--forward-only", action="store_true",
                        help="Analyze only forward data (skip backtest)")
    parser.add_argument("--days", type=int, default=0,
                        help="Limit forward analysis to last N days")
    args = parser.parse_args()

    print("=" * 78)
    print("  STRATEGY CONTRIBUTION ANALYZER")
    print("  Per-strategy performance from backtest and forward data")
    print("=" * 78)

    bt_metrics = pd.DataFrame()
    fwd_metrics = pd.DataFrame()

    # ── Backtest data ─────────────────────────────────────────────────────
    if not args.forward_only:
        print("\n  [1/2] Loading backtest portfolio...\n")
        controlled = load_backtest_trades()

        # Combine into a single DataFrame
        parts = [t for t in controlled.values() if not t.empty]
        if parts:
            bt_trades = pd.concat(parts, ignore_index=True)
            bt_metrics = compute_strategy_metrics(bt_trades)
            print_metrics_table(bt_metrics, "BACKTEST PORTFOLIO — Strategy Contributions")
        else:
            print("  WARNING: No backtest trades produced.\n")

    # ── Forward data ──────────────────────────────────────────────────────
    mode_label = "[1/1]" if args.forward_only else "[2/2]"
    print(f"\n  {mode_label} Loading forward trade data...\n")
    fwd_trades = load_forward_trades(days=args.days)

    if fwd_trades is not None and not fwd_trades.empty:
        fwd_metrics = compute_strategy_metrics(fwd_trades)
        print_metrics_table(fwd_metrics, "FORWARD TRADING — Strategy Contributions")
    else:
        print("  No forward data available. Run with paper trading to generate logs/trade_log.csv.\n")

    # ── Comparison ────────────────────────────────────────────────────────
    if not bt_metrics.empty and not fwd_metrics.empty:
        print_comparison(bt_metrics, fwd_metrics)
        flags = flag_deviations(bt_metrics, fwd_metrics)
        print_deviation_flags(flags)
    elif bt_metrics.empty and fwd_metrics.empty:
        print("  No data available for analysis.\n")

    print("=" * 78)
    print("  DONE")
    print("=" * 78)


if __name__ == "__main__":
    main()
