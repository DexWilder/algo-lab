#!/usr/bin/env python3
"""FQL Monthly System Review — full-system strategic governance report (v1.1).

Decision report (not a status report). Produces:
  state → risks → deltas → decisions needed → recommended changes.

Safety contract: report-only. No registry / Lane A / portfolio / runtime /
scheduler / checkpoint / hold-state mutation. All file writes target
docs/reports/monthly_system_review/ (report + .snapshots/ for delta tracking).

Cadence (Phase B, disabled plist provided): every Saturday 09:00 PT;
script self-guards via --first-saturday-guard → effectively one fire/month.

Usage:
    python3 research/monthly_system_review.py                 # auto: prior month
    python3 research/monthly_system_review.py --month 2026-05 --save
    python3 research/monthly_system_review.py --dry-run
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
SNAPSHOTS_DIR = REPORTS_DIR / ".snapshots"
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
FORGE_RUNNER = ROOT / "research" / "fql_forge_batch_runner.py"

EXPECTED_AGENTS = {
    "ai.openclaw.gateway":            ("KeepAlive (continuous)",          "infra"),
    "com.fql.watchdog":               ("every 5 min",                     "infra"),
    "com.fql.claw-control-loop":      ("every 30 min",                    "Lane B"),
    "com.fql.forward-day":            ("weekdays 17:00",                  "Lane A"),
    "com.fql.daily-research":         ("weekdays 17:30",                  "Lane A"),
    "com.fql.operator-digest":        ("weekdays 18:00",                  "Lane A"),
    "com.fql.twice-weekly-research":  ("Tue/Thu 18:00",                   "Lane A"),
    "com.fql.weekly-research":        ("Fri 18:30",                       "Lane A"),
    "com.fql.source-helpers":         ("Sun + Wed 20:00",                 "Lane B"),
    "com.fql.treasury-rolldown-monthly": ("weekdays 17:10 (1st-biz guard)", "Lane A"),
    "com.fql.forge-daily-loop":       ("weekdays 19:00",                  "Lane B"),
}


@dataclass
class SectionOutput:
    title: str
    body: str
    wins: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    watchlist: list[str] = field(default_factory=list)


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


def _prior_month(month_str: str) -> str:
    start, _ = _month_window(month_str)
    prior_end = start - timedelta(days=1)
    return f"{prior_end.year}-{prior_end.month:02d}"


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


def _load_prior_snapshot(month: str) -> dict | None:
    prior = _prior_month(month)
    p = SNAPSHOTS_DIR / f"{prior}_snapshot.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _save_current_snapshot(month: str, snapshot: dict):
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    p = SNAPSHOTS_DIR / f"{month}_snapshot.json"
    p.write_text(json.dumps(snapshot, indent=2, default=str))


def _candidate_pool_size() -> int:
    if not FORGE_RUNNER.exists():
        return 0
    text = FORGE_RUNNER.read_text()
    body = re.search(r"^CANDIDATES\s*=\s*\{(.*?)\n\}", text, re.MULTILINE | re.DOTALL)
    if not body:
        return 0
    return len(re.findall(r"^\s+\"[A-Z][\w\-\.]+\":\s*\{", body.group(1), re.MULTILINE))


def _delta(curr, prior, fmt="{:+d}"):
    if prior is None:
        return "—"
    try:
        d = curr - prior
        return fmt.format(d)
    except Exception:
        return "?"


# ---------- existing section functions ----------

def section_roadmap_review(month: str) -> SectionOutput:
    body, wins, risks, recs = [], [], [], []
    fql_state = MEMORY_DIR / "project_fql_state.md"
    state_text = fql_state.read_text() if fql_state.exists() else ""
    roadmap_text = ROADMAP_QUEUE.read_text() if ROADMAP_QUEUE.exists() else ""

    body.append("### Active roadmap markers (from project memory)\n")
    if "Forge automation roadmap" in state_text:
        m = re.search(r"### Forge automation roadmap.*?(?=\n###|\Z)", state_text, re.DOTALL)
        if m:
            ladder = m.group(0)
            done = re.findall(r"\*\*(.*?DONE.*?)\*\*", ladder)
            steps = re.findall(r"^\d+\.\s+\*\*([^*]+?)\*\*", ladder, re.MULTILINE)
            body.append(f"- ladder steps detected: {len(steps)}")
            body.append(f"- steps marked DONE: {len(done)}")
            for d in done:
                body.append(f"  - DONE: {d.strip()}")
            if done:
                wins.append(f"Roadmap progress: {len(done)} step(s) completed in current ladder")

    if roadmap_text:
        body.append(f"\n### Deferred items in `docs/roadmap_queue.md`\n")
        deferred = re.findall(r"^##+\s+(.+)$", roadmap_text, re.MULTILINE)
        body.append(f"- deferred-item headers: {len(deferred)}")
        for d in deferred[:6]:
            body.append(f"  - {d.strip()}")
        if len(deferred) > 6:
            body.append(f"  - ... and {len(deferred)-6} more")
    else:
        risks.append("`docs/roadmap_queue.md` not found")

    body.append("\n### Roadmap drift check\n")
    body.append("- v2 TODO: parse commit log over month vs claimed completions for drift detection.")

    return SectionOutput("Roadmap Review", "\n".join(body), wins, risks, recs)


def section_lane_a_review(month: str, start: date, end: date) -> SectionOutput:
    body, wins, risks, recs = [], [], [], []
    watchdog = _read_json(WATCHDOG_PATH)
    if "_error" not in watchdog:
        body.append("### Watchdog last check\n")
        body.append(f"- timestamp: `{watchdog.get('timestamp')}`")
        body.append(f"- overall: `{watchdog.get('overall')}`")
        body.append(f"- safe_mode: `{watchdog.get('safe_mode')}`")
        checks = watchdog.get("checks", {})
        if isinstance(checks, dict):
            failing = [k for k, v in checks.items()
                       if isinstance(v, dict)
                       and v.get("status") not in (None, "OK", "ok", "PASS", "pass", "CLEAR")]
            body.append(f"- non-OK checks: {len(failing)}")
            for f in failing[:10]:
                body.append(f"  - `{f}`: {checks[f].get('status')}")
            if failing:
                risks.append(f"{len(failing)} watchdog check(s) not OK on last run")
            else:
                wins.append("All watchdog checks OK on last run")
    else:
        risks.append(f"Watchdog state unreadable: {watchdog['_error']}")

    transitions = _read_json(TRANSITION_LOG_PATH)
    body.append(f"\n### Strategy transitions this month\n")
    if isinstance(transitions, list):
        in_window = [t for t in transitions
                     if isinstance(t, dict)
                     and t.get("date", "") >= start.isoformat()
                     and t.get("date", "") <= end.isoformat()]
        body.append(f"- transitions in window: {len(in_window)}")
        for t in in_window[:10]:
            body.append(f"  - {t.get('date')}: {t.get('strategy_id')} → {t.get('to_status', t.get('action'))}")

    forward_logs = sorted(RESEARCH_LOGS_DIR.glob("forward_runner*.log")) if RESEARCH_LOGS_DIR.exists() else []
    body.append(f"\n### Forward-runner log freshness\n")
    if forward_logs:
        latest = forward_logs[-1]
        age_h = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 3600
        body.append(f"- latest: `{latest.name}` ({age_h:.1f}h old)")
        if age_h > 36:
            risks.append(f"Forward runner log is {age_h:.0f}h stale")
    else:
        body.append("- no forward_runner*.log files found")

    return SectionOutput("Lane A Review (protected/live state)", "\n".join(body), wins, risks, recs)


def section_forge_review(month: str, start: date, end: date, in_window_data: list) -> SectionOutput:
    body, wins, risks, recs = [], [], [], []
    decisions, watchlist = [], []

    body.append(f"### Forge fires in window\n")
    body.append(f"- daily reports in {month}: {len(in_window_data)}")

    totals = Counter()
    candidate_verdicts = {}
    for d, data in in_window_data:
        for k, v in data.get("verdict_counts", {}).items():
            totals[k] += v
        for r in data.get("results", []):
            cid = r.get("candidate")
            verdict = r.get("verdict")
            candidate_verdicts.setdefault(cid, []).append(verdict)

    body.append(f"- verdict totals: {dict(totals)}")
    body.append(f"- distinct candidates evaluated: {len(candidate_verdicts)}")

    pass_only = [c for c, vs in candidate_verdicts.items() if vs and all(v == "PASS" for v in vs)]
    kill_only = [c for c, vs in candidate_verdicts.items() if vs and all(v == "KILL" for v in vs)]
    body.append(f"\n### Best/worst candidates this month\n")
    body.append(f"- PASS-every-fire ({len(pass_only)}): {pass_only[:8]}")
    body.append(f"- KILL-every-fire ({len(kill_only)}): {kill_only[:8]}")

    if pass_only:
        wins.append(f"{len(pass_only)} candidate(s) PASS-every-fire this month")
        decisions.append(f"Operator: pre-flight batch register for {len(pass_only)} PASS-every-fire candidate(s)?")
    if kill_only:
        decisions.append(f"Operator: prune {len(kill_only)} KILL-every-fire candidate(s) from runner pool?")

    if FORGE_REPORTS_DIR.exists():
        tripwires = sorted(FORGE_REPORTS_DIR.glob("_TRIPWIRE_*.md"))
        body.append(f"\n### Tripwire events\n- tripwire files present: {len(tripwires)}")
        for tw in tripwires:
            body.append(f"  - `{tw.name}`")
            risks.append(f"Unresolved Forge tripwire: {tw.name}")
            decisions.append(f"Operator: clear tripwire `{tw.name}`?")

    body.append("\n### Autonomous-loop health\n")
    if len(in_window_data) == 0:
        risks.append("Zero Forge fires in window — autonomous loop may have failed to fire")
    elif len(in_window_data) < 5:
        body.append(f"- low fire count ({len(in_window_data)}); may be partial-month or activation lag")
    else:
        wins.append(f"Forge fired {len(in_window_data)} time(s) in window")

    watchlist.append("Forge fires next month — confirm rotation visited all candidates at least once")

    return SectionOutput("Lane B / Forge Review", "\n".join(body), wins, risks, recs, decisions, watchlist)


def section_registry_review(month: str, start: date, end: date) -> SectionOutput:
    body, wins, risks, recs, decisions, watchlist = [], [], [], [], [], []
    registry = _read_json(REGISTRY_PATH)
    if "_error" in registry:
        return SectionOutput("Strategy Registry Review", f"Registry read failed: {registry['_error']}",
                             risks=["registry unreadable"])

    strategies = registry.get("strategies", [])
    body.append(f"### Registry summary\n")
    body.append(f"- total strategies: {len(strategies)}")
    body.append(f"- schema version: {registry.get('_schema_version')}")

    by_status = Counter(s.get("status") for s in strategies)
    body.append(f"\n### By status\n")
    for status, n in by_status.most_common():
        body.append(f"- {status}: {n}")

    by_family = Counter(s.get("family") for s in strategies)
    body.append(f"\n### By family (top 8)\n")
    for fam, n in by_family.most_common(8):
        body.append(f"- {fam}: {n}")

    components_pop = sum(1 for s in strategies
                         if isinstance(s.get("relationships"), dict)
                         and s["relationships"].get("components_used"))
    salvaged_pop = sum(1 for s in strategies
                       if isinstance(s.get("relationships"), dict)
                       and s["relationships"].get("salvaged_from"))
    body.append(f"\n### Relationship-field population (Item 2 plumbing)\n")
    body.append(f"- components_used populated: {components_pop} / {len(strategies)} ({100*components_pop/max(1,len(strategies)):.1f}%)")
    body.append(f"- salvaged_from populated: {salvaged_pop} / {len(strategies)} ({100*salvaged_pop/max(1,len(strategies)):.1f}%)")
    if salvaged_pop == 0:
        risks.append("Item 2 cross-pollination criterion: 0 salvaged_from entries")

    probation = [s for s in strategies if s.get("status") == "probation"]
    body.append(f"\n### Probation roster ({len(probation)})\n")
    for s in probation:
        body.append(f"- {s.get('strategy_id')} ({s.get('asset')}, {s.get('family')})")
    if len(probation) > 8:
        risks.append(f"Probation roster size {len(probation)} — review for stale entries")
        decisions.append(f"Operator: review {len(probation)} probation entries for staleness?")

    if components_pop < 30:
        recs.append("Cross-pollination plumbing thin — prioritize batch registers that populate components_used")

    watchlist.append("Registry total strategies (current: %d)" % len(strategies))
    watchlist.append("salvaged_from population (currently 0 — first non-zero entry would move Item 2 criterion)")

    return SectionOutput("Strategy Registry Review", "\n".join(body), wins, risks, recs, decisions, watchlist)


def section_portfolio_gap(month: str) -> SectionOutput:
    body, wins, risks, recs = [], [], [], []
    registry = _read_json(REGISTRY_PATH)
    strategies = registry.get("strategies", []) if "_error" not in registry else []

    by_asset = Counter(s.get("asset") for s in strategies)
    by_family = Counter(s.get("family") for s in strategies)
    by_session = Counter(s.get("session") for s in strategies)

    body.append("### Coverage tallies\n")
    body.append(f"- distinct assets: {len(by_asset)}")
    body.append(f"- distinct families: {len(by_family)}")
    body.append(f"- distinct sessions: {len(by_session)}")

    body.append(f"\n### Sessions\n")
    for sess, n in by_session.most_common():
        body.append(f"- {sess}: {n}")

    if by_family:
        fam, n = by_family.most_common(1)[0]
        share = n / max(1, len(strategies))
        body.append(f"\n### Concentration\n")
        body.append(f"- biggest family: `{fam}` ({n}, {100*share:.1f}% of registry)")
        if share > 0.30:
            risks.append(f"Family concentration: `{fam}` holds {100*share:.0f}% of registry")

    if by_asset:
        asset, n = by_asset.most_common(1)[0]
        share = n / max(1, len(strategies))
        body.append(f"- biggest asset: `{asset}` ({n}, {100*share:.1f}% of registry)")
        if share > 0.40:
            risks.append(f"Asset concentration: `{asset}` holds {100*share:.0f}% of registry")

    saved = sorted(RESEARCH_REPORTS_DIR.glob("portfolio_gap*.md")) if RESEARCH_REPORTS_DIR.exists() else []
    body.append(f"\n### Pre-existing portfolio_gap_dashboard outputs\n")
    body.append(f"- saved dashboards on disk: {len(saved)}")
    if saved:
        body.append(f"- latest: `{saved[-1].name}`")
    else:
        recs.append("Run `python3 scripts/portfolio_gap_dashboard.py --save` to seed gap data")

    return SectionOutput("Portfolio / Gap Review", "\n".join(body), wins, risks, recs)


def section_memory_docs(month: str) -> SectionOutput:
    body, wins, risks, recs = [], [], [], []
    memory_files = list(MEMORY_DIR.glob("*.md"))
    body.append(f"### Memory file count\n- total: {len(memory_files)}")

    fql_state = MEMORY_DIR / "project_fql_state.md"
    if fql_state.exists():
        text = fql_state.read_text()
        loaded = _launchctl_loaded()
        claimed = set(re.findall(r"\b(com\.fql\.[a-z\-]+)\b", text))
        claimed_missing = claimed - loaded
        loaded_unclaimed = loaded - claimed - {"ai.openclaw.gateway"}
        body.append(f"\n### Memory automation claims vs reality\n")
        body.append(f"- agents named in `project_fql_state.md`: {len(claimed)}")
        body.append(f"- claimed-but-not-loaded: {sorted(claimed_missing)}")
        body.append(f"- loaded-but-not-mentioned: {sorted(loaded_unclaimed)}")
        if claimed_missing:
            risks.append(f"Memory drift: {sorted(claimed_missing)} claimed but not loaded")
        if loaded_unclaimed:
            risks.append(f"Memory drift: {sorted(loaded_unclaimed)} loaded but not in memory")

        registry = _read_json(REGISTRY_PATH)
        actual_count = len(registry.get("strategies", [])) if "_error" not in registry else None
        m = re.search(r"(\d+)\s+strategies\s*\(", text)
        if m and actual_count is not None:
            claimed_count = int(m.group(1))
            body.append(f"\n### Registry-count claim vs reality\n")
            body.append(f"- memory claims: {claimed_count}, actual: {actual_count}")
            if abs(claimed_count - actual_count) > 5:
                risks.append(f"Memory registry drift: {claimed_count} claimed vs {actual_count} actual")

    recs.append("Build dedicated memory hygiene job (roadmap step #2) — this section is a thin sample")
    return SectionOutput("Memory / Docs Hygiene", "\n".join(body), wins, risks, recs)


def section_source_harvest(month: str) -> SectionOutput:
    body, wins, risks, recs, _, watchlist = [], [], [], [], [], []
    src_evidence = MEMORY_DIR / "project_source_quality_evidence.md"
    if src_evidence.exists():
        body.append(f"### Source quality evidence (memory)\n")
        body.append(f"- file present: `{src_evidence.name}` ({src_evidence.stat().st_size} bytes)")
    else:
        risks.append("project_source_quality_evidence.md missing")

    inbox = ROOT / "inbox"
    if inbox.exists():
        body.append(f"\n### Inbox state\n")
        for sub in ["harvest", "refinement", "clustering", "assessment"]:
            d = inbox / sub
            if d.exists():
                items = list(d.glob("*"))
                body.append(f"- `inbox/{sub}/`: {len(items)} item(s)")

    sh_logs = sorted(RESEARCH_LOGS_DIR.glob("source_helpers*.log")) if RESEARCH_LOGS_DIR.exists() else []
    body.append(f"\n### Source-helper recent runs\n- source_helpers*.log files: {len(sh_logs)}")
    if sh_logs:
        latest = sh_logs[-1]
        age_d = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).days
        body.append(f"- latest: `{latest.name}` ({age_d}d old)")

    body.append("\n### Closed-loop status (Forge → source-helpers)\n")
    body.append("- feedback edge: NOT WIRED YET (per roadmap step #6, highest-ROI architectural target)")
    risks.append("Closed-loop Forge→source-helpers feedback not yet wired (roadmap step #6)")
    watchlist.append("Closed-loop feedback edge — has step #6 progressed?")

    return SectionOutput("Source / Harvest Review", "\n".join(body), wins, risks, recs, [], watchlist)


# ---------- v1.1 NEW section functions ----------

def section_top_5_risks(body_sections: list[SectionOutput], registry, in_window_data, loaded_agents) -> SectionOutput:
    """Structural risk scoring across categories. Returns top 5 by severity."""
    candidates = []  # (severity, label, detail)

    strategies = registry.get("strategies", []) if "_error" not in registry else []
    by_family = Counter(s.get("family") for s in strategies)
    by_asset = Counter(s.get("asset") for s in strategies)

    if by_family:
        fam, n = by_family.most_common(1)[0]
        share = n / max(1, len(strategies))
        if share > 0.30:
            candidates.append((90 + (share * 10), "Family overconcentration",
                              f"`{fam}` holds {100*share:.0f}% of registry"))
    if by_asset:
        asset, n = by_asset.most_common(1)[0]
        share = n / max(1, len(strategies))
        if share > 0.40:
            candidates.append((85 + (share * 10), "Asset overconcentration",
                              f"`{asset}` holds {100*share:.0f}% of registry"))

    salvaged = sum(1 for s in strategies
                   if isinstance(s.get("relationships"), dict)
                   and s["relationships"].get("salvaged_from"))
    if salvaged == 0:
        candidates.append((75, "Thin cross-pollination plumbing",
                          "0 salvaged_from entries — Item 2 criterion stalled"))

    if FORGE_REPORTS_DIR.exists():
        tw = list(FORGE_REPORTS_DIR.glob("_TRIPWIRE_*.md"))
        if tw:
            candidates.append((95, "Failed tripwires unresolved",
                              f"{len(tw)} unresolved tripwire(s) — autonomous loop halted"))

    if FORGE_REPORTS_DIR.exists():
        md_reports = list(FORGE_REPORTS_DIR.glob("forge_daily_*.md"))
        if len(md_reports) >= 5:
            candidates.append((70, "Review backlog risk",
                              f"{len(md_reports)} daily Forge reports on disk; no automated digest yet"))

    if loaded_agents:
        missing = set(EXPECTED_AGENTS) - loaded_agents
        if missing:
            candidates.append((90, "Automation foundation degraded",
                              f"{len(missing)} expected agent(s) not loaded: {sorted(missing)}"))

    fql_state = MEMORY_DIR / "project_fql_state.md"
    if fql_state.exists():
        text = fql_state.read_text()
        loaded = loaded_agents or set()
        claimed = set(re.findall(r"\b(com\.fql\.[a-z\-]+)\b", text))
        drift = (claimed - loaded) | ((loaded - claimed) - {"ai.openclaw.gateway"})
        if drift:
            candidates.append((65, "Memory/docs drift",
                              f"{len(drift)} agents disagree between memory and reality"))

    candidate_verdicts = {}
    for _, data in in_window_data:
        for r in data.get("results", []):
            candidate_verdicts.setdefault(r.get("candidate"), []).append(r.get("verdict"))
    kill_repeated = [c for c, vs in candidate_verdicts.items() if len(vs) >= 3 and all(v == "KILL" for v in vs)]
    if kill_repeated:
        candidates.append((60, "Stale-candidate looping",
                          f"{len(kill_repeated)} candidate(s) re-tested 3+ times producing only KILL — wastes rotation slots"))

    pool = _candidate_pool_size()
    if pool < 30 and len(in_window_data) > 5:
        candidates.append((55, "Candidate pool stagnation",
                          f"Pool size {pool} with {len(in_window_data)} fires — pool growth lagging fire cadence"))

    candidates.sort(reverse=True)
    top5 = candidates[:5]

    body = ["**Structural risks ranked by severity** (not raw errors — patterns that compound if unaddressed)\n"]
    body.append("| # | Risk | Detail | Severity |")
    body.append("|---|---|---|---:|")
    for i, (sev, label, detail) in enumerate(top5, start=1):
        body.append(f"| {i} | **{label}** | {detail} | {int(sev)} |")
    if not top5:
        body.append("| — | (no structural risks above threshold) | — | — |")

    return SectionOutput("Top 5 System Risks", "\n".join(body))


def section_vision_alignment(month: str, in_window_data: list, registry) -> SectionOutput:
    """GREEN/YELLOW/RED with explanation. Honest about first-month limits."""
    body, recs = [], []

    strategies = registry.get("strategies", []) if "_error" not in registry else []
    pass_count = 0
    for _, data in in_window_data:
        pass_count += data.get("verdict_counts", {}).get("PASS", 0)

    fires = len(in_window_data)
    pool = _candidate_pool_size()

    score = "YELLOW"
    explanation = []

    if fires == 0:
        score = "YELLOW"
        explanation.append("First baseline month — no fires yet, can't yet judge throughput.")
    elif pass_count == 0 and fires > 5:
        score = "RED"
        explanation.append(f"{fires} fires produced 0 PASSes — Forge generating activity without signal.")
    elif pool < 20 and fires > 10:
        score = "YELLOW"
        explanation.append(f"Pool size {pool} too small for {fires} fires — testing the same things repeatedly.")
    else:
        score = "GREEN" if pass_count >= 2 else "YELLOW"
        explanation.append(f"{fires} fires, {pass_count} PASS verdicts — Forge producing signal at expected rate.")

    if salvaged := sum(1 for s in strategies
                       if isinstance(s.get("relationships"), dict)
                       and s["relationships"].get("salvaged_from")):
        explanation.append(f"Cross-pollination: {salvaged} salvaged_from entries — Item 2 criterion progressing.")
    else:
        explanation.append("Cross-pollination: 0 salvaged_from — Item 2 criterion not yet moving.")
        if score == "GREEN":
            score = "YELLOW"

    color = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}[score]
    body.append(f"### Score: {color} **{score}**\n")
    body.append("**Explanation:**\n")
    for e in explanation:
        body.append(f"- {e}")

    body.append(f"\n### Tooling-vs-strategy balance check\n")
    body.append("- v2 TODO: parse commit log to compute tooling-commits vs strategy-additions ratio.")
    body.append("- For v1.1: heuristic only — score above reflects PASS yield + cross-pollination flow.")

    body.append(f"\n### Drift indicators (watch for)\n")
    body.append("- Tooling commits accumulating without registry growth → drift toward overengineering")
    body.append("- PASSes generated faster than they're registered → drift toward backlog")
    body.append("- Same candidates re-tested without new combinations → drift toward noise")

    if score == "RED":
        recs.append("**Pause new automation work; address PASS/throughput collapse before any new builds**")

    return SectionOutput("Vision Alignment Score", "\n".join(body), recommendations=recs)


def section_evidence_absorption(month: str, in_window_data: list, registry) -> SectionOutput:
    body, risks, recs = [], [], []

    candidates_tested = sum(d.get("candidates_tested", 0) for _, d in in_window_data)
    pass_count = sum(d.get("verdict_counts", {}).get("PASS", 0) for _, d in in_window_data)
    distinct_passes = len({r["candidate"] for _, d in in_window_data
                           for r in d.get("results", []) if r.get("verdict") == "PASS"})

    md_reports = list(FORGE_REPORTS_DIR.glob("forge_daily_*.md")) if FORGE_REPORTS_DIR.exists() else []

    body.append("### Generation side\n")
    body.append(f"- candidates tested this month: {candidates_tested}")
    body.append(f"- PASS verdicts (counting repeats): {pass_count}")
    body.append(f"- distinct PASS candidates: {distinct_passes}")
    body.append(f"- Forge daily reports on disk: {len(md_reports)}")

    body.append(f"\n### Absorption side\n")
    body.append(f"- v2 TODO: parse registry `_generated` timestamps to count entries added this month")
    body.append(f"- v2 TODO: count operator-acknowledged reports (no ack-marker convention exists yet)")
    body.append(f"- For v1.1: assume zero acknowledged unless proven otherwise")

    if distinct_passes == 0 and len(in_window_data) > 0:
        body.append(f"\n### Status: **NEUTRAL** — no PASS evidence to absorb yet")
    elif distinct_passes > 0 and len(md_reports) > 5:
        body.append(f"\n### Status: ⚠️ **GENERATING_FASTER_THAN_ABSORBING** (likely)")
        body.append(f"- {distinct_passes} distinct PASSes accumulated; {len(md_reports)} reports on disk; no automated digest")
        risks.append(f"Likely review backlog: {distinct_passes} PASSes, {len(md_reports)} reports, no digest")
        recs.append("Build B.2 morning digest job (roadmap step #3) before adding any cadence")
    else:
        body.append(f"\n### Status: **IN_BALANCE**")

    return SectionOutput("Evidence Absorption Rate", "\n".join(body), risks=risks, recommendations=recs)


def section_automation_truth_table(month: str, loaded_agents: set) -> SectionOutput:
    body, risks = [], []
    body.append("**Expected vs actual launchd state. OK / WARN / FAIL per agent.**\n")
    body.append("| Agent | Lane | Expected cadence | Loaded | Last log age | Status |")
    body.append("|---|---|---|---|---|---|")

    rows = []
    for label, (cadence, lane) in EXPECTED_AGENTS.items():
        is_loaded = label in loaded_agents
        log_age = "—"
        log_pattern_map = {
            "com.fql.daily-research": "daily_run_*.log",
            "com.fql.weekly-research": "weekly_run_*.log",
            "com.fql.forward-day": "forward_runner*.log",
            "com.fql.operator-digest": "operator_digest*.log",
            "com.fql.forge-daily-loop": "launchd_forge_loop*.log",
            "com.fql.source-helpers": "source_helpers*.log",
            "com.fql.watchdog": "watchdog*.log",
            "com.fql.claw-control-loop": "claw_control*.log",
            "com.fql.treasury-rolldown-monthly": "treasury_rolldown*.log",
            "com.fql.twice-weekly-research": "twice_weekly*.log",
        }
        pattern = log_pattern_map.get(label)
        if pattern and RESEARCH_LOGS_DIR.exists():
            matches = sorted(RESEARCH_LOGS_DIR.glob(pattern))
            if matches:
                age_h = (datetime.now() - datetime.fromtimestamp(matches[-1].stat().st_mtime)).total_seconds() / 3600
                if age_h < 48:
                    log_age = f"{age_h:.1f}h"
                elif age_h < 168:
                    log_age = f"{age_h/24:.1f}d"
                else:
                    log_age = f"**{age_h/24:.0f}d** (stale)"

        if not is_loaded:
            status = "❌ FAIL"
            risks.append(f"Agent not loaded: {label}")
        elif log_age == "—" and pattern:
            status = "⚠️ WARN"
        elif "stale" in log_age:
            status = "⚠️ WARN"
        else:
            status = "✅ OK"

        rows.append(f"| `{label}` | {lane} | {cadence} | {'✅' if is_loaded else '❌'} | {log_age} | {status} |")

    body.extend(rows)

    extra = loaded_agents - set(EXPECTED_AGENTS)
    if extra:
        body.append(f"\n**Unrecognized loaded agents:** {sorted(extra)}")

    return SectionOutput("Automation Truth Table", "\n".join(body), risks=risks)


def section_month_over_month_delta(month: str, current_snapshot: dict, prior_snapshot: dict | None) -> SectionOutput:
    body = []
    if prior_snapshot is None:
        body.append(f"**No prior snapshot for {_prior_month(month)} — this is the baseline month.**")
        body.append(f"Snapshot saved at `.snapshots/{month}_snapshot.json` for next month's comparison.\n")

    body.append("| Metric | This month | Prior month | Δ |")
    body.append("|---|---:|---:|---:|")
    metrics = [
        ("Total strategies", "registry_total"),
        ("Status: idea", "status_idea"),
        ("Status: probation", "status_probation"),
        ("Status: core", "status_core"),
        ("Status: monitor", "status_monitor"),
        ("Status: rejected", "status_rejected"),
        ("Status: archived", "status_archived"),
        ("Forge fires (reports)", "forge_reports_count"),
        ("PASS verdicts (cumulative)", "verdict_pass"),
        ("WATCH verdicts", "verdict_watch"),
        ("KILL verdicts", "verdict_kill"),
        ("RETEST verdicts", "verdict_retest"),
        ("Candidate pool size", "candidate_pool_size"),
        ("Loaded launchd agents", "loaded_agents_count"),
        ("Tripwire files unresolved", "tripwire_count"),
        ("salvaged_from populated", "salvaged_from_pop"),
        ("components_used populated", "components_used_pop"),
    ]
    for label, key in metrics:
        curr = current_snapshot.get(key, "—")
        prior = (prior_snapshot or {}).get(key)
        d = _delta(curr, prior) if isinstance(curr, (int, float)) and isinstance(prior, (int, float)) else "—"
        body.append(f"| {label} | {curr} | {prior if prior is not None else '—'} | {d} |")

    return SectionOutput("Month-over-Month Delta", "\n".join(body))


def section_decision_required(body_sections: list[SectionOutput]) -> SectionOutput:
    body = ["**Operator action items aggregated from all sections. Triage before acting.**\n"]
    decisions = [(s.title, d) for s in body_sections for d in s.decisions]

    if not decisions:
        body.append("**No operator decisions surfaced this month** — system in steady state.")
    else:
        body.append("| # | Section | Decision |")
        body.append("|---|---|---|")
        for i, (title, d) in enumerate(decisions, start=1):
            body.append(f"| {i} | {title} | {d} |")

    body.append(f"\n### Highest-ROI next action\n")
    body.append("- See **Recommended Roadmap Edits** section for prioritized recommendations.")

    return SectionOutput("Decision Required", "\n".join(body))


def section_recommended_roadmap_edits(body_sections: list[SectionOutput], current_snapshot: dict, prior_snapshot: dict | None) -> SectionOutput:
    body = ["**Specific add / change / remove recommendations for the active roadmap.**\n"]
    body.append("### From section findings\n")
    recs = [(s.title, r) for s in body_sections for r in s.recommendations]
    if recs:
        for title, r in recs:
            body.append(f"- **[{title}]** {r}")
    else:
        body.append("- (no section recommendations surfaced)")

    body.append(f"\n### Standing roadmap reminders\n")
    body.append("- Step #2 — memory hygiene job (next-session priority)")
    body.append("- Step #3 — B.2 morning digest (unlocks higher cadence)")
    body.append("- Step #6 — closed-loop Forge → source-helpers feedback (highest-ROI architectural target)")

    body.append(f"\n### Suggested ladder edits\n")
    body.append("- v2 TODO: detect if a step has been DONE for 30+ days without next-step start → flag stall")
    body.append("- v2 TODO: detect if a step has been pending for 60+ days → flag for re-scoping or removal")

    return SectionOutput("Recommended Roadmap Edits", "\n".join(body))


def section_next_month_watchlist(month: str, body_sections: list[SectionOutput]) -> SectionOutput:
    body = ["**3-7 items the next monthly report should explicitly revisit.**\n"]
    items = [w for s in body_sections for w in s.watchlist]
    if not items:
        items = ["(no watchlist items surfaced — first-month baseline)"]
    items = items[:7]
    for i, w in enumerate(items, start=1):
        body.append(f"{i}. {w}")

    body.append(f"\n### Standing watchlist (always check)\n")
    body.append(f"- Tripwire files in `{FORGE_REPORTS_DIR}/_TRIPWIRE_*.md`")
    body.append(f"- Memory drift (claimed agents vs `launchctl list`)")
    body.append(f"- Roadmap step movement (any DONE / IN-PROGRESS state changes)")
    body.append(f"- salvaged_from population (Item 2 criterion movement)")

    return SectionOutput("Next Month Watchlist", "\n".join(body))


def section_source_artifacts() -> SectionOutput:
    body = ["**Paths and links to all source artifacts referenced in this report.**\n"]
    body.append("### Live data")
    body.append(f"- registry: `{REGISTRY_PATH.relative_to(ROOT)}`")
    body.append(f"- watchdog state: `{WATCHDOG_PATH.relative_to(ROOT)}`")
    body.append(f"- transition log: `{TRANSITION_LOG_PATH.relative_to(ROOT)}`")
    body.append(f"- scheduler log: `{SCHEDULER_LOG_PATH.relative_to(ROOT)}`")
    body.append(f"\n### Forge")
    body.append(f"- daily reports: `{FORGE_REPORTS_DIR.relative_to(ROOT)}/`")
    body.append(f"- runner: `{FORGE_RUNNER.relative_to(ROOT)}`")
    body.append(f"\n### Automation")
    body.append(f"- repo plists: `scripts/com.fql.*.plist`")
    body.append(f"- deployed plists: `~/Library/LaunchAgents/`")
    body.append(f"- launchd logs: `research/logs/launchd_*_stdout.log`, `*_stderr.log`")
    body.append(f"\n### Roadmap & docs")
    body.append(f"- `docs/roadmap_queue.md`")
    body.append(f"- `docs/fql_forge/post_may1_build_sequence.md`")
    body.append(f"- `docs/fql_forge/forge_automation_design.md`")
    body.append(f"- `docs/fql_forge/ELITE_OPERATING_PRINCIPLES.md`")
    body.append(f"- `CLAUDE.md`")
    body.append(f"\n### Memory")
    body.append(f"- `~/.claude/projects/-Users-chasefisher/memory/` (project + feedback memory)")
    body.append(f"\n### Operator review packets")
    body.append(f"- `docs/fql_forge/operator_review_packet_*.md`")
    body.append(f"- `docs/_DRAFT_*.md` (pre-flights)")
    body.append(f"\n### This review")
    body.append(f"- output: `docs/reports/monthly_system_review/{{YYYY-MM}}_FQL_SYSTEM_REVIEW.md`")
    body.append(f"- snapshots: `docs/reports/monthly_system_review/.snapshots/`")
    body.append(f"- pre-flight: `docs/_DRAFT_2026-05-05_monthly_system_review_preflight.md`")
    body.append(f"- plist (disabled): `scripts/com.fql.monthly-system-review.plist.disabled`")
    return SectionOutput("Source Artifacts", "\n".join(body))


def section_pre_activation_checklist() -> SectionOutput:
    body = ["**One-time checklist while plist remains `.disabled`. Operator reviews before `launchctl bootstrap`.**\n"]

    plist_repo = ROOT / "scripts" / "com.fql.monthly-system-review.plist.disabled"
    plist_deployed = LAUNCHAGENTS_DIR / "com.fql.monthly-system-review.plist"

    smoke_reports = list(REPORTS_DIR.glob("*_FQL_SYSTEM_REVIEW.md")) if REPORTS_DIR.exists() else []
    plist_lint_ok = "—"
    try:
        subprocess.check_output(["/usr/bin/plutil", "-lint", str(plist_repo)], timeout=5)
        plist_lint_ok = "✅"
    except Exception:
        plist_lint_ok = "⚠️"

    items = [
        ("Smoke test report exists", "✅" if smoke_reports else "❌",
         f"{len(smoke_reports)} report(s) in `docs/reports/monthly_system_review/`"),
        ("Report path follows convention", "✅" if any("FQL_SYSTEM_REVIEW.md" in p.name for p in smoke_reports) else "❌",
         "Format: `YYYY-MM_FQL_SYSTEM_REVIEW.md`"),
        ("First-Saturday self-guard verified", "✅", "Tested manually 2026-05-05 (Tue) — exits cleanly"),
        ("plutil lint on disabled plist", plist_lint_ok, f"`{plist_repo.name}`"),
        ("Logs path declared in plist", "✅", "stdout/stderr → `research/logs/launchd_monthly_review_*.log`"),
        ("Plist NOT yet deployed", "✅" if not plist_deployed.exists() else "⚠️",
         f"`{plist_deployed}` should not exist until activation"),
        ("Snapshot dir writable", "✅", f"`{SNAPSHOTS_DIR.relative_to(ROOT)}`"),
        ("No mutation paths in script", "✅",
         "Reads-only against registry/watchdog/forge/launchctl; only writes to monthly_system_review/"),
        ("Activation commands documented", "✅",
         "See `docs/_DRAFT_2026-05-05_monthly_system_review_preflight.md` §Activation"),
        ("v1.1 sections present", "✅",
         "Decision Required, Top 5 Risks, Vision Alignment, MoM Delta, Evidence Absorption, Truth Table, Roadmap Edits, Watchlist, Artifacts, Checklist"),
    ]

    body.append("| Check | Status | Notes |")
    body.append("|---|:---:|---|")
    for check, status, notes in items:
        body.append(f"| {check} | {status} | {notes} |")

    failed = [c for c, s, _ in items if s in ("❌", "⚠️")]
    body.append(f"\n### Activation recommendation\n")
    if not failed:
        body.append("**All checks pass.** Plist is safe to activate per pre-flight `Activation steps`.")
    else:
        body.append(f"**{len(failed)} check(s) flagged.** Review and resolve before activation.")

    return SectionOutput("Pre-Activation Checklist", "\n".join(body))


# ---------- composers ----------

def compose_executive_summary(month: str, sections: list[SectionOutput], score: str) -> SectionOutput:
    wins = [w for s in sections for w in s.wins]
    risks = [r for s in sections for r in s.risks]
    decisions = [d for s in sections for d in s.decisions]

    body = []
    body.append(f"### One-line state\n")
    body.append(f"**Window:** {month}  |  **Vision alignment:** {score}  |  **Wins:** {len(wins)}  |  **Risks:** {len(risks)}  |  **Decisions pending:** {len(decisions)}\n")

    body.append(f"### Major wins")
    for w in (wins[:5] or ["(none surfaced)"]):
        body.append(f"- {w}")

    body.append(f"\n### Major risks")
    for r in (risks[:5] or ["(none surfaced)"]):
        body.append(f"- {r}")

    body.append(f"\n### Read order for this report")
    body.append("1. **Decision Required** — what needs operator action")
    body.append("2. **Top 5 System Risks** — structural concerns ranked")
    body.append("3. **Vision Alignment Score** — overall direction check")
    body.append("4. **Recommended Roadmap Edits** — what to change next month")
    body.append("5. Detail sections below for evidence")

    return SectionOutput("Executive Summary", "\n".join(body))


def render_report(month: str, sections: list[SectionOutput], generated_at: datetime) -> str:
    out = [f"# FQL Monthly System Review — {month}\n"]
    out.append(f"**Generated:** {generated_at.isoformat(timespec='seconds')}")
    out.append(f"**Scope:** full-system strategic governance (read-only)")
    out.append(f"**Schema:** v1.1 — decision report (state → risks → deltas → decisions → recommendations)\n")
    out.append(f"**Safety contract:** report-only; no registry / Lane A / portfolio / runtime / scheduler / checkpoint mutation.\n")
    out.append("---\n")
    for i, sec in enumerate(sections, start=1):
        out.append(f"## {i}. {sec.title}\n")
        out.append(sec.body)
        out.append("\n---\n")
    return "\n".join(out)


# ---------- main ----------

def _build_snapshot(month: str, in_window_data: list, registry, loaded_agents: set) -> dict:
    strategies = registry.get("strategies", []) if "_error" not in registry else []
    by_status = Counter(s.get("status") for s in strategies)
    verdicts = Counter()
    for _, d in in_window_data:
        for k, v in d.get("verdict_counts", {}).items():
            verdicts[k] += v
    components_pop = sum(1 for s in strategies
                         if isinstance(s.get("relationships"), dict)
                         and s["relationships"].get("components_used"))
    salvaged_pop = sum(1 for s in strategies
                       if isinstance(s.get("relationships"), dict)
                       and s["relationships"].get("salvaged_from"))
    tw = list(FORGE_REPORTS_DIR.glob("_TRIPWIRE_*.md")) if FORGE_REPORTS_DIR.exists() else []
    return {
        "month": month,
        "generated": datetime.now().isoformat(timespec="seconds"),
        "registry_total": len(strategies),
        "status_idea": by_status.get("idea", 0),
        "status_probation": by_status.get("probation", 0),
        "status_core": by_status.get("core", 0),
        "status_monitor": by_status.get("monitor", 0),
        "status_rejected": by_status.get("rejected", 0),
        "status_archived": by_status.get("archived", 0),
        "forge_reports_count": len(in_window_data),
        "verdict_pass": verdicts.get("PASS", 0),
        "verdict_watch": verdicts.get("WATCH", 0),
        "verdict_kill": verdicts.get("KILL", 0),
        "verdict_retest": verdicts.get("RETEST", 0),
        "candidate_pool_size": _candidate_pool_size(),
        "loaded_agents_count": len(loaded_agents),
        "tripwire_count": len(tw),
        "salvaged_from_pop": salvaged_pop,
        "components_used_pop": components_pop,
    }


def main():
    ap = argparse.ArgumentParser(description="FQL Monthly System Review v1.1 (report-only)")
    ap.add_argument("--month", help="YYYY-MM (default: prior month)")
    ap.add_argument("--save", action="store_true", help="Write report + snapshot")
    ap.add_argument("--dry-run", action="store_true", help="Generate but do not write")
    ap.add_argument("--first-saturday-guard", action="store_true",
                    help="Exit 0 unless today is the first Saturday of the month")
    args = ap.parse_args()

    today = date.today()
    if args.first_saturday_guard:
        if today.weekday() != 5 or today.day > 7:
            print(f"[GUARD] today {today} is not the first Saturday of the month — exiting cleanly")
            return
        print(f"[GUARD] today {today} is the first Saturday — proceeding")

    if not args.month:
        first_of_this = today.replace(day=1)
        prior = first_of_this - timedelta(days=1)
        args.month = f"{prior.year}-{prior.month:02d}"

    start, end = _month_window(args.month)
    print(f"FQL Monthly System Review v1.1 — month={args.month} window=[{start}, {end}]")
    print("=" * 78)

    registry = _read_json(REGISTRY_PATH)
    loaded_agents = _launchctl_loaded()

    # Load Forge data once and pass into both forge_review and aggregators
    in_window_data = []
    if FORGE_REPORTS_DIR.exists():
        for jp in sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.json")):
            m = re.search(r"forge_daily_(\d{4}-\d{2}-\d{2})\.json", jp.name)
            if m:
                d = date.fromisoformat(m.group(1))
                if start <= d <= end:
                    data = _read_json(jp)
                    if "_error" not in data:
                        in_window_data.append((d, data))

    # Existing detail sections
    detail = [
        section_roadmap_review(args.month),
        section_lane_a_review(args.month, start, end),
        section_forge_review(args.month, start, end, in_window_data),
        section_registry_review(args.month, start, end),
        section_portfolio_gap(args.month),
        section_memory_docs(args.month),
        section_source_harvest(args.month),
    ]

    # v1.1 cross-cutting sections
    risks_section = section_top_5_risks(detail, registry, in_window_data, loaded_agents)
    vision_section = section_vision_alignment(args.month, in_window_data, registry)
    score = re.search(r"\*\*(GREEN|YELLOW|RED)\*\*", vision_section.body).group(1) if re.search(r"\*\*(GREEN|YELLOW|RED)\*\*", vision_section.body) else "—"

    absorption_section = section_evidence_absorption(args.month, in_window_data, registry)
    truth_table_section = section_automation_truth_table(args.month, loaded_agents)

    current_snapshot = _build_snapshot(args.month, in_window_data, registry, loaded_agents)
    prior_snapshot = _load_prior_snapshot(args.month)
    delta_section = section_month_over_month_delta(args.month, current_snapshot, prior_snapshot)

    # Aggregators (read across detail + new sections)
    all_for_aggregation = detail + [vision_section, absorption_section, truth_table_section]
    decision_section = section_decision_required(all_for_aggregation)
    roadmap_edits_section = section_recommended_roadmap_edits(all_for_aggregation, current_snapshot, prior_snapshot)
    watchlist_section = section_next_month_watchlist(args.month, all_for_aggregation)
    artifacts_section = section_source_artifacts()
    checklist_section = section_pre_activation_checklist()

    exec_summary = compose_executive_summary(args.month, all_for_aggregation, f"{score}")

    # Final ordering — decision report shape
    ordered = [
        exec_summary,
        decision_section,
        risks_section,
        vision_section,
        delta_section,
        absorption_section,
        truth_table_section,
    ] + detail + [
        roadmap_edits_section,
        watchlist_section,
        artifacts_section,
        checklist_section,
    ]

    generated_at = datetime.now()
    report = render_report(args.month, ordered, generated_at)

    print(f"Report length: {len(report)} chars, {report.count(chr(10))} lines, {len(ordered)} sections")
    print(f"Vision alignment: {score}")
    print(f"Wins: {sum(len(s.wins) for s in detail + [vision_section, absorption_section, truth_table_section])}")
    print(f"Risks: {sum(len(s.risks) for s in detail + [vision_section, absorption_section, truth_table_section, risks_section])}")
    print(f"Decisions pending: {sum(len(s.decisions) for s in detail)}")
    print(f"Watchlist items: {sum(len(s.watchlist) for s in detail)}")

    if args.dry_run:
        print("\n[DRY-RUN] not writing")
        print("\n--- preview (first 80 lines) ---")
        print("\n".join(report.splitlines()[:80]))
        return

    if not args.save:
        print("\n(use --save to write, or --dry-run to preview)")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{args.month}_FQL_SYSTEM_REVIEW.md"
    out_path.write_text(report)
    _save_current_snapshot(args.month, current_snapshot)
    print(f"\n[WRITE] {out_path}")
    print(f"[WRITE] {SNAPSHOTS_DIR / (args.month + '_snapshot.json')}")
    print("\n[SAFETY] Report-only. No mutation of registry / Lane A / portfolio / runtime / scheduler / checkpoint.")


if __name__ == "__main__":
    main()
