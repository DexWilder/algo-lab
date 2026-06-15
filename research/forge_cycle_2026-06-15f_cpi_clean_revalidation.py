"""Cycle 2026-06-15f — CLEAN-events re-validation of cleared CPI event-window configs.

Lane B / REPORT-ONLY. Applies feedback_event_window_clean_events_rule +
feedback_hold_continuity_canonical_filter to the configs that cleared the raw
harness (15e). Raw MGC showed ON=40 overnight holds = data-gap contamination;
clean metrics are the only trustworthy ones.

Clean filter per event+config:
  1. a bar exists within MAX_GAP_MIN (10) of the CPI release timestamp, AND
  2. the FULL hold window [entry_idx .. exit_idx] is contiguous: no inter-bar
     gap > MAX_HOLD_GAP_MIN (15). Any gap -> drop the event (fictitious-PnL risk).

Reports clean_n vs raw_n + clean PF/median/H1H2/concentration/largest-day-loss/
overnight. Verdict gates on CLEAN metrics only.
"""
from __future__ import annotations

import json
import sys
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

MAX_GAP_MIN = 10        # event must align to a bar within 10 min
MAX_HOLD_GAP_MIN = 15   # no inter-bar gap > 15 min inside the hold window

# (asset, entry_offset, exit_offset, direction, label) — cleared configs + MNQ clean control
CANDIDATES = [
    ("MGC", -12, 12, "long", "pre_drift_L"),
    ("MGC", 1, 24, "long", "post_L_120m"),
    ("6J", -12, 12, "long", "pre_drift_L"),
    ("6J", 1, 24, "long", "post_L_120m"),
    ("6E", -12, 12, "long", "pre_drift_L"),
    ("MNQ", 1, 24, "long", "post_L_120m"),  # clean-data control (MNQ coverage is good)
]


def clean_events(df, events, entry_off, exit_off):
    """Keep events whose entry+hold window is gap-free and event aligns to a bar."""
    dts = pd.to_datetime(df["datetime"]).reset_index(drop=True)
    n = len(dts)
    vals = dts.values
    kept, dropped_align, dropped_gap = [], 0, 0
    for e in events:
        e = pd.Timestamp(e)
        idx = int(np.searchsorted(vals, np.datetime64(e)))
        if idx >= n:
            dropped_align += 1; continue
        # nearest bar gap (look at idx and idx-1)
        cand = [idx] + ([idx - 1] if idx > 0 else [])
        gap = min(abs((dts.iloc[j] - e).total_seconds()) for j in cand) / 60.0
        if gap > MAX_GAP_MIN:
            dropped_align += 1; continue
        entry_idx = idx + entry_off
        exit_idx = entry_idx + exit_off
        if entry_idx < 0 or exit_idx >= n:
            dropped_align += 1; continue
        window = dts.iloc[min(entry_idx, idx):max(exit_idx, idx) + 1]
        maxgap = window.diff().dropna().dt.total_seconds().max() / 60.0
        if maxgap > MAX_HOLD_GAP_MIN:
            dropped_gap += 1; continue
        kept.append(e)
    return kept, dropped_align, dropped_gap


def revalidate(asset, entry_off, exit_off, direction, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dts = pd.to_datetime(df["datetime"])
    events_all = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                  for c in build_verified_cpi_calendar()]
    raw = [e for e in events_all if dts.iloc[0] <= e <= dts.iloc[-1]]
    clean, drop_align, drop_gap = clean_events(df, raw, entry_off, exit_off)
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    sigs = generate_event_window_signals(df, events=clean, entry_offset_bars=entry_off,
                                         exit_offset_bars=exit_off, direction=direction)
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    trades = res["trades_df"]
    m = _metrics(trades, f"{asset}-{label}-clean", costs=res["stats"]["costs"])
    largest_day = overnight = None
    if trades is not None and not trades.empty and "pnl" in trades.columns:
        et = pd.to_datetime(trades["entry_time"])
        largest_day = round(float(trades["pnl"].astype(float).groupby(et.dt.date).sum().min()), 2)
        if "exit_time" in trades.columns:
            overnight = int((pd.to_datetime(trades["exit_time"]).dt.date > et.dt.date).sum())
    pf = m.get("pf"); pf = round(float(pf), 3) if pf == pf else None
    h1 = m.get("h1_pf"); h1 = round(float(h1), 3) if h1 == h1 else None
    h2 = m.get("h2_pf"); h2 = round(float(h2), 3) if h2 == h2 else None
    return {
        "asset": asset, "config": label, "raw_n": len(raw), "clean_n": len(clean),
        "dropped_misalign": drop_align, "dropped_gap": drop_gap,
        "clean_pf": pf, "clean_median": round(float(m.get("median", 0)), 2),
        "clean_h1_pf": h1, "clean_h2_pf": h2,
        "clean_max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
        "clean_largest_day_loss": largest_day, "clean_overnight_holds": overnight,
        "clean_gate_verdict": m.get("gate_verdict"), "clean_archetype": m.get("archetype"),
    }


def run():
    print("Cycle 2026-06-15f — CPI clean-events re-validation (REPORT-ONLY)\n", flush=True)
    rows = []
    for c in CANDIDATES:
        r = revalidate(*c)
        rows.append(r)
        print(f"  {r['asset']:4s} {r['config']:12s} raw_n={r['raw_n']} -> clean_n={r['clean_n']} "
              f"(drop align={r['dropped_misalign']} gap={r['dropped_gap']}) | "
              f"clean PF={r['clean_pf']} med=${r['clean_median']} "
              f"H1/H2={r['clean_h1_pf']}/{r['clean_h2_pf']} maxyr={r['clean_max_year_share_pct']}% "
              f"ON={r['clean_overnight_holds']} dayLoss=${r['clean_largest_day_loss']} "
              f"-> {r['clean_gate_verdict']}", flush=True)

    survivors = [r for r in rows if r["clean_pf"] and r["clean_pf"] >= 1.3 and r["clean_n"] >= 20
                 and r["clean_h1_pf"] and r["clean_h2_pf"]
                 and r["clean_h1_pf"] > 1.0 and r["clean_h2_pf"] > 1.0
                 and (r["clean_overnight_holds"] or 0) <= max(2, int(0.1 * r["clean_n"]))]
    print("\n=== CLEAN SURVIVORS (PF>=1.3, n>=20, both halves >1, low overnight) ===", flush=True)
    for r in survivors:
        print(f"  ** {r['asset']}/{r['config']}: clean PF={r['clean_pf']} n={r['clean_n']} "
              f"med=${r['clean_median']} maxyr={r['clean_max_year_share_pct']}%", flush=True)
    if not survivors:
        print("  NONE survive clean-events validation.", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15f_cpi_clean_revalidation.json"
    out.write_text(json.dumps({
        "cycle": "2026-06-15f_cpi_clean_revalidation", "mode": "Lane B report-only",
        "clean_filter": {"max_event_align_min": MAX_GAP_MIN, "max_hold_gap_min": MAX_HOLD_GAP_MIN},
        "results": rows, "clean_survivors": survivors,
        "calendar_grade": "DATA_REQUIRED (BLS recall; promotion needs machine-fetched-official)",
        "boundaries": "report-only; no promotion/wiring",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
