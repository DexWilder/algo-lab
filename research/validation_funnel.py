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
import sys
from pathlib import Path
from datetime import date

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals
from research.cost_integrity_reread import (
    PROBATION_CANDIDATES, CORRELATION_CANDIDATES,
)

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


# Chunk control for Session 2 compute (operator-locked 2026-05-20).
CHUNK_PROBATION = {"XB-ORB-EMA-Ladder-MNQ", "XB-ORB-EMA-Ladder-MCL", "XB-ORB-EMA-Ladder-MYM"}
CHUNK_CORR_TOP = {"XB-BB-EMA-Ladder-MGC", "XB-ORB-EMA-Chandelier-MNQ",
                  "XB-BB-EMA-Ladder-MYM", "XB-PB-EMA-Ladder-MNQ"}
CHUNK_CORR_REST = {"XB-VWAP-EMA-Ladder-MYM", "XB-VWAP-EMA-Ladder-MGC",
                   "XB-BB-EMA-Ladder-MNQ", "XB-PB-EMA-Ladder-MYM"}
CHUNK_TIMESTOP = {"XB-ORB-EMA-TimeStop-MNQ"}


# Strategy specs (asset, entry, filter, exit, params) for backtesting.
# Sourced from research/cost_integrity_reread.py so the funnel and the
# re-read agree on what each candidate is.
def _build_strategy_specs():
    specs = {}
    for c in PROBATION_CANDIDATES + CORRELATION_CANDIDATES:
        sid, asset, entry, filt, exit_name, params = c
        specs[sid] = {
            "asset": asset, "entry": entry, "filter": filt,
            "exit": exit_name, "params": params,
        }
    return specs

STRATEGY_SPECS = _build_strategy_specs()

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


# ── Gate 4: Walk-Forward H1/H2 (cost-aware) ──────────────────────────────────

