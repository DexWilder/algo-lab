"""Fetch FRED driver series (batch 2) — ACQUISITION + STRUCTURAL VALIDATION ONLY.

State FRED_YIELD_CURVE_BRANCH_CLOSED__FORGE_DISCOVERY_CONTINUES: keep expanding the
information surface. These are NEW daily market-based external drivers (real rates,
inflation expectations, dollar, vol, energy) — several attach to gold (our live edge) via
a new driver dimension. STRICT: fetch + structural validation + provenance ONLY. NO screens,
NO edge, NO PASS/WATCH/KILL, NO synthetic fill, NO mutation. Structural readiness != evidence.
"""
from __future__ import annotations

import io
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "data" / "feeds"
DL_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def fetch(sid):
    try:
        with urllib.request.urlopen(URL.format(sid), timeout=30) as r:
            raw = r.read().decode("utf-8")
        if "<html" in raw[:200].lower():
            return None
        df = pd.read_csv(io.StringIO(raw))
        dc = df.columns[0]
        df[dc] = pd.to_datetime(df[dc], errors="coerce")
        df[sid] = pd.to_numeric(df[sid].replace(".", pd.NA), errors="coerce")
        return df.set_index(dc)[sid]
    except Exception as e:
        print(f"  [fail] {sid}: {str(e)[:70]}", flush=True)
        return None


def write_feed(fname, series_map):
    cols = {}
    for out, sid in series_map.items():
        s = fetch(sid)
        if s is None:
            print(f"  [skip] {out} ({sid})", flush=True)
            continue
        cols[out] = s
        d = s.dropna()
        print(f"  [ok] {out} <- FRED:{sid} n={s.notna().sum()} range={d.index.min().date()}..{d.index.max().date()}", flush=True)
    if not cols:
        return None
    df = pd.concat(cols, axis=1).sort_index().reset_index()
    df = df.rename(columns={df.columns[0]: "date"})
    df.to_csv(FEEDS / fname, index=False)
    cc = [c for c in df.columns if c != "date"]
    return {"path": str(FEEDS / fname), "series_map": series_map, "n_rows": int(len(df)),
            "date_range": [str(df["date"].min().date()), str(df["date"].max().date())],
            "duplicate_dates": int(df["date"].duplicated().sum()),
            "missing_per_col": {c: int(df[c].isna().sum()) for c in cc},
            "missing_handling": "FRED '.' -> NaN; NO synthetic fill"}


def run():
    print(f"FRED drivers batch-2 (download_date={DL_DATE}) — STRUCTURAL ONLY, no screens/edge\n", flush=True)
    reports = {}
    print("real_rates.csv (TIPS real yields)", flush=True)
    reports["real_rates"] = write_feed("real_rates.csv", {"dfii5": "DFII5", "dfii10": "DFII10", "dfii30": "DFII30"})
    print("\ninflation_expectations.csv (breakevens)", flush=True)
    reports["inflation_expectations"] = write_feed("inflation_expectations.csv", {"t5yie": "T5YIE", "t10yie": "T10YIE"})
    print("\ndollar_index.csv (broad USD)", flush=True)
    reports["dollar_index"] = write_feed("dollar_index.csv", {"usd_broad": "DTWEXBGS"})
    print("\nvix.csv", flush=True)
    reports["vix"] = write_feed("vix.csv", {"vix": "VIXCLS"})
    print("\nenergy_spot.csv (WTI/Brent/HenryHub)", flush=True)
    reports["energy_spot"] = write_feed("energy_spot.csv", {"wti": "DCOILWTICO", "brent": "DCOILBRENTEU", "henryhub": "DHHNGSP"})
    print("\ncredit_oas.csv (HY OAS)", flush=True)
    reports["credit_oas"] = write_feed("credit_oas.csv", {"hy_oas": "BAMLH0A0HYM2"})

    status = "FRED_DRIVERS_BATCH2_ACQUIRED_STRUCTURAL_ONLY" if any(reports.values()) else "FETCH_FAILED"
    out = {"download_date": DL_DATE, "source": "FRED keyless fredgraph.csv (.org, reachable)",
           "status": status, "class_note": "STRUCTURAL ONLY — NOT evidence of edge; screens are separate",
           "reports": reports, "boundaries": "fetch + structural validation only; no screens/edge/labels/synthetic-fill/mutation"}
    (ROOT / "research" / "data" / "fql_forge" / "reports" / "fred_drivers_batch2_2026-06-17.json").write_text(json.dumps(out, indent=2, default=str))
    print("\n=== PROVENANCE + STRUCTURAL VALIDATION ===", flush=True)
    for k, r in reports.items():
        if r:
            print(f"  {k}: n={r['n_rows']} range={r['date_range']} dups={r['duplicate_dates']} missing={r['missing_per_col']}", flush=True)
    print(f"\n  STATUS: {status} (NOT evidence of edge)", flush=True)


if __name__ == "__main__":
    run()
