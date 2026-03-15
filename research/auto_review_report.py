#!/usr/bin/env python3
"""Auto Review Report — consolidated daily/weekly diagnostic overview.

READ-ONLY tool. Does NOT modify any execution pipeline files.

Combines outputs from multiple diagnostic tools into a single concise
human-readable report:
  - Forward health (equity, drawdown, kill switch)
  - Strategy status (edge decay, contribution, alerts)
  - Probation tracker
  - Portfolio health (correlation, diversification, eigenvalue)
  - Risk alerts (drift, decay, regime shifts)
  - Opportunities (portfolio gaps, promotion candidates)

Uses the same data sources and computations as:
  - research/strategy_contribution_analyzer.py
  - research/portfolio_correlation_matrix.py
  - research/trade_duration_analysis.py
  - research/edge_decay_monitor.py
  - scripts/forward_scorecard.py
  - scripts/forward_health_report.py

Usage:
    python3 research/auto_review_report.py              # full report (weekly)
    python3 research/auto_review_report.py --daily      # forward-focused daily report
    python3 research/auto_review_report.py --weekly     # full diagnostic report
    python3 research/auto_review_report.py --save       # write to reports/
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
from engine.regime_engine import RegimeEngine
from engine.strategy_controller import StrategyController, PORTFOLIO_CONFIG

# ── Constants ─────────────────────────────────────────────────────────────────

PROCESSED_DIR = ROOT / "data" / "processed"
TRADE_LOG_PATH = ROOT / "logs" / "trade_log.csv"
DAILY_REPORT_PATH = ROOT / "logs" / "daily_report.csv"
SIGNAL_LOG_PATH = ROOT / "logs" / "signal_log.csv"
KILL_SWITCH_PATH = ROOT / "logs" / "kill_switch_events.csv"
ACCOUNT_STATE_PATH = ROOT / "state" / "account_state.json"

TODAY = datetime.now().strftime("%Y-%m-%d")
EDGE_DECAY_WINDOW = 60

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

# Probation strategies and their promotion thresholds
PROBATION_TRACKER = {
    "Donchian-MNQ-Long-GRINDING": {"min_trades": 150, "note": "Probation (sample-size driven)"},
    "MomIgn-M2K-Short": {"min_trades": 50, "note": "Probation — tail engine, 6.0/10 extended (was 9.0/10 on 2yr), 96% param stability, M2K-specific edge"},
    "CloseVWAP-M2K-Short": {"min_trades": 60, "note": "Probation — close stabilizer, 6.0/10 extended (was 8.0/10 on 2yr), 100% param stability, M2K-specific edge"},
    "TTMSqueeze-M2K-Short": {"min_trades": 100, "note": "Probation — vol expansion tail engine, 5.5/10 extended, 86% param stability, M2K-specific"},
    # CloseVWAP-MNQ-Long REJECTED — 3.5/10 on extended data (PF=0.85, 20% param stability, edge illusory)
    # TTMSqueeze-MNQ-Short REJECTED — 2.0/10 on extended data
    # TTMSqueeze-MGC-Long REJECTED — 3.5/10 on extended data
}


# ── Data Loading ──────────────────────────────────────────────────────────────

def load_csv(path: Path, parse_dates=None) -> pd.DataFrame | None:
    """Load a CSV, returning None if missing or empty."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=parse_dates or [])
        return df if len(df) > 0 else None
    except Exception:
        return None


def load_json(path: Path) -> dict:
    """Load a JSON file, returning {} if missing."""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


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
    csv_path = PROCESSED_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


# ── Backtest Pipeline ─────────────────────────────────────────────────────────

