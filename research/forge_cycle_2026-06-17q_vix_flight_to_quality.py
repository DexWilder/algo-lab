"""Cycle 2026-06-17q — Lane 1: VIX-spike flight-to-quality -> ZN (report-only).

Reachable cross-asset FORCED-FLOW: risk-off VIX spike forces a flight-to-quality bid into
Treasuries. Non-gold, ZN-traded (non-MNQ). Tests next-day FOLLOW-THROUGH (lag 1d, no-lookahead;
the same-day flight is likely already priced). clean-before-rolling on VIX (NaN-holes). OOS split.
2 minimal predeclared variants (spike-change, high-regime), no sweep, no mutation.
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
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index).astype("datetime64[ns]"); return s


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
    print("Cycle 2026-06-17q — Lane 1: VIX-spike flight-to-quality -> ZN (REPORT-ONLY)\n", flush=True)
    vix = pd.read_csv(ROOT / "data" / "feeds" / "vix.csv", parse_dates=["date"])
    vix["date"] = pd.to_datetime(vix["date"]).astype("datetime64[ns]")
    vix = vix.sort_values("date").dropna(subset=["vix"]).reset_index(drop=True)   # clean-before-rolling
    vix["chg1"] = vix["vix"].diff()
    vix["mean60"] = vix["vix"].rolling(60).mean()
    print(f"1. FEED: vix clean n={len(vix)} (NaN-cleaned before diff/rolling)", flush=True)

    zn = daily_close("ZN"); zn = zn[zn.index.year >= 2019]; zn_ret = zn.diff()
    pv = ASSETS["ZN"]["point_value"]; cp = get_cost_params("ZN")
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    mnq_ret = daily_close("MNQ").diff(); mnq_ret.index = pd.to_datetime(mnq_ret.index).astype("datetime64[ns]")
    zn_bh = zn_ret * pv

    td = pd.DataFrame({"date": zn.index}).sort_values("date")
    m = pd.merge_asof(td, vix[["date", "chg1", "vix", "mean60"]].dropna().rename(columns={"date": "vdate"}),
                      left_on="date", right_on="vdate", direction="backward", allow_exact_matches=False)
    assert int((m["vdate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
    m = m.set_index("date")
    print(f"2/3. NO-LOOKAHEAD+JOIN: ZN days={len(zn)} matched={int(m['vix'].notna().sum())} (VIX lagged strictly prior)", flush=True)

    def screen(name, pos):
        valid = pos.notna() & zn_ret.notna() & (pos != 0)
        p = pos[valid]; r = zn_ret[valid]; idx = p.index
        pnl = p.values * r.values * pv
        dpos = np.abs(np.diff(np.concatenate([[0], p.values]))); pnl = pnl - dpos * rt
        st = stats(pnl, idx)
        tr = stats(pnl[idx.year <= 2022], idx[idx.year <= 2022]); te = stats(pnl[idx.year >= 2023], idx[idx.year >= 2023])
        s2 = pd.Series(pnl, index=pd.to_datetime(idx)); cm = _corr(s2, mnq_ret); cz = _corr(s2, zn_bh)
        pf = st.get("pf")
        quality = pf and pf > 1.2 and st["median"] >= 0 and st["h1_pf"] > 1.0 and st["h2_pf"] > 1.0
        oos = (tr.get("pf") or 0) > 1.0 and (te.get("pf") or 0) > 1.0
        v = "KILL_low_n" if not pf else ("KILL" if not quality or not oos else ("RATES_SLEEVE_ENHANCER" if abs(cz) >= 0.5 else ("CANDIDATE" if abs(cm) < 0.3 else "WATCH")))
        print(f"  {name:<26} PF={pf} med=${st.get('median')} net=${st.get('net')} H1/H2={st.get('h1_pf')}/{st.get('h2_pf')} "
              f"OOS={tr.get('pf')}/{te.get('pf')} fires={int(valid.sum())} corr(mnq/zn)={cm}/{cz} -> {v}", flush=True)
        return {"verdict": v, **st, "train_pf": tr.get("pf"), "test_pf": te.get("pf"), "corr_mnq": cm, "corr_zn": cz, "n_fires": int(valid.sum())}

    print("\n4/5. BOARD (2 predeclared variants):", flush=True)
    res = {}
    # V1: VIX spike (1d change in top ~15%) -> long ZN next day (flight-to-quality follow-through)
    thr = float(np.nanpercentile(m["chg1"].dropna(), 85))
    res["V1_spike_followthrough"] = screen(f"V1 VIX-spike(>{thr:.2f})->longZN", (m["chg1"] > thr).astype(float))
    # V2: VIX high-regime (above clean 60d mean) -> long ZN (risk-off regime)
    res["V2_highregime"] = screen("V2 VIX>60dmean->longZN", (m["vix"] > m["mean60"]).astype(float))

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17q_vix_flight_to_quality.json"
    out.write_text(json.dumps({"cycle": "2026-06-17q_vix_flight_to_quality", "mode": "Lane 1 report-only; reachable forced-flow; NON-WIRED",
        "spike_threshold": round(thr, 2), "results": res, "boundaries": "2 variants; clean-before-rolling; no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; reachable forced-flow probe; no mutation)", flush=True)


if __name__ == "__main__":
    run()
