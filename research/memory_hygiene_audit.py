#!/usr/bin/env python3
"""FQL Memory Hygiene Audit — detect drift between claimed and actual state.

Catches the kind of drift that compounds silently as the system evolves:
- Memory says "every 3 days" but plist actually fires Sun+Wed
- Memory claims 151 strategies but registry has 163
- CLAUDE.md probation roster mentions strategies no longer in registry
- Path references in memory point to files that have moved or been removed

Safety contract (Phase A — manual CLI):
- Report-only. No mutation of memory / docs / registry / plists / launchd state.
- All file writes target docs/reports/memory_hygiene/.
- Reads: memory dir, key docs, registry JSON, launchctl, plist files, runner pool.

Usage:
    python3 research/memory_hygiene_audit.py                # report to stdout
    python3 research/memory_hygiene_audit.py --save         # write to docs/reports/
    python3 research/memory_hygiene_audit.py --dry-run      # generate but no write
"""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPORTS_DIR = ROOT / "docs" / "reports" / "memory_hygiene"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "-Users-chasefisher" / "memory"
LAUNCHAGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
CLAUDE_MD = ROOT / "CLAUDE.md"
FORGE_RUNNER = ROOT / "research" / "fql_forge_batch_runner.py"
SCRIPTS_DIR = ROOT / "scripts"


@dataclass
class Drift:
    severity: str  # "INFO" | "WARN" | "FAIL"
    check: str
    detail: str
    suggested_fix: str = ""


@dataclass
class CheckResult:
    name: str
    body: str
    drifts: list[Drift] = field(default_factory=list)


# ---------- helpers ----------

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


def _read_plist_schedule(plist_path: Path) -> str:
    """Read StartCalendarInterval / StartInterval / KeepAlive and produce a
    human-readable cadence string."""
    if not plist_path.exists():
        return "(plist not found)"
    try:
        out = subprocess.check_output(
            ["/usr/libexec/PlistBuddy", "-c", "Print :StartInterval", str(plist_path)],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
        if out and out.isdigit():
            secs = int(out)
            if secs % 60 == 0:
                mins = secs // 60
                if mins < 60:
                    return f"every {mins} min"
                hrs = mins / 60
                return f"every {hrs:.1f}h"
            return f"every {secs}s"
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["/usr/libexec/PlistBuddy", "-c", "Print :StartCalendarInterval", str(plist_path)],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
        )
        weekdays = re.findall(r"Weekday\s*=\s*(\d+)", out)
        hours = re.findall(r"Hour\s*=\s*(\d+)", out)
        minutes = re.findall(r"Minute\s*=\s*(\d+)", out)
        days = re.findall(r"Day\s*=\s*(\d+)", out)
        if weekdays and hours:
            wd_map = {"0": "Sun", "1": "Mon", "2": "Tue", "3": "Wed", "4": "Thu", "5": "Fri", "6": "Sat"}
            wd_set = sorted(set(weekdays), key=int)
            wd_names = [wd_map.get(w, f"?{w}") for w in wd_set]
            if wd_set == ["1", "2", "3", "4", "5"]:
                wd_str = "weekdays"
            else:
                wd_str = "+".join(wd_names)
            hour = hours[0]
            minute = minutes[0] if minutes else "00"
            return f"{wd_str} {int(hour):02d}:{minute.zfill(2)}"
        if days and hours:
            return f"day-{days[0]} {int(hours[0]):02d}:{(minutes[0] if minutes else '00').zfill(2)}"
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["/usr/libexec/PlistBuddy", "-c", "Print :KeepAlive", str(plist_path)],
            text=True, stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
        if out.lower() == "true":
            return "KeepAlive (continuous)"
    except Exception:
        pass

    return "(no schedule fields detected)"


# ---------- checks ----------