def generate_signals_for_strategy(strat_cfg: dict, df: pd.DataFrame):
    """Generate signals, handling exit_variant and asset kwarg."""
    asset = strat_cfg["asset"]
    tick_size = ASSET_CONFIG[asset]["tick_size"]

    if strat_cfg.get("exit_variant") == "profit_ladder":
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        data = donchian_entries(df)
        return apply_profit_ladder(data)

    mod = load_strategy_module(strat_cfg["name"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = tick_size

    sig = inspect.signature(mod.generate_signals)
    kwargs = {}
    if "asset" in sig.parameters:
        kwargs["asset"] = asset
    return mod.generate_signals(df, **kwargs)


def run_portfolio_backtests() -> tuple[dict, dict]:
    """Run all portfolio strategy backtests.

    Returns (baseline_trades, regime_daily_cache) where
    baseline_trades = {strat_key: trades_df}.
    """
    strat_configs = PORTFOLIO_CONFIG["strategies"]
    regime_engine = RegimeEngine()

    data_cache = {}
    regime_daily_cache = {}
    baseline_trades = {}

    for strat_key, strat in strat_configs.items():
        asset = strat["asset"]
        config = ASSET_CONFIG[asset]

        if asset not in data_cache:
            data_cache[asset] = load_data(asset)
            regime_daily_cache[asset] = regime_engine.get_daily_regimes(
                data_cache[asset]
            )

        df = data_cache[asset]

        try:
            signals = generate_signals_for_strategy(strat, df.copy())
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
                trades = trades.copy()
                trades["entry_date"] = pd.to_datetime(
                    trades["entry_time"]
                ).dt.date
                trades = trades.merge(
                    rd[["_date_date", "trend_persistence"]],
                    left_on="entry_date", right_on="_date_date", how="left",
                )
                trades = trades[
                    trades["trend_persistence"] == "GRINDING"
                ].drop(
                    columns=["entry_date", "_date_date", "trend_persistence"],
                    errors="ignore",
                ).reset_index(drop=True)

            baseline_trades[strat_key] = trades
        except Exception as e:
            print(f"    WARNING: {strat_key} backtest failed: {e}")
            baseline_trades[strat_key] = pd.DataFrame()

    return baseline_trades, regime_daily_cache


def get_controlled_trades(
    baseline_trades: dict, regime_daily_cache: dict
) -> dict:
    """Apply strategy controller to baseline trades."""
    controller = StrategyController(PORTFOLIO_CONFIG)
    result = controller.simulate(baseline_trades, regime_daily_cache)
    return result["filtered_trades"]


# ── Contribution Metrics ──────────────────────────────────────────────────────

def compute_strategy_metrics(trades_dict: dict) -> pd.DataFrame:
    """Compute per-strategy contribution metrics from {key: trades_df}.

    Returns a DataFrame with one row per strategy.
    """
    rows = []
    total_pnl = sum(
        t["pnl"].sum() for t in trades_dict.values() if not t.empty
    )
    total_trades = sum(len(t) for t in trades_dict.values() if not t.empty)

    for strat_key, trades in trades_dict.items():
        if trades.empty:
            rows.append({
                "strategy": strat_key, "trades": 0, "win_rate": 0,
                "avg_pnl": 0, "net_pnl": 0, "pnl_share": 0,
                "profit_factor": 0, "sharpe": 0, "max_dd": 0,
            })
            continue

        pnl = trades["pnl"]
        n = len(pnl)
        wins = pnl[pnl > 0]
        losses = pnl[pnl <= 0]
        net = pnl.sum()
        pf = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else 10.0

        # Daily Sharpe
        if "exit_time" in trades.columns:
            t = trades.copy()
            t["_date"] = pd.to_datetime(t["exit_time"]).dt.date
            daily_pnl = t.groupby("_date")["pnl"].sum()
        else:
            daily_pnl = pnl
        sharpe = (
            float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(252))
            if len(daily_pnl) > 1 and daily_pnl.std() > 0
            else 0.0
        )

        # Max drawdown
        cum = pnl.cumsum()
        dd = (cum.cummax() - cum).max()

        rows.append({
            "strategy": strat_key,
            "trades": n,
            "win_rate": len(wins) / n if n > 0 else 0,
            "avg_pnl": round(pnl.mean(), 2),
            "net_pnl": round(net, 2),
            "pnl_share": net / total_pnl if total_pnl != 0 else 0,
            "profit_factor": round(pf, 2),
            "sharpe": round(sharpe, 2),
            "max_dd": round(dd, 2),
        })

    return pd.DataFrame(rows)


# ── Edge Decay ────────────────────────────────────────────────────────────────

def classify_edge_status(trades: pd.DataFrame, window: int = EDGE_DECAY_WINDOW) -> dict:
    """Classify edge stability for a single strategy.

    Returns dict with status, slope, last_window_pf, overall_pf.
    """
    if trades.empty or len(trades) < window:
        return {"status": "LOW_SAMPLE", "slope": 0, "last_pf": 0, "overall_pf": 0}

    pnl = trades["pnl"].reset_index(drop=True)
    vals = pnl.values
    n = len(vals)

    # Overall PF
    gp = vals[vals > 0].sum()
    gl = abs(vals[vals <= 0].sum())
    overall_pf = gp / gl if gl > 0.001 else 10.0

    # Rolling PF
    rolling_pf = []
    for i in range(window - 1, n):
        chunk = vals[i - window + 1: i + 1]
        gp_w = chunk[chunk > 0].sum()
        gl_w = abs(chunk[chunk <= 0].sum())
        rolling_pf.append(gp_w / gl_w if gl_w > 0.001 else (10.0 if gp_w > 0 else 0.0))

    rolling_pf = np.array(rolling_pf)
    if len(rolling_pf) < 3:
        return {"status": "LOW_SAMPLE", "slope": 0,
                "last_pf": 0, "overall_pf": round(overall_pf, 3)}

    last_pf = rolling_pf[-1]
    slope = float(np.polyfit(np.arange(len(rolling_pf)), rolling_pf, 1)[0])

    if last_pf < 1.0:
        status = "DECAYED"
    elif slope < 0 and last_pf < overall_pf * 0.8:
        status = "WEAKENING"
    elif slope > 0:
        status = "STRENGTHENING"
    else:
        status = "STABLE"

    return {
        "status": status,
        "slope": round(slope, 6),
        "last_pf": round(last_pf, 3),
        "overall_pf": round(overall_pf, 3),
    }


def detect_regime_shift(trades: pd.DataFrame) -> dict:
    """Detect first-half vs second-half PF shift."""
    if trades.empty or len(trades) < 20:
        return {"shift": False, "pf_change_pct": 0}

    pnl = trades["pnl"].values
    mid = len(pnl) // 2

    def half_pf(chunk):
        gp = chunk[chunk > 0].sum()
        gl = abs(chunk[chunk <= 0].sum())
        return gp / gl if gl > 0.001 else (10.0 if gp > 0 else 0.0)

    pf1 = half_pf(pnl[:mid])
    pf2 = half_pf(pnl[mid:])
    change = ((pf2 - pf1) / pf1 * 100) if pf1 > 0.001 else 0
    return {"shift": abs(change) > 30, "pf_change_pct": round(change, 1)}


# ── Portfolio Correlation ─────────────────────────────────────────────────────

def compute_correlation_metrics(trades_dict: dict) -> dict:
    """Compute portfolio-level correlation metrics.

    Returns dict with diversification_score, eigenvalue_concentration,
    max_corr_pair, and correlation matrix.
    """
    daily_pnls = {}
    for key, trades in trades_dict.items():
        if trades.empty:
            continue
        t = trades.copy()
        t["_date"] = pd.to_datetime(t["exit_time"]).dt.date
        daily = t.groupby("_date")["pnl"].sum()
        daily.index = pd.to_datetime(daily.index)
        daily_pnls[key] = daily

    if len(daily_pnls) < 2:
        return {
            "diversification_score": 0,
            "eigenvalue_concentration": 0,
            "max_corr_pair": ("N/A", "N/A", 0),
            "corr_matrix": pd.DataFrame(),
        }

    df = pd.DataFrame(daily_pnls).fillna(0)
    corr = df.corr()

    # Diversification score: avg |r| off-diagonal
    n = len(corr)
    mask = ~np.eye(n, dtype=bool)
    div_score = float(np.abs(corr.values[mask]).mean())

    # Eigenvalue concentration
    eigvals = np.abs(np.linalg.eigvalsh(corr.values))
    eig_total = eigvals.sum()
    eig_concentration = float(eigvals.max() / eig_total) if eig_total > 0 else 0

    # Max correlation pair
    max_r = 0
    max_pair = ("N/A", "N/A")
    keys = list(corr.columns)
    for i in range(n):
        for j in range(i + 1, n):
            r = abs(corr.iloc[i, j])
            if r > max_r:
                max_r = r
                max_pair = (keys[i], keys[j])

    return {
        "diversification_score": round(div_score, 4),
        "eigenvalue_concentration": round(eig_concentration, 4),
        "max_corr_pair": (max_pair[0], max_pair[1], round(max_r, 3)),
        "corr_matrix": corr,
    }


# ── Forward Data ──────────────────────────────────────────────────────────────

def load_forward_state() -> dict:
    """Load all forward-test data sources.

    Returns dict with keys: account, daily_row, trades_today,
    kill_switch, health_status.
    """
    account = load_json(ACCOUNT_STATE_PATH)
    daily_df = load_csv(DAILY_REPORT_PATH, parse_dates=["date"])
    trade_df = load_csv(TRADE_LOG_PATH, parse_dates=["date"])
    ks_df = load_csv(KILL_SWITCH_PATH, parse_dates=["date"])

    has_forward = any([
        account, daily_df is not None, trade_df is not None,
    ])

    if not has_forward:
        return {"available": False}

    # Latest daily row
    daily_row = {}
    if daily_df is not None and len(daily_df) > 0:
        daily_row = daily_df.iloc[-1].to_dict()

    # Today's trades
    trades_today = []
    trades_all = trade_df
    if trade_df is not None and len(trade_df) > 0:
        today_mask = pd.to_datetime(trade_df["date"]).dt.strftime("%Y-%m-%d") == TODAY
        trades_today = trade_df[today_mask]

    # Equity and drawdown
    equity = daily_row.get("equity") or account.get("equity", "N/A")
    trailing_dd = daily_row.get("trailing_dd") or account.get("trailing_dd", 0)
    cum_pnl = daily_row.get("cumulative_pnl") or account.get("cumulative_pnl", 0)

    # Daily PnL
    daily_pnl = daily_row.get("daily_pnl", 0)

    # Kill switch
    ks_triggered = str(daily_row.get("kill_switch", "")).lower() in (
        "true", "1", "yes"
    )
    ks_events_today = 0
    if ks_df is not None and len(ks_df) > 0:
        today_ks = ks_df[
            pd.to_datetime(ks_df["date"]).dt.strftime("%Y-%m-%d") == TODAY
        ]
        ks_events_today = len(today_ks)

    # Health status
    try:
        dd_val = float(trailing_dd)
    except (TypeError, ValueError):
        dd_val = 0

    if ks_triggered or dd_val > 2000:
        health = "CRITICAL"
    elif dd_val > 1000 or (trades_today is not None and len(trades_today) == 0):
        health = "WARNING"
    else:
        health = "HEALTHY"

    # N trading days
    n_days = 0
    if daily_df is not None:
        n_days = len(daily_df)

    # All-time forward metrics
    fwd_total_trades = len(trade_df) if trade_df is not None else 0
    fwd_total_pnl = 0
    fwd_win_rate = 0
    if trade_df is not None and len(trade_df) > 0:
        fwd_total_pnl = trade_df["pnl"].sum()
        fwd_win_rate = (trade_df["pnl"] > 0).mean()

    return {
        "available": True,
        "equity": equity,
        "trailing_dd": trailing_dd,
        "cumulative_pnl": cum_pnl,
        "daily_pnl": daily_pnl,
        "trades_today": len(trades_today) if trades_today is not None else 0,
        "kill_switch": "TRIGGERED" if ks_triggered else "OK",
        "ks_events_today": ks_events_today,
        "health": health,
        "n_days": n_days,
        "total_trades": fwd_total_trades,
        "total_pnl": fwd_total_pnl,
        "win_rate": fwd_win_rate,
        "trades_df": trade_df,
    }


# ── Report Generation ────────────────────────────────────────────────────────

def fmt_pnl(val) -> str:
    """Format a PnL value with sign and dollar."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "N/A"
    if v >= 0:
        return f"+${v:,.2f}"
    return f"-${abs(v):,.2f}"


def fmt_pct(val, decimals=1) -> str:
    return f"{val:.{decimals}f}%"


def section_daily_overview(forward: dict) -> list[str]:
    """Generate the DAILY OVERVIEW section."""
    lines = []
    lines.append(f"DAILY OVERVIEW ({TODAY})")
    lines.append("\u2500" * 50)

    if not forward["available"]:
        lines.append("Health: N/A (no forward data)")
        lines.append("Forward testing has not started. Showing backtest-only report.")
        return lines

    lines.append(f"Health:         {forward['health']}")
    lines.append(f"Equity:         {fmt_pnl(forward['equity']).lstrip('+')}")
    lines.append(f"Daily PnL:      {fmt_pnl(forward['daily_pnl'])}")
    lines.append(f"Trailing DD:    {fmt_pnl(forward['trailing_dd']).lstrip('+')}")
    lines.append(f"Trades today:   {forward['trades_today']}")
    lines.append(f"Kill switch:    {forward['kill_switch']}")

    if forward["n_days"] > 0:
        lines.append(f"Days running:   {forward['n_days']}")
        lines.append(f"Total trades:   {forward['total_trades']}")
        if forward["total_trades"] > 0:
            lines.append(f"Cum PnL:        {fmt_pnl(forward['total_pnl'])}")
            lines.append(f"Win rate:       {fmt_pct(forward['win_rate'] * 100)}")

    return lines


def section_strategy_status(
    controlled_trades: dict, edge_results: dict, metrics_df: pd.DataFrame
) -> list[str]:
    """Generate the STRATEGY STATUS section."""
    lines = []
    lines.append("")
    lines.append("STRATEGY STATUS")
    lines.append("\u2500" * 50)

    header = f"{'Strategy':<34} {'Edge':<14} {'PF':>6} {'Contrib':>8} {'Alert'}"
    lines.append(header)
    lines.append(f"{'-'*34} {'-'*14} {'-'*6} {'-'*8} {'-'*20}")

    total_pnl = metrics_df["net_pnl"].sum()

    for _, row in metrics_df.iterrows():
        strat = row["strategy"]
        edge = edge_results.get(strat, {})
        edge_status = edge.get("status", "N/A")

        pf_str = f"{row['profit_factor']:.2f}" if np.isfinite(row["profit_factor"]) else "inf"
        contrib = f"{row['pnl_share'] * 100:.1f}%" if total_pnl != 0 else "N/A"

        # Alert logic
        alerts = []
        if edge_status == "DECAYED":
            alerts.append("PF < 1.0")
        elif edge_status == "WEAKENING":
            alerts.append("PF declining")

        shift = edge.get("regime_shift", {})
        if shift.get("shift", False):
            alerts.append(f"Shift {shift['pf_change_pct']:+.0f}%")

        if row["trades"] == 0:
            alerts.append("No trades")

        alert_str = ", ".join(alerts) if alerts else "\u2014"

        lines.append(
            f"{strat:<34} {edge_status:<14} {pf_str:>6} {contrib:>8} {alert_str}"
        )

    return lines


def section_probation_tracker(controlled_trades: dict) -> list[str]:
    """Generate the PROBATION TRACKER section."""
    lines = []
    lines.append("")
    lines.append("PROBATION TRACKER")
    lines.append("\u2500" * 50)

    if not PROBATION_TRACKER:
        lines.append("No strategies on probation.")
        return lines

    for strat_key, info in PROBATION_TRACKER.items():
        trades = controlled_trades.get(strat_key, pd.DataFrame())
        n = len(trades) if not trades.empty else 0
        needed = info["min_trades"]
        pct = min(100, n / needed * 100) if needed > 0 else 0

        # Simple score: PF-based
        score = "N/A"
        if not trades.empty and n >= 10:
            pnl = trades["pnl"]
            gp = pnl[pnl > 0].sum()
            gl = abs(pnl[pnl <= 0].sum())
            pf = gp / gl if gl > 0.001 else 10.0
            # Score 0-10: PF mapped roughly
            score_val = min(10, max(0, (pf - 0.8) * 5))
            score = f"{score_val:.1f}/10"

        bar = "#" * int(pct // 5) + "." * (20 - int(pct // 5))
        lines.append(
            f"{strat_key}: {n} trades (need {needed}) [{bar}] {pct:.0f}%"
        )
        lines.append(f"  Score: {score}  |  {info['note']}")

    return lines


def section_portfolio_health(corr_metrics: dict) -> list[str]:
    """Generate the PORTFOLIO HEALTH section."""
    lines = []
    lines.append("")
    lines.append("PORTFOLIO HEALTH")
    lines.append("\u2500" * 50)

    div = corr_metrics["diversification_score"]
    eig = corr_metrics["eigenvalue_concentration"]
    max_pair = corr_metrics["max_corr_pair"]

    # Diversification quality
    if div < 0.05:
        div_quality = "EXCELLENT"
    elif div < 0.10:
        div_quality = "VERY GOOD"
    elif div < 0.20:
        div_quality = "GOOD"
    elif div < 0.30:
        div_quality = "MODERATE"
    else:
        div_quality = "POOR"

    lines.append(f"Diversification score:  {div:.4f}  (target: <0.15)  [{div_quality}]")
    lines.append(f"Max correlation pair:   {max_pair[0]} vs {max_pair[1]} (r={max_pair[2]:.3f})")

    n_strats = len(corr_metrics["corr_matrix"]) if not corr_metrics["corr_matrix"].empty else 0
    ideal_eig = 1.0 / n_strats if n_strats > 0 else 0
    eig_ratio = eig / ideal_eig if ideal_eig > 0 else 0
    lines.append(
        f"Eigenvalue concentration: {eig:.4f}  "
        f"(ideal: {ideal_eig:.4f}, ratio: {eig_ratio:.1f}x)"
    )

    return lines


def section_risk_alerts(
    edge_results: dict, corr_metrics: dict, forward: dict
) -> list[str]:
    """Generate the RISK ALERTS section."""
    lines = []
    lines.append("")
    lines.append("RISK ALERTS")
    lines.append("\u2500" * 50)

    alerts = []

    # Edge decay alerts
    for strat, edge in edge_results.items():
        if edge.get("status") == "DECAYED":
            alerts.append(f"[CRITICAL] {strat}: edge DECAYED (rolling PF < 1.0)")
        elif edge.get("status") == "WEAKENING":
            alerts.append(
                f"[WARNING]  {strat}: edge WEAKENING "
                f"(slope={edge.get('slope', 0):+.6f}, last PF={edge.get('last_pf', 0):.2f})"
            )
        shift = edge.get("regime_shift", {})
        if shift.get("shift", False):
            alerts.append(
                f"[WARNING]  {strat}: regime shift detected "
                f"(PF change {shift['pf_change_pct']:+.1f}%)"
            )

    # Correlation alerts
    div = corr_metrics["diversification_score"]
    if div > 0.20:
        alerts.append(
            f"[WARNING]  Portfolio diversification degraded: "
            f"avg |r| = {div:.3f} (target < 0.15)"
        )

    max_pair = corr_metrics["max_corr_pair"]
    if max_pair[2] > 0.30:
        alerts.append(
            f"[WARNING]  High correlation: {max_pair[0]} vs {max_pair[1]} "
            f"(r={max_pair[2]:.3f})"
        )

    # Forward alerts
    if forward["available"]:
        try:
            dd = float(forward["trailing_dd"])
            if dd > 2000:
                alerts.append(f"[CRITICAL] Trailing drawdown ${dd:,.2f} exceeds $2,000 limit")
            elif dd > 1000:
                alerts.append(f"[WARNING]  Trailing drawdown ${dd:,.2f} approaching limit")
        except (TypeError, ValueError):
            pass

        if forward["kill_switch"] == "TRIGGERED":
            alerts.append("[CRITICAL] Kill switch TRIGGERED")

    if not alerts:
        lines.append("No risk alerts. All systems nominal.")
    else:
        for a in alerts:
            lines.append(f"- {a}")

    return lines


def section_opportunities(
    metrics_df: pd.DataFrame, edge_results: dict
) -> list[str]:
    """Generate the OPPORTUNITIES section."""
    lines = []
    lines.append("")
    lines.append("OPPORTUNITIES")
    lines.append("\u2500" * 50)

    opportunities = []

    # Promotion candidates from probation
    for strat_key, info in PROBATION_TRACKER.items():
        edge = edge_results.get(strat_key, {})
        if edge.get("status") in ("STABLE", "STRENGTHENING"):
            row = metrics_df[metrics_df["strategy"] == strat_key]
            if not row.empty and row.iloc[0]["trades"] >= info["min_trades"]:
                opportunities.append(
                    f"[PROMOTE] {strat_key}: meets trade threshold, "
                    f"edge {edge['status']}"
                )

    # Strengthening strategies
    for strat, edge in edge_results.items():
        if edge.get("status") == "STRENGTHENING" and strat not in PROBATION_TRACKER:
            opportunities.append(
                f"[STRONG]  {strat}: edge strengthening "
                f"(slope={edge.get('slope', 0):+.6f})"
            )

    # Portfolio gaps (from memory: structural gaps in regime coverage)
    gaps = [
        "Regime gap: HIGH_VOL_TRENDING_LOW_RV still structural (3 entry models failed)",
        "Missing archetypes: trend_following (60+ bar hold), overnight, event_driven",
    ]
    for g in gaps:
        opportunities.append(f"[GAP]     {g}")

    if not opportunities:
        lines.append("No actionable opportunities identified.")
    else:
        for o in opportunities:
            lines.append(f"- {o}")

    return lines


def section_backtest_summary(metrics_df: pd.DataFrame) -> list[str]:
    """Generate a concise backtest portfolio summary."""
    lines = []
    lines.append("")
    lines.append("BACKTEST PORTFOLIO SUMMARY")
    lines.append("\u2500" * 50)

    total_trades = metrics_df["trades"].sum()
    total_pnl = metrics_df["net_pnl"].sum()

    # Portfolio-level sharpe from combined daily PnL would require
    # recomputation; use a simpler summary here
    avg_pf = metrics_df.loc[
        metrics_df["profit_factor"] > 0, "profit_factor"
    ].mean()

    lines.append(f"Total trades:   {total_trades}")
    lines.append(f"Total PnL:      {fmt_pnl(total_pnl)}")
    lines.append(f"Avg strat PF:   {avg_pf:.2f}")
    lines.append("")

    # Per-strategy one-liner
    header = f"{'Strategy':<34} {'Trades':>6} {'PnL':>10} {'WR':>6} {'PF':>6} {'Sharpe':>7}"
    lines.append(header)
    lines.append(f"{'-'*34} {'-'*6} {'-'*10} {'-'*6} {'-'*6} {'-'*7}")

    for _, row in metrics_df.sort_values("net_pnl", ascending=False).iterrows():
        pf_str = (
            f"{row['profit_factor']:.2f}"
            if np.isfinite(row["profit_factor"])
            else "inf"
        )
        lines.append(
            f"{row['strategy']:<34} {row['trades']:>6} "
            f"${row['net_pnl']:>9,.0f} "
            f"{row['win_rate']*100:>5.1f}% "
            f"{pf_str:>6} "
            f"{row['sharpe']:>7.2f}"
        )

    return lines


# ── Main Report Builder ──────────────────────────────────────────────────────

def generate_report(mode: str = "weekly") -> str:
    """Generate the full auto-review report.

    Args:
        mode: "daily" for forward-focused, "weekly" for full diagnostic.

    Returns:
        Report as a string.
    """
    output_lines = []

    def add(lines):
        if isinstance(lines, str):
            output_lines.append(lines)
        else:
            output_lines.extend(lines)

    add("=" * 60)
    add(f"  AUTO REVIEW REPORT  ({mode.upper()})")
    add(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    add("=" * 60)
    add("")

    # ── Forward data (always loaded) ──
    print("  Loading forward data...")
    forward = load_forward_state()
    add(section_daily_overview(forward))

    if mode == "daily" and not forward["available"]:
        add("")
        add("No forward data available. Use --weekly for backtest analysis.")
        add("")
        add("=" * 60)
        return "\n".join(output_lines)

    # ── Backtest data (weekly mode, or if no forward data) ──
    run_backtest_analysis = (mode == "weekly") or not forward["available"]

    controlled_trades = {}
    metrics_df = pd.DataFrame()
    edge_results = {}
    corr_metrics = {
        "diversification_score": 0,
        "eigenvalue_concentration": 0,
        "max_corr_pair": ("N/A", "N/A", 0),
        "corr_matrix": pd.DataFrame(),
    }

    if run_backtest_analysis:
        print("  Running portfolio backtests...")
        baseline_trades, regime_daily_cache = run_portfolio_backtests()

        print("  Applying strategy controller...")
        controlled_trades = get_controlled_trades(
            baseline_trades, regime_daily_cache
        )

        print("  Computing strategy metrics...")
        metrics_df = compute_strategy_metrics(controlled_trades)

        print("  Classifying edge stability...")
        for strat_key, trades in controlled_trades.items():
            edge = classify_edge_status(trades)
            shift = detect_regime_shift(trades)
            edge["regime_shift"] = shift
            edge_results[strat_key] = edge

        print("  Computing portfolio correlations...")
        corr_metrics = compute_correlation_metrics(controlled_trades)

    # ── Strategy Status ──
    if not metrics_df.empty:
        add(section_strategy_status(controlled_trades, edge_results, metrics_df))

    # ── Probation Tracker ──
    if not metrics_df.empty:
        add(section_probation_tracker(controlled_trades))

    # ── Portfolio Health ──
    if corr_metrics["corr_matrix"] is not None and not corr_metrics["corr_matrix"].empty:
        add(section_portfolio_health(corr_metrics))

    # ── Risk Alerts ──
    add(section_risk_alerts(edge_results, corr_metrics, forward))

    # ── Opportunities (weekly only) ──
    if mode == "weekly" and not metrics_df.empty:
        add(section_opportunities(metrics_df, edge_results))

    # ── Backtest Summary (weekly only) ──
    if mode == "weekly" and not metrics_df.empty:
        add(section_backtest_summary(metrics_df))

    add("")
    add("=" * 60)
    add(f"  END OF {mode.upper()} REPORT")
    add("=" * 60)

    return "\n".join(output_lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Auto Review Report — consolidated diagnostic overview"
    )
    parser.add_argument(
        "--daily", action="store_true",
        help="Forward-focused daily report (health + trades + alerts)",
    )
    parser.add_argument(
        "--weekly", action="store_true",
        help="Full diagnostic report (all sections including backtest analysis)",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="Write report to reports/ directory",
    )
    args = parser.parse_args()

    # Determine mode
    if args.daily:
        mode = "daily"
    elif args.weekly:
        mode = "weekly"
    else:
        mode = "weekly"  # default to full report

    report = generate_report(mode=mode)
    print(report)

    if args.save:
        reports_dir = ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        filename = f"{mode}_{TODAY}.md"
        save_path = reports_dir / filename
        save_path.write_text(report + "\n")
        print(f"\n  Report saved to {save_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
