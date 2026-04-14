#!/usr/bin/env python3
"""FQL Probation Decision Journal — Record and review probation decisions.

**DEPRECATED 2026-04-14.** This tool's PROBATION_STRATEGIES dict lists
only 3 legacy strategies (DailyTrend-MGC, MomPB-6J, FXBreak-6J) and was
never kept in sync with the current probation set (Treasury-Rolldown,
ZN-Afternoon, VolManaged, XB-ORB-EMA-Ladder-{MNQ,MCL,MYM}). The backing
log `research/data/probation_decision_log.json` has been empty since
2026-03-16. Do not invoke this tool for review decisions. Authoritative
governance lives in docs/PROBATION_REVIEW_CRITERIA.md (legacy watch set)
and docs/XB_ORB_PROBATION_FRAMEWORK.md (XB-ORB family). If a structured
decision journal is wanted in the future, redesign against the current
probation set rather than extending this one.

Records structured evidence and decisions at each review checkpoint.
Connects the weekly scorecard, contribution report, and promotion
playbook into a single decision trail.

Usage:
    # Record a review decision
    python3 research/probation_journal.py --review DailyTrend-MGC-Long --checkpoint week_2

    # View history for a strategy
    python3 research/probation_journal.py --history DailyTrend-MGC-Long

    # View all entries
    python3 research/probation_journal.py --all

    # Generate evidence snapshot for all probation strategies
    python3 research/probation_journal.py --snapshot
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

DATA_DIR = ROOT / "research" / "data"
LOGS_DIR = ROOT / "logs"
LOG_PATH = DATA_DIR / "probation_decision_log.json"

PROBATION_STRATEGIES = {
    "DailyTrend-MGC-Long": {"target_trades": 15, "promote_pf": 1.2, "tier": "REDUCED"},
    "MomPB-6J-Long-US": {"target_trades": 30, "promote_pf": 1.2, "tier": "REDUCED"},
    "FXBreak-6J-Short-London": {"target_trades": 50, "promote_pf": 1.1, "tier": "MICRO"},
}

VALID_CHECKPOINTS = ["week_2", "week_4", "week_8", "week_12", "ad_hoc"]
VALID_DECISIONS = ["continue", "promote", "downgrade", "remove", "investigate"]


def load_log():
    if LOG_PATH.exists():
        return json.load(open(LOG_PATH))
    return {"entries": []}


def save_log(log):
    atomic_write_json(LOG_PATH, log)


def gather_evidence(strategy_id):
    """Automatically gather current evidence for a probation strategy."""
    evidence = {
        "forward_trades": 0,
        "forward_pnl": 0,
        "forward_pf": None,
        "forward_wr": None,
        "forward_max_dd": None,
        "contribution_status": "unknown",
        "drift_status": "unknown",
        "allocation_tier": "unknown",
        "days_in_probation": None,
    }

    # Forward trades from trade log
    trade_log = LOGS_DIR / "trade_log.csv"
    if trade_log.exists():
        try:
            df = pd.read_csv(trade_log)
            if "strategy" in df.columns:
                strat_trades = df[df["strategy"] == strategy_id]
                n = len(strat_trades)
                evidence["forward_trades"] = n
                if n > 0 and "pnl" in strat_trades.columns:
                    pnl = strat_trades["pnl"].sum()
                    evidence["forward_pnl"] = round(float(pnl), 2)
                    wins = strat_trades[strat_trades["pnl"] > 0]
                    losses = strat_trades[strat_trades["pnl"] < 0]
                    gw = wins["pnl"].sum() if len(wins) else 0
                    gl = abs(losses["pnl"].sum()) if len(losses) else 0
                    evidence["forward_pf"] = round(float(gw / gl), 2) if gl > 0 else (99.0 if gw > 0 else 0)
                    evidence["forward_wr"] = round(float(len(wins) / n * 100), 1)
                    eq = 50000 + strat_trades["pnl"].cumsum()
                    evidence["forward_max_dd"] = round(float((eq.cummax() - eq).max()), 2)
        except Exception:
            pass

    # Allocation tier
    alloc_path = DATA_DIR / "allocation_matrix.json"
    if alloc_path.exists():
        try:
            alloc = json.load(open(alloc_path))
            strat_alloc = alloc.get("strategies", {}).get(strategy_id, {})
            evidence["allocation_tier"] = strat_alloc.get("final_tier", "unknown")
        except Exception:
            pass

    # Drift status
    drift_path = DATA_DIR / "live_drift_log.json"
    if drift_path.exists():
        try:
            drift_log = json.load(open(drift_path))
            if drift_log:
                latest = drift_log[-1]
                strat_drift = latest.get("strategies", {}).get(strategy_id, {})
                severities = []
                for sess, info in strat_drift.get("sessions", {}).items():
                    sev = info.get("severity", "NORMAL")
                    if sev != "NORMAL":
                        severities.append(f"{sess}:{sev}")
                evidence["drift_status"] = ", ".join(severities) if severities else "clean"
        except Exception:
            pass

    # Days in probation from registry
    reg_path = DATA_DIR / "strategy_registry.json"
    if reg_path.exists():
        try:
            reg = json.load(open(reg_path))
            for s in reg["strategies"]:
                if s["strategy_id"] == strategy_id:
                    review_date = s.get("last_review_date", "")
                    if review_date:
                        try:
                            start = datetime.strptime(review_date, "%Y-%m-%d")
                            evidence["days_in_probation"] = (datetime.now() - start).days
                        except ValueError:
                            pass
                    break
        except Exception:
            pass

    return evidence


def record_review(strategy_id, checkpoint):
    """Interactive review recording."""
    if strategy_id not in PROBATION_STRATEGIES:
        print(f"Unknown probation strategy: {strategy_id}")
        print(f"Valid: {list(PROBATION_STRATEGIES.keys())}")
        return

    if checkpoint not in VALID_CHECKPOINTS:
        print(f"Invalid checkpoint: {checkpoint}")
        print(f"Valid: {VALID_CHECKPOINTS}")
        return

    thresholds = PROBATION_STRATEGIES[strategy_id]
    evidence = gather_evidence(strategy_id)

    # Display evidence
    W = 65
    print()
    print("=" * W)
    print(f"  PROBATION REVIEW: {strategy_id}")
    print(f"  Checkpoint: {checkpoint}  |  Date: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * W)

    print(f"\n  EVIDENCE (auto-gathered)")
    print(f"  {'-' * (W-4)}")
    target = thresholds["target_trades"]
    progress = round(evidence["forward_trades"] / target * 100, 1) if target else 0
    print(f"  Forward trades:  {evidence['forward_trades']} / {target} ({progress:.0f}%)")
    print(f"  Forward PnL:     ${evidence['forward_pnl']:+,.2f}")
    print(f"  Forward PF:      {evidence['forward_pf'] or 'N/A'}")
    print(f"  Forward WR:      {evidence['forward_wr'] or 'N/A'}%")
    print(f"  Forward Max DD:  ${evidence['forward_max_dd'] or 0:,.2f}")
    print(f"  Allocation tier: {evidence['allocation_tier']}")
    print(f"  Drift status:    {evidence['drift_status']}")
    print(f"  Days in probation: {evidence['days_in_probation'] or '?'}")

    print(f"\n  THRESHOLDS")
    print(f"  {'-' * (W-4)}")
    print(f"  Promote PF:    > {thresholds['promote_pf']}")
    print(f"  Target trades: {thresholds['target_trades']}")

    # Prompt for decision
    print(f"\n  DECISION")
    print(f"  {'-' * (W-4)}")
    print(f"  Options: {', '.join(VALID_DECISIONS)}")
    decision = input("  Decision: ").strip().lower()
    if decision not in VALID_DECISIONS:
        print(f"  Invalid decision. Aborting.")
        return

    rationale = input("  Rationale (one line): ").strip()
    anomaly_notes = input("  Anomaly/drift notes (or Enter to skip): ").strip()
    contribution_notes = input("  Contribution notes (or Enter to skip): ").strip()

    # Build entry
    entry = {
        "strategy_id": strategy_id,
        "review_date": datetime.now().strftime("%Y-%m-%d"),
        "checkpoint": checkpoint,
        "decision": decision,
        "rationale": rationale,
        "evidence": evidence,
        "anomaly_notes": anomaly_notes or None,
        "contribution_notes": contribution_notes or None,
        "next_review": None,
    }

    # Set next review
    next_map = {
        "week_2": "week_4",
        "week_4": "week_8",
        "week_8": "week_12",
        "week_12": None,
    }
    if decision in ("continue", "investigate"):
        entry["next_review"] = next_map.get(checkpoint)

    # Save
    log = load_log()
    log["entries"].append(entry)
    save_log(log)

    print(f"\n  Recorded: {decision.upper()} for {strategy_id} at {checkpoint}")
    if entry["next_review"]:
        print(f"  Next review: {entry['next_review']}")
    print(f"  Saved to: {LOG_PATH.relative_to(ROOT)}")


def show_snapshot():
    """Generate evidence snapshot for all probation strategies."""
    W = 65
    print()
    print("=" * W)
    print(f"  PROBATION EVIDENCE SNAPSHOT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    for sid, thresholds in PROBATION_STRATEGIES.items():
        evidence = gather_evidence(sid)
        target = thresholds["target_trades"]
        progress = round(evidence["forward_trades"] / target * 100, 1) if target else 0
        bar_len = int(progress / 5)
        bar = "#" * bar_len + "." * (20 - bar_len)

        print(f"\n  {sid}")
        print(f"  [{bar}] {evidence['forward_trades']}/{target} ({progress:.0f}%)")
        print(f"  PnL: ${evidence['forward_pnl']:+,.2f}  |  "
              f"PF: {evidence['forward_pf'] or 'N/A'}  |  "
              f"Tier: {evidence['allocation_tier']}  |  "
              f"Drift: {evidence['drift_status']}")

    print(f"\n{'=' * W}")


def show_history(strategy_id):
    """Show decision history for a strategy."""
    log = load_log()
    entries = [e for e in log["entries"] if e["strategy_id"] == strategy_id]

    if not entries:
        print(f"No review history for {strategy_id}")
        return

    W = 65
    print()
    print("=" * W)
    print(f"  REVIEW HISTORY: {strategy_id}")
    print("=" * W)

    for entry in entries:
        print(f"\n  {entry['review_date']} — {entry['checkpoint']}")
        print(f"  Decision: {entry['decision'].upper()}")
        print(f"  Rationale: {entry['rationale']}")
        ev = entry.get("evidence", {})
        print(f"  Evidence: {ev.get('forward_trades', 0)} trades, "
              f"PnL ${ev.get('forward_pnl', 0):+,.2f}, "
              f"PF {ev.get('forward_pf', 'N/A')}")
        if entry.get("anomaly_notes"):
            print(f"  Anomalies: {entry['anomaly_notes']}")
        if entry.get("next_review"):
            print(f"  Next review: {entry['next_review']}")

    print(f"\n{'=' * W}")


def show_all():
    """Show all entries."""
    log = load_log()
    if not log["entries"]:
        print("No review entries yet.")
        return

    W = 65
    print()
    print("=" * W)
    print(f"  ALL PROBATION REVIEWS ({len(log['entries'])} entries)")
    print("=" * W)

    for entry in log["entries"]:
        print(f"  {entry['review_date']} | {entry['strategy_id']:<30s} | "
              f"{entry['checkpoint']:<8s} | {entry['decision'].upper()}")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL Probation Decision Journal")
    parser.add_argument("--review", type=str, help="Record a review for a strategy")
    parser.add_argument("--checkpoint", type=str, help="Review checkpoint (week_2/4/8/12/ad_hoc)")
    parser.add_argument("--history", type=str, help="Show review history for a strategy")
    parser.add_argument("--snapshot", action="store_true", help="Evidence snapshot for all probation strategies")
    parser.add_argument("--all", action="store_true", help="Show all review entries")
    args = parser.parse_args()

    if args.review:
        if not args.checkpoint:
            print("--checkpoint required with --review")
            print(f"Valid: {VALID_CHECKPOINTS}")
            return
        record_review(args.review, args.checkpoint)
    elif args.history:
        show_history(args.history)
    elif args.snapshot:
        show_snapshot()
    elif args.all:
        show_all()
    else:
        show_snapshot()


if __name__ == "__main__":
    main()
