"""Cycle 2026-06-17d — P1/P2 rates carry/curve FIRST-CUT screen (report-only).

Approved single locked cycle against the acquired FRED yield curve. Sequence:
  1. re-validate feed
  2. timestamp/no-lookahead audit (lag convention)
  3. join audit to ZN/ZF/ZB daily
  4. coverage by year/instrument
  5. first-cut cheap screen — MINIMAL predeclared variants only (NO sweep)
  6. brutal board: KILL / RETEST / STRUCTURE_FOUND / CANDIDATE (separate "mechanism observed"
     from "strategy candidate")
  7. archive

NO-LOOKAHEAD: FRED DGS yields dated D are published ~EOD D. We LAG one trading day — a
decision on futures day D uses the curve through D-1 only, via merge_asof(backward,
allow_exact_matches=False) so matched curve date < trade date (asserted). NO synthetic fill,
NO parameter mining, NO activation/mutation. Structural feed readiness is NOT evidence.
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
TENORS = {"ZF": ("dgs5", "dgs2"), "ZN": ("dgs10", "dgs5"), "ZB": ("dgs30", "dgs10")}  # (own, next-shorter) for rolldown


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    return df.assign(date=dt.dt.normalize()).groupby("date")["close"].last()


def board(pnl, dates, label, mnq_daily):
    p = np.asarray(pnl, float); n = len(p)
    if n < 200:
        return {"label": label, "n": n, "verdict": "KILL_low_n"}
    s = pd.Series(p, index=pd.to_datetime(dates)); yr = s.groupby(s.index.year)
    net = float(p.sum()); h = n // 2
    daypos = s[s > 0].sort_values(ascending=False); gp = float(daypos.sum())
    top3 = round(float(daypos.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    per_yr = yr.sum(); maxyr = round(float(per_yr.abs().max() / net * 100), 1) if net else None
    yrs_pos = int((per_yr > 0).sum()); n_yr = int(per_yr.shape[0])
    cuts = np.linspace(0, n, 4).astype(int); eras = [round(_pf(p[cuts[i]:cuts[i + 1]]), 3) for i in range(3)]
    yx = [round(_pf(s[s.index.year != y].values), 3) for y in sorted(set(s.index.year))]
    al = pd.concat([s.rename("a"), mnq_daily.rename("b")], axis=1).fillna(0.0); corr = round(float(al["a"].corr(al["b"])), 3)
    pf = _pf(p); med = float(np.median(p))
    quality = (pf > 1.2 and med >= 0 and _pf(p[:h]) > 1.0 and _pf(p[h:]) > 1.0
               and (top3 or 99) < 30 and (maxyr or 99) < 40 and (yrs_pos / max(n_yr, 1)) >= 0.75
               and all(e > 1.0 for e in eras) and min(yx) > 1.15)
    structure = pf > 1.2 and med >= 0   # mechanism observed but not all gates
    verdict = ("CANDIDATE" if quality and abs(corr) < 0.5 else
               ("STRUCTURE_FOUND" if structure else ("RETEST" if pf > 1.05 else "KILL")))
    return {"label": label, "n": n, "pf": round(pf, 3), "net": round(net, 0), "median": round(med, 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "top3_day_pct": top3,
            "max_year_pct": maxyr, "yrs_pos": f"{yrs_pos}/{n_yr}", "era_pf": eras, "yr_excl_min": min(yx),
            "corr_mnq": corr, "verdict": verdict}


def run():
    print("Cycle 2026-06-17d — P1/P2 rates carry/curve FIRST-CUT (REPORT-ONLY)\n", flush=True)

    # 1. re-validate feed
    yc = pd.read_csv(YC, parse_dates=["date"]).sort_values("date")
    print(f"1. FEED: {YC.name} n={len(yc)} range={yc['date'].min().date()}..{yc['date'].max().date()} "
          f"missing={ {c:int(yc[c].isna().sum()) for c in ['dgs2','dgs5','dgs10','dgs30']} }", flush=True)

    # 2. no-lookahead: lag curve by using it only for STRICTLY LATER futures days
    print("2. NO-LOOKAHEAD: DGS dated D published ~EOD D; decisions on futures day D use curve "
          "through D-1 (merge_asof backward, allow_exact_matches=False -> curve_date < trade_date).", flush=True)

    # 3+4. join to ZN/ZF/ZB daily + coverage
    closes = {a: daily_close(a) for a in TENORS}
    fut = pd.concat(closes, axis=1).dropna()  # common futures trading days
    fut = fut.reset_index().rename(columns={"index": "date"})
    if "date" not in fut.columns:
        fut = fut.rename(columns={fut.columns[0]: "date"})
    fut["date"] = pd.to_datetime(fut["date"])
    j = pd.merge_asof(fut.sort_values("date"), yc.rename(columns={"date": "curve_date"}).sort_values("curve_date"),
                      left_on="date", right_on="curve_date", direction="backward", allow_exact_matches=False)
    viol = int((j["curve_date"] >= j["date"]).sum())
    assert viol == 0, f"LOOKAHEAD LEAK {viol}"
    matched = int(j["curve_date"].notna().sum()); lag = (j["date"] - j["curve_date"]).dt.days
    print(f"3. JOIN AUDIT: futures days={len(fut)} matched-curve={matched} "
          f"median_lag={float(lag.median())}d max_lag={int(lag.max())}d (holiday gaps absorbed by backward-asof)", flush=True)
    j = j.dropna(subset=["curve_date", "dgs2", "dgs5", "dgs10", "dgs30"]).reset_index(drop=True)
    j = j[j["date"].dt.year >= 2019].reset_index(drop=True)  # align to futures history
    cov = j.groupby(j["date"].dt.year).size().to_dict()
    print(f"4. COVERAGE by year (rows): { {int(k): int(v) for k,v in cov.items()} }", flush=True)

    # 5. MINIMAL predeclared variants (NO sweep):
    # rolldown carry per tenor = own_yield - next_shorter_yield (upward slope -> positive roll for a long bond)
    j["roll_ZF"] = j["dgs5"] - j["dgs2"]; j["roll_ZN"] = j["dgs10"] - j["dgs5"]; j["roll_ZB"] = j["dgs30"] - j["dgs10"]
    rolls = j[["roll_ZF", "roll_ZN", "roll_ZB"]].to_numpy()
    tenor_list = ["ZF", "ZN", "ZB"]
    pv = {a: ASSETS[a]["point_value"] for a in tenor_list}; cp = {a: get_cost_params(a) for a in tenor_list}
    rt = {a: 2 * (cp[a]["commission_per_side"] + cp[a]["slippage_ticks"] * cp[a]["tick_size"] * pv[a]) for a in tenor_list}
    dates = j["date"].to_numpy()
    px = {a: j[a].to_numpy() for a in tenor_list}

    mnq = daily_close("MNQ").diff(); mnq.index = pd.to_datetime(mnq.index)

    def backtest(mode):
        # mode: 'rotation' = long best-carry tenor; 'spread' = long best / short worst (1:1, NOT duration-balanced)
        prev_long = prev_short = None; pnl = []; pdates = []
        for k in range(1, len(j)):
            r = rolls[k - 1]  # carry signal from prior day (already lagged curve -> double-safe)
            best = tenor_list[int(np.argmax(r))]; worst = tenor_list[int(np.argmin(r))]
            day_pnl = 0.0
            # realize move from k-1 -> k on positions decided at k-1
            day_pnl += (px[best][k] - px[best][k - 1]) * pv[best]
            if mode == "spread":
                day_pnl -= (px[worst][k] - px[worst][k - 1]) * pv[worst]
            # costs on rebalance
            if best != prev_long:
                day_pnl -= rt[best] + (rt[prev_long] if prev_long else 0)
            if mode == "spread" and worst != prev_short:
                day_pnl -= rt[worst] + (rt[prev_short] if prev_short else 0)
            prev_long, prev_short = best, worst
            pnl.append(day_pnl); pdates.append(dates[k])
        return pnl, pdates

    print("\n5/6. FIRST-CUT BOARD (minimal predeclared variants):", flush=True)
    results = {}
    for mode in ("rotation", "spread"):
        pnl, pdates = backtest(mode)
        b = board(pnl, pdates, f"carry_{mode}", mnq); results[mode] = b
        if b["verdict"].startswith("KILL"):
            print(f"  carry_{mode}: {b['verdict']} (n={b.get('n')})", flush=True)
        else:
            print(f"  carry_{mode}: {b['verdict']:<16} n={b['n']} PF={b['pf']} med=${b['median']} net=${b['net']} "
                  f"H1/H2={b['h1_pf']}/{b['h2_pf']} top3day={b['top3_day_pct']}% maxyr={b['max_year_pct']}% "
                  f"yrs+={b['yrs_pos']} eras={b['era_pf']} corr_mnq={b['corr_mnq']}", flush=True)
    # benchmark context (NOT a candidate): long-only ZN buy&hold daily
    zn_bh = [(px["ZN"][k] - px["ZN"][k - 1]) * pv["ZN"] for k in range(1, len(j))]
    bh = board(zn_bh, dates[1:], "BENCHMARK_ZN_buyhold", mnq)
    print(f"  [benchmark, not candidate] ZN buy&hold: PF={bh.get('pf')} net=${bh.get('net')} (context only)", flush=True)

    note = ("spread is 1:1 NOT duration-balanced -> dominated by ZB leg; treat as exploratory. "
            "rotation is the cleaner first-cut. Structural feed readiness is NOT evidence.")
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17d_p1p2_rates_carry.json"
    out.write_text(json.dumps({"cycle": "2026-06-17d_p1p2_rates_carry", "mode": "Lane B report-only; FIRST-CUT; NO-LOOKAHEAD; NON-WIRED",
        "feed_rows": len(yc), "join_matched": matched, "coverage_by_year": {int(k): int(v) for k, v in cov.items()},
        "results": results, "benchmark_zn_buyhold": bh, "caveats": note,
        "boundaries": "no sweep/synthetic-fill/activation/registry/scheduler/portfolio/mutation"}, indent=2, default=str))
    print(f"\n  caveat: {note}", flush=True)
    print(f"Wrote: {out}\n(report-only; first-cut; no sweep; no mutation; structural feed-readiness != evidence)", flush=True)


if __name__ == "__main__":
    run()
