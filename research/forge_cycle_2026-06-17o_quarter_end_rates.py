"""Cycle 2026-06-17o — Lane 1: quarter-end rates settlement-flow (report-only).

Reachable FORCED-FLOW structural test (NOT generic OHLCV): pension/insurer/index duration
rebalancing concentrates demand into quarter-end -> a predictable bid in bonds (ZN/ZF) over the
last few trading days of Mar/Jun/Sep/Dec. Non-gold, non-MNQ, structural. Sparse (~4/yr) -> a
TAIL/event candidate if it survives, not a daily WH2 (flagged). Minimal predeclared variants
(K=3,5 day windows), no sweep, OOS half-split, no mutation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last()
    s.index = pd.to_datetime(s.index); return s


def quarter_end_trades(asset, K):
    s = daily_close(asset); s = s[s.index.year >= 2019]
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    days = list(s.index)
    # quarter-end month last-trading-day
    dfd = pd.DataFrame({"date": days}); dfd["q"] = dfd["date"].dt.quarter; dfd["y"] = dfd["date"].dt.year
    dfd["ym"] = dfd["date"].dt.to_period("M"); dfd["month"] = dfd["date"].dt.month
    qe_months = dfd[dfd["month"].isin([3, 6, 9, 12])]
    rows = []
    for (y, m), g in qe_months.groupby([dfd["y"], dfd["month"]]):
        gd = list(g["date"]);
        if len(gd) < K + 1:
            continue
        qe = gd[-1]                       # last trading day of quarter-end month
        entry_day = gd[-1 - K]            # K trading days before
        try:
            entry = s.loc[entry_day]; exit_px = s.loc[qe]
        except KeyError:
            continue
        pnl = (exit_px - entry) * pv - rt   # long bonds into quarter-end
        rows.append({"date": qe, "pnl": float(pnl), "year": y})
    return pd.DataFrame(rows)


def board(tr, label):
    if tr is None or len(tr) < 12:
        return {"label": label, "n": len(tr) if tr is not None else 0, "verdict": "KILL_low_n"}
    p = tr["pnl"].to_numpy(); n = len(p); h = n // 2
    pos_frac = float((p > 0).mean())
    g = tr[tr["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    top3 = round(float(g.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    pf = _pf(p)
    # tail/event gates: PF>=1.3, pos-fraction>=0.6, both halves positive net, top3<60%
    quality = pf >= 1.3 and pos_frac >= 0.6 and p[:h].sum() > 0 and p[h:].sum() > 0 and (top3 or 99) < 60
    verdict = ("STRUCTURE_FOUND_tail" if quality else ("WATCH_tail" if (pf >= 1.2 and pos_frac >= 0.55) else "KILL"))
    return {"label": label, "n": n, "pf": round(pf, 3), "net": round(float(p.sum()), 0), "median": round(float(np.median(p)), 2),
            "pos_frac": round(pos_frac, 2), "h1_net": round(float(p[:h].sum()), 0), "h2_net": round(float(p[h:].sum()), 0),
            "top3_pct": top3, "verdict": verdict}


def run():
    print("Cycle 2026-06-17o — Lane 1: quarter-end rates settlement-flow (REPORT-ONLY)\n", flush=True)
    print("Structural: pension/index duration rebalancing -> bid into quarter-end. ZN/ZF, sparse ~4/yr (tail).\n", flush=True)
    results = {}
    for asset in ("ZN", "ZF"):
        for K in (3, 5):
            tr = quarter_end_trades(asset, K)
            b = board(tr, f"{asset}-QE-long-K{K}"); results[f"{asset}_K{K}"] = b
            print(f"  {asset} K={K}: " + (f"{b['verdict']} (n={b['n']})" if b['verdict'].startswith('KILL') and b.get('pf') is None
                  else f"{b['verdict']:<20} n={b['n']} PF={b['pf']} net=${b['net']} med=${b['median']} pos={b['pos_frac']} "
                       f"H1/H2net=${b['h1_net']}/${b['h2_net']} top3={b['top3_pct']}%"), flush=True)

    surv = [k for k, v in results.items() if v["verdict"].startswith(("STRUCTURE", "WATCH"))]
    print(f"\n  survivors: {surv or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17o_quarter_end_rates.json"
    out.write_text(json.dumps({"cycle": "2026-06-17o_quarter_end_rates", "mode": "Lane 1 report-only; reachable forced-flow; NON-WIRED",
        "results": results, "note": "sparse ~4/yr tail/event, NOT daily WH2; structural forced-flow probe",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; forced-flow probe; no mutation)", flush=True)


if __name__ == "__main__":
    run()
