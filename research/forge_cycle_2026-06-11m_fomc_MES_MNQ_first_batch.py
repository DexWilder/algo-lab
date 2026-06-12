"""Cycle 2026-06-11m — FOMC-MES/MNQ first batch under V1 doctrine.

Per operator decision #173 OK A. POST-V1 NONSTOP HUNTING restart batch.

Search basis: FOMC equity-index event-window
  - Asset: MES, MNQ (CLEAN_EVENT_READY for FOMC per 11i strict audit at 93.1%)
  - Event: FOMC scheduled meetings (58 events, OFFICIAL Fed.gov calendar)
  - Direction: long and short (first-time test of both directions on equities)
  - Hold: 1h (12 bars; strict-only filter sufficient per R1 carve-out)
  - Calendar: MACHINE_FETCHED_OFFICIAL (Fed.gov)
  - Filter: strict next-bar only (hold == 60min)

V1 tail-engine gates applied:
  - n >= 20
  - PF >= 1.30 STRONG
  - Stress PF >= 1.30 at 2x cost + 2 ticks slip
  - Max instance <= 35%
  - Positive instance fraction >= 60%
  - Instance CV <= 3.0
  - Era 3 PF >= 1.0
  - Calendar grade >= MACHINE_FETCHED_OFFICIAL
  - Era 3 median: SOFT flag

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


def strict_filter(events, df, max_gap_minutes=60):
    """Strict next-bar only — sufficient per R1 for hold <= 60min."""
    df_dt = pd.to_datetime(df["datetime"])
    clean = []
    for ev in events:
        if ev < df_dt.iloc[0]: continue
        after = df[df_dt > ev].head(1)
        if len(after) == 0: continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes: clean.append(ev)
    return clean


def temporal_split(trades):
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)), "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i + 1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i + 1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    nets = [y["net"] for y in per_year]
    total_net = sum(nets)
    max_yr_share = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
    nets_arr = np.array(nets)
    instance_cv = float(nets_arr.std() / nets_arr.mean()) if nets_arr.mean() != 0 else float("inf")
    return {
        "per_year": per_year, "eras": eras,
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year), "total_net": total_net,
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
        "max_yr_share_pct": max_yr_share,
        "instance_cv": instance_cv,
        "positive_instance_fraction": sum(1 for r in per_year if r["net"] > 0) / len(per_year) if per_year else 0,
    }


def _run(asset, events, exit_bars, direction, label, cost_mult=1.0, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=1, exit_offset_bars=exit_bars, direction=direction,
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


def evaluate_v1_tail_engine_gates(m, ts, stress_m, calendar_grade):
    return {
        "n_>=_20": m["n"] >= 20,
        "PF_>=_1.30": m["pf"] >= 1.30,
        "PASS_STRESS_PF_>=_1.30": stress_m["pf"] >= 1.30,
        "max_instance_<=_35pct": ts["max_yr_share_pct"] <= 35.0,
        "positive_instance_frac_>=_60pct": ts["positive_instance_fraction"] >= 0.6,
        "instance_CV_<=_3.0": ts["instance_cv"] <= 3.0,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
        "calendar_grade_OK": calendar_grade in ("OFFICIAL_SOURCE_VERIFIED", "OPERATOR_VERIFIED",
                                                  "MACHINE_FETCHED_OFFICIAL"),
    }


def _classify_cheap(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 20: return f"KILL (n={n}, tail-engine min 20)"
    if median < 0 and pf >= 1.2: return "KILL (asymmetric trap)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if pf >= 1.30 and median > 0: return "ESCALATE_TO_V1_AUDIT"
    return "WATCH"


def run():
    print("Cycle 2026-06-11m — FOMC-MES/MNQ first batch under V1 (#173)", flush=True)
    print("Calendar: OFFICIAL Fed.gov. Filter: strict-only (hold==60min).", flush=True)
    print("V1 tail-engine gates applied to any escalation candidate.\n", flush=True)

    fomc_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                   for c in build_official_fomc_calendar()]

    clean_per_asset = {}
    for asset in ["MES", "MNQ"]:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
        clean = strict_filter(fomc_events, df, max_gap_minutes=60)
        clean_per_asset[asset] = clean
        print(f"  {asset}: {len(clean)} clean FOMC events ({len(clean)/len(fomc_events)*100:.1f}%)", flush=True)
    print()

    t_start = time.time()
    results = []
    for asset in ["MES", "MNQ"]:
        for direction in ["long", "short"]:
            label = f"FOMC-{asset}-{direction[0].upper()}{direction[1:].lower()}-1h"
            events = clean_per_asset[asset]
            t0 = time.time()
            try:
                m, trades = _run(asset, events, exit_bars=12, direction=direction, label=label)
                cheap_verdict = _classify_cheap(m)
                v1_gates = None
                v1_verdict = None
                stress_m = None
                if cheap_verdict == "ESCALATE_TO_V1_AUDIT":
                    stress_m, _ = _run(asset, events, exit_bars=12, direction=direction,
                                        label=f"{label}-stress", cost_mult=2.0, slip_mult=3.0)
                    ts = temporal_split(trades)
                    v1_gates = evaluate_v1_tail_engine_gates(m, ts, stress_m,
                                                              calendar_grade="MACHINE_FETCHED_OFFICIAL")
                    all_pass = all(v1_gates.values())
                    v1_verdict = "PAPER_PACKET_CANDIDATE" if all_pass else \
                                  f"ARCHIVED (fails: {[k for k, v in v1_gates.items() if not v]})"
            except Exception as e:
                import traceback; traceback.print_exc()
                print(f"  {label}: ERROR {e}", flush=True)
                results.append({"label": label, "error": str(e)})
                continue
            elapsed = time.time() - t0
            extra = f" → {v1_verdict}" if v1_verdict else ""
            print(
                f"  {label:25s}: n={m['n']:3d} PF={m['pf']:.3f} "
                f"median=${m['median']:7.2f} → {cheap_verdict}{extra} [{elapsed:.0f}s]",
                flush=True
            )
            results.append({
                "label": label, "asset": asset, "direction": direction,
                "exit_bars": 12,
                "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
                "cheap_verdict": cheap_verdict,
                "v1_gates": v1_gates,
                "v1_verdict": v1_verdict,
                "stress_metrics": {"pf": float(stress_m["pf"]), "median": float(stress_m["median"])}
                                    if stress_m else None,
                "n_clean_events": len(events),
            })
    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s", flush=True)

    paper_candidates = [r for r in results if r.get("v1_verdict") == "PAPER_PACKET_CANDIDATE"]
    archived = [r for r in results if "ARCHIVED" in (r.get("v1_verdict") or "") or "KILL" in r.get("cheap_verdict", "")]

    print(f"\nV1 tier: PAPER_PACKET_CANDIDATE={len(paper_candidates)} ARCHIVED={len(archived)}", flush=True)
    if paper_candidates:
        print("\nPAPER_PACKET_CANDIDATE — pending 8-dim audit + family review:")
        for r in paper_candidates:
            m = r["metrics"]
            print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11m_fomc_MES_MNQ_v1.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "FOMC-MES/MNQ first batch under V1 doctrine (#173 OK A — POST-V1 NONSTOP HUNTING)",
        "doctrine_reference": "docs/fql_forge/PACKET_STANDARD_V1_2026-06-11.md",
        "calendar_grade": "MACHINE_FETCHED_OFFICIAL (Fed.gov verified 2026-06-11)",
        "filter": "strict-only (hold==60min per R1 carve-out)",
        "v1_tier": {"PAPER_PACKET_CANDIDATE": len(paper_candidates), "ARCHIVED": len(archived)},
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
