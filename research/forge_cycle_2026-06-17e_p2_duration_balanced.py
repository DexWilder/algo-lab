"""Cycle 2026-06-17e — P2 DURATION-BALANCED curve spread, ONE retest (report-only).

The structurally-correct form of P2 (the naïve 1:1 spread in 17d was duration-contaminated,
dominated by ZB). ONE predeclared variant only — NOT an ad hoc rescue. If this fails, the
FRED yield-curve branch closes as mapped/dead (futures roll-yield P1 stays separate/feed-blocked).

PREDECLARED duration weights (FIXED before running; standard CME-ballpark DV01 $/contract/bp):
    ZF = 45, ZN = 65, ZB = 130.
Each leg sized 1/DV01 -> dollar-duration-neutral spread. Long best-rolldown tenor,
short worst-rolldown tenor, DV01-weighted.

Same 1-trading-day FRED lag + merge_asof(backward, allow_exact_matches=False) no-lookahead;
same join audit. NO additional filters, NO parameter sweep, NO synthetic fill, NO mutation.
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

YC = ROOT / "data" / "feeds" / "treasury_yield_curve.csv"
DV01 = {"ZF": 45.0, "ZN": 65.0, "ZB": 130.0}   # PREDECLARED, fixed, CME-ballpark $/contract/bp
TENORS = ["ZF", "ZN", "ZB"]
ROLL = {"ZF": ("dgs5", "dgs2"), "ZN": ("dgs10", "dgs5"), "ZB": ("dgs30", "dgs10")}


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    return df.assign(date=dt.dt.normalize()).groupby("date")["close"].last()


def board(pnl, dates, mnq_daily):
    p = np.asarray(pnl, float); n = len(p)
    if n < 200:
        return {"n": n, "verdict": "KILL_low_n"}
    s = pd.Series(p, index=pd.to_datetime(dates)); net = float(p.sum()); h = n // 2
    dpos = s[s > 0].sort_values(ascending=False); gp = float(dpos.sum())
    top3 = round(float(dpos.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    per_yr = s.groupby(s.index.year).sum(); maxyr = round(float(per_yr.abs().max() / net * 100), 1) if net else None
    yrs_pos = int((per_yr > 0).sum()); n_yr = int(per_yr.shape[0])
    cuts = np.linspace(0, n, 4).astype(int); eras = [round(_pf(p[cuts[i]:cuts[i + 1]]), 3) for i in range(3)]
    yx = [round(_pf(s[s.index.year != y].values), 3) for y in sorted(set(s.index.year))]
    al = pd.concat([s.rename("a"), mnq_daily.rename("b")], axis=1).fillna(0.0); corr = round(float(al["a"].corr(al["b"])), 3)
    pf = _pf(p); med = float(np.median(p))
    quality = (pf > 1.2 and med >= 0 and _pf(p[:h]) > 1.0 and _pf(p[h:]) > 1.0 and (top3 or 99) < 30
               and (maxyr or 99) < 40 and (yrs_pos / max(n_yr, 1)) >= 0.75 and all(e > 1.0 for e in eras) and min(yx) > 1.15)
    verdict = ("CANDIDATE" if quality and abs(corr) < 0.5 else
               ("STRUCTURE_FOUND" if (pf > 1.2 and med >= 0) else ("RETEST" if pf > 1.05 else "KILL")))
    return {"n": n, "pf": round(pf, 3), "net": round(net, 0), "median": round(med, 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "top3_day_pct": top3,
            "max_year_pct": maxyr, "yrs_pos": f"{yrs_pos}/{n_yr}", "era_pf": eras, "yr_excl_min": min(yx),
            "corr_mnq": corr, "verdict": verdict}


def run():
    print("Cycle 2026-06-17e — P2 DURATION-BALANCED curve spread (ONE retest) (REPORT-ONLY)\n", flush=True)
    print(f"PREDECLARED DV01 ($/contract/bp, fixed): {DV01}; leg size = 1/DV01 (dollar-duration-neutral)\n", flush=True)

    yc = pd.read_csv(YC, parse_dates=["date"]).sort_values("date")
    closes = {a: daily_close(a) for a in TENORS}
    fut = pd.concat(closes, axis=1).dropna().reset_index()
    fut = fut.rename(columns={fut.columns[0]: "date"}); fut["date"] = pd.to_datetime(fut["date"])
    j = pd.merge_asof(fut.sort_values("date"), yc.rename(columns={"date": "curve_date"}).sort_values("curve_date"),
                      left_on="date", right_on="curve_date", direction="backward", allow_exact_matches=False)
    assert int((j["curve_date"] >= j["date"]).sum()) == 0, "LOOKAHEAD LEAK"
    j = j.dropna(subset=["curve_date", "dgs2", "dgs5", "dgs10", "dgs30"]).reset_index(drop=True)
    j = j[j["date"].dt.year >= 2019].reset_index(drop=True)
    print(f"JOIN: {len(j)} rows, no-lookahead OK (curve_date < trade_date), 2019-2026.", flush=True)

    j["roll_ZF"] = j["dgs5"] - j["dgs2"]; j["roll_ZN"] = j["dgs10"] - j["dgs5"]; j["roll_ZB"] = j["dgs30"] - j["dgs10"]
    rolls = j[["roll_ZF", "roll_ZN", "roll_ZB"]].to_numpy()
    pv = {a: ASSETS[a]["point_value"] for a in TENORS}; cp = {a: get_cost_params(a) for a in TENORS}
    rt = {a: 2 * (cp[a]["commission_per_side"] + cp[a]["slippage_ticks"] * cp[a]["tick_size"] * pv[a]) for a in TENORS}
    px = {a: j[a].to_numpy() for a in TENORS}; dates = j["date"].to_numpy()

    mnq = daily_close("MNQ").diff(); mnq.index = pd.to_datetime(mnq.index)

    prev_long = prev_short = None; pnl = []; pd_dates = []
    for k in range(1, len(j)):
        r = rolls[k - 1]
        best = TENORS[int(np.argmax(r))]; worst = TENORS[int(np.argmin(r))]
        wl = 1.0 / DV01[best]; ws = 1.0 / DV01[worst]   # DV01-weighted leg sizes
        day = wl * (px[best][k] - px[best][k - 1]) * pv[best] - ws * (px[worst][k] - px[worst][k - 1]) * pv[worst]
        if best != prev_long:
            day -= wl * rt[best] + (1.0 / DV01[prev_long] * rt[prev_long] if prev_long else 0)
        if worst != prev_short:
            day -= ws * rt[worst] + (1.0 / DV01[prev_short] * rt[prev_short] if prev_short else 0)
        prev_long, prev_short = best, worst
        pnl.append(day); pd_dates.append(dates[k])

    b = board(pnl, pd_dates, mnq)
    print("\nP2 DURATION-BALANCED spread board:", flush=True)
    if b["verdict"].startswith("KILL") and "low_n" in b["verdict"]:
        print(f"  {b['verdict']} (n={b.get('n')})", flush=True)
    else:
        print(f"  {b['verdict']:<16} n={b['n']} PF={b['pf']} med=${b['median']} net=${b['net']} "
              f"H1/H2={b['h1_pf']}/{b['h2_pf']} top3day={b['top3_day_pct']}% maxyr={b['max_year_pct']}% "
              f"yrs+={b['yrs_pos']} eras={b['era_pf']} yr_excl_min={b['yr_excl_min']} corr_mnq={b['corr_mnq']}", flush=True)

    branch = ("FRED yield-curve branch CLOSED as mapped/dead (rotation, naive spread, AND duration-balanced all fail)"
              if b["verdict"] in ("KILL", "KILL_low_n", "RETEST") else
              "duration-balanced spread shows structure — NOT a rescue; evidence-clean; warrants honest follow-up")
    print(f"\n  BRANCH STATUS: {branch}", flush=True)
    print("  (P1 futures roll-yield stays SEPARATE + feed-blocked; FRED yields != futures roll)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17e_p2_duration_balanced.json"
    out.write_text(json.dumps({"cycle": "2026-06-17e_p2_duration_balanced", "mode": "Lane B report-only; ONE retest; NO-LOOKAHEAD; NON-WIRED",
        "predeclared_dv01": DV01, "n_rows": len(j), "board": b, "branch_status": branch,
        "boundaries": "one variant; no filters/sweep/synthetic-fill/mutation; structural feed-readiness != evidence"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; one predeclared retest; no sweep; no mutation)", flush=True)


if __name__ == "__main__":
    run()
