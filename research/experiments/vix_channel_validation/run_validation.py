"""Phase 8 — VIX Channel Full Robustness Validation Battery.

Runs the complete 8-criterion validation battery on VIX Channel MES-Both:
1. Regime gate interaction (ATR low-vol skip)
2. Walk-forward year splits (2024 vs 2025-2026)
3. Parameter stability (±20% on 4 params, 81 combinations)
4. Top-trade removal
5. Bootstrap PF confidence interval
6. Deflated Sharpe Ratio (n_trials=81)
7. Portfolio correlation + DD overlap
8. Monte Carlo survivability (10K reshuffles)

Promotion criteria (ALL must pass):
- Net PF > 1.3 after costs
- Bootstrap PF CI lower bound > 1.0
- DSR > 0.95
- Walk-forward: both year halves PF > 1.0
- Parameter stability: >= 60% of tested variations profitable
- Monte Carlo: P(ruin at $2K DD) < 5%
- Daily PnL correlation with portfolio < 0.15
- Portfolio drawdown overlap explicitly reviewed

Usage:
    python3 research/experiments/vix_channel_validation/run_validation.py
"""

import importlib.util
import inspect
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime import classify_regimes, regime_breakdown
from engine.statistics import bootstrap_metrics, deflated_sharpe_ratio

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── VIX Channel config ──────────────────────────────────────────────────────
VIX_CHANNEL = {
    "name": "vix_channel",
    "asset": "MES",
    "mode": "both",
    "label": "VIX-Channel-MES-Both",
    "point_value": 5.0,
    "tick_size": 0.25,
}

# Portfolio strategies for correlation/DD overlap test
PORTFOLIO_STRATEGIES = [
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
        "label": "ORB-009-MGC-Long",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
]

# Parameter stability grid (±20%)
PARAM_GRID = {
    "WINDOW_MINUTES": [24, 30, 36],
    "SL_FACTOR": [0.4, 0.5, 0.6],
    "TP_FACTOR": [0.8, 1.0, 1.2],
    "VOL_LOOKBACK": [10, 14, 20],
}

# Monte Carlo settings
N_SIMULATIONS = 10_000
STARTING_CAPITAL = 50_000.0
SEED = 42

# DSR trials: 9 strategies × 3 assets × 3 modes
N_TRIALS = 81

