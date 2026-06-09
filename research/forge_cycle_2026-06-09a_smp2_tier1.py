"""Cycle 2026-06-09a — SMP-2 Tier 1 RUNNABLE_NOW batch.

Per operator decision #112-E. 5 candidates from Source Mining Packet 2 Tier 1.
First deployment of hurst_stable_trend filter (built 06-03, NEVER USED before).

PL-default per #91. Strict gates per #100/#102/#106.

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

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    generate_crossbred_signals, feature_cache_stats,
)
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.prop_stress_screen import prop_stress_screen  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 30: return f"KILL (n={n})"
    if median < 0 and pf >= 1.2: return "KILL (asymmetric trap: PF>1.2, median<0)"
    if median < 0: return "KILL (median neg)"
    if pf < 1.15: return "KILL (PF<1.15)"
    if max_yr >= 50: return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0: return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def temporal_split(trades):
    if trades.empty: return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)), "net": float(pnl.sum())})
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
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan")}


def _doctrine(m, ts, full_median):
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None: return v, None
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5: return "ARCHITECTURAL_REJECT (<50% yrs+)", None
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)", None
    era3 = ts.get("era3_pf", 1.0)
    if np.isfinite(era3) and era3 < 1.0:
        return "ARCHITECTURAL_REJECT (Era-3 regime-wall fail)", None
    era3_med = ts.get("era3_median", full_median)
    delta = None
    if full_median > 0:
        if era3_med > full_median * 2: delta = "RECENT_IMPROVEMENT_SIGNAL"
        elif era3_med < full_median * 0.5 or era3_med < 0: delta = "CURRENT_REGIME_WARNING"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (temporal+Era3)", delta
    return "WATCH (temporal)", delta


def make_runner(spec):
    _cache = {}
    def runner(commission_mult, slippage_mult):
        cfg = ASSETS[spec["asset"]]
        base_costs = get_cost_params(spec["asset"])
        if "sigs" not in _cache:
            df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
            sigs = generate_crossbred_signals(
                df, entry_name=spec["entry"], exit_name=spec["exit"],
                filter_name=spec["filter"], params=spec.get("params", {}),
            )
            _cache["df"] = df; _cache["sigs"] = sigs
        df = _cache["df"]; sigs = _cache["sigs"]
        mode = spec.get("mode", "both")
        return run_backtest(
            df, sigs, mode=mode, point_value=cfg["point_value"],
            symbol=spec["asset"],
            commission_per_side=base_costs["commission_per_side"] * commission_mult,
            slippage_ticks=int(np.ceil(base_costs["slippage_ticks"] * slippage_mult)),
            tick_size=base_costs["tick_size"],
        )
    return runner


def run_one(spec):
    runner = make_runner(spec)
    res = runner(1.0, 1.0)
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    vc = _classify(m)
    ts = temporal_split(res["trades_df"]) if vc == "TEMPORAL_SPLIT_REQUIRED" else None
    v, delta = _doctrine(m, ts, m.get("median", 0))
    stress = None
    if "WATCH" in v:
        stress = prop_stress_screen(runner, spec["label"])
    return m, ts, v, delta, stress


# SMP-2 Tier 1 — 5 RUNNABLE_NOW candidates per source_mining_packet_2 catalog
SPECS = [
    # FIRST hurst_stable_trend deployment (filter built 06-03, never used)
    {"label": "SM2-DC-MES-HurstTrend-PL", "asset": "MES", "entry": "donchian_breakout",
     "filter": "hurst_stable_trend", "exit": "profit_ladder", "mode": "both"},
    {"label": "SM2-DC-MNQ-HurstTrend-PL", "asset": "MNQ", "entry": "donchian_breakout",
     "filter": "hurst_stable_trend", "exit": "profit_ladder", "mode": "both"},
    {"label": "SM2-ORB-MGC-HurstTrend-PL", "asset": "MGC", "entry": "orb_breakout",
     "filter": "hurst_stable_trend", "exit": "profit_ladder", "mode": "both"},

    # vol_expansion on untested assets
    {"label": "SM2-VolExp-MYM-PL", "asset": "MYM", "entry": "vol_expansion",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "both"},
    {"label": "SM2-VolExp-MCL-PL", "asset": "MCL", "entry": "vol_expansion",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "both"},
]


def run():
    print(f"Cycle 2026-06-09a — SMP-2 Tier 1 RUNNABLE_NOW batch ({len(SPECS)} candidates)", flush=True)
    print(f"FIRST hurst_stable_trend deployment (filter built 06-03, never used).", flush=True)
    print(f"PL-default. Strict gates: median >= $2 AND PASS_STRESS AND max-yr <= 50% AND Era3 >= 0.", flush=True)
    print(f"Boundaries: report-only Lane B.\n", flush=True)
    print(f"Feature cache: {feature_cache_stats()}\n", flush=True)
    t_start = time.time()
    results = []
    for i, spec in enumerate(SPECS, 1):
        t0 = time.time()
        try:
            m, ts, v, delta, stress = run_one(spec)
        except Exception as e:
            print(f"  [{i}] {spec['label']}: ERROR {e}", flush=True)
            results.append({"spec": spec, "error": str(e)})
            continue
        elapsed = time.time() - t0
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        era3_med = ts["era3_median"] if ts else float("nan")
        stress_str = f" stress={stress['verdict'].split()[0]}" if stress else ""
        delta_str = f" [{delta}]" if delta else ""
        print(
            f"  [{i}] {spec['label']:32s}: n={m['n']:5d} PF={m['pf']:.3f} "
            f"med=${m['median']:7.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} Era3-med=${era3_med:.2f} → {v}{delta_str}{stress_str} [{elapsed:.0f}s]",
            flush=True
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd", "max_year_share_pct",
                "top3_share_pct", "h1_pf", "h2_pf", "years_positive", "n_years",
            )},
            "temporal_split": ts, "doctrine_verdict": v,
            "era3_delta": delta, "prop_stress": stress,
            "elapsed_seconds": elapsed,
        })
    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s. Feature cache: {feature_cache_stats()}", flush=True)

    upgrade_candidates = []
    observational = []
    kill = []
    for r in results:
        if "error" in r: continue
        v = r["doctrine_verdict"]; s = r["prop_stress"]
        m = r["metrics"]; ts = r["temporal_split"]
        if "KILL" in v or "ARCHITECTURAL_REJECT" in v:
            kill.append(r); continue
        era3_med = ts.get("era3_median", -1) if ts else None
        gates_passed = (
            s and s["verdict"] == "PASS_STRESS"
            and m.get("median", 0) >= 2.0
            and m.get("max_year_share_pct", 100) <= 50
            and (era3_med is None or era3_med >= 0)
            and m.get("n", 0) >= 50
            and (ts is None or ts["yrs_pos"] >= ts["n_yrs"] * 0.5)
        )
        if gates_passed: upgrade_candidates.append(r)
        else: observational.append(r)

    print(f"\nStrict-gate tier: UPGRADE_CANDIDATE={len(upgrade_candidates)} "
          f"OBSERVATIONAL={len(observational)} KILL={len(kill)}", flush=True)
    if upgrade_candidates:
        print("\nUPGRADE_CANDIDATE — all strict gates clear (requires family review):")
        for r in upgrade_candidates:
            m = r["metrics"]; ts = r["temporal_split"]
            era3_med_str = f"${ts['era3_median']:.2f}" if ts else 'n/a'
            print(f"  {r['spec']['label']}: PF={m['pf']:.3f} med=${m['median']:.2f} "
                  f"max-yr={m['max_year_share_pct']:.1f}% Era3-med={era3_med_str}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-09a.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "SMP-2 Tier 1 RUNNABLE_NOW batch (#112-E part A)",
        "boundaries": "report-only Lane B",
        "notable": "FIRST deployment of hurst_stable_trend filter (built 06-03)",
        "tier_classification": {
            "UPGRADE_CANDIDATE": len(upgrade_candidates),
            "OBSERVATIONAL": len(observational),
            "KILL": len(kill),
        },
        "results": results,
        "feature_cache_stats_final": feature_cache_stats(),
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
