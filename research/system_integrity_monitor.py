#!/usr/bin/env python3
"""FQL System Integrity Monitor — Weekly self-diagnostic report.

Builds on the minimum viable watchdog (system_watchdog.py) to provide
a comprehensive weekly health report across all FQL subsystems.

Checks:
  1. Scheduler/job health — missed runs, error rates, stale jobs
  2. Registry consistency — schema, field completeness, orphaned entries
  3. Data freshness — processed data staleness, missing assets
  4. Batch first-pass health — output accumulation, classification distribution
  5. Forward runner health — trade logging, probation evidence accumulation
  6. Probation strategy tracking — forward trade counts vs thresholds
  7. Failed/missing run detection — gaps in expected automation

Usage:
    python3 research/system_integrity_monitor.py              # Full report
    python3 research/system_integrity_monitor.py --json       # JSON output
    python3 research/system_integrity_monitor.py --save       # Save report
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

REPORTS_DIR = ROOT / "research" / "reports"
DATA_DIR = ROOT / "research" / "data"
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"

# Probation promotion thresholds
PROBATION_THRESHOLDS = {
    "DailyTrend-MGC-Long": {"target_trades": 15, "min_pf": 1.2},
    "MomPB-6J-Long-US": {"target_trades": 30, "min_pf": 1.2},
    "FXBreak-6J-Short-London": {"target_trades": 50, "min_pf": 1.1},
}


def check_scheduler_health():
    """Check scheduler job execution over last 14 days."""
    log_path = DATA_DIR / "scheduler_log.json"
    result = {"status": "OK", "details": {}, "issues": []}

    if not log_path.exists():
        return {"status": "FAIL", "details": {}, "issues": ["No scheduler log found"]}

    try:
        log = json.load(open(log_path))
    except Exception:
        return {"status": "FAIL", "details": {}, "issues": ["Scheduler log corrupted"]}

    cutoff = (datetime.now() - timedelta(days=14)).isoformat()
    recent = [e for e in log if e.get("started", "") >= cutoff]

    # Count by status
    success = sum(1 for e in recent if e.get("status") == "SUCCESS")
    errors = sum(1 for e in recent if e.get("status") == "ERROR")
    total = len(recent)

    result["details"] = {
        "total_runs_14d": total,
        "success": success,
        "errors": errors,
        "error_rate": round(errors / total * 100, 1) if total else 0,
    }

    # Check for jobs that should have run but didn't
    if total == 0:
        result["status"] = "FAIL"
        result["issues"].append("No scheduler runs in last 14 days")
    elif errors > 5:
        result["status"] = "WARN"
        result["issues"].append(f"{errors} errors in last 14 days")

    # Check which daily jobs ran in the last 3 days
    cutoff_3d = (datetime.now() - timedelta(days=3)).isoformat()
    recent_3d = [e for e in log if e.get("started", "") >= cutoff_3d]
    daily_jobs = {"daily_health_check", "daily_half_life", "daily_contribution",
                  "daily_activation_matrix", "daily_decision_report", "daily_drift_monitor"}
    ran_recently = {e.get("job") for e in recent_3d if e.get("status") == "SUCCESS"}
    missing_daily = daily_jobs - ran_recently

    if missing_daily:
        result["details"]["missing_daily_jobs"] = sorted(missing_daily)
        if len(missing_daily) >= 3:
            result["status"] = "WARN"
            result["issues"].append(f"Missing daily jobs: {', '.join(sorted(missing_daily))}")

    return result


def check_registry_consistency():
    """Check registry for schema consistency and field completeness."""
    reg_path = DATA_DIR / "strategy_registry.json"
    result = {"status": "OK", "details": {}, "issues": []}

    if not reg_path.exists():
        return {"status": "FAIL", "details": {}, "issues": ["Registry file missing"]}

    try:
        reg = json.load(open(reg_path))
    except Exception:
        return {"status": "FAIL", "details": {}, "issues": ["Registry JSON corrupted"]}

    strategies = reg.get("strategies", [])
    result["details"]["total_strategies"] = len(strategies)
    result["details"]["schema_version"] = reg.get("_schema_version", "unknown")

    # Check required fields
    required = ["strategy_id", "family", "asset", "direction", "status"]
    missing_fields = []
    for s in strategies:
        for f in required:
            if not s.get(f):
                missing_fields.append(f"{s.get('strategy_id', '?')}: missing {f}")

    if missing_fields:
        result["status"] = "WARN"
        result["issues"].append(f"{len(missing_fields)} missing required fields")
        result["details"]["missing_fields"] = missing_fields[:10]

    # Check for duplicate IDs
    ids = [s["strategy_id"] for s in strategies]
    dupes = [sid for sid in ids if ids.count(sid) > 1]
    if dupes:
        result["status"] = "FAIL"
        result["issues"].append(f"Duplicate strategy IDs: {set(dupes)}")

    # Status distribution
    from collections import Counter
    statuses = Counter(s.get("status") for s in strategies)
    result["details"]["status_distribution"] = dict(statuses)

    # Rejection coverage
    rejected = [s for s in strategies if s.get("status") == "rejected"]
    classified = sum(1 for s in rejected if s.get("rejection_reason"))
    result["details"]["rejection_classified"] = f"{classified}/{len(rejected)}"
    if rejected and classified < len(rejected):
        result["issues"].append(f"{len(rejected) - classified} rejected strategies without classification")

    return result


def check_data_freshness():
    """Check processed data files for staleness."""
    processed = ROOT / "data" / "processed"
    result = {"status": "OK", "details": {}, "issues": []}

    if not processed.exists():
        return {"status": "FAIL", "details": {}, "issues": ["data/processed/ missing"]}

    now = datetime.now()
    assets = {}
    stale = []

    for csv in sorted(processed.glob("*_5m.csv")):
        sym = csv.stem.replace("_5m", "")
        age_hours = (now.timestamp() - csv.stat().st_mtime) / 3600
        size_mb = csv.stat().st_size / (1024 * 1024)
        assets[sym] = {"age_hours": round(age_hours, 1), "size_mb": round(size_mb, 1)}
        if age_hours > 120:  # 5 days (account for weekends)
            stale.append(sym)

    result["details"]["assets_with_data"] = len(assets)
    result["details"]["assets"] = assets

    if stale:
        result["status"] = "WARN"
        result["issues"].append(f"Stale data (>5 days): {', '.join(stale)}")

    return result


def check_batch_first_pass():
    """Check batch first-pass output health."""
    fp_dir = DATA_DIR / "first_pass"
    result = {"status": "OK", "details": {}, "issues": []}

    if not fp_dir.exists():
        return {"status": "OK", "details": {"reports": 0}, "issues": []}

    reports = list(fp_dir.glob("*.json"))
    result["details"]["total_reports"] = len(reports)

    # Classification distribution
    from collections import Counter
    classifications = Counter()
    for f in reports:
        try:
            data = json.load(open(f))
            classifications[data.get("overall_classification", "UNKNOWN")] += 1
        except Exception:
            classifications["CORRUPT"] += 1

    result["details"]["classification_distribution"] = dict(classifications)

    if classifications.get("CORRUPT", 0) > 0:
        result["status"] = "WARN"
        result["issues"].append(f"{classifications['CORRUPT']} corrupted first-pass reports")

    return result


def check_forward_runner():
    """Check forward runner output and trade logging."""
    result = {"status": "OK", "details": {}, "issues": []}

    # Check account state
    state_path = STATE_DIR / "account_state.json"
    if state_path.exists():
        try:
            state = json.load(open(state_path))
            result["details"]["equity"] = state.get("equity", 0)
            result["details"]["cumulative_pnl"] = state.get("cumulative_pnl", 0)
            result["details"]["total_trades"] = state.get("total_trades", 0)
            result["details"]["last_run"] = state.get("last_run", "never")
            result["details"]["run_count"] = state.get("run_count", 0)

            # Check staleness
            last_run = state.get("last_run", "")
            if last_run:
                try:
                    last_dt = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
                    days_since = (datetime.now() - last_dt).days
                    if days_since > 5:
                        result["status"] = "WARN"
                        result["issues"].append(f"Forward runner last ran {days_since} days ago")
                except ValueError:
                    pass
        except Exception:
            result["status"] = "WARN"
            result["issues"].append("Account state file unreadable")
    else:
        result["details"]["last_run"] = "never"

    # Check trade log
    trade_log = LOGS_DIR / "trade_log.csv"
    if trade_log.exists():
        try:
            df = pd.read_csv(trade_log)
            result["details"]["logged_trades"] = len(df)
            if "status" in df.columns:
                result["details"]["probation_trades"] = int((df["status"] == "probation").sum())
                result["details"]["core_trades"] = int((df["status"] == "core").sum())
        except Exception:
            result["details"]["logged_trades"] = "error reading"
    else:
        result["details"]["logged_trades"] = 0

    return result


def check_probation_progress():
    """Check forward evidence accumulation for probation strategies."""
    result = {"status": "OK", "details": {}, "issues": []}

    trade_log = LOGS_DIR / "trade_log.csv"
    probation_trades = {}

    if trade_log.exists():
        try:
            df = pd.read_csv(trade_log)
            if "strategy" in df.columns:
                for sid in PROBATION_THRESHOLDS:
                    count = int((df["strategy"] == sid).sum())
                    probation_trades[sid] = count
        except Exception:
            pass

    for sid, thresholds in PROBATION_THRESHOLDS.items():
        forward_trades = probation_trades.get(sid, 0)
        target = thresholds["target_trades"]
        pct = round(forward_trades / target * 100, 1) if target else 0

        result["details"][sid] = {
            "forward_trades": forward_trades,
            "target": target,
            "progress_pct": pct,
        }

        if forward_trades == 0:
            result["issues"].append(f"{sid}: 0 forward trades (target: {target})")

    if len(result["issues"]) == len(PROBATION_THRESHOLDS):
        result["status"] = "WARN"

    return result


def check_allocation_matrix():
    """Check allocation matrix freshness and consistency."""
    result = {"status": "OK", "details": {}, "issues": []}

    alloc_path = DATA_DIR / "allocation_matrix.json"
    if not alloc_path.exists():
        return {"status": "WARN", "details": {}, "issues": ["No allocation matrix found"]}

    try:
        alloc = json.load(open(alloc_path))
        result["details"]["report_date"] = alloc.get("report_date", "unknown")
        result["details"]["strategies"] = len(alloc.get("strategies", {}))
        result["details"]["tier_distribution"] = alloc.get("summary", {}).get("tier_distribution", {})
    except Exception:
        result["status"] = "WARN"
        result["issues"].append("Allocation matrix unreadable")

    return result


# ── Report Builder ───────────────────────────────────────────────────────────

CHECKS = [
    ("scheduler_health", check_scheduler_health),
    ("registry_consistency", check_registry_consistency),
    ("data_freshness", check_data_freshness),
    ("batch_first_pass", check_batch_first_pass),
    ("forward_runner", check_forward_runner),
    ("probation_progress", check_probation_progress),
    ("allocation_matrix", check_allocation_matrix),
]


def run_integrity_check():
    """Run all integrity checks and produce report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "checks": {},
        "overall": "HEALTHY",
        "total_issues": 0,
    }

    for name, check_fn in CHECKS:
        try:
            result = check_fn()
        except Exception as e:
            result = {"status": "FAIL", "details": {}, "issues": [f"Check crashed: {e}"]}
        report["checks"][name] = result

    # Determine overall status
    statuses = [r["status"] for r in report["checks"].values()]
    all_issues = []
    for r in report["checks"].values():
        all_issues.extend(r.get("issues", []))

    report["total_issues"] = len(all_issues)

    if "FAIL" in statuses:
        report["overall"] = "DEGRADED"
    elif len(all_issues) > 3:
        report["overall"] = "ATTENTION"
    elif all_issues:
        report["overall"] = "HEALTHY_WITH_NOTES"
    else:
        report["overall"] = "HEALTHY"

    return report


def print_report(report):
    """Print formatted integrity report."""
    W = 70
    print()
    print("=" * W)
    print(f"  FQL SYSTEM INTEGRITY REPORT")
    print(f"  {report['timestamp'][:19]}")
    print(f"  Overall: {report['overall']}  |  Issues: {report['total_issues']}")
    print("=" * W)

    for name, check in report["checks"].items():
        status = check["status"]
        icon = {"OK": " ", "WARN": "!", "FAIL": "X"}[status]
        label = name.replace("_", " ").title()
        print(f"\n  [{icon}] {label}")
        print(f"  {'-' * (W - 4)}")

        # Print key details
        for k, v in check.get("details", {}).items():
            if isinstance(v, dict) and len(str(v)) > 60:
                print(f"      {k}:")
                for dk, dv in v.items():
                    print(f"        {dk}: {dv}")
            else:
                print(f"      {k}: {v}")

        for issue in check.get("issues", []):
            print(f"      >> {issue}")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL System Integrity Monitor")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    report = run_integrity_check()

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(report)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        out_path = REPORTS_DIR / f"integrity_report_{timestamp}.json"
        atomic_write_json(out_path, report)
        print(f"\n  Report saved: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
