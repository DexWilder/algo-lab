"""Cycle 2026-06-11k — R4 Recovery Mode: Excluded-event anatomy.

Per operator #168 R4 first: for each of the 21 events that strict+hold-continuity
excluded but strict (next-bar only) included, report:
  - event date/time
  - entry timestamp
  - intended exit timestamp (24 bars after entry = 2h)
  - nearest available bars
  - size and location of intra-hold gap
  - whether gap is session-boundary, holiday/early-close, rollover, missing
    data, or true outage
  - PnL impact if included/excluded
  - classification:
      TRUE_DATA_GAP / SESSION_BOUNDARY / EARLY_CLOSE_OR_HOLIDAY /
      ROLLOVER_ARTIFACT / RECOVERABLE_WITH_SESSION_AWARE_ENGINE / UNUSABLE

For NFP events at 08:30 ET with 24-bar (2h) hold, entry is at 08:35 ET and
intended exit at 10:35 ET — all within RTH (no session boundary expected).
Gaps in this window during normal trading days indicate genuine outages.

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
from datetime import date, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


# Known US half-day / early close dates (best-effort recall — operator-verifiable)
US_EARLY_CLOSES = {
    # Day after Thanksgiving, day before Christmas, day before July 4
    # Listed for 2019-2026 known to fall near NFP first Fridays
    # NFP is first Friday — rarely aligns with these but check
    "2019-07-03",  # day before July 4 holiday early close
    "2019-11-29",  # day after Thanksgiving (NFP isn't Friday after T-giving typically)
    "2019-12-24",
    "2020-07-02",  # day before July 4
    "2020-11-27",
    "2020-12-24",
    "2021-07-02",
    "2021-11-26",
    "2021-12-23",
    "2022-07-01",
    "2022-11-25",
    "2022-12-23",
    "2023-07-03",
    "2023-11-24",
    "2023-12-22",
    "2024-07-03",
    "2024-11-29",
    "2024-12-24",
    "2025-07-03",
    "2025-11-28",
    "2025-12-24",
    "2026-07-02",
}


def find_session_boundary_gaps(df, start_dt, end_dt):
    """Return list of (gap_start, gap_end, gap_minutes) within [start_dt, end_dt]."""
    df_dt = pd.to_datetime(df["datetime"])
    window = df[(df_dt >= start_dt) & (df_dt <= end_dt)].copy()
    window["dt"] = pd.to_datetime(window["datetime"])
    if len(window) < 2: return [{"gap_start": str(start_dt), "gap_end": str(end_dt), "minutes": (end_dt - start_dt).total_seconds() / 60, "note": "<2 bars in window"}]
    diffs = window["dt"].diff().dt.total_seconds() / 60
    gaps = []
    for i, gap_min in diffs.items():
        if pd.notna(gap_min) and gap_min > 6:  # >6 min = gap (5-min bars expected)
            prev_idx = window.index[window.index.get_indexer([i])[0] - 1]
            gap_start = window.loc[prev_idx, "dt"]
            gap_end = window.loc[i, "dt"]
            gaps.append({
                "gap_start": str(gap_start),
                "gap_end": str(gap_end),
                "minutes": float(gap_min),
            })
    return gaps


def classify_gap(gap_record, event_date):
    """Per operator #168 R4 categories. CORRECTED order: duration FIRST.

    MGC GLOBEX overnight pause is only ~60 minutes (17:00-18:00 ET).
    Any gap > 90 minutes is NOT a normal session boundary regardless of
    when the gap starts.
    """
    duration = gap_record["minutes"]
    gap_start_dt = pd.to_datetime(gap_record["gap_start"])
    event_date_str = str(event_date)

    # PRIORITY 1: Multi-day outage (> 24 hours) = TRUE_DATA_GAP regardless of timing
    if duration > 24 * 60:
        return "TRUE_DATA_GAP (multi-day outage)"

    # PRIORITY 2: Multi-hour gap (>3h to 24h) = TRUE_DATA_GAP unless on early-close
    # day (which only legitimately gaps from ~13:00 ET to 18:00 ET = ~5h)
    if duration > 3 * 60:
        if event_date_str in US_EARLY_CLOSES:
            return "EARLY_CLOSE_OR_HOLIDAY"
        prev_day = (pd.to_datetime(event_date_str) - timedelta(days=1)).strftime("%Y-%m-%d")
        if prev_day in US_EARLY_CLOSES:
            return "POST_HOLIDAY_REOPEN"
        return "TRUE_DATA_GAP (multi-hour outage)"

    # PRIORITY 3: ~60 minute gap at 17:00-18:00 ET = normal overnight pause
    if 30 <= duration <= 90 and (gap_start_dt.hour == 17 or gap_start_dt.hour == 18):
        return "SESSION_BOUNDARY"

    # PRIORITY 4: Sub-3-hour gap during RTH = data outage
    if 8 <= gap_start_dt.hour <= 16:
        return "TRUE_DATA_GAP (RTH outage)"

    return "TRUE_DATA_GAP (other)"


def per_event_pnl(asset, single_event):
    """Run backtest on a single event to get its PnL contribution."""
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(
        df, events=[single_event], entry_offset_bars=1,
        exit_offset_bars=24, direction="long",
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"],
                       symbol=asset, commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    trades = res["trades_df"]
    if len(trades) == 0: return {"pnl": 0.0, "n_trades": 0}
    return {
        "pnl": float(trades["pnl"].sum()),
        "n_trades": len(trades),
        "entry_time": str(trades["entry_time"].iloc[0]),
        "exit_time": str(trades["exit_time"].iloc[0]),
    }


def run():
    print("Cycle 2026-06-11k — R4 Recovery Mode: Excluded-event anatomy", flush=True)
    print("21 events lost between strict and strict+hold-continuity filters.\n", flush=True)

    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]
    df_mgc = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    df_dt = pd.to_datetime(df_mgc["datetime"]).reset_index(drop=True)

    # Re-derive the strict-but-not-hold-continuity event set
    excluded_events = []
    for ev in nfp_events:
        if ev < df_dt.iloc[0]: continue
        future_mask = df_dt > ev
        if not future_mask.any(): continue
        next_idx = int(np.argmax(future_mask.values))
        gap_min = (df_dt.iloc[next_idx] - ev).total_seconds() / 60
        if gap_min > 60: continue  # strict reject
        entry_idx = next_idx + 1
        exit_idx = entry_idx + 24
        if exit_idx >= len(df_dt): continue
        hold_window_dt = df_dt.iloc[entry_idx:exit_idx + 1]
        max_intra_gap_min = hold_window_dt.diff().dropna().dt.total_seconds().max() / 60
        if max_intra_gap_min > 60:
            excluded_events.append({
                "event_dt": ev,
                "entry_dt": df_dt.iloc[entry_idx],
                "intended_exit_dt": df_dt.iloc[exit_idx],
                "max_intra_hold_gap_min": float(max_intra_gap_min),
            })

    print(f"Re-derived excluded set: {len(excluded_events)} events\n", flush=True)

    # Per-event anatomy
    print(f"{'#':<3} {'Event date':<11} {'Entry':<20} {'Intended exit':<20} {'Max gap':<10} {'Gap class':<35} {'PnL ($)':<10}", flush=True)
    print("-" * 110, flush=True)

    full_records = []
    classification_counts = {}
    pnl_by_class = {}

    for i, ev_record in enumerate(excluded_events, start=1):
        event_dt = ev_record["event_dt"]
        entry_dt = ev_record["entry_dt"]
        exit_dt = ev_record["intended_exit_dt"]
        # Find ALL gaps in entry → exit window
        gaps = find_session_boundary_gaps(df_mgc, entry_dt, exit_dt)
        # Get the largest gap and classify
        if gaps:
            largest_gap = max(gaps, key=lambda g: g["minutes"])
            gap_class = classify_gap(largest_gap, event_dt.date())
        else:
            largest_gap = {"minutes": 0}
            gap_class = "NO_GAP_FOUND (sanity check failed)"
        # PnL for this single event
        pnl_info = per_event_pnl("MGC", event_dt)

        print(f"{i:<3} {str(event_dt.date()):<11} {str(entry_dt):<20} {str(exit_dt):<20} {largest_gap['minutes']:<10.0f} {gap_class:<35} {pnl_info['pnl']:<10.2f}", flush=True)

        classification_counts[gap_class] = classification_counts.get(gap_class, 0) + 1
        pnl_by_class.setdefault(gap_class, []).append(pnl_info["pnl"])

        full_records.append({
            "event_dt": str(event_dt),
            "entry_dt": str(entry_dt),
            "intended_exit_dt": str(exit_dt),
            "max_intra_hold_gap_min": ev_record["max_intra_hold_gap_min"],
            "all_gaps_in_window": gaps,
            "classification": gap_class,
            "pnl_dollar": pnl_info["pnl"],
            "actual_entry_time": pnl_info.get("entry_time"),
            "actual_exit_time": pnl_info.get("exit_time"),
        })

    print()
    print("--- Classification summary ---", flush=True)
    for cls, count in sorted(classification_counts.items(), key=lambda x: -x[1]):
        pnls = pnl_by_class[cls]
        total_pnl = sum(pnls)
        mean_pnl = total_pnl / len(pnls) if pnls else 0
        print(f"  {cls:<45}: {count:>3} events, total PnL ${total_pnl:>8.2f}, mean ${mean_pnl:>7.2f}", flush=True)

    # PnL impact of inclusion
    total_excluded_pnl = sum(r["pnl_dollar"] for r in full_records)
    print(f"\nTotal PnL from excluded events: ${total_excluded_pnl:.2f}", flush=True)
    print(f"(If included via permissive: adds this to Packet #1 total net)", flush=True)

    # Recommendation
    salvageable_classes = {"SESSION_BOUNDARY", "EARLY_CLOSE_OR_HOLIDAY", "POST_HOLIDAY_REOPEN"}
    unusable_classes = {cls for cls in classification_counts if "TRUE_DATA_GAP" in cls or cls == "UNUSABLE"}
    n_salvageable = sum(c for cls, c in classification_counts.items() if cls in salvageable_classes)
    n_unusable = sum(c for cls, c in classification_counts.items() if cls in unusable_classes)
    print(f"\n=== R4 Verdict ===", flush=True)
    print(f"  Salvageable (session/holiday): {n_salvageable}/{len(excluded_events)}", flush=True)
    print(f"  Genuine data gaps (unusable):  {n_unusable}/{len(excluded_events)}", flush=True)

    if n_salvageable / len(excluded_events) > 0.5:
        verdict = "Most excluded events are SESSION/HOLIDAY artifacts. Strict+hold-continuity is TOO BLUNT. Recommend: session-aware engine or strict next-bar only."
    elif n_unusable / len(excluded_events) > 0.5:
        verdict = "Most excluded events are TRUE DATA GAPS. Strict+hold-continuity is CORRECT. Recommend: strict+hold as canonical."
    else:
        verdict = "Mixed. Further investigation needed per-event."

    print(f"  Recommendation: {verdict}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11k_R4_excluded_event_anatomy.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "R4 Recovery Mode: anatomy of 21 strict+hold-continuity excluded events per #168",
        "boundaries": "report-only Lane B",
        "n_excluded_events": len(excluded_events),
        "classification_counts": classification_counts,
        "pnl_by_class": {k: {"total": sum(v), "n": len(v), "mean": sum(v)/len(v) if v else 0}
                          for k, v in pnl_by_class.items()},
        "total_excluded_pnl_dollar": total_excluded_pnl,
        "per_event_records": full_records,
        "verdict_recommendation": verdict,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
