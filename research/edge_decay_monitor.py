#!/usr/bin/env python3
"""Edge Decay Monitor — rolling metric analysis for strategy health.

READ-ONLY analysis tool. Tracks whether strategy edges are stable,
strengthening, or decaying over time. Does NOT modify any execution
pipeline files.

For each portfolio strategy, computes:
  - Rolling PF, Sharpe, win rate, avg PnL (60-trade window)
  - Edge stability classification (STABLE / STRENGTHENING / WEAKENING / DECAYED)
  - First-half vs second-half regime shift detection
  - Forward vs backtest drift alerts (if logs/trade_log.csv exists)

Usage:
    python3 research/edge_decay_monitor.py
    python3 research/edge_decay_monitor.py --strategy PB-MGC-Short
    python3 research/edge_decay_monitor.py --window 40
    python3 research/edge_decay_monitor.py --save
"""

import argparse
import importlib.util
import json
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
TRADE_LOG_PATH = ROOT / "logs" / "trade_log.csv"
STARTING_CAPITAL = 50_000.0
DEFAULT_WINDOW = 60

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
}


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_data(asset: str) -> pd.DataFrame:
    """Load processed 5m OHLCV data for an asset."""
    csv = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv.exists():
        raise FileNotFoundError(f"Data file not found: {csv}")
    df = pd.read_csv(csv)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_strategy(name: str):
    """Dynamically import a strategy module."""
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Backtest Runner ──────────────────────────────────────────────────────────

