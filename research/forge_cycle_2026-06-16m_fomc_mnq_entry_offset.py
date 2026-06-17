"""Cycle 2026-06-16m — FOMC-MNQ-1h ENTRY-OFFSET robustness (report-only).

The remaining boundary question for FOMC-MNQ-1h: is the +1-bar entry REAL post-FOMC
drift, or a lucky convention? If only +1 works -> fragile (WATCH, strict caution). If a
band of nearby entries survives -> a credible independent event engine.

Answers, per the operator's questions:
  - Does +0/+1/+2/+3 still work? (sweep entry_offset)
  - Is +1 uniquely magic or part of a broader drift window?
  - Does entering ON the release bar (+0) add noise/drawdown? (std, largest loss, win rate)
  - Does later entry preserve PF but reduce opportunity? (net vs PF by offset)
  - Does the edge vanish if you AVOID the immediate release bar? (offsets >= 2)

Reuses the FIDELITY-GREEN executor. Hold fixed at the validated 12 bars (hold-robustness
already shown in 16k). NO mutation; NON-WIRED.
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


def _stats(p):
    p = np.asarray(p, float)
    if len(p) == 0:
        return {"n": 0}
    return {"n": int(len(p)), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 2),
            "median": round(float(np.median(p)), 2), "mean": round(float(p.mean()), 2),
            "std": round(float(p.std(ddof=1)), 2) if len(p) > 1 else 0.0,
            "win_rate": round(float((p > 0).mean()), 3), "largest_loss": round(float(p.min()), 2)}


def clean_fomc_events(df5, fomc):
    dt = pd.to_datetime(df5["datetime"])
    ev = []
    for e in fomc:
        if e < dt.iloc[0] or e > dt.iloc[-1]:
            continue
        after = df5[dt > e].head(1)
        if len(after) and (pd.to_datetime(after["datetime"].iloc[0]) - e).total_seconds() / 60 <= 60:
            ev.append(e)
    return ev


def run():
    print("Cycle 2026-06-16m — FOMC-MNQ-1h entry-offset robustness (REPORT-ONLY)\n", flush=True)
    cp = get_cost_params("MNQ"); cfg = ASSETS["MNQ"]
    fomc = [pd.Timestamp(f"{c['actual_date']} {c['actual_time_et']}") for c in build_official_fomc_calendar()]
    mnq_df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    clean_ev = clean_fomc_events(mnq_df, fomc)
    print(f"clean FOMC events: n={len(clean_ev)}; hold fixed = 12 bars (60min)\n", flush=True)

    sweep = {}
    for eoff in (0, 1, 2, 3, 4, 5, 6):
        spec = EventStrategySpec(name="FOMC-MNQ-Long-1h", instrument="MNQ", calendar="FOMC_official",
                                 timeframe="intraday_5m", direction=1, entry_offset=eoff, exit_offset=12,
                                 point_value=cfg["point_value"], commission_per_side=cp["commission_per_side"],
                                 slippage_ticks=cp["slippage_ticks"], tick_size=cp["tick_size"], archetype="EVENT_TAIL")
        tr = replay(spec, mnq_df, clean_ev)
        sweep[eoff] = _stats(tr["pnl"].to_numpy() if not tr.empty else np.array([]))

    print(f"{'off':>3} | {'n':>3} {'PF':>6} {'net':>9} {'med':>7} {'std':>8} {'win%':>5} {'maxLoss':>9}", flush=True)
    for o, m in sweep.items():
        tag = "  <- release bar" if o == 0 else ("  <- validated" if o == 1 else "")
        print(f"{o:>3} | {m['n']:>3} {m['pf']:>6} {m['net']:>9} {m['median']:>7} {m['std']:>8} "
              f"{m['win_rate']:>5} {m['largest_loss']:>9}{tag}", flush=True)

    # ---- answer the boundary questions ----
    band = [o for o in (0, 1, 2, 3) if sweep[o].get("pf", 0) >= 1.2 and sweep[o].get("n", 0) >= 20]
    avoid_release = [o for o in (2, 3, 4) if sweep[o].get("pf", 0) >= 1.2]
    plus1_unique = (sweep[1].get("pf", 0) >= 1.2 and len([o for o in (0, 2, 3) if sweep[o].get("pf", 0) >= 1.2]) == 0)
    release_noisier = (sweep[0].get("std", 0) > sweep[1].get("std", 0) and
                       sweep[0].get("largest_loss", 0) < sweep[1].get("largest_loss", 0))
    drift_window = len(band) >= 3  # +1 is part of a broader post-FOMC drift window

    if plus1_unique:
        verdict = "ENTRY_FRAGILE_PLUS1_ONLY — keep WATCH, strict caution"
    elif drift_window:
        verdict = "ENTRY_ROBUST_DRIFT_WINDOW — credible independent event engine"
    else:
        verdict = "ENTRY_PARTIAL — survives a narrow band; WATCH-credible, size conservatively"

    print(f"\nPF>=1.2 band within +0..+3: offsets {band}", flush=True)
    print(f"  edge survives AVOIDING the release bar (offsets +2..+4 >=1.2): {avoid_release}", flush=True)
    print(f"  +1 uniquely magic (only +1 works): {plus1_unique}", flush=True)
    print(f"  release bar (+0) noisier (higher std AND worse largest loss) than +1: {release_noisier}", flush=True)
    print(f"  broad post-FOMC drift window (>=3 of +0..+3 survive): {drift_window}", flush=True)
    print(f"\n  VERDICT: {verdict}", flush=True)
    print("  (report-only; reuses fidelity-green executor; NON-WIRED; no mutation)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16m_fomc_mnq_entry_offset.json"
    out.write_text(json.dumps({"cycle": "2026-06-16m_fomc_mnq_entry_offset",
        "mode": "Lane B report-only; reuses fidelity-green executor; NON-WIRED",
        "clean_events": len(clean_ev), "hold_bars": 12, "entry_offset_sweep": sweep,
        "analysis": {"pf_ge_1.2_band_0to3": band, "edge_survives_avoiding_release_bar": avoid_release,
                     "plus1_uniquely_magic": plus1_unique, "release_bar_noisier": release_noisier,
                     "broad_drift_window": drift_window},
        "verdict": verdict,
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
