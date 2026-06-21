"""Cycle 2026-06-20a — fresh discovery loop: PRE-HOLIDAY DRIFT (report-only).

Demonstrates "dead queue != dead Forge": the reachable structural-flow queue #2-6 is mapped, so
roll into a NEW reachable mechanism. Pre-holiday drift = calendar-mechanical (the productive vein,
not reactive): documented positive drift on the last session before market closures (pre-closure
short-covering + thinned liquidity = forced flow). Genuinely untested here, reachable (holidays
detected EMPIRICALLY from missing-weekday gaps in the data -> exact, no external feed, no-lookahead
since the holiday schedule is known in advance).

Mechanism (predeclared, no sweep): LONG entry at prior-session close -> exit at pre-holiday close.
Tested across MES/MYM/M2K (equity = Lane-2/benchmark) + MCL/ZN/ZF (non-equity = WH2-relevant).
Discipline: OOS halves, per-year, contamination (FOMC overlap), sample floor, tail gates. No mutation.
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


def _nyse_holidays(y0=2019, y1=2026):
    """Proper US equity-market holiday calendar (NYSE-like): federal set MINUS market-open ones
    (Columbus/Veterans) PLUS Good Friday + Juneteenth(2022+). Reachable, consistent across instruments
    (fixes the unreliable empirical-gap method). Known in advance -> no-lookahead."""
    from pandas.tseries.holiday import USFederalHolidayCalendar, GoodFriday
    fed = USFederalHolidayCalendar().holidays(start=f"{y0}-01-01", end=f"{y1}-12-31")
    drop = set()  # Columbus Day (2nd Mon Oct) + Veterans Day (Nov 11) = market OPEN
    for d in fed:
        if (d.month == 10 and d.weekday() == 0 and 8 <= d.day <= 14) or (d.month == 11 and d.day in (10, 11, 12)):
            drop.add(d.normalize())
    gf = GoodFriday.dates(f"{y0}-01-01", f"{y1}-12-31")
    hol = set(d.normalize() for d in fed) - drop | set(pd.Timestamp(d).normalize() for d in gf)
    return hol


def preholiday_days(idx):
    """Pre-holiday day = last trading day strictly before a known market holiday.
    Uses the proper holiday calendar (consistent across instruments) -> no-lookahead (schedule known)."""
    hol = _nyse_holidays(); days = list(idx); dset = set(d.normalize() for d in days); out = []
    for h in sorted(hol):
        prior = [d for d in days if d.normalize() < h]
        if not prior:
            continue
        pre = prior[-1]
        # require the pre-holiday day to be within 4 cal-days of the holiday (real adjacency, not a gap)
        if (h - pre.normalize()).days <= 4:
            out.append(pre)
    return sorted(set(out))


def run():
    print("Cycle 2026-06-20a — fresh discovery loop: PRE-HOLIDAY DRIFT (REPORT-ONLY)\n", flush=True)
    print("Calendar-mechanical forced-flow (pre-closure short-cover/thin liquidity). Holidays detected from data gaps.\n", flush=True)
    fomc = set(pd.Timestamp(x["actual_date"]).normalize() for x in build_official_fomc_calendar())
    results = {}
    for asset in ("MES", "MYM", "M2K", "MCL", "ZN", "ZF"):
        s = daily_close(asset); s = s[s.index.year >= 2019]
        days = list(s.index); pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        ph = preholiday_days(s.index)
        rows = []
        for d in ph:
            i = days.index(d)
            if i < 1:
                continue
            entry = s.iloc[i - 1]; exit_px = s.loc[d]   # prior close -> pre-holiday close (long)
            rows.append({"pnl": float((exit_px - entry) * pv - rt), "year": d.year,
                         "fomc": any(abs((d - f).days) <= 2 for f in fomc)})
        tr = pd.DataFrame(rows)
        if len(tr) < 30:
            results[asset] = {"n": len(tr), "verdict": "KILL_low_n"}
            print(f"  {asset}: n={len(tr)} -> KILL_low_n", flush=True); continue
        def stat(sub):
            p = sub["pnl"].to_numpy()
            if len(p) < 20:
                return {"n": len(p), "pf": None}
            g = np.sort(p[p > 0])[::-1]; gp = float(p[p > 0].sum()); net = float(p.sum()); py = sub.groupby("year")["pnl"].sum(); h = len(p) // 2
            return {"n": len(p), "pf": round(_pf(p), 3), "net": round(net, 0), "median": round(float(np.median(p)), 2),
                    "pos_frac": round(float((p > 0).mean()), 2), "max_single_pct": round(float(g[0]) / gp * 100, 1) if gp > 0 else None,
                    "max_year_pct": round(float(py.abs().max() / net * 100), 1) if net else None, "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}",
                    "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3)}
        allm = stat(tr); clean = stat(tr[~tr["fomc"]])
        c = clean if clean.get("pf") else allm
        ok = (c.get("pf") or 0) >= 1.3 and (c.get("max_single_pct") or 99) < 35 and (c.get("max_year_pct") or 99) < 50 \
            and (c.get("pos_frac") or 0) >= 0.58 and (c.get("h1_pf") or 0) > 1.0 and (c.get("h2_pf") or 0) > 1.0
        eq = asset in ("MES", "MYM", "M2K")
        v = ("STRUCTURE_FOUND_tail" + ("(equity-not-WH2)" if eq else "(non-equity!)")) if ok else ("WATCH_tail" if (c.get("pf") or 0) >= 1.2 else "KILL")
        results[asset] = {"all": allm, "clean": clean, "equity": eq, "verdict": v}
        print(f"  {asset:<4} ({'eq' if eq else 'non-eq'}): ALL n={allm['n']} PF={allm['pf']} | clean PF={c.get('pf')} pos={c.get('pos_frac')} "
              f"med=${c.get('median')} max-single={c.get('max_single_pct')}% max-yr={c.get('max_year_pct')}% H1/H2={c.get('h1_pf')}/{c.get('h2_pf')} yrs+={c.get('yrs_pos')} -> {v}", flush=True)

    surv = [k for k, v in results.items() if "STRUCTURE_FOUND" in str(v.get("verdict")) or v.get("verdict") == "WATCH_tail"]
    noneq_surv = [k for k in surv if not results[k].get("equity")]
    print(f"\n  survivors: {surv or 'none'}  | non-equity survivors (WH2-relevant): {noneq_surv or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-20a_preholiday_drift.json"
    out.write_text(json.dumps({"cycle": "2026-06-20a_preholiday_drift", "mode": "Lane B report-only; fresh reachable discovery; NON-WIRED",
        "results": results, "note": "calendar-mechanical; equity survivors=Lane2 not WH2; non-equity survivors=WH2-relevant tail",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; fresh discovery loop; no mutation)", flush=True)


if __name__ == "__main__":
    run()
