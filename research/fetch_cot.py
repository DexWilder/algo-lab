"""Fetch CFTC COT positioning — ACQUISITION + STRUCTURAL VALIDATION ONLY (report-only).

Scout found COT reachable (publicreporting.cftc.gov Socrata, HTTP 200) — S6 is NOT feed-blocked.
Weekly commercial(comm)/spec(noncomm) positioning; mechanism = crowded specs forced to unwind at
extremes. STRICT: fetch + structural validation + provenance ONLY. No screens/edge/labels/synthetic-
fill/mutation. Weekly cadence -> GATES daily entries (not itself daily WH2). Structural readiness != edge.
"""
from __future__ import annotations

import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "data" / "feeds"
DL = datetime.now(timezone.utc).strftime("%Y-%m-%d")
COLS = ["market_and_exchange_names", "report_date_as_yyyy_mm_dd", "open_interest_all",
        "noncomm_positions_long_all", "noncomm_positions_short_all", "comm_positions_long_all", "comm_positions_short_all"]
URL = ("https://publicreporting.cftc.gov/resource/6dca-aqww.csv?$select=" + ",".join(COLS) +
       "&$where=report_date_as_yyyy_mm_dd>'2018-12-31'&$limit=400000")
# market -> our futures symbol (exact CFTC names; exclude cross-rate XRATE pairs)
MARKET_MAP = {
    "10Y": ["UST 10Y NOTE", "10-YEAR U.S. TREASURY NOTES", "10 YEAR U.S. TREASURY"],
    "5Y": ["UST 5Y NOTE", "5-YEAR U.S. TREASURY NOTES", "5 YEAR U.S. TREASURY"],
    "BOND": ["UST BOND", "U.S. TREASURY BONDS", "ULTRA UST BOND", "ULTRA U.S. TREASURY BONDS"],
    "CRUDE": ["WTI FINANCIAL CRUDE OIL - NEW YORK MERCANTILE EXCHANGE", "CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE"],
    "GOLD": ["GOLD - COMMODITY EXCHANGE INC."],
    "SP500": ["E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE"],
    "EUR": ["EURO FX - CHICAGO MERCANTILE EXCHANGE"],
    "JPY": ["JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"],
}


def classify(name):
    u = str(name).upper()
    if "XRATE" in u or "/" in u:
        return None
    for sym, pats in MARKET_MAP.items():
        if any(p.upper() in u for p in pats):
            return sym
    # broad treasury catch
    if "TREASURY" in u or u.startswith("UST "):
        if "10" in u:
            return "10Y"
        if "5" in u or "FIVE" in u:
            return "5Y"
        if "BOND" in u:
            return "BOND"
    return None


def run():
    print(f"CFTC COT acquisition (download_date={DL}) — STRUCTURAL ONLY, no screens/edge\n", flush=True)
    raw = urllib.request.urlopen(URL, timeout=60).read().decode()
    df = pd.read_csv(io.StringIO(raw))
    df["sym"] = df["market_and_exchange_names"].map(classify)
    df = df[df["sym"].notna()].copy()
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"], errors="coerce")
    for c in ["noncomm_positions_long_all", "noncomm_positions_short_all", "comm_positions_long_all", "comm_positions_short_all", "open_interest_all"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["spec_net"] = df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]
    df["comm_net"] = df["comm_positions_long_all"] - df["comm_positions_short_all"]
    out = df[["date", "sym", "spec_net", "comm_net", "open_interest_all"]].sort_values(["sym", "date"]).reset_index(drop=True)
    out.to_csv(FEEDS / "cot.csv", index=False)

    per = out.groupby("sym").agg(n=("date", "count"), start=("date", "min"), end=("date", "max")).reset_index()
    print("STRUCTURAL VALIDATION (per market):", flush=True)
    for _, r in per.iterrows():
        print(f"  {r['sym']:<6} n={r['n']} range={r['start'].date()}..{r['end'].date()}", flush=True)
    rep = {"source": "CFTC COT legacy futures-only via publicreporting.cftc.gov Socrata", "download_date": DL,
           "path": str(FEEDS / "cot.csv"), "n_rows": int(len(out)), "markets": per.to_dict("records"),
           "derived": "spec_net = noncomm_long - noncomm_short; comm_net = comm_long - comm_short",
           "missing": {c: int(out[c].isna().sum()) for c in ["spec_net", "comm_net", "open_interest_all"]},
           "status": "COT_ACQUIRED_STRUCTURAL_ONLY", "cadence": "weekly (Tue report, Fri release) -> GATES daily entries, not daily WH2",
           "note": "S6 reachable (refutes 'everything feed-blocked'); structural readiness != edge; screen is a SEPARATE step"}
    (ROOT / "research" / "data" / "fql_forge" / "reports" / "cot_acquisition_2026-06-18.json").write_text(json.dumps(rep, indent=2, default=str))
    print(f"\n  STATUS: COT_ACQUIRED_STRUCTURAL_ONLY  n={len(out)} markets={list(per['sym'])} (NOT evidence of edge)", flush=True)
    print("  (weekly -> gates daily entries; screen is a separate report-only step w/ no-lookahead Fri-release lag)", flush=True)


if __name__ == "__main__":
    run()
