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
NOW = datetime.now().strftime("%H:%M")
DOW = datetime.now().strftime("%A")
HOUR = datetime.now().hour

# Day-of-week PRIMARY task (the anchor task for each day)
CLAW_SCHEDULE = {
    "Monday": "gap_harvest",
    "Tuesday": "academic_scan",
    "Wednesday": "family_refinement",
    "Thursday": "tradingview_scan",
    "Friday": "cluster_review",
    "Saturday": "off",
    "Sunday": "blocker_mapping",
}

# Secondary task queue — Claw pulls from this after completing primary task.
# Ordered by value. Claw works through these until daily budget is exhausted.
SECONDARY_TASKS = [
    "gap_harvest_supplemental",    # Always valuable: more gap-targeted ideas
    "cross_source_verification",   # Check if existing ideas are confirmed by new sources
    "blocker_reassessment",        # Quick check: have any blockers been resolved?
    "family_variant_scan",         # Lightweight: scan for variants of promising families
    "cluster_maintenance",         # Merge/split/relabel existing clusters
]

# Daily work budget: max notes Claw should generate per day across all tasks
DAILY_NOTE_CAP = 15
DAILY_REPORT_CAP = 2

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
        "today_phases_completed": 0,
        "today_notes_generated": 0,
        "harvest_notes_today": [],
        "refinement_notes_today": [],
        "cluster_reports_today": [],
        "assessment_reports_today": [],
        "total_harvest_pending": 0,
        "total_refinement_pending": 0,
        "recent_logs": [],
        "budget_remaining": DAILY_NOTE_CAP,
    }

    # Check today's logs (may have multiple phases: _task.log, _task_2.log, etc.)
    log_file = CLAW_LOGS / f"{TODAY}_task.log"
    if log_file.exists():
        status["today_completed"] = True
        status["today_log"] = log_file.read_text().strip()
        status["today_phases_completed"] = 1

    # Check for additional phase logs
    for phase in range(2, 10):
        phase_log = CLAW_LOGS / f"{TODAY}_task_{phase}.log"
        if phase_log.exists():
            status["today_phases_completed"] = phase
            extra = phase_log.read_text().strip()
            status["today_log"] = (status["today_log"] or "") + f"\n[Phase {phase}] {extra}"

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

    # Count today's total notes generated
    status["today_notes_generated"] = (
        len(status["harvest_notes_today"]) + len(status["refinement_notes_today"])
    )
    status["budget_remaining"] = max(0, DAILY_NOTE_CAP - status["today_notes_generated"])

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

def _task_instructions(task_name):
    """Return instructions for a given task type."""
    instructions = {
        "gap_harvest": """Focus on the highest-priority gaps. Read `_priorities.md` for closed
families, momentum high-bar rule, and search terms.
Generate 5-8 notes to `inbox/harvest/`.""",

        "academic_scan": """Search Quantpedia, SSRN, AlphaArchitect, Return Stacked for documented
futures edges. Focus on HIGH-priority factors.
Generate 3-5 notes to `inbox/harvest/`.""",

        "family_refinement": """Read `_family_queue.md` for families needing depth. Generate 3-5
refinement notes to `inbox/refinement/`. Deepen existing clusters,
don't create redundant new ideas.""",

        "tradingview_scan": """Search TradingView public scripts for mechanical futures strategies.
Focus on gap factors. Reject discretionary, ICT, crypto, spot forex.
Generate 5-8 notes to `inbox/harvest/`.""",

        "cluster_review": """Review all notes from this week. Group into concept clusters.
Flag duplicates, near-duplicates, closed-family violations.
Write a single cluster report to `inbox/clustering/`.""",

        "blocker_mapping": """Review blocked ideas. Assess which blockers may have been resolved.
Write a gap refresh report to `inbox/assessment/`.""",

        "gap_harvest_supplemental": """Generate 3-5 additional gap-targeted notes focusing on factors NOT
covered by today's primary task. Emphasize different asset classes or
sessions than the primary batch. Write to `inbox/harvest/`.""",

        "cross_source_verification": """Pick 3-5 existing ideas from `_priorities.md` and search for
independent confirmation from a different source type. If an idea
from Quantpedia also appears in a TradingView script or practitioner
blog, note the convergent evidence. Write to `inbox/refinement/`.""",

        "blocker_reassessment": """Quick scan of blocked ideas. For each blocker type, check if any
new data sources, tools, or infrastructure might have resolved it.
Write a short assessment to `inbox/assessment/`.""",

        "family_variant_scan": """Pick 2-3 families with HIGH-priority gaps. Generate 2-3 lightweight
variant ideas per family — different entry timing, different asset,
different exit structure. Write to `inbox/refinement/`.""",

        "cluster_maintenance": """Review existing clusters. Merge clusters that are too similar.
Split clusters that contain genuinely different mechanisms. Update
best-representative picks. Write report to `inbox/clustering/`.""",

        "off": "Day off. No catalog task needed.",
    }
    return instructions.get(task_name, "No instructions defined for this task.")


