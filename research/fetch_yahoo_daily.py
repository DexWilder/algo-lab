"""Fetch Yahoo Finance daily futures — ACQUISITION + STRUCTURAL VALIDATION ONLY.

New reachable source (query1.finance.yahoo.com, non-.gov). Fresh daily continuous front-month
futures — removes the stale-FRED-spot problem (which likely killed P12) and opens many non-gold
instruments. STRICT: fetch + structural validation + provenance ONLY. No screens/edge/labels/
synthetic-fill/mutation.

QUALITY CAVEAT (provenance): Yahoo futures are CONTINUOUS FRONT-MONTH, auto-rolled, generally
unadjusted, retail-grade. Fine for report-only RESEARCH screening; NOT capital-grade (would need
DSCL treatment + a controlled vendor before any deployment). Structural readiness != evidence.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "data" / "feeds"
DL_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}?range=15y&interval=1d"


def fetch(sym):
    enc = urllib.parse.quote(sym)
    req = urllib.request.Request(URL.format(enc), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except Exception as e:
        print(f"  [fail] {sym}: {str(e)[:70]}", flush=True)
        return None
    res = d.get("chart", {}).get("result")
    if not res or not res[0].get("timestamp"):
        print(f"  [no-data] {sym}: {str(d.get('chart',{}).get('error'))[:60]}", flush=True)
        return None
    ts = res[0]["timestamp"]; close = res[0]["indicators"]["quote"][0]["close"]
    s = pd.Series(close, index=pd.to_datetime(pd.to_datetime(ts, unit="s").date))
    return s


def run():
    print(f"Yahoo daily futures acquisition (download_date={DL_DATE}) — STRUCTURAL ONLY\n", flush=True)
    syms = {"wti_f": "CL=F", "brent_f": "BZ=F"}   # fresh energy spread (CL=F - BZ=F)
    cols = {}
    for out, sym in syms.items():
        s = fetch(sym)
        if s is None:
            continue
        s = s[~s.index.duplicated()].dropna()
        cols[out] = s
        print(f"  [ok] {out} <- Yahoo:{sym} n={len(s)} range={s.index.min().date()}..{s.index.max().date()}", flush=True)
    if not cols:
        print("  no data", flush=True); return
    df = pd.concat(cols, axis=1).sort_index().reset_index().rename(columns={"index": "date"})
    df["date"] = pd.to_datetime(df["date"])
    df.to_csv(FEEDS / "energy_futures_yahoo.csv", index=False)
    cc = [c for c in df.columns if c != "date"]
    rep = {"path": str(FEEDS / "energy_futures_yahoo.csv"), "source": "Yahoo Finance query1 chart API (retail-grade, continuous front-month, unadjusted)",
           "download_date": DL_DATE, "symbols": syms, "n_rows": int(len(df)),
           "date_range": [str(df["date"].min().date()), str(df["date"].max().date())],
           "duplicate_dates": int(df["date"].duplicated().sum()),
           "missing_per_col": {c: int(df[c].isna().sum()) for c in cc},
           "quality_caveat": "retail-grade continuous front-month; research-only, NOT capital-grade (needs DSCL + controlled vendor before deployment)",
           "status": "YAHOO_ENERGY_FUTURES_ACQUIRED_STRUCTURAL_ONLY"}
    (ROOT / "research" / "data" / "fql_forge" / "reports" / "yahoo_energy_futures_2026-06-17.json").write_text(json.dumps(rep, indent=2, default=str))
    print(f"\n  n={rep['n_rows']} range={rep['date_range']} dups={rep['duplicate_dates']} missing={rep['missing_per_col']}", flush=True)
    print(f"  STATUS: {rep['status']} (NOT evidence of edge; retail-grade research-only)", flush=True)


if __name__ == "__main__":
    run()
