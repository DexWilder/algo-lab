"""Cycle 2026-06-24g — VX term-structure carry / volatility risk premium (report-only).

DIFFERENT premium (volatility), genuinely distinct from ORB momentum & rates carry. Class-B reachable:
^VIX, ^VIX3M, SVXY (short-vol ETP). Mechanism (Sinclair/Ilmanen VRP): VIX curve usually in CONTANGO
(VIX3M>VIX) -> short-vol earns roll-down carry; BACKWARDATION (VIX>VIX3M) = stress -> exit to dodge the
crash. Predeclared, NO flip: contango -> long SVXY (short vol); backwardation -> FLAT. Signal known prior close.

KEY QUESTION: does term-structure TIMING avoid the short-vol crashes (Feb-2018, Mar-2020) while keeping carry,
i.e. beat UNCONDITIONAL always-short-vol on risk-adjusted terms? Strict: per-year incl crises, tail, cost,
DSR, ORB-correlation. CAVEAT: SVXY leverage changed -1x->-0.5x Feb-2018 (noted). Report-only; no mutation.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
from forge_deflated_sharpe import deflated_sharpe

REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"


def yahoo(sym):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10y&interval=1d"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read())
    res = r["chart"]["result"][0]; ts = res["timestamp"]; cl = res["indicators"]["quote"][0]["close"]
    s = pd.Series(cl, index=pd.to_datetime(ts, unit="s").normalize()).dropna()
    return s[~s.index.duplicated()]


def _pf(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]; l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def metrics(s):
    p = s.values; eq = np.cumsum(p); dd = eq - np.maximum.accumulate(eq); sd = p.std()
    yr = s.groupby(s.index.year).sum(); h = len(p) // 2
    return {"n": len(p), "ann_ret_pct": round(float(p.mean()) * 252 * 100, 1), "sharpe": round(float(p.mean()) / sd * np.sqrt(252), 2) if sd > 0 else None,
            "maxDD_pct": round(float(dd.min()) * 100, 1), "MAR": round(float(p.sum()) / abs(dd.min()), 2) if dd.min() < 0 else None,
            "worst_day_pct": round(float(s.min()) * 100, 1), "pf": round(_pf(p), 3),
            "h1_sharpe": round(float(p[:h].mean()) / p[:h].std() * np.sqrt(252), 2) if p[:h].std() > 0 else None,
            "h2_sharpe": round(float(p[h:].mean()) / p[h:].std() * np.sqrt(252), 2) if p[h:].std() > 0 else None,
            "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}", "per_year_pct": {int(y): round(float(v) * 100, 1) for y, v in yr.items()}}


def run():
    print("Cycle 2026-06-24g — VX term-structure carry / VRP (report-only)\n", flush=True)
    vix = yahoo("^VIX"); vix3m = yahoo("^VIX3M"); svxy = yahoo("SVXY")
    d = pd.DataFrame({"vix": vix, "vix3m": vix3m, "svxy": svxy}).dropna().sort_index()
    d["slope"] = d["vix3m"] / d["vix"] - 1                       # >0 contango (short-vol carry regime)
    d["svxy_ret"] = d["svxy"].pct_change()
    d["regime"] = np.where(d["slope"].shift(1) > 0, 1, 0)        # prior-close slope -> today (no lookahead); contango=1
    d = d.dropna(subset=["svxy_ret", "regime"])
    print(f"  data: {len(d)} days {d.index.min().date()}..{d.index.max().date()} | contango days {100*d['regime'].mean():.0f}% | (SVXY -1x->-0.5x Feb2018 caveat)", flush=True)

    cost = 0.0002  # ETP round-trip ~2bps per regime switch
    sw = d["regime"].diff().abs().fillna(0)
    timed = pd.Series(d["regime"].values * d["svxy_ret"].values - sw.values * cost, index=d.index)   # contango-only long SVXY
    uncond = d["svxy_ret"].copy()                                                                     # always long SVXY (raw short-vol beta)

    mt, mu = metrics(timed), metrics(uncond)
    # crisis windows
    def win(s, a, b):
        w = s[(s.index >= a) & (s.index <= b)]; return round(float(w.sum()) * 100, 1)
    crises = {"feb2018": (win(timed, "2018-01-25", "2018-02-15"), win(uncond, "2018-01-25", "2018-02-15")),
              "mar2020": (win(timed, "2020-02-20", "2020-03-31"), win(uncond, "2020-02-20", "2020-03-31"))}
    # ORB corr (MNQ daily)
    try:
        mdf = pd.read_csv(ROOT / "data/processed/MNQ_5m.csv"); mdt = pd.to_datetime(mdf["datetime"])
        mnq = mdf.assign(x=mdt.dt.normalize()).groupby("x")["close"].last().pct_change(); mnq.index = pd.to_datetime(mnq.index)
        al = pd.concat([timed.rename("a"), mnq.rename("b")], axis=1).dropna(); corr = round(float(al["a"].corr(al["b"])), 3)
    except Exception:
        corr = None

    dsr = deflated_sharpe(timed[timed != 0].values, n_trials=4)
    incr = (mt["sharpe"] or 0) > (mu["sharpe"] or 0) and (mt["MAR"] or 0) > (mu["MAR"] or 0)
    avoids = crises["feb2018"][0] > crises["feb2018"][1] and crises["mar2020"][0] > crises["mar2020"][1]
    robust = mt["pf"] >= 1.1 and (mt["h1_sharpe"] or 0) > 0 and (mt["h2_sharpe"] or 0) > 0 and "0/" not in mt["yrs_pos"]
    if incr and avoids and robust and dsr.get("passes"):
        v = "PASS_REVIEW_vol_premium"
    elif incr and robust:
        v = "WATCH_vol_carry"
    elif mt["sharpe"] and mt["sharpe"] > 0:
        v = "WATCH_marginal"
    else:
        v = "KILL"
    R = {"timed": mt, "unconditional_shortvol": mu, "crises_timed_vs_uncond_pct": crises, "corr_to_ORB_MNQ": corr,
         "DSR": dsr, "term_structure_timing_beats_uncond": incr, "avoids_crises": avoids, "verdict": v,
         "contango_pct_days": round(100 * float(d["regime"].mean()), 0)}
    print(f"\n  TIMED (contango-only short-vol): Sharpe={mt['sharpe']} ann={mt['ann_ret_pct']}% maxDD={mt['maxDD_pct']}% MAR={mt['MAR']} worstday={mt['worst_day_pct']}% PF={mt['pf']} H1/H2 Sharpe={mt['h1_sharpe']}/{mt['h2_sharpe']} yrs+={mt['yrs_pos']}", flush=True)
    print(f"  UNCOND  (always short-vol):     Sharpe={mu['sharpe']} ann={mu['ann_ret_pct']}% maxDD={mu['maxDD_pct']}% MAR={mu['MAR']} worstday={mu['worst_day_pct']}% yrs+={mu['yrs_pos']}", flush=True)
    print(f"  per-year timed %: {mt['per_year_pct']}", flush=True)
    print(f"  CRISIS (timed vs uncond): Feb2018 {crises['feb2018'][0]}% vs {crises['feb2018'][1]}% | Mar2020 {crises['mar2020'][0]}% vs {crises['mar2020'][1]}%", flush=True)
    print(f"  corr-to-ORB={corr} | DSR={dsr.get('dsr')} ({dsr.get('verdict')}) | timing>uncond={incr} avoids_crises={avoids} robust={robust}", flush=True)
    print(f"  -> VERDICT: {v}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24g_VX_carry.json").write_text(json.dumps({"cycle": "2026-06-24g_VX_carry", "result": R,
        "note": "VIX term-structure-timed short-vol carry; volatility premium; vs unconditional short-vol; crisis-tail tested; report-only"}, indent=2, default=str))
    print("\nWrote VX-carry JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
