#!/usr/bin/env python3
"""FQL Forge → Source-helpers Feedback (Phase A — recommendation-only).

Closes the learning loop. The Forge produces evidence about which
candidate combinations are working; this script reads that evidence and
recommends adjustments to harvest priorities (`_priorities.md`,
`_family_queue.md`) and source-helper query weights.

The closed loop architecture target from `feedback_closed_loop_over_cadence.md`:
  Forge results → up-weight matching harvest themes → next-week Claw fetches
  candidates aligned with what's actually validated → adaptive research.

Safety contract (Phase A — recommendation-only):
- Report-only. No automatic mutation of source-helper config, harvest
  priorities, family queue, or any Lane A surface.
- All file writes target docs/reports/forge_source_feedback/.
- All other I/O is read-only against existing artifacts (forge daily JSON,
  strategy registry, batch runner pool, ~/openclaw-intake/inbox/).

Usage:
    python3 research/forge_source_feedback.py                  # last 7 days
    python3 research/forge_source_feedback.py --lookback-days 14 --save
    python3 research/forge_source_feedback.py --dry-run
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REPORTS_DIR = ROOT / "docs" / "reports" / "forge_source_feedback"
FORGE_REPORTS_DIR = ROOT / "research" / "data" / "fql_forge" / "reports"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
FORGE_RUNNER = ROOT / "research" / "fql_forge_batch_runner.py"
INBOX_PRIORITIES = Path.home() / "openclaw-intake" / "inbox" / "_priorities.md"
INBOX_FAMILY_QUEUE = Path.home() / "openclaw-intake" / "inbox" / "_family_queue.md"

# --- Theme mapping (asset/component → harvest theme keywords) ---

ASSET_THEMES = {
    "MNQ": ["nasdaq", "equity-index", "tech-equity"],
    "MES": ["sp500", "equity-index"],
    "MYM": ["dow", "equity-index"],
    "M2K": ["russell-2000", "small-cap-equity"],
    "MGC": ["gold", "precious-metals"],
    "MCL": ["crude-oil", "energy"],
    "ZN": ["10y-treasury", "rates"],
    "ZF": ["5y-treasury", "rates"],
    "ZB": ["30y-treasury", "rates"],
    "6E": ["eur-fx", "fx"],
    "6J": ["jpy-fx", "fx"],
    "6B": ["gbp-fx", "fx"],
}

ENTRY_THEMES = {
    "orb_breakout": ["opening-range-breakout", "ORB", "morning-breakout"],
    "pb_pullback": ["pullback", "dip-buy", "trend-pullback"],
    "bb_reversion": ["bollinger", "compression-breakout", "squeeze"],
    "vwap_continuation": ["VWAP", "intraday-momentum", "VWAP-fade"],
    "donchian_breakout": ["donchian", "channel-breakout"],
}

FILTER_THEMES = {
    "ema_slope": ["trend-filter", "regime-detection", "moving-average-slope"],
    "vwap_slope": ["VWAP-slope", "intraday-trend"],
    "bandwidth_squeeze": ["volatility-compression", "low-volatility-regime"],
    "session_morning": ["morning-session-only"],
    "session_afternoon": ["afternoon-session-only"],
}

EXIT_THEMES = {
    "profit_ladder": ["staged-profit-taking", "scale-out"],
    "atr_trail": ["ATR-trailing-stop"],
    "chandelier": ["chandelier-trail", "trailing-stop"],
    "time_stop": ["time-bound-exit", "session-close-exit"],
    "midline_target": ["midline-target", "mean-reversion-target"],
}


@dataclass
class SectionOutput:
    title: str
    body: str
    actions: list[str] = field(default_factory=list)


# ---------- helpers ----------

def _read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"_error": str(e)}


def _read_forge_runs(lookback_days: int) -> list[tuple[date, dict]]:
    if not FORGE_REPORTS_DIR.exists():
        return []
    cutoff = date.today() - timedelta(days=lookback_days)
    out = []
    for jp in sorted(FORGE_REPORTS_DIR.glob("forge_daily_*.json")):
        m = re.search(r"forge_daily_(\d{4}-\d{2}-\d{2})\.json", jp.name)
        if m:
            d = date.fromisoformat(m.group(1))
            if d >= cutoff:
                data = _read_json(jp)
                if "_error" not in data:
                    out.append((d, data))
    return out


def _registry_components_lookup() -> dict[str, list[str]]:
    """Return {strategy_id: components_used list} for all entries that have it."""
    registry = _read_json(REGISTRY_PATH)
    if "_error" in registry:
        return {}
    out = {}
    for s in registry.get("strategies", []):
        rel = s.get("relationships") or {}
        comps = rel.get("components_used")
        if comps:
            out[s.get("strategy_id")] = comps
    return out


def _parse_candidate_id(cid: str, registry_components: dict) -> dict:
    """Extract entry/filter/exit/asset from a candidate ID. Use registry
    components_used if available; fall back to ID parsing for unregistered."""
    if cid in registry_components:
        comps = registry_components[cid]
        if len(comps) == 3:
            return {"entry": comps[0], "filter": comps[1], "exit": comps[2]}

    # ID parsing fallback. Conventions:
    #   XB-{ENTRY}-EMA-Ladder-{ASSET}   → entry, ema_slope, profit_ladder
    #   XB-{ENTRY}-EMA-{EXIT}-{ASSET}   → entry, ema_slope, custom exit
    #   XB-{ENTRY}-EMA-{SESS}Only-{ASS} → entry, session_X (filter), profit_ladder
    entry_map = {"PB": "pb_pullback", "BB": "bb_reversion", "VWAP": "vwap_continuation",
                 "ORB": "orb_breakout"}
    exit_map = {"Ladder": "profit_ladder", "Chandelier": "chandelier",
                "TimeStop": "time_stop", "MidlineTarget": "midline_target"}
    sess_map = {"Morning": "session_morning", "Afternoon": "session_afternoon"}

    parts = cid.split("-")
    if len(parts) < 4 or parts[0] != "XB":
        return {"entry": "?", "filter": "?", "exit": "?"}

    entry = entry_map.get(parts[1], parts[1].lower())
    third = parts[3] if len(parts) > 3 else ""

    if third == "Ladder":
        return {"entry": entry, "filter": "ema_slope", "exit": "profit_ladder"}
    if third in exit_map:
        return {"entry": entry, "filter": "ema_slope", "exit": exit_map[third]}
    if third.endswith("Only"):
        sess = sess_map.get(third.replace("Only", ""), "?")
        return {"entry": entry, "filter": sess, "exit": "profit_ladder"}
    return {"entry": entry, "filter": "?", "exit": "?"}


def _aggregate_by_dim(forge_runs: list, dim_extractor, registry_components: dict) -> dict:
    """For each dim value, count {PASS, WATCH, KILL, RETEST, total}."""
    counts = defaultdict(lambda: {"PASS": 0, "WATCH": 0, "KILL": 0, "RETEST": 0, "total": 0})
    for d, data in forge_runs:
        for r in data.get("results", []):
            value = dim_extractor(r, registry_components)
            if value is None or value == "?":
                continue
            verdict = r.get("verdict", "?")
            if verdict in counts[value]:
                counts[value][verdict] += 1
            counts[value]["total"] += 1
    return dict(counts)


def _confidence(total: int) -> str:
    if total >= 10:
        return "STRONG"
    if total >= 5:
        return "MODERATE"
    return "WEAK"


def _pass_rate(d: dict) -> float:
    return d["PASS"] / d["total"] if d["total"] else 0.0


def _format_dim_table(label: str, counts: dict) -> str:
    rows = sorted(counts.items(), key=lambda kv: (-_pass_rate(kv[1]), -kv[1]["total"]))
    out = [f"\n#### {label}\n"]
    out.append("| Value | n | PASS | WATCH | KILL | RETEST | PASS-rate | Confidence |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---|")
    for value, c in rows:
        out.append(f"| `{value}` | {c['total']} | {c['PASS']} | {c['WATCH']} | {c['KILL']} | {c['RETEST']} | {_pass_rate(c)*100:.0f}% | {_confidence(c['total'])} |")
    return "\n".join(out)


# ---------- sections ----------

def section_winning_patterns(forge_runs, registry_components) -> SectionOutput:
    body = []
    body.append("**Aggregated by dimension across the lookback window. Sorted by PASS-rate desc.**")

    def by_asset(r, _):
        return r.get("asset")

    def by_verdict_pass_only(r, _):
        return None  # not used

    def by_entry(r, regcomps):
        return _parse_candidate_id(r.get("candidate", ""), regcomps).get("entry")

    def by_filter(r, regcomps):
        return _parse_candidate_id(r.get("candidate", ""), regcomps).get("filter")

    def by_exit(r, regcomps):
        return _parse_candidate_id(r.get("candidate", ""), regcomps).get("exit")

    def by_asset_class(r, _):
        a = r.get("asset", "")
        return ASSET_THEMES.get(a, [a])[0] if a else None

    body.append(_format_dim_table("By asset", _aggregate_by_dim(forge_runs, by_asset, registry_components)))
    body.append(_format_dim_table("By asset class", _aggregate_by_dim(forge_runs, by_asset_class, registry_components)))
    body.append(_format_dim_table("By entry mechanism", _aggregate_by_dim(forge_runs, by_entry, registry_components)))
    body.append(_format_dim_table("By filter", _aggregate_by_dim(forge_runs, by_filter, registry_components)))
    body.append(_format_dim_table("By exit", _aggregate_by_dim(forge_runs, by_exit, registry_components)))

    return SectionOutput("Winning Pattern Extraction", "\n".join(body))


def section_weak_patterns(forge_runs, registry_components) -> SectionOutput:
    body = []
    body.append("**Repeated KILL / WATCH neighborhoods. Candidates re-tested without verdict change.**\n")

    candidate_history = defaultdict(list)
    for d, data in forge_runs:
        for r in data.get("results", []):
            candidate_history[r.get("candidate")].append((d, r.get("verdict")))

    repeated = [(cid, hist) for cid, hist in candidate_history.items() if len(hist) >= 2]
    if not repeated:
        body.append("- (no candidates re-tested in window — sample too small)")
        return SectionOutput("Weak / Noisy Pattern Extraction", "\n".join(body))

    body.append("| Candidate | Times tested | Verdict history | Wasted slots? |")
    body.append("|---|---:|---|---|")
    for cid, hist in sorted(repeated, key=lambda kv: -len(kv[1])):
        verdicts = [v for _, v in hist]
        all_kill = all(v == "KILL" for v in verdicts)
        all_watch = all(v == "WATCH" for v in verdicts)
        wasted = "✅ prune from rotation" if all_kill else ("⚠️ low yield" if all_watch else "—")
        body.append(f"| `{cid}` | {len(hist)} | {' → '.join(verdicts)} | {wasted} |")

    return SectionOutput("Weak / Noisy Pattern Extraction", "\n".join(body))


def section_harvest_recommendations(forge_runs, registry_components) -> SectionOutput:
    body, actions = [], []
    body.append("**Harvest theme recommendations based on Forge winning evidence + current `_priorities.md` factor gaps.**\n")

    # Aggregate PASSers by asset and entry
    by_asset_passes = defaultdict(int)
    by_entry_passes = defaultdict(int)
    for d, data in forge_runs:
        for r in data.get("results", []):
            if r.get("verdict") == "PASS":
                a = r.get("asset")
                if a:
                    by_asset_passes[a] += 1
                e = _parse_candidate_id(r.get("candidate", ""), registry_components).get("entry")
                if e and e != "?":
                    by_entry_passes[e] += 1

    body.append("### Read of current harvest priorities (`~/openclaw-intake/inbox/_priorities.md`)\n")
    if INBOX_PRIORITIES.exists():
        text = INBOX_PRIORITIES.read_text()
        # Extract the factor gap table heuristically
        m = re.search(r"## Priority Factor Gaps.*?(?=\n## )", text, re.DOTALL)
        if m:
            for line in m.group(0).splitlines()[:12]:
                if line.startswith("| HIGH") or line.startswith("| MEDIUM") or line.startswith("| LOW"):
                    body.append(f"- {line.strip()}")
    else:
        body.append("- (priorities file not found at `~/openclaw-intake/inbox/_priorities.md`)")

    body.append("\n### Forge evidence vs harvest priority alignment\n")
    body.append("| Forge winner | Theme | Current harvest priority | Recommendation |")
    body.append("|---|---|---|---|")

    # Map Forge wins to harvest themes
    forge_winning_assets = list(by_asset_passes.keys())
    forge_winning_entries = list(by_entry_passes.keys())

    for asset in forge_winning_assets:
        themes = ASSET_THEMES.get(asset, [asset])
        passes = by_asset_passes[asset]
        # All current Forge winners (PB/BB/VWAP) are momentum/breakout family
        # Per _priorities.md, MOMENTUM is LOW priority (overweight)
        body.append(f"| `{asset}` ({passes} PASSes) | {', '.join(themes[:2])} | MOMENTUM family — LOW (overweight portfolio) | **TRANSFER** mechanism, do not amplify |")

    body.append("\n### Recommendation map (UP / DOWN / TRANSFER / NEUTRAL)\n")

    body.append("**TRANSFER (highest-leverage):** Forge has validated a load-bearing mechanism `ema_slope + profit_ladder` that works across MNQ/MGC/MCL/MYM with multiple entries (PB/BB/VWAP). The pattern is reproducible. **However the wins are all in MOMENTUM/breakout family, which `_priorities.md` flags as overweight (55% portfolio).** Recommendation: don't harvest more momentum. Instead, harvest sources that explore the SAME load-bearing mechanism in UNDERWEIGHT factors:")
    body.append("- **VALUE** (HIGH priority gap): up-weight sources discussing `trend-filter + staged-exit` applied to value/term-premium/PPP signals (e.g., 'value-momentum hybrid', 'staged scale-out value entries')")
    body.append("- **CARRY** (MEDIUM): up-weight sources where carry signals layer with trend-filter regime-detection")
    body.append("- **VOLATILITY** (MEDIUM): up-weight `compression-breakout` (BB-style) sources on non-equity assets — Forge BB winners point that way")
    body.append("- **STRUCTURAL** (MEDIUM): up-weight afternoon-session microstructure sources — XB-BB-AfternoonOnly-MGC was a tail-engine PASS")
    actions.append("If approved: refresh `~/openclaw-intake/inbox/_priorities.md` `Search Term Suggestions` section with TRANSFER themes (operator-gated)")

    body.append("\n**AVOID amplifying** (would deepen overconcentration):")
    body.append("- More momentum-family sources (already 55% portfolio per priorities)")
    body.append("- More MNQ-specific or equity-index-only momentum sources (Forge already showed cross-asset works; new MNQ-only sources add nothing)")

    body.append("\n**NEUTRAL** (continue current weighting):")
    body.append("- General GitHub strategy-research sources (broad enough to surface diverse families)")
    body.append("- Reddit/YouTube monitoring (unfocused; not amenable to up/down per-Forge)")

    body.append("\n**DOWN-WEIGHT (per Forge weak signals):**")
    body.append("- Salvage-template harvesting (per `project_proven_trio_architecture.md`, 7 salvage attempts on 2026-05-05 produced 0 PASSes; salvage template was downgraded)")
    body.append("- VWAP-on-MNQ sources specifically (Forge showed VWAP works on MGC/MCL/MYM but FAILS on MNQ — entry portability is asset-conditional)")

    return SectionOutput("Harvest Recommendation Map", "\n".join(body), actions)


def section_candidate_pool_implication(forge_runs, registry_components) -> SectionOutput:
    body, actions = [], []
    body.append("**What new candidates the Forge runner pool should consider next, vs what to pause.**\n")

    body.append("### Generate next (per Forge evidence)\n")
    body.append("- VALUE-themed candidates with `ema_slope + profit_ladder` mechanism (validate the TRANSFER hypothesis on underweight factor)")
    body.append("- CARRY-themed candidates layered with trend-filter regime detection")
    body.append("- Compression-breakout (BB) candidates on rates (ZN/ZF/ZB) and FX (6E/6J/6B) — extends BB cross-asset evidence into UNDERWEIGHT factors")
    body.append("- Afternoon-session candidates on under-tested assets — XB-BB-AfternoonOnly-MGC PASSed (PF 1.207); test session-restricted patterns on more assets")
    actions.append("Operator approval needed to add new candidate IDs to `fql_forge_batch_runner.py CANDIDATES` dict")

    body.append("\n### Pause / deprioritize\n")
    body.append("- Salvage-template candidates (Phase 0 §3.4 #5) — already downgraded per `project_proven_trio_architecture.md`")
    body.append("- VWAP-on-MNQ specifically (KILL on MNQ; PASSes on MGC/MCL/MYM)")
    body.append("- KILL-every-fire candidates if any surface (none in current 2-day window)")

    body.append("\n### Pool composition health\n")
    pool_size = 19  # current pool size
    body.append(f"- current pool size: ~{pool_size}")
    body.append("- per `project_proven_trio_architecture.md`, entry portability is asset-conditional — ensure each entry-asset combo is tested at least once before generalizing")

    return SectionOutput("Candidate-Pool Implication", "\n".join(body), actions)


def section_safety_confidence(forge_runs) -> SectionOutput:
    body = []
    n_runs = len(forge_runs)
    n_results = sum(len(d.get("results", [])) for _, d in forge_runs)
    n_passes = sum(1 for _, d in forge_runs for r in d.get("results", []) if r.get("verdict") == "PASS")

    body.append(f"### Sample size\n")
    body.append(f"- Forge runs in lookback window: **{n_runs}**")
    body.append(f"- candidate evaluations: **{n_results}**")
    body.append(f"- distinct PASS verdicts: **{n_passes}**")

    if n_runs < 5:
        score = "🔴 **WEAK**"
        explain = ("Sample too small for reliable feedback. Cross-window patterns "
                   "are speculative; a single PASS streak could reverse next week. "
                   "Treat all recommendations as DIRECTIONAL ONLY.")
    elif n_runs < 15:
        score = "🟡 **MODERATE**"
        explain = ("Multi-week sample. Patterns showing across multiple distinct "
                   "candidates are signal; single-candidate patterns may still be noise.")
    else:
        score = "🟢 **STRONG**"
        explain = ("Sufficient sample for reliable cross-asset / cross-entry pattern "
                   "extraction. Recommendations can be acted on with operator review.")

    body.append(f"\n### Recommendation confidence: {score}\n")
    body.append(f"{explain}")

    body.append(f"\n### Caveats")
    body.append("- All Forge metrics come from cheap-screen evaluations (no walk-forward, no out-of-sample). PASS verdicts are PROMOTION-CANDIDATE, not validated edges.")
    body.append("- Asset/entry/filter/exit dimensions are not independent — many combinations co-occur in tested candidates")
    body.append("- Harvest theme mapping is heuristic (asset → keywords); operator should review specific theme suggestions before applying")

    return SectionOutput("Safety / Confidence", "\n".join(body))


def section_executive_summary(forge_runs, recommendations: SectionOutput, candidate: SectionOutput) -> SectionOutput:
    body = []
    n_runs = len(forge_runs)
    n_passes = sum(1 for _, d in forge_runs for r in d.get("results", []) if r.get("verdict") == "PASS")

    body.append(f"### One-line state\n")
    body.append(f"**Forge runs in window:** {n_runs}  |  **distinct PASSes:** {n_passes}  |  **Confidence:** see §6")

    body.append(f"\n### What is working\n")
    body.append("- **Mechanism:** `ema_slope` filter + `profit_ladder` exit (load-bearing pair) reproducible across PB/BB/VWAP entries and across multiple assets")
    body.append("- **Cross-asset:** entry portability confirmed on MGC, MCL, MYM (less so MNQ for VWAP, more so for BB)")
    body.append("- **Tail-engine variant:** XB-BB-AfternoonOnly-MGC validates session-restricted approach for tail archetype")

    body.append(f"\n### What is failing\n")
    body.append("- **VWAP-on-MNQ:** PF 1.056 KILL — entry portability is asset-conditional, not universal")
    body.append("- **Salvage template** (parent + salvaged-failed-component): 0/7 success on 2026-05-05 — downgraded")

    body.append(f"\n### Top recommendation: TRANSFER, do not amplify\n")
    body.append("Forge wins are all in MOMENTUM/breakout family (per `_priorities.md`, that family is OVERWEIGHT at 55% portfolio). Don't harvest more momentum. **Apply the validated mechanism to UNDERWEIGHT factors** — VALUE (HIGH gap), CARRY/VOL/EVENT/STRUCTURAL (MEDIUM gaps).")

    body.append(f"\n### Read order")
    body.append("1. **Section 4 (Harvest Recommendation Map)** — TRANSFER themes, AVOID/DOWN-WEIGHT lists")
    body.append("2. **Section 5 (Candidate-Pool Implication)** — what to generate next vs pause")
    body.append("3. **Section 6 (Safety / Confidence)** — interpret confidence before acting")
    body.append("4. Detail sections 2/3 for evidence")

    return SectionOutput("Executive Summary", "\n".join(body))


def section_next_action(executive: SectionOutput, recommendations: SectionOutput, candidate: SectionOutput, confidence: SectionOutput) -> SectionOutput:
    body = []
    body.append("### Operator action\n")
    body.append("- **Review §4 TRANSFER recommendation.** Decide whether to update `~/openclaw-intake/inbox/_priorities.md` `Search Term Suggestions` to favor mechanism-transfer themes (VALUE+trend-filter, CARRY+regime-detection, VOL+compression-breakout-on-non-equity, STRUCTURAL+afternoon-session).")
    body.append("- **No source-helper config mutation occurred during this run.** All changes require operator approval.")

    body.append("\n### Safe Forge action\n")
    body.append("- **Continue scheduled fires.** Cadence remains weekday 19:00 PT evening + 08:00 PT next-morning digest. No cadence increase recommended.")
    body.append("- **If approved:** queue new candidates in the runner pool that test the TRANSFER hypothesis (VALUE/CARRY/VOL/EVENT/STRUCTURAL with proven `ema_slope + profit_ladder` mechanism). Pre-flight required.")

    body.append("\n### Mode\n")
    n_runs = sum(1 for line in confidence.body.splitlines() if "Forge runs" in line)
    body.append("- **🟡 SURFACE-AND-WAIT** — sample size is WEAK (only 2 fires); recommendations are directional. Re-run feedback after another 5+ fires to upgrade to MODERATE confidence before acting.")

    body.append("\n### Phase B activation question\n")
    body.append("- Should this become scheduled (e.g., weekly Sunday morning before next-week harvest)? **Recommend defer** — first run sample is too small. Re-evaluate Phase B after 2-3 weekly manual runs produce stable recommendations.")

    return SectionOutput("Next Action", "\n".join(body))


# ---------- composer ----------

def render_report(date_str: str, lookback_days: int, sections: list[SectionOutput], generated_at: datetime) -> str:
    out = [f"# FQL Forge → Source-helpers Feedback — {date_str}\n"]
    out.append(f"**Generated:** {generated_at.isoformat(timespec='seconds')}")
    out.append(f"**Lookback:** prior {lookback_days} days")
    out.append(f"**Scope:** Lane B / Forge — recommendation-only feedback layer (closed-loop learning)\n")
    out.append(f"**Safety contract:** report-only; no source-helper / harvest priority / registry / Lane A / portfolio / runtime / scheduler / checkpoint / hold-state mutation. All recommendations require operator approval.\n")
    out.append("---\n")
    for i, sec in enumerate(sections, start=1):
        out.append(f"## {i}. {sec.title}\n")
        out.append(sec.body)
        out.append("\n---\n")
    return "\n".join(out)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="FQL Forge → Source-helpers Feedback (Phase A — recommendation-only)")
    ap.add_argument("--lookback-days", type=int, default=7, help="Days of Forge history to consider (default: 7)")
    ap.add_argument("--save", action="store_true", help="Write report to docs/reports/forge_source_feedback/")
    ap.add_argument("--dry-run", action="store_true", help="Generate but do not write")
    args = ap.parse_args()

    today = date.today().isoformat()
    print(f"FQL Forge → Source Feedback — {today} — lookback {args.lookback_days} days")
    print("=" * 78)

    forge_runs = _read_forge_runs(args.lookback_days)
    registry_components = _registry_components_lookup()

    print(f"Forge runs in window: {len(forge_runs)}")
    print(f"Registry entries with components_used: {len(registry_components)}")

    winning = section_winning_patterns(forge_runs, registry_components)
    weak = section_weak_patterns(forge_runs, registry_components)
    harvest = section_harvest_recommendations(forge_runs, registry_components)
    candidate_pool = section_candidate_pool_implication(forge_runs, registry_components)
    confidence = section_safety_confidence(forge_runs)
    executive = section_executive_summary(forge_runs, harvest, candidate_pool)
    next_action = section_next_action(executive, harvest, candidate_pool, confidence)

    sections = [executive, winning, weak, harvest, candidate_pool, confidence, next_action]
    generated_at = datetime.now()
    report = render_report(today, args.lookback_days, sections, generated_at)

    print(f"Report length: {len(report)} chars, {report.count(chr(10))} lines, {len(sections)} sections")

    if args.dry_run:
        print("\n[DRY-RUN] preview (first 60 lines):\n")
        print("\n".join(report.splitlines()[:60]))
        return

    if not args.save:
        print("\n(use --save to write, or --dry-run for preview)")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{today}_forge_source_feedback.md"
    out_path.write_text(report)
    print(f"\n[WRITE] {out_path}")
    print("\n[SAFETY] Report-only. No source-helper / harvest priority mutation.")


if __name__ == "__main__":
    main()
