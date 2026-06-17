"""Lever-B1 Treasury-auction FEED VALIDATOR STUB — structure-only (report-only).

DELIBERATELY NOT A STRATEGY SCREEN. Per operator 2026-06-17: the one allowed "road-ready"
action while feed-gated is ultra-thin validation code that CANNOT produce strategy results.
This module:
  - validates the FEED FILE structure only (existence, columns/aliases, date parsing, sort/
    dedup, tenor/type normalization preview, future-date sanity)
  - emits NO strategy metrics, NO PASS/WATCH/KILL labels, NO parameter sweeps
  - generates NO synthetic data
If the real file is absent it reports AWAITING_FEED. The actual WP-B1 screen (validation ->
no-lookahead audit -> join audit -> coverage -> first-10 cheap screen -> board) runs as a
SEPARATE cycle ONLY once the real CSV exists.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FEED_PATH = ROOT / "data" / "feeds" / "treasury_auctions.csv"

# required field -> acceptable column aliases (resolved case-insensitively)
ALIASES = {
    "tenor": ["tenor", "security_term", "term", "originalsecurityterm", "security_term_week_year"],
    "security_type": ["security_type", "securitytype", "type"],
    "auction_date": ["auction_date", "auctiondate", "record_date"],
}
OPTIONAL = {
    "issue_date": ["issue_date", "issuedate", "settlement_date"],
    "cusip": ["cusip"],
    "high_yield": ["high_yield", "highyield", "high_investment_rate"],
    "bid_to_cover": ["bid_to_cover_ratio", "bidtocoverratio", "bid_to_cover"],
}


def _resolve(cols_lower, aliases):
    for a in aliases:
        if a.lower() in cols_lower:
            return cols_lower[a.lower()]
    return None


def validate_structure(path: Path = FEED_PATH) -> dict:
    """Structure-only validation. Returns a report dict. NO strategy evaluation."""
    if not path.exists():
        return {"status": "AWAITING_FEED", "path": str(path),
                "note": "drop the real Treasury-auction CSV here; structural validation will run, "
                        "strategy screening is a SEPARATE cycle (operator-gated)."}
    df = pd.read_csv(path)
    cols_lower = {c.lower(): c for c in df.columns}
    resolved = {k: _resolve(cols_lower, v) for k, v in ALIASES.items()}
    opt_resolved = {k: _resolve(cols_lower, v) for k, v in OPTIONAL.items()}
    missing_required = [k for k, v in resolved.items() if v is None]

    rep = {"status": "STRUCTURE_OK" if not missing_required else "STRUCTURE_INCOMPLETE",
           "path": str(path), "n_rows": int(len(df)), "columns": list(df.columns),
           "resolved_required": resolved, "missing_required": missing_required,
           "resolved_optional": {k: v for k, v in opt_resolved.items() if v}}
    if missing_required:
        rep["note"] = f"missing required field(s): {missing_required} (no acceptable alias found)"
        return rep

    # auction_date parse + ordering + dedup (structural only)
    ad = pd.to_datetime(df[resolved["auction_date"]], errors="coerce")
    rep["auction_date_parse_rate"] = round(float(ad.notna().mean()), 4)
    valid = ad.dropna()
    rep["date_range"] = [str(valid.min().date()), str(valid.max().date())] if len(valid) else None
    rep["is_sorted_ascending"] = bool(valid.is_monotonic_increasing)
    key_cols = [resolved["auction_date"]] + ([opt_resolved["cusip"]] if opt_resolved.get("cusip") else [resolved["tenor"]])
    rep["duplicate_rows_on_key"] = int(df.duplicated(subset=key_cols).sum())
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    rep["future_dated_rows_vs_today"] = int((valid > today).sum())  # sanity only, not a join check

    # normalization PREVIEW (does the labeling resolve cleanly?) — NOT a screen
    rep["security_type_values"] = sorted(df[resolved["security_type"]].dropna().astype(str).unique().tolist())[:20]
    rep["tenor_values_sample"] = sorted(df[resolved["tenor"]].dropna().astype(str).unique().tolist())[:25]
    rep["note"] = ("structural validation only — NO strategy results produced. Run the WP-B1 "
                   "screen cycle next (separate): validation -> no-lookahead audit -> join audit -> "
                   "coverage -> first-10 cheap screen -> brutal board.")
    return rep


def main():
    import json
    rep = validate_structure()
    print("Lever-B1 Treasury-auction FEED VALIDATOR (structure-only; NO strategy results)", flush=True)
    print("NOTE: this validator is NOT evidence of edge. It confirms feed PLUMBING readiness only —", flush=True)
    print("      no no-lookahead claim, no join-quality conclusion, no PASS/WATCH/KILL. State: LEVER_B1_FEED_GATED_NOT_IDLE.\n", flush=True)
    print(json.dumps(rep, indent=2, default=str), flush=True)
    if rep["status"] == "AWAITING_FEED":
        print("\nExpected path: data/feeds/treasury_auctions.csv", flush=True)
        print("Minimum columns (or aliases): tenor/security_term, security_type, auction_date", flush=True)
        print("Run order once the REAL file lands (separate cycle):", flush=True)
        for i, step in enumerate(["feed validation", "timestamp/no-lookahead audit", "join audit to ZN/ZF/ZB bars",
                                  "coverage by tenor & year", "first-10 auction-mechanism cheap screen",
                                  "brutal board classification", "archive kills / keep evidence-clean survivors"], 1):
            print(f"  {i}. {step}", flush=True)
    print("\n(report-only; structure validator; no synthetic data; no PASS/WATCH/KILL; NON-WIRED)", flush=True)


if __name__ == "__main__":
    main()
