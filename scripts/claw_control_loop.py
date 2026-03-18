#!/usr/bin/env python3
"""Claude-side Claw Control Loop — reads Claw outputs, writes directives.

This script is the Claude half of the Claude↔Claw file-based coordination.
It runs on a schedule (launchd) and does NOT modify live trading logic.

Actions:
  1. Read Claw's status and completion logs
  2. Scan new notes in inbox/harvest/ and inbox/refinement/
  3. Read cluster reports and gap refresh reports
  4. Update _priorities.md and _family_queue.md based on registry state
  5. Write _directives_today.md with Claw's next task
  6. Write _claw_status.md summarizing what Claw has done
  7. Write _eod_audit.md with daily control loop summary

Usage:
    python3 scripts/claw_control_loop.py              # Full cycle
    python3 scripts/claw_control_loop.py --status      # Show Claw status only
    python3 scripts/claw_control_loop.py --refresh     # Refresh priorities only
    python3 scripts/claw_control_loop.py --audit       # Write EOD audit only
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CLAW_INBOX = Path.home() / "openclaw-intake" / "inbox"
CLAW_LOGS = Path.home() / "openclaw-intake" / "logs"
CLAW_REVIEWED = Path.home() / "openclaw-intake" / "reviewed"
CLAW_REJECTED = Path.home() / "openclaw-intake" / "rejected"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
GENOME_PATH = ROOT / "research" / "data" / "strategy_genome_map.json"
MANIFEST_PATH = ROOT / "research" / "data" / "harvest_manifest.json"

TODAY = datetime.now().strftime("%Y-%m-%d")
DOW = datetime.now().strftime("%A")

# Day-of-week task map (matches Claw's HEARTBEAT.md schedule)
CLAW_SCHEDULE = {
    "Monday": "gap_harvest",
    "Tuesday": "academic_scan",
    "Wednesday": "family_refinement",
    "Thursday": "tradingview_scan",
    "Friday": "cluster_review",
    "Saturday": "off",
    "Sunday": "blocker_mapping",
}

TOMORROW_MAP = {
    "Monday": "Tuesday", "Tuesday": "Wednesday", "Wednesday": "Thursday",
    "Thursday": "Friday", "Friday": "Saturday", "Saturday": "Sunday",
    "Sunday": "Monday",
}


# ── 1. Read Claw Status ─────────────────────────────────────────────────────

def read_claw_status():
    """Read what Claw has done recently."""
    status = {
        "today_task": CLAW_SCHEDULE.get(DOW, "unknown"),
        "today_completed": False,
        "today_log": None,
        "harvest_notes_today": [],
        "refinement_notes_today": [],
        "cluster_reports_today": [],
        "assessment_reports_today": [],
        "total_harvest_pending": 0,
        "total_refinement_pending": 0,
        "recent_logs": [],
    }

    # Check today's log
    log_file = CLAW_LOGS / f"{TODAY}_task.log"
    if log_file.exists():
        status["today_completed"] = True
        status["today_log"] = log_file.read_text().strip()

    # Count pending notes in each folder
    harvest_dir = CLAW_INBOX / "harvest"
    refinement_dir = CLAW_INBOX / "refinement"
    clustering_dir = CLAW_INBOX / "clustering"
    assessment_dir = CLAW_INBOX / "assessment"

    if harvest_dir.exists():
        all_harvest = sorted(harvest_dir.glob("*.md"))
        status["total_harvest_pending"] = len(all_harvest)
        status["harvest_notes_today"] = [
            f.name for f in all_harvest if f.name.startswith(TODAY)
        ]

    if refinement_dir.exists():
        all_ref = sorted(refinement_dir.glob("*.md"))
        status["total_refinement_pending"] = len(all_ref)
        status["refinement_notes_today"] = [
            f.name for f in all_ref if f.name.startswith(TODAY)
        ]

    if clustering_dir.exists():
        status["cluster_reports_today"] = [
            f.name for f in clustering_dir.glob(f"{TODAY}*.md")
        ]

    if assessment_dir.exists():
        status["assessment_reports_today"] = [
            f.name for f in assessment_dir.glob(f"{TODAY}*.md")
        ]

    # Recent logs (last 7 days)
    if CLAW_LOGS.exists():
        for i in range(7):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            lf = CLAW_LOGS / f"{d}_task.log"
            if lf.exists():
                status["recent_logs"].append({"date": d, "log": lf.read_text().strip()})

    return status


# ── 2. Read Registry State ───────────────────────────────────────────────────

def read_registry_state():
    """Extract current registry state for priority calculation."""
    if not REGISTRY_PATH.exists():
        return {}

    reg = json.load(open(REGISTRY_PATH))
    strategies = reg.get("strategies", [])

    statuses = Counter(s.get("status") for s in strategies)

    # Factor distribution for ideas
    ideas = [s for s in strategies if s.get("status") == "idea"]
    idea_factors = Counter()
    for s in ideas:
        for t in s.get("tags", []):
            if t in ("CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "MOMENTUM", "VALUE"):
                idea_factors[t] += 1

    # Probation factors
    probation = [s for s in strategies if s.get("status") == "probation"]
    probation_factors = Counter()
    for s in probation:
        for t in s.get("tags", []):
            if t in ("CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "MOMENTUM"):
                probation_factors[t] += 1

    # Blocked ideas
    blocked = [s for s in ideas if any("blocked" in t for t in s.get("tags", []))]
    blocker_types = Counter()
    for s in blocked:
        for t in s.get("tags", []):
            if t.startswith("blocked_by_"):
                blocker_types[t] += 1

    return {
        "total": len(strategies),
        "statuses": dict(statuses),
        "idea_factors": dict(idea_factors),
        "probation_factors": dict(probation_factors),
        "blocked_count": len(blocked),
        "blocker_types": dict(blocker_types),
    }


# ── 3. Compute Priorities ───────────────────────────────────────────────────

def compute_priorities(registry_state):
    """Determine current gap priorities from registry state."""
    idea_factors = registry_state.get("idea_factors", {})
    prob_factors = registry_state.get("probation_factors", {})

    # Factor gap scoring: lower coverage = higher priority
    all_factors = ["CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "MOMENTUM", "VALUE"]
    gaps = []
    for f in all_factors:
        active = prob_factors.get(f, 0)
        ideas = idea_factors.get(f, 0)
        if f == "MOMENTUM":
            # Momentum is overcrowded — always LOW unless zero coverage
            priority = "LOW"
        elif active == 0 and ideas < 3:
            priority = "HIGH"
        elif active == 0 and ideas >= 3:
            priority = "MEDIUM"
        elif active > 0 and ideas < 5:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        gaps.append({"factor": f, "priority": priority, "active": active, "ideas": ideas})

    return sorted(gaps, key=lambda g: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[g["priority"]])


# ── 4. Write Directives ─────────────────────────────────────────────────────

def write_directives(claw_status, registry_state, priorities):
    """Write _directives_today.md for Claw."""
    tomorrow = TOMORROW_MAP.get(DOW, "Monday")
    tomorrow_task = CLAW_SCHEDULE.get(tomorrow, "unknown")

    top_gaps = [g for g in priorities if g["priority"] in ("HIGH", "MEDIUM")]
    gap_lines = "\n".join(
        f"- **{g['priority']}** {g['factor']}: {g['active']} active, {g['ideas']} ideas"
        for g in top_gaps
    )

    content = f"""# Claw Directives — {TODAY} ({DOW})

