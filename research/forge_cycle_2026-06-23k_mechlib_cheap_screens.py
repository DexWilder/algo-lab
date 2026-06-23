"""Cycle 2026-06-23k — Mechanism Library cheap screens, batch 1 (report-only).

Velocity mandate: H5 (weekly COT) + DAILY-cadence Harris microstructure WH candidates. Fast falsification only;
NO full build unless a screen earns it. No post-hoc direction flips (predeclared below). Archive KILLs.

DAILY WH candidates (priority — we need daily workhorse cadence):
  D1 stop-run / liquidity-sweep reversal: sweep prior-day extreme then close back inside -> fade next day.
  D2 range-compression -> expansion (NR7): narrow-range day -> next-day breakout continuation from prior range.
  D3 opening-drive continuation: 09:30->10:00 drive sign -> rest-of-day (10:00->16:00) continuation.
  D4 MOC/closing-imbalance overnight reversal: last-30min (15:30->16:00) move -> overnight (16:00->09:30) reversal.
WEEKLY: H5 COT positioning-extreme reversal: spec_net z-extreme -> fade (long/short), forward ~1wk. COT lagged
  Tue->Fri release (no-lookahead).
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


def _verdict(p, pf_pass=1.20, beat_cost_pf=1.12):
    p = np.asarray(p, float); p = p[~np.isnan(p)]
    if len(p) < 40:
        return "DATA-LIMITED", {}
    h = len(p) // 2; pf = _pf(p)
    m = {"n": len(p), "pf": round(pf, 3), "mean_bps": round(float(p.mean()) * 1e4, 1), "win_pct": round(float((p > 0).mean()) * 100, 1),
         "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3)}
    if pf >= pf_pass and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and m["mean_bps"] > 0:
        return "STRUCTURE_FOUND", m
    if pf >= beat_cost_pf and m["mean_bps"] > 0:
        return "WATCH", m
    return "KILL", m


def rth_bars(sym):
    """5m ET -> per-day RTH OHLC + intraday marks (09:30, 10:00, 15:30, 16:00) + overnight to next 09:30."""
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
    dtv = pd.to_datetime(df["datetime"]); df = df.assign(d=dtv.dt.normalize(), t=dtv.dt.strftime("%H:%M"))
    rth = df[(df["t"] >= "09:30") & (df["t"] <= "15:55")]
    o = rth.groupby("d").agg(o930=("open", "first"), hi=("high", "max"), lo=("low", "min"), c=("close", "last"))
    mark = lambda hhmm: rth[rth["t"] == hhmm].groupby("d")["open"].first()
    o["m1000"] = mark("10:00"); o["m1530"] = mark("15:30")
    o["c_next_open"] = o["o930"].shift(-1)
    return o.dropna(subset=["o930", "hi", "lo", "c"])


def daily_close(sym):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
    dtv = pd.to_datetime(df["datetime"])
    return df.assign(d=dtv.dt.normalize()).groupby("d")["close"].last()


COST = 0.0004   # 4bps round-trip, micro futures intraday


def run():
    print("Cycle 2026-06-23k — Mechanism Library cheap screens batch 1 (report-only)\n", flush=True)
    OUT = {"cycle": "2026-06-23k_mechlib_cheap_screens", "status": "fast falsification; report-only", "screens": {}}

    # ---------- DAILY WH candidates ----------
    for sym in ("MNQ", "MES", "MGC"):
        g = rth_bars(sym)
        ph, pl, pc = g["hi"].shift(1), g["lo"].shift(1), g["c"].shift(1)
        prng = (g["hi"].shift(1) - g["lo"].shift(1))

        # D1 stop-run reversal: failed sweep of prior extreme
        fail_hi = (g["hi"] > ph) & (g["c"] < ph)         # poked above prior high, closed back below -> short next
        fail_lo = (g["lo"] < pl) & (g["c"] > pl)         # poked below prior low, closed back above -> long next
        nxt = g["c"].pct_change().shift(-1)              # next-day close-to-close
        d1 = pd.concat([(-nxt[fail_hi] - COST), (nxt[fail_lo] - COST)]).dropna()
        v, m = _verdict(d1.values); OUT["screens"][f"D1_stoprun_{sym}"] = {"verdict": v, **m, "n_fail_hi": int(fail_hi.sum()), "n_fail_lo": int(fail_lo.sum())}

        # D2 NR7 expansion breakout: after narrowest-range-of-7 day, trade breakout of that day's range, exit close
        rng = g["hi"] - g["lo"]
        nr7 = rng <= rng.rolling(7).min()
        bl = nr7.shift(1) & (g["hi"] > g["hi"].shift(1))   # broke above NR-day high -> long, entry=NR high, exit=close
        bs = nr7.shift(1) & (g["lo"] < g["lo"].shift(1))   # broke below NR-day low -> short
        long_pnl = (g["c"] - g["hi"].shift(1)) / g["hi"].shift(1)
        short_pnl = (g["lo"].shift(1) - g["c"]) / g["lo"].shift(1)
        d2 = pd.concat([(long_pnl[bl & ~bs] - COST), (short_pnl[bs & ~bl] - COST)]).dropna()
        v, m = _verdict(d2.values); OUT["screens"][f"D2_NRbreakout_{sym}"] = {"verdict": v, **m, "n": len(d2)}

        # D3 opening-drive continuation: 09:30->10:00 drive -> 10:00->16:00 continuation
        drive = (g["m1000"] / g["o930"] - 1)
        rest = (g["c"] / g["m1000"] - 1)
        dirn = np.sign(drive)
        d3 = (dirn * rest - COST).dropna()
        d3 = d3[drive.abs() > drive.abs().rolling(60, min_periods=30).median()]   # only meaningful drives
        v, m = _verdict(d3.values); OUT["screens"][f"D3_opendrive_{sym}"] = {"verdict": v, **m}

        # D4 MOC overnight reversal: 15:30->16:00 move -> overnight reversal
        late = (g["c"] / g["m1530"] - 1)
        on = (g["c_next_open"] / g["c"] - 1)
        d4 = (-np.sign(late) * on - COST).dropna()
        d4 = d4[late.abs() > late.abs().rolling(60, min_periods=30).median()]
        v, m = _verdict(d4.values); OUT["screens"][f"D4_MOCreversal_{sym}"] = {"verdict": v, **m}

    # ---------- WEEKLY: H5 COT positioning extreme ----------
    cot = pd.read_csv(ROOT / "data" / "feeds" / "cot.csv", parse_dates=["date"])
    cmap = {"GOLD": "MGC", "CRUDE": "MCL", "EUR": "6E", "JPY": "6J", "SP500": "MES"}
    for csym, asym in cmap.items():
        try:
            px = daily_close(asym)
        except FileNotFoundError:
            OUT["screens"][f"H5_COT_{csym}->{asym}"] = {"verdict": "DATA-LIMITED", "note": "no price file"}; continue
        c = cot[cot["sym"] == csym].sort_values("date").copy()
        if len(c) < 80:
            OUT["screens"][f"H5_COT_{csym}->{asym}"] = {"verdict": "DATA-LIMITED", "n": len(c)}; continue
        c["z"] = (c["spec_net"] - c["spec_net"].rolling(52, min_periods=26).mean()) / c["spec_net"].rolling(52, min_periods=26).std()
        c["act_date"] = c["date"] + pd.Timedelta(days=3)      # COT Tue snapshot released ~Fri (no-lookahead lag)
        pxd = px.copy(); pxd.index = pd.to_datetime(pxd.index)
        # forward ~1wk (5 trading-day) return from first price on/after act_date
        rows = []
        pidx = pxd.index
        for _, r in c.dropna(subset=["z"]).iterrows():
            if abs(r["z"]) < 1.5:
                continue
            fut = pidx[pidx >= r["act_date"]]
            if len(fut) < 6:
                continue
            p0 = pxd.loc[fut[0]]; p1 = pxd.loc[fut[5]]
            ret = p1 / p0 - 1
            dirn = -1 if r["z"] > 1.5 else 1                  # fade spec extreme
            rows.append(dirn * ret - 0.0006)
        v, m = _verdict(np.array(rows), pf_pass=1.25, beat_cost_pf=1.10)
        OUT["screens"][f"H5_COT_{csym}->{asym}"] = {"verdict": v, **m, "n_events": len(rows)}

    # ---------- print ----------
    print(f"{'screen':28s} {'verdict':16s} {'n':>5s} {'PF':>6s} {'mean_bps':>9s} {'H1/H2':>12s}", flush=True)
    survivors = []
    for k, r in OUT["screens"].items():
        if "pf" in r:
            print(f"{k:28s} {r['verdict']:16s} {r.get('n', 0):>5d} {r['pf']:>6.3f} {r['mean_bps']:>9.1f} {str(r['h1_pf'])+'/'+str(r['h2_pf']):>12s}", flush=True)
            if r["verdict"] in ("STRUCTURE_FOUND", "WATCH"):
                survivors.append((k, r["verdict"], r["pf"], r["mean_bps"]))
        else:
            print(f"{k:28s} {r['verdict']:16s}   {r.get('note', '')}", flush=True)
    print(f"\nSURVIVORS (WATCH/STRUCTURE_FOUND): {survivors if survivors else 'NONE — all KILL/DATA-LIMITED'}", flush=True)
    OUT["survivors"] = survivors
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23k_mechlib_cheap_screens.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote batch-1 cheap-screen JSON.\n(report-only; no mutation; fast falsification)", flush=True)


if __name__ == "__main__":
    run()
