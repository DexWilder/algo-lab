"""Cycle 2026-06-23e — O1 DVOL variance-risk-premium (report-only).

Pivot from C3 (DATA-BLOCKED) to the Deribit options/vol vein. DVOL = Deribit BTC implied-vol index
(VIX-equivalent), deep daily history, single clean series -> NO perp/index hedge-timestamp problem.

Harvesting VRP directly needs option premia history (NOT reachable). The CONSTRUCTIBLE expression is
VRP-CONDITIONED SPOT DIRECTION: VRP = DVOL(implied) - trailing realized vol. Mechanism / forced
participant: during fear, option buyers OVERPAY for protection (implied >> realized) -> the premium is
historically overcompensated -> contrarian LONG spot bias when VRP is rich. PREDECLARED direction, NO flip:
  - rich VRP (IV-RV high, z>1)  -> LONG spot next period (fear overpriced)
  - we do NOT flip to short if long fails (that would be complacency-fade = a different, un-predeclared story)
No-lookahead: DVOL_t and realized_t use info up to and incl day t; trade return is day t+1 (shift -1).
Judge as a CONDITIONAL DIRECTIONAL sleeve: PF, both-halves, top-k concentration, yrs+, cost-stress,
bench-correlation to MNQ. Report-only; no mutation. KILL if direction wrong / not cost-robust / one-tail.
"""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "data" / "feeds"


def _get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())


