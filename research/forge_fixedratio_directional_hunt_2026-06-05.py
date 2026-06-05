"""Fixed-ratio + Directional Core Daily Hunt (post-plateau pivot).

Per operator approvals 2026-06-05 (#69 B+C). Two simple new search dimensions:
  - Fixed-ratio exits (1:1, 1:2, 1:3) replacing profit_ladder default
  - Long-only / Short-only directional diagnostics

13 candidates across MGC/MCL/MES/MYM/ZN. Hurst filters DEPRIORITIZED (#70);
no Hurst-gated candidates. No MNQ workhorse variants. No chandelier/atr-trail.
Prop-stress applied upfront on any WATCH.

Authority: T1 / Lane B / report-only.
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
from research.prop_stress_screen import prop_stress_screen  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 30:
        return f"KILL (insufficient-n, n={n})"
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
    delta_signal = None
    if full_median > 0:
        if era3_med > full_median * 2:
            delta_signal = "RECENT_IMPROVEMENT_SIGNAL"
        elif era3_med < full_median * 0.5 or era3_med < 0:
            delta_signal = "CURRENT_REGIME_WARNING"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (passed temporal + Era-3)", delta_signal
    return "WATCH (passed temporal; modest)", delta_signal


def make_runner(spec, mode_override=None):
    def runner(commission_mult, slippage_mult):
        df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
        cfg = ASSETS[spec["asset"]]
        base_costs = get_cost_params(spec["asset"])
        sigs = generate_crossbred_signals(
            df, entry_name=spec["entry"], exit_name=spec["exit"],
            filter_name=spec["filter"], params=spec.get("params", {}),
        )
        mode = mode_override or spec.get("mode", "both")
        res = run_backtest(
            df, sigs, mode=mode, point_value=cfg["point_value"],
            symbol=spec["asset"],
            commission_per_side=base_costs["commission_per_side"] * commission_mult,
            slippage_ticks=int(np.ceil(base_costs["slippage_ticks"] * slippage_mult)),
            tick_size=base_costs["tick_size"],
        )
        return res
    return runner


def run_candidate(spec):
    runner = make_runner(spec, mode_override=spec.get("mode"))
    res = runner(1.0, 1.0)
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    vc = _classify(m)
    ts = temporal_split(res["trades_df"]) if (vc == "TEMPORAL_SPLIT_REQUIRED" or
                                              vc == "WATCH_FOR_DEEP_SCREEN") else None
    v, era3_delta = _doctrine(m, ts, m.get("median", 0))
    stress = None
    if "WATCH" in v:
        stress = prop_stress_screen(runner, spec["label"])
    return m, ts, vc, v, era3_delta, stress


# Specs: fixed-ratio exits + directional splits
SPECS = [
    # Fixed-ratio exits on ORB family (MGC/MCL/MES/MYM)
    {"label": "FR-MGC-ORB-EMA-R1", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 1.0},
     "mode": "both", "gap": "MGC ORB 1:1 fixed-ratio"},
    {"label": "FR-MGC-ORB-EMA-R2", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both", "gap": "MGC ORB 1:2 fixed-ratio"},
    {"label": "FR-MGC-ORB-EMA-R3", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 3.0},
     "mode": "both", "gap": "MGC ORB 1:3 fixed-ratio"},
    {"label": "FR-MCL-ORB-EMA-R2", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both", "gap": "MCL ORB 1:2 fixed-ratio"},
    {"label": "FR-MCL-ORB-EMA-R3", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 3.0},
     "mode": "both", "gap": "MCL ORB 1:3 fixed-ratio"},
    {"label": "FR-MES-PB-EMA-R2", "asset": "MES", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both", "gap": "MES pullback 1:2 fixed-ratio"},
    {"label": "FR-MYM-ORB-EMA-R2", "asset": "MYM", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both", "gap": "MYM ORB 1:2 fixed-ratio"},
    {"label": "FR-ZN-PB-EMA-R2", "asset": "ZN", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "fixed_ratio", "params": {"ratio": 2.0},
     "mode": "both", "gap": "ZN pullback 1:2 fixed-ratio"},

    # Directional diagnostics (long-only / short-only)
    {"label": "DIR-MGC-ORB-Long", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long",
     "gap": "MGC ORB LONG ONLY"},
    {"label": "DIR-MGC-ORB-Short", "asset": "MGC", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short",
     "gap": "MGC ORB SHORT ONLY"},
    {"label": "DIR-MCL-ORB-Long", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long",
     "gap": "MCL ORB LONG ONLY"},
    {"label": "DIR-MCL-ORB-Short", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "short",
     "gap": "MCL ORB SHORT ONLY"},
    {"label": "DIR-MGC-PriorDayBreak-Long", "asset": "MGC", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder", "mode": "long",
     "gap": "MGC PriorDayBreak LONG ONLY (baseline was both)"},
]


def run():
    print(f"Fixed-Ratio + Directional Hunt — {len(SPECS)} candidates + prop-stress on WATCH\n")
    results = []
    for spec in SPECS:
        try:
            m, ts, vc, v, era3_delta, stress = run_candidate(spec)
        except Exception as e:
            print(f"  {spec['label']:38s}: ERROR {e}")
            continue
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        delta_str = f" [{era3_delta}]" if era3_delta else ""
        stress_str = f" stress={stress['verdict'].split()[0]}" if stress else ""
        print(
            f"  {spec['label']:35s} ({spec['mode']:5s}): n={m['n']:5d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% "
            f"yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}{delta_str}{stress_str}"
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct",
                "h1_pf", "h2_pf", "years_positive", "n_years",
            )},
            "temporal_split": ts,
            "doctrine_verdict": v,
            "era3_delta_signal": era3_delta,
            "prop_stress": stress,
        })

    # 3-tier classification
    paper_packet = []
    portfolio_complement = []
    observational = []
    kill = []
    for r in results:
        v = r["doctrine_verdict"]
        s = r["prop_stress"]
        if "KILL" in v or "ARCHITECTURAL_REJECT" in v:
            kill.append(r)
        elif "WATCH_FOR_DEEP_SCREEN" in v:
            if s and s["verdict"] == "PASS_STRESS":
                paper_packet.append(r)
            elif s and "KNIFE_EDGE" in s["verdict"]:
                observational.append(r)
            elif s and "FAIL_STRESS" in s["verdict"]:
                observational.append(r)
            else:
                paper_packet.append(r)
        elif "WATCH" in v:
            observational.append(r)

    print(f"\nAggregate ({len(results)} candidates):")
    print(f"  PAPER_PACKET tier (passes stress):     {len(paper_packet)}")
    print(f"  PORTFOLIO_COMPLEMENT tier:             {len(portfolio_complement)}")
    print(f"  OBSERVATIONAL tier:                    {len(observational)}")
    print(f"  KILL/REJECT:                           {len(kill)}")
    if paper_packet:
        print("\nPAPER_PACKET tier headlines:")
        for r in paper_packet:
            m = r["metrics"]
            ts = r["temporal_split"]
            stress = r["prop_stress"]
            print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}")
            if stress:
                print(f"    stress: {stress['headline_reason']}")

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_fixedratio_directional_hunt_2026-06-05.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "approval": "OK direction B+C (#69 fixed-ratio + directional) + Hurst deprioritized (#70)",
        "tier_classification": {
            "PAPER_PACKET": len(paper_packet),
            "PORTFOLIO_COMPLEMENT": len(portfolio_complement),
            "OBSERVATIONAL": len(observational),
            "KILL": len(kill),
        },
        "results": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
