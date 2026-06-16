"""Cycle 2026-06-16d — Seasonal mining batch 2 (NON-EQUITY, distribution-aware).

Lane B / REPORT-ONLY. Operator mandate: non-equity only (ZN/ZF/ZB/MGC/MCL; MES/MNQ
controls). Mechanisms: TOM re-eval (distribution-appropriate), day-of-week,
pre/post-holiday (holidays detected deterministically from data gaps), FOMC-week
(official FOMC calendar). Distribution metrics added: expectancy, skew, payoff ratio,
left-tail (worst trade), worst-3-cluster, max-adverse-window. New verdict framing:
WATCH-LOW/STRUCTURE_FOUND for real positive-skew edges where the median gate alone
shouldn't KILL. Deployability bar NOT lowered. No promotion/wiring/mutation.
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402

NONEQ = ["ZN", "ZF", "ZB", "MGC", "MCL"]
CTRL = ["MES", "MNQ"]


def _pf(p):
    p = np.array(p); g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def daily(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df = df.assign(date=dt.dt.date)
    g = df.groupby("date").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).reset_index()
    g["dow"] = pd.to_datetime(g["date"]).dt.dayofweek
    return g


def evaluate(trs):
    if len(trs) < 12:
        return {"n": len(trs), "note": "low_n"}
    p = np.array([t["pnl"] for t in trs]); yrs = np.array([t["year"] for t in trs])
    wins = p[p > 0]; losses = p[p < 0]
    yn = {int(y): float(p[yrs == y].sum()) for y in sorted(set(yrs))}
    pos_yr = sum(1 for v in yn.values() if v > 0)
    posshare = sum(v for v in yn.values() if v > 0)
    maxyr = round(100 * max(yn.values()) / posshare, 1) if posshare > 0 else 0.0
    loo = {int(y): round(_pf(p[yrs != y]), 3) for y in sorted(set(yrs))}
    half = len(p) // 2
    # worst-3 consecutive cluster
    w3 = min((p[i:i+3].sum() for i in range(len(p)-2)), default=p.sum())
    mtm = [t.get("mtm_worst_usd") for t in trs if t.get("mtm_worst_usd") is not None]
    return {
        "n": len(p), "pf": round(_pf(p), 3), "expectancy": round(float(p.mean()), 2),
        "median": round(float(np.median(p)), 2), "skew": round(float(pd.Series(p).skew()), 2),
        "payoff_ratio": round(float(wins.mean() / -losses.mean()), 2) if len(losses) and len(wins) else None,
        "win_rate_pct": round(100 * float((p > 0).mean()), 1),
        "left_tail_worst_trade": round(float(p.min()), 2),
        "worst_3_cluster": round(float(w3), 2),
        "max_adverse_window_usd": round(float(min(mtm)), 2) if mtm else None,
        "max_year_share_pct": maxyr, "pos_years": f"{pos_yr}/{len(yn)}",
        "loo_min_pf": round(min(loo.values()), 3), "h1_pf": round(_pf(p[:half]), 3), "h2_pf": round(_pf(p[half:]), 3),
        "net": round(float(p.sum()), 0),
    }


def beta_ctrl(g, pv, rt, hold):
    c = g["c"].values
    gp = np.array([(c[i+hold]-c[i])*pv - rt for i in range(len(c)-hold)])
    return round(_pf(gp), 3)


def _trade(g, pv, rt, ei, xi):
    c = g["c"].values; lo = g["l"].values
    return {"pnl": (c[xi]-c[ei])*pv - rt, "mtm_worst_usd": (lo[ei:xi+1].min()-c[ei])*pv,
            "year": pd.Timestamp(g["date"].iloc[ei]).year, "hold": xi-ei}


def tom(g, pv, rt):
    months = pd.to_datetime(g["date"]).dt.to_period("M"); bym = {}
    for i, m in enumerate(months):
        bym.setdefault(m, []).append(i)
    ms = sorted(bym); out = []
    for k in range(len(ms)-1):
        cur, nxt = bym[ms[k]], bym[ms[k+1]]
        if len(cur) < 2 or len(nxt) < 3: continue
        out.append(_trade(g, pv, rt, cur[-2], nxt[2]))
    return out


def dow(g, pv, rt, wd):
    out = []; c = g["c"].values
    for i in range(1, len(g)):
        if g["dow"].iloc[i] == wd:
            out.append(_trade(g, pv, rt, i-1, i))
    return out


def holidays(g):
    d = pd.to_datetime(g["date"]); gaps = []
    for i in range(1, len(d)):
        bdays = np.busday_count(d.iloc[i-1].date(), d.iloc[i].date())
        if bdays > 1:  # a weekday with no trading between = holiday
            gaps.append(i)  # i = first td AFTER holiday; i-1 = last td BEFORE
    return gaps


def preholiday(g, pv, rt):
    return [_trade(g, pv, rt, i-2, i-1) for i in holidays(g) if i-2 >= 0]  # long the day before holiday


def fomc_week(g, pv, rt):
    cal = [pd.Timestamp(c["actual_date"]) for c in build_official_fomc_calendar()]
    dates = pd.to_datetime(g["date"]); out = []
    for ev in cal:
        after = np.where(dates >= ev)[0]
        if not len(after): continue
        i = after[0]
        ei, xi = i-2, min(i+2, len(g)-1)  # 2 td before -> 2 td after FOMC
        if ei >= 0 and xi > ei:
            out.append(_trade(g, pv, rt, ei, xi))
    return out


def verdict(m, gen_pf):
    if not m or m.get("n", 0) < 12 or m.get("pf") is None:
        return "DEFER/low_n"
    pf, exp, ltail, mtm = m["pf"], m["expectancy"], m["left_tail_worst_trade"], m.get("max_adverse_window_usd")
    beta_ok = gen_pf is None or pf >= 1.4 * gen_pf
    robust = m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and m["loo_min_pf"] > 1.0 and m["max_year_share_pct"] <= 50
    prop_ok = (mtm is None or abs(mtm) <= 2000) and abs(ltail) <= 2000
    if pf < 1.15 and not beta_ok:
        return "KILL"
    deployable = pf >= 1.3 and exp > 0 and robust and prop_ok and beta_ok
    if deployable and m["median"] > 0:
        return "PASS (deployable+prop-safe)"
    if deployable and m["median"] <= 0:
        return "WATCH-LOW/STRUCTURE_FOUND (positive-skew tail edge; expectancy+left-tail OK, median<0)"
    if pf >= 1.3 and exp > 0 and beta_ok:
        blocker = ("concentration" if m["max_year_share_pct"] > 50 else
                   "prop-DD" if not prop_ok else "era/LOO" if not robust else "?")
        return f"WATCH (1 blocker: {blocker})"
    return "KILL"


def run():
    print("Cycle 2026-06-16d — seasonal batch 2 (non-equity, distribution-aware) REPORT-ONLY\n", flush=True)
    report = {"cycle": "2026-06-16d_seasonal_batch2", "mode": "Lane B report-only", "results": {}}
    mechs = {"TOM": tom, "preholiday": preholiday, "FOMC_week": fomc_week,
             "DOW_Mon": lambda g, pv, rt: dow(g, pv, rt, 0), "DOW_Tue": lambda g, pv, rt: dow(g, pv, rt, 1),
             "DOW_Wed": lambda g, pv, rt: dow(g, pv, rt, 2), "DOW_Thu": lambda g, pv, rt: dow(g, pv, rt, 3),
             "DOW_Fri": lambda g, pv, rt: dow(g, pv, rt, 4)}
    for a in NONEQ + CTRL:
        g = daily(a); pv = ASSETS[a]["point_value"]; cp = get_cost_params(a)
        rt = 2*(cp["commission_per_side"]+cp["slippage_ticks"]*cp["tick_size"]*pv)
        tag = "NONEQ" if a in NONEQ else "CTRL"
        print(f"\n===== {a} ({tag}) =====", flush=True)
        report["results"][a] = {"tag": tag, "mechanisms": {}}
        for mn, fn in mechs.items():
            trs = fn(g, pv, rt); m = evaluate(trs)
            if m.get("n", 0) < 12:
                continue
            hold = int(np.median([t["hold"] for t in trs])) or 1
            gpf = beta_ctrl(g, pv, rt, hold)
            v = verdict(m, gpf) if tag == "NONEQ" else f"(control) PF={m['pf']} gen={gpf}"
            report["results"][a]["mechanisms"][mn] = {**m, "generic_pf": gpf, "verdict": v}
            if tag == "NONEQ" and ("PASS" in v or "WATCH" in v or "STRUCTURE" in v):
                print(f"  {mn:11s} PF={m['pf']} (gen {gpf}) exp=${m['expectancy']} med=${m['median']} "
                      f"skew={m['skew']} payoff={m['payoff_ratio']} WR={m['win_rate_pct']}% maxyr={m['max_year_share_pct']}% "
                      f"LTail=${m['left_tail_worst_trade']} w3=${m['worst_3_cluster']} MAW=${m['max_adverse_window_usd']} -> {v}", flush=True)
            elif tag == "NONEQ":
                print(f"  {mn:11s} PF={m['pf']} (gen {gpf}) exp=${m['expectancy']} -> {v}", flush=True)
            else:
                print(f"  {mn:11s} {v}", flush=True)
    # collect non-KILL non-equity
    keep = []
    for a in NONEQ:
        for mn, mm in report["results"][a]["mechanisms"].items():
            if "PASS" in mm["verdict"] or "WATCH" in mm["verdict"] or "STRUCTURE" in mm["verdict"]:
                keep.append(f"{a}/{mn}: {mm['verdict']}")
    print("\n=== NON-EQUITY STRUCTURE/WATCH/PASS ===", flush=True)
    for k in keep: print("  "+k, flush=True)
    if not keep: print("  (none)", flush=True)
    report["nonequity_keep"] = keep
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16d_seasonal_batch2.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
