#!/usr/bin/env python3
"""
FQL Strategy Half-Life Monitor
=================================
Tracks strategy edge decay using rolling metrics to predict when edges die.

Principle: Every strategy is dying from the day it's created. Markets adapt.

Metrics tracked:
  1. Rolling Sharpe (3y, 2y, 1y, 6m windows)
  2. Rolling win rate
  3. Rolling expectancy (avg_win * win_rate - avg_loss * loss_rate)
  4. Decay score = weighted decline across all metrics

Statuses:
  - HEALTHY: decay_score < 0.10
  - MONITOR: 0.10 <= decay_score < 0.25
  - DECAYING: 0.25 <= decay_score < 0.40
  - ARCHIVE_CANDIDATE: decay_score >= 0.40

Usage:
    python3 research/strategy_half_life_monitor.py              # Full report
    python3 research/strategy_half_life_monitor.py --json       # JSON output
    python3 research/strategy_half_life_monitor.py --save       # Save to reports/
"""

import argparse
import json
import sys
import importlib.util
import inspect
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

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

# Same strategies as kill criteria
EVAL_STRATEGIES = [
    ("VWAP-MNQ-Long", "vwap_trend", "MNQ", "long"),
    ("XB-PB-EMA-MES-Short", "xb_pb_ema_timestop", "MES", "short"),
    ("ORB-MGC-Long", "orb_009", "MGC", "long"),
    ("BB-EQ-MGC-Long", "bb_equilibrium", "MGC", "long"),
    ("PB-MGC-Short", "pb_trend", "MGC", "short"),
    ("Donchian-MNQ-Long", "donchian_trend", "MNQ", "long"),
    ("NoiseBoundary-MNQ-Long", "noise_boundary", "MNQ", "long"),
    ("RangeExpansion-MCL-Short", "range_expansion", "MCL", "short"),
    ("GapMom-MGC-Long", "gap_mom", "MGC", "long"),
    ("GapMom-MNQ-Long", "gap_mom", "MNQ", "long"),
]

# Rolling windows for decay analysis (calendar days for date filtering)
ROLLING_WINDOWS = {
    "3y": 365 * 3,
    "2y": 365 * 2,
    "1y": 365,
    "6m": 183,
}

# Decay thresholds
HEALTHY_THRESHOLD = 0.10
MONITOR_THRESHOLD = 0.25
DECAYING_THRESHOLD = 0.40


# ── Strategy Loading ─────────────────────────────────────────────────────────

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

def get_strategy_trades(strategy_id: str, module_name: str,
                        asset: str, mode: str) -> pd.DataFrame:
    """Load data, generate signals, run backtest, return trades with date column."""
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


