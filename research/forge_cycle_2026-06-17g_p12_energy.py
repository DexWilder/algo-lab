"""Cycle 2026-06-17g — P12 WTI-Brent energy dislocation -> MCL, first-cut (report-only).

Non-gold rotation. Driver: WTI-Brent spread (FRED daily spots) dislocation -> reversion traded
via MCL (WTI futures). Genuinely different asset/driver from gold/equity/rates.

Discipline: MCL treated as COST-FRAGILE from the start (explicit slippage-sensitivity 1x/2x/3x
+ cost_ratio). MANDATORY date-split OOS. Separate ENERGY_SLEEVE_ENHANCER from PORTFOLIO_
DIVERSIFIER / WH2 by correlation to long-crude. ONE predeclared variant (no sweep). NO-lookahead:
FRED spots dated D (and publish-lagged ~1wk) -> merge_asof backward, allow_exact_matches=False
(staleness is conservative, flagged). NO synthetic fill, NO mutation.
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
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "yrs_pos": f"{int((per_yr>0).sum())}/{int(per_yr.shape[0])}"}


def run():
    print("Cycle 2026-06-17g — P12 WTI-Brent dislocation -> MCL (REPORT-ONLY)\n", flush=True)
    en = pd.read_csv(FEEDS / "energy_spot.csv", parse_dates=["date"])
    en["spread"] = en["wti"] - en["brent"]
    print(f"1. FEED: energy_spot n={len(en)} wti_last={en.dropna(subset=['wti'])['date'].max().date()} "
          f"(NOTE: FRED spot publish-lag ~1wk -> stale but no-lookahead; flagged realism caveat)", flush=True)
    print("2. NO-LOOKAHEAD: spread lagged via merge_asof backward allow_exact_matches=False (spread_date < trade_date).", flush=True)

    mcl = daily_close("MCL"); mcl = mcl[mcl.index.year >= 2021]
    mcl_ret = mcl.diff(); pv = ASSETS["MCL"]["point_value"]; cp = get_cost_params("MCL")
    mnq_ret = daily_close("MNQ").diff(); crude_bh = mcl_ret * pv

    td = pd.DataFrame({"date": mcl.index}).sort_values("date")
    sp = en[["date", "spread"]].dropna().sort_values("date").rename(columns={"date": "sdate"})
    m = pd.merge_asof(td, sp, left_on="date", right_on="sdate", direction="backward", allow_exact_matches=False)
    assert int((m["sdate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    spread = m.set_index("date")["spread"].reindex(mcl.index)
    lag_days = (m["date"] - m["sdate"]).dt.days
    print(f"3/4. JOIN+COVERAGE: MCL days={len(mcl)} spread-matched={int(spread.notna().sum())} "
          f"median_lag={float(lag_days.median())}d max_lag={int(lag_days.max())}d years={sorted(set(mcl.index.year))}", flush=True)

    # 5. ONE predeclared variant: WTI-Brent spread z-score (60d) MEAN-REVERSION -> MCL.
    # WTI cheap vs Brent (z<-1) -> long MCL (catch up); WTI rich (z>+1) -> short MCL. else flat.
    z = (spread - spread.rolling(60).mean()) / spread.rolling(60).std()
    pos = pd.Series(0.0, index=spread.index)
    pos[z < -1.0] = 1.0; pos[z > 1.0] = -1.0
    valid = pos.notna() & mcl_ret.notna() & z.notna()
    pos = pos[valid]; ret = mcl_ret[valid]; idx = pos.index

    def backtest(slip_mult):
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * slip_mult * cp["tick_size"] * pv)
        pnl = pos.values * ret.values * pv
        dpos = np.abs(np.diff(np.concatenate([[0], pos.values])))
        gross = float(np.sum(np.abs(pos.values * ret.values * pv)))
        cost = float(np.sum(dpos * rt))
        return pnl - dpos * rt, (cost / gross * 100 if gross else None)

    print("\n5/6. P12 spread-reversion board + COST-SENSITIVITY (MCL cost-fragile):", flush=True)
    base = None
    for sm in (1.0, 2.0, 3.0):
        pnl, cost_ratio = backtest(sm)
        st = stats(pnl, idx)
        tr = stats(pnl[idx.year <= 2022], idx[idx.year <= 2022]); te = stats(pnl[idx.year >= 2023], idx[idx.year >= 2023])
        if sm == 1.0:
            s2 = pd.Series(pnl, index=pd.to_datetime(idx))
            def _corr(a, b):
                al = pd.concat([a.rename("a"), b.rename("b")], axis=1).fillna(0.0)
                return round(float(al["a"].corr(al["b"])), 3)
            c_mnq = _corr(s2, mnq_ret); c_crude = _corr(s2, crude_bh)
            base = {"st": st, "tr": tr, "te": te, "cost_ratio_pct": round(cost_ratio, 1), "corr_mnq": c_mnq, "corr_longcrude": c_crude}
        print(f"  slip={sm}x: PF={st.get('pf')} net=${st.get('net')} cost_ratio={round(cost_ratio,1) if cost_ratio else None}% "
              f"OOS train/test={tr.get('pf')}/{te.get('pf')}", flush=True)

    # classification
    st, tr, te = base["st"], base["tr"], base["te"]
    pf = st.get("pf"); cmnq = base["corr_mnq"]; ccr = base["corr_longcrude"]
    quality = pf and pf > 1.2 and st["median"] >= 0 and st["h1_pf"] > 1.0 and st["h2_pf"] > 1.0
    oos_ok = (tr.get("pf") or 0) > 1.0 and (te.get("pf") or 0) > 1.0
    _, cr3 = backtest(3.0); cost_robust = (stats(backtest(3.0)[0], idx).get("pf") or 0) > 1.2
    if not pf:
        verdict = "KILL_low_n"
    elif not quality or not oos_ok:
        verdict = "KILL"
    elif not cost_robust:
        verdict = "KILL_cost_fragile"
    elif abs(ccr) >= 0.5:
        verdict = "ENERGY_SLEEVE_ENHANCER"
    elif abs(cmnq) < 0.3 and abs(ccr) < 0.5:
        verdict = "WH2_CANDIDATE"
    else:
        verdict = "PORTFOLIO_DIVERSIFIER_CAND"
    print(f"\n  full PF={pf} med=${st.get('median')} H1/H2={st.get('h1_pf')}/{st.get('h2_pf')} yrs+={st.get('yrs_pos')} "
          f"corr(mnq/crude)={cmnq}/{ccr} cost_ratio@1x={base['cost_ratio_pct']}% -> VERDICT: {verdict}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17g_p12_energy.json"
    out.write_text(json.dumps({"cycle": "2026-06-17g_p12_energy", "mode": "Lane B report-only; first-cut; OOS+cost-sensitivity; NON-WIRED",
        "base": base, "verdict": verdict, "caveats": "FRED spot publish-lag ~1wk (stale but no-lookahead); MCL cost-fragile; short train (2021-22)",
        "boundaries": "one variant; no sweep/synthetic-fill/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; one variant; cost-sensitivity; no mutation)", flush=True)


if __name__ == "__main__":
    run()
