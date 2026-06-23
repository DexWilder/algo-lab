"""Cycle 2026-06-23d — C3-FIXED delta-neutral carry, SAME-TIMESTAMP legs (report-only).

Fix for 22c construction-invalid (perp was sampled at funding-stamp ~23:xx UTC vs Coinbase 00:00 UTC ->
hedge not neutral). NOW: Deribit perp DAILY CANDLE close (get_tradingview_chart_data, UTC 00:00) +
Coinbase daily close (UTC 00:00) -> same boundary. HEDGE VALIDATION PRINTED FIRST; verdict only if
hedge clean (corr~0.999, basis-drift std collapses). Else verdict stays CONSTRUCTION-INVALID.
Carry = funding + (spot_ret - perp_ret), held when funding>0; judged Sharpe/DD/consistency/bench-corr.
Report-only; no mutation; no fake short-borrow.
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
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())


def deribit_perp_daily(inst):
    def ms(d):
        return int(d.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    out = {}
    cur = dt.datetime(2020, 1, 1)
    while cur < dt.datetime(2026, 6, 23):
        we = cur + dt.timedelta(days=500)
        r = _get(f"https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name={inst}&resolution=1D&start_timestamp={ms(cur)}&end_timestamp={ms(we)}").get("result", {})
        if r.get("status") == "ok" and r.get("ticks"):
            for tk, cl in zip(r["ticks"], r["close"]):
                out[pd.to_datetime(tk, unit="ms", utc=True).normalize()] = cl
        cur = we; time.sleep(0.12)
    return pd.Series(out).sort_index()


def coinbase_daily(prod):
    rows = []; ce = dt.datetime.utcnow()
    for _ in range(30):
        cs = ce - dt.timedelta(days=290)
        d = _get(f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400&start={cs.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={ce.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        if not d:
            break
        rows += d; ce = cs
        if cs < dt.datetime(2020, 1, 1):
            break
        time.sleep(0.15)
    c = pd.DataFrame(rows, columns=["t", "low", "high", "open", "close", "vol"])
    c["day"] = pd.to_datetime(pd.to_numeric(c["t"]), unit="s", utc=True).dt.normalize()
    c["spot"] = pd.to_numeric(c["close"], errors="coerce")
    return c.drop_duplicates("day").set_index("day")["spot"].sort_index()


def _pf(a):
    a = np.asarray(a, float); l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def daily_mnq():
    df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv"); d = pd.to_datetime(df["datetime"])
    r = df.assign(x=d.dt.normalize()).groupby("x")["close"].last().pct_change()
    r.index = pd.to_datetime(r.index).tz_localize("UTC"); return r


def run():
    print("Cycle 2026-06-23d — C3-FIXED same-timestamp delta-neutral carry (report-only)\n", flush=True)
    fund = pd.read_csv(ROOT / "data" / "feeds" / "deribit_BTC_PERPETUAL.csv", parse_dates=["day"])
    fund["day"] = pd.to_datetime(fund["day"], utc=True); fund = fund.set_index("day")["carry"]
    perp = deribit_perp_daily("BTC-PERPETUAL")
    spot = coinbase_daily("BTC-USD")
    df = pd.DataFrame({"perp": perp, "spot": spot, "carry": fund}).dropna().sort_index()
    df["spot_ret"] = df["spot"].pct_change(); df["perp_ret"] = df["perp"].pct_change()
    df = df.dropna(subset=["spot_ret", "perp_ret"])

    # ---- HEDGE VALIDATION FIRST ----
    corr = float(df["spot_ret"].corr(df["perp_ret"]))
    drift = (df["spot_ret"] - df["perp_ret"])
    print("=== HEDGE VALIDATION (must pass before any verdict) ===", flush=True)
    print(f"  days={len(df)} corr(spot_ret,perp_ret)={corr:.4f} (target ~0.999)", flush=True)
    print(f"  basis-drift (spot_ret-perp_ret) std={drift.std()*100:.3f}% mean={drift.mean()*1e4:.2f}bps (target std ~0.1-0.2%)", flush=True)
    print(f"  perp/spot level ratio mean={float((df['perp']/df['spot']).mean()):.4f}", flush=True)
    hedge_ok = corr >= 0.99 and drift.std() < 0.004
    print(f"  HEDGE CLEAN: {hedge_ok} ({'proceed to carry verdict' if hedge_ok else 'STILL CONSTRUCTION-INVALID -> no verdict'})", flush=True)
    if not hedge_ok:
        out = {"cycle": "2026-06-23d_crypto_c3_fixed", "hedge": {"corr": round(corr, 4), "drift_std_pct": round(drift.std() * 100, 3)},
               "verdict": "CONSTRUCTION-INVALID", "note": "same-timestamp legs still not clean enough; carry not judged"}
        (ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-23d_crypto_c3_fixed.json").write_text(json.dumps(out, indent=2))
        print("\n  -> verdict CONSTRUCTION-INVALID (hedge not clean); no carry metrics reported.", flush=True)
        return

    # ---- carry (hedge validated) ----
    mnq = daily_mnq(); RT = 0.0030
    df["fz"] = (df["carry"] - df["carry"].rolling(90, min_periods=45).mean()) / df["carry"].rolling(90, min_periods=45).std()
    res = {}
    for vlabel, mask in [("V1_funding>0", df["carry"] > 0), ("V2_funding_z>1", df["fz"] > 1)]:
        for cost, cl in [(RT, "30bps"), (0.0050, "50bps")]:
            m = mask.fillna(False).values.astype(int)
            daily = df["carry"].values + (df["spot_ret"].values - df["perp_ret"].values)
            pnl = np.where(m == 1, daily, 0.0) - np.abs(np.diff(np.concatenate([[0], m]))) * cost
            s = pd.Series(pnl, index=df.index)
            ann = float(s.mean()) * 365; vol = float(s.std()) * np.sqrt(365); sh = ann / vol if vol > 0 else 0
            eq = s.cumsum(); dd = float((eq - eq.cummax()).min()); yr = s.groupby(s.index.year).sum()
            al = pd.concat([s.rename("a"), mnq.rename("b")], axis=1).fillna(0.0); cm = round(float(al["a"].corr(al["b"])), 3)
            h = len(s) // 2
            mm = {"ann_pct": round(ann * 100, 1), "vol_pct": round(vol * 100, 1), "sharpe": round(sh, 2), "maxdd_pct": round(dd * 100, 1),
                  "net_pct": round(float(s.sum()) * 100, 1), "days": int((pnl != 0).sum()), "yrs_pos": f"{int((yr>0).sum())}/{int(yr.shape[0])}",
                  "corr_mnq": cm, "h1": round(float(s.iloc[:h].sum()) * 100, 1), "h2": round(float(s.iloc[h:].sum()) * 100, 1)}
            if cl == "30bps":
                res[vlabel] = mm
                ok = sh >= 1.0 and mm["net_pct"] > 0 and abs(cm) < 0.3 and "0/" not in mm["yrs_pos"] and mm["h1"] > 0 and mm["h2"] > 0
                res[vlabel]["verdict"] = "PASS" if ok else ("WATCH" if sh >= 0.5 and mm["net_pct"] > 0 else "KILL")
            print(f"  {vlabel} @{cl}: ann={mm['ann_pct']}% vol={mm['vol_pct']}% Sharpe={mm['sharpe']} maxDD={mm['maxdd_pct']}% net={mm['net_pct']}% "
                  f"days={mm['days']} yrs+={mm['yrs_pos']} corrMNQ={mm['corr_mnq']} H1/H2={mm['h1']}/{mm['h2']}%" + (f" -> {res[vlabel]['verdict']}" if cl == "30bps" else " [stress]"), flush=True)
    out = {"cycle": "2026-06-23d_crypto_c3_fixed", "hedge": {"corr": round(corr, 4), "drift_std_pct": round(drift.std() * 100, 3), "clean": True},
           "results": res, "note": "delta-neutral funding carry, same-timestamp legs validated; judged Sharpe/consistency/bench-corr"}
    (ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-23d_crypto_c3_fixed.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\nWrote screen JSON.\n(report-only; C3-fixed; no mutation)", flush=True)


if __name__ == "__main__":
    run()
