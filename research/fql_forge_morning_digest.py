#!/usr/bin/env python3
"""FQL Forge Morning Digest — consume prior Forge daily-loop output and surface what changed.

Turns the autonomous Forge from "report generator" into "report generator +
review packet." The packet is what unlocks higher Forge cadence later without
burying the operator in unread evidence.

Safety contract (Phase A — manual CLI):
- Report-only. No registry / Lane A / portfolio / runtime / scheduler /
  checkpoint / hold-state mutation.
- All file writes target docs/reports/fql_forge_morning_digest/.
- All other I/O is read-only against existing artifacts.

Cadence (Phase B — disabled plist provided): weekdays 08:00 PT, after the
prior weekday's 19:00 Forge fire. Plist provided as `.disabled` so it cannot
be loaded accidentally.

Usage:
    python3 research/fql_forge_morning_digest.py                  # latest forge report
    python3 research/fql_forge_morning_digest.py --date 2026-05-05 --save
    python3 research/fql_forge_morning_digest.py --dry-run
"""

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPORTS_DIR = ROOT / "docs" / "reports" / "fql_forge_morning_digest"
FORGE_REPORTS_DIR = ROOT / "research" / "data" / "fql_forge" / "reports"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
FORGE_STDOUT_LOG = ROOT / "research" / "logs" / "forge_daily_loop_stdout.log"
FORGE_STDERR_LOG = ROOT / "research" / "logs" / "forge_daily_loop_stderr.log"

# Backlog thresholds
BACKLOG_GREEN_MAX = 5      # ≤ 5 unreviewed PASSes is fine
BACKLOG_YELLOW_MAX = 15    # 6-15 = noticeable backlog
                           # > 15 = RED


@dataclass
class SectionOutput:
    title: str
    body: str
    actions: list[str] = field(default_factory=list)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"_error": str(e)}


def _find_latest_forge_report() -> tuple[str, dict] | None:
    """Return (date_str, json_data) for the most recent forge_daily_*.json."""
    if not FORGE_REPORTS_DIR.exists():
        return None
    reports = sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.json"))
    if not reports:
        return None
    latest = reports[-1]
    m = re.search(r"forge_daily_(\d{4}-\d{2}-\d{2})\.json", latest.name)
    if not m:
        return None
    data = _read_json(latest)
    if "_error" in data:
        return None
    return m.group(1), data


def _all_forge_reports_before(target_date: date, n_days: int = 7) -> list[tuple[date, dict]]:
    """Return list of (date, data) for all forge reports in the prior N days."""
    if not FORGE_REPORTS_DIR.exists():
        return []
    out = []
    cutoff = target_date - timedelta(days=n_days)
    for jp in sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.json")):
        m = re.search(r"forge_daily_(\d{4}-\d{2}-\d{2})\.json", jp.name)
        if m:
            d = date.fromisoformat(m.group(1))
            if cutoff <= d < target_date:
                data = _read_json(jp)
                if "_error" not in data:
                    out.append((d, data))
    return out


def _registered_strategy_ids() -> set[str]:
    reg = _read_json(REGISTRY_PATH)
    if "_error" in reg:
        return set()
    return {s.get("strategy_id") for s in reg.get("strategies", [])}


# ---------- sections ----------

def section_executive_summary(date_str: str, data: dict, tripwires: list[Path]) -> SectionOutput:
    body, actions = [], []
    counts = data.get("verdict_counts", {})
    runtime = data.get("runtime_total_sec", 0)
    candidates_tested = data.get("candidates_tested", 0)
    run_mode = data.get("run_mode", "?")

    if tripwires:
        status = "🔴 **TRIPWIRE FIRED**"
        actions.append(f"CLEAR TRIPWIRE: review and remove `{tripwires[0].name}` before next fire")
    elif candidates_tested == 0:
        status = "⚠️ **NO CANDIDATES TESTED** (run may have failed early)"
        actions.append("Investigate Forge runtime — no candidates were evaluated")
    else:
        status = "✅ **COMPLETE**"

    body.append(f"### Last Forge run: {status}\n")
    body.append(f"- date: **{date_str}**")
    body.append(f"- run mode: {run_mode}")
    body.append(f"- candidates tested: {candidates_tested}")
    body.append(f"- runtime: {runtime:.1f}s (limit 300s)")
    body.append(f"- verdicts: **PASS {counts.get('PASS', 0)} / WATCH {counts.get('WATCH', 0)} / KILL {counts.get('KILL', 0)} / RETEST {counts.get('RETEST', 0)}**")
    body.append(f"- tripwires: {len(tripwires)}")

    if counts.get("PASS", 0) > 0 and not tripwires:
        actions.append(f"REVIEW {counts['PASS']} PASS candidate(s) — see §2 for details")
    if counts.get("RETEST", 0) > 0:
        actions.append(f"RETEST flagged for {counts['RETEST']} candidate(s) — investigate harness")

    body.append(f"\n### Action needed\n")
    if not actions:
        body.append("- (none — system in steady state)")
    else:
        for a in actions:
            body.append(f"- {a}")

    return SectionOutput("Executive Summary", "\n".join(body), actions)


