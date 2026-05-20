#!/usr/bin/env python3
"""Validation Funnel v0 — Item #7 of Paper-Readiness Sprint.

Composes existing gates into a decision-grade scorecard for the 12
cost-aware-viable candidates feeding Item #8 top-3 selection and Item #9
paper-readiness packets (deliverable 2026-06-17).

Sessions:
  1 (today):    Gates 1+2+3 — cheap-screen PASS, correlation cleared, net PF ≥ 1.15
  2 (planned):  Gate 4      — walk-forward H1/H2 > 1.0
  3 (planned):  Gates 5+6+7 — trade count, concentration, forward-runner trades
  4 (planned):  Gate 8      — promotion humility doc check; final rendering

Hard rules per docs/_DRAFT_2026-05-20_validation_funnel_v0_preflight.md:
  - Cost-aware backtests only (allow_uncosted=True is forbidden in this funnel)
  - No registry mutation; output is read-only intelligence
  - If a gate invalidates a candidate, record the failure — do not rescue
  - Source of truth for cost: engine/asset_config.py (post-Piece-I)

Per FQL evidence law (CLAUDE.md): every report shows cost assumptions.
"""

import argparse
import json
from pathlib import Path
from datetime import date

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ── Funnel input ──────────────────────────────────────────────────────────────
# 12 candidates from the post-cost candidate landscape (3 probation + 9 viable).
# The 3 archived/monitor MCL candidates are explicitly excluded per operator
# decisions of 2026-05-20.

PROBATION_REREAD_PATH = ROOT / "docs/reports/cost_integrity_reset/2026-05-20_cost_integrity_reread_probation.json"
CORRELATION_REREAD_PATH = ROOT / "docs/reports/cost_integrity_reset/2026-05-20_cost_integrity_reread_correlation.json"

EXCLUDED_BY_OPERATOR_DECISION = {
    "XB-BB-EMA-Ladder-MCL",      # archived 2026-05-20 (RED, net PF 0.983)
    "XB-VWAP-EMA-Ladder-MCL",    # archived 2026-05-20 (RED, net PF 1.040)
    "XB-PB-EMA-Ladder-MCL",      # monitor 2026-05-20 (YELLOW, net PF 1.058)
}

# Exposure cluster mapping (from 2026-05-19 cluster decision).
# Retained variants don't earn a Gate 2 point — the cluster_leader represents
# the exposure. Top-3 selection treats the cluster as one slot.
CLUSTER_RETAINED_VARIANTS = {
    "XB-ORB-EMA-TimeStop-MNQ": "XB-ORB-EMA-Chandelier-MNQ",  # retained variant → leader
}


def _load_funnel_inputs():
    """Load the 12 candidates from cost integrity re-read JSONs, tagged by bucket."""
    with open(PROBATION_REREAD_PATH) as f:
        probation = json.load(f)
    with open(CORRELATION_REREAD_PATH) as f:
        correlation = json.load(f)

    rows = []
    for r in probation:
        r = dict(r)
        r["bucket"] = "probation"
        rows.append(r)
    for r in correlation:
        if r["strategy_id"] in EXCLUDED_BY_OPERATOR_DECISION:
            continue
        r = dict(r)
        r["bucket"] = "correlation"
        rows.append(r)
    return rows


# ── Gates (Session 1) ────────────────────────────────────────────────────────


def gate_1_cheap_screen_pass(candidate: dict) -> tuple:
    """G1 (weight 1): candidate must have passed a documented cheap-screen.

    For probation: passing the original promotion gate implies cheap-screen
    was cleared at intake. For correlation candidates: presence in
    correlation_matrix.py inputs implies registered-from-cheap-screen.
    Any candidate that wouldn't qualify is excluded upstream from funnel input.
    """
    bucket = candidate["bucket"]
    if bucket == "probation":
        return 1, "promoted (cheap-screen long since cleared)"
    if bucket == "correlation":
        return 1, "registered as cheap-screen PASS in correlation matrix set"
    return 0, "unknown bucket"


