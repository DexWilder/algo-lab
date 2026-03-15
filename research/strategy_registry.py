#!/usr/bin/env python3
"""
FQL Strategy Registry — Institutional Memory
=============================================
Central registry for ALL strategy ideas (core, probation, rejected, ideas).
Supports querying, gap analysis, and feeding the Strategy Factory.

Usage:
    python3 research/strategy_registry.py                  # Print full summary
    python3 research/strategy_registry.py --gaps           # Show portfolio gaps
    python3 research/strategy_registry.py --status core    # Filter by status
    python3 research/strategy_registry.py --family vol_expansion  # Filter by family
    python3 research/strategy_registry.py --asset M2K      # Filter by asset
    python3 research/strategy_registry.py --candidates     # Show testable candidates
"""

import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"


def load_registry():
    with open(REGISTRY_PATH) as f:
        data = json.load(f)
    return data["strategies"]


def add_strategy(entry: dict):
    """Add a new strategy to the registry. Deduplicates by strategy_id."""
    with open(REGISTRY_PATH) as f:
        data = json.load(f)

    existing_ids = {s["strategy_id"] for s in data["strategies"]}
    if entry["strategy_id"] in existing_ids:
        print(f"  SKIP: {entry['strategy_id']} already exists")
        return False

    data["strategies"].append(entry)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  ADDED: {entry['strategy_id']} ({entry['status']})")
    return True


def update_status(strategy_id: str, new_status: str, notes_append: str = None):
    """Update a strategy's status (and optionally append to notes)."""
    with open(REGISTRY_PATH) as f:
        data = json.load(f)

    for s in data["strategies"]:
        if s["strategy_id"] == strategy_id:
            old = s["status"]
            s["status"] = new_status
            if notes_append:
                s["notes"] = (s.get("notes") or "") + " " + notes_append
            with open(REGISTRY_PATH, "w") as f:
                json.dump(data, f, indent=2)
            print(f"  UPDATED: {strategy_id} — {old} → {new_status}")
            return True

    print(f"  NOT FOUND: {strategy_id}")
    return False


def print_summary(strategies, title="FQL STRATEGY REGISTRY"):
    """Print formatted registry summary."""
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)

    # Status breakdown
    status_counts = Counter(s["status"] for s in strategies)
    print(f"\n  STATUS BREAKDOWN ({len(strategies)} total)")
    print("  " + "-" * 40)
    for status in ["core", "probation", "testing", "idea", "rejected"]:
        count = status_counts.get(status, 0)
        if count > 0:
            names = [s["strategy_id"] for s in strategies if s["status"] == status]
            print(f"  {status.upper():12s} {count:3d}  {', '.join(names[:5])}")
            if len(names) > 5:
                print(f"  {'':12s}      + {len(names) - 5} more")

    # Family breakdown
    family_counts = Counter(s["family"] for s in strategies)
    print(f"\n  FAMILY COVERAGE")
    print("  " + "-" * 40)
    for family, count in sorted(family_counts.items(), key=lambda x: -x[1]):
        active = sum(1 for s in strategies if s["family"] == family and s["status"] in ("core", "probation"))
        ideas = sum(1 for s in strategies if s["family"] == family and s["status"] == "idea")
        rejected = sum(1 for s in strategies if s["family"] == family and s["status"] == "rejected")
        print(f"  {family:20s}  active={active}  ideas={ideas}  rejected={rejected}")

    # Asset breakdown
    asset_counts = Counter(s["asset"] for s in strategies if s["status"] in ("core", "probation", "idea"))
    print(f"\n  ASSET DISTRIBUTION (non-rejected)")
    print("  " + "-" * 40)
    for asset, count in sorted(asset_counts.items(), key=lambda x: -x[1]):
        print(f"  {asset:8s}  {count} strategies")

    # Session breakdown
    session_counts = Counter(s.get("session", "unknown") for s in strategies if s["status"] in ("core", "probation", "idea"))
    print(f"\n  SESSION DISTRIBUTION (non-rejected)")
    print("  " + "-" * 40)
    for session, count in sorted(session_counts.items(), key=lambda x: -x[1]):
        print(f"  {session:12s}  {count} strategies")

    # Direction balance
    dirs = Counter(s["direction"] for s in strategies if s["status"] in ("core", "probation"))
    print(f"\n  DIRECTION BALANCE (active)")
    print("  " + "-" * 40)
    for d, c in sorted(dirs.items()):
        print(f"  {d:8s}  {c}")

    print()
    print("=" * 70)


