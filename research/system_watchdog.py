#!/usr/bin/env python3
"""FQL System Watchdog — Minimum viable safety layer.

Consolidates health checks into a single pass that detects:
    1. Stale or missing data
    2. Scheduler job failures
    3. Corrupted state files
    4. Process health / hung jobs
    5. Critical drift alerts

Outputs a SAFE_MODE flag when critical failures are detected.
Does not over-build — this is the immune system, not the brain.

LIVE CONSUMER: scripts/run_fql_forward.sh runs
`python3 research/system_watchdog.py --safe-mode` as a pre-flight
gate before every forward-trading day. `--safe-mode` reads the cached
verdict in research/data/watchdog_state.json and exits 1 if
safe_mode=true, aborting forward trading.

SCHEDULING: this module is invoked daily by fql_research_scheduler
as `daily_system_watchdog` (priority 0, runs first). That refresh is
what keeps the cached state current for the next forward-day pre-flight.
If you remove this module from the scheduler, the pre-flight gate will
operate on stale state again.

Relationship to the other health layers:
    scripts/fql_watchdog.sh            — shell recovery layer, writes
                                         research/logs/.watchdog_state.json
                                         (per-component backoff state,
                                         different file, different purpose)
    research/fql_health_check.py       — 60-point daily health pass
                                         (daily_health_check in scheduler)
    research/system_watchdog.py (this) — 5-check pass + SAFE_MODE flag
                                         consumed by forward pre-flight

Usage:
    python3 research/system_watchdog.py              # Run all checks
    python3 research/system_watchdog.py --json       # JSON output
    python3 research/system_watchdog.py --safe-mode  # Check cached SAFE_MODE
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = ROOT / "research" / "data"
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "research" / "logs"
WATCHDOG_STATE_PATH = DATA_DIR / "watchdog_state.json"

CRITICAL_STATE_FILES = [
    DATA_DIR / "strategy_registry.json",
    DATA_DIR / "portfolio_activation_matrix.json",
    DATA_DIR / "scheduler_log.json",
]

# ── Check Results ────────────────────────────────────────────────────────────
# Each check returns: {"status": "OK"|"WARN"|"FAIL", "detail": str}

def check_data_freshness() -> dict:
    """Check if processed data files are recent enough."""
    processed = ROOT / "data" / "processed"
    if not processed.exists():
        return {"status": "FAIL", "detail": "data/processed/ directory missing"}

    now = datetime.now()
    stale_assets = []
    for csv in processed.glob("*_5m.csv"):
        age_hours = (now.timestamp() - csv.stat().st_mtime) / 3600
        if age_hours > 72:  # stale if >3 days old (weekends ok)
            stale_assets.append(f"{csv.stem} ({age_hours:.0f}h old)")

    if stale_assets:
        return {"status": "WARN", "detail": f"Stale data: {', '.join(stale_assets)}"}
    return {"status": "OK", "detail": "All data files recent"}


def check_scheduler_health() -> dict:
    """Check for recent scheduler failures."""
    log_path = DATA_DIR / "scheduler_log.json"
    if not log_path.exists():
        return {"status": "WARN", "detail": "No scheduler log found"}

    try:
        log = json.load(open(log_path))
    except (json.JSONDecodeError, IOError):
        return {"status": "FAIL", "detail": "Scheduler log corrupted"}

    if not log:
        return {"status": "WARN", "detail": "Scheduler log empty"}

    # Check last 7 days of entries
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    recent = [e for e in log if e.get("started", "") >= cutoff]
    errors = [e for e in recent if e.get("status") == "ERROR"]

    if len(errors) >= 5:
        return {"status": "FAIL", "detail": f"{len(errors)} errors in last 7 days"}
    if errors:
        jobs = [e.get("job", "?") for e in errors]
        return {"status": "WARN", "detail": f"{len(errors)} error(s): {', '.join(jobs)}"}

    # Check if scheduler has run recently
    last_run = max(e.get("started", "") for e in log) if log else ""
    if last_run:
        try:
            last_dt = datetime.fromisoformat(last_run)
            days_since = (datetime.now() - last_dt).days
            if days_since > 3:
                return {"status": "WARN", "detail": f"Last scheduler run was {days_since} days ago"}
        except ValueError:
            pass

    return {"status": "OK", "detail": f"{len(recent)} jobs in last 7 days, {len(errors)} errors"}


def check_state_integrity() -> dict:
    """Check critical state files for corruption."""
    issues = []
    for path in CRITICAL_STATE_FILES:
        if not path.exists():
            issues.append(f"{path.name}: missing")
            continue
        try:
            with open(path) as f:
                data = json.load(f)
            if not data:
                issues.append(f"{path.name}: empty")
        except json.JSONDecodeError:
            issues.append(f"{path.name}: corrupted JSON")
        except IOError as e:
            issues.append(f"{path.name}: read error ({e})")

    if any("corrupted" in i for i in issues):
        return {"status": "FAIL", "detail": "; ".join(issues)}
    if issues:
        return {"status": "WARN", "detail": "; ".join(issues)}
    return {"status": "OK", "detail": "All state files valid"}


def check_process_health() -> dict:
    """Check for hung or zombie FQL processes."""
    lockfile = LOGS_DIR / ".fql_daily.lock"
    if not lockfile.exists():
        return {"status": "OK", "detail": "No active lockfile"}

    try:
        pid = int(lockfile.read_text().strip())
    except (ValueError, IOError):
        return {"status": "WARN", "detail": "Lockfile exists but unreadable"}

    # Check if process is still running
    try:
        os.kill(pid, 0)
        # Process exists — check how long it's been running
        lock_age_hours = (datetime.now().timestamp() - lockfile.stat().st_mtime) / 3600
        if lock_age_hours > 2:
            return {"status": "FAIL", "detail": f"Process {pid} running for {lock_age_hours:.1f}h (possible hang)"}
        return {"status": "OK", "detail": f"Process {pid} running ({lock_age_hours:.1f}h)"}
    except ProcessLookupError:
        return {"status": "WARN", "detail": f"Stale lockfile (PID {pid} dead)"}


def check_drift_alerts() -> dict:
    """Check for critical drift alerts."""
    drift_path = DATA_DIR / "live_drift_log.json"
    if not drift_path.exists():
        return {"status": "OK", "detail": "No drift log (not yet generated)"}

    try:
        log = json.load(open(drift_path))
    except (json.JSONDecodeError, IOError):
        return {"status": "WARN", "detail": "Drift log unreadable"}

    if not log:
        return {"status": "OK", "detail": "Drift log empty"}

    latest = log[-1] if log else {}
    alarms = []
    for sid, sdata in latest.get("strategies", {}).items():
        for sess, info in sdata.get("sessions", {}).items():
            if info.get("severity") == "ALARM":
                alarms.append(f"{sid}/{sess}")

    if len(alarms) >= 4:
        return {"status": "FAIL", "detail": f"{len(alarms)} ALARM drift alerts: {', '.join(alarms[:5])}"}
    if alarms:
        return {"status": "WARN", "detail": f"{len(alarms)} ALARM(s): {', '.join(alarms)}"}
    return {"status": "OK", "detail": "No ALARM-level drift"}


# ── Watchdog Runner ──────────────────────────────────────────────────────────

CHECKS = [
    ("data_freshness", check_data_freshness),
    ("scheduler_health", check_scheduler_health),
    ("state_integrity", check_state_integrity),
    ("process_health", check_process_health),
    ("drift_alerts", check_drift_alerts),
]


def run_watchdog() -> dict:
    """Run all watchdog checks and determine system status."""
    results = {}
    for name, check_fn in CHECKS:
        try:
            results[name] = check_fn()
        except Exception as e:
            results[name] = {"status": "FAIL", "detail": f"Check crashed: {e}"}

    # Determine overall status
    statuses = [r["status"] for r in results.values()]
    if "FAIL" in statuses:
        fail_count = statuses.count("FAIL")
        overall = "CRITICAL" if fail_count >= 2 else "DEGRADED"
        safe_mode = fail_count >= 2
    elif "WARN" in statuses:
        overall = "HEALTHY"
        safe_mode = False
    else:
        overall = "HEALTHY"
        safe_mode = False

    report = {
        "timestamp": datetime.now().isoformat(),
        "overall": overall,
        "safe_mode": safe_mode,
        "checks": results,
    }

    # Save watchdog state
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(WATCHDOG_STATE_PATH, report)

    return report


def print_report(report: dict):
    """Print formatted watchdog report."""
    W = 60
    print()
    print("=" * W)
    print(f"  FQL SYSTEM WATCHDOG — {report['timestamp'][:19]}")
    print("=" * W)
    print()

    safe_str = "!! SAFE_MODE ACTIVE !!" if report["safe_mode"] else "Normal operation"
    print(f"  Overall: {report['overall']}  |  {safe_str}")
    print(f"  {'-' * (W - 4)}")

    for name, result in report["checks"].items():
        status = result["status"]
        icon = {"OK": " ", "WARN": "!", "FAIL": "X"}[status]
        label = name.replace("_", " ").title()
        print(f"  [{icon}] {label:<25s} {status:<6s} {result['detail']}")

    print()
    print("=" * W)


def main():
    parser = argparse.ArgumentParser(description="FQL System Watchdog")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--safe-mode", action="store_true", help="Check SAFE_MODE status only")
    args = parser.parse_args()

    if args.safe_mode:
        if WATCHDOG_STATE_PATH.exists():
            state = json.load(open(WATCHDOG_STATE_PATH))
            if state.get("safe_mode"):
                print("SAFE_MODE: ACTIVE")
                sys.exit(1)
            else:
                print("SAFE_MODE: inactive")
                sys.exit(0)
        else:
            print("SAFE_MODE: unknown (no watchdog state)")
            sys.exit(0)

    report = run_watchdog()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    sys.exit(1 if report["safe_mode"] else 0)


if __name__ == "__main__":
    main()
