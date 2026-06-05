"""Non-equity pair screens with HL-validated spreads.

Per operator approval 2026-06-04 (#45 pivot to non-equity/commodity spreads).
HL gate proved MCL/ZN (HL 3.0mo, β 0.796) and MGC/MES (HL 8.7mo, β 0.923) are
genuinely mean-reverting. Run level_z pair screens on these + ZN/ZF (borderline
HL, rolling 80% MR<24mo) with tighter z thresholds.

Plus FX overnight scratch screens to confirm 6J/6E data viability.

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

from research.pairs_engine import pairs_backtest, pairs_metrics, _resample_close  # noqa: E402
from research.half_life_filter import (  # noqa: E402
    estimate_half_life_spread, rolling_half_life, is_stable_half_life,
    gate_pair_signal_by_half_life,
)
from research.fql_forge_batch_runner import _verdict  # noqa: E402


def _classify(m, ts):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 5:
        return f"KILL (insufficient-n, n={n})"
    if median < 0:
        return "KILL (median neg)"
    if pf < 1.15:
        return "KILL (PF<1.15)"
    if ts and ts.get("yrs_pos", 0) < ts.get("n_yrs", 1) * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def _ts(trades):
    if trades.empty:
        return {"per_year": [], "yrs_pos": 0, "n_yrs": 0}
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    rows = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        rows.append({"year": int(y), "n": int(len(g)),
                     "pf": pf, "net": float(pnl.sum())})
    return {"per_year": rows,
            "yrs_pos": sum(1 for r in rows if r["net"] > 0),
            "n_yrs": len(rows)}


def run_pair(asset_a, asset_b, freq, lookback, z_thresh, exit_z,
             label, signal_class="level_z", hedge="vol_adjusted"):
    df_a = pd.read_csv(ROOT / "data" / "processed" / f"{asset_a}_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / f"{asset_b}_5m.csv")
    a_lvl = _resample_close(df_a, freq)
    b_lvl = _resample_close(df_b, freq)
    res = pairs_backtest(
        df_a=df_a, df_b=df_b, asset_a=asset_a, asset_b=asset_b,
        freq=freq, lookback=lookback, z_threshold=z_thresh, exit_z=exit_z,
        hedge=hedge, label=label,
        signal_class=signal_class,
        series_a_override=a_lvl, series_b_override=b_lvl,
    )
    m = pairs_metrics(res, label)
    ts = _ts(res["trades_df"])
    v = _classify(m, ts)
    return m, ts, v


PAIRS = [
    # MCL/ZN (HL 3.0mo PASS)
    {"label": "PAIR-MCL-ZN-level_z-mo-z1.5", "a": "MCL", "b": "ZN",
     "freq": "M", "lookback": 12, "z": 1.5, "exit_z": 0.5},
    {"label": "PAIR-MCL-ZN-level_z-mo-z1.0", "a": "MCL", "b": "ZN",
     "freq": "M", "lookback": 12, "z": 1.0, "exit_z": 0.3},
    {"label": "PAIR-MCL-ZN-level_z-mo-z2.0", "a": "MCL", "b": "ZN",
     "freq": "M", "lookback": 12, "z": 2.0, "exit_z": 0.5},
    # MGC/MES (HL 8.7mo PASS)
    {"label": "PAIR-MGC-MES-level_z-mo-z1.5", "a": "MGC", "b": "MES",
     "freq": "M", "lookback": 12, "z": 1.5, "exit_z": 0.5},
    {"label": "PAIR-MGC-MES-level_z-mo-z1.0", "a": "MGC", "b": "MES",
     "freq": "M", "lookback": 12, "z": 1.0, "exit_z": 0.3},
    {"label": "PAIR-MGC-MES-level_z-mo-z2.0", "a": "MGC", "b": "MES",
     "freq": "M", "lookback": 12, "z": 2.0, "exit_z": 0.5},
    # ZN/ZF (borderline HL — 80% rolling MR<24mo) — try lower z
    {"label": "PAIR-ZN-ZF-level_z-mo-z1.0", "a": "ZN", "b": "ZF",
     "freq": "M", "lookback": 12, "z": 1.0, "exit_z": 0.3},
    {"label": "PAIR-ZN-ZF-level_z-mo-z0.8", "a": "ZN", "b": "ZF",
     "freq": "M", "lookback": 12, "z": 0.8, "exit_z": 0.2},
]


def run():
    print(f"Non-equity HL-gated pair screens ({len(PAIRS)} candidates):\n")
    results = []
    for spec in PAIRS:
        try:
            m, ts, v = run_pair(spec["a"], spec["b"], spec["freq"],
                                 spec["lookback"], spec["z"], spec["exit_z"],
                                 spec["label"])
        except Exception as e:
            print(f"  {spec['label']}: ERROR {e}")
            continue
        max_yr = m.get("max_year_share_pct", float("nan"))
        print(
            f"  {spec['label']:38s}: n={m['n']:3d} PF={m['pf']:.3f} "
            f"median=${m['median']:8.2f} max-yr={max_yr:.1f}% yrs+={ts['yrs_pos']}/{ts['n_yrs']} → {v}"
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_year_share_pct",
                "top3_share_pct", "h1_pf", "h2_pf",
                "years_positive", "n_years",
            )},
            "temporal": ts,
            "verdict": v,
        })

    n_watch_deep = sum(1 for r in results if "WATCH_FOR_DEEP_SCREEN" in r["verdict"])
    n_watch = sum(1 for r in results if r["verdict"].startswith("WATCH"))
    n_kill = sum(1 for r in results if r["verdict"].startswith("KILL"))
    n_reject = sum(1 for r in results if "ARCHITECTURAL_REJECT" in r["verdict"])
    n_tsr = sum(1 for r in results if "TEMPORAL_SPLIT_REQUIRED" in r["verdict"])
    print(f"\nAggregate ({len(results)} candidates):")
    print(f"  WATCH_FOR_DEEP_SCREEN: {n_watch_deep}")
    print(f"  WATCH (non-deep):      {n_watch - n_watch_deep}")
    print(f"  TEMPORAL_SPLIT_REQ:    {n_tsr}")
    print(f"  ARCHITECTURAL_REJECT:  {n_reject}")
    print(f"  KILL:                  {n_kill}")

    if n_watch_deep or n_tsr:
        print("\nHeadlines:")
        for r in results:
            if "WATCH_FOR_DEEP_SCREEN" in r["verdict"] or "TEMPORAL_SPLIT_REQUIRED" in r["verdict"]:
                m = r["metrics"]
                print(f"  {r['spec']['label']}: PF={m['pf']:.3f} median=${m['median']:.2f} yrs+={r['temporal']['yrs_pos']}/{r['temporal']['n_yrs']} → {r['verdict']}")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    (out_dir / f"forge_nonequity_pair_screens_{date_iso}.json").write_text(
        json.dumps({"date": date_iso,
                    "approval": "OK pivot to non-equity events + commodity spreads (#45)",
                    "hl_diagnostic_passes": [
                        {"pair": "MCL/ZN", "beta": 0.796, "hl_months": 3.04, "verdict": "PASS"},
                        {"pair": "MGC/MES", "beta": 0.923, "hl_months": 8.69, "verdict": "PASS"},
                        {"pair": "ZN/ZF", "beta": 0.977, "hl_months": 29.8, "rolling_mr_pct_under_24mo": 80, "verdict": "BORDERLINE"},
                    ],
                    "hl_diagnostic_fails": [
                        {"pair": "ZN/ZB", "beta": 0.985, "hl_months": 44.6, "verdict": "FAIL"},
                        {"pair": "ZF/ZB", "beta": 0.984, "hl_months": 42.3, "verdict": "FAIL"},
                        {"pair": "MGC/ZN", "beta": 1.017, "hl_months": "NaN", "verdict": "FAIL (trending)"},
                    ],
                    "results": results}, indent=2, default=str))
    print(f"\nWrote: forge_nonequity_pair_screens_{date_iso}.json")
    return results


if __name__ == "__main__":
    run()