def check_launchd_agents() -> CheckResult:
    body, drifts = [], []
    loaded = _launchctl_loaded()

    repo_plists = sorted(SCRIPTS_DIR.glob("com.fql.*.plist"))
    repo_disabled = sorted(SCRIPTS_DIR.glob("com.fql.*.plist.disabled"))
    deployed_plists = sorted(LAUNCHAGENTS_DIR.glob("com.fql.*.plist")) if LAUNCHAGENTS_DIR.exists() else []
    deployed_plus_openclaw = sorted(LAUNCHAGENTS_DIR.glob("*.plist")) if LAUNCHAGENTS_DIR.exists() else []

    repo_labels = {p.stem for p in repo_plists}
    repo_disabled_labels = {p.name.replace(".plist.disabled", "") for p in repo_disabled}
    deployed_labels = {p.stem for p in deployed_plus_openclaw if p.stem.startswith("com.fql.") or p.stem == "ai.openclaw.gateway"}

    body.append(f"### Inventory\n")
    body.append(f"- repo enabled plists (`scripts/com.fql.*.plist`): {len(repo_labels)}")
    body.append(f"- repo disabled plists (`*.plist.disabled`): {len(repo_disabled_labels)}: {sorted(repo_disabled_labels)}")
    body.append(f"- deployed plists (`~/Library/LaunchAgents/`): {len(deployed_labels)}")
    body.append(f"- launchctl loaded: {len(loaded)}")

    deployed_not_loaded = deployed_labels - loaded
    if deployed_not_loaded:
        for label in sorted(deployed_not_loaded):
            drifts.append(Drift("WARN", "deployed-not-loaded",
                                f"`{label}` plist exists in LaunchAgents but launchctl shows not loaded",
                                "launchctl bootstrap or remove the plist"))

    loaded_not_deployed = loaded - deployed_labels
    if loaded_not_deployed:
        for label in sorted(loaded_not_deployed):
            drifts.append(Drift("WARN", "loaded-not-in-launchagents",
                                f"`{label}` is launchctl-loaded but no plist in `~/Library/LaunchAgents/`",
                                "investigate (loaded from another path?)"))

    repo_not_deployed = repo_labels - deployed_labels
    if repo_not_deployed:
        for label in sorted(repo_not_deployed):
            drifts.append(Drift("INFO", "repo-not-deployed",
                                f"`{label}` exists in `scripts/` but not deployed",
                                "intentional or needs deployment?"))

    deployed_not_in_repo = deployed_labels - repo_labels - {l + ".disabled" for l in deployed_labels}
    deployed_not_in_repo = {d for d in deployed_not_in_repo
                            if d not in {l for l in repo_disabled_labels}
                            and d != "ai.openclaw.gateway"}
    if deployed_not_in_repo:
        for label in sorted(deployed_not_in_repo):
            drifts.append(Drift("WARN", "deployed-not-in-repo",
                                f"`{label}` deployed but no source in repo",
                                "add to repo or remove deployment"))

    body.append(f"\n### Checks")
    if drifts:
        for d in drifts:
            body.append(f"- {d.severity}: {d.detail}")
    else:
        body.append(f"- ✅ All loaded agents have deployed plists; all deployed have source-of-truth in repo.")

    return CheckResult("Launchd agents — repo / deployed / loaded coherence", "\n".join(body), drifts)


