"""Core Daily Algo Hunt Round 2 — operator's gap list.

Per operator approval 2026-06-04 (#54). Continue 70% Core Daily Hunt priority.
13 candidates target the explicit operator gap list using existing primitives
+ one tiny new session_close filter.

All Forge laws apply: cheap-screen → temporal split for promising → Era-3 wall
check → flag any WATCH for evidence-integrity audit before deep-screen.

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
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


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
                         "pf": pf, "net": float(pnl.sum())})
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
                     "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan")}


def _doctrine(m, ts):
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)"
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)"
    era3 = ts.get("era3_pf", 1.0)
    if np.isfinite(era3) and era3 < 1.0:
        return "ARCHITECTURAL_REJECT (Era-3 regime-wall fail)"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (passed temporal + Era-3)"
    return "WATCH (passed temporal; modest)"


def run_candidate(spec):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
    cfg = ASSETS[spec["asset"]]
    sigs = generate_crossbred_signals(
        df, entry_name=spec["entry"], exit_name=spec["exit"],
        filter_name=spec["filter"], params=spec.get("params", {}),
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=spec["asset"])
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    vc = _classify(m)
    ts = temporal_split(res["trades_df"]) if (vc == "TEMPORAL_SPLIT_REQUIRED" or
                                              vc == "WATCH_FOR_DEEP_SCREEN") else None
    v = _doctrine(m, ts)
    return m, ts, vc, v


SPECS = [
    # MCL ORB alt-exits (operator #2)
    {"label": "DAILY-ORB-EMA-AtrTrail-MCL", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "atr_trail",
     "gap": "MCL ORB continuation, alt exit (atr_trail)"},
    {"label": "DAILY-ORB-EMA-Chandelier-MCL", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "chandelier",
     "gap": "MCL ORB continuation, alt exit (chandelier)"},
    {"label": "DAILY-ORB-EMA-TimeStop-MCL", "asset": "MCL", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "time_stop",
     "gap": "MCL ORB continuation, alt exit (time_stop)"},

    # MGC vol-overlay + alt filter (operators #1 / #5)
    {"label": "DAILY-VWAP-VolLow-MGC", "asset": "MGC", "entry": "vwap_continuation",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "gap": "MGC VWAP + low-vol overlay"},
    {"label": "DAILY-PB-VolLow-MGC", "asset": "MGC", "entry": "pb_pullback",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "gap": "MGC low-vol trend rider (operator #5)"},
    {"label": "DAILY-PB-VolHigh-MGC", "asset": "MGC", "entry": "pb_pullback",
     "filter": "ema_slope_vol_high", "exit": "profit_ladder",
     "params": {"vr_threshold": 70},
     "gap": "MGC high-vol trend rider counter-test"},

    # MNQ pullback continuation variants (operator #6)
    {"label": "DAILY-PB-VolLow-MNQ", "asset": "MNQ", "entry": "pb_pullback",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 40},
     "gap": "MNQ pullback + low-vol overlay (alt to existing XB-PB-Ladder-MNQ)"},
    {"label": "DAILY-PB-EMA-Chandelier-MNQ", "asset": "MNQ", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "chandelier",
     "gap": "MNQ pullback + alt exit (chandelier)"},

    # ZN morning extension MR (operator #7)
    {"label": "DAILY-BB-Morning-ZN", "asset": "ZN", "entry": "bb_reversion",
     "filter": "session_morning", "exit": "profit_ladder",
     "gap": "ZN morning-only mean reversion (operator #7)"},
    {"label": "DAILY-BB-VolLow-ZN", "asset": "ZN", "entry": "bb_reversion",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "gap": "ZN MR + low-vol overlay"},

    # MES VWAP + alt exit
    {"label": "DAILY-VWAP-Chandelier-MES", "asset": "MES", "entry": "vwap_continuation",
     "filter": "ema_slope", "exit": "chandelier",
     "gap": "MES VWAP + chandelier exit"},

    # MYM afternoon ORB (operator #10)
    {"label": "DAILY-ORB-Afternoon-MYM", "asset": "MYM", "entry": "orb_breakout",
     "filter": "session_afternoon", "exit": "profit_ladder",
     "gap": "MYM afternoon ORB"},

    # Close momentum (new session_close filter) (operator #4)
    {"label": "DAILY-ORB-Close-MYM", "asset": "MYM", "entry": "orb_breakout",
     "filter": "session_close", "exit": "profit_ladder",
     "gap": "MYM close momentum (operator #4) — new session_close filter"},
    {"label": "DAILY-ORB-Close-MGC", "asset": "MGC", "entry": "orb_breakout",
     "filter": "session_close", "exit": "profit_ladder",
     "gap": "MGC close momentum — new session_close filter"},
]


def run():
    print(f"Core Daily Hunt Round 2 — {len(SPECS)} candidates targeting operator gap list\n")
    results = []
    for spec in SPECS:
        try:
            m, ts, vc, v = run_candidate(spec)
        except Exception as e:
            print(f"  {spec['label']:42s}: ERROR {e}")
            continue
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        print(
            f"  {spec['label']:42s}: n={m['n']:5d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% "
            f"yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}"
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct", "top10_share_pct",
                "h1_pf", "h2_pf", "years_positive", "n_years",
            )},
            "temporal_split": ts,
            "cheap_verdict": vc,
            "doctrine_verdict": v,
        })

    n_watch_deep = sum(1 for r in results if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"])
    n_arch_reject = sum(1 for r in results if "ARCHITECTURAL_REJECT" in r["doctrine_verdict"])
    n_era3_fail = sum(1 for r in results if "Era-3 regime-wall fail" in r["doctrine_verdict"])
    n_watch_modest = sum(1 for r in results
                          if r["doctrine_verdict"].startswith("WATCH ")
                          and "DEEP" not in r["doctrine_verdict"])
    n_kill = sum(1 for r in results if r["doctrine_verdict"].startswith("KILL"))
    print(f"\nAggregate ({len(results)} candidates):")
    print(f"  WATCH_FOR_DEEP_SCREEN:           {n_watch_deep}")
    print(f"  WATCH (modest):                  {n_watch_modest}")
    print(f"  ARCHITECTURAL_REJECT:            {n_arch_reject}")
    print(f"    of which Era-3 regime-wall:    {n_era3_fail}")
    print(f"  KILL:                            {n_kill}")

    if n_watch_deep:
        print("\nHeadlines (WATCH_FOR_DEEP_SCREEN):")
        for r in results:
            if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"]:
                m = r["metrics"]
                ts = r["temporal_split"]
                if ts:
                    print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f} "
                          f"yrs+={ts['yrs_pos']}/{ts['n_yrs']} Era3={ts.get('era3_pf', float('nan')):.2f}")
                else:
                    print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    (out_dir / f"forge_core_daily_hunt_round2_{date_iso}.json").write_text(
        json.dumps({"date": date_iso,
                    "approval": "OK continue daily hunt (#54)",
                    "doctrine_applied": "Era-3 regime-wall + Hard Forge laws + audit-gate-mandatory",
                    "results": results,
                    "aggregate": {
                        "total": len(results),
                        "watch_for_deep_screen": n_watch_deep,
                        "watch_modest": n_watch_modest,
                        "architectural_reject": n_arch_reject,
                        "era3_regime_wall_failures": n_era3_fail,
                        "kill": n_kill,
                    }}, indent=2, default=str)
    )
    print(f"\nWrote: forge_core_daily_hunt_round2_{date_iso}.json")
    return results


if __name__ == "__main__":
    run()
