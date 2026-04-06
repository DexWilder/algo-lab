#!/usr/bin/env python3
"""FQL Convergence Scorer — boost priority when multiple sources confirm a mechanism.

A mechanism confirmed by 2+ independent sources is stronger evidence than
one source alone. This scorer:
  1. Scans the registry for convergent_sources entries
  2. Checks recent harvest notes for cross-source confirmation of existing ideas
  3. Boosts review_priority for ideas with convergent evidence
  4. Reports convergence status for the operator

Scoring rules:
  1 source:  baseline priority (no boost)
  2 sources: +1 priority level (e.g., MEDIUM → HIGH)
  3+ sources: auto-flag HIGH + priority review

"Independent" = different source_category. Two TradingView scripts saying
the same thing = 1 source. TradingView + GitHub + Quantpedia = 3.

Usage:
    python3 scripts/convergence_scorer.py              # Report
    python3 scripts/convergence_scorer.py --apply      # Report + update registry
    python3 scripts/convergence_scorer.py --scan       # Scan harvest for new matches
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
HARVEST_DIR = Path.home() / "openclaw-intake" / "inbox" / "harvest"
REVIEWED_DIR = Path.home() / "openclaw-intake" / "reviewed"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

# Keywords that indicate the same mechanism (for fuzzy matching)
MECHANISM_CLUSTERS = {
    "carry_rank": ["carry rank", "carry sort", "carry rotation", "roll yield rank",
                    "backwardation premium rank", "term structure carry"],
    "rolldown_carry": ["rolldown", "roll down", "carry spread", "tenor carry",
                        "duration carry", "yield curve carry"],
    "ppp_value": ["ppp", "purchasing power parity", "fair value currency",
                   "currency valuation", "fx value"],
    "vol_managed": ["volatility managed", "vol managed", "inverse vol",
                     "volatility targeting", "vol targeting", "risk scaling"],
    "mean_reversion_fx": ["mean reversion currency", "fx mean reversion",
                           "currency reversion", "relative value fx"],
    "commodity_carry": ["commodity carry", "convenience yield", "commodity term",
                         "commodity backwardation", "commodity contango"],
    "trend_following": ["trend following", "time series momentum", "managed futures trend",
                         "cta trend"],
}


def load_registry():
    if not REGISTRY_PATH.exists():
        return {}
    return json.load(open(REGISTRY_PATH))


def extract_mechanism_keywords(text):
    """Extract mechanism cluster matches from text."""
    text_lower = text.lower()
    matches = []
    for cluster, keywords in MECHANISM_CLUSTERS.items():
        if any(kw in text_lower for kw in keywords):
            matches.append(cluster)
    return matches


def scan_for_new_convergence(registry):
    """Scan recent harvest notes for mechanism matches with existing registry entries.

    Returns list of potential convergent matches:
    {strategy_id, note_file, mechanism_cluster, source_category}
    """
    strategies = registry.get("strategies", [])
    potential_matches = []

    # Build registry mechanism index
    registry_mechanisms = {}
    for s in strategies:
        sid = s["strategy_id"]
        # Extract from rule_summary, notes, family
        text = f"{s.get('rule_summary', '')} {s.get('notes', '')} {s.get('family', '')}"
        clusters = extract_mechanism_keywords(text)
        if clusters:
            registry_mechanisms[sid] = {
                "clusters": clusters,
                "source_category": s.get("source_category", "unknown"),
                "existing_convergent": len(s.get("convergent_sources", [])),
            }

    # Scan harvest notes
    for d in [HARVEST_DIR, REVIEWED_DIR]:
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            try:
                text = f.read_text()
                note_source = "unknown"
                for line in text.split("\n"):
                    if line.startswith("- source URL:"):
                        url = line.split(":", 1)[-1].strip().lower()
                        if "quantpedia" in url or "ssrn" in url:
                            note_source = "academic"
                        elif "tradingview" in url:
                            note_source = "tradingview"
                        elif "github" in url:
                            note_source = "github"
                        elif "youtube" in url:
                            note_source = "youtube"
                        elif "internal" in url:
                            note_source = "claw_synthesis"
                        else:
                            note_source = "other"
                        break

                note_clusters = extract_mechanism_keywords(text)

                for sid, info in registry_mechanisms.items():
                    # Check for cluster overlap
                    overlap = set(note_clusters) & set(info["clusters"])
                    if overlap and note_source != info["source_category"]:
                        potential_matches.append({
                            "strategy_id": sid,
                            "note_file": f.name,
                            "mechanism_cluster": list(overlap)[0],
                            "note_source": note_source,
                            "registry_source": info["source_category"],
                            "existing_convergent": info["existing_convergent"],
                        })
            except Exception:
                pass

    # Deduplicate
    seen = set()
    unique = []
    for m in potential_matches:
        key = f"{m['strategy_id']}|{m['note_file']}"
        if key not in seen:
            seen.add(key)
            unique.append(m)

    return unique


def compute_priority_boosts(registry):
    """Compute priority boosts based on convergent evidence."""
    boosts = []
    for s in registry.get("strategies", []):
        cs = s.get("convergent_sources", [])
        if not cs:
            continue

        sid = s["strategy_id"]
        current_priority = s.get("review_priority", "LOW")
        n_sources = len(cs) + 1  # +1 for the original source

        # Determine unique source categories
        source_cats = {s.get("source_category", "unknown")}
        for c in cs:
            src = c.get("source", "").lower()
            if "github" in src:
                source_cats.add("github")
            elif "quantpedia" in src or "academic" in src:
                source_cats.add("academic")
            elif "tradingview" in src:
                source_cats.add("tradingview")
            else:
                source_cats.add("other")

        independent_sources = len(source_cats)

        # Boost logic
        if independent_sources >= 3:
            new_priority = "HIGH"
            boost = "AUTO_HIGH (3+ independent sources)"
        elif independent_sources >= 2:
            # Boost one level
            priority_order = {"LOW": "MEDIUM", "MEDIUM": "HIGH", "HIGH": "HIGH", "NONE": "MEDIUM"}
            new_priority = priority_order.get(current_priority, "MEDIUM")
            boost = f"+1 level ({current_priority} → {new_priority})"
        else:
            new_priority = current_priority
            boost = "no boost (same source category)"

        boosts.append({
            "strategy_id": sid,
            "current_priority": current_priority,
            "new_priority": new_priority,
            "independent_sources": independent_sources,
            "convergent_count": len(cs),
            "boost": boost,
        })

    return boosts


def apply_boosts(registry, boosts):
    """Apply priority boosts to the registry."""
    applied = 0
    for boost in boosts:
        if boost["current_priority"] != boost["new_priority"]:
            for s in registry["strategies"]:
                if s["strategy_id"] == boost["strategy_id"]:
                    s["review_priority"] = boost["new_priority"]
                    applied += 1
                    break
    return applied


def generate_report(registry, boosts, new_matches):
    lines = []
    lines.append("# FQL Convergence Report")
    lines.append(f"*{NOW}*")
    lines.append("")

    # Current convergent strategies
    convergent = [s for s in registry.get("strategies", []) if s.get("convergent_sources")]
    lines.append(f"## Confirmed Convergent Evidence ({len(convergent)} strategies)")
    lines.append("")

    if convergent:
        for s in convergent:
            sid = s["strategy_id"]
            cs = s["convergent_sources"]
            lines.append(f"### {sid}")
            lines.append(f"- Original source: {s.get('source_category', '?')}")
            for c in cs:
                lines.append(f"- Confirmed by: {c['source']} ({c.get('date', '?')})")
                lines.append(f"  Mechanism: {c.get('mechanism', '?')[:80]}")
            lines.append("")
    else:
        lines.append("No confirmed convergent evidence yet.")
        lines.append("")

    # Priority boosts
    if boosts:
        lines.append(f"## Priority Boosts ({len(boosts)})")
        lines.append("")
        lines.append("| Strategy | Sources | Current | New | Boost |")
        lines.append("|----------|---------|---------|-----|-------|")
        for b in boosts:
            lines.append(f"| {b['strategy_id']} | {b['independent_sources']} | {b['current_priority']} | {b['new_priority']} | {b['boost']} |")
        lines.append("")

    # New potential matches from scan
    if new_matches:
        lines.append(f"## Potential New Convergence ({len(new_matches)} matches)")
        lines.append("")
        lines.append("| Strategy | Note | Mechanism | Note Source | Registry Source |")
        lines.append("|----------|------|-----------|------------|-----------------|")
        for m in new_matches[:20]:
            lines.append(f"| {m['strategy_id'][:30]} | {m['note_file'][:30]} | {m['mechanism_cluster']} | {m['note_source']} | {m['registry_source']} |")
        lines.append("")
        lines.append("*Review these manually — fuzzy matches may include false positives.*")
    else:
        lines.append("## No New Convergence Found")
        lines.append("Harvest notes do not match existing registry mechanisms from independent sources.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Convergence Scorer")
    parser.add_argument("--apply", action="store_true", help="Apply priority boosts to registry")
    parser.add_argument("--scan", action="store_true", help="Scan harvest for new convergent matches")
    parser.add_argument("--save", action="store_true", help="Save report to inbox")
    args = parser.parse_args()

    registry = load_registry()
    boosts = compute_priority_boosts(registry)

    new_matches = []
    if args.scan:
        new_matches = scan_for_new_convergence(registry)

    report = generate_report(registry, boosts, new_matches)
    print(report)

    if args.apply and boosts:
        from research.utils.atomic_io import atomic_write_json
        applied = apply_boosts(registry, boosts)
        atomic_write_json(REGISTRY_PATH, registry)
        print(f"\n  Applied {applied} priority boost(s) to registry.")

    if args.save:
        output = Path.home() / "openclaw-intake" / "inbox" / "_convergence_report.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {output}")


if __name__ == "__main__":
    main()