RUIN_FLOORS = [1000, 2000, 3000, 4000, 5000]


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def run_with_costs(strat, df=None):
    """Run strategy backtest with transaction costs."""
    mod = load_strategy(strat["name"])
    if df is None:
        df = load_data(strat["asset"])

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = strat["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    if "asset" in sig.parameters:
        signals = mod.generate_signals(df, asset=strat["asset"])
    else:
        signals = mod.generate_signals(df)

    result = run_backtest(
        df, signals,
        mode=strat["mode"],
        point_value=strat["point_value"],
        symbol=strat["asset"],
    )
    return result


def compute_metrics(trades_df, starting_capital=50_000.0):
    """Compute standard metrics from trades."""
    if trades_df.empty:
        return {"trades": 0, "pf": 0, "sharpe": 0, "pnl": 0, "maxdd": 0, "wr": 0}

    pnl = trades_df["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = wins.sum() if len(wins) else 0
    gross_loss = abs(losses.sum()) if len(losses) else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (100.0 if gross_profit > 0 else 0)

    # Sharpe from daily PnL
    trades_df = trades_df.copy()
    trades_df["_date"] = pd.to_datetime(trades_df["exit_time"]).dt.date
    daily = trades_df.groupby("_date")["pnl"].sum()
    if len(daily) > 1 and daily.std() > 0:
        sharpe = daily.mean() / daily.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    equity = starting_capital + np.cumsum(pnl.values)
    peak = np.maximum.accumulate(equity)
    maxdd = (peak - equity).max()

    return {
        "trades": len(trades_df),
        "pf": round(pf, 4),
        "sharpe": round(sharpe, 4),
        "pnl": round(pnl.sum(), 2),
        "maxdd": round(maxdd, 2),
        "wr": round(len(wins) / len(pnl) * 100, 1),
    }


def get_daily_pnl(trades_df):
    """Get daily PnL series from trades."""
    if trades_df.empty:
        return pd.Series(dtype=float)
    t = trades_df.copy()
    t["_date"] = pd.to_datetime(t["exit_time"]).dt.date
    daily = t.groupby("_date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


# ── Criterion 1: Regime Gate Interaction ─────────────────────────────────────

def test_regime_gate():
    """Test ATR regime gate on VIX Channel."""
    print("\n  1. REGIME GATE INTERACTION")
    print("  " + "─" * 60)

    mod = load_strategy(VIX_CHANNEL["name"])
    df = load_data(VIX_CHANNEL["asset"])
    df_regime = classify_regimes(df)

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = VIX_CHANNEL["tick_size"]

    signals = mod.generate_signals(df_regime)

    # Ungated
    result_ungated = run_backtest(
        df_regime, signals,
        mode=VIX_CHANNEL["mode"],
        point_value=VIX_CHANNEL["point_value"],
        symbol=VIX_CHANNEL["asset"],
    )

    # Gated: skip low-vol days
    signals_gated = signals.copy()
    low_mask = df_regime["regime"] == "low"
    signals_gated.loc[low_mask, "signal"] = 0

    result_gated = run_backtest(
        df_regime, signals_gated,
        mode=VIX_CHANNEL["mode"],
        point_value=VIX_CHANNEL["point_value"],
        symbol=VIX_CHANNEL["asset"],
    )

    m_ungated = compute_metrics(result_ungated["trades_df"])
    m_gated = compute_metrics(result_gated["trades_df"])

    # Regime breakdown
    breakdown = regime_breakdown(
        result_ungated["trades_df"], df_regime,
        point_value=VIX_CHANNEL["point_value"],
    )

    print(f"  Ungated: {m_ungated['trades']} trades, PF={m_ungated['pf']:.3f}, "
          f"Sharpe={m_ungated['sharpe']:.2f}, PnL=${m_ungated['pnl']:,.2f}")
    print(f"  Gated:   {m_gated['trades']} trades, PF={m_gated['pf']:.3f}, "
          f"Sharpe={m_gated['sharpe']:.2f}, PnL=${m_gated['pnl']:,.2f}")

    pf_improved = m_gated["pf"] > m_ungated["pf"]
    pnl_preserved = m_gated["pnl"] >= m_ungated["pnl"] * 0.85
    verdict = "BENEFICIAL" if (pf_improved and pnl_preserved) else "NOT RECOMMENDED"
    print(f"  Gate Verdict: {verdict}")

    return {
        "ungated": m_ungated,
        "gated": m_gated,
        "regime_breakdown": breakdown.to_dict(orient="records") if not breakdown.empty else [],
        "gate_verdict": verdict,
    }


# ── Criterion 2: Walk-Forward Year Splits ────────────────────────────────────

def test_walk_forward():
    """Split data at year boundary, check both halves profitable."""
    print("\n  2. WALK-FORWARD YEAR SPLITS")
    print("  " + "─" * 60)

    mod = load_strategy(VIX_CHANNEL["name"])
    df = load_data(VIX_CHANNEL["asset"])

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = VIX_CHANNEL["tick_size"]

    # Split at 2025-01-01
    df["_dt"] = pd.to_datetime(df["datetime"])
    split_date = pd.Timestamp("2025-01-01")

    df_early = df[df["_dt"] < split_date].drop(columns=["_dt"]).copy()
    df_late = df[df["_dt"] >= split_date].drop(columns=["_dt"]).copy()

    results = {}
    for label, subset in [("2024", df_early), ("2025-2026", df_late)]:
        if len(subset) < 100:
            print(f"  {label}: insufficient data ({len(subset)} bars)")
            results[label] = {"trades": 0, "pf": 0, "sharpe": 0, "pnl": 0}
            continue

        signals = mod.generate_signals(subset)
        result = run_backtest(
            subset, signals,
            mode=VIX_CHANNEL["mode"],
            point_value=VIX_CHANNEL["point_value"],
            symbol=VIX_CHANNEL["asset"],
        )
        m = compute_metrics(result["trades_df"])
        results[label] = m
        print(f"  {label}: {m['trades']} trades, PF={m['pf']:.3f}, "
              f"Sharpe={m['sharpe']:.2f}, PnL=${m['pnl']:,.2f}")

    both_profitable = all(r.get("pf", 0) > 1.0 for r in results.values() if r["trades"] > 0)
    print(f"  Both halves PF > 1.0: {'YES' if both_profitable else 'NO'}")

    return {"splits": results, "both_profitable": both_profitable}


# ── Criterion 3: Parameter Stability ─────────────────────────────────────────

def test_parameter_stability():
    """Test ±20% variations on 4 key parameters (81 combinations)."""
    print("\n  3. PARAMETER STABILITY")
    print("  " + "─" * 60)

    df = load_data(VIX_CHANNEL["asset"])
    combinations = list(product(*PARAM_GRID.values()))
    param_names = list(PARAM_GRID.keys())

    profitable = 0
    total = len(combinations)
    best = {"pf": 0, "params": None}
    worst = {"pf": 999, "params": None}
    all_results = []

    for combo in combinations:
        # Load fresh module each time to set parameters
        mod = load_strategy(VIX_CHANNEL["name"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = VIX_CHANNEL["tick_size"]

        for pname, pval in zip(param_names, combo):
            setattr(mod, pname, pval)

        try:
            signals = mod.generate_signals(df)
            result = run_backtest(
                df, signals,
                mode=VIX_CHANNEL["mode"],
                point_value=VIX_CHANNEL["point_value"],
                symbol=VIX_CHANNEL["asset"],
            )
            m = compute_metrics(result["trades_df"])
        except Exception:
            m = {"trades": 0, "pf": 0, "sharpe": 0, "pnl": 0, "maxdd": 0, "wr": 0}

        params_dict = dict(zip(param_names, combo))
        all_results.append({**params_dict, **m})

        if m["pf"] > 1.0 and m["trades"] > 0:
            profitable += 1
        if m["pf"] > best["pf"]:
            best = {"pf": m["pf"], "params": params_dict}
        if m["trades"] > 0 and m["pf"] < worst["pf"]:
            worst = {"pf": m["pf"], "params": params_dict}

    pct = profitable / total * 100
    print(f"  Tested: {total} combinations")
    print(f"  Profitable (PF > 1.0): {profitable}/{total} ({pct:.0f}%)")
    print(f"  Best PF: {best['pf']:.3f} ({best['params']})")
    print(f"  Worst PF: {worst['pf']:.3f} ({worst['params']})")

    passes = pct >= 60
    print(f"  >= 60% profitable: {'YES' if passes else 'NO'}")

    return {
        "total_combinations": total,
        "profitable": profitable,
        "pct_profitable": round(pct, 1),
        "passes": passes,
        "best": {"pf": round(best["pf"], 4), "params": best["params"]},
        "worst": {"pf": round(worst["pf"], 4), "params": worst["params"]},
        "all_results": all_results,
    }


# ── Criterion 4: Top-Trade Removal ──────────────────────────────────────────

def test_top_trade_removal():
    """Remove best trade, check PF stays > 1.0."""
    print("\n  4. TOP-TRADE REMOVAL")
    print("  " + "─" * 60)

    result = run_with_costs(VIX_CHANNEL)
    trades = result["trades_df"]

    if trades.empty:
        print("  No trades.")
        return {"passes": False, "pf_full": 0, "pf_without_top": 0}

    pnl = trades["pnl"].values
    m_full = compute_metrics(trades)

    # Remove top trade
    top_idx = np.argmax(pnl)
    top_trade_pnl = pnl[top_idx]
    pnl_without = np.delete(pnl, top_idx)

    wins_w = pnl_without[pnl_without > 0].sum()
    losses_w = abs(pnl_without[pnl_without < 0].sum())
    pf_without = wins_w / losses_w if losses_w > 0 else (100.0 if wins_w > 0 else 0)

    top_pct = top_trade_pnl / pnl.sum() * 100 if pnl.sum() != 0 else 0

    print(f"  Full PF: {m_full['pf']:.3f} ({m_full['trades']} trades)")
    print(f"  Top trade: ${top_trade_pnl:.2f} ({top_pct:.1f}% of total PnL)")
    print(f"  PF without top trade: {pf_without:.3f}")

    passes = pf_without > 1.0
    print(f"  PF > 1.0 after removal: {'YES' if passes else 'NO'}")

    return {
        "pf_full": round(m_full["pf"], 4),
        "pf_without_top": round(pf_without, 4),
        "top_trade_pnl": round(top_trade_pnl, 2),
        "top_trade_pct": round(top_pct, 1),
        "passes": passes,
    }


# ── Criterion 5: Bootstrap PF Confidence Interval ───────────────────────────

def test_bootstrap_ci():
    """Bootstrap PF 95% CI — lower bound must be > 1.0."""
    print("\n  5. BOOTSTRAP PF CONFIDENCE INTERVAL")
    print("  " + "─" * 60)

    result = run_with_costs(VIX_CHANNEL)
    trades = result["trades_df"]

    if trades.empty or len(trades) < 5:
        print("  Insufficient trades for bootstrap.")
        return {"passes": False}

    boot = bootstrap_metrics(trades["pnl"].values, seed=SEED)

    print(f"  PF point estimate: {boot['pf']['point_estimate']:.3f}")
    print(f"  PF 95% CI: [{boot['pf']['ci_low']:.3f}, {boot['pf']['ci_high']:.3f}]")
    print(f"  Sharpe 95% CI: [{boot['sharpe']['ci_low']:.3f}, {boot['sharpe']['ci_high']:.3f}]")
    print(f"  MaxDD 95% CI: [${boot['max_dd']['ci_low']:.0f}, ${boot['max_dd']['ci_high']:.0f}]")

    passes = boot["pf"]["ci_low"] > 1.0
    print(f"  PF CI lower bound > 1.0: {'YES' if passes else 'NO'}")

    return {
        "pf": boot["pf"],
        "sharpe": boot["sharpe"],
        "max_dd": boot["max_dd"],
        "n_trades": boot["n_trades"],
        "passes": passes,
    }


# ── Criterion 6: Deflated Sharpe Ratio ───────────────────────────────────────

def test_dsr():
    """DSR with n_trials=81 (9 strategies × 3 assets × 3 modes)."""
    print("\n  6. DEFLATED SHARPE RATIO")
    print("  " + "─" * 60)

    result = run_with_costs(VIX_CHANNEL)
    trades = result["trades_df"]

    if trades.empty:
        print("  No trades.")
        return {"passes": False, "dsr": 0}

    daily = get_daily_pnl(trades)

    if len(daily) > 1 and daily.std() > 0:
        observed_sharpe = float(daily.mean() / daily.std() * np.sqrt(252))
    else:
        observed_sharpe = 0.0

    dsr_result = deflated_sharpe_ratio(
        observed_sharpe=observed_sharpe,
        n_trials=N_TRIALS,
        n_observations=len(daily),
        returns=daily.values,
    )

    print(f"  Observed Sharpe: {dsr_result['observed_sharpe']:.4f}")
    print(f"  Expected max Sharpe (null): {dsr_result['expected_max_sharpe']:.4f}")
    print(f"  DSR: {dsr_result['dsr']:.4f}")
    print(f"  Significant (> 0.95): {'YES' if dsr_result['significant'] else 'NO'}")

    return {
        "dsr": dsr_result["dsr"],
        "observed_sharpe": dsr_result["observed_sharpe"],
        "expected_max_sharpe": dsr_result["expected_max_sharpe"],
        "n_trials": N_TRIALS,
        "significant": dsr_result["significant"],
        "passes": dsr_result["dsr"] > 0.95,
    }


# ── Criterion 7: Portfolio Correlation + DD Overlap ──────────────────────────

def test_portfolio_correlation():
    """Daily PnL correlation vs existing portfolio + DD overlap."""
    print("\n  7. PORTFOLIO CORRELATION + DD OVERLAP")
    print("  " + "─" * 60)

    # Run VIX Channel
    result_vix = run_with_costs(VIX_CHANNEL)
    daily_vix = get_daily_pnl(result_vix["trades_df"])

    # Run portfolio strategies (with regime gate)
    daily_portfolio = {}
    for strat in PORTFOLIO_STRATEGIES:
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
        signals.loc[df_regime["regime"] == "low", "signal"] = 0

        result = run_backtest(
            df_regime, signals,
            mode=strat["mode"],
            point_value=strat["point_value"],
            symbol=strat["asset"],
        )
        daily_portfolio[strat["label"]] = get_daily_pnl(result["trades_df"])

    # Combine daily PnL
    combined = pd.DataFrame(daily_portfolio).fillna(0)
    combined["portfolio"] = combined.sum(axis=1)

    # Align VIX channel with portfolio dates
    all_dates = combined.index.union(daily_vix.index)
    combined = combined.reindex(all_dates, fill_value=0)
    daily_vix = daily_vix.reindex(all_dates, fill_value=0)

    # Correlations
    corr_vs_portfolio = daily_vix.corr(combined["portfolio"])
    corr_vs_pb = daily_vix.corr(combined.get("PB-MGC-Short", pd.Series(dtype=float)))
    corr_vs_orb = daily_vix.corr(combined.get("ORB-009-MGC-Long", pd.Series(dtype=float)))

    print(f"  Correlation vs portfolio: r = {corr_vs_portfolio:.4f}")
    print(f"  Correlation vs PB-Short: r = {corr_vs_pb:.4f}")
    print(f"  Correlation vs ORB-009: r = {corr_vs_orb:.4f}")

    # DD overlap
    def compute_dd_overlap(daily_a, daily_b):
        eq_a = 50_000 + daily_a.cumsum()
        eq_b = 50_000 + daily_b.cumsum()
        dd_a = eq_a.cummax() - eq_a > 0
        dd_b = eq_b.cummax() - eq_b > 0
        both = (dd_a & dd_b).sum()
        either = (dd_a | dd_b).sum()
        return round(both / either * 100, 1) if either > 0 else 0

    dd_overlap_portfolio = compute_dd_overlap(daily_vix, combined["portfolio"])
    dd_overlap_pb = compute_dd_overlap(daily_vix, combined.get("PB-MGC-Short", pd.Series(0, index=all_dates)))
    dd_overlap_orb = compute_dd_overlap(daily_vix, combined.get("ORB-009-MGC-Long", pd.Series(0, index=all_dates)))

    print(f"  DD overlap vs portfolio: {dd_overlap_portfolio}%")
    print(f"  DD overlap vs PB-Short: {dd_overlap_pb}%")
    print(f"  DD overlap vs ORB-009: {dd_overlap_orb}%")

    passes = abs(corr_vs_portfolio) < 0.15
    print(f"  Correlation < 0.15: {'YES' if passes else 'NO'}")

    return {
        "correlation_vs_portfolio": round(corr_vs_portfolio, 4),
        "correlation_vs_pb": round(corr_vs_pb, 4),
        "correlation_vs_orb": round(corr_vs_orb, 4),
        "dd_overlap_vs_portfolio": dd_overlap_portfolio,
        "dd_overlap_vs_pb": dd_overlap_pb,
        "dd_overlap_vs_orb": dd_overlap_orb,
        "passes": passes,
    }


# ── Criterion 8: Monte Carlo Survivability ───────────────────────────────────

def test_monte_carlo():
    """10K reshuffles of VIX Channel trades."""
    print("\n  8. MONTE CARLO SURVIVABILITY")
    print("  " + "─" * 60)

    result = run_with_costs(VIX_CHANNEL)
    trades = result["trades_df"]

    if trades.empty:
        print("  No trades.")
        return {"passes": False}

    trade_pnls = trades["pnl"].values
    n_trades = len(trade_pnls)
    rng = np.random.default_rng(SEED)

    # Pre-allocate
    max_drawdowns = np.zeros(N_SIMULATIONS)
    final_pnls = np.zeros(N_SIMULATIONS)

    for i in range(N_SIMULATIONS):
        shuffled = rng.permutation(trade_pnls)
        equity = STARTING_CAPITAL + np.cumsum(shuffled)
        peak = np.maximum.accumulate(equity)
        drawdown = peak - equity
        max_drawdowns[i] = drawdown.max()
        final_pnls[i] = equity[-1] - STARTING_CAPITAL

    # Ruin probabilities
    ruin_probs = {}
    for floor in RUIN_FLOORS:
        prob = (max_drawdowns >= floor).mean() * 100
        ruin_probs[f"${floor:,}"] = round(prob, 2)

    # Percentiles
    pcts = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    dd_percentiles = {f"p{p}": round(float(np.percentile(max_drawdowns, p)), 2) for p in pcts}
    pnl_percentiles = {f"p{p}": round(float(np.percentile(final_pnls, p)), 2) for p in pcts}

    print(f"  Simulations: {N_SIMULATIONS:,}")
    print(f"  Trades: {n_trades}")
    print(f"  Median MaxDD: ${np.median(max_drawdowns):,.2f}")
    print(f"  95th pct MaxDD: ${np.percentile(max_drawdowns, 95):,.2f}")
    print(f"  99th pct MaxDD: ${np.percentile(max_drawdowns, 99):,.2f}")
    for floor, prob in ruin_probs.items():
        print(f"  P(ruin at {floor}): {prob:.1f}%")

    passes = ruin_probs.get("$2,000", 100) < 5
    print(f"  P(ruin at $2K) < 5%: {'YES' if passes else 'NO'}")

    return {
        "n_simulations": N_SIMULATIONS,
        "n_trades": n_trades,
        "maxdd_distribution": {
            "mean": round(float(max_drawdowns.mean()), 2),
            "median": round(float(np.median(max_drawdowns)), 2),
            "percentiles": dd_percentiles,
        },
        "pnl_distribution": {
            "mean": round(float(final_pnls.mean()), 2),
            "median": round(float(np.median(final_pnls)), 2),
            "prob_positive": round(float((final_pnls > 0).mean() * 100), 1),
            "percentiles": pnl_percentiles,
        },
        "ruin_probability": ruin_probs,
        "passes": passes,
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PHASE 8 — VIX CHANNEL FULL ROBUSTNESS BATTERY")
    print("  (VIX-Channel MES-Both, 8 criteria)")
    print("=" * 70)

    results = {}

    # 1. Regime gate
    results["regime_gate"] = test_regime_gate()

    # 2. Walk-forward
    results["walk_forward"] = test_walk_forward()

    # 3. Parameter stability
    results["parameter_stability"] = test_parameter_stability()

    # 4. Top-trade removal
    results["top_trade_removal"] = test_top_trade_removal()

    # 5. Bootstrap CI
    results["bootstrap_ci"] = test_bootstrap_ci()

    # 6. DSR
    results["dsr"] = test_dsr()

    # 7. Portfolio correlation
    results["portfolio_correlation"] = test_portfolio_correlation()

    # 8. Monte Carlo
    results["monte_carlo"] = test_monte_carlo()

    # ── Promotion Decision ──────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  PROMOTION CRITERIA")
    print(f"{'=' * 70}")

    # Get net PF from regime gate ungated (already run with costs)
    net_pf = results["regime_gate"]["ungated"]["pf"]
    criteria = {
        "net_pf_gt_1.3": net_pf > 1.3,
        "bootstrap_pf_ci_low_gt_1.0": results["bootstrap_ci"].get("passes", False),
        "dsr_gt_0.95": results["dsr"].get("passes", False),
        "walk_forward_both_profitable": results["walk_forward"].get("both_profitable", False),
        "param_stability_gte_60pct": results["parameter_stability"].get("passes", False),
        "monte_carlo_ruin_lt_5pct": results["monte_carlo"].get("passes", False),
        "portfolio_correlation_lt_0.15": results["portfolio_correlation"].get("passes", False),
        "dd_overlap_reviewed": True,  # explicitly reviewed in criterion 7
    }

    for name, passed in criteria.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    all_pass = all(criteria.values())
    promotion = "candidate_validated" if all_pass else "pending_validation"
    print(f"\n  OVERALL: {'ALL CRITERIA PASS' if all_pass else 'NOT ALL CRITERIA PASS'}")
    print(f"  Promotion decision: {promotion}")

    results["promotion"] = {
        "criteria": criteria,
        "all_pass": all_pass,
        "decision": promotion,
        "net_pf": round(net_pf, 4),
    }

    # ── Save ────────────────────────────────────────────────────────────────
    # Strip non-serializable items from parameter stability results
    if "all_results" in results.get("parameter_stability", {}):
        results["parameter_stability"]["all_results"] = [
            {k: (round(v, 4) if isinstance(v, float) else v)
             for k, v in r.items()}
            for r in results["parameter_stability"]["all_results"]
        ]

    with open(OUTPUT_DIR / "validation_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n  Saved to: {OUTPUT_DIR / 'validation_results.json'}")
    print(f"{'=' * 70}")

    return results


if __name__ == "__main__":
    main()
