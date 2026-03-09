"""Phase 6.2 — Monte Carlo Robustness Test.

Reshuffles the gated portfolio's trade sequence 10,000 times to measure
distribution of outcomes under different orderings. Tests whether the
portfolio survives unfavorable trade ordering.

Key outputs:
- MaxDD distribution (percentiles)
- Final PnL distribution
- Probability of ruin at various drawdown floors
- Prop account survival probability ($4K trailing DD)

Usage:
    python3 research/monte_carlo/run_monte_carlo.py
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

from engine.backtest import run_backtest
from engine.regime import classify_regimes

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

N_SIMULATIONS = 10_000
STARTING_CAPITAL = 50_000.0
SEED = 42

STRATEGIES = [
    {
        "name": "pb_trend",
        "asset": "MGC",
        "mode": "short",
        "label": "PB-MGC-Short",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
    {
        "name": "orb_009",
        "asset": "MGC",
        "mode": "long",
        "label": "ORB-009 MGC-Long",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
]

# Drawdown floors to test ruin probability
RUIN_FLOORS = [1000, 2000, 3000, 4000, 5000]
# Prop account configs to test
PROP_DD_LIMITS = {
    "prop_2k": 2000,
    "prop_3k": 3000,
    "prop_4k": 4000,
    "prop_5k": 5000,
}


def load_strategy(name):
    path = PROJECT_ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset):
    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def get_gated_trades():
    """Run both strategies with regime gate and costs, return combined trade PnLs."""
    all_pnls = []

    for strat in STRATEGIES:
        mod = load_strategy(strat["name"])
        df = load_data(strat["asset"])
        df_regime = classify_regimes(df)

        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = strat["tick_size"]

        sig = inspect.signature(mod.generate_signals)
        if "asset" in sig.parameters:
            signals = mod.generate_signals(df_regime, asset=strat["asset"])
        else:
            signals = mod.generate_signals(df_regime)

        # Apply regime gate
        signals = signals.copy()
        low_mask = df_regime["regime"] == "low"
        signals.loc[low_mask, "signal"] = 0

        result = run_backtest(
            df_regime, signals,
            mode=strat["mode"],
            point_value=strat["point_value"],
            symbol=strat["asset"],
        )

        trades = result["trades_df"]
        if not trades.empty:
            all_pnls.extend(trades["pnl"].values.tolist())
            print(f"  {strat['label']}: {len(trades)} trades, PnL=${trades['pnl'].sum():,.2f}")

    return np.array(all_pnls)


def run_simulation(trade_pnls, n_sims, rng):
    """Reshuffle trade sequence n_sims times, compute outcome distributions."""
    n_trades = len(trade_pnls)

    # Pre-allocate result arrays
    final_pnls = np.zeros(n_sims)
    max_drawdowns = np.zeros(n_sims)
    max_runups = np.zeros(n_sims)
    worst_dd_durations = np.zeros(n_sims, dtype=int)

    for i in range(n_sims):
        # Shuffle trade order
        shuffled = rng.permutation(trade_pnls)

        # Compute equity curve
        equity = STARTING_CAPITAL + np.cumsum(shuffled)
        peak = np.maximum.accumulate(equity)
        drawdown = peak - equity

        final_pnls[i] = equity[-1] - STARTING_CAPITAL
        max_drawdowns[i] = drawdown.max()

        # Max runup (peak above starting)
        max_runups[i] = (equity - STARTING_CAPITAL).max()

        # Worst drawdown duration (consecutive bars in drawdown from peak)
        in_dd = drawdown > 0
        if in_dd.any():
            # Count max consecutive True values
            changes = np.diff(in_dd.astype(int), prepend=0)
            starts = np.where(changes == 1)[0]
            ends = np.where(changes == -1)[0]
            if len(ends) < len(starts):
                ends = np.append(ends, len(in_dd))
            durations = ends - starts
            worst_dd_durations[i] = durations.max() if len(durations) > 0 else 0

    return final_pnls, max_drawdowns, max_runups, worst_dd_durations


def compute_percentiles(arr):
    """Compute standard percentile table."""
    pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    values = np.percentile(arr, pcts)
    return {f"p{p}": round(float(v), 2) for p, v in zip(pcts, values)}


def compute_ruin_probabilities(max_drawdowns, floors):
    """Probability that MaxDD exceeds various thresholds."""
    results = {}
    for floor in floors:
        prob = (max_drawdowns >= floor).mean()
        results[f"${floor:,}"] = round(float(prob) * 100, 2)
    return results


def main():
    print("=" * 70)
    print("  PHASE 6.2 — MONTE CARLO ROBUSTNESS TEST")
    print(f"  ({N_SIMULATIONS:,} reshuffled trade sequences)")
    print("=" * 70)

    # ── Get actual gated trades ──────────────────────────────────────────────
    print("\n  Loading gated portfolio trades...")
    trade_pnls = get_gated_trades()
    n_trades = len(trade_pnls)
    observed_pnl = trade_pnls.sum()
    observed_dd = (np.maximum.accumulate(STARTING_CAPITAL + np.cumsum(trade_pnls))
                   - (STARTING_CAPITAL + np.cumsum(trade_pnls))).max()

    print(f"\n  Portfolio: {n_trades} trades")
    print(f"  Observed PnL: ${observed_pnl:,.2f}")
    print(f"  Observed MaxDD: ${observed_dd:,.2f}")

    # ── Run Monte Carlo ──────────────────────────────────────────────────────
    print(f"\n  Running {N_SIMULATIONS:,} simulations...")
    rng = np.random.default_rng(SEED)
    final_pnls, max_drawdowns, max_runups, dd_durations = run_simulation(
        trade_pnls, N_SIMULATIONS, rng
    )

    # ── Results ──────────────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  FINAL PnL DISTRIBUTION")
    print(f"{'─' * 70}")
    pnl_pcts = compute_percentiles(final_pnls)
    print(f"  Mean:   ${final_pnls.mean():,.2f}")
    print(f"  Median: ${np.median(final_pnls):,.2f}")
    print(f"  Std:    ${final_pnls.std():,.2f}")
    for k, v in pnl_pcts.items():
        print(f"  {k}: ${v:,.2f}")
    print(f"  Prob(PnL > 0): {(final_pnls > 0).mean()*100:.1f}%")
    print(f"  Prob(PnL > $3K): {(final_pnls > 3000).mean()*100:.1f}%")

    print(f"\n{'─' * 70}")
    print("  MAX DRAWDOWN DISTRIBUTION")
    print(f"{'─' * 70}")
    dd_pcts = compute_percentiles(max_drawdowns)
    print(f"  Mean:   ${max_drawdowns.mean():,.2f}")
    print(f"  Median: ${np.median(max_drawdowns):,.2f}")
    for k, v in dd_pcts.items():
        print(f"  {k}: ${v:,.2f}")

    print(f"\n{'─' * 70}")
    print("  RUIN PROBABILITY (MaxDD exceeds floor)")
    print(f"{'─' * 70}")
    ruin_probs = compute_ruin_probabilities(max_drawdowns, RUIN_FLOORS)
    for floor, prob in ruin_probs.items():
        marker = " ← PROP LIMIT" if floor == "$4,000" else ""
        print(f"  P(MaxDD >= {floor}): {prob:.1f}%{marker}")

    # Prop survival analysis
    print(f"\n{'─' * 70}")
    print("  PROP ACCOUNT SURVIVAL ANALYSIS")
    print(f"{'─' * 70}")
    for name, dd_limit in PROP_DD_LIMITS.items():
        # For each simulation, check if max drawdown ever exceeds the DD limit
        survival = (max_drawdowns < dd_limit).mean() * 100
        # Also check: of those that survive, what's the median PnL?
        surviving_mask = max_drawdowns < dd_limit
        if surviving_mask.any():
            median_pnl_surviving = np.median(final_pnls[surviving_mask])
        else:
            median_pnl_surviving = 0
        print(f"  {name} (${dd_limit:,} trailing DD):")
        print(f"    Survival rate: {survival:.1f}%")
        print(f"    Median PnL (surviving): ${median_pnl_surviving:,.2f}")

    # DD duration analysis
    print(f"\n{'─' * 70}")
    print("  DRAWDOWN DURATION (in trades)")
    print(f"{'─' * 70}")
    dur_pcts = compute_percentiles(dd_durations)
    print(f"  Mean:   {dd_durations.mean():.0f} trades")
    print(f"  Median: {np.median(dd_durations):.0f} trades")
    for k, v in dur_pcts.items():
        print(f"  {k}: {v:.0f} trades")

    # ── Save results ─────────────────────────────────────────────────────────
    results = {
        "n_simulations": N_SIMULATIONS,
        "n_trades": n_trades,
        "seed": SEED,
        "starting_capital": STARTING_CAPITAL,
        "observed": {
            "pnl": round(float(observed_pnl), 2),
            "maxdd": round(float(observed_dd), 2),
        },
        "pnl_distribution": {
            "mean": round(float(final_pnls.mean()), 2),
            "median": round(float(np.median(final_pnls)), 2),
            "std": round(float(final_pnls.std()), 2),
            "percentiles": pnl_pcts,
            "prob_positive": round(float((final_pnls > 0).mean() * 100), 1),
            "prob_gt_3k": round(float((final_pnls > 3000).mean() * 100), 1),
        },
        "maxdd_distribution": {
            "mean": round(float(max_drawdowns.mean()), 2),
            "median": round(float(np.median(max_drawdowns)), 2),
            "std": round(float(max_drawdowns.std()), 2),
            "percentiles": dd_pcts,
        },
        "ruin_probability": ruin_probs,
        "prop_survival": {
            name: {
                "dd_limit": dd_limit,
                "survival_pct": round(float((max_drawdowns < dd_limit).mean() * 100), 1),
                "median_pnl_surviving": round(float(np.median(final_pnls[max_drawdowns < dd_limit])), 2)
                    if (max_drawdowns < dd_limit).any() else 0,
            }
            for name, dd_limit in PROP_DD_LIMITS.items()
        },
        "dd_duration": {
            "mean": round(float(dd_durations.mean()), 1),
            "median": round(float(np.median(dd_durations)), 1),
            "percentiles": {k: round(v, 0) for k, v in compute_percentiles(dd_durations).items()},
        },
    }

    with open(OUTPUT_DIR / "monte_carlo_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  Saved to: {OUTPUT_DIR / 'monte_carlo_results.json'}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
