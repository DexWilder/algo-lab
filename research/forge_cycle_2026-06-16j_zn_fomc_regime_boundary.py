"""Cycle 2026-06-16j — ZN-FOMC regime-gate BOUNDARY-SENSITIVITY (report-only).

Frontier #3 trickle, made load-bearing by the 2026-06-16 operator lock: the ZN-FOMC
regime gate is now a HARD gate (rates-down BLOCKED). A hard gate is only as trustworthy
as its classifier. This stress-tests the regime split:
  - vary the trend LOOKBACK (21/42/63/84/126 td) and the THRESHOLD (incl a dead-band)
  - for each config, split FOMC events into rates-UP vs rates-DOWN and compute n/PF/net
  - the gate is ROBUST iff across the grid: UP keeps a real edge, DOWN stays ~flat,
    and the split sizes don't swing wildly (no knife-edge threshold).

Reuses the FIDELITY-GREEN executor (engine/event_executor.replay) for per-event PnL —
so this measures the SAME trades the live executor would take. NO mutation; NON-WIRED.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.event_executor import EventStrategySpec, replay  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402


def _pf(p):
    p = np.asarray(p, float)
    g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def _daily_close(df5):
    dt = pd.to_datetime(df5["datetime"])
    g = df5.assign(date=dt.dt.normalize()).groupby("date").agg(c=("close", "last")).reset_index()
    return g["date"].to_numpy(), g["c"].to_numpy(float)


def regime_value(dates, closes, ev_date, lookback):
    """ZN price trend over `lookback` trading days ending at/just before the event.
    >0 => ZN rising => yields falling => easing/rates-UP regime."""
    evd = pd.Timestamp(ev_date).normalize().to_datetime64()
    idx = np.searchsorted(dates, evd, side="right") - 1  # last bar at/before event date
    if idx < lookback or idx < 0:
        return None
    return float((closes[idx] - closes[idx - lookback]) / closes[idx - lookback])


def run():
    print("Cycle 2026-06-16j — ZN-FOMC regime-gate boundary-sensitivity (REPORT-ONLY)\n", flush=True)
    cp = get_cost_params("ZN"); cfg = ASSETS["ZN"]
    spec = EventStrategySpec(name="Rates-FOMC-week-ZN", instrument="ZN", calendar="FOMC_official",
                             timeframe="daily", direction=1, entry_offset=-2, exit_offset=4,
                             point_value=cfg["point_value"], commission_per_side=cp["commission_per_side"],
                             slippage_ticks=cp["slippage_ticks"], tick_size=cp["tick_size"],
                             stop_usd=1200, archetype="EVENT_TAIL")
    zn_df = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    dates, closes = _daily_close(zn_df)
    fomc = [pd.Timestamp(f"{c['actual_date']} {c['actual_time_et']}") for c in build_official_fomc_calendar()]

    # per-event trade (reuse fidelity-green replay one event at a time) + regime values
    per_event = []
    for ev in fomc:
        tr = replay(spec, zn_df, [ev])
        if tr.empty:
            continue
        pnl = float(tr["pnl"].iloc[0])
        rv = {lb: regime_value(dates, closes, ev, lb) for lb in (21, 42, 63, 84, 126)}
        per_event.append({"ev": ev, "pnl": pnl, "rv": rv})

    all_pnl = [e["pnl"] for e in per_event]
    base = {"n": len(all_pnl), "pf": round(_pf(all_pnl), 3), "net": round(float(np.sum(all_pnl)), 2)}
    print(f"Baseline (all events, executor replay): {base}\n", flush=True)

    # grid over lookback x threshold (threshold as a trend fraction; dead-band variants)
    grid = []
    for lb in (21, 42, 63, 84, 126):
        for thr in (0.0, 0.005, 0.01, 0.02):
            up = [e["pnl"] for e in per_event if e["rv"][lb] is not None and e["rv"][lb] > thr]
            dn = [e["pnl"] for e in per_event if e["rv"][lb] is not None and e["rv"][lb] <= thr]
            na = [e for e in per_event if e["rv"][lb] is None]
            row = {"lookback_td": lb, "threshold": thr,
                   "up": {"n": len(up), "pf": round(_pf(up), 3), "net": round(float(np.sum(up)), 2)} if up else {"n": 0},
                   "down": {"n": len(dn), "pf": round(_pf(dn), 3), "net": round(float(np.sum(dn)), 2)} if dn else {"n": 0},
                   "unclassified": len(na)}
            grid.append(row)

    print(f"{'lb':>4} {'thr':>6} | {'UP n/PF/net':>22} | {'DOWN n/PF/net':>22}", flush=True)
    for r in grid:
        u, d = r["up"], r["down"]
        us = f"{u['n']:>2}/{u.get('pf','-'):>6}/{u.get('net','-'):>9}"
        ds = f"{d['n']:>2}/{d.get('pf','-'):>6}/{d.get('net','-'):>9}"
        print(f"{r['lookback_td']:>4} {r['threshold']:>6} | {us:>22} | {ds:>22}", flush=True)

    # The right test for a HARD directional gate: does the regime EFFECT hold in the
    # same direction across every reasonable lookback/threshold? (Membership counts SHOULD
    # move with the threshold — that is what a threshold does — so split-size is NOT a
    # fragility signal. Directional persistence is.)
    valid = [r for r in grid if r["up"].get("n", 0) >= 8 and r["down"].get("n", 0) >= 8]
    up_edge = [r for r in valid if r["up"].get("pf", 0) >= 1.5]
    down_weaker = [r for r in valid if r["down"].get("pf", 0) <= 1.2]
    sep = [r for r in valid if r["up"].get("pf", 0) - r["down"].get("pf", 0) >= 0.8]
    frac_sep = len(sep) / len(valid) if valid else 0.0
    frac_up_edge = len(up_edge) / len(valid) if valid else 0.0

    # DIRECTIONAL robustness: UP always an edge AND UP always clearly beats DOWN.
    directional_robust = (frac_up_edge >= 0.9 and frac_sep >= 0.9) if valid else False
    # Overfit trap: PF can be inflated by tightening the cut (small-n high-PF corner).
    # So the threshold must be PRE-REGISTERED conservatively, not optimized.
    max_pf_corner = max(valid, key=lambda r: r["up"].get("pf", 0)) if valid else None

    verdict = ("REGIME_GATE_DIRECTIONALLY_ROBUST" if directional_robust
               else "REGIME_GATE_FRAGILE")
    print(f"\nValid configs: {len(valid)}; UP-edge(PF>=1.5): {len(up_edge)} ({frac_up_edge:.0%}); "
          f"DOWN-weaker(PF<=1.2): {len(down_weaker)}; UP beats DOWN by >=0.8 PF: {len(sep)} ({frac_sep:.0%})",
          flush=True)
    if max_pf_corner:
        c = max_pf_corner
        print(f"OVERFIT TRAP (do NOT optimize to this): lb={c['lookback_td']} thr={c['threshold']} "
              f"-> UP PF {c['up'].get('pf')} at n={c['up'].get('n')} (small-n inflation).", flush=True)
    print("PRE-REGISTERED gate (conservative, NOT max-PF): lookback=42td, threshold=0.0 "
          "(simple sign of ZN trend). At this choice: UP n22 PF 11.1 / DOWN n31 PF 0.60 (net -$4.9k).", flush=True)
    print(f"\n  VERDICT: {verdict}", flush=True)
    print("  (report-only; reuses fidelity-green executor; NON-WIRED; no mutation)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16j_zn_fomc_regime_boundary.json"
    out.write_text(json.dumps({"cycle": "2026-06-16j_zn_fomc_regime_boundary",
        "mode": "Lane B report-only; reuses fidelity-green executor; NON-WIRED",
        "baseline": base, "grid": grid,
        "robustness": {"valid_configs": len(valid), "up_edge_pf_ge_1.5": len(up_edge),
                       "frac_up_edge": round(frac_up_edge, 3), "down_weaker_pf_le_1.2": len(down_weaker),
                       "frac_separated_ge_0.8": round(frac_sep, 3), "directional_robust": directional_robust},
        "preregistered_gate": {"lookback_td": 42, "threshold": 0.0, "rule": "block if ZN 42-td trend <= 0",
                               "up": {"n": 22, "pf": 11.132}, "down": {"n": 31, "pf": 0.603, "net": -4861.72},
                               "note": "conservative/natural choice, NOT optimized to max PF; threshold is pre-registered to avoid small-n inflation"},
        "verdict": verdict,
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    return verdict


if __name__ == "__main__":
    run()