def section_candidate_results(data: dict, prior_runs: list[tuple[date, dict]], registered: set[str]) -> SectionOutput:
    body = []
    results = data.get("results", [])

    # Build "seen in prior runs" lookup
    prior_candidates = {}
    for d, prior_data in prior_runs:
        for r in prior_data.get("results", []):
            prior_candidates.setdefault(r.get("candidate"), []).append((d, r.get("verdict")))

    body.append("| Candidate | Asset | Verdict | PF | n | Net PnL | Repeat? | Registered? |")
    body.append("|---|---|---:|---:|---:|---:|---|---|")
    for r in results:
        cid = r.get("candidate", "?")
        asset = r.get("asset", "?")
        verdict = r.get("verdict", "?")
        m = r.get("metrics", {})
        pf = m.get("pf", 0)
        n = m.get("n", 0)
        net = m.get("net", 0)

        repeat_info = "—"
        if cid in prior_candidates:
            prior = prior_candidates[cid]
            recent_verdict = prior[-1][1]
            repeat_info = f"{len(prior)}× prior (last: {recent_verdict})"
            if recent_verdict == verdict:
                repeat_info += " ✓same"
            else:
                repeat_info += f" ⚠️changed→{verdict}"

        registered_marker = "✅ in registry" if cid in registered else "—"

        body.append(f"| `{cid}` | {asset} | **{verdict}** | {pf:.3f} | {n} | ${net:.0f} | {repeat_info} | {registered_marker} |")

    if not results:
        body.append("| (no candidates in this run) | | | | | | | |")

    body.append(f"\n### Architecture notes")
    pass_assets = [r.get("asset") for r in results if r.get("verdict") == "PASS"]
    if pass_assets:
        body.append(f"- PASS assets this fire: {pass_assets}")
    new_passes = [r.get("candidate") for r in results
                  if r.get("verdict") == "PASS" and r.get("candidate") not in prior_candidates]
    if new_passes:
        body.append(f"- **NEW PASSes (not seen in prior 7 days):** {new_passes}")

    return SectionOutput("Candidate Results", "\n".join(body))


def section_queue_changes(date_str: str) -> SectionOutput:
    body = []
    queue_path = FORGE_REPORTS_DIR / "forge_queue.md"
    if not queue_path.exists():
        return SectionOutput("Queue Changes", "- (no `forge_queue.md` found)")

    text = queue_path.read_text()
    body.append(f"### Current rolling queue (`forge_queue.md`)\n")
    queue_lines = text.splitlines()
    next_actions = []
    for i, line in enumerate(queue_lines):
        if "Next safe Forge actions" in line:
            for follow in queue_lines[i+1:i+10]:
                if follow.strip().startswith("-"):
                    next_actions.append(follow.strip())
                elif follow.startswith("**") and next_actions:
                    break

    if next_actions:
        body.append("**Recommended next candidates** (from rolling queue):")
        for a in next_actions[:5]:
            body.append(f"  {a}")
    else:
        body.append("- (no parseable 'Next safe Forge actions' section)")

    body.append(f"\n### Aging analysis")
    body.append(f"- v2 TODO: snapshot queue daily and surface entries that have been recommended for >7 days without action")

    return SectionOutput("Queue Changes", "\n".join(body))


