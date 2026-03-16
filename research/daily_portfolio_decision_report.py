#!/usr/bin/env python3
"""FQL Daily Portfolio Decision Report — Human + machine-readable output.

Consumes the Portfolio Regime Controller output and generates both
JSON and Markdown reports with 9 required sections.

Sections:
    1. Portfolio health summary
    2. Promotions / demotions (state changes)
    3. Activation matrix
    4. Probation list
    5. Archive candidates
    6. Resurrection candidates
    7. Redundancy / crowding warnings
    8. Gap summary
    9. Research targeting suggestions

Usage:
    python3 research/daily_portfolio_decision_report.py              # Full report
    python3 research/daily_portfolio_decision_report.py --json       # JSON only
    python3 research/daily_portfolio_decision_report.py --save       # Save both formats
    python3 research/daily_portfolio_decision_report.py --fast       # Skip heavy backtests
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.portfolio_regime_controller import run_controller, EVAL_STRATEGIES
from research.strategy_genome_map import STRATEGIES as GENOME_STRATEGIES, EXPOSURE_TYPES
from research.reason_codes import ReasonCode, REASON_DESCRIPTIONS

REPORTS_DIR = ROOT / "research" / "reports"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"


# ── Report Data Builder ──────────────────────────────────────────────────────

def build_report_data(controller_results: dict) -> dict:
    """Build structured report from controller output."""
    matrix = controller_results["activation_matrix"]
    transitions = controller_results["state_transitions"]
    summary = controller_results["portfolio_summary"]
    regime = controller_results["regime_snapshot"]

    report = {
        "report_date": controller_results["report_date"],
        "sections": {},
    }

    # ── 1. Portfolio Health Summary ──
    active_strategies = [e for e in matrix if e["recommended_action"] in ("FULL_ON", "REDUCED_ON")]
    decay_candidates = [e for e in matrix if ReasonCode.HALF_LIFE_DECAY in e.get("reason_codes", [])
                        or ReasonCode.HALF_LIFE_DEAD in e.get("reason_codes", [])]
    archive_candidates = [e for e in matrix if e["recommended_action"] == "ARCHIVE_REVIEW"]

    report["sections"]["health_summary"] = {
        "headline_metrics": {
            "total_strategies_evaluated": summary["total_strategies"],
            "active_count": summary["active"],
            "probation_count": summary["probation"],
            "disabled_count": summary["disabled_or_off"],
            "avg_activation_score": summary["avg_activation_score"],
            "health_status": summary["health_status"],
        },
        "warnings": [w for e in matrix for w in e.get("warnings", [])],
        "flagged_decay": [e["strategy_id"] for e in decay_candidates],
        "flagged_archive": [e["strategy_id"] for e in archive_candidates],
    }

    # ── 2. Promotions / Demotions ──
    promotions = []
    demotions = []
    for t in transitions:
        state_rank = {
            "ARCHIVED": 0, "DISABLED": 1, "PROBATION": 2,
            "ACTIVE_REDUCED": 3, "ACTIVE": 4, "PAPER": 2.5,
            "VALIDATED": 1.5, "RESURRECTION_CANDIDATE": 0.5,
        }
        from_rank = state_rank.get(t["from_state"], 0)
        to_rank = state_rank.get(t["to_state"], 0)
        entry = {
            "strategy_id": t["strategy_id"],
            "from_state": t["from_state"],
            "to_state": t["to_state"],
            "trigger": t["trigger"],
            "reason_codes": t["reason_codes"],
        }
        if to_rank > from_rank:
            promotions.append(entry)
        else:
            demotions.append(entry)

    report["sections"]["state_changes"] = {
        "promotions": promotions,
        "demotions": demotions,
        "total_changes": len(transitions),
    }

    # ── 3. Activation Matrix ──
    report["sections"]["activation_matrix"] = [
        {
            "strategy_id": e["strategy_id"],
            "asset": e["asset"],
            "family": e["family"],
            "exposure": e["primary_exposure"],
            "activation_score": e["activation_score"],
            "recommended_action": e["recommended_action"],
            "state": e["new_state"],
            "situation": e.get("situation", "HEALTHY"),
            "confidence": e["confidence"],
            "uncertainty": e.get("uncertainty", False),
            "review_priority": e["review_priority"],
        }
        for e in sorted(matrix, key=lambda x: x["activation_score"], reverse=True)
    ]

    # ── 4. Probation List ──
    probation = []
    for e in matrix:
        if e["new_state"] == "PROBATION" or e["recommended_action"] == "PROBATION":
            reasons = []
            if ReasonCode.HALF_LIFE_DECAY in e.get("reason_codes", []):
                reasons.append("Edge decaying")
            if ReasonCode.PORTFOLIO_DILUTION in e.get("reason_codes", []):
                reasons.append("Portfolio dilution")
            if ReasonCode.KILL_TRIGGER_SOFT in e.get("reason_codes", []):
                reasons.append("Kill flag triggered")
            if ReasonCode.REGIME_MISMATCH in e.get("reason_codes", []):
                reasons.append("Regime mismatch")
            if ReasonCode.REDUNDANT_CLUSTER in e.get("reason_codes", []):
                reasons.append("Redundant with active strategy")
            if not reasons:
                reasons.append("Activation score below threshold")
            probation.append({
                "strategy_id": e["strategy_id"],
                "activation_score": e["activation_score"],
                "reasons": reasons,
            })

    report["sections"]["probation_list"] = probation

    # ── 5. Archive Candidates ──
    archive = []
    for e in matrix:
        if e["recommended_action"] in ("ARCHIVE_REVIEW", "DISABLE"):
            reasons = []
            if ReasonCode.HALF_LIFE_DEAD in e.get("reason_codes", []):
                reasons.append("Edge dead")
            if ReasonCode.KILL_TRIGGER_HARD in e.get("reason_codes", []):
                reasons.append("Hard kill triggered")
            if ReasonCode.PORTFOLIO_DILUTION in e.get("reason_codes", []):
                reasons.append("Persistently dilutive")
            if ReasonCode.RECENT_COLLAPSE in e.get("reason_codes", []):
                reasons.append("Recent performance collapse")
            if not reasons:
                reasons.append("Below minimum activation threshold")
            archive.append({
                "strategy_id": e["strategy_id"],
                "activation_score": e["activation_score"],
                "reasons": reasons,
            })

    report["sections"]["archive_candidates"] = archive

    # ── 6. Resurrection Candidates ──
    resurrection = []
    for e in matrix:
        if e["new_state"] == "RESURRECTION_CANDIDATE":
            resurrection.append({
                "strategy_id": e["strategy_id"],
                "activation_score": e["activation_score"],
                "trigger": e["transition_trigger"],
            })

    # Also check registry for archived strategies with potential
    try:
        with open(REGISTRY_PATH) as f:
            registry = json.load(f)
        for s in registry.get("strategies", []):
            if s.get("status") in ("rejected", "retired"):
                sid = s.get("strategy_id", "")
                # Check if any archived strategy could be worth reviewing
                if s.get("validation_score") and s["validation_score"] >= 6.0:
                    resurrection.append({
                        "strategy_id": sid,
                        "activation_score": None,
                        "trigger": f"Previously validated (score={s['validation_score']}), now archived — worth periodic check",
                    })
    except Exception:
        pass

    report["sections"]["resurrection_candidates"] = resurrection

    # ── 7. Redundancy / Crowding Warnings ──
    redundancy_warnings = []

    # Exposure cluster concentration
    exposure_counts = {}
    for e in matrix:
        if e["recommended_action"] in ("FULL_ON", "REDUCED_ON"):
            exp = e.get("primary_exposure", "unknown")
            exposure_counts.setdefault(exp, []).append(e["strategy_id"])

    for exp, strats in exposure_counts.items():
        if len(strats) >= 3:
            redundancy_warnings.append({
                "type": "exposure_concentration",
                "exposure": exp,
                "strategies": strats,
                "message": f"{exp}: {len(strats)} active strategies share this edge — crowding risk",
            })

    # Family concentration
    family_counts = {}
    for e in matrix:
        if e["recommended_action"] in ("FULL_ON", "REDUCED_ON"):
            fam = e.get("family", "unknown")
            family_counts.setdefault(fam, []).append(e["strategy_id"])

    for fam, strats in family_counts.items():
        if len(strats) >= 3:
            redundancy_warnings.append({
                "type": "family_concentration",
                "family": fam,
                "strategies": strats,
                "message": f"{fam}: {len(strats)} active strategies — family overstacked",
            })

    # Time-of-day concentration
    session_counts = {}
    for g in GENOME_STRATEGIES:
        sid = g["id"]
        entry = next((e for e in matrix if e["strategy_id"] == sid), None)
        if entry and entry["recommended_action"] in ("FULL_ON", "REDUCED_ON"):
            sess = g.get("session", "all_day")
            session_counts.setdefault(sess, []).append(sid)

    for sess, strats in session_counts.items():
        if len(strats) >= 4 and sess != "all_day":
            redundancy_warnings.append({
                "type": "session_concentration",
                "session": sess,
                "strategies": strats,
                "message": f"{sess}: {len(strats)} strategies concentrated in same session window",
            })

    # High correlation pairs
    for e in matrix:
        codes = e.get("reason_codes", [])
        if ReasonCode.REDUNDANT_CLUSTER in codes:
            redundancy_warnings.append({
                "type": "high_correlation",
                "strategy": e["strategy_id"],
                "message": f"{e['strategy_id']}: flagged as redundant with another active strategy",
            })

    report["sections"]["redundancy_warnings"] = redundancy_warnings

    # ── 8. Gap Summary ──
    # Uncovered regime cells
    covered_exposures = set()
    covered_assets = set()
    covered_sessions = set()
    covered_families = set()
    for e in matrix:
        if e["recommended_action"] in ("FULL_ON", "REDUCED_ON"):
            covered_exposures.add(e.get("primary_exposure", "unknown"))
            covered_assets.add(e.get("asset", "unknown"))
        g = next((gs for gs in GENOME_STRATEGIES if gs["id"] == e["strategy_id"]), None)
        if g and e["recommended_action"] in ("FULL_ON", "REDUCED_ON"):
            covered_sessions.add(g.get("session", "unknown"))
            covered_families.add(g.get("family", "unknown"))

    all_exposures = set(EXPOSURE_TYPES.keys())
    all_assets = {"MES", "MNQ", "MGC", "M2K", "MCL"}
    all_sessions = {"morning", "midday", "afternoon", "close"}
    all_families = {"trend", "pullback", "breakout", "mean_reversion", "vol_expansion", "event_driven"}

    report["sections"]["gap_summary"] = {
        "uncovered_exposures": sorted(all_exposures - covered_exposures),
        "uncovered_assets": sorted(all_assets - covered_assets),
        "uncovered_sessions": sorted(all_sessions - covered_sessions),
        "uncovered_families": sorted(all_families - covered_families),
        "regime_gaps": _identify_regime_gaps(matrix),
    }

    # ── 9. Research Targeting Suggestions ──
    suggestions = []

    missing_exp = all_exposures - covered_exposures
    if "liquidity_sweep" in missing_exp:
        suggestions.append({
            "priority": "HIGH",
            "target": "Liquidity sweep / stop hunt strategies",
            "reason": "No coverage of this edge type — potential uncorrelated returns",
        })
    if "inventory_reversion" in missing_exp:
        suggestions.append({
            "priority": "HIGH",
            "target": "Event-driven / inventory strategies (EIA, FOMC)",
            "reason": "No event-driven exposure — missing structural edge category",
        })

    uncovered_assets = all_assets - covered_assets
    for asset in sorted(uncovered_assets):
        suggestions.append({
            "priority": "MEDIUM",
            "target": f"{asset}-long or {asset}-short strategies",
            "reason": f"No active strategies on {asset} — asset gap",
        })

    if probation:
        suggestions.append({
            "priority": "MEDIUM",
            "target": "Probation strategy replacements",
            "reason": f"{len(probation)} strategies on probation — search for stronger alternatives",
        })

    if not suggestions:
        suggestions.append({
            "priority": "LOW",
            "target": "Portfolio is well-covered",
            "reason": "No critical gaps — focus on monitoring existing strategies",
        })

    report["sections"]["research_suggestions"] = suggestions

    return report


def _identify_regime_gaps(matrix: list) -> list:
    """Identify regime cells with no active strategy coverage."""
    from research.strategy_genome_map import ALL_REGIME_CELLS, _strategies_in_regime_cell

    gaps = []
    for cell in ALL_REGIME_CELLS:
        active_in_cell = _strategies_in_regime_cell(cell)
        # Filter to only strategies that are recommended active
        active_ids = {e["strategy_id"] for e in matrix
                      if e["recommended_action"] in ("FULL_ON", "REDUCED_ON")}
        covered = [s for s in active_in_cell if s in active_ids]
        if not covered:
            gaps.append(cell)

    return gaps


# ── Markdown Report ──────────────────────────────────────────────────────────

def generate_markdown(report: dict) -> str:
    """Generate markdown report from structured data."""
    lines = []
    sections = report["sections"]

    lines.append(f"# FQL Daily Portfolio Decision Report")
    lines.append(f"**Date:** {report['report_date']}")
    lines.append("")

    # 1. Health Summary
    hs = sections["health_summary"]
    metrics = hs["headline_metrics"]
    lines.append("## 1. Portfolio Health Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Strategies Evaluated | {metrics['total_strategies_evaluated']} |")
    lines.append(f"| Active (FULL+REDUCED) | {metrics['active_count']} |")
    lines.append(f"| Probation | {metrics['probation_count']} |")
    lines.append(f"| Disabled/Off | {metrics['disabled_count']} |")
    lines.append(f"| Avg Activation Score | {metrics['avg_activation_score']:.3f} |")
    lines.append(f"| Health Status | {metrics['health_status']} |")
    lines.append("")

    if hs["flagged_decay"]:
        lines.append(f"**Decaying edges:** {', '.join(hs['flagged_decay'])}")
    if hs["flagged_archive"]:
        lines.append(f"**Archive candidates:** {', '.join(hs['flagged_archive'])}")
    if hs["warnings"]:
        lines.append("")
        lines.append("**Warnings:**")
        for w in hs["warnings"][:10]:
            lines.append(f"- {w}")
    lines.append("")

    # 2. State Changes
    sc = sections["state_changes"]
    lines.append("## 2. Promotions / Demotions")
    lines.append("")
    if sc["total_changes"] == 0:
        lines.append("No state changes since last report.")
    else:
        if sc["promotions"]:
            lines.append("**Promotions:**")
            for p in sc["promotions"]:
                lines.append(f"- {p['strategy_id']}: {p['from_state']} -> {p['to_state']} ({p['trigger']})")
        if sc["demotions"]:
            lines.append("**Demotions:**")
            for d in sc["demotions"]:
                lines.append(f"- {d['strategy_id']}: {d['from_state']} -> {d['to_state']} ({d['trigger']})")
    lines.append("")

    # 3. Activation Matrix
    lines.append("## 3. Activation Matrix")
    lines.append("")
    lines.append("| Strategy | Asset | Score | Action | State | Situation | Priority |")
    lines.append("|---|---|---|---|---|---|---|")
    for e in sections["activation_matrix"]:
        uncertain = " *" if e.get("uncertainty") else ""
        lines.append(
            f"| {e['strategy_id']} | {e['asset']} | {e['activation_score']:.3f}{uncertain} "
            f"| {e['recommended_action']} | {e['state']} | {e.get('situation', 'HEALTHY')} | {e['review_priority']} |"
        )
    lines.append("")

    # 4. Probation List
    lines.append("## 4. Probation List")
    lines.append("")
    if not sections["probation_list"]:
        lines.append("No strategies on probation.")
    else:
        for p in sections["probation_list"]:
            lines.append(f"- **{p['strategy_id']}** (score: {p['activation_score']:.3f})")
            for r in p["reasons"]:
                lines.append(f"  - {r}")
    lines.append("")

    # 5. Archive Candidates
    lines.append("## 5. Archive Candidates")
    lines.append("")
    if not sections["archive_candidates"]:
        lines.append("No strategies flagged for archival.")
    else:
        for a in sections["archive_candidates"]:
            lines.append(f"- **{a['strategy_id']}** (score: {a['activation_score']:.3f})")
            for r in a["reasons"]:
                lines.append(f"  - {r}")
    lines.append("")

    # 6. Resurrection Candidates
    lines.append("## 6. Resurrection Candidates")
    lines.append("")
    if not sections["resurrection_candidates"]:
        lines.append("No archived strategies showing revival signals.")
    else:
        for r in sections["resurrection_candidates"]:
            score_str = f"{r['activation_score']:.3f}" if r['activation_score'] else "N/A"
            lines.append(f"- **{r['strategy_id']}** (score: {score_str})")
            lines.append(f"  - {r['trigger']}")
    lines.append("")

    # 7. Redundancy Warnings
    lines.append("## 7. Redundancy / Crowding Warnings")
    lines.append("")
    if not sections["redundancy_warnings"]:
        lines.append("No redundancy concerns.")
    else:
        for w in sections["redundancy_warnings"]:
            lines.append(f"- **{w['type']}:** {w['message']}")
    lines.append("")

    # 8. Gap Summary
    lines.append("## 8. Gap Summary")
    lines.append("")
    gaps = sections["gap_summary"]
    if gaps["uncovered_exposures"]:
        lines.append(f"**Missing exposure types:** {', '.join(gaps['uncovered_exposures'])}")
    if gaps["uncovered_assets"]:
        lines.append(f"**Uncovered assets:** {', '.join(gaps['uncovered_assets'])}")
    if gaps["uncovered_sessions"]:
        lines.append(f"**Uncovered sessions:** {', '.join(gaps['uncovered_sessions'])}")
    if gaps["uncovered_families"]:
        lines.append(f"**Missing families:** {', '.join(gaps['uncovered_families'])}")
    if gaps["regime_gaps"]:
        lines.append(f"**Uncovered regime cells:** {len(gaps['regime_gaps'])}")
        for cell in gaps["regime_gaps"][:5]:
            lines.append(f"  - {cell}")
        if len(gaps["regime_gaps"]) > 5:
            lines.append(f"  - ... and {len(gaps['regime_gaps']) - 5} more")
    lines.append("")

    # 9. Research Suggestions
    lines.append("## 9. Research Targeting Suggestions")
    lines.append("")
    for s in sections["research_suggestions"]:
        lines.append(f"- **[{s['priority']}]** {s['target']}")
        lines.append(f"  - {s['reason']}")
    lines.append("")

    lines.append("---")
    lines.append(f"*Generated by FQL Portfolio Regime Controller — {report['report_date']}*")

    return "\n".join(lines)


# ── Terminal Report ──────────────────────────────────────────────────────────

def print_terminal_report(report: dict):
    """Print formatted terminal report."""
    sections = report["sections"]
    W = 75
    SEP = "=" * W

    print()
    print(SEP)
    print("  FQL DAILY PORTFOLIO DECISION REPORT")
    print(f"  {report['report_date']}")
    print(SEP)

    # 1. Health Summary
    hs = sections["health_summary"]
    m = hs["headline_metrics"]
    print()
    print("  1. PORTFOLIO HEALTH SUMMARY")
    print(f"  {'-' * 55}")
    print(f"  Active: {m['active_count']}  |  Probation: {m['probation_count']}  |  "
          f"Disabled: {m['disabled_count']}  |  Health: {m['health_status']}")
    print(f"  Avg score: {m['avg_activation_score']:.3f}")
    if hs["flagged_decay"]:
        print(f"  Decaying: {', '.join(hs['flagged_decay'])}")
    if hs["flagged_archive"]:
        print(f"  Archive:  {', '.join(hs['flagged_archive'])}")

    # 2. State Changes
    sc = sections["state_changes"]
    if sc["total_changes"] > 0:
        print()
        print("  2. STATE CHANGES")
        print(f"  {'-' * 55}")
        for p in sc["promotions"]:
            print(f"  [UP]   {p['strategy_id']}: {p['from_state']} -> {p['to_state']}")
        for d in sc["demotions"]:
            print(f"  [DOWN] {d['strategy_id']}: {d['from_state']} -> {d['to_state']}")

    # 3. Activation Matrix
    print()
    print("  3. ACTIVATION MATRIX")
    print(f"  {'-' * 55}")
    print(f"  {'Strategy':<28s} {'Score':>6s} {'Action':<14s} {'Situation':<16s}")
    print(f"  {'-' * 66}")
    for e in sections["activation_matrix"]:
        sid = e["strategy_id"]
        if len(sid) > 27:
            sid = sid[:24] + "..."
        uncertain = "*" if e.get("uncertainty") else " "
        situation = e.get("situation", "HEALTHY")
        print(f"  {sid:<28s} {e['activation_score']:.3f}{uncertain} {e['recommended_action']:<14s} {situation:<16s}")

    # 4-5. Probation + Archive (compact)
    if sections["probation_list"] or sections["archive_candidates"]:
        print()
        print("  4-5. PROBATION & ARCHIVE")
        print(f"  {'-' * 55}")
        for p in sections["probation_list"]:
            print(f"  [PROBATION] {p['strategy_id']} — {', '.join(p['reasons'])}")
        for a in sections["archive_candidates"]:
            print(f"  [ARCHIVE]   {a['strategy_id']} — {', '.join(a['reasons'])}")

    # 7. Redundancy
    if sections["redundancy_warnings"]:
        print()
        print("  7. REDUNDANCY WARNINGS")
        print(f"  {'-' * 55}")
        for w in sections["redundancy_warnings"]:
            print(f"  ! {w['message']}")

    # 8. Gaps
    gaps = sections["gap_summary"]
    print()
    print("  8. GAP SUMMARY")
    print(f"  {'-' * 55}")
    if gaps["uncovered_exposures"]:
        print(f"  Missing exposures: {', '.join(gaps['uncovered_exposures'])}")
    if gaps["uncovered_assets"]:
        print(f"  Missing assets:    {', '.join(gaps['uncovered_assets'])}")
    if gaps["uncovered_families"]:
        print(f"  Missing families:  {', '.join(gaps['uncovered_families'])}")
    if gaps["regime_gaps"]:
        print(f"  Uncovered regimes: {len(gaps['regime_gaps'])} cells")

    # 9. Research Suggestions
    print()
    print("  9. RESEARCH TARGETING")
    print(f"  {'-' * 55}")
    for s in sections["research_suggestions"]:
        print(f"  [{s['priority']:>6s}] {s['target']}")

    print()
    print(SEP)


# ── Main ─────────────────────────────────────────────────────────────────────

ACTIVATION_MATRIX_PATH = ROOT / "research" / "data" / "portfolio_activation_matrix.json"


def load_cached_controller_results() -> dict | None:
    """Load cached activation matrix if it exists and is from today."""
    if not ACTIVATION_MATRIX_PATH.exists():
        return None
    try:
        with open(ACTIVATION_MATRIX_PATH) as f:
            data = json.load(f)
        # Check if from today
        report_date = data.get("report_date", "")
        today = datetime.now().strftime("%Y-%m-%d")
        if report_date.startswith(today):
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def main():
    parser = argparse.ArgumentParser(
        description="FQL Daily Portfolio Decision Report"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output JSON only")
    parser.add_argument("--save", action="store_true",
                        help="Save JSON + Markdown reports")
    parser.add_argument("--fast", action="store_true",
                        help="Skip heavy backtests")
    parser.add_argument("--from-cache", action="store_true",
                        help="Use cached activation matrix (skip controller re-run)")
    args = parser.parse_args()

    # Try cached results first (avoids re-running 20+ min of backtests)
    controller_results = None
    if args.from_cache:
        controller_results = load_cached_controller_results()
        if controller_results:
            print("Using cached activation matrix from today.")
        else:
            print("No cached results from today — running controller.")

    if controller_results is None:
        controller_results = run_controller(skip_heavy=args.fast)

    # Build report
    report = build_report_data(controller_results)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_terminal_report(report)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        # Save JSON
        json_path = REPORTS_DIR / f"daily_decision_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"JSON saved: {json_path}")

        # Save Markdown
        md = generate_markdown(report)
        md_path = REPORTS_DIR / f"daily_decision_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write(md)
        print(f"Markdown saved: {md_path}")

        # Save controller raw data
        raw_path = REPORTS_DIR / f"controller_raw_{timestamp}.json"
        with open(raw_path, "w") as f:
            json.dump(controller_results, f, indent=2, default=str)
        print(f"Raw data saved: {raw_path}")


if __name__ == "__main__":
    main()
