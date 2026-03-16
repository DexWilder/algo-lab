#!/usr/bin/env python3
"""FQL Strategy Genome Classifier — Classify and map the full strategy universe.

Reads the enriched v3.0 registry and classifies every strategy across 9
behavioral dimensions. Produces a genome map that reveals overcrowding,
gaps, and overlap to guide future harvesting and factory priorities.

Dimensions:
  1. family          — strategy family (breakout, trend, MR, etc.)
  2. asset_class     — equity_index, metal, energy, rate, fx
  3. horizon         — intraday_5m, daily, swing, multi_day
  4. session         — morning, midday, afternoon, london, tokyo, us, all_day, daily_close
  5. direction       — long, short, both
  6. entry_type      — breakout, pullback, fade, compression, event, range
  7. exit_type       — atr_trail, target, time_stop, mean_revert, trend_reversal
  8. regime_tendency  — trending, ranging, all_regimes, vol_expansion
  9. portfolio_role  — core_earner, diversifier, stabilizer, gap_filler, rejected_pattern

Usage:
    python3 research/strategy_genome_classifier.py              # Full report
    python3 research/strategy_genome_classifier.py --json       # JSON output
    python3 research/strategy_genome_classifier.py --save       # Save genome map
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.asset_config import ASSETS
from research.utils.atomic_io import atomic_write_json

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = ROOT / "research" / "data" / "strategy_genome_map.json"

# ── Classification Rules ─────────────────────────────────────────────────────

ASSET_CLASS_MAP = {
    "MES": "equity_index", "MNQ": "equity_index", "M2K": "equity_index",
    "MGC": "metal", "SI": "metal", "HG": "metal",
    "MCL": "energy",
    "ZN": "rate", "ZF": "rate", "ZB": "rate",
    "6E": "fx", "6J": "fx", "6B": "fx",
    "MYM": "equity_index", "NG": "energy",
    "multi": "multi",
}

HORIZON_MAP = {
    "daily": "daily", "daily_close": "daily",
    "morning": "intraday", "midday": "intraday", "afternoon": "intraday",
    "close": "intraday", "all_day": "intraday", "custom": "intraday",
    "us_only": "intraday", "us_rth": "intraday",
    "london_open": "intraday", "london_ny": "intraday",
}

SESSION_NORMALIZE = {
    "morning": "morning", "midday": "midday", "afternoon": "afternoon",
    "close": "close", "all_day": "all_day", "custom": "all_day",
    "daily": "daily_close", "daily_close": "daily_close",
    "us_only": "us_session", "us_rth": "us_session",
    "london_open": "london", "london_ny": "london",
}

ENTRY_TYPE_MAP = {
    "breakout": "breakout", "vol_expansion": "compression",
    "trend": "pullback", "pullback": "pullback",
    "mean_reversion": "fade", "ict": "fade",
    "event_driven": "event", "momentum": "breakout",
}

REGIME_MAP = {
    "breakout": "trending", "vol_expansion": "vol_expansion",
    "trend": "trending", "pullback": "trending",
    "mean_reversion": "ranging", "ict": "all_regimes",
    "event_driven": "all_regimes", "momentum": "trending",
}


def classify_strategy(s):
    """Classify a single strategy across all 9 genome dimensions."""
    family = s.get("family", "unknown")
    asset = s.get("asset", "unknown")
    session = s.get("session", "all_day")
    direction = s.get("direction", "both")
    status = s.get("status", "unknown")

    genome = {
        "strategy_id": s["strategy_id"],
        "family": family,
        "asset_class": ASSET_CLASS_MAP.get(asset, "unknown"),
        "asset": asset,
        "horizon": HORIZON_MAP.get(session, "intraday"),
        "session": SESSION_NORMALIZE.get(session, session),
        "direction": direction,
        "entry_type": ENTRY_TYPE_MAP.get(family, "unknown"),
        "exit_type": _infer_exit_type(s),
        "regime_tendency": REGIME_MAP.get(family, "all_regimes"),
        "portfolio_role": _infer_portfolio_role(s),
        "status": status,
        "lifecycle_stage": s.get("lifecycle_stage", "unknown"),
    }
    return genome


def _infer_exit_type(s):
    """Infer exit type from strategy notes and family."""
    notes = (s.get("notes") or "") + " " + (s.get("rule_summary") or "")
    notes_lower = notes.lower()

    if "trail" in notes_lower or "atr trail" in notes_lower:
        return "atr_trail"
    if "time stop" in notes_lower or "time-stop" in notes_lower:
        return "time_stop"
    if "reversion" in notes_lower or "vwap" in notes_lower and "mean" in notes_lower:
        return "mean_revert"
    if "target" in notes_lower or "1:1" in notes_lower:
        return "fixed_target"
    if "trend reversal" in notes_lower or "ema cross" in notes_lower:
        return "trend_reversal"

    family = s.get("family", "")
    if family in ("mean_reversion",):
        return "mean_revert"
    if family in ("trend", "breakout"):
        return "atr_trail"
    return "mixed"


def _infer_portfolio_role(s):
    """Infer portfolio role from status and characteristics."""
    status = s.get("status", "")
    family = s.get("family", "")
    rejection = s.get("rejection_reason", "")

    if status == "rejected":
        return "rejected_pattern"
    if status == "core":
        return "core_earner"
    if status == "probation":
        if s.get("asset") in ("6J", "6E", "6B"):
            return "diversifier"
        if "daily" in (s.get("session") or ""):
            return "diversifier"
        return "probation_candidate"

    if family == "mean_reversion":
        return "stabilizer"
    if family == "event_driven":
        return "event_specialist"
    if family in ("breakout", "trend", "momentum"):
        return "growth_candidate"
    return "unclassified"


# ── Analysis ─────────────────────────────────────────────────────────────────

def analyze_genome(genomes):
    """Analyze the genome map for overcrowding and gaps."""
    # Only analyze non-rejected strategies for overcrowding
    active = [g for g in genomes if g["status"] not in ("rejected",)]

    analysis = {
        "overcrowded": [],
        "gaps": [],
        "overlap_warnings": [],
    }

    # Overcrowding: count active strategies per dimension combo
    combos = Counter()
    for g in active:
        key = (g["family"], g["asset_class"])
        combos[key] += 1

    for (fam, ac), count in combos.most_common():
        if count >= 4:
            strategies = [g["strategy_id"] for g in active
                          if g["family"] == fam and g["asset_class"] == ac]
            analysis["overcrowded"].append({
                "dimension": f"{fam} x {ac}",
                "count": count,
                "strategies": strategies,
            })

    # Session overcrowding
    session_counts = Counter(g["session"] for g in active)
    for sess, count in session_counts.most_common():
        if count >= 6 and sess != "all_day":
            analysis["overcrowded"].append({
                "dimension": f"session: {sess}",
                "count": count,
                "strategies": [g["strategy_id"] for g in active if g["session"] == sess],
            })

    # Gaps: what asset classes have < 2 active strategies?
    active_non_idea = [g for g in active if g["status"] not in ("idea",)]
    asset_class_counts = Counter(g["asset_class"] for g in active_non_idea)
    for ac in ["equity_index", "metal", "energy", "rate", "fx"]:
        count = asset_class_counts.get(ac, 0)
        if count < 2:
            analysis["gaps"].append({
                "dimension": f"asset_class: {ac}",
                "active_strategies": count,
                "note": f"Only {count} active strategy(s) in {ac}",
            })

    # Horizon gaps
    horizon_counts = Counter(g["horizon"] for g in active_non_idea)
    if horizon_counts.get("daily", 0) < 2:
        analysis["gaps"].append({
            "dimension": "horizon: daily",
            "active_strategies": horizon_counts.get("daily", 0),
            "note": "Daily-bar strategies underrepresented",
        })

    # Direction gaps
    direction_counts = Counter(g["direction"] for g in active_non_idea)
    if direction_counts.get("short", 0) < 3:
        analysis["gaps"].append({
            "dimension": "direction: short-only",
            "active_strategies": direction_counts.get("short", 0),
            "note": "Short-only strategies underrepresented",
        })

    # Regime tendency gaps
    regime_counts = Counter(g["regime_tendency"] for g in active_non_idea)
    if regime_counts.get("ranging", 0) < 2:
        analysis["gaps"].append({
            "dimension": "regime: ranging",
            "active_strategies": regime_counts.get("ranging", 0),
            "note": "Ranging-market strategies underrepresented",
        })

    # Overlap warnings: same asset + same session + same direction
    seen = defaultdict(list)
    for g in active_non_idea:
        key = (g["asset"], g["session"], g["direction"])
        seen[key].append(g["strategy_id"])
    for key, sids in seen.items():
        if len(sids) >= 2:
            analysis["overlap_warnings"].append({
                "key": f"{key[0]} / {key[1]} / {key[2]}",
                "strategies": sids,
                "note": f"{len(sids)} strategies compete for same slot",
            })

    return analysis


# ── Report ───────────────────────────────────────────────────────────────────

def print_report(genomes, analysis):
    """Print formatted genome map report."""
    W = 70
    print()
    print("=" * W)
    print("  FQL STRATEGY GENOME MAP")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    # Distribution summaries
    active = [g for g in genomes if g["status"] not in ("rejected",)]

    print(f"\n  UNIVERSE: {len(genomes)} total, {len(active)} active (non-rejected)")
    print(f"  {'-' * (W - 4)}")

    for dim in ["family", "asset_class", "horizon", "session", "direction",
                "entry_type", "regime_tendency", "portfolio_role"]:
        counts = Counter(g[dim] for g in active)
        top = counts.most_common(5)
        vals = ", ".join(f"{v}:{c}" for v, c in top)
        print(f"  {dim:<20s} {vals}")

    # Overcrowded
    if analysis["overcrowded"]:
        print(f"\n  OVERCROWDED AREAS")
        print(f"  {'-' * (W - 4)}")
        for item in analysis["overcrowded"]:
            print(f"  !! {item['dimension']}: {item['count']} strategies")
            for sid in item["strategies"][:5]:
                print(f"       - {sid}")

    # Gaps
    if analysis["gaps"]:
        print(f"\n  GAPS (underrepresented)")
        print(f"  {'-' * (W - 4)}")
        for gap in analysis["gaps"]:
            print(f"  -- {gap['dimension']}: {gap['active_strategies']} active — {gap['note']}")

    # Overlap warnings
    if analysis["overlap_warnings"]:
        print(f"\n  OVERLAP WARNINGS")
        print(f"  {'-' * (W - 4)}")
        for warn in analysis["overlap_warnings"]:
            print(f"  ~~ {warn['key']}: {', '.join(warn['strategies'])}")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL Strategy Genome Classifier")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    reg = json.load(open(REGISTRY_PATH))
    strategies = reg["strategies"]

    genomes = [classify_strategy(s) for s in strategies]
    analysis = analyze_genome(genomes)

    output = {
        "generated": datetime.now().isoformat(),
        "total_strategies": len(genomes),
        "genomes": genomes,
        "analysis": analysis,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print_report(genomes, analysis)

    if args.save:
        atomic_write_json(OUTPUT_PATH, output)
        print(f"\n  Genome map saved: {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
