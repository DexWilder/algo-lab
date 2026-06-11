"""Cycle 2026-06-11g — Last-hour drift workhorse on MES/MNQ.

Per operator decision #159 OK E: Last-hour drift first, Overnight gap as
fallback. Pivot to workhorse archetype to escape sparse-event concentration
trap (CPI/NFP/FOMC all hit 100%+ max-yr).

Hypothesis:
  Last RTH hour (15:00-16:00 ET) has documented directional drift due to
  end-of-day flows (pension rebalancing, ETF settlements, hedger covering).
  This is a workhorse mechanism: ~250 sessions/year × 8 years = ~2000 trades.
  Sample size dilutes concentration risk.

Mechanism (simplest possible, no filters first pass):
  - Each RTH trading day, enter at 15:00 ET (final-hour start)
  - Hold for 12 bars = 60 min → exit at 16:00 ET (RTH close)
  - Direction: long or short (test both)

Implementation: reuse event_window_engine by treating 15:00 ET each session
as a synthetic "event".

Matrix: 2 assets × 2 directions × 1 hold window = 4 candidates.

Per #159 gates: positive median, PF ≥ 1.15 cheap-screen / ≥ 1.30 watch,
PASS_STRESS, max-yr ≤ 50%, yrs+ ≥ 50%, Era3 PF ≥ 1.0, Era3 median ≥ 0.

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, time as dtime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def build_last_hour_events(df, hour_et=15, minute_et=0):
    """Synthesize 'events' at 15:00 ET each RTH trading day.

    Returns a list of pd.Timestamp at 15:00 ET on every distinct RTH date.
    """
    dt = pd.to_datetime(df["datetime"])
    # Filter to bars at the target time
    mask = (dt.dt.hour == hour_et) & (dt.dt.minute == minute_et)
    events_df = df[mask].copy()
    events_df["dt"] = pd.to_datetime(events_df["datetime"])
    return list(events_df["dt"])


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 100: return f"KILL (n={n}, workhorse min 100)"
    if median < 0 and pf >= 1.15: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return f"KILL (PF<1.15)"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def _run(asset, events, exit_bars=12, direction="long",
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
    if moderate["median"] < 0.5: return {"rows": rows, "verdict": "KNIFE_EDGE"}
    if extreme["median"] <= 0: return {"rows": rows, "verdict": "KNIFE_EDGE (4x)"}
    return {"rows": rows, "verdict": "PASS_STRESS"}


def run():
    print("Cycle 2026-06-11g — Last-hour drift workhorse on MES/MNQ (#159)", flush=True)
    print("Mechanism: 15:00 ET entry, 16:00 ET exit (12 5min bars), both directions.\n", flush=True)

    t_start = time.time()
    results = []
    events_per_asset = {}
    for asset in ["MES", "MNQ"]:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
        events = build_last_hour_events(df, hour_et=15, minute_et=0)
        events_per_asset[asset] = events
        print(f"  {asset}: {len(events)} session entries (15:00 ET bars)", flush=True)
    print()

    for asset in ["MES", "MNQ"]:
        for direction in ["long", "short"]:
            label = f"LHD-{asset}-{direction[0].upper()}{direction[1:].lower()}-60m"
            events = events_per_asset[asset]
            t0 = time.time()
            try:
                m, trades = _run(asset, events, exit_bars=12, direction=direction, label=label)
                v = _classify(m)
                stress = None
                if "WATCH" in v:
                    stress = stress_screen(asset, events, 12, direction, label)
            except Exception as e:
                print(f"  {label}: ERROR {e}", flush=True)
                results.append({"label": label, "error": str(e)})
                continue
            elapsed = time.time() - t0
            stress_str = f" stress={stress['verdict']}" if stress else ""
            print(
                f"  {label:30s}: n={m['n']:5d} PF={m['pf']:.3f} "
                f"median=${m['median']:6.2f} → {v}{stress_str} [{elapsed:.0f}s]",
                flush=True
            )
            results.append({
                "label": label, "asset": asset, "direction": direction,
                "exit_bars": 12,
                "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
                "verdict": v, "stress": stress,
                "n_session_entries": len(events),
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
        print("\nPAPER_PACKET tier — deep-screen + family review required:")
        for r in paper:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    if observational:
        print("\nOBSERVATIONAL tier:")
        for r in observational:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11g_last_hour_drift.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Last-hour drift workhorse on MES/MNQ (#159 Option B)",
        "mechanism": "Enter at 15:00 ET, exit 60min later at 16:00 ET, both directions",
        "tier": {"PAPER_PACKET_TIER": len(paper), "OBSERVATIONAL": len(observational), "KILL": len(kill)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
