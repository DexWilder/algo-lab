"""Phase 5.3 — Portfolio Sizing Research.

Compares sizing approaches for the 2-strategy portfolio:
1. Equal weight (1 contract each)
2. Equal risk contribution (size inversely proportional to per-trade volatility)
3. Volatility targeting (scale total portfolio to target vol)
4. Fractional Kelly (quarter-Kelly max)

All analysis uses net PnL (with transaction costs).

Usage:
    python3 research/portfolio/sizing_comparison.py
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

STARTING_CAPITAL = 50_000.0
TARGET_ANNUAL_VOL = 0.10  # 10% annual vol target


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


def compute_portfolio_metrics(daily_pnl, label=""):
    """Standard portfolio metrics from daily PnL series."""
    if daily_pnl.empty or daily_pnl.std() == 0:
        return {}

    total_pnl = daily_pnl.sum()
    sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)
    equity = STARTING_CAPITAL + daily_pnl.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    maxdd = dd.max()
    maxdd_pct = (maxdd / peak[dd.idxmax()]) * 100 if maxdd > 0 else 0
    recovery = total_pnl / maxdd if maxdd > 0 else float("inf")

    # Calmar ratio (annualized return / max drawdown)
    n_years = len(daily_pnl) / 252
    annual_return = total_pnl / n_years if n_years > 0 else 0
    calmar = annual_return / maxdd if maxdd > 0 else float("inf")

    # Sortino (downside deviation)
    neg_returns = daily_pnl[daily_pnl < 0]
    downside_std = neg_returns.std() if len(neg_returns) > 1 else daily_pnl.std()
    sortino = daily_pnl.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0

    # Monthly consistency
    monthly = daily_pnl.resample("ME").sum()
    profitable_months = (monthly > 0).sum()
    total_months = len(monthly)

    return {
        "label": label,
        "total_pnl": round(total_pnl, 2),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "maxdd": round(maxdd, 2),
        "maxdd_pct": round(maxdd_pct, 2),
        "recovery_factor": round(recovery, 2),
        "calmar": round(calmar, 2),
        "annual_return": round(annual_return, 2),
        "profitable_months": f"{profitable_months}/{total_months}",
        "daily_vol": round(daily_pnl.std(), 2),
        "annual_vol_pct": round(daily_pnl.std() * np.sqrt(252) / STARTING_CAPITAL * 100, 2),
    }


def main():
    print("=" * 70)
    print("  PHASE 5.3 — PORTFOLIO SIZING COMPARISON")
    print("  (PB-MGC-Short + ORB-009 MGC-Long)")
    print("=" * 70)

    # ── Run strategies ───────────────────────────────────────────────────────
    daily_pnls = {}
    trade_stats = {}

    for strat in STRATEGIES:
        label = strat["label"]
        result = run_strategy(strat)
        trades = result["trades_df"]

        if not trades.empty:
            trades["_date"] = pd.to_datetime(trades["exit_time"]).dt.date
            daily = trades.groupby("_date")["pnl"].sum()
            daily.index = pd.to_datetime(daily.index)
            daily_pnls[label] = daily

            # Per-trade statistics for sizing
            trade_stats[label] = {
                "mean_pnl": trades["pnl"].mean(),
                "std_pnl": trades["pnl"].std(),
                "n_trades": len(trades),
                "win_rate": (trades["pnl"] > 0).mean(),
                "avg_win": trades.loc[trades["pnl"] > 0, "pnl"].mean() if (trades["pnl"] > 0).any() else 0,
                "avg_loss": abs(trades.loc[trades["pnl"] < 0, "pnl"].mean()) if (trades["pnl"] < 0).any() else 0,
            }

    labels = list(daily_pnls.keys())
    l1, l2 = labels[0], labels[1]

    # Align to common date index
    combined = pd.DataFrame(daily_pnls).fillna(0)
    print(f"\n  Date range: {combined.index.min().date()} to {combined.index.max().date()}")
    print(f"  Trading days: {len(combined)}")

    # ── Per-strategy statistics ──────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  PER-STRATEGY TRADE STATISTICS")
    print(f"{'─' * 70}")
    for label in labels:
        ts = trade_stats[label]
        print(f"\n  {label}:")
        print(f"    Trades: {ts['n_trades']}")
        print(f"    Mean PnL: ${ts['mean_pnl']:.2f}")
        print(f"    Std PnL:  ${ts['std_pnl']:.2f}")
        print(f"    Win Rate: {ts['win_rate']*100:.1f}%")
        print(f"    Avg Win:  ${ts['avg_win']:.2f}")
        print(f"    Avg Loss: ${ts['avg_loss']:.2f}")

    # ── Method 1: Equal Weight ───────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  METHOD 1: EQUAL WEIGHT (1 contract each)")
    print(f"{'─' * 70}")

    eq_port = combined[l1] + combined[l2]
    m1 = compute_portfolio_metrics(eq_port, "Equal Weight")
    for k, v in m1.items():
        if k != "label":
            print(f"    {k}: {v}")

    # ── Method 2: Equal Risk Contribution ────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  METHOD 2: EQUAL RISK CONTRIBUTION")
    print(f"{'─' * 70}")

    # Scale each strategy's PnL by inverse of its daily vol
    vol_1 = combined[l1].std()
    vol_2 = combined[l2].std()

    if vol_1 > 0 and vol_2 > 0:
        # Weight inversely proportional to volatility
        w1_raw = 1 / vol_1
        w2_raw = 1 / vol_2
        w_sum = w1_raw + w2_raw
        w1 = w1_raw / w_sum
        w2 = w2_raw / w_sum

        print(f"  Daily vol: {l1}=${vol_1:.2f}, {l2}=${vol_2:.2f}")
        print(f"  Weights: {l1}={w1:.3f}, {l2}={w2:.3f}")
        print(f"  Effective contracts: {l1}={w1*2:.2f}, {l2}={w2*2:.2f}")

        erc_port = combined[l1] * w1 * 2 + combined[l2] * w2 * 2
        m2 = compute_portfolio_metrics(erc_port, "Equal Risk Contribution")
        for k, v in m2.items():
            if k != "label":
                print(f"    {k}: {v}")
    else:
        m2 = {}
        print("  Insufficient data for ERC calculation")

    # ── Method 3: Volatility Targeting ───────────────────────────────────────
    print(f"\n{'─' * 70}")
    print(f"  METHOD 3: VOLATILITY TARGETING ({TARGET_ANNUAL_VOL*100:.0f}% annual)")
    print(f"{'─' * 70}")

    # Target daily vol = annual_vol / sqrt(252)
    target_daily_vol = TARGET_ANNUAL_VOL * STARTING_CAPITAL / np.sqrt(252)
    current_daily_vol = eq_port.std()

    if current_daily_vol > 0:
        vol_scale = target_daily_vol / current_daily_vol
        print(f"  Current portfolio daily vol: ${current_daily_vol:.2f}")
        print(f"  Target daily vol: ${target_daily_vol:.2f}")
        print(f"  Scale factor: {vol_scale:.3f}")
        print(f"  Effective contracts: {vol_scale:.2f} each")

        vt_port = eq_port * vol_scale
        m3 = compute_portfolio_metrics(vt_port, f"Vol Target {TARGET_ANNUAL_VOL*100:.0f}%")
        for k, v in m3.items():
            if k != "label":
                print(f"    {k}: {v}")
    else:
        m3 = {}

    # ── Method 4: Fractional Kelly ───────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  METHOD 4: FRACTIONAL KELLY (quarter-Kelly)")
    print(f"{'─' * 70}")

    kelly_results = {}
    for label in labels:
        ts = trade_stats[label]
        if ts["avg_loss"] > 0:
            # Kelly: f* = (p * b - q) / b
            # where p = win_rate, q = 1-p, b = avg_win/avg_loss
            p = ts["win_rate"]
            q = 1 - p
            b = ts["avg_win"] / ts["avg_loss"]
            kelly_full = (p * b - q) / b if b > 0 else 0
            kelly_quarter = kelly_full * 0.25
            kelly_results[label] = {
                "full_kelly": round(kelly_full, 4),
                "quarter_kelly": round(kelly_quarter, 4),
                "b_ratio": round(b, 3),
            }
            print(f"\n  {label}:")
            print(f"    Win rate: {p*100:.1f}%")
            print(f"    Win/Loss ratio: {b:.3f}")
            print(f"    Full Kelly: {kelly_full:.4f} ({kelly_full*100:.1f}% of capital)")
            print(f"    Quarter Kelly: {kelly_quarter:.4f} ({kelly_quarter*100:.1f}% of capital)")
        else:
            kelly_results[label] = {"full_kelly": 0, "quarter_kelly": 0, "b_ratio": 0}

    # Apply quarter-Kelly as contract scaling
    # Kelly fraction × capital / avg_loss gives effective sizing
    kelly_scales = {}
    for label in labels:
        kr = kelly_results[label]
        ts = trade_stats[label]
        if kr["quarter_kelly"] > 0 and ts["avg_loss"] > 0:
            # How many contracts: kelly_fraction * capital / (avg_loss per contract)
            contracts = kr["quarter_kelly"] * STARTING_CAPITAL / ts["avg_loss"]
            kelly_scales[label] = contracts
        else:
            kelly_scales[label] = 1.0

    print(f"\n  Quarter-Kelly effective contracts:")
    for label in labels:
        print(f"    {label}: {kelly_scales[label]:.2f} contracts")

    k_port = combined[l1] * kelly_scales[l1] + combined[l2] * kelly_scales[l2]
    m4 = compute_portfolio_metrics(k_port, "Quarter Kelly")
    for k, v in m4.items():
        if k != "label":
            print(f"    {k}: {v}")

    # ── Comparison Table ─────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  SIZING COMPARISON SUMMARY")
    print(f"{'=' * 70}")

    methods = [m1, m2, m3, m4]
    headers = ["Metric", "Equal Wt", "ERC", f"Vol {TARGET_ANNUAL_VOL*100:.0f}%", "¼ Kelly"]
    metrics_to_show = ["total_pnl", "sharpe", "sortino", "maxdd", "recovery_factor", "calmar", "annual_vol_pct", "profitable_months"]

    print(f"  {headers[0]:<20} {headers[1]:>12} {headers[2]:>12} {headers[3]:>12} {headers[4]:>12}")
    print(f"  {'─' * 70}")

    for metric in metrics_to_show:
        vals = []
        for m in methods:
            v = m.get(metric, "—")
            if isinstance(v, float):
                if metric in ("total_pnl", "maxdd"):
                    vals.append(f"${v:,.0f}")
                else:
                    vals.append(f"{v:.2f}")
            else:
                vals.append(str(v))
        print(f"  {metric:<20} {vals[0]:>12} {vals[1]:>12} {vals[2]:>12} {vals[3]:>12}")

    # ── Recommendation ───────────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  RECOMMENDATION")
    print(f"{'─' * 70}")

    # Find best Sharpe
    best_sharpe_idx = max(range(len(methods)), key=lambda i: methods[i].get("sharpe", 0))
    best_calmar_idx = max(range(len(methods)), key=lambda i: methods[i].get("calmar", 0))

    method_names = ["Equal Weight", "Equal Risk Contribution", f"Volatility Targeting", "Quarter Kelly"]
    print(f"  Best Sharpe:  {method_names[best_sharpe_idx]} ({methods[best_sharpe_idx].get('sharpe', 0):.2f})")
    print(f"  Best Calmar:  {method_names[best_calmar_idx]} ({methods[best_calmar_idx].get('calmar', 0):.2f})")

    # ── Save ─────────────────────────────────────────────────────────────────
    report = {
        "strategies": labels,
        "starting_capital": STARTING_CAPITAL,
        "target_annual_vol": TARGET_ANNUAL_VOL,
        "trade_stats": {k: {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in trade_stats.items()},
        "kelly_results": kelly_results,
        "methods": {m.get("label", f"method_{i}"): m for i, m in enumerate(methods) if m},
        "erc_weights": {l1: round(w1, 4), l2: round(w2, 4)} if m2 else None,
        "vol_target_scale": round(vol_scale, 4) if m3 else None,
        "kelly_scales": {k: round(v, 4) for k, v in kelly_scales.items()},
    }

    with open(OUTPUT_DIR / "sizing_comparison.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n  Saved to: {OUTPUT_DIR / 'sizing_comparison.json'}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