def _ms(d):
    return int(d.replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


def acquire_dvol(currency="BTC"):
    """Deribit DVOL daily OHLC, paginated. Returns Series of daily close (vol points, e.g. 65.0 = 65% annualized)."""
    out = {}
    cur = dt.datetime(2021, 3, 1)   # DVOL history starts ~2021
    end = dt.datetime(2026, 6, 23)
    while cur < end:
        we = cur + dt.timedelta(days=300)
        u = (f"https://www.deribit.com/api/v2/public/get_volatility_index_data?currency={currency}"
             f"&start_timestamp={_ms(cur)}&end_timestamp={_ms(we)}&resolution=86400")
        try:
            data = _get(u).get("result", {}).get("data", [])
        except Exception:
            data = []
        for row in data:                       # [ts, open, high, low, close]
            out[pd.to_datetime(row[0], unit="ms", utc=True).normalize()] = float(row[4])
        cur = we; time.sleep(0.12)
    return pd.Series(out).sort_index() if out else None


def coinbase_daily(prod, start_year=2021):
    rows = []; ce = dt.datetime.utcnow()
    for _ in range(30):
        cs = ce - dt.timedelta(days=290)
        d = _get(f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity=86400"
                 f"&start={cs.strftime('%Y-%m-%dT%H:%M:%SZ')}&end={ce.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        if not d:
            break
        rows += d; ce = cs
        if cs < dt.datetime(start_year, 1, 1):
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


def screen(df, mnq, label, rt=0.0010):
    """df: spot, dvol aligned daily. VRP = dvol - realized(annualized). Predeclared LONG when VRP z>1."""
    df = df.copy()
    df["ret"] = df["spot"].pct_change()
    # realized vol: trailing 30d, annualized to vol points (×100 to match DVOL units)
    df["rv"] = df["ret"].rolling(30, min_periods=20).std() * np.sqrt(365) * 100
    df["vrp"] = df["dvol"] - df["rv"]
    df["vrp_z"] = (df["vrp"] - df["vrp"].rolling(120, min_periods=60).mean()) / df["vrp"].rolling(120, min_periods=60).std()
    df["ret_fwd"] = df["ret"].shift(-1)        # trade next day, no lookahead
    df = df.dropna(subset=["vrp_z", "ret_fwd"])
    # predeclared: rich VRP (z>1) -> LONG next day
    t = df[df["vrp_z"] > 1.0].copy()
    if len(t) < 60:
        return {"label": label, "n": int(len(t)), "verdict": "DATA-LIMITED" if len(df) < 300 else "KILL_low_n"}
    t["pnl"] = t["ret_fwd"] - rt              # long; cost per entry (held 1d)
    p = t["pnl"].to_numpy(); h = len(p) // 2
    gp = np.sort(p[p > 0])[::-1]; gpsum = gp.sum()
    by_yr = t.assign(yr=t.index.year).groupby("yr")["pnl"].sum()
    al = pd.concat([t["pnl"].rename("a"), mnq.rename("b")], axis=1).dropna()
    cm = round(float(al["a"].corr(al["b"])), 3) if len(al) > 30 else None
    p20 = (t["ret_fwd"] - 0.0020).to_numpy()
    # baseline: unconditional next-day long over same window (is the signal better than just being long?)
    base = (df["ret_fwd"] - rt).to_numpy()
    r = {"label": label, "n": int(len(p)), "pf": round(_pf(p), 3), "mean_bps": round(float(p.mean()) * 1e4, 1),
         "net_pct": round(float(p.sum()) * 100, 1), "win%": round(float((p > 0).mean()) * 100, 1),
         "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
         "max_single_pct_gross": round(float(gp[0]) / gpsum * 100, 1) if gpsum > 0 else None,
         "top3_pct_gross": round(float(gp[:3].sum()) / gpsum * 100, 1) if gpsum > 0 else None,
         "pf_20bps": round(_pf(p20), 3), "yrs_pos": f"{int((by_yr>0).sum())}/{int(by_yr.shape[0])}",
         "corr_mnq": cm, "base_pf_uncond": round(_pf(base), 3), "base_mean_bps": round(float(base.mean()) * 1e4, 1)}
    edge_over_base = r["mean_bps"] > r["base_mean_bps"]      # conditional must beat unconditional long
    ok = (r["pf"] >= 1.2 and r["mean_bps"] > 0 and r["h1_pf"] > 1.0 and r["h2_pf"] > 1.0
          and (r["max_single_pct_gross"] or 99) < 35 and r["pf_20bps"] >= 1.1
          and "0/" not in r["yrs_pos"] and edge_over_base)
    r["edge_over_uncond_long"] = edge_over_base
    r["verdict"] = "PASS" if ok else ("WATCH" if r["pf"] >= 1.15 and edge_over_base else "KILL")
    return r


def run():
    print("Cycle 2026-06-23e — O1 DVOL variance-risk-premium (report-only)\n", flush=True)
    mnq = daily_mnq()
    res = {}
    for cur, prod in [("BTC", "BTC-USD"), ("ETH", "ETH-USD")]:
        dvol = acquire_dvol(cur)
        if dvol is None or len(dvol) < 300:
            print(f"  {cur}: DVOL insufficient ({0 if dvol is None else len(dvol)}) -> DATA-LIMITED", flush=True)
            res[cur] = {"verdict": "DATA-LIMITED"}; continue
        dvol.to_csv(FEEDS / f"deribit_DVOL_{cur}.csv")
        spot = coinbase_daily(prod)
        df = pd.DataFrame({"spot": spot, "dvol": dvol}).dropna().sort_index()
        print(f"  {cur}: DVOL {len(dvol)}d {dvol.index.min().date()}..{dvol.index.max().date()} (mean {dvol.mean():.1f} vol pts) | aligned {len(df)}d", flush=True)
        r = screen(df, mnq, cur); res[cur] = r
        if r.get("verdict", "").startswith(("DATA", "KILL_low")):
            print(f"    VRP_z>1 LONG: {r['verdict']} (n={r.get('n')})", flush=True); continue
        print(f"    VRP_z>1 LONG: n={r['n']} PF={r['pf']} mean={r['mean_bps']}bps win={r['win%']}% net={r['net_pct']}% "
              f"H1/H2={r['h1_pf']}/{r['h2_pf']} maxsingle={r['max_single_pct_gross']}% top3={r['top3_pct_gross']}% "
              f"PF@20bps={r['pf_20bps']} yrs+={r['yrs_pos']} corrMNQ={r['corr_mnq']} | "
              f"vs-uncond-long: {r['mean_bps']} vs {r['base_mean_bps']}bps (edge={r['edge_over_uncond_long']}) -> {r['verdict']}", flush=True)

    both = all(res.get(c, {}).get("verdict") in ("PASS", "WATCH") for c in ("BTC", "ETH"))
    print(f"\n  BTC & ETH both support O1 mechanism: {both}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-23e_crypto_o1_dvol_vrp.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cycle": "2026-06-23e_crypto_o1_dvol_vrp", "mode": "report-only; DVOL VRP-conditioned spot direction; NON-WIRED",
        "results": res, "both_support": both,
        "note": "DVOL implied vs 30d realized -> rich VRP (z>1) predeclared LONG spot (fear overpriced); NO flip; must beat unconditional-long; full gates + cost-stress + bench-corr",
        "boundaries": "report-only; no mutation; mechanism-implied direction; option-premia VRP harvest not reachable so tested as conditional spot sleeve"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; O1 DVOL; no mutation)", flush=True)


if __name__ == "__main__":
    run()
