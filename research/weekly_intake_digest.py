#!/usr/bin/env python3
"""FQL Weekly Intake Intelligence Digest — Advisory report only.

Summarizes the state of the idea pipeline, harvest results, and
conversion queue. Read-only — does not modify registry or live logic.

Usage:
    python3 research/weekly_intake_digest.py
    python3 research/weekly_intake_digest.py --save
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json

DATA_DIR = ROOT / "research" / "data"
REPORTS_DIR = ROOT / "research" / "reports"

# Conversion queue (manually maintained priority order)
CONVERSION_QUEUE = [
    {"id": "Treasury-CPI-Day-Long", "factor": "EVENT", "priority": 1, "blocked": False},
    {"id": "TV-Larry-Oops-Gap-Reversal", "factor": "STRUCTURAL", "priority": 2, "blocked": False},
    {"id": "OPEX-Week-Effect", "factor": "EVENT", "priority": 3, "blocked": False},
    {"id": "TV-Session-Gap-Fill", "factor": "STRUCTURAL", "priority": 4, "blocked": False},
    {"id": "Treasury-12M-TSM", "factor": "CARRY/MOMENTUM", "priority": 5, "blocked": True,
     "blocker": "rates_data_backfill ($12.59)"},
]


def load_registry():
    reg_path = DATA_DIR / "strategy_registry.json"
    if not reg_path.exists():
        return []
    return json.load(open(reg_path)).get("strategies", [])


def load_manifest():
    manifest_path = DATA_DIR / "harvest_manifest.json"
    if not manifest_path.exists():
        return {"items": [], "stats": {}}
    return json.load(open(manifest_path))


def section_intake_summary(strategies, manifest):
    """Section 1: Intake pipeline summary."""
    statuses = Counter(s.get("status") for s in strategies)
    ideas = [s for s in strategies if s.get("status") == "idea"]

    # Source breakdown for ideas
    sources = Counter(s.get("source_category", "other") for s in ideas)

    # Factor breakdown for ideas
    factors = Counter()
    for s in ideas:
        tags = s.get("tags", [])
        for t in tags:
            if t in ("EVENT", "CARRY", "STRUCTURAL", "MOMENTUM", "VOLATILITY", "VALUE"):
                factors[t] += 1

    # Blocked count
    blocked = sum(1 for s in ideas if any("blocked" in t for t in s.get("tags", [])))

    # Manifest stats
    m_stats = manifest.get("stats", {})

    return {
        "total_strategies": len(strategies),
        "status_distribution": dict(statuses.most_common()),
        "total_ideas": len(ideas),
        "blocked_ideas": blocked,
        "actionable_ideas": len(ideas) - blocked,
        "idea_sources": dict(sources.most_common()),
        "idea_factors": dict(factors.most_common()),
        "manifest_total": m_stats.get("total", 0),
        "manifest_staged": m_stats.get("staged", 0),
        "manifest_logged": m_stats.get("logged", 0),
        "manifest_rejected": m_stats.get("rejected", 0),
    }


def section_family_representatives(strategies):
    """Section 2: Best representative idea per factor family."""
    ideas = [s for s in strategies if s.get("status") == "idea"]
    probation = [s for s in strategies if s.get("status") == "probation"]

    # Current probation factors
    probation_factors = set()
    for s in probation:
        tags = s.get("tags", [])
        for t in tags:
            if t in ("EVENT", "CARRY", "STRUCTURAL", "MOMENTUM", "VOLATILITY"):
                probation_factors.add(t)

    reps = {}
    # Find best idea per factor (highest priority)
    priority_map = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    for factor in ["EVENT", "CARRY", "STRUCTURAL", "VOLATILITY", "VALUE"]:
        candidates = [s for s in ideas if factor in s.get("tags", [])
                      and not any("blocked" in t for t in s.get("tags", []))]
        if candidates:
            best = min(candidates, key=lambda x: priority_map.get(x.get("review_priority", "LOW"), 2))
            reps[factor] = {
                "id": best["strategy_id"],
                "priority": best.get("review_priority", "?"),
                "in_probation": factor in probation_factors,
            }
        else:
            blocked_candidates = [s for s in ideas if factor in s.get("tags", [])]
            if blocked_candidates:
                reps[factor] = {
                    "id": blocked_candidates[0]["strategy_id"],
                    "priority": "BLOCKED",
                    "in_probation": factor in probation_factors,
                }
            else:
                reps[factor] = {"id": None, "priority": "NO_CANDIDATES", "in_probation": factor in probation_factors}

    return reps


def section_overlap_clusters(strategies):
    """Section 3: Ideas that overlap with each other or existing strategies."""
    ideas = [s for s in strategies if s.get("status") == "idea"]
    clusters = defaultdict(list)

    for s in ideas:
        key = (s.get("family", ""), s.get("asset", ""))
        clusters[key].append(s["strategy_id"])

    # Only report clusters with 2+ ideas
    overlaps = []
    for (fam, asset), sids in clusters.items():
        if len(sids) >= 2:
            overlaps.append({
                "family": fam,
                "asset": asset,
                "count": len(sids),
                "strategies": sids[:5],
            })

    return sorted(overlaps, key=lambda x: -x["count"])


def section_blocked_closest(strategies):
    """Section 4: Blocked ideas closest to becoming actionable."""
    ideas = [s for s in strategies if s.get("status") == "idea"]
    blocked = []

    for s in ideas:
        tags = s.get("tags", [])
        blockers = [t for t in tags if "blocked" in t or "needs_" in t]
        if blockers:
            blocked.append({
                "id": s["strategy_id"],
                "blockers": blockers,
                "priority": s.get("review_priority", "LOW"),
                "family": s.get("family", "?"),
            })

    # Sort: HIGH priority first, then by number of blockers (fewer = closer)
    priority_map = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(blocked, key=lambda x: (priority_map.get(x["priority"], 2), len(x["blockers"])))


def print_digest(intake, reps, queue, overlaps, blocked):
    W = 70
    print()
    print("=" * W)
    print("  FQL WEEKLY INTAKE INTELLIGENCE DIGEST")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    # 1. Intake Summary
    print(f"\n  1. INTAKE SUMMARY")
    print(f"  {'-' * (W-4)}")
    print(f"  Registry: {intake['total_strategies']} strategies")
    print(f"  Ideas: {intake['total_ideas']} ({intake['actionable_ideas']} actionable, {intake['blocked_ideas']} blocked)")
    print(f"  Status: {intake['status_distribution']}")
    print(f"  Sources: {intake['idea_sources']}")
    print(f"  Factors: {intake['idea_factors']}")
    print(f"  Manifest: {intake['manifest_total']} scanned, {intake['manifest_logged']} logged, {intake['manifest_rejected']} rejected")

    # 2. Family Representatives
    print(f"\n  2. BEST REPRESENTATIVE BY FACTOR")
    print(f"  {'-' * (W-4)}")
    for factor, rep in reps.items():
        in_prob = " (IN PROBATION)" if rep["in_probation"] else ""
        if rep["id"]:
            print(f"  {factor:<14s} {rep['id']:<40s} [{rep['priority']}]{in_prob}")
        else:
            print(f"  {factor:<14s} {'NO CANDIDATES':<40s}{in_prob}")

    # 3. Conversion Queue
    print(f"\n  3. NEXT 5 CONVERSION CANDIDATES")
    print(f"  {'-' * (W-4)}")
    for item in queue:
        blocked_str = f" (BLOCKED: {item['blocker']})" if item.get("blocked") else ""
        print(f"  #{item['priority']}  {item['id']:<40s} [{item['factor']}]{blocked_str}")

    # 4. Overlap Clusters
    if overlaps:
        print(f"\n  4. OVERLAP CLUSTERS (2+ ideas in same family/asset)")
        print(f"  {'-' * (W-4)}")
        for cl in overlaps[:5]:
            print(f"  {cl['family']}/{cl['asset']}: {cl['count']} ideas — {', '.join(cl['strategies'][:3])}")

    # 5. Closest Blocked Ideas
    print(f"\n  5. BLOCKED IDEAS CLOSEST TO ACTIONABLE")
    print(f"  {'-' * (W-4)}")
    for b in blocked[:5]:
        print(f"  {b['id']:<40s} [{b['priority']}] {', '.join(b['blockers'][:2])}")

    # 6. Recommended Next Step
    print(f"\n  6. RECOMMENDED NEXT STEP")
    print(f"  {'-' * (W-4)}")
    next_actionable = [q for q in queue if not q.get("blocked")]
    if next_actionable:
        nxt = next_actionable[0]
        print(f"  Next conversion: {nxt['id']} ({nxt['factor']})")
    else:
        print(f"  All queue items are blocked. Consider unlocking rates data backfill ($12.59).")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL Weekly Intake Intelligence Digest")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    strategies = load_registry()
    manifest = load_manifest()

    intake = section_intake_summary(strategies, manifest)
    reps = section_family_representatives(strategies)
    overlaps = section_overlap_clusters(strategies)
    blocked = section_blocked_closest(strategies)

    if args.json:
        report = {
            "generated": datetime.now().isoformat(),
            "intake": intake,
            "family_representatives": reps,
            "conversion_queue": CONVERSION_QUEUE,
            "overlap_clusters": overlaps,
            "blocked_closest": blocked,
        }
        print(json.dumps(report, indent=2, default=str))
    else:
        print_digest(intake, reps, CONVERSION_QUEUE, overlaps, blocked)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d")
        out = REPORTS_DIR / f"intake_digest_{ts}.json"
        report = {
            "generated": datetime.now().isoformat(),
            "intake": intake,
            "family_representatives": reps,
            "conversion_queue": CONVERSION_QUEUE,
            "overlap_clusters": overlaps,
            "blocked_closest": blocked[:10],
        }
        atomic_write_json(out, report)
        print(f"\n  Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
