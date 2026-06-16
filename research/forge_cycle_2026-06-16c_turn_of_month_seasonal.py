"""Cycle 2026-06-16c — Turn-of-Month seasonal on NON-EQUITY (constrained mandate).

Lane B / REPORT-ONLY. Pivot into the validated seasonal/calendar vein (OPEX proved
the family). Targets BOTH goals: seasonal family + non-equity diversifier. Constrained
gates per operator: per-instrument, prop-DD < $2K @ 1 micro, no single-bear-year
failure, lower beta than pre-OPEX (non-equity by construction), beta-control, both
halves. NON-equity primary (MGC/MCL/ZN/ZF/ZB); MES/MNQ as equity reference only.

TOM window: long from close of penultimate trading day of month M through close of
the 3rd trading day of month M+1 (classic turn-of-month). Daily bars.
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

NONEQUITY = ["MGC", "MCL", "ZN", "ZF", "ZB"]
EQUITY_REF = ["MES", "MNQ"]
ENTER_BEFORE_LAST = 1   # entry = penultimate td of month (last - 1)
EXIT_TD_NEXT = 3        # exit = 3rd td of next month


def _pf(p):
    p = np.array(p); g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def daily_ohlc(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df = df.assign(date=dt.dt.date)
    g = df.groupby("date").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
    g = g.reset_index()
    g["ym"] = pd.to_datetime(g["date"]).dt.to_period("M")
    return g


def tom_windows(g, pv, rt):
    dates = list(g["date"]); c = g["c"].values; lo = g["l"].values
    months = list(g["ym"]); n = len(dates)
    # index of trading days per month
    by_month = {}
    for i, m in enumerate(months):
        by_month.setdefault(m, []).append(i)
    ms = sorted(by_month)
    trs = []
    for k in range(len(ms) - 1):
        cur, nxt = by_month[ms[k]], by_month[ms[k + 1]]
        if len(cur) < ENTER_BEFORE_LAST + 1 or len(nxt) < EXIT_TD_NEXT:
            continue
        ei = cur[-1 - ENTER_BEFORE_LAST]   # penultimate td of month
        xi = nxt[EXIT_TD_NEXT - 1]         # 3rd td of next month
        if xi <= ei:
            continue
        entry, exit_ = c[ei], c[xi]
        mtm_worst = lo[ei:xi + 1].min() - entry
        pnl = (exit_ - entry) * pv - rt
        trs.append({"year": pd.Timestamp(dates[ei]).year, "pnl": pnl,
                    "mtm_worst_usd": mtm_worst * pv, "hold": xi - ei})
    return trs


def metrics(trs):
    if not trs:
        return {"n": 0}
    p = np.array([t["pnl"] for t in trs]); yrs = np.array([t["year"] for t in trs])
    yn = {int(y): float(p[yrs == y].sum()) for y in sorted(set(yrs))}
    pos = sum(v for v in yn.values() if v > 0)
    maxyr = round(100 * max(yn.values()) / pos, 1) if pos > 0 else 0.0
    loo = {int(y): round(_pf(p[yrs != y]), 3) for y in sorted(set(yrs))}
    half = len(p) // 2
    return {"n": len(p), "pf": round(_pf(p), 3), "median": round(float(np.median(p)), 2),
            "net": round(float(p.sum()), 0), "win_rate_pct": round(100 * float((p > 0).mean()), 1),
            "max_year_share_pct": maxyr, "worst_year_net": round(min(yn.values()), 0),
            "loo_min_pf": round(min(loo.values()), 3), "h1_pf": round(_pf(p[:half]), 3), "h2_pf": round(_pf(p[half:]), 3),
            "largest_window_loss": round(float(p.min()), 2),
            "worst_mtm_dd_usd": round(float(min(t["mtm_worst_usd"] for t in trs)), 2),
            "by_year_net": yn}


def beta_control(g, pv, rt, hold):
    c = g["c"].values
    gp = np.array([(c[i + hold] - c[i]) * pv - rt for i in range(len(c) - hold)])
    return {"generic_pf": round(_pf(gp), 3), "generic_mean": round(float(gp.mean()), 2)}


def viable(m, bc):
    return (m.get("pf") and m["pf"] >= 1.3 and m.get("median", -1) > 0
            and m.get("h1_pf", 0) > 1.0 and m.get("h2_pf", 0) > 1.0 and m.get("loo_min_pf", 0) > 1.0
            and m.get("max_year_share_pct", 100) <= 50 and m.get("worst_year_net", -1) >= 0
            and abs(m.get("worst_mtm_dd_usd", 1e9)) <= 2000
            and bc.get("generic_pf") and m["pf"] >= 1.4 * bc["generic_pf"])


def run():
    print("Cycle 2026-06-16c — Turn-of-Month seasonal, non-equity focus (REPORT-ONLY)\n", flush=True)
    report = {"cycle": "2026-06-16c_turn_of_month_seasonal", "mode": "Lane B report-only (seasonal pivot)",
              "window": "penultimate td of M -> 3rd td of M+1, long", "results": {}}
    any_v = False
    for tag, assets in (("NON-EQUITY", NONEQUITY), ("EQUITY-REF", EQUITY_REF)):
        print(f"\n===== {tag} =====", flush=True)
        for a in assets:
            g = daily_ohlc(a); pv = ASSETS[a]["point_value"]; cp = get_cost_params(a)
            rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
            trs = tom_windows(g, pv, rt); m = metrics(trs)
            if not m.get("n"):
                print(f"  {a}: no windows"); continue
            hold = int(np.median([t["hold"] for t in trs]))
            bc = beta_control(g, pv, rt, hold)
            v = viable(m, bc) and tag == "NON-EQUITY"
            any_v = any_v or v
            report["results"][a] = {"tag": tag, **m, "beta_control": bc, "viable": v}
            print(f"  {a}: n={m['n']} PF={m['pf']} (gen {bc['generic_pf']}) med=${m['median']} WR={m['win_rate_pct']}% "
                  f"maxyr={m['max_year_share_pct']}% worstYr=${m['worst_year_net']} LOOmin={m['loo_min_pf']} "
                  f"H1/H2={m['h1_pf']}/{m['h2_pf']} MTMdd=${m['worst_mtm_dd_usd']} {'VIABLE' if v else ''}", flush=True)
    verdict = ("WATCH — >=1 non-equity TOM seasonal independently viable (real diversifier candidate)"
               if any_v else "KILL/NONE — no non-equity TOM seasonal clears the constrained gates")
    report["verdict"] = verdict
    print(f"\n  VERDICT: {verdict}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16c_turn_of_month_seasonal.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
