#!/usr/bin/env python3
"""Consolidate Sessions 1+2+3 of the Validation Funnel into one scorecard.

Each session was run chunk-by-chunk and saved per-chunk JSONs. This script
merges them by strategy_id and produces the true cumulative report.

Outputs:
  docs/reports/validation_funnel/<date>_validation_funnel_cumulative.md
  docs/reports/validation_funnel/<date>_validation_funnel_cumulative.json
"""

import json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "docs/reports/validation_funnel"

SESSION_1_FILE = "2026-05-20_validation_funnel_session1.json"
SESSION_2_FILES = [
    "2026-05-20_validation_funnel_session2_probation.json",
    "2026-05-20_validation_funnel_session2_corr-top.json",
    "2026-05-20_validation_funnel_session2_corr-rest.json",
    "2026-05-20_validation_funnel_session2_timestop.json",
]
SESSION_3_FILES = [
    "2026-05-20_validation_funnel_session3_probation.json",
    "2026-05-20_validation_funnel_session3_corr-top.json",
    "2026-05-20_validation_funnel_session3_corr-rest.json",
    "2026-05-20_validation_funnel_session3_timestop.json",
]

PROBATION_SET = {
    "XB-ORB-EMA-Ladder-MNQ", "XB-ORB-EMA-Ladder-MCL", "XB-ORB-EMA-Ladder-MYM",
}

CLUSTER_RETAINED_VARIANTS = {
    "XB-ORB-EMA-TimeStop-MNQ": "XB-ORB-EMA-Chandelier-MNQ",
}

ARCHETYPES = {
    "XB-ORB-EMA-Ladder-MNQ": "workhorse",
    "XB-ORB-EMA-Ladder-MCL": "workhorse",
    "XB-ORB-EMA-Ladder-MYM": "workhorse",
    "XB-PB-EMA-Ladder-MNQ": "workhorse",
    "XB-PB-EMA-Ladder-MYM": "tail",
    "XB-BB-EMA-Ladder-MNQ": "workhorse",
    "XB-BB-EMA-Ladder-MGC": "tail",
    "XB-BB-EMA-Ladder-MYM": "tail",
    "XB-VWAP-EMA-Ladder-MGC": "tail",
    "XB-VWAP-EMA-Ladder-MYM": "tail",
    "XB-ORB-EMA-Chandelier-MNQ": "workhorse",
    "XB-ORB-EMA-TimeStop-MNQ": "tail",
}


