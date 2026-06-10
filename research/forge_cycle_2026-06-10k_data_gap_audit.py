"""Cycle 2026-06-10k — Data-gap audit across all primary assets.

Per operator decision #152 phase 2: extend the MGC data-gap doctrine check
to all primary intraday-futures assets so future event-window candidates
on these assets can be screened cleanly.

Assets audited:
  - MES, MNQ, MYM, MCL, MGC (reference), ZN, 6E, 6J

For each asset, the audit reports:
  - Data span (start_date, end_date)
  - Total bars
  - Bar continuity (5min interval %, intra-day gap stats)
  - NFP calendar coverage (since NFP is a universal benchmark — both 8:30 ET)
  - CPI calendar coverage (rule-based or verified)
  - Eligibility label per #146 doctrine:
      CLEAN_EVENT_READY        — exact match + small-gap >= 90%
      CLEAN_EVENT_USABLE_WITH_WARN — 70-90% clean
      EVENT_DATA_GAPPED        — < 70% clean
      DATA_REQUIRED            — multi-month outages

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402


def _bake_nfp():
    cal = build_verified_nfp_calendar(2019, 2026)
    return [pd.to_datetime(f"{c['actual_date']} 08:30:00") for c in cal]


def _bake_cpi():
    cal = build_verified_cpi_calendar()
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in cal]


def audit_asset(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["dt"] = pd.to_datetime(df["datetime"])
    span_start = df["dt"].iloc[0]
    span_end = df["dt"].iloc[-1]
    n_bars = len(df)

    # Bar continuity stats
    gaps = df["dt"].diff()
    n_5min = (gaps == pd.Timedelta(minutes=5)).sum()
    n_gt_10min = (gaps > pd.Timedelta(minutes=10)).sum()
    n_gt_2h = (gaps > pd.Timedelta(hours=2)).sum()
    n_gt_1d = (gaps > pd.Timedelta(days=1)).sum()

    # Event coverage check per #146 doctrine
    def check_events(events, label):
        n_total = len(events)
        n_exact = 0
        n_lt_1h = 0
        n_1h_to_1d = 0
        n_gt_1d = 0
        n_pre_data = 0
        for ev in events:
            if ev < span_start:
                n_pre_data += 1
                continue
            exact = df[df["dt"] == ev]
            if len(exact) > 0:
                n_exact += 1
                continue
            after = df[df["dt"] > ev].head(1)
            if len(after) == 0:
                n_gt_1d += 1
                continue
            gap_min = (after["dt"].iloc[0] - ev).total_seconds() / 60
            if gap_min < 60:
                n_lt_1h += 1
            elif gap_min < 1440:
                n_1h_to_1d += 1
            else:
                n_gt_1d += 1
        clean = n_exact + n_lt_1h
        clean_pct = clean / n_total * 100 if n_total > 0 else 0
        return {
            "calendar": label,
            "total_events": n_total,
            "exact_match": n_exact,
            "gap_lt_1h": n_lt_1h,
            "gap_1h_to_1d": n_1h_to_1d,
            "gap_gt_1d": n_gt_1d,
            "pre_data_start_excluded": n_pre_data,
            "clean_events": clean,
            "clean_pct": clean_pct,
        }

    nfp = check_events(_bake_nfp(), "NFP")
    cpi = check_events(_bake_cpi(), "CPI")

    # Eligibility label
    def label_eligibility(clean_pct, pre_excluded):
        if pre_excluded > 0 and pre_excluded >= 12:  # > 1 year of events missing
            return f"DATA_REQUIRED (pre-data-start exclusions: {pre_excluded})"
        if clean_pct >= 90:
            return "CLEAN_EVENT_READY"
        if clean_pct >= 70:
            return "CLEAN_EVENT_USABLE_WITH_WARN"
        if clean_pct >= 30:
            return "EVENT_DATA_GAPPED"
        return "DATA_REQUIRED"

    nfp_label = label_eligibility(nfp["clean_pct"], nfp["pre_data_start_excluded"])
    cpi_label = label_eligibility(cpi["clean_pct"], cpi["pre_data_start_excluded"])

    return {
        "asset": asset,
        "data_span": {"start": str(span_start), "end": str(span_end)},
        "n_bars": int(n_bars),
        "bar_continuity": {
            "n_5min_intervals": int(n_5min),
            "n_gt_10min_gaps": int(n_gt_10min),
            "n_gt_2h_gaps": int(n_gt_2h),
            "n_gt_1d_gaps": int(n_gt_1d),
        },
        "NFP_coverage": nfp,
        "CPI_coverage": cpi,
        "eligibility": {
            "NFP_event_window": nfp_label,
            "CPI_event_window": cpi_label,
        },
    }


ASSETS_TO_AUDIT = ["MGC", "MES", "MNQ", "MYM", "MCL", "ZN", "6E", "6J"]


def run():
    print("Cycle 2026-06-10k — Data-gap audit across 8 assets", flush=True)
    print("Per #152 phase 2 + #146 doctrine.\n", flush=True)
    t_start = time.time()
    results = {}
    for asset in ASSETS_TO_AUDIT:
        print(f"\n--- Auditing {asset} ---", flush=True)
        try:
            r = audit_asset(asset)
            results[asset] = r
            print(f"  Data span: {r['data_span']['start']} to {r['data_span']['end']}", flush=True)
            print(f"  Total bars: {r['n_bars']}", flush=True)
            print(f"  NFP: clean {r['NFP_coverage']['clean_pct']:.1f}% ({r['NFP_coverage']['clean_events']}/{r['NFP_coverage']['total_events']}) — {r['eligibility']['NFP_event_window']}", flush=True)
            print(f"  CPI: clean {r['CPI_coverage']['clean_pct']:.1f}% ({r['CPI_coverage']['clean_events']}/{r['CPI_coverage']['total_events']}) — {r['eligibility']['CPI_event_window']}", flush=True)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)
            results[asset] = {"error": str(e)}

    print(f"\n=== Summary table ===")
    print(f"{'Asset':<6} {'Span':<25} {'NFP clean':<15} {'CPI clean':<15} {'NFP eligibility':<35} {'CPI eligibility':<35}", flush=True)
    for asset, r in results.items():
        if "error" in r:
            print(f"{asset:<6} ERROR: {r['error']}", flush=True)
            continue
        span = r['data_span']['start'][:10] + " to " + r['data_span']['end'][:10]
        nfp_pct = f"{r['NFP_coverage']['clean_pct']:.1f}%"
        cpi_pct = f"{r['CPI_coverage']['clean_pct']:.1f}%"
        print(f"{asset:<6} {span:<25} {nfp_pct:<15} {cpi_pct:<15} {r['eligibility']['NFP_event_window']:<35} {r['eligibility']['CPI_event_window']:<35}", flush=True)

    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s")

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-10k_data_gap_audit.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Data-gap audit across 8 primary assets (per #146 doctrine + #152 phase 2)",
        "boundaries": "report-only Lane B",
        "calendars_used": "NFP verified + CPI verified (Forge-recall)",
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
