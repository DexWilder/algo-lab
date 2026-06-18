"""Cycle 2026-06-17k — Lane 1: dollar (DTWEXBGS) -> MCL directional (report-only).

Non-gold, non-MNQ daily macro driver: crude is USD-priced -> dollar down => crude up. Structural
(pricing-currency) rationale. Keeps Lane 1 alive in parallel with Lane 2. Locked discipline:
clean the dollar series BEFORE any rolling/change (NaN-rolling lesson from 17j), lag 1 trading
day, date-split OOS, classification by corr to long-crude. ONE predeclared variant, no sweep,
no synthetic fill, no mutation. FRED dollar = research-grade.
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
    s.index = pd.to_datetime(s.index).astype("datetime64[ns]"); return s


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
    print("Cycle 2026-06-17k — Lane 1: dollar -> MCL directional (REPORT-ONLY)\n", flush=True)
    usd = pd.read_csv(ROOT / "data" / "feeds" / "dollar_index.csv", parse_dates=["date"])
    usd["date"] = pd.to_datetime(usd["date"]).astype("datetime64[ns]")
    usd = usd.sort_values("date").dropna(subset=["usd_broad"]).reset_index(drop=True)   # CLEAN before change (NaN-rolling lesson)
    usd["chg20"] = usd["usd_broad"].pct_change(20)
    print(f"1. FEED: dollar_index clean n={len(usd)} (NaN-cleaned before change)", flush=True)

    mcl = daily_close("MCL"); mcl = mcl[mcl.index.year >= 2021]; mcl_ret = mcl.diff()
    pv = ASSETS["MCL"]["point_value"]; cp = get_cost_params("MCL")
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    mnq_ret = daily_close("MNQ").diff(); crude_bh = mcl_ret * pv

    td = pd.DataFrame({"date": mcl.index}).sort_values("date")
    m = pd.merge_asof(td, usd[["date", "chg20"]].dropna().rename(columns={"date": "udate"}),
                      left_on="date", right_on="udate", direction="backward", allow_exact_matches=False)
    assert int((m["udate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    chg = m.set_index("date")["chg20"].reindex(mcl.index)
    print(f"2/3. NO-LOOKAHEAD+JOIN: MCL days={len(mcl)} matched={int(chg.notna().sum())}", flush=True)

    # ONE predeclared variant: dollar falling (20d chg<0) -> long MCL; rising -> short MCL.
    pos = -np.sign(chg)
    valid = pos.notna() & mcl_ret.notna() & (chg != 0)
    pos = pos[valid]; ret = mcl_ret[valid]; idx = pos.index
    pnl = pos.values * ret.values * pv
    dpos = np.abs(np.diff(np.concatenate([[0], pos.values]))); pnl = pnl - dpos * rt
    st = stats(pnl, idx)
    tr = stats(pnl[idx.year <= 2022], idx[idx.year <= 2022]); te = stats(pnl[idx.year >= 2023], idx[idx.year >= 2023])
    s2 = pd.Series(pnl, index=pd.to_datetime(idx)); c_mnq = _corr(s2, mnq_ret); c_crude = _corr(s2, crude_bh)
    pf = st.get("pf")
    quality = pf and pf > 1.2 and st["median"] >= 0 and st["h1_pf"] > 1.0 and st["h2_pf"] > 1.0
    oos_ok = (tr.get("pf") or 0) > 1.0 and (te.get("pf") or 0) > 1.0
    if not pf:
        verdict = "KILL_low_n"
    elif not quality or not oos_ok:
        verdict = "KILL"
    elif abs(c_crude) >= 0.5:
        verdict = "ENERGY_SLEEVE_ENHANCER"
    elif abs(c_mnq) < 0.3 and abs(c_crude) < 0.5:
        verdict = "WH2_CANDIDATE"
    else:
        verdict = "PORTFOLIO_DIVERSIFIER_CANDIDATE"
    print("\n4/5. BOARD:", flush=True)
    print(f"  dollar->MCL: PF={pf} med=${st.get('median')} net=${st.get('net')} H1/H2={st.get('h1_pf')}/{st.get('h2_pf')} "
          f"yrs+={st.get('yrs_pos')} OOS train/test={tr.get('pf')}/{te.get('pf')} corr(mnq/crude)={c_mnq}/{c_crude} -> {verdict}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17k_dollar_crude.json"
    out.write_text(json.dumps({"cycle": "2026-06-17k_dollar_crude", "mode": "Lane 1 report-only; non-gold macro; NON-WIRED",
        "board": {**st, "train_pf": tr.get("pf"), "test_pf": te.get("pf"), "corr_mnq": c_mnq, "corr_longcrude": c_crude, "verdict": verdict},
        "boundaries": "one variant; clean-before-rolling; no sweep/synthetic-fill/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; one variant; no mutation)", flush=True)


if __name__ == "__main__":
    run()
