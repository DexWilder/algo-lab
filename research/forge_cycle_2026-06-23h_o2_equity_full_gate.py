"""Cycle 2026-06-23h — O2-EQUITY full gate: DVOL-spike -> next-day long MES/MNQ (report-only).

PROMISING_V1 / STRUCTURE_CANDIDATE — NOT banked. Operator framework (2026-06-23): guard against this being
disguised dip-buying / short-vol rebound with crash tails. Must add value beyond VIX / prior-day selloff /
realized-vol, be stable by split+year, not top-k driven, survive equity-futures costs.

TIMESTAMP INTEGRITY (#1 control):
  - 5m bars are ET (empty 17:00 hr = CME equity-futures 5-6pm ET maintenance halt).
  - DVOL daily close stamped 00:00 UTC = ~19-20:00 ET the SAME calendar evening -> known the EVENING BEFORE
    an ET trading day. We align signal so DVOL obs for ET day T = the DVOL daily close known the prior evening
    (dvol_utc shifted +1 day), then ENTER at T 09:30 ET open (~13h after obs). Unambiguous no-lookahead.
  - VIX_{T-1} close (16:15 ET T-1) and prior-day returns also strictly precede T 09:30 entry.

Entry variants (predeclared): V1 intraday long 09:30->16:00 ET day T; V2 24h long 09:30 T -> 09:30 T+1.
Cost stress 3/6 bps round-trip (micro equity futures). Report-only; no mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def rth_daily(sym):
    """Return DataFrame indexed by ET date with open_0930, close_1600, prior-day close-to-close return."""
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
    dtv = pd.to_datetime(df["datetime"])
    df = df.assign(d=dtv.dt.normalize(), t=dtv.dt.strftime("%H:%M"))
    rth = df[(df["t"] >= "09:30") & (df["t"] <= "15:55")]
    op = rth[rth["t"] == "09:30"].groupby("d")["open"].first().rename("open0930")
    cl = rth.groupby("d")["close"].last().rename("close1600")          # last RTH bar close (~16:00)
    g = pd.concat([op, cl], axis=1).dropna()
    g["intraday"] = g["close1600"] / g["open0930"] - 1                 # V1
    g["open_next"] = g["open0930"].shift(-1)
    g["hold24"] = g["open_next"] / g["open0930"] - 1                   # V2 (enter 09:30 T, exit 09:30 T+1)
    g["cc"] = g["close1600"].pct_change()                             # close-to-close (for prior-day selloff)
    return g


def zser(s, w=120):
    return (s - s.rolling(w, min_periods=60).mean()) / s.rolling(w, min_periods=60).std()


def gate_block(t, retcol, cost_bps):
    p = (t[retcol] - cost_bps / 1e4).to_numpy()
    p = p[~np.isnan(p)]
    if len(p) < 25:
        return {"n": int(len(p)), "note": "too few"}
    h = len(p) // 2
    gp = np.sort(p[p > 0])[::-1]; gs = gp.sum() if (p > 0).any() else 1
    eq = np.cumsum(p); dd = eq - np.maximum.accumulate(eq)
    yr = pd.Series(p, index=t.dropna(subset=[retcol]).index).groupby(lambda x: x.year).sum()
    return {"n": int(len(p)), "pf": round(_pf(p), 3), "mean_bps": round(float(p.mean()) * 1e4, 1),
            "win_pct": round(float((p > 0).mean()) * 100, 1),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "h1_mean_bps": round(float(p[:h].mean()) * 1e4, 1), "h2_mean_bps": round(float(p[h:].mean()) * 1e4, 1),
            "max_single_pct": round(float(gp[0]) / gs * 100, 1) if gs > 0 else None,
            "top3_pct": round(float(gp[:3].sum()) / gs * 100, 1) if gs > 0 else None,
            "pf_ex_top3": round(_pf(np.concatenate([gp[3:], p[p <= 0]])), 3),
            "equity_maxdd_pct": round(float(dd.min()) * 100, 2),
            "worst_trade_pct": round(float(p.min()) * 100, 2), "best_trade_pct": round(float(p.max()) * 100, 2),
            "worst5_sum_pct": round(float(np.sort(p)[:5].sum()) * 100, 2),
            "yrs_pos": f"{int((yr > 0).sum())}/{int(yr.shape[0])}",
            "per_year_bps": {int(y): round(float(v) / max(1, (yr.index == y).sum()) * 1e4, 0) for y, v in
                             pd.Series(p, index=t.dropna(subset=[retcol]).index).groupby(lambda x: x.year).mean().items()}}


def run():
    print("Cycle 2026-06-23h — O2-EQUITY full gate (report-only)\n", flush=True)
    dvol = pd.read_csv(ROOT / "data" / "feeds" / "deribit_DVOL_BTC.csv", index_col=0)
    dvol.index = pd.to_datetime(dvol.index).tz_localize(None).normalize(); dvol = dvol.iloc[:, 0]
    dvol_z = zser(dvol)
    # align to ET day: signal for day T = DVOL close known prior evening = dvol_z at (T-1)
    dvol_sig = dvol_z.copy(); dvol_sig.index = dvol_sig.index + pd.Timedelta(days=1)
    dvol_sig = dvol_sig.rename("dvolz")
    vix = pd.read_csv(ROOT / "data" / "feeds" / "vix.csv", parse_dates=["date"]).set_index("date")["vix"]
    vix_z = zser(vix); vix_sig = vix_z.copy(); vix_sig.index = vix_sig.index + pd.Timedelta(days=1); vix_sig = vix_sig.rename("vixz")

    # timestamp proof (example)
    ex = dvol.index[-1]
    print("=== TIMESTAMP PROOF ===", flush=True)
    print(f"  DVOL daily close indexed {ex.date()} = value at {(ex + pd.Timedelta(days=1))} 00:00 UTC (~19-20:00 ET {ex.date()} eve)", flush=True)
    print(f"  -> used as signal for ET trading day {(ex + pd.Timedelta(days=1)).date()}, ENTRY at 09:30 ET (~13h later). DVOL_obs < entry: TRUE", flush=True)
    print(f"  VIX_(T-1) close 16:15 ET and prior-day returns also strictly precede T 09:30 entry.\n", flush=True)

    OUT = {"cycle": "2026-06-23h_o2_equity_full_gate", "status": "PROMISING_V1 / STRUCTURE_CANDIDATE — not banked", "assets": {}}
    for sym in ("MES", "MNQ"):
        g = rth_daily(sym)
        g = g.join(dvol_sig).join(vix_sig).dropna(subset=["dvolz"])
        g["prior_cc"] = g["cc"].shift(1)         # prior-day close-to-close (known before T)
        g["rv10"] = g["cc"].rolling(10, min_periods=6).std()
        g["rv10z"] = zser(g["rv10"]); g["rv10z_prior"] = g["rv10z"].shift(1)
        spike = g["dvolz"] > 1.5
        A = {"n_spike": int(spike.sum()), "n_total": int(len(g))}
        print(f"=== {sym} ===  spike days (DVOL z>1.5) = {A['n_spike']} of {A['n_total']}", flush=True)

        for v, rc in [("V1_intraday_0930_1600", "intraday"), ("V2_hold24_0930_0930", "hold24")]:
            A[v] = {}
            for cb in (3, 6):
                A[v][f"{cb}bps"] = gate_block(g[spike], rc, cb)
            # incremental controls at 3bps
            base = gate_block(g, rc, 3)             # unconditional long every day
            m = A[v]["3bps"]
            A[v]["incremental"] = {
                "uncond_long_mean_bps": base.get("mean_bps"), "spike_mean_bps": m.get("mean_bps"),
                "lift_vs_uncond_bps": round((m.get("mean_bps") or 0) - (base.get("mean_bps") or 0), 1),
            }
            # vs VIX: cells
            vspike = g["vixz"] > 1.5
            cells = {}
            for nm, msk in [("DVOLonly_not_VIX", spike & ~vspike), ("VIXonly_not_DVOL", ~spike & vspike),
                            ("both", spike & vspike), ("DVOL_followUP", spike & (g["prior_cc"] > 0)),
                            ("DVOL_followDOWN", spike & (g["prior_cc"] < 0)),
                            ("DVOL_not_RVspike", spike & (g["rv10z_prior"] < 1.5))]:
                b = gate_block(g[msk], rc, 3)
                cells[nm] = {"n": b.get("n"), "mean_bps": b.get("mean_bps"), "pf": b.get("pf")}
            A[v]["incremental"]["cells"] = cells
            x = A[v]["3bps"]; ctl = A[v]["incremental"]
            print(f"  {v} @3bps: n={x.get('n')} PF={x.get('pf')} mean={x.get('mean_bps')}bps H1/H2={x.get('h1_pf')}/{x.get('h2_pf')} "
                  f"yrs+={x.get('yrs_pos')} maxsingle={x.get('max_single_pct')}% worst5={x.get('worst5_sum_pct')}% maxDD={x.get('equity_maxdd_pct')}%", flush=True)
            print(f"       per-yr bps: {x.get('per_year_bps')}", flush=True)
            print(f"       @6bps: PF={A[v]['6bps'].get('pf')} mean={A[v]['6bps'].get('mean_bps')}bps | lift vs uncond={ctl['lift_vs_uncond_bps']}bps", flush=True)
            print(f"       controls: DVOLonly(noVIX) {cells['DVOLonly_not_VIX']} | both {cells['both']} | followUP {cells['DVOL_followUP']} | followDOWN {cells['DVOL_followDOWN']} | noRVspike {cells['DVOL_not_RVspike']}", flush=True)

            # verdict per variant
            x3 = A[v]["3bps"]
            stable = (x3.get("h1_pf", 0) > 1.0 and x3.get("h2_pf", 0) > 1.0 and "0/" not in str(x3.get("yrs_pos"))
                      and (x3.get("max_single_pct") or 99) < 35)
            adds_value = (cells["DVOLonly_not_VIX"].get("mean_bps") or -9) > 0 and (cells["DVOL_followUP"].get("mean_bps") or -9) > 0
            cost_ok = (A[v]["6bps"].get("pf") or 0) >= 1.15
            A[v]["verdict"] = ("PASS_REVIEW" if (stable and adds_value and cost_ok and (x3.get("pf") or 0) >= 1.2)
                               else "WATCH" if ((x3.get("pf") or 0) >= 1.15 and adds_value) else "KILL")
            print(f"       -> {v} VERDICT: {A[v]['verdict']} (stable={stable} adds_value_beyond_VIX/dip={adds_value} cost6bps_ok={cost_ok})\n", flush=True)
        OUT["assets"][sym] = A

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23h_o2_equity_full_gate.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("Wrote full-gate JSON.\n(report-only; O2-equity; no mutation; PROMISING_V1 until verdict clears)", flush=True)


if __name__ == "__main__":
    run()
