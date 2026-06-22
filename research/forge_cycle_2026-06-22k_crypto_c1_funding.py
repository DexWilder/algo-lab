"""Cycle 2026-06-22k — C1 crypto funding-rate mean-reversion (acquire + screen, report-only).

Mechanism (pure, predeclared, NO flip): extreme POSITIVE funding = crowded longs paying carry -> unwind
-> SHORT perp next day; extreme NEGATIVE funding = crowded shorts paying -> squeeze -> LONG next day.
Daily (OKX funding 8h summed to daily carry; OKX BTC-USD-SWAP 1Dutc perp candles, same venue). NO-LOOKAHEAD:
day-d total funding known at d-close -> decision for d+1; enter d-close, exit d+1-close.
PnL DECOMPOSED: price_ret + funding_pnl + (-cost) = net (separated per operator). BTC first; ETH = confirm only.
Predeclared bands z in {1.0,1.5,2.0}; split-sample; long/short decomposition; tail concentration; cost sensitivity.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "data" / "feeds"
TAKER = 0.0005   # OKX taker ~5bps
SLIP = 0.0002    # 2bps slippage
RT_COST = 2 * (TAKER + SLIP)   # round-trip fraction


def _get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode())


def acquire(inst):
    # funding history (paginate via 'after'=oldest ts)
    fund = []; cur = ""
    for _ in range(50):
        u = f"https://www.okx.com/api/v5/public/funding-rate-history?instId={inst}&limit=100" + (f"&after={cur}" if cur else "")
        d = _get(u).get("data", [])
        if not d:
            break
        fund += d; cur = d[-1]["fundingTime"]; time.sleep(0.05)
    f = pd.DataFrame(fund)
    f["t"] = pd.to_datetime(pd.to_numeric(f["fundingTime"]), unit="ms", utc=True)
    f["fr"] = pd.to_numeric(f["realizedRate"] if "realizedRate" in f else f["fundingRate"], errors="coerce")
    f["day"] = f["t"].dt.normalize()
    daily_f = f.groupby("day")["fr"].sum().rename("funding")   # daily carry = sum of 3 stamps
    # price: Coinbase BTC-USD daily (deep, reachable; paginate 300-day windows back to funding span).
    # venue caveat: funding=OKX-perp, price=Coinbase-spot -> daily perp return ~= spot return (basis is the
    # separately-accounted carry); acceptable for a daily first-cut.
    import datetime as _dt
    start = daily_f.index.min().tz_convert(None).to_pydatetime() if daily_f.index.min().tzinfo else daily_f.index.min().to_pydatetime()
    end = _dt.datetime.utcnow()
    rows = []
    cur_end = end
    for _ in range(40):
        cur_start = cur_end - _dt.timedelta(days=290)
        u = (f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400"
             f"&start={cur_start.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={cur_end.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        d = _get(u)
        if not d:
            break
        rows += d
        cur_end = cur_start
        if cur_start < start - _dt.timedelta(days=5):
            break
        time.sleep(0.15)
    c = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "vol"])
    c["day"] = pd.to_datetime(pd.to_numeric(c["t"]), unit="s", utc=True).dt.normalize()
    c["close"] = pd.to_numeric(c["close"], errors="coerce")
    px = c.drop_duplicates("day").set_index("day")["close"]
    df = pd.concat([px, daily_f], axis=1).dropna().sort_index()
    return df


def screen(df, inst, z_thresh):
    df = df.copy()
    df["fz"] = (df["funding"] - df["funding"].rolling(90, min_periods=45).mean()) / df["funding"].rolling(90, min_periods=45).std()
    df["ret_fwd"] = df["close"].pct_change().shift(-1)        # d -> d+1 price return
    df["fund_fwd"] = df["funding"].shift(-1)                  # funding paid/received during held day d+1
    df = df.dropna(subset=["fz", "ret_fwd", "fund_fwd"])
    # mechanism-pure direction: high funding -> short (-1), low -> long (+1)
    df["dir"] = 0
    df.loc[df["fz"] > z_thresh, "dir"] = -1
    df.loc[df["fz"] < -z_thresh, "dir"] = 1
    t = df[df["dir"] != 0].copy()
    if len(t) < 60:
        return {"z": z_thresh, "n": len(t), "verdict": "KILL_low_n"}
    t["price_pnl"] = t["dir"] * t["ret_fwd"]
    t["funding_pnl"] = np.where(t["dir"] == -1, t["fund_fwd"], -t["fund_fwd"])   # short receives +funding; long pays
    t["cost"] = RT_COST
    t["net"] = t["price_pnl"] + t["funding_pnl"] - t["cost"]
    p = t["net"].to_numpy(); n = len(p)
    pf = lambda a: (a[a > 0].sum() / -a[a < 0].sum()) if (a[a < 0].sum() < 0) else float("inf")
    h = n // 2
    g = np.sort(p[p > 0])[::-1]; gp = g.sum()
    long_net = t[t["dir"] == 1]["net"]; short_net = t[t["dir"] == -1]["net"]
    return {"z": z_thresh, "n": n, "net_ret_sum_pct": round(float(p.sum()) * 100, 1), "pf": round(float(pf(p)), 3),
            "mean_bps": round(float(p.mean()) * 1e4, 2), "win%": round(float((p > 0).mean()) * 100, 1),
            "h1_pf": round(float(pf(p[:h])), 3), "h2_pf": round(float(pf(p[h:])), 3),
            "price_pnl_sum_pct": round(float(t["price_pnl"].sum()) * 100, 1), "funding_pnl_sum_pct": round(float(t["funding_pnl"].sum()) * 100, 1),
            "cost_sum_pct": round(float(t["cost"].sum()) * 100, 1), "max_single_pct_of_gross": round(float(g[0]) / gp * 100, 1) if gp > 0 else None,
            "long_pf": round(float(pf(long_net.to_numpy())), 3) if len(long_net) else None,
            "short_pf": round(float(pf(short_net.to_numpy())), 3) if len(short_net) else None,
            "long_n": int(len(long_net)), "short_n": int(len(short_net))}


def run():
    print("Cycle 2026-06-22k — C1 crypto funding mean-reversion (BTC; report-only)\n", flush=True)
    print(f"cost model: taker {TAKER*1e4:.0f}bps + slip {SLIP*1e4:.0f}bps -> round-trip {RT_COST*100:.2f}%\n", flush=True)
    for inst in ("BTC-USD-SWAP",):
        df = acquire(inst)
        df.to_csv(FEEDS / f"okx_{inst.replace('-','_')}.csv")
        print(f"{inst}: acquired {len(df)} days {df.index.min().date()}..{df.index.max().date()} "
              f"(funding/day mean {df['funding'].mean()*100:.4f}% std {df['funding'].std()*100:.4f}%)", flush=True)
        results = {}
        for z in (1.0, 1.5, 2.0):
            r = screen(df, inst, z); results[f"z{z}"] = r
            if r.get("verdict", "").startswith("KILL"):
                print(f"  z>{z}: {r['verdict']} (n={r['n']})", flush=True); continue
            print(f"  z>{z}: n={r['n']} net={r['net_ret_sum_pct']}% PF={r['pf']} mean={r['mean_bps']}bps win={r['win%']}% "
                  f"H1/H2={r['h1_pf']}/{r['h2_pf']} | price={r['price_pnl_sum_pct']}% funding={r['funding_pnl_sum_pct']}% cost={r['cost_sum_pct']}% "
                  f"| long_pf={r['long_pf']}(n{r['long_n']}) short_pf={r['short_pf']}(n{r['short_n']}) maxsingle={r['max_single_pct_of_gross']}%", flush=True)
        # verdict on z1.5 (predeclared primary)
        r = results.get("z1.5", {})
        if r.get("pf"):
            ok = r["pf"] >= 1.2 and r["mean_bps"] > 0 and r["h1_pf"] > 1.0 and r["h2_pf"] > 1.0 and (r["max_single_pct_of_gross"] or 99) < 30 \
                and (r["long_pf"] or 0) > 1.0 and (r["short_pf"] or 0) > 1.0
            v = "STRUCTURE_FOUND" if ok else ("WATCH" if r["pf"] >= 1.1 else "KILL")
            print(f"\n  VERDICT (z1.5 primary): {v}  (needs both sides>1, both halves>1, net+ after cost+funding, low tail)", flush=True)
            results["verdict"] = v
        out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22k_crypto_c1_funding.json"
        out.write_text(json.dumps({"cycle": "2026-06-22k_crypto_c1_funding", "mode": "report-only; crypto new-vein; NON-WIRED",
            "inst": inst, "cost_model": {"taker": TAKER, "slip": SLIP, "round_trip": RT_COST}, "results": results,
            "note": "daily funding mean-reversion; PnL decomposed price/funding/cost/net; mechanism-pure direction no-flip; BTC first",
            "boundaries": "no sweep beyond predeclared z-band; no mutation"}, indent=2, default=str))
        print(f"\nWrote: {out}\n(report-only; crypto C1; no mutation)", flush=True)


if __name__ == "__main__":
    run()
