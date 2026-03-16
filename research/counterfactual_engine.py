#!/usr/bin/env python3
"""FQL Counterfactual / Opportunity-Cost Engine.

Answers the key portfolio question:
    "Did running this strategy improve the portfolio, or did it consume
     capital/exposure/risk that would have been better allocated elsewhere?"

Metrics per strategy:
    1. Marginal Sharpe Contribution  — portfolio Sharpe with vs without
    2. Marginal Drawdown Contribution — portfolio DD with vs without
    3. Overlap Cost                  — correlation drag on portfolio efficiency
    4. Displaced Opportunity Cost    — what stronger sibling could have earned
    5. Slot Efficiency               — risk-adjusted return per risk slot
    6. Blocked-Signal Opportunity    — cost of controller filtering

Usage:
    python3 research/counterfactual_engine.py              # Full report
    python3 research/counterfactual_engine.py --json       # JSON output
    python3 research/counterfactual_engine.py --save       # Save report + log
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
COUNTERFACTUAL_LOG_PATH = ROOT / "research" / "data" / "counterfactual_log.json"
REPORTS_DIR = ROOT / "research" / "reports"

# ── Strategy Universe ────────────────────────────────────────────────────────

from research.portfolio_regime_controller import EVAL_STRATEGIES

STRATEGY_LIST = [s[0] for s in EVAL_STRATEGIES]


# ── Data Loading ─────────────────────────────────────────────────────────────

def build_daily_pnl_matrix() -> pd.DataFrame:
    """Build daily PnL matrix for all strategies using contribution analysis."""
    from research.strategy_contribution_analysis import (
        build_daily_pnl_matrix as _build_matrix,
        PORTFOLIO_STRATEGIES, PROBATION_CANDIDATES,
    )
    all_strategies = list(PORTFOLIO_STRATEGIES) + list(PROBATION_CANDIDATES)
    return _build_matrix(all_strategies)


# ── Marginal Sharpe Contribution ─────────────────────────────────────────────

def compute_marginal_sharpe(matrix: pd.DataFrame) -> dict:
    """Compute marginal Sharpe contribution per strategy.

    For each strategy, compare:
        - Portfolio Sharpe WITH the strategy
        - Portfolio Sharpe WITHOUT the strategy
    """
    if matrix.empty:
        return {}

    # Full portfolio
    portfolio_daily = matrix.sum(axis=1)
    full_sharpe = _annualized_sharpe(portfolio_daily)

    results = {}
    for strat in matrix.columns:
        # Portfolio without this strategy
        without = matrix.drop(columns=[strat]).sum(axis=1)
        without_sharpe = _annualized_sharpe(without)

        marginal = full_sharpe - without_sharpe
        strat_only = _annualized_sharpe(matrix[strat])

        results[strat] = {
            "standalone_sharpe": round(strat_only, 3),
            "portfolio_sharpe_with": round(full_sharpe, 3),
            "portfolio_sharpe_without": round(without_sharpe, 3),
            "marginal_sharpe": round(marginal, 3),
            "verdict": "ADDS_VALUE" if marginal > 0.01 else "DILUTIVE" if marginal < -0.01 else "NEUTRAL",
        }

    return results


# ── Marginal Drawdown Contribution ───────────────────────────────────────────

def compute_marginal_drawdown(matrix: pd.DataFrame) -> dict:
    """Compute marginal max drawdown contribution per strategy."""
    if matrix.empty:
        return {}

    portfolio_daily = matrix.sum(axis=1)
    full_dd = _max_drawdown(portfolio_daily)

    results = {}
    for strat in matrix.columns:
        without = matrix.drop(columns=[strat]).sum(axis=1)
        without_dd = _max_drawdown(without)

        # Positive = strategy reduces DD (good), negative = strategy increases DD
        marginal_dd = without_dd - full_dd

        results[strat] = {
            "portfolio_dd_with": round(full_dd, 2),
            "portfolio_dd_without": round(without_dd, 2),
            "marginal_dd": round(marginal_dd, 2),
            "verdict": "REDUCES_RISK" if marginal_dd > 50 else "INCREASES_RISK" if marginal_dd < -50 else "NEUTRAL",
        }

    return results


# ── Overlap Cost ─────────────────────────────────────────────────────────────

def compute_overlap_cost(matrix: pd.DataFrame) -> dict:
    """Compute correlation-based overlap cost per strategy.

    Measures how much a strategy's returns overlap with the rest of the portfolio,
    reducing diversification benefit.
    """
    if matrix.empty:
        return {}

    results = {}
    for strat in matrix.columns:
        rest = matrix.drop(columns=[strat]).sum(axis=1)
        corr = matrix[strat].corr(rest)
        if np.isnan(corr):
            corr = 0.0

        # Overlap cost: high correlation = high overlap = less diversification
        # Perfect diversification would be corr ≈ 0
        overlap_pct = max(0, corr)  # Only positive correlation is "overlap"

        results[strat] = {
            "correlation_with_portfolio": round(corr, 3),
            "overlap_cost_pct": round(overlap_pct, 3),
            "verdict": "HIGH_OVERLAP" if overlap_pct > 0.50 else "MODERATE_OVERLAP" if overlap_pct > 0.25 else "LOW_OVERLAP",
        }

    return results


# ── Slot Efficiency ──────────────────────────────────────────────────────────

def compute_slot_efficiency(matrix: pd.DataFrame, marginal_sharpe: dict) -> dict:
    """Compute risk-adjusted return per strategy slot.

    Slot efficiency = marginal Sharpe / risk consumed (normalized).
    A strategy that adds 0.1 Sharpe but consumes minimal risk budget is more
    efficient than one that adds 0.2 Sharpe but concentrates exposure.
    """
    if matrix.empty:
        return {}

    # Compute volatility contribution (% of portfolio vol from this strategy)
    portfolio_daily = matrix.sum(axis=1)
    portfolio_vol = portfolio_daily.std()

    results = {}
    for strat in matrix.columns:
        strat_vol = matrix[strat].std()
        vol_share = strat_vol / portfolio_vol if portfolio_vol > 0 else 0

        # PnL share
        total_pnl = matrix.sum().sum()
        strat_pnl = matrix[strat].sum()
        pnl_share = strat_pnl / total_pnl if total_pnl != 0 else 0

        # Marginal Sharpe from earlier computation
        ms = marginal_sharpe.get(strat, {}).get("marginal_sharpe", 0)

        # Efficiency = marginal Sharpe / volatility share
        efficiency = ms / vol_share if vol_share > 0.01 else 0

        results[strat] = {
            "vol_share": round(vol_share, 3),
            "pnl_share": round(pnl_share, 3),
            "marginal_sharpe": round(ms, 3),
            "slot_efficiency": round(efficiency, 3),
            "verdict": "EFFICIENT" if efficiency > 0.5 else "NEUTRAL" if efficiency > -0.1 else "INEFFICIENT",
        }

    return results


# ── Displaced Opportunity Cost ───────────────────────────────────────────────

def compute_displaced_opportunity(matrix: pd.DataFrame, marginal_sharpe: dict) -> dict:
    """Estimate opportunity cost from running a dilutive strategy.

    For dilutive strategies, estimate what a stronger sibling could have earned
    in the same risk slot.
    """
    if matrix.empty:
        return {}

    # Rank strategies by marginal Sharpe
    ranked = sorted(marginal_sharpe.items(), key=lambda x: x[1].get("marginal_sharpe", 0), reverse=True)
    best_marginal = ranked[0][1]["marginal_sharpe"] if ranked else 0

    results = {}
    for strat, ms_data in marginal_sharpe.items():
        ms = ms_data.get("marginal_sharpe", 0)
        if ms < -0.01:  # Dilutive
            # Opportunity cost: what the best sibling could have added instead
            opportunity = best_marginal - ms
            results[strat] = {
                "marginal_sharpe": round(ms, 3),
                "best_sibling_marginal": round(best_marginal, 3),
                "displaced_opportunity": round(opportunity, 3),
                "verdict": "SHOULD_REPLACE" if opportunity > 0.1 else "MARGINAL",
            }
        else:
            results[strat] = {
                "marginal_sharpe": round(ms, 3),
                "verdict": "NO_DISPLACEMENT",
            }

    return results


# ── Blocked Signal Opportunity Cost ──────────────────────────────────────────

def compute_blocked_opportunity() -> dict:
    """Pull blocked-signal data from daily states."""
    daily_states_path = ROOT / "research" / "phase17_paper_trading" / "daily_states.json"
    if not daily_states_path.exists():
        return {"status": "NO_DATA"}

    with open(daily_states_path) as f:
        states = json.load(f)

    total_taken = 0
    total_blocked = 0
    taken_pnl = 0
    blocked_by_strat = {}

    for state in states:
        total_taken += state.get("signals_taken", 0)
        total_blocked += state.get("signals_blocked", 0)
        for trade in state.get("trades_completed", []):
            taken_pnl += trade.get("pnl", 0)
        for strat, reason in state.get("blocked_strategies", {}).items():
            blocked_by_strat.setdefault(strat, 0)
            blocked_by_strat[strat] += 1

    avg_pnl = taken_pnl / total_taken if total_taken > 0 else 0

    return {
        "total_taken": total_taken,
        "total_blocked": total_blocked,
        "retention_rate": round(total_taken / (total_taken + total_blocked), 3) if (total_taken + total_blocked) > 0 else 0,
        "avg_pnl_per_taken": round(avg_pnl, 2),
        "estimated_blocked_cost": round(total_blocked * avg_pnl, 2),
        "blocked_by_strategy": dict(sorted(blocked_by_strat.items(), key=lambda x: -x[1])),
        "note": "Upper bound — blocked signals may have been losing trades",
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _annualized_sharpe(series: pd.Series) -> float:
    """Compute annualized Sharpe ratio from daily PnL."""
    if len(series) < 10 or series.std() == 0:
        return 0.0
    return float((series.mean() / series.std()) * np.sqrt(252))


def _max_drawdown(series: pd.Series) -> float:
    """Compute max drawdown from daily PnL series."""
    cumulative = series.cumsum()
    hwm = cumulative.cummax()
    dd = cumulative - hwm
    return float(abs(dd.min())) if len(dd) > 0 else 0.0


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_counterfactual_engine() -> dict:
    """Run full counterfactual analysis."""
    print("Building daily PnL matrix...")
    matrix = build_daily_pnl_matrix()

    if matrix.empty:
        return {"status": "NO_DATA", "message": "Could not build PnL matrix"}

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("Computing marginal Sharpe contributions...")
    marginal_sharpe = compute_marginal_sharpe(matrix)

    print("Computing marginal drawdown contributions...")
    marginal_dd = compute_marginal_drawdown(matrix)

    print("Computing overlap costs...")
    overlap = compute_overlap_cost(matrix)

    print("Computing slot efficiency...")
    efficiency = compute_slot_efficiency(matrix, marginal_sharpe)

    print("Computing displaced opportunity costs...")
    displaced = compute_displaced_opportunity(matrix, marginal_sharpe)

    print("Computing blocked signal costs...")
    blocked = compute_blocked_opportunity()

    # ── Composite counterfactual score per strategy ──
    composite = {}
    for strat in matrix.columns:
        ms = marginal_sharpe.get(strat, {})
        dd = marginal_dd.get(strat, {})
        ov = overlap.get(strat, {})
        eff = efficiency.get(strat, {})
        dis = displaced.get(strat, {})

        # Score: weighted combination of signals
        score = 0.0
        # Marginal Sharpe (most important)
        ms_val = ms.get("marginal_sharpe", 0)
        if ms_val > 0.01:
            score += 0.40
        elif ms_val < -0.01:
            score -= 0.40

        # Drawdown contribution
        dd_verdict = dd.get("verdict", "NEUTRAL")
        if dd_verdict == "REDUCES_RISK":
            score += 0.20
        elif dd_verdict == "INCREASES_RISK":
            score -= 0.20

        # Overlap
        ov_verdict = ov.get("verdict", "LOW_OVERLAP")
        if ov_verdict == "HIGH_OVERLAP":
            score -= 0.15
        elif ov_verdict == "LOW_OVERLAP":
            score += 0.10

        # Slot efficiency
        eff_verdict = eff.get("verdict", "NEUTRAL")
        if eff_verdict == "EFFICIENT":
            score += 0.15
        elif eff_verdict == "INEFFICIENT":
            score -= 0.15

        # Normalize to [-1, 1]
        score = max(-1.0, min(1.0, score))

        # Recommendation
        if score >= 0.30:
            recommendation = "KEEP_FULL"
        elif score >= 0.0:
            recommendation = "KEEP_REDUCED"
        elif score >= -0.30:
            recommendation = "REVIEW"
        else:
            recommendation = "REMOVE"

        composite[strat] = {
            "counterfactual_score": round(score, 3),
            "recommendation": recommendation,
            "marginal_sharpe_verdict": ms.get("verdict", "UNKNOWN"),
            "drawdown_verdict": dd.get("verdict", "UNKNOWN"),
            "overlap_verdict": ov.get("verdict", "UNKNOWN"),
            "efficiency_verdict": eff.get("verdict", "UNKNOWN"),
        }

    # Portfolio summary
    portfolio_daily = matrix.sum(axis=1)
    portfolio_sharpe = _annualized_sharpe(portfolio_daily)
    portfolio_dd = _max_drawdown(portfolio_daily)
    portfolio_pnl = portfolio_daily.sum()

    return {
        "report_date": report_date,
        "portfolio_summary": {
            "total_days": len(matrix),
            "strategies_evaluated": len(matrix.columns),
            "portfolio_sharpe": round(portfolio_sharpe, 3),
            "portfolio_max_dd": round(portfolio_dd, 2),
            "portfolio_total_pnl": round(portfolio_pnl, 2),
        },
        "composite_scores": composite,
        "marginal_sharpe": marginal_sharpe,
        "marginal_drawdown": marginal_dd,
        "overlap_cost": overlap,
        "slot_efficiency": efficiency,
        "displaced_opportunity": displaced,
        "blocked_signal_cost": blocked,
    }


# ── Terminal Report ──────────────────────────────────────────────────────────

def print_counterfactual_report(results: dict):
    """Print formatted counterfactual report."""
    W = 80
    SEP = "=" * W
    THIN = "-" * 60

    print()
    print(SEP)
    print("  FQL COUNTERFACTUAL / OPPORTUNITY-COST ENGINE")
    print(f"  {results['report_date']}")
    print(SEP)

    # Portfolio summary
    ps = results["portfolio_summary"]
    print(f"\n  PORTFOLIO BASELINE")
    print(f"  {THIN}")
    print(f"  Days: {ps['total_days']}  |  Strategies: {ps['strategies_evaluated']}  |  "
          f"Sharpe: {ps['portfolio_sharpe']:.2f}  |  DD: ${ps['portfolio_max_dd']:.0f}  |  PnL: ${ps['portfolio_total_pnl']:.0f}")

    # Composite scores
    print(f"\n  COUNTERFACTUAL SCORES")
    print(f"  {THIN}")
    print(f"  {'Strategy':<28s} {'Score':>7s} {'Rec':>12s} {'Sharpe':>8s} {'DD':>12s} {'Overlap':>10s}")
    print(f"  {'-' * 79}")

    sorted_comp = sorted(results["composite_scores"].items(),
                         key=lambda x: x[1]["counterfactual_score"], reverse=True)
    for strat, data in sorted_comp:
        sid = strat[:27] if len(strat) <= 27 else strat[:24] + "..."
        score = data["counterfactual_score"]
        rec = data["recommendation"]
        ms_v = data["marginal_sharpe_verdict"]
        dd_v = data["drawdown_verdict"]
        ov_v = data["overlap_verdict"]

        indicator = "[+]" if rec == "KEEP_FULL" else "[~]" if rec == "KEEP_REDUCED" else "[?]" if rec == "REVIEW" else "[-]"

        print(f"  {indicator} {sid:<25s} {score:>+6.3f} {rec:>12s} {ms_v:>8s} {dd_v:>12s} {ov_v:>10s}")

    # Marginal Sharpe detail
    print(f"\n  MARGINAL SHARPE CONTRIBUTION")
    print(f"  {THIN}")
    print(f"  {'Strategy':<28s} {'Standalone':>10s} {'With':>7s} {'Without':>9s} {'Marginal':>9s} {'Verdict':>12s}")
    print(f"  {'-' * 77}")

    for strat, data in sorted(results["marginal_sharpe"].items(),
                               key=lambda x: x[1].get("marginal_sharpe", 0), reverse=True):
        sid = strat[:27] if len(strat) <= 27 else strat[:24] + "..."
        print(f"  {sid:<28s} {data['standalone_sharpe']:>10.3f} {data['portfolio_sharpe_with']:>7.3f} "
              f"{data['portfolio_sharpe_without']:>9.3f} {data['marginal_sharpe']:>+9.3f} {data['verdict']:>12s}")

    # Overlap cost
    print(f"\n  CORRELATION OVERLAP")
    print(f"  {THIN}")
    for strat, data in sorted(results["overlap_cost"].items(),
                               key=lambda x: x[1].get("overlap_cost_pct", 0), reverse=True):
        sid = strat[:27] if len(strat) <= 27 else strat[:24] + "..."
        print(f"  {sid:<28s} corr={data['correlation_with_portfolio']:>+.3f}  overlap={data['overlap_cost_pct']:.1%}  {data['verdict']}")

    # Slot efficiency
    print(f"\n  SLOT EFFICIENCY")
    print(f"  {THIN}")
    print(f"  {'Strategy':<28s} {'Vol%':>7s} {'PnL%':>7s} {'Marg.S':>7s} {'Eff':>8s} {'Verdict':>12s}")
    print(f"  {'-' * 71}")
    for strat, data in sorted(results["slot_efficiency"].items(),
                               key=lambda x: x[1].get("slot_efficiency", 0), reverse=True):
        sid = strat[:27] if len(strat) <= 27 else strat[:24] + "..."
        print(f"  {sid:<28s} {data['vol_share']:>6.1%} {data['pnl_share']:>6.1%} "
              f"{data['marginal_sharpe']:>+6.3f} {data['slot_efficiency']:>+7.3f} {data['verdict']:>12s}")

    # Blocked signal cost
    blocked = results.get("blocked_signal_cost", {})
    if blocked.get("status") != "NO_DATA":
        print(f"\n  BLOCKED SIGNAL COST")
        print(f"  {THIN}")
        print(f"  Signals taken: {blocked.get('total_taken', 0)}  |  Blocked: {blocked.get('total_blocked', 0)}  |  "
              f"Retention: {blocked.get('retention_rate', 0):.0%}")
        print(f"  Avg PnL/taken: ${blocked.get('avg_pnl_per_taken', 0):.2f}  |  "
              f"Est. blocked cost: ${blocked.get('estimated_blocked_cost', 0):.2f}")
        print(f"  Note: {blocked.get('note', '')}")

    # Actionable recommendations
    print(f"\n  RECOMMENDATIONS")
    print(f"  {THIN}")
    for strat, data in sorted_comp:
        rec = data["recommendation"]
        if rec in ("REVIEW", "REMOVE"):
            ms = results["marginal_sharpe"].get(strat, {})
            dd = results["marginal_drawdown"].get(strat, {})
            reasons = []
            if ms.get("verdict") == "DILUTIVE":
                reasons.append(f"dilutive (marginal Sharpe {ms.get('marginal_sharpe', 0):+.3f})")
            if dd.get("verdict") == "INCREASES_RISK":
                reasons.append(f"increases DD by ${abs(dd.get('marginal_dd', 0)):.0f}")
            ov = results["overlap_cost"].get(strat, {})
            if ov.get("verdict") == "HIGH_OVERLAP":
                reasons.append(f"high overlap ({ov.get('overlap_cost_pct', 0):.0%})")
            if reasons:
                print(f"  [{rec}] {strat}: {'; '.join(reasons)}")
            else:
                print(f"  [{rec}] {strat}")

    has_recommendations = any(d["recommendation"] in ("REVIEW", "REMOVE") for d in results["composite_scores"].values())
    if not has_recommendations:
        print(f"  All strategies contributing positively — no changes recommended.")

    print()
    print(SEP)


# ── Persistence ──────────────────────────────────────────────────────────────

def save_counterfactual_log(results: dict):
    """Append counterfactual results to persistent log."""
    log = []
    if COUNTERFACTUAL_LOG_PATH.exists():
        try:
            with open(COUNTERFACTUAL_LOG_PATH) as f:
                log = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            log = []

    entry = {
        "date": results["report_date"],
        "portfolio_sharpe": results["portfolio_summary"]["portfolio_sharpe"],
        "strategies": {},
    }
    for strat, data in results["composite_scores"].items():
        entry["strategies"][strat] = {
            "score": data["counterfactual_score"],
            "recommendation": data["recommendation"],
        }

    log.append(entry)
    if len(log) > 365:
        log = log[-365:]

    COUNTERFACTUAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    from research.utils.atomic_io import atomic_write_json
    atomic_write_json(COUNTERFACTUAL_LOG_PATH, log)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Counterfactual / Opportunity-Cost Engine")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", action="store_true", help="Save report + log")
    args = parser.parse_args()

    results = run_counterfactual_engine()

    if results.get("status") == "NO_DATA":
        print(results.get("message", "No data available"))
        return

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_counterfactual_report(results)

    if args.save:
        save_counterfactual_log(results)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = REPORTS_DIR / f"counterfactual_{timestamp}.json"
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Report saved: {path}")
        print(f"Log updated: {COUNTERFACTUAL_LOG_PATH}")


if __name__ == "__main__":
    main()
