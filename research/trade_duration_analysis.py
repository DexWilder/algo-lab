#!/usr/bin/env python3
"""Trade Duration Analysis — Relationship between hold time and profitability.

READ-ONLY research tool. Does NOT modify any execution pipeline files.

Analyzes the 6-strategy portfolio to understand how trade duration relates
to PnL, win rate, and optimal exit timing. Produces duration buckets,
winner/loser hold time comparisons, time-decay curves, and actionable flags.

Usage:
    python3 research/trade_duration_analysis.py
    python3 research/trade_duration_analysis.py --strategy PB-MGC-Short
    python3 research/trade_duration_analysis.py --strategy VWAP-MNQ-Long

Flags:
    --strategy KEY   Analyze a single strategy in detail (uses PORTFOLIO_CONFIG keys)
    --no-controller  Use baseline (always-on) trades instead of controller-filtered
"""

import argparse
import importlib.util
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.strategy_controller import StrategyController, PORTFOLIO_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
}

BAR_MINUTES = 5  # 5-minute bars

# Duration buckets (in bars)
DURATION_BUCKETS = [
    ("< 5 bars",    0,   5),
    ("5-15 bars",   5,  15),
    ("15-30 bars", 15,  30),
    ("30-60 bars", 30,  60),
    ("60-120 bars", 60, 120),
    ("120+ bars",  120, 99999),
]


# ── Strategy loading ─────────────────────────────────────────────────────────

def load_strategy(name: str):
    """Load a strategy module by name from strategies/<name>/strategy.py."""
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    """Load processed 5-minute OHLCV data for an asset."""
    csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def generate_signals(mod, df, asset=None, mode=None):
    """Run generate_signals with optional asset/mode kwargs."""
    sig = inspect.signature(mod.generate_signals)
    params = list(sig.parameters.keys())
    kwargs = {}
    if "asset" in params:
        kwargs["asset"] = asset
    if "mode" in params:
        kwargs["mode"] = mode
    return mod.generate_signals(df, **kwargs)


# ── Backtest runner ──────────────────────────────────────────────────────────

