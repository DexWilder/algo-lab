"""Cycle 2026-06-17i — Lane 1: copper/gold ratio -> ZN directional (report-only).

Structural cross-asset macro driver (NOT generic OHLCV): copper/gold ratio = growth/risk-on
vs safe-haven demand (the Gundlach copper-gold <-> 10y-yield relationship). Rising ratio ->
yields up -> bonds (ZN) down. Trades ZN (non-gold-traded, non-MNQ) off a cross-asset signal.

Locked discipline: fresh Yahoo HG=F/GC=F (research-only, retail-grade), lag 1 trading day
(no-lookahead), date-split OOS, classification RATES_SLEEVE_ENHANCER / PORTFOLIO_DIVERSIFIER /
WH2 by corr to long-ZN. ONE predeclared variant, no sweep, no synthetic fill, no mutation.
Yahoo = map expansion, NOT capital evidence.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402


def yahoo(sym):
    enc = urllib.parse.quote(sym)
    req = urllib.request.Request(f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range=15y&interval=1d",
                                 headers={"User-Agent": "Mozilla/5.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    r = d["chart"]["result"][0]
    s = pd.Series(r["indicators"]["quote"][0]["close"], index=pd.to_datetime(pd.to_datetime(r["timestamp"], unit="s").date))
    return s[~s.index.duplicated()].dropna()


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    return df.assign(date=dt.dt.normalize()).groupby("date")["close"].last()


def stats(p, idx):
    p = np.asarray(p, float); n = len(p)
    if n < 200:
        return {"n": n, "pf": None}
    s = pd.Series(p, index=pd.to_datetime(idx)); h = n // 2; per_yr = s.groupby(s.index.year).sum()
    return {"n": n, "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "yrs_pos": f"{int((per_yr>0).sum())}/{int(per_yr.shape[0])}"}


def _corr(a, b):
    al = pd.concat([a.rename("a"), b.rename("b")], axis=1).fillna(0.0)
    return round(float(al["a"].corr(al["b"])), 3)


def run():
    print("Cycle 2026-06-17i — Lane 1: copper/gold ratio -> ZN directional (REPORT-ONLY)\n", flush=True)
    print("1. ACQUIRE (Yahoo, research-only): HG=F (copper), GC=F (gold)", flush=True)
    hg = yahoo("HG=F"); gc = yahoo("GC=F")
    ratio = (hg / gc).dropna()
    ratio_df = ratio.reset_index(); ratio_df.columns = ["date", "cu_au"]
    ratio_df.to_csv(ROOT / "data" / "feeds" / "copper_gold_ratio_yahoo.csv", index=False)
    print(f"   copper n={len(hg)} gold n={len(gc)} ratio n={len(ratio)} range={ratio.index.min().date()}..{ratio.index.max().date()}", flush=True)

    zn = daily_close("ZN"); zn = zn[zn.index.year >= 2019]
    zn.index = pd.to_datetime(zn.index).astype("datetime64[ns]"); zn_ret = zn.diff()
    pv = ASSETS["ZN"]["point_value"]; cp = get_cost_params("ZN")
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    mnq_ret = daily_close("MNQ").diff(); mnq_ret.index = pd.to_datetime(mnq_ret.index).astype("datetime64[ns]")
    zn_bh = zn_ret * pv

    td = pd.DataFrame({"date": pd.to_datetime(zn.index).astype("datetime64[ns]")}).sort_values("date")
    rr = ratio.reset_index(); rr.columns = ["rdate", "cu_au"]
    rr["rdate"] = pd.to_datetime(rr["rdate"]).astype("datetime64[ns]")
    m = pd.merge_asof(td, rr.sort_values("rdate"), left_on="date", right_on="rdate", direction="backward", allow_exact_matches=False)
    assert int((m["rdate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    cu_au = m.set_index("date")["cu_au"].reindex(zn.index)
    print(f"2/3. NO-LOOKAHEAD+JOIN: ZN days={len(zn)} matched={int(cu_au.notna().sum())} (ratio lagged strictly prior)", flush=True)

    # ONE predeclared variant: 20d change in copper/gold ratio -> ZN directional.
    # ratio rising (growth/risk-on) -> yields up -> SHORT ZN; falling -> LONG ZN.
    d_ratio = cu_au.pct_change(20)
    pos = -np.sign(d_ratio)  # short ZN when ratio rising
    valid = pos.notna() & zn_ret.notna() & (d_ratio != 0)
    pos = pos[valid]; ret = zn_ret[valid]; idx = pos.index
    pnl = pos.values * ret.values * pv
    dpos = np.abs(np.diff(np.concatenate([[0], pos.values])))
    pnl = pnl - dpos * rt
    st = stats(pnl, idx)
    tr = stats(pnl[idx.year <= 2022], idx[idx.year <= 2022]); te = stats(pnl[idx.year >= 2023], idx[idx.year >= 2023])
    s2 = pd.Series(pnl, index=pd.to_datetime(idx)); c_mnq = _corr(s2, mnq_ret); c_zn = _corr(s2, zn_bh)

    pf = st.get("pf")
    quality = pf and pf > 1.2 and st["median"] >= 0 and st["h1_pf"] > 1.0 and st["h2_pf"] > 1.0
    oos_ok = (tr.get("pf") or 0) > 1.0 and (te.get("pf") or 0) > 1.0
    if not pf:
        verdict = "KILL_low_n"
    elif not quality or not oos_ok:
        verdict = "KILL"
    elif abs(c_zn) >= 0.5:
        verdict = "RATES_SLEEVE_ENHANCER"
    elif abs(c_mnq) < 0.3 and abs(c_zn) < 0.5:
        verdict = "WH2_CANDIDATE"
    else:
        verdict = "PORTFOLIO_DIVERSIFIER_CANDIDATE"
    print("\n4/5. BOARD:", flush=True)
    print(f"  copper_gold->ZN: PF={pf} med=${st.get('median')} net=${st.get('net')} H1/H2={st.get('h1_pf')}/{st.get('h2_pf')} "
          f"yrs+={st.get('yrs_pos')} OOS train/test={tr.get('pf')}/{te.get('pf')} corr(mnq/longZN)={c_mnq}/{c_zn} -> {verdict}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17i_copper_gold_rates.json"
    out.write_text(json.dumps({"cycle": "2026-06-17i_copper_gold_rates", "mode": "Lane B report-only; Lane-1 cross-asset; Yahoo research-only; NON-WIRED",
        "board": {**st, "train_pf": tr.get("pf"), "test_pf": te.get("pf"), "corr_mnq": c_mnq, "corr_longZN": c_zn, "verdict": verdict},
        "data_caveat": "Yahoo retail-grade research-only; not capital evidence",
        "boundaries": "one variant; no sweep/synthetic-fill/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; one variant; Yahoo research-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
