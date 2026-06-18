"""Cycle 2026-06-18f — priority #4: settlement-window reversion (report-only, low-expectation).

Forced-flow thesis: hedgers/dealers square inventory into the cash/settlement close -> intraday
extension fades into the settle. DATA REALITY: ZN 5m is irregularly sampled (~22% days miss the
15:00 ET window) AND a ZN settlement test overlaps the existing ZN-Afternoon-Reversion book ->
ZN settlement is data-quality-limited + redundant (flagged, not run). MES has clean full intraday
-> tested there, but MES = EQUITY (MNQ-adjacent) so even a PASS is NOT the non-MNQ WH2.

Predeclared (no sweep): fade the open->15:30 ET extension into the 16:00 ET cash close if
|ext| > 0.75*ATR. CONTAMINATION day-exclusions predeclared BEFORE run: FOMC, CPI, NFP, month-end
(last 3 td), quarter-end, roll-window (late Feb/May/Aug/Nov), OPEX (3rd Fri). Report clean edge.
Strict PASS/WATCH/KILL. No mutation.
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


def first_fridays(yrs):
    out = []
    for y in yrs:
        for mth in range(1, 13):
            d = pd.Timestamp(y, mth, 1)
            while d.weekday() != 4:
                d += pd.Timedelta(days=1)
            out.append(d.normalize())
    return out


def third_fridays(yrs):
    out = []
    for y in yrs:
        for mth in (3, 6, 9, 12):
            d = pd.Timestamp(y, mth, 1); n = 0
            while True:
                if d.weekday() == 4:
                    n += 1
                    if n == 3:
                        out.append(d.normalize()); break
                d += pd.Timedelta(days=1)
    return out


def run():
    print("Cycle 2026-06-18f — priority #4: settlement-window reversion (MES; ZN data-quality-limited) (REPORT-ONLY)\n", flush=True)
    print("MES = equity -> even PASS is NOT the non-MNQ WH2. ZN settlement data-quality-limited + overlaps ZN-Afternoon book.\n", flush=True)
    asset = "MES"
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    df["date"] = dt.dt.normalize(); df["hm"] = dt.dt.strftime("%H:%M"); df["y"] = dt.dt.year
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    fomc = set(pd.Timestamp(x["actual_date"]).normalize() for x in build_official_fomc_calendar())
    try:
        import research.forge_cpi_calendar_verified as cc
        cpi = set(pd.Timestamp(x["actual_date"]).normalize() for x in cc.build_verified_cpi_calendar())
    except Exception:
        cpi = set()
    nfp = set(first_fridays(range(2019, 2027))); opex = set(third_fridays(range(2019, 2027)))
    ROLL = {2, 5, 8, 11}
    md = {}
    for d in sorted(df["date"].unique()):
        md.setdefault((pd.Timestamp(d).year, pd.Timestamp(d).month), []).append(pd.Timestamp(d))

    rows = []
    for d, g in df.groupby("date"):
        rth = g[(g["hm"] >= "09:30") & (g["hm"] <= "16:00")]
        if len(rth) < 20:
            continue
        o = rth.iloc[0]["open"]
        pre = rth[rth["hm"] <= "15:30"]
        wind = rth[(rth["hm"] > "15:30") & (rth["hm"] <= "16:00")]
        if len(pre) < 5 or len(wind) < 2:
            continue
        atr = (pre["high"].max() - pre["low"].min())  # NO-LOOKAHEAD: range through 15:30 decision point ONLY (not full day)
        ext = pre.iloc[-1]["close"] - o
        if atr <= 0 or abs(ext) < 0.75 * atr:
            continue
        direction = -np.sign(ext)  # fade the extension into settle
        entry = wind.iloc[0]["open"]; exit_px = wind.iloc[-1]["close"]
        me = md[(d.year, d.month)]
        ts = pd.Timestamp(d)
        rows.append({"pnl": float(direction * (exit_px - entry) * pv - rt), "year": d.year,
                     "c_fomc": ts in fomc, "c_cpi": ts in cpi, "c_nfp": ts in nfp, "c_opex": ts in opex,
                     "c_me": ts in me[-3:], "c_qe": (d.month in (3, 6, 9, 12) and ts in me[-3:]), "c_roll": (d.month in ROLL and d.day >= 20)})
    tr = pd.DataFrame(rows)
    if len(tr) < 50:
        print(f"  n={len(tr)} too few -> KILL_low_n"); return

    def stats(sub, label):
        if len(sub) < 30:
            print(f"  {label}: n={len(sub)} (too few)"); return None
        p = sub["pnl"].to_numpy(); net = float(p.sum()); g = np.sort(p[p > 0])[::-1]; gp = float(p[p > 0].sum())
        py = sub.groupby("year")["pnl"].sum()
        s = {"n": len(p), "pf": round(_pf(p), 3), "net": round(net, 0), "median": round(float(np.median(p)), 2),
             "pos_frac": round(float((p > 0).mean()), 2), "max_single_pct": round(float(g[0]) / gp * 100, 1) if gp > 0 else None,
             "max_year_pct": round(float(py.abs().max() / net * 100), 1) if net else None, "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}"}
        print(f"  {label}: n={s['n']} PF={s['pf']} net=${s['net']} med=${s['median']} pos={s['pos_frac']} "
              f"max-single={s['max_single_pct']}% max-yr={s['max_year_pct']}% yrs+={s['yrs_pos']}", flush=True)
        return s
    allm = stats(tr, "ALL extended-days")
    clean = stats(tr[~(tr["c_fomc"] | tr["c_cpi"] | tr["c_nfp"] | tr["c_opex"] | tr["c_me"] | tr["c_roll"])], "CLEAN (excl FOMC/CPI/NFP/OPEX/month-end/roll)")
    c = clean or allm
    ok = c and (c.get("pf") or 0) >= 1.3 and (c.get("max_single_pct") or 99) < 30 and (c.get("max_year_pct") or 99) < 40 and (c.get("pos_frac") or 0) >= 0.55
    verdict = "PASS_clean(equity, not WH2)" if ok else ("WATCH" if c and (c.get("pf") or 0) >= 1.2 else "KILL")
    print(f"\n  VERDICT: {verdict}  (MES=equity -> even PASS != non-MNQ WH2; ZN settlement data-quality-limited)", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-18f_settlement_window.json"
    out.write_text(json.dumps({"cycle": "2026-06-18f_settlement_window", "mode": "Lane 1 report-only; equity event/daily; NON-WIRED",
        "all": allm, "clean": clean, "verdict": verdict,
        "note": "MES equity (not WH2); ZN settlement data-quality-limited (irregular 5m, 22% gap days) + overlaps ZN-Afternoon book",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
