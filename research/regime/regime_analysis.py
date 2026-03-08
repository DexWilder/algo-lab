"""Phase 5 — Regime Analysis for validated strategies.

Runs ATR regime classification on ORB-009 MGC-Long and PB-MGC-Short.
Reports per-regime PF, Sharpe, PnL, trade count.
Tests whether a simple regime gate (skip low-vol days) improves net performance.

Usage:
    python3 research/regime/regime_analysis.py
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
from engine.regime import classify_regimes, regime_breakdown
from engine.statistics import bootstrap_metrics

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STRATEGIES = [
    {
        "name": "orb_009",
        "asset": "MGC",
        "mode": "long",
        "label": "ORB-009 MGC-Long",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
    {
        "name": "pb_trend",
        "asset": "MGC",
        "mode": "short",
        "label": "PB-MGC-Short",
        "point_value": 10.0,
        "tick_size": 0.10,
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


def run_with_costs(strat, df_with_regime=None):
    """Run strategy with transaction costs. Optionally pass pre-classified df."""
    mod = load_strategy(strat["name"])
    df = df_with_regime if df_with_regime is not None else load_data(strat["asset"])

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


def compute_metrics(trades_df, daily_pnl=None):
    """Compute standard metrics from trades."""
    if trades_df.empty:
        return {"trades": 0, "pf": 0, "sharpe": 0, "pnl": 0, "maxdd": 0, "wr": 0, "exp": 0}

    pnl = trades_df["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = wins.sum() if len(wins) else 0
    gross_loss = abs(losses.sum()) if len(losses) else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (100.0 if gross_profit > 0 else 0)

    # Sharpe from daily PnL
    if daily_pnl is not None and len(daily_pnl) > 1 and daily_pnl.std() > 0:
        sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    equity = 50_000 + np.cumsum(pnl.values)
    peak = np.maximum.accumulate(equity)
    maxdd = (peak - equity).max()

    return {
        "trades": len(trades_df),
        "pf": round(pf, 3),
        "sharpe": round(sharpe, 4),
        "pnl": round(pnl.sum(), 2),
        "maxdd": round(maxdd, 2),
        "wr": round(len(wins) / len(pnl) * 100, 1),
        "exp": round(pnl.mean(), 2),
    }


def test_regime_gate(strat, regime_to_skip="low"):
    """Test gated strategy: zero out signals on low-vol days, re-backtest."""
    mod = load_strategy(strat["name"])
    df = load_data(strat["asset"])

    # Classify regimes
    df_regime = classify_regimes(df)

    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = strat["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    if "asset" in sig.parameters:
        signals = mod.generate_signals(df_regime, asset=strat["asset"])
    else:
        signals = mod.generate_signals(df_regime)

    # Gate: zero out signals on low-vol days
    signals_gated = signals.copy()
    low_mask = df_regime["regime"] == regime_to_skip
    signals_gated.loc[low_mask, "signal"] = 0

    result_gated = run_backtest(
        df_regime, signals_gated,
        mode=strat["mode"],
        point_value=strat["point_value"],
        symbol=strat["asset"],
    )

    # Also run ungated for comparison
    result_ungated = run_backtest(
        df_regime, signals,
        mode=strat["mode"],
        point_value=strat["point_value"],
        symbol=strat["asset"],
    )

    return result_ungated, result_gated, df_regime


def main():
    print("=" * 70)
    print("  PHASE 5 — REGIME ANALYSIS")
    print("  (ATR Percentile Volatility Regimes)")
    print("=" * 70)

    all_results = {}

    for strat in STRATEGIES:
        label = strat["label"]
        print(f"\n{'─' * 70}")
        print(f"  {label}")
        print(f"{'─' * 70}")

        # Run ungated and gated
        result_ungated, result_gated, df_regime = test_regime_gate(strat, regime_to_skip="low")

        # Regime breakdown (ungated)
        trades_ungated = result_ungated["trades_df"]
        breakdown = regime_breakdown(trades_ungated, df_regime, point_value=strat["point_value"])

        print(f"\n  Regime Breakdown (ungated, with costs):")
        print(f"  {'Regime':<10} {'Trades':>7} {'PF':>7} {'Sharpe':>8} {'PnL':>10} {'WR':>6} {'Exp':>8}")
        print(f"  {'─' * 60}")
        for _, row in breakdown.iterrows():
            print(f"  {row['regime']:<10} {row['trades']:>7} {row['pf']:>7.2f} {row['sharpe']:>8.2f} "
                  f"${row['pnl']:>9.2f} {row['wr']:>5.1f}% ${row['exp']:>7.2f}")

        # Ungated metrics
        trades_u = result_ungated["trades_df"]
        if not trades_u.empty:
            trades_u["_date"] = pd.to_datetime(trades_u["exit_time"]).dt.date
            daily_u = trades_u.groupby("_date")["pnl"].sum()
            daily_u.index = pd.to_datetime(daily_u.index)
        else:
            daily_u = pd.Series(dtype=float)
        m_ungated = compute_metrics(trades_u, daily_u)

        # Gated metrics
        trades_g = result_gated["trades_df"]
        if not trades_g.empty:
            trades_g["_date"] = pd.to_datetime(trades_g["exit_time"]).dt.date
            daily_g = trades_g.groupby("_date")["pnl"].sum()
            daily_g.index = pd.to_datetime(daily_g.index)
        else:
            daily_g = pd.Series(dtype=float)
        m_gated = compute_metrics(trades_g, daily_g)

        print(f"\n  Ungated vs Gated (skip low-vol):")
        print(f"  {'Metric':<15} {'Ungated':>12} {'Gated':>12} {'Delta':>12}")
        print(f"  {'─' * 55}")
        for key in ["trades", "pf", "sharpe", "pnl", "maxdd", "wr", "exp"]:
            u_val = m_ungated[key]
            g_val = m_gated[key]
            if isinstance(u_val, float):
                delta = g_val - u_val
                print(f"  {key:<15} {u_val:>12.2f} {g_val:>12.2f} {delta:>+12.2f}")
            else:
                delta = g_val - u_val
                print(f"  {key:<15} {u_val:>12} {g_val:>12} {delta:>+12}")

        # Bootstrap CIs for gated version
        if not trades_g.empty and len(trades_g) > 5:
            boot = bootstrap_metrics(trades_g["pnl"].values)
            print(f"\n  Gated Bootstrap PF 95% CI: [{boot['pf']['ci_low']:.3f}, {boot['pf']['ci_high']:.3f}]")
            print(f"  Gated Bootstrap Sharpe CI: [{boot['sharpe']['ci_low']:.3f}, {boot['sharpe']['ci_high']:.3f}]")
        else:
            boot = None

        # Gate verdict
        pf_improved = m_gated["pf"] > m_ungated["pf"]
        dd_improved = m_gated["maxdd"] < m_ungated["maxdd"]
        pnl_preserved = m_gated["pnl"] >= m_ungated["pnl"] * 0.85  # preserve 85%+ of PnL

        verdict = "BENEFICIAL" if (pf_improved and pnl_preserved) else "NOT RECOMMENDED"
        print(f"\n  Gate Verdict: {verdict}")
        print(f"    PF improved: {'YES' if pf_improved else 'NO'}")
        print(f"    DD improved: {'YES' if dd_improved else 'NO'}")
        print(f"    PnL preserved (>85%): {'YES' if pnl_preserved else 'NO'}")

        all_results[label] = {
            "regime_breakdown": breakdown.to_dict(orient="records"),
            "ungated": m_ungated,
            "gated": m_gated,
            "gate_verdict": verdict,
            "gated_bootstrap": {
                "pf_ci": [boot["pf"]["ci_low"], boot["pf"]["ci_high"]] if boot else None,
                "sharpe_ci": [boot["sharpe"]["ci_low"], boot["sharpe"]["ci_high"]] if boot else None,
            } if boot else None,
        }

    # ── Save results ─────────────────────────────────────────────────────────
    with open(OUTPUT_DIR / "regime_analysis.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print(f"  Results saved to: {OUTPUT_DIR / 'regime_analysis.json'}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