def _compute_window_metrics(pnl: np.ndarray) -> dict:
    """Compute Sharpe, win rate, and expectancy from a PnL array."""
    n = len(pnl)
    if n == 0:
        return {"sharpe": 0.0, "win_rate": 0.0, "expectancy": 0.0, "trades": 0}

    mean_pnl = float(np.mean(pnl))
    std_pnl = float(np.std(pnl, ddof=1)) if n > 1 else 1.0
    sharpe = float(mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0.0

    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    win_rate = len(wins) / n
    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(abs(np.mean(losses))) if len(losses) > 0 else 0.0
    expectancy = avg_win * win_rate - avg_loss * (1 - win_rate)

    return {
        "sharpe": round(sharpe, 4),
        "win_rate": round(win_rate, 4),
        "expectancy": round(expectancy, 2),
        "trades": n,
    }


def compute_rolling_metrics(trades: pd.DataFrame) -> dict:
    """Compute rolling metrics across multiple time windows.

    Parameters
    ----------
    trades : pd.DataFrame
        Must have 'date' and 'pnl' columns.

    Returns
    -------
    dict with keys "full", "3y", "2y", "1y", "6m", each containing
    sharpe, win_rate, expectancy, trades count.
    """
    if trades.empty:
        empty = {"sharpe": 0.0, "win_rate": 0.0, "expectancy": 0.0, "trades": 0}
        result = {"full": empty.copy()}
        for window_name in ROLLING_WINDOWS:
            result[window_name] = empty.copy()
        return result

    trades = trades.copy()
    trades["date_dt"] = pd.to_datetime(trades["date"])
    pnl_all = trades["pnl"].values
    result = {"full": _compute_window_metrics(pnl_all)}

    max_date = trades["date_dt"].max()
    for window_name, calendar_days in ROLLING_WINDOWS.items():
        cutoff = max_date - timedelta(days=calendar_days)
        window_trades = trades[trades["date_dt"] >= cutoff]
        result[window_name] = _compute_window_metrics(window_trades["pnl"].values)

    return result


def compute_decay_score(rolling_metrics: dict) -> float:
    """Compute weighted decay score from rolling metrics.

    Decay = weighted combination of metric declines between full history
    and recent (1y, falling back to 6m) window.
    """
    full = rolling_metrics["full"]
    # Prefer 1y window; fall back to 6m if 1y has too few trades
    recent = rolling_metrics.get("1y", full)
    if recent["trades"] < 10:
        recent = rolling_metrics.get("6m", full)

    # Sharpe decay (weight 0.50)
    if full["sharpe"] > 0:
        sharpe_decay = max(0.0, 1.0 - recent["sharpe"] / full["sharpe"])
    else:
        sharpe_decay = 0.5  # can't measure decay on negative baseline

    # Win rate decay (weight 0.25)
    if full["win_rate"] > 0:
        wr_decay = max(0.0, 1.0 - recent["win_rate"] / full["win_rate"])
    else:
        wr_decay = 0.5

    # Expectancy decay (weight 0.25)
    if full["expectancy"] > 0:
        exp_decay = max(0.0, 1.0 - recent["expectancy"] / full["expectancy"])
    else:
        exp_decay = 0.5

    decay_score = 0.50 * sharpe_decay + 0.25 * wr_decay + 0.25 * exp_decay
    return min(1.0, max(0.0, round(decay_score, 4)))


def get_status(decay_score: float) -> str:
    """Map decay score to human-readable status."""
    if decay_score < HEALTHY_THRESHOLD:
        return "HEALTHY"
    elif decay_score < MONITOR_THRESHOLD:
        return "MONITOR"
    elif decay_score < DECAYING_THRESHOLD:
        return "DECAYING"
    else:
        return "ARCHIVE_CANDIDATE"


def estimate_half_life(rolling_metrics: dict) -> str:
    """Estimate years until Sharpe decays to 0.5 using linear extrapolation.

    Uses the decline rate between the full-history Sharpe and the 1y Sharpe
    to project when Sharpe will cross 0.5.
    """
    full_sharpe = rolling_metrics["full"]["sharpe"]
    recent = rolling_metrics.get("1y", rolling_metrics.get("6m"))
    if recent is None or recent["trades"] < 10:
        return "N/A"

    recent_sharpe = recent["sharpe"]

    # If Sharpe is improving recently
    if recent_sharpe >= full_sharpe:
        return "Strengthening"

    if full_sharpe <= 0.5:
        return "<1 year"

    # Decay rate per year (approximate: 1y window represents ~1 year of decay)
    decay_per_year = full_sharpe - recent_sharpe
    if decay_per_year <= 0:
        return ">10 years"

    # Years until Sharpe hits 0.5
    years_to_half = (recent_sharpe - 0.5) / decay_per_year
    if years_to_half <= 0:
        return "<1 year"
    elif years_to_half > 10:
        return ">10 years"
    else:
        return f"~{years_to_half:.0f} years"


def _sharpe_trend(rolling_metrics: dict) -> str:
    """Classify Sharpe trend across windows."""
    windows = ["full", "3y", "2y", "1y", "6m"]
    values = []
    for w in windows:
        m = rolling_metrics.get(w)
        if m and m["trades"] >= 10:
            values.append(m["sharpe"])

    if len(values) < 3:
        return "INSUFFICIENT"

    # Compare first half avg to second half avg
    mid = len(values) // 2
    first_half = np.mean(values[:mid])
    second_half = np.mean(values[mid:])

    pct_change = (second_half - first_half) / abs(first_half) if first_half != 0 else 0
    if pct_change > 0.10:
        return "IMPROVING"
    elif pct_change < -0.10:
        return "DECLINING"
    else:
        return "STABLE"


# ── Analysis Runner ──────────────────────────────────────────────────────────

def run_half_life_analysis() -> dict:
    """Run full half-life analysis for all strategies.

    Returns
    -------
    dict with:
        "report_date": ISO date string
        "strategies": list of per-strategy results
        "summary": status counts and portfolio estimate
    """
    report_date = datetime.now().strftime("%Y-%m-%d")
    results = []

    for strat in EVAL_STRATEGIES:
        strategy_id, module_name, asset, mode = strat[0], strat[1], strat[2], strat[3]
        print(f"  Analyzing {strategy_id}...")

        try:
            trades = get_strategy_trades(strategy_id, module_name, asset, mode)
            rolling = compute_rolling_metrics(trades)
            decay = compute_decay_score(rolling)
            status = get_status(decay)
            half_life = estimate_half_life(rolling)
            trend = _sharpe_trend(rolling)

            results.append({
                "strategy_id": strategy_id,
                "rolling_metrics": rolling,
                "decay_score": decay,
                "status": status,
                "half_life": half_life,
                "sharpe_trend": trend,
            })
        except Exception as e:
            print(f"  WARNING: Failed {strategy_id}: {e}")
            results.append({
                "strategy_id": strategy_id,
                "rolling_metrics": None,
                "decay_score": None,
                "status": "ERROR",
                "half_life": "N/A",
                "sharpe_trend": "ERROR",
                "error": str(e),
            })

    # Summary
    status_counts = {}
    valid_decays = []
    for r in results:
        s = r["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
        if r["decay_score"] is not None:
            valid_decays.append(r["decay_score"])

    avg_decay = float(np.mean(valid_decays)) if valid_decays else None

    # Portfolio half-life estimate from average decay
    if avg_decay is not None and avg_decay > 0:
        # Rough estimate: invert decay to get years
        portfolio_years = max(1, int(round(1.0 / avg_decay))) if avg_decay > 0.05 else 10
        portfolio_half_life = f"~{portfolio_years} years"
    else:
        portfolio_half_life = ">10 years"

    return {
        "report_date": report_date,
        "strategies": results,
        "summary": {
            "status_counts": status_counts,
            "avg_decay_score": round(avg_decay, 4) if avg_decay is not None else None,
            "portfolio_half_life": portfolio_half_life,
        },
    }


# ── Report Printing ──────────────────────────────────────────────────────────

def print_report(results: dict) -> None:
    """Print formatted half-life report to stdout."""
    print()
    print("STRATEGY HALF-LIFE MONITOR")
    print("=" * 60)
    print(f"Report Date: {results['report_date']}")
    print()

    # ── Health Table ──
    print("STRATEGY HEALTH TABLE")
    print("-" * 70)
    header = f"{'Strategy':<30} {'Decay':>6}   {'Status':<18} {'Half-Life':<14}"
    print(header)
    print("-" * 70)

    # Sort by decay score (worst first)
    sorted_strats = sorted(
        results["strategies"],
        key=lambda x: x["decay_score"] if x["decay_score"] is not None else -1,
        reverse=True,
    )

    for r in sorted_strats:
        sid = r["strategy_id"]
        if r["decay_score"] is not None:
            decay_str = f"{r['decay_score']:.2f}"
        else:
            decay_str = "ERR"
        status = r["status"]
        half_life = r["half_life"]
        print(f"  {sid:<28} {decay_str:>6}   {status:<18} {half_life:<14}")

    print()

    # ── Rolling Sharpe Trends ──
    print("ROLLING SHARPE TRENDS")
    print("-" * 85)
    header2 = (f"{'Strategy':<30} {'Full':>6} {'3yr':>6} {'2yr':>6} "
               f"{'1yr':>6} {'6mo':>6}   {'Trend':<12}")
    print(header2)
    print("-" * 85)

    for r in sorted_strats:
        sid = r["strategy_id"]
        rm = r.get("rolling_metrics")
        if rm is None:
            print(f"  {sid:<28}   -- error --")
            continue

        vals = []
        for w in ["full", "3y", "2y", "1y", "6m"]:
            m = rm.get(w)
            if m and m["trades"] >= 10:
                vals.append(f"{m['sharpe']:>6.2f}")
            else:
                vals.append(f"{'--':>6}")

        trend = r.get("sharpe_trend", "N/A")
        print(f"  {sid:<28} {vals[0]} {vals[1]} {vals[2]} {vals[3]} {vals[4]}   {trend:<12}")

    print()

    # ── Summary ──
    summary = results["summary"]
    print("SUMMARY")
    print("-" * 60)
    for status_name in ["HEALTHY", "MONITOR", "DECAYING", "ARCHIVE_CANDIDATE", "ERROR"]:
        count = summary["status_counts"].get(status_name, 0)
        if count > 0:
            print(f"  {status_name}: {count} strategies")

    if summary["avg_decay_score"] is not None:
        print(f"\n  Average decay score: {summary['avg_decay_score']:.4f}")
    print(f"  Estimated portfolio edge half-life: {summary['portfolio_half_life']}")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FQL Strategy Half-Life Monitor"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    parser.add_argument("--save", action="store_true",
                        help="Save report to research/reports/")
    args = parser.parse_args()

    print("\nRunning half-life analysis...")
    results = run_half_life_analysis()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = REPORTS_DIR / f"half_life_{timestamp}.json"
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        # Also write pretty text version
        import io
        buf = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = buf
        print_report(results)
        sys.stdout = old_stdout
        txt_path = REPORTS_DIR / f"half_life_{timestamp}.txt"
        with open(txt_path, "w") as f:
            f.write(buf.getvalue())
        print(f"Saved: {out_path}")
        print(f"Saved: {txt_path}")


if __name__ == "__main__":
    main()
