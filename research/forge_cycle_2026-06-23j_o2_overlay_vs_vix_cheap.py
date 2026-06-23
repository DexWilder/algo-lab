"""Cycle 2026-06-23j — O2 CHEAP overlay-vs-VIX screen (report-only).

Operator rules: cheap proxy ONLY (no full ORB regeneration). Question: does DVOL-spike regime help avoid
bad MNQ/MES workhorse days BETTER than VIX-spike / prior-day selloff / realized-vol spike — or is it redundant?
If DVOL does not clearly beat/complement VIX -> close O2 at WATCH/archive and pivot to Mechanism Library.

Workhorse-day PROXY (cheap, long-biased intraday): intraday RTH return open0930->close1600 as a stand-in for
the equity workhorse's daily PnL. (Caveat: true ORB book differs; full regen only if this surprises.)
All filters known BEFORE the trading day (no-lookahead): DVOL z (prior eve), VIX z (prior close),
prior-day close-to-close selloff, realized-vol z (prior). Each filter tested as an AVOIDANCE filter
(skip day if regime ON) + day-separation + opportunity cost + drawdown proxy + filter overlap.
Report-only; no mutation.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def _maxdd(p):
    eq = np.cumsum(p); return float((eq - np.maximum.accumulate(eq)).min())


def rth_daily(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
    dtv = pd.to_datetime(df["datetime"]); df = df.assign(d=dtv.dt.normalize(), t=dtv.dt.strftime("%H:%M"))
    rth = df[(df["t"] >= "09:30") & (df["t"] <= "15:55")]
    op = rth[rth["t"] == "09:30"].groupby("d")["open"].first().rename("open0930")
    cl = rth.groupby("d")["close"].last().rename("close1600")
    g = pd.concat([op, cl], axis=1).dropna()
    g["intraday"] = g["close1600"] / g["open0930"] - 1            # workhorse-day PROXY
    g["cc"] = g["close1600"].pct_change()
    return g


def zser(s, w=120):
    return (s - s.rolling(w, min_periods=60).mean()) / s.rolling(w, min_periods=60).std()


def run():
    print("Cycle 2026-06-23j — O2 cheap overlay-vs-VIX screen (report-only)\n", flush=True)
    dvol = pd.read_csv(ROOT / "data" / "feeds" / "deribit_DVOL_BTC.csv", index_col=0)
    dvol.index = pd.to_datetime(dvol.index).tz_localize(None).normalize(); dvol = dvol.iloc[:, 0]
    dz = zser(dvol).copy(); dz.index = dz.index + pd.Timedelta(days=1); dz = dz.rename("dvolz")
    vix = pd.read_csv(ROOT / "data" / "feeds" / "vix.csv", parse_dates=["date"]).set_index("date")["vix"]
    vz = zser(vix).copy(); vz.index = vz.index + pd.Timedelta(days=1); vz = vz.rename("vixz")

    OUT = {"cycle": "2026-06-23j_o2_overlay_vs_vix_cheap", "proxy": "intraday RTH open0930->close1600 (long-biased workhorse-day proxy)",
           "status": "cheap screen; report-only", "assets": {}}
    for sym in ("MES", "MNQ"):
        g = rth_daily(sym).join(dz).join(vz).dropna(subset=["dvolz", "vixz", "intraday"])
        g["prior_cc"] = g["cc"].shift(1)
        g["rv10"] = g["cc"].rolling(10, min_periods=6).std(); g["rv10z"] = zser(g["rv10"]).shift(1)
        g = g.dropna(subset=["prior_cc", "rv10z"])
        base = g["intraday"].to_numpy()
        base_pf, base_mean = _pf(base), float(base.mean())
        n = len(g)
        filters = {
            "DVOL_spike_z>1.5": (g["dvolz"] > 1.5).to_numpy(),
            "VIX_spike_z>1.5": (g["vixz"] > 1.5).to_numpy(),
            "prior_selloff_cc<-0.7%": (g["prior_cc"] < -0.007).to_numpy(),
            "RV_spike_z>1.5": (g["rv10z"] > 1.5).to_numpy(),
        }
        A = {"n_days": n, "baseline_all_days": {"pf": round(base_pf, 3), "mean_bps": round(base_mean * 1e4, 1),
             "neg_day_share_pct": round(float((base < 0).mean()) * 100, 1), "maxdd_pct": round(_maxdd(base) * 100, 1)}}
        res = {}
        for fn, on in filters.items():
            on_ret, off_ret = base[on], base[~on]
            if len(on_ret) < 20:
                res[fn] = {"n_on": int(on.sum()), "note": "too few"}; continue
            # avoidance filter = trade only OFF days
            retained_pf = _pf(off_ret); retained_mean = float(off_ret.mean())
            res[fn] = {
                "n_on": int(on.sum()), "pct_days_flagged": round(float(on.mean()) * 100, 1),
                "mean_ON_bps": round(float(on_ret.mean()) * 1e4, 1), "mean_OFF_bps": round(float(off_ret.mean()) * 1e4, 1),
                "separation_OFF_minus_ON_bps": round((float(off_ret.mean()) - float(on_ret.mean())) * 1e4, 1),
                "ON_neg_share_pct": round(float((on_ret < 0).mean()) * 100, 1),
                "retained_pf": round(retained_pf, 3), "retained_mean_bps": round(retained_mean * 1e4, 1),
                "pf_lift_vs_base": round(retained_pf - base_pf, 3), "mean_lift_vs_base_bps": round((retained_mean - base_mean) * 1e4, 1),
                "opp_cost_trades_removed": int(on.sum()), "retained_maxdd_pct": round(_maxdd(off_ret) * 100, 1),
                "maxdd_improve_pct": round((_maxdd(off_ret) - _maxdd(base)) * 100, 1),
            }
        A["filters"] = res
        # overlap (Jaccard) between filter ON-sets
        ov = {}
        for a, b in combinations(filters, 2):
            ia, ib = filters[a], filters[b]
            inter = float((ia & ib).sum()); union = float((ia | ib).sum())
            ov[f"{a} ∩ {b}"] = round(inter / union, 3) if union else 0.0
        A["filter_overlap_jaccard"] = ov
        OUT["assets"][sym] = A

        print(f"=== {sym} (n={n}) baseline intraday PF={A['baseline_all_days']['pf']} mean={A['baseline_all_days']['mean_bps']}bps maxDD={A['baseline_all_days']['maxdd_pct']}% ===", flush=True)
        for fn, r in res.items():
            if "note" in r:
                print(f"  {fn:24s}: {r['note']}"); continue
            print(f"  {fn:24s}: flags {r['pct_days_flagged']}% | sep(OFF-ON)={r['separation_OFF_minus_ON_bps']:+.1f}bps | "
                  f"retained PF={r['retained_pf']} (lift {r['pf_lift_vs_base']:+.3f}) mean_lift={r['mean_lift_vs_base_bps']:+.1f}bps DDimprove={r['maxdd_improve_pct']:+.1f}%", flush=True)
        print(f"  overlap: {ov}\n", flush=True)

    # verdict: does DVOL beat VIX on bad-day avoidance?
    print("=== VERDICT: DVOL vs VIX as workhorse-day overlay ===", flush=True)
    close = True
    for sym in ("MES", "MNQ"):
        d = OUT["assets"][sym]["filters"].get("DVOL_spike_z>1.5", {})
        v = OUT["assets"][sym]["filters"].get("VIX_spike_z>1.5", {})
        dvol_beats = (d.get("pf_lift_vs_base", -9) > v.get("pf_lift_vs_base", 9)) and d.get("pf_lift_vs_base", -9) > 0
        print(f"  {sym}: DVOL PF-lift={d.get('pf_lift_vs_base')} sep={d.get('separation_OFF_minus_ON_bps')}bps | "
              f"VIX PF-lift={v.get('pf_lift_vs_base')} sep={v.get('separation_OFF_minus_ON_bps')}bps -> DVOL beats VIX: {dvol_beats}", flush=True)
        if dvol_beats:
            close = False
    OUT["verdict"] = ("CLOSE_O2_AT_WATCH — DVOL redundant/weaker vs VIX as overlay; pivot to Mechanism Library"
                      if close else "DVOL surprises as overlay — escalate to full ORB-regeneration overlay test")
    print(f"\n  -> {OUT['verdict']}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23j_o2_overlay_vs_vix_cheap.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote cheap-overlay JSON.\n(report-only; no mutation; no ORB regen)", flush=True)


if __name__ == "__main__":
    run()
