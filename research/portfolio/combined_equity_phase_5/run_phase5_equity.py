"""Phase 5.4 — Combined Equity Simulation.

Runs the 2-strategy portfolio (PB-MGC-Short + ORB-009 MGC-Long) with:
- Transaction costs
- ATR regime gate (skip low-vol days) on both strategies
- Equal weight sizing (1 contract each)

Outputs:
- combined equity curves (gated vs ungated)
- portfolio Sharpe, MaxDD, monthly breakdown
- worst drawdown periods
- per-strategy contribution analysis

Usage:
    python3 research/portfolio/combined_equity_phase_5/run_phase5_equity.py
"""

import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime import classify_regimes
from engine.statistics import bootstrap_metrics, deflated_sharpe_ratio

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

STARTING_CAPITAL = 50_000.0
N_TRIALS = 36  # for DSR

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


def run_strategy_gated(strat, gate_low=True):
    """Run strategy with costs and optional regime gate."""
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

    if gate_low:
        signals = signals.copy()
        low_mask = df_regime["regime"] == "low"
        signals.loc[low_mask, "signal"] = 0

    result = run_backtest(
        df_regime, signals,
        mode=strat["mode"],
        point_value=strat["point_value"],
        symbol=strat["asset"],
    )
    return result


def strategy_metrics(trades_df, daily_pnl, label):
    """Compute per-strategy metrics."""
    if trades_df.empty:
        return {"label": label, "trades": 0}

    pnl = trades_df["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = wins.sum() if len(wins) else 0
    gross_loss = abs(losses.sum()) if len(losses) else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (100.0 if gross_profit > 0 else 0)

    sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252) if len(daily_pnl) > 1 and daily_pnl.std() > 0 else 0

    equity = STARTING_CAPITAL + np.cumsum(pnl.values)
    peak = np.maximum.accumulate(equity)
    maxdd = (peak - equity).max()

    boot = bootstrap_metrics(pnl.values)

    return {
        "label": label,
        "trades": len(trades_df),
        "pf": round(pf, 3),
        "sharpe": round(sharpe, 4),
        "pnl": round(pnl.sum(), 2),
        "maxdd": round(maxdd, 2),
        "wr": round(len(wins) / len(pnl) * 100, 1),
        "exp": round(pnl.mean(), 2),
        "bootstrap_pf_ci": [boot["pf"]["ci_low"], boot["pf"]["ci_high"]],
        "bootstrap_sharpe_ci": [boot["sharpe"]["ci_low"], boot["sharpe"]["ci_high"]],
    }


