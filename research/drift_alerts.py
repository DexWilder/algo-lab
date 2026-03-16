#!/usr/bin/env python3
"""FQL Drift Alert System — Evaluate drift results and generate actionable alerts.

Consumes output from live_drift_monitor.py and produces:
    - Controller-facing signals (feeds into activation scoring)
    - Human-readable alert summaries
    - Recommended actions per strategy

Usage:
    from research.drift_alerts import evaluate_drift_alerts
    alerts = evaluate_drift_alerts(drift_results)
"""

from research.live_drift_monitor import run_drift_monitor


def evaluate_drift_alerts(drift_results: dict = None) -> dict:
    """Evaluate drift results and produce structured alerts.

    Parameters
    ----------
    drift_results : dict, optional
        Output from run_drift_monitor(). If None, runs the monitor.

    Returns
    -------
    dict with:
        - overall_status: NORMAL / DRIFT / ALARM
        - controller_signals: dict of strategy -> signal updates
        - alerts: list of alert dicts
        - recommended_actions: list of action dicts
    """
    if drift_results is None:
        drift_results = run_drift_monitor()

    alerts = []
    controller_signals = {}
    recommended_actions = []

    overall = drift_results.get("overall_status", "NO_DATA")

    # ── Portfolio-level alerts ────────────────────────────────────────
    portfolio = drift_results.get("portfolio_drift", {})
    if portfolio.get("status") == "ALARM":
        alerts.append({
            "level": "ALARM",
            "scope": "PORTFOLIO",
            "message": "Portfolio performance significantly diverges from backtest — review all active strategies",
            "action": "REDUCE_ALL",
        })
        recommended_actions.append({
            "action": "Reduce position sizes across all strategies",
            "urgency": "HIGH",
            "reason": "Portfolio-level ALARM drift detected",
        })

    # Check specific metrics
    metrics = portfolio.get("metrics", {})

    # Win rate alarm
    wr = metrics.get("win_rate", {})
    if wr.get("severity") == "ALARM":
        alerts.append({
            "level": "ALARM",
            "scope": "PORTFOLIO",
            "message": f"Win rate dropped to {wr.get('live', 0):.1%} (baseline {wr.get('baseline', 0):.1%})",
        })

    # Profit factor alarm
    pf = metrics.get("profit_factor", {})
    if pf.get("severity") == "ALARM" and isinstance(pf.get("live"), (int, float)) and pf["live"] < 1.0:
        alerts.append({
            "level": "ALARM",
            "scope": "PORTFOLIO",
            "message": f"Profit factor below 1.0 ({pf['live']:.2f}) — system is losing money",
            "action": "HALT_REVIEW",
        })
        recommended_actions.append({
            "action": "Pause forward testing and conduct full review",
            "urgency": "CRITICAL",
            "reason": "Portfolio losing money in forward test",
        })

    # ── Strategy-level alerts ─────────────────────────────────────────
    for strat, data in drift_results.get("strategy_drift", {}).items():
        severity = data.get("severity", "NORMAL")

        if severity == "ALARM":
            controller_signals[strat] = {
                "drift_status": "ALARM",
                "recommended_action": "PROBATION",
                "reason": f"Forward metrics diverge significantly from backtest",
            }
            alerts.append({
                "level": "ALARM",
                "scope": strat,
                "message": f"{strat}: significant forward divergence — recommend PROBATION",
            })
            recommended_actions.append({
                "action": f"Move {strat} to PROBATION or REDUCED_ON",
                "urgency": "HIGH",
                "reason": f"Drift ALARM on {strat}",
            })

        elif severity == "DRIFT":
            controller_signals[strat] = {
                "drift_status": "DRIFT",
                "recommended_action": "MONITOR",
                "reason": "Moderate divergence from baseline — watch for 2+ weeks",
            }
            alerts.append({
                "level": "DRIFT",
                "scope": strat,
                "message": f"{strat}: moderate drift detected — monitoring",
            })

        else:
            controller_signals[strat] = {
                "drift_status": "NORMAL",
                "recommended_action": "NO_CHANGE",
            }

    # ── No-trade detection ────────────────────────────────────────────
    for strat, data in drift_results.get("strategy_drift", {}).items():
        if data.get("trades", 0) == 0 and drift_results["forward_period"]["days"] >= 5:
            alerts.append({
                "level": "DRIFT",
                "scope": strat,
                "message": f"{strat}: zero trades in {drift_results['forward_period']['days']} forward days",
            })
            controller_signals.setdefault(strat, {})["no_trades"] = True

    # ── Session-specific alerts ─────────────────────────────────────
    session_drift = drift_results.get("session_drift", {})
    strategy_sessions = session_drift.get("strategy_sessions", {})

    for strat, sessions in strategy_sessions.items():
        session_restrictions = []
        for session_name, data in sessions.items():
            sev = data.get("severity", "NORMAL")
            if sev == "ALARM":
                session_restrictions.append({
                    "session": session_name,
                    "action": "BLOCK",
                    "severity": "ALARM",
                    "reason": f"Edge broken (WR delta {data.get('wr_delta', 0):+.1%}, PnL ratio {data.get('pnl_ratio', 0):.2f})",
                })
                alerts.append({
                    "level": "ALARM",
                    "scope": f"{strat}/{session_name}",
                    "message": f"{strat}: {session_name} edge broken — recommend BLOCK in {session_name}",
                })
            elif sev == "DRIFT":
                session_restrictions.append({
                    "session": session_name,
                    "action": "REDUCE",
                    "severity": "DRIFT",
                    "reason": f"Degraded (WR delta {data.get('wr_delta', 0):+.1%})",
                })

        if session_restrictions:
            controller_signals.setdefault(strat, {})["session_restrictions"] = session_restrictions

    # Session concentration warnings
    for warning in session_drift.get("concentration_warnings", []):
        alerts.append({
            "level": "DRIFT",
            "scope": "PORTFOLIO",
            "message": f"Session concentration: {warning['message']}",
        })

    return {
        "overall_status": overall,
        "controller_signals": controller_signals,
        "alerts": alerts,
        "recommended_actions": recommended_actions,
    }