def gate_2_correlation_cleared(candidate: dict) -> tuple:
    """G2 (weight 1): candidate must not be a retained_variant duplicate.

    Per cluster decision 2026-05-19: the cluster_leader represents the
    exposure; retained_variants do not. Probation candidates were not in
    the correlation matrix, so they default-pass — but the 3 XB-ORB-Ladder
    probation candidates are each unique exposures.
    """
    sid = candidate["strategy_id"]
    if sid in CLUSTER_RETAINED_VARIANTS:
        leader = CLUSTER_RETAINED_VARIANTS[sid]
        return 0, f"retained variant of {leader} cluster — duplicate exposure"
    return 1, "distinct exposure cluster"


def gate_3_cost_adjusted_pf(candidate: dict) -> tuple:
    """G3 (weight 2): net PF must be ≥ 1.15."""
    net_pf = candidate.get("new_pf")
    if net_pf is None:
        return 0, "no net PF available"
    if net_pf >= 1.15:
        return 2, f"net PF {net_pf:.3f} ≥ 1.15"
    return 0, f"net PF {net_pf:.3f} < 1.15"


# ── Gate registry ────────────────────────────────────────────────────────────

SESSION_1_GATES = [
    ("G1_cheap_screen_pass", 1, gate_1_cheap_screen_pass),
    ("G2_correlation_cleared", 1, gate_2_correlation_cleared),
    ("G3_cost_adjusted_pf", 2, gate_3_cost_adjusted_pf),
]

# Placeholder columns for Sessions 2-4 (will fill incrementally).
SESSION_2_PLUS_GATES = [
    ("G4_walkforward_h1h2", 3, None),
    ("G5_trade_count", 1, None),
    ("G6_concentration", 2, None),
    ("G7_forward_runner_trades", 2, None),
    ("G8_promotion_humility_doc", 1, None),
]

MAX_TOTAL = sum(w for _, w, _ in SESSION_1_GATES + SESSION_2_PLUS_GATES)  # 13


def score_candidate(candidate: dict, gates) -> dict:
    """Apply all gates to a candidate; return score dict."""
    scores = {}
    explanations = {}
    total = 0
    for name, weight, fn in gates:
        if fn is None:
            scores[name] = None
            explanations[name] = "deferred to later session"
            continue
        points, why = fn(candidate)
        scores[name] = points
        explanations[name] = why
        total += points
    return {
        **candidate,
        "scores": scores,
        "explanations": explanations,
        "session_1_score": total,
        "session_1_max": sum(w for _, w, fn in SESSION_1_GATES if fn is not None),
    }


# ── Reporting ────────────────────────────────────────────────────────────────


def render_cost_block(scored):
    """Per-asset cost assumptions used (mandatory header per FQL evidence law)."""
    assumptions = {}
    for c in scored:
        a = c["asset"]
        if a not in assumptions:
            assumptions[a] = c.get("new_cost_assumption", "?")
    lines = ["| Asset | Cost assumption |", "|---|---|"]
    for a in sorted(assumptions):
        lines.append(f"| {a} | {assumptions[a]} |")
    return "\n".join(lines)