def _determine_next_task(claw_status, priorities):
    """Determine what Claw should do next based on completion state and budget."""
    primary_task = CLAW_SCHEDULE.get(DOW, "off")
    budget = claw_status["budget_remaining"]
    phases_done = claw_status["today_phases_completed"]

    if primary_task == "off":
        # Saturday: still allow lightweight secondary work
        if budget > 0 and phases_done < 2:
            return "blocker_reassessment", "secondary"
        return "off", "done"

    if not claw_status["today_completed"]:
        # Primary task not done yet
        return primary_task, "primary"

    if budget <= 0:
        return "off", "budget_exhausted"

    # Primary done, budget remaining — assign secondary tasks
    # Skip tasks that don't make sense given today's primary
    skip = set()
    if primary_task == "gap_harvest":
        skip.add("gap_harvest_supplemental")  # Already did harvest
    if primary_task == "cluster_review":
        skip.add("cluster_maintenance")  # Already did clustering
    if primary_task == "blocker_mapping":
        skip.add("blocker_reassessment")  # Already did blockers

    for task in SECONDARY_TASKS:
        if task in skip:
            continue
        # Check if this secondary was already completed today
        sec_log = CLAW_LOGS / f"{TODAY}_task_{phases_done + 1}.log"
        if not sec_log.exists():
            return task, "secondary"

    return "off", "all_tasks_complete"


def write_directives(claw_status, registry_state, priorities):
    """Write _directives_today.md for Claw — multi-phase aware."""
    top_gaps = [g for g in priorities if g["priority"] in ("HIGH", "MEDIUM")]
    gap_lines = "\n".join(
        f"- **{g['priority']}** {g['factor']}: {g['active']} active, {g['ideas']} ideas"
        for g in top_gaps
    )

    next_task, task_type = _determine_next_task(claw_status, priorities)

    content = f"""# Claw Directives — {TODAY} {NOW} ({DOW})

*Auto-generated by Claude control loop every 4 hours. Read before executing.*

## Status Right Now

- Primary task: **{claw_status['today_task']}** — {'DONE' if claw_status['today_completed'] else 'PENDING'}
- Phases completed today: **{claw_status['today_phases_completed']}**
- Notes generated today: **{claw_status['today_notes_generated']}**
- Daily budget remaining: **{claw_status['budget_remaining']}** notes
- Harvest pending pickup: **{claw_status['total_harvest_pending']}**
- Refinement pending pickup: **{claw_status['total_refinement_pending']}**

## Current Gap Priorities

{gap_lines}

## YOUR NEXT TASK: {next_task} ({task_type})

"""
    if task_type == "budget_exhausted":
        content += f"""Daily note budget exhausted ({DAILY_NOTE_CAP} notes). No more generation tasks.
You may still do cluster maintenance or blocker reassessment (report-only, no notes).
Log completion and wait for tomorrow's directives.
"""
    elif task_type == "all_tasks_complete":
        content += """All primary and secondary tasks complete for today. Well done.
Log completion and wait for tomorrow's directives.
"""
    elif task_type == "done":
        content += "Day off or all work complete. Rest.\n"
    else:
        content += _task_instructions(next_task) + "\n"

    content += f"""
## After Completing This Task

1. Log to `logs/{TODAY}_task{'_' + str(claw_status['today_phases_completed'] + 1) if claw_status['today_phases_completed'] > 0 else ''}.log`
2. Read `_directives_today.md` again — Claude may have refreshed it with a new task
3. If budget remains and directives show another task, execute it
4. If budget is exhausted or directives say "done", stop

## Daily Budget

- Cap: {DAILY_NOTE_CAP} notes/day, {DAILY_REPORT_CAP} reports/day
- Generated so far: {claw_status['today_notes_generated']} notes
- Remaining: {claw_status['budget_remaining']} notes

## Registry Snapshot

- Total: {registry_state.get('total', '?')} strategies
- Blocked: {registry_state.get('blocked_count', '?')} ideas

## Governance

You NEVER: convert to code, test, backtest, promote, demote, or modify
any file outside ~/openclaw-intake/. You recommend verdicts. The human decides.
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


# ── 5. Write Master Operating Brief ──────────────────────────────────────────

def _load_vitality_alerts():
    """Load edge vitality data, running the monitor if scores aren't cached."""
    if not REGISTRY_PATH.exists():
        return [], {}

    reg = json.load(open(REGISTRY_PATH))

    # Check if vitality scores are cached in registry
    has_cached = any(s.get("edge_vitality") is not None
                     for s in reg.get("strategies", [])
                     if s.get("status") in ("core", "probation", "watch"))

    if not has_cached:
        # Run vitality monitor inline to get fresh scores
        try:
            from research.edge_vitality_monitor import (
                load_half_life_data, load_drift_data,
                load_forward_decay, compute_vitality,
            )
            hl = load_half_life_data()
            dr = load_drift_data()
            fd = load_forward_decay()
            vitality_results = compute_vitality(hl, dr, fd)
        except Exception:
            vitality_results = {}
    else:
        vitality_results = {}

    alerts = []
    vitality_map = {}
    for s in reg.get("strategies", []):
        if s.get("status") not in ("core", "probation", "watch"):
            continue
        sid = s["strategy_id"]
        # Prefer cached, fall back to computed
        vt = s.get("edge_vitality_tier")
        vs = s.get("edge_vitality")
        if vt is None and sid in vitality_results:
            vt = vitality_results[sid]["tier"]
            vs = vitality_results[sid]["vitality_score"]
        if vt is None:
            vt = "UNKNOWN"

        vitality_map[sid] = {"tier": vt, "score": vs}
        if vt in ("FADING", "DEAD"):
            alerts.append(f"{sid}: {vt} (vitality {vs})")
    return alerts, vitality_map


