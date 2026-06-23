"""Cycle 2026-06-23a — C5 crypto weekend-liquidity (price-only, deep; report-only).

First rung of the crypto PRICE ladder (price-only -> deep history, no funding-depth limit). Crypto is
24/7; weekends are thin (institutions out). Two parts:
  (1) EXPLORATORY day-of-week return map (BTC/ETH/SOL) — is weekend/Monday distinct? (honest map, like
      the futures day-of-week cycle; not a predeclared direction).
  (2) PREDECLARED mechanism: thin-weekend OVERSHOOT -> Monday FADES the weekend move. Enter Sun-close,
      exit Mon-close, direction = -sign(Fri->Sun move). Single predeclared direction (mechanism=mean-rev);
      if it loses, do NOT flip to continuation (that needs a separate momentum thesis). Cost-aware
      (crypto costs HIGH -> stress 20/40bps round-trip), date-split, by-coin, tail check.
Deep price via Coinbase daily. Report-only; no mutation.
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


def _get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read())


def coinbase_daily(prod):
    rows = []; cur_end = dt.datetime.utcnow()
    for _ in range(40):
        cur_start = cur_end - dt.timedelta(days=290)
        u = (f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400"
             f"&start={cur_start.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={cur_end.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        d = _get(u)
        if not d:
            break
        rows += d; cur_end = cur_start; time.sleep(0.15)
    c = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "vol"])
    c["day"] = pd.to_datetime(pd.to_numeric(c["t"]), unit="s", utc=True).dt.normalize()
    c["close"] = pd.to_numeric(c["close"], errors="coerce")
    return c.drop_duplicates("day").set_index("day")["close"].sort_index()


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def run():
    print("Cycle 2026-06-23a — C5 crypto weekend-liquidity (price-only; report-only)\n", flush=True)
    RT = 0.0020  # 20bps round-trip (competitive crypto spot); stress 40bps
    out_all = {}
    for prod in ("BTC-USD", "ETH-USD", "SOL-USD"):
        s = coinbase_daily(prod)
        if len(s) < 400:
            print(f"  {prod}: only {len(s)} days -> skip"); continue
        ret = s.pct_change()
        wd = s.index.weekday  # 0=Mon..6=Sun
        # (1) day-of-week mean return (exploratory)
        dow = {int(d): round(float(ret[wd == d].mean()) * 1e4, 1) for d in range(7)}  # bps
        print(f"  {prod} ({len(s)}d {s.index.min().date()}..{s.index.max().date()}) DoW mean ret bps {{Mon..Sun}}: {[dow[d] for d in range(7)]}", flush=True)
        # (2) predeclared weekend-reversion: weekend move Fri(4)->Sun(6), trade Sun-close->Mon-close, dir=-sign(weekend)
        df = pd.DataFrame({"close": s}); df["wd"] = wd
        fri = df[df["wd"] == 4]["close"]; sun = df[df["wd"] == 6]["close"]; mon = df[df["wd"] == 0]["close"]
        recs = []
        sun_idx = list(sun.index)
        for sd in sun_idx:
            # find prior Friday (sd-2) and next Monday (sd+1)
            fd = sd - pd.Timedelta(days=2); md = sd + pd.Timedelta(days=1)
            if fd in df.index and sd in df.index and md in df.index:
                wmove = (df.loc[sd, "close"] - df.loc[fd, "close"]) / df.loc[fd, "close"]
                mon_ret = (df.loc[md, "close"] - df.loc[sd, "close"]) / df.loc[sd, "close"]
                d = -np.sign(wmove)  # FADE the weekend move
                if d == 0:
                    continue
                recs.append({"date": md, "net": d * mon_ret - RT, "gross": d * mon_ret, "yr": md.year, "dir": d})
        t = pd.DataFrame(recs)
        if len(t) < 100:
            out_all[prod] = {"dow_bps": dow, "n": len(t), "verdict": "KILL_low_n"}; continue
        p = t["net"].to_numpy(); h = len(p) // 2
        gpos = np.sort(p[p > 0])[::-1]; gp = gpos.sum()
        # stress 40bps
        p40 = (t["gross"] - 0.0040).to_numpy()
        m = {"dow_bps": dow, "n": len(p), "pf": round(_pf(p), 3), "mean_bps": round(float(p.mean()) * 1e4, 1),
             "win%": round(float((p > 0).mean()) * 100, 1), "net_sum_pct": round(float(p.sum()) * 100, 1),
             "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
             "pf_40bps": round(_pf(p40), 3), "max_single_pct_gross": round(float(gpos[0]) / gp * 100, 1) if gp > 0 else None}
        ok = m["pf"] >= 1.2 and m["mean_bps"] > 0 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and m["pf_40bps"] >= 1.1 and (m["max_single_pct_gross"] or 99) < 30
        m["verdict"] = "STRUCTURE_FOUND" if ok else ("WATCH" if m["pf"] >= 1.1 else "KILL")
        out_all[prod] = m
        print(f"    weekend-FADE: n={m['n']} PF={m['pf']} mean={m['mean_bps']}bps win={m['win%']}% net={m['net_sum_pct']}% "
              f"H1/H2={m['h1_pf']}/{m['h2_pf']} PF@40bps={m['pf_40bps']} maxsingle={m['max_single_pct_gross']}% -> {m['verdict']}", flush=True)

    surv = [k for k, v in out_all.items() if v.get("verdict", "").startswith(("STRUCTURE", "WATCH"))]
    print(f"\n  survivors: {surv or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-23a_crypto_c5_weekend.json"
    out.write_text(json.dumps({"cycle": "2026-06-23a_crypto_c5_weekend", "mode": "report-only; crypto price ladder rung1; NON-WIRED",
        "cost_rt": RT, "results": out_all, "note": "weekend FADE predeclared (mean-rev); no flip to continuation; cost-stressed 20/40bps; DERIBIT funding deep (2020+) -> C1/C3 retestable next",
        "boundaries": "no sweep/mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; crypto C5; no mutation)", flush=True)


if __name__ == "__main__":
    run()
