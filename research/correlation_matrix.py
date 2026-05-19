#!/usr/bin/env python3
"""Correlation matrix for the 12 forge-hybrid candidates registered 2026-05-06.

Phase 2 Item #2 of the Paper-Readiness Sprint. Lane 2 governance analysis —
report-only; any registry reclassification based on findings is Lane 3 and
requires explicit operator approval.

Purpose: detect fictional diversification across registered candidates.
We may think we have 12 distinct strategies but really have 3-5 clusters.
Without this analysis, top-3 candidate selection for paper-readiness packets
risks shipping correlated duplicates as "diverse."

Methodology (locked 2026-05-13, refined 2026-05-18):
1. Structural similarity (entry × filter × exit × asset overlap, 0-4 scale)
2. Pearson r on aligned daily PnL series (outer-join, no-trade day = $0)
3. Threshold classification (0.30 / 0.60 / 0.85)
4. Same-asset vs cross-asset split (cross-asset high r = regime co-movement,
   not necessarily duplicate strategy logic)
5. v1: single run per candidate, no 3x reproducibility (separate item)
6. v1: Pearson only; Spearman deferred unless trivial

Safety contract:
- Report-only. No registry mutation. Report ends with proposed
  reclassifications; operator approval required before any registry change.
- All file writes target docs/reports/correlation_matrix/.
- No Lane A surfaces, no scheduler changes, no source-helper changes.

Usage:
    python3 research/correlation_matrix.py              # print summary
    python3 research/correlation_matrix.py --save       # write full report
    python3 research/correlation_matrix.py --dry-run    # preview, no write
"""

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from itertools import combinations
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402
from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    generate_crossbred_signals,
)
from research.fql_forge_batch_runner import _load, _metrics, _params  # noqa: E402

REPORTS_DIR = ROOT / "docs" / "reports" / "correlation_matrix"

# The 12 registered 2026-05-06 candidates (per docs/_BACKLOG_post_patch_a_and_phase_1_exit.md §1)
# Derived from registry.relationships.components_used.
CANDIDATES = [
    # (strategy_id, asset, entry, filter, exit, archetype)
    ("XB-PB-EMA-Ladder-MNQ",      "MNQ", "pb_pullback",       "ema_slope", "profit_ladder", "workhorse"),
    ("XB-PB-EMA-Ladder-MCL",      "MCL", "pb_pullback",       "ema_slope", "profit_ladder", "workhorse"),
    ("XB-PB-EMA-Ladder-MYM",      "MYM", "pb_pullback",       "ema_slope", "profit_ladder", "tail"),
    ("XB-BB-EMA-Ladder-MNQ",      "MNQ", "bb_reversion",      "ema_slope", "profit_ladder", "workhorse"),
    ("XB-BB-EMA-Ladder-MGC",      "MGC", "bb_reversion",      "ema_slope", "profit_ladder", "tail"),
    ("XB-BB-EMA-Ladder-MCL",      "MCL", "bb_reversion",      "ema_slope", "profit_ladder", "tail"),
    ("XB-BB-EMA-Ladder-MYM",      "MYM", "bb_reversion",      "ema_slope", "profit_ladder", "tail"),
    ("XB-VWAP-EMA-Ladder-MGC",    "MGC", "vwap_continuation", "ema_slope", "profit_ladder", "tail"),
    ("XB-VWAP-EMA-Ladder-MCL",    "MCL", "vwap_continuation", "ema_slope", "profit_ladder", "workhorse"),
    ("XB-VWAP-EMA-Ladder-MYM",    "MYM", "vwap_continuation", "ema_slope", "profit_ladder", "tail"),
    ("XB-ORB-EMA-Chandelier-MNQ", "MNQ", "orb_breakout",      "ema_slope", "chandelier",    "workhorse"),
    ("XB-ORB-EMA-TimeStop-MNQ",   "MNQ", "orb_breakout",      "ema_slope", "time_stop",     "tail"),
]

# Classification thresholds (per operator-locked spec 2026-05-13)
THRESHOLD_DUPLICATE = 0.85
THRESHOLD_HIGHLY = 0.60
THRESHOLD_RELATED = 0.30

# Minimum sample size for reliable correlation (flag LOW_CONFIDENCE below this)
MIN_OVERLAP_DAYS = 100