def check_plist_cadences() -> CheckResult:
    body, drifts = [], []
    loaded = _launchctl_loaded()
    deployed_plists = sorted(LAUNCHAGENTS_DIR.glob("com.fql.*.plist")) if LAUNCHAGENTS_DIR.exists() else []

    fql_state = MEMORY_DIR / "project_fql_state.md"
    state_text = fql_state.read_text() if fql_state.exists() else ""
    claude_md_text = CLAUDE_MD.read_text() if CLAUDE_MD.exists() else ""
    combined = state_text + "\n" + claude_md_text

    body.append("### Per-agent claimed vs actual cadence\n")
    body.append("| Agent | Claimed (memory/CLAUDE.md) | Actual (plist) | Match? |")
    body.append("|---|---|---|:---:|")

    for plist_path in deployed_plists:
        label = plist_path.stem
        actual = _read_plist_schedule(plist_path)

        claimed = "—"
        # Find the line containing the label and grab nearby cadence text.
        # Strip the agent label from the line first so we don't match cadence
        # words inside the label itself (e.g., "weekly" inside "weekly-research").
        cadence_re = re.compile(
            r"\b(every\s+\d+\s?(?:min|hour|h|day|business\s+day)s?|"
            r"weekdays?\s+\d+:\d+|"
            r"(?:Sun|Mon|Tue|Wed|Thu|Fri|Sat)(?:[\+/](?:Sun|Mon|Tue|Wed|Thu|Fri|Sat))*\s*\d{1,2}:\d{2}|"
            r"every\s+\d+\s+days?|"
            r"first\s+business\s+day|"
            r"\bweekly\b|\bmonthly\b|\bdaily\b|\bcontinuous\b|KeepAlive)\b",
            re.IGNORECASE,
        )
        for line in combined.splitlines():
            if label in line:
                stripped = line.replace(label, " ")
                m = cadence_re.search(stripped)
                if m:
                    claimed = m.group(0)
                    break

        match = "?"
        if claimed != "—":
            actual_normalized = actual.lower().replace(" ", "")
            claimed_normalized = claimed.lower().replace(" ", "")
            actual_keywords = set(re.findall(r"\w+", actual.lower()))
            claimed_keywords = set(re.findall(r"\w+", claimed.lower()))
            shared = actual_keywords & claimed_keywords
            if shared and (claimed_normalized in actual_normalized or actual_normalized in claimed_normalized or len(shared) >= 2):
                match = "✅"
            else:
                match = "❌"
                drifts.append(Drift("WARN", "cadence-drift",
                                    f"`{label}`: claimed `{claimed}` vs actual `{actual}`",
                                    f"update memory/CLAUDE.md to say `{actual}`"))

        body.append(f"| `{label}` | {claimed} | {actual} | {match} |")

    if not drifts:
        body.append(f"\n- ✅ No cadence drift detected (or claims too vague to mismatch).")

    return CheckResult("Plist cadence — claimed vs actual", "\n".join(body), drifts)


def check_registry_summary() -> CheckResult:
    body, drifts = [], []

    try:
        registry = json.loads(REGISTRY_PATH.read_text())
        strategies = registry.get("strategies", [])
        actual_total = len(strategies)
        actual_status = Counter(s.get("status") for s in strategies)
    except Exception as e:
        return CheckResult("Registry summary", f"Registry read failed: {e}",
                           [Drift("FAIL", "registry-unreadable", str(e), "fix JSON")])

    body.append(f"### Actual registry state\n")
    body.append(f"- total: {actual_total}")
    body.append(f"- by status: {dict(actual_status.most_common())}")

    fql_state = MEMORY_DIR / "project_fql_state.md"
    claude_md = CLAUDE_MD
    sources = [("project_fql_state.md", fql_state), ("CLAUDE.md", claude_md)]

    body.append(f"\n### Claims in memory/docs\n")
    for label, path in sources:
        if not path.exists():
            continue
        text = path.read_text()
        for m in re.finditer(r"(\d+)\+?\s+strateg(?:ies|y)\b", text, re.IGNORECASE):
            claimed = int(m.group(1))
            ctx = text[max(0, m.start()-40):m.end()+40].replace("\n", " ")
            drift = abs(claimed - actual_total)
            ok = drift <= 5
            body.append(f"- `{label}`: claims `{claimed}` (actual {actual_total}, Δ {claimed-actual_total}) — {'✅' if ok else '❌'}")
            body.append(f"  - context: \"...{ctx.strip()}...\"")
            if not ok:
                drifts.append(Drift("WARN", "registry-count-drift",
                                    f"`{label}` claims {claimed} strategies, actual is {actual_total} (Δ {claimed-actual_total})",
                                    f"update {label} to say `{actual_total}`"))

    fql_state_text = fql_state.read_text() if fql_state.exists() else ""
    status_claim_match = re.search(r"\(idea:\s*(\d+).*?probation:\s*(\d+).*?core:\s*(\d+)", fql_state_text)
    if not status_claim_match:
        status_claim_match = re.search(r"idea:\s*(\d+),\s*rejected:\s*(\d+),\s*archived:\s*(\d+),\s*probation:\s*(\d+),\s*core:\s*(\d+),\s*monitor:\s*(\d+)", fql_state_text)
    if not status_claim_match:
        status_claim_match = re.search(r"idea:\s*(\d+).*?rejected:\s*(\d+).*?archived:\s*(\d+).*?probation:\s*(\d+).*?core:\s*(\d+).*?monitor:\s*(\d+)", fql_state_text, re.DOTALL)

    if status_claim_match:
        body.append(f"\n### Status breakdown claim found in memory")
        body.append(f"- match groups: {status_claim_match.groups()}")
        body.append(f"- (manual cross-check: compare against actual {dict(actual_status)})")

    return CheckResult("Registry summary — claimed vs actual", "\n".join(body), drifts)


