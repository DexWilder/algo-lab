#!/usr/bin/env python3
"""
FQL Strategy Harvest Scheduler
===============================
Runs the weekly strategy harvest cycle:
  1. Gap analysis — identify what the portfolio needs
  2. Candidate scan — surface strategies from registry that fill gaps
  3. Validation queue — prioritize and queue candidates for testing
  4. Registry update — update statuses based on results

Usage:
    python3 research/harvest_scheduler.py                # Run full cycle
    python3 research/harvest_scheduler.py --gap-report   # Gap analysis only
    python3 research/harvest_scheduler.py --queue        # Show validation queue
    python3 research/harvest_scheduler.py --stats        # Research stats

Weekly rhythm:
    Monday:    Gap analysis + candidate surfacing
    Tuesday:   Validation runs (batch)
    Wednesday: Results review + registry update
    Thursday:  New idea harvesting (TradingView, papers, forums)
    Friday:    Portfolio impact assessment
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
QUEUE_PATH = ROOT / "research" / "data" / "validation_queue.json"


def load_registry():
    with open(REGISTRY_PATH) as f:
        return json.load(f)["strategies"]


def gap_analysis():
    """Identify what the portfolio needs most urgently."""
    strategies = load_registry()
    active = [s for s in strategies if s["status"] in ("core", "probation")]

    gaps = {
        "missing_families": [],
        "missing_assets": [],
        "missing_sessions": [],
        "missing_combos": [],
        "direction_imbalance": None,
        "priority_candidates": [],
    }

    # Family gaps
    active_families = set(s["family"] for s in active)
    target_families = {"trend", "pullback", "breakout", "mean_reversion", "momentum",
                       "vol_expansion", "event_driven"}
    gaps["missing_families"] = sorted(target_families - active_families)

    # Asset gaps
    active_assets = set(s["asset"] for s in active)
    target_assets = {"MNQ", "MES", "MGC", "M2K", "MCL"}
    gaps["missing_assets"] = sorted(target_assets - active_assets - {"multi"})

    # Session gaps
    active_sessions = set(s.get("session") for s in active) - {None}
    target_sessions = {"morning", "midday", "afternoon", "close"}
    gaps["missing_sessions"] = sorted(target_sessions - active_sessions)

    # Direction
    longs = sum(1 for s in active if s["direction"] == "long")
    shorts = sum(1 for s in active if s["direction"] == "short")
    if abs(longs - shorts) > 2:
        gaps["direction_imbalance"] = f"{longs} long vs {shorts} short"

    # Asset-direction combos
    active_combos = set((s["asset"], s["direction"]) for s in active)
    for asset in ["MNQ", "MES", "MGC", "M2K", "MCL"]:
        for direction in ["long", "short"]:
            if (asset, direction) not in active_combos:
                gaps["missing_combos"].append(f"{asset}-{direction}")

    # Score ideas by gap fill potential
    ideas = [s for s in strategies if s["status"] == "idea"]
    for idea in ideas:
        score = 0
        fills = []
        if idea["family"] in gaps["missing_families"]:
            score += 3
            fills.append(f"family:{idea['family']}")
        if idea["asset"] in gaps["missing_assets"]:
            score += 2
            fills.append(f"asset:{idea['asset']}")
        if idea.get("session") in gaps["missing_sessions"]:
            score += 2
            fills.append(f"session:{idea.get('session')}")
        if f"{idea['asset']}-{idea['direction']}" in gaps["missing_combos"]:
            score += 1
            fills.append(f"combo:{idea['asset']}-{idea['direction']}")
        # Bonus for having code ready
        if idea.get("strategy_name"):
            score += 1
            fills.append("has_code")

        if score > 0:
            gaps["priority_candidates"].append({
                "id": idea["strategy_id"],
                "score": score,
                "fills": fills,
                "family": idea["family"],
                "asset": idea["asset"],
            })

    gaps["priority_candidates"].sort(key=lambda x: -x["score"])
    return gaps


def build_validation_queue():
    """Build prioritized queue of candidates to test next."""
    gaps = gap_analysis()
    strategies = load_registry()
    ideas = [s for s in strategies if s["status"] == "idea"]

    queue = []
    for candidate in gaps["priority_candidates"]:
        idea = next((s for s in ideas if s["strategy_id"] == candidate["id"]), None)
        if idea:
            queue.append({
                "strategy_id": idea["strategy_id"],
                "strategy_name": idea.get("strategy_name"),
                "family": idea["family"],
                "asset": idea["asset"],
                "direction": idea["direction"],
                "gap_score": candidate["score"],
                "fills": candidate["fills"],
                "has_code": bool(idea.get("strategy_name")),
                "rule_summary": idea["rule_summary"],
                "queued_date": datetime.now().strftime("%Y-%m-%d"),
            })

    # Save queue
    queue_data = {
        "_generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "_gaps": {
            "missing_families": gaps["missing_families"],
            "missing_assets": gaps["missing_assets"],
            "missing_sessions": gaps["missing_sessions"],
            "direction_imbalance": gaps["direction_imbalance"],
        },
        "queue": queue,
    }

    with open(QUEUE_PATH, "w") as f:
        json.dump(queue_data, f, indent=2)

    return queue


def print_gap_report():
    """Print formatted gap analysis."""
    gaps = gap_analysis()

    print("=" * 70)
    print("  FQL HARVEST GAP REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    print(f"\n  MISSING FAMILIES: {', '.join(gaps['missing_families']) or 'None'}")
    print(f"  MISSING ASSETS:   {', '.join(gaps['missing_assets']) or 'None'}")
    print(f"  MISSING SESSIONS: {', '.join(gaps['missing_sessions']) or 'None'}")
    if gaps["direction_imbalance"]:
        print(f"  DIRECTION:        {gaps['direction_imbalance']}")
    print(f"  MISSING COMBOS:   {', '.join(gaps['missing_combos'][:8])}")

    print(f"\n  TOP CANDIDATES (by gap-fill score)")
    print("  " + "-" * 55)
    for c in gaps["priority_candidates"][:15]:
        code = "*" if "has_code" in c["fills"] else " "
        fills_str = ", ".join(f for f in c["fills"] if f != "has_code")
        print(f"  {code} {c['id']:30s}  score={c['score']}  fills: {fills_str}")

    print(f"\n  * = code already exists in strategies/")
    print("=" * 70)


def print_queue():
    """Print current validation queue."""
    queue = build_validation_queue()

    print("=" * 70)
    print("  FQL VALIDATION QUEUE")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    ready = [q for q in queue if q["has_code"]]
    needs_code = [q for q in queue if not q["has_code"]]

    print(f"\n  READY TO VALIDATE ({len(ready)})")
    print("  " + "-" * 55)
    for q in ready:
        print(f"  [{q['gap_score']}] {q['strategy_id']:30s}  {q['asset']:6s}  {q['family']}")
        print(f"      {q['rule_summary'][:70]}")

    print(f"\n  NEEDS CODE FIRST ({len(needs_code)})")
    print("  " + "-" * 55)
    for q in needs_code:
        print(f"  [{q['gap_score']}] {q['strategy_id']:30s}  {q['asset']:6s}  {q['family']}")
        print(f"      {q['rule_summary'][:70]}")

    print()
    print("=" * 70)


def print_stats():
    """Print research statistics."""
    strategies = load_registry()

    print("=" * 70)
    print("  FQL RESEARCH STATISTICS")
    print(f"  As of: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 70)

    total = len(strategies)
    by_status = Counter(s["status"] for s in strategies)
    by_family = Counter(s["family"] for s in strategies)
    by_source = Counter(s.get("source", "unknown") for s in strategies)

    print(f"\n  TOTAL STRATEGIES IN REGISTRY: {total}")
    print()
    print(f"  BY STATUS:")
    for status, count in sorted(by_status.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "#" * int(pct / 2)
        print(f"    {status:12s}  {count:3d}  ({pct:4.1f}%)  {bar}")

    print(f"\n  BY FAMILY:")
    for family, count in sorted(by_family.items(), key=lambda x: -x[1]):
        print(f"    {family:20s}  {count}")

    print(f"\n  BY SOURCE:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"    {source:35s}  {count}")

    # Conversion rates
    tested = [s for s in strategies if s["status"] in ("core", "probation", "rejected")]
    promoted = [s for s in strategies if s["status"] in ("core", "probation")]
    rejected = [s for s in strategies if s["status"] == "rejected"]
    if tested:
        print(f"\n  CONVERSION FUNNEL:")
        print(f"    Ideas in registry:       {by_status.get('idea', 0)}")
        print(f"    Tested (any result):     {len(tested)}")
        print(f"    Promoted (core/probation): {len(promoted)}")
        print(f"    Rejected:                {len(rejected)}")
        print(f"    Promotion rate:          {len(promoted)/len(tested)*100:.0f}%")

    print()
    print("=" * 70)


def main():
    if "--gap-report" in sys.argv:
        print_gap_report()
    elif "--queue" in sys.argv:
        print_queue()
    elif "--stats" in sys.argv:
        print_stats()
    else:
        # Full cycle
        print_gap_report()
        print()
        print_queue()
        print()
        print_stats()


if __name__ == "__main__":
    main()
