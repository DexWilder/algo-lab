#!/usr/bin/env python3
"""Harvest Coverage Audit — are we searching broadly enough?

Reports which sources are active, which gaps are targeted, and which
gaps still lack live search coverage. Prevents the system from silently
narrowing its search while appearing systematic.

Design principle: broad intake first, ruthless filtering later.
The harvest layer should optimize for coverage, diversity, and novelty.
The validation layer should optimize for truth, robustness, and portfolio usefulness.

Usage:
    python3 scripts/harvest_coverage_audit.py              # Print
    python3 scripts/harvest_coverage_audit.py --save       # Print + save to inbox
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

HARVEST_CONFIG = ROOT / "research" / "harvest_config.yaml"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
HARVEST_DIR = Path.home() / "openclaw-intake" / "inbox" / "harvest"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_harvest_coverage_audit.md"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")
TODAY = datetime.now().strftime("%Y-%m-%d")

ALL_FACTORS = ["MOMENTUM", "MEAN_REVERSION", "VOLATILITY", "CARRY", "EVENT", "STRUCTURAL", "VALUE"]
ALL_ASSETS = ["Equity Index", "Metal", "Energy", "FX", "Rates"]
ALL_SESSIONS = ["Morning", "Midday", "Afternoon", "Daily/Close", "Overnight/Event"]


def load_config():
    if not HARVEST_CONFIG.exists():
        return {}
    with open(HARVEST_CONFIG) as f:
        return yaml.safe_load(f)


def load_registry_factors():
    if not REGISTRY_PATH.exists():
        return {}, {}, {}
    reg = json.load(open(REGISTRY_PATH))
    core = Counter()
    prob = Counter()
    ideas = Counter()

    FAMILY_MAP = {
        "pullback": "MOMENTUM", "breakout": "MOMENTUM", "trend": "MOMENTUM",
        "mean_reversion": "MEAN_REVERSION", "event_driven": "EVENT",
        "carry": "CARRY", "afternoon_rates_reversion": "STRUCTURAL",
        "vol_expansion": "VOLATILITY", "structural": "STRUCTURAL",
        "volatility": "VOLATILITY",
    }

    for s in reg.get("strategies", []):
        tags = s.get("tags", [])
        factor = None
        for t in tags:
            if t in ALL_FACTORS:
                factor = t
                break
        if not factor:
            factor = FAMILY_MAP.get(s.get("family", ""), None)
        if not factor:
            continue

        status = s.get("status")
        if status == "core":
            core[factor] += 1
        elif status == "probation":
            prob[factor] += 1
        elif status == "idea":
            ideas[factor] += 1

    return dict(core), dict(prob), dict(ideas)


def count_recent_notes_by_source():
    """Count harvest notes from last 7 days by source type."""
    if not HARVEST_DIR.exists():
        return {}
    counts = Counter()
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    for f in HARVEST_DIR.glob("*.md"):
        # Check if recent
        name = f.name
        date_part = name[:10]
        if date_part < cutoff:
            continue
        # Read source from note
        try:
            text = f.read_text()
            for line in text.split("\n"):
                if line.startswith("- source URL:"):
                    url = line.replace("- source URL:", "").strip()
                    if "tradingview" in url.lower():
                        counts["TradingView"] += 1
                    elif "ssrn" in url.lower() or "quantpedia" in url.lower() or "doi.org" in url.lower():
                        counts["Academic"] += 1
                    elif "youtube" in url.lower():
                        counts["YouTube"] += 1
                    elif "github" in url.lower():
                        counts["GitHub"] += 1
                    elif "internal" in url.lower():
                        counts["Claw synthesis"] += 1
                    else:
                        counts["Other"] += 1
                    break
        except Exception:
            counts["Unknown"] += 1
    return dict(counts)


def generate_report():
    config = load_config()
    core, prob, ideas = load_registry_factors()
    recent = count_recent_notes_by_source()
    lanes = config.get("source_lanes", {})
    targeting = config.get("targeting", {})

    lines = []
    lines.append("# Harvest Coverage Audit")
    lines.append(f"*Generated: {NOW}*")
    lines.append("")
    lines.append("*Principle: broad intake first, ruthless filtering later.*")

    # ── Source lane status ──
    lines.append("")
    lines.append("## Source Lanes")
    lines.append("")
    lines.append("| Lane | Status | Factor Targets | Notes/Week (last 7d) |")
    lines.append("|------|--------|----------------|---------------------|")

    active_count = 0
    dormant_count = 0
    for name, cfg in lanes.items():
        status = cfg.get("status", "ENABLED" if cfg.get("enabled") else "DISABLED")
        factors = ", ".join(cfg.get("factor_targets", []))
        if status == "ACTIVE":
            active_count += 1
        elif status == "DORMANT":
            dormant_count += 1
        lines.append(f"| {name:<25s} | {status:<8s} | {factors:<30s} | — |")

    lines.append(f"\n**Active: {active_count} | Dormant: {dormant_count} | Total configured: {len(lanes)}**")

    # ── Recent note sources ──
    lines.append("")
    lines.append("## Recent Notes by Source (last 7 days)")
    lines.append("")
    if recent:
        total_recent = sum(recent.values())
        lines.append(f"Total: {total_recent} notes")
        for source, count in sorted(recent.items(), key=lambda x: -x[1]):
            pct = count / total_recent * 100
            lines.append(f"- {source}: {count} ({pct:.0f}%)")

        # Source diversity check
        if len(recent) <= 2:
            lines.append(f"\n**WARNING: Source monoculture — only {len(recent)} source type(s) producing notes.**")
            lines.append("Risk: missing entire classes of ideas from underrepresented sources.")
    else:
        lines.append("No recent notes found.")

    # ── Factor coverage vs search targeting ──
    lines.append("")
    lines.append("## Factor Coverage vs Search Targeting")
    lines.append("")
    lines.append("| Factor | Core | Prob | Ideas | Portfolio Status | In Search Targets? | Gap Covered? |")
    lines.append("|--------|------|------|-------|-----------------|-------------------|-------------|")

    # Check which factors are in any active lane's factor_targets
    factor_in_search = {f: False for f in ALL_FACTORS}
    for name, cfg in lanes.items():
        if cfg.get("status") == "ACTIVE" or cfg.get("enabled"):
            for f in cfg.get("factor_targets", []):
                if f in factor_in_search:
                    factor_in_search[f] = True

    for f in ALL_FACTORS:
        c = core.get(f, 0)
        p = prob.get(f, 0)
        i = ideas.get(f, 0)
        total = c + p
        if total == 0 and i == 0:
            port_status = "**BLIND SPOT**"
        elif total == 0:
            port_status = "**GAP**"
        elif c == 0:
            port_status = "Thin"
        elif f == "MOMENTUM" and total > 4:
            port_status = "CROWDED"
        else:
            port_status = "OK"

        in_search = "YES" if factor_in_search.get(f) else "**NO**"
        covered = "YES" if factor_in_search.get(f) and (total > 0 or i > 0) else (
            "SEARCH ONLY" if factor_in_search.get(f) else "**UNCOVERED**"
        )
        lines.append(f"| {f:<15s} | {c:>4d} | {p:>4d} | {i:>5d} | {port_status:<17s} | {in_search:<19s} | {covered} |")

    # ── Asset class coverage ──
    lines.append("")
    lines.append("## Asset Class Search Coverage")
    lines.append("")

    asset_bias = set()
    for name, cfg in lanes.items():
        if cfg.get("status") == "ACTIVE" or cfg.get("enabled"):
            for a in cfg.get("asset_bias", []):
                asset_bias.add(a)
            for t in cfg.get("secondary_targets", []):
                if "energy" in t:
                    asset_bias.add("energy")
                if "rate" in t:
                    asset_bias.add("rates")

    lines.append("| Asset Class | In Active Search? | Notes |")
    lines.append("|-------------|------------------|-------|")
    for cls in ALL_ASSETS:
        cls_lower = cls.lower()
        in_search = any(cls_lower in a for a in asset_bias) or cls_lower in str(asset_bias)
        status = "YES" if in_search else "**NO**"
        lines.append(f"| {cls:<13s} | {status:<18s} | |")

    # ── Gaps without search coverage ──
    lines.append("")
    lines.append("## Gaps Without Live Search Coverage")
    lines.append("")

    uncovered = []
    for f in ALL_FACTORS:
        total = core.get(f, 0) + prob.get(f, 0)
        if total == 0 and not factor_in_search.get(f):
            uncovered.append(("FACTOR", f, f"0 active, not in any lane's factor_targets"))
    if not any("energy" in a for a in asset_bias):
        uncovered.append(("ASSET", "Energy", "Not in any active lane's asset_bias"))

    if uncovered:
        for gtype, gap, detail in uncovered:
            lines.append(f"- **{gtype}: {gap}** — {detail}")
    else:
        lines.append("All portfolio gaps have at least one live search lane targeting them.")

    # ── Closed families ──
    lines.append("")
    lines.append("## Closed Families (blocked from rediscovery)")
    lines.append("")
    closed = targeting.get("high_bar_families", [])
    lines.append(f"| Family | Failures | Closed Date |")
    lines.append(f"|--------|----------|-------------|")
    for fam in closed:
        name = fam.get("family", "?")
        failures = fam.get("failures", fam.get("count", "?"))
        closed_date = fam.get("closed_date", "legacy")
        lines.append(f"| {name} | {failures} | {closed_date} |")

    # ── Recommendations ──
    lines.append("")
    lines.append("## Recommendations")
    lines.append("")

    if recent and len(recent) <= 2:
        lines.append("- **Diversify sources.** Most notes come from 1-2 sources. Enable dormant lanes or add new search terms to broaden intake.")

    uncovered_factors = [f for f in ALL_FACTORS if core.get(f,0)+prob.get(f,0)==0 and not factor_in_search.get(f)]
    if uncovered_factors:
        lines.append(f"- **Add to search targets:** {', '.join(uncovered_factors)} — portfolio gaps with no live search coverage.")

    if dormant_count > 0:
        dormant_names = [n for n, c in lanes.items() if c.get("status") == "DORMANT"]
        lines.append(f"- **Dormant lanes ({dormant_count}):** {', '.join(dormant_names)}. Consider activating when current lanes saturate.")

    if not uncovered and len(recent) > 2:
        lines.append("- Coverage is adequate. Focus on filtering quality, not search breadth.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Harvest Coverage Audit")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    report = generate_report()
    print(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
