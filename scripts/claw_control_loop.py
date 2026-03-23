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

    # Factor mapping from family (for strategies without explicit factor tags)
    FAMILY_TO_FACTOR = {
        "pullback": "MOMENTUM", "breakout": "MOMENTUM", "trend": "MOMENTUM",
        "mean_reversion": "MEAN_REVERSION", "event_driven": "EVENT",
        "carry": "CARRY", "afternoon_rates_reversion": "STRUCTURAL",
        "vol_expansion": "VOLATILITY", "structural": "STRUCTURAL",
        "volatility": "VOLATILITY",
    }

    def _get_factor(s):
        for t in s.get("tags", []):
            if t in ("CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "MOMENTUM", "VALUE"):
                return t
        return FAMILY_TO_FACTOR.get(s.get("family", ""), None)

    # Core factors
    core = [s for s in strategies if s.get("status") == "core"]
    core_factors = Counter()
    for s in core:
        f = _get_factor(s)
        if f:
            core_factors[f] += 1

    # Probation factors
    probation = [s for s in strategies if s.get("status") == "probation"]
    probation_factors = Counter()
    for s in probation:
        f = _get_factor(s)
        if f:
            probation_factors[f] += 1

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
        "core_factors": dict(core_factors),
        "probation_factors": dict(probation_factors),
        "blocked_count": len(blocked),
        "blocker_types": dict(blocker_types),
    }


# ── 3. Compute Priorities ───────────────────────────────────────────────────