def run_portfolio_backtests(use_controller: bool = True) -> dict:
    """Run the 6-strategy portfolio and return trades per strategy.

    Returns {strat_key: trades_df} where trades_df has columns:
    entry_time, exit_time, side, entry_price, exit_price, pnl, contracts
    """
    strat_configs = PORTFOLIO_CONFIG["strategies"]
    regime_engine = RegimeEngine()

    data_cache = {}
    regime_daily_cache = {}
    baseline_trades = {}

    print("  Loading strategies and running backtests...")

    for strat_key, strat in strat_configs.items():
        asset = strat["asset"]
        config = ASSET_CONFIG[asset]

        if asset not in data_cache:
            df = load_data(asset)
            data_cache[asset] = df
            regime_daily_cache[asset] = regime_engine.get_daily_regimes(df)

        df = data_cache[asset]
        mod = load_strategy(strat["name"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = config["tick_size"]

        # Handle exit variant (Donchian profit_ladder)
        if strat.get("exit_variant") == "profit_ladder":
            from research.exit_evolution import donchian_entries, apply_profit_ladder
            data = donchian_entries(df)
            signals = apply_profit_ladder(data)
        else:
            signals = generate_signals(mod, df, asset=asset, mode=strat["mode"])

        result = run_backtest(
            df, signals,
            mode=strat["mode"],
            point_value=config["point_value"],
            symbol=asset,
        )
        trades = result["trades_df"]

        # Apply GRINDING filter for Donchian
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
        tc = len(trades)
        pnl = trades["pnl"].sum() if not trades.empty else 0
        print(f"    {strat_key}: {tc} trades, PnL=${pnl:,.0f}")

    if use_controller:
        print("\n  Applying strategy controller filters...")
        controller = StrategyController(PORTFOLIO_CONFIG)
        ctrl_result = controller.simulate(baseline_trades, regime_daily_cache)
        controlled = ctrl_result["filtered_trades"]
        total_base = sum(len(t) for t in baseline_trades.values())
        total_ctrl = sum(len(t) for t in controlled.values())
        print(f"    Trades: {total_base} baseline -> {total_ctrl} controlled")
        return controlled
    else:
        return baseline_trades


# ── Duration computation ─────────────────────────────────────────────────────

def add_duration_columns(trades: pd.DataFrame) -> pd.DataFrame:
    """Add duration_bars and duration_minutes columns to a trades DataFrame."""
    if trades.empty:
        trades["duration_bars"] = []
        trades["duration_minutes"] = []
        return trades

    t = trades.copy()
    t["entry_dt"] = pd.to_datetime(t["entry_time"])
    t["exit_dt"] = pd.to_datetime(t["exit_time"])
    t["duration_minutes"] = (t["exit_dt"] - t["entry_dt"]).dt.total_seconds() / 60.0
    t["duration_bars"] = (t["duration_minutes"] / BAR_MINUTES).round().astype(int)
    # Floor at 1 bar minimum
    t["duration_bars"] = t["duration_bars"].clip(lower=1)
    return t


# ── Analysis functions ───────────────────────────────────────────────────────

def compute_hold_time_stats(trades: pd.DataFrame) -> dict:
    """Compute hold time distribution statistics."""
    if trades.empty:
        return {"count": 0}

    bars = trades["duration_bars"]
    mins = trades["duration_minutes"]

    return {
        "count": len(trades),
        "avg_bars": round(bars.mean(), 1),
        "avg_minutes": round(mins.mean(), 1),
        "median_bars": round(bars.median(), 1),
        "median_minutes": round(mins.median(), 1),
        "p10_bars": round(bars.quantile(0.10), 1),
        "p25_bars": round(bars.quantile(0.25), 1),
        "p50_bars": round(bars.quantile(0.50), 1),
        "p75_bars": round(bars.quantile(0.75), 1),
        "p90_bars": round(bars.quantile(0.90), 1),
    }


def compute_winner_loser_duration(trades: pd.DataFrame) -> dict:
    """Compare hold times for winners vs losers."""
    if trades.empty:
        return {}

    winners = trades[trades["pnl"] > 0]
    losers = trades[trades["pnl"] <= 0]

    result = {}
    if not winners.empty:
        result["winner_avg_bars"] = round(winners["duration_bars"].mean(), 1)
        result["winner_median_bars"] = round(winners["duration_bars"].median(), 1)
        result["winner_count"] = len(winners)
    if not losers.empty:
        result["loser_avg_bars"] = round(losers["duration_bars"].mean(), 1)
        result["loser_median_bars"] = round(losers["duration_bars"].median(), 1)
        result["loser_count"] = len(losers)

    # Ratio: winners shorter than losers? (< 1.0 means winners are shorter)
    if not winners.empty and not losers.empty:
        result["winner_loser_ratio"] = round(
            winners["duration_bars"].mean() / max(losers["duration_bars"].mean(), 0.1), 2
        )

    return result


def compute_pnl_duration_correlation(trades: pd.DataFrame) -> float:
    """Pearson correlation between hold time (bars) and PnL."""
    if len(trades) < 5:
        return 0.0
    return round(trades["duration_bars"].corr(trades["pnl"]), 3)


def compute_duration_buckets(trades: pd.DataFrame) -> list[dict]:
    """Break trades into duration buckets with per-bucket stats."""
    if trades.empty:
        return []

    rows = []
    for label, lo, hi in DURATION_BUCKETS:
        bucket = trades[(trades["duration_bars"] >= lo) & (trades["duration_bars"] < hi)]
        if bucket.empty:
            rows.append({
                "bucket": label, "trades": 0, "win_rate": 0.0,
                "avg_pnl": 0.0, "net_pnl": 0.0, "pct_of_trades": 0.0,
            })
            continue

        winners = bucket[bucket["pnl"] > 0]
        rows.append({
            "bucket": label,
            "trades": len(bucket),
            "win_rate": round(len(winners) / len(bucket) * 100, 1),
            "avg_pnl": round(bucket["pnl"].mean(), 2),
            "net_pnl": round(bucket["pnl"].sum(), 2),
            "pct_of_trades": round(len(bucket) / len(trades) * 100, 1),
        })

    return rows


def find_optimal_exit_window(buckets: list[dict]) -> str:
    """Return the duration bucket with the highest average PnL."""
    active = [b for b in buckets if b["trades"] >= 3]
    if not active:
        return "N/A (insufficient data)"
    best = max(active, key=lambda b: b["avg_pnl"])
    return f"{best['bucket']} (avg PnL=${best['avg_pnl']:.2f}, {best['trades']} trades)"


def compute_time_decay(trades: pd.DataFrame) -> list[dict]:
    """For winning trades, estimate at what bar count remaining PnL starts declining.

    Groups winning trades by duration bucket and computes avg PnL per bucket.
    The peak bucket is where winners are most profitable; after that is 'time decay'.
    """
    winners = trades[trades["pnl"] > 0]
    if winners.empty:
        return []

    rows = []
    for label, lo, hi in DURATION_BUCKETS:
        bucket = winners[(winners["duration_bars"] >= lo) & (winners["duration_bars"] < hi)]
        if bucket.empty:
            rows.append({"bucket": label, "winner_count": 0, "avg_winner_pnl": 0.0})
            continue
        rows.append({
            "bucket": label,
            "winner_count": len(bucket),
            "avg_winner_pnl": round(bucket["pnl"].mean(), 2),
        })

    return rows


def find_decay_point(decay_data: list[dict]) -> str:
    """Find the bucket after which avg winner PnL starts declining."""
    active = [d for d in decay_data if d["winner_count"] >= 2]
    if len(active) < 2:
        return "N/A (insufficient data)"

    peak_idx = 0
    peak_pnl = active[0]["avg_winner_pnl"]
    for i, d in enumerate(active):
        if d["avg_winner_pnl"] > peak_pnl:
            peak_pnl = d["avg_winner_pnl"]
            peak_idx = i

    if peak_idx == len(active) - 1:
        return f"No decay detected — longest bucket is peak ({active[peak_idx]['bucket']})"

    return (f"Peak at {active[peak_idx]['bucket']} "
            f"(avg=${active[peak_idx]['avg_winner_pnl']:.2f}), "
            f"declines after into {active[peak_idx + 1]['bucket']}")


# ── Flags / Alerts ───────────────────────────────────────────────────────────

def check_flags(strat_key: str, trades: pd.DataFrame, wl: dict,
                buckets: list[dict]) -> list[str]:
    """Generate actionable flags for a strategy."""
    flags = []

    # Flag 1: Winners significantly shorter than losers
    if ("winner_avg_bars" in wl and "loser_avg_bars" in wl
            and wl.get("winner_loser_ratio", 1.0) < 0.7):
        flags.append(
            f"EARLY-EXIT OPPORTUNITY: Winners avg {wl['winner_avg_bars']} bars vs "
            f"losers avg {wl['loser_avg_bars']} bars (ratio={wl['winner_loser_ratio']}). "
            f"Consider tighter time-based exits."
        )

    # Flag 2: Long-duration trades lose money
    long_buckets = [b for b in buckets if b["bucket"] in ("60-120 bars", "120+ bars")]
    for b in long_buckets:
        if b["trades"] >= 3 and b["avg_pnl"] < 0:
            flags.append(
                f"TIME-STOP OPPORTUNITY: {b['bucket']} trades lose money "
                f"(avg PnL=${b['avg_pnl']:.2f}, {b['trades']} trades, "
                f"net=${b['net_pnl']:.2f}). Consider a time-based exit."
            )

    # Flag 3: Very short trades with low win rate
    short_buckets = [b for b in buckets if b["bucket"] == "< 5 bars"]
    for b in short_buckets:
        if b["trades"] >= 5 and b["win_rate"] < 40:
            flags.append(
                f"NOISE TRADES: {b['bucket']} has low win rate ({b['win_rate']}%, "
                f"{b['trades']} trades). Possible false signals."
            )

    return flags


# ── Display functions ────────────────────────────────────────────────────────

def print_strategy_analysis(strat_key: str, trades: pd.DataFrame, detailed: bool = False):
    """Print full duration analysis for one strategy."""
    t = add_duration_columns(trades)

    if t.empty:
        print(f"\n  {strat_key}: No trades.")
        return

    stats = compute_hold_time_stats(t)
    wl = compute_winner_loser_duration(t)
    corr = compute_pnl_duration_correlation(t)
    buckets = compute_duration_buckets(t)
    optimal = find_optimal_exit_window(buckets)
    decay = compute_time_decay(t)
    decay_point = find_decay_point(decay)
    flags = check_flags(strat_key, t, wl, buckets)

    print(f"\n  {'='*74}")
    print(f"  {strat_key}  ({stats['count']} trades)")
    print(f"  {'='*74}")

    # ── Hold time summary ──
    print(f"\n  Hold Time Summary:")
    print(f"    {'Metric':<25} {'Bars':>8}  {'Minutes':>10}")
    print(f"    {'-'*25} {'-'*8}  {'-'*10}")
    print(f"    {'Average':<25} {stats['avg_bars']:>8.1f}  {stats['avg_minutes']:>10.1f}")
    print(f"    {'Median':<25} {stats['median_bars']:>8.1f}  {stats['median_minutes']:>10.1f}")

    # ── Distribution percentiles ──
    print(f"\n  Distribution (bars):")
    print(f"    p10={stats['p10_bars']:.0f}  p25={stats['p25_bars']:.0f}  "
          f"p50={stats['p50_bars']:.0f}  p75={stats['p75_bars']:.0f}  "
          f"p90={stats['p90_bars']:.0f}")

    # ── Winners vs Losers ──
    print(f"\n  Winners vs Losers:")
    if "winner_avg_bars" in wl:
        print(f"    Winners: avg={wl['winner_avg_bars']:.1f} bars, "
              f"median={wl['winner_median_bars']:.1f} bars  ({wl['winner_count']} trades)")
    if "loser_avg_bars" in wl:
        print(f"    Losers:  avg={wl['loser_avg_bars']:.1f} bars, "
              f"median={wl['loser_median_bars']:.1f} bars  ({wl['loser_count']} trades)")
    if "winner_loser_ratio" in wl:
        print(f"    W/L duration ratio: {wl['winner_loser_ratio']:.2f} "
              f"({'winners shorter' if wl['winner_loser_ratio'] < 1.0 else 'losers shorter'})")

    print(f"\n  PnL vs Duration correlation: r={corr:+.3f}")

    # ── Duration buckets ──
    print(f"\n  Duration Buckets:")
    print(f"    {'Bucket':<14} {'Trades':>7} {'%':>6} {'WinRate':>8} "
          f"{'AvgPnL':>10} {'NetPnL':>12}")
    print(f"    {'-'*14} {'-'*7} {'-'*6} {'-'*8} {'-'*10} {'-'*12}")
    for b in buckets:
        if b["trades"] > 0:
            print(f"    {b['bucket']:<14} {b['trades']:>7} {b['pct_of_trades']:>5.1f}% "
                  f"{b['win_rate']:>7.1f}% {b['avg_pnl']:>10.2f} {b['net_pnl']:>12.2f}")

    print(f"\n  Optimal Exit Window: {optimal}")

    # ── Time decay analysis ──
    print(f"\n  Time Decay (winning trades only):")
    print(f"    {'Bucket':<14} {'Winners':>8} {'AvgWinPnL':>12}")
    print(f"    {'-'*14} {'-'*8} {'-'*12}")
    for d in decay:
        if d["winner_count"] > 0:
            print(f"    {d['bucket']:<14} {d['winner_count']:>8} {d['avg_winner_pnl']:>12.2f}")
    print(f"    Decay point: {decay_point}")

    # ── Flags ──
    if flags:
        print(f"\n  ** FLAGS **")
        for f in flags:
            print(f"    >> {f}")

    # ── Detailed: individual trade scatter (if --strategy mode) ──
    if detailed and len(t) > 0:
        print(f"\n  Top 10 Longest Trades:")
        print(f"    {'Entry':<22} {'Bars':>6} {'PnL':>10} {'Side':<6}")
        print(f"    {'-'*22} {'-'*6} {'-'*10} {'-'*6}")
        longest = t.nlargest(10, "duration_bars")
        for _, row in longest.iterrows():
            entry_str = str(row["entry_time"])[:19]
            print(f"    {entry_str:<22} {row['duration_bars']:>6} "
                  f"{row['pnl']:>10.2f} {row['side']:<6}")

        print(f"\n  Top 10 Shortest Trades:")
        print(f"    {'Entry':<22} {'Bars':>6} {'PnL':>10} {'Side':<6}")
        print(f"    {'-'*22} {'-'*6} {'-'*10} {'-'*6}")
        shortest = t.nsmallest(10, "duration_bars")
        for _, row in shortest.iterrows():
            entry_str = str(row["entry_time"])[:19]
            print(f"    {entry_str:<22} {row['duration_bars']:>6} "
                  f"{row['pnl']:>10.2f} {row['side']:<6}")


def print_portfolio_summary(all_trades: dict):
    """Print cross-strategy duration comparison table."""
    print(f"\n  {'='*74}")
    print(f"  PORTFOLIO DURATION COMPARISON")
    print(f"  {'='*74}")

    # Header
    print(f"\n  {'Strategy':<28} {'Trades':>6} {'AvgBars':>8} {'MedBars':>8} "
          f"{'WAvg':>7} {'LAvg':>7} {'W/L':>5} {'Corr':>6}")
    print(f"  {'-'*28} {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*7} {'-'*5} {'-'*6}")

    combined_trades = []

    for strat_key, trades in all_trades.items():
        t = add_duration_columns(trades)
        if t.empty:
            print(f"  {strat_key:<28} {'--':>6}")
            continue

        combined_trades.append(t)
        stats = compute_hold_time_stats(t)
        wl = compute_winner_loser_duration(t)
        corr = compute_pnl_duration_correlation(t)

        w_avg = f"{wl.get('winner_avg_bars', 0):.0f}"
        l_avg = f"{wl.get('loser_avg_bars', 0):.0f}"
        ratio = f"{wl.get('winner_loser_ratio', 0):.2f}" if "winner_loser_ratio" in wl else "--"

        print(f"  {strat_key:<28} {stats['count']:>6} {stats['avg_bars']:>8.1f} "
              f"{stats['median_bars']:>8.1f} {w_avg:>7} {l_avg:>7} {ratio:>5} {corr:>+6.3f}")

    # Portfolio aggregate
    if combined_trades:
        all_t = pd.concat(combined_trades, ignore_index=True)
        stats = compute_hold_time_stats(all_t)
        wl = compute_winner_loser_duration(all_t)
        corr = compute_pnl_duration_correlation(all_t)

        w_avg = f"{wl.get('winner_avg_bars', 0):.0f}"
        l_avg = f"{wl.get('loser_avg_bars', 0):.0f}"
        ratio = f"{wl.get('winner_loser_ratio', 0):.2f}" if "winner_loser_ratio" in wl else "--"

        print(f"  {'-'*28} {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*7} {'-'*5} {'-'*6}")
        print(f"  {'PORTFOLIO':<28} {stats['count']:>6} {stats['avg_bars']:>8.1f} "
              f"{stats['median_bars']:>8.1f} {w_avg:>7} {l_avg:>7} {ratio:>5} {corr:>+6.3f}")

        # Portfolio-level buckets
        buckets = compute_duration_buckets(all_t)
        print(f"\n  Portfolio Duration Buckets:")
        print(f"    {'Bucket':<14} {'Trades':>7} {'%':>6} {'WinRate':>8} "
              f"{'AvgPnL':>10} {'NetPnL':>12}")
        print(f"    {'-'*14} {'-'*7} {'-'*6} {'-'*8} {'-'*10} {'-'*12}")
        for b in buckets:
            if b["trades"] > 0:
                print(f"    {b['bucket']:<14} {b['trades']:>7} {b['pct_of_trades']:>5.1f}% "
                      f"{b['win_rate']:>7.1f}% {b['avg_pnl']:>10.2f} {b['net_pnl']:>12.2f}")

        optimal = find_optimal_exit_window(buckets)
        print(f"\n  Portfolio Optimal Exit Window: {optimal}")


def print_all_flags(all_trades: dict):
    """Print all flags across all strategies."""
    print(f"\n  {'='*74}")
    print(f"  ACTIONABLE FLAGS")
    print(f"  {'='*74}")

    any_flags = False
    for strat_key, trades in all_trades.items():
        t = add_duration_columns(trades)
        if t.empty:
            continue

        wl = compute_winner_loser_duration(t)
        buckets = compute_duration_buckets(t)
        flags = check_flags(strat_key, t, wl, buckets)

        if flags:
            any_flags = True
            print(f"\n  {strat_key}:")
            for f in flags:
                print(f"    >> {f}")

    if not any_flags:
        print(f"\n  No actionable flags detected.")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Trade Duration Analysis — hold time vs profitability"
    )
    parser.add_argument(
        "--strategy", type=str, default=None,
        help="Analyze a single strategy (e.g. PB-MGC-Short)"
    )
    parser.add_argument(
        "--no-controller", action="store_true",
        help="Use baseline (always-on) trades instead of controller-filtered"
    )
    args = parser.parse_args()

    use_controller = not args.no_controller

    print()
    print("=" * 78)
    print("  TRADE DURATION ANALYSIS")
    print(f"  {'Controller-managed' if use_controller else 'Baseline (always-on)'} portfolio")
    print("=" * 78)

    all_trades = run_portfolio_backtests(use_controller=use_controller)

    if args.strategy:
        # Single-strategy detailed mode
        if args.strategy not in all_trades:
            available = ", ".join(sorted(all_trades.keys()))
            print(f"\n  ERROR: Strategy '{args.strategy}' not found.")
            print(f"  Available: {available}")
            sys.exit(1)

        print_strategy_analysis(args.strategy, all_trades[args.strategy], detailed=True)
    else:
        # Full portfolio mode
        print_portfolio_summary(all_trades)

        for strat_key, trades in all_trades.items():
            print_strategy_analysis(strat_key, trades, detailed=False)

        print_all_flags(all_trades)

    print(f"\n{'='*78}")
    print(f"  DONE")
    print(f"{'='*78}\n")


if __name__ == "__main__":
    main()
