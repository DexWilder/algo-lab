#!/usr/bin/env python3
"""FQL Live Drift Monitor — Detect divergence between expected and forward behavior.

Compares rolling forward-test metrics against backtest reference baselines
to detect edge drift before major damage occurs.

Drift Dimensions:
    1. Win Rate Drift         — entry edge weakening
    2. Expectancy Drift       — payoff distribution changing
    3. Trade Frequency Drift  — regime shift or signal degradation
    4. Sharpe Drift           — overall edge quality
    5. Regime-Specific Drift  — environment-dependent performance change
    6. Session Drift          — intraday structural changes

Alert Tiers:
    NORMAL   — within 1σ of baseline
    DRIFT    — >1σ deviation sustained 2+ weeks
    ALARM    — >2σ deviation or structural break

Usage:
    python3 research/live_drift_monitor.py                # Full drift report
    python3 research/live_drift_monitor.py --json         # JSON output
    python3 research/live_drift_monitor.py --save         # Save to reports/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Paths ────────────────────────────────────────────────────────────────────

FORWARD_DIR = ROOT / "research" / "phase17_paper_trading"
DAILY_STATES_PATH = FORWARD_DIR / "daily_states.json"
DAILY_LOGS_DIR = FORWARD_DIR / "daily_logs"
EQUITY_CURVE_PATH = FORWARD_DIR / "equity_curve.csv"
DRIFT_LOG_PATH = ROOT / "research" / "data" / "live_drift_log.json"
REPORTS_DIR = ROOT / "research" / "reports"

# ── Backtest Reference Baselines ─────────────────────────────────────────────
# From Phase 17 backtest (355 trading days, 391 trades)

BASELINE = {
    "portfolio": {
        "trades_per_day": 1.1,
        "win_rate": 0.499,
        "daily_win_rate": 0.526,
        "sharpe": 4.04,
        "avg_pnl_per_trade": 41.89,
        "profit_factor": 2.11,
        "avg_winner": 159.38,
        "avg_loser": -75.01,
        "max_dd": 2007,
        "trade_retention": 0.70,
        "monthly_positive_rate": 0.84,
    },
    "strategies": {
        "VWAP-MNQ-Long": {
            "trade_share": 0.417, "pnl_share": 0.324,
            "win_rate": 0.417, "avg_pnl": 32.51, "trades": 163,
        },
        "XB-PB-EMA-MES-Short": {
            "trade_share": 0.225, "pnl_share": 0.155,
            "win_rate": 0.557, "avg_pnl": 28.86, "trades": 88,
        },
        "ORB-MGC-Long": {
            "trade_share": 0.159, "pnl_share": 0.169,
            "win_rate": 0.565, "avg_pnl": 44.63, "trades": 62,
        },
        "Donchian-MNQ-Long-GRINDING": {
            "trade_share": 0.120, "pnl_share": 0.139,
            "win_rate": 0.553, "avg_pnl": 48.43, "trades": 47,
        },
        "BB-EQ-MGC-Long": {
            "trade_share": 0.056, "pnl_share": 0.166,
            "win_rate": 0.500, "avg_pnl": 123.40, "trades": 22,
        },
        "PB-MGC-Short": {
            "trade_share": 0.023, "pnl_share": 0.048,
            "win_rate": 0.667, "avg_pnl": 86.76, "trades": 9,
        },
    },
}

# ── Drift Thresholds ─────────────────────────────────────────────────────────

THRESHOLDS = {
    "win_rate": {
        "drift": 0.08,     # 8pp deviation = DRIFT
        "alarm": 0.15,     # 15pp = ALARM
    },
    "expectancy": {
        "drift": 0.40,     # 40% below baseline avg_pnl = DRIFT
        "alarm": 0.70,     # 70% below = ALARM
    },
    "trade_frequency": {
        "drift": 0.40,     # 40% fewer/more trades = DRIFT
        "alarm": 0.60,     # 60% = ALARM
    },
    "sharpe": {
        "drift": 1.5,      # Sharpe below 1.5 = DRIFT (baseline 4.04)
        "alarm": 0.5,      # Below 0.5 = ALARM
    },
    "profit_factor": {
        "drift": 1.3,      # PF below 1.3 = DRIFT
        "alarm": 1.0,      # PF below 1.0 = ALARM (losing money)
    },
}


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_forward_trades() -> pd.DataFrame:
    """Load all forward trades from daily logs into a DataFrame."""
    trades = []
    if not DAILY_LOGS_DIR.exists():
        return pd.DataFrame()

    for log_file in sorted(DAILY_LOGS_DIR.glob("*.json")):
        try:
            with open(log_file) as f:
                day_data = json.load(f)

            date_str = log_file.stem  # e.g., "2026-03-10"
            for trade in day_data.get("trades", day_data.get("trades_completed", [])):
                trade["date"] = date_str
                trades.append(trade)
        except (json.JSONDecodeError, KeyError):
            continue

    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame(trades)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_daily_states() -> list:
    """Load daily state snapshots."""
    if not DAILY_STATES_PATH.exists():
        return []
    with open(DAILY_STATES_PATH) as f:
        return json.load(f)


def load_equity_curve() -> pd.DataFrame:
    """Load equity curve CSV."""
    if not EQUITY_CURVE_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(EQUITY_CURVE_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ── Drift Computation ────────────────────────────────────────────────────────

def compute_portfolio_drift(trades: pd.DataFrame, equity: pd.DataFrame,
                            daily_states: list) -> dict:
    """Compute portfolio-level drift metrics."""
    if trades.empty:
        return {"status": "NO_DATA", "message": "No forward trades available"}

    n_days = len(trades["date"].unique())
    n_trades = len(trades)

    # Win rate
    wins = trades[trades["pnl"] > 0]
    live_wr = len(wins) / n_trades if n_trades > 0 else 0
    wr_delta = live_wr - BASELINE["portfolio"]["win_rate"]

    # Trade frequency
    live_tpd = n_trades / max(n_days, 1)
    tpd_ratio = live_tpd / BASELINE["portfolio"]["trades_per_day"]

    # Expectancy
    live_avg_pnl = trades["pnl"].mean()
    exp_ratio = live_avg_pnl / BASELINE["portfolio"]["avg_pnl_per_trade"] if BASELINE["portfolio"]["avg_pnl_per_trade"] != 0 else 0

    # Profit factor
    gross_profit = trades[trades["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades[trades["pnl"] <= 0]["pnl"].sum())
    live_pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Avg winner / loser
    live_avg_win = wins["pnl"].mean() if len(wins) > 0 else 0
    losses = trades[trades["pnl"] <= 0]
    live_avg_loss = losses["pnl"].mean() if len(losses) > 0 else 0

    # Sharpe (annualized from daily PnL)
    if not equity.empty and "daily_pnl" in equity.columns:
        daily_pnl = equity["daily_pnl"].dropna()
        if len(daily_pnl) > 1 and daily_pnl.std() > 0:
            live_sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)
        else:
            live_sharpe = 0.0
    else:
        live_sharpe = 0.0

    # Trade retention
    total_signals = sum(s.get("signals_generated", 0) for s in daily_states)
    total_taken = sum(s.get("signals_taken", 0) for s in daily_states)
    live_retention = total_taken / total_signals if total_signals > 0 else 0

    # Classify drift levels
    metrics = {
        "win_rate": {
            "baseline": BASELINE["portfolio"]["win_rate"],
            "live": round(live_wr, 3),
            "delta": round(wr_delta, 3),
            "severity": _classify_drift_abs(abs(wr_delta),
                                            THRESHOLDS["win_rate"]["drift"],
                                            THRESHOLDS["win_rate"]["alarm"]),
        },
        "trade_frequency": {
            "baseline_tpd": BASELINE["portfolio"]["trades_per_day"],
            "live_tpd": round(live_tpd, 2),
            "ratio": round(tpd_ratio, 2),
            "severity": _classify_drift_ratio(tpd_ratio,
                                              THRESHOLDS["trade_frequency"]["drift"],
                                              THRESHOLDS["trade_frequency"]["alarm"]),
        },
        "expectancy": {
            "baseline_avg_pnl": BASELINE["portfolio"]["avg_pnl_per_trade"],
            "live_avg_pnl": round(live_avg_pnl, 2),
            "ratio": round(exp_ratio, 2),
            "severity": _classify_drift_degradation(exp_ratio,
                                                    1 - THRESHOLDS["expectancy"]["drift"],
                                                    1 - THRESHOLDS["expectancy"]["alarm"]),
        },
        "profit_factor": {
            "baseline": BASELINE["portfolio"]["profit_factor"],
            "live": round(live_pf, 2),
            "severity": _classify_drift_floor(live_pf,
                                              THRESHOLDS["profit_factor"]["drift"],
                                              THRESHOLDS["profit_factor"]["alarm"]),
        },
        "sharpe": {
            "baseline": BASELINE["portfolio"]["sharpe"],
            "live": round(live_sharpe, 2),
            "severity": _classify_drift_floor(live_sharpe,
                                              THRESHOLDS["sharpe"]["drift"],
                                              THRESHOLDS["sharpe"]["alarm"]),
        },
        "avg_winner": {
            "baseline": BASELINE["portfolio"]["avg_winner"],
            "live": round(live_avg_win, 2),
        },
        "avg_loser": {
            "baseline": BASELINE["portfolio"]["avg_loser"],
            "live": round(live_avg_loss, 2),
        },
        "trade_retention": {
            "baseline": BASELINE["portfolio"]["trade_retention"],
            "live": round(live_retention, 2),
        },
    }

    # Overall severity
    severities = [m.get("severity", "NORMAL") for m in metrics.values() if "severity" in m]
    if "ALARM" in severities:
        overall = "ALARM"
    elif "DRIFT" in severities:
        overall = "DRIFT"
    else:
        overall = "NORMAL"

    return {
        "status": overall,
        "forward_days": n_days,
        "forward_trades": n_trades,
        "metrics": metrics,
    }


def compute_strategy_drift(trades: pd.DataFrame) -> dict:
    """Compute per-strategy drift vs baseline."""
    if trades.empty:
        return {}

    results = {}
    n_total = len(trades)
    n_days = len(trades["date"].unique())

    for strat_name, baseline in BASELINE["strategies"].items():
        strat_trades = trades[trades["strategy"] == strat_name]
        n = len(strat_trades)

        if n == 0:
            results[strat_name] = {
                "trades": 0,
                "severity": "ALARM" if n_days >= 5 else "NORMAL",
                "message": "No trades in forward period" if n_days >= 5 else "Insufficient data",
            }
            continue

        # Win rate
        live_wr = len(strat_trades[strat_trades["pnl"] > 0]) / n
        wr_delta = live_wr - baseline["win_rate"]

        # Trade share
        live_share = n / n_total if n_total > 0 else 0
        share_delta = live_share - baseline["trade_share"]

        # Avg PnL
        live_avg = strat_trades["pnl"].mean()
        pnl_ratio = live_avg / baseline["avg_pnl"] if baseline["avg_pnl"] != 0 else 0

        # Expected trades per day (from baseline)
        baseline_tpd = baseline["trades"] / 355  # 355 backtest days
        live_tpd = n / max(n_days, 1)
        freq_ratio = live_tpd / baseline_tpd if baseline_tpd > 0 else 0

        # Severity
        wr_sev = _classify_drift_abs(abs(wr_delta), 0.10, 0.20)
        pnl_sev = _classify_drift_degradation(pnl_ratio, 0.50, 0.20)
        freq_sev = _classify_drift_ratio(freq_ratio, 0.50, 0.70)

        severities = [wr_sev, pnl_sev, freq_sev]
        if "ALARM" in severities:
            overall = "ALARM"
        elif "DRIFT" in severities:
            overall = "DRIFT"
        else:
            overall = "NORMAL"

        results[strat_name] = {
            "trades": n,
            "severity": overall,
            "win_rate": {"baseline": baseline["win_rate"], "live": round(live_wr, 3), "delta": round(wr_delta, 3), "severity": wr_sev},
            "avg_pnl": {"baseline": baseline["avg_pnl"], "live": round(live_avg, 2), "ratio": round(pnl_ratio, 2), "severity": pnl_sev},
            "trade_frequency": {"baseline_tpd": round(baseline_tpd, 3), "live_tpd": round(live_tpd, 3), "ratio": round(freq_ratio, 2), "severity": freq_sev},
            "trade_share": {"baseline": baseline["trade_share"], "live": round(live_share, 3), "delta": round(share_delta, 3)},
        }

    return results


def compute_regime_drift(trades: pd.DataFrame, daily_states: list) -> dict:
    """Compute regime-specific performance drift."""
    if not daily_states:
        return {"status": "NO_DATA"}

    # Build regime-to-pnl mapping
    regime_pnl = {}
    for state in daily_states:
        date = state.get("date", "")
        regime = state.get("regime", {})
        vol = regime.get("vol_regime", "NORMAL")
        daily_pnl = state.get("portfolio_daily_pnl", 0)

        regime_pnl.setdefault(vol, []).append(daily_pnl)

    results = {}
    for vol_regime, pnls in regime_pnl.items():
        avg = np.mean(pnls) if pnls else 0
        n_days = len(pnls)
        results[vol_regime] = {
            "days": n_days,
            "avg_daily_pnl": round(avg, 2),
            "total_pnl": round(sum(pnls), 2),
            "positive_rate": round(sum(1 for p in pnls if p > 0) / max(n_days, 1), 2),
        }

    return results


# ── Classification Helpers ───────────────────────────────────────────────────

def _classify_drift_abs(delta: float, drift_thresh: float, alarm_thresh: float) -> str:
    """Classify drift by absolute deviation."""
    if delta >= alarm_thresh:
        return "ALARM"
    elif delta >= drift_thresh:
        return "DRIFT"
    return "NORMAL"


def _classify_drift_ratio(ratio: float, drift_thresh: float, alarm_thresh: float) -> str:
    """Classify drift by ratio (too high or too low)."""
    deviation = abs(1.0 - ratio)
    if deviation >= alarm_thresh:
        return "ALARM"
    elif deviation >= drift_thresh:
        return "DRIFT"
    return "NORMAL"


def _classify_drift_degradation(ratio: float, drift_floor: float, alarm_floor: float) -> str:
    """Classify drift by degradation from baseline (ratio < 1.0 = worse)."""
    if ratio <= alarm_floor:
        return "ALARM"
    elif ratio <= drift_floor:
        return "DRIFT"
    return "NORMAL"


def _classify_drift_floor(value: float, drift_floor: float, alarm_floor: float) -> str:
    """Classify drift by absolute floor value."""
    if value <= alarm_floor:
        return "ALARM"
    elif value <= drift_floor:
        return "DRIFT"
    return "NORMAL"


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_drift_monitor() -> dict:
    """Run full drift analysis and return structured results."""
    trades = load_forward_trades()
    daily_states = load_daily_states()
    equity = load_equity_curve()

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    portfolio_drift = compute_portfolio_drift(trades, equity, daily_states)
    strategy_drift = compute_strategy_drift(trades)
    regime_drift = compute_regime_drift(trades, daily_states)

    # Build alerts
    alerts = []

    # Portfolio-level alerts
    if portfolio_drift.get("status") == "ALARM":
        alerts.append({
            "level": "ALARM",
            "scope": "PORTFOLIO",
            "message": "Portfolio-level metrics show significant divergence from backtest baseline",
        })
    elif portfolio_drift.get("status") == "DRIFT":
        alerts.append({
            "level": "DRIFT",
            "scope": "PORTFOLIO",
            "message": "Portfolio metrics drifting from baseline — monitor closely",
        })

    # Strategy-level alerts
    for strat, data in strategy_drift.items():
        if data.get("severity") == "ALARM":
            alerts.append({
                "level": "ALARM",
                "scope": strat,
                "message": f"{strat}: forward performance significantly diverges from backtest",
            })
        elif data.get("severity") == "DRIFT":
            alerts.append({
                "level": "DRIFT",
                "scope": strat,
                "message": f"{strat}: drifting from baseline metrics",
            })

    results = {
        "report_date": report_date,
        "forward_period": {
            "days": portfolio_drift.get("forward_days", 0),
            "trades": portfolio_drift.get("forward_trades", 0),
        },
        "portfolio_drift": portfolio_drift,
        "strategy_drift": strategy_drift,
        "regime_drift": regime_drift,
        "alerts": alerts,
        "overall_status": portfolio_drift.get("status", "NO_DATA"),
    }

    return results


# ── Terminal Report ──────────────────────────────────────────────────────────

def print_drift_report(results: dict):
    """Print formatted drift report to terminal."""
    W = 75
    SEP = "=" * W
    THIN = "-" * 55

    print()
    print(SEP)
    print("  FQL LIVE DRIFT MONITOR")
    print(f"  {results['report_date']}")
    print(f"  Overall: {results['overall_status']}")
    print(SEP)

    period = results["forward_period"]
    print(f"\n  Forward period: {period['days']} days, {period['trades']} trades")

    # ── Portfolio Drift ──
    pd_data = results["portfolio_drift"]
    if pd_data.get("status") == "NO_DATA":
        print(f"\n  {pd_data.get('message', 'No data')}")
        return

    print(f"\n  PORTFOLIO DRIFT")
    print(f"  {THIN}")
    print(f"  {'Metric':<22s} {'Baseline':>10s} {'Live':>10s} {'Delta':>10s} {'Status':>8s}")
    print(f"  {'-' * 62}")

    metrics = pd_data["metrics"]
    for key in ["win_rate", "trade_frequency", "expectancy", "profit_factor", "sharpe"]:
        m = metrics.get(key, {})
        if "baseline" in m:
            baseline_val = f"{m['baseline']:.3f}" if isinstance(m["baseline"], float) else str(m["baseline"])
            live_val = f"{m['live']:.3f}" if isinstance(m["live"], float) else str(m["live"])
        elif "baseline_tpd" in m:
            baseline_val = f"{m['baseline_tpd']:.2f}"
            live_val = f"{m['live_tpd']:.2f}"
        elif "baseline_avg_pnl" in m:
            baseline_val = f"${m['baseline_avg_pnl']:.2f}"
            live_val = f"${m['live_avg_pnl']:.2f}"
        else:
            continue

        delta = m.get("delta", m.get("ratio", ""))
        if isinstance(delta, float):
            delta_str = f"{delta:+.3f}"
        else:
            delta_str = str(delta)

        severity = m.get("severity", "—")
        indicator = {"NORMAL": "  ", "DRIFT": "! ", "ALARM": "!!"}
        ind = indicator.get(severity, "  ")

        print(f"  {ind}{key:<20s} {baseline_val:>10s} {live_val:>10s} {delta_str:>10s} {severity:>8s}")

    # Payoff structure
    print(f"\n  PAYOFF STRUCTURE")
    print(f"  {THIN}")
    aw = metrics.get("avg_winner", {})
    al = metrics.get("avg_loser", {})
    if aw:
        print(f"  Avg winner:  baseline ${aw['baseline']:.2f}  |  live ${aw['live']:.2f}")
    if al:
        print(f"  Avg loser:   baseline ${al['baseline']:.2f}  |  live ${al['live']:.2f}")

    # ── Strategy Drift ──
    strat_drift = results["strategy_drift"]
    if strat_drift:
        print(f"\n  STRATEGY DRIFT")
        print(f"  {THIN}")
        print(f"  {'Strategy':<28s} {'Trades':>6s} {'WR Δ':>8s} {'PnL ratio':>10s} {'Status':>8s}")
        print(f"  {'-' * 62}")

        for strat, data in sorted(strat_drift.items(), key=lambda x: x[1].get("severity", "NORMAL"), reverse=True):
            n = data.get("trades", 0)
            wr = data.get("win_rate", {})
            pnl = data.get("avg_pnl", {})
            sev = data.get("severity", "—")

            wr_delta = f"{wr.get('delta', 0):+.3f}" if isinstance(wr.get("delta"), (int, float)) else "—"
            pnl_ratio = f"{pnl.get('ratio', 0):.2f}x" if isinstance(pnl.get("ratio"), (int, float)) else "—"

            indicator = {"NORMAL": "  ", "DRIFT": "! ", "ALARM": "!!"}
            ind = indicator.get(sev, "  ")
            print(f"  {ind}{strat:<26s} {n:>6d} {wr_delta:>8s} {pnl_ratio:>10s} {sev:>8s}")

    # ── Regime Drift ──
    regime_drift = results.get("regime_drift", {})
    if regime_drift and regime_drift.get("status") != "NO_DATA":
        print(f"\n  REGIME-SPECIFIC PERFORMANCE")
        print(f"  {THIN}")
        for regime, data in sorted(regime_drift.items()):
            if isinstance(data, dict) and "days" in data:
                print(f"  {regime:<15s} {data['days']}d  avg ${data['avg_daily_pnl']:>8.2f}/day  "
                      f"total ${data['total_pnl']:>8.2f}  pos_rate {data['positive_rate']:.0%}")

    # ── Alerts ──
    alerts = results.get("alerts", [])
    if alerts:
        print(f"\n  DRIFT ALERTS")
        print(f"  {THIN}")
        for a in alerts:
            level = a["level"]
            indicator = "!!" if level == "ALARM" else "! "
            print(f"  {indicator}[{level}] {a['message']}")
    else:
        print(f"\n  No drift alerts.")

    print()
    print(SEP)


# ── Persistence ──────────────────────────────────────────────────────────────

def save_drift_log(results: dict):
    """Append drift results to persistent log."""
    log = []
    if DRIFT_LOG_PATH.exists():
        try:
            with open(DRIFT_LOG_PATH) as f:
                log = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            log = []

    log.append({
        "date": results["report_date"],
        "overall_status": results["overall_status"],
        "forward_days": results["forward_period"]["days"],
        "forward_trades": results["forward_period"]["trades"],
        "alerts_count": len(results.get("alerts", [])),
        "portfolio_status": results["portfolio_drift"].get("status", "NO_DATA"),
    })

    # Keep last 365 entries
    if len(log) > 365:
        log = log[-365:]

    DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DRIFT_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Live Drift Monitor")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", action="store_true", help="Save report + log")
    args = parser.parse_args()

    results = run_drift_monitor()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_drift_report(results)

    if args.save:
        save_drift_log(results)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = REPORTS_DIR / f"drift_report_{timestamp}.json"
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Drift report saved: {path}")
        print(f"Drift log updated: {DRIFT_LOG_PATH}")


if __name__ == "__main__":
    main()
