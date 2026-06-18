"""Cycle 2026-06-17r — Lane 1 calendar/mechanical: ALL month-end rates settlement flow (report-only).

Extends the quarter-end rates WATCH_tail (n=28) to ALL month-ends (n~84) to test whether the
month-end duration-rebalancing bid is MONTHLY (more sample -> resolves the n/concentration limiter)
or genuinely quarter-end-specific. Calendar/mechanical forced-flow (the productive sub-vein).
Long bonds (ZF primary, ZN confirm) last K=3 trading days into month-end. Audit metrics +
quarter-end vs non-quarter-end split. Mechanical dates, no-lookahead. Report-only; no mutation.
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
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def month_end_events(asset, K, months=None):
    s = daily_close(asset); s = s[s.index.year >= 2019]
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    days = list(s.index); dfd = pd.DataFrame({"date": days}); dfd["y"] = dfd["date"].dt.year; dfd["m"] = dfd["date"].dt.month
    rows = []
    for (y, m), g in dfd.groupby([dfd["y"], dfd["m"]]):
        if months and m not in months:
            continue
        gd = list(g["date"])
        if len(gd) < K + 1:
            continue
        me = gd[-1]; entry = gd[-1 - K]
        pnl = (s.loc[me] - s.loc[entry]) * pv - rt
        rows.append({"me": me, "pnl": float(pnl), "year": int(y), "month": int(m),
                     "is_qe": m in (3, 6, 9, 12)})
    return pd.DataFrame(rows)


def metrics(tr):
    if tr is None or len(tr) < 12:
        return {"n": len(tr) if tr is not None else 0, "pf": None}
    p = tr["pnl"].to_numpy(); net = float(p.sum()); pf = _pf(p); gross = float(p[p > 0].sum())
    g = np.sort(p[p > 0])[::-1]
    per_y = tr.groupby("year")["pnl"].sum(); h = len(p) // 2
    return {"n": len(p), "pf": round(pf, 3), "net": round(net, 0), "median": round(float(np.median(p)), 2),
            "pos_frac": round(float((p > 0).mean()), 2), "max_single_pct": round(float(g[0]) / gross * 100, 1) if gross > 0 else None,
            "top3_pct": round(float(g[:3].sum()) / gross * 100, 1) if gross > 0 else None,
            "max_year_pct": round(float(per_y.abs().max() / net * 100), 1) if net else None,
            "yrs_pos": f"{int((per_y>0).sum())}/{int(per_y.shape[0])}",
            "h1_net": round(float(p[:h].sum()), 0), "h2_net": round(float(p[h:].sum()), 0)}


def run():
    print("Cycle 2026-06-17r — ALL month-end rates settlement flow (REPORT-ONLY)\n", flush=True)
    print("Tests if quarter-end rates edge generalizes to ALL month-ends (n~84) -> resolves n=28 limiter, or is QE-specific.\n", flush=True)
    for asset in ("ZF", "ZN"):
        allm = month_end_events(asset, 3)
        qe = allm[allm["is_qe"]]; nonqe = allm[~allm["is_qe"]]
        ma, mq, mn = metrics(allm), metrics(qe), metrics(nonqe)
        print(f"  {asset} K=3:", flush=True)
        print(f"    ALL months  : n={ma['n']} PF={ma['pf']} net=${ma['net']} pos={ma['pos_frac']} max-single={ma['max_single_pct']}% "
              f"top3={ma['top3_pct']}% max-yr={ma['max_year_pct']}% yrs+={ma['yrs_pos']} H1/H2=${ma['h1_net']}/${ma['h2_net']}", flush=True)
        print(f"    quarter-end : n={mq['n']} PF={mq['pf']} net=${mq['net']} pos={mq['pos_frac']}", flush=True)
        print(f"    non-QE month: n={mn['n']} PF={mn['pf']} net=${mn['net']} pos={mn['pos_frac']}", flush=True)
        # interpretation
        if ma['pf'] and ma['pf'] >= 1.3 and (ma['max_year_pct'] or 99) < 50 and ma['pos_frac'] >= 0.58:
            verdict = "MONTH-END GENERALIZES (broader candidate, more sample, better concentration)"
        elif mq['pf'] and mn['pf'] and mq['pf'] > 1.4 and mn['pf'] < 1.15:
            verdict = "QUARTER-END-SPECIFIC (non-QE months weak -> edge is quarterly rebalancing, keep QE-only)"
        else:
            verdict = "MIXED / weak"
        print(f"    -> {verdict}", flush=True)
        if asset == "ZF":
            zf_all = ma; zf_verdict = verdict

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17r_month_end_rates.json"
    out.write_text(json.dumps({"cycle": "2026-06-17r_month_end_rates", "mode": "Lane 1 report-only; calendar/mechanical; NON-WIRED",
        "zf_all_month_K3": zf_all, "interpretation": zf_verdict,
        "note": "extends quarter-end rates WATCH_tail; tests monthly generalization vs QE-specificity",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; calendar/mechanical probe; no mutation)", flush=True)


if __name__ == "__main__":
    run()
