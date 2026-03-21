#!/usr/bin/env python3
"""FQL Doctor — holistic system health check and repair.

One entry point that inspects every component of the FQL platform and
reports a single verdict: HEALTHY / DEGRADED / BROKEN.

Usage:
    python3 scripts/fql_doctor.py              # Read-only audit
    python3 scripts/fql_doctor.py --repair     # Audit + fix common issues
    python3 scripts/fql_doctor.py --json       # Machine-readable output
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = Path.home() / "openclaw-intake" / "inbox"
OUTPUT = INBOX / "_system_health.md"

NOW = datetime.now()
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M:%S")
TODAY = NOW.strftime("%Y-%m-%d")
UID = os.getuid()


# ── Check infrastructure ──────────────────────────────────────────────────

def _age_minutes(path):
    try:
        return (time.time() - Path(path).stat().st_mtime) / 60
    except Exception:
        return 99999


def _age_hours(path):
    return _age_minutes(path) / 60


def _launchd_status(label):
    """Check if a launchd job is loaded and get its PID."""
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split("\n"):
            if label in line:
                parts = line.split()
                pid = parts[0] if parts[0] != "-" else None
                return {"loaded": True, "pid": pid, "exit": parts[1]}
        return {"loaded": False, "pid": None, "exit": None}
    except Exception:
        return {"loaded": False, "pid": None, "exit": None}


def _kickstart(label):
    """Kickstart a launchd agent."""
    try:
        subprocess.run(
            ["launchctl", "kickstart", "-k", f"gui/{UID}/{label}"],
            capture_output=True, timeout=10
        )
        return True
    except Exception:
        return False


def _run_script(cmd, timeout=30):
    """Run a script and return success."""
    try:
        subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=str(ROOT))
        return True
    except Exception:
        return False


# ── Individual checks ─────────────────────────────────────────────────────

def check_gateway():
    status = _launchd_status("ai.openclaw.gateway")
    health_ok = False
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "3", "http://localhost:18789/health"],
            capture_output=True, text=True, timeout=5
        )
        health_ok = '"ok":true' in result.stdout
    except Exception:
        pass

    if status["loaded"] and health_ok:
        return {"name": "Gateway", "status": "HEALTHY", "detail": f"PID {status['pid']}, health OK"}
    elif status["loaded"] and not health_ok:
        return {"name": "Gateway", "status": "DEGRADED", "detail": "Loaded but health check failed",
                "repair": "kickstart:ai.openclaw.gateway"}
    else:
        return {"name": "Gateway", "status": "BROKEN", "detail": "Not loaded",
                "repair": "kickstart:ai.openclaw.gateway"}


def check_watchdog():
    status = _launchd_status("com.fql.watchdog")
    log_dir = ROOT / "research" / "logs"
    log_file = log_dir / f"watchdog_{NOW.strftime('%Y%m%d')}.log"
    age = _age_minutes(log_file) if log_file.exists() else 99999

    if status["loaded"] and age < 10:
        return {"name": "Watchdog", "status": "HEALTHY", "detail": f"Last run {age:.0f}m ago"}
    elif status["loaded"] and age < 30:
        return {"name": "Watchdog", "status": "HEALTHY", "detail": f"Last run {age:.0f}m ago (within 5m cycle)"}
    elif status["loaded"]:
        return {"name": "Watchdog", "status": "DEGRADED", "detail": f"Last run {age:.0f}m ago",
                "repair": "kickstart:com.fql.watchdog"}
    else:
        return {"name": "Watchdog", "status": "BROKEN", "detail": "Not loaded",
                "repair": "kickstart:com.fql.watchdog"}


def check_claw_loop():
    status = _launchd_status("com.fql.claw-control-loop")
    log_dir = ROOT / "research" / "logs"
    claw_logs = sorted(log_dir.glob("claw_loop_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    age = _age_minutes(claw_logs[0]) if claw_logs else 99999

    if status["loaded"] and age < 45:
        return {"name": "Claw loop", "status": "HEALTHY", "detail": f"Last run {age:.0f}m ago"}
    elif status["loaded"] and age < 120:
        return {"name": "Claw loop", "status": "DEGRADED", "detail": f"Last run {age:.0f}m ago (stale)",
                "repair": "kickstart:com.fql.claw-control-loop"}
    elif status["loaded"]:
        return {"name": "Claw loop", "status": "BROKEN", "detail": f"Last run {age:.0f}m ago",
                "repair": "kickstart:com.fql.claw-control-loop"}
    else:
        return {"name": "Claw loop", "status": "BROKEN", "detail": "Not loaded",
                "repair": "kickstart:com.fql.claw-control-loop"}


def check_daily_pipeline():
    log_dir = ROOT / "research" / "logs"
    today_log = list(log_dir.glob(f"daily_run_{NOW.strftime('%Y%m%d')}*.log"))
    status = _launchd_status("com.fql.daily-research")

    if not status["loaded"]:
        return {"name": "Daily pipeline", "status": "BROKEN", "detail": "Not loaded"}

    # Only check if past 18:00
    if NOW.hour < 18:
        return {"name": "Daily pipeline", "status": "HEALTHY", "detail": "Not yet due today"}
    elif today_log:
        return {"name": "Daily pipeline", "status": "HEALTHY", "detail": f"Ran today ({today_log[0].name})"}
    else:
        return {"name": "Daily pipeline", "status": "DEGRADED", "detail": "Past 18:00, no log today",
                "repair": "kickstart:com.fql.daily-research"}


def check_source_helpers():
    manifest = INBOX / "source_leads" / "_manifest.json"
    if not manifest.exists():
        return {"name": "Source helpers", "status": "DEGRADED", "detail": "No manifest — helpers may not have run"}

    try:
        data = json.load(open(manifest))
        runs = data.get("runs", [])
        if not runs:
            return {"name": "Source helpers", "status": "DEGRADED", "detail": "No runs recorded"}

        last = runs[-1]
        total = last.get("total", 0)
        ts = last.get("timestamp", "")[:10]
        age_days = (NOW - datetime.strptime(ts, "%Y-%m-%d")).days if ts else 999

        if age_days <= 8 and total > 0:
            return {"name": "Source helpers", "status": "HEALTHY",
                    "detail": f"Last run {ts}: {total} leads ({age_days}d ago)"}
        elif age_days <= 14:
            return {"name": "Source helpers", "status": "DEGRADED",
                    "detail": f"Last run {age_days}d ago — may have missed Sunday cycle",
                    "repair": "run:scripts/run_source_helpers.sh"}
        else:
            return {"name": "Source helpers", "status": "BROKEN",
                    "detail": f"Last run {age_days}d ago",
                    "repair": "run:scripts/run_source_helpers.sh"}
    except Exception as e:
        return {"name": "Source helpers", "status": "DEGRADED", "detail": f"Manifest error: {e}"}


def check_reports():
    reports = {
        "_operator_brief.md": 26,       # hours — should refresh daily
        "_recovery_status.md": 0.5,      # hours — every 5 min
        "_eod_audit.md": 2,              # hours — every 30 min
        "_probation_scoreboard.md": 26,  # hours — daily
        "_alerts.md": 26,               # hours — daily
    }
    issues = []
    for name, max_hours in reports.items():
        path = INBOX / name
        if not path.exists():
            issues.append(f"{name}: MISSING")
        else:
            age = _age_hours(path)
            if age > max_hours * 2:
                issues.append(f"{name}: {age:.1f}h old (expected <{max_hours}h)")

    if not issues:
        return {"name": "Reports", "status": "HEALTHY", "detail": "All reports fresh"}
    elif len(issues) <= 2:
        return {"name": "Reports", "status": "DEGRADED", "detail": "; ".join(issues),
                "repair": "run:scripts/operator_brief.py --save"}
    else:
        return {"name": "Reports", "status": "BROKEN", "detail": "; ".join(issues),
                "repair": "run:scripts/operator_brief.py --save"}


def check_alerts():
    alerts_path = INBOX / "_alerts.md"
    if not alerts_path.exists():
        return {"name": "Alerts", "status": "HEALTHY", "detail": "No alerts file (may not have run yet)"}

    try:
        text = alerts_path.read_text()
        alert_count = text.count("[ALERT]")
        action_count = text.count("[ACTION]")
        warn_count = text.count("[WARN]")

        if alert_count > 0:
            return {"name": "Alerts", "status": "DEGRADED",
                    "detail": f"{alert_count} ALERT, {action_count} ACTION, {warn_count} WARN"}
        elif action_count > 0:
            return {"name": "Alerts", "status": "HEALTHY",
                    "detail": f"{action_count} ACTION, {warn_count} WARN — decisions needed"}
        elif warn_count > 0:
            return {"name": "Alerts", "status": "HEALTHY",
                    "detail": f"{warn_count} WARN — see _alerts.md"}
        else:
            return {"name": "Alerts", "status": "HEALTHY", "detail": "No active alerts"}
    except Exception:
        return {"name": "Alerts", "status": "HEALTHY", "detail": "Could not read alerts"}


def check_recovery():
    log = ROOT / "research" / "logs" / "recovery_actions.log"
    if not log.exists():
        return {"name": "Recovery", "status": "HEALTHY", "detail": "No recovery actions recorded"}

    today_count = 0
    try:
        for line in open(log):
            if TODAY in line:
                today_count += 1
    except Exception:
        pass

    if today_count >= 5:
        return {"name": "Recovery", "status": "DEGRADED",
                "detail": f"{today_count} recovery actions today — possible instability"}
    elif today_count > 0:
        return {"name": "Recovery", "status": "HEALTHY",
                "detail": f"{today_count} recovery action(s) today — self-healing worked"}
    else:
        return {"name": "Recovery", "status": "HEALTHY", "detail": "0 recovery actions today"}


# ── Main ──────────────────────────────────────────────────────────────────

def run_doctor(repair=False):
    checks = [
        check_gateway(),
        check_watchdog(),
        check_claw_loop(),
        check_daily_pipeline(),
        check_source_helpers(),
        check_reports(),
        check_alerts(),
        check_recovery(),
    ]

    # Overall verdict
    statuses = [c["status"] for c in checks]
    if "BROKEN" in statuses:
        overall = "BROKEN"
    elif "DEGRADED" in statuses:
        overall = "DEGRADED"
    else:
        overall = "HEALTHY"

    # Repair if requested
    repairs_done = []
    repairs_failed = []

    if repair:
        for c in checks:
            if c.get("repair") and c["status"] in ("DEGRADED", "BROKEN"):
                action = c["repair"]
                if action.startswith("kickstart:"):
                    label = action.split(":", 1)[1]
                    if _kickstart(label):
                        repairs_done.append(f"Kickstarted {label}")
                    else:
                        repairs_failed.append(f"Failed to kickstart {label}")
                elif action.startswith("run:"):
                    script = action.split(":", 1)[1]
                    parts = script.split()
                    cmd = ["python3" if parts[0].endswith(".py") else "bash"] + parts
                    if _run_script(cmd):
                        repairs_done.append(f"Ran {script}")
                    else:
                        repairs_failed.append(f"Failed to run {script}")

        # Re-check after repairs
        if repairs_done:
            time.sleep(3)
            checks = [
                check_gateway(),
                check_watchdog(),
                check_claw_loop(),
                check_daily_pipeline(),
                check_source_helpers(),
                check_reports(),
                check_alerts(),
                check_recovery(),
            ]
            statuses = [c["status"] for c in checks]
            if "BROKEN" in statuses:
                overall = "BROKEN"
            elif "DEGRADED" in statuses:
                overall = "DEGRADED"
            else:
                overall = "HEALTHY"

    return {
        "timestamp": TIMESTAMP,
        "overall": overall,
        "checks": checks,
        "repairs_done": repairs_done,
        "repairs_failed": repairs_failed,
    }


def format_report(result):
    lines = []
    lines.append("# FQL System Health")
    lines.append(f"*{result['timestamp']}*")
    lines.append("")

    # Overall verdict with visual indicator
    overall = result["overall"]
    indicator = {"HEALTHY": "ALL CLEAR", "DEGRADED": "NEEDS ATTENTION", "BROKEN": "ACTION REQUIRED"}
    lines.append(f"## Overall: {overall} — {indicator.get(overall, '')}")
    lines.append("")

    # Component table
    lines.append("| Component | Status | Detail |")
    lines.append("|-----------|--------|--------|")
    for c in result["checks"]:
        lines.append(f"| {c['name']} | {c['status']} | {c['detail']} |")

    # Repairs
    if result["repairs_done"]:
        lines.append("")
        lines.append("## Repairs Applied")
        for r in result["repairs_done"]:
            lines.append(f"- {r}")

    if result["repairs_failed"]:
        lines.append("")
        lines.append("## Repairs Failed")
        for r in result["repairs_failed"]:
            lines.append(f"- {r}")

    # Suggested actions for remaining issues
    remaining = [c for c in result["checks"] if c["status"] in ("DEGRADED", "BROKEN") and c.get("repair")]
    if remaining and not result.get("repairs_done"):
        lines.append("")
        lines.append("## Suggested Fixes")
        lines.append("Run `python3 scripts/fql_doctor.py --repair` or manually:")
        for c in remaining:
            action = c["repair"]
            if action.startswith("kickstart:"):
                label = action.split(":", 1)[1]
                lines.append(f"- `launchctl kickstart -k gui/{UID}/{label}`")
            elif action.startswith("run:"):
                script = action.split(":", 1)[1]
                lines.append(f"- `{script}`")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Doctor — system health check and repair")
    parser.add_argument("--repair", action="store_true", help="Attempt to fix common issues")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--save", action="store_true", help="Save to inbox (default in non-json mode)")
    args = parser.parse_args()

    result = run_doctor(repair=args.repair)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        report = format_report(result)
        print(report)

        # Always save unless --json
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT, "w") as f:
            f.write(report)


if __name__ == "__main__":
    main()
