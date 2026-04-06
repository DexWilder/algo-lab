#!/usr/bin/env python3
"""FQL Throughput Audit — surface dormant inventory at every pipeline stage.

Scans the entire factory for work that should be advancing but isn't.
Designed to prevent the "62 coded strategies never tested" blind spot.

Audit buckets:
  1. Coded but never backtested
  2. Harvested but never converted to strategy code
  3. Converted but never first-passed
  4. Validated components never tested on parents
  5. Blocked items whose dependency may now be cleared
  6. Strategies with review status but no next trigger
  7. Automation jobs built but not actually firing
  8. Reports generated but not connected to a decision/action

Usage:
    python3 scripts/throughput_audit.py              # Full audit
    python3 scripts/throughput_audit.py --save       # Audit + save to inbox
"""

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

INBOX = Path.home() / "openclaw-intake" / "inbox"
HARVEST_DIR = INBOX / "harvest"
REVIEWED_DIR = Path.home() / "openclaw-intake" / "reviewed"
STRAT_DIR = ROOT / "strategies"
FIRST_PASS_DIR = ROOT / "research" / "data" / "first_pass"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = INBOX / "_throughput_audit.md"
LOG_DIR = ROOT / "research" / "logs"

NOW = datetime.now()
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")


def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


# ── Bucket 1: Coded but never backtested ─────────────────────────────────

def audit_coded_untested():
    """Strategies with strategy.py but no first_pass result."""
    has_first_pass = set()
    for f in FIRST_PASS_DIR.glob("*.json"):
        name = f.stem.split("_2026")[0].split("_2025")[0].split("_2024")[0]
        has_first_pass.add(name)

    untested = []
    for d in sorted(STRAT_DIR.iterdir()):
        if d.is_dir() and (d / "strategy.py").exists():
            if d.name not in has_first_pass:
                age_days = (time.time() - (d / "strategy.py").stat().st_mtime) / 86400
                untested.append({"name": d.name, "age_days": int(age_days)})

    return {
        "bucket": "Coded but never backtested",
        "count": len(untested),
        "items": untested,
        "unlock": untested[0]["name"] if untested else None,
        "action": "Run: python3 research/mass_screen.py",
    }


# ── Bucket 2: Harvested but never converted ──────────────────────────────

def audit_harvested_unconverted():
    """Harvest notes that haven't been turned into strategy code or registry entries."""
    reg = _load_json(str(REGISTRY_PATH))
    registry_ids = {s.get("strategy_id", "").lower() for s in reg.get("strategies", [])}

    unconverted = []
    for d in [HARVEST_DIR, REVIEWED_DIR]:
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            try:
                text = f.read_text()
                # Check if this note has been picked up (has a strategy_id match)
                name_line = ""
                for line in text.split("\n"):
                    if line.startswith("# ") or line.startswith("- strategy_name:"):
                        name_line = line.lower()
                        break

                # Simple heuristic: if no registry entry references this note's name
                matched = any(n_part in sid for sid in registry_ids
                             for n_part in name_line.split() if len(n_part) > 4)

                if not matched:
                    age_days = (time.time() - f.stat().st_mtime) / 86400
                    unconverted.append({"file": f.name, "age_days": int(age_days)})
            except Exception:
                pass

    # Sort oldest first
    unconverted.sort(key=lambda x: -x["age_days"])

    return {
        "bucket": "Harvested but never converted",
        "count": len(unconverted),
        "items": unconverted[:10],  # Top 10 oldest
        "unlock": unconverted[0]["file"] if unconverted else None,
        "action": "Review oldest harvest notes for conversion or explicit rejection",
    }


# ── Bucket 3: Registry ideas never first-passed ─────────────────────────

def audit_ideas_untested():
    """Registry entries at 'idea' status with no test data."""
    reg = _load_json(str(REGISTRY_PATH))
    untested = []
    for s in reg.get("strategies", []):
        if s.get("status") == "idea" and not s.get("profit_factor") and not s.get("trades_6yr"):
            untested.append({
                "id": s["strategy_id"],
                "family": s.get("family", "?"),
                "asset": s.get("asset", "?"),
            })

    return {
        "bucket": "Registry ideas never tested",
        "count": len(untested),
        "items": untested[:10],
        "unlock": untested[0]["id"] if untested else None,
        "action": "Convert to strategy code and run through mass_screen",
    }