*Auto-generated by Claude control loop. Claw reads this before executing.*

## Today's Status

- Scheduled task: **{claw_status['today_task']}**
- Completed: **{'YES' if claw_status['today_completed'] else 'NO'}**
- Harvest notes pending pickup: **{claw_status['total_harvest_pending']}**
- Refinement notes pending pickup: **{claw_status['total_refinement_pending']}**

## Current Gap Priorities

{gap_lines}

## Next Task: {tomorrow} — {tomorrow_task}

"""
    if tomorrow_task == "gap_harvest":
        content += """Focus on the highest-priority gaps listed above. Read `_priorities.md`
for closed families, momentum high-bar rule, and search terms.
Generate 5-8 notes to `inbox/harvest/`.
"""
    elif tomorrow_task == "academic_scan":
        content += """Search Quantpedia, SSRN, AlphaArchitect, Return Stacked for documented
futures edges. Focus on the HIGH-priority factors above.
Generate 3-5 notes to `inbox/harvest/`.
"""
    elif tomorrow_task == "family_refinement":
        content += """Read `_family_queue.md` for families needing depth. Generate 3-5
refinement notes to `inbox/refinement/`. Deepen existing clusters,
don't create redundant new ideas.
"""
    elif tomorrow_task == "tradingview_scan":
        content += """Search TradingView public scripts for mechanical futures strategies.
