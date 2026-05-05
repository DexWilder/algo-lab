#!/usr/bin/env python3
"""FQL Monthly System Review — full-system strategic governance report.

Produces a once-per-month synthesis covering roadmap, lanes, registry,
portfolio gaps, automation health, memory hygiene, and source/harvest yield.
The report is the artifact that prevents drift while the strategy factory
speeds up.

Safety contract (Phase A — manual CLI):
- Report-only. No registry / Lane A / portfolio / runtime / scheduler /
  checkpoint / hold-state mutation.
- All file writes target docs/reports/monthly_system_review/.
- All other reads are read-only against existing artifacts.

Cadence (Phase B — disabled plist provided): first Saturday of each month at
09:00 PT. The plist fires every Saturday; this script self-guards and exits
0 unless `today.day <= 7`. Same pattern as treasury-rolldown's first-business-
day guard.

Usage:
    python3 research/monthly_system_review.py                 # auto: prior month
    python3 research/monthly_system_review.py --month 2026-05 --save
    python3 research/monthly_system_review.py --dry-run       # no file write
    python3 research/monthly_system_review.py --first-saturday-guard
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPORTS_DIR = ROOT / "docs" / "reports" / "monthly_system_review"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
WATCHDOG_PATH = ROOT / "research" / "data" / "watchdog_state.json"
SCHEDULER_LOG_PATH = ROOT / "research" / "data" / "scheduler_log.json"
TRANSITION_LOG_PATH = ROOT / "research" / "data" / "strategy_transition_log.json"
FORGE_REPORTS_DIR = ROOT / "research" / "data" / "fql_forge" / "reports"
RESEARCH_REPORTS_DIR = ROOT / "research" / "reports"
RESEARCH_LOGS_DIR = ROOT / "research" / "logs"
LAUNCHAGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-Users-chasefisher" / "memory"
ROADMAP_QUEUE = ROOT / "docs" / "roadmap_queue.md"

EXPECTED_AGENTS = {
    "ai.openclaw.gateway",
    "com.fql.watchdog",
    "com.fql.claw-control-loop",
    "com.fql.forward-day",
    "com.fql.daily-research",
    "com.fql.operator-digest",
    "com.fql.twice-weekly-research",
    "com.fql.weekly-research",
    "com.fql.source-helpers",
    "com.fql.treasury-rolldown-monthly",
    "com.fql.forge-daily-loop",
}


@dataclass
class SectionOutput:
    title: str
    body: str
    wins: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


# ---------- helpers ----------

def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"_error": str(e)}


def _month_window(month_str: str) -> tuple[date, date]:
    y, m = (int(x) for x in month_str.split("-"))
    start = date(y, m, 1)
    end = date(y + (m // 12), (m % 12) + 1, 1) - timedelta(days=1)
    return start, end


def _launchctl_loaded() -> set[str]:
    try:
        out = subprocess.check_output(["launchctl", "list"], text=True, timeout=10)
    except Exception:
        return set()
    loaded = set()
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3:
            label = parts[2]
            if label.startswith("com.fql.") or label == "ai.openclaw.gateway":
                loaded.add(label)
    return loaded


# ---------- sections ----------

def section_2_roadmap_review(month: str) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    fql_state = MEMORY_DIR / "project_fql_state.md"
    roadmap_text = ROADMAP_QUEUE.read_text() if ROADMAP_QUEUE.exists() else ""
    state_text = fql_state.read_text() if fql_state.exists() else ""

    body_lines.append("### Active roadmap markers (from project memory)\n")
    if "Forge automation roadmap" in state_text:
        m = re.search(r"### Forge automation roadmap.*?(?=\n###|\Z)", state_text, re.DOTALL)
        if m:
            ladder = m.group(0)
            done_steps = re.findall(r"\*\*(.*?DONE.*?)\*\*", ladder)
            pending = re.findall(r"^\d+\.\s+\*\*([^*]+?)\*\*", ladder, re.MULTILINE)
            body_lines.append(f"- Ladder steps detected: {len(pending)}")
            body_lines.append(f"- Steps marked DONE: {len(done_steps)}")
            for d in done_steps:
                body_lines.append(f"  - DONE: {d.strip()}")
            if done_steps:
                wins.append(f"Roadmap progress: {len(done_steps)} step(s) completed in current ladder")

    if roadmap_text:
        body_lines.append(f"\n### Deferred items in `docs/roadmap_queue.md`\n")
        deferred = re.findall(r"^##+\s+(.+)$", roadmap_text, re.MULTILINE)
        body_lines.append(f"- Deferred-item headers: {len(deferred)}")
        for d in deferred[:8]:
            body_lines.append(f"  - {d.strip()}")
        if len(deferred) > 8:
            body_lines.append(f"  - ... and {len(deferred)-8} more")
    else:
        risks.append("`docs/roadmap_queue.md` not found")

    body_lines.append("\n### Roadmap drift check\n")
    body_lines.append("- TODO: compare claimed roadmap vs commit log evidence (deepen in v2).")
    recs.append("v2: parse commit log over the month and cross-check against claimed roadmap completions")

    return SectionOutput("Roadmap Review", "\n".join(body_lines), wins, risks, recs)


def section_3_lane_a_review(month: str, start: date, end: date) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    watchdog = _read_json(WATCHDOG_PATH)
    if "_error" not in watchdog:
        body_lines.append(f"### Watchdog last check\n")
        body_lines.append(f"- timestamp: `{watchdog.get('timestamp')}`")
        body_lines.append(f"- overall: `{watchdog.get('overall')}`")
        body_lines.append(f"- safe_mode: `{watchdog.get('safe_mode')}`")
        checks = watchdog.get("checks", {})
        if isinstance(checks, dict):
            failing = [k for k, v in checks.items()
                       if isinstance(v, dict) and v.get("status") not in (None, "OK", "ok", "PASS", "pass", "CLEAR")]
            body_lines.append(f"- non-OK checks: {len(failing)}")
            for f in failing[:10]:
                body_lines.append(f"  - `{f}`: {checks[f].get('status')}")
            if failing:
                risks.append(f"{len(failing)} watchdog check(s) not OK on last run")
            else:
                wins.append("All watchdog checks OK on last run")
    else:
        risks.append(f"Watchdog state unreadable: {watchdog['_error']}")

    transitions = _read_json(TRANSITION_LOG_PATH)
    body_lines.append(f"\n### Strategy transitions this month\n")
    if isinstance(transitions, list):
        in_window = [t for t in transitions
                     if isinstance(t, dict) and t.get("date", "") >= start.isoformat() and t.get("date", "") <= end.isoformat()]
        body_lines.append(f"- transitions in window: {len(in_window)}")
        for t in in_window[:10]:
            body_lines.append(f"  - {t.get('date')}: {t.get('strategy_id')} → {t.get('to_status', t.get('action'))}")
    else:
        body_lines.append("- transition log not a list; shape changed?")
        risks.append("strategy_transition_log shape unexpected")

    body_lines.append(f"\n### Forward-runner log freshness\n")
    forward_logs = sorted(RESEARCH_LOGS_DIR.glob("forward_runner*.log")) if RESEARCH_LOGS_DIR.exists() else []
    if forward_logs:
        latest = forward_logs[-1]
        age_h = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 3600
        body_lines.append(f"- latest: `{latest.name}` ({age_h:.1f}h old)")
        if age_h > 36:
            risks.append(f"Forward runner log is {age_h:.0f}h stale")
    else:
        body_lines.append("- no forward_runner*.log files found")

    return SectionOutput("Lane A Review (protected/live state)", "\n".join(body_lines), wins, risks, recs)


def section_4_forge_review(month: str, start: date, end: date) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    if not FORGE_REPORTS_DIR.exists():
        return SectionOutput("Lane B / Forge Review", "Forge reports dir does not exist.", risks=["Forge dir missing"])

    json_reports = sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.json"))
    in_window = []
    for jp in json_reports:
        m = re.search(r"forge_daily_(\d{4}-\d{2}-\d{2})\.json", jp.name)
        if m:
            d = date.fromisoformat(m.group(1))
            if start <= d <= end:
                data = _read_json(jp)
                if "_error" not in data:
                    in_window.append((d, data))

    body_lines.append(f"### Forge fires in window\n")
    body_lines.append(f"- daily reports in {month}: {len(in_window)}")

    totals = Counter()
    candidate_verdicts = {}
    for d, data in in_window:
        for k, v in data.get("verdict_counts", {}).items():
            totals[k] += v
        for r in data.get("results", []):
            cid = r.get("candidate")
            verdict = r.get("verdict")
            candidate_verdicts.setdefault(cid, []).append(verdict)

    body_lines.append(f"- verdict totals: {dict(totals)}")
    body_lines.append(f"- distinct candidates evaluated: {len(candidate_verdicts)}")

    pass_only = [c for c, vs in candidate_verdicts.items() if vs and all(v == "PASS" for v in vs)]
    kill_only = [c for c, vs in candidate_verdicts.items() if vs and all(v == "KILL" for v in vs)]
    body_lines.append(f"\n### Best/worst candidates this month\n")
    body_lines.append(f"- PASS-every-fire ({len(pass_only)}): {pass_only[:8]}")
    body_lines.append(f"- KILL-every-fire ({len(kill_only)}): {kill_only[:8]}")

    if pass_only:
        wins.append(f"{len(pass_only)} candidate(s) PASS-every-fire this month")
        recs.append("Consider batch register pre-flight for PASS-every-fire candidates not yet in registry")
    if kill_only:
        recs.append(f"Prune {len(kill_only)} KILL-every-fire candidate(s) from runner pool to free rotation slots")

    tripwires = sorted(FORGE_REPORTS_DIR.glob("_TRIPWIRE_*.md"))
    body_lines.append(f"\n### Tripwire events\n- tripwire files present: {len(tripwires)}")
    for tw in tripwires:
        body_lines.append(f"  - `{tw.name}`")
        risks.append(f"Unresolved Forge tripwire: {tw.name}")

    body_lines.append(f"\n### Autonomous-loop health\n")
    if len(in_window) == 0:
        risks.append("Zero Forge fires in window — autonomous loop may have failed to fire")
    elif len(in_window) < 5:
        body_lines.append(f"- low fire count ({len(in_window)}); may be partial-month report or activation lag")
    else:
        wins.append(f"Forge fired {len(in_window)} time(s) in window")

    return SectionOutput("Lane B / Forge Review", "\n".join(body_lines), wins, risks, recs)


def section_5_registry_review(month: str, start: date, end: date) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    registry = _read_json(REGISTRY_PATH)
    if "_error" in registry:
        return SectionOutput("Strategy Registry Review", f"Registry read failed: {registry['_error']}", risks=["registry unreadable"])

    strategies = registry.get("strategies", [])
    body_lines.append(f"### Registry summary\n")
    body_lines.append(f"- total strategies: {len(strategies)}")
    body_lines.append(f"- schema version: {registry.get('_schema_version')}")

    by_status = Counter(s.get("status") for s in strategies)
    body_lines.append(f"\n### By status\n")
    for status, n in by_status.most_common():
        body_lines.append(f"- {status}: {n}")

    by_family = Counter(s.get("family") for s in strategies)
    body_lines.append(f"\n### By family (top 8)\n")
    for fam, n in by_family.most_common(8):
        body_lines.append(f"- {fam}: {n}")

    by_asset = Counter(s.get("asset") for s in strategies)
    body_lines.append(f"\n### By asset (top 10)\n")
    for asset, n in by_asset.most_common(10):
        body_lines.append(f"- {asset}: {n}")

    components_populated = sum(1 for s in strategies
                               if isinstance(s.get("relationships"), dict)
                               and s["relationships"].get("components_used"))
    salvaged_populated = sum(1 for s in strategies
                             if isinstance(s.get("relationships"), dict)
                             and s["relationships"].get("salvaged_from"))
    body_lines.append(f"\n### Relationship-field population (Item 2 plumbing)\n")
    body_lines.append(f"- components_used populated: {components_populated} / {len(strategies)} ({100*components_populated/max(1,len(strategies)):.1f}%)")
    body_lines.append(f"- salvaged_from populated: {salvaged_populated} / {len(strategies)} ({100*salvaged_populated/max(1,len(strategies)):.1f}%)")
    if salvaged_populated == 0:
        risks.append("Item 2 cross-pollination criterion: still 0 salvaged_from entries")

    probation = [s for s in strategies if s.get("status") == "probation"]
    body_lines.append(f"\n### Probation roster ({len(probation)})\n")
    for s in probation:
        body_lines.append(f"- {s.get('strategy_id')} ({s.get('asset')}, {s.get('family')})")
    if len(probation) > 8:
        risks.append(f"Probation roster size {len(probation)} — review for stale entries")

    if components_populated < 30:
        recs.append("Cross-pollination plumbing thin — prioritize batch registers that populate components_used")

    return SectionOutput("Strategy Registry Review", "\n".join(body_lines), wins, risks, recs)


def section_6_portfolio_gap(month: str) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    registry = _read_json(REGISTRY_PATH)
    strategies = registry.get("strategies", []) if "_error" not in registry else []

    by_asset = Counter(s.get("asset") for s in strategies)
    by_family = Counter(s.get("family") for s in strategies)
    by_session = Counter(s.get("session") for s in strategies)

    body_lines.append(f"### Coverage tallies\n")
    body_lines.append(f"- distinct assets: {len(by_asset)}")
    body_lines.append(f"- distinct families: {len(by_family)}")
    body_lines.append(f"- distinct sessions: {len(by_session)}")

    body_lines.append(f"\n### Sessions\n")
    for sess, n in by_session.most_common():
        body_lines.append(f"- {sess}: {n}")

    biggest_family = by_family.most_common(1)
    if biggest_family:
        fam, n = biggest_family[0]
        share = n / max(1, len(strategies))
        body_lines.append(f"\n### Concentration\n")
        body_lines.append(f"- biggest family: `{fam}` with {n} strategies ({100*share:.1f}% of registry)")
        if share > 0.30:
            risks.append(f"Family concentration: `{fam}` holds {100*share:.0f}% of registry")

    biggest_asset = by_asset.most_common(1)
    if biggest_asset:
        asset, n = biggest_asset[0]
        share = n / max(1, len(strategies))
        body_lines.append(f"- biggest asset: `{asset}` with {n} strategies ({100*share:.1f}% of registry)")
        if share > 0.40:
            risks.append(f"Asset concentration: `{asset}` holds {100*share:.0f}% of registry")

    saved_dashboards = sorted(RESEARCH_REPORTS_DIR.glob("portfolio_gap*.md")) if RESEARCH_REPORTS_DIR.exists() else []
    body_lines.append(f"\n### Pre-existing portfolio_gap_dashboard outputs\n")
    body_lines.append(f"- saved dashboards on disk: {len(saved_dashboards)}")
    if saved_dashboards:
        body_lines.append(f"- latest: `{saved_dashboards[-1].name}`")
        recs.append("v2: parse latest portfolio_gap_dashboard output and surface its top-3 gaps inline")
    else:
        recs.append("Run `python3 scripts/portfolio_gap_dashboard.py --save` to seed gap data")

    return SectionOutput("Portfolio / Gap Review", "\n".join(body_lines), wins, risks, recs)


def section_7_automation_review(month: str, start: date, end: date) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    loaded = _launchctl_loaded()
    body_lines.append(f"### Loaded launchd agents\n")
    body_lines.append(f"- loaded: {len(loaded)}")
    for a in sorted(loaded):
        body_lines.append(f"  - `{a}`")

    missing = EXPECTED_AGENTS - loaded
    extra = loaded - EXPECTED_AGENTS
    if missing:
        body_lines.append(f"\n- **MISSING (expected but not loaded):** {sorted(missing)}")
        risks.append(f"Missing launchd agents: {sorted(missing)}")
    if extra:
        body_lines.append(f"- unrecognized loaded agents: {sorted(extra)}")
    if not missing and not extra:
        wins.append(f"All {len(EXPECTED_AGENTS)} expected launchd agents loaded")

    body_lines.append(f"\n### Recent launchd plist files in scripts/ vs LaunchAgents\n")
    repo_plists = sorted((ROOT / "scripts").glob("com.fql.*.plist")) if (ROOT / "scripts").exists() else []
    deployed = sorted(LAUNCHAGENTS_DIR.glob("com.fql.*.plist")) if LAUNCHAGENTS_DIR.exists() else []
    body_lines.append(f"- plists in repo scripts/: {len(repo_plists)}")
    body_lines.append(f"- plists deployed to LaunchAgents/: {len(deployed)}")

    body_lines.append(f"\n### Recent stderr log audit\n")
    log_dir = RESEARCH_LOGS_DIR
    stderr_logs = list(log_dir.glob("*stderr*.log")) if log_dir.exists() else []
    nonempty = []
    for sl in stderr_logs:
        try:
            if sl.stat().st_size > 0:
                nonempty.append((sl.name, sl.stat().st_size))
        except Exception:
            pass
    body_lines.append(f"- stderr log files: {len(stderr_logs)} (non-empty: {len(nonempty)})")
    for name, sz in nonempty[:5]:
        body_lines.append(f"  - `{name}`: {sz} bytes")

    body_lines.append(f"\n### Tripwire events this month\n")
    tw_files = list(FORGE_REPORTS_DIR.glob("_TRIPWIRE_*.md")) if FORGE_REPORTS_DIR.exists() else []
    body_lines.append(f"- Forge tripwire files present: {len(tw_files)}")

    return SectionOutput("Automation Review", "\n".join(body_lines), wins, risks, recs)


def section_8_memory_docs_hygiene(month: str) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    memory_files = list(MEMORY_DIR.glob("*.md"))
    body_lines.append(f"### Memory file count\n- total: {len(memory_files)}")

    fql_state = MEMORY_DIR / "project_fql_state.md"
    if fql_state.exists():
        text = fql_state.read_text()
        loaded = _launchctl_loaded()
        # Catch both backticked (`com.fql.x`) and bare (com.fql.x) references
        claimed = set(re.findall(r"\b(com\.fql\.[a-z\-]+)\b", text))
        claimed_missing = claimed - loaded
        loaded_unclaimed = loaded - claimed - {"ai.openclaw.gateway"}
        body_lines.append(f"\n### Memory automation claims vs reality\n")
        body_lines.append(f"- agents named in `project_fql_state.md`: {len(claimed)}")
        body_lines.append(f"- claimed-but-not-loaded: {sorted(claimed_missing)}")
        body_lines.append(f"- loaded-but-not-mentioned: {sorted(loaded_unclaimed)}")
        if claimed_missing:
            risks.append(f"Memory drift: {sorted(claimed_missing)} claimed in memory but not loaded")
        if loaded_unclaimed:
            risks.append(f"Memory drift: {sorted(loaded_unclaimed)} loaded but not in memory")

        registry = _read_json(REGISTRY_PATH)
        actual_count = len(registry.get("strategies", [])) if "_error" not in registry else None
        m = re.search(r"(\d+)\s+strategies\s*\(", text)
        if m and actual_count is not None:
            claimed_count = int(m.group(1))
            body_lines.append(f"\n### Registry-count claim vs reality\n")
            body_lines.append(f"- memory claims: {claimed_count}, actual: {actual_count}")
            if abs(claimed_count - actual_count) > 5:
                risks.append(f"Memory registry count drift: {claimed_count} claimed vs {actual_count} actual")

    if not (ROOT / "docs" / "_DRAFT_2026-05-01_stale_probation_batch_review.md").exists():
        body_lines.append("\n- Note: pre-flight drafts referenced in memory not all present on disk (expected; drafts are session-local)")

    body_lines.append(f"\n### Hygiene scan summary\n")
    body_lines.append(f"- TODO v2: scan all .md docs for stale dates / broken cross-references / claimed-vs-actual JSON divergences")
    recs.append("Build dedicated memory hygiene job (already on roadmap step #2) — this section is a thin sample")

    return SectionOutput("Memory / Docs Hygiene", "\n".join(body_lines), wins, risks, recs)


def section_9_source_harvest(month: str) -> SectionOutput:
    body_lines = []
    wins, risks, recs = [], [], []

    source_evidence = MEMORY_DIR / "project_source_quality_evidence.md"
    if source_evidence.exists():
        body_lines.append(f"### Source quality evidence (memory)\n")
        body_lines.append(f"- file present: `{source_evidence.name}` ({source_evidence.stat().st_size} bytes)")
    else:
        risks.append("project_source_quality_evidence.md missing")

    inbox = ROOT / "inbox"
    if inbox.exists():
        body_lines.append(f"\n### Inbox state\n")
        priorities = inbox / "_priorities.md"
        family_queue = inbox / "_family_queue.md"
        body_lines.append(f"- `_priorities.md` present: {priorities.exists()}")
        body_lines.append(f"- `_family_queue.md` present: {family_queue.exists()}")
        for sub in ["harvest", "refinement", "clustering", "assessment"]:
            d = inbox / sub
            if d.exists():
                items = list(d.glob("*"))
                body_lines.append(f"- `inbox/{sub}/`: {len(items)} item(s)")

    body_lines.append(f"\n### Source-helper recent runs\n")
    sh_logs = sorted(RESEARCH_LOGS_DIR.glob("source_helpers*.log")) if RESEARCH_LOGS_DIR.exists() else []
    body_lines.append(f"- source_helpers*.log files: {len(sh_logs)}")
    if sh_logs:
        latest = sh_logs[-1]
        age_d = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
        body_lines.append(f"- latest: `{latest.name}` ({age_d}d old)")

    body_lines.append(f"\n### Closed-loop status (Forge → source-helpers)\n")
    body_lines.append(f"- feedback edge: NOT WIRED YET (per roadmap step #6, highest-ROI architectural target)")
    risks.append("Closed-loop Forge→source-helpers feedback not yet wired (roadmap step #6)")
    recs.append("Build closed-loop feedback edge: Forge PASSes up-weight source-helper priorities")

    return SectionOutput("Source / Harvest Review", "\n".join(body_lines), wins, risks, recs)


# ---------- composers ----------

def compose_executive_summary(month: str, sections: list[SectionOutput]) -> SectionOutput:
    wins = [w for s in sections for w in s.wins]
    risks = [r for s in sections for r in s.risks]
    recs = [r for s in sections for r in s.recommendations]

    body = []
    body.append(f"### System health overview\n")
    body.append(f"- review window: **{month}**")
    body.append(f"- sections produced: {len(sections)}")
    body.append(f"- wins surfaced: {len(wins)}")
    body.append(f"- risks surfaced: {len(risks)}")
    body.append(f"- recommendations surfaced: {len(recs)}")

    body.append(f"\n### Major wins\n")
    for w in wins[:8] or ["(none surfaced this month)"]:
        body.append(f"- {w}")

    body.append(f"\n### Major risks\n")
    for r in risks[:8] or ["(none surfaced this month)"]:
        body.append(f"- {r}")

    body.append(f"\n### Top recommended next actions\n")
    for r in recs[:5] or ["(none surfaced this month)"]:
        body.append(f"- {r}")

    return SectionOutput("Executive Summary", "\n".join(body))


def compose_recommendations(sections: list[SectionOutput]) -> SectionOutput:
    recs = [(s.title, r) for s in sections for r in s.recommendations]
    body = [f"Aggregated from all sections. **Operator decides** which to act on next month.\n"]
    body.append("### Keep / Change / Add / Remove\n")
    if not recs:
        body.append("(no recommendations surfaced)")
    else:
        for title, r in recs:
            body.append(f"- **[{title}]** {r}")
    body.append(f"\n### Highest-ROI next builds (per current roadmap)\n")
    body.append("- Step #2 — memory hygiene job (next-session priority)")
    body.append("- Step #3 — B.2 morning digest (unlocks higher cadence)")
    body.append("- Step #6 — closed-loop Forge → source-helpers feedback (architectural target)")
    body.append(f"\n### Safety affirmation\n")
    body.append("- Report-only. No registry / Lane A / portfolio / runtime / scheduler / checkpoint changes occurred during generation.")
    body.append("- All recommendations require operator approval before execution.")
    return SectionOutput("Recommendations", "\n".join(body))


def render_report(month: str, sections: list[SectionOutput], generated_at: datetime) -> str:
    out = [f"# FQL Monthly System Review — {month}\n"]
    out.append(f"**Generated:** {generated_at.isoformat(timespec='seconds')}")
    out.append(f"**Scope:** full-system strategic governance (read-only)\n")
    out.append(f"**Safety contract:** report-only; no registry / Lane A / portfolio / runtime / scheduler / checkpoint mutation.\n")
    out.append("---\n")
    for i, sec in enumerate(sections, start=1):
        out.append(f"## {i}. {sec.title}\n")
        out.append(sec.body)
        out.append("\n---\n")
    return "\n".join(out)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="FQL Monthly System Review (report-only)")
    ap.add_argument("--month", help="YYYY-MM (default: prior month)")
    ap.add_argument("--save", action="store_true", help="Write report to docs/reports/monthly_system_review/")
    ap.add_argument("--dry-run", action="store_true", help="Generate but do not write")
    ap.add_argument("--first-saturday-guard", action="store_true",
                    help="Exit 0 unless today is the first Saturday of the month (for launchd self-guard)")
    args = ap.parse_args()

    today = date.today()

    if args.first_saturday_guard:
        if today.weekday() != 5 or today.day > 7:
            print(f"[GUARD] today {today} is not the first Saturday of the month — exiting cleanly")
            return
        print(f"[GUARD] today {today} is the first Saturday — proceeding")

    if not args.month:
        first_of_this_month = today.replace(day=1)
        prior = first_of_this_month - timedelta(days=1)
        args.month = f"{prior.year}-{prior.month:02d}"

    start, end = _month_window(args.month)
    print(f"FQL Monthly System Review — month={args.month} window=[{start}, {end}]")
    print("=" * 78)

    body_sections = [
        section_2_roadmap_review(args.month),
        section_3_lane_a_review(args.month, start, end),
        section_4_forge_review(args.month, start, end),
        section_5_registry_review(args.month, start, end),
        section_6_portfolio_gap(args.month),
        section_7_automation_review(args.month, start, end),
        section_8_memory_docs_hygiene(args.month),
        section_9_source_harvest(args.month),
    ]
    exec_summary = compose_executive_summary(args.month, body_sections)
    recommendations = compose_recommendations(body_sections)

    all_sections = [exec_summary] + body_sections + [recommendations]
    generated_at = datetime.now()
    report = render_report(args.month, all_sections, generated_at)

    print(f"Report length: {len(report)} chars, {report.count(chr(10))} lines, {len(all_sections)} sections")
    print(f"Wins: {sum(len(s.wins) for s in body_sections)}")
    print(f"Risks: {sum(len(s.risks) for s in body_sections)}")
    print(f"Recommendations: {sum(len(s.recommendations) for s in body_sections)}")

    if args.dry_run:
        print("\n[DRY-RUN] not writing")
        print("\n--- preview (first 60 lines) ---")
        print("\n".join(report.splitlines()[:60]))
        return

    if not args.save:
        print("\n(use --save to write to docs/reports/monthly_system_review/, or --dry-run to preview)")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{args.month}_FQL_SYSTEM_REVIEW.md"
    out_path.write_text(report)
    print(f"\n[WRITE] {out_path}")
    print("\n[SAFETY] Report-only. No mutation of registry / Lane A / portfolio / runtime / scheduler / checkpoint.")


if __name__ == "__main__":
    main()
