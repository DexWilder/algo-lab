"""Cycle 2026-06-11a — CPI event-window first batch on MES/MNQ/ZN.

Per operator decision #153 OK A. Cleanest event-ready assets per data-gap audit:
  - MES: CPI clean 91.1% (CLEAN_EVENT_READY)
  - MNQ: CPI clean 91.1% (CLEAN_EVENT_READY)
  - ZN:  CPI clean 90.0% (CLEAN_EVENT_READY)

Mandatory clean-events filter per #146 doctrine.

Test matrix:
  - 3 assets × 2 directions (long, short) × 3 holding windows (1h, 2h, 4h) = 18 candidates
  - Direction bidirectional because CPI surprise direction is ambiguous a priori
  - EOD skipped per #153 'only if cheap'

CRITICAL: Calendar is Forge-recall verified per #140 still DATA_REQUIRED.
Packet acceptance blocked until operator verifies BLS calendar.

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
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def filter_clean_events(events, df, max_gap_minutes=60):
    """Apply clean-events filter per #146 doctrine."""
    df_dt = pd.to_datetime(df["datetime"])
    clean = []
    contaminated = []
    for ev in events:
        after = df[df_dt > ev].head(1)
        if len(after) == 0:
            contaminated.append((ev, "no future bar"))
            continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes and ev >= df_dt.iloc[0]:
            clean.append(ev)
        else:
            contaminated.append((ev, f"{gap_min/60:.1f}h gap" if gap_min > max_gap_minutes else "pre-data-start"))
    return clean, contaminated


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 20: return f"KILL (n={n}, tail-engine min 20)"
    if median < 0 and pf >= 1.2: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def _run(asset, events, exit_bars=24, direction="long",
         commission_mult=1.0, slippage_mult=1.0, label=""):
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
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


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
    print("Cycle 2026-06-11a — CPI event-window batch on MES/MNQ/ZN (#153)", flush=True)
    print("Calendar: Forge-recall (still DATA_REQUIRED per #140).", flush=True)
    print("Clean-events filter applied per #146 doctrine.\n", flush=True)

    cpi_events_all = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                      for c in build_verified_cpi_calendar()]
    print(f"Total CPI events (Forge-recall): {len(cpi_events_all)}\n", flush=True)

    # Per-asset clean events
    clean_per_asset = {}
    for asset in ["MES", "MNQ", "ZN"]:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
        clean, contaminated = filter_clean_events(cpi_events_all, df, max_gap_minutes=60)
        clean_per_asset[asset] = clean
        print(f"  {asset}: {len(clean)} clean events ({len(clean)/len(cpi_events_all)*100:.1f}%), {len(contaminated)} excluded", flush=True)
    print()

    t_start = time.time()
    results = []
    for asset in ["MES", "MNQ", "ZN"]:
        for direction in ["long", "short"]:
            for hold_h, exit_bars in [("1h", 12), ("2h", 24), ("4h", 48)]:
                label = f"CPI-{asset}-{direction[0].upper()}{direction[1:].lower()}-{hold_h}"
                events = clean_per_asset[asset]
                t0 = time.time()
                try:
                    m, trades = _run(asset, events, exit_bars=exit_bars,
                                      direction=direction, label=label)
                    v = _classify(m)
                    stress = None
                    if "WATCH" in v:
                        stress = stress_screen(asset, events, exit_bars, direction, label)
                except Exception as e:
                    print(f"  {label}: ERROR {e}", flush=True)
                    results.append({"label": label, "error": str(e)})
                    continue
                elapsed = time.time() - t0
                stress_str = f" stress={stress['verdict']}" if stress else ""
                print(
                    f"  {label:25s}: n={m['n']:4d} PF={m['pf']:.3f} "
                    f"median=${m['median']:7.2f} → {v}{stress_str} [{elapsed:.0f}s]",
                    flush=True
                )
                results.append({
                    "label": label, "asset": asset, "direction": direction,
                    "exit_bars": exit_bars,
                    "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
                    "verdict": v, "stress": stress,
                    "n_clean_events": len(events),
                })
    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s", flush=True)

    paper, observational, kill = [], [], []
    for r in results:
        if "error" in r: continue
        v = r["verdict"]; s = r.get("stress")
        if "KILL" in v: kill.append(r)
        elif "WATCH_FOR_DEEP_SCREEN" in v:
            if s and s["verdict"] == "PASS_STRESS": paper.append(r)
            else: observational.append(r)
        elif "WATCH" in v: observational.append(r)
    print(f"\nTier: PAPER_PACKET={len(paper)} OBSERVATIONAL={len(observational)} KILL={len(kill)}", flush=True)
    if paper:
        print("\nPAPER_PACKET tier — requires deep-screen + family review + audit:")
        for r in paper:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11a_cpi_MES_MNQ_ZN.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "CPI event-window first batch on MES/MNQ/ZN (#153)",
        "calendar_status": "Forge-recall verified; DATA_REQUIRED per #140 — packet acceptance blocked",
        "clean_events_filter": "gap <= 1h applied per #146 doctrine",
        "clean_events_per_asset": {k: len(v) for k, v in clean_per_asset.items()},
        "tier": {"PAPER_PACKET": len(paper), "OBSERVATIONAL": len(observational), "KILL": len(kill)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
