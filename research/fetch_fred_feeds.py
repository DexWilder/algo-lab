"""Fetch FRED feeds — ACQUISITION + STRUCTURAL VALIDATION ONLY (report-only).

Approved 2026-06-17: self-serve the FRED-available feeds (FRED is .org, sandbox-reachable
unlike .gov). STRICT boundaries: probe/fetch only; NO strategy screens; NO edge inference;
NO PASS/WATCH/KILL; NO synthetic fill for missing values; NO mutation. Emits provenance
(series IDs, download date, row counts, date ranges, missing handling) + structural
validation (schema, parse, rows, range, missing, duplicates). Result class on success:
FRED_FEEDS_ACQUIRED_STRUCTURAL_ONLY (NOT evidence of edge).
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
FEEDS.mkdir(parents=True, exist_ok=True)
DL_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"


def fetch_series(sid: str) -> pd.Series | None:
    try:
        with urllib.request.urlopen(URL.format(sid), timeout=30) as r:
            raw = r.read().decode("utf-8")
    except Exception as e:
        print(f"  [fetch FAIL] {sid}: {str(e)[:80]}", flush=True)
        return None
    df = pd.read_csv(io.StringIO(raw))
    datecol = df.columns[0]  # 'observation_date'
    df[datecol] = pd.to_datetime(df[datecol], errors="coerce")
    # FRED encodes missing as '.'; coerce to NaN — NO synthetic fill
    df[sid] = pd.to_numeric(df[sid].replace(".", pd.NA), errors="coerce")
    return df.set_index(datecol)[sid]


def structural(df: pd.DataFrame, name: str) -> dict:
    cols = [c for c in df.columns if c != "date"]
    rep = {"file": name, "n_rows": int(len(df)),
           "date_range": [str(df["date"].min().date()), str(df["date"].max().date())] if len(df) else None,
           "columns": list(df.columns), "duplicate_dates": int(df["date"].duplicated().sum()),
           "missing_per_col": {c: int(df[c].isna().sum()) for c in cols},
           "missing_handling": "FRED '.' -> NaN; NO synthetic fill (gaps preserved)"}
    return rep


def write_feed(series_map: dict, fname: str) -> dict | None:
    cols = {}
    for outcol, sid in series_map.items():
        s = fetch_series(sid)
        if s is None:
            print(f"  [skip] {outcol} ({sid}) unavailable", flush=True)
            continue
        cols[outcol] = s
        print(f"  [ok] {outcol} <- FRED:{sid}  n={s.notna().sum()} range={s.dropna().index.min().date()}..{s.dropna().index.max().date()}", flush=True)
    if not cols:
        return None
    df = pd.concat(cols, axis=1).sort_index().reset_index().rename(columns={"index": "date", "observation_date": "date"})
    if "date" not in df.columns:
        df = df.rename(columns={df.columns[0]: "date"})
    path = FEEDS / fname
    df.to_csv(path, index=False)
    rep = structural(df, fname); rep["series_map"] = series_map; rep["path"] = str(path)
    return rep


def run():
    print(f"FRED feed acquisition (download_date={DL_DATE}) — STRUCTURAL ONLY, no screens/edge\n", flush=True)
    reports = {}

    print("1. Treasury yield curve -> treasury_yield_curve.csv", flush=True)
    reports["yield_curve"] = write_feed({"dgs2": "DGS2", "dgs5": "DGS5", "dgs10": "DGS10", "dgs30": "DGS30"},
                                         "treasury_yield_curve.csv")

    print("\n2. CPI level -> cpi_levels.csv", flush=True)
    reports["cpi_levels"] = write_feed({"cpiaucsl": "CPIAUCSL"}, "cpi_levels.csv")

    print("\n3. Policy rates -> policy_rates.csv (Fed + BoJ proxy)", flush=True)
    # BoJ proxy candidates (clearly sourced): IRSTCB01JPM156N = Immediate/Central Bank Rate Japan
    boj = fetch_series("IRSTCB01JPM156N")
    fed = fetch_series("FEDFUNDS")
    pol_cols = {}
    if fed is not None:
        pol_cols["fed_funds"] = fed
    boj_note = None
    if boj is not None and boj.notna().sum() > 50:
        pol_cols["boj_rate"] = boj
        boj_note = "BoJ = FRED:IRSTCB01JPM156N (Immediate Rates, Central Bank Rate, Japan)"
    else:
        boj_note = "BoJ NOT cleanly available from FRED -> saved Fed side only; P6 remains PARTIALLY FEED-BLOCKED"
    if pol_cols:
        df = pd.concat(pol_cols, axis=1).sort_index().reset_index().rename(columns={"observation_date": "date", "index": "date"})
        if "date" not in df.columns:
            df = df.rename(columns={df.columns[0]: "date"})
        df.to_csv(FEEDS / "policy_rates.csv", index=False)
        rep = structural(df, "policy_rates.csv"); rep["fed"] = "FRED:FEDFUNDS"; rep["boj_note"] = boj_note
        rep["path"] = str(FEEDS / "policy_rates.csv"); reports["policy_rates"] = rep
        print(f"  {boj_note}", flush=True)
    else:
        reports["policy_rates"] = None

    status = "FRED_FEEDS_ACQUIRED_STRUCTURAL_ONLY" if any(reports.values()) else "FRED_FETCH_FAILED"
    out = {"download_date": DL_DATE, "source": "FRED keyless fredgraph.csv (.org, sandbox-reachable)",
           "status": status, "class_note": "STRUCTURAL ONLY — NOT evidence of edge; screens are a separate approved cycle",
           "reports": reports, "boundaries": "fetch + structural validation only; no screens/edge/labels/synthetic-fill/mutation"}
    (ROOT / "research" / "data" / "fql_forge" / "reports" / "fred_feed_acquisition_2026-06-17.json").write_text(json.dumps(out, indent=2, default=str))
    print(f"\n=== PROVENANCE + STRUCTURAL VALIDATION ===", flush=True)
    for k, r in reports.items():
        if r:
            print(f"  {k}: n={r['n_rows']} range={r['date_range']} dups={r['duplicate_dates']} missing={r['missing_per_col']}", flush=True)
    print(f"\n  STATUS: {status} (NOT evidence of edge)", flush=True)
    print("  (fetch + structural only; no screens; no PASS/WATCH/KILL; no synthetic fill; NON-WIRED)", flush=True)


if __name__ == "__main__":
    run()
