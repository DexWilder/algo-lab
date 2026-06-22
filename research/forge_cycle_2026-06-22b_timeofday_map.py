"""Cycle 2026-06-22b — fresh loop: INTRADAY TIME-OF-DAY asymmetry map (report-only).

Shift from 'any structure' -> 'non-equity daily structure that isn't beta'. Intraday hour-of-day
drift exposes FORCED behavior (open imbalance, lunch liquidity vacuum, settlement/close flow,
session transitions) — structural, near-daily (~250/yr per hour = truly daily cadence), reachable.
Data-quality-gated: all instruments confirmed 100% on-5m-grid (earlier 'ZN irregular' was a single
low-vol day, not the norm). Non-MNQ/non-gold focus: MCL/ZN/ZF/M2K + MES benchmark.

Per instrument x hour: 'long that hour every day' (first-open -> last-close within hour), cost-aware,
PF/pos/OOS(train<=2022,test>=2023)/per-year. Flag OOS-CONSISTENT hours (PF>=1.2 BOTH halves,
pos>=0.55, >=75% yrs+, net>0 after cost). Honest: hour-drift is also decay-prone; map-fill + any
survivor = daily intraday-conditioning candidate (still needs deeper audit). No sweep, no mutation.
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


def hour_returns(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df["date"] = dt.dt.normalize(); df["hour"] = dt.dt.hour; df["yr"] = dt.dt.year
    df = df[df["yr"] >= 2019]
    g = df.groupby(["date", "hour"]).agg(o=("open", "first"), c=("close", "last"), n=("close", "size")).reset_index()
    g = g[g["n"] >= 6]  # require near-full hour (>=6 of 12 5m bars)
    g["ret"] = g["c"] - g["o"]
    g["yr"] = pd.to_datetime(g["date"]).dt.year
    return g


def run():
    print("Cycle 2026-06-22b — INTRADAY TIME-OF-DAY asymmetry map (REPORT-ONLY)\n", flush=True)
    print("Forced-behavior hours (open/lunch/close/session-transition); near-daily; non-MNQ/non-gold + MES bench.\n", flush=True)
    survivors = []
    out_all = {}
    for asset in ("MCL", "ZN", "ZF", "M2K", "MES"):
        g = hour_returns(asset); pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        out_all[asset] = {}
        rows_printed = []
        for hr in sorted(g["hour"].unique()):
            sub = g[g["hour"] == hr]
            if len(sub) < 250:  # need a real daily-cadence sample
                continue
            pl = sub["ret"].to_numpy() * pv - rt; ps = -sub["ret"].to_numpy() * pv - rt
            dr, p = (1, pl) if _pf(pl) >= _pf(ps) else (-1, ps)
            n = len(p); pf = _pf(p); pos = float((p > 0).mean()); net = float(p.sum())
            so = sub.sort_values("date"); psd = dr * so["ret"].to_numpy() * pv - rt
            tr_pf = _pf(psd[so["yr"].values <= 2022]); te_pf = _pf(psd[so["yr"].values >= 2023])
            py = pd.Series(p, index=sub["yr"].values).groupby(level=0).sum(); yrs_pos = int((py > 0).sum()); n_yr = int(py.shape[0])
            ok = pf >= 1.2 and pos >= 0.55 and tr_pf > 1.05 and te_pf > 1.05 and (yrs_pos / max(n_yr, 1)) >= 0.75 and net > 0
            rec = {"hour": int(hr), "dir": "long" if dr == 1 else "short", "n": n, "pf": round(pf, 3),
                   "pos": round(pos, 2), "net": round(net, 0), "train_pf": round(tr_pf, 3), "test_pf": round(te_pf, 3),
                   "yrs_pos": f"{yrs_pos}/{n_yr}", "ok": ok}
            out_all[asset][f"h{hr}"] = rec
            if ok:
                survivors.append(f"{asset}-h{hr}-{rec['dir']}")
                rows_printed.append(rec)
        # print survivors (or top-PF hour if none) per instrument
        if rows_printed:
            for r in rows_printed:
                print(f"  {asset} h{r['hour']:02d} {r['dir']:<5} n={r['n']} PF={r['pf']} pos={r['pos']} net=${r['net']} OOS={r['train_pf']}/{r['test_pf']} yrs+={r['yrs_pos']} <-- OOS-CONSISTENT", flush=True)
        else:
            best = max(out_all[asset].values(), key=lambda x: x["pf"]) if out_all[asset] else None
            if best:
                print(f"  {asset}: no OOS-consistent hour (best h{best['hour']:02d} {best['dir']} PF={best['pf']} OOS={best['train_pf']}/{best['test_pf']})", flush=True)

    print(f"\n  OOS-consistent intraday hours: {survivors or 'NONE'}", flush=True)
    noneq = [s for s in survivors if s.split('-')[0] in ("MCL", "ZN", "ZF")]
    print(f"  non-MNQ/non-gold/non-equity survivors (WH2-relevant): {noneq or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22b_timeofday_map.json"
    out.write_text(json.dumps({"cycle": "2026-06-22b_timeofday_map", "mode": "Lane B report-only; intraday TOD map; NON-WIRED",
        "results": out_all, "survivors": survivors, "noneq_survivors": noneq,
        "note": "hour drift; survivor=daily intraday-conditioning candidate (deeper audit needed); equity survivors=Lane2 not WH2",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; intraday map; no mutation)", flush=True)


if __name__ == "__main__":
    run()
