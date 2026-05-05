#!/usr/bin/env python3
"""Batch cheap-screen 3 hybrid candidates — Lane B Forge throughput run.

Per operator's 2026-05-05 push: candidate batch → cheap screens → kill fast → keep winners.

Candidates this batch:
  1. HYB-CashClose-Salvage-RatesWindow (ZN, 14:45-15:25 cash-close window)
  2. XB-VWAP-EMA-Ladder-MNQ (proven trio, VWAP entry instead of ORB)
  3. XB-Donchian-EMA-Ladder-MCL (proven trio, Donchian entry, energy breadth)

No registry mutation. No Lane A surfaces touched. Operator review for any append.
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
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    return df


def metrics(trades_df, label):
    if trades_df.empty:
        return {"label": label, "n": 0, "net": 0, "pf": float("nan"),
                "median": 0, "max_dd": 0, "max_single_pct": 0, "win_rate": 0,
                "sharpe": float("nan")}
    pnl = trades_df["pnl"].values
    n = len(pnl)
    net = pnl.sum()
    gp = pnl[pnl > 0].sum()
    gl = abs(pnl[pnl < 0].sum())
    pf = gp / gl if gl > 0 else float("inf")
    equity = np.cumsum(pnl)
    rmax = np.maximum.accumulate(equity)
    max_dd = float((equity - rmax).min())
    abs_total = abs(pnl).sum()
    max_single_pct = (abs(pnl).max() / abs_total * 100) if abs_total > 0 else 0
    std = float(np.std(pnl))
    sharpe = (pnl.mean() / std * np.sqrt(n / 6)) if std > 0 else float("nan")
    return {
        "label": label, "n": n, "net": float(net), "pf": pf,
        "median": float(np.median(pnl)),
        "max_dd": max_dd, "max_single_pct": max_single_pct,
        "win_rate": float((pnl > 0).mean()),
        "sharpe": sharpe,
    }


def candidate_xb_swap(asset, entry_name, label):
    """Run a proven-trio swap: <entry_name> + ema_slope + profit_ladder on <asset>."""
    df = load(asset)
    cfg = ASSETS[asset]
    params = {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5}
    sigs = generate_crossbred_signals(df, entry_name=entry_name,
                                       exit_name="profit_ladder",
                                       filter_name="ema_slope", params=params)
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    return metrics(res["trades_df"], label)


def candidate_cashclose():
    """HYB-CashClose: ZN cash-close window (14:45-15:25 ET) with impulse filter A/B.
    Mini-recreates ZN-Afternoon's mechanism at different time window (rather than
    requiring the deleted Treasury-Cash-Close strategy code).
    """
    df = load("ZN").copy()
    dt = pd.to_datetime(df["datetime"])
    df["date"] = dt.dt.date
    df["hhmm"] = dt.dt.hour * 100 + dt.dt.minute

    # Pre-cash-close impulse window: 14:30-14:45 ET
    # Entry decision at 14:45 ET; exit at 15:25 ET (time stop)
    pre_window = df[(df["hhmm"] >= 1430) & (df["hhmm"] < 1445)]
    pre_agg = pre_window.groupby("date").agg(
        pre_high=("high", "max"), pre_low=("low", "min"),
        pre_open=("open", "first"), pre_close=("close", "last"),
    )
    pre_agg["pre_range"] = pre_agg["pre_high"] - pre_agg["pre_low"]
    pre_agg["impulse"] = (pre_agg["pre_close"] - pre_agg["pre_open"]).abs()
    pre_agg["impulse_dir"] = np.sign(pre_agg["pre_close"] - pre_agg["pre_open"])
    pre_agg["pre_range_20d_median"] = pre_agg["pre_range"].rolling(20).median()
    pre_agg["impulse_pass"] = pre_agg["impulse"] >= 1.5 * pre_agg["pre_range_20d_median"]

    # For each date, get entry price at 14:45 (close of 14:40 5m bar) and exit at 15:25
    entry_bars = df[df["hhmm"] == 1445][["date", "close"]].rename(columns={"close": "entry_price"}).set_index("date")
    exit_bars = df[df["hhmm"] == 1525][["date", "close"]].rename(columns={"close": "exit_price"}).set_index("date")
    trades = pre_agg.join(entry_bars).join(exit_bars).dropna(subset=["entry_price", "exit_price"])

    # Strategy: FADE the impulse (mean-reversion). If impulse_dir > 0 (up impulse), short. Vice versa.
    # PnL for short: (entry - exit) * point_value; for long: (exit - entry) * point_value
    cfg = ASSETS["ZN"]
    pv = cfg["point_value"]
    trades["side"] = -trades["impulse_dir"]  # fade
    trades["pnl"] = (trades["exit_price"] - trades["entry_price"]) * trades["side"] * pv
    # Approximate cost (entry + exit fee + slippage)
    trades["pnl"] -= cfg.get("commission_per_side", 1.0) * 2 + cfg.get("slippage_ticks", 1) * cfg["tick_size"] * pv * 2

    # Run A: all impulse trades (no filter — every day has SOME impulse, even tiny)
    # Define A: only trades where pre_range_20d_median is computable (so first 20 days excluded)
    valid = trades.dropna(subset=["pre_range_20d_median"])
    a_trades = valid.copy()
    b_trades = valid[valid["impulse_pass"]]

    # Convert to trade_df format (just need pnl column for metrics)
    a_pseudo_df = pd.DataFrame({"pnl": a_trades["pnl"].values})
    b_pseudo_df = pd.DataFrame({"pnl": b_trades["pnl"].values})
    return metrics(a_pseudo_df, "HYB-CashClose-A no-filter"), metrics(b_pseudo_df, "HYB-CashClose-B impulse-filtered")


def main():
    print("=" * 78)
    print("BATCH CHEAP-SCREEN — 2026-05-05")
    print("=" * 78)
    results = []

    # Candidate 2: XB-VWAP-EMA-Ladder-MNQ
    print("\n[2] XB-VWAP-EMA-Ladder-MNQ — vwap_continuation entry + ema_slope filter + profit_ladder exit")
    try:
        m = candidate_xb_swap("MNQ", "vwap_continuation", "XB-VWAP-EMA-Ladder-MNQ")
        results.append(("XB-VWAP-EMA-Ladder-MNQ", "Workhorse diversity", m))
        print(f"  trades={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} netPnL=${m['net']:.0f} maxDD=${m['max_dd']:.0f} max_single={m['max_single_pct']:.1f}% sharpe={m['sharpe']:.3f}")
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("XB-VWAP-EMA-Ladder-MNQ", "Workhorse diversity", {"label": "ERROR", "n": 0, "net": 0, "pf": float('nan'), "median": 0, "max_dd": 0, "max_single_pct": 0, "win_rate": 0, "sharpe": float('nan')}))

    # Candidate 3: XB-Donchian-EMA-Ladder-MCL
    print("\n[3] XB-Donchian-EMA-Ladder-MCL — donchian_breakout entry + ema_slope + profit_ladder, MCL")
    try:
        m = candidate_xb_swap("MCL", "donchian_breakout", "XB-Donchian-EMA-Ladder-MCL")
        results.append(("XB-Donchian-EMA-Ladder-MCL", "Energy breadth", m))
        print(f"  trades={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} netPnL=${m['net']:.0f} maxDD=${m['max_dd']:.0f} max_single={m['max_single_pct']:.1f}% sharpe={m['sharpe']:.3f}")
    except Exception as e:
        print(f"  ERROR: {e}")
        results.append(("XB-Donchian-EMA-Ladder-MCL", "Energy breadth", {"label": "ERROR", "n": 0, "net": 0, "pf": float('nan'), "median": 0, "max_dd": 0, "max_single_pct": 0, "win_rate": 0, "sharpe": float('nan')}))

    # Candidate 4: HYB-CashClose
    print("\n[4] HYB-CashClose-Salvage-RatesWindow — ZN cash-close window 14:45-15:25 fade, impulse filter A/B")
    try:
        m_a, m_b = candidate_cashclose()
        results.append(("HYB-CashClose-A no-filter", "STRUCTURAL session-transition (rates)", m_a))
        results.append(("HYB-CashClose-B impulse-filtered", "STRUCTURAL session-transition (rates)", m_b))
        for m in (m_a, m_b):
            print(f"  {m['label']}: trades={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} netPnL=${m['net']:.0f} maxDD=${m['max_dd']:.0f} max_single={m['max_single_pct']:.1f}% sharpe={m['sharpe']:.3f}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()

    # Verdict synthesis
    print("\n" + "=" * 78)
    print("BATCH RESULT TABLE")
    print("=" * 78)
    print(f"{'Candidate':40s} | {'gap':30s} | {'n':>5s} | {'PF':>6s} | {'netPnL':>9s} | {'maxDD':>9s} | verdict")
    print("-" * 130)
    for name, gap, m in results:
        # Quick verdict: tail-engine bars (PF>=1.15, n>=30) for sparse strategies; workhorse bars (PF>=1.2, n>=500) for dense
        n, pf = m["n"], m["pf"]
        if n == 0:
            v = "ERROR"
        elif n >= 500:  # workhorse archetype
            if pf >= 1.2: v = "PASS"
            elif pf >= 1.05: v = "WATCH"
            else: v = "KILL"
        elif n >= 30:  # tail-engine archetype
            if pf >= 1.30: v = "PASS-STRONG"
            elif pf >= 1.15: v = "PASS"
            elif pf >= 1.0: v = "WATCH"
            else: v = "KILL"
        else:
            v = "RETEST" if pf > 1.0 else "KILL"
        print(f"{name:40s} | {gap:30s} | {n:>5d} | {pf:>6.3f} | {m['net']:>9.0f} | {m['max_dd']:>9.0f} | {v}")

    print("\n" + "=" * 78)


if __name__ == "__main__":
    main()
