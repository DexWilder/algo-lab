"""Phase 8 — Portfolio Regime Simulation.

Simulates portfolio performance under 3 activation modes:
1. Baseline — all strategies always active (no gate)
2. ATR-gated — current approach (skip low-vol days)
3. Regime-profiled — each strategy only trades in its preferred regimes

Compares: Sharpe, Calmar, MaxDD, trade count, monthly consistency.
Tests both 2-strategy (PB + ORB) and 3-strategy (+ VIX Channel) portfolios.

Usage:
    python3 research/portfolio/regime_portfolio_sim.py
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
from engine.regime_engine import RegimeEngine

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROFILES_PATH = PROJECT_ROOT / "research" / "regime" / "strategy_regime_profiles.json"

STARTING_CAPITAL = 50_000.0

# Core portfolio (2 strategies)
STRATEGIES_2 = [
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

# Extended portfolio (3 strategies, includes VIX Channel)
STRATEGIES_3 = STRATEGIES_2 + [
    {
        "name": "vix_channel",
        "asset": "MES",
        "mode": "both",
        "label": "VIX-Channel-MES-Both",
        "point_value": 5.0,
        "tick_size": 0.25,
    },
]


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


def run_strategy_mode(strat, gate_mode="none", regime_df=None, profiles=None, engine=None):
    """Run a single strategy under a specific gating mode.

    gate_mode:
    - 'none': no gating (baseline)
    - 'atr': skip low-vol days (ATR < 33rd percentile)
    - 'regime_profiled': skip avoid_regimes from profiles
    """
    mod = load_strategy(strat["name"])
    df = load_data(strat["asset"])

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = strat["tick_size"]

    # Classify regimes based on mode
    if gate_mode == "atr":
        df_work = classify_regimes(df)
    elif gate_mode == "regime_profiled" and engine is not None:
        df_work = engine.classify(df)
    else:
        df_work = df.copy()

    sig = inspect.signature(mod.generate_signals)
    if "asset" in sig.parameters:
        signals = mod.generate_signals(df_work, asset=strat["asset"])
    else:
        signals = mod.generate_signals(df_work)

    # Apply gate
    if gate_mode == "atr" and "regime" in df_work.columns:
        signals = signals.copy()
        signals.loc[df_work["regime"] == "low", "signal"] = 0
    elif gate_mode == "regime_profiled" and profiles and strat["label"] in profiles:
        profile = profiles[strat["label"]]
        avoid = set(profile.get("avoid_regimes", []))
        if avoid and all(col in df_work.columns for col in ["vol_regime", "trend_regime", "rv_regime"]):
            signals = signals.copy()
            for _, row in df_work.iterrows():
                current = {row.get("vol_regime"), row.get("trend_regime"), row.get("rv_regime")}
                if avoid & current:
                    signals.loc[row.name, "signal"] = 0

    result = run_backtest(
        df_work, signals,
        mode=strat["mode"],
        point_value=strat["point_value"],
        symbol=strat["asset"],
    )
    return result


def get_daily_pnl(trades_df):
    """Extract daily PnL series from trades."""
    if trades_df.empty:
        return pd.Series(dtype=float)
    t = trades_df.copy()
    t["_date"] = pd.to_datetime(t["exit_time"]).dt.date
    daily = t.groupby("_date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def compute_portfolio_metrics(daily_pnl, label):
    """Compute portfolio-level metrics from combined daily PnL."""
    if daily_pnl.empty or len(daily_pnl) == 0:
        return {"label": label, "pnl": 0, "sharpe": 0, "maxdd": 0, "calmar": 0,
                "trades": 0, "monthly_pct": 0}

    total_pnl = daily_pnl.sum()

    # Sharpe
    if len(daily_pnl) > 1 and daily_pnl.std() > 0:
        sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    # MaxDD
    equity = STARTING_CAPITAL + daily_pnl.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    maxdd = dd.max()

    # Calmar
    calmar = total_pnl / maxdd if maxdd > 0 else 0

    # Monthly consistency
    monthly = daily_pnl.resample("ME").sum()
    profitable_months = (monthly > 0).sum()
    total_months = len(monthly)
    monthly_pct = round(profitable_months / total_months * 100, 1) if total_months > 0 else 0

    return {
        "label": label,
        "pnl": round(total_pnl, 2),
        "sharpe": round(sharpe, 4),
        "maxdd": round(maxdd, 2),
        "calmar": round(calmar, 4),
        "profitable_months": profitable_months,
        "total_months": total_months,
        "monthly_pct": monthly_pct,
    }


def simulate_portfolio(strategies, gate_mode, engine=None, profiles=None):
    """Run all strategies in a portfolio under a gating mode."""
    daily_pnls = {}
    total_trades = 0

    for strat in strategies:
        result = run_strategy_mode(
            strat, gate_mode=gate_mode,
            profiles=profiles, engine=engine,
        )
        trades = result["trades_df"]
        total_trades += len(trades)
        daily_pnls[strat["label"]] = get_daily_pnl(trades)

    # Combine to portfolio
    combined = pd.DataFrame(daily_pnls).fillna(0)
    portfolio_daily = combined.sum(axis=1)

    return portfolio_daily, total_trades, combined


def main():
    print("=" * 70)
    print("  PHASE 8 — PORTFOLIO REGIME SIMULATION")
    print("  (Baseline vs ATR-Gated vs Regime-Profiled)")
    print("=" * 70)

    engine = RegimeEngine()

    # Load profiles (generated by regime_performance_report.py)
    profiles = {}
    if PROFILES_PATH.exists():
        with open(PROFILES_PATH) as f:
            profiles = json.load(f)
        print(f"\n  Loaded profiles for: {list(profiles.keys())}")
    else:
        print(f"\n  WARNING: No profiles found at {PROFILES_PATH}")
        print("  Run regime_performance_report.py first to generate profiles.")
        print("  Proceeding with empty profiles (regime-profiled = baseline).")

    all_results = {}
    gate_modes = ["none", "atr", "regime_profiled"]
    mode_labels = {
        "none": "Baseline (no gate)",
        "atr": "ATR-Gated (skip low-vol)",
        "regime_profiled": "Regime-Profiled",
    }

    for portfolio_label, strategies in [("2-Strategy", STRATEGIES_2), ("3-Strategy", STRATEGIES_3)]:
        print(f"\n{'=' * 70}")
        print(f"  {portfolio_label} PORTFOLIO")
        strat_names = [s["label"] for s in strategies]
        print(f"  Strategies: {', '.join(strat_names)}")
        print(f"{'=' * 70}")

        portfolio_results = {}

        for gate_mode in gate_modes:
            label = mode_labels[gate_mode]
            print(f"\n  {'─' * 60}")
            print(f"  {label}")
            print(f"  {'─' * 60}")

            portfolio_daily, total_trades, combined = simulate_portfolio(
                strategies, gate_mode, engine=engine, profiles=profiles,
            )

            metrics = compute_portfolio_metrics(portfolio_daily, label)
            metrics["total_trades"] = total_trades

            # Per-strategy breakdown
            per_strat = {}
            for col in combined.columns:
                strat_daily = combined[col]
                strat_m = compute_portfolio_metrics(strat_daily, col)
                per_strat[col] = strat_m

            metrics["per_strategy"] = per_strat

            print(f"  PnL: ${metrics['pnl']:,.2f}")
            print(f"  Sharpe: {metrics['sharpe']:.4f}")
            print(f"  Calmar: {metrics['calmar']:.4f}")
            print(f"  MaxDD: ${metrics['maxdd']:,.2f}")
            print(f"  Trades: {total_trades}")
            print(f"  Monthly: {metrics.get('profitable_months', 0)}/"
                  f"{metrics.get('total_months', 0)} ({metrics['monthly_pct']}%)")

            portfolio_results[gate_mode] = metrics

        # Comparison table
        print(f"\n  {'─' * 60}")
        print(f"  COMPARISON — {portfolio_label}")
        print(f"  {'─' * 60}")
        print(f"  {'Mode':<25} {'PnL':>10} {'Sharpe':>8} {'Calmar':>8} "
              f"{'MaxDD':>10} {'Trades':>7} {'Mo%':>6}")
        print(f"  {'─' * 76}")
        for gate_mode in gate_modes:
            m = portfolio_results[gate_mode]
            print(f"  {mode_labels[gate_mode]:<25} ${m['pnl']:>9,.2f} "
                  f"{m['sharpe']:>8.4f} {m['calmar']:>8.4f} "
                  f"${m['maxdd']:>9,.2f} {m['total_trades']:>7} "
                  f"{m['monthly_pct']:>5.1f}%")

        all_results[portfolio_label] = portfolio_results

    # ── Save results ─────────────────────────────────────────────────────────
    with open(OUTPUT_DIR / "regime_portfolio_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n  Saved to: {OUTPUT_DIR / 'regime_portfolio_results.json'}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
