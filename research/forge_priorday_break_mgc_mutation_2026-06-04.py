"""PriorDay-Break-MGC bounded mutation cycle.

Per operator approval #62. Baseline: n=403, PF 1.278, median +$6.76,
max-yr 32.6%, 7/8 yrs+. Goal: push PF above 1.30 while preserving:
  - positive median
  - max-year below 40%
  - broad year survival (≥ 75%)
  - Era 3 survival (PF > 1.0)

If mutation improves PF but creates concentration or weakens current-regime
survival, do NOT upgrade.

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


def _run(filter_name, exit_name, params, label):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    sigs = generate_crossbred_signals(
        df, entry_name="prior_day_break", exit_name=exit_name,
        filter_name=filter_name, params=params or {},
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol="MGC")
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    ts = temporal_split(res["trades_df"])
    return m, ts


def _classify(m, ts, baseline):
    """Apply operator's preservation rules + improvement test."""
    if m["n"] < 30:
        return f"KILL (n={m['n']})"
    if m["median"] <= 0:
        return "KILL (median ≤ 0)"
    if m["pf"] < 1.15:
        return f"KILL (PF<1.15)"
    if m.get("max_year_share_pct", 100) >= 40:
        return f"REJECT (max-yr {m.get('max_year_share_pct'):.1f}% > 40 gate)"
    if ts and ts["yrs_pos"] < ts["n_yrs"] * 0.75:
        return f"REJECT (yrs+ {ts['yrs_pos']}/{ts['n_yrs']} < 75%)"
    if ts and ts.get("era3_pf", 1.0) < 1.0:
        return "REJECT (Era 3 PF < 1.0)"
    # Improvement: PF > baseline (1.278) AND median > baseline ($6.76)
    if m["pf"] > 1.30 and m["median"] > baseline["median"]:
        return "WATCH_FOR_DEEP_SCREEN (upgrades baseline; PF > 1.30)"
    if m["pf"] > baseline["pf"] and m["median"] > 0:
        return f"WATCH (improves PF but not above 1.30 gate)"
    return f"WATCH (preserved but no improvement)"


# Baseline (already known)
BASELINE = {"pf": 1.278, "median": 6.76, "max_year_share_pct": 32.6, "yrs_pos": 7, "n_yrs": 8}

MUTATIONS = [
    # Vol overlays
    {"label": "PriorDay-Break-MGC-VolLow30", "filter": "ema_slope_vol_low",
     "exit": "profit_ladder", "params": {"vr_threshold": 30}},
    {"label": "PriorDay-Break-MGC-VolLow40", "filter": "ema_slope_vol_low",
     "exit": "profit_ladder", "params": {"vr_threshold": 40}},
    {"label": "PriorDay-Break-MGC-VolHigh70", "filter": "ema_slope_vol_high",
     "exit": "profit_ladder", "params": {"vr_threshold": 70}},
    # Stop/target tweaks
    {"label": "PriorDay-Break-MGC-Stop1.5T4", "filter": "ema_slope",
     "exit": "profit_ladder", "params": {"stop_mult": 1.5, "target_mult": 4.0}},
    {"label": "PriorDay-Break-MGC-Stop2.5T4", "filter": "ema_slope",
     "exit": "profit_ladder", "params": {"stop_mult": 2.5, "target_mult": 4.0}},
    {"label": "PriorDay-Break-MGC-Stop2T5", "filter": "ema_slope",
     "exit": "profit_ladder", "params": {"stop_mult": 2.0, "target_mult": 5.0}},
    # Session restrictions
    {"label": "PriorDay-Break-MGC-MorningOnly", "filter": "session_morning",
     "exit": "profit_ladder", "params": {}},
    {"label": "PriorDay-Break-MGC-AfternoonOnly", "filter": "session_afternoon",
     "exit": "profit_ladder", "params": {}},
]


def run():
    print("PriorDay-Break-MGC mutation cycle (bounded; operator #62)\n")
    print(f"Baseline (no mutation): PF {BASELINE['pf']} median ${BASELINE['median']} max-yr {BASELINE['max_year_share_pct']}% yrs+ {BASELINE['yrs_pos']}/{BASELINE['n_yrs']}\n")

    results = []
    for spec in MUTATIONS:
        try:
            m, ts = _run(spec["filter"], spec["exit"], spec["params"], spec["label"])
        except Exception as e:
            print(f"  {spec['label']:42s}: ERROR {e}")
            continue
        verdict = _classify(m, ts, BASELINE)
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else "?"
        yrs_pos = ts["yrs_pos"] if ts else "?"
        era3 = ts["era3_pf"] if ts else float("nan")
        print(
            f"  {spec['label']:42s}: n={m['n']:4d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% "
            f"yrs+={yrs_pos}/{n_yrs} Era3={era3:.2f} → {verdict}"
        )
        results.append({
            "label": spec["label"],
            "filter": spec["filter"], "exit": spec["exit"], "params": spec["params"],
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_year_share_pct",
                "top3_share_pct", "h1_pf", "h2_pf",
            )},
            "temporal": ts, "verdict": verdict,
        })

    n_watch_deep = sum(1 for r in results if "WATCH_FOR_DEEP_SCREEN" in r["verdict"])
    n_watch = sum(1 for r in results if r["verdict"].startswith("WATCH"))
    n_kill = sum(1 for r in results if r["verdict"].startswith("KILL") or r["verdict"].startswith("REJECT"))
    print(f"\nAggregate ({len(results)} mutations):")
    print(f"  WATCH_FOR_DEEP_SCREEN: {n_watch_deep}")
    print(f"  WATCH:                 {n_watch}")
    print(f"  KILL/REJECT:           {n_kill}")
    if n_watch_deep:
        print("\nHeadlines (upgrade baseline + WATCH_FOR_DEEP_SCREEN):")
        for r in results:
            if "WATCH_FOR_DEEP_SCREEN" in r["verdict"]:
                m = r["metrics"]
                print(f"  {r['label']}: PF={m['pf']:.3f} median=${m['median']:.2f}")

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_priorday_break_mgc_mutation_2026-06-04.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "approval": "OK mutate PriorDay-Break-MGC (#62, bounded)",
        "baseline": BASELINE,
        "results": results,
        "aggregate": {
            "total": len(results),
            "watch_for_deep_screen": n_watch_deep,
            "watch": n_watch, "kill_reject": n_kill,
        }
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
