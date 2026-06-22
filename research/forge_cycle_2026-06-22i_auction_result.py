"""Cycle 2026-06-22i — P-AUC-RESULT: auction-result-conditioned reaction (report-only).

Mechanism packet (NOT z-score fishing): demand strength = bid-to-cover vs that tenor's trailing norm.
Forced participant: dealers absorbing a WEAK auction (low bid-to-cover) must distribute inventory ->
concession persists -> SHORT matched future; STRONG auction -> relief -> LONG. Direction IMPLIED by
the mechanism. NO-LOOKAHEAD: bid-to-cover public at auction result (~1pm ET T0) -> entry at T0 daily
close (after results), exit T+2. By-tenor (exact parse), contamination-clean (FOMC/CPI/NFP/month-end/
roll), OOS, cost-aware, sample floor. The untested branch after vanilla auction windows KILLed. No sweep.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402

TENOR_FUT = {2: "ZF", 3: "ZF", 5: "ZF", 7: "ZN", 10: "ZN", 20: "ZB", 30: "ZB"}
STD = [2, 3, 5, 7, 10, 20, 30]


def tenor_years(term):
    if "Week" in str(term) or "Day" in str(term):
        return None
    ym = re.search(r"(\d+)\s*-?\s*Year", str(term))
    if not ym:
        return None
    y = int(ym.group(1)); mm = re.search(r"(\d+)\s*-?\s*Month", str(term))
    if mm:
        y += int(mm.group(1)) / 12.0
    return min(STD, key=lambda t: abs(t - y))


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def first_fridays(yrs):
    o = []
    for y in yrs:
        for m in range(1, 13):
            d = pd.Timestamp(y, m, 1)
            while d.weekday() != 4:
                d += pd.Timedelta(days=1)
            o.append(d.normalize())
    return o


def run():
    print("Cycle 2026-06-22i — auction-result-conditioned (demand strength -> matched future) (REPORT-ONLY)\n", flush=True)
    url = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
           "?fields=auction_date,security_type,security_term,bid_to_cover_ratio"
           "&filter=auction_date:gte:2019-01-01,security_type:in:(Note,Bond)&page[size]=2000&format=json")
    a = pd.DataFrame(json.loads(urllib.request.urlopen(url, timeout=60).read().decode())["data"])
    a["auction_date"] = pd.to_datetime(a["auction_date"]); a["yrs"] = a["security_term"].map(tenor_years)
    a["fut"] = a["yrs"].map(TENOR_FUT); a["btc"] = pd.to_numeric(a["bid_to_cover_ratio"], errors="coerce")
    a = a.dropna(subset=["yrs", "btc", "fut"]).sort_values(["yrs", "auction_date"])
    # demand surprise = btc - trailing mean of PRIOR same-tenor auctions (no-lookahead within tenor)
    a["btc_norm"] = a.groupby("yrs")["btc"].transform(lambda x: x.shift(1).rolling(8, min_periods=4).mean())
    a["demand"] = a["btc"] - a["btc_norm"]
    a = a.dropna(subset=["demand"])

    fomc = set(pd.Timestamp(c["actual_date"]).normalize() for c in build_official_fomc_calendar())
    nfp = set(first_fridays(range(2019, 2027)))
    try:
        import research.forge_cpi_calendar_verified as cc
        cpi = set(pd.Timestamp(c["actual_date"]).normalize() for c in cc.build_verified_cpi_calendar())
    except Exception:
        cpi = set()
    ROLL = {2, 5, 8, 11}

    results = {}
    for fut in ("ZF", "ZN", "ZB"):
        s = daily_close(fut); s = s[s.index.year >= 2019]; days = list(s.index); dset = set(days)
        pv = ASSETS[fut]["point_value"]; cp = get_cost_params(fut)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        sub = a[a["fut"] == fut]
        rows = []
        mdays = {}
        for d in days:
            mdays.setdefault((d.year, d.month), []).append(d)
        for _, r in sub.iterrows():
            ad = r["auction_date"].normalize()
            while ad not in dset and ad < days[-1]:
                ad += pd.Timedelta(days=1)
            if ad not in dset:
                continue
            i = days.index(ad)
            if i + 2 >= len(days):
                continue
            side = 1.0 if r["demand"] > 0 else -1.0   # strong demand->long, weak->short
            pnl = side * (s.loc[days[i + 2]] - s.loc[ad]) * pv - rt   # entry T0 close (post-results) -> T+2
            me = mdays[(ad.year, ad.month)]
            contam = (any(abs((ad - f).days) <= 3 for f in fomc) or any(abs((ad - f).days) <= 2 for f in cpi)
                      or any(abs((ad - f).days) <= 2 for f in nfp) or ad in me[-3:] or (ad.month in ROLL and ad.day >= 20))
            rows.append({"pnl": float(pnl), "year": ad.year, "contam": contam, "strong": side > 0})
        tr = pd.DataFrame(rows)
        clean = tr[~tr["contam"]]
        for label, d in [("ALL", tr), ("clean", clean)]:
            if len(d) < 40:
                continue
            p = d["pnl"].to_numpy(); h = len(p) // 2; py = d.groupby("year")["pnl"].sum()
            g = np.sort(p[p > 0])[::-1]; gp = float(p[p > 0].sum())
            m = {"n": len(p), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "pos": round(float((p > 0).mean()), 2),
                 "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3), "max_single_pct": round(float(g[0]) / gp * 100, 1) if gp > 0 else None,
                 "max_year_pct": round(float(py.abs().max() / d["pnl"].sum() * 100), 1) if d["pnl"].sum() else None}
            if label == "clean":
                ok = m["pf"] >= 1.3 and m["pos"] >= 0.55 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and (m["max_single_pct"] or 99) < 35 and (m["max_year_pct"] or 99) < 50
                v = "STRUCTURE_FOUND_tail" if ok else ("WATCH_tail" if m["pf"] >= 1.2 else "KILL")
                results[fut] = {**m, "verdict": v}
                # also report strong vs weak split for diagnostic
                sw = {grp: round(_pf(d[d["strong"] == (grp == "strong")]["pnl"]), 3) for grp in ("strong", "weak")}
                print(f"  {fut} clean: n={m['n']} PF={m['pf']} net=${m['net']} pos={m['pos']} H1/H2={m['h1_pf']}/{m['h2_pf']} "
                      f"max-single={m['max_single_pct']}% max-yr={m['max_year_pct']}% | strong/weak PF={sw} -> {v}", flush=True)
            else:
                print(f"  {fut} ALL: n={m['n']} PF={m['pf']} net=${m['net']} pos={m['pos']}", flush=True)

    surv = [k for k, v in results.items() if v["verdict"].startswith(("STRUCTURE", "WATCH"))]
    print(f"\n  survivors: {surv or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22i_auction_result.json"
    out.write_text(json.dumps({"cycle": "2026-06-22i_auction_result", "mode": "Lane B report-only; auction-result mechanism packet; NON-WIRED",
        "results": results, "note": "demand=btc vs trailing tenor norm; strong->long/weak->short matched future T0(post-results)->T+2; contamination-clean",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; mechanism packet; no mutation)", flush=True)


if __name__ == "__main__":
    run()
