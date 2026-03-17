#!/usr/bin/env python3
"""FQL Factor Decomposition — Portfolio-level factor exposure analysis.

Classifies each strategy by primary and secondary factor exposure,
then analyzes portfolio-level concentration. Answers the question:
"Are we secretly just long momentum everywhere?"

Factors:
  - MOMENTUM: directional continuation (trend following, breakout)
  - MEAN_REVERSION: fade extremes, return to mean
  - VOLATILITY: profit from vol expansion or compression
  - CARRY: directional bias from yield/rate differentials
  - EVENT: calendar-driven or news-driven setups
  - STRUCTURAL: session-specific microstructure (session handoffs, range breaks)

Usage:
    python3 research/factor_decomposition.py              # Full report
    python3 research/factor_decomposition.py --save       # Save to reports/
    python3 research/factor_decomposition.py --json       # JSON output
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

# ── Factor Definitions ───────────────────────────────────────────────────────

FACTORS = {
    "MOMENTUM": "Directional continuation — trend following, breakout, pullback-with-trend",
    "MEAN_REVERSION": "Fade extremes — VWAP fade, RSI bounce, gap fill, range reversion",
    "VOLATILITY": "Profit from vol expansion or compression — squeeze breakout, NR7, ATR expansion",
    "CARRY": "Directional bias from macro/yield — carry trade, macro momentum, rate direction",
    "EVENT": "Calendar or news driven — EIA, FOMC, OPEX, earnings reaction",
    "STRUCTURAL": "Session microstructure — session handoff, range break, London/Tokyo transition",
}

# ── Strategy-to-Factor Mapping ───────────────────────────────────────────────
# Each strategy gets a primary factor and optional secondary factor.
# This is based on actual entry logic, not just family labels.

STRATEGY_FACTORS = {
    # Core equity intraday
    "VWAP-MNQ-Long": {"primary": "MOMENTUM", "secondary": "STRUCTURAL", "logic": "VWAP pullback in trend direction, session-timed"},
    "XB-PB-EMA-MES-Short": {"primary": "MOMENTUM", "secondary": None, "logic": "EMA pullback with trend, time-stop exit"},
    "ORB-MGC-Long": {"primary": "MOMENTUM", "secondary": "STRUCTURAL", "logic": "Opening range breakout — momentum + session structure"},
    "BB-EQ-MGC-Long": {"primary": "MEAN_REVERSION", "secondary": "VOLATILITY", "logic": "Bollinger band snapback — fade overextension"},
    "PB-MGC-Short": {"primary": "MOMENTUM", "secondary": None, "logic": "Pullback trend following, short side"},
    "Donchian-MNQ-Long-GRINDING": {"primary": "MOMENTUM", "secondary": None, "logic": "Donchian breakout + GRINDING persistence filter"},

    # Core equity probation/other
    "NoiseBoundary-MNQ-Long": {"primary": "MOMENTUM", "secondary": "VOLATILITY", "logic": "Intraday momentum with noise filter"},
    "GapMom": {"primary": "MOMENTUM", "secondary": "STRUCTURAL", "logic": "Gap momentum continuation"},
    "RangeExpansion": {"primary": "VOLATILITY", "secondary": "MOMENTUM", "logic": "Range expansion breakout"},

    # Probation — non-equity
    "DailyTrend-MGC-Long": {"primary": "MOMENTUM", "secondary": "CARRY", "logic": "Daily Donchian + EMA trend — captures macro gold momentum"},
    "MomPB-6J-Long-US": {"primary": "MOMENTUM", "secondary": "CARRY", "logic": "EMA pullback on 6J — captures USD/JPY macro momentum"},
    "FXBreak-6J-Short-London": {"primary": "STRUCTURAL", "secondary": "MOMENTUM", "logic": "Asian range breakout at London open — session transition"},

    # M2K probation/testing
    "MomIgn-M2K-Short": {"primary": "MOMENTUM", "secondary": "VOLATILITY", "logic": "Volume surge + VWAP cross momentum"},
    "CloseVWAP-M2K-Short": {"primary": "MEAN_REVERSION", "secondary": "STRUCTURAL", "logic": "Close session VWAP reversion"},
    "TTMSqueeze-M2K-Short": {"primary": "VOLATILITY", "secondary": "MOMENTUM", "logic": "TTM squeeze release — vol compression breakout"},
    "ORBEnh-M2K-Short": {"primary": "MOMENTUM", "secondary": "STRUCTURAL", "logic": "Enhanced ORB on Russell"},

    # MCL/other probation
    "VWAPMR-MCL-Short": {"primary": "MEAN_REVERSION", "secondary": None, "logic": "VWAP mean reversion on crude"},

    # FX watchlist/monitor
    "MomPB-6E-Long-US": {"primary": "MOMENTUM", "secondary": "CARRY", "logic": "EMA pullback on Euro — macro momentum"},

    # Rates monitor
    "DualThrust-ZB-Short-Monitor": {"primary": "MOMENTUM", "secondary": "CARRY", "logic": "DualThrust range breakout short — rates rising / macro tightening"},
}


def load_registry():
    reg_path = DATA_DIR / "strategy_registry.json"
    if not reg_path.exists():
        return []
    return json.load(open(reg_path)).get("strategies", [])


def classify_strategy(strategy_id):
    """Get factor classification for a strategy."""
    if strategy_id in STRATEGY_FACTORS:
        return STRATEGY_FACTORS[strategy_id]
    return {"primary": "UNKNOWN", "secondary": None, "logic": "Not yet classified"}


def analyze_portfolio_factors(strategies):
    """Analyze factor concentration across the active portfolio."""
    # Only analyze non-rejected, non-idea strategies
    active_statuses = {"core", "probation", "testing"}
    active = [s for s in strategies if s.get("status") in active_statuses]

    # Factor counts
    primary_counts = Counter()
    secondary_counts = Counter()
    factor_strategies = defaultdict(list)

    for s in active:
        sid = s["strategy_id"]
        factors = classify_strategy(sid)
        primary = factors["primary"]
        secondary = factors.get("secondary")

        primary_counts[primary] += 1
        factor_strategies[primary].append(sid)

        if secondary:
            secondary_counts[secondary] += 1
            factor_strategies[f"{secondary} (secondary)"].append(sid)

    # Weighted exposure (primary=1.0, secondary=0.5)
    weighted = Counter()
    for s in active:
        sid = s["strategy_id"]
        factors = classify_strategy(sid)
        weighted[factors["primary"]] += 1.0
        if factors.get("secondary"):
            weighted[factors["secondary"]] += 0.5

    total_weight = sum(weighted.values())
    exposure_pct = {f: round(w / total_weight * 100, 1) for f, w in weighted.most_common()} if total_weight else {}

    return {
        "active_count": len(active),
        "primary_counts": dict(primary_counts.most_common()),
        "secondary_counts": dict(secondary_counts.most_common()),
        "weighted_exposure_pct": exposure_pct,
        "factor_strategies": {k: v for k, v in sorted(factor_strategies.items())},
    }


def find_concentration_risks(analysis):
    """Identify hidden factor crowding."""
    risks = []

    # Any single factor > 50% of weighted exposure
    for factor, pct in analysis["weighted_exposure_pct"].items():
        if pct > 50:
            strategies = analysis["factor_strategies"].get(factor, [])
            risks.append({
                "type": "DOMINANT_FACTOR",
                "factor": factor,
                "exposure_pct": pct,
                "strategies": strategies,
                "detail": f"{factor} is {pct}% of portfolio factor exposure — hidden concentration even if assets/sessions differ",
            })

    # Any factor with 5+ strategies
    for factor, count in analysis["primary_counts"].items():
        if count >= 5:
            risks.append({
                "type": "OVERCROWDED_FACTOR",
                "factor": factor,
                "count": count,
                "strategies": analysis["factor_strategies"].get(factor, []),
                "detail": f"{count} strategies with {factor} as primary factor",
            })

    return risks


def find_missing_factors(analysis):
    """Identify factor gaps in the portfolio."""
    gaps = []
    all_factors = set(FACTORS.keys())
    present = set(analysis["primary_counts"].keys())
    missing = all_factors - present

    for factor in missing:
        gaps.append({
            "factor": factor,
            "description": FACTORS[factor],
            "detail": f"No active strategy has {factor} as primary factor",
        })

    # Also flag factors with only 1 strategy (thin coverage)
    for factor, count in analysis["primary_counts"].items():
        if count == 1:
            gaps.append({
                "factor": factor,
                "description": FACTORS[factor],
                "detail": f"Only 1 strategy with {factor} as primary — thin coverage",
            })

    return gaps


def check_probation_complementarity(strategies):
    """Check if probation strategies add genuine factor diversification."""
    core = [s for s in strategies if s.get("status") == "core"]
    probation = [s for s in strategies if s.get("status") == "probation"]

    core_factors = Counter()
    for s in core:
        f = classify_strategy(s["strategy_id"])
        core_factors[f["primary"]] += 1

    notes = []
    for s in probation:
        sid = s["strategy_id"]
        f = classify_strategy(sid)
        primary = f["primary"]

        if primary in core_factors and core_factors[primary] >= 3:
            notes.append({
                "strategy": sid,
                "factor": primary,
                "verdict": "REDUNDANT_FACTOR",
                "detail": f"{sid} adds more {primary} exposure — core already has {core_factors[primary]} {primary} strategies",
            })
        else:
            notes.append({
                "strategy": sid,
                "factor": primary,
                "verdict": "ADDS_FACTOR_DIVERSITY",
                "detail": f"{sid} adds {primary} exposure where core has {core_factors.get(primary, 0)}",
            })

    return notes


# ── Report ───────────────────────────────────────────────────────────────────

def print_report(analysis, risks, gaps, complementarity):
    W = 70
    print()
    print("=" * W)
    print("  FQL FACTOR DECOMPOSITION REPORT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    # Factor exposure
    print(f"\n  1. PORTFOLIO FACTOR EXPOSURE (weighted: primary=1.0, secondary=0.5)")
    print(f"  {'-' * (W-4)}")
    for factor, pct in sorted(analysis["weighted_exposure_pct"].items(), key=lambda x: -x[1]):
        bar_len = int(pct / 2.5)
        bar = "#" * bar_len + "." * (40 - bar_len)
        count = analysis["primary_counts"].get(factor, 0)
        print(f"  {factor:<18s} [{bar}] {pct:>5.1f}%  ({count} primary)")

    # Per-strategy classification
    print(f"\n  2. STRATEGY FACTOR MAP")
    print(f"  {'-' * (W-4)}")
    print(f"  {'Strategy':<35s} {'Primary':<18s} {'Secondary':<18s}")
    print(f"  {'-' * 68}")

    registry = load_registry()
    active = [s for s in registry if s.get("status") in ("core", "probation", "testing")]
    for s in sorted(active, key=lambda x: x.get("status", "")):
        sid = s["strategy_id"]
        f = classify_strategy(sid)
        status_tag = f"[{s.get('status', '?')[:4]}]"
        sec = f["secondary"] or "-"
        print(f"  {sid:<35s} {f['primary']:<18s} {sec:<18s} {status_tag}")

    # Concentration risks
    print(f"\n  3. CONCENTRATION RISKS")
    print(f"  {'-' * (W-4)}")
    if risks:
        for r in risks:
            print(f"  !! {r['type']}: {r['factor']} ({r['exposure_pct']}%)" if 'exposure_pct' in r
                  else f"  !! {r['type']}: {r['factor']} ({r['count']} strategies)")
            print(f"     {r['detail']}")
    else:
        print(f"  No concentration risks detected.")

    # Missing factors
    print(f"\n  4. MISSING / THIN FACTOR COVERAGE")
    print(f"  {'-' * (W-4)}")
    if gaps:
        for g in gaps:
            print(f"  -- {g['factor']}: {g['detail']}")
    else:
        print(f"  All factors represented.")

    # Probation complementarity
    print(f"\n  5. PROBATION FACTOR COMPLEMENTARITY")
    print(f"  {'-' * (W-4)}")
    for c in complementarity:
        icon = ">>" if c["verdict"] == "ADDS_FACTOR_DIVERSITY" else "!!"
        print(f"  {icon} {c['strategy']}: {c['verdict']}")
        print(f"     {c['detail']}")

    print(f"\n{'=' * W}")


def main():
    parser = argparse.ArgumentParser(description="FQL Factor Decomposition")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    registry = load_registry()
    analysis = analyze_portfolio_factors(registry)
    risks = find_concentration_risks(analysis)
    gaps = find_missing_factors(analysis)
    complementarity = check_probation_complementarity(registry)

    report = {
        "generated": datetime.now().isoformat(),
        "factor_definitions": FACTORS,
        "analysis": analysis,
        "concentration_risks": risks,
        "missing_factors": gaps,
        "probation_complementarity": complementarity,
    }

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(analysis, risks, gaps, complementarity)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out = REPORTS_DIR / f"factor_decomposition_{ts}.json"
        atomic_write_json(out, report)
        print(f"\n  Saved: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
