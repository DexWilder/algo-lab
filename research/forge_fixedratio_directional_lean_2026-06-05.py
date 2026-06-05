"""Lean fixed-ratio + directional hunt — minimal scope to avoid Hurst recompute pain.

Per operator approvals #69 B+C, #70 Hurst deprioritized. 8 candidates chosen
for highest expected information. NO prop-stress in this script (can be run
separately on any WATCH). Direct stdout for visibility.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 30:
        return f"KILL (n={n})"
    if median < 0:
        return "KILL (median neg)"
    if pf < 1.15:
        return "KILL (PF<1.15)"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def temporal_split(trades):
    if trades.empty:
        return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": pf, "median": float(np.median(pnl)),
                         "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)),
                     "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan")}


def _doctrine(m, ts, full_median):
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v, None
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)", None
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)", None
    era3 = ts.get("era3_pf", 1.0)
    if np.isfinite(era3) and era3 < 1.0:
        return "ARCHITECTURAL_REJECT (Era-3 regime-wall fail)", None
    era3_med = ts.get("era3_median", full_median)
    delta = None
    if full_median > 0:
        if era3_med > full_median * 2:
            delta = "RECENT_IMPROVEMENT_SIGNAL"
        elif era3_med < full_median * 0.5 or era3_med < 0:
            delta = "CURRENT_REGIME_WARNING"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (temporal+Era3)", delta
    return "WATCH (temporal)", delta


def run_one(spec):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
    cfg = ASSETS[spec["asset"]]
    sigs = generate_crossbred_signals(
        df, entry_name=spec["entry"], exit_name=spec["exit"],
        filter_name=spec["filter"], params=spec.get("params", {}),
    )
    res = run_backtest(df, sigs, mode=spec.get("mode", "both"),
                       point_value=cfg["point_value"], symbol=spec["asset"])
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    ts = temporal_split(res["trades_df"]) if m.get("max_year_share_pct", 0) >= 50 else None
    v, delta = _doctrine(m, ts, m.get("median", 0))
    return m, ts, v, delta


SPECS = [
    # Fixed-ratio comparisons on existing strong baselines
    {"label": "FR-MGC-ORB-EMA-R2", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both"},
    {"label": "FR-MGC-ORB-EMA-R3", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 3.0},
     "mode": "both"},
    {"label": "FR-MCL-ORB-EMA-R2", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both"},
    {"label": "FR-MYM-ORB-EMA-R2", "asset": "MYM", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both"},

    # Direction diagnostics on strongest baselines
    {"label": "DIR-MGC-ORB-Long-PL", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DIR-MGC-ORB-Short-PL", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short"},
    {"label": "DIR-MCL-ORB-Long-PL", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
    {"label": "DIR-MGC-PriorDayBreak-Long", "asset": "MGC", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long"},
]


def run():
    print(f"Lean fixed-ratio + directional hunt — {len(SPECS)} candidates", flush=True)
    results = []
    for i, spec in enumerate(SPECS, 1):
        try:
            m, ts, v, delta = run_one(spec)
        except Exception as e:
            print(f"  [{i}] {spec['label']}: ERROR {e}", flush=True)
            continue
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        delta_str = f" [{delta}]" if delta else ""
        print(
            f"  [{i}] {spec['label']:32s} ({spec['mode']:5s}): n={m['n']:5d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}{delta_str}",
            flush=True
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct",
                "h1_pf", "h2_pf", "years_positive", "n_years",
            )},
            "temporal_split": ts, "doctrine_verdict": v, "era3_delta": delta,
        })

    watch_deep = [r for r in results if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"]]
    watch = [r for r in results if r["doctrine_verdict"].startswith("WATCH ")
             and "DEEP" not in r["doctrine_verdict"]]
    arch_reject = [r for r in results if "ARCHITECTURAL_REJECT" in r["doctrine_verdict"]]
    kill = [r for r in results if r["doctrine_verdict"].startswith("KILL")]
    print(f"\nAggregate ({len(results)}):", flush=True)
    print(f"  WATCH_FOR_DEEP_SCREEN: {len(watch_deep)}", flush=True)
    print(f"  WATCH (modest):        {len(watch)}", flush=True)
    print(f"  ARCH_REJECT:           {len(arch_reject)}", flush=True)
    print(f"  KILL:                  {len(kill)}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_fixedratio_directional_lean_2026-06-05.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "approval": "OK direction B+C (#69), Hurst deprioritized (#70)",
        "results": results,
        "aggregate": {
            "watch_for_deep_screen": len(watch_deep),
            "watch_modest": len(watch),
            "architectural_reject": len(arch_reject),
            "kill": len(kill),
        }
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
