"""Phase 10 — 4-Strategy Portfolio Test.

Tests combined portfolio of:
1. PB-MGC-Short (existing core)
2. ORB-MGC-Long (existing core)
3. VWAP-Trend MNQ-Long (new Phase 10)
4. Donchian MNQ-Long GRINDING-only (new Phase 10)

Compares against 2-strategy baseline (PB + ORB).

Usage:
    python3 research/phase10_portfolio.py
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"
STARTING_CAPITAL = 50_000.0

STRATEGIES = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short",
     "label": "PB-MGC-Short", "grinding_filter": False},
    {"name": "orb_009", "asset": "MGC", "mode": "long",
     "label": "ORB-MGC-Long", "grinding_filter": False},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long",
     "label": "VWAP-MNQ-Long", "grinding_filter": False},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long",
     "label": "Donchian-MNQ-Long-GRINDING", "grinding_filter": True},
]


def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def run_strategy(strat: dict, engine: RegimeEngine) -> tuple:
    """Run a single strategy, return (daily_pnl, trades_df, metrics)."""
    asset = strat["asset"]
    config = ASSET_CONFIG[asset]

    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    mod = load_strategy(strat["name"])
    mod.TICK_SIZE = config["tick_size"]
    signals = mod.generate_signals(df)

    result = run_backtest(
        df, signals,
        mode=strat["mode"],
        point_value=config["point_value"],
        symbol=asset,
    )
    trades = result["trades_df"]

    if strat.get("grinding_filter") and not trades.empty:
        # Get regime data and filter to GRINDING days
        regime_daily = engine.get_daily_regimes(df)
        regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
        regime_daily["_date_date"] = regime_daily["_date"].dt.date

        trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
        trades = trades.merge(
            regime_daily[["_date_date", "trend_persistence"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )
        trades = trades[trades["trend_persistence"] == "GRINDING"]
        trades = trades.drop(columns=["entry_date", "_date_date", "trend_persistence"],
                             errors="ignore")

    daily = get_daily_pnl(trades)

    # Compute metrics
    eq = pd.Series(STARTING_CAPITAL + np.cumsum(
        np.concatenate([[0], trades["pnl"].values if not trades.empty else []])
    ))
    metrics = compute_extended_metrics(trades, eq, config["point_value"]) if not trades.empty else {}

    return daily, trades, metrics


def portfolio_metrics(port_daily: pd.Series, label: str, trade_count: int):
    """Compute and print portfolio metrics."""
    total_pnl = port_daily.sum()
    sharpe = (port_daily.mean() / port_daily.std() * np.sqrt(252)
              if port_daily.std() > 0 else 0)

    equity = STARTING_CAPITAL + port_daily.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    maxdd = dd.max()
    calmar = total_pnl / maxdd if maxdd > 0 else 0

    monthly = port_daily.resample("ME").sum()
    profitable_months = (monthly > 0).sum()
    total_months = len(monthly)
    monthly_pct = profitable_months / total_months * 100 if total_months > 0 else 0

    return {
        "label": label,
        "total_pnl": total_pnl,
        "sharpe": sharpe,
        "calmar": calmar,
        "maxdd": maxdd,
        "trades": trade_count,
        "profitable_months": f"{profitable_months}/{total_months} ({monthly_pct:.0f}%)",
        "trading_days": len(port_daily[port_daily != 0]),
    }


def main():
    engine = RegimeEngine()

    print("=" * 70)
    print("  PHASE 10 — 4-STRATEGY PORTFOLIO TEST")
    print("=" * 70)

    # Run all strategies
    daily_pnls = {}
    all_trades = {}
    strat_metrics = {}
    total_trades_map = {}

    for strat in STRATEGIES:
        label = strat["label"]
        print(f"\n  Running {label}...")
        daily, trades, metrics = run_strategy(strat, engine)
        daily_pnls[label] = daily
        all_trades[label] = trades
        strat_metrics[label] = metrics
        total_trades_map[label] = len(trades)
        tc = len(trades)
        pf = metrics.get("profit_factor", 0)
        pnl = metrics.get("total_pnl", 0)
        print(f"    {tc} trades, PF={pf}, PnL=${pnl:,.0f}")

    # ── Build portfolios ─────────────────────────────────────────────
    # 2-strategy baseline
    baseline_labels = ["PB-MGC-Short", "ORB-MGC-Long"]
    baseline_df = pd.DataFrame({l: daily_pnls[l] for l in baseline_labels}).fillna(0)
    baseline_daily = baseline_df.sum(axis=1).sort_index()
    baseline_trades = sum(total_trades_map[l] for l in baseline_labels)

    # 4-strategy portfolio
    all_labels = [s["label"] for s in STRATEGIES]
    full_df = pd.DataFrame({l: daily_pnls[l] for l in all_labels}).fillna(0)
    full_daily = full_df.sum(axis=1).sort_index()
    full_trades = sum(total_trades_map[l] for l in all_labels)

    # 3-strategy (no Donchian GRINDING — just PB + ORB + VWAP)
    three_labels = ["PB-MGC-Short", "ORB-MGC-Long", "VWAP-MNQ-Long"]
    three_df = pd.DataFrame({l: daily_pnls[l] for l in three_labels}).fillna(0)
    three_daily = three_df.sum(axis=1).sort_index()
    three_trades = sum(total_trades_map[l] for l in three_labels)

    # ── Compute metrics ──────────────────────────────────────────────
    base_m = portfolio_metrics(baseline_daily, "2-Strat Baseline", baseline_trades)
    three_m = portfolio_metrics(three_daily, "3-Strat (+VWAP)", three_trades)
    full_m = portfolio_metrics(full_daily, "4-Strat (+VWAP+Donchian)", full_trades)

    # ── Print comparison ─────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  PORTFOLIO COMPARISON")
    print(f"{'='*70}")

    headers = ["Metric", "2-Strat Baseline", "3-Strat (+VWAP)", "4-Strat (Full)"]
    print(f"\n  {headers[0]:<22} {headers[1]:>18} {headers[2]:>18} {headers[3]:>18}")
    print(f"  {'-'*22} {'-'*18} {'-'*18} {'-'*18}")

    for key, fmt in [
        ("total_pnl", "${:,.0f}"),
        ("sharpe", "{:.2f}"),
        ("calmar", "{:.2f}"),
        ("maxdd", "${:,.0f}"),
        ("trades", "{:,}"),
        ("profitable_months", "{}"),
        ("trading_days", "{:,}"),
    ]:
        label = key.replace("_", " ").title()
        v1 = fmt.format(base_m[key])
        v2 = fmt.format(three_m[key])
        v3 = fmt.format(full_m[key])
        print(f"  {label:<22} {v1:>18} {v2:>18} {v3:>18}")

    # ── Correlation matrix ───────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  DAILY PNL CORRELATION MATRIX")
    print(f"{'='*70}\n")

    corr = full_df.corr()
    short_labels = {
        "PB-MGC-Short": "PB",
        "ORB-MGC-Long": "ORB",
        "VWAP-MNQ-Long": "VWAP",
        "Donchian-MNQ-Long-GRINDING": "DONCH",
    }

    header = "  " + " " * 8
    for l in all_labels:
        header += f"{short_labels[l]:>8}"
    print(header)

    for l1 in all_labels:
        row = f"  {short_labels[l1]:<8}"
        for l2 in all_labels:
            val = corr.loc[l1, l2]
            row += f"{val:>8.3f}"
        print(row)

    # ── Monthly breakdown ────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  MONTHLY PNL BREAKDOWN (4-STRAT)")
    print(f"{'='*70}\n")

    monthly_full = full_daily.resample("ME").sum()
    monthly_base = baseline_daily.resample("ME").sum()

    print(f"  {'Month':<12} {'2-Strat':>10} {'4-Strat':>10} {'Delta':>10}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}")

    for dt in monthly_full.index:
        base_val = monthly_base.get(dt, 0)
        full_val = monthly_full[dt]
        delta = full_val - base_val
        month_str = dt.strftime("%Y-%m")
        print(f"  {month_str:<12} {'${:,.0f}'.format(base_val):>10} "
              f"{'${:,.0f}'.format(full_val):>10} "
              f"{'${:+,.0f}'.format(delta):>10}")

    # ── Per-strategy contribution ────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  PER-STRATEGY CONTRIBUTION")
    print(f"{'='*70}\n")

    for label in all_labels:
        daily = daily_pnls[label]
        pnl = daily.sum()
        trades_n = total_trades_map[label]
        pct = pnl / full_m["total_pnl"] * 100 if full_m["total_pnl"] != 0 else 0
        print(f"  {label:<35} ${pnl:>8,.0f} ({pct:>5.1f}%)  [{trades_n} trades]")

    print(f"\n  {'TOTAL':<35} ${full_m['total_pnl']:>8,.0f} (100.0%)")

    # ── Drawdown overlap analysis ────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  DRAWDOWN ANALYSIS")
    print(f"{'='*70}\n")

    for label, daily in [("2-Strat Baseline", baseline_daily),
                         ("4-Strat Full", full_daily)]:
        equity = STARTING_CAPITAL + daily.cumsum()
        peak = equity.cummax()
        dd = peak - equity
        maxdd = dd.max()
        maxdd_date = dd.idxmax() if len(dd) > 0 else "N/A"
        print(f"  {label}:")
        print(f"    MaxDD: ${maxdd:,.0f} on {maxdd_date}")
        # Time to recover
        if maxdd > 0:
            maxdd_idx = dd.idxmax()
            recovery = equity[maxdd_idx:][equity[maxdd_idx:] >= peak[maxdd_idx]]
            if len(recovery) > 0:
                recovery_date = recovery.index[0]
                recovery_days = (recovery_date - maxdd_idx).days
                print(f"    Recovery: {recovery_days} calendar days")
            else:
                print(f"    Recovery: not yet recovered")
        print()

    print("=" * 70)
    print("  DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()