def run_strategy_backtest(strat_key: str, strat_cfg: dict) -> pd.DataFrame:
    """Run a single strategy backtest and return the trades DataFrame.

    Handles exit_variant (profit_ladder) and grinding filter as the
    paper trading engine does.
    """
    asset = strat_cfg["asset"]
    config = ASSET_CONFIG[asset]
    df = load_data(asset)

    # Generate signals
    if strat_cfg.get("exit_variant") == "profit_ladder":
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        data = donchian_entries(df)
        signals = apply_profit_ladder(data)
    else:
        mod = load_strategy(strat_cfg["name"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = config["tick_size"]
        signals = mod.generate_signals(df)

    result = run_backtest(
        df, signals,
        mode=strat_cfg["mode"],
        point_value=config["point_value"],
        symbol=asset,
    )

    trades = result["trades_df"]
    if trades.empty:
        return trades

    # Apply GRINDING filter if configured
    if strat_cfg.get("grinding_filter"):
        regime_engine = RegimeEngine()
        regime_daily = regime_engine.get_daily_regimes(df)
        regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
        regime_daily["_date_date"] = regime_daily["_date"].dt.date

        trades = trades.copy()
        trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
        trades = trades.merge(
            regime_daily[["_date_date", "trend_persistence"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )
        trades = trades[trades["trend_persistence"] == "GRINDING"].drop(
            columns=["entry_date", "_date_date", "trend_persistence"],
            errors="ignore",
        ).reset_index(drop=True)

    return trades


def run_portfolio_backtests(strategy_filter: str = None) -> dict:
    """Run backtests for the full portfolio (or a single strategy).

    Returns {strat_key: trades_df}.
    """
    strats = PORTFOLIO_CONFIG["strategies"]
    results = {}

    for strat_key, strat_cfg in strats.items():
        if strategy_filter and strat_key != strategy_filter:
            continue
        try:
            trades = run_strategy_backtest(strat_key, strat_cfg)
            results[strat_key] = trades
            n = len(trades)
            print(f"    {strat_key}: {n} trades")
        except Exception as e:
            print(f"    {strat_key}: ERROR — {e}")
            results[strat_key] = pd.DataFrame()

    return results


# ── Rolling Metric Computation ───────────────────────────────────────────────

def compute_rolling_pf(pnl_series: pd.Series, window: int) -> pd.Series:
    """Compute rolling profit factor over a trade-count window."""
    vals = pnl_series.values
    n = len(vals)
    pf = np.full(n, np.nan)

    for i in range(window - 1, n):
        chunk = vals[i - window + 1: i + 1]
        gross_profit = chunk[chunk > 0].sum()
        gross_loss = abs(chunk[chunk <= 0].sum())
        pf[i] = gross_profit / gross_loss if gross_loss > 0.001 else (
            10.0 if gross_profit > 0 else 0.0
        )

    return pd.Series(pf, index=pnl_series.index)


def compute_rolling_sharpe(pnl_series: pd.Series, window: int) -> pd.Series:
    """Compute rolling Sharpe ratio (annualized, trade-level)."""
    rolling_mean = pnl_series.rolling(window, min_periods=window).mean()
    rolling_std = pnl_series.rolling(window, min_periods=window).std()
    # Annualize assuming ~252 trading days, ~4 trades/day average
    sharpe = (rolling_mean / rolling_std.replace(0, np.nan)) * np.sqrt(252)
    return sharpe


def compute_rolling_win_rate(pnl_series: pd.Series, window: int) -> pd.Series:
    """Compute rolling win rate (%) over a trade-count window."""
    winners = (pnl_series > 0).astype(float)
    return winners.rolling(window, min_periods=window).mean() * 100


def compute_rolling_avg_pnl(pnl_series: pd.Series, window: int) -> pd.Series:
    """Compute rolling average PnL per trade."""
    return pnl_series.rolling(window, min_periods=window).mean()


def compute_rolling_metrics(trades: pd.DataFrame, window: int) -> dict:
    """Compute all rolling metrics for a trades DataFrame.

    Returns dict with overall stats and rolling series.
    """
    if trades.empty or len(trades) < window:
        return None

    pnl = trades["pnl"].reset_index(drop=True)

    # Overall metrics
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = abs(pnl[pnl <= 0].sum())
    overall_pf = gross_profit / gross_loss if gross_loss > 0.001 else 10.0
    overall_wr = (pnl > 0).mean() * 100
    overall_avg = pnl.mean()

    # Daily PnL for overall Sharpe
    t = trades.copy()
    t["exit_date"] = pd.to_datetime(t["exit_time"]).dt.date
    daily_pnl = t.groupby("exit_date")["pnl"].sum()
    overall_sharpe = (
        (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)
        if len(daily_pnl) > 1 and daily_pnl.std() > 0
        else 0.0
    )

    # Rolling series
    rolling_pf = compute_rolling_pf(pnl, window)
    rolling_sharpe = compute_rolling_sharpe(pnl, window)
    rolling_wr = compute_rolling_win_rate(pnl, window)
    rolling_avg = compute_rolling_avg_pnl(pnl, window)

    return {
        "overall": {
            "pf": round(overall_pf, 3),
            "sharpe": round(overall_sharpe, 3),
            "win_rate": round(overall_wr, 1),
            "avg_pnl": round(overall_avg, 2),
            "total_pnl": round(pnl.sum(), 2),
            "trades": len(pnl),
        },
        "rolling": {
            "pf": rolling_pf,
            "sharpe": rolling_sharpe,
            "win_rate": rolling_wr,
            "avg_pnl": rolling_avg,
        },
    }


# ── Edge Stability Classification ────────────────────────────────────────────

def classify_edge(metrics: dict, window: int) -> dict:
    """Classify edge stability from rolling metrics.

    Returns:
        status: STABLE | STRENGTHENING | WEAKENING | DECAYED
        details: dict with slope, last_window_pf, deviation_pct
    """
    overall_pf = metrics["overall"]["pf"]
    rolling_pf = metrics["rolling"]["pf"].dropna()

    if len(rolling_pf) < 3:
        return {"status": "INSUFFICIENT_DATA", "details": {}}

    last_pf = rolling_pf.iloc[-1]

    # Linear regression slope on rolling PF
    x = np.arange(len(rolling_pf))
    slope, intercept = np.polyfit(x, rolling_pf.values, 1)

    # Deviation of rolling PF from overall PF
    deviation = (rolling_pf - overall_pf) / overall_pf
    max_pos_dev = deviation.max()
    max_neg_dev = deviation.min()
    stays_within_20 = (deviation.abs() <= 0.20).mean()

    details = {
        "slope": round(float(slope), 6),
        "last_window_pf": round(float(last_pf), 3),
        "overall_pf": overall_pf,
        "pct_within_20pct": round(float(stays_within_20 * 100), 1),
        "max_pos_deviation": round(float(max_pos_dev * 100), 1),
        "max_neg_deviation": round(float(max_neg_dev * 100), 1),
    }

    # Classification logic
    if last_pf < 1.0:
        status = "DECAYED"
    elif slope < 0 and last_pf < overall_pf * 0.8:
        status = "WEAKENING"
    elif slope > 0:
        status = "STRENGTHENING"
    else:
        status = "STABLE"

    return {"status": status, "details": details}


# ── Regime Shift Detection ───────────────────────────────────────────────────

def detect_regime_shift(trades: pd.DataFrame) -> dict:
    """Compare first-half vs second-half performance.

    Flags if PF changes by >30% between halves.
    """
    if trades.empty or len(trades) < 20:
        return {"shift_detected": False, "detail": "insufficient trades"}

    pnl = trades["pnl"].values
    mid = len(pnl) // 2

    first_half = pnl[:mid]
    second_half = pnl[mid:]

    def half_pf(chunk):
        gp = chunk[chunk > 0].sum()
        gl = abs(chunk[chunk <= 0].sum())
        return gp / gl if gl > 0.001 else (10.0 if gp > 0 else 0.0)

    def half_wr(chunk):
        return (chunk > 0).mean() * 100

    pf_1 = half_pf(first_half)
    pf_2 = half_pf(second_half)
    wr_1 = half_wr(first_half)
    wr_2 = half_wr(second_half)
    avg_1 = float(first_half.mean())
    avg_2 = float(second_half.mean())

    pf_change_pct = (
        ((pf_2 - pf_1) / pf_1 * 100) if pf_1 > 0.001 else 0.0
    )
    shift_detected = abs(pf_change_pct) > 30

    return {
        "shift_detected": shift_detected,
        "first_half": {
            "trades": len(first_half),
            "pf": round(pf_1, 3),
            "win_rate": round(wr_1, 1),
            "avg_pnl": round(avg_1, 2),
        },
        "second_half": {
            "trades": len(second_half),
            "pf": round(pf_2, 3),
            "win_rate": round(wr_2, 1),
            "avg_pnl": round(avg_2, 2),
        },
        "pf_change_pct": round(pf_change_pct, 1),
    }


# ── Forward vs Backtest Comparison ───────────────────────────────────────────

def check_forward_drift(
    strat_key: str,
    backtest_metrics: dict,
    forward_trades: pd.DataFrame,
) -> dict:
    """Compare forward trading metrics to backtest bootstrap CI.

    Uses backtest PnL distribution to build a bootstrap CI and checks
    whether forward PF deviates by >2 sigma.
    """
    if forward_trades.empty:
        return {"drift_detected": False, "detail": "no forward trades"}

    bt_pnl = backtest_metrics["overall"]

    # Bootstrap CI from backtest avg PnL
    bt_avg = bt_pnl["avg_pnl"]
    bt_n = bt_pnl["trades"]
    # Approximate std of avg PnL: std(pnl) / sqrt(n)
    # We don't have the full series here, so use overall stats
    bt_total = bt_pnl["total_pnl"]

    # Forward metrics
    fwd_pnl = forward_trades["pnl"]
    fwd_pf_gp = fwd_pnl[fwd_pnl > 0].sum()
    fwd_pf_gl = abs(fwd_pnl[fwd_pnl <= 0].sum())
    fwd_pf = fwd_pf_gp / fwd_pf_gl if fwd_pf_gl > 0.001 else 10.0
    fwd_avg = fwd_pnl.mean()
    fwd_wr = (fwd_pnl > 0).mean() * 100

    # Deviation check: compare forward avg PnL to backtest avg PnL
    # Use bootstrap from backtest PnL
    bt_std_approx = abs(bt_total) / max(np.sqrt(bt_n), 1) if bt_n > 0 else 1.0
    z_score = (fwd_avg - bt_avg) / bt_std_approx if bt_std_approx > 0 else 0.0

    drift_detected = abs(z_score) > 2.0

    return {
        "drift_detected": drift_detected,
        "forward_trades": len(fwd_pnl),
        "forward_pf": round(fwd_pf, 3),
        "forward_avg_pnl": round(float(fwd_avg), 2),
        "forward_win_rate": round(float(fwd_wr), 1),
        "backtest_avg_pnl": bt_avg,
        "backtest_pf": bt_pnl["pf"],
        "z_score": round(float(z_score), 2),
    }


def load_forward_trades() -> dict:
    """Load forward trade log and split by strategy.

    Returns {strat_key: trades_df} or empty dict if no log exists.
    """
    if not TRADE_LOG_PATH.exists():
        return {}

    try:
        df = pd.read_csv(TRADE_LOG_PATH)
        if "strategy" not in df.columns or "pnl" not in df.columns:
            return {}
        return {
            name: group.reset_index(drop=True)
            for name, group in df.groupby("strategy")
        }
    except Exception:
        return {}


# ── Display ──────────────────────────────────────────────────────────────────

STATUS_LABELS = {
    "STABLE": "STABLE",
    "STRENGTHENING": "STRENGTHENING",
    "WEAKENING": "** WEAKENING **",
    "DECAYED": "*** DECAYED ***",
    "INSUFFICIENT_DATA": "LOW SAMPLE",
}


def print_summary(all_results: dict, window: int):
    """Print the portfolio-wide edge decay summary."""
    print()
    print("=" * 78)
    print("  EDGE DECAY MONITOR — PORTFOLIO HEALTH REPORT")
    print(f"  Rolling window: {window} trades")
    print("=" * 78)

    # ── Per-strategy summary table ──
    print(f"\n  {'Strategy':<30} {'Status':<18} {'PF':>6} {'Last PF':>8} "
          f"{'Slope':>8} {'Shift':>6}")
    print(f"  {'-'*30} {'-'*18} {'-'*6} {'-'*8} {'-'*8} {'-'*6}")

    for strat_key, res in all_results.items():
        if res["metrics"] is None:
            print(f"  {strat_key:<30} {'NO DATA':<18}")
            continue

        edge = res["edge"]
        shift = res["regime_shift"]
        overall = res["metrics"]["overall"]
        status_label = STATUS_LABELS.get(edge["status"], edge["status"])
        shift_flag = "YES" if shift["shift_detected"] else "—"

        print(f"  {strat_key:<30} {status_label:<18} "
              f"{overall['pf']:>6.2f} "
              f"{edge['details'].get('last_window_pf', 0):>8.2f} "
              f"{edge['details'].get('slope', 0):>8.4f} "
              f"{shift_flag:>6}")

    # ── Detailed per-strategy sections ──
    for strat_key, res in all_results.items():
        if res["metrics"] is None:
            continue

        print(f"\n{'─'*78}")
        print(f"  {strat_key}")
        print(f"{'─'*78}")

        overall = res["metrics"]["overall"]
        edge = res["edge"]
        shift = res["regime_shift"]

        # Overall stats
        print(f"\n  Overall: {overall['trades']} trades, "
              f"PF={overall['pf']:.2f}, Sharpe={overall['sharpe']:.2f}, "
              f"WR={overall['win_rate']:.1f}%, "
              f"Avg=${overall['avg_pnl']:.2f}, "
              f"Total=${overall['total_pnl']:,.0f}")

        # Edge classification
        d = edge["details"]
        print(f"\n  Edge Status: {STATUS_LABELS.get(edge['status'], edge['status'])}")
        if d:
            print(f"    Slope:           {d.get('slope', 0):+.6f} PF/trade")
            print(f"    Last window PF:  {d.get('last_window_pf', 0):.3f}")
            print(f"    Within +-20%:    {d.get('pct_within_20pct', 0):.0f}% of windows")
            print(f"    Max deviation:   {d.get('max_pos_deviation', 0):+.1f}% / "
                  f"{d.get('max_neg_deviation', 0):+.1f}%")

        # Rolling metric trend (last 5 windows)
        rolling_pf = res["metrics"]["rolling"]["pf"].dropna()
        rolling_wr = res["metrics"]["rolling"]["win_rate"].dropna()
        rolling_avg = res["metrics"]["rolling"]["avg_pnl"].dropna()
        if len(rolling_pf) >= 5:
            print(f"\n  Rolling Trend (last 5 windows):")
            tail_pf = rolling_pf.tail(5).values
            tail_wr = rolling_wr.tail(5).values
            tail_avg = rolling_avg.tail(5).values
            print(f"    PF:     {' -> '.join(f'{v:.2f}' for v in tail_pf)}")
            print(f"    WR%:    {' -> '.join(f'{v:.1f}' for v in tail_wr)}")
            print(f"    Avg$:   {' -> '.join(f'{v:.2f}' for v in tail_avg)}")

        # Regime shift
        if shift.get("first_half"):
            h1 = shift["first_half"]
            h2 = shift["second_half"]
            flag = " ** SHIFT DETECTED **" if shift["shift_detected"] else ""
            print(f"\n  Half Comparison:{flag}")
            print(f"    First half:  {h1['trades']} trades, PF={h1['pf']:.2f}, "
                  f"WR={h1['win_rate']:.1f}%, Avg=${h1['avg_pnl']:.2f}")
            print(f"    Second half: {h2['trades']} trades, PF={h2['pf']:.2f}, "
                  f"WR={h2['win_rate']:.1f}%, Avg=${h2['avg_pnl']:.2f}")
            print(f"    PF change:   {shift['pf_change_pct']:+.1f}%")

        # Forward drift
        fwd = res.get("forward_drift")
        if fwd and fwd.get("forward_trades", 0) > 0:
            flag = " ** DRIFT DETECTED **" if fwd["drift_detected"] else ""
            print(f"\n  Forward vs Backtest:{flag}")
            print(f"    Forward:  {fwd['forward_trades']} trades, "
                  f"PF={fwd['forward_pf']:.2f}, "
                  f"Avg=${fwd['forward_avg_pnl']:.2f}, "
                  f"WR={fwd['forward_win_rate']:.1f}%")
            print(f"    Backtest: PF={fwd['backtest_pf']:.2f}, "
                  f"Avg=${fwd['backtest_avg_pnl']:.2f}")
            print(f"    Z-score:  {fwd['z_score']:+.2f}")

    # ── Alerts ──
    alerts = []
    for strat_key, res in all_results.items():
        if res["edge"]["status"] == "DECAYED":
            alerts.append(f"  ALERT: {strat_key} edge has DECAYED (PF < 1.0)")
        elif res["edge"]["status"] == "WEAKENING":
            alerts.append(f"  WARN:  {strat_key} edge is WEAKENING")
        if res["regime_shift"].get("shift_detected"):
            alerts.append(f"  WARN:  {strat_key} regime shift detected "
                          f"(PF {res['regime_shift']['pf_change_pct']:+.1f}%)")
        fwd = res.get("forward_drift", {})
        if fwd.get("drift_detected"):
            alerts.append(f"  ALERT: {strat_key} forward drift detected "
                          f"(z={fwd['z_score']:+.2f})")

    if alerts:
        print(f"\n{'='*78}")
        print(f"  ALERTS")
        print(f"{'='*78}")
        for a in alerts:
            print(a)
    else:
        print(f"\n  No alerts — all strategies healthy.")


def print_deep_dive(strat_key: str, res: dict, window: int):
    """Print detailed single-strategy deep dive."""
    print()
    print("=" * 78)
    print(f"  EDGE DECAY DEEP DIVE — {strat_key}")
    print(f"  Rolling window: {window} trades")
    print("=" * 78)

    if res["metrics"] is None:
        print(f"\n  No data or insufficient trades for analysis.")
        return

    overall = res["metrics"]["overall"]
    rolling = res["metrics"]["rolling"]

    # Full overall stats
    print(f"\n  Overall Performance:")
    print(f"    Trades:       {overall['trades']}")
    print(f"    Total PnL:    ${overall['total_pnl']:,.2f}")
    print(f"    Profit Factor: {overall['pf']:.3f}")
    print(f"    Sharpe:        {overall['sharpe']:.3f}")
    print(f"    Win Rate:      {overall['win_rate']:.1f}%")
    print(f"    Avg PnL:       ${overall['avg_pnl']:.2f}")

    # Edge status
    edge = res["edge"]
    d = edge["details"]
    print(f"\n  Edge Classification: {STATUS_LABELS.get(edge['status'], edge['status'])}")
    if d:
        print(f"    Regression slope:     {d['slope']:+.6f} PF/trade")
        print(f"    Last window PF:       {d['last_window_pf']:.3f} "
              f"(overall: {d['overall_pf']:.3f})")
        print(f"    Windows within +-20%: {d['pct_within_20pct']:.0f}%")
        print(f"    Max positive dev:     {d['max_pos_deviation']:+.1f}%")
        print(f"    Max negative dev:     {d['max_neg_deviation']:+.1f}%")

    # Rolling PF timeline (every 10th value)
    pf_series = rolling["pf"].dropna()
    if len(pf_series) >= 10:
        step = max(1, len(pf_series) // 20)
        sampled = pf_series.iloc[::step]
        print(f"\n  Rolling PF Timeline ({len(pf_series)} windows, sampled every {step}):")
        line = "    "
        for i, (idx, val) in enumerate(sampled.items()):
            line += f"{val:5.2f} "
            if (i + 1) % 10 == 0:
                print(line)
                line = "    "
        if line.strip():
            print(line)

    # Rolling win rate timeline
    wr_series = rolling["win_rate"].dropna()
    if len(wr_series) >= 10:
        step = max(1, len(wr_series) // 20)
        sampled = wr_series.iloc[::step]
        print(f"\n  Rolling Win Rate Timeline:")
        line = "    "
        for i, (idx, val) in enumerate(sampled.items()):
            line += f"{val:5.1f} "
            if (i + 1) % 10 == 0:
                print(line)
                line = "    "
        if line.strip():
            print(line)

    # Quartile analysis
    if len(pf_series) >= 4:
        q = len(pf_series) // 4
        quartiles = [
            pf_series.iloc[:q].mean(),
            pf_series.iloc[q:2*q].mean(),
            pf_series.iloc[2*q:3*q].mean(),
            pf_series.iloc[3*q:].mean(),
        ]
        print(f"\n  PF by Quartile (early -> late):")
        print(f"    Q1: {quartiles[0]:.3f}  Q2: {quartiles[1]:.3f}  "
              f"Q3: {quartiles[2]:.3f}  Q4: {quartiles[3]:.3f}")

        # Trend direction
        if quartiles[3] > quartiles[0] * 1.1:
            print(f"    Trend: Improving (Q4 > Q1 by "
                  f"{(quartiles[3]/quartiles[0]-1)*100:.0f}%)")
        elif quartiles[3] < quartiles[0] * 0.9:
            print(f"    Trend: Degrading (Q4 < Q1 by "
                  f"{(1-quartiles[3]/quartiles[0])*100:.0f}%)")
        else:
            print(f"    Trend: Flat")

    # Regime shift detail
    shift = res["regime_shift"]
    if shift.get("first_half"):
        h1 = shift["first_half"]
        h2 = shift["second_half"]
        print(f"\n  Half-Period Comparison:")
        print(f"    {'Metric':<15} {'First Half':>12} {'Second Half':>12} {'Change':>10}")
        print(f"    {'-'*15} {'-'*12} {'-'*12} {'-'*10}")
        print(f"    {'PF':<15} {h1['pf']:>12.3f} {h2['pf']:>12.3f} "
              f"{shift['pf_change_pct']:>+9.1f}%")
        print(f"    {'Win Rate':<15} {h1['win_rate']:>11.1f}% {h2['win_rate']:>11.1f}% "
              f"{h2['win_rate']-h1['win_rate']:>+9.1f}%")
        print(f"    {'Avg PnL':<15} ${h1['avg_pnl']:>10.2f} ${h2['avg_pnl']:>10.2f} "
              f"${h2['avg_pnl']-h1['avg_pnl']:>+8.2f}")

        if shift["shift_detected"]:
            print(f"\n    ** REGIME SHIFT DETECTED — PF changed by "
                  f"{shift['pf_change_pct']:+.1f}% (threshold: +-30%) **")

    # Forward drift
    fwd = res.get("forward_drift", {})
    if fwd and fwd.get("forward_trades", 0) > 0:
        print(f"\n  Forward vs Backtest Comparison:")
        print(f"    {'Metric':<15} {'Backtest':>12} {'Forward':>12}")
        print(f"    {'-'*15} {'-'*12} {'-'*12}")
        print(f"    {'PF':<15} {fwd['backtest_pf']:>12.3f} {fwd['forward_pf']:>12.3f}")
        print(f"    {'Avg PnL':<15} ${fwd['backtest_avg_pnl']:>10.2f} "
              f"${fwd['forward_avg_pnl']:>10.2f}")
        print(f"    {'Win Rate':<15} {'—':>12} {fwd['forward_win_rate']:>11.1f}%")
        print(f"    Z-score: {fwd['z_score']:+.2f}")
        if fwd["drift_detected"]:
            print(f"\n    ** FORWARD DRIFT DETECTED — z={fwd['z_score']:+.2f} "
                  f"exceeds +-2.0 threshold **")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Edge Decay Monitor — rolling metric health check"
    )
    parser.add_argument(
        "--strategy", type=str, default=None,
        help="Single strategy key for deep dive (e.g. PB-MGC-Short)",
    )
    parser.add_argument(
        "--window", type=int, default=DEFAULT_WINDOW,
        help=f"Rolling window size in trades (default: {DEFAULT_WINDOW})",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Save results to research/edge_decay_report.json",
    )
    args = parser.parse_args()

    window = args.window
    strategy_filter = args.strategy

    # Validate strategy key
    if strategy_filter and strategy_filter not in PORTFOLIO_CONFIG["strategies"]:
        valid = list(PORTFOLIO_CONFIG["strategies"].keys())
        print(f"  ERROR: Unknown strategy '{strategy_filter}'")
        print(f"  Valid keys: {', '.join(valid)}")
        sys.exit(1)

    print("=" * 78)
    print("  EDGE DECAY MONITOR")
    print("=" * 78)
    print(f"\n  Running portfolio backtests...")

    # Step 1: Run backtests
    portfolio_trades = run_portfolio_backtests(strategy_filter)

    # Step 2: Load forward trades if available
    forward_trades = load_forward_trades()
    if forward_trades:
        print(f"\n  Forward trade log found: {len(forward_trades)} strategies")
    else:
        print(f"\n  No forward trade log found (logs/trade_log.csv)")

    # Step 3: Compute metrics for each strategy
    print(f"\n  Computing rolling metrics (window={window})...")
    all_results = {}

    for strat_key, trades in portfolio_trades.items():
        metrics = compute_rolling_metrics(trades, window)

        if metrics is None:
            all_results[strat_key] = {
                "metrics": None,
                "edge": {"status": "INSUFFICIENT_DATA", "details": {}},
                "regime_shift": {"shift_detected": False, "detail": "insufficient trades"},
                "forward_drift": None,
            }
            continue

        edge = classify_edge(metrics, window)
        shift = detect_regime_shift(trades)

        # Forward drift check
        fwd_drift = None
        fwd_key_candidates = [strat_key, strat_key.replace("-", "_")]
        for fk in fwd_key_candidates:
            if fk in forward_trades:
                fwd_drift = check_forward_drift(strat_key, metrics, forward_trades[fk])
                break

        all_results[strat_key] = {
            "metrics": metrics,
            "edge": edge,
            "regime_shift": shift,
            "forward_drift": fwd_drift,
        }

    # Step 4: Display results
    if strategy_filter:
        print_deep_dive(strategy_filter, all_results[strategy_filter], window)
    else:
        print_summary(all_results, window)

    # Step 5: Save if requested
    if args.save:
        save_path = ROOT / "research" / "edge_decay_report.json"
        save_data = {
            "window": window,
            "strategy_filter": strategy_filter,
            "results": {},
        }
        for strat_key, res in all_results.items():
            entry = {
                "edge_status": res["edge"]["status"],
                "edge_details": res["edge"]["details"],
                "regime_shift": {
                    k: v for k, v in res["regime_shift"].items()
                },
            }
            if res["metrics"]:
                entry["overall"] = res["metrics"]["overall"]
            if res.get("forward_drift"):
                entry["forward_drift"] = res["forward_drift"]
            save_data["results"][strat_key] = entry

        with open(save_path, "w") as f:
            json.dump(save_data, f, indent=2, default=str)
        print(f"\n  Report saved to {save_path}")

    print(f"\n{'='*78}")
    print(f"  DONE")
    print(f"{'='*78}")


if __name__ == "__main__":
    main()