def check_probation_roster() -> CheckResult:
    body, drifts = [], []

    try:
        registry = json.loads(REGISTRY_PATH.read_text())
        actual_probation = sorted({s.get("strategy_id") for s in registry.get("strategies", [])
                                   if s.get("status") == "probation"})
    except Exception as e:
        return CheckResult("Probation roster", f"Registry read failed: {e}",
                           [Drift("FAIL", "registry-unreadable", str(e), "fix JSON")])

    body.append(f"### Actual probation roster ({len(actual_probation)})\n")
    for sid in actual_probation:
        body.append(f"- {sid}")

    if not CLAUDE_MD.exists():
        return CheckResult("Probation roster — CLAUDE.md vs registry", "\n".join(body), drifts)

    claude_text = CLAUDE_MD.read_text()
    section_match = re.search(r"##\s+Probation\s+Portfolio.*?(?=\n##\s|\Z)", claude_text, re.DOTALL)
    if not section_match:
        body.append(f"\n- (CLAUDE.md does not have a 'Probation Portfolio' section)")
        return CheckResult("Probation roster — CLAUDE.md vs registry", "\n".join(body), drifts)

    section = section_match.group(0)
    # Strip lines that are explicit "removed/archived/rejected" annotations —
    # those preserve history correctly, not stale claims.
    active_lines = [ln for ln in section.splitlines()
                    if not re.search(r"removed from probation|\(archived\)|\(rejected", ln, re.IGNORECASE)]
    active_section = "\n".join(active_lines)
    claimed = sorted(set(re.findall(r"\b((?:XB-ORB-EMA-Ladder|DailyTrend|MomPB|FXBreak|NoiseBoundary|"
                                    r"PreFOMC|TV-NFP|VolManaged|ZN-Afternoon|Treasury-Rolldown)[\w\-]+)",
                                    active_section)))

    body.append(f"\n### Strategy IDs mentioned in CLAUDE.md Probation Portfolio section ({len(claimed)})\n")
    for sid in claimed:
        present = sid in actual_probation
        body.append(f"- {sid}: {'✅ in registry as probation' if present else '❌ NOT probation in registry'}")
        if not present:
            in_registry_at_all = any(s.get("strategy_id") == sid
                                     for s in registry.get("strategies", []))
            actual_status = next((s.get("status") for s in registry.get("strategies", [])
                                  if s.get("strategy_id") == sid), None)
            if in_registry_at_all:
                drifts.append(Drift("WARN", "probation-roster-drift",
                                    f"`{sid}` in CLAUDE.md probation table; actual status: `{actual_status}`",
                                    "update CLAUDE.md or re-probate"))
            else:
                drifts.append(Drift("INFO", "probation-roster-stale-mention",
                                    f"`{sid}` in CLAUDE.md probation context but not in registry (likely archived/removed)",
                                    "update CLAUDE.md"))

    not_in_claude = sorted(set(actual_probation) - set(claimed))
    if not_in_claude:
        body.append(f"\n### Probation strategies in registry but not mentioned in CLAUDE.md ({len(not_in_claude)})\n")
        for sid in not_in_claude:
            body.append(f"- {sid}")
            drifts.append(Drift("INFO", "probation-undocumented",
                                f"`{sid}` in registry as probation but not mentioned in CLAUDE.md",
                                "consider adding to CLAUDE.md"))

    return CheckResult("Probation roster — CLAUDE.md vs registry", "\n".join(body), drifts)


