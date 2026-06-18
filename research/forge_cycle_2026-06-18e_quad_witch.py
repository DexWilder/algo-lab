"""Cycle 2026-06-18e — priority #3: quad-witch expiry-DAY / post-expiry (report-only).

Reachable-now, distinct from the OPEX-WEEK beta test (15j) — this is the expiry-DAY mechanics +
the documented post-triple-witch weak week. 3rd Friday of Mar/Jun/Sep/Dec; index futures/options
settle AM -> dealer gamma unwind. Predeclared windows + thesis (no direction-fishing):
  W1 expiry_day: Thu-close -> Fri-close (the pin day), dir +1 (test continuation)
  W2 post_witch_week: Fri-close -> +5 td (documented post-witch weakness), dir -1 (short equity)
EQUITY-event/tail (MES/MNQ) -> NOT WH2 (equity, MNQ-adjacent) even if it survives. FOMC-contam flag.
Tail discipline. ~28 events. No sweep, no mutation.
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
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def third_fridays():
    out = []
    for y in range(2019, 2027):
        for mth in (3, 6, 9, 12):
            d = pd.Timestamp(y, mth, 1); fri = 0
            while True:
                if d.weekday() == 4:
                    fri += 1
                    if fri == 3:
                        out.append(d.normalize()); break
                d += pd.Timedelta(days=1)
    return out


def events(asset, entry_off, exit_off, dr):
    s = daily_close(asset); s = s[s.index.year >= 2019]; days = list(s.index); dset = set(days)
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    fomc = [pd.Timestamp(x["actual_date"]).normalize() for x in build_official_fomc_calendar()]
    rows = []
    for w in third_fridays():
        wd = w
        while wd not in dset and wd < days[-1]:
            wd += pd.Timedelta(days=1)
        if wd not in dset:
            continue
        i = days.index(wd); ei, xi = i + entry_off, i + exit_off
        if ei < 0 or xi >= len(days):
            continue
        rows.append({"pnl": float(dr * (s.loc[days[xi]] - s.loc[days[ei]]) * pv - rt), "year": wd.year,
                     "fomc": any(abs((wd - f).days) <= 4 for f in fomc)})
    return pd.DataFrame(rows)


def board(tr):
    if tr is None or len(tr) < 12:
        return {"n": len(tr) if tr is not None else 0, "pf": None}
    p = tr["pnl"].to_numpy(); net = float(p.sum()); g = np.sort(p[p > 0])[::-1]; gp = float(p[p > 0].sum())
    py = tr.groupby("year")["pnl"].sum()
    return {"n": len(p), "pf": round(_pf(p), 3), "net": round(net, 0), "pos_frac": round(float((p > 0).mean()), 2),
            "max_single_pct": round(float(g[0]) / gp * 100, 1) if gp > 0 else None,
            "max_year_pct": round(float(py.abs().max() / net * 100), 1) if net else None, "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}"}


def run():
    print("Cycle 2026-06-18e — priority #3: quad-witch expiry-day / post-witch (REPORT-ONLY)\n", flush=True)
    print("EQUITY event/tail (MES/MNQ) -> NOT the non-MNQ WH2 even if it survives.\n", flush=True)
    WIN = [("W1_expiry_day_Thu->Fri_long", -1, 0, 1), ("W2_post_witch_week_short", 0, 5, -1)]
    results = {}
    any_struct = False
    for asset in ("MES", "MNQ"):
        for name, eo, xo, dr in WIN:
            tr = events(asset, eo, xo, dr)
            allm = board(tr); clean = board(tr[~tr["fomc"]])
            c = clean if clean.get("pf") else allm
            ok = (c.get("pf") or 0) >= 1.3 and (c.get("max_single_pct") or 99) < 40 and (c.get("max_year_pct") or 99) < 60 and (c.get("pos_frac") or 0) >= 0.55
            v = "STRUCTURE_FOUND_tail" if ok else ("WATCH_tail" if (c.get("pf") or 0) >= 1.2 else "KILL")
            if ok:
                any_struct = True
            results[f"{asset}|{name}"] = {"all": allm, "clean_of_fomc": clean, "verdict": v}
            print(f"  {asset} {name:<28} ALL PF={allm.get('pf')} n={allm.get('n')} | clean-FOMC PF={clean.get('pf')} "
                  f"pos={c.get('pos_frac')} max-single={c.get('max_single_pct')}% max-yr={c.get('max_year_pct')}% yrs+={c.get('yrs_pos')} -> {v}", flush=True)
    print(f"\n  {'a structure cleared (equity-event/tail, NOT WH2)' if any_struct else 'no clean structure -> KILL/WATCH'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-18e_quad_witch.json"
    out.write_text(json.dumps({"cycle": "2026-06-18e_quad_witch", "mode": "Lane 1 report-only; equity event/tail; NON-WIRED",
        "results": results, "note": "equity (MES/MNQ) event/tail NOT non-MNQ WH2; ~28 events", "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