Focus on gap factors. Reject discretionary, ICT, crypto, spot forex.
Generate 5-8 notes to `inbox/harvest/`.
"""
    elif tomorrow_task == "cluster_review":
        content += """Review all notes from this week. Group into concept clusters.
Flag duplicates, near-duplicates, closed-family violations.
Write a single cluster report to `inbox/clustering/`.
"""
    elif tomorrow_task == "blocker_mapping":
        content += """Review blocked ideas. Assess which blockers may have been resolved.
Write a gap refresh report to `inbox/assessment/`.
"""
    elif tomorrow_task == "off":
        content += "Day off. No catalog task needed.\n"

    content += f"""
## Registry Snapshot

- Total strategies: {registry_state.get('total', '?')}
- Status distribution: {registry_state.get('statuses', {})}
- Blocked ideas: {registry_state.get('blocked_count', '?')}

## Governance Reminder

You NEVER: convert to code, test, backtest, promote, demote, or modify
any file outside ~/openclaw-intake/. You recommend verdicts. The human
decides.
"""

    (CLAW_INBOX / "_directives_today.md").write_text(content)
    return content


def write_claw_status(claw_status):
    """Write _claw_status.md summarizing what Claw has done."""
    recent_lines = "\n".join(
        f"- {log['date']}: {log['log']}" for log in claw_status["recent_logs"]
    ) or "- No recent activity"

    content = f"""# Claw Status — {TODAY}

*Auto-generated by Claude control loop.*

## Today ({DOW})

- Task: {claw_status['today_task']}
- Completed: {'YES' if claw_status['today_completed'] else 'NO — pending or skipped'}
- Log: {claw_status.get('today_log', 'none')}
- Harvest notes today: {len(claw_status['harvest_notes_today'])}
- Refinement notes today: {len(claw_status['refinement_notes_today'])}
- Cluster reports today: {len(claw_status['cluster_reports_today'])}
- Assessment reports today: {len(claw_status['assessment_reports_today'])}

## Pending Pickup (Claude needs to process these)

- Harvest notes: {claw_status['total_harvest_pending']}
- Refinement notes: {claw_status['total_refinement_pending']}

## Recent Activity (last 7 days)

{recent_lines}
"""
    (CLAW_INBOX / "_claw_status.md").write_text(content)
    return content


def write_claw_next_needs(claw_status, priorities):
    """Write _claw_next_needs.md — what Claw should focus on next."""
    high_gaps = [g for g in priorities if g["priority"] == "HIGH"]
    medium_gaps = [g for g in priorities if g["priority"] == "MEDIUM"]

    content = f"""# Claw Next Needs — {TODAY}

*What Claw should prioritize in its next harvest run.*

## Highest-Value Discovery Targets

"""
    if high_gaps:
        for g in high_gaps:
            content += f"### {g['factor']} (HIGH priority)\n"
            content += f"- Active in portfolio: {g['active']}\n"
            content += f"- Ideas in registry: {g['ideas']}\n"
            content += f"- Need: More testable ideas in this factor\n\n"

    if medium_gaps:
        content += "## Medium-Priority Targets\n\n"
        for g in medium_gaps:
            content += f"- {g['factor']}: {g['active']} active, {g['ideas']} ideas\n"

    content += f"""
## What NOT to Generate

