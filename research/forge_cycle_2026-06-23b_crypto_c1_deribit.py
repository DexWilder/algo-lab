"""Cycle 2026-06-23b — C1 funding mean-reversion on DEEP Deribit funding (report-only).

Retest C1 now that Deribit funding is deep (2020+, same endpoint gives funding + index_price -> same-venue,
no cross-venue mix). Mechanism (predeclared, NO flip): extreme POSITIVE funding = crowded longs paying ->
SHORT next day; extreme NEGATIVE funding = crowded shorts paying -> LONG. Hold 1 day.
PnL DECOMPOSED: price + funding + (-cost) = net. Cuts: pos-extreme vs neg-extreme, long vs short, BTC vs
ETH separate (pooled only if both agree), date-split, rolling-year, top-k tail, cost-stress, no-lookahead.
Verdict: PASS (net survives cost, clean timestamps, both halves sane, not one-tail/one-side) / WATCH / KILL
/ DATA-LIMITED. Report-only; no mutation; no momentum-flip.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "data" / "feeds"


def _get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())


def acquire(inst, start_year=2020):
    def ms(d):
        return int(d.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    rows = []; cur = dt.datetime(start_year, 1, 1)
    end = dt.datetime(2026, 6, 23)
    while cur < end:
        w_end = cur + dt.timedelta(days=31)
        u = (f"https://www.deribit.com/api/v2/public/get_funding_rate_history?instrument_name={inst}"
             f"&start_timestamp={ms(cur)}&end_timestamp={ms(w_end)}")
        try:
            d = _get(u).get("result", [])
        except Exception:
            d = []
        rows += d; cur = w_end; time.sleep(0.12)
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["t"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["day"] = df["t"].dt.normalize()
    df["i8"] = pd.to_numeric(df.get("interest_8h"), errors="coerce")
    df["i1"] = pd.to_numeric(df.get("interest_1h"), errors="coerce")
    df["px"] = pd.to_numeric(df.get("index_price"), errors="coerce")
    g = df.groupby("day").agg(px=("px", "last"), f8=("i8", "mean"), carry=("i1", "sum")).dropna(subset=["px"])
    if g["carry"].isna().all():            # fallback if interest_1h absent
        g["carry"] = g["f8"] * 3
    return g.sort_index()


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def screen(g, inst, z=1.5, rt=0.0012):
    g = g.copy()
    g["fz"] = (g["f8"] - g["f8"].rolling(90, min_periods=45).mean()) / g["f8"].rolling(90, min_periods=45).std()
    g["ret_fwd"] = g["px"].pct_change().shift(-1)
    g["carry_fwd"] = g["carry"].shift(-1)
    g = g.dropna(subset=["fz", "ret_fwd", "carry_fwd"])
    g["dir"] = 0
    g.loc[g["fz"] > z, "dir"] = -1          # crowded longs -> short
    g.loc[g["fz"] < -z, "dir"] = 1          # crowded shorts -> long
    t = g[g["dir"] != 0].copy()
    if len(t) < 60:
        return {"n": len(t), "verdict": "DATA-LIMITED" if len(g) < 300 else "KILL_low_n"}
    t["price"] = t["dir"] * t["ret_fwd"]
    t["funding"] = np.where(t["dir"] == -1, t["carry_fwd"], -t["carry_fwd"])
    t["net"] = t["price"] + t["funding"] - rt
    p = t["net"].to_numpy(); h = len(p) // 2
    g2 = np.sort(p[p > 0])[::-1]; gp = g2.sum()
    longn = t[t["dir"] == 1]["net"]; shortn = t[t["dir"] == -1]["net"]
    by_yr = t.assign(yr=t.index.year).groupby("yr")["net"].sum()
    p20 = (t["price"] + t["funding"] - 0.0020).to_numpy()
    return {"n": len(p), "pf": round(_pf(p), 3), "mean_bps": round(float(p.mean()) * 1e4, 1), "net_pct": round(float(p.sum()) * 100, 1),
            "win%": round(float((p > 0).mean()) * 100, 1), "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "price_pct": round(float(t["price"].sum()) * 100, 1), "funding_pct": round(float(t["funding"].sum()) * 100, 1),
            "long_pf": round(_pf(longn.to_numpy()), 3) if len(longn) else None, "short_pf": round(_pf(shortn.to_numpy()), 3) if len(shortn) else None,
            "long_n": int(len(longn)), "short_n": int(len(shortn)), "max_single_pct_gross": round(float(g2[0]) / gp * 100, 1) if gp > 0 else None,
            "pf_20bps": round(_pf(p20), 3), "yrs_pos": f"{int((by_yr>0).sum())}/{int(by_yr.shape[0])}"}


def run():
    print("Cycle 2026-06-23b — C1 funding mean-reversion on DEEP Deribit (report-only)\n", flush=True)
    res = {}
    for inst in ("BTC-PERPETUAL", "ETH-PERPETUAL"):
        g = acquire(inst)
        if g is None or len(g) < 300:
            print(f"  {inst}: insufficient ({0 if g is None else len(g)} days) -> DATA-LIMITED", flush=True)
            res[inst] = {"verdict": "DATA-LIMITED", "days": 0 if g is None else len(g)}; continue
        g.to_csv(FEEDS / f"deribit_{inst.replace('-','_')}.csv")
        print(f"  {inst}: {len(g)} days {g.index.min().date()}..{g.index.max().date()} (f8 mean {g['f8'].mean()*100:.4f}% std {g['f8'].std()*100:.4f}%)", flush=True)
        r = screen(g, inst); res[inst] = r
        if r.get("verdict", "").startswith(("DATA", "KILL_low")):
            print(f"    z1.5: {r['verdict']} (n={r.get('n')})", flush=True); continue
        ok = (r["pf"] >= 1.2 and r["mean_bps"] > 0 and r["h1_pf"] > 1.0 and r["h2_pf"] > 1.0 and (r["max_single_pct_gross"] or 99) < 30
              and (r["long_pf"] or 0) > 1.0 and (r["short_pf"] or 0) > 1.0 and r["pf_20bps"] >= 1.1)
        r["verdict"] = "PASS" if ok else ("WATCH" if r["pf"] >= 1.1 else "KILL")
        print(f"    z1.5: n={r['n']} PF={r['pf']} mean={r['mean_bps']}bps win={r['win%']}% net={r['net_pct']}% H1/H2={r['h1_pf']}/{r['h2_pf']} "
              f"| price={r['price_pct']}% funding={r['funding_pct']}% | long_pf={r['long_pf']}(n{r['long_n']}) short_pf={r['short_pf']}(n{r['short_n']}) "
              f"| maxsingle={r['max_single_pct_gross']}% PF@20bps={r['pf_20bps']} yrs+={r['yrs_pos']} -> {r['verdict']}", flush=True)

    # pooled only if both BTC+ETH agree (both >=WATCH same mechanism)
    both_ok = all(res.get(i, {}).get("verdict") in ("PASS", "WATCH") for i in ("BTC-PERPETUAL", "ETH-PERPETUAL"))
    print(f"\n  BTC & ETH both support mechanism: {both_ok}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-23b_crypto_c1_deribit.json"
    out.write_text(json.dumps({"cycle": "2026-06-23b_crypto_c1_deribit", "mode": "report-only; deep Deribit funding; NON-WIRED",
        "results": res, "both_support": both_ok, "note": "C1 funding-mean-rev on deep Deribit; PnL decomposed; mechanism-pure no-flip; pos/neg+long/short+date-split+tail+coststress",
        "boundaries": "no sweep beyond z1.5 primary; no mutation; no momentum-flip"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; C1 deep; no mutation)", flush=True)


if __name__ == "__main__":
    run()
