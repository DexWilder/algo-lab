"""Strategy Genome Map — Classify and visualize validated strategies by structural DNA.

READ-ONLY research tool. Does NOT modify any execution files.

Classifies the 6 validated strategies across entry type, regime niche,
holding characteristics, asset, side, and portfolio role. Identifies gaps
and overlap to guide future research.

Usage:
    python3 research/strategy_genome_map.py             # Terminal report
    python3 research/strategy_genome_map.py --json       # JSON to stdout
    python3 research/strategy_genome_map.py --save       # Save JSON to research/strategy_genome_map.json
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Hardcoded strategy characteristics (well-established from research phases) ──

STRATEGIES = [
    {
        "id": "PB-MGC-Short",
        "name": "pb_trend",
        "family": "pullback",
        "entry_type": "pullback",
        "entry_desc": "Trend pullback (EMA bounce with strong close)",
        "asset": "MGC",
        "side": "short",
        "hold_bars": 3,
        "hold_class": "scalp",
        "regime_niche": ["HIGH_RV"],
        "regime_preferred": ["HIGH_VOL_TRENDING_HIGH_RV", "NORMAL_TRENDING_HIGH_RV"],
        "portfolio_role": "core",
        "status": "parent",
        "exit_type": "bracket + BE + trail",
        "notes": "Gold short specialist, fast entries in volatile trends",
    },
    {
        "id": "ORB-MGC-Long",
        "name": "orb_009",
        "family": "breakout",
        "entry_type": "breakout",
        "entry_desc": "Opening range breakout (5m OR with volume confirm)",
        "asset": "MGC",
        "side": "long",
        "hold_bars": 28,
        "hold_class": "swing",
        "regime_niche": ["TRENDING"],
        "regime_preferred": ["NORMAL_TRENDING_LOW_RV", "NORMAL_TRENDING_HIGH_RV", "LOW_VOL_TRENDING"],
        "portfolio_role": "core",
        "status": "parent",
        "exit_type": "bracket + BE + trail",
        "notes": "Gold long breakout, captures opening range expansion",
    },
    {
        "id": "VWAP-MNQ-Long",
        "name": "vwap_trend",
        "family": "trend",
        "entry_type": "trend_continuation",
        "entry_desc": "VWAP pullback entry in trending regime",
        "asset": "MNQ",
        "side": "long",
        "hold_bars": 15,
        "hold_class": "swing",
        "regime_niche": ["LOW_VOL_TRENDING", "NORMAL_TRENDING"],
        "regime_preferred": ["LOW_VOL_TRENDING_LOW_RV", "LOW_VOL_TRENDING_HIGH_RV",
                             "NORMAL_TRENDING_LOW_RV", "NORMAL_TRENDING_HIGH_RV"],
        "portfolio_role": "core",
        "status": "parent",
        "exit_type": "ATR trail",
        "notes": "100% param stability, best risk-adjusted validated strategy",
    },
    {
        "id": "XB-PB-EMA-MES-Short",
        "name": "xb_pb_ema_timestop",
        "family": "pullback",
        "entry_type": "pullback",
        "entry_desc": "EMA pullback with time stop exit",
        "asset": "MES",
        "side": "short",
        "hold_bars": 5,
        "hold_class": "scalp",
        "regime_niche": ["BROAD"],
        "regime_preferred": ["NORMAL_TRENDING_LOW_RV", "NORMAL_RANGING_LOW_RV",
                             "HIGH_VOL_TRENDING_HIGH_RV"],
        "portfolio_role": "enhancer",
        "status": "parent",
        "exit_type": "time stop + bracket",
        "notes": "Crossbred from PB parent, broad regime coverage, S&P short specialist",
    },
    {
        "id": "BB-EQ-MGC-Long",
        "name": "bb_equilibrium",
        "family": "mean_reversion",
        "entry_type": "mean_reversion",
        "entry_desc": "Bollinger Band snapback (equilibrium reversion in trend)",
        "asset": "MGC",
        "side": "long",
        "hold_bars": 10,
        "hold_class": "swing",
        "regime_niche": ["TRENDING"],
        "regime_preferred": ["NORMAL_TRENDING_LOW_RV", "NORMAL_TRENDING_HIGH_RV",
                             "LOW_VOL_TRENDING_LOW_RV"],
        "portfolio_role": "enhancer",
        "status": "parent",
        "exit_type": "bracket + trail",
        "notes": "Gold snapback — profits in TRENDING not RANGING (counterintuitive)",
    },
    {
        "id": "Donchian-MNQ-Long",
        "name": "donchian_trend",
        "family": "breakout",
        "entry_type": "breakout",
        "entry_desc": "Donchian channel breakout with GRINDING regime filter",
        "asset": "MNQ",
        "side": "long",
        "hold_bars": 60,
        "hold_class": "trend",
        "regime_niche": ["GRINDING"],
        "regime_preferred": ["GRINDING"],
        "portfolio_role": "probation",
        "status": "probation",
        "exit_type": "Profit Ladder (ratcheting R-stops)",
        "notes": "True trend-follower DNA (60b hold). GRINDING-only filter. Sample size limits validation.",
    },
    # ── Probation strategies (Track 2) ─────────────────────────────────────
    {
        "id": "MomIgn-M2K-Short",
        "name": "momentum_ignition",
        "family": "momentum",
        "entry_type": "momentum_burst",
        "entry_desc": "VWAP cross + 2x volume surge + RSI confirm + EMA slope",
        "asset": "M2K",
        "side": "short",
        "hold_bars": 12,
        "hold_class": "swing",
        "regime_niche": ["TRENDING"],
        "regime_preferred": ["NORMAL_TRENDING_LOW_RV", "LOW_VOL_TRENDING_LOW_RV"],
        "portfolio_role": "tail_engine",
        "status": "probation",
        "exit_type": "Profit Ladder (4R target)",
        "validation_score": 6.0,
        "param_stability": 96,
        "session": "midday",
        "notes": "M2K-specific momentum burst. 6.0/10 on extended data. Tail engine profile.",
    },
    {
        "id": "CloseVWAP-M2K-Short",
        "name": "close_vwap_reversion",
        "family": "mean_reversion",
        "entry_type": "mean_reversion",
        "entry_desc": "Session VWAP deviation band fade (2 sigma + RSI)",
        "asset": "M2K",
        "side": "short",
        "hold_bars": 6,
        "hold_class": "scalp",
        "regime_niche": ["BROAD"],
        "regime_preferred": ["NORMAL_TRENDING_LOW_RV", "LOW_VOL_TRENDING_LOW_RV",
                             "NORMAL_RANGING_LOW_RV"],
        "portfolio_role": "stabilizer",
        "status": "probation",
        "exit_type": "Target=VWAP + time exit 15:55",
        "validation_score": 6.0,
        "param_stability": 100,
        "session": "close",
        "notes": "Close session stabilizer (15:00-15:55). 100% param stability on 6.7yr. M2K-specific.",
    },
    {
        "id": "TTMSqueeze-M2K-Short",
        "name": "ttm_squeeze",
        "family": "vol_expansion",
        "entry_type": "volatility_expansion",
        "entry_desc": "BB inside KC squeeze → first expansion bar + momentum direction",
        "asset": "M2K",
        "side": "short",
        "hold_bars": 15,
        "hold_class": "swing",
        "regime_niche": ["LOW_VOL"],
        "regime_preferred": ["LOW_VOL_RANGING_LOW_RV", "LOW_VOL_RANGING_HIGH_RV",
                             "NORMAL_RANGING_LOW_RV"],
        "portfolio_role": "tail_engine",
        "status": "probation",
        "exit_type": "Profit Ladder (4R target) + time exit",
        "validation_score": 5.5,
        "param_stability": 86,
        "session": "all_day",
        "notes": "First vol expansion strategy. Fires from compression. 86% param stability. M2K-specific.",
    },
    {
        "id": "ORBEnh-M2K-Short",
        "name": "orb_enhanced",
        "family": "breakout",
        "entry_type": "breakout",
        "entry_desc": "Enhanced ORB with volume + range filters",
        "asset": "M2K",
        "side": "short",
        "hold_bars": 20,
        "hold_class": "swing",
        "regime_niche": ["TRENDING"],
        "regime_preferred": ["NORMAL_TRENDING_LOW_RV", "NORMAL_TRENDING_HIGH_RV"],
        "portfolio_role": "probation",
        "status": "probation",
        "exit_type": "bracket + trail",
        "validation_score": 8.0,
        "param_stability": 100,
        "session": "morning",
        "notes": "ORB on Russell. 8.0/10, 100% param stability. Needs 150+ trades.",
    },
    {
        "id": "VWAPMR-MCL-Short",
        "name": "vwap_mean_reversion",
        "family": "mean_reversion",
        "entry_type": "mean_reversion",
        "entry_desc": "VWAP deviation band fade on crude oil",
        "asset": "MCL",
        "side": "short",
        "hold_bars": 8,
        "hold_class": "scalp",
        "regime_niche": ["RANGING"],
        "regime_preferred": ["NORMAL_RANGING_LOW_RV", "LOW_VOL_RANGING_LOW_RV"],
        "portfolio_role": "probation",
        "status": "probation",
        "exit_type": "Target=VWAP + bracket",
        "validation_score": 6.5,
        "param_stability": 70,
        "session": "morning",
        "notes": "Crude oil mean reversion. 6.5/10, 70% param stability.",
    },
]

# ── Session definitions ───────────────────────────────────────────────────
SESSION_WINDOWS = {
    "pre_market": ("08:00", "09:30"),
    "morning": ("09:30", "12:00"),
    "midday": ("12:00", "14:00"),
    "afternoon": ("14:00", "15:00"),
    "close": ("15:00", "16:00"),
}

# Add session to core strategies that don't have it
for s in STRATEGIES:
    if "session" not in s:
        if s["id"] in ["PB-MGC-Short", "ORB-MGC-Long"]:
            s["session"] = "morning"
        elif s["id"] in ["VWAP-MNQ-Long"]:
            s["session"] = "midday"
        elif s["id"] in ["XB-PB-EMA-MES-Short"]:
            s["session"] = "morning"
        elif s["id"] in ["BB-EQ-MGC-Long"]:
            s["session"] = "all_day"
        elif s["id"] in ["Donchian-MNQ-Long"]:
            s["session"] = "morning"
        else:
            s["session"] = "all_day"

# ── Regime grid definition ──────────────────────────────────────────────────

VOL_REGIMES = ["LOW_VOL", "NORMAL", "HIGH_VOL"]
TREND_REGIMES = ["TRENDING", "RANGING"]
RV_REGIMES = ["LOW_RV", "HIGH_RV"]

ALL_REGIME_CELLS = []
for vol in VOL_REGIMES:
    for trend in TREND_REGIMES:
        for rv in RV_REGIMES:
            ALL_REGIME_CELLS.append(f"{vol}_{trend}_{rv}")
# Plus GRINDING as a special cell
ALL_REGIME_CELLS.append("GRINDING")


def _strategies_in_regime_cell(cell: str) -> list[str]:
    """Return strategy IDs active in a given regime cell."""
    active = []
    for s in STRATEGIES:
        # Check exact match in preferred list
        if cell in s["regime_preferred"]:
            active.append(s["id"])
            continue
        # Check partial match for broad niche keywords
        for niche in s["regime_niche"]:
            if niche == "BROAD":
                active.append(s["id"])
                break
            if niche == "GRINDING" and cell == "GRINDING":
                active.append(s["id"])
                break
            # Partial: e.g. "TRENDING" matches "NORMAL_TRENDING_LOW_RV"
            if niche != "BROAD" and niche != "GRINDING" and niche in cell:
                active.append(s["id"])
                break
    return list(dict.fromkeys(active))  # dedupe preserving order


def build_genome_data() -> dict:
    """Build the full genome map data structure."""

    # Entry type classification
    entry_types = {}
    for s in STRATEGIES:
        entry_types.setdefault(s["entry_type"], []).append(s["id"])

    # Holding period spectrum
    hold_classes = {}
    for s in STRATEGIES:
        label = {
            "scalp": f"Scalp (1-5 bars)",
            "swing": f"Swing (5-30 bars)",
            "trend": f"Trend (30+ bars)",
        }[s["hold_class"]]
        hold_classes.setdefault(label, []).append(
            {"id": s["id"], "bars": s["hold_bars"]}
        )

    # Regime niche map (grid)
    regime_grid = {}
    covered_cells = 0
    thin_cells = []
    missing_cells = []
    for cell in ALL_REGIME_CELLS:
        active = _strategies_in_regime_cell(cell)
        regime_grid[cell] = active
        if len(active) >= 2:
            covered_cells += 1
        elif len(active) == 1:
            covered_cells += 1
            thin_cells.append(cell)
        else:
            missing_cells.append(cell)

    # Asset distribution
    asset_dist = {}
    for s in STRATEGIES:
        asset_dist.setdefault(s["asset"], []).append(
            {"id": s["id"], "side": s["side"]}
        )

    # Side balance
    long_strats = [s["id"] for s in STRATEGIES if s["side"] == "long"]
    short_strats = [s["id"] for s in STRATEGIES if s["side"] == "short"]

    # Portfolio gaps
    existing_entries = set(s["entry_type"] for s in STRATEGIES)
    missing_entries = [t for t in ["overnight", "event_driven", "session_profile"]
                       if t not in existing_entries]

    existing_assets_sides = set((s["asset"], s["side"]) for s in STRATEGIES)
    all_combos = [(a, sd) for a in ["MES", "MNQ", "MGC"] for sd in ["long", "short"]]
    missing_asset_sides = [f"{a}-{sd}" for a, sd in all_combos
                           if (a, sd) not in existing_assets_sides]

    # Overlap warnings
    overlaps = []
    # Pullback overlap
    pb_strats = [s["id"] for s in STRATEGIES if s["entry_type"] == "pullback"]
    if len(pb_strats) > 1:
        overlaps.append({
            "strategies": pb_strats,
            "dimension": "entry_type",
            "value": "pullback",
            "mitigant": "Different assets and sides (MGC-short vs MES-short)",
        })
    # Breakout overlap
    bo_strats = [s["id"] for s in STRATEGIES if s["entry_type"] == "breakout"]
    if len(bo_strats) > 1:
        overlaps.append({
            "strategies": bo_strats,
            "dimension": "entry_type",
            "value": "breakout",
            "mitigant": "Different holding periods (28b vs 60b) and assets (MGC vs MNQ)",
        })

    # Diversity score
    unique_entries = len(set(s["entry_type"] for s in STRATEGIES))
    total_strats = len(STRATEGIES)
    unique_hold_classes = len(set(s["hold_class"] for s in STRATEGIES))
    unique_assets = len(set(s["asset"] for s in STRATEGIES))
    total_cells = len(ALL_REGIME_CELLS)
    covered = sum(1 for v in regime_grid.values() if v)

    def _grade(ratio):
        if ratio >= 0.9:
            return "EXCELLENT"
        if ratio >= 0.7:
            return "GOOD"
        if ratio >= 0.5:
            return "MODERATE"
        return "WEAK"

    diversity = {
        "entry_diversity": {
            "unique": unique_entries, "total": total_strats,
            "grade": _grade(unique_entries / total_strats)
        },
        "holding_diversity": {
            "unique": unique_hold_classes, "total": 3,
            "grade": _grade(unique_hold_classes / 3)
        },
        "asset_coverage": {
            "unique": unique_assets, "total": 3,
            "grade": _grade(unique_assets / 3)
        },
        "regime_coverage": {
            "covered": covered, "total": total_cells,
            "grade": _grade(covered / total_cells)
        },
    }

    # Overall grade
    grades = [d["grade"] for d in diversity.values()]
    grade_scores = {"EXCELLENT": 4, "GOOD": 3, "MODERATE": 2, "WEAK": 1}
    avg_score = sum(grade_scores[g] for g in grades) / len(grades)
    if avg_score >= 3.5:
        overall = "STRONG DIVERSIFICATION"
    elif avg_score >= 2.5:
        overall = "GOOD DIVERSIFICATION"
    elif avg_score >= 1.5:
        overall = "MODERATE DIVERSIFICATION"
    else:
        overall = "WEAK DIVERSIFICATION"
    diversity["overall"] = overall

    return {
        "strategies": [
            {k: v for k, v in s.items()}
            for s in STRATEGIES
        ],
        "entry_types": entry_types,
        "holding_periods": hold_classes,
        "regime_grid": regime_grid,
        "asset_distribution": asset_dist,
        "side_balance": {"long": long_strats, "short": short_strats},
        "gaps": {
            "missing_entry_types": missing_entries,
            "missing_holding": ["ultra-short (<1 bar)", "multi-day (200+ bars)"],
            "missing_regimes": missing_cells,
            "structural_gap": "HIGH_VOL_TRENDING_LOW_RV (wide stops + small moves contradiction)",
            "missing_asset_sides": missing_asset_sides,
            "side_imbalance": f"{len(long_strats)} long vs {len(short_strats)} short",
        },
        "overlaps": overlaps,
        "diversity": diversity,
    }


# ── Terminal report ──────────────────────────────────────────────────────────

def _short_id(sid: str) -> str:
    """Shorten strategy IDs for display."""
    return (sid
            .replace("-MGC-Short", "")
            .replace("-MGC-Long", "")
            .replace("-MNQ-Long", "")
            .replace("-MES-Short", ""))


def print_report(data: dict) -> None:
    W = 70
    SEP = "=" * W
    THIN = "-" * 38

    print()
    print(SEP)
    print("  STRATEGY GENOME MAP")
    print(SEP)

    # Entry Type Classification
    print()
    print("  ENTRY TYPE CLASSIFICATION")
    print(f"  {THIN}")
    entry_labels = {
        "pullback": "Pullback",
        "breakout": "Breakout",
        "trend_continuation": "Trend Continuation",
        "mean_reversion": "Mean Reversion",
    }
    for etype, label in entry_labels.items():
        strats = data["entry_types"].get(etype, [])
        if strats:
            print(f"  {label + ':':22s} {', '.join(strats)}")

    # Holding Period Spectrum
    print()
    print("  HOLDING PERIOD SPECTRUM")
    print(f"  {THIN}")
    for label in ["Scalp (1-5 bars)", "Swing (5-30 bars)", "Trend (30+ bars)"]:
        entries = data["holding_periods"].get(label, [])
        if entries:
            descs = [f"{e['id']} ({e['bars']}b)" for e in entries]
            print(f"  {label + ':':22s} {', '.join(descs)}")

    # Regime Niche Map (grid format)
    print()
    print("  REGIME NICHE MAP")
    print(f"  {THIN}")

    # Build a readable grid: vol x trend x rv
    col_width = 28
    header = f"  {'':22s} {'LOW_RV':^{col_width}s} {'HIGH_RV':^{col_width}s}"
    print(header)
    print(f"  {'':22s} {'-' * col_width:s} {'-' * col_width:s}")

    for vol in VOL_REGIMES:
        for trend in TREND_REGIMES:
            row_label = f"{vol}_{trend}"
            low_rv_cell = f"{vol}_{trend}_LOW_RV"
            high_rv_cell = f"{vol}_{trend}_HIGH_RV"
            low_rv = data["regime_grid"].get(low_rv_cell, [])
            high_rv = data["regime_grid"].get(high_rv_cell, [])

            low_str = ", ".join(_short_id(s) for s in low_rv) if low_rv else "---"
            high_str = ", ".join(_short_id(s) for s in high_rv) if high_rv else "---"

            print(f"  {row_label:22s} {low_str:<{col_width}s} {high_str:<{col_width}s}")

    # GRINDING special row
    grinding = data["regime_grid"].get("GRINDING", [])
    g_str = ", ".join(_short_id(s) for s in grinding) if grinding else "---"
    print(f"  {'GRINDING':22s} {g_str}")

    # Asset Distribution
    print()
    print("  ASSET DISTRIBUTION")
    print(f"  {THIN}")
    for asset in ["MGC", "MNQ", "MES"]:
        entries = data["asset_distribution"].get(asset, [])
        if entries:
            descs = [f"{_short_id(e['id'])} ({e['side']})" for e in entries]
            print(f"  {asset + ':':22s} {', '.join(descs)}")

    # Side Balance
    print()
    print("  SIDE BALANCE")
    print(f"  {THIN}")
    sb = data["side_balance"]
    print(f"  Long:                 {len(sb['long'])} strategies ({', '.join(_short_id(s) for s in sb['long'])})")
    print(f"  Short:                {len(sb['short'])} strategies ({', '.join(_short_id(s) for s in sb['short'])})")

    # Portfolio Gaps
    print()
    print("  PORTFOLIO GAPS")
    print(f"  {THIN}")
    gaps = data["gaps"]
    print(f"  Missing entry types:  {', '.join(gaps['missing_entry_types']) or 'None'}")
    print(f"  Missing holding:      {', '.join(gaps['missing_holding'])}")
    print(f"  Missing regimes:      {len(gaps['missing_regimes'])} cells")
    for cell in gaps["missing_regimes"]:
        print(f"    - {cell}")
    print(f"  Structural gap:       {gaps['structural_gap']}")
    print(f"  Missing asset/sides:  {', '.join(gaps['missing_asset_sides']) or 'None'}")
    print(f"  Side imbalance:       {gaps['side_imbalance']}")

    # Overlap Warnings
    print()
    print("  OVERLAP WARNINGS")
    print(f"  {THIN}")
    if data["overlaps"]:
        for o in data["overlaps"]:
            strats = " + ".join(o["strategies"])
            print(f"  {strats}")
            print(f"    Both {o['value']} entries")
            print(f"    Mitigant: {o['mitigant']}")
    else:
        print("  No significant overlaps detected.")

    # Diversity Score
    print()
    print("  DIVERSITY SCORE")
    print(f"  {THIN}")
    div = data["diversity"]
    e = div["entry_diversity"]
    print(f"  Entry diversity:      {e['unique']}/{e['total']} unique types     ({e['grade']})")
    h = div["holding_diversity"]
    print(f"  Holding diversity:    {h['unique']}/{h['total']} time classes     ({h['grade']})")
    a = div["asset_coverage"]
    print(f"  Asset coverage:       {a['unique']}/{a['total']} assets           ({a['grade']})")
    r = div["regime_coverage"]
    print(f"  Regime coverage:      {r['covered']}/{r['total']} cells           ({r['grade']})")
    print(f"  Overall:              {div['overall']}")

    print()
    print(SEP)
    print()


# ── Enrichment: attempt to read existing data sources ────────────────────────

def _try_load_json(path: Path) -> dict | None:
    """Attempt to load a JSON file, return None if missing."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def enrich_from_files(data: dict) -> dict:
    """Optionally enrich genome map with data from existing research files.

    This is best-effort — the core map works from hardcoded data alone.
    """
    # Try loading DNA catalog for additional structural info
    dna = _try_load_json(ROOT / "research" / "dna" / "dna_catalog.json")
    if dna:
        data["_sources"] = data.get("_sources", [])
        data["_sources"].append("research/dna/dna_catalog.json")

    # Try loading regime profiles
    regime = _try_load_json(ROOT / "research" / "regime" / "strategy_regime_profiles.json")
    if regime:
        data["_sources"] = data.get("_sources", [])
        data["_sources"].append("research/regime/strategy_regime_profiles.json")

    # Try loading Phase 16 results
    p16 = _try_load_json(ROOT / "research" / "phase16_strategy_controller_results.json")
    if p16:
        data["_sources"] = data.get("_sources", [])
        data["_sources"].append("research/phase16_strategy_controller_results.json")

    return data


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Strategy Genome Map — classify and visualize validated strategies"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON instead of terminal report")
    parser.add_argument("--save", action="store_true",
                        help="Save JSON to research/strategy_genome_map.json")
    args = parser.parse_args()

    data = build_genome_data()
    data = enrich_from_files(data)

    if args.json:
        print(json.dumps(data, indent=2))
    elif args.save:
        out_path = ROOT / "research" / "strategy_genome_map.json"
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Saved to {out_path}")
    else:
        print_report(data)


if __name__ == "__main__":
    main()