@dataclass
class CandidateResult:
    cid: str
    asset: str
    entry: str
    filter: str
    exit: str
    archetype: str
    n_trades: int
    pf: float
    daily_pnl: pd.Series  # indexed by date


def _run_candidate(spec: tuple) -> CandidateResult:
    """Run cheap-screen capturing trades_df + aggregating to daily PnL."""
    cid, asset, entry, filter_name, exit_name, archetype = spec
    df = _load(asset)
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(
        df, entry_name=entry, exit_name=exit_name,
        filter_name=filter_name, params=_params(),
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    trades = res["trades_df"]
    m = _metrics(trades, cid)

    if len(trades) == 0:
        daily = pd.Series(dtype=float)
    else:
        # Aggregate per-trade PnL to daily series (entry date)
        trades = trades.copy()
        trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
        daily = trades.groupby("entry_date")["pnl"].sum()
        daily.index = pd.to_datetime(daily.index)

    return CandidateResult(
        cid=cid, asset=asset, entry=entry, filter=filter_name,
        exit=exit_name, archetype=archetype,
        n_trades=m["n"], pf=m["pf"], daily_pnl=daily,
    )


def _structural_similarity(a: CandidateResult, b: CandidateResult) -> int:
    """0-4 scale: count of matching dimensions (entry/filter/exit/asset)."""
    return (
        (1 if a.entry == b.entry else 0)
        + (1 if a.filter == b.filter else 0)
        + (1 if a.exit == b.exit else 0)
        + (1 if a.asset == b.asset else 0)
    )


def _pearson_corr(a: CandidateResult, b: CandidateResult) -> tuple:
    """Returns (pearson_r, overlap_days). Outer-join daily PnL,
    fill missing with 0 (no-trade day = $0 PnL), compute Pearson."""
    if len(a.daily_pnl) == 0 or len(b.daily_pnl) == 0:
        return (None, 0)
    # Align on common date index (outer join, fill 0)
    aligned = pd.concat([a.daily_pnl, b.daily_pnl], axis=1, keys=["a", "b"], sort=True).fillna(0)
    # Use intersection of dates that one of them traded on
    nonzero_a = aligned["a"] != 0
    nonzero_b = aligned["b"] != 0
    active_days = aligned[nonzero_a | nonzero_b]
    if len(active_days) < 5:
        return (None, len(active_days))
    r = active_days["a"].corr(active_days["b"])
    return (r if pd.notna(r) else None, len(active_days))


def _classify_pair(structural: int, pearson_r: float, same_asset: bool, overlap_days: int) -> str:
    """Classify a pair per locked thresholds + same-asset vs cross-asset rule."""
    if pearson_r is None:
        return "INSUFFICIENT_DATA"
    if overlap_days < MIN_OVERLAP_DAYS:
        suffix = " (LOW_CONFIDENCE)"
    else:
        suffix = ""
    if pearson_r >= THRESHOLD_DUPLICATE:
        return ("DUPLICATE_EXPOSURE" if same_asset
                else "DUPLICATE_EXPOSURE_CROSS_ASSET_SUSPICIOUS") + suffix
    if pearson_r >= THRESHOLD_HIGHLY:
        return ("HIGHLY_CORRELATED" if same_asset
                else "HIGHLY_CORRELATED_CROSS_ASSET_REGIME") + suffix
    if pearson_r >= THRESHOLD_RELATED:
        return "RELATED_VARIANT" + suffix
    return "DISTINCT" + suffix


def _propose_reclassification(per_candidate: dict, all_pairs: list) -> list:
    """For each candidate, recommend KEEP_DISTINCT / FLAG_FOR_REVIEW / MARK_VARIANT_OF.
    Returns list of dicts. NEVER applies — operator approval required for any registry change."""
    proposals = []
    for cid, info in per_candidate.items():
        dup_peers = [p["other"] for p in info["pairs"]
                     if "DUPLICATE_EXPOSURE" in p["classification"]
                     and "CROSS_ASSET" not in p["classification"]]
        if dup_peers:
            proposals.append({
                "candidate": cid,
                "recommendation": "FLAG_FOR_OPERATOR_REVIEW",
                "reason": f"Same-asset duplicate-exposure peer(s): {dup_peers}",
                "suggested_action": f"Operator decides: KEEP both as distinct (different exits/filters retain real value) "
                                    f"OR mark as variant_of_{dup_peers[0]}",
            })
        elif any("HIGHLY_CORRELATED" in p["classification"] and "CROSS_ASSET" not in p["classification"]
                 for p in info["pairs"]):
            proposals.append({
                "candidate": cid,
                "recommendation": "ACKNOWLEDGE_RELATED",
                "reason": "Same-asset highly-correlated peer(s); not duplicate but related",
                "suggested_action": "Update relationships.related list in registry to reflect peer ties",
            })
        else:
            proposals.append({
                "candidate": cid,
                "recommendation": "KEEP_DISTINCT",
                "reason": "No same-asset peer crosses HIGHLY_CORRELATED threshold",
                "suggested_action": "No registry change needed",
            })
    return proposals


def _render_report(results: list, structural_matrix: dict, pearson_matrix: dict,
                   pairs: list, per_candidate: dict, proposals: list,
                   generated_at: datetime) -> str:
    today = date.today().isoformat()
    n = len(results)

    classifications = Counter(p["classification"] for p in pairs)

    out = [f"# FQL Correlation Matrix — {today}\n"]
    out.append(f"**Generated:** {generated_at.isoformat(timespec='seconds')}")
    out.append(f"**Phase 2 Item #2** — Paper-Readiness Sprint Day 1")
    out.append(f"**Scope:** Lane 2 analysis on 12 registered 2026-05-06 forge-hybrid candidates")
    out.append(f"**Safety:** report-only; registry reclassification requires explicit operator approval (Lane 3)\n")
    out.append(f"**Evidence tier:** Cheap Screen Tier — correlations are backtest-derived; forward correlation may vary.\n")
    out.append("---\n")

    # Executive summary
    out.append("## 1. Executive Summary\n")
    out.append(f"- Candidates analyzed: **{n}**")
    out.append(f"- Pairs evaluated: **{len(pairs)}**")
    out.append(f"- Min overlap days threshold for LOW_CONFIDENCE: {MIN_OVERLAP_DAYS}")
    out.append(f"\n### Pair classification counts")
    for cls, count in classifications.most_common():
        out.append(f"- {cls}: **{count}**")

    n_dup_same = sum(1 for p in pairs if p["classification"].startswith("DUPLICATE_EXPOSURE")
                     and "CROSS_ASSET" not in p["classification"])
    n_dup_cross = sum(1 for p in pairs if "DUPLICATE_EXPOSURE_CROSS_ASSET" in p["classification"])
    n_high_same = sum(1 for p in pairs if p["classification"].startswith("HIGHLY_CORRELATED")
                      and "CROSS_ASSET" not in p["classification"])
    n_distinct = sum(1 for p in pairs if p["classification"].startswith("DISTINCT"))

    out.append(f"\n### Same-asset findings (the ones that matter for fictional diversification)")
    out.append(f"- Same-asset DUPLICATE_EXPOSURE pairs: **{n_dup_same}**")
    out.append(f"- Same-asset HIGHLY_CORRELATED pairs: **{n_high_same}**")
    out.append(f"- DISTINCT pairs (any asset): {n_distinct}")
    out.append(f"- Cross-asset DUPLICATE_EXPOSURE pairs (suspicious; likely regime co-movement): {n_dup_cross}")

    # Candidates summary table
    out.append("\n---\n## 2. Candidates analyzed\n")
    out.append("| # | Strategy | Asset | Entry | Filter | Exit | Archetype | n_trades | PF |")
    out.append("|---|---|---|---|---|---|---|---:|---:|")
    for i, r in enumerate(results, 1):
        out.append(f"| {i} | `{r.cid}` | {r.asset} | {r.entry} | {r.filter} | {r.exit} | {r.archetype} | {r.n_trades} | {r.pf:.3f} |")

    # Structural similarity matrix
    out.append("\n---\n## 3. Structural similarity matrix (0-4 scale)\n")
    out.append("Components matched: entry + filter + exit + asset (each contributes 1). 4 = identical.\n")
    out.append("| | " + " | ".join(f"{i+1}" for i in range(n)) + " |")
    out.append("|---|" + "|".join(":---:" for _ in range(n)) + "|")
    for i, r_i in enumerate(results, 1):
        row = [f"**{i}**"]
        for j in range(1, n + 1):
            if i == j:
                row.append("—")
            elif j > i:
                row.append("·")  # upper triangle
            else:
                row.append(str(structural_matrix[(i, j)]))
        out.append("| " + " | ".join(row) + " |")

    # Pearson matrix
    out.append("\n---\n## 4. Pearson r matrix (daily PnL, outer-join with 0-fill)\n")
    out.append("| | " + " | ".join(f"{i+1}" for i in range(n)) + " |")
    out.append("|---|" + "|".join(":---:" for _ in range(n)) + "|")
    for i, r_i in enumerate(results, 1):
        row = [f"**{i}**"]
        for j in range(1, n + 1):
            if i == j:
                row.append("—")
            elif j > i:
                row.append("·")
            else:
                r_val = pearson_matrix.get((i, j))
                row.append(f"{r_val:.2f}" if r_val is not None else "n/a")
        out.append("| " + " | ".join(row) + " |")

    # Pair classification table
    out.append("\n---\n## 5. Pair classification (all 66 pairs)\n")
    out.append("Sorted by Pearson r descending (most-correlated first).\n")
    out.append("| Pair | Structural (0-4) | Same asset? | Overlap days | Pearson r | Classification |")
    out.append("|---|---:|:---:|---:|---:|---|")
    for p in sorted(pairs, key=lambda x: -(x["pearson"] if x["pearson"] is not None else -2)):
        same_marker = "✅" if p["same_asset"] else "—"
        r_str = f"{p['pearson']:.3f}" if p["pearson"] is not None else "n/a"
        out.append(f"| `{p['a']}` ↔ `{p['b']}` | {p['structural']} | {same_marker} | {p['overlap_days']} | {r_str} | {p['classification']} |")

    # Per-candidate summary
    out.append("\n---\n## 6. Per-candidate summary\n")
    out.append("| Candidate | # DUPLICATE peers (same-asset) | # HIGHLY_CORRELATED peers (same-asset) | # DISTINCT peers |")
    out.append("|---|---:|---:|---:|")
    for cid, info in per_candidate.items():
        dup_count = sum(1 for p in info["pairs"]
                        if "DUPLICATE_EXPOSURE" in p["classification"]
                        and "CROSS_ASSET" not in p["classification"])
        high_count = sum(1 for p in info["pairs"]
                         if "HIGHLY_CORRELATED" in p["classification"]
                         and "CROSS_ASSET" not in p["classification"])
        dist_count = sum(1 for p in info["pairs"] if p["classification"].startswith("DISTINCT"))
        out.append(f"| `{cid}` | {dup_count} | {high_count} | {dist_count} |")

    # Proposed reclassifications
    out.append("\n---\n## 7. Proposed reclassifications (operator approval required)\n")
    out.append("**This is Lane 2 analysis. Any registry change is Lane 3 and requires explicit operator approval.**\n")
    out.append("| Candidate | Recommendation | Reason | Suggested action |")
    out.append("|---|---|---|---|")
    for prop in proposals:
        out.append(f"| `{prop['candidate']}` | **{prop['recommendation']}** | {prop['reason']} | {prop['suggested_action']} |")

    # Caveats
    out.append("\n---\n## 8. Caveats & limitations\n")
    out.append(f"- Single-run-per-candidate (no 3× reproducibility in v1; separate item)")
    out.append(f"- Pearson on daily PnL (Spearman not included in v1)")
    out.append(f"- Outer-join with 0-fill: no-trade days count as zero correlation contribution")
    out.append(f"- Pairs with overlap_days < {MIN_OVERLAP_DAYS} flagged LOW_CONFIDENCE")
    out.append(f"- 66 pairwise tests at α=0.05 → ~3 false-positive 'duplicates' by chance; use stricter r ≥ 0.85")
    out.append(f"- Cross-asset high r may indicate regime co-movement, NOT strategy duplication — classified separately")
    out.append(f"- Backtest-derived; forward correlation may diverge")

    # Safety
    out.append("\n---\n## 9. Safety affirmation\n")
    out.append("- Report-only. NO registry mutation occurred during this analysis.")
    out.append("- NO Lane A surfaces touched (runtime / scheduler / portfolio / checkpoint / hold-state).")
    out.append("- NO source-helper / candidate pool / promotion / paper-readiness changes.")
    out.append("- Any registry reclassification based on §7 proposals requires explicit operator approval (Lane 3, surgical commit pattern).")

    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="Phase 2 Item #2: Correlation matrix on 12 forge-hybrid candidates")
    ap.add_argument("--save", action="store_true", help="Write report + JSON to docs/reports/correlation_matrix/")
    ap.add_argument("--dry-run", action="store_true", help="Generate but do not write")
    args = ap.parse_args()

    print(f"FQL Correlation Matrix — Phase 2 Item #2 — {date.today().isoformat()}")
    print("=" * 78)
    print(f"Running {len(CANDIDATES)} candidates (cheap-screen, capturing trades_df)...")

    results = []
    for i, spec in enumerate(CANDIDATES, 1):
        cid = spec[0]
        print(f"  [{i:2d}/12] {cid} ...", end=" ", flush=True)
        try:
            r = _run_candidate(spec)
            results.append(r)
            print(f"n={r.n_trades:>5} PF={r.pf:.3f} daily_days={len(r.daily_pnl):>4}")
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    print(f"\nComputing structural similarity matrix + Pearson r matrix...")
    structural_matrix = {}
    pearson_matrix = {}
    pairs = []
    per_candidate = {r.cid: {"pairs": []} for r in results}

    for (i, a), (j, b) in combinations(enumerate(results, 1), 2):
        s = _structural_similarity(a, b)
        r, overlap = _pearson_corr(a, b)
        same_asset = (a.asset == b.asset)
        cls = _classify_pair(s, r, same_asset, overlap)
        structural_matrix[(j, i)] = s  # lower triangle uses (row, col) where row > col
        pearson_matrix[(j, i)] = r
        pair_entry = {
            "a": a.cid, "b": b.cid,
            "structural": s, "pearson": r,
            "overlap_days": overlap, "same_asset": same_asset,
            "classification": cls,
        }
        pairs.append(pair_entry)
        per_candidate[a.cid]["pairs"].append({"other": b.cid, **pair_entry})
        per_candidate[b.cid]["pairs"].append({"other": a.cid, **pair_entry})

    proposals = _propose_reclassification(per_candidate, pairs)

    generated_at = datetime.now()
    report = _render_report(results, structural_matrix, pearson_matrix,
                            pairs, per_candidate, proposals, generated_at)

    # Summary to stdout
    print(f"\n=== Summary ===")
    classifications = Counter(p["classification"] for p in pairs)
    for cls, count in classifications.most_common():
        print(f"  {cls}: {count}")
    n_dup_same = sum(1 for p in pairs
                     if p["classification"].startswith("DUPLICATE_EXPOSURE")
                     and "CROSS_ASSET" not in p["classification"])
    print(f"\nSame-asset DUPLICATE_EXPOSURE pairs: {n_dup_same}")
    print(f"Total pairs: {len(pairs)}")

    if args.dry_run:
        print(f"\n[DRY-RUN] preview (first 80 lines):\n")
        print("\n".join(report.splitlines()[:80]))
        return

    if not args.save:
        print(f"\n(use --save to write report + JSON, or --dry-run for preview)")
        return

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    md_path = REPORTS_DIR / f"{today}_correlation_matrix.md"
    json_path = REPORTS_DIR / f"{today}_correlation_matrix.json"
    md_path.write_text(report)
    json_payload = {
        "date": today,
        "generated": generated_at.isoformat(timespec="seconds"),
        "candidates": [
            {"cid": r.cid, "asset": r.asset, "entry": r.entry, "filter": r.filter,
             "exit": r.exit, "archetype": r.archetype, "n_trades": r.n_trades, "pf": r.pf,
             "daily_days": len(r.daily_pnl)}
            for r in results
        ],
        "pairs": pairs,
        "proposals": proposals,
        "thresholds": {
            "duplicate": THRESHOLD_DUPLICATE,
            "highly_correlated": THRESHOLD_HIGHLY,
            "related_variant": THRESHOLD_RELATED,
            "min_overlap_days_for_high_confidence": MIN_OVERLAP_DAYS,
        },
    }
    json_path.write_text(json.dumps(json_payload, indent=2, default=str))
    print(f"\n[WRITE] {md_path}")
    print(f"[WRITE] {json_path}")
    print(f"\n[SAFETY] Report-only. No registry mutation. Operator approval required for any reclassification.")


if __name__ == "__main__":
    main()
