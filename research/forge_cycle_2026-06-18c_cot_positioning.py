"""Cycle 2026-06-18c — COT spec-positioning extreme reversal (report-only).

Scout: COT is reachable (S6 NOT feed-blocked) -> active-testable now. Mechanism: crowded specs
(non-commercials) at a positioning EXTREME are forced to unwind -> reversal. Weekly signal gates
a daily position. NO-LOOKAHEAD: COT report_date is the Tue snapshot, RELEASED ~Fri 15:30 ET ->
usable only AFTER release; lag release_date = report_date + 3d and require release_date < trade_date
(merge_asof strictly-prior). Dedup to canonical contract (max open_interest per sym/date).
clean-before-rolling on the z-score. ONE predeclared mechanism, OOS split, no sweep, no mutation.
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

COT_TO_FUT = {"10Y": "ZN", "GOLD": "MGC", "CRUDE": "MCL"}   # cleanest single-contract mappings


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index).astype("datetime64[ns]"); return s


def stats(p, idx):
    p = np.asarray(p, float); n = len(p)
    if n < 200:
        return {"n": n, "pf": None}
    s = pd.Series(p, index=pd.to_datetime(idx)); h = n // 2; py = s.groupby(s.index.year).sum()
    return {"n": n, "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}"}


def run():
    print("Cycle 2026-06-18c — COT spec-positioning extreme reversal (REPORT-ONLY)\n", flush=True)
    cot = pd.read_csv(ROOT / "data" / "feeds" / "cot.csv", parse_dates=["date"])
    # dedup canonical contract: per (sym,date) keep max open_interest
    cot = cot.sort_values("open_interest_all", ascending=False).drop_duplicates(["sym", "date"]).sort_values(["sym", "date"])
    cot["release"] = (cot["date"] + pd.Timedelta(days=3)).astype("datetime64[ns]")   # Tue snapshot -> Fri release
    print("NO-LOOKAHEAD: COT released ~Fri (report+3d); used only when release < trade_date.\n", flush=True)

    results = {}
    for cotsym, fut in COT_TO_FUT.items():
        c = cot[cot["sym"] == cotsym].copy()
        if len(c) < 100:
            results[f"{cotsym}->{fut}"] = {"n": len(c), "verdict": "KILL_low_cot"}; continue
        # spec_net z-score over trailing 52 weeks (clean-before-rolling; cot weekly, min_periods)
        c["z"] = (c["spec_net"] - c["spec_net"].rolling(52, min_periods=26).mean()) / c["spec_net"].rolling(52, min_periods=26).std()
        c = c.dropna(subset=["z"])
        # signal: spec extreme long (z>1.5) -> short future (reversal); extreme short (z<-1.5) -> long
        c["pos"] = 0.0; c.loc[c["z"] > 1.5, "pos"] = -1.0; c.loc[c["z"] < -1.5, "pos"] = 1.0
        s = daily_close(fut); s = s[s.index.year >= 2019]; ret = s.diff()
        pv = ASSETS[fut]["point_value"]; cp = get_cost_params(fut)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        # attach COT position as-of latest RELEASE strictly before each trade day
        td = pd.DataFrame({"date": s.index}).sort_values("date")
        m = pd.merge_asof(td, c[["release", "pos"]].dropna().sort_values("release"),
                          left_on="date", right_on="release", direction="backward", allow_exact_matches=False)
        assert int((m["release"] >= m["date"]).sum()) == 0, "LOOKAHEAD"
        pos = m.set_index("date")["pos"].reindex(s.index).fillna(0.0)
        valid = ret.notna()
        p = pos[valid].values * ret[valid].values * pv
        dpos = np.abs(np.diff(np.concatenate([[0], pos[valid].values]))); p = p - dpos * rt
        idx = ret[valid].index
        st = stats(p, idx); tr = stats(p[idx.year <= 2022], idx[idx.year <= 2022]); te = stats(p[idx.year >= 2023], idx[idx.year >= 2023])
        pf = st.get("pf")
        quality = pf and pf > 1.2 and st["median"] >= 0 and st["h1_pf"] > 1.0 and st["h2_pf"] > 1.0
        oos = (tr.get("pf") or 0) > 1.0 and (te.get("pf") or 0) > 1.0
        fires = int((pos != 0).sum())
        v = "KILL_low_n" if not pf else ("KILL" if not quality or not oos else "STRUCTURE_FOUND")
        results[f"{cotsym}->{fut}"] = {**st, "train_pf": tr.get("pf"), "test_pf": te.get("pf"), "days_in_pos": fires, "verdict": v}
        print(f"  {cotsym}->{fut}: PF={pf} med=${st.get('median')} net=${st.get('net')} H1/H2={st.get('h1_pf')}/{st.get('h2_pf')} "
              f"OOS={tr.get('pf')}/{te.get('pf')} days-in-pos={fires} -> {v}", flush=True)

    surv = [k for k, v in results.items() if v["verdict"] == "STRUCTURE_FOUND"]
    print(f"\n  survivors: {surv or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-18c_cot_positioning.json"
    out.write_text(json.dumps({"cycle": "2026-06-18c_cot_positioning", "mode": "Lane 1 report-only; reachable COT; NON-WIRED",
        "results": results, "note": "weekly COT gates daily; no-lookahead Fri-release lag; spec-extreme reversal",
        "boundaries": "one mechanism; no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; reachable scout; no mutation)", flush=True)


if __name__ == "__main__":
    run()
