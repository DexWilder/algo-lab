"""Vol-expansion mutation cycle on MGC (secondary; bounded).

Per operator approval 2026-06-04 (#30). One cycle only; do not let it delay
NFP-MGC validation work.

Variants (all on MGC where baseline produced the best metrics):
  1. Baseline (proven trio defaults)         — already run; PF 1.204 KILL
  2. Tighter T/S: stop_mult=1.5, target=3.0
  3. atr_trail exit
  4. chandelier exit
  5. time_stop exit
  6. ema_slope_vol_low filter (counterintuitive: enter vol expansion in low-vol context)

Authority: T1 / Lane B / report-only.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


def _run(asset, entry, filter_name, exit_name, params, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(
        df, entry_name=entry, exit_name=exit_name,
        filter_name=filter_name, params=params,
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m


def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    if n < 10:
        return f"KILL (n={n})"
    if median < 0:
        return "KILL (median negative)"
    if pf < 1.15:
        return "KILL (PF < 1.15)"
    if pf >= 1.30 and median > 0:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


MUTATIONS = [
    {"label": "VX-baseline (proven trio)", "entry": "vol_expansion",
     "filter": "ema_slope", "exit": "profit_ladder",
     "params": {"vx_high": 70}},
    {"label": "VX-tighter-TS (stop 1.5 / target 2.5)", "entry": "vol_expansion",
     "filter": "ema_slope", "exit": "profit_ladder",
     "params": {"vx_high": 70, "stop_mult": 1.5, "target_mult": 2.5}},
    {"label": "VX-atr-trail", "entry": "vol_expansion",
     "filter": "ema_slope", "exit": "atr_trail",
     "params": {"vx_high": 70}},
    {"label": "VX-chandelier", "entry": "vol_expansion",
     "filter": "ema_slope", "exit": "chandelier",
     "params": {"vx_high": 70}},
    {"label": "VX-time-stop", "entry": "vol_expansion",
     "filter": "ema_slope", "exit": "time_stop",
     "params": {"vx_high": 70}},
    {"label": "VX-vol-low-precondition", "entry": "vol_expansion",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vx_high": 70, "vr_threshold": 50}},
    {"label": "VX-vol-high-confirm", "entry": "vol_expansion",
     "filter": "ema_slope_vol_high", "exit": "profit_ladder",
     "params": {"vx_high": 70, "vr_threshold": 50}},
]


def run():
    print("Vol-expansion mutation cycle on MGC (operator #30, bounded):\n")
    results = []
    for spec in MUTATIONS:
        m = _run("MGC", spec["entry"], spec["filter"], spec["exit"],
                 spec["params"], spec["label"])
        v = _classify(m)
        max_yr = m.get("max_year_share_pct", float("nan"))
        print(
            f"  [{spec['label']:45s}] n={m['n']:4d} PF={m['pf']:.3f} "
            f"median=${m['median']:7.2f} max-yr={max_yr:.1f}% → {v}"
        )
        results.append({"spec": spec,
                        "metrics": {k: m.get(k) for k in (
                            "n", "pf", "median", "net", "max_dd",
                            "max_year_share_pct", "top3_share_pct",
                            "h1_pf", "h2_pf", "years_positive", "n_years",
                        )},
                        "verdict": v})

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    (out_dir / f"forge_vol_expansion_mutation_{date_iso}.json").write_text(
        json.dumps({"date": date_iso,
                    "operator_approval": "OK vol-expansion mutation (#30, bounded)",
                    "results": results}, indent=2, default=str))
    print(f"\nWrote: forge_vol_expansion_mutation_{date_iso}.json")
    # Aggregate
    n_watch = sum(1 for r in results if "WATCH" in r["verdict"])
    n_kill = sum(1 for r in results if "KILL" in r["verdict"])
    print(f"\nAggregate: {n_watch} WATCH, {n_kill} KILL out of {len(results)}")
    if n_watch == 0:
        print("DOCTRINE: vol_expansion primitive NOT VALIDATED per primitive-validation rule. No mutation produced a non-KILL. Consider primitive itself dead.")


if __name__ == "__main__":
    run()
