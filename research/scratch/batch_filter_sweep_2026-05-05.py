#!/usr/bin/env python3
"""Filter substitution sweep — does ema_slope hold? — 2026-05-05.

Architecture question: is ema_slope load-bearing or substitutable in the proven
XB-ORB trio? Test 4 alternative filters (all already in crossbreeding engine)
against ema_slope baseline on MNQ.

Single asset, single entry (ORB), varying filter. One clean sweep. No optimization.
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

PARAMS = {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5}
ASSET = "MNQ"
ENTRY = "orb_breakout"

FILTERS = [
    ("ema_slope", "BASELINE — proven trio default"),
    ("vwap_slope", "alt: vwap-based slope"),
    ("bandwidth_squeeze", "alt: BB bandwidth gate"),
    ("session_morning", "alt: morning-session-only"),
    ("session_afternoon", "alt: afternoon-session-only"),
    ("none", "alt: no filter (control)"),
]


def metrics(td, label):
    if td.empty:
        return {"label": label, "n": 0, "net": 0.0, "pf": float("nan"),
                "median": 0, "max_dd": 0, "max_single_pct": 0, "win_rate": 0, "sharpe": float("nan")}
    pnl = td["pnl"].values
    n = len(pnl); net = float(pnl.sum())
    gp = pnl[pnl > 0].sum(); gl = abs(pnl[pnl < 0].sum())
    pf = float(gp/gl) if gl > 0 else float("inf")
    eq = np.cumsum(pnl)
    max_dd = float((eq - np.maximum.accumulate(eq)).min())
    abs_total = abs(pnl).sum()
    max_single = float(abs(pnl).max() / abs_total * 100) if abs_total > 0 else 0
    std = float(np.std(pnl))
    sharpe = float(pnl.mean() / std * np.sqrt(n / 6)) if std > 0 else float("nan")
    return {"label": label, "n": n, "net": net, "pf": pf,
            "median": float(np.median(pnl)), "max_dd": max_dd,
            "max_single_pct": max_single, "win_rate": float((pnl > 0).mean()),
            "sharpe": sharpe}


def verdict(m, n_threshold=500):
    n, pf = m["n"], m["pf"]
    if n == 0: return "RETEST"
    if n >= n_threshold:  # workhorse
        if pf >= 1.20: return "PASS"
        if pf >= 1.05: return "WATCH"
        return "KILL"
    else:  # tail-engine
        if n < 30: return "RETEST" if pf > 1.0 else "KILL"
        if pf >= 1.30: return "PASS"
        if pf >= 1.15: return "PASS"
        if pf >= 1.0: return "WATCH"
        return "KILL"


def main():
    df = pd.read_csv(ROOT / "data/processed" / f"{ASSET}_5m.csv")
    cfg = ASSETS[ASSET]
    print("=" * 80)
    print(f"FILTER SUBSTITUTION SWEEP — {ASSET}, entry={ENTRY}, exit=profit_ladder")
    print("=" * 80)

    rows = []
    for filt, note in FILTERS:
        sigs = generate_crossbred_signals(df, entry_name=ENTRY, exit_name="profit_ladder",
                                            filter_name=filt, params=PARAMS)
        res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=ASSET)
        m = metrics(res["trades_df"], filt)
        v = verdict(m)
        rows.append((filt, note, m, v))
        print(f"  {filt:25s} | n={m['n']:5d} PF={m['pf']:.3f} median=${m['median']:>6.2f} netPnL=${m['net']:>8.0f} maxDD=${m['max_dd']:>8.0f} → {v}")

    print("\n" + "=" * 80)
    print("RESULT TABLE")
    print("=" * 80)
    print(f"| {'Filter':22s} | {'n':>5s} | {'PF':>6s} | {'netPnL':>9s} | {'maxDD':>9s} | {'sharpe':>6s} | verdict |")
    print("|" + "-"*24 + "|" + "-"*7 + "|" + "-"*8 + "|" + "-"*11 + "|" + "-"*11 + "|" + "-"*8 + "|---------|")
    for filt, _note, m, v in rows:
        print(f"| {filt:22s} | {m['n']:>5d} | {m['pf']:>6.3f} | {m['net']:>9.0f} | {m['max_dd']:>9.0f} | {m['sharpe']:>6.3f} | {v} |")

    # Synthesis
    print("\nSYNTHESIS:")
    baseline_pf = next(m["pf"] for f, _, m, _ in rows if f == "ema_slope")
    no_filter_pf = next(m["pf"] for f, _, m, _ in rows if f == "none")
    alts = [(f, m, v) for f, _note, m, v in rows if f not in ("ema_slope", "none")]
    best_alt = max(alts, key=lambda x: x[1]["pf"] if not np.isnan(x[1]["pf"]) else -1)
    print(f"  Baseline ema_slope PF: {baseline_pf:.3f}")
    print(f"  No-filter (control) PF: {no_filter_pf:.3f}  (delta vs baseline: {no_filter_pf-baseline_pf:+.3f})")
    print(f"  Best alternative filter: {best_alt[0]} with PF {best_alt[1]['pf']:.3f}  ({best_alt[2]})")
    print(f"  Number of alternatives PASS: {sum(1 for _f, _m, v in alts if v == 'PASS')}/{len(alts)}")

    # Architecture call
    print("\nARCHITECTURE READ:")
    if baseline_pf - max(m["pf"] for _, _, m, _ in alts) > 0.10:
        print("  ema_slope is LOAD-BEARING — alternatives degrade meaningfully")
    elif sum(1 for _, _, _, v in alts if v == "PASS") >= 2:
        print("  ema_slope is SUBSTITUTABLE — multiple alternatives also PASS")
    else:
        print("  ema_slope is BEST-OF-CLASS — alternatives don't degrade dramatically but baseline still wins")


if __name__ == "__main__":
    main()
