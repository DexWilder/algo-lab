"""Portfolio equity curve — combines validated strategies into a single stream.

Runs PB-MGC-Short + PB-MNQ-Long + ORB-009 MGC-Long with transaction costs,
aligns daily PnL, and computes combined portfolio metrics.

Usage:
    python3 research/portfolio/combined_equity.py
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
from engine.statistics import bootstrap_metrics, deflated_sharpe_ratio
from backtests.run_baseline import compute_extended_metrics

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STRATEGIES = [
    {"name": "pb_trend",  "asset": "MGC", "mode": "short", "label": "PB-MGC-Short",  "point_value": 10.0, "tick_size": 0.10},
    {"name": "pb_trend",  "asset": "MNQ", "mode": "long",  "label": "PB-MNQ-Long",   "point_value": 2.0,  "tick_size": 0.25},
    {"name": "orb_009",   "asset": "MGC", "mode": "long",  "label": "ORB009-MGC-Long","point_value": 10.0, "tick_size": 0.10},
]

# Number of trials tested (for DSR correction)
N_TRIALS = 36  # 4 strategies × 3 assets × 3 modes


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


def run_strategy(strat):
    """Run a single strategy with transaction costs, return daily PnL series + trades."""
    mod = load_strategy(strat["name"])
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
        symbol=strat["asset"],  # enables transaction costs
    )

    trades_df = result["trades_df"]
    if trades_df.empty:
        return pd.Series(dtype=float), trades_df

    # Compute daily PnL
    trades_df["_date"] = pd.to_datetime(trades_df["exit_time"]).dt.date
    daily_pnl = trades_df.groupby("_date")["pnl"].sum()
    daily_pnl.index = pd.to_datetime(daily_pnl.index)

    return daily_pnl, trades_df


def main():
    print("=" * 70)
    print("  PORTFOLIO EQUITY CURVE — Combined Strategy Analysis")
    print("  (With Transaction Costs)")
    print("=" * 70)

    all_daily = {}
    all_trades = {}
    strategy_metrics = {}

    for strat in STRATEGIES:
        label = strat["label"]
        print(f"\n  Running {label}...")
        daily_pnl, trades_df = run_strategy(strat)
        all_daily[label] = daily_pnl
        all_trades[label] = trades_df

        if not daily_pnl.empty:
            total_pnl = daily_pnl.sum()
            sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252) if daily_pnl.std() > 0 else 0
            print(f"    {len(trades_df)} trades, PnL=${total_pnl:,.2f}, Sharpe={sharpe:.2f}")

            # Bootstrap CIs
            boot = bootstrap_metrics(trades_df["pnl"].values)
            strategy_metrics[label] = {
                "trades": len(trades_df),
                "pnl": round(total_pnl, 2),
                "sharpe": round(sharpe, 4),
                "bootstrap_pf_ci": [boot["pf"]["ci_low"], boot["pf"]["ci_high"]],
                "bootstrap_sharpe_ci": [boot["sharpe"]["ci_low"], boot["sharpe"]["ci_high"]],
                "bootstrap_maxdd_ci": [boot["max_dd"]["ci_low"], boot["max_dd"]["ci_high"]],
                "pf_point": boot["pf"]["point_estimate"],
            }
            print(f"    Bootstrap PF 95% CI: [{boot['pf']['ci_low']:.3f}, {boot['pf']['ci_high']:.3f}]")

    # ── Combine into portfolio ────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  PORTFOLIO COMBINATION")
    print(f"{'='*70}")

    # Align all daily PnL to common date index
    combined = pd.DataFrame(all_daily)
    combined = combined.fillna(0)
    combined["portfolio"] = combined.sum(axis=1)

    # Date range
    date_range = f"{combined.index.min().date()} to {combined.index.max().date()}"
    print(f"  Date range: {date_range}")
    print(f"  Trading days: {len(combined)}")

    # Portfolio metrics
    port_pnl = combined["portfolio"]
    port_total = port_pnl.sum()
    port_sharpe = port_pnl.mean() / port_pnl.std() * np.sqrt(252) if port_pnl.std() > 0 else 0

    # Portfolio equity curve and drawdown
    port_equity = 50_000 + port_pnl.cumsum()
    port_peak = port_equity.cummax()
    port_dd = port_peak - port_equity
    port_maxdd = port_dd.max()
    port_maxdd_pct = (port_maxdd / port_peak[port_dd.idxmax()]) * 100 if port_maxdd > 0 else 0

    # Recovery factor
    recovery_factor = port_total / port_maxdd if port_maxdd > 0 else float("inf")

    print(f"\n  Portfolio Total PnL: ${port_total:,.2f}")
    print(f"  Portfolio Sharpe:    {port_sharpe:.4f}")
    print(f"  Portfolio MaxDD:     ${port_maxdd:,.2f} ({port_maxdd_pct:.2f}%)")
    print(f"  Recovery Factor:     {recovery_factor:.2f}")

    # ── Individual strategy daily PnL stats ───────────────────────────────
    print(f"\n  Daily PnL Correlations:")
    corr = combined.drop(columns=["portfolio"]).corr()
    for i, c1 in enumerate(corr.columns):
        for c2 in corr.columns[i+1:]:
            print(f"    {c1} vs {c2}: r={corr.loc[c1, c2]:.4f}")

    # ── Drawdown overlap analysis ─────────────────────────────────────────
    print(f"\n  Drawdown Overlap Analysis:")
    # For each pair, check if drawdowns co-occur
    for label in all_daily:
        s = combined[label]
        eq = 50_000 + s.cumsum()
        pk = eq.cummax()
        dd = pk - eq
        in_dd = dd > 0
        combined[f"{label}_in_dd"] = in_dd

    dd_cols = [c for c in combined.columns if c.endswith("_in_dd")]
    for i, c1 in enumerate(dd_cols):
        l1 = c1.replace("_in_dd", "")
        for c2 in dd_cols[i+1:]:
            l2 = c2.replace("_in_dd", "")
            both_dd = (combined[c1] & combined[c2]).sum()
            either_dd = (combined[c1] | combined[c2]).sum()
            overlap = both_dd / either_dd * 100 if either_dd > 0 else 0
            print(f"    {l1} + {l2}: {overlap:.1f}% drawdown overlap "
                  f"({both_dd} days both in DD)")

    # ── DSR for portfolio ─────────────────────────────────────────────────
    print(f"\n  Deflated Sharpe Ratio (N={N_TRIALS} trials tested):")
    dsr = deflated_sharpe_ratio(
        observed_sharpe=port_sharpe,
        n_trials=N_TRIALS,
        n_observations=len(port_pnl),
        returns=port_pnl.values,
    )
    print(f"    DSR = {dsr['dsr']:.4f} {'✓ SIGNIFICANT' if dsr['significant'] else '✗ NOT SIGNIFICANT'}")
    print(f"    Expected max Sharpe under null: {dsr['expected_max_sharpe']:.4f}")
    print(f"    Observed portfolio Sharpe: {dsr['observed_sharpe']:.4f}")

    # ── Per-strategy DSR ──────────────────────────────────────────────────
    for label in all_daily:
        s = combined[label]
        s_nonzero = s[s != 0]
        if len(s_nonzero) > 1 and s_nonzero.std() > 0:
            obs_sr = s_nonzero.mean() / s_nonzero.std() * np.sqrt(252)
            d = deflated_sharpe_ratio(
                observed_sharpe=obs_sr,
                n_trials=N_TRIALS,
                n_observations=len(s_nonzero),
                returns=s_nonzero.values,
            )
            print(f"    {label}: DSR={d['dsr']:.4f} "
                  f"{'✓' if d['significant'] else '✗'} "
                  f"(Sharpe={obs_sr:.2f})")

    # ── Bootstrap portfolio ───────────────────────────────────────────────
    # Combine all trade PnLs for portfolio-level bootstrap
    all_trade_pnl = pd.concat([t["pnl"] for t in all_trades.values()]).values
    port_boot = bootstrap_metrics(all_trade_pnl)
    print(f"\n  Portfolio Bootstrap CIs (95%):")
    print(f"    PF:    [{port_boot['pf']['ci_low']:.3f}, {port_boot['pf']['ci_high']:.3f}] "
          f"(point: {port_boot['pf']['point_estimate']:.3f})")
    print(f"    MaxDD: [{port_boot['max_dd']['ci_low']:.0f}, {port_boot['max_dd']['ci_high']:.0f}] "
          f"(point: {port_boot['max_dd']['point_estimate']:.0f})")

    # ── Save outputs ──────────────────────────────────────────────────────
    # Daily PnL CSV
    export = combined[[c for c in combined.columns if not c.endswith("_in_dd")]].copy()
    export.to_csv(OUTPUT_DIR / "combined_daily_pnl.csv")

    # Portfolio equity curve
    eq_export = pd.DataFrame({
        "date": port_equity.index,
        "equity": port_equity.values,
        "drawdown": port_dd.values,
    })
    eq_export.to_csv(OUTPUT_DIR / "portfolio_equity_curve.csv", index=False)

    # Full metrics JSON
    portfolio_report = {
        "date_range": date_range,
        "trading_days": len(combined),
        "strategies": strategy_metrics,
        "portfolio": {
            "total_pnl": round(port_total, 2),
            "sharpe": round(port_sharpe, 4),
            "max_drawdown": round(port_maxdd, 2),
            "max_drawdown_pct": round(port_maxdd_pct, 2),
            "recovery_factor": round(recovery_factor, 2),
            "total_trades": sum(len(t) for t in all_trades.values()),
        },
        "correlations": {
            f"{c1}_vs_{c2}": round(corr.loc[c1, c2], 4)
            for i, c1 in enumerate(corr.columns)
            for c2 in corr.columns[i+1:]
        },
        "dsr": dsr,
        "bootstrap": {
            "pf_ci": [port_boot["pf"]["ci_low"], port_boot["pf"]["ci_high"]],
            "pf_point": port_boot["pf"]["point_estimate"],
            "maxdd_ci": [port_boot["max_dd"]["ci_low"], port_boot["max_dd"]["ci_high"]],
        },
    }
    with open(OUTPUT_DIR / "portfolio_metrics.json", "w") as f:
        json.dump(portfolio_report, f, indent=2, default=str)

    print(f"\n  Saved to: {OUTPUT_DIR}")
    print(f"    combined_daily_pnl.csv")
    print(f"    portfolio_equity_curve.csv")
    print(f"    portfolio_metrics.json")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
