#!/usr/bin/env python3
"""Harvest Note Ranker — prioritize the 97 unconverted notes for processing.

Ranks by:
  1. Priority gap (Energy / Tail / Time-of-day / Carry-Value)
  2. Differentiation from current portfolio (high vs duplicate)
  3. Testability (high = ready to convert, low = blocked)
  4. Asset availability (we have data?)

Outputs ranked tranche files for the next discovery wave.
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARVEST_DIR = Path.home() / "openclaw-intake" / "inbox" / "harvest"
REVIEWED_DIR = Path.home() / "openclaw-intake" / "reviewed"
OUTPUT_PATH = ROOT / "research" / "data" / "harvest_ranking.json"

# Priority gaps (in order)
PRIORITY_GAPS = {
    "energy": 100,
    "tail": 90,
    "time_of_day": 80,
    "carry": 70,
    "value": 65,
    "vol": 60,
    "diversification": 50,
}

# Available assets (from data/processed/)
AVAILABLE_ASSETS = {"6B", "6E", "6J", "ES", "M2K", "MCL", "MES", "MGC", "MNQ", "MYM", "ZB", "ZF", "ZN"}


def parse_note(path):
    """Extract structured fields from a harvest note."""
    text = path.read_text()
    fields = {"file": path.name, "raw_text": text}

    # Standard fields
    for key in ["title", "source URL", "author", "target futures instruments",
                "summary", "factor fit", "distinctness from current portfolio",
                "testability", "blocker", "parent family", "verdict",
                "component_type"]:
        # Match "- key: value" lines
        pattern = rf"^- {re.escape(key)}:\s*(.+?)$"
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            fields[key.replace(" ", "_")] = m.group(1).strip()

    return fields


def score_note(fields):
    """Score a note for processing priority."""
    score = 0
    reasons = []
    text_lower = (fields.get("title", "") + " " +
                  fields.get("summary", "") + " " +
                  fields.get("factor_fit", "") + " " +
                  fields.get("parent_family", "")).lower()

    # ── Gap priority ──
    gap_score = 0
    gaps_matched = []
    if any(w in text_lower for w in ["energy", "crude", "oil", "natural gas", "wti", " ng "]):
        gap_score = max(gap_score, PRIORITY_GAPS["energy"])
        gaps_matched.append("energy")
    if any(w in text_lower for w in ["tail", "vol expansion", "convex", "vix", "volatility breakout"]):
        gap_score = max(gap_score, PRIORITY_GAPS["tail"])
        gaps_matched.append("tail")
    if any(w in text_lower for w in ["overnight", "session", "afternoon", "morning", "asia", "london", "asian", "tokyo", "asia session", "european", "european session"]):
        gap_score = max(gap_score, PRIORITY_GAPS["time_of_day"])
        gaps_matched.append("time_of_day")
    if "carry" in text_lower or "term structure" in text_lower or "rolldown" in text_lower:
        gap_score = max(gap_score, PRIORITY_GAPS["carry"])
        gaps_matched.append("carry")
    if "value" in text_lower or "ppp" in text_lower or "fair value" in text_lower:
        gap_score = max(gap_score, PRIORITY_GAPS["value"])
        gaps_matched.append("value")
    if "vol target" in text_lower or "vol manage" in text_lower:
        gap_score = max(gap_score, PRIORITY_GAPS["vol"])
        gaps_matched.append("vol")

    score += gap_score
    if gaps_matched:
        reasons.append(f"gaps={'+'.join(gaps_matched)}({gap_score})")

    # ── Distinctness ──
    dist = fields.get("distinctness_from_current_portfolio", "").lower()
    if dist.startswith("high"):
        score += 30
        reasons.append("high_distinct(+30)")
    elif dist.startswith("medium"):
        score += 15
        reasons.append("med_distinct(+15)")
    elif dist.startswith("low"):
        score -= 10
        reasons.append("low_distinct(-10)")

    # ── Testability ──
    test = fields.get("testability", "").lower()
    if test.startswith("high"):
        score += 40
        reasons.append("high_test(+40)")
    elif test.startswith("medium"):
        score += 20
        reasons.append("med_test(+20)")
    elif test.startswith("low"):
        score -= 20
        reasons.append("low_test(-20)")

    # ── Blocker penalty ──
    blocker = fields.get("blocker", "").lower()
    if blocker and blocker not in ("none", "no", "n/a", ""):
        score -= 30
        reasons.append(f"blocked(-30)")

    # ── Verdict ──
    verdict = fields.get("verdict", "").lower()
    if "accept" in verdict and "blocked" not in verdict:
        score += 20
        reasons.append("verdict_accept(+20)")
    elif "blocked" in verdict:
        score += 5  # still useful but lower
        reasons.append("verdict_blocked(+5)")
    elif "reject" in verdict:
        score -= 50
        reasons.append("verdict_reject(-50)")

    # ── Asset availability ──
    targets = fields.get("target_futures_instruments", "")
    asset_tokens = re.findall(r"\b([A-Z]{1,3}\d?)\b", targets)
    has_data = any(a in AVAILABLE_ASSETS or
                   a.replace("/", "") in AVAILABLE_ASSETS
                   for a in asset_tokens)
    # Common abbreviations
    if "crude" in text_lower or "oil" in text_lower or "wti" in targets.lower():
        has_data = has_data or "MCL" in AVAILABLE_ASSETS
    if "gold" in text_lower:
        has_data = has_data or "MGC" in AVAILABLE_ASSETS
    if "treasury" in text_lower or "rates" in text_lower:
        has_data = has_data or "ZN" in AVAILABLE_ASSETS

    if has_data:
        score += 10
        reasons.append("data_avail(+10)")
    else:
        score -= 20
        reasons.append("no_data(-20)")

    return score, reasons


def main():
    notes = []
    for d in [HARVEST_DIR, REVIEWED_DIR]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.md")):
            try:
                fields = parse_note(f)
                score, reasons = score_note(fields)
                notes.append({
                    "file": fields["file"],
                    "title": fields.get("title", "")[:80],
                    "factor": fields.get("factor_fit", "")[:30],
                    "family": fields.get("parent_family", "")[:30],
                    "verdict": fields.get("verdict", "")[:30],
                    "blocker": fields.get("blocker", "")[:50],
                    "testability": fields.get("testability", "")[:30],
                    "score": score,
                    "reasons": reasons,
                })
            except Exception as e:
                print(f"  Error parsing {f.name}: {e}")

    # Sort by score descending
    notes.sort(key=lambda n: -n["score"])

    # Save
    with open(OUTPUT_PATH, "w") as f:
        json.dump(notes, f, indent=2)

    # Print ranked summary
    print(f"=== Ranked {len(notes)} harvest notes ===")
    print()
    print(f"  {'Score':>6s} {'File':<60s} {'Factor':15s}")
    print(f"  {'-'*6} {'-'*60} {'-'*15}")
    for n in notes[:30]:
        print(f"  {n['score']:>6d} {n['file'][:60]:<60s} {n['factor']:15s}")

    # Distribution by score buckets
    print()
    print(f"=== Score Distribution ===")
    buckets = {
        "TIER A (>=150)": [n for n in notes if n["score"] >= 150],
        "TIER B (100-149)": [n for n in notes if 100 <= n["score"] < 150],
        "TIER C (50-99)": [n for n in notes if 50 <= n["score"] < 100],
        "TIER D (0-49)": [n for n in notes if 0 <= n["score"] < 50],
        "TIER R (<0)": [n for n in notes if n["score"] < 0],
    }
    for name, items in buckets.items():
        print(f"  {name}: {len(items)} notes")

    # Save tranches
    tier_a_path = ROOT / "research" / "data" / "harvest_tier_a.json"
    tier_b_path = ROOT / "research" / "data" / "harvest_tier_b.json"
    with open(tier_a_path, "w") as f:
        json.dump(buckets["TIER A (>=150)"], f, indent=2)
    with open(tier_b_path, "w") as f:
        json.dump(buckets["TIER B (100-149)"], f, indent=2)
    print()
    print(f"Tier A saved: {tier_a_path}")
    print(f"Tier B saved: {tier_b_path}")


if __name__ == "__main__":
    main()
