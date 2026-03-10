"""Portfolio Fitness Function — Phase 9.5.

Scores evolution candidates by portfolio contribution rather than standalone PF.
Reusable by the evolution scheduler and by ad-hoc analysis.

Scoring components (weights sum to 1.0):
  - pnl_contribution (0.25): Does adding this strategy increase total PnL?
  - correlation_benefit (0.25): Is the candidate uncorrelated with existing strategies?
  - drawdown_improvement (0.20): Does the candidate reduce MaxDD / improve Calmar?
  - regime_coverage (0.20): Does it fill gaps in the regime coverage map?
  - monthly_consistency (0.10): Does it improve profitable month %?

Score thresholds:
  7-10: portfolio_star — clear portfolio improver, promote
  4-7:  portfolio_useful — marginal, needs further analysis
  0-4:  portfolio_redundant — doesn't help portfolio, reject unless standalone PF exceptional

Usage:
    from research.evolution.portfolio_fitness import compute_portfolio_fitness

    score = compute_portfolio_fitness(candidate_trades, baseline_daily_pnl)
"""

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from research.evolution.portfolio_comparison import (
    build_daily_pnl,
    compute_portfolio_metrics,
    load_data,
    load_module,
    ASSET_CONFIG,
)
from engine.backtest import run_backtest

# ── Baseline configuration ──────────────────────────────────────────────────

BASELINE_STRATEGIES = {
    "PB-MGC-Short": {
        "module_path": PROJECT_ROOT / "strategies" / "pb_trend" / "strategy.py",
        "asset": "MGC",
        "mode": "short",
    },
    "ORB-009-MGC-Long": {
        "module_path": PROJECT_ROOT / "strategies" / "orb_009" / "strategy.py",
        "asset": "MGC",
        "mode": "long",
    },
}

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REGIME_COVERAGE_PATH = PROJECT_ROOT / "research" / "regime" / "regime_coverage.json"

# ── Component weights ────────────────────────────────────────────────────────

WEIGHTS = {
    "pnl_contribution": 0.25,
    "correlation_benefit": 0.25,
    "drawdown_improvement": 0.20,
    "regime_coverage": 0.20,
    "monthly_consistency": 0.10,
}


# ── Baseline loading ────────────────────────────────────────────────────────

_baseline_cache = {}


