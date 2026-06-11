"""Cycle 2026-06-11i — Strict-filter 8-asset data-gap audit (re-run of 06-10k).

Per operator decision #161 OK A: re-run 06-10k 8-asset audit with the strict
next-bar-gap filter as defensive hygiene. The 06-10k audit used a permissive
"exact-match" filter that overcounts clean events (per #161-C doctrine
update). This re-run produces the canonical clean-percent figures.

Assets: MGC, MES, MNQ, MYM, MCL, ZN, 6E, 6J
Calendars: NFP (verified), CPI (Forge-recall — still DATA_REQUIRED for use)

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
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402


def strict_audit(asset, events, max_gap_minutes=60):
    """Strict next-bar-gap filter (per #161-C doctrine).

    An event is CLEAN iff the next available bar AFTER the event timestamp
    occurs within max_gap_minutes. The exact-bar-match check is NOT applied
    as a clean-override.
    """
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["dt"] = pd.to_datetime(df["datetime"])
    span_start = df["dt"].iloc[0]
    span_end = df["dt"].iloc[-1]

    n_clean = 0
    n_gap_1h_to_1d = 0
    n_gap_gt_1d = 0
    n_pre_data = 0
    for ev in events:
        if ev < span_start:
            n_pre_data += 1
            continue
        after = df[df["dt"] > ev].head(1)
        if len(after) == 0:
            n_gap_gt_1d += 1
            continue
        gap_min = (after["dt"].iloc[0] - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes:
            n_clean += 1
        elif gap_min <= 1440:
            n_gap_1h_to_1d += 1
        else:
            n_gap_gt_1d += 1

    total = len(events)
    clean_pct = n_clean / total * 100 if total > 0 else 0
    if n_pre_data >= 12: label = f"DATA_REQUIRED (pre-data exclusions: {n_pre_data})"
    elif clean_pct >= 90: label = "CLEAN_EVENT_READY"
    elif clean_pct >= 70: label = "CLEAN_EVENT_USABLE_WITH_WARN"
    elif clean_pct >= 30: label = "EVENT_DATA_GAPPED"
    else: label = "DATA_REQUIRED"

    return {
        "asset": asset,
        "data_span_start": str(span_start),
        "data_span_end": str(span_end),
        "total_events": total,
        "clean_events": n_clean,
        "gap_1h_to_1d": n_gap_1h_to_1d,
        "gap_gt_1d": n_gap_gt_1d,
        "pre_data_excluded": n_pre_data,
        "clean_pct": clean_pct,
        "eligibility": label,
    }


def run():
    print("Cycle 2026-06-11i — Strict 8-asset data-gap audit (per #161-A)", flush=True)
    print("Strict filter: next-bar gap <= 60 min (no exact-match override).\n", flush=True)

    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]
    cpi_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                  for c in build_verified_cpi_calendar()]
    fomc_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                   for c in build_official_fomc_calendar()]
    print(f"Calendars: NFP {len(nfp_events)} events, CPI {len(cpi_events)} events, FOMC {len(fomc_events)} events\n", flush=True)

    assets = ["MGC", "MES", "MNQ", "MYM", "MCL", "ZN", "6E", "6J"]

    print(f"{'Asset':<6} {'Span':<25} {'NFP%':<10} {'CPI%':<10} {'FOMC%':<10} {'NFP label':<35} {'CPI label':<35} {'FOMC label':<35}", flush=True)
    results = {}
    for asset in assets:
        try:
            nfp_audit = strict_audit(asset, nfp_events)
            cpi_audit = strict_audit(asset, cpi_events)
            fomc_audit = strict_audit(asset, fomc_events)
        except Exception as e:
            print(f"{asset:<6} ERROR: {e}", flush=True)
            results[asset] = {"error": str(e)}
            continue
        span = nfp_audit["data_span_start"][:10] + " to " + nfp_audit["data_span_end"][:10]
        print(f"{asset:<6} {span:<25} {nfp_audit['clean_pct']:>6.1f}%   {cpi_audit['clean_pct']:>6.1f}%   {fomc_audit['clean_pct']:>6.1f}%   {nfp_audit['eligibility']:<35} {cpi_audit['eligibility']:<35} {fomc_audit['eligibility']:<35}", flush=True)
        results[asset] = {
            "NFP": nfp_audit,
            "CPI": cpi_audit,
            "FOMC": fomc_audit,
        }

    # Comparison vs 06-10k permissive audit
    print("\n=== Comparison vs 06-10k (permissive filter) ===", flush=True)
    print(f"{'Asset':<6} {'NFP delta':<15} {'CPI delta':<15}", flush=True)
    # Load 06-10k audit for delta
    old_audit_path = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-10k_data_gap_audit.json"
    if old_audit_path.exists():
        old = json.loads(old_audit_path.read_text())
        for asset in assets:
            if asset in old.get("results", {}) and asset in results:
                old_a = old["results"][asset]
                new_a = results[asset]
                if "NFP_coverage" in old_a:
                    old_nfp = old_a["NFP_coverage"]["clean_pct"]
                    new_nfp = new_a["NFP"]["clean_pct"]
                    nfp_delta = new_nfp - old_nfp
                    old_cpi = old_a["CPI_coverage"]["clean_pct"]
                    new_cpi = new_a["CPI"]["clean_pct"]
                    cpi_delta = new_cpi - old_cpi
                    print(f"{asset:<6} {nfp_delta:+6.1f}%        {cpi_delta:+6.1f}%", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11i_strict_data_gap_audit.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Strict 8-asset data-gap audit per #161-A (defensive hygiene re-run of 06-10k)",
        "filter": "strict next-bar gap <= 60 min, no exact-match override",
        "doctrine_reference": "docs/fql_forge/event_window_clean_events_rule.md (#161-C update)",
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
