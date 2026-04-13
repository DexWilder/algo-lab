#!/usr/bin/env python3
"""FQL Doctrine Integrity Check — verifies the full operating stack is wired and active.

Two modes:
  --daily   Lightweight assertion check (runs in daily pipeline, exception-only)
  --weekly  Full doctrine verification (runs in weekly pipeline, comprehensive)

Daily checks: agents loaded, reports fresh, registry basic integrity, forward
runner matches portfolio. Only outputs when something fails.

Weekly checks: everything daily checks PLUS docs exist, metadata completeness,
crossbreeding layer, doctrine memory, config-to-automation alignment.

Usage:
    python3 scripts/doctrine_integrity_check.py --daily     # In daily pipeline
    python3 scripts/doctrine_integrity_check.py --weekly    # In weekly pipeline
    python3 scripts/doctrine_integrity_check.py --save      # Save report to inbox
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
sys.path.insert(0, str(ROOT))

INBOX = Path.home() / "openclaw-intake" / "inbox"
OUTPUT_PATH = INBOX / "_doctrine_integrity.md"

NOW = datetime.now()
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")
IS_WEEKDAY = NOW.weekday() < 5
IS_WEEKEND = not IS_WEEKDAY


def _age_hours(path):
    try:
        return (time.time() - Path(path).stat().st_mtime) / 3600
    except Exception:
        return 9999


def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


# ── DAILY ASSERTIONS (lightweight, exception-only) ───────────────────────

def daily_assertions():
    """Quick integrity checks that run every day. Returns list of failures."""
    failures = []

    # 1. Required launchd agents loaded
    try:
        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
        agents_output = result.stdout
    except Exception:
        agents_output = ""

    required_agents = [
        "com.fql.watchdog",
        "com.fql.daily-research",
        "com.fql.forward-day",
        "com.fql.operator-digest",
        "com.fql.claw-control-loop",
        "com.fql.weekly-research",
        "com.fql.twice-weekly-research",
    ]
    for agent in required_agents:
        if agent not in agents_output:
            failures.append(f"AGENT MISSING: {agent} not loaded in launchctl")

    # 2. Forward runner config matches active workhorses
    from engine.strategy_universe import build_portfolio_config
    cfg = build_portfolio_config(include_probation=True)
    reg = _load_json(str(ROOT / "research" / "data" / "strategy_registry.json"))
    xb_probation = [s for s in reg.get("strategies", [])
                    if s.get("status") == "probation" and "XB-ORB" in s.get("strategy_id", "")]
    for s in xb_probation:
        sid = s["strategy_id"]
        if sid not in cfg.get("strategies", {}):
            failures.append(f"RUNNER MISMATCH: {sid} is probation but not in forward portfolio")

    # 3. Registry basic integrity
    strategies = reg.get("strategies", [])
    valid_states = {"idea", "testing", "watch", "monitor", "probation", "core",
                    "rejected", "archived", "broken"}
    for s in strategies:
        status = s.get("status", "")
        if status not in valid_states:
            failures.append(f"INVALID STATUS: {s['strategy_id']} has status '{status}'")

    for s in strategies:
        if s.get("status") == "probation" and not s.get("controller_action"):
            failures.append(f"NO CONTROLLER: {s['strategy_id']} is probation without controller_action")

    # 4. No coded-untested (should be 0 between twice-weekly mass-screens)
    strat_dir = ROOT / "strategies"
    fp_dir = ROOT / "research" / "data" / "first_pass"
    fp_names = set()
    for f in fp_dir.glob("*.json"):
        name = f.stem
        for sep in ["_2026", "_2025", "_2024"]:
            if sep in name:
                name = name.split(sep)[0]
                break
        fp_names.add(name)
    for d in strat_dir.iterdir():
        if d.is_dir() and (d / "strategy.py").exists() and d.name not in fp_names:
            try:
                if "\nBROKEN = True" in (d / "strategy.py").read_text():
                    continue
            except Exception:
                pass
            failures.append(f"CODED UNTESTED: {d.name} has strategy code but no first_pass")

    # 5. Reports freshness (only on weekdays, allow 30h for weekend recovery)
    if IS_WEEKDAY:
        required_reports = {
            "_alerts.md": 30,
            "_daily_digest.md": 30,
        }
        for name, max_hours in required_reports.items():
            path = INBOX / name
            if path.exists():
                age = _age_hours(path)
                if age > max_hours:
                    failures.append(f"STALE REPORT: {name} is {age:.0f}h old (max {max_hours}h)")
            # Don't fail on missing — new reports may not exist yet

    return failures


# ── WEEKLY FULL DOCTRINE CHECK ───────────────────────────────────────────

def weekly_doctrine_check():
    """Comprehensive doctrine verification. Returns (passes, failures) lists."""
    passes = []
    failures = []

    # Run all daily assertions first
    daily_fails = daily_assertions()
    if daily_fails:
        for f in daily_fails:
            failures.append(f)
    else:
        passes.append("Daily assertions: all pass")

    reg = _load_json(str(ROOT / "research" / "data" / "strategy_registry.json"))
    strategies = reg.get("strategies", [])

    # 6. All strategies have created_date
    no_date = [s for s in strategies if not s.get("created_date")]
    if no_date:
        failures.append(f"MISSING DATES: {len(no_date)} strategies without created_date")
    else:
        passes.append(f"All {len(strategies)} strategies have created_date")

    # 7. Reusability tags complete
    no_reuse = [s for s in strategies if s.get("reusable_as_component") is None]
    if no_reuse:
        failures.append(f"MISSING REUSE TAGS: {len(no_reuse)} strategies without reusability tag")
    else:
        passes.append(f"All {len(strategies)} strategies have reusability tags")

    # 8. Session and regime tags
    no_session = [s for s in strategies if not s.get("session_tag")]
    no_regime = [s for s in strategies if not s.get("regime_tag")]
    if no_session:
        failures.append(f"MISSING SESSION TAGS: {len(no_session)} strategies")
    else:
        passes.append(f"All strategies have session tags")
    if no_regime:
        failures.append(f"MISSING REGIME TAGS: {len(no_regime)} strategies")
    else:
        passes.append(f"All strategies have regime tags")

    # 9. Zero limbo (watch/testing with no routing)
    limbo = [s for s in strategies
             if s.get("status") in ("watch", "testing")
             and not s.get("triage_reason")
             and not s.get("salvage_lane")
             and not s.get("next_action")]
    if limbo:
        failures.append(f"LIMBO: {len(limbo)} strategies in watch/testing with no routing")
    else:
        passes.append("Zero limbo strategies")

    # 10. Docs exist
    required_docs = [
        "XB_ORB_PROBATION_FRAMEWORK.md",
        "BLOCKER_ROUTING_RULES.md",
    ]
    for doc in required_docs:
        if (ROOT / "docs" / doc).exists():
            passes.append(f"Doc exists: {doc}")
        else:
            failures.append(f"DOC MISSING: {doc}")

    # 11. Crossbreeding candidate list exists
    cb_path = ROOT / "research" / "data" / "crossbreeding_candidates.json"
    if cb_path.exists():
        candidates = json.load(open(cb_path))
        passes.append(f"Crossbreeding candidates: {len(candidates)} queued")
    else:
        failures.append("CROSSBREEDING: candidate list missing")

    # 12. Doctrine memory files
    memory_dir = Path.home() / ".claude/projects/-Users-chasefisher/memory"
    if memory_dir.exists():
        memory_files = list(memory_dir.glob("feedback_*.md"))
        if len(memory_files) >= 10:
            passes.append(f"Doctrine memory: {len(memory_files)} feedback files")
        else:
            failures.append(f"DOCTRINE MEMORY: only {len(memory_files)} feedback files (expected 10+)")
    else:
        failures.append("DOCTRINE MEMORY: memory directory not found")

    # 13. Claw targeting has testability gate
    priorities_path = INBOX / "_priorities.md"
    if priorities_path.exists():
        content = priorities_path.read_text()
        if "testab" in content.lower() or "TESTABILITY" in content:
            passes.append("Claw targeting: testability gate present")
        else:
            failures.append("CLAW TARGETING: no testability gate in _priorities.md")
    else:
        failures.append("CLAW TARGETING: _priorities.md missing")

    # 14. Pipeline scripts contain required reports
    daily_sh = (ROOT / "scripts" / "run_fql_daily.sh").read_text() if (ROOT / "scripts" / "run_fql_daily.sh").exists() else ""
    required_in_daily = [
        ("xb_orb_portfolio_monitor", "portfolio monitor"),
        ("forward_behavior_tracker", "behavior tracker"),
        ("probation_health_audit", "probation health"),
        ("fql_alerts", "alert engine"),
        ("operator_brief", "operator brief"),
    ]
    for script, name in required_in_daily:
        if script in daily_sh:
            passes.append(f"Daily pipeline: {name} wired")
        else:
            failures.append(f"PIPELINE GAP: {name} ({script}) not in daily pipeline")

    weekly_sh = (ROOT / "scripts" / "run_fql_weekly.sh").read_text() if (ROOT / "scripts" / "run_fql_weekly.sh").exists() else ""
    required_in_weekly = [
        ("throughput_audit", "throughput audit"),
        ("weekly_operational_audit", "operational audit"),
    ]
    for script, name in required_in_weekly:
        if script in weekly_sh:
            passes.append(f"Weekly pipeline: {name} wired")
        else:
            failures.append(f"PIPELINE GAP: {name} ({script}) not in weekly pipeline")

    return passes, failures


# ── REPORT ───────────────────────────────────────────────────────────────

def generate_report(mode="weekly"):
    lines = []

    if mode == "daily":
        failures = daily_assertions()
        if not failures:
            # Exception-only: say nothing when clean
            return None
        lines.append("# ⚠️ Doctrine Integrity Alert")
        lines.append(f"*{TIMESTAMP}*")
        lines.append("")
        lines.append(f"**{len(failures)} integrity failure(s) detected:**")
        lines.append("")
        for f in failures:
            # Classify as timing artifact or real
            is_timing = any(k in f.lower() for k in ["stale report", "weekend"])
            tag = "(timing)" if is_timing else "(REAL)"
            lines.append(f"  ❌ {f} {tag}")
        return "\n".join(lines)

    else:  # weekly
        passes, failures = weekly_doctrine_check()
        lines.append("# FQL Doctrine Integrity — Weekly Verification")
        lines.append(f"*{TIMESTAMP}*")
        lines.append("")

        if failures:
            real = [f for f in failures if not any(k in f.lower() for k in ["stale", "timing"])]
            timing = [f for f in failures if any(k in f.lower() for k in ["stale", "timing"])]
            lines.append(f"**{len(passes)} PASS / {len(failures)} FAIL** ({len(real)} real, {len(timing)} timing)")
        else:
            lines.append(f"**{len(passes)} PASS / 0 FAIL — all doctrine layers verified**")
        lines.append("")

        if failures:
            lines.append("## Failures")
            for f in failures:
                is_timing = any(k in f.lower() for k in ["stale", "timing"])
                lines.append(f"  ❌ {f} {'(timing artifact)' if is_timing else ''}")
            lines.append("")

        lines.append("## Passes")
        for p in passes:
            lines.append(f"  ✅ {p}")
        lines.append("")
        lines.append("---")
        lines.append("*Auto-generated. Daily assertions run at 17:30 (exception-only). Weekly full check runs Friday 18:30.*")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Doctrine Integrity Check")
    parser.add_argument("--daily", action="store_true", help="Lightweight daily assertion")
    parser.add_argument("--weekly", action="store_true", help="Full weekly doctrine verification")
    parser.add_argument("--save", action="store_true", help="Save report to inbox")
    args = parser.parse_args()

    mode = "daily" if args.daily else "weekly"
    report = generate_report(mode)

    if report is None:
        if mode == "daily":
            print("  Doctrine integrity: all assertions pass (no output needed)")
        return

    print(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
