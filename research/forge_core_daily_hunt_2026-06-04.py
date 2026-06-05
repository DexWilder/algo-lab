"""Core Daily Algo Hunt — pivot to 70% main-engine daily workhorse strategies.

Per operator strategic correction 2026-06-04: NFP-MGC monthly event is Packet
#1, but the portfolio needs core daily algos for trade flow + prop-payout
velocity. Run 14 candidates covering operator's preferred families × assets.

Avoids exact duplicates with existing XB-* cluster in CANDIDATES. Cheap-screen
broadly with hard Forge laws: temporal split for promising candidates;
current-regime (Era 3) survival required.

Authority: T1 / Lane B / report-only. No registry mutation.
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
from research.fql_forge_batch_runner import _metrics, CANDIDATES, EXCLUDED_FROM_ROTATION  # noqa: E402
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
    """Apply hard Forge laws + Era-3 regime-wall rule."""
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        # Even non-TSR candidates: check Era 3 survival if temporal split available
        return v
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)"
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)"
    # Era-3 wall check: regime survival
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
    ts = None
    if vc == "TEMPORAL_SPLIT_REQUIRED" or (vc == "WATCH_FOR_DEEP_SCREEN" and m["n"] > 50):
        ts = temporal_split(res["trades_df"])
    v = _doctrine(m, ts)
    return m, ts, vc, v


# 14 specs targeting operator's gaps: non-MGC/non-NFP/non-XB-clone + diverse
# assets + diverse mechanisms + afternoon/FX/rates coverage
SPECS = [
    # VWAP family on assets NOT in existing CANDIDATES
    {"label": "DAILY-VWAP-EMA-MNQ", "asset": "MNQ", "entry": "vwap_continuation",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "VWAP on MNQ (existing CANDIDATES has VWAP only on MES/MGC/MCL/MYM)"},

    # BB reversion on assets NOT in CANDIDATES — rates + crude
    {"label": "DAILY-BB-EMA-ZN", "asset": "ZN", "entry": "bb_reversion",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "BB-reversion on rates (ZN) — never tested at this level"},
    {"label": "DAILY-BB-EMA-MCL-Crude-MR", "asset": "MCL", "entry": "bb_reversion",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "BB-reversion on crude (MCL) — already in CANDIDATES via XB-BB-MCL (PF 1.007 KILL prior); test as new exit context"},

    # BB + Hurst-MR gate (new mechanism)
    {"label": "DAILY-BB-Hurst-MR-MGC", "asset": "MGC", "entry": "bb_reversion",
     "filter": "hurst_stable_mr", "exit": "profit_ladder",
     "params": {"hurst_threshold_high": 0.50},
     "gap": "BB-reversion + Hurst-MR-gate on gold (replaces ema_slope; new filter combo)"},
    {"label": "DAILY-BB-Hurst-MR-MES", "asset": "MES", "entry": "bb_reversion",
     "filter": "hurst_stable_mr", "exit": "profit_ladder",
     "params": {"hurst_threshold_high": 0.50},
     "gap": "BB-reversion + Hurst-MR-gate on equity index"},

    # PB-pullback + Hurst-trend gate (new mechanism)
    {"label": "DAILY-PB-Hurst-Trend-ZN", "asset": "ZN", "entry": "pb_pullback",
     "filter": "hurst_stable_trend", "exit": "profit_ladder",
     "params": {"hurst_threshold_low": 0.55},
     "gap": "PB-pullback + Hurst-trend-gate on rates"},
    {"label": "DAILY-PB-Hurst-Trend-MCL", "asset": "MCL", "entry": "pb_pullback",
     "filter": "hurst_stable_trend", "exit": "profit_ladder",
     "params": {"hurst_threshold_low": 0.55},
     "gap": "PB-pullback + Hurst-trend-gate on crude"},

    # Afternoon-only ORB on MES + MGC (only MNQ tested before)
    {"label": "DAILY-ORB-Afternoon-MES", "asset": "MES", "entry": "orb_breakout",
     "filter": "session_afternoon", "exit": "profit_ladder",
     "gap": "Afternoon ORB on MES (operator gap: afternoon coverage)"},

    # FX candidates — limited data window (2024-02+) but operator-flagged
    {"label": "DAILY-PB-EMA-6J", "asset": "6J", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "FX pullback (operator gap: FX session strategies)"},
    {"label": "DAILY-PB-EMA-6E", "asset": "6E", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "FX pullback EUR"},
    {"label": "DAILY-ORB-EMA-6J", "asset": "6J", "entry": "orb_breakout",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "FX ORB JPY"},

    # Donchian on MNQ (only MCL/MGC/ZN tested)
    {"label": "DAILY-DC-EMA-MNQ", "asset": "MNQ", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "Donchian on MNQ (existing has MCL/MGC/ZN; MGC was WATCH-decaying)"},

    # Donchian + Hurst-trend gate (new combo)
    {"label": "DAILY-DC-Hurst-Trend-MGC", "asset": "MGC", "entry": "donchian_breakout",
     "filter": "hurst_stable_trend", "exit": "profit_ladder",
     "params": {"hurst_threshold_low": 0.55},
     "gap": "Donchian + Hurst-trend on gold (mutation of XB-DC-MGC WATCH-decaying)"},

    # PB + vol-low + chandelier exit (alt exit on existing entry+filter cluster)
    {"label": "DAILY-PB-VolLow-Chandelier-MCL", "asset": "MCL", "entry": "pb_pullback",
     "filter": "ema_slope_vol_low", "exit": "chandelier",
     "params": {"vr_threshold": 30},
     "gap": "PB + vol-low + chandelier on crude (alt-exit combo)"},
]


def run():
    print(f"Core Daily Algo Hunt — {len(SPECS)} candidates (operator strategic pivot 2026-06-04)\n")
    print(f"Existing CANDIDATES in rotation: {len(CANDIDATES)}; excluded: {len(EXCLUDED_FROM_ROTATION)}\n")
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

    # Aggregate
    n_watch_deep = sum(1 for r in results if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"])
    n_arch_reject = sum(1 for r in results if "ARCHITECTURAL_REJECT" in r["doctrine_verdict"])
    n_watch = sum(1 for r in results if r["doctrine_verdict"].startswith("WATCH"))
    n_kill = sum(1 for r in results if r["doctrine_verdict"].startswith("KILL"))
    n_era3_fail = sum(1 for r in results if "Era-3 regime-wall fail" in r["doctrine_verdict"])
    print(f"\nAggregate ({len(results)} candidates):")
    print(f"  WATCH_FOR_DEEP_SCREEN:           {n_watch_deep}")
    print(f"  WATCH (modest):                  {n_watch - n_watch_deep}")
    print(f"  ARCHITECTURAL_REJECT (any):      {n_arch_reject}")
    print(f"    of which Era-3 regime-wall:    {n_era3_fail}")
    print(f"  KILL:                            {n_kill}")

    if n_watch_deep:
        print("\nHeadlines (WATCH_FOR_DEEP_SCREEN):")
        for r in results:
            if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"]:
                m = r["metrics"]
                ts = r["temporal_split"]
                print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f} "
                      f"yrs+={ts['yrs_pos']}/{ts['n_yrs']} Era3={ts.get('era3_pf', float('nan')):.2f}")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    (out_dir / f"forge_core_daily_hunt_{date_iso}.json").write_text(
        json.dumps({"date": date_iso,
                    "approval": "OK Core Daily Algo Hunt — strategic pivot to 70% daily core",
                    "doctrine_applied": "Era-3 regime-wall rule + Hard Forge laws + non-XB-duplicate preference",
                    "results": results,
                    "aggregate": {
                        "total": len(results),
                        "watch_for_deep_screen": n_watch_deep,
                        "architectural_reject": n_arch_reject,
                        "era3_regime_wall_failures": n_era3_fail,
                        "kill": n_kill,
                    }}, indent=2, default=str)
    )
    print(f"\nWrote: forge_core_daily_hunt_{date_iso}.json")
    return results


if __name__ == "__main__":
    run()