- Generic momentum variants (portfolio is 54% momentum)
- Morning equity breakout variants (13 tested, saturated)
- Mean reversion on equity index 5m bars (5 failures, closed)
- Gap-fade / gap-reversal (3 failures, closed)
- ICT/SMC concepts (2 failures, closed)
"""
    (CLAW_INBOX / "_claw_next_needs.md").write_text(content)
    return content


# ── 5. Write EOD Audit ──────────────────────────────────────────────────────

def write_eod_audit(claw_status, registry_state, priorities):
    """Write _eod_audit.md — daily control loop summary."""
    content = f"""# FQL Discovery Control Loop — EOD Audit
## {TODAY} ({DOW})

*Auto-generated. Reviews the day's discovery activity and loop health.*

---

### Claw Execution

- Scheduled task: **{claw_status['today_task']}**
- Completed: **{'YES' if claw_status['today_completed'] else 'NO'}**
- Notes generated today: {len(claw_status['harvest_notes_today']) + len(claw_status['refinement_notes_today'])}
- Log: {claw_status.get('today_log', 'none')}

### Pipeline State

- Harvest notes pending Claude pickup: **{claw_status['total_harvest_pending']}**
- Refinement notes pending Claude pickup: **{claw_status['total_refinement_pending']}**
- Registry total: **{registry_state.get('total', '?')}**

### Gap Coverage

| Factor | Priority | Active | Ideas |
|--------|----------|--------|-------|
"""
    for g in priorities:
        content += f"| {g['factor']} | {g['priority']} | {g['active']} | {g['ideas']} |\n"

    # Health checks
    issues = []
    if not claw_status['today_completed'] and DOW != "Saturday":
        issues.append("Claw did not complete today's scheduled task")
    if claw_status['total_harvest_pending'] > 30:
        issues.append(f"Harvest backlog is large ({claw_status['total_harvest_pending']} notes) — Claude pickup may be falling behind")
    if claw_status['total_harvest_pending'] == 0 and DOW in ("Tuesday", "Wednesday", "Thursday", "Friday"):
        issues.append("No harvest notes pending — Claw may not be running")

    days_with_logs = len(claw_status['recent_logs'])
    if days_with_logs < 3:
        issues.append(f"Only {days_with_logs} Claw logs in last 7 days — possible execution gap")

    content += "\n### Health\n\n"
    if issues:
        for issue in issues:
            content += f"- **WARN:** {issue}\n"
    else:
        content += "- All checks PASS. Control loop is healthy.\n"

    content += f"""
### Loop Cadence

| Component | Schedule | Last Run |
|-----------|----------|----------|
| Claw task execution | Daily via heartbeat | {TODAY if claw_status['today_completed'] else 'not today'} |
| Claude directive refresh | Daily 06:00 ET (launchd) | {TODAY} |
| Claude EOD audit | Daily 20:00 ET (launchd) | {TODAY} |
| Claude priority refresh | Sunday + after registry changes | see _priorities.md |
| Human review | Monday + Friday sessions | manual |

### Governance

- Claw boundary: INTACT (writes only to ~/openclaw-intake/)
- Claude boundary: INTACT (bridge only, no auto-accept)
- Human gates: INTACT (accept/reject, conversion, promotion all manual)
"""

    (CLAW_INBOX / "_eod_audit.md").write_text(content)

    # Also save a copy to algo-lab for Claude's reference
    audit_dir = ROOT / "research" / "data" / "claw_audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / f"audit_{TODAY}.md").write_text(content)

    return content


# ── 6. Refresh Priorities File ───────────────────────────────────────────────

def refresh_priorities(registry_state, priorities):
    """Rewrite _priorities.md based on current registry state."""
    # Read existing priorities to preserve search terms and closed families
    existing = (CLAW_INBOX / "_priorities.md").read_text() if (CLAW_INBOX / "_priorities.md").exists() else ""

    # Extract sections we want to preserve (search terms, closed families, momentum rule)
    # by finding them in the existing file
    preserve_sections = []
    in_preserve = False
    preserve_headers = [
        "## Search Term Suggestions",
        "## Closed Families",
        "## Momentum High-Bar Rule",
    ]
    current_section = []
    for line in existing.split("\n"):
        if any(line.startswith(h) for h in preserve_headers):
            if current_section:
                preserve_sections.append("\n".join(current_section))
            current_section = [line]
            in_preserve = True
        elif in_preserve and line.startswith("## ") and not any(line.startswith(h) for h in preserve_headers):
            preserve_sections.append("\n".join(current_section))
            current_section = []
            in_preserve = False
        elif in_preserve:
            current_section.append(line)
    if current_section:
        preserve_sections.append("\n".join(current_section))

    # Build new priorities
    content = f"""# FQL Catalog Priorities — Updated {TODAY}

