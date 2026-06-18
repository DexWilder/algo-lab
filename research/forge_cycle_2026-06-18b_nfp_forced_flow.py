"""Cycle 2026-06-18b — Lane 1 exact-date forced-flow: NFP-day rates (report-only).

Sanctioned exact-date forced-flow probe (operator highest-EV reachable category). NFP = first
Friday of month, 08:30 ET. Forced-flow thesis: pre-NFP de-risking/positioning + post-release
rate repricing. CONTAMINATION LESSON APPLIED UP FRONT (no month-end-style over-claim): report
the CLEAN edge (non-roll-adjacent AND non-FOMC-overlap) directly, decompose by source.
ZN/ZF, daily. Event/tail (NOT daily WH2). No sweep, no mutation.
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
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402

ROLL_ADJ = {2, 5, 8, 11}


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def first_fridays(years):
    out = []
    for y in years:
        for m in range(1, 13):
            d = pd.Timestamp(y, m, 1)
            while d.weekday() != 4:  # Friday
                d += pd.Timedelta(days=1)
            out.append(d)
    return out


def nfp_events(asset, mode="prdrift", K=2):
    """prdrift = long bonds the K days BEFORE NFP (positioning); postday = NFP-day close move."""
    s = daily_close(asset); s = s[s.index.year >= 2019]
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    days = list(s.index); dset = set(days)
    fomc = set(pd.Timestamp(c["actual_date"]).normalize() for c in build_official_fomc_calendar())
    rows = []
    for nfp in first_fridays(range(2019, 2027)):
        # align NFP to a real trading day (the first trading day >= nfp)
        nd = nfp
        while nd not in dset and nd < days[-1]:
            nd += pd.Timedelta(days=1)
        if nd not in dset:
            continue
        i = days.index(nd)
        if mode == "prdrift":
            if i - K < 0:
                continue
            entry = days[i - K]; exit_d = nd
        else:  # postday: enter prior close, exit NFP-day close
            if i - 1 < 0:
                continue
            entry = days[i - 1]; exit_d = nd
        pnl = (s.loc[exit_d] - s.loc[entry]) * pv - rt
        fomc_ov = any(abs((nd - f).days) <= 3 for f in fomc)
        rows.append({"nfp": nd, "pnl": float(pnl), "year": nd.year, "month": nd.month,
                     "roll_adj": nd.month in ROLL_ADJ, "fomc": fomc_ov})
    return pd.DataFrame(rows)


def m(tr):
    if tr is None or len(tr) < 12:
        return {"n": len(tr) if tr is not None else 0, "pf": None}
    p = tr["pnl"].to_numpy(); net = float(p.sum()); gross = float(p[p > 0].sum()); g = np.sort(p[p > 0])[::-1]
    py = tr.groupby("year")["pnl"].sum()
    return {"n": len(p), "pf": round(_pf(p), 3), "net": round(net, 0), "median": round(float(np.median(p)), 2),
            "pos_frac": round(float((p > 0).mean()), 2), "max_single_pct": round(float(g[0]) / gross * 100, 1) if gross > 0 else None,
            "max_year_pct": round(float(py.abs().max() / net * 100), 1) if net else None, "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}"}


def run():
    print("Cycle 2026-06-18b — NFP-day rates exact-date forced-flow (REPORT-ONLY)\n", flush=True)
    print("Contamination lesson applied up front: report CLEAN (non-roll AND non-FOMC) edge directly.\n", flush=True)
    any_clean = False
    summary = {}
    for asset in ("ZN", "ZF"):
        for mode in ("prdrift", "postday"):
            tr = nfp_events(asset, mode)
            allm = m(tr); clean = m(tr[(~tr["roll_adj"]) & (~tr["fomc"])])
            tag = f"{asset}-{mode}"
            summary[tag] = {"all": allm, "clean": clean}
            print(f"  {tag:<14} ALL n={allm['n']} PF={allm['pf']} pos={allm.get('pos_frac')} | "
                  f"CLEAN(non-roll,non-FOMC) n={clean['n']} PF={clean['pf']} pos={clean.get('pos_frac')} "
                  f"max-yr={clean.get('max_year_pct')}% yrs+={clean.get('yrs_pos')}", flush=True)
            if clean.get("pf") and clean["pf"] >= 1.3 and clean.get("pos_frac", 0) >= 0.58 and (clean.get("max_year_pct") or 99) < 50:
                any_clean = True

    verdict = "STRUCTURE_FOUND_tail (a clean NFP variant cleared gates -> audit further)" if any_clean else \
              "KILL/NO-CLEAN-EDGE: NFP-day rates shows no clean (non-roll/non-FOMC) edge that clears gates"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print("  (event/tail NOT daily WH2; rates-event space already has FOMC sleeve — incremental value low unless clean+distinct)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-18b_nfp_forced_flow.json"
    out.write_text(json.dumps({"cycle": "2026-06-18b_nfp_forced_flow", "mode": "Lane 1 report-only; exact-date forced-flow; NON-WIRED",
        "summary": summary, "verdict": verdict, "boundaries": "clean-decomposed up front; no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
