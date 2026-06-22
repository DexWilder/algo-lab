"""Fetch Treasury auctions (TreasuryDirect Fiscal Data) — ACQUISITION + STRUCTURAL VALIDATION ONLY.

Scout found the .gov Fiscal Data auctions API now REACHABLE (HTTP 200; was HTTP 000/blocked earlier).
Self-unblocks WP-B1 (highest-EV WH2 test) without waiting on operator CSV. STRICT: fetch + structural
validation + provenance ONLY. No screens/edge/labels here (WP-B1 harness is the separate report-only
screen). Writes data/feeds/treasury_auctions.csv with a CLEAN 'tenor' column (handles reopenings).
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEEDS = ROOT / "data" / "feeds"
DL = datetime.now(timezone.utc).strftime("%Y-%m-%d")
URL = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/auctions_query"
       "?fields=auction_date,security_type,security_term,cusip,issue_date,offering_amt,high_yield,reopening"
       "&filter=auction_date:gte:2019-01-01&page[size]=10000&format=json")
STD = [2, 3, 5, 7, 10, 20, 30]


def norm_tenor(term):
    """security_term -> standard year-tenor (e.g. '9-Year 10-Month'->10Y, '29-Year 10-Month'->30Y).
    Bills (Week terms) -> None (no futures)."""
    s = str(term)
    if "Week" in s or "Day" in s:
        return None
    ym = re.search(r"(\d+)\s*-?\s*Year", s)
    if not ym:
        return None
    yrs = int(ym.group(1))
    mm = re.search(r"(\d+)\s*-?\s*Month", s)
    if mm:
        yrs += int(mm.group(1)) / 12.0
    nearest = min(STD, key=lambda t: abs(t - yrs))
    return f"{nearest}Y"


def run():
    print(f"Treasury auctions acquisition (download_date={DL}) — STRUCTURAL ONLY\n", flush=True)
    raw = urllib.request.urlopen(URL, timeout=90).read().decode()
    rows = json.loads(raw).get("data", [])
    df = pd.DataFrame(rows)
    df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce")
    df["tenor"] = df["security_term"].map(norm_tenor)
    # keep all (Bills included for provenance) but flag note/bond with mapped tenor
    keep = df[["auction_date", "tenor", "security_type", "security_term", "cusip", "issue_date", "offering_amt", "high_yield"]]
    if "reopening" in df.columns:
        keep = keep.assign(reopening=df["reopening"])
    keep = keep.sort_values("auction_date")
    keep.to_csv(FEEDS / "treasury_auctions.csv", index=False)

    notebond = keep[keep["security_type"].isin(["Note", "Bond"])]
    rep = {"source": "TreasuryDirect Fiscal Data API (api.fiscaldata.treasury.gov, reachable HTTP 200)",
           "download_date": DL, "path": str(FEEDS / "treasury_auctions.csv"), "n_rows_all": int(len(keep)),
           "date_range": [str(keep["auction_date"].min().date()), str(keep["auction_date"].max().date())],
           "by_security_type": keep["security_type"].value_counts().to_dict(),
           "note_bond_by_tenor": notebond["tenor"].value_counts().to_dict(),
           "note_bond_n": int(len(notebond)), "duplicate_cusip_date": int(keep.duplicated(["cusip", "auction_date"]).sum()),
           "status": "TREASURY_AUCTIONS_ACQUIRED_STRUCTURAL_ONLY",
           "note": "Bills (no futures) retained for provenance but tenor=None -> WP-B1 routes only Note/Bond tenors. NOT evidence of edge; WP-B1 screen is separate report-only step."}
    (ROOT / "research" / "data" / "fql_forge" / "reports" / "treasury_auctions_acquisition_2026-06-22.json").write_text(json.dumps(rep, indent=2, default=str))
    print(f"  n_all={rep['n_rows_all']} range={rep['date_range']} by_type={rep['by_security_type']}", flush=True)
    print(f"  Note/Bond by mapped tenor: {rep['note_bond_by_tenor']} (n={rep['note_bond_n']})", flush=True)
    print(f"  STATUS: {rep['status']} (structural only; WP-B1 screen is separate)", flush=True)


if __name__ == "__main__":
    run()
