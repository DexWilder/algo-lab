"""Cycle 2026-06-08f — NFP event-window expansion to MCL (crude oil).

Per operator decision #94 Hybrid D-B: restart sparse/tail/event exploration
on metals/commodities where calendar is clean.

Hypothesis: NFP releases (1st Friday of month, 8:30 ET) create directional
flows in USD which affect crude oil pricing. The same 2h post-event window
that worked for MGC (Packet #1) may work for MCL.

Tests:
  - NFP-MCL-Long-2h (matching Packet #1 template)
  - NFP-MCL-Short-2h (opposite direction control)
  - NFP-MCL-Long-1h (shorter window)
  - NFP-MCL-Long-4h (longer window)

Boundaries: report-only Lane B. Cost via get_cost_params (Evidence Law).
Family review vs Packet #1 if any survivor — corr to NFP-MGC > 0.7 = DUPLICATE.
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
from research.forge_nfp_calendar_verify import (  # noqa: E402
    build_verified_nfp_calendar,
)
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _bake_calendar():
    cal = build_verified_nfp_calendar(2019, 2026)
    return [pd.to_datetime(f"{c['actual_date']} 08:30:00") for c in cal]


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 20: return f"KILL (n={n}, tail-engine min 20)"
    if median < 0 and pf >= 1.2: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def _run(asset, events, exit_bars=24, entry_bars=1, direction="long",
         commission_mult=1.0, slippage_mult=1.0, label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_bars,
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


def stress_screen_event(asset, events, exit_bars, direction, label):
    """Lightweight prop-stress for event candidates: baseline + 2x cost + 1tick."""
    rows = []
    for stress_label, cm, sm in [
        ("baseline (1x)", 1.0, 1.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
    ]:
        m, _ = _run(asset, events, exit_bars=exit_bars, direction=direction,
                    commission_mult=cm, slippage_mult=sm,
                    label=f"{label}-{stress_label}")
        rows.append({"stress": stress_label, "n": m["n"], "pf": float(m["pf"]),
                     "median": float(m["median"]), "net": float(m["net"])})
    moderate = next(r for r in rows if r["stress"] == "2x cost + 2 ticks slip")
    if moderate["median"] <= 0:
        verdict = "FAIL_STRESS"
    elif moderate["median"] < 1.0:
        verdict = "KNIFE_EDGE"
    else:
        verdict = "PASS_STRESS"
    return {"rows": rows, "verdict": verdict}


SPECS = [
    ("NFP-MCL-Long-2h", "MCL", "long", 24),
    ("NFP-MCL-Short-2h", "MCL", "short", 24),
    ("NFP-MCL-Long-1h", "MCL", "long", 12),
    ("NFP-MCL-Long-4h", "MCL", "long", 48),
    ("NFP-MCL-Long-EOD", "MCL", "long", 72),
]


def run():
    print("Cycle 2026-06-08f — NFP event-window expansion to MCL (Hybrid D-B leg)", flush=True)
    print("Boundaries: report-only Lane B; no registry/portfolio/scheduler/promotion mutation\n", flush=True)
    events = _bake_calendar()
    print(f"NFP calendar: {len(events)} events ({events[0].date()} to {events[-1].date()})\n", flush=True)
    t_start = time.time()
    results = []
    for label, asset, direction, exit_bars in SPECS:
        t0 = time.time()
        try:
            m, trades = _run(asset, events, exit_bars=exit_bars,
                             direction=direction, label=label)
            v = _classify(m)
            stress = None
            if "WATCH" in v:
                stress = stress_screen_event(asset, events, exit_bars, direction, label)
        except Exception as e:
            print(f"  {label}: ERROR {e}", flush=True)
            results.append({"label": label, "error": str(e)})
            continue
        elapsed = time.time() - t0
        stress_str = f" stress={stress['verdict']}" if stress else ""
        print(
            f"  {label:25s} ({direction:5s}, {exit_bars}b): n={m['n']:4d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} → {v}{stress_str} [{elapsed:.0f}s]",
            flush=True
        )
        results.append({
            "label": label, "asset": asset, "direction": direction,
            "exit_bars": exit_bars,
            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
            "verdict": v,
            "stress": stress,
            "elapsed_seconds": elapsed,
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
        print("\nPAPER_PACKET tier (passes prop-stress) — requires family review vs Packet #1:")
        for r in paper:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-08f.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "NFP event-window expansion to MCL — Hybrid D-B leg restart of sparse/tail/event hunt",
        "operator_approval": "OK D Hybrid (#94)",
        "boundaries": "report-only Lane B",
        "calendar": "verified NFP calendar (2019-2026), 1st-Friday rule with shifts",
        "tier": {"PAPER_PACKET": len(paper), "OBSERVATIONAL": len(observational), "KILL": len(kill)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