*Auto-generated by Claude control loop. Claw reads this before harvest tasks.*

---

## Priority Factor Gaps (harvest these)

| Priority | Factor | Active | Ideas | Target |
|----------|--------|--------|-------|--------|
"""
    for g in priorities:
        target = {
            "CARRY": "First testable carry strategy",
            "VOLATILITY": "Benchmark vol-management sleeve",
            "EVENT": "More event families beyond FOMC/NFP",
            "STRUCTURAL": "Afternoon/close session coverage",
            "MOMENTUM": "HIGH BAR ONLY — portfolio is 54% momentum",
            "VALUE": "Any testable value/fundamental strategy",
        }.get(g["factor"], "Fill gap")
        content += f"| {g['priority']} | {g['factor']} | {g['active']} | {g['ideas']} | {target} |\n"

    content += f"""
## Registry State

- Total strategies: {registry_state.get('total', '?')}
- Status distribution: {registry_state.get('statuses', {})}
- Blocked ideas: {registry_state.get('blocked_count', '?')}
- Blocker types: {registry_state.get('blocker_types', {})}

"""
    # Append preserved sections
    for section in preserve_sections:
        content += section + "\n\n"

    (CLAW_INBOX / "_priorities.md").write_text(content)


# ── Main ─────────────────────────────────────────────────────────────────────

def run_full_cycle():
    """Run the complete control loop cycle."""
    print(f"FQL Claw Control Loop — {TODAY} ({DOW})")
    print("=" * 50)

    # 1. Read Claw status
    print("  Reading Claw status...")
    claw_status = read_claw_status()
    print(f"    Task: {claw_status['today_task']}, completed: {claw_status['today_completed']}")
    print(f"    Pending: {claw_status['total_harvest_pending']} harvest, {claw_status['total_refinement_pending']} refinement")

    # 2. Read registry
    print("  Reading registry state...")
    registry_state = read_registry_state()
    print(f"    Registry: {registry_state.get('total', '?')} strategies")

    # 3. Compute priorities
    priorities = compute_priorities(registry_state)

    # 4. Write all handoff files
    print("  Writing directives...")
    write_directives(claw_status, registry_state, priorities)

    print("  Writing Claw status...")
    write_claw_status(claw_status)

    print("  Writing next needs...")
    write_claw_next_needs(claw_status, priorities)

    print("  Writing EOD audit...")
    write_eod_audit(claw_status, registry_state, priorities)

    # 5. Refresh priorities (only on Sundays or if significant changes)
    print("  Refreshing priorities...")
    refresh_priorities(registry_state, priorities)

    print(f"\n  Control loop complete. Files written to {CLAW_INBOX}")
    print(f"  Audit saved to research/data/claw_audits/audit_{TODAY}.md")


def main():
    parser = argparse.ArgumentParser(description="Claude-side Claw Control Loop")
    parser.add_argument("--status", action="store_true", help="Show Claw status only")
    parser.add_argument("--refresh", action="store_true", help="Refresh priorities only")
    parser.add_argument("--audit", action="store_true", help="Write EOD audit only")
    args = parser.parse_args()

    if args.status:
        status = read_claw_status()
        print(json.dumps(status, indent=2, default=str))
    elif args.refresh:
        registry_state = read_registry_state()
        priorities = compute_priorities(registry_state)
        refresh_priorities(registry_state, priorities)
        print(f"Priorities refreshed: {CLAW_INBOX / '_priorities.md'}")
    elif args.audit:
        claw_status = read_claw_status()
        registry_state = read_registry_state()
        priorities = compute_priorities(registry_state)
        content = write_eod_audit(claw_status, registry_state, priorities)
        print(content)
    else:
        run_full_cycle()


if __name__ == "__main__":
    main()
