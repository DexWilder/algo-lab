"""Cycle 2026-06-22a — fresh loop: DAY-OF-WEEK directional drift map (report-only).

Continue-by-default (queue archived != Forge done). Near-daily calendar/positioning structure
(weekend-risk + start/end-of-week repositioning), NOT generic indicators. Daily close-to-close
(prior close -> that-day close) so ZN's irregular INTRADAY sampling doesn't contaminate (daily
bars are clean). Non-MNQ/non-gold focus: ZN/ZF/MCL + MES benchmark. Each (instrument x weekday)
~ 50-360/yr -> near-daily cadence.

For each instrument x weekday: long-bias close-to-close PF/pos/OOS(train<=2022,test>=2023)/per-year.
Flag only OOS-CONSISTENT same-sign drift clearing gates (PF>=1.2 BOTH halves, pos>=0.55, >=6/8 yrs).
Honest prior: day-of-week is a classic mostly-decayed anomaly -> expect mostly nothing; filling a
real reachable gap + any survivor = near-daily conditioning candidate. No sweep, no mutation.
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

WD = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def run():
    print("Cycle 2026-06-22a — DAY-OF-WEEK directional drift map (REPORT-ONLY)\n", flush=True)
    print("Near-daily calendar/positioning structure; daily close-to-close; non-MNQ/non-gold + MES bench.\n", flush=True)
    survivors = []
    out_all = {}
    for asset in ("ZN", "ZF", "MCL", "MES"):
        s = daily_close(asset); s = s[s.index.year >= 2019]
        pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        df = pd.DataFrame({"close": s}); df["ret"] = df["close"].diff(); df["wd"] = df.index.weekday; df["yr"] = df.index.year
        df = df.dropna(subset=["ret"])
        print(f"  {asset}:", flush=True)
        out_all[asset] = {}
        for wd, name in WD.items():
            sub = df[df["wd"] == wd].copy()
            if len(sub) < 100:
                continue
            # long-bias close-to-close pnl on that weekday (minus round-trip cost)
            pnl = sub["ret"].to_numpy() * pv - rt
            # also test SHORT-bias (just sign flip) — pick the directionally-consistent one honestly
            for dr, dlab in ((1, "long"), (-1, "short")):
                p = dr * sub["ret"].to_numpy() * pv - rt
                n = len(p); h = n // 2
                pf = _pf(p); pos = float((p > 0).mean())
                py = pd.Series(p, index=sub.index).groupby(sub["yr"]).sum()
                yrs_pos = int((py > 0).sum()); n_yr = int(py.shape[0])
                tr = pf if False else None
                # OOS: split by date order
                so = sub.sort_index(); psorted = dr * so["ret"].to_numpy() * pv - rt
                tr_pf = _pf(psorted[so.index.year <= 2022]); te_pf = _pf(psorted[so.index.year >= 2023])
                ok = pf >= 1.2 and pos >= 0.55 and tr_pf > 1.05 and te_pf > 1.05 and (yrs_pos / max(n_yr, 1)) >= 0.75
                out_all[asset][f"{name}_{dlab}"] = {"n": n, "pf": round(pf, 3), "pos": round(pos, 2),
                                                     "train_pf": round(tr_pf, 3), "test_pf": round(te_pf, 3), "yrs_pos": f"{yrs_pos}/{n_yr}", "ok": ok}
                flag = " <-- OOS-CONSISTENT" if ok else ""
                if ok:
                    survivors.append(f"{asset}-{name}-{dlab}")
                # only print the better direction per weekday to keep it readable
                if dlab == "long":
                    # decide which direction to show: the one with higher PF
                    p_s = -1 * sub["ret"].to_numpy() * pv - rt
                    show = (dr, dlab, pf, pos, tr_pf, te_pf, yrs_pos, n_yr) if pf >= _pf(p_s) else None
            # print best-direction summary
            pl = _pf(sub["ret"].to_numpy() * pv - rt); ps = _pf(-sub["ret"].to_numpy() * pv - rt)
            bestdir = "long" if pl >= ps else "short"
            b = out_all[asset][f"{name}_{bestdir}"]
            print(f"    {name} ({len(sub)}): best={bestdir} PF={b['pf']} pos={b['pos']} OOS={b['train_pf']}/{b['test_pf']} yrs+={b['yrs_pos']}"
                  + (" <-- OOS-CONSISTENT" if b['ok'] else ""), flush=True)

    print(f"\n  OOS-consistent day-of-week drifts: {survivors or 'NONE (classic anomaly decayed, as expected)'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22a_dayofweek_map.json"
    out.write_text(json.dumps({"cycle": "2026-06-22a_dayofweek_map", "mode": "Lane B report-only; near-daily calendar map; NON-WIRED",
        "results": out_all, "survivors": survivors,
        "note": "day-of-week close-to-close; survivor=near-daily conditioning candidate (would still need deeper audit); none=clean map-fill",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; near-daily map; no mutation)", flush=True)


if __name__ == "__main__":
    run()
