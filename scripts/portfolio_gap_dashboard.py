#!/usr/bin/env python3
"""FQL Portfolio Gap & Crowding Dashboard — concentration risk and gap analysis.

Shows where the portfolio is crowded, where it's thin, and what the next
research branch should target.

Usage:
    python3 scripts/portfolio_gap_dashboard.py              # Print report
    python3 scripts/portfolio_gap_dashboard.py --save       # Print + save to inbox
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_portfolio_gap_dashboard.md"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── Factor mapping (derived from family/tags/session) ──
# Since many strategies lack explicit factor tags, map from family name.
FAMILY_TO_FACTOR = {
    "pullback": "MOMENTUM",
    "breakout": "MOMENTUM",
    "trend": "MOMENTUM",
    "mean_reversion": "MEAN_REVERSION",
    "event_driven": "EVENT",
    "carry": "CARRY",
    "afternoon_rates_reversion": "STRUCTURAL",
    "vol_expansion": "VOLATILITY",
    "structural": "STRUCTURAL",
}

# Session normalization
SESSION_BUCKETS = {
    "morning": "Morning (09:30-12:00)",
    "midday": "Midday (10:00-13:00)",
    "us_only": "US Session (08:00-17:00)",
    "all_day": "All Day",
    "afternoon": "Afternoon (14:00-15:30)",
    "daily_close": "Daily Close",
    "overnight_fomc": "Overnight/Event",
    "multi_day_nfp": "Multi-Day Event",
}

# Asset class mapping
ASSET_CLASS = {
    "MES": "Equity Index", "MNQ": "Equity Index", "M2K": "Equity Index",
    "MGC": "Metal", "MCL": "Energy",
    "6J": "FX", "6E": "FX", "6B": "FX",
    "ZN": "Rates", "ZF": "Rates", "ZB": "Rates",
}

# Horizon from session/family heuristics
def _infer_horizon(s):
    session = s.get("session", "")
    family = s.get("family", "")
    name = s.get("strategy_name", "")
    if "daily" in session or "daily" in family or name in ("fx_daily_trend",):
        return "Daily"
    if "monthly" in session or name == "treasury_rolldown_carry":
        return "Monthly"
    if "event" in session or "fomc" in session or "nfp" in session:
        return "Event"
    if "afternoon" in session:
        return "Intraday (afternoon)"
    return "Intraday (morning)"


def load_active_strategies():
    """Load core + probation strategies from registry."""
    if not REGISTRY_PATH.exists():
        return []
    reg = json.load(open(REGISTRY_PATH))
    result = []
    for s in reg.get("strategies", []):
        if s.get("status") in ("core", "probation"):
            sid = s["strategy_id"]
            asset = s.get("asset", "?")
            family = s.get("family", "?")
            direction = s.get("direction", "both")
            session = s.get("session", "?")
            status = s["status"]
            tags = s.get("tags", [])

            # Infer factor
            factor_tags = [t for t in tags if t in
                          ("MOMENTUM", "CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "MEAN_REVERSION", "VALUE")]
            if factor_tags:
                factor = factor_tags[0]
            else:
                factor = FAMILY_TO_FACTOR.get(family, "UNKNOWN")

            result.append({
                "sid": sid,
                "status": status,
                "asset": asset,
                "asset_class": ASSET_CLASS.get(asset, "Other"),
                "factor": factor,
                "direction": direction,
                "session": session,
                "session_bucket": SESSION_BUCKETS.get(session, session),
                "horizon": _infer_horizon(s),
                "family": family,
            })
    return result


def count_ideas_by_factor():
    """Count registry ideas per factor for gap assessment."""
    if not REGISTRY_PATH.exists():
        return {}
    reg = json.load(open(REGISTRY_PATH))
    counts = Counter()
    for s in reg.get("strategies", []):
        if s.get("status") == "idea":
            family = s.get("family", "")
            tags = s.get("tags", [])
            factor_tags = [t for t in tags if t in
                          ("MOMENTUM", "CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "MEAN_REVERSION", "VALUE")]
            if factor_tags:
                counts[factor_tags[0]] += 1
            else:
                f = FAMILY_TO_FACTOR.get(family, "UNKNOWN")
                counts[f] += 1
    return dict(counts)


def generate_report():
    strats = load_active_strategies()
    idea_counts = count_ideas_by_factor()
    total = len(strats)
    core = [s for s in strats if s["status"] == "core"]
    prob = [s for s in strats if s["status"] == "probation"]

    lines = []
    lines.append("# FQL Portfolio Gap & Crowding Dashboard")
    lines.append(f"*Generated: {NOW}*")
    lines.append(f"*Active: {len(core)} core + {len(prob)} probation = {total} strategies*")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 1: FACTOR DISTRIBUTION
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Factor Distribution")
    lines.append("")

    all_factors = ["MOMENTUM", "MEAN_REVERSION", "VOLATILITY", "CARRY", "EVENT", "STRUCTURAL", "VALUE"]
    factor_core = Counter(s["factor"] for s in core)
    factor_prob = Counter(s["factor"] for s in prob)
    factor_total = Counter(s["factor"] for s in strats)

    lines.append("| Factor | Core | Probation | Total | % of Active | Ideas | Status |")
    lines.append("|--------|------|-----------|-------|-------------|-------|--------|")

    for f in all_factors:
        c = factor_core.get(f, 0)
        p = factor_prob.get(f, 0)
        t = factor_total.get(f, 0)
        pct = t / total * 100 if total > 0 else 0
        ideas = idea_counts.get(f, 0)

        if t == 0:
            status = "**GAP**"
        elif c == 0 and p <= 1:
            status = "THIN (probation only)"
        elif pct > 40:
            status = "**CROWDED**"
        elif pct > 25:
            status = "Heavy"
        else:
            status = "OK"

        lines.append(f"| {f:<15s} | {c:>4d} | {p:>9d} | {t:>5d} | {pct:>10.0f}% | {ideas:>5d} | {status} |")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 2: ASSET DISTRIBUTION
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Asset Distribution")
    lines.append("")

    asset_counts = Counter(s["asset"] for s in strats)
    class_counts = Counter(s["asset_class"] for s in strats)

    lines.append("| Asset | Count | Direction | Status |")
    lines.append("|-------|-------|-----------|--------|")

    for asset in sorted(asset_counts.keys()):
        count = asset_counts[asset]
        dirs = Counter(s["direction"] for s in strats if s["asset"] == asset)
        dir_str = ", ".join(f"{d}={n}" for d, n in sorted(dirs.items()))
        status = "**AT LIMIT**" if count >= 4 else ("Heavy" if count >= 3 else "OK")
        lines.append(f"| {asset:<6s} | {count:>5d} | {dir_str:<25s} | {status} |")

    lines.append("")
    lines.append("| Asset Class | Count | Target Range | Status |")
    lines.append("|-------------|-------|-------------|--------|")

    class_targets = {
        "Equity Index": (30, 50), "Metal": (15, 25), "Energy": (10, 20),
        "FX": (10, 25), "Rates": (5, 15),
    }
    for cls in ["Equity Index", "Metal", "Energy", "FX", "Rates"]:
        count = class_counts.get(cls, 0)
        pct = count / total * 100 if total > 0 else 0
        lo, hi = class_targets.get(cls, (0, 100))
        if pct > hi:
            status = "**OVER**"
        elif pct < lo:
            status = "UNDER" if count > 0 else "**GAP**"
        else:
            status = "OK"
        lines.append(f"| {cls:<13s} | {count:>5d} ({pct:.0f}%) | {lo}-{hi}% | {status} |")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 3: SESSION DISTRIBUTION
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Session Distribution")
    lines.append("")

    session_counts = Counter(s["session_bucket"] for s in strats)
    lines.append("| Session | Count | Strategies | Status |")
    lines.append("|---------|-------|-----------|--------|")

    for bucket in sorted(session_counts.keys()):
        count = session_counts[bucket]
        strat_names = [s["sid"].split("-")[0][:12] for s in strats if s["session_bucket"] == bucket]
        status = "**CROWDED**" if count >= 5 else ("Heavy" if count >= 3 else "OK")
        lines.append(f"| {bucket:<28s} | {count:>5d} | {', '.join(strat_names[:4])}{'...' if len(strat_names)>4 else ''} | {status} |")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 4: HORIZON DISTRIBUTION
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Horizon Distribution")
    lines.append("")

    horizon_counts = Counter(s["horizon"] for s in strats)
    lines.append("| Horizon | Count | % | Status |")
    lines.append("|---------|-------|---|--------|")
    for h in sorted(horizon_counts.keys()):
        count = horizon_counts[h]
        pct = count / total * 100
        status = "**OVER 80%**" if pct > 80 else ("Heavy" if pct > 60 else "OK")
        lines.append(f"| {h:<25s} | {count:>5d} | {pct:.0f}% | {status} |")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 5: DIRECTION BIAS
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Direction Bias")
    lines.append("")

    dir_counts = Counter()
    for s in strats:
        d = s["direction"]
        if d == "both":
            dir_counts["long"] += 0.5
            dir_counts["short"] += 0.5
        else:
            dir_counts[d] += 1

    long_n = dir_counts.get("long", 0)
    short_n = dir_counts.get("short", 0)
    ratio = long_n / short_n if short_n > 0 else float("inf")
    bias_status = "**LONG HEAVY**" if ratio > 2.0 else ("Balanced" if ratio < 1.5 else "Slightly long")
    lines.append(f"- Long exposure: {long_n:.1f} strategies")
    lines.append(f"- Short exposure: {short_n:.1f} strategies")
    lines.append(f"- Ratio: {ratio:.1f}:1 — {bias_status}")
    lines.append(f"- Long-only strategies: {sum(1 for s in strats if s['direction']=='long')}")
    lines.append(f"- Short-only strategies: {sum(1 for s in strats if s['direction']=='short')}")
    lines.append(f"- Both-direction strategies: {sum(1 for s in strats if s['direction']=='both')}")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 6: GAP SUMMARY
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Current Gaps")
    lines.append("")

    gaps = []
    # Factor gaps
    for f in all_factors:
        t = factor_total.get(f, 0)
        if t == 0:
            gaps.append(("FACTOR", f, "No active or probation strategy", "HIGH"))
        elif factor_core.get(f, 0) == 0 and t <= 1:
            gaps.append(("FACTOR", f, f"Only {t} probation, no core", "MEDIUM"))

    # Asset class gaps
    for cls in class_targets:
        if class_counts.get(cls, 0) == 0:
            gaps.append(("ASSET_CLASS", cls, "No strategies in this class", "HIGH"))

    # Session gaps
    if not any(s["session_bucket"].startswith("Afternoon") for s in strats if s["asset_class"] != "Rates"):
        gaps.append(("SESSION", "Non-rates afternoon", "Only rates cover afternoon session", "LOW"))

    # Direction gap
    if ratio > 2.5:
        gaps.append(("DIRECTION", "Short exposure", f"Long:Short = {ratio:.1f}:1", "MEDIUM"))

    lines.append("| Type | Gap | Detail | Priority |")
    lines.append("|------|-----|--------|----------|")
    for gtype, gname, detail, priority in sorted(gaps, key=lambda x: {"HIGH":0,"MEDIUM":1,"LOW":2}.get(x[3],3)):
        lines.append(f"| {gtype} | {gname} | {detail} | {priority} |")

    if not gaps:
        lines.append("| — | No critical gaps | All dimensions have coverage | — |")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 7: CROWDING SUMMARY
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Crowding Risks")
    lines.append("")

    crowding = []
    # Factor crowding
    for f in all_factors:
        pct = factor_total.get(f, 0) / total * 100 if total > 0 else 0
        if pct > 40:
            crowding.append(("FACTOR", f, f"{pct:.0f}% of active strategies", f"Deprioritize new {f} ideas"))

    # Asset crowding
    for asset, count in asset_counts.items():
        if count >= 4:
            crowding.append(("ASSET", asset, f"{count} strategies", f"No new {asset} strategies unless displacing weakest"))

    # Morning crowding
    morning_count = sum(1 for s in strats if "morning" in s["session_bucket"].lower() or s["session"] == "morning")
    if morning_count >= 5:
        crowding.append(("SESSION", "Morning", f"{morning_count} strategies", "New morning strategies must displace, not add"))

    lines.append("| Type | Area | Detail | Action |")
    lines.append("|------|------|--------|--------|")
    for ctype, area, detail, action in crowding:
        lines.append(f"| {ctype} | {area} | {detail} | {action} |")

    if not crowding:
        lines.append("| — | No crowding detected | All dimensions within limits | — |")

    # ══════════════════════════════════════════════════════════════════
    # SECTION 8: RECOMMENDATIONS
    # ══════════════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Research Targeting Recommendations")
    lines.append("")

    # Build recommendation from gaps and crowding
    high_gaps = [g for g in gaps if g[3] == "HIGH"]
    med_gaps = [g for g in gaps if g[3] == "MEDIUM"]

    lines.append("### Prioritize")
    if high_gaps:
        for _, gname, detail, _ in high_gaps:
            ideas = idea_counts.get(gname, 0)
            lines.append(f"- **{gname}**: {detail}. {ideas} ideas in catalog.")
    else:
        lines.append("- No HIGH-priority gaps. Focus on strengthening existing coverage.")

    if med_gaps:
        lines.append("")
        lines.append("### Monitor")
        for _, gname, detail, _ in med_gaps:
            lines.append(f"- {gname}: {detail}")

    lines.append("")
    lines.append("### Deprioritize")
    if crowding:
        for _, area, detail, action in crowding:
            lines.append(f"- **{area}**: {detail}. {action}.")
    else:
        lines.append("- No areas require active deprioritization.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Portfolio Gap & Crowding Dashboard")
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