def render_scorecard(scored):
    """Per-candidate scorecard with gate-by-gate breakdown."""
    lines = [
        "| Candidate | Asset | Bucket | G1 | G2 | G3 | S1 score | Net PF | Notes |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for c in sorted(scored, key=lambda x: (-x["session_1_score"], -x.get("new_pf", 0))):
        sid = c["strategy_id"]
        g1 = c["scores"]["G1_cheap_screen_pass"]
        g2 = c["scores"]["G2_correlation_cleared"]
        g3 = c["scores"]["G3_cost_adjusted_pf"]
        note_parts = []
        if g2 == 0:
            note_parts.append(c["explanations"]["G2_correlation_cleared"])
        if g3 == 0:
            note_parts.append(c["explanations"]["G3_cost_adjusted_pf"])
        notes = "; ".join(note_parts) if note_parts else ""
        lines.append(
            f"| {sid} | {c['asset']} | {c['bucket']} | {g1} | {g2} | {g3} | "
            f"{c['session_1_score']}/{c['session_1_max']} | "
            f"{c.get('new_pf', '?'):.3f} | {notes} |"
        )
    return "\n".join(lines)


def render_session1_summary(scored):
    """Roll-up: candidates eligible to advance, blocked, exposure cluster count."""
    advancing = [c for c in scored if c["session_1_score"] == c["session_1_max"]]
    partial = [c for c in scored if 0 < c["session_1_score"] < c["session_1_max"]]
    blocked = [c for c in scored if c["session_1_score"] == 0]

    # Cluster count: each retained_variant counts as 0; each leader/distinct counts as 1
    cluster_slots = sum(
        1 for c in advancing
        if c["strategy_id"] not in CLUSTER_RETAINED_VARIANTS
    )

    summary = []
    summary.append(f"- **{len(advancing)}/{len(scored)} candidates score full marks** ({sum(w for _, w, _ in SESSION_1_GATES)}/4) and advance to Session 2 gates.")
    summary.append(f"- **{len(partial)} candidate(s) partial** (failed at least one Session 1 gate but not all).")
    summary.append(f"- **{len(blocked)} candidate(s) blocked** (failed all Session 1 gates).")
    summary.append(f"- **Exposure cluster count after Session 1: {cluster_slots}** (retained variants do not count as separate slots).")
    return "\n".join(summary)


def render_report(scored):
    out = []
    today = date.today().isoformat()
    out.append(f"# Validation Funnel v0 — Session 1 ({today})")
    out.append("")
    out.append("**Filed by:** `research/validation_funnel.py`")
    out.append("**Authority:** T1 intelligence; no registry mutation, no status changes.")
    out.append("**Sprint:** Phase 2 / Paper-Readiness Sprint Item #7.")
    out.append("")
    out.append("## Session 1 scope — Gates 1+2+3")
    out.append("")
    out.append("- **Gate 1 (1 pt):** cheap-screen PASS documented at intake")
    out.append("- **Gate 2 (1 pt):** correlation cleared — not a retained-variant duplicate")
    out.append("- **Gate 3 (2 pt):** cost-adjusted net PF ≥ 1.15")
    out.append("")
    out.append("Sessions 2-4 will add 9 more points across walk-forward, trade count,")
    out.append("concentration, forward-runner, and promotion-humility gates (13 pt max total).")
    out.append("")
    out.append("## Cost assumptions used")
    out.append("")
    out.append("Per FQL evidence law: net PFs below come from the post-Piece-I cost-aware")
    out.append("engine. `engine/asset_config.py` is the single source of truth. Conservative")
    out.append("estimates; replace with broker rate sheets before paper/prop.")
    out.append("")
    out.append(render_cost_block(scored))
    out.append("")
    out.append("## Per-candidate scorecard")
    out.append("")
    out.append(render_scorecard(scored))
    out.append("")
    out.append("## Session 1 summary")
    out.append("")
    out.append(render_session1_summary(scored))
    out.append("")
    out.append("## Top risks before Session 2 (Gate 4: walk-forward H1/H2)")
    out.append("")
    out.append("- Walk-forward is the heaviest gate (3 pts) and most likely to cull candidates.")
    out.append("- MCL probation (net PF 1.298) is the closest to the 1.15 gate; small WF instability could compound the fragility flag.")
    out.append("- The 9 correlation candidates have not been walk-forward tested under the cost-aware engine. WF was originally computed pre-Piece-I (mostly zero-cost via correlation_matrix.py path); a fresh run is required.")
    out.append("- Walk-forward + cost-aware backtests = ~12 candidates × ≥4 WF runs each = significant compute. Session 2 may need to chunk or background.")
    out.append("")
    out.append("## Cluster / top-3 selection note")
    out.append("")
    for retained, leader in CLUSTER_RETAINED_VARIANTS.items():
        out.append(f"- **{retained}** is the retained variant of the **{leader}** cluster. Both remain registered but count as one exposure slot for top-3 selection.")
    out.append("")
    out.append("---")
    out.append("")
    out.append("*Session 1 of 4. Read-only intelligence; no decisions taken. Next session: Gate 4 walk-forward on the candidates that score full marks here.*")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true",
                    help="Write report + JSON to docs/reports/validation_funnel/")
    args = ap.parse_args()

    rows = _load_funnel_inputs()
    scored = [score_candidate(r, SESSION_1_GATES) for r in rows]

    report = render_report(scored)
    print(report)

    if args.save:
        out_dir = ROOT / "docs/reports/validation_funnel"
        out_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        md_path = out_dir / f"{today}_validation_funnel_session1.md"
        json_path = out_dir / f"{today}_validation_funnel_session1.json"
        md_path.write_text(report + "\n")
        json_path.write_text(json.dumps(scored, indent=2, default=str))
        print(f"\nSaved:\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()