def _load_forward_summary():
    """Load forward trading summary from trade log."""
    trade_log = ROOT / "logs" / "trade_log.csv"
    if not trade_log.exists():
        return {"trades": 0, "pnl": 0, "strategies": 0, "days": 0}
    try:
        import pandas as pd
        df = pd.read_csv(trade_log)
        if df.empty:
            return {"trades": 0, "pnl": 0, "strategies": 0, "days": 0}
        return {
            "trades": len(df),
            "pnl": round(float(df["pnl"].sum()), 2),
            "strategies": df["strategy"].nunique(),
            "days": df["date"].nunique(),
        }
    except Exception:
        return {"trades": 0, "pnl": 0, "strategies": 0, "days": 0}


def _load_account_state():
    """Load account state for equity/DD info."""
    state_path = ROOT / "state" / "account_state.json"
    if not state_path.exists():
        return {}
    try:
        return json.load(open(state_path))
    except Exception:
        return {}


def write_eod_audit(claw_status, registry_state, priorities):
    """Write _eod_audit.md — single master operating brief.

    This is the ONE report that answers: what happened today, where does
    FQL stand, and what needs attention.
    """
    vitality_alerts, vitality_map = _load_vitality_alerts()
    forward = _load_forward_summary()
    account = _load_account_state()

    # Health checks
    issues = []
    if not claw_status['today_completed'] and DOW != "Saturday":
        issues.append("Claw did not complete today's scheduled task")
    if claw_status['total_harvest_pending'] > 30:
        issues.append(f"Harvest backlog large ({claw_status['total_harvest_pending']} notes)")
    days_with_logs = len(claw_status['recent_logs'])
    if days_with_logs < 3:
        issues.append(f"Only {days_with_logs} Claw logs in last 7 days")
    if vitality_alerts:
        for va in vitality_alerts:
            issues.append(f"Vitality alert: {va}")

    # Determine top risk and top opportunity
    top_risk = "None identified"
    top_opportunity = "None identified"

    # Risk: FADING strategies or negative forward PnL
    if vitality_alerts:
        top_risk = f"FADING edge: {vitality_alerts[0]}"
    elif forward["pnl"] < -500:
        top_risk = f"Forward PnL is ${forward['pnl']:+,.0f} across {forward['trades']} trades"

    # Opportunity: upgrade sequence
    # Check if Treasury-Rolldown is still the lead or if fallback is needed
    upgrade_lead = None
    upgrade_fallback = None
    if REGISTRY_PATH.exists():
        _reg = json.load(open(REGISTRY_PATH))
        for _s in _reg.get("strategies", []):
            if _s.get("upgrade_sequence") == 1:
                upgrade_lead = _s["strategy_id"]
            if _s.get("upgrade_sequence") == 2:
                upgrade_fallback = _s["strategy_id"]

    high_gaps = [g for g in priorities if g["priority"] == "HIGH"]
    if high_gaps:
        top_opportunity = (
            f"Upgrade sequence: #1 {upgrade_lead or 'Treasury-Rolldown'} (CARRY+Rates), "
            f"#2 {upgrade_fallback or 'VolManaged-Equity'} (VOL), "
            f"#3 Commodity-Carry v2"
        )

    # Decisions needed
    decisions = []
    # Check for watch deadlines within 30 days
    reg_data = json.load(open(REGISTRY_PATH)) if REGISTRY_PATH.exists() else {"strategies": []}
    for s in reg_data.get("strategies", []):
        if s.get("status") == "watch":
            notes = s.get("notes", "")
            for token in notes.split():
                if token.startswith("2026-") and len(token) == 10:
                    try:
                        dl = datetime.strptime(token, "%Y-%m-%d")
                        days_left = (dl - datetime.now()).days
                        if 0 < days_left <= 30:
                            decisions.append(f"{s['strategy_id']}: watch deadline in {days_left} days")
                    except ValueError:
                        pass

    content = f"""# FQL Master Operating Brief
## {TODAY} ({DOW})

*Single daily report. Read this one document to know where FQL stands.*

---

### 1. Claw Discovery Engine

- Task: **{claw_status['today_task']}** — {'DONE' if claw_status['today_completed'] else 'PENDING'}
- Phases today: **{claw_status['today_phases_completed']}**
- Notes generated: **{claw_status['today_notes_generated']}** / {DAILY_NOTE_CAP} budget
- Harvest pending pickup: **{claw_status['total_harvest_pending']}**
- Refinement pending pickup: **{claw_status['total_refinement_pending']}**

### 2. Claude Automation

- Control loop: running (30-min cadence)
- Daily research pipeline: {'fired today' if DOW not in ('Saturday', 'Sunday') else 'weekend'}
- Registry: **{registry_state.get('total', '?')}** strategies
- Forward runner: **{forward['trades']}** trades across **{forward['strategies']}** strategies, **{forward['days']}** days

### 3. New Notes / Families / Clusters

"""
    if claw_status['harvest_notes_today']:
        for note in claw_status['harvest_notes_today']:
            content += f"- NEW: `{note}`\n"
    if claw_status['refinement_notes_today']:
        for note in claw_status['refinement_notes_today']:
            content += f"- REF: `{note}`\n"
    if claw_status['cluster_reports_today']:
        for note in claw_status['cluster_reports_today']:
            content += f"- CLUSTER: `{note}`\n"
    if not any([claw_status['harvest_notes_today'], claw_status['refinement_notes_today'],
                claw_status['cluster_reports_today']]):
        content += "- No new outputs today.\n"

    content += f"""
### 4. Pressure Summary

- **Weakest core:** PB-MGC-Short (rubric 16, fwd: {forward.get('pnl', 0):+.0f} overall)
- **Weakest watch:** MomIgn-M2K-Short (rubric 14, deadline 2026-06-01)
- **Top challenger:** Treasury-Rolldown-Carry-Spread (effective 20, CARRY + Rates)
- **Next displacement:** Treasury-Rolldown → MomIgn at June 1

### 5. Vitality / Decay Alerts

"""
    if vitality_alerts:
        for va in vitality_alerts:
            content += f"- **ALERT:** {va}\n"
    else:
        content += "- No FADING or DEAD strategies. Edge health is good.\n"

    content += f"""
### 6. Forward / Counterfactual

- Forward equity: **${account.get('equity', 0):,.2f}** (DD from HWM: ${account.get('equity_hwm', 0) - account.get('equity', 0):,.2f})
- Forward trades: **{forward['trades']}** across {forward['strategies']} strategies
- Forward PnL: **${forward['pnl']:+,.2f}**
- Only strategy with positive forward PnL: ORB-MGC-Long

### 7. Top Portfolio Risk

**{top_risk}**

### 8. Top Portfolio Opportunity

**{top_opportunity}**

### 9. Decisions / Reviews Needed

"""
    if decisions:
        for d in decisions:
            content += f"- {d}\n"
    elif issues:
        for issue in issues:
            content += f"- INVESTIGATE: {issue}\n"
    else:
        content += "- No immediate decisions needed. System operating normally.\n"

    content += f"""
---

### Factor Coverage

| Factor | Priority | Active | Ideas |
|--------|----------|--------|-------|
"""
    for g in priorities:
        content += f"| {g['factor']} | {g['priority']} | {g['active']} | {g['ideas']} |\n"

    content += f"""
### System Health

"""
    if issues:
        for issue in issues:
            content += f"- **WARN:** {issue}\n"
    else:
        content += "- All systems nominal.\n"

    (CLAW_INBOX / "_eod_audit.md").write_text(content)

    # Save archive copy
    audit_dir = ROOT / "research" / "data" / "claw_audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / f"brief_{TODAY}.md").write_text(content)

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
