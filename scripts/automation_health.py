#!/usr/bin/env python3
"""FQL Automation Health Monitor — Single-command integrity check.

Checks freshness and status of every automated component. Produces a
compact health summary for the Master Operating Brief.

Usage:
    python3 scripts/automation_health.py          # Full report
    python3 scripts/automation_health.py --brief   # Compact summary for brief
    python3 scripts/automation_health.py --json    # JSON output
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Freshness Thresholds ─────────────────────────────────────────────────────

# Each component has: where to check, max age before STALE, max age before FAILED
COMPONENTS = {
    "claw_heartbeat": {
        "description": "Claw discovery heartbeat (every 30 min)",
        "check": "claw_cron",
        "stale_minutes": 60,
        "failed_minutes": 120,
    },
    "claude_control_loop": {
        "description": "Claude directive refresh (every 30 min)",
        "check": "log_glob",
        "log_pattern": "research/logs/claw_loop_*.log",
        "stale_minutes": 60,
        "failed_minutes": 120,
    },
    "master_brief": {
        "description": "Master Operating Brief",
        "check": "file_mtime",
        "file_path": str(Path.home() / "openclaw-intake" / "inbox" / "_eod_audit.md"),
        "stale_minutes": 60,
        "failed_minutes": 240,
    },
    "daily_research": {
        "description": "Daily research pipeline (weekdays 17:30 ET)",
        "check": "log_glob",
        "log_pattern": "research/logs/daily_run_*.log",
        "stale_minutes": 1560,     # 26 hours (fires daily on weekdays)
        "failed_minutes": 2880,    # 48 hours
        "weekday_only": True,
    },
    "twice_weekly_research": {
        "description": "Twice-weekly batch testing (Tue/Thu 18:00 ET)",
        "check": "log_glob",
        "log_pattern": "research/logs/twice_weekly_run_*.log",
        "stale_minutes": 5760,     # 4 days
        "failed_minutes": 10080,   # 7 days
    },
    "weekly_research": {
        "description": "Weekly integrity/kill criteria (Fri 18:30 ET)",
        "check": "log_glob",
        "log_pattern": "research/logs/weekly_run_*.log",
        "stale_minutes": 10080,    # 7 days
        "failed_minutes": 20160,   # 14 days
    },
    "forward_runner": {
        "description": "Forward paper trading day",
        "check": "file_mtime",
        "file_path": str(ROOT / "state" / "account_state.json"),
        "stale_minutes": 2880,     # 48 hours (manual, weekdays)
        "failed_minutes": 5760,    # 4 days
    },
}


# ── Check Functions ──────────────────────────────────────────────────────────

def _check_claw_cron():
    """Check Claw heartbeat via openclaw cron runs."""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "runs",
             "--id", "85c3eb78-b228-4106-a71e-ff6011e5ac1d",
             "--limit", "1"],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(result.stdout)
        entries = data.get("entries", [])
        if not entries:
            return None, None, "no runs found"

        last = entries[0]
        ts_ms = last.get("runAtMs", 0)
        last_dt = datetime.fromtimestamp(ts_ms / 1000)
        status = last.get("status", "unknown")
        age_min = (datetime.now() - last_dt).total_seconds() / 60
        error = None if status == "ok" else f"status={status}"
        return last_dt, age_min, error
    except Exception as e:
        return None, None, str(e)


def _check_log_glob(pattern):
    """Check freshness of the most recent log matching a glob pattern."""
    log_dir = ROOT
    matches = sorted(log_dir.glob(pattern))
    if not matches:
        return None, None, "no log files found"

    latest = matches[-1]
    mtime = datetime.fromtimestamp(latest.stat().st_mtime)
    age_min = (datetime.now() - mtime).total_seconds() / 60

    # Check LAST exit line of the log for errors (not just any error string)
    error = None
    try:
        content = latest.read_text().strip()
        last_line = content.split("\n")[-1] if content else ""
        if "COMPLETED WITH ERRORS" in last_line or "FAILED" in last_line.upper():
            error = f"last run failed: {latest.name}"
    except Exception:
        pass

    return mtime, age_min, error


def _check_file_mtime(file_path):
    """Check freshness of a specific file."""
    p = Path(file_path)
    if not p.exists():
        return None, None, "file not found"

    mtime = datetime.fromtimestamp(p.stat().st_mtime)
    age_min = (datetime.now() - mtime).total_seconds() / 60
    return mtime, age_min, None


def _check_launchd_exit():
    """Check launchd exit codes for all FQL agents."""
    results = {}
    try:
        output = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True, timeout=5,
        )
        for line in output.stdout.strip().split("\n"):
            parts = line.split("\t")
            if len(parts) >= 3 and "com.fql." in parts[2]:
                label = parts[2]
                exit_code = parts[1] if parts[1] != "-" else "0"
                results[label] = int(exit_code) if exit_code.isdigit() else -1
    except Exception:
        pass
    return results


# ── Main Check ───────────────────────────────────────────────────────────────

def run_health_check():
    """Run all health checks and return structured results."""
    now = datetime.now()
    results = {}
    launchd_exits = _check_launchd_exit()

    for name, comp in COMPONENTS.items():
        check_type = comp["check"]
        last_run = None
        age_min = None
        error = None

        if check_type == "claw_cron":
            last_run, age_min, error = _check_claw_cron()
        elif check_type == "log_glob":
            last_run, age_min, error = _check_log_glob(comp["log_pattern"])
        elif check_type == "file_mtime":
            last_run, age_min, error = _check_file_mtime(comp["file_path"])

        # Determine status
        if error and ("not found" in str(error) or "no log" in str(error) or "no runs" in str(error)):
            status = "MISSING"
        elif error:
            status = "ERROR"
        elif age_min is None:
            status = "UNKNOWN"
        elif age_min > comp["failed_minutes"]:
            status = "FAILED"
        elif age_min > comp["stale_minutes"]:
            status = "STALE"
        else:
            status = "HEALTHY"

        results[name] = {
            "description": comp["description"],
            "status": status,
            "last_run": last_run.strftime("%Y-%m-%d %H:%M") if last_run else None,
            "age_minutes": round(age_min) if age_min else None,
            "age_human": _human_age(age_min) if age_min else "never",
            "error": error,
            "thresholds": {
                "stale": comp["stale_minutes"],
                "failed": comp["failed_minutes"],
            },
        }

    # Add launchd exit code check
    launchd_issues = []
    for label, exit_code in launchd_exits.items():
        if exit_code != 0:
            launchd_issues.append(f"{label}: exit code {exit_code}")

    results["_launchd"] = {
        "agents_loaded": len(launchd_exits),
        "all_healthy": len(launchd_issues) == 0,
        "issues": launchd_issues,
    }

    # Overall status
    statuses = [v["status"] for k, v in results.items() if k != "_launchd"]
    if "FAILED" in statuses or "ERROR" in statuses:
        results["_overall"] = "DEGRADED"
    elif "STALE" in statuses or "MISSING" in statuses:
        results["_overall"] = "WARNING"
    else:
        results["_overall"] = "HEALTHY"

    return results


def _human_age(minutes):
    """Convert minutes to human-readable age."""
    if minutes is None:
        return "never"
    if minutes < 60:
        return f"{int(minutes)}m ago"
    elif minutes < 1440:
        return f"{minutes/60:.1f}h ago"
    else:
        return f"{minutes/1440:.1f}d ago"


# ── Output ───────────────────────────────────────────────────────────────────

def print_full_report(results):
    """Print full health report."""
    W = 80
    print()
    print("=" * W)
    print("  FQL AUTOMATION HEALTH CHECK")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    overall = results.get("_overall", "UNKNOWN")
    icon = {"HEALTHY": "OK", "WARNING": "!!", "DEGRADED": "XX"}.get(overall, "??")
    print(f"\n  OVERALL: [{icon}] {overall}")

    print(f"\n  COMPONENT STATUS")
    print(f"  {'-' * (W-4)}")
    print(f"  {'Component':<30s} {'Status':<10s} {'Last Run':<14s} {'Age':<12s} {'Error'}")
    print(f"  {'-'*30} {'-'*10} {'-'*14} {'-'*12} {'-'*15}")

    for name, data in results.items():
        if name.startswith("_"):
            continue
        status = data["status"]
        marker = "  " if status == "HEALTHY" else "!!" if status in ("STALE", "WARNING") else "XX"
        last = data.get("last_run") or "—"
        age = data.get("age_human") or "—"
        error = data.get("error") or ""
        print(f"  {marker} {name:<28s} {status:<10s} {last:<14s} {age:<12s} {error}")

    # LaunchD
    ld = results.get("_launchd", {})
    print(f"\n  LAUNCHD AGENTS: {ld.get('agents_loaded', 0)} loaded, "
          f"{'all healthy' if ld.get('all_healthy') else 'ISSUES: ' + ', '.join(ld.get('issues', []))}")

    print(f"\n{'=' * W}")


def format_brief_section(results):
    """Format compact automation health section for Master Brief."""
    lines = []
    overall = results.get("_overall", "UNKNOWN")

    healthy = []
    problems = []

    for name, data in results.items():
        if name.startswith("_"):
            continue
        status = data["status"]
        age = data.get("age_human", "?")
        if status == "HEALTHY":
            healthy.append(f"{name} ({age})")
        else:
            error_detail = f": {data['error']}" if data.get("error") else ""
            problems.append(f"{name}: **{status}** ({age}){error_detail}")

    # LaunchD
    ld = results.get("_launchd", {})
    if not ld.get("all_healthy"):
        for issue in ld.get("issues", []):
            problems.append(f"launchd: **{issue}**")

    lines.append(f"- Overall: **{overall}**")
    if problems:
        for p in problems:
            lines.append(f"- {p}")
    lines.append(f"- Healthy: {', '.join(healthy) if healthy else 'none'}")

    return "\n".join(lines)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Automation Health Monitor")
    parser.add_argument("--brief", action="store_true", help="Compact summary for brief")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = run_health_check()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    elif args.brief:
        print(format_brief_section(results))
    else:
        print_full_report(results)


if __name__ == "__main__":
    main()
