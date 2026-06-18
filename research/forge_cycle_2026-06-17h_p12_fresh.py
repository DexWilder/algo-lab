"""Cycle 2026-06-17h — P12 retest on FRESH Yahoo futures (diagnostic, report-only).

DIAGNOSTIC, not rescue: did P12 fail because the IDEA is bad, or because the FRED spot feed
was ~1wk stale? IDENTICAL locked design to 17g (60d spread z-score reversion, lag 1 trading
day, date-split OOS, cost-sensitivity 1x/2x/3x, same classification). ONLY change = data
source: FRESH Yahoo CL=F (WTI) - BZ=F (Brent) instead of stale FRED spots. NO sweep, NO
rescue tuning. Yahoo = research-only (retail-grade, provenance-caveated); NOT capital evidence.
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

FEEDS = ROOT / "data" / "feeds"


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    return df.assign(date=dt.dt.normalize()).groupby("date")["close"].last()


def stats(p, idx):
    p = np.asarray(p, float); n = len(p)
    if n < 150:
        return {"n": n, "pf": None}
    s = pd.Series(p, index=pd.to_datetime(idx)); h = n // 2; per_yr = s.groupby(s.index.year).sum()
    return {"n": n, "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "yrs_pos": f"{int((per_yr>0).sum())}/{int(per_yr.shape[0])}"}


def _corr(a, b):
    al = pd.concat([a.rename("a"), b.rename("b")], axis=1).fillna(0.0)
    return round(float(al["a"].corr(al["b"])), 3)


def run():
    print("Cycle 2026-06-17h — P12 FRESH-data retest (Yahoo CL=F-BZ=F) — DIAGNOSTIC (REPORT-ONLY)\n", flush=True)
    en = pd.read_csv(FEEDS / "energy_futures_yahoo.csv", parse_dates=["date"])
    en["spread"] = en["wti_f"] - en["brent_f"]
    print(f"1. FEED: energy_futures_yahoo (Yahoo, FRESH) n={len(en)} last={en.dropna(subset=['wti_f'])['date'].max().date()} "
          f"(vs FRED stale to 2026-06-08). QUALITY: retail-grade research-only.", flush=True)

    mcl = daily_close("MCL"); mcl = mcl[mcl.index.year >= 2021]
    mcl_ret = mcl.diff(); pv = ASSETS["MCL"]["point_value"]; cp = get_cost_params("MCL")
    mnq_ret = daily_close("MNQ").diff(); crude_bh = mcl_ret * pv

    td = pd.DataFrame({"date": mcl.index}).sort_values("date")
    sp = en[["date", "spread"]].dropna().sort_values("date").rename(columns={"date": "sdate"})
    m = pd.merge_asof(td, sp, left_on="date", right_on="sdate", direction="backward", allow_exact_matches=False)
    assert int((m["sdate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    spread = m.set_index("date")["spread"].reindex(mcl.index)
    lag = (m["date"] - m["sdate"]).dt.days
    print(f"2/3. NO-LOOKAHEAD+JOIN: MCL days={len(mcl)} matched={int(spread.notna().sum())} "
          f"median_lag={float(lag.median())}d max_lag={int(lag.max())}d (fresh -> small lag)", flush=True)

    # IDENTICAL predeclared variant: 60d spread z-score reversion -> MCL
    z = (spread - spread.rolling(60).mean()) / spread.rolling(60).std()
    pos = pd.Series(0.0, index=spread.index); pos[z < -1.0] = 1.0; pos[z > 1.0] = -1.0
    valid = pos.notna() & mcl_ret.notna() & z.notna()
    pos = pos[valid]; ret = mcl_ret[valid]; idx = pos.index

    def bt(sm):
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * sm * cp["tick_size"] * pv)
        pnl = pos.values * ret.values * pv
        dpos = np.abs(np.diff(np.concatenate([[0], pos.values])))
        gross = float(np.sum(np.abs(pos.values * ret.values * pv)))
        return pnl - dpos * rt, (float(np.sum(dpos * rt)) / gross * 100 if gross else None)

    print("\n4/5. FRESH P12 board + cost-sensitivity:", flush=True)
    base = None
    for sm in (1.0, 2.0, 3.0):
        pnl, cr = bt(sm); st = stats(pnl, idx)
        tr = stats(pnl[idx.year <= 2022], idx[idx.year <= 2022]); te = stats(pnl[idx.year >= 2023], idx[idx.year >= 2023])
        if sm == 1.0:
            s2 = pd.Series(pnl, index=pd.to_datetime(idx))
            base = {"st": st, "tr": tr, "te": te, "cost_ratio_pct": round(cr, 1) if cr else None,
                    "corr_mnq": _corr(s2, mnq_ret), "corr_longcrude": _corr(s2, crude_bh)}
        print(f"  slip={sm}x: PF={st.get('pf')} net=${st.get('net')} cost_ratio={round(cr,1) if cr else None}% "
              f"OOS train/test={tr.get('pf')}/{te.get('pf')}", flush=True)

    st, tr, te = base["st"], base["tr"], base["te"]; pf = st.get("pf"); cmnq = base["corr_mnq"]; ccr = base["corr_longcrude"]
    quality = pf and pf > 1.2 and st["median"] >= 0 and st["h1_pf"] > 1.0 and st["h2_pf"] > 1.0
    oos_ok = (tr.get("pf") or 0) > 1.0 and (te.get("pf") or 0) > 1.0
    cost_robust = (stats(bt(3.0)[0], idx).get("pf") or 0) > 1.2
    if not pf:
        verdict = "KILL_low_n"
    elif not quality or not oos_ok:
        verdict = "KILL"
    elif not cost_robust:
        verdict = "KILL_cost_fragile"
    elif abs(ccr) >= 0.5:
        verdict = "ENERGY_SLEEVE_ENHANCER"
    elif abs(cmnq) < 0.3 and abs(ccr) < 0.5:
        verdict = "PORTFOLIO_DIVERSIFIER_CANDIDATE"
    else:
        verdict = "PORTFOLIO_DIVERSIFIER_CANDIDATE"
    # diagnostic vs stale (17g was PF 0.928)
    diag = ("FRESH improved vs stale (0.928) but " + ("still KILL" if verdict.startswith("KILL") else f"-> {verdict}")
            if pf else "low-n")
    print(f"\n  FRESH full PF={pf} med=${st.get('median')} H1/H2={st.get('h1_pf')}/{st.get('h2_pf')} yrs+={st.get('yrs_pos')} "
          f"corr(mnq/crude)={cmnq}/{ccr} -> VERDICT: {verdict}", flush=True)
    print(f"  DIAGNOSTIC vs stale-FRED P12 (PF 0.928): fresh PF {pf} -> "
          f"{'feed staleness was NOT the cause; mechanism is the problem' if (pf or 0) < 1.1 else 'feed staleness mattered; mechanism warrants honest classification'}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17h_p12_fresh.json"
    out.write_text(json.dumps({"cycle": "2026-06-17h_p12_fresh", "mode": "Lane B report-only; DIAGNOSTIC; fresh Yahoo; NON-WIRED",
        "stale_fred_p12_pf": 0.928, "fresh_base": base, "verdict": verdict, "diagnostic": diag,
        "data_caveat": "Yahoo retail-grade research-only; not capital evidence",
        "boundaries": "identical design; no sweep/rescue/synthetic-fill/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; diagnostic; no sweep; Yahoo research-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
