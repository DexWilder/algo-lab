"""Cycle 2026-06-24c — S1 roll-yield carry via WTI spot-front BASIS PROXY (report-only).

CLASS-B PROXY, explicitly NOT true front/next term structure (that's class-C: needs 2nd-month futures, packetized).
Mechanism (Schwager commodity carry): backwardation (front future < spot) => positive roll yield + historically
positive crude forward returns => LONG crude; contango (front > spot) => negative roll yield => flat/short.
Predeclared, NO flip. Sparse/carry/ENSEMBLE lane — NOT a WH replacement.

Data: WTI spot (FRED energy_spot.csv) + WTI front future (Yahoo energy_futures_yahoo.csv), 2011+. Tradeable:
wti_f daily returns (long history) + MCL micro daily (2019+, the real instrument). Signal known PRIOR close.
Battery: backwardation/contango regimes; long vs short/flat decomposition; per-year; H1/H2; cost stress;
top-k; crude-shock tail (2020 COVID, 2022); vs UNCONDITIONAL long crude (the incremental test).
HONESTY GUARD: if basis is degenerate (std ~0, FRED spot == front settlement) => FEED-BLOCKED, not noise.
Report-only; no mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"


def _pf(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]; l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def mcl_daily():
    df = pd.read_csv(ROOT / "data/processed/MCL_5m.csv"); dtv = pd.to_datetime(df["datetime"])
    return df.assign(d=dtv.dt.normalize()).groupby("d")["close"].last()


def run():
    print("Cycle 2026-06-24c — S1 roll-yield carry (spot-front basis PROXY; report-only)\n", flush=True)
    spot = pd.read_csv(ROOT / "data/feeds/energy_spot.csv", parse_dates=["date"]).set_index("date")["wti"]
    fut = pd.read_csv(ROOT / "data/feeds/energy_futures_yahoo.csv", parse_dates=["date"]).set_index("date")["wti_f"]
    d = pd.DataFrame({"spot": spot, "fut": fut}).dropna().sort_index()
    d = d[d.index >= "2011-01-01"]
    d["basis"] = d["fut"] / d["spot"] - 1                     # >0 contango, <0 backwardation
    d["basis_z"] = (d["basis"] - d["basis"].rolling(120, min_periods=60).mean()) / d["basis"].rolling(120, min_periods=60).std()

    # HONESTY GUARD
    bstd = float(d["basis"].std())
    print(f"=== BASIS SANITY === n={len(d)} mean={d['basis'].mean()*100:.3f}% std={bstd*100:.3f}% "
          f"min={d['basis'].min()*100:.2f}% max={d['basis'].max()*100:.2f}% | days |basis|>1%: {int((d['basis'].abs()>0.01).sum())}", flush=True)
    if bstd < 0.0008:
        out = {"cycle": "2026-06-24c_s1_rollyield_carry", "verdict": "FEED-BLOCKED",
               "note": f"spot-front basis degenerate (std {bstd*100:.4f}%) — FRED WTI spot tracks front settlement too closely; "
                       "proxy inadequate. TRUE roll-yield requires 2nd-month futures (class-C feed need: CL1+CL2 term structure)."}
        (REPORTS / "forge_cycle_2026-06-24c_s1_rollyield_carry.json").write_text(json.dumps(out, indent=2))
        print("\n  -> FEED-BLOCKED: basis proxy inadequate; packetize 2nd-month feed (class-C). No verdict on carry.", flush=True)
        return

    OUT = {"cycle": "2026-06-24c_s1_rollyield_carry", "proxy": "WTI spot-front basis (NOT true term structure)", "basis_std_pct": round(bstd*100, 3), "instruments": {}}
    # signal known prior close -> trade today; backwardation = basis_z < -0.5, contango = basis_z > 0.5
    d["regime"] = 0
    d.loc[d["basis_z"] < -0.5, "regime"] = 1       # backwardation -> long
    d.loc[d["basis_z"] > 0.5, "regime"] = -1       # contango -> short/flat
    d["pos"] = d["regime"].shift(1)                # act next day (no lookahead)

    for label, px in [("wti_f_future", d["fut"]), ("MCL_micro", mcl_daily())]:
        ret = px.pct_change()
        x = pd.DataFrame({"pos": d["pos"], "ret": ret.reindex(d.index), "basis_z": d["basis_z"], "year": d.index.year}).dropna(subset=["pos", "ret"])
        if label == "MCL_micro":
            x = x[x.index >= "2019-01-01"]
        if len(x) < 100:
            OUT["instruments"][label] = {"verdict": "DATA-LIMITED", "n": len(x)}; continue
        cost = 0.0006
        # long-in-backwardation leg, short-in-contango leg
        longp = (x["ret"][x["pos"] == 1] - cost)
        shortp = (-x["ret"][x["pos"] == -1] - cost)
        combined = pd.concat([longp, shortp])
        uncond = (x["ret"] - 0)                      # unconditional long crude (no cost, benchmark beta)
        p = combined.to_numpy(); h = len(p) // 2; sp = np.sort(p)[::-1]; tot = p[p > 0].sum()
        yr = combined.groupby(combined.index.year).sum()
        # crude-shock tail
        shock = combined[(combined.index >= "2020-02-01") & (combined.index <= "2020-05-31")]
        shock22 = combined[(combined.index >= "2022-02-01") & (combined.index <= "2022-04-30")]
        m = {"n": len(p), "pf": round(_pf(p), 3), "mean_bps": round(float(p.mean())*1e4, 1), "win_pct": round(float((p>0).mean())*100, 1),
             "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
             "long_n": int((x["pos"]==1).sum()), "long_pf": round(_pf(longp.to_numpy()), 3) if len(longp) else None, "long_mean_bps": round(float(longp.mean())*1e4,1) if len(longp) else None,
             "short_n": int((x["pos"]==-1).sum()), "short_pf": round(_pf(shortp.to_numpy()), 3) if len(shortp) else None, "short_mean_bps": round(float(shortp.mean())*1e4,1) if len(shortp) else None,
             "top5_pct": round(float(sp[:5].sum())/tot*100,1) if tot>0 else None,
             "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}",
             "pf_12bps": round(_pf(pd.concat([x['ret'][x['pos']==1]-0.0012, -x['ret'][x['pos']==-1]-0.0012]).to_numpy()), 3),
             "uncond_long_mean_bps": round(float(uncond.mean())*1e4,1), "signal_long_mean_bps": round(float((x['ret'][x['pos']==1]).mean())*1e4,1),
             "backwardation_fwd_mean_bps": round(float(x['ret'][x['pos']==1].mean())*1e4,1), "contango_fwd_mean_bps": round(float(x['ret'][x['pos']==-1].mean())*1e4,1),
             "shock2020_net_pct": round(float(shock.sum())*100,1), "shock2022_net_pct": round(float(shock22.sum())*100,1)}
        # incremental: does backwardation beat unconditional, and is contango actually worse (not just less-good long)?
        adds_value = m["backwardation_fwd_mean_bps"] > m["uncond_long_mean_bps"] and m["contango_fwd_mean_bps"] < m["uncond_long_mean_bps"]
        both_sides = (m["long_pf"] or 0) > 1.0 and (m["short_pf"] or 0) > 1.0
        ok = m["pf"] >= 1.2 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and "0/" not in m["yrs_pos"] and m["pf_12bps"] >= 1.1 and adds_value
        m["adds_value_vs_uncond"] = adds_value; m["both_sides_work"] = both_sides
        m["verdict"] = ("WATCH_carry" if ok else ("KILL_just_long_crude" if not adds_value and m["mean_bps"]>0 else "KILL"))
        OUT["instruments"][label] = m
        print(f"\n=== {label} (n={m['n']}) ===", flush=True)
        print(f"  PF={m['pf']} mean={m['mean_bps']}bps win={m['win_pct']}% H1/H2={m['h1_pf']}/{m['h2_pf']} yrs+={m['yrs_pos']} PF@12bps={m['pf_12bps']} top5={m['top5_pct']}%", flush=True)
        print(f"  long(backwardation): n={m['long_n']} pf={m['long_pf']} mean={m['long_mean_bps']}bps | short(contango): n={m['short_n']} pf={m['short_pf']} mean={m['short_mean_bps']}bps", flush=True)
        print(f"  INCREMENTAL: backwardation_fwd={m['backwardation_fwd_mean_bps']}bps vs uncond_long={m['uncond_long_mean_bps']}bps vs contango_fwd={m['contango_fwd_mean_bps']}bps -> adds_value={adds_value}", flush=True)
        print(f"  tail: shock2020={m['shock2020_net_pct']}% shock2022={m['shock2022_net_pct']}% -> {m['verdict']}", flush=True)

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24c_s1_rollyield_carry.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote S1 JSON.\n(report-only; no mutation; PROXY not true term structure)", flush=True)


if __name__ == "__main__":
    run()
