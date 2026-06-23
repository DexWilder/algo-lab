"""Cycle 2026-06-23m — Mechanism Library WH batch-2: Lehalle class-A daily candidates (report-only).

Top of the protected class-A WH queue. Fast falsification, intraday, REALISTIC fills (D2 lesson: no stop-fill
optimism — enter/exit at bar close). No direction flips (predeclared).
  L2 VWAP-deviation reversion: price >Nσ from session VWAP -> fade over next 60min.
  L1 large-print impact reversion: volume-z spike + large-range bar -> fade the bar over next 60min.
  L5 overnight-gap fade/follow: gap small -> fade toward prior close; gap large -> follow. (open->close, daily.)
Cost 4bps round-trip. Report-only; no mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"
COST = 0.0004
HORIZON = 12   # 12 x 5m = 60 min


def _pf(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]; l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def _verdict(p, pf_pass=1.20):
    p = np.asarray(p, float); p = p[~np.isnan(p)]
    if len(p) < 60:
        return "DATA-LIMITED", {"n": int(len(p))}
    h = len(p) // 2; pf = _pf(p)
    m = {"n": int(len(p)), "pf": round(pf, 3), "mean_bps": round(float(p.mean()) * 1e4, 2), "win_pct": round(float((p > 0).mean()) * 100, 1),
         "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3)}
    if pf >= pf_pass and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and m["mean_bps"] > 0:
        v = "STRUCTURE_FOUND"
    elif pf >= 1.10 and m["mean_bps"] > 0:
        v = "WATCH"
    else:
        v = "KILL"
    return v, m


def load5m(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
    dtv = pd.to_datetime(df["datetime"]); df = df.assign(d=dtv.dt.normalize(), t=dtv.dt.strftime("%H:%M"))
    return df[(df["t"] >= "09:30") & (df["t"] <= "15:55")].copy()


def run():
    print("Cycle 2026-06-23m — WH batch-2 Lehalle class-A (report-only)\n", flush=True)
    OUT = {"cycle": "2026-06-23m_mechlib_wh_batch2", "status": "report-only; fast falsification; realistic fills", "screens": {}}
    for sym in ("MNQ", "MES", "MGC"):
        r = load5m(sym)
        r["yr"] = pd.to_datetime(r["d"]).dt.year
        # within-day forward return (close now -> close +HORIZON, not crossing day)
        r["fwd"] = r.groupby("d")["close"].transform(lambda s: s.shift(-HORIZON) / s - 1)

        # ---- L2 VWAP-deviation reversion ----
        def vwap_dev(grp):
            typ = (grp["high"] + grp["low"] + grp["close"]) / 3
            vw = (typ * grp["volume"]).cumsum() / grp["volume"].cumsum().replace(0, np.nan)
            dev = grp["close"] / vw - 1
            z = dev / dev.rolling(20, min_periods=8).std()
            return z
        r["vwap_z"] = r.groupby("d", group_keys=False).apply(vwap_dev)
        bar_in_day = r.groupby("d").cumcount()
        m2 = (bar_in_day >= 8) & (bar_in_day <= 60)        # mid-session, after warmup, leave room for horizon
        long_l2 = m2 & (r["vwap_z"] < -2)
        short_l2 = m2 & (r["vwap_z"] > 2)
        l2 = pd.concat([(r["fwd"][long_l2] - COST), (-r["fwd"][short_l2] - COST)]).dropna()
        v, mm = _verdict(l2.values); OUT["screens"][f"L2_VWAPrev_{sym}"] = {"verdict": v, **mm, "n_long": int(long_l2.sum()), "n_short": int(short_l2.sum())}

        # ---- L1 large-print impact reversion ----
        r["volz"] = r.groupby("d")["volume"].transform(lambda s: (s - s.rolling(20, min_periods=8).mean()) / s.rolling(20, min_periods=8).std())
        r["barret"] = r["close"] / r["open"] - 1
        r["rangez"] = r.groupby("d").apply(lambda g: ((g["high"] - g["low"]) / ((g["high"] - g["low"]).rolling(20, min_periods=8).mean()))).reset_index(level=0, drop=True)
        spike = m2 & (r["volz"] > 2) & (r["rangez"] > 1.5)
        l1 = (-np.sign(r["barret"]) * r["fwd"] - COST)[spike].dropna()
        v, mm = _verdict(l1.values); OUT["screens"][f"L1_impactrev_{sym}"] = {"verdict": v, **mm, "n_signals": int(spike.sum())}

        # ---- L5 overnight gap fade/follow (daily) ----
        day = r.groupby("d").agg(o930=("open", "first"), c1600=("close", "last"))
        day["prev_c"] = day["c1600"].shift(1)
        day["gap"] = day["o930"] / day["prev_c"] - 1
        day["o2c"] = day["c1600"] / day["o930"] - 1
        day = day.dropna(subset=["gap", "o2c"])
        gz = (day["gap"] - day["gap"].rolling(60, min_periods=30).mean()) / day["gap"].rolling(60, min_periods=30).std()
        small = gz.abs() <= 1.0; large = gz.abs() >= 2.0
        # small gap -> fade (position = -sign(gap), profit if o2c moves back); large -> follow (+sign(gap))
        fade = (-np.sign(day["gap"]) * day["o2c"] - COST)[small].dropna()
        follow = (np.sign(day["gap"]) * day["o2c"] - COST)[large].dropna()
        v, mm = _verdict(fade.values); OUT["screens"][f"L5gap_smallFADE_{sym}"] = {"verdict": v, **mm}
        v, mm = _verdict(follow.values); OUT["screens"][f"L5gap_largeFOLLOW_{sym}"] = {"verdict": v, **mm}

    print(f"{'screen':28s} {'verdict':16s} {'n':>6s} {'PF':>6s} {'mean_bps':>9s} {'H1/H2':>13s}", flush=True)
    surv = []
    for k, m in OUT["screens"].items():
        if "pf" in m:
            print(f"{k:28s} {m['verdict']:16s} {m['n']:>6d} {m['pf']:>6.3f} {m['mean_bps']:>9.2f} {str(m['h1_pf'])+'/'+str(m['h2_pf']):>13s}", flush=True)
            if m["verdict"] in ("STRUCTURE_FOUND", "WATCH"):
                surv.append((k, m["verdict"], m["pf"], m["mean_bps"]))
        else:
            print(f"{k:28s} {m['verdict']:16s} {m.get('n','')}", flush=True)
    print(f"\nSURVIVORS: {surv if surv else 'NONE — all KILL/DATA-LIMITED'}", flush=True)
    OUT["survivors"] = surv
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23m_mechlib_wh_batch2.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote WH batch-2 JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