def _split_h1_h2(df: pd.DataFrame) -> tuple:
    """Split data 50/50 by date midpoint. First half = H1, second = H2."""
    dates = pd.to_datetime(df["datetime"]).dt.date
    unique_dates = sorted(dates.unique())
    midpoint = unique_dates[len(unique_dates) // 2]
    h1 = df[dates <= midpoint].copy().reset_index(drop=True)
    h2 = df[dates > midpoint].copy().reset_index(drop=True)
    return h1, h2


def _compute_pf(trades_df) -> float:
    if trades_df is None or len(trades_df) == 0:
        return 0.0
    wins = trades_df.loc[trades_df["pnl"] > 0, "pnl"].sum()
    losses = abs(trades_df.loc[trades_df["pnl"] < 0, "pnl"].sum())
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return float(wins / losses)


def walkforward_h1h2(strategy_id: str) -> dict:
    """Run cost-aware H1/H2 backtest. Returns net PF for each half + stability."""
    spec = STRATEGY_SPECS.get(strategy_id)
    if spec is None:
        return {"error": f"no spec for {strategy_id}"}

    asset = spec["asset"]
    data_path = ROOT / f"data/processed/{asset}_5m.csv"
    if not data_path.exists():
        return {"error": f"no data at {data_path}"}

    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    asset_cfg = get_asset(asset)

    h1, h2 = _split_h1_h2(df)

    def _backtest_half(half_df, label):
        signals = generate_crossbred_signals(
            half_df, entry_name=spec["entry"], exit_name=spec["exit"],
            filter_name=spec["filter"], params=spec["params"],
        )
        res = run_backtest(
            half_df, signals, mode="both",
            point_value=asset_cfg["point_value"], symbol=asset,
        )
        trades = res["trades_df"]
        return {
            f"{label}_pf": round(_compute_pf(trades), 3),
            f"{label}_trades": int(len(trades)),
            f"{label}_pnl": round(float(trades["pnl"].sum()) if len(trades) else 0.0, 0),
            f"{label}_start": str(pd.to_datetime(half_df["datetime"].iloc[0]).date()),
            f"{label}_end": str(pd.to_datetime(half_df["datetime"].iloc[-1]).date()),
        }

    h1_res = _backtest_half(h1, "h1")
    h2_res = _backtest_half(h2, "h2")
    result = {"strategy_id": strategy_id, "asset": asset, **h1_res, **h2_res}

    h1_pf = result["h1_pf"]
    h2_pf = result["h2_pf"]
    result["worst_half_pf"] = round(min(h1_pf, h2_pf), 3)
    result["best_half_pf"] = round(max(h1_pf, h2_pf), 3)
    if max(h1_pf, h2_pf) > 0:
        result["stability_ratio"] = round(min(h1_pf, h2_pf) / max(h1_pf, h2_pf), 3)
    else:
        result["stability_ratio"] = 0.0
    result["passed"] = (h1_pf > 1.0) and (h2_pf > 1.0)
    return result


def gate_4_walkforward(candidate: dict) -> tuple:
    """G4 (weight 3): both halves must have net PF > 1.0.

    Requires walkforward_h1h2() to have been run first and the result
    attached to the candidate dict under 'g4_walkforward'.
    """
    wf = candidate.get("g4_walkforward")
    if wf is None:
        return None, "walk-forward not yet run"
    if "error" in wf:
        return 0, f"error: {wf['error']}"
    if wf["passed"]:
        return 3, f"H1 PF {wf['h1_pf']:.3f}, H2 PF {wf['h2_pf']:.3f}, stability {wf['stability_ratio']:.2f}"
    return 0, f"failed — H1 PF {wf['h1_pf']:.3f}, H2 PF {wf['h2_pf']:.3f}, worst half {wf['worst_half_pf']:.3f}"


# ── Gate registry ────────────────────────────────────────────────────────────

SESSION_1_GATES = [
    ("G1_cheap_screen_pass", 1, gate_1_cheap_screen_pass),
    ("G2_correlation_cleared", 1, gate_2_correlation_cleared),
    ("G3_cost_adjusted_pf", 2, gate_3_cost_adjusted_pf),
]

# Gate 4 lands in Session 2.
SESSION_2_GATES = [
    ("G4_walkforward_h1h2", 3, gate_4_walkforward),
]

# Placeholder columns for Sessions 3-4 (will fill incrementally).
SESSION_3_PLUS_GATES = [
    ("G5_trade_count", 1, None),
    ("G6_concentration", 2, None),
    ("G7_forward_runner_trades", 2, None),
    ("G8_promotion_humility_doc", 1, None),
]

SESSION_2_PLUS_GATES = SESSION_2_GATES + SESSION_3_PLUS_GATES

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


CHUNK_MAP = {
    "probation": CHUNK_PROBATION,
    "corr-top": CHUNK_CORR_TOP,
    "corr-rest": CHUNK_CORR_REST,
    "timestop": CHUNK_TIMESTOP,
    "all": CHUNK_PROBATION | CHUNK_CORR_TOP | CHUNK_CORR_REST | CHUNK_TIMESTOP,
}


def render_session2_table(s2_rows):
    """Per-candidate Gate 4 walk-forward table."""
    lines = [
        "| Candidate | Asset | H1 PF | H2 PF | Worst | Stability | H1 trades | H2 trades | Pass? | G4 pts |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for r in sorted(s2_rows, key=lambda x: (-int(x.get("passed", False)), -x.get("worst_half_pf", 0))):
        if "error" in r:
            lines.append(f"| {r['strategy_id']} | {r.get('asset', '?')} | ERROR: {r['error']} |||||||||")
            continue
        passed = "✓" if r["passed"] else "✗"
        pts = 3 if r["passed"] else 0
        lines.append(
            f"| {r['strategy_id']} | {r['asset']} | {r['h1_pf']:.3f} | {r['h2_pf']:.3f} | "
            f"{r['worst_half_pf']:.3f} | {r['stability_ratio']:.2f} | "
            f"{r['h1_trades']} | {r['h2_trades']} | {passed} | {pts} |"
        )
    return "\n".join(lines)


def render_session2_report(scored, chunk_label):
    today = date.today().isoformat()
    out = []
    out.append(f"# Validation Funnel v0 — Session 2 ({today}) — chunk: {chunk_label}")
    out.append("")
    out.append("**Filed by:** `research/validation_funnel.py`")
    out.append("**Authority:** T1 intelligence; no registry mutation, no status changes.")
    out.append("**Sprint:** Phase 2 / Paper-Readiness Sprint Item #7 — Session 2 of 4.")
    out.append("")
    out.append("## Gate 4 — Walk-Forward H1/H2 (cost-aware)")
    out.append("")
    out.append("- 50/50 date-midpoint split of each asset's price series")
    out.append("- Cost-aware backtest on each half (`engine/asset_config.py` source of truth)")
    out.append("- Pass requires **both halves > 1.0 net PF** (worth 3 points)")
    out.append("")
    out.append("## Walk-forward results")
    out.append("")
    wf_rows = [c["g4_walkforward"] for c in scored if c.get("g4_walkforward")]
    for r in wf_rows:
        # carry strategy_id and asset into the row for rendering
        pass
    # Combine wf result with strategy_id key for clarity
    enriched = []
    for c in scored:
        wf = c.get("g4_walkforward")
        if wf:
            enriched.append({**wf, "strategy_id": c["strategy_id"], "asset": c["asset"]})
    out.append(render_session2_table(enriched))
    out.append("")
    out.append("## Cumulative scores after Gate 4")
    out.append("")
    out.append("| Candidate | S1 | G4 | Total (out of 7) | Net PF | Notes |")
    out.append("|---|---:|---:|---:|---:|---|")
    for c in sorted(scored, key=lambda x: -x.get("cumulative_score", 0)):
        s1 = c.get("session_1_score", 0)
        g4 = c["scores"].get("G4_walkforward_h1h2")
        g4_str = str(g4) if g4 is not None else "—"
        total = c.get("cumulative_score", s1)
        wf = c.get("g4_walkforward") or {}
        note = ""
        if g4 == 0 and "passed" in wf:
            note = f"WF failed — worst {wf.get('worst_half_pf', '?')}"
        elif g4 is None:
            note = "deferred (different chunk)"
        out.append(
            f"| {c['strategy_id']} | {s1}/4 | {g4_str if g4 is not None else '—'} | "
            f"{total}/7 | {c.get('new_pf', 0):.3f} | {note} |"
        )
    out.append("")
    out.append("## Eligible / Culled summary")
    out.append("")
    g4_run = [c for c in scored if c.get("g4_walkforward")]
    g4_pass = [c for c in g4_run if c.get("g4_walkforward", {}).get("passed")]
    g4_fail = [c for c in g4_run if not c.get("g4_walkforward", {}).get("passed") and "error" not in c.get("g4_walkforward", {})]
    g4_err = [c for c in g4_run if "error" in c.get("g4_walkforward", {})]
    g4_deferred = [c for c in scored if c.get("g4_walkforward") is None]
    out.append(f"- **{len(g4_pass)} candidates passed Gate 4** (full 3 pts; both halves > 1.0 net PF)")
    out.append(f"- **{len(g4_fail)} candidates failed Gate 4** (one or both halves ≤ 1.0)")
    if g4_err:
        out.append(f"- **{len(g4_err)} candidates errored** during walk-forward")
    out.append(f"- **{len(g4_deferred)} candidates deferred** to other chunks")
    out.append("")
    out.append("## Cost fragility notes")
    out.append("")
    out.append("- **XB-ORB-EMA-Ladder-MCL** (full-sample net PF 1.298, cost 34.7% of gross avg trade) is the most cost-sensitive surviving probation candidate. Any WF half ratio < 0.6 should be flagged as compounding fragility.")
    out.append("- All MCL/MYM candidates run with slip=2 (conservative bias); the WF result inherits that cost basis.")
    out.append("")
    out.append("---")
    out.append("")
    out.append(f"*Session 2 chunk '{chunk_label}'. Read-only intelligence; no decisions taken. Next chunk(s) or Session 3 to follow.*")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", action="store_true",
                    help="Write report + JSON to docs/reports/validation_funnel/")
    ap.add_argument("--session", type=int, default=1, choices=[1, 2],
                    help="Which session to run (1 = Gates 1-3; 2 = Gate 4 walk-forward)")
    ap.add_argument("--chunk", default="all", choices=list(CHUNK_MAP),
                    help="Session 2 chunk: probation / corr-top / corr-rest / timestop / all")
    args = ap.parse_args()

    rows = _load_funnel_inputs()
    scored = [score_candidate(r, SESSION_1_GATES) for r in rows]

    if args.session == 2:
        # Run Gate 4 walk-forward on the chosen chunk
        chunk_ids = CHUNK_MAP[args.chunk]
        print(f"Running Gate 4 walk-forward on chunk '{args.chunk}' ({len(chunk_ids)} candidates)...\n",
              flush=True)
        for c in scored:
            if c["strategy_id"] in chunk_ids:
                print(f"  [WF] {c['strategy_id']} ...", flush=True)
                c["g4_walkforward"] = walkforward_h1h2(c["strategy_id"])
                wf = c["g4_walkforward"]
                if "error" in wf:
                    print(f"    → ERROR: {wf['error']}", flush=True)
                else:
                    pf_str = f"H1={wf['h1_pf']:.3f} H2={wf['h2_pf']:.3f}"
                    pass_str = "PASS" if wf["passed"] else "FAIL"
                    print(f"    → {pf_str} → {pass_str}", flush=True)

        # Compute G4 score for each candidate that ran
        for c in scored:
            if c.get("g4_walkforward"):
                pts, why = gate_4_walkforward(c)
                c["scores"]["G4_walkforward_h1h2"] = pts
                c["explanations"]["G4_walkforward_h1h2"] = why
            else:
                c["scores"]["G4_walkforward_h1h2"] = None
                c["explanations"]["G4_walkforward_h1h2"] = "deferred"

        # Cumulative score
        for c in scored:
            s1 = c.get("session_1_score", 0)
            g4 = c["scores"].get("G4_walkforward_h1h2") or 0
            c["cumulative_score"] = s1 + g4

        report = render_session2_report(scored, args.chunk)
    else:
        report = render_report(scored)

    print(report)

    if args.save:
        out_dir = ROOT / "docs/reports/validation_funnel"
        out_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        if args.session == 1:
            md_path = out_dir / f"{today}_validation_funnel_session1.md"
            json_path = out_dir / f"{today}_validation_funnel_session1.json"
        else:
            md_path = out_dir / f"{today}_validation_funnel_session2_{args.chunk}.md"
            json_path = out_dir / f"{today}_validation_funnel_session2_{args.chunk}.json"
        md_path.write_text(report + "\n")
        json_path.write_text(json.dumps(scored, indent=2, default=str))
        print(f"\nSaved:\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()