def section_evidence_absorption(date_str: str, prior_runs: list[tuple[date, dict]], data: dict, registered: set[str]) -> SectionOutput:
    body, actions = [], []

    all_runs = prior_runs + [(date.fromisoformat(date_str), data)]
    distinct_passes = set()
    for d, run_data in all_runs:
        for r in run_data.get("results", []):
            if r.get("verdict") == "PASS":
                distinct_passes.add(r.get("candidate"))

    pass_in_registry = distinct_passes & registered
    pass_pending = distinct_passes - registered

    md_reports = sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.md")) if FORGE_REPORTS_DIR.exists() else []

    body.append(f"### Counts\n")
    body.append(f"- distinct PASS candidates across prior 7 days + today: **{len(distinct_passes)}**")
    body.append(f"  - already in registry: **{len(pass_in_registry)}** ✅")
    body.append(f"  - **awaiting review (not in registry):** **{len(pass_pending)}**")
    body.append(f"- daily Forge reports on disk: {len(md_reports)}")

    if pass_pending:
        body.append(f"\n### PASS candidates awaiting review")
        for cid in sorted(pass_pending)[:10]:
            body.append(f"- `{cid}`")
        if len(pass_pending) > 10:
            body.append(f"- ... and {len(pass_pending) - 10} more")

    n = len(pass_pending)
    if n <= BACKLOG_GREEN_MAX:
        score = "🟢 **GREEN — IN BALANCE**"
    elif n <= BACKLOG_YELLOW_MAX:
        score = "🟡 **YELLOW — REVIEW BACKLOG ACCUMULATING**"
        actions.append(f"Triage {n} pending PASS candidate(s) before next batch register cycle")
    else:
        score = "🔴 **RED — GENERATING FASTER THAN ABSORBING**"
        actions.append(f"Halt cadence increase; absorb {n} pending PASSes before adding fires")

    body.append(f"\n### Backlog status: {score}")
    body.append(f"- thresholds: GREEN ≤ {BACKLOG_GREEN_MAX} / YELLOW ≤ {BACKLOG_YELLOW_MAX} / RED > {BACKLOG_YELLOW_MAX}")

    return SectionOutput("Evidence Absorption Status", "\n".join(body), actions)


def section_automation_health(date_str: str, data: dict, tripwires: list[Path]) -> SectionOutput:
    body = []
    runtime = data.get("runtime_total_sec", 0)

    body.append(f"### Runtime\n- total: {runtime:.1f}s (limit 300s, threshold to fire 'runtime_overrun' tripwire)")
    if runtime > 240:
        body.append(f"- ⚠️ approaching tripwire threshold")
    elif runtime > 0:
        body.append(f"- ✅ comfortably within limit")

    body.append(f"\n### stderr (`{FORGE_STDERR_LOG.relative_to(ROOT) if FORGE_STDERR_LOG.exists() else 'missing'}`)\n")
    if FORGE_STDERR_LOG.exists():
        try:
            text = FORGE_STDERR_LOG.read_text().strip()
            if text:
                lines = text.splitlines()
                body.append(f"- {len(lines)} line(s) in stderr — non-empty (recent tail):")
                for line in lines[-5:]:
                    body.append(f"  - `{line}`")
            else:
                body.append("- empty ✅")
        except Exception as e:
            body.append(f"- read failed: {e}")
    else:
        body.append("- (file does not exist)")

    body.append(f"\n### stdout (`{FORGE_STDOUT_LOG.relative_to(ROOT) if FORGE_STDOUT_LOG.exists() else 'missing'}`)\n")
    if FORGE_STDOUT_LOG.exists():
        size_kb = FORGE_STDOUT_LOG.stat().st_size / 1024
        age_h = (datetime.now() - datetime.fromtimestamp(FORGE_STDOUT_LOG.stat().st_mtime)).total_seconds() / 3600
        body.append(f"- size: {size_kb:.1f} KB; last modified: {age_h:.1f}h ago")
    else:
        body.append("- (file does not exist)")

    body.append(f"\n### Tripwires\n")
    if tripwires:
        body.append(f"- 🔴 **{len(tripwires)} unresolved tripwire(s):**")
        for tw in tripwires:
            body.append(f"  - `{tw.name}`")
    else:
        body.append("- ✅ none")

    return SectionOutput("Automation Health", "\n".join(body))


def section_recommended_next_action(exec_summary: SectionOutput, absorption: SectionOutput, tripwires: list[Path]) -> SectionOutput:
    body = []

    if tripwires:
        op_action = f"CLEAR TRIPWIRE: review `{tripwires[0].name}` and remove file when ready to resume"
        forge_action = "loop will not auto-resume until tripwire cleared"
        mode = "🔴 PAUSE — tripwire fired"
    elif absorption.actions:
        op_action = absorption.actions[0]
        forge_action = "continue evening fires; skip cadence increase until backlog absorbed"
        mode = "🟡 CONTINUE — but address backlog"
    elif exec_summary.actions:
        op_action = exec_summary.actions[0]
        forge_action = "continue scheduled fires"
        mode = "🟢 CONTINUE — review PASSes when ready"
    else:
        op_action = "(none — system steady state)"
        forge_action = "continue scheduled fires"
        mode = "🟢 CONTINUE"

    body.append(f"### Operator action")
    body.append(f"- **{op_action}**")
    body.append(f"\n### Safe Forge action")
    body.append(f"- **{forge_action}**")
    body.append(f"\n### Mode")
    body.append(f"- **{mode}**")

    return SectionOutput("Recommended Next Action", "\n".join(body))