def check_path_references() -> CheckResult:
    body, drifts = [], []

    files_to_scan = []
    files_to_scan.extend(MEMORY_DIR.glob("*.md"))
    if CLAUDE_MD.exists():
        files_to_scan.append(CLAUDE_MD)

    body.append(f"### Files scanned: {len(files_to_scan)}\n")

    path_pattern = re.compile(r"`((?:docs|research|scripts|engine|strategies|inbox|state|logs|data)/[\w\-/\.]+\.\w{1,5})`")
    seen_paths = set()
    for f in files_to_scan:
        try:
            text = f.read_text()
        except Exception:
            continue
        for m in path_pattern.finditer(text):
            seen_paths.add((m.group(1), f.name))

    body.append(f"### Distinct path references found: {len({p for p,_ in seen_paths})}\n")

    missing = []
    for path_str, source_file in sorted(seen_paths):
        if "YYYY" in path_str or "{" in path_str or "*" in path_str or "<" in path_str:
            continue
        full = ROOT / path_str
        if not full.exists():
            missing.append((path_str, source_file))

    if missing:
        body.append(f"### Broken references ({len(missing)})\n")
        for path_str, source_file in missing[:20]:
            body.append(f"- `{path_str}` (referenced in `{source_file}`)")
            drifts.append(Drift("INFO", "broken-path-reference",
                                f"`{path_str}` cited in `{source_file}` but doesn't exist",
                                "remove reference or restore file"))
        if len(missing) > 20:
            body.append(f"- ... and {len(missing) - 20} more")
    else:
        body.append(f"- ✅ No broken path references in memory/CLAUDE.md")

    return CheckResult("Path references — claimed paths vs filesystem", "\n".join(body), drifts)


def check_forge_pool_size() -> CheckResult:
    body, drifts = [], []

    if not FORGE_RUNNER.exists():
        return CheckResult("Forge candidate pool size", "fql_forge_batch_runner.py not found",
                           [Drift("FAIL", "runner-missing", "runner script absent", "investigate")])

    text = FORGE_RUNNER.read_text()
    body_match = re.search(r"^CANDIDATES\s*=\s*\{(.*?)\n\}", text, re.MULTILINE | re.DOTALL)
    if not body_match:
        return CheckResult("Forge candidate pool size", "could not parse CANDIDATES dict",
                           [Drift("WARN", "candidates-unparsable", "regex failed", "verify file shape")])

    actual_count = len(re.findall(r"^\s+\"[A-Z][\w\-\.]+\":\s*\{", body_match.group(1), re.MULTILINE))

    body.append(f"### Actual pool size: {actual_count}\n")

    fql_state = MEMORY_DIR / "project_fql_state.md"
    if fql_state.exists():
        state_text = fql_state.read_text()
        for m in re.finditer(r"(\d+)[\s\-]?(?:item|candidate)\s+pool", state_text, re.IGNORECASE):
            claimed = int(m.group(1))
            body.append(f"- memory claims `{claimed}-candidate pool` — {'✅' if claimed == actual_count else '❌ Δ ' + str(claimed - actual_count)}")
            if claimed != actual_count:
                drifts.append(Drift("WARN", "pool-size-drift",
                                    f"memory claims {claimed} pool size; actual is {actual_count}",
                                    f"update memory to `{actual_count}-candidate pool`"))

    return CheckResult("Forge candidate pool size — claimed vs actual", "\n".join(body), drifts)


