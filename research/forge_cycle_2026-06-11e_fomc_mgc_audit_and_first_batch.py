"""Cycle 2026-06-11e — FOMC-MGC data-gap audit + first batch.

Per operator decision #157 OK C: FOMC-MGC first, rotate to Option B
if it fails.

Pre-flight checks per #157:
  1. FOMC data-gap audit on MGC (event timestamps + bar continuity at 2pm ET)
  2. Verified against official Fed.gov calendar (forge_fomc_calendar_official.py)
  3. Clean-events filter applied per #146 doctrine

Test matrix:
  - 1 asset (MGC) × 2 directions × 3 holding windows (1h/2h/4h) = 6 candidates
  - No EOD test (FOMC 2pm + 4h = 6pm; already covers most of session remainder)
  - No MES/MNQ FOMC sweep in first pass per #157

Calendar status: OFFICIAL_FED_GOV (operator-verifiable; not Forge-recall).
Concentration / Era 3 gates still apply for packet promotion.

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

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def data_gap_audit(asset, events, max_gap_minutes=60):
    """Per #146: classify each event as clean / gapped / pre-data."""
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["dt"] = pd.to_datetime(df["datetime"])
    span_start = df["dt"].iloc[0]
    n_exact = 0
    n_lt_1h = 0
    n_1h_to_1d = 0
    n_gt_1d = 0
    n_pre_data = 0
    clean = []
    details = []
    for ev in events:
        if ev < span_start:
            n_pre_data += 1
            details.append({"event": str(ev), "status": "pre-data-start"})
            continue
        exact = df[df["dt"] == ev]
        if len(exact) > 0:
            n_exact += 1
            clean.append(ev)
            details.append({"event": str(ev), "status": "exact match"})
            continue
        after = df[df["dt"] > ev].head(1)
        if len(after) == 0:
            n_gt_1d += 1
            details.append({"event": str(ev), "status": "no future bar"})
            continue
        gap_min = (after["dt"].iloc[0] - ev).total_seconds() / 60
        if gap_min < 60:
            n_lt_1h += 1
            clean.append(ev)
            details.append({"event": str(ev), "status": f"clean ({gap_min:.0f} min)"})
        elif gap_min < 1440:
            n_1h_to_1d += 1
            details.append({"event": str(ev), "status": f"GAPPED ({gap_min/60:.1f}h)"})
        else:
            n_gt_1d += 1
            details.append({"event": str(ev), "status": f"GAPPED ({gap_min/60:.0f}h)"})
    total = len(events)
    clean_pct = (n_exact + n_lt_1h) / total * 100 if total > 0 else 0
    if n_pre_data >= 12: label = f"DATA_REQUIRED (pre-data exclusions: {n_pre_data})"
    elif clean_pct >= 90: label = "CLEAN_EVENT_READY"
    elif clean_pct >= 70: label = "CLEAN_EVENT_USABLE_WITH_WARN"
    elif clean_pct >= 30: label = "EVENT_DATA_GAPPED"
    else: label = "DATA_REQUIRED"
    return {
        "asset": asset, "data_span_start": str(span_start),
        "total_events": total, "exact_match": n_exact,
        "gap_lt_1h": n_lt_1h, "gap_1h_to_1d": n_1h_to_1d,
        "gap_gt_1d": n_gt_1d, "pre_data_excluded": n_pre_data,
        "clean_events": clean, "clean_pct": clean_pct,
        "eligibility": label, "details": details,
    }


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 20: return f"KILL (n={n}, tail-engine min 20)"
    if median < 0 and pf >= 1.2: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def _run(asset, events, exit_bars, direction, commission_mult=1.0, slippage_mult=1.0, label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=1,
        exit_offset_bars=exit_bars, direction=direction,
    )
    res = run_backtest(
        df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
        commission_per_side=costs["commission_per_side"] * commission_mult,
        slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slippage_mult)),
        tick_size=costs["tick_size"],
    )
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def stress_screen(asset, events, exit_bars, direction, label):
    rows = []
    for stress_label, cm, sm in [
        ("baseline (1x)", 1.0, 1.0),
        ("1.5x cost + 1 tick slip", 1.5, 2.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
        ("4x cost + 2 ticks slip", 4.0, 3.0),
    ]:
        m, _ = _run(asset, events, exit_bars=exit_bars, direction=direction,
                    commission_mult=cm, slippage_mult=sm,
                    label=f"{label}-{stress_label}")
        rows.append({"stress": stress_label, "n": m["n"], "pf": float(m["pf"]),
                     "median": float(m["median"])})
    moderate = next(r for r in rows if r["stress"] == "2x cost + 2 ticks slip")
    extreme = next(r for r in rows if r["stress"] == "4x cost + 2 ticks slip")
    if moderate["median"] <= 0: return {"rows": rows, "verdict": "FAIL_STRESS"}
    if moderate["median"] < 1.0: return {"rows": rows, "verdict": "KNIFE_EDGE"}
    if extreme["median"] <= 0: return {"rows": rows, "verdict": "KNIFE_EDGE (4x)"}
    return {"rows": rows, "verdict": "PASS_STRESS"}


def run():
    print("Cycle 2026-06-11e — FOMC-MGC data-gap audit + first batch", flush=True)
    print("Calendar: OFFICIAL Fed.gov (verified 2026-06-11).", flush=True)
    print("Clean-events filter applied per #146 doctrine.\n", flush=True)

    fomc_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                   for c in build_official_fomc_calendar()]
    print(f"Total scheduled FOMC events: {len(fomc_events)}\n", flush=True)

    print("--- FOMC-MGC data-gap audit ---", flush=True)
    audit = data_gap_audit("MGC", fomc_events, max_gap_minutes=60)
    print(f"  Data span starts: {audit['data_span_start']}", flush=True)
    print(f"  Total events: {audit['total_events']}", flush=True)
    print(f"  Exact match: {audit['exact_match']}", flush=True)
    print(f"  Gap < 1h (clean): {audit['gap_lt_1h']}", flush=True)
    print(f"  Gap 1h-1d (contaminated): {audit['gap_1h_to_1d']}", flush=True)
    print(f"  Gap > 1d (excluded): {audit['gap_gt_1d']}", flush=True)
    print(f"  Pre-data excluded: {audit['pre_data_excluded']}", flush=True)
    print(f"  Clean %: {audit['clean_pct']:.1f}%", flush=True)
    print(f"  Eligibility: {audit['eligibility']}", flush=True)

    if "DATA_REQUIRED" in audit["eligibility"]:
        print(f"\n  EARLY EXIT: {audit['eligibility']} — abandon FOMC-MGC search basis", flush=True)
        out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11e_fomc_mgc.json"
        out.write_text(json.dumps({
            "date": date.today().isoformat(),
            "purpose": "FOMC-MGC data-gap audit + first batch (#157)",
            "calendar_source": "OFFICIAL federalreserve.gov (verified 2026-06-11)",
            "audit": {k: v for k, v in audit.items() if k not in ("clean_events", "details")},
            "early_exit": True,
            "batch_skipped_reason": audit["eligibility"],
        }, indent=2, default=str))
        return

    clean_events = audit["clean_events"]
    print(f"\n--- Running FOMC-MGC first batch (clean events: {len(clean_events)}) ---", flush=True)

    t_start = time.time()
    results = []
    for direction in ["long", "short"]:
        for hold_h, exit_bars in [("1h", 12), ("2h", 24), ("4h", 48)]:
            label = f"FOMC-MGC-{direction[0].upper()}{direction[1:].lower()}-{hold_h}"
            t0 = time.time()
            try:
                m, trades = _run("MGC", clean_events, exit_bars=exit_bars,
                                  direction=direction, label=label)
                v = _classify(m)
                stress = None
                if "WATCH" in v:
                    stress = stress_screen("MGC", clean_events, exit_bars, direction, label)
            except Exception as e:
                print(f"  {label}: ERROR {e}", flush=True)
                results.append({"label": label, "error": str(e)})
                continue
            elapsed = time.time() - t0
            stress_str = f" stress={stress['verdict']}" if stress else ""
            print(
                f"  {label:25s}: n={m['n']:3d} PF={m['pf']:.3f} "
                f"median=${m['median']:7.2f} → {v}{stress_str} [{elapsed:.0f}s]",
                flush=True
            )
            results.append({
                "label": label, "direction": direction, "exit_bars": exit_bars,
                "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
                "verdict": v, "stress": stress,
                "n_clean_events": len(clean_events),
            })
    print(f"\nTotal: {time.time() - t_start:.0f}s", flush=True)

    paper, observational, kill = [], [], []
    for r in results:
        if "error" in r: continue
        v = r["verdict"]; s = r.get("stress")
        if "KILL" in v: kill.append(r)
        elif "WATCH_FOR_DEEP_SCREEN" in v:
            if s and s["verdict"] == "PASS_STRESS": paper.append(r)
            else: observational.append(r)
        elif "WATCH" in v: observational.append(r)
    print(f"\nTier: PAPER_PACKET_TIER={len(paper)} OBSERVATIONAL={len(observational)} KILL={len(kill)}", flush=True)
    if paper:
        print("\nPAPER_PACKET tier — deep-screen + family review + 8-dim audit required:")
        for r in paper:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    if observational:
        print("\nOBSERVATIONAL tier:")
        for r in observational:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11e_fomc_mgc.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "FOMC-MGC data-gap audit + first batch (#157)",
        "calendar_source": "OFFICIAL federalreserve.gov (verified 2026-06-11)",
        "audit": {k: v for k, v in audit.items() if k not in ("clean_events", "details")},
        "clean_events_filter": "gap <= 1h per #146 doctrine",
        "tier": {"PAPER_PACKET_TIER": len(paper), "OBSERVATIONAL": len(observational), "KILL": len(kill)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