# ---------- composer ----------

def render_report(date_str: str, sections: list[SectionOutput], generated_at: datetime) -> str:
    digest_run_date = generated_at.date().isoformat()
    out = [f"# FQL Forge Morning Digest — {digest_run_date}\n"]
    out.append(f"**Generated:** {generated_at.isoformat(timespec='seconds')}")
    out.append(f"**Source fire date:** {date_str}")
    out.append(f"**Source artifacts:** `forge_daily_{date_str}.{{md,json}}` + queue + tripwires + logs")
    out.append(f"**Scope:** Lane B / Forge — daily review packet (read-only)\n")
    out.append(f"**Safety contract:** report-only; no registry / Lane A / portfolio / runtime / scheduler / checkpoint mutation.\n")
    out.append("---\n")
    for i, sec in enumerate(sections, start=1):
        out.append(f"## {i}. {sec.title}\n")
        out.append(sec.body)
        out.append("\n---\n")
    return "\n".join(out)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="FQL Forge Morning Digest (Phase A — report-only)")
    ap.add_argument("--date", help="YYYY-MM-DD (default: latest forge_daily_*.json)")
    ap.add_argument("--save", action="store_true", help="Write report to docs/reports/fql_forge_morning_digest/")
    ap.add_argument("--dry-run", action="store_true", help="Generate but do not write")
    args = ap.parse_args()

    if args.date:
        target_date_str = args.date
        json_path = FORGE_REPORTS_DIR / f"forge_daily_{args.date}.json"
        if not json_path.exists():
            print(f"[ERROR] forge_daily_{args.date}.json not found")
            sys.exit(1)
        data = _read_json(json_path)
        if "_error" in data:
            print(f"[ERROR] read failed: {data['_error']}")
            sys.exit(1)
    else:
        latest = _find_latest_forge_report()
        if not latest:
            print("[ERROR] no forge_daily_*.json reports found")
            sys.exit(1)
        target_date_str, data = latest

    print(f"FQL Forge Morning Digest — source date={target_date_str}")
    print("=" * 78)

    target_date = date.fromisoformat(target_date_str)
    prior_runs = _all_forge_reports_before(target_date, n_days=7)
    registered = _registered_strategy_ids()
    tripwires = sorted(FORGE_REPORTS_DIR.glob("_TRIPWIRE_*.md")) if FORGE_REPORTS_DIR.exists() else []

    exec_summary = section_executive_summary(target_date_str, data, tripwires)
    candidates = section_candidate_results(data, prior_runs, registered)
    queue = section_queue_changes(target_date_str)
    absorption = section_evidence_absorption(target_date_str, prior_runs, data, registered)
    health = section_automation_health(target_date_str, data, tripwires)
    next_action = section_recommended_next_action(exec_summary, absorption, tripwires)

    sections = [exec_summary, candidates, queue, absorption, health, next_action]
    generated_at = datetime.now()
    report = render_report(target_date_str, sections, generated_at)

    print(f"Report length: {len(report)} chars, {report.count(chr(10))} lines, {len(sections)} sections")
    print(f"Verdicts: {data.get('verdict_counts', {})}")
    print(f"Tripwires: {len(tripwires)}")
    print(f"Prior runs in 7-day window: {len(prior_runs)}")

    if args.dry_run:
        print("\n[DRY-RUN] preview (first 60 lines):\n")
        print("\n".join(report.splitlines()[:60]))
        return

    if not args.save:
        print("\n(use --save to write, or --dry-run for preview)")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    # Filename = the date the digest RAN (today), so a Wed 08:00 digest of
    # Tue 19:00's fire writes 2026-05-(Wed)_forge_morning_digest.md. The source
    # fire date is shown prominently in the report header. This matches operator
    # mental model of "today's morning digest" rather than "the fire's digest."
    digest_run_date = date.today().isoformat()
    out_path = REPORTS_DIR / f"{digest_run_date}_forge_morning_digest.md"
    out_path.write_text(report)
    print(f"\n[WRITE] {out_path}")
    print(f"  (digest ran on {digest_run_date}; source fire was {target_date_str})")
    print("\n[SAFETY] Report-only. No mutation.")


if __name__ == "__main__":
    main()
