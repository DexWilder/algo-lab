"""Phase 5.2 — Portfolio Overlap Realism.

Deep dive into the 2-strategy portfolio (PB-MGC-Short + ORB-009 MGC-Long):
- Return correlation (daily PnL)
- Trade date overlap
- Drawdown overlap (static + rolling 30-day)
- Rolling 30-day correlation
- Generates overlap_analysis.md report

Usage:
    python3 research/portfolio/overlap_analysis.py
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


def run_strategy(strat):
    """Run strategy with costs, return daily PnL + trades."""
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
        symbol=strat["asset"],
    )
    return result


def main():
    print("=" * 70)
    print("  PHASE 5.2 — PORTFOLIO OVERLAP REALISM")
    print("  (PB-MGC-Short + ORB-009 MGC-Long)")
    print("=" * 70)

    # ── Run both strategies ──────────────────────────────────────────────────
    results = {}
    daily_pnls = {}
    all_trades = {}

    for strat in STRATEGIES:
        label = strat["label"]
        print(f"\n  Running {label}...")
        result = run_strategy(strat)
        results[label] = result
        trades = result["trades_df"]
        all_trades[label] = trades

        if not trades.empty:
            trades["_date"] = pd.to_datetime(trades["exit_time"]).dt.date
            daily = trades.groupby("_date")["pnl"].sum()
            daily.index = pd.to_datetime(daily.index)
            daily_pnls[label] = daily
            print(f"    {len(trades)} trades, PnL=${trades['pnl'].sum():,.2f}")

    # ── Align daily PnL ──────────────────────────────────────────────────────
    combined = pd.DataFrame(daily_pnls).fillna(0)
    combined["portfolio"] = combined.sum(axis=1)

    labels = list(daily_pnls.keys())
    l1, l2 = labels[0], labels[1]

    # ── 1. Return Correlation ────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  1. RETURN CORRELATION (daily PnL)")
    print(f"{'─' * 70}")

    full_corr = combined[l1].corr(combined[l2])
    print(f"  Full-period correlation: r = {full_corr:.4f}")

    # Only days when both strategies traded
    both_active = combined[(combined[l1] != 0) & (combined[l2] != 0)]
    if len(both_active) > 5:
        active_corr = both_active[l1].corr(both_active[l2])
        print(f"  Active-days-only correlation: r = {active_corr:.4f} ({len(both_active)} days)")
    else:
        active_corr = None
        print(f"  Active-days-only: insufficient overlap ({len(both_active)} days)")

    # ── 2. Trade Date Overlap ────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  2. TRADE DATE OVERLAP")
    print(f"{'─' * 70}")

    dates_1 = set(all_trades[l1]["_date"].unique()) if not all_trades[l1].empty else set()
    dates_2 = set(all_trades[l2]["_date"].unique()) if not all_trades[l2].empty else set()

    overlap_dates = dates_1 & dates_2
    union_dates = dates_1 | dates_2

    print(f"  {l1} trading days: {len(dates_1)}")
    print(f"  {l2} trading days: {len(dates_2)}")
    print(f"  Days both traded: {len(overlap_dates)}")
    print(f"  Trade date overlap: {len(overlap_dates)/len(union_dates)*100:.1f}% (Jaccard)")

    # On overlap days, are they in the same or opposite direction?
    if len(overlap_dates) > 0:
        overlap_pnl = combined.loc[combined.index.isin([pd.Timestamp(d) for d in overlap_dates])]
        same_direction = ((overlap_pnl[l1] > 0) & (overlap_pnl[l2] > 0)) | \
                         ((overlap_pnl[l1] < 0) & (overlap_pnl[l2] < 0))
        print(f"  Same-direction days: {same_direction.sum()}/{len(overlap_pnl)} "
              f"({same_direction.mean()*100:.1f}%)")

    # ── 3. Drawdown Overlap ──────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  3. DRAWDOWN OVERLAP")
    print(f"{'─' * 70}")

    dd_data = {}
    for label in labels:
        eq = 50_000 + combined[label].cumsum()
        pk = eq.cummax()
        dd = pk - eq
        dd_pct = dd / pk * 100
        in_dd = dd > 0
        dd_data[label] = {"equity": eq, "drawdown": dd, "dd_pct": dd_pct, "in_dd": in_dd}

    both_in_dd = dd_data[l1]["in_dd"] & dd_data[l2]["in_dd"]
    either_in_dd = dd_data[l1]["in_dd"] | dd_data[l2]["in_dd"]
    dd_overlap = both_in_dd.sum() / either_in_dd.sum() * 100 if either_in_dd.sum() > 0 else 0

    print(f"  {l1} days in drawdown: {dd_data[l1]['in_dd'].sum()}")
    print(f"  {l2} days in drawdown: {dd_data[l2]['in_dd'].sum()}")
    print(f"  Days both in drawdown: {both_in_dd.sum()}")
    print(f"  Drawdown overlap: {dd_overlap:.1f}%")

    # Portfolio drawdown
    port_eq = 50_000 + combined["portfolio"].cumsum()
    port_pk = port_eq.cummax()
    port_dd = port_pk - port_eq
    port_maxdd = port_dd.max()
    port_in_dd = port_dd > 0

    print(f"\n  Portfolio MaxDD: ${port_maxdd:.2f}")
    print(f"  Portfolio days in drawdown: {port_in_dd.sum()}")

    # Worst drawdown periods
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
    print(f"\n  Top 5 Drawdown Periods:")
    for j, wp in enumerate(worst_periods[:5]):
        print(f"    {j+1}. ${wp['depth']:.2f} over {wp['days']}d "
              f"({wp['start'].strftime('%Y-%m-%d')} to {wp['end'].strftime('%Y-%m-%d')})")

    # ── 4. Rolling 30-Day Correlation ────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  4. ROLLING 30-DAY ANALYSIS")
    print(f"{'─' * 70}")

    roll_corr = combined[l1].rolling(30, min_periods=10).corr(combined[l2])
    roll_corr_clean = roll_corr.dropna()

    if len(roll_corr_clean) > 0:
        print(f"  Rolling 30d correlation:")
        print(f"    Mean:   {roll_corr_clean.mean():.4f}")
        print(f"    Median: {roll_corr_clean.median():.4f}")
        print(f"    Min:    {roll_corr_clean.min():.4f}")
        print(f"    Max:    {roll_corr_clean.max():.4f}")
        print(f"    Std:    {roll_corr_clean.std():.4f}")

        # Percentage of time correlation is negative (good)
        pct_neg = (roll_corr_clean < 0).mean() * 100
        print(f"    Days with negative correlation: {pct_neg:.1f}%")

    # Rolling 30d drawdown overlap
    roll_dd_overlap = (both_in_dd.rolling(30, min_periods=10).mean() * 100).dropna()
    if len(roll_dd_overlap) > 0:
        print(f"\n  Rolling 30d drawdown overlap:")
        print(f"    Mean:   {roll_dd_overlap.mean():.1f}%")
        print(f"    Median: {roll_dd_overlap.median():.1f}%")
        print(f"    Min:    {roll_dd_overlap.min():.1f}%")
        print(f"    Max:    {roll_dd_overlap.max():.1f}%")

    # ── 5. Portfolio Summary ─────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  5. 2-STRATEGY PORTFOLIO SUMMARY")
    print(f"{'─' * 70}")

    port_pnl = combined["portfolio"]
    port_total = port_pnl.sum()
    port_sharpe = port_pnl.mean() / port_pnl.std() * np.sqrt(252) if port_pnl.std() > 0 else 0
    total_trades = sum(len(t) for t in all_trades.values())

    print(f"  Total PnL: ${port_total:,.2f}")
    print(f"  Sharpe: {port_sharpe:.4f}")
    print(f"  MaxDD: ${port_maxdd:,.2f}")
    print(f"  Recovery Factor: {port_total/port_maxdd:.2f}" if port_maxdd > 0 else "  Recovery Factor: inf")
    print(f"  Total Trades: {total_trades}")
    print(f"  Trading Days: {len(combined)}")

    # Monthly breakdown
    print(f"\n  Monthly PnL Breakdown:")
    combined["_month"] = combined.index.to_period("M")
    monthly = combined.groupby("_month").agg(
        pb_pnl=(l1, "sum"),
        orb_pnl=(l2, "sum"),
        port_pnl=("portfolio", "sum"),
    )
    profitable_months = (monthly["port_pnl"] > 0).sum()
    total_months = len(monthly)
    print(f"  {'Month':<10} {'PB-Short':>10} {'ORB-Long':>10} {'Portfolio':>10}")
    print(f"  {'─' * 45}")
    for idx, row in monthly.iterrows():
        marker = " ✓" if row["port_pnl"] > 0 else " ✗"
        print(f"  {str(idx):<10} ${row['pb_pnl']:>9.2f} ${row['orb_pnl']:>9.2f} ${row['port_pnl']:>9.2f}{marker}")
    print(f"\n  Profitable months: {profitable_months}/{total_months} ({profitable_months/total_months*100:.0f}%)")

    # ── Save outputs ─────────────────────────────────────────────────────────
    report = {
        "strategies": [l1, l2],
        "date_range": f"{combined.index.min().date()} to {combined.index.max().date()}",
        "return_correlation": {
            "full_period": round(full_corr, 4),
            "active_days_only": round(active_corr, 4) if active_corr is not None else None,
        },
        "trade_overlap": {
            "dates_1": len(dates_1),
            "dates_2": len(dates_2),
            "overlap_dates": len(overlap_dates),
            "jaccard_pct": round(len(overlap_dates) / len(union_dates) * 100, 1) if union_dates else 0,
        },
        "drawdown_overlap": {
            "dd_days_1": int(dd_data[l1]["in_dd"].sum()),
            "dd_days_2": int(dd_data[l2]["in_dd"].sum()),
            "both_in_dd": int(both_in_dd.sum()),
            "overlap_pct": round(dd_overlap, 1),
        },
        "rolling_30d": {
            "correlation_mean": round(roll_corr_clean.mean(), 4) if len(roll_corr_clean) > 0 else None,
            "correlation_median": round(roll_corr_clean.median(), 4) if len(roll_corr_clean) > 0 else None,
            "pct_negative_corr": round(pct_neg, 1) if len(roll_corr_clean) > 0 else None,
            "dd_overlap_mean": round(roll_dd_overlap.mean(), 1) if len(roll_dd_overlap) > 0 else None,
        },
        "portfolio": {
            "total_pnl": round(port_total, 2),
            "sharpe": round(port_sharpe, 4),
            "maxdd": round(port_maxdd, 2),
            "recovery_factor": round(port_total / port_maxdd, 2) if port_maxdd > 0 else None,
            "total_trades": total_trades,
            "profitable_months": profitable_months,
            "total_months": total_months,
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

    with open(OUTPUT_DIR / "overlap_analysis.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Rolling data for potential charting
    roll_export = pd.DataFrame({
        "date": roll_corr.index,
        "rolling_30d_corr": roll_corr.values,
        "rolling_30d_dd_overlap": roll_dd_overlap.reindex(roll_corr.index).values,
    })
    roll_export.to_csv(OUTPUT_DIR / "rolling_overlap.csv", index=False)

    print(f"\n  Saved to: {OUTPUT_DIR}")
    print(f"    overlap_analysis.json")
    print(f"    rolling_overlap.csv")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