def compute_priorities(registry_state):
    """Determine current gap priorities from registry state.

    Priority logic:
      HIGH  — 0 active AND 0 core (genuine gap, nothing in pipeline)
      HIGH  — 0 active AND < 3 ideas (gap with thin catalog)
      MEDIUM — 1 probation only, no core (thin, fragile coverage)
      MEDIUM — 0 active AND >= 3 ideas (gap but catalog has options)
      LOW   — 2+ active, or core coverage exists
      LOW   — MOMENTUM always (portfolio is overcrowded at 55%)

    "Active" counts both core AND probation strategies tagged with
    the factor. A single probation strategy is MEDIUM, not LOW —
    probation is not proven coverage.
    """
    idea_factors = registry_state.get("idea_factors", {})
    prob_factors = registry_state.get("probation_factors", {})
    core_factors = registry_state.get("core_factors", {})

    all_factors = ["CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "MOMENTUM", "VALUE"]
    gaps = []
    for f in all_factors:
        core = core_factors.get(f, 0)
        probation = prob_factors.get(f, 0)
        active = core + probation
        ideas = idea_factors.get(f, 0)

        if f == "MOMENTUM":
            priority = "LOW"
        elif core == 0 and probation == 0 and ideas < 3:
            priority = "HIGH"
        elif core == 0 and probation == 0 and ideas >= 3:
            priority = "HIGH"  # Still a gap even with ideas — nothing in pipeline
        elif core == 0 and probation <= 1:
            priority = "MEDIUM"  # Thin: only 1 probation, not proven
        elif core == 0 and probation >= 2:
            priority = "LOW"  # Multiple probation = pipeline is working
        else:
            priority = "LOW"

        target = {
            "CARRY": "Carry strategies across asset classes (rates, commodity, FX)",
            "VOLATILITY": "Vol strategies on non-equity assets, non-morning sessions",
            "EVENT": "Event families beyond FOMC/NFP (CPI, OPEC, auctions, rebalance)",
            "STRUCTURAL": "Afternoon/close session, rates/FX microstructure",
            "MOMENTUM": "HIGH BAR ONLY — portfolio is 55% momentum",
            "VALUE": "Any testable value/fundamental strategy on any asset class",
        }.get(f, "Fill gap")

        gaps.append({
            "factor": f, "priority": priority,
            "core": core, "probation": probation,
            "active": active, "ideas": ideas, "target": target,
        })

    return sorted(gaps, key=lambda g: {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[g["priority"]])


# ── 4. Write Directives ─────────────────────────────────────────────────────

def _task_instructions(task_name):
    """Return instructions for a given task type.

    Source diversity rule: each task should search DIFFERENT sources than
    the previous day. The weekly rotation ensures all major source classes
    get coverage across the week. No single source should dominate intake.

    Source classes (all are valid search targets):
      - Academic: SSRN, Quantpedia, arXiv, AlphaArchitect, Return Stacked,
        Journal of Financial Economics, Review of Financial Studies
      - TradingView: public scripts with mechanical futures rules
      - GitHub: quant repos with testable strategy code
      - YouTube: practitioner content with explicit entry/exit rules
      - Reddit/forums: r/algotrading, r/quant, r/FuturesTrading,
        EliteTrader, NuclearPhynance, QuantConnect forums
      - Microstructure: CME research, BIS reports, specialist blogs,
        commodity/rates/FX-specific practitioner content

    PRE-GATHERED LEADS: Check `inbox/source_leads/` for pre-fetched
    URLs from GitHub, Reddit, YouTube, and blog helpers. These are
    curated starting points — read each lead, assess for futures
    applicability and mechanical rules, and write a harvest note if
    it qualifies. Not every lead will produce a note; that is expected.

    COMPONENT TYPES: Most notes should NOT be full_strategy. If a source
    describes only an entry condition, or only a filter, or only an asset
    behavior — tag it as that component type. See _note_template.md for
    examples of each type. Fragments are MORE valuable than forced-complete
    strategies because they combine with existing validated logic.

    Types: full_strategy, entry_logic, exit_logic, filter, sizing_overlay,
           asset_behavior, session_effect

    WHEN IN DOUBT: use a component type, not full_strategy. A well-tagged
    fragment is more useful than a vaguely specified full strategy.

    CONVERGENT EVIDENCE: If you find an idea that already exists in the
    registry from a different source, do NOT discard it. Note the
    convergence — multiple independent sources confirming the same
    mechanism is stronger evidence than one source alone.
    """
    instructions = {
        "gap_harvest": """MULTI-SOURCE gap harvest. Search across ALL available sources for
the highest-priority gaps in `_priorities.md`. Cast a WIDE net:
  - Academic papers and quant blogs
  - TradingView public scripts
  - GitHub quant repos with testable code
  - YouTube practitioner content (mechanical rules only)
  - Reddit/forum discussions (r/algotrading, r/quant, EliteTrader)
  - Microstructure specialist sources
ALSO: check `inbox/source_leads/` for pre-gathered URLs from GitHub
and Reddit helpers. Review each lead for futures applicability.
Tag each note with its source. Focus on HIGH-priority factors.
Prefer non-equity assets, non-morning sessions, short-biased ideas.
Read closed families list — do NOT regenerate dead mechanisms.
Generate 5-8 notes to `inbox/harvest/`.""",

        "academic_scan": """Search academic and research sources for documented futures edges:
  - SSRN, arXiv quantitative finance
  - Quantpedia, QuantifiedStrategies, AlphaArchitect
  - Return Stacked, AQR research
  - Journal of Financial Economics, Review of Financial Studies
Focus on HIGH-priority factors (check `_priorities.md`).
Prefer papers with: testable mechanical rules, futures applicability,
non-equity assets, value/fundamental factors.
Generate 3-5 notes to `inbox/harvest/`.""",

        "family_refinement": """Read `_family_queue.md` for families needing depth. Generate 3-5
refinement notes to `inbox/refinement/`. Deepen existing clusters,
don't create redundant new ideas. Search across ALL sources for
variants and confirmations of existing families.""",

        "tradingview_scan": """Search TradingView AND practitioner/YouTube sources for mechanical
futures strategies. This day covers all practitioner content:
  - TradingView public scripts (futures, not crypto/spot forex)
  - YouTube channels with explicit mechanical rules
  - GitHub repos with strategy code
  - Reddit/forum strategy discussions
ALSO: check `inbox/source_leads/` for pre-gathered URLs from GitHub
and Reddit helpers. These are curated starting points to review.
Focus on gap factors. Reject discretionary, ICT, crypto, spot forex.
Tag each note with exact source (URL or channel name).
Generate 5-8 notes to `inbox/harvest/`.""",

        "cluster_review": """Review all notes from this week. Group into concept clusters.
Flag duplicates, near-duplicates, closed-family violations.
Check source diversity: are notes coming from multiple source types?
If one source dominates, flag it.
Write a single cluster report to `inbox/clustering/`.""",

        "blocker_mapping": """Review blocked ideas. Assess which blockers may have been resolved.
Also: scan for ideas in source classes not well-represented this week
(e.g., if no GitHub or Reddit ideas appeared, do a quick search).
Write a gap refresh report to `inbox/assessment/`.""",

        "gap_harvest_supplemental": """Generate 3-5 additional gap-targeted notes. KEY RULE: use DIFFERENT
sources than the primary task today. If primary used academic papers,
supplemental should search TradingView/YouTube/Reddit/GitHub.
Emphasize different asset classes or sessions than the primary batch.
Write to `inbox/harvest/`.""",

        "cross_source_verification": """Pick 3-5 existing ideas from `_priorities.md` and search for
independent confirmation from a DIFFERENT source type. If an idea
from Quantpedia also appears in a TradingView script or practitioner
blog, note the convergent evidence. Multi-source confirmation
strengthens ideas. Write to `inbox/refinement/`.""",

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

    # Compute days to June 1 for the brief
    try:
        _june1 = datetime.strptime("2026-06-01", "%Y-%m-%d")
        _days_to_june1 = max(0, (_june1 - datetime.now()).days)
    except Exception:
        _days_to_june1 = "?"

    # Check VolManaged status from registry
    _vm_status = "unknown"
    _vm_fwd_trades = 0
    if REGISTRY_PATH.exists():
        _r = json.load(open(REGISTRY_PATH))
        for _s in _r.get("strategies", []):
            if _s["strategy_id"] == "VolManaged-EquityIndex-Futures":
                _vm_status = _s.get("status", "?")
                break

    content += f"""
### 4. Pressure Summary

- **Weakest core:** PB-MGC-Short (rubric 16)
- **Weakest watch:** MomIgn-M2K-Short (rubric 14, deadline June 1 — {_days_to_june1} days)
- **Top challenger:** Treasury-Rolldown-Carry-Spread (eff. 20, CARRY + Rates)
- **Next displacement:** Treasury-Rolldown → MomIgn at June 1 (base case)

### 4b. Upgrade Ladder

| # | Challenger | Score | Target | Status | Timeline |
|---|-----------|-------|--------|--------|----------|
| 1 | Treasury-Rolldown | eff. 20 | MomIgn (watch) | Evidence accumulating | June 1 ({_days_to_june1}d) |
| 2 | VolManaged-Equity | eff. 22 | Conviction entry | **CONVICTION-READY** ({_vm_status}) | After June 1 |
| 3 | VolManaged-Equity | eff. 22 | PB-MGC (core) | Needs 8w conviction + fwd Sharpe > 0.5 | ~6 months |
| 4 | Commodity-Carry v2 | eff. 19 | Watch slot | Needs v2 data or fwd evidence | Later |

- VolManaged tier restriction: **MICRO/REDUCED only** until forward evidence confirms crisis DD acceptable

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

    # Automation health
    auto_health_lines = "- Health check unavailable\n"
    try:
        from scripts.automation_health import run_health_check, format_brief_section
        health_results = run_health_check()
        auto_health_lines = format_brief_section(health_results)
    except Exception:
        pass

    content += f"""
---

### 10. Automation Health

{auto_health_lines}

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
        target = g.get("target", "Fill gap")
        content += f"| {g['priority']} | {g['factor']} | {g.get('core',0)}c+{g.get('probation',0)}p | {g['ideas']} | {target} |\n"

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


# ── Source Lead Lifecycle ─────────────────────────────────────────────────────

def _track_lead_pickup():
    """Track source lead consumption by content similarity, not URL matching.

    Root cause of prior notes_produced=0: Claw writes 'source URL: internal'
    when synthesizing, even if the idea came from a source lead. URL matching
    fails because Claw doesn't cite leads directly.

    Fix: extract title/description keywords from source leads and check if
    recent harvest notes contain similar content. This is fuzzy attribution —
    it won't be perfect, but it's directionally correct.
    """
    leads_dir = CLAW_INBOX / "source_leads"
    manifest_path = leads_dir / "_manifest.json"

    if not manifest_path.exists():
        return

    try:
        manifest = json.load(open(manifest_path))
    except Exception:
        return

    # Extract title keywords from each source lead file
    lead_files = list(leads_dir.glob("*_leads.md"))
    lead_signatures = {}  # {source_type: [set_of_keywords, ...]}
    lead_count = 0

    for lf in lead_files:
        if lf.name.startswith("_"):
            continue
        source_type = lf.stem.replace("_leads", "").replace("_prev", "")
        sigs = []
        try:
            for line in lf.read_text().split("\n"):
                if line.strip().startswith("- title:") or line.strip().startswith("- description:"):
                    text = line.split(":", 1)[-1].strip().lower()
                    # Extract distinctive words (4+ chars, not common)
                    words = set(w for w in text.split() if len(w) >= 4
                               and w not in {"this", "that", "with", "from", "your",
                                            "about", "their", "have", "been", "will",
                                            "more", "most", "some", "what", "when",
                                            "here", "into", "also", "just", "than"})
                    if len(words) >= 3:
                        sigs.append(words)
                        lead_count += 1
        except Exception:
            pass
        if sigs:
            lead_signatures[source_type] = sigs

    # Check recent harvest notes (last 3 days) for content overlap
    harvest_dir = CLAW_INBOX / "harvest"
    reviewed_dir = CLAW_INBOX.parent / "reviewed"
    recent_notes = []
    for d in [harvest_dir, reviewed_dir]:
        if d.exists():
            for note in d.glob("*.md"):
                # Recent = last 3 days
                if note.name[:10] >= (datetime.now() - __import__("datetime").timedelta(days=3)).strftime("%Y-%m-%d"):
                    recent_notes.append(note)

    # Also extract URLs from lead files for direct URL matching
    lead_urls_by_source = {}  # {source_type: set_of_url_prefixes}
    for lf in lead_files:
        if lf.name.startswith("_"):
            continue
        source_type = lf.stem.replace("_leads", "").replace("_prev", "")
        urls = set()
        try:
            for line in lf.read_text().split("\n"):
                stripped = line.strip()
                if stripped.startswith("- url:") or stripped.startswith("url:"):
                    url = stripped.split(":", 1)[-1].strip() if ":" in stripped else ""
                    if url and url.startswith("http"):
                        # Use domain + first path segment as match key
                        parts = url.split("/")
                        if len(parts) >= 4:
                            urls.add("/".join(parts[:4]).lower())
                        elif len(parts) >= 3:
                            urls.add("/".join(parts[:3]).lower())
        except Exception:
            pass
        if urls:
            lead_urls_by_source[source_type] = urls

    # Match notes to lead signatures + detect component types
    notes_by_source = {}
    components_by_source = {}  # {source: {type: count}}
    note_types_by_source = {}  # {source: {"full_strategy": N, "fragment": N}}

    for note in recent_notes:
        try:
            text = note.read_text()
            text_lower = text.lower()
            note_words = set(w for w in text_lower.split() if len(w) >= 4)

            # Extract source URL from note
            note_url = ""
            for line in text.split("\n"):
                if line.startswith("- source URL:"):
                    note_url = line.split(":", 1)[-1].strip().lower()
                    break

            matched_source = None

            # Method 1: URL prefix match (highest confidence)
            if note_url and note_url != "internal":
                for source_type, urls in lead_urls_by_source.items():
                    for lead_url in urls:
                        if lead_url in note_url or note_url.startswith(lead_url):
                            matched_source = source_type
                            break
                    if matched_source:
                        break

            # Method 2: Content similarity fallback
            if not matched_source:
                for source_type, sigs in lead_signatures.items():
                    for sig in sigs:
                        overlap = sig & note_words
                        if len(overlap) >= 3:
                            matched_source = source_type
                            break
                    if matched_source:
                        break

            if matched_source:
                notes_by_source[matched_source] = notes_by_source.get(matched_source, 0) + 1

                # Detect component_type in the note
                comp_type = "full_strategy"
                for line in text.split("\n"):
                    if line.startswith("- component_type:"):
                        comp_type = line.split(":", 1)[-1].strip()
                        break

                if matched_source not in note_types_by_source:
                    note_types_by_source[matched_source] = {"full_strategy": 0, "fragment": 0}
                if comp_type == "full_strategy":
                    note_types_by_source[matched_source]["full_strategy"] += 1
                else:
                    note_types_by_source[matched_source]["fragment"] += 1

                # Detect reusable components via keyword scan
                _COMP_HINTS = {
                    "entry_logic": ["entry", "enter when", "buy when", "go long"],
                    "exit_logic": ["exit", "stop loss", "take profit", "trailing"],
                    "filter": ["filter", "only when", "regime", "threshold"],
                    "sizing": ["position size", "vol target", "risk parity", "leverage"],
                    "session_effect": ["session", "overnight", "morning", "afternoon"],
                }
                detected = []
                for ctype, kws in _COMP_HINTS.items():
                    if sum(1 for kw in kws if kw in text_lower) >= 2:
                        detected.append(ctype)

                if detected:
                    if matched_source not in components_by_source:
                        components_by_source[matched_source] = {}
                    for ct in detected:
                        components_by_source[matched_source][ct] = components_by_source[matched_source].get(ct, 0) + 1
        except Exception:
            pass

    total_attributed = sum(notes_by_source.values())

    # Update manifest
    lifecycle = manifest.get("lifecycle", {})
    for key in lifecycle:
        entry = lifecycle[key]
        source = entry.get("source", "")

        # Mark as picked up if leads file exists (Claw reads source_leads/)
        if entry.get("status") == "fetched":
            # Check if the leads file for this source still exists
            leads_file = leads_dir / f"{source}_leads.md"
            if leads_file.exists():
                entry["picked_up"] = True
                entry["pickup_date"] = TODAY
                entry["status"] = "picked_up"

        # Update notes attribution
        if source in notes_by_source:
            entry["notes_produced"] = notes_by_source[source]

    manifest["last_pickup_check"] = NOW
    manifest["pending_leads"] = lead_count
    manifest["attribution_method"] = "content_similarity"
    manifest["last_attribution"] = {
        "date": TODAY,
        "notes_checked": len(recent_notes),
        "attributed_by_source": notes_by_source,
        "total_attributed": total_attributed,
        "note_types_by_source": note_types_by_source,
        "components_by_source": components_by_source,
    }

    try:
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
    except Exception:
        pass


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

    # 5. Track source lead pickup
    _track_lead_pickup()

    # 6. Refresh priorities (only on Sundays or if significant changes)
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
