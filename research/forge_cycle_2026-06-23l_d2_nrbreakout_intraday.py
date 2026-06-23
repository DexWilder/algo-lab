"""Cycle 2026-06-23l — D2 NR-breakout PROPER intraday first-touch reconstruction (report-only).

Batch-1 daily-OHLC D2 was CONSTRUCTION-INVALID (lookahead: used T+1 realized high/low to pick long-vs-short
direction; PF 7-75 artifact). Proper test: on the day AFTER a narrow-range (NR7) day, place stop-entries at
the NR-day high (long) and low (short); whichever is touched FIRST chronologically (via 5m bars) is the trade;
exit at RTH close. Includes failed breakouts that reverse (real losers). No lookahead. Cost 4bps.
Predeclared: breakout-continuation (long on up-break, short on down-break). NO flip to fade if it fails.
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


def run():
    print("Cycle 2026-06-23l — D2 NR-breakout intraday first-touch (report-only)\n", flush=True)
    OUT = {"cycle": "2026-06-23l_d2_nrbreakout_intraday", "status": "report-only; proper no-lookahead recon", "assets": {}}
    for sym in ("MNQ", "MES", "MGC"):
        df = pd.read_csv(ROOT / "data" / "processed" / f"{sym}_5m.csv")
        dtv = pd.to_datetime(df["datetime"]); df = df.assign(d=dtv.dt.normalize(), t=dtv.dt.strftime("%H:%M"))
        rth = df[(df["t"] >= "09:30") & (df["t"] <= "15:55")].copy()
        day = rth.groupby("d").agg(hi=("high", "max"), lo=("low", "min"), c=("close", "last"))
        rng = day["hi"] - day["lo"]; nr7 = (rng <= rng.rolling(7).min())
        days = list(day.index)
        bars_by_day = {d: g for d, g in rth.groupby("d")}
        trades = []
        for i in range(len(days) - 1):
            di, dn = days[i], days[i + 1]
            if not bool(nr7.loc[di]):
                continue
            eh, el = day["hi"].loc[di], day["lo"].loc[di]
            b = bars_by_day.get(dn)
            if b is None or len(b) == 0:
                continue
            cexit = b["close"].iloc[-1]
            # first-touch in chronological order; REALISTIC fill = gapped open if bar opens past the level
            side, fill = None, None
            for _, bar in b.iterrows():
                hit_long = bar["high"] >= eh
                hit_short = bar["low"] <= el
                if hit_long and hit_short:                 # same bar both -> ambiguous, use open proximity
                    if abs(bar["open"] - eh) <= abs(bar["open"] - el):
                        side, fill = "L", max(eh, bar["open"])
                    else:
                        side, fill = "S", min(el, bar["open"])
                    break
                if hit_long:
                    side, fill = "L", max(eh, bar["open"]); break   # gap-through -> fill at open, not stop
                if hit_short:
                    side, fill = "S", min(el, bar["open"]); break
            if side == "L":
                trades.append(("L", cexit / fill - 1 - 0.0004, di.year))
            elif side == "S":
                trades.append(("S", fill / cexit - 1 - 0.0004, di.year))
            # neither touched -> no trade
        if len(trades) < 40:
            OUT["assets"][sym] = {"verdict": "DATA-LIMITED", "n": len(trades)}
            print(f"  {sym}: n={len(trades)} DATA-LIMITED", flush=True); continue
        p = np.array([t[1] for t in trades]); h = len(p) // 2
        yr = pd.Series(p, index=[t[2] for t in trades]).groupby(level=0).sum()
        nlong = sum(1 for t in trades if t[0] == "L"); nshort = len(trades) - nlong
        longp = np.array([t[1] for t in trades if t[0] == "L"]); shortp = np.array([t[1] for t in trades if t[0] == "S"])
        m = {"n": len(p), "pf": round(_pf(p), 3), "mean_bps": round(float(p.mean()) * 1e4, 1), "win_pct": round(float((p > 0).mean()) * 100, 1),
             "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
             "long_pf": round(_pf(longp), 3) if len(longp) else None, "short_pf": round(_pf(shortp), 3) if len(shortp) else None,
             "n_long": nlong, "n_short": nshort, "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}",
             "pf_8bps": round(_pf(p + 0.0004 - 0.0008), 3), "max_single_pct": round(float(np.sort(p[p>0])[::-1][0]) / p[p>0].sum() * 100, 1) if (p>0).any() else None}
        ok = m["pf"] >= 1.2 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and (m["long_pf"] or 0) > 1.0 and (m["short_pf"] or 0) > 1.0 and m["pf_8bps"] >= 1.1
        m["verdict"] = "STRUCTURE_FOUND" if ok else ("WATCH" if m["pf"] >= 1.15 and m["mean_bps"] > 0 else "KILL")
        OUT["assets"][sym] = m
        print(f"  {sym}: n={m['n']} (L{nlong}/S{nshort}) PF={m['pf']} mean={m['mean_bps']}bps win={m['win_pct']}% H1/H2={m['h1_pf']}/{m['h2_pf']} "
              f"long_pf={m['long_pf']} short_pf={m['short_pf']} yrs+={m['yrs_pos']} PF@8bps={m['pf_8bps']} maxsingle={m['max_single_pct']}% -> {m['verdict']}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23l_d2_nrbreakout_intraday.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote D2-intraday JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
