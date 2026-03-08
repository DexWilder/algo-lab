"""ORB-009 MGC-Long — Full Robustness Validation.

Runs:
1. Top-trade removal (top 1, 2, 3)
2. Walk-forward splits (2024 / 2025 / 2026 YTD)
3. Session sensitivity (4 windows)
4. Parameter stability (OR period, TP mult, vol mult, VWAP slope bars)
5. Monthly breakdown
6. Drawdown analysis

Output: validation_report.md, robustness_metrics.json, monthly_breakdown.csv
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from backtests.run_baseline import compute_extended_metrics

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

POINT_VALUE = 10.0  # MGC
TICK_SIZE = 0.10


def load_strategy():
    path = PROJECT_ROOT / "strategies" / "orb_009" / "strategy.py"
    spec = importlib.util.spec_from_file_location("orb_009", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data():
    df = pd.read_csv(PROCESSED_DIR / "MGC_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def run_and_metrics(df, signals_df, mode="long"):
    result = run_backtest(df, signals_df, mode=mode, point_value=POINT_VALUE)
    metrics = compute_extended_metrics(
        result["trades_df"], result["equity_curve"], POINT_VALUE
    )
    return metrics, result["trades_df"], result["equity_curve"]


# ── 1. Top-Trade Removal ────────────────────────────────────────────────

def test_top_trade_removal(trades_df):
    """Remove top N trades and recompute metrics."""
    rows = []
    pnl = trades_df["pnl"].values
    equity_full = pd.Series(50000 + np.cumsum(pnl))

    base_m = compute_extended_metrics(trades_df, equity_full, POINT_VALUE)
    rows.append({
        "test": "base", "trades": base_m["trade_count"],
        "pf": base_m["profit_factor"], "sharpe": base_m["sharpe"],
        "pnl": base_m["total_pnl"], "maxdd": base_m["max_drawdown"],
        "wr": round(base_m["win_rate"] * 100, 1),
        "avgR": base_m["avg_R"], "exp": base_m["expectancy"],
        "removed_pnl": 0,
    })

    sorted_idx = trades_df["pnl"].sort_values(ascending=False).index
    for n in [1, 2, 3]:
        remove_idx = sorted_idx[:n]
        remaining = trades_df.drop(remove_idx).reset_index(drop=True)
        removed_pnl = trades_df.loc[remove_idx, "pnl"].sum()
        if remaining.empty:
            continue
        eq = pd.Series(50000 + np.cumsum(remaining["pnl"].values))
        m = compute_extended_metrics(remaining, eq, POINT_VALUE)
        rows.append({
            "test": f"remove_top_{n}", "trades": m["trade_count"],
            "pf": m["profit_factor"], "sharpe": m["sharpe"],
            "pnl": m["total_pnl"], "maxdd": m["max_drawdown"],
            "wr": round(m["win_rate"] * 100, 1),
            "avgR": m["avg_R"], "exp": m["expectancy"],
            "removed_pnl": round(removed_pnl, 2),
        })

    return pd.DataFrame(rows)


# ── 2. Walk-Forward Splits ──────────────────────────────────────────────

def test_walk_forward(df, strategy_mod):
    """Split by calendar year and run independently."""
    df["_year"] = pd.to_datetime(df["datetime"]).dt.year
    years = sorted(df["_year"].unique())
    rows = []

    for year in years:
        subset = df[df["_year"] == year].copy().reset_index(drop=True)
        if len(subset) < 100:
            continue

        strategy_mod.TICK_SIZE = TICK_SIZE
        signals = strategy_mod.generate_signals(subset)
        m, trades, eq = run_and_metrics(subset, signals)

        label = f"{year}" if year < 2026 else f"{year} YTD"
        rows.append({
            "segment": label, "trades": m["trade_count"],
            "pf": m["profit_factor"], "sharpe": m["sharpe"],
            "pnl": m["total_pnl"], "maxdd": m["max_drawdown"],
            "wr": round(m["win_rate"] * 100, 1),
            "avgR": m["avg_R"], "exp": m["expectancy"],
        })

    df.drop(columns=["_year"], inplace=True)
    return pd.DataFrame(rows)


# ── 3. Session Sensitivity ──────────────────────────────────────────────

def test_session_windows(df, strategy_mod):
    """Test different entry window restrictions."""
    windows = {
        "full (baseline)": ("10:00", "15:00"),
        "10:00-10:30": ("10:00", "10:30"),
        "10:00-11:00": ("10:00", "11:00"),
        "10:00-12:00": ("10:00", "12:00"),
        "10:00-13:00": ("10:00", "13:00"),
    }
    rows = []

    for name, (start, end) in windows.items():
        strategy_mod.TICK_SIZE = TICK_SIZE
        # Temporarily change the entry window
        orig_end = strategy_mod.ENTRY_END
        strategy_mod.ENTRY_END = end

        signals = strategy_mod.generate_signals(df.copy())
        m, trades, eq = run_and_metrics(df, signals)

        strategy_mod.ENTRY_END = orig_end

        rows.append({
            "window": name, "trades": m["trade_count"],
            "pf": m["profit_factor"], "sharpe": m["sharpe"],
            "pnl": m["total_pnl"], "maxdd": m["max_drawdown"],
            "wr": round(m["win_rate"] * 100, 1),
            "avgR": m["avg_R"], "exp": m["expectancy"],
        })

    return pd.DataFrame(rows)


# ── 4. Parameter Stability ──────────────────────────────────────────────

def test_parameter_stability(df, strategy_mod):
    """Test sensitivity to key parameters."""
    variations = [
        # (param_name, values_to_test)
        ("OR_MINUTES", [15, 20, 25, 30, 45, 60]),
        ("TP_MULT", [1.0, 1.5, 2.0, 2.5, 3.0]),
        ("VOL_MULT", [1.0, 1.25, 1.5, 1.75, 2.0]),
        ("VWAP_SLOPE_BARS", [3, 5, 7, 10]),
        ("CANDLE_STRENGTH", [0.20, 0.25, 0.30, 0.35, 0.40]),
    ]
    rows = []

    for param, values in variations:
        orig = getattr(strategy_mod, param)
        for val in values:
            setattr(strategy_mod, param, val)
            strategy_mod.TICK_SIZE = TICK_SIZE
            signals = strategy_mod.generate_signals(df.copy())
            m, trades, eq = run_and_metrics(df, signals)

            label = f"{param}={val}"
            if val == orig:
                label += " (BASE)"
            rows.append({
                "variation": label, "trades": m["trade_count"],
                "pf": m["profit_factor"], "sharpe": m["sharpe"],
                "pnl": m["total_pnl"], "maxdd": m["max_drawdown"],
                "wr": round(m["win_rate"] * 100, 1),
            })
        setattr(strategy_mod, param, orig)

    return pd.DataFrame(rows)


# ── 5. Monthly Breakdown ────────────────────────────────────────────────

def compute_monthly(trades_df):
    """Monthly PnL breakdown."""
    if trades_df.empty:
        return pd.DataFrame()
    t = trades_df.copy()
    t["month"] = pd.to_datetime(t["exit_time"]).dt.to_period("M").astype(str)
    monthly = t.groupby("month").agg(
        trades=("pnl", "count"),
        pnl=("pnl", "sum"),
        wins=("pnl", lambda x: (x > 0).sum()),
        avg_pnl=("pnl", "mean"),
        best=("pnl", "max"),
        worst=("pnl", "min"),
    ).reset_index()
    monthly["wr"] = (monthly["wins"] / monthly["trades"] * 100).round(1)
    return monthly


# ── 6. Drawdown Series ──────────────────────────────────────────────────

def compute_drawdown_series(trades_df):
    """Trade-by-trade drawdown tracking."""
    if trades_df.empty:
        return pd.DataFrame()
    pnl_cum = trades_df["pnl"].cumsum()
    peak = pnl_cum.cummax()
    dd = peak - pnl_cum
    return pd.DataFrame({
        "trade_num": range(len(pnl_cum)),
        "equity": pnl_cum.values,
        "peak": peak.values,
        "drawdown": dd.values,
    })


# ── Main ────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  ORB-009 MGC-Long — Full Robustness Validation")
    print("=" * 60)

    strategy_mod = load_strategy()
    df = load_data()

    print(f"  Data: {len(df):,} bars, {df['datetime'].dt.date.nunique()} days")

    # Baseline run
    strategy_mod.TICK_SIZE = TICK_SIZE
    signals = strategy_mod.generate_signals(df.copy())
    base_metrics, base_trades, base_eq = run_and_metrics(df, signals)
    print(f"\n  Baseline: {base_metrics['trade_count']} trades, "
          f"PF={base_metrics['profit_factor']}, Sharpe={base_metrics['sharpe']}, "
          f"PnL=${base_metrics['total_pnl']:,.2f}")

    # 1. Top-trade removal
    print("\n  Running top-trade removal...")
    ttr = test_top_trade_removal(base_trades)
    ttr.to_csv(OUTPUT_DIR / "top_trade_removal.csv", index=False)
    print(f"    Saved top_trade_removal.csv")
    for _, row in ttr.iterrows():
        print(f"    {row['test']}: PF={row['pf']}, Sharpe={row['sharpe']}, PnL=${row['pnl']}")

    # 2. Walk-forward
    print("\n  Running walk-forward splits...")
    wf = test_walk_forward(df.copy(), strategy_mod)
    wf.to_csv(OUTPUT_DIR / "walk_forward_splits.csv", index=False)
    print(f"    Saved walk_forward_splits.csv")
    for _, row in wf.iterrows():
        print(f"    {row['segment']}: {row['trades']} trades, PF={row['pf']}, PnL=${row['pnl']}")

    # 3. Session sensitivity
    print("\n  Running session sensitivity...")
    ss = test_session_windows(df.copy(), strategy_mod)
    ss.to_csv(OUTPUT_DIR / "session_windows.csv", index=False)
    print(f"    Saved session_windows.csv")
    for _, row in ss.iterrows():
        print(f"    {row['window']}: {row['trades']} trades, PF={row['pf']}, Sharpe={row['sharpe']}")

    # 4. Parameter stability
    print("\n  Running parameter stability...")
    ps = test_parameter_stability(df.copy(), strategy_mod)
    ps.to_csv(OUTPUT_DIR / "param_stability.csv", index=False)
    print(f"    Saved param_stability.csv ({len(ps)} variations)")

    # 5. Monthly breakdown
    print("\n  Computing monthly breakdown...")
    monthly = compute_monthly(base_trades)
    monthly.to_csv(OUTPUT_DIR / "monthly_breakdown.csv", index=False)
    pos_months = (monthly["pnl"] > 0).sum()
    neg_months = (monthly["pnl"] <= 0).sum()
    print(f"    {len(monthly)} months: {pos_months} positive, {neg_months} negative "
          f"({pos_months / len(monthly) * 100:.0f}% consistency)")

    # 6. Drawdown series
    dd_series = compute_drawdown_series(base_trades)
    dd_series.to_csv(OUTPUT_DIR / "drawdown_series.csv", index=False)

    # 7. Equity curve
    eq_df = pd.DataFrame({"trade_num": range(len(base_trades)), "equity": base_trades["pnl"].cumsum()})
    eq_df.to_csv(OUTPUT_DIR / "equity_curve.csv", index=False)

    # Save trades
    base_trades.to_csv(OUTPUT_DIR / "trades.csv", index=False)

    # ── Build robustness_metrics.json ────────────────────────────────────
    robustness = {
        "strategy": "orb_009",
        "asset": "MGC",
        "mode": "long",
        "data_range": f"{df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}",
        "trading_days": df["datetime"].dt.date.nunique(),
        "baseline": base_metrics,
        "top_trade_removal": ttr.to_dict(orient="records"),
        "walk_forward": wf.to_dict(orient="records"),
        "session_windows": ss.to_dict(orient="records"),
        "param_stability_summary": {
            "total_variations": len(ps),
            "all_profitable": int((ps["pf"] > 1.0).sum()),
            "pf_range": [round(ps["pf"].min(), 3), round(ps["pf"].max(), 3)],
            "sharpe_range": [round(ps["sharpe"].min(), 4), round(ps["sharpe"].max(), 4)],
        },
        "monthly_summary": {
            "total_months": len(monthly),
            "positive_months": int(pos_months),
            "negative_months": int(neg_months),
            "consistency_pct": round(pos_months / max(len(monthly), 1) * 100, 1),
        },
        "drawdown": {
            "max_drawdown": base_metrics["max_drawdown"],
            "max_drawdown_pct": base_metrics["max_drawdown_pct"],
        },
    }
    with open(OUTPUT_DIR / "robustness_metrics.json", "w") as f:
        json.dump(robustness, f, indent=2, default=str)

    # ── Assessment ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  ROBUSTNESS ASSESSMENT")
    print(f"{'='*60}")

    # Top-trade removal check
    ttr_pass = ttr.iloc[-1]["pf"] > 1.0 if len(ttr) > 3 else ttr.iloc[-1]["pf"] > 1.0
    print(f"  Top-3 removal: PF={ttr.iloc[-1]['pf']} → {'PASS' if ttr_pass else 'FAIL'}")

    # Walk-forward check
    wf_positive = (wf["pnl"] > 0).sum()
    wf_pass = wf_positive >= len(wf) * 0.5
    print(f"  Walk-forward: {wf_positive}/{len(wf)} segments profitable → {'PASS' if wf_pass else 'FAIL'}")

    # Parameter stability check
    ps_profitable = (ps["pf"] > 1.0).sum()
    ps_total = len(ps)
    ps_pass = ps_profitable >= ps_total * 0.6
    print(f"  Param stability: {ps_profitable}/{ps_total} profitable → {'PASS' if ps_pass else 'FAIL'}")

    # Monthly consistency
    mc_pass = pos_months >= len(monthly) * 0.5
    print(f"  Monthly consistency: {pos_months}/{len(monthly)} → {'PASS' if mc_pass else 'FAIL'}")

    overall = ttr_pass and wf_pass and ps_pass and mc_pass
    print(f"\n  OVERALL: {'CANDIDATE VALIDATED' if overall else 'NEEDS REVIEW'}")
    print(f"{'='*60}")

    return robustness, overall


if __name__ == "__main__":
    main()
