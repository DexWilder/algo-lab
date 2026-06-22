"""Cycle 2026-06-22h — NY-Fed/funding forced-flow: SOFR-EFFR stress -> rates (report-only).

New forced-flow vein (cheapest predeclared screen first). Forced participant: under repo/funding
STRESS (SOFR >> EFFR), leveraged players face margin/funding pressure -> flight-to-quality bid in
Treasuries. Hypothesis: high SOFR-EFFR spread (lagged) -> long ZN/ZF next day. Also predeclared
contrast: RRP-volume surge (liquidity glut). Clean-before-rolling (funding series have business-day
gaps), lag 1d (SOFR/EFFR publish next morning), merge_asof strictly-prior, OOS, cost-aware. No sweep.
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
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index).astype("datetime64[ns]"); return s


def stats(p, idx):
    p = np.asarray(p, float); n = len(p)
    if n < 150:
        return {"n": n, "pf": None}
    s = pd.Series(p, index=pd.to_datetime(idx)); h = n // 2; py = s.groupby(s.index.year).sum()
    return {"n": n, "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}"}


def run():
    print("Cycle 2026-06-22h — funding-stress (SOFR-EFFR) -> rates flight-to-quality (REPORT-ONLY)\n", flush=True)
    f = pd.read_csv(ROOT / "data" / "feeds" / "funding.csv", parse_dates=["date"])
    # clean-before-rolling: spread on rows where both present
    fs = f.dropna(subset=["sofr", "effr"]).copy()
    fs["spread"] = fs["sofr"] - fs["effr"]
    fs["spread_z"] = (fs["spread"] - fs["spread"].rolling(60, min_periods=30).mean()) / fs["spread"].rolling(60, min_periods=30).std()
    fs = fs.dropna(subset=["spread_z"])
    fs["date"] = pd.to_datetime(fs["date"]).astype("datetime64[ns]")
    # RRP surge (contrast): vol z-score
    fr = f.dropna(subset=["rrp_vol"]).copy()
    fr["rrp_z"] = (fr["rrp_vol"] - fr["rrp_vol"].rolling(60, min_periods=30).mean()) / fr["rrp_vol"].rolling(60, min_periods=30).std()
    fr = fr.dropna(subset=["rrp_z"]); fr["date"] = pd.to_datetime(fr["date"]).astype("datetime64[ns]")
    print(f"funding: SOFR-EFFR spread n={len(fs)} (stress days z>1: {int((fs['spread_z']>1).sum())}); RRP n={len(fr)}\n", flush=True)

    results = {}
    for asset in ("ZN", "ZF"):
        s = daily_close(asset); s = s[s.index.year >= 2019]; ret = s.diff()
        pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        mnq = daily_close("MNQ").diff(); mnq.index = pd.to_datetime(mnq.index).astype("datetime64[ns]")
        td = pd.DataFrame({"date": s.index}).sort_values("date")
        # SOFR-EFFR stress -> long bonds (lag strictly prior)
        m = pd.merge_asof(td, fs[["date", "spread_z"]].rename(columns={"date": "fdate"}).sort_values("fdate"),
                          left_on="date", right_on="fdate", direction="backward", allow_exact_matches=False)
        assert int((m["fdate"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
        z = m.set_index("date")["spread_z"].reindex(s.index)
        for label, pos in [("stress_long(z>1)", (z > 1).astype(float)),
                           ("stress_long(z>0.5)", (z > 0.5).astype(float))]:
            valid = pos.notna() & ret.notna() & (pos != 0)
            p = pos[valid].values * ret[valid].values * pv
            dpos = np.abs(np.diff(np.concatenate([[0], pos[valid].values]))); p = p - dpos * rt
            idx = ret[valid].index; st = stats(p, idx)
            if st.get("pf"):
                tr = stats(p[idx.year <= 2022], idx[idx.year <= 2022]); te = stats(p[idx.year >= 2023], idx[idx.year >= 2023])
                s2 = pd.Series(p, index=pd.to_datetime(idx)); al = pd.concat([s2.rename('a'), mnq.rename('b')], axis=1).fillna(0.0)
                cm = round(float(al['a'].corr(al['b'])), 3)
                v = "STRUCTURE_FOUND" if (st["pf"] > 1.2 and st["median"] >= 0 and (tr.get("pf") or 0) > 1.0 and (te.get("pf") or 0) > 1.0) else "KILL"
                print(f"  {asset} {label}: n={st['n']} fires PF={st['pf']} net=${st['net']} H1/H2={st['h1_pf']}/{st['h2_pf']} OOS={tr.get('pf')}/{te.get('pf')} corrMNQ={cm} -> {v}", flush=True)
                results[f"{asset}-{label}"] = {**st, "verdict": v}
            else:
                print(f"  {asset} {label}: n={st['n']} -> KILL_low_n", flush=True)
                results[f"{asset}-{label}"] = {"n": st["n"], "verdict": "KILL_low_n"}

    surv = [k for k, v in results.items() if v.get("verdict") == "STRUCTURE_FOUND"]
    print(f"\n  survivors: {surv or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22h_funding_stress.json"
    out.write_text(json.dumps({"cycle": "2026-06-22h_funding_stress", "mode": "Lane B report-only; NY-Fed/funding forced-flow; NON-WIRED",
        "results": results, "note": "cheapest predeclared funding-stress screen; clean-before-rolling; lag 1d; RRP/SOMA/WALCL variants untested",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; forced-flow probe; no mutation)", flush=True)


if __name__ == "__main__":
    run()
