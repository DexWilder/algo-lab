"""Cycle 2026-06-23o — WH batch-3: MOMENTUM / ORB-adjacent / regime-conditioned (report-only).

Operator correction: raw 5m MR is dry; the productive WH family is momentum/continuation/ORB-adjacent/
regime-conditioned. Test that family. Realistic fills (D2 lesson). Predeclared directions, no flips.
  M1 first-hour-range regime -> rest-of-day: narrow FH + directional -> CONTINUATION; wide FH -> exhaustion fade.
  M3 time-of-day momentum: morning drive (09:30->10:00) -> (10:00->11:00) continuation; power-hour (14:00->15:00)
     -> (15:00->16:00) continuation.
  M4 prior-day-level breakout continuation (ORB-adjacent): intraday break of prior-day RTH high/low -> continuation
     to close; intraday first-touch + GAP-AWARE fills (no stop-fill optimism).
Cost 4bps. Report-only; no mutation.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"
COST = 0.0004


def _pf(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]; l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def _verdict(p, pf_pass=1.20):
    p = np.asarray(p, float); p = p[~np.isnan(p)]
    if len(p) < 60:
        return "DATA-LIMITED", {"n": int(len(p))}
    h = len(p) // 2; pf = _pf(p)
    m = {"n": int(len(p)), "pf": round(pf, 3), "mean_bps": round(float(p.mean()) * 1e4, 1), "win_pct": round(float((p > 0).mean()) * 100, 1),
         "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3)}
    v = "STRUCTURE_FOUND" if (pf >= pf_pass and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and m["mean_bps"] > 0) else ("WATCH" if pf >= 1.10 and m["mean_bps"] > 0 else "KILL")
    return v, m


def load5m(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
    dtv = pd.to_datetime(df["datetime"]); df = df.assign(d=dtv.dt.normalize(), t=dtv.dt.strftime("%H:%M"))
    return df[(df["t"] >= "09:30") & (df["t"] <= "15:55")].copy()


def mark(r, hhmm, col="open"):
    return r[r["t"] == hhmm].groupby("d")[col].first()


def run():
    print("Cycle 2026-06-23o — WH batch-3 momentum/ORB-adjacent (report-only)\n", flush=True)
    OUT = {"cycle": "2026-06-23o_mechlib_wh_batch3_momentum", "status": "report-only; momentum family", "screens": {}}
    for sym in ("MNQ", "MES", "MGC"):
        r = load5m(sym)
        day = r.groupby("d").agg(o930=("open", "first"), hi=("high", "max"), lo=("low", "min"), c=("close", "last"))
        o1000 = mark(r, "10:00"); o1100 = mark(r, "11:00"); o1030 = mark(r, "10:30"); o1400 = mark(r, "14:00"); o1500 = mark(r, "15:00")
        # first hour high/low
        fh = r[r["t"] <= "10:25"].groupby("d").agg(fh_hi=("high", "max"), fh_lo=("low", "min"))
        g = day.join([o1000.rename("o1000"), o1100.rename("o1100"), o1030.rename("o1030"), o1400.rename("o1400"), o1500.rename("o1500"), fh]).dropna()

        # M1 first-hour-range regime
        fh_dir = np.sign(g["o1030"] - g["o930"])
        fh_rng = g["fh_hi"] - g["fh_lo"]
        fh_pct = fh_rng.rolling(60, min_periods=30).apply(lambda s: (s <= s.iloc[-1]).mean(), raw=False)
        rest = g["c"] / g["o1030"] - 1
        narrow = fh_pct < 0.33; wide = fh_pct > 0.67
        m1_cont = (fh_dir * rest - COST)[narrow].dropna()        # narrow FH -> continuation
        m1_fade = (-fh_dir * rest - COST)[wide].dropna()         # wide FH -> exhaustion fade
        v, mm = _verdict(m1_cont.values); OUT["screens"][f"M1_FHnarrow_CONT_{sym}"] = {"verdict": v, **mm}
        v, mm = _verdict(m1_fade.values); OUT["screens"][f"M1_FHwide_FADE_{sym}"] = {"verdict": v, **mm}

        # M3 time-of-day momentum
        am_drive = np.sign(g["o1000"] - g["o930"]); am_next = g["o1100"] / g["o1000"] - 1
        m3_am = (am_drive * am_next - COST).dropna()
        m3_am = m3_am[(g["o1000"] / g["o930"] - 1).abs() > (g["o1000"] / g["o930"] - 1).abs().rolling(60, min_periods=30).median()]
        ph_dir = np.sign(g["o1500"] - g["o1400"]); ph_next = g["c"] / g["o1500"] - 1
        m3_ph = (ph_dir * ph_next - COST).dropna()
        m3_ph = m3_ph[(g["o1500"] / g["o1400"] - 1).abs() > (g["o1500"] / g["o1400"] - 1).abs().rolling(60, min_periods=30).median()]
        v, mm = _verdict(m3_am.values); OUT["screens"][f"M3_AMmomentum_{sym}"] = {"verdict": v, **mm}
        v, mm = _verdict(m3_ph.values); OUT["screens"][f"M3_powerhour_{sym}"] = {"verdict": v, **mm}

        # M4 prior-day-level breakout continuation (intraday first-touch + gap-aware fills)
        days = list(day.index); bars = {d: gg for d, gg in r.groupby("d")}
        trades = []
        for i in range(1, len(days)):
            di = days[i]; ph_, pl_ = day["hi"].iloc[i - 1], day["lo"].iloc[i - 1]
            b = bars.get(di)
            if b is None or len(b) == 0:
                continue
            cexit = b["close"].iloc[-1]; side = None; fill = None
            for _, bar in b.iterrows():
                hl = bar["high"] >= ph_; sl = bar["low"] <= pl_
                if hl and sl:
                    if abs(bar["open"] - ph_) <= abs(bar["open"] - pl_): side, fill = "L", max(ph_, bar["open"])
                    else: side, fill = "S", min(pl_, bar["open"])
                    break
                if hl: side, fill = "L", max(ph_, bar["open"]); break
                if sl: side, fill = "S", min(pl_, bar["open"]); break
            if side == "L": trades.append(cexit / fill - 1 - COST)
            elif side == "S": trades.append(fill / cexit - 1 - COST)
        v, mm = _verdict(np.array(trades)); OUT["screens"][f"M4_PDbreakout_CONT_{sym}"] = {"verdict": v, **mm}

    print(f"{'screen':30s} {'verdict':16s} {'n':>6s} {'PF':>6s} {'mean_bps':>9s} {'H1/H2':>13s}", flush=True)
    surv = []
    for k, m in OUT["screens"].items():
        if "pf" in m:
            print(f"{k:30s} {m['verdict']:16s} {m['n']:>6d} {m['pf']:>6.3f} {m['mean_bps']:>9.1f} {str(m['h1_pf'])+'/'+str(m['h2_pf']):>13s}", flush=True)
            if m["verdict"] in ("STRUCTURE_FOUND", "WATCH"): surv.append((k, m["verdict"], m["pf"], m["mean_bps"]))
        else:
            print(f"{k:30s} {m['verdict']:16s} {m.get('n','')}", flush=True)
    print(f"\nSURVIVORS: {surv if surv else 'NONE'}", flush=True)
    OUT["survivors"] = surv
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23o_mechlib_wh_batch3_momentum.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote WH batch-3 JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