def print_gaps(strategies):
    """Analyze and print portfolio gaps that need filling."""
    active = [s for s in strategies if s["status"] in ("core", "probation")]
    ideas = [s for s in strategies if s["status"] == "idea"]

    print("=" * 70)
    print("  FQL PORTFOLIO GAP ANALYSIS")
    print("=" * 70)

    # Family gaps
    active_families = set(s["family"] for s in active)
    all_families = {"trend", "pullback", "breakout", "mean_reversion", "momentum",
                    "vol_expansion", "event_driven", "ict", "microstructure"}
    missing_families = all_families - active_families
    print(f"\n  MISSING FAMILIES: {', '.join(sorted(missing_families)) or 'None'}")

    # Asset gaps
    active_assets = set(s["asset"] for s in active)
    target_assets = {"MNQ", "MES", "MGC", "M2K", "MCL", "MYM", "NG"}
    missing_assets = target_assets - active_assets - {"multi"}
    print(f"  MISSING ASSETS: {', '.join(sorted(missing_assets)) or 'None'}")

    # Session gaps
    active_sessions = set(s.get("session") for s in active)
    target_sessions = {"morning", "midday", "afternoon", "close", "all_day", "daily"}
    missing_sessions = target_sessions - active_sessions - {None}
    print(f"  MISSING SESSIONS: {', '.join(sorted(missing_sessions)) or 'None'}")

    # Direction imbalance
    longs = sum(1 for s in active if s["direction"] == "long")
    shorts = sum(1 for s in active if s["direction"] == "short")
    print(f"  DIRECTION: {longs} long vs {shorts} short")

    # Asset-direction combos
    active_combos = set((s["asset"], s["direction"]) for s in active)
    missing_combos = []
    for asset in ["MNQ", "MES", "MGC", "M2K", "MCL"]:
        for direction in ["long", "short"]:
            if (asset, direction) not in active_combos:
                missing_combos.append(f"{asset}-{direction}")
    print(f"  MISSING ASSET/DIRECTION: {', '.join(missing_combos)}")

    # Ideas that fill gaps
    print(f"\n  IDEAS THAT FILL GAPS")
    print("  " + "-" * 40)
    for idea in ideas:
        fills = []
        if idea["family"] in missing_families:
            fills.append(f"family:{idea['family']}")
        if idea["asset"] in missing_assets:
            fills.append(f"asset:{idea['asset']}")
        if idea.get("session") in missing_sessions:
            fills.append(f"session:{idea.get('session')}")
        if (idea["asset"], idea["direction"]) not in active_combos and idea["asset"] != "multi":
            fills.append(f"combo:{idea['asset']}-{idea['direction']}")
        if fills:
            print(f"  {idea['strategy_id']:30s}  fills: {', '.join(fills)}")

    print()
    print("=" * 70)


def print_candidates(strategies):
    """Show strategies ready for testing."""
    candidates = [s for s in strategies if s["status"] == "idea"]

    print("=" * 70)
    print("  FQL TESTABLE CANDIDATES")
    print("=" * 70)

    # Separate: has code vs needs code
    has_code = [s for s in candidates if s.get("strategy_name")]
    needs_code = [s for s in candidates if not s.get("strategy_name")]

    print(f"\n  READY TO TEST (code exists in strategies/)")
    print("  " + "-" * 50)
    for s in has_code:
        print(f"  {s['strategy_id']:30s}  {s['family']:18s}  {s['asset']:6s}  strategies/{s['strategy_name']}/")

    print(f"\n  NEEDS CODE FIRST")
    print("  " + "-" * 50)
    for s in needs_code:
        source = s.get("source", "unknown")
        print(f"  {s['strategy_id']:30s}  {s['family']:18s}  {s['asset']:6s}  src: {source}")

    print()
    print("=" * 70)


def main():
    strategies = load_registry()

    if "--gaps" in sys.argv:
        print_gaps(strategies)
    elif "--candidates" in sys.argv:
        print_candidates(strategies)
    elif "--status" in sys.argv:
        idx = sys.argv.index("--status")
        status = sys.argv[idx + 1]
        filtered = [s for s in strategies if s["status"] == status]
        print_summary(filtered, title=f"FQL REGISTRY — {status.upper()}")
    elif "--family" in sys.argv:
        idx = sys.argv.index("--family")
        family = sys.argv[idx + 1]
        filtered = [s for s in strategies if s["family"] == family]
        print_summary(filtered, title=f"FQL REGISTRY — {family.upper()}")
    elif "--asset" in sys.argv:
        idx = sys.argv.index("--asset")
        asset = sys.argv[idx + 1]
        filtered = [s for s in strategies if s["asset"] == asset]
        print_summary(filtered, title=f"FQL REGISTRY — {asset}")
    else:
        print_summary(strategies)

    return 0


if __name__ == "__main__":
    sys.exit(main())
