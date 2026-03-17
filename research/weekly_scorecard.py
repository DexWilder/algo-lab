#!/usr/bin/env python3
"""FQL Weekly Portfolio Scorecard -- Friday review template.

Pulls from all FQL subsystems to produce a structured weekly review.
Designed to be run every Friday as part of the operating rhythm.

Sections:
  1. Forward runner summary
  2. Probation strategy progress
  3. Core strategy summary
  4. Drift / anomaly review
  5. Regime and session observations
  6. Factory pipeline status
  7. Recommended actions

Usage:
    python3 research/weekly_scorecard.py              # Terminal report
    python3 research/weekly_scorecard.py --save       # Save to reports/
    python3 research/weekly_scorecard.py --json       # JSON output
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

DATA_DIR = ROOT / "research" / "data"
LOGS_DIR = ROOT / "logs"
REPORTS_DIR = ROOT / "research" / "reports"
STATE_DIR = ROOT / "state"

PROBATION_THRESHOLDS = {
    "DailyTrend-MGC-Long": {"target": 15, "min_pf": 1.2, "tier": "REDUCED"},
    "MomPB-6J-Long-US": {"target": 30, "min_pf": 1.2, "tier": "REDUCED"},
    "FXBreak-6J-Short-London": {"target": 50, "min_pf": 1.1, "tier": "MICRO"},
}


def section_forward_runner():
    """Section 1: Forward runner summary."""
    result = {"trades_this_week": 0, "pnl_this_week": 0, "equity": 0, "trailing_dd": 0,
              "total_trades": 0, "last_run": "never", "run_count": 0, "issues": []}

    # Account state
    state_path = STATE_DIR / "account_state.json"
    if state_path.exists():
        try:
            state = json.load(open(state_path))
            result["equity"] = state.get("equity", 0)
            result["trailing_dd"] = state.get("equity_hwm", 0) - state.get("equity", 0)
            result["total_trades"] = state.get("total_trades", 0)
            result["last_run"] = state.get("last_run", "never")
            result["run_count"] = state.get("run_count", 0)
        except Exception:
            result["issues"].append("Account state unreadable")

    # Trade log — this week's trades
    trade_log = LOGS_DIR / "trade_log.csv"
    if trade_log.exists():
        try:
            df = pd.read_csv(trade_log)
            if "date" in df.columns:
                cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                week = df[df["date"] >= cutoff]
                result["trades_this_week"] = len(week)
                result["pnl_this_week"] = round(float(week["pnl"].sum()), 2) if "pnl" in week.columns and len(week) > 0 else 0

                # Per-strategy breakdown
                if "strategy" in week.columns and len(week) > 0:
                    breakdown = week.groupby("strategy")["pnl"].agg(["count", "sum"]).reset_index()
                    result["strategy_breakdown"] = [
                        {"strategy": row["strategy"], "trades": int(row["count"]), "pnl": round(float(row["sum"]), 2)}
                        for _, row in breakdown.iterrows()
                    ]
        except Exception:
            result["issues"].append("Trade log unreadable")

    return result


def section_probation_progress():
    """Section 2: Probation strategy forward evidence."""
    result = {"strategies": {}, "issues": []}

    trade_log = LOGS_DIR / "trade_log.csv"
    trade_counts = {}

    if trade_log.exists():
        try:
            df = pd.read_csv(trade_log)
            if "strategy" in df.columns:
                for sid in PROBATION_THRESHOLDS:
                    strat_trades = df[df["strategy"] == sid]
                    count = len(strat_trades)
                    pnl = round(float(strat_trades["pnl"].sum()), 2) if "pnl" in strat_trades.columns and count > 0 else 0
                    trade_counts[sid] = {"count": count, "pnl": pnl}
        except Exception:
            result["issues"].append("Trade log unreadable")

    for sid, thresh in PROBATION_THRESHOLDS.items():
        tc = trade_counts.get(sid, {"count": 0, "pnl": 0})
        target = thresh["target"]
        progress = round(tc["count"] / target * 100, 1) if target else 0

        # Determine status
        if tc["count"] >= target:
            if tc["count"] > 0:
                pf_est = "needs_calculation"
            else:
                pf_est = "no_trades"
            status = "REVIEW_READY"
        elif tc["count"] == 0:
            status = "NO_EVIDENCE"
        else:
            status = "ACCUMULATING"

        result["strategies"][sid] = {
            "forward_trades": tc["count"],
            "target": target,
            "progress_pct": progress,
            "forward_pnl": tc["pnl"],
            "tier": thresh["tier"],
            "status": status,
        }

    return result


def section_core_summary():
    """Section 3: Core strategy summary."""
    result = {"strategies": [], "issues": []}

    reg_path = DATA_DIR / "strategy_registry.json"
    if not reg_path.exists():
        return result

    try:
        reg = json.load(open(reg_path))
        for s in reg["strategies"]:
            if s.get("status") == "core":
                result["strategies"].append({
                    "strategy_id": s["strategy_id"],
                    "asset": s.get("asset", "?"),
                    "activation_score": s.get("activation_score"),
                    "controller_action": s.get("controller_action", "?"),
                    "half_life_status": s.get("half_life_status", "?"),
                })
    except Exception:
        result["issues"].append("Registry unreadable")

    return result


def section_drift_anomalies():
    """Section 4: Drift alerts and anomalies."""
    result = {"alarms": [], "drifts": [], "issues": []}

    drift_path = DATA_DIR / "live_drift_log.json"
    if not drift_path.exists():
        return result

    try:
        log = json.load(open(drift_path))
        if log:
            latest = log[-1]
            for sid, sdata in latest.get("strategies", {}).items():
                for sess, info in sdata.get("sessions", {}).items():
                    severity = info.get("severity", "NORMAL")
                    if severity == "ALARM":
                        result["alarms"].append(f"{sid}/{sess}")
                    elif severity == "DRIFT":
                        result["drifts"].append(f"{sid}/{sess}")
    except Exception:
        result["issues"].append("Drift log unreadable")

    return result


def section_regime_session():
    """Section 5: Current regime and session observations."""
    result = {"current_regime": {}, "issues": []}

    alloc_path = DATA_DIR / "allocation_matrix.json"
    if alloc_path.exists():
        try:
            alloc = json.load(open(alloc_path))
            result["allocation_date"] = alloc.get("report_date", "?")
            result["tier_distribution"] = alloc.get("summary", {}).get("tier_distribution", {})
        except Exception:
            pass

    # Get latest regime from activation matrix
    matrix_path = DATA_DIR / "portfolio_activation_matrix.json"
    if matrix_path.exists():
        try:
            matrix = json.load(open(matrix_path))
            result["current_regime"] = matrix.get("regime_snapshot", {})
        except Exception:
            pass

    return result


def section_factory_status():
    """Section 6: Factory pipeline status."""
    result = {"first_pass_reports": 0, "classifications": {}, "registry_counts": {}, "issues": []}

    # First-pass reports
    fp_dir = DATA_DIR / "first_pass"
    if fp_dir.exists():
        reports = list(fp_dir.glob("*.json"))
        result["first_pass_reports"] = len(reports)
        cls = Counter()
        for f in reports:
            try:
                data = json.load(open(f))
                cls[data.get("overall_classification", "?")] += 1
            except Exception:
                pass
        result["classifications"] = dict(cls)

    # Registry counts
    reg_path = DATA_DIR / "strategy_registry.json"
    if reg_path.exists():
        try:
            reg = json.load(open(reg_path))
            statuses = Counter(s.get("status") for s in reg.get("strategies", []))
            result["registry_counts"] = dict(statuses)
        except Exception:
            pass

    # Scheduler health
    log_path = DATA_DIR / "scheduler_log.json"
    if log_path.exists():
        try:
            log = json.load(open(log_path))
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            recent = [e for e in log if e.get("started", "") >= cutoff]
            errors = [e for e in recent if e.get("status") == "ERROR"]
            result["scheduler_runs_7d"] = len(recent)
            result["scheduler_errors_7d"] = len(errors)
        except Exception:
            pass

    return result


def build_actions(forward, probation, drift):
    """Section 7: Recommended actions."""
    actions = []

    # Probation reviews
    for sid, data in probation.get("strategies", {}).items():
        if data["status"] == "REVIEW_READY":
            actions.append({"type": "PROMOTE_REVIEW", "strategy": sid,
                            "detail": f"{data['forward_trades']} trades accumulated, review for promotion"})
        elif data["status"] == "NO_EVIDENCE":
            actions.append({"type": "INVESTIGATE", "strategy": sid,
                            "detail": "0 forward trades — check if strategy is generating signals"})

    # Drift alarms
    for alarm in drift.get("alarms", []):
        actions.append({"type": "INVESTIGATE", "strategy": alarm,
                        "detail": "ALARM-level drift — review whether edge is broken"})

    # Forward runner staleness
    last_run = forward.get("last_run", "never")
    if last_run != "never":
        try:
            last_dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
            days = (datetime.now() - last_dt).days
            if days > 3:
                actions.append({"type": "INVESTIGATE", "strategy": "forward_runner",
                                "detail": f"Last run {days} days ago — run start_forward_day.sh"})
        except ValueError:
            pass

    if not actions:
        actions.append({"type": "CONTINUE", "strategy": "all",
                        "detail": "No immediate actions required. System operating normally."})

    return actions


# ── Report Output ────────────────────────────────────────────────────────────

def print_scorecard(sections):
    W = 70
    print()
    print("=" * W)
    print("  FQL WEEKLY PORTFOLIO SCORECARD")
    print(f"  Week ending: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * W)

    # 1. Forward Runner
    fwd = sections["forward_runner"]
    print(f"\n  1. FORWARD RUNNER")
    print(f"  {'-' * (W-4)}")
    print(f"  Equity: ${fwd['equity']:,.2f}  |  Trailing DD: ${fwd['trailing_dd']:,.2f}")
    print(f"  This week: {fwd['trades_this_week']} trades, PnL ${fwd['pnl_this_week']:+,.2f}")
    print(f"  Total: {fwd['total_trades']} trades  |  Last run: {fwd['last_run']}")
    for bd in fwd.get("strategy_breakdown", []):
        print(f"    {bd['strategy']}: {bd['trades']} trades, ${bd['pnl']:+,.2f}")

    # 2. Probation Progress
    prob = sections["probation_progress"]
    print(f"\n  2. PROBATION PROGRESS")
    print(f"  {'-' * (W-4)}")
    for sid, data in prob["strategies"].items():
        bar_len = int(data["progress_pct"] / 5)
        bar = "#" * bar_len + "." * (20 - bar_len)
        print(f"  {sid}")
        print(f"    [{bar}] {data['forward_trades']}/{data['target']} ({data['progress_pct']:.0f}%)  PnL: ${data['forward_pnl']:+,.2f}  [{data['status']}]")

    # 3. Core Summary
    core = sections["core_summary"]
    print(f"\n  3. CORE STRATEGIES")
    print(f"  {'-' * (W-4)}")
    for s in core["strategies"]:
        score = s.get("activation_score")
        score_str = f"{score:.2f}" if score else "?"
        print(f"  {s['strategy_id']:<30s} {s['asset']:<5s} score={score_str} action={s['controller_action']} HL={s['half_life_status']}")

    # 4. Drift
    drift = sections["drift_anomalies"]
    print(f"\n  4. DRIFT / ANOMALIES")
    print(f"  {'-' * (W-4)}")
    if drift["alarms"]:
        print(f"  ALARMS: {', '.join(drift['alarms'])}")
    if drift["drifts"]:
        print(f"  DRIFTS: {', '.join(drift['drifts'])}")
    if not drift["alarms"] and not drift["drifts"]:
        print(f"  No active drift alerts.")

    # 5. Regime
    regime = sections["regime_session"]
    print(f"\n  5. REGIME / ALLOCATION")
    print(f"  {'-' * (W-4)}")
    cr = regime.get("current_regime", {})
    if cr:
        print(f"  Regime: {cr.get('composite', '?')}  |  RV: {cr.get('rv_regime', '?')}  |  Persist: {cr.get('trend_persistence', '?')}")
    td = regime.get("tier_distribution", {})
    if td:
        print(f"  Tiers: {', '.join(f'{k}:{v}' for k,v in td.items())}")

    # 6. Factory
    factory = sections["factory_status"]
    print(f"\n  6. FACTORY PIPELINE")
    print(f"  {'-' * (W-4)}")
    print(f"  Reports: {factory['first_pass_reports']}  |  Scheduler: {factory.get('scheduler_runs_7d', '?')} runs, {factory.get('scheduler_errors_7d', '?')} errors (7d)")
    rc = factory.get("registry_counts", {})
    if rc:
        print(f"  Registry: {', '.join(f'{k}:{v}' for k,v in rc.items())}")
    cls = factory.get("classifications", {})
    if cls:
        print(f"  Classifications: {', '.join(f'{k}:{v}' for k,v in cls.items())}")

    # 7. Actions
    actions = sections["actions"]
    print(f"\n  7. RECOMMENDED ACTIONS")
    print(f"  {'-' * (W-4)}")
    for a in actions:
        icon = {"PROMOTE_REVIEW": ">>", "INVESTIGATE": "!!", "CONTINUE": "  ", "DOWNGRADE": "XX"}.get(a["type"], "  ")
        print(f"  {icon} [{a['type']}] {a['strategy']}: {a['detail']}")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL Weekly Portfolio Scorecard")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    sections = {
        "forward_runner": section_forward_runner(),
        "probation_progress": section_probation_progress(),
        "core_summary": section_core_summary(),
        "drift_anomalies": section_drift_anomalies(),
        "regime_session": section_regime_session(),
        "factory_status": section_factory_status(),
    }
    sections["actions"] = build_actions(
        sections["forward_runner"],
        sections["probation_progress"],
        sections["drift_anomalies"],
    )

    report = {"week_ending": datetime.now().strftime("%Y-%m-%d"), "sections": sections}

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_scorecard(sections)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d")
        out = REPORTS_DIR / f"weekly_scorecard_{ts}.json"
        atomic_write_json(out, report)
        print(f"\n  Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
