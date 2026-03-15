#!/usr/bin/env python3
"""
FQL Auto-Report Generator
===========================
Generates daily and weekly research summaries from registry, queue, and validation results.

Usage:
    python3 research/auto_report.py                # Daily report
    python3 research/auto_report.py --weekly       # Weekly summary
    python3 research/auto_report.py --save         # Save report to file
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
QUEUE_PATH = ROOT / "research" / "data" / "roadmap_queue.json"
HARVEST_PATH = ROOT / "research" / "data" / "harvest_results.json"
REPORTS_DIR = ROOT / "research" / "reports"


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def generate_daily_report():
    """Generate daily research status report."""
    registry = load_json(REGISTRY_PATH)
    queue = load_json(QUEUE_PATH)
    harvest = load_json(HARVEST_PATH)

    now = datetime.now()
    report = []
    report.append("=" * 70)
    report.append(f"  FQL DAILY RESEARCH REPORT")
    report.append(f"  Date: {now.strftime('%Y-%m-%d %H:%M')}")
    report.append("=" * 70)

    # Registry status
    if registry:
        strategies = registry["strategies"]
        by_status = Counter(s["status"] for s in strategies)
        report.append(f"\n  REGISTRY STATUS ({len(strategies)} total)")
        report.append("  " + "-" * 50)
        for status in ["core", "probation", "testing", "idea", "rejected"]:
            if by_status.get(status, 0) > 0:
                report.append(f"    {status:12s}  {by_status[status]}")

    # Queue status
    if queue:
        tasks = queue["tasks"]
        by_status = Counter(t["status"] for t in tasks)
        report.append(f"\n  ROADMAP QUEUE ({len(tasks)} tasks)")
        report.append("  " + "-" * 50)
        for status in ["in_progress", "completed", "queued", "monitoring", "blocked"]:
            count = by_status.get(status, 0)
            if count > 0:
                report.append(f"    {status:15s}  {count}")

        # Show completed tasks (recent)
        completed = [t for t in tasks if t["status"] == "completed"]
        if completed:
            report.append(f"\n  RECENTLY COMPLETED:")
            for t in completed:
                report.append(f"    [{t['id']}] {t['title']}")
                if t.get("result"):
                    report.append(f"           → {t['result'][:70]}")

        # Show in-progress
        in_progress = [t for t in tasks if t["status"] == "in_progress"]
        if in_progress:
            report.append(f"\n  IN PROGRESS:")
            for t in in_progress:
                report.append(f"    [{t['id']}] {t['title']}")

        # Show next up
        queued = sorted([t for t in tasks if t["status"] == "queued"],
                       key=lambda t: t.get("priority", 99))
        if queued:
            report.append(f"\n  NEXT UP (top 5):")
            for t in queued[:5]:
                report.append(f"    [P{t.get('priority', '?')}] {t['title']}")

    # Harvest results
    if harvest:
        passed = harvest.get("summary", {}).get("passed", [])
        failed_count = harvest.get("summary", {}).get("failed_count", 0)
        report.append(f"\n  LATEST HARVEST VALIDATION")
        report.append("  " + "-" * 50)
        report.append(f"    Generated: {harvest.get('_generated', 'unknown')}")
        report.append(f"    Passed gate: {len(passed)}")
        report.append(f"    Failed: {failed_count}")
        if passed:
            report.append(f"    Winners:")
            for p in passed:
                report.append(f"      + {p}")

    # Walk-forward matrix results
    wf_files = list((ROOT / "research" / "data").glob("wf_matrix_*.json"))
    if wf_files:
        report.append(f"\n  WALK-FORWARD MATRIX RESULTS")
        report.append("  " + "-" * 50)
        for wf_file in sorted(wf_files):
            wf = load_json(wf_file)
            if wf:
                sc = wf.get("scorecard", {}).get("overall", {})
                report.append(f"    {wf['strategy']} {wf['asset']}-{wf['mode']}:  "
                            f"Score={sc.get('matrix_score', '?')}/10  "
                            f"→ {sc.get('recommendation', '?')}")

    # Portfolio gaps
    report.append(f"\n  OPEN PORTFOLIO GAPS")
    report.append("  " + "-" * 50)
    if registry:
        active = [s for s in registry["strategies"] if s["status"] in ("core", "probation")]
        active_families = set(s["family"] for s in active)
        target_families = {"trend", "pullback", "breakout", "mean_reversion", "momentum",
                          "vol_expansion", "event_driven"}
        missing = target_families - active_families
        report.append(f"    Missing families: {', '.join(sorted(missing)) or 'None'}")

        active_combos = set((s["asset"], s["direction"]) for s in active)
        missing_combos = []
        for asset in ["MNQ", "MES", "MGC", "M2K", "MCL"]:
            for d in ["long", "short"]:
                if (asset, d) not in active_combos:
                    missing_combos.append(f"{asset}-{d}")
        report.append(f"    Missing combos: {', '.join(missing_combos[:6])}")

    report.append("")
    report.append("=" * 70)

    return "\n".join(report)


def generate_weekly_report():
    """Generate weekly research summary."""
    daily = generate_daily_report()

    # Add weekly-specific sections
    extra = []
    extra.append("")
    extra.append("=" * 70)
    extra.append("  WEEKLY RESEARCH SUMMARY")
    extra.append("=" * 70)

    registry = load_json(REGISTRY_PATH)
    if registry:
        strategies = registry["strategies"]
        # Conversion funnel
        tested = [s for s in strategies if s["status"] in ("core", "probation", "rejected")]
        promoted = [s for s in strategies if s["status"] in ("core", "probation")]
        rejected = [s for s in strategies if s["status"] == "rejected"]
        ideas = [s for s in strategies if s["status"] == "idea"]

        extra.append(f"\n  CONVERSION FUNNEL")
        extra.append("  " + "-" * 50)
        extra.append(f"    Ideas in registry:       {len(ideas)}")
        extra.append(f"    Tested (any result):     {len(tested)}")
        extra.append(f"    Promoted:                {len(promoted)}")
        extra.append(f"    Rejected:                {len(rejected)}")
        if tested:
            extra.append(f"    Promotion rate:          {len(promoted)/len(tested)*100:.0f}%")

        # Family coverage
        active = [s for s in strategies if s["status"] in ("core", "probation")]
        extra.append(f"\n  FAMILY COVERAGE (active strategies)")
        extra.append("  " + "-" * 50)
        families = Counter(s["family"] for s in active)
        for family, count in sorted(families.items()):
            extra.append(f"    {family:20s}  {count}")

        # Probation board
        probation = [s for s in strategies if s["status"] == "probation"]
        if probation:
            extra.append(f"\n  PROBATION BOARD ({len(probation)} strategies)")
            extra.append("  " + "-" * 50)
            for s in probation:
                score = s.get("validation_score", "?")
                stability = s.get("parameter_stability", "?")
                extra.append(f"    {s['strategy_id']:30s}  score={score}  stability={stability}%")

    # Recommendations
    extra.append(f"\n  RECOMMENDED NEXT PRIORITIES")
    extra.append("  " + "-" * 50)

    queue = load_json(QUEUE_PATH)
    if queue:
        queued = sorted([t for t in queue["tasks"] if t["status"] == "queued"],
                       key=lambda t: t.get("priority", 99))
        for t in queued[:5]:
            extra.append(f"    [P{t.get('priority', '?')}] {t['title']}")
            if t.get("next_action"):
                extra.append(f"           → {t['next_action']}")

    extra.append("")
    extra.append("=" * 70)

    return daily + "\n" + "\n".join(extra)


def main():
    weekly = "--weekly" in sys.argv
    save = "--save" in sys.argv

    if weekly:
        report = generate_weekly_report()
    else:
        report = generate_daily_report()

    print(report)

    if save:
        REPORTS_DIR.mkdir(exist_ok=True)
        now = datetime.now()
        kind = "weekly" if weekly else "daily"
        filename = f"fql_report_{kind}_{now.strftime('%Y%m%d')}.txt"
        path = REPORTS_DIR / filename
        with open(path, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {path}")


if __name__ == "__main__":
    main()
