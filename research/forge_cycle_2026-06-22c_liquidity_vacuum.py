"""Cycle 2026-06-22c — Option A: liquidity-vacuum-release (conditional microstructure, report-only).

Genuinely-different class (NOT unconditional drift, NOT a generic entry already killed in 16p/16q).
Structural 'who-is-forced': the intraday LIQUIDITY VACUUM (lowest-volume hour = midday/session-handoff)
compresses range; when liquidity returns the break of the vacuum range runs (repositioning). CONDITIONAL:
only fires when the vacuum-hour range is COMPRESSED vs its own trailing median. Reachable, non-MNQ/non-gold
(MCL/ZN/ZF/M2K + MES bench). Vacuum window identified EMPIRICALLY per instrument (lowest median-volume
active hour) -> avoids timezone/session-boundary guessing.

Entry: break of vacuum-hour high (long) / low (short) in the NEXT hour, only if vacuum range < trailing-20d
median (compressed). Exit: end of next hour. NO-LOOKAHEAD (vacuum hour complete + trailing median pre-day).
OOS, cost-aware, sample floor. No sweep, no mutation.
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


def load(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df["date"] = dt.dt.normalize(); df["hour"] = dt.dt.hour; df["yr"] = dt.dt.year
    return df[df["yr"] >= 2019]


def run():
    print("Cycle 2026-06-22c — liquidity-vacuum-release (conditional microstructure) (REPORT-ONLY)\n", flush=True)
    print("Vacuum window = empirically-lowest-volume active hour; conditional on compressed vacuum range.\n", flush=True)
    results = {}
    survivors = []
    for asset in ("MCL", "ZN", "ZF", "M2K", "MES"):
        df = load(asset); pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        # active hours = hours present on >=60% of days; vacuum = lowest median-volume among active (excl first/last active hr)
        hr_days = df.groupby("hour")["date"].nunique(); ndays = df["date"].nunique()
        active = sorted([h for h in hr_days.index if hr_days[h] >= 0.6 * ndays])
        if len(active) < 4:
            results[asset] = {"verdict": "KILL_no_session"}; print(f"  {asset}: insufficient active hours"); continue
        medvol = df[df["hour"].isin(active)].groupby("hour")["volume"].median()
        inner = [h for h in active if h not in (active[0], active[-1])]
        vac = int(medvol[inner].idxmin()); nxt = vac + 1
        if nxt not in active:
            nxt = active[active.index(vac) + 1] if active.index(vac) + 1 < len(active) else None
        if nxt is None:
            results[asset] = {"verdict": "KILL_no_next_hour"}; print(f"  {asset}: no hour after vacuum"); continue
        # per-day vacuum range + next-hour break
        vacg = df[df["hour"] == vac].groupby("date").agg(vh=("high", "max"), vl=("low", "min"))
        vacg["vrange"] = vacg["vh"] - vacg["vl"]
        vacg["vmed"] = vacg["vrange"].shift(1).rolling(20).median()    # trailing, no-lookahead
        vacg["compressed"] = vacg["vrange"] < vacg["vmed"]
        nxtg = df[df["hour"] == nxt].groupby("date").agg(no=("open", "first"), nh=("high", "max"), nl=("low", "min"), nc=("close", "last"))
        m = vacg.join(nxtg, how="inner").dropna(subset=["vmed"])
        rows = []
        for d, r in m.iterrows():
            if not r["compressed"]:
                continue
            # break direction in next hour: which side of vacuum range breaks first (approx: high break if nh>vh)
            long_brk = r["nh"] > r["vh"]; short_brk = r["nl"] < r["vl"]
            if long_brk and not short_brk:
                # REALISTIC FILL: if hour already opened above the level, the break pre-occurred -> fill at open (worse), not the level
                entry_px = r["no"] if r["no"] >= r["vh"] else r["vh"]
                pnl = (r["nc"] - entry_px) * pv - rt; dr = 1
            elif short_brk and not long_brk:
                entry_px = r["no"] if r["no"] <= r["vl"] else r["vl"]
                pnl = (entry_px - r["nc"]) * pv - rt; dr = -1
            else:
                continue  # both or neither -> skip ambiguous
            rows.append({"pnl": float(pnl), "yr": pd.Timestamp(d).year, "dir": dr})
        tr = pd.DataFrame(rows)
        if len(tr) < 150:
            results[asset] = {"vacuum_hour": vac, "n": len(tr), "verdict": "KILL_low_n"}
            print(f"  {asset}: vacuum h{vac}->h{nxt}, n={len(tr)} -> KILL_low_n", flush=True); continue
        p = tr["pnl"].to_numpy(); n = len(p); pf = _pf(p); pos = float((p > 0).mean()); net = float(p.sum())
        so = tr.sort_index()  # already date-ordered via groupby
        h = n // 2; tr_pf = _pf(p[:h]); te_pf = _pf(p[h:])
        py = tr.groupby("yr")["pnl"].sum(); yrs_pos = int((py > 0).sum()); n_yr = int(py.shape[0])
        g = np.sort(p[p > 0])[::-1]; gp = float(p[p > 0].sum()); top3 = round(float(g[:3].sum()) / gp * 100, 1) if gp > 0 else None
        ok = pf >= 1.2 and pos >= 0.5 and tr_pf > 1.05 and te_pf > 1.05 and (yrs_pos / max(n_yr, 1)) >= 0.7 and net > 0 and (top3 or 99) < 40
        v = "STRUCTURE_FOUND" if ok else ("WATCH" if pf >= 1.15 and net > 0 else "KILL")
        if ok:
            survivors.append(f"{asset}-vacuum")
        results[asset] = {"vacuum_hour": vac, "next_hour": nxt, "n": n, "pf": round(pf, 3), "pos": round(pos, 2),
                          "net": round(net, 0), "train_pf": round(tr_pf, 3), "test_pf": round(te_pf, 3), "top3_pct": top3, "yrs_pos": f"{yrs_pos}/{n_yr}", "verdict": v}
        print(f"  {asset}: vacuum h{vac}->break h{nxt} | n={n} PF={pf:.3f} pos={pos:.2f} net=${net:.0f} "
              f"OOS={tr_pf:.3f}/{te_pf:.3f} top3={top3}% yrs+={yrs_pos}/{n_yr} -> {v}", flush=True)

    noneq = [s for s in survivors if s.split('-')[0] in ("MCL", "ZN", "ZF")]
    print(f"\n  survivors: {survivors or 'none'} | non-equity (WH2-relevant): {noneq or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22c_liquidity_vacuum.json"
    out.write_text(json.dumps({"cycle": "2026-06-22c_liquidity_vacuum", "mode": "Lane B report-only; conditional microstructure; NON-WIRED",
        "results": results, "survivors": survivors, "noneq_survivors": noneq,
        "note": "vacuum hour empirical (lowest-vol active hour); conditional on compressed vacuum range; no-lookahead",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; conditional microstructure; no mutation)", flush=True)


if __name__ == "__main__":
    run()
