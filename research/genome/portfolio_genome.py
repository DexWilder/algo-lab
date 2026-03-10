"""Portfolio Genome — Detect redundancy, gaps, concentration risk.

Loads strategy genomes and performs portfolio-level analysis:
- Engine type coverage and gaps
- Behavioral similarity matrix
- Regime concentration risk
- Diversification score
- Automated research target generation

Usage:
    python3 research/genome/portfolio_genome.py
    python3 research/genome/portfolio_genome.py --parents-only
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

GENOME_DIR = Path(__file__).resolve().parent
GENOME_FILE = GENOME_DIR / "strategy_genomes.json"


# All known engine types in a systematic trading portfolio
ALL_ENGINE_TYPES = [
    "pullback_scalper",
    "momentum_scalper",
    "breakout",
    "trend_continuation",
    "trend_follower",
    "mean_reversion",
    "counter_trend",
    "session_structure",
    "volatility_compression",
    "overnight_gap",
    "hybrid",
]

# 18 regime cells
REGIME_CELLS = [
    f"{vol}_{trend}_{rv}"
    for vol in ["LOW_VOL", "NORMAL", "HIGH_VOL"]
    for trend in ["TRENDING", "RANGING"]
    for rv in ["LOW_RV", "NORMAL_RV", "HIGH_RV"]
]


def load_genomes(parents_only: bool = False) -> dict:
    if not GENOME_FILE.exists():
        print(f"  ERROR: No genomes found. Run strategy_genome.py first.")
        sys.exit(1)
    with open(GENOME_FILE) as f:
        genomes = json.load(f)
    if parents_only:
        genomes = {k: v for k, v in genomes.items()
                   if v.get("status") in ("parent", "probation")}
    return genomes


def compute_similarity(g1: dict, g2: dict) -> float:
    """Behavioral similarity score (0-1). Higher = more similar."""
    features = []

    # Hold time similarity (normalized)
    h1 = g1["hold_characteristics"]["median_hold_bars"]
    h2 = g2["hold_characteristics"]["median_hold_bars"]
    max_hold = max(h1, h2, 1)
    features.append(1.0 - abs(h1 - h2) / max_hold)

    # Win rate similarity
    wr1 = g1["trade_structure"]["win_rate"]
    wr2 = g2["trade_structure"]["win_rate"]
    features.append(1.0 - abs(wr1 - wr2))

    # Trend sensitivity similarity
    ts1 = g1["market_sensitivity"]["trend_sensitivity"]
    ts2 = g2["market_sensitivity"]["trend_sensitivity"]
    features.append(1.0 - abs(ts1 - ts2) / 2.0)

    # Volatility sensitivity similarity
    vs1 = g1["market_sensitivity"]["volatility_sensitivity"]
    vs2 = g2["market_sensitivity"]["volatility_sensitivity"]
    features.append(1.0 - abs(vs1 - vs2) / 2.0)

    # RV sensitivity similarity
    rs1 = g1["market_sensitivity"]["rv_sensitivity"]
    rs2 = g2["market_sensitivity"]["rv_sensitivity"]
    features.append(1.0 - abs(rs1 - rs2) / 2.0)

    # Engine type match bonus
    if g1["engine_type"] == g2["engine_type"]:
        features.append(1.0)
    else:
        features.append(0.0)

    # Trade density similarity
    td1 = g1["trade_structure"]["trades_per_day"]
    td2 = g2["trade_structure"]["trades_per_day"]
    max_td = max(td1, td2, 0.01)
    features.append(1.0 - abs(td1 - td2) / max_td)

    # Payoff ratio similarity
    pr1 = g1["trade_structure"]["payoff_ratio"]
    pr2 = g2["trade_structure"]["payoff_ratio"]
    max_pr = max(pr1, pr2, 0.01)
    features.append(1.0 - abs(pr1 - pr2) / max_pr)

    return round(np.mean(features), 3)


def analyze_portfolio(genomes: dict):
    """Full portfolio genome analysis."""
    names = list(genomes.keys())
    n = len(names)

    print(f"\n{'='*74}")
    print(f"  PORTFOLIO GENOME ANALYSIS")
    print(f"{'='*74}")
    print(f"  Strategies analyzed: {n}")

    # ── 1. Engine Type Coverage ────────────────────────────────────────
    print(f"\n  ENGINE TYPE COVERAGE")
    print(f"  {'-'*50}")

    present_engines = set()
    engine_strats = {}
    for name, g in genomes.items():
        et = g["engine_type"]
        present_engines.add(et)
        engine_strats.setdefault(et, []).append(name)

    for et in ALL_ENGINE_TYPES:
        strats = engine_strats.get(et, [])
        if strats:
            status = "COVERED" if len(strats) == 1 else f"OVERLAP ({len(strats)})"
            print(f"    {et:<25} {status:<12} {', '.join(strats)}")
        else:
            print(f"    {et:<25} {'MISSING':<12} ← research target")

    missing_engines = [et for et in ALL_ENGINE_TYPES
                       if et not in present_engines and et != "hybrid"]
    overlapping = {et: strats for et, strats in engine_strats.items() if len(strats) > 1}

    # ── 2. Behavioral Similarity Matrix ────────────────────────────────
    print(f"\n  BEHAVIORAL SIMILARITY MATRIX")
    print(f"  {'-'*50}")

    sim_matrix = {}
    redundant_pairs = []

    # Header
    short_names = {n: n[:8] for n in names}
    header = f"  {'':>12} " + " ".join(f"{short_names[n]:>8}" for n in names)
    print(header)

    for i, n1 in enumerate(names):
        row = f"  {short_names[n1]:>12} "
        for j, n2 in enumerate(names):
            if i == j:
                row += f"{'—':>8} "
            elif j > i:
                sim = compute_similarity(genomes[n1], genomes[n2])
                sim_matrix[(n1, n2)] = sim
                if sim > 0.75:
                    redundant_pairs.append((n1, n2, sim))
                row += f"{sim:>8.3f} "
            else:
                sim = sim_matrix.get((n2, n1), 0)
                row += f"{sim:>8.3f} "
        print(row)

    # ── 3. Redundancy Detection ────────────────────────────────────────
    print(f"\n  REDUNDANCY DETECTION")
    print(f"  {'-'*50}")

    if redundant_pairs:
        redundant_pairs.sort(key=lambda x: x[2], reverse=True)
        for n1, n2, sim in redundant_pairs:
            print(f"    WARNING: {n1} ↔ {n2} similarity={sim:.3f}")
            print(f"             Both are {genomes[n1]['engine_type']} / {genomes[n2]['engine_type']}")
    else:
        print(f"    No redundant pairs detected (threshold > 0.75)")

    # ── 4. Regime Concentration Risk ───────────────────────────────────
    print(f"\n  REGIME CONCENTRATION RISK")
    print(f"  {'-'*50}")

    # Aggregate PnL by regime cell across all strategies
    cell_pnl = {}
    cell_strat_count = {}
    for name, g in genomes.items():
        for cell, data in g["regime_performance"]["pnl_by_regime_cell"].items():
            cell_pnl[cell] = cell_pnl.get(cell, 0) + data["pnl"]
            if data["pnl"] > 0:
                cell_strat_count.setdefault(cell, set()).add(name)

    total_portfolio_pnl = sum(v for v in cell_pnl.values() if v > 0)
    if total_portfolio_pnl > 0:
        # Find concentrated cells (>25% of portfolio PnL)
        concentrated = []
        for cell, pnl in sorted(cell_pnl.items(), key=lambda x: x[1], reverse=True):
            share = pnl / total_portfolio_pnl if total_portfolio_pnl > 0 else 0
            strats = cell_strat_count.get(cell, set())
            if share > 0.15:
                concentrated.append((cell, pnl, share, strats))
                risk = "HIGH" if share > 0.25 else "MODERATE"
                print(f"    {risk}: {cell}")
                print(f"           PnL share: {share:.1%}, Strategies: {', '.join(strats)}")

        if not concentrated:
            print(f"    No concentrated regime cells (all < 15% of PnL)")

    # ── 5. Asset Diversification ───────────────────────────────────────
    print(f"\n  ASSET DIVERSIFICATION")
    print(f"  {'-'*50}")

    asset_strats = {}
    for name, g in genomes.items():
        asset = g["asset"]
        asset_strats.setdefault(asset, []).append(name)

    for asset in ["MES", "MNQ", "MGC"]:
        strats = asset_strats.get(asset, [])
        if strats:
            print(f"    {asset}: {len(strats)} strategies — {', '.join(strats)}")
        else:
            print(f"    {asset}: NONE ← asset gap")

    # ── 6. Diversification Score ───────────────────────────────────────
    print(f"\n  PORTFOLIO DIVERSIFICATION SCORE")
    print(f"  {'-'*50}")

    # Components:
    scores = {}

    # Engine diversity (unique engine types / total possible)
    unique_engines = len(present_engines - {"hybrid"})
    scores["engine_diversity"] = min(unique_engines / 6, 1.0)  # Cap at 6 types

    # Asset coverage (unique assets / 3)
    unique_assets = len(asset_strats)
    scores["asset_coverage"] = unique_assets / 3

    # Behavioral spread (avg pairwise distance = 1 - similarity)
    if sim_matrix:
        avg_distance = 1.0 - np.mean(list(sim_matrix.values()))
        scores["behavioral_spread"] = avg_distance
    else:
        scores["behavioral_spread"] = 0

    # Regime coverage (cells with positive PnL / total cells)
    positive_cells = sum(1 for v in cell_pnl.values() if v > 0)
    scores["regime_coverage"] = positive_cells / len(REGIME_CELLS)

    # No redundancy bonus
    scores["no_redundancy"] = 1.0 if not redundant_pairs else max(0, 1.0 - 0.2 * len(redundant_pairs))

    overall = round(np.mean(list(scores.values())) * 10, 1)
    for component, score in scores.items():
        print(f"    {component:<25} {score:.2f}")
    print(f"    {'─' * 35}")
    print(f"    {'OVERALL':.<25} {overall:.1f}/10")

    # ── 7. Research Targets ────────────────────────────────────────────
    print(f"\n{'='*74}")
    print(f"  RESEARCH TARGETS (auto-generated)")
    print(f"{'='*74}")

    targets = []
    for et in missing_engines:
        targets.append(f"  → Build {et} strategy (engine gap)")

    # Regime gaps
    thin_cells = [cell for cell, pnl in cell_pnl.items()
                  if pnl <= 0 or cell_strat_count.get(cell, set()) == set()]
    missing_cells = [cell for cell in REGIME_CELLS if cell not in cell_pnl]
    for cell in (missing_cells + thin_cells)[:5]:
        targets.append(f"  → Find strategy for {cell} regime cell")

    # Asset gaps
    for asset in ["MES", "MNQ", "MGC"]:
        if asset not in asset_strats:
            targets.append(f"  → Develop {asset} strategy (asset gap)")

    if targets:
        for t in targets:
            print(t)
    else:
        print(f"  No critical gaps identified")

    # ── Save Report ────────────────────────────────────────────────────
    report = {
        "strategies_analyzed": n,
        "engine_coverage": {
            "present": list(present_engines),
            "missing": missing_engines,
            "overlapping": {k: v for k, v in overlapping.items()},
        },
        "similarity_matrix": {f"{k[0]}_vs_{k[1]}": v for k, v in sim_matrix.items()},
        "redundant_pairs": [(n1, n2, sim) for n1, n2, sim in redundant_pairs],
        "regime_concentration": {
            cell: {"pnl": pnl, "share": pnl / total_portfolio_pnl if total_portfolio_pnl > 0 else 0}
            for cell, pnl in sorted(cell_pnl.items(), key=lambda x: x[1], reverse=True)[:10]
        },
        "diversification_scores": scores,
        "overall_score": overall,
        "research_targets": targets,
    }

    output_path = GENOME_DIR / "portfolio_genome_report.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Saved report to {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Portfolio Genome Analyzer")
    parser.add_argument("--parents-only", action="store_true",
                        help="Only analyze parent/probation strategies")
    args = parser.parse_args()

    genomes = load_genomes(parents_only=args.parents_only)
    analyze_portfolio(genomes)


if __name__ == "__main__":
    main()