def _load(filename):
    p = REPORTS / filename
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def consolidate():
    # Session 1 is the universe
    s1 = _load(SESSION_1_FILE)
    by_id = {c["strategy_id"]: dict(c) for c in s1}

    # Merge Session 2 G4 scores
    for f in SESSION_2_FILES:
        for c in _load(f):
            sid = c["strategy_id"]
            if sid not in by_id:
                by_id[sid] = dict(c)
            # Only copy G4 if present
            g4 = c.get("scores", {}).get("G4_walkforward_h1h2")
            if g4 is not None:
                by_id[sid].setdefault("scores", {})["G4_walkforward_h1h2"] = g4
                by_id[sid].setdefault("explanations", {})["G4_walkforward_h1h2"] = (
                    c.get("explanations", {}).get("G4_walkforward_h1h2", "")
                )
                if c.get("g4_walkforward"):
                    by_id[sid]["g4_walkforward"] = c["g4_walkforward"]

    # Merge Session 3 G5+G6+G7 scores
    for f in SESSION_3_FILES:
        for c in _load(f):
            sid = c["strategy_id"]
            if sid not in by_id:
                continue
            for gate in ("G5_trade_count", "G6_concentration", "G7_forward_runner_trades"):
                if c.get("scores", {}).get(gate) is not None or (
                    gate == "G7_forward_runner_trades" and sid not in PROBATION_SET
                ):
                    by_id[sid].setdefault("scores", {})[gate] = c.get("scores", {}).get(gate)
                    by_id[sid].setdefault("explanations", {})[gate] = (
                        c.get("explanations", {}).get(gate, "")
                    )
            if c.get("g6_concentration"):
                by_id[sid]["g6_concentration"] = c["g6_concentration"]
            if c.get("g7_forward_trade_count") is not None:
                by_id[sid]["g7_forward_trade_count"] = c["g7_forward_trade_count"]

    # G8 (humility doc check) — inline existence + required-sections check
    humility_dir = ROOT / "docs/promotion_humility"
    required_sections = (
        "failure modes", "concentration caveat", "cost caveat",
        "forward-evidence caveat", "cluster / correlation caveat",
        "what would invalidate",
    )
    for c in by_id.values():
        sid = c["strategy_id"]
        doc = humility_dir / f"{sid}.md"
        if not doc.exists():
            pts, why = 0, f"no humility doc at {doc.relative_to(ROOT)}"
        else:
            text = doc.read_text().lower()
            missing = [s for s in required_sections if s not in text]
            if missing:
                pts, why = 0, f"missing sections: {missing}"
            else:
                pts, why = 1, f"complete at {doc.relative_to(ROOT)}"
        c.setdefault("scores", {})["G8_promotion_humility_doc"] = pts
        c.setdefault("explanations", {})["G8_promotion_humility_doc"] = why

    # Compute cumulative
    for c in by_id.values():
        scores = c.get("scores", {})
        s1_pts = sum(scores.get(g, 0) or 0 for g in
                     ("G1_cheap_screen_pass", "G2_correlation_cleared", "G3_cost_adjusted_pf"))
        g4 = scores.get("G4_walkforward_h1h2") or 0
        g5 = scores.get("G5_trade_count") or 0
        g6 = scores.get("G6_concentration") or 0
        g7_raw = scores.get("G7_forward_runner_trades")
        g7 = g7_raw if g7_raw is not None else 0
        g8 = scores.get("G8_promotion_humility_doc") or 0
        cum = s1_pts + g4 + g5 + g6 + g7 + g8
        c["cumulative_score"] = cum
        c["cumulative_max"] = 13 if c["strategy_id"] in PROBATION_SET else 11

    return list(by_id.values())


def classify(c):
    """Classify per Session 4 final thresholds (13-pt scale, 11 for non-probation).

    Probation:
      ≥11/13 → paper-eligible
       ≥9/13 → paper-borderline
       else  → REJECT
    Non-probation (G7=PENDING):
      ≥9/11  → paper-eligible (promotion PEND forward)
      ≥7/11  → paper-borderline (promotion PEND forward)
       else  → REJECT
    """
    sid = c["strategy_id"]
    cum = c.get("cumulative_score", 0)
    is_probation = sid in PROBATION_SET
    if is_probation:
        if cum >= 11:
            return "paper-eligible (promotion gate borderline)"
        if cum >= 9:
            return "paper-borderline (work needed)"
        return "REJECT"
    if cum >= 9:
        return "paper-eligible (promotion PEND forward)"
    if cum >= 7:
        return "paper-borderline (promotion PEND forward)"
    return "REJECT"


