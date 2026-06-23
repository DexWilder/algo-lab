"""Cycle 2026-06-23c — C3 delta-neutral funding/basis CARRY (report-only).

Mechanistically-correct funding expression (C1 directional KILLed). LONG spot / SHORT perp to HARVEST
funding while delta-hedged. Forced participant: leveraged longs pay funding to the hedged carry-provider.
Judge by Sharpe/consistency/maxDD/bench-correlation (market-neutral), NOT directional PF.

PnL decomposed daily (delta-neutral, $1 long spot + $1 short perp): funding_received(+carry when funding>0,
short receives) + price_leg(spot_ret - perp_ret = basis drift, ~0) ; costs at regime entry/exit (both legs).
Deribit funding+perp(px) [have] + Coinbase spot [acquire], timestamp-aligned. NO fake short-borrow (long-spot/
short-perp only; mirror excluded). Predeclared variants: V1 hold while funding>0; V2 hold while funding z>1.
Conservative cost 0.30% round-trip both legs, stress 0.50%. Date-split, rolling-year, cost-stress. Report-only.
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


def coinbase_daily(prod, start):
    rows = []; cur_end = dt.datetime.utcnow()
    for _ in range(40):
        cs = cur_end - dt.timedelta(days=290)
        u = (f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400"
             f"&start={cs.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={cur_end.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        d = _get(u)
        if not d:
            break
        rows += d; cur_end = cs
        if cs < start - dt.timedelta(days=5):
            break
        time.sleep(0.15)
    c = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "vol"])
    c["day"] = pd.to_datetime(pd.to_numeric(c["t"]), unit="s", utc=True).dt.normalize()
    c["spot"] = pd.to_numeric(c["close"], errors="coerce")
    return c.drop_duplicates("day").set_index("day")["spot"].sort_index()


def carry_bt(df, hold_mask, rt_cost):
    """df has spot_ret, perp_ret, carry (daily funding, short receives +). hold_mask: bool per day (in position).
    daily net (while held) = carry + (spot_ret - perp_ret); cost on entry+exit transitions."""
    m = hold_mask.values.astype(int)
    daily = df["carry"].values + (df["spot_ret"].values - df["perp_ret"].values)
    pnl = np.where(m == 1, daily, 0.0)
    trans = np.abs(np.diff(np.concatenate([[0], m])))   # 1 at each enter/exit
    pnl = pnl - trans * rt_cost
    return pd.Series(pnl, index=df.index)


def metrics(pnl, mnq_ret):
    p = pnl[pnl != 0] if (pnl != 0).any() else pnl
    s = pnl  # full daily series incl flat days for Sharpe/vol
    ann = float(s.mean()) * 365
    vol = float(s.std()) * np.sqrt(365)
    sharpe = ann / vol if vol > 0 else 0.0
    eq = s.cumsum(); dd = float((eq - eq.cummax()).min())
    yr = s.groupby(s.index.year).sum()
    al = pd.concat([s.rename("a"), mnq_ret.rename("b")], axis=1).fillna(0.0)
    corr = round(float(al["a"].corr(al["b"])), 3)
    h = len(s) // 2
    return {"ann_ret_pct": round(ann * 100, 1), "ann_vol_pct": round(vol * 100, 1), "sharpe": round(sharpe, 2),
            "max_dd_pct": round(dd * 100, 1), "net_pct": round(float(s.sum()) * 100, 1), "days_in_pos": int((pnl != 0).sum()),
            "yrs_pos": f"{int((yr>0).sum())}/{int(yr.shape[0])}", "corr_mnq": corr,
            "h1_net_pct": round(float(s.iloc[:h].sum()) * 100, 1), "h2_net_pct": round(float(s.iloc[h:].sum()) * 100, 1)}


def daily_mnq():
    df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv"); dt2 = pd.to_datetime(df["datetime"])
    c = df.assign(d=dt2.dt.normalize()).groupby("d")["close"].last()
    r = c.pct_change(); r.index = pd.to_datetime(r.index).tz_localize("UTC"); return r


def run():
    print("Cycle 2026-06-23c — C3 delta-neutral funding/basis CARRY (report-only)\n", flush=True)
    RT = 0.0030  # 0.30% round-trip both legs (conservative); stress 0.50%
    mnq = daily_mnq()
    out = {}
    for perp_csv, spot_prod, name in [("deribit_BTC_PERPETUAL.csv", "BTC-USD", "BTC"), ("deribit_ETH_PERPETUAL.csv", "ETH-USD", "ETH")]:
        d = pd.read_csv(ROOT / "data" / "feeds" / perp_csv, parse_dates=["day"]).set_index("day")
        d.index = pd.to_datetime(d.index, utc=True)
        spot = coinbase_daily(spot_prod, d.index.min().tz_convert(None).to_pydatetime())
        spot.index = pd.to_datetime(spot.index, utc=True)
        df = pd.DataFrame({"perp": d["px"], "carry": d["carry"], "spot": spot}).dropna().sort_index()
        df["spot_ret"] = df["spot"].pct_change(); df["perp_ret"] = df["perp"].pct_change()
        df["fz"] = (df["carry"] - df["carry"].rolling(90, min_periods=45).mean()) / df["carry"].rolling(90, min_periods=45).std()
        df = df.dropna(subset=["spot_ret", "perp_ret", "fz"])
        print(f"  {name}: {len(df)} days {df.index.min().date()}..{df.index.max().date()} | mean daily carry {df['carry'].mean()*100:.4f}% (~{df['carry'].mean()*365*100:.1f}%/yr gross if always-on)", flush=True)
        res = {}
        for vlabel, mask in [("V1_funding>0", df["carry"] > 0), ("V2_funding_z>1", df["fz"] > 1)]:
            for cost, clabel in [(RT, "30bps"), (0.0050, "50bps")]:
                pnl = carry_bt(df, mask, cost); m = metrics(pnl, mnq)
                if clabel == "30bps":
                    res[vlabel] = m
                    ok = m["sharpe"] >= 1.0 and m["net_pct"] > 0 and abs(m["corr_mnq"]) < 0.3 and "0/" not in m["yrs_pos"] and m["h1_net_pct"] > 0 and m["h2_net_pct"] > 0
                    res[vlabel]["verdict_30bps"] = "PASS" if ok else ("WATCH" if m["sharpe"] >= 0.5 and m["net_pct"] > 0 else "KILL")
                print(f"    {vlabel} @{clabel}: ann={m['ann_ret_pct']}% vol={m['ann_vol_pct']}% Sharpe={m['sharpe']} maxDD={m['max_dd_pct']}% "
                      f"net={m['net_pct']}% days={m['days_in_pos']} yrs+={m['yrs_pos']} corrMNQ={m['corr_mnq']} H1/H2={m['h1_net_pct']}/{m['h2_net_pct']}%"
                      + (f" -> {res[vlabel]['verdict_30bps']}" if clabel == "30bps" else " [stress]"), flush=True)
        out[name] = res
    o = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-23c_crypto_c3_carry.json"
    o.write_text(json.dumps({"cycle": "2026-06-23c_crypto_c3_carry", "mode": "report-only; delta-neutral carry; NON-WIRED",
        "cost_rt": RT, "results": out, "note": "long-spot/short-perp funding harvest; judged Sharpe/consistency/corr not PF; no fake short-borrow; cost-stressed 30/50bps; market-neutral ensemble candidate",
        "boundaries": "no mutation; report-only; ensemble-candidate eval not promotion"}, indent=2, default=str))
    print(f"\nWrote: {o}\n(report-only; C3 carry; no mutation)", flush=True)


if __name__ == "__main__":
    run()