# ── Bucket 4: Validated components never tested on parents ───────────────

def audit_untested_components():
    """Components with validation history but no parent integration test."""
    reg = _load_json(str(REGISTRY_PATH))
    untested = []
    for s in reg.get("strategies", []):
        cvh = s.get("component_validation_history", [])
        validated = [c for c in cvh if c.get("result") == "validated"]
        if validated:
            # Check if any validated component has been tested as integration
            integrated = [c for c in cvh if c.get("test_type") == "integration"]
            if not integrated:
                untested.append({
                    "id": s["strategy_id"],
                    "validated_components": len(validated),
                })

    return {
        "bucket": "Validated components never integrated",
        "count": len(untested),
        "items": untested,
        "unlock": untested[0]["id"] if untested else None,
        "action": "Test validated components on parent strategies",
    }


# ── Bucket 5: Blocked items with cleared dependencies ────────────────────

def audit_blocked_items():
    """Registry entries marked blocked whose dependency may be resolved."""
    reg = _load_json(str(REGISTRY_PATH))
    potentially_cleared = []

    for s in reg.get("strategies", []):
        notes = (s.get("notes", "") + " " + s.get("salvage_notes", "")).lower()
        status = s.get("status", "")

        # Check for blocked/gated language
        if any(word in notes for word in ["blocked", "gated on", "waiting for", "depends on"]):
            potentially_cleared.append({
                "id": s["strategy_id"],
                "status": status,
                "notes": s.get("notes", "")[:100],
            })

    # Also check watchdog for recently cleared components
    ws = _load_json(str(ROOT / "research" / "logs" / ".watchdog_state.json"))
    recently_cleared = []
    if Path(ROOT / "research" / "logs" / "recovery_actions.log").exists():
        try:
            cutoff = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")
            for line in open(ROOT / "research" / "logs" / "recovery_actions.log"):
                if "CLEARED" in line and line[:10] >= cutoff:
                    recently_cleared.append(line.strip()[:80])
        except Exception:
            pass

    return {
        "bucket": "Potentially unblocked items",
        "count": len(potentially_cleared),
        "items": potentially_cleared,
        "recently_cleared": recently_cleared,
        "unlock": potentially_cleared[0]["id"] if potentially_cleared else None,
        "action": "Review blocked items against recently cleared dependencies",
    }


# ── Bucket 6: Stale review status ────────────────────────────────────────

def audit_stale_reviews():
    """Strategies at monitor/watch/testing with no defined next trigger."""
    reg = _load_json(str(REGISTRY_PATH))
    stale = []
    for s in reg.get("strategies", []):
        status = s.get("status", "")
        if status in ("monitor", "watch", "testing"):
            has_trigger = bool(s.get("salvage_lane") or s.get("review_date") or
                             s.get("next_action") or s.get("test_date"))
            stale.append({
                "id": s["strategy_id"],
                "status": status,
                "has_trigger": has_trigger,
                "pf": s.get("profit_factor"),
            })

    no_trigger = [s for s in stale if not s["has_trigger"]]

    return {
        "bucket": "Review status with no next trigger",
        "count": len(no_trigger),
        "total_in_review": len(stale),
        "items": no_trigger,
        "unlock": no_trigger[0]["id"] if no_trigger else None,
        "action": "Define next trigger or advance/reject each item",
    }


# ── Bucket 7: Automation jobs not firing ─────────────────────────────────

