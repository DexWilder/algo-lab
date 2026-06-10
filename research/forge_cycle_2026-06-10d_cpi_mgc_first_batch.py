"""Cycle 2026-06-10d — CPI-MGC event-window first batch.

Per operator decision #132 (proceed to CPI-MGC) and #128 (metals-specific events;
single-asset; clean calendar required).

Template: same as Packet #1 (EVT-NFP-MGC-Long-2h). Entry +1 bar after event,
exit at multiple hold windows.

Tests:
  - CPI-MGC-Long-2h (matching Packet #1 template, 2h holding)
  - CPI-MGC-Short-2h (control)
  - CPI-MGC-Long-1h (shorter window)
  - CPI-MGC-Long-4h (longer window)
  - CPI-MGC-Long-EOD (~6h late session)

Family review vs Packet #1 NFP-MGC mandatory if any survivor — different
event days but both BLS-USD-driving so possible overlap.

Boundaries: report-only Lane B. No registry/scheduler/portfolio/promotion mutation.
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
from research.forge_cpi_calendar import build_cpi_release_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _bake_calendar():
    cal = build_cpi_release_calendar(2019, 2026)
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in cal]


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 20: return f"KILL (n={n}, tail-engine min 20)"
    if median < 0 and pf >= 1.2: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def _run(events, exit_bars=24, entry_bars=1, direction="long",
         commission_mult=1.0, slippage_mult=1.0, label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    costs = get_cost_params("MGC")
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_bars,
        exit_offset_bars=exit_bars, direction=direction,
    )
    res = run_backtest(
        df, sigs, mode="both", point_value=cfg["point_value"], symbol="MGC",
        commission_per_side=costs["commission_per_side"] * commission_mult,
        slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slippage_mult)),
        tick_size=costs["tick_size"],
    )
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


def stress_screen_event(events, exit_bars, direction, label):
    """5-rung break-even diagnostic for event candidates."""
    rows = []
    for stress_label, cm, sm in [
        ("baseline (1x)", 1.0, 1.0),
        ("1.5x cost + 1 tick slip", 1.5, 2.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
        ("4x cost + 2 ticks slip", 4.0, 3.0),
    ]:
        m, _ = _run(events, exit_bars=exit_bars, direction=direction,
                    commission_mult=cm, slippage_mult=sm,
                    label=f"{label}-{stress_label}")
        rows.append({"stress": stress_label, "n": m["n"], "pf": float(m["pf"]),
                     "median": float(m["median"]), "net": float(m["net"])})
    moderate = next(r for r in rows if r["stress"] == "2x cost + 2 ticks slip")
    extreme = next(r for r in rows if r["stress"] == "4x cost + 2 ticks slip")
    if moderate["median"] <= 0:
        verdict = "FAIL_STRESS"
    elif moderate["median"] < 1.0:
        verdict = "KNIFE_EDGE"
    elif extreme["median"] <= 0:
        verdict = "KNIFE_EDGE (4x stress)"
    else:
        verdict = "PASS_STRESS"
    return {"rows": rows, "verdict": verdict}


SPECS = [
    ("CPI-MGC-Long-2h", "long", 24),
    ("CPI-MGC-Short-2h", "short", 24),
    ("CPI-MGC-Long-1h", "long", 12),
    ("CPI-MGC-Long-4h", "long", 48),
    ("CPI-MGC-Long-EOD", "long", 72),
]


def run():
    print("Cycle 2026-06-10d — CPI-MGC event-window first batch (#132)", flush=True)
    print("Boundaries: report-only Lane B; calendar = rule-based v1, audit pending.\n", flush=True)
    events = _bake_calendar()
    print(f"CPI calendar: {len(events)} events ({events[0].date()} to {events[-1].date()})", flush=True)
    print(f"Calendar status: RULE-BASED (2nd Tuesday at 8:30 ET); AUDIT REQUIRED before production\n", flush=True)
    t_start = time.time()
    results = []
    for label, direction, exit_bars in SPECS:
        t0 = time.time()
        try:
            m, _ = _run(events, exit_bars=exit_bars, direction=direction, label=label)
            v = _classify(m)
            stress = None
            if "WATCH" in v:
                stress = stress_screen_event(events, exit_bars, direction, label)
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
            "label": label, "direction": direction, "exit_bars": exit_bars,
            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
            "verdict": v, "stress": stress, "elapsed_seconds": elapsed,
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
        print("\nPAPER_PACKET tier — REQUIRES family review vs Packet #1 + 8-dim audit:")
        for r in paper:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-10d.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "CPI-MGC event-window first batch (#132 metals-specific events)",
        "operator_approval": "OK 128 metals-specific permitted + OK 132 proceed to CPI-MGC",
        "calendar_source": "research/forge_cpi_calendar.py (v1 rule-based; audit required)",
        "calendar_caveat": "Uses 2nd Tuesday rule; actual BLS releases sometimes shift to Wednesday or Thursday. ~80% expected accuracy. Cross-check required for any promotion.",
        "boundaries": "report-only Lane B",
        "tier": {"PAPER_PACKET": len(paper), "OBSERVATIONAL": len(observational), "KILL": len(kill)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