def main():
    print("=" * 70)
    print("  PHASE 5.4 — COMBINED EQUITY SIMULATION")
    print("  (Regime-Gated 2-Strategy Portfolio)")
    print("=" * 70)

    # ── Run both versions ────────────────────────────────────────────────────
    variants = {
        "ungated": {},
        "gated": {},
    }

    for variant_name, gate_low in [("ungated", False), ("gated", True)]:
        print(f"\n  Running {variant_name} portfolio...")
        daily_pnls = {}
        all_trades = {}
        strat_metrics = {}

        for strat in STRATEGIES:
            label = strat["label"]
            result = run_strategy_gated(strat, gate_low=gate_low)
            trades = result["trades_df"]
            all_trades[label] = trades

            if not trades.empty:
                trades_copy = trades.copy()
                trades_copy["_date"] = pd.to_datetime(trades_copy["exit_time"]).dt.date
                daily = trades_copy.groupby("_date")["pnl"].sum()
                daily.index = pd.to_datetime(daily.index)
                daily_pnls[label] = daily

                sm = strategy_metrics(trades, daily, label)
                strat_metrics[label] = sm
                print(f"    {label}: {sm['trades']} trades, PF={sm['pf']}, "
                      f"PnL=${sm['pnl']:,.2f}, Sharpe={sm['sharpe']}")

        variants[variant_name] = {
            "daily_pnls": daily_pnls,
            "all_trades": all_trades,
            "strat_metrics": strat_metrics,
        }

    # ── Build portfolio equity curves ────────────────────────────────────────
    for variant_name in ["ungated", "gated"]:
        v = variants[variant_name]
        combined = pd.DataFrame(v["daily_pnls"]).fillna(0)
        combined["portfolio"] = combined.sum(axis=1)
        v["combined"] = combined

    # ── Gated Portfolio Deep Analysis ────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  GATED PORTFOLIO — DETAILED ANALYSIS")
    print(f"{'=' * 70}")

    gated = variants["gated"]
    combined = gated["combined"]
    labels = list(gated["daily_pnls"].keys())
    l1, l2 = labels[0], labels[1]

    port_pnl = combined["portfolio"]
    port_total = port_pnl.sum()
    port_sharpe = port_pnl.mean() / port_pnl.std() * np.sqrt(252) if port_pnl.std() > 0 else 0

    port_equity = STARTING_CAPITAL + port_pnl.cumsum()
    port_peak = port_equity.cummax()
    port_dd = port_peak - port_equity
    port_maxdd = port_dd.max()
    port_maxdd_pct = (port_maxdd / port_peak[port_dd.idxmax()]) * 100 if port_maxdd > 0 else 0
    recovery = port_total / port_maxdd if port_maxdd > 0 else float("inf")

    total_trades = sum(len(t) for t in gated["all_trades"].values())

    print(f"\n  Portfolio Metrics:")
    print(f"    Total PnL:       ${port_total:,.2f}")
    print(f"    Sharpe:          {port_sharpe:.4f}")
    print(f"    MaxDD:           ${port_maxdd:,.2f} ({port_maxdd_pct:.2f}%)")
    print(f"    Recovery Factor: {recovery:.2f}")
    print(f"    Total Trades:    {total_trades}")
    print(f"    Trading Days:    {len(combined)}")

    # Daily PnL correlation
    corr = combined[l1].corr(combined[l2])
    print(f"    Daily PnL Corr:  {corr:.4f}")

    # DSR for gated portfolio
    print(f"\n  Deflated Sharpe Ratio (N={N_TRIALS} trials):")
    dsr = deflated_sharpe_ratio(
        observed_sharpe=port_sharpe,
        n_trials=N_TRIALS,
        n_observations=len(port_pnl),
        returns=port_pnl.values,
    )
    print(f"    DSR = {dsr['dsr']:.4f} {'SIGNIFICANT' if dsr['significant'] else 'NOT SIGNIFICANT'}")
    print(f"    Expected max Sharpe under null: {dsr['expected_max_sharpe']:.4f}")

    # Per-strategy DSR
    for label in labels:
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
                  f"{'SIG' if d['significant'] else 'NOT SIG'} (Sharpe={obs_sr:.2f})")

    # Bootstrap portfolio
    all_trade_pnl = pd.concat([t["pnl"] for t in gated["all_trades"].values()]).values
    port_boot = bootstrap_metrics(all_trade_pnl)
    print(f"\n  Portfolio Bootstrap CIs (95%):")
    print(f"    PF: [{port_boot['pf']['ci_low']:.3f}, {port_boot['pf']['ci_high']:.3f}] "
          f"(point: {port_boot['pf']['point_estimate']:.3f})")
    print(f"    MaxDD: [{port_boot['max_dd']['ci_low']:.0f}, {port_boot['max_dd']['ci_high']:.0f}]")

    # ── Monthly Breakdown ────────────────────────────────────────────────────
    print(f"\n  Monthly PnL Breakdown:")
    combined["_month"] = combined.index.to_period("M")
    monthly = combined.groupby("_month").agg(
        pb_pnl=(l1, "sum"),
        orb_pnl=(l2, "sum"),
        port_pnl=("portfolio", "sum"),
    )

    print(f"  {'Month':<10} {'PB-Short':>10} {'ORB-Long':>10} {'Portfolio':>10}")
    print(f"  {'─' * 45}")
    for idx, row in monthly.iterrows():
        marker = " +" if row["port_pnl"] > 0 else " -"
        print(f"  {str(idx):<10} ${row['pb_pnl']:>9.2f} ${row['orb_pnl']:>9.2f} ${row['port_pnl']:>9.2f}{marker}")

    profitable = (monthly["port_pnl"] > 0).sum()
    total_m = len(monthly)
    print(f"\n  Profitable months: {profitable}/{total_m} ({profitable/total_m*100:.0f}%)")

    # Best/worst months
    best_month = monthly["port_pnl"].idxmax()
    worst_month = monthly["port_pnl"].idxmin()
    print(f"  Best month:  {best_month} (${monthly.loc[best_month, 'port_pnl']:,.2f})")
    print(f"  Worst month: {worst_month} (${monthly.loc[worst_month, 'port_pnl']:,.2f})")

    # ── Worst Drawdown Periods ───────────────────────────────────────────────
    print(f"\n  Worst Drawdown Periods:")
    dd_start = None
    worst_periods = []
    for i in range(len(port_dd)):
        if port_dd.iloc[i] > 0 and dd_start is None:
            dd_start = port_dd.index[i]
        elif port_dd.iloc[i] == 0 and dd_start is not None:
            dd_end = port_dd.index[i-1]
            peak_dd = port_dd.loc[dd_start:dd_end].max()
            duration = (dd_end - dd_start).days
            worst_periods.append({"start": dd_start, "end": dd_end, "depth": peak_dd, "days": duration})
            dd_start = None
    if dd_start is not None:
        dd_end = port_dd.index[-1]
        peak_dd = port_dd.loc[dd_start:dd_end].max()
        duration = (dd_end - dd_start).days
        worst_periods.append({"start": dd_start, "end": dd_end, "depth": peak_dd, "days": duration})

    worst_periods.sort(key=lambda x: x["depth"], reverse=True)
    for j, wp in enumerate(worst_periods[:5]):
        print(f"    {j+1}. ${wp['depth']:,.2f} over {wp['days']}d "
              f"({wp['start'].strftime('%Y-%m-%d')} to {wp['end'].strftime('%Y-%m-%d')})")

    # ── Ungated vs Gated Comparison ──────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  UNGATED vs GATED PORTFOLIO COMPARISON")
    print(f"{'─' * 70}")

    ungated = variants["ungated"]
    u_combined = ungated["combined"]
    u_port = u_combined["portfolio"]
    u_total = u_port.sum()
    u_sharpe = u_port.mean() / u_port.std() * np.sqrt(252) if u_port.std() > 0 else 0
    u_eq = STARTING_CAPITAL + u_port.cumsum()
    u_pk = u_eq.cummax()
    u_dd = u_pk - u_eq
    u_maxdd = u_dd.max()
    u_trades = sum(len(t) for t in ungated["all_trades"].values())

    print(f"  {'Metric':<20} {'Ungated':>12} {'Gated':>12} {'Delta':>12}")
    print(f"  {'─' * 60}")
    print(f"  {'Total PnL':<20} ${u_total:>11,.2f} ${port_total:>11,.2f} ${port_total-u_total:>+11,.2f}")
    print(f"  {'Sharpe':<20} {u_sharpe:>12.2f} {port_sharpe:>12.2f} {port_sharpe-u_sharpe:>+12.2f}")
    print(f"  {'MaxDD':<20} ${u_maxdd:>11,.2f} ${port_maxdd:>11,.2f} ${port_maxdd-u_maxdd:>+11,.2f}")
    print(f"  {'Total Trades':<20} {u_trades:>12} {total_trades:>12} {total_trades-u_trades:>+12}")

    # ── Save outputs ─────────────────────────────────────────────────────────
    # Equity curve CSV
    eq_export = pd.DataFrame({
        "date": port_equity.index,
        "equity": port_equity.values,
        "drawdown": port_dd.values,
    })
    eq_export.to_csv(OUTPUT_DIR / "equity_curve.csv", index=False)

    # Daily PnL CSV
    export = combined[[c for c in combined.columns if c != "_month"]].copy()
    export.to_csv(OUTPUT_DIR / "daily_pnl.csv")

    # Full metrics JSON
    report = {
        "date_range": f"{combined.index.min().date()} to {combined.index.max().date()}",
        "regime_gate": "skip low-vol days (ATR < 33rd percentile)",
        "strategies": {k: v for k, v in gated["strat_metrics"].items()},
        "portfolio_gated": {
            "total_pnl": round(port_total, 2),
            "sharpe": round(port_sharpe, 4),
            "maxdd": round(port_maxdd, 2),
            "maxdd_pct": round(port_maxdd_pct, 2),
            "recovery_factor": round(recovery, 2),
            "total_trades": total_trades,
            "daily_pnl_corr": round(corr, 4),
            "profitable_months": f"{profitable}/{total_m}",
        },
        "portfolio_ungated": {
            "total_pnl": round(u_total, 2),
            "sharpe": round(u_sharpe, 4),
            "maxdd": round(u_maxdd, 2),
            "total_trades": u_trades,
        },
        "dsr": dsr,
        "bootstrap": {
            "pf_ci": [port_boot["pf"]["ci_low"], port_boot["pf"]["ci_high"]],
            "pf_point": port_boot["pf"]["point_estimate"],
            "maxdd_ci": [port_boot["max_dd"]["ci_low"], port_boot["max_dd"]["ci_high"]],
        },
        "worst_drawdowns": [
            {
                "start": wp["start"].strftime("%Y-%m-%d"),
                "end": wp["end"].strftime("%Y-%m-%d"),
                "depth": round(wp["depth"], 2),
                "days": wp["days"],
            }
            for wp in worst_periods[:5]
        ],
        "monthly_pnl": {
            str(idx): {
                "pb_short": round(row["pb_pnl"], 2),
                "orb_long": round(row["orb_pnl"], 2),
                "portfolio": round(row["port_pnl"], 2),
            }
            for idx, row in monthly.iterrows()
        },
    }

    with open(OUTPUT_DIR / "phase5_metrics.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n  Saved to: {OUTPUT_DIR}")
    print(f"    equity_curve.csv")
    print(f"    daily_pnl.csv")
    print(f"    phase5_metrics.json")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