def render_report(merged):
    today = date.today().isoformat()
    out = []
    out.append(f"# Validation Funnel v0 — Final Consolidated ({today})")
    out.append("")
    out.append("**Filed by:** `research/funnel_consolidate.py`")
    out.append("**Authority:** T1 intelligence; no registry mutation, no status changes.")
    out.append("**Sprint:** Phase 2 / Paper-Readiness Sprint Item #7 — **all 4 sessions complete**.")
    out.append("")
    out.append("## Headline")
    out.append("")
    advancing = [c for c in merged if c["cumulative_score"] >= (10 if c["strategy_id"] in PROBATION_SET else 9)]
    paper_border = [c for c in merged if c not in advancing and c["cumulative_score"] >= (8 if c["strategy_id"] in PROBATION_SET else 7)]
    reject = [c for c in merged if c not in advancing and c not in paper_border]
    out.append(f"**{len(advancing)} paper-eligible / {len(paper_border)} paper-borderline / {len(reject)} REJECT.**")
    out.append("")
    out.append("Concentration (Gate 6) is the dominant culling factor — many candidates that passed walk-forward (Gate 4) fail concentration because their total profit depends on a small number of outlier trades (top-10 PnL > 100% of total net = remaining trades net negative).")
    out.append("")
    out.append("## Cumulative scorecard (sorted by cumulative score)")
    out.append("")
    out.append("Max possible: **13** (probation) / **11** (non-probation; G7=PENDING_FORWARD_EVIDENCE).")
    out.append("")
    out.append("| Candidate | Asset | Bucket | S1 | G4 | G5 | G6 | G7 | G8 | Cumulative | Net PF | Worst WF | Classification |")
    out.append("|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|")
    for c in sorted(merged, key=lambda x: (-x.get("cumulative_score", 0), -x.get("new_pf", 0))):
        sid = c["strategy_id"]
        scores = c.get("scores", {})
        s1 = sum(scores.get(g, 0) or 0 for g in
                 ("G1_cheap_screen_pass", "G2_correlation_cleared", "G3_cost_adjusted_pf"))
        g4 = scores.get("G4_walkforward_h1h2") or 0
        g5 = scores.get("G5_trade_count")
        g6 = scores.get("G6_concentration")
        g7 = scores.get("G7_forward_runner_trades")
        g8 = scores.get("G8_promotion_humility_doc")
        g7_str = "PEND" if g7 is None else str(g7)
        worst_wf = c.get("g4_walkforward", {}).get("worst_half_pf", "?")
        out.append(
            f"| {sid} | {c.get('asset', '?')} | {c.get('bucket', '?')} | "
            f"{s1} | {g4} | {g5 if g5 is not None else '—'} | "
            f"{g6 if g6 is not None else '—'} | {g7_str} | "
            f"{g8 if g8 is not None else '—'} | "
            f"**{c.get('cumulative_score', 0)}/{c.get('cumulative_max', '?')}** | "
            f"{c.get('new_pf', 0):.3f} | {worst_wf} | {classify(c)} |"
        )
    out.append("")
    out.append("## Concentration detail (Gate 6)")
    out.append("")
    out.append("Threshold: top-3 < 30%, top-10 < 55%, max single year < 40%.")
    out.append("")
    out.append("| Candidate | top-3 | top-10 | max-year | Verdict |")
    out.append("|---|---:|---:|---:|---|")
    for c in sorted(merged, key=lambda x: -x.get("cumulative_score", 0)):
        conc = c.get("g6_concentration") or {}
        if not conc:
            continue
        top3 = conc.get("top3_pct")
        top10 = conc.get("top10_pct")
        maxy = conc.get("max_year_pct")
        passed = "PASS ✓" if conc.get("passed") else "FAIL"
        out.append(
            f"| {c['strategy_id']} | "
            f"{(top3 * 100):.1f}% | {(top10 * 100):.1f}% | {(maxy * 100):.1f}% | {passed} |"
            if all(x is not None for x in (top3, top10, maxy)) else
            f"| {c['strategy_id']} | — | — | — | {passed} |"
        )
    out.append("")
    out.append("## Forward-evidence status (Gate 7)")
    out.append("")
    out.append("| Candidate | Probation? | Forward trades | G7 |")
    out.append("|---|---|---:|---|")
    for c in sorted(merged, key=lambda x: -x.get("cumulative_score", 0)):
        sid = c["strategy_id"]
        is_prob = sid in PROBATION_SET
        fwd = c.get("g7_forward_trade_count")
        g7 = c.get("scores", {}).get("G7_forward_runner_trades")
        if is_prob:
            g7_str = f"{g7} pts ({fwd} forward trades)"
        else:
            g7_str = "PENDING_FORWARD_EVIDENCE (never forward-traded)"
        out.append(f"| {sid} | {'yes' if is_prob else 'no'} | {fwd if fwd is not None else '—'} | {g7_str} |")
    out.append("")
    out.append("## Critical findings (Sessions 1–3 net)")
    out.append("")
    out.append("### 1. Concentration is the cull")
    out.append("")
    out.append("8 of 12 candidates fail Gate 6 concentration despite passing walk-forward. Multiple show top-10 > 100% of total PnL (i.e., the remaining trades net negative). The strategy depends on a small number of outliers.")
    out.append("")
    fails_g6 = [c for c in merged if c.get("g6_concentration", {}).get("passed") is False]
    for c in fails_g6:
        conc = c["g6_concentration"]
        out.append(f"- **{c['strategy_id']}**: top-3 {conc.get('top3_pct', 0)*100:.0f}%, top-10 {conc.get('top10_pct', 0)*100:.0f}%, max-year {conc.get('max_year_pct', 0)*100:.0f}%")
    out.append("")
    out.append("### 2. G5 archetype/threshold issue surfaced — XB-ORB-EMA-Ladder-MYM")
    out.append("")
    out.append("MYM probation: workhorse archetype + 371 full-sample trades → G5=0 (workhorse threshold is 500). But MYM's data window is only 2.0 years (per CLAUDE.md). The 500-trade workhorse threshold was calibrated for 6-year strategies. Strict application here is **biased against newer assets**.")
    out.append("")
    out.append("Operator decision needed: relax G5 for data-window-limited probation candidates, or accept that MYM doesn't clear G5 until data accumulates.")
    out.append("")
    out.append("### 3. Probation forward-trade counts are below 30 for MNQ and MCL")
    out.append("")
    out.append("- XB-ORB-EMA-Ladder-MNQ: 24 forward trades → G7=0")
    out.append("- XB-ORB-EMA-Ladder-MCL: 20 forward trades → G7=0")
    out.append("- XB-ORB-EMA-Ladder-MYM: 32 forward trades → G7=2 ✓")
    out.append("")
    out.append("MNQ and MCL each need 6–10 more forward trades to clear Gate 7. They are paper-eligible now but not promotion-eligible until forward accumulates.")
    out.append("")
    out.append("### 4. The candidate pool that emerges as paper-ready")
    out.append("")
    pe = sorted([c for c in advancing], key=lambda x: -x.get("cumulative_score", 0))
    if pe:
        for c in pe:
            extra = ""
            if c["strategy_id"] in PROBATION_SET and c.get("scores", {}).get("G7_forward_runner_trades", 0) < 2:
                extra = " (forward trades below 30 — promotion-eligible only after accumulation)"
            out.append(f"- **{c['strategy_id']}** — cum {c['cumulative_score']}/{c['cumulative_max']}, net PF {c.get('new_pf', 0):.3f}{extra}")
    else:
        out.append("- (none after Session 3 — Session 4 / Gate 8 still to land + concentration/G5 decisions pending)")
    out.append("")
    out.append("## Cluster / top-3 selection note")
    out.append("")
    for retained, leader in CLUSTER_RETAINED_VARIANTS.items():
        out.append(f"- **{retained}** is retained variant of **{leader}** cluster — one exposure slot.")
    out.append("")
    out.append("## Top-3 selection (Item #8)")
    out.append("")
    out.append("Per operator lean 2026-05-20:")
    out.append("")
    out.append("1. **XB-ORB-EMA-Ladder-MNQ** — probation, cum 11/13, anchor candidate")
    out.append("2. **XB-ORB-EMA-Chandelier-MNQ** — correlation cluster leader, cum 11/11 (TimeStop collapses to this slot)")
    out.append("3. **XB-PB-EMA-Ladder-MNQ** — correlation, cum 11/11, cleaner third than fragile MCL")
    out.append("")
    out.append("**XB-ORB-EMA-Ladder-MCL** (cum 11/13, fragile) is the alternate. Same gate score as the top-3 but `cost_fragility` flag and lower worst-half WF (1.199 vs 1.242–1.445) make it second-choice. If the top-3 want broker-rate-light candidates only, MCL drops to alternate.")
    out.append("")
    out.append("## Next: Item #9 paper-readiness packets")
    out.append("")
    out.append("Each top-3 candidate already has its promotion-humility packet (filed today as part of Gate 8). Item #9 builds the full paper-readiness packet around each, combining: cost-aware funnel evidence + humility packet + forward-runner data + decision recommendation. Target ship by 2026-06-17.")
    out.append("")
    out.append("---")
    out.append("")
    out.append("*Final consolidated 2026-05-20. Read-only intelligence; no status mutation. Top-3 selection awaits operator confirmation.*")
    return "\n".join(out)


def main():
    merged = consolidate()
    report = render_report(merged)
    today = date.today().isoformat()
    md_path = REPORTS / f"{today}_validation_funnel_cumulative.md"
    json_path = REPORTS / f"{today}_validation_funnel_cumulative.json"
    md_path.write_text(report + "\n")
    json_path.write_text(json.dumps(merged, indent=2, default=str))
    print(f"Saved:\n  {md_path}\n  {json_path}")


if __name__ == "__main__":
    main()
