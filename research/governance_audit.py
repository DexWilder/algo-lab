#!/usr/bin/env python3
"""FQL Governance Audit — review-load + absorption + Lane B health + cost-of-evidence.

The governance hardening packet. Catches three failure modes:
1. Evidence outrunning operator review capacity (backlog monster)
2. Operator review density crossing into overload (attention is constrained)
3. Lane B agents lacking tripwires / stale logs / silent output failures

Plus baseline cost-of-evidence instrumentation for future cadence escalation
gates.

Safety contract (Phase A — manual CLI):
- Report-only. No mutation of any surface. Everything is read-only audit.
- All file writes target docs/reports/governance_audit/.

Usage:
    python3 research/governance_audit.py                   # run + print summary
    python3 research/governance_audit.py --save            # write full report
    python3 research/governance_audit.py --lookback-days 7 --save
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

REPORTS_DIR = ROOT / "docs" / "reports" / "governance_audit"
ACKS_PATH = ROOT / "docs" / "reports" / "governance" / "_acknowledgments.json"
FORGE_REPORTS_DIR = ROOT / "research" / "data" / "fql_forge" / "reports"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
LAUNCHAGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
LOGS_DIR = ROOT / "research" / "logs"
DIGEST_REPORTS_DIR = ROOT / "docs" / "reports" / "fql_forge_morning_digest"
MONTHLY_REPORTS_DIR = ROOT / "docs" / "reports" / "monthly_system_review"
HYGIENE_REPORTS_DIR = ROOT / "docs" / "reports" / "memory_hygiene"
FEEDBACK_REPORTS_DIR = ROOT / "docs" / "reports" / "forge_source_feedback"

# Review load weights per operator spec
REVIEW_WEIGHTS = {
    "report": 1,
    "preflight": 2,
    "registry_proposal": 3,
    "automation_activation": 5,
    "lane_a_change": 5,
}

# Backlog thresholds (matches morning digest)
BACKLOG_GREEN_MAX = 5
BACKLOG_YELLOW_MAX = 15

# Cost-of-evidence placeholders (operator can refine when actuals are available)
COST_PLACEHOLDER_PER_SECOND_USD = 0.001  # rough Anthropic-API-equivalent placeholder

# Expected agents and which have tripwire mechanisms
AGENT_TRIPWIRE_STATUS = {
    "ai.openclaw.gateway":            False,
    "com.fql.watchdog":               True,   # the watchdog IS the tripwire mechanism
    "com.fql.claw-control-loop":      False,
    "com.fql.forward-day":            False,
    "com.fql.daily-research":         False,
    "com.fql.operator-digest":        False,
    "com.fql.twice-weekly-research":  False,
    "com.fql.weekly-research":        False,
    "com.fql.source-helpers":         False,
    "com.fql.treasury-rolldown-monthly": True,  # has self-test
    "com.fql.forge-daily-loop":       True,   # 5 explicit tripwires
    "com.fql.forge-morning-digest":   False,
    "com.fql.monthly-system-review":  False,
}

# Expected log file pattern + max-staleness (hours) per agent
AGENT_LOG_HEALTH = {
    "com.fql.daily-research":         ("daily_run_*.log", 30),
    "com.fql.weekly-research":        ("weekly_run_*.log", 30 * 24),
    "com.fql.twice-weekly-research":  ("twice_weekly*.log", 4 * 24),
    "com.fql.source-helpers":         ("source_helpers*.log", 5 * 24),
    "com.fql.forge-daily-loop":       ("forge_daily_loop*.log", 30),
    "com.fql.forge-morning-digest":   ("launchd_forge_morning_digest*.log", 30),
    "com.fql.monthly-system-review":  ("launchd_monthly_review*.log", 32 * 24),
    "com.fql.treasury-rolldown-monthly": ("treasury_rolldown_monthly*.log", 30),
    "com.fql.forward-day":            ("forward_runner*.log", 30),
    "com.fql.watchdog":               ("watchdog*.log", 0.5),
    "com.fql.claw-control-loop":      ("claw_control*.log", 1),
    "com.fql.operator-digest":        ("operator_digest*.log", 30),
}


@dataclass
class SectionOutput:
    title: str
    body: str
    risks: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)


def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"_error": str(e)}


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


# ---------- section 1: evidence absorption ----------

def section_evidence_absorption(lookback_days: int) -> SectionOutput:
    body, risks, actions = [], [], []

    forge_runs = []
    if FORGE_REPORTS_DIR.exists():
        cutoff = date.today() - timedelta(days=lookback_days)
        for jp in sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.json")):
            m = re.search(r"forge_daily_(\d{4}-\d{2}-\d{2})\.json", jp.name)
            if m:
                d = date.fromisoformat(m.group(1))
                if d >= cutoff:
                    data = _read_json(jp)
                    if "_error" not in data:
                        forge_runs.append((d, data))

    registry = _read_json(REGISTRY_PATH)
    registered_ids = set()
    if "_error" not in registry:
        registered_ids = {s.get("strategy_id") for s in registry.get("strategies", [])}

    distinct_passes = set()
    repeated_after_register = []
    for d, data in forge_runs:
        for r in data.get("results", []):
            if r.get("verdict") == "PASS":
                cid = r.get("candidate")
                distinct_passes.add(cid)
                if cid in registered_ids:
                    repeated_after_register.append((d, cid))

    pass_pending = distinct_passes - registered_ids
    pass_in_registry = distinct_passes & registered_ids

    md_reports = sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.md")) if FORGE_REPORTS_DIR.exists() else []

    body.append(f"### Counts (lookback {lookback_days}d)\n")
    body.append(f"- Forge fires in window: **{len(forge_runs)}**")
    body.append(f"- distinct PASS candidates: **{len(distinct_passes)}**")
    body.append(f"  - already in registry: {len(pass_in_registry)} ✅")
    body.append(f"  - **pending review (not in registry): {len(pass_pending)}**")
    body.append(f"- daily Forge reports on disk: {len(md_reports)}")
    body.append(f"- repeated PASS-tests of already-registered candidates: {len(repeated_after_register)}")

    if pass_pending:
        body.append(f"\n### Pending PASS candidates")
        for cid in sorted(pass_pending)[:8]:
            body.append(f"- `{cid}`")
        if len(pass_pending) > 8:
            body.append(f"- ... and {len(pass_pending) - 8} more")

    n_pending = len(pass_pending)
    if n_pending <= BACKLOG_GREEN_MAX:
        score = "🟢 **GREEN**"
    elif n_pending <= BACKLOG_YELLOW_MAX:
        score = "🟡 **YELLOW**"
        actions.append(f"Triage {n_pending} pending PASS candidate(s) before next batch register cycle")
    else:
        score = "🔴 **RED**"
        risks.append(f"Evidence backlog at {n_pending} pending PASSes (>{BACKLOG_YELLOW_MAX})")
        actions.append(f"HALT cadence increase; absorb {n_pending} pending PASSes before adding fires")

    body.append(f"\n### Backlog status: {score}")
    body.append(f"- thresholds: GREEN ≤ {BACKLOG_GREEN_MAX} / YELLOW ≤ {BACKLOG_YELLOW_MAX} / RED > {BACKLOG_YELLOW_MAX}")

    body.append(f"\n### Repeated-already-registered diagnostic\n")
    if repeated_after_register:
        body.append(f"- {len(repeated_after_register)} candidate-tests in window are RE-TESTING already-registered candidates.")
        body.append(f"- Not a problem at low counts (cross-validation), but if same candidate is hit >3× without verdict change, prune from rotation.")
        from collections import Counter
        retest_counts = Counter(cid for _, cid in repeated_after_register)
        for cid, n in retest_counts.most_common(5):
            mark = " ⚠️ prune candidate" if n >= 3 else ""
            body.append(f"  - `{cid}`: {n} re-tests{mark}")
    else:
        body.append("- (none in window — pool rotation working)")

    return SectionOutput("Evidence Absorption Status", "\n".join(body), risks, actions)


# ---------- section 2: operator review load score ----------

def _load_acknowledgments() -> dict:
    """Returns {short_sha: {status, type, due_date?, note}}."""
    if not ACKS_PATH.exists():
        return {}
    try:
        data = json.loads(ACKS_PATH.read_text())
    except Exception:
        return {}
    out = {}
    for entry in data.get("acknowledgments", []):
        sha = entry.get("commit", "")
        if sha:
            out[sha[:7]] = entry
    return out


def _ack_discount(entry: dict) -> float:
    """Return weight multiplier for an acknowledged commit. 0.0 = full discount, 1.0 = full weight."""
    status = entry.get("status", "")
    if status in ("VERIFIED_CLEAN", "ACKNOWLEDGED", "SUPERSEDED"):
        return 0.0
    if status == "DEFERRED_UNTIL_DATE":
        due = entry.get("due_date")
        if due:
            try:
                if date.today() < date.fromisoformat(due):
                    return 0.2  # light weight while deferred
                else:
                    return 1.0  # past due — count normally
            except Exception:
                return 1.0
        return 0.2
    return 1.0


def section_review_load_score(lookback_days: int) -> SectionOutput:
    body, risks, actions = [], [], []
    acks = _load_acknowledgments()

    try:
        since = (date.today() - timedelta(days=lookback_days)).isoformat()
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", f"--since={since}", "--pretty=format:%H||%s"],
            text=True, timeout=15,
        )
        commits = [line.split("||", 1) for line in out.splitlines() if "||" in line]
    except Exception as e:
        return SectionOutput("Operator Review Load Score", f"git log read failed: {e}",
                             risks=[f"review load not computable: {e}"])

    raw_breakdown = Counter()
    eff_breakdown_pts = Counter()  # tracks effective points (weight × multiplier)
    items_by_class = {k: [] for k in REVIEW_WEIGHTS}
    ack_count = 0
    ack_total_discount = 0.0
    deferred_count = 0

    for sha, msg in commits:
        msg_lower = msg.lower()
        short_sha = sha[:7]

        # Classify
        if any(k in msg_lower for k in ["activate", "launchctl bootstrap", "phase b activation", "loaded plist"]):
            cls = "automation_activation"
        elif any(k in msg_lower for k in ["lane a", "live", "promote ", "promotion"]):
            cls = "lane_a_change"
        elif any(k in msg_lower for k in ["batch register", "registry append"]):
            cls = "registry_proposal"
        elif any(k in msg_lower for k in ["pre-flight", "preflight", "_draft_"]):
            cls = "preflight"
        else:
            cls = "report"

        weight = REVIEW_WEIGHTS[cls]
        raw_breakdown[cls] += 1

        # Apply acknowledgment discount if present
        ack = acks.get(short_sha)
        if ack:
            multiplier = _ack_discount(ack)
            ack_count += 1
            ack_total_discount += weight * (1 - multiplier)
            if ack.get("status") == "DEFERRED_UNTIL_DATE":
                deferred_count += 1
            eff_breakdown_pts[cls] += weight * multiplier
            items_by_class[cls].append((short_sha, msg, ack.get("status", ""), multiplier))
        else:
            eff_breakdown_pts[cls] += weight
            items_by_class[cls].append((short_sha, msg, "", 1.0))

    raw_score = sum(REVIEW_WEIGHTS[k] * v for k, v in raw_breakdown.items())
    eff_score = sum(eff_breakdown_pts.values())

    body.append(f"### Review Load Score (lookback {lookback_days}d)\n")
    body.append(f"**Raw score (all commits): {raw_score}**  |  **Effective score (after acknowledgments): {eff_score:.1f}**")
    body.append(f"- acknowledgments applied: {ack_count} (discount total: {ack_total_discount:.1f} pts)")
    body.append(f"- of those, deferred-until-date: {deferred_count}")
    body.append(f"- ledger: `{ACKS_PATH.relative_to(ROOT)}`")

    body.append(f"\n| Class | Weight | Raw count | Raw pts | Effective pts |")
    body.append("|---|---:|---:|---:|---:|")
    for k in REVIEW_WEIGHTS:
        cnt = raw_breakdown[k]
        body.append(f"| {k} | {REVIEW_WEIGHTS[k]} | {cnt} | {REVIEW_WEIGHTS[k] * cnt} | {eff_breakdown_pts[k]:.1f} |")
    body.append(f"\n- commits in window: {len(commits)}")

    # Density bands based on EFFECTIVE score (the metric that matters)
    if eff_score < 15:
        density = "🟢 **GREEN — manageable**"
    elif eff_score < 35:
        density = "🟡 **YELLOW — review load elevated**"
        risks.append(f"Operator review density elevated (effective {eff_score:.1f})")
    else:
        density = "🔴 **RED — operator overload risk**"
        risks.append(f"Operator review density at OVERLOAD threshold (effective {eff_score:.1f})")
        actions.append("STOP building; consolidate, review, and absorb before adding new modules")

    body.append(f"\n### Density: {density}")
    body.append(f"- bands (7d window, on EFFECTIVE score): GREEN <15 / YELLOW 15-34 / RED ≥35")
    body.append(f"- raw score reflects total commits; effective score reflects unresolved review burden")

    body.append(f"\n### Unresolved items (full or partial weight)")
    unresolved = []
    for cls in REVIEW_WEIGHTS:
        for sha, msg, status, mult in items_by_class[cls]:
            if mult > 0:
                unresolved.append((cls, sha, msg, status, mult, REVIEW_WEIGHTS[cls] * mult))
    unresolved.sort(key=lambda x: -x[5])  # biggest unresolved weight first
    if not unresolved:
        body.append("- ✅ no unresolved review burden — every commit in window has been acknowledged")
    else:
        body.append("| Class | SHA | Status | Pts | Message |")
        body.append("|---|---|---|---:|---|")
        for cls, sha, msg, status, mult, pts in unresolved[:15]:
            status_str = status if status else "(unacked)"
            body.append(f"| {cls} | `{sha}` | {status_str} | {pts:.1f} | {msg[:70]} |")
        if len(unresolved) > 15:
            body.append(f"| ... | | | | and {len(unresolved) - 15} more |")

    return SectionOutput("Operator Review Load Score", "\n".join(body), risks, actions)


# ---------- section 3: Lane B self-healing audit ----------

def section_lane_b_self_healing() -> SectionOutput:
    body, risks, actions = [], [], []
    loaded = _launchctl_loaded()

    body.append("### Per-agent self-healing posture\n")
    body.append("| Agent | Loaded | Tripwire mechanism | Last log age | Output health |")
    body.append("|---|:---:|:---:|---|:---:|")

    now = datetime.now()
    for label, has_tripwire in AGENT_TRIPWIRE_STATUS.items():
        is_loaded = "✅" if label in loaded else "❌"
        tw = "✅" if has_tripwire else "—"

        log_age_str = "—"
        log_health = "—"
        if label in AGENT_LOG_HEALTH:
            pattern, max_h = AGENT_LOG_HEALTH[label]
            matches = sorted(LOGS_DIR.glob(pattern)) if LOGS_DIR.exists() else []
            if matches:
                age_h = (now - datetime.fromtimestamp(matches[-1].stat().st_mtime)).total_seconds() / 3600
                if age_h < 24:
                    log_age_str = f"{age_h:.1f}h"
                elif age_h < 24 * 7:
                    log_age_str = f"{age_h/24:.1f}d"
                else:
                    log_age_str = f"{age_h/24:.0f}d"
                if age_h <= max_h:
                    log_health = "✅"
                else:
                    log_health = "⚠️ stale"
                    risks.append(f"`{label}`: log {age_h:.0f}h old (threshold {max_h}h)")
            else:
                log_age_str = "(no logs)"
                log_health = "⚠️"
                risks.append(f"`{label}`: no logs found matching `{pattern}`")

        body.append(f"| `{label}` | {is_loaded} | {tw} | {log_age_str} | {log_health} |")

    no_tripwire = [k for k, v in AGENT_TRIPWIRE_STATUS.items() if not v and k in loaded and k != "ai.openclaw.gateway"]
    body.append(f"\n### Agents WITHOUT tripwire mechanism ({len(no_tripwire)})\n")
    for label in no_tripwire:
        body.append(f"- `{label}`")
    if no_tripwire:
        actions.append(f"Roadmap: extend tripwire/self-halt pattern from forge-daily-loop to {len(no_tripwire)} agents that lack it")

    return SectionOutput("Lane B Self-Healing Audit", "\n".join(body), risks, actions)


# ---------- section 4: cost-of-evidence ----------

def section_cost_of_evidence(lookback_days: int) -> SectionOutput:
    body, risks, actions = [], [], []

    forge_runs = []
    if FORGE_REPORTS_DIR.exists():
        cutoff = date.today() - timedelta(days=lookback_days)
        for jp in sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.json")):
            m = re.search(r"forge_daily_(\d{4}-\d{2}-\d{2})\.json", jp.name)
            if m:
                d = date.fromisoformat(m.group(1))
                if d >= cutoff:
                    data = _read_json(jp)
                    if "_error" not in data:
                        forge_runs.append((d, data))

    if not forge_runs:
        return SectionOutput("Cost-of-Evidence", "- (no Forge fires in lookback window)")

    runtimes = [d.get("runtime_total_sec", 0) for _, d in forge_runs]
    candidates_per_fire = [d.get("candidates_tested", 0) for _, d in forge_runs]
    total_runtime = sum(runtimes)
    total_candidates = sum(candidates_per_fire)
    avg_per_candidate = total_runtime / total_candidates if total_candidates else 0

    body.append(f"### Forge fires in window: {len(forge_runs)}\n")
    body.append(f"- total runtime: **{total_runtime:.1f}s**")
    body.append(f"- candidates tested: **{total_candidates}**")
    body.append(f"- avg runtime per candidate: **{avg_per_candidate:.1f}s**")
    body.append(f"- avg candidates per fire: {total_candidates / len(forge_runs):.1f}")

    placeholder_cost = total_runtime * COST_PLACEHOLDER_PER_SECOND_USD
    body.append(f"\n### Placeholder cost\n")
    body.append(f"- assumes ${COST_PLACEHOLDER_PER_SECOND_USD}/s (rough placeholder; replace when actual cost data available)")
    body.append(f"- estimated window cost: **${placeholder_cost:.4f}**")
    body.append(f"- per-fire cost: ${placeholder_cost / len(forge_runs):.4f}")
    body.append(f"- per-candidate cost: ${placeholder_cost / max(1, total_candidates):.4f}")

    body.append(f"\n### Per-fire detail\n")
    body.append("| Date | Runtime (s) | Candidates | s/candidate |")
    body.append("|---|---:|---:|---:|")
    for d, data in forge_runs:
        rt = data.get("runtime_total_sec", 0)
        n = data.get("candidates_tested", 0)
        per_c = rt / n if n else 0
        body.append(f"| {d} | {rt:.1f} | {n} | {per_c:.1f} |")

    body.append(f"\n### Trend\n")
    if len(runtimes) >= 3:
        recent = sum(runtimes[-3:]) / 3
        older = sum(runtimes[:-3]) / max(1, len(runtimes) - 3) if len(runtimes) > 3 else recent
        if recent > older * 1.5:
            risks.append(f"Runtime trending up: recent avg {recent:.1f}s vs older avg {older:.1f}s")
        body.append(f"- recent (last 3 fires) avg runtime: {recent:.1f}s")
    else:
        body.append("- (need ≥3 fires for trend; current sample {})".format(len(runtimes)))

    body.append(f"\n### Cadence-escalation gate suggestions (for future #10)\n")
    body.append(f"- HALT escalation if avg runtime > 240s (trending toward 5min tripwire)")
    body.append(f"- HALT escalation if per-candidate runtime > 30s (cheap-screen no longer cheap)")
    body.append(f"- HALT escalation if placeholder cost projects > $10/month at proposed cadence")

    return SectionOutput("Cost-of-Evidence Instrumentation", "\n".join(body), risks, actions)


# ---------- composer ----------

def render_report(date_str: str, sections: list[SectionOutput], generated_at: datetime) -> str:
    all_risks = [r for s in sections for r in s.risks]
    all_actions = [a for s in sections for a in s.actions]

    if any("RED" in r or "OVERLOAD" in r or "HALT" in r for r in all_risks):
        verdict = "🔴 **RED**"
    elif all_risks:
        verdict = "🟡 **YELLOW**"
    else:
        verdict = "🟢 **GREEN**"

    out = [f"# FQL Governance Audit — {date_str}\n"]
    out.append(f"**Generated:** {generated_at.isoformat(timespec='seconds')}")
    out.append(f"**Scope:** evidence absorption + review load + Lane B self-healing + cost-of-evidence")
    out.append(f"**Safety:** report-only; no mutation of any surface\n")
    out.append(f"**Overall posture:** {verdict}  |  Risks: {len(all_risks)}  |  Actions surfaced: {len(all_actions)}\n")
    out.append("---\n")

    out.append("## Summary — actions surfaced\n")
    if all_actions:
        for i, a in enumerate(all_actions, start=1):
            out.append(f"{i}. {a}")
    else:
        out.append("- (none — system in steady state)")
    out.append("\n---\n")

    for i, sec in enumerate(sections, start=1):
        out.append(f"## {i}. {sec.title}\n")
        out.append(sec.body)
        out.append("\n---\n")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="FQL Governance Audit (Phase A — report-only)")
    ap.add_argument("--lookback-days", type=int, default=7, help="Days of history to consider")
    ap.add_argument("--save", action="store_true", help="Write report to docs/reports/governance_audit/")
    ap.add_argument("--dry-run", action="store_true", help="Generate but do not write")
    args = ap.parse_args()

    today = date.today().isoformat()
    print(f"FQL Governance Audit — {today} — lookback {args.lookback_days}d")
    print("=" * 78)

    sections = [
        section_evidence_absorption(args.lookback_days),
        section_review_load_score(args.lookback_days),
        section_lane_b_self_healing(),
        section_cost_of_evidence(args.lookback_days),
    ]

    generated_at = datetime.now()
    report = render_report(today, sections, generated_at)

    print(f"Report length: {len(report)} chars, {report.count(chr(10))} lines")
    print(f"Total risks: {sum(len(s.risks) for s in sections)}")
    print(f"Total actions: {sum(len(s.actions) for s in sections)}")

    if args.dry_run:
        print("\n[DRY-RUN] preview (first 60 lines):\n")
        print("\n".join(report.splitlines()[:60]))
        return

    if not args.save:
        print("\n--- summary ---")
        for s in sections:
            print(f"  {s.title}: {len(s.risks)} risks, {len(s.actions)} actions")
        print("\n(use --save to write, or --dry-run for full preview)")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{today}_governance_audit.md"
    out_path.write_text(report)
    print(f"\n[WRITE] {out_path}")
    print("\n[SAFETY] Report-only. No mutation.")


if __name__ == "__main__":
    main()
