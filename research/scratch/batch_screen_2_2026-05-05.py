#!/usr/bin/env python3
"""Batch cheap-screen #2 — entry-substitution sweep + salvage attempt #3.

Candidates:
  1. XB-PB-EMA-Ladder-MNQ (pb_pullback entry in proven trio)
  2. XB-BB-EMA-Ladder-MNQ (bb_reversion entry in proven trio)
  3. HYB-LunchComp-RatesAfternoon (lunch-compression filter on ZN cash-close-style fade)

No registry mutation. Lane B / Forge only.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402


def load(asset):
    return pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")


def metrics(trades_df, label):
    if trades_df is None or trades_df.empty:
        return {"label": label, "n": 0, "net": 0, "pf": float("nan"), "median": 0,
                "max_dd": 0, "max_single_pct": 0, "win_rate": 0, "sharpe": float("nan")}
    pnl = trades_df["pnl"].values
    n = len(pnl)
    net = pnl.sum()
    gp = pnl[pnl > 0].sum(); gl = abs(pnl[pnl < 0].sum())
    pf = gp / gl if gl > 0 else float("inf")
    eq = np.cumsum(pnl)
    max_dd = float((eq - np.maximum.accumulate(eq)).min())
    abs_total = abs(pnl).sum()
    max_single_pct = (abs(pnl).max() / abs_total * 100) if abs_total > 0 else 0
    std = float(np.std(pnl))
    sharpe = (pnl.mean() / std * np.sqrt(n / 6)) if std > 0 else float("nan")
    return {"label": label, "n": n, "net": float(net), "pf": pf,
            "median": float(np.median(pnl)), "max_dd": max_dd,
            "max_single_pct": max_single_pct, "win_rate": float((pnl > 0).mean()),
            "sharpe": sharpe}


def candidate_xb_swap(asset, entry_name, label):
    df = load(asset)
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(df, entry_name=entry_name,
                                       exit_name="profit_ladder",
                                       filter_name="ema_slope",
                                       params={"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5})
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    return metrics(res["trades_df"], label)


def candidate_lunchcomp_zn():
    """HYB-LunchComp-RatesAfternoon: ZN-Afternoon-style fade gated by lunch-compression filter.

    A: baseline — all impulse-fade trades at 13:45-14:00 ET window
    B: filtered — same trades, only on days where lunch (11:30-13:30 ET) was compressed
    """
    df = load("ZN").copy()
    dt = pd.to_datetime(df["datetime"])
    df["date"] = dt.dt.date
    df["hhmm"] = dt.dt.hour * 100 + dt.dt.minute

    # Lunch window (11:30-13:30 ET) → range
    lunch = df[(df["hhmm"] >= 1130) & (df["hhmm"] < 1330)]
    lunch_agg = lunch.groupby("date").agg(lh=("high", "max"), ll=("low", "min"))
    lunch_agg["lunch_range"] = lunch_agg["lh"] - lunch_agg["ll"]
    lunch_agg["lunch_range_20d_median"] = lunch_agg["lunch_range"].rolling(20).median()
    lunch_agg["compressed"] = lunch_agg["lunch_range"] < (0.7 * lunch_agg["lunch_range_20d_median"])

    # Impulse window (13:30-13:45 ET) → impulse magnitude
    impulse_w = df[(df["hhmm"] >= 1330) & (df["hhmm"] < 1345)]
    imp_agg = impulse_w.groupby("date").agg(io=("open", "first"), ic=("close", "last"))
    imp_agg["impulse"] = (imp_agg["ic"] - imp_agg["io"]).abs()
    imp_agg["impulse_dir"] = np.sign(imp_agg["ic"] - imp_agg["io"])
    imp_agg["impulse_20d_median"] = imp_agg["impulse"].rolling(20).median()
    imp_agg["impulse_pass"] = imp_agg["impulse"] >= 1.5 * imp_agg["impulse_20d_median"]

    entry_bars = df[df["hhmm"] == 1345][["date", "close"]].rename(columns={"close": "entry_price"}).set_index("date")
    exit_bars = df[df["hhmm"] == 1425][["date", "close"]].rename(columns={"close": "exit_price"}).set_index("date")
    trades = imp_agg.join(entry_bars).join(exit_bars).join(lunch_agg[["compressed", "lunch_range_20d_median"]]).dropna(subset=["entry_price", "exit_price"])

    cfg = ASSETS["ZN"]; pv = cfg["point_value"]
    trades["side"] = -trades["impulse_dir"]  # fade
    trades["pnl"] = (trades["exit_price"] - trades["entry_price"]) * trades["side"] * pv
    trades["pnl"] -= cfg.get("commission_per_side", 1.0) * 2 + cfg.get("slippage_ticks", 1) * cfg["tick_size"] * pv * 2

    valid = trades.dropna(subset=["impulse_20d_median", "lunch_range_20d_median"])
    a = valid[valid["impulse_pass"]].copy()  # all impulse-fade
    b = valid[valid["impulse_pass"] & valid["compressed"]].copy()  # also lunch-compressed
    return (metrics(pd.DataFrame({"pnl": a["pnl"].values}), "HYB-LunchComp-A impulse-only"),
            metrics(pd.DataFrame({"pnl": b["pnl"].values}), "HYB-LunchComp-B impulse+lunch-comp"))


def main():
    print("=" * 78)
    print("BATCH CHEAP-SCREEN #2 — 2026-05-05")
    print("=" * 78)
    rows = []

    # 1
    print("\n[1] XB-PB-EMA-Ladder-MNQ")
    m = candidate_xb_swap("MNQ", "pb_pullback", "XB-PB-EMA-Ladder-MNQ")
    rows.append(("XB-PB-EMA-Ladder-MNQ", "MNQ", "Workhorse / entry-substitution", m, "XB-ORB-MNQ baseline PF 1.62 / n=1183"))
    print(f"  trades={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} netPnL=${m['net']:.0f} maxDD=${m['max_dd']:.0f} max_single={m['max_single_pct']:.1f}% sharpe={m['sharpe']:.3f}")

    # 2
    print("\n[2] XB-BB-EMA-Ladder-MNQ")
    m = candidate_xb_swap("MNQ", "bb_reversion", "XB-BB-EMA-Ladder-MNQ")
    rows.append(("XB-BB-EMA-Ladder-MNQ", "MNQ", "Workhorse / entry-substitution", m, "XB-ORB-MNQ baseline PF 1.62 / n=1183"))
    print(f"  trades={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} netPnL=${m['net']:.0f} maxDD=${m['max_dd']:.0f} max_single={m['max_single_pct']:.1f}% sharpe={m['sharpe']:.3f}")

    # 3
    print("\n[3] HYB-LunchComp-RatesAfternoon (A/B)")
    m_a, m_b = candidate_lunchcomp_zn()
    rows.append(("HYB-LunchComp-A impulse-only", "ZN", "STRUCTURAL session-transition (rates) — salvage attempt #3", m_a, "ZN-Afternoon baseline (analogous mechanism)"))
    rows.append(("HYB-LunchComp-B impulse+lunch-comp", "ZN", "Same; lunch-compressed days only", m_b, "A above"))
    for m in (m_a, m_b):
        print(f"  {m['label']}: trades={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} netPnL=${m['net']:.0f} maxDD=${m['max_dd']:.0f} max_single={m['max_single_pct']:.1f}% sharpe={m['sharpe']:.3f}")

    # Verdict synthesis
    print("\n" + "=" * 78)
    print("BATCH RESULT TABLE")
    print("=" * 78)
    print(f"{'Candidate':40s} | {'Asset':5s} | {'n':>5s} | {'PF':>6s} | {'netPnL':>9s} | {'maxDD':>9s} | verdict")
    print("-" * 130)
    for name, asset, gap, m, baseline in rows:
        n, pf = m["n"], m["pf"]
        if n == 0:
            v = "RETEST"
        elif n >= 500:
            if pf >= 1.2: v = "PASS"
            elif pf >= 1.05: v = "WATCH"
            else: v = "KILL"
        elif n >= 30:
            if pf >= 1.30: v = "PASS-STRONG"
            elif pf >= 1.15: v = "PASS"
            elif pf >= 1.0: v = "WATCH"
            else: v = "KILL"
        else:
            v = "RETEST" if pf > 1.0 else "KILL"
        print(f"{name:40s} | {asset:5s} | {n:>5d} | {pf:>6.3f} | {m['net']:>9.0f} | {m['max_dd']:>9.0f} | {v}")

    print("\n" + "=" * 78)


if __name__ == "__main__":
    main()