# ---------- composer ----------

def render_report(date_str: str, results: list[CheckResult], generated_at: datetime) -> str:
    all_drifts = [d for r in results for d in r.drifts]
    fails = [d for d in all_drifts if d.severity == "FAIL"]
    warns = [d for d in all_drifts if d.severity == "WARN"]
    infos = [d for d in all_drifts if d.severity == "INFO"]

    if fails:
        score = "🔴 RED"
    elif warns:
        score = "🟡 YELLOW"
    else:
        score = "🟢 GREEN"

    out = [f"# Memory Hygiene Audit — {date_str}\n"]
    out.append(f"**Generated:** {generated_at.isoformat(timespec='seconds')}")
    out.append(f"**Scope:** Phase A — manual CLI; report-only, no mutation.\n")
    out.append(f"**Verdict:** {score}  |  FAIL: {len(fails)}  |  WARN: {len(warns)}  |  INFO: {len(infos)}\n")
    out.append("---\n")

    out.append("## Summary — drift items\n")
    if not all_drifts:
        out.append("No drift detected. Memory and docs match the actual system state.\n")
    else:
        out.append("| Severity | Check | Detail | Suggested fix |")
        out.append("|---|---|---|---|")
        for d in fails + warns + infos:
            out.append(f"| {d.severity} | `{d.check}` | {d.detail} | {d.suggested_fix} |")
    out.append("\n---\n")

    out.append("## Detail per check\n")
    for r in results:
        out.append(f"### {r.name}\n")
        out.append(r.body)
        out.append(f"\n*Drifts: {len(r.drifts)}*\n")
        out.append("---\n")

    out.append("## Safety affirmation\n")
    out.append("- Report-only. No memory / docs / registry / plist / launchd state mutation.\n")
    out.append("- Operator decides which drifts to fix.\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="FQL Memory Hygiene Audit (Phase A — report-only)")
    ap.add_argument("--save", action="store_true", help="Write report to docs/reports/memory_hygiene/")
    ap.add_argument("--dry-run", action="store_true", help="Generate but do not write")
    args = ap.parse_args()

    today = date.today().isoformat()
    print(f"FQL Memory Hygiene Audit — {today}")
    print("=" * 78)

    results = [
        check_launchd_agents(),
        check_plist_cadences(),
        check_registry_summary(),
        check_probation_roster(),
        check_path_references(),
        check_forge_pool_size(),
    ]

    generated_at = datetime.now()
    report = render_report(today, results, generated_at)

    total_drifts = sum(len(r.drifts) for r in results)
    fails = sum(1 for r in results for d in r.drifts if d.severity == "FAIL")
    warns = sum(1 for r in results for d in r.drifts if d.severity == "WARN")
    infos = sum(1 for r in results for d in r.drifts if d.severity == "INFO")

    print(f"Checks run: {len(results)}")
    print(f"Drifts: {total_drifts} (FAIL {fails} / WARN {warns} / INFO {infos})")
    print(f"Report: {len(report)} chars, {report.count(chr(10))} lines")

    if args.dry_run:
        print("\n[DRY-RUN] preview (first 80 lines):\n")
        print("\n".join(report.splitlines()[:80]))
        return

    if not args.save:
        print("\n--- summary table ---")
        for r in results:
            print(f"  {r.name}: {len(r.drifts)} drift(s)")
        print("\n(use --save to write, or --dry-run for full preview)")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{today}_memory_hygiene.md"
    out_path.write_text(report)
    print(f"\n[WRITE] {out_path}")
    print("\n[SAFETY] Report-only. No mutation.")


if __name__ == "__main__":
    main()