def audit_automation_health():
    """Launchd agents that are loaded but haven't produced output."""
    issues = []

    checks = {
        "com.fql.daily-research": ("daily_run_*.log", 26),  # hours
        "com.fql.weekly-research": ("weekly_run_*.log", 8 * 24),
        "com.fql.twice-weekly-research": ("twice_weekly_run_*.log", 4 * 24),
        "com.fql.operator-digest": ("digest_*.log", 26),
        "com.fql.source-helpers": ("source_helpers_*.log", 4 * 24),
        "com.fql.watchdog": ("watchdog_*.log", 1),
        "com.fql.claw-control-loop": ("claw_loop_*.log", 2),
        "com.fql.forward-day": ("forward_day_*.log", 26),
    }

    for label, (pattern, max_hours) in checks.items():
        # Check if loaded
        try:
            result = subprocess.run(
                ["launchctl", "list"], capture_output=True, text=True, timeout=5
            )
            loaded = label in result.stdout
        except Exception:
            loaded = False

        # Check last output
        logs = sorted(LOG_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        if logs:
            age_hours = (time.time() - logs[0].stat().st_mtime) / 3600
            fresh = age_hours <= max_hours
        else:
            age_hours = 9999
            fresh = False

        if not loaded or not fresh:
            issues.append({
                "agent": label,
                "loaded": loaded,
                "last_output_hours": round(age_hours, 1) if age_hours < 9999 else None,
                "expected_max_hours": max_hours,
            })

    return {
        "bucket": "Automation jobs not firing",
        "count": len(issues),
        "items": issues,
        "unlock": issues[0]["agent"] if issues else None,
        "action": "fql restart or launchctl load for missing agents",
    }


# ── Bucket 8: Disconnected reports ───────────────────────────────────────

def audit_disconnected_reports():
    """Reports that exist but aren't consumed by the digest or any decision flow."""
    # Reports in inbox
    report_files = list(INBOX.glob("_*.md"))
    connected = {
        "_daily_digest.md", "_operator_brief.md", "_alerts.md",
        "_system_health.md", "_probation_scoreboard.md",
        "_challenger_stack_review.md", "_rates_challenger_review.md",
        "_portfolio_gap_dashboard.md", "_harvest_quality_review.md",
        "_harvest_coverage_audit.md", "_convergence_report.md",
        "_recovery_status.md", "_throughput_audit.md",
    }

    disconnected = []
    for f in report_files:
        if f.name not in connected:
            age_days = (time.time() - f.stat().st_mtime) / 86400
            disconnected.append({"file": f.name, "age_days": int(age_days)})

    return {
        "bucket": "Reports not connected to decisions",
        "count": len(disconnected),
        "items": disconnected,
        "unlock": None,
        "action": "Connect to digest or remove if obsolete",
    }


# ── Report generation ────────────────────────────────────────────────────

def generate_audit():
    audits = [
        audit_coded_untested(),
        audit_ideas_untested(),
        audit_harvested_unconverted(),
        audit_untested_components(),
        audit_blocked_items(),
        audit_stale_reviews(),
        audit_automation_health(),
        audit_disconnected_reports(),
    ]

    lines = []
    lines.append("# FQL Throughput Audit")
    lines.append(f"*{TIMESTAMP}*")
    lines.append("")

    # Summary
    total_dormant = sum(a["count"] for a in audits)
    lines.append(f"**Total dormant items: {total_dormant}**")
    lines.append("")
    lines.append("| # | Bucket | Count | Immediate Unlock |")
    lines.append("|---|--------|-------|------------------|")
    for i, a in enumerate(audits, 1):
        unlock = a.get("unlock", "—") or "—"
        lines.append(f"| {i} | {a['bucket']} | {a['count']} | {unlock} |")
    lines.append("")

    # Recommended execution order
    actionable = [(a, i) for i, a in enumerate(audits) if a["count"] > 0]
    actionable.sort(key=lambda x: -x[0]["count"])

    if actionable:
        lines.append("## Recommended Execution Order")
        lines.append("")
        for rank, (a, _) in enumerate(actionable, 1):
            lines.append(f"**{rank}. {a['bucket']}** ({a['count']} items)")
            lines.append(f"   Action: {a['action']}")
            if a.get("unlock"):
                lines.append(f"   Highest-value unlock: {a['unlock']}")
            lines.append("")

    # Detail sections
    for a in audits:
        if a["count"] == 0:
            continue
        lines.append(f"## {a['bucket']} ({a['count']})")
        lines.append("")
        for item in a.get("items", [])[:15]:
            if isinstance(item, dict):
                parts = [f"{k}={v}" for k, v in item.items() if v is not None]
                lines.append(f"  - {', '.join(parts)}")
            else:
                lines.append(f"  - {item}")

        rc = a.get("recently_cleared", [])
        if rc:
            lines.append("")
            lines.append("  Recently cleared dependencies:")
            for r in rc:
                lines.append(f"    {r}")
        lines.append("")

    return "\n".join(lines), audits


def main():
    parser = argparse.ArgumentParser(description="FQL Throughput Audit")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    report, audits = generate_audit()
    print(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
