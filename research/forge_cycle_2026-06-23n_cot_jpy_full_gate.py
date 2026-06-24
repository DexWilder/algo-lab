"""Cycle 2026-06-23n — COT-JPY->6J positioning-extreme reversal FULL GATE (report-only).

Live survivor from Library batch-1 (PF 1.33 cheap screen). Full battery: proper COT release lag (Tue
positions released Fri 15:30 ET -> actionable Fri close), per-year, H1/H2, top-k concentration, cost/slip
stress, long/short decomposition, regime/tail, correlation to existing equity sleeve (MNQ). Predeclared:
spec_net z-extreme -> FADE (crowded specs exhaust). NO flip. Report-only; no mutation.
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


def daily_close(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv"); dtv = pd.to_datetime(df["datetime"])
    return df.assign(d=dtv.dt.normalize()).groupby("d")["close"].last()


def build_trades(cot_sym, px, z_thr=1.5, lag_days=3, horizon=5, cost=0.0006):
    cot = pd.read_csv(ROOT / "data" / "feeds" / "cot.csv", parse_dates=["date"])
    c = cot[cot["sym"] == cot_sym].sort_values("date").copy()
    c["z"] = (c["spec_net"] - c["spec_net"].rolling(52, min_periods=26).mean()) / c["spec_net"].rolling(52, min_periods=26).std()
    c["act"] = c["date"] + pd.Timedelta(days=lag_days)
    pidx = px.index
    rows = []
    for _, r in c.dropna(subset=["z"]).iterrows():
        if abs(r["z"]) < z_thr:
            continue
        fut = pidx[pidx >= r["act"]]
        if len(fut) < horizon + 1:
            continue
        p0, p1 = px.loc[fut[0]], px.loc[fut[horizon]]
        ret = p1 / p0 - 1
        side = -1 if r["z"] > z_thr else 1            # fade spec extreme
        rows.append({"date": r["date"], "year": r["date"].year, "z": r["z"], "side": side, "raw": ret, "pnl": side * ret - cost})
    return pd.DataFrame(rows)


def metrics(t, mnq=None):
    p = t["pnl"].to_numpy(); h = len(p) // 2
    gp = np.sort(p[p > 0])[::-1]; gs = gp.sum() if (p > 0).any() else 1
    yr = t.groupby("year")["pnl"].sum()
    longs = t[t["side"] == 1]["pnl"].to_numpy(); shorts = t[t["side"] == -1]["pnl"].to_numpy()
    m = {"n": len(p), "pf": round(_pf(p), 3), "mean_bps": round(float(p.mean()) * 1e4, 1), "win_pct": round(float((p > 0).mean()) * 100, 1),
         "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
         "max_single_pct": round(float(gp[0]) / gs * 100, 1) if gs > 0 else None, "top3_pct": round(float(gp[:3].sum()) / gs * 100, 1) if gs > 0 else None,
         "long_n": int((t["side"] == 1).sum()), "short_n": int((t["side"] == -1).sum()),
         "long_pf": round(_pf(longs), 3) if len(longs) else None, "short_pf": round(_pf(shorts), 3) if len(shorts) else None,
         "long_mean_bps": round(float(longs.mean()) * 1e4, 1) if len(longs) else None, "short_mean_bps": round(float(shorts.mean()) * 1e4, 1) if len(shorts) else None,
         "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}", "per_year_bps": {int(y): round(float(v)/max(1,(t['year']==y).sum())*1e4, 0) for y, v in yr.items()},
         "worst3_pct": [round(float(x) * 100, 2) for x in np.sort(p)[:3]]}
    if mnq is not None:
        # align JPY-trade pnl to MNQ same-window return (crude: MNQ 5d return over same dates)
        corrs = []
        for _, r in t.iterrows():
            fut = mnq.index[mnq.index >= r["date"] + pd.Timedelta(days=3)]
            if len(fut) >= 6:
                corrs.append((r["pnl"], float(mnq.loc[fut[0]:fut[5]].sum())))
        if len(corrs) > 30:
            a = np.array(corrs); m["corr_to_MNQ"] = round(float(np.corrcoef(a[:, 0], a[:, 1])[0, 1]), 3)
    return m


def run():
    print("Cycle 2026-06-23n — COT-JPY->6J full gate (report-only)\n", flush=True)
    px = daily_close("6J")
    mnq = daily_close("MNQ").pct_change()
    base = build_trades("JPY", px)
    if len(base) < 60:
        print(f"  insufficient events n={len(base)} -> DATA-LIMITED"); return
    m = metrics(base, mnq)
    print("=== PRIMARY (z>1.5, lag=Fri, 1wk fwd, 6bps) ===", flush=True)
    for k in ["n", "pf", "mean_bps", "win_pct", "h1_pf", "h2_pf", "max_single_pct", "top3_pct", "yrs_pos",
              "long_n", "long_pf", "long_mean_bps", "short_n", "short_pf", "short_mean_bps", "corr_to_MNQ", "worst3_pct"]:
        print(f"  {k}: {m.get(k)}", flush=True)
    print(f"  per_year_bps: {m['per_year_bps']}", flush=True)

    print("\n=== ROBUSTNESS ===", flush=True)
    rob = {}
    for label, kw in [("lag_+1wk_conservative", dict(lag_days=7)), ("horizon_2wk", dict(horizon=10)),
                      ("z_thr_2.0", dict(z_thr=2.0)), ("cost_12bps", dict(cost=0.0012))]:
        t = build_trades("JPY", px, **kw)
        if len(t) >= 40:
            mm = metrics(t)
            rob[label] = {"n": mm["n"], "pf": mm["pf"], "mean_bps": mm["mean_bps"], "h1_pf": mm["h1_pf"], "h2_pf": mm["h2_pf"], "yrs_pos": mm["yrs_pos"]}
            print(f"  {label:24s}: n={mm['n']} PF={mm['pf']} mean={mm['mean_bps']}bps H1/H2={mm['h1_pf']}/{mm['h2_pf']} yrs+={mm['yrs_pos']}", flush=True)
        else:
            rob[label] = {"n": len(t), "note": "too few"}; print(f"  {label}: too few (n={len(t)})", flush=True)

    # verdict
    ok = (m["pf"] >= 1.25 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and (m["max_single_pct"] or 99) < 35
          and "0/" not in m["yrs_pos"] and (m["long_pf"] or 0) > 1.0 and (m["short_pf"] or 0) > 1.0
          and rob.get("cost_12bps", {}).get("pf", 0) >= 1.1 and rob.get("lag_+1wk_conservative", {}).get("pf", 0) >= 1.1)
    verdict = "PACKET_CANDIDATE_tail" if ok else ("WATCH_tail" if m["pf"] >= 1.2 and (m["long_pf"] or 0) > 1 and (m["short_pf"] or 0) > 1 else "KILL")
    print(f"\n  VERDICT: {verdict} (both-sides={m['long_pf']}/{m['short_pf']}, cost12={rob.get('cost_12bps',{}).get('pf')}, lag+1wk={rob.get('lag_+1wk_conservative',{}).get('pf')})", flush=True)
    out = {"cycle": "2026-06-23n_cot_jpy_full_gate", "primary": m, "robustness": rob, "verdict": verdict,
           "note": "COT-JPY spec-extreme fade; report-only; sparse/tail archetype; both-sides + cost + lag + per-year gated"}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23n_cot_jpy_full_gate.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nWrote COT-JPY gate JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
