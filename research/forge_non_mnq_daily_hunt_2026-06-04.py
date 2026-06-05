"""Non-MNQ Core Daily Algo Hunt.

Per operator approvals 2026-06-04 (#58 pivot off MNQ, #60 continue daily,
#59 no chandelier/atr-trail defaults). MNQ workhorse cluster saturated;
this cycle hunts NEW edge in MGC / MCL / MES / MYM / ZN / 6J / 6E.

12 candidates using existing primitives + new prior_day_break/fade entries.

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
    # === MGC daily ===
    {"label": "NONMNQ-VWAP-VolLow-MGC", "asset": "MGC", "entry": "vwap_continuation",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "gap": "MGC VWAP reclaim/rejection + low-vol overlay (operator #1)"},
    {"label": "NONMNQ-PB-EMA-MGC-baseline", "asset": "MGC", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MGC pullback continuation (operator #1, NOT in CANDIDATES as MGC)"},
    {"label": "NONMNQ-PriorDay-Break-MGC", "asset": "MGC", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MGC prior-day high/low breakout (new primitive)"},
    {"label": "NONMNQ-PriorDay-Fade-MGC", "asset": "MGC", "entry": "prior_day_fade",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MGC prior-day high/low fade (new primitive)"},

    # === MCL daily — NO chandelier/atr_trail per #59 ===
    {"label": "NONMNQ-PB-EMA-MCL-baseline", "asset": "MCL", "entry": "pb_pullback",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MCL pullback continuation (different from killed CL settlement fade)"},
    {"label": "NONMNQ-PB-VolLow-MCL", "asset": "MCL", "entry": "pb_pullback",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "gap": "MCL low-vol trend pullback (operator #2 + low-vol)"},
    {"label": "NONMNQ-PriorDay-Break-MCL", "asset": "MCL", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MCL prior-day breakout"},

    # === MES alternatives (not MNQ-class) ===
    {"label": "NONMNQ-PriorDay-Break-MES", "asset": "MES", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MES prior-day high/low breakout (operator #3)"},
    {"label": "NONMNQ-PriorDay-Fade-MES", "asset": "MES", "entry": "prior_day_fade",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MES prior-day fade (operator #3)"},

    # === MYM (Dow) alternatives ===
    {"label": "NONMNQ-PriorDay-Break-MYM", "asset": "MYM", "entry": "prior_day_break",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "MYM prior-day breakout"},
    {"label": "NONMNQ-PB-VolLow-MYM", "asset": "MYM", "entry": "pb_pullback",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "gap": "MYM pullback + low-vol (non-MNQ Dow exposure)"},

    # === ZN — rates MR / range fade (operator #4) ===
    {"label": "NONMNQ-PriorDay-Fade-ZN", "asset": "ZN", "entry": "prior_day_fade",
     "filter": "ema_slope", "exit": "profit_ladder",
     "gap": "ZN range fade at prior-day extremes (operator #4)"},
]


def run():
    print(f"Non-MNQ Core Daily Hunt — {len(SPECS)} candidates\n")
    results = []
    for spec in SPECS:
        try:
            m, ts, vc, v = run_candidate(spec)
        except Exception as e:
            print(f"  {spec['label']:40s}: ERROR {e}")
            continue
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        era3 = ts["era3_pf"] if ts else float("nan")
        print(
            f"  {spec['label']:40s}: n={m['n']:5d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% "
            f"yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {v}"
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
        })

    n_watch_deep = sum(1 for r in results if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"])
    n_arch_reject = sum(1 for r in results if "ARCHITECTURAL_REJECT" in r["doctrine_verdict"])
    n_kill = sum(1 for r in results if r["doctrine_verdict"].startswith("KILL"))
    n_watch_modest = sum(1 for r in results
                          if r["doctrine_verdict"].startswith("WATCH ")
                          and "DEEP" not in r["doctrine_verdict"])
    print(f"\nAggregate ({len(results)} candidates):")
    print(f"  WATCH_FOR_DEEP_SCREEN: {n_watch_deep}")
    print(f"  WATCH (modest):        {n_watch_modest}")
    print(f"  ARCHITECTURAL_REJECT:  {n_arch_reject}")
    print(f"  KILL:                  {n_kill}")
    if n_watch_deep:
        print("\nHeadlines (WATCH_FOR_DEEP_SCREEN):")
        for r in results:
            if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"]:
                m = r["metrics"]; ts = r["temporal_split"]
                era3 = ts.get("era3_pf", float("nan")) if ts else float("nan")
                print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f} max-yr={m.get('max_year_share_pct'):.1f}% Era3={era3:.2f}")

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_non_mnq_daily_hunt_{date.today().isoformat()}.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "approval": "OK pivot off MNQ + continue non-MNQ daily hunt (#58, #60)",
        "doctrine_applied": "Era-3 wall + no chandelier/atr-trail + audit gate mandatory",
        "results": results,
        "aggregate": {"total": len(results),
                      "watch_for_deep_screen": n_watch_deep,
                      "watch_modest": n_watch_modest,
                      "architectural_reject": n_arch_reject,
                      "kill": n_kill}
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