def load_baseline_daily_pnl() -> dict[str, pd.Series]:
    """Load (or cache) baseline strategies' daily PnL series.

    Returns dict mapping strategy name to daily PnL pd.Series.
    """
    if _baseline_cache:
        return _baseline_cache

    for name, cfg in BASELINE_STRATEGIES.items():
        asset = cfg["asset"]
        mode = cfg["mode"]
        acfg = ASSET_CONFIG[asset]

        df = load_data(asset)
        mod = load_module(name, cfg["module_path"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = acfg["tick_size"]

        sig = inspect.signature(mod.generate_signals)
        if "asset" in sig.parameters:
            signals = mod.generate_signals(df, asset=asset)
        else:
            signals = mod.generate_signals(df)

        result = run_backtest(
            df, signals,
            mode=mode,
            point_value=acfg["point_value"],
            symbol=asset,
        )
        _baseline_cache[name] = build_daily_pnl(result["trades_df"])

    return _baseline_cache


# ── Scoring components ──────────────────────────────────────────────────────

def _score_pnl_contribution(
    candidate_daily: pd.Series,
    baseline_daily_pnl: dict[str, pd.Series],
) -> float:
    """Score 0-10: how much PnL the candidate adds to the portfolio."""
    # Build baseline portfolio daily PnL
    combined = pd.DataFrame(baseline_daily_pnl).fillna(0)
    baseline_total = combined.sum(axis=1).sort_index()
    baseline_pnl = baseline_total.sum()

    # Build portfolio with candidate
    with_cand = combined.copy()
    with_cand["candidate"] = candidate_daily
    with_cand = with_cand.fillna(0)
    portfolio_total = with_cand.sum(axis=1).sort_index()
    portfolio_pnl = portfolio_total.sum()

    if baseline_pnl <= 0:
        return 5.0 if portfolio_pnl > 0 else 0.0

    # Relative PnL increase
    pnl_increase = (portfolio_pnl - baseline_pnl) / abs(baseline_pnl)

    # Scale: 0% → 0, 50% → 5, 100%+ → 10
    score = min(10.0, max(0.0, pnl_increase * 10.0))
    return round(score, 2)


def _score_correlation_benefit(
    candidate_daily: pd.Series,
    baseline_daily_pnl: dict[str, pd.Series],
) -> float:
    """Score 0-10: how uncorrelated the candidate is with existing strategies."""
    if not baseline_daily_pnl:
        return 10.0

    all_series = {**baseline_daily_pnl, "candidate": candidate_daily}
    combined = pd.DataFrame(all_series).fillna(0)

    # Need enough overlapping data
    if len(combined) < 10:
        return 5.0

    corr_matrix = combined.corr()

    # Max absolute correlation between candidate and any existing strategy
    max_abs_corr = 0.0
    for name in baseline_daily_pnl:
        c = abs(corr_matrix.loc["candidate", name])
        if c > max_abs_corr:
            max_abs_corr = c

    # Score: corr=0 → 10, corr=0.5 → 5, corr=1.0 → 0
    score = max(0.0, (1.0 - max_abs_corr) * 10.0)
    return round(score, 2)


def _score_drawdown_improvement(
    candidate_daily: pd.Series,
    baseline_daily_pnl: dict[str, pd.Series],
) -> float:
    """Score 0-10: does the candidate improve Calmar / reduce MaxDD?"""
    # Baseline portfolio metrics
    combined = pd.DataFrame(baseline_daily_pnl).fillna(0)
    baseline_total = combined.sum(axis=1).sort_index()
    baseline_m = compute_portfolio_metrics(baseline_total)

    # Portfolio with candidate
    with_cand = combined.copy()
    with_cand["candidate"] = candidate_daily
    with_cand = with_cand.fillna(0)
    portfolio_total = with_cand.sum(axis=1).sort_index()
    portfolio_m = compute_portfolio_metrics(portfolio_total)

    # Signal 1: Calmar improvement
    b_calmar = baseline_m["calmar"]
    p_calmar = portfolio_m["calmar"]
    if b_calmar > 0:
        calmar_signal = (p_calmar - b_calmar) / b_calmar
    else:
        calmar_signal = 1.0 if p_calmar > 0 else 0.0

    # Signal 2: MaxDD reduction (positive when DD falls)
    b_dd = baseline_m["max_dd"]
    p_dd = portfolio_m["max_dd"]
    if b_dd > 0:
        dd_signal = (b_dd - p_dd) / b_dd
    else:
        dd_signal = 0.0

    # Average of both signals, clamped to [0, 1]
    avg_signal = max(0.0, min(1.0, (calmar_signal + dd_signal) / 2.0))

    score = avg_signal * 10.0
    return round(score, 2)


def _score_regime_coverage(
    candidate_trades: pd.DataFrame,
    regime_coverage: dict | None = None,
) -> float:
    """Score 0-10: does the candidate fill gaps in regime coverage?

    Uses trade dates → regime labels → check against coverage map.
    Minimum evidence: ≥15 trades in a cell to count, or clear upgrade
    (MISSING→COVERED, THIN→COVERED).
    """
    if regime_coverage is None:
        # Try loading from disk
        if REGIME_COVERAGE_PATH.exists():
            with open(REGIME_COVERAGE_PATH) as f:
                regime_coverage = json.load(f)
        else:
            return 5.0  # No coverage map available, neutral score

    if candidate_trades.empty:
        return 0.0

    # Identify gap cells
    cells = regime_coverage.get("cells", [])
    gap_cells = [
        c for c in cells
        if c.get("coverage") in ("MISSING", "THIN")
    ]
    if not gap_cells:
        return 5.0  # No gaps to fill

    # Get candidate trade dates
    trade_dates = pd.to_datetime(candidate_trades["exit_time"]).dt.date.tolist()
    if not trade_dates:
        return 0.0

    # Load regime labels for the candidate's asset
    # We need regime data — get from the coverage map's cell data
    # Match trade dates against regime cells
    try:
        from engine.regime_engine import RegimeEngine

        # Determine asset from trades (use the first entry_price magnitude as heuristic)
        # Or load all assets and match dates
        # Load MES data as default (covers all trading dates)
        df = load_data("MES")
        engine = RegimeEngine()
        daily_regimes = engine.get_daily_regimes(df)
        daily_regimes["_date"] = pd.to_datetime(daily_regimes["_date"]).dt.date

        # Build lookup: date → (vol, trend, rv)
        regime_lookup = {}
        for _, row in daily_regimes.iterrows():
            regime_lookup[row["_date"]] = {
                "vol_regime": row["vol_regime"],
                "trend_regime": row["trend_regime"],
                "rv_regime": row["rv_regime"],
            }

        # Count trades per regime cell
        cell_trade_counts = {}
        for dt in trade_dates:
            regime = regime_lookup.get(dt)
            if regime is None:
                continue
            cell_key = f"{regime['vol_regime']}_{regime['trend_regime']}_{regime['rv_regime']}"
            cell_trade_counts[cell_key] = cell_trade_counts.get(cell_key, 0) + 1

        # Check which gap cells the candidate trades in with sufficient evidence
        qualified_cells = 0
        for gap_cell in gap_cells:
            cell_key = f"{gap_cell['vol_regime']}_{gap_cell['trend_regime']}_{gap_cell['rv_regime']}"
            trades_in_cell = cell_trade_counts.get(cell_key, 0)

            coverage_level = gap_cell.get("coverage", "MISSING")
            if coverage_level == "MISSING" and trades_in_cell >= 5:
                # Even a few trades in a MISSING cell is valuable
                qualified_cells += 1
            elif coverage_level == "THIN" and trades_in_cell >= 15:
                # Need more evidence to upgrade THIN → COVERED
                qualified_cells += 1

        total_gap_cells = len(gap_cells)
        score = (qualified_cells / total_gap_cells) * 10.0 if total_gap_cells > 0 else 5.0

    except Exception:
        # Fallback if regime engine fails
        score = 5.0

    return round(score, 2)


def _score_monthly_consistency(
    candidate_daily: pd.Series,
    baseline_daily_pnl: dict[str, pd.Series],
) -> float:
    """Score 0-10: delta in profitable months percentage."""
    # Baseline
    combined = pd.DataFrame(baseline_daily_pnl).fillna(0)
    baseline_total = combined.sum(axis=1).sort_index()
    baseline_m = compute_portfolio_metrics(baseline_total)

    # With candidate
    with_cand = combined.copy()
    with_cand["candidate"] = candidate_daily
    with_cand = with_cand.fillna(0)
    portfolio_total = with_cand.sum(axis=1).sort_index()
    portfolio_m = compute_portfolio_metrics(portfolio_total)

    # Delta in profitable months %
    delta = portfolio_m["profitable_months_pct"] - baseline_m["profitable_months_pct"]

    # Scale: -10% delta → 0, 0% → 5, +10% → 10
    score = max(0.0, min(10.0, 5.0 + delta / 2.0))
    return round(score, 2)


# ── Main scoring function ───────────────────────────────────────────────────

def compute_portfolio_fitness(
    candidate_trades: pd.DataFrame,
    baseline_daily_pnl: dict[str, pd.Series] | None = None,
    regime_coverage: dict | None = None,
) -> dict:
    """Score a candidate's portfolio contribution.

    Parameters
    ----------
    candidate_trades : pd.DataFrame
        Candidate's trades_df from backtest (columns: entry_time, exit_time, pnl, side, ...).
    baseline_daily_pnl : dict[str, pd.Series] | None
        Existing strategies' daily PnL. If None, loads from baseline strategies.
    regime_coverage : dict | None
        From regime_coverage.json. If None, attempts to load from disk.

    Returns
    -------
    dict with keys:
        score: float (0-10)
        label: str (portfolio_star / portfolio_useful / portfolio_redundant)
        components: dict of {component_name: {score, weight, weighted_score}}
        baseline_strategies: list of baseline strategy names
    """
    if baseline_daily_pnl is None:
        baseline_daily_pnl = load_baseline_daily_pnl()

    # Build candidate daily PnL
    candidate_daily = build_daily_pnl(candidate_trades)

    if candidate_daily.empty:
        return {
            "score": 0.0,
            "label": "portfolio_redundant",
            "components": {},
            "baseline_strategies": list(baseline_daily_pnl.keys()),
        }

    # Compute each component
    components = {}
    total_score = 0.0

    # PnL contribution
    pnl_score = _score_pnl_contribution(candidate_daily, baseline_daily_pnl)
    components["pnl_contribution"] = {
        "score": pnl_score,
        "weight": WEIGHTS["pnl_contribution"],
        "weighted_score": round(pnl_score * WEIGHTS["pnl_contribution"], 3),
    }
    total_score += components["pnl_contribution"]["weighted_score"]

    # Correlation benefit
    corr_score = _score_correlation_benefit(candidate_daily, baseline_daily_pnl)
    components["correlation_benefit"] = {
        "score": corr_score,
        "weight": WEIGHTS["correlation_benefit"],
        "weighted_score": round(corr_score * WEIGHTS["correlation_benefit"], 3),
    }
    total_score += components["correlation_benefit"]["weighted_score"]

    # Drawdown improvement
    dd_score = _score_drawdown_improvement(candidate_daily, baseline_daily_pnl)
    components["drawdown_improvement"] = {
        "score": dd_score,
        "weight": WEIGHTS["drawdown_improvement"],
        "weighted_score": round(dd_score * WEIGHTS["drawdown_improvement"], 3),
    }
    total_score += components["drawdown_improvement"]["weighted_score"]

    # Regime coverage
    regime_score = _score_regime_coverage(candidate_trades, regime_coverage)
    components["regime_coverage"] = {
        "score": regime_score,
        "weight": WEIGHTS["regime_coverage"],
        "weighted_score": round(regime_score * WEIGHTS["regime_coverage"], 3),
    }
    total_score += components["regime_coverage"]["weighted_score"]

    # Monthly consistency
    monthly_score = _score_monthly_consistency(candidate_daily, baseline_daily_pnl)
    components["monthly_consistency"] = {
        "score": monthly_score,
        "weight": WEIGHTS["monthly_consistency"],
        "weighted_score": round(monthly_score * WEIGHTS["monthly_consistency"], 3),
    }
    total_score += components["monthly_consistency"]["weighted_score"]

    total_score = round(total_score, 2)

    # Classify
    if total_score >= 7.0:
        label = "portfolio_star"
    elif total_score >= 4.0:
        label = "portfolio_useful"
    else:
        label = "portfolio_redundant"

    return {
        "score": total_score,
        "label": label,
        "components": components,
        "baseline_strategies": list(baseline_daily_pnl.keys()),
    }


# ── CLI for ad-hoc testing ──────────────────────────────────────────────────

def main():
    """Score a candidate strategy's portfolio fitness."""
    import argparse

    parser = argparse.ArgumentParser(description="Portfolio Fitness Scorer")
    parser.add_argument("--candidate", type=str, required=True,
                        help="Candidate ID (must exist in generated_candidates/)")
    parser.add_argument("--combo", type=str, default=None,
                        help="Asset-mode combo to test (e.g., MNQ-long). Auto-detects best if omitted.")
    args = parser.parse_args()

    CANDIDATES_DIR = PROJECT_ROOT / "research" / "evolution" / "generated_candidates"

    # Load candidate strategy
    cand_path = CANDIDATES_DIR / args.candidate / "strategy.py"
    if not cand_path.exists():
        print(f"ERROR: {cand_path} not found")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location(args.candidate, cand_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Determine combos to test
    if args.combo:
        combos = [args.combo]
    else:
        # Test all and find best
        combos = [
            f"{asset}-{mode}"
            for asset in ["MES", "MNQ", "MGC"]
            for mode in ["long", "short", "both"]
        ]

    print("=" * 60)
    print(f"  PORTFOLIO FITNESS — {args.candidate}")
    print("=" * 60)

    print("\n  Loading baseline strategies...")
    baseline = load_baseline_daily_pnl()
    for name, dpnl in baseline.items():
        print(f"    {name}: {len(dpnl)} trading days, ${dpnl.sum():,.2f} total PnL")

    best_result = None
    best_score = -1
    best_combo_name = ""

    for combo in combos:
        parts = combo.split("-")
        asset = parts[0]
        mode = parts[1]
        acfg = ASSET_CONFIG.get(asset)
        if not acfg:
            continue

        df = load_data(asset)
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = acfg["tick_size"]

        sig = inspect.signature(mod.generate_signals)
        if "asset" in sig.parameters:
            signals = mod.generate_signals(df, asset=asset)
        else:
            signals = mod.generate_signals(df)

        result = run_backtest(
            df, signals,
            mode=mode,
            point_value=acfg["point_value"],
            symbol=asset,
        )

        trades_df = result["trades_df"]
        if trades_df.empty or len(trades_df) < 30:
            continue

        pf = result["stats"]["total_pnl"]
        fitness = compute_portfolio_fitness(trades_df, baseline)

        if fitness["score"] > best_score:
            best_score = fitness["score"]
            best_result = fitness
            best_combo_name = combo

    if best_result is None:
        print("\n  No valid combos found (all < 30 trades)")
        return

    print(f"\n  Best combo: {best_combo_name}")
    print(f"\n  PORTFOLIO FITNESS SCORE: {best_result['score']:.2f} / 10  [{best_result['label']}]")
    print(f"\n  Component Breakdown:")
    print(f"  {'Component':<25} {'Raw':>6} {'Weight':>7} {'Weighted':>9}")
    print(f"  {'-'*25} {'-'*6} {'-'*7} {'-'*9}")
    for name, comp in best_result["components"].items():
        print(f"  {name:<25} {comp['score']:>6.2f} {comp['weight']:>7.2f} {comp['weighted_score']:>9.3f}")

    print(f"\n  Baseline: {', '.join(best_result['baseline_strategies'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
