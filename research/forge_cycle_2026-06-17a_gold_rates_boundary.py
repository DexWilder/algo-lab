"""Cycle 2026-06-17a — boundary-test the gold/rates-state CONDITIONING lead (report-only).

The cross-asset board found MGC-ORB conditions on rates-UP and MGC-prior_day_break on
rates-DOWN. Before trusting it, stress it (like the ZN-FOMC regime gate):
  - ZN trend THRESHOLD BANDS (not just binary sign) + multiple lookbacks
  - PREDECLARED retention floor (>=40% of trades AND n>=120) so we never manufacture an
    85%-cut overfit filter
  - compare against the UNCONDITIONED baselines
  - verdict: SEPARATE_SLEEVE_VARIANT (robust + strong lift + enough trades) vs
    ALLOCATION/RISK-TIMING ONLY (directionally real but modest/retention-limited) vs NOISE.

No-lookahead via the harness (strictly-prior state). NO mutation; NON-WIRED.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params, run_backtest  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals as gcs  # noqa: E402
import research.cross_asset_harness as cah  # noqa: E402

RETAIN_FLOOR = 40.0     # predeclared
N_FLOOR = 120
PF_LIFT = 0.15


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def base_trades(asset, entry):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); cfg = ASSETS[asset]; c = get_cost_params(asset)
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    tr = run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol=asset,
                      commission_per_side=c["commission_per_side"], slippage_ticks=c["slippage_ticks"],
                      tick_size=c["tick_size"])["trades_df"]
    return tr


def zn_state(lookback):
    d = cah.daily_closes("ZN")
    d["zn_ret"] = (d["c"] - d["c"].shift(lookback)) / d["c"].shift(lookback)
    return d[["date", "zn_ret"]]


def attribute(tr, lookback):
    s = zn_state(lookback)
    m = cah.attribute_by_state(tr.assign(entry_time=tr["entry_time"]), s.rename(columns={"zn_ret": "zn_state"}), "zn_state")
    # the harness renames the value col 'zn_state'; recover numeric
    return m


def run():
    print("Cycle 2026-06-17a — gold/rates conditioning boundary-test (REPORT-ONLY)\n", flush=True)
    print(f"Predeclared floors: retain>={RETAIN_FLOOR}% AND n>={N_FLOOR}; PF lift>={PF_LIFT} to count.\n", flush=True)
    results = {}
    # expected direction per mechanism (from the board): ORB likes rates-UP, PDB likes rates-DOWN
    specs = [("MGC", "orb_breakout", "up"), ("MGC", "prior_day_break", "down")]
    for asset, entry, want in specs:
        tr = base_trades(asset, entry)
        base_pf = round(_pf(tr["pnl"]), 3); base_n = len(tr)
        print(f"=== {asset}-{entry} | baseline PF={base_pf} n={base_n} | expected favorable regime: rates-{want} ===", flush=True)
        grid = []
        for lb in (21, 42, 63, 84, 126):
            m = attribute(tr, lb).dropna(subset=["state_date"])
            zr = m["zn_state"].astype(float)
            for thr in (0.0, 0.005, 0.01, 0.02):
                up = m[zr > thr]; dn = m[zr <= -thr] if thr > 0 else m[zr <= 0]
                fav = up if want == "up" else dn
                unf = dn if want == "up" else up
                fav_pf = round(_pf(fav["pnl"]), 3) if len(fav) else None
                unf_pf = round(_pf(unf["pnl"]), 3) if len(unf) else None
                retain = round(len(fav) / base_n * 100, 1)
                lift = (fav_pf - base_pf) if fav_pf is not None else None
                counts = (fav_pf is not None and lift is not None and lift >= PF_LIFT
                          and retain >= RETAIN_FLOOR and len(fav) >= N_FLOOR)
                grid.append({"lookback": lb, "thr": thr, "fav_n": len(fav), "fav_retain_pct": retain,
                             "fav_pf": fav_pf, "unfav_pf": unf_pf, "lift_vs_base": round(lift, 3) if lift is not None else None,
                             "counts_as_usable": counts})
        # robustness: of configs that meet retention floor, how many show favorable PF > unfavorable PF + 0.2?
        elig = [g for g in grid if g["fav_retain_pct"] >= RETAIN_FLOOR and g["fav_n"] >= N_FLOOR]
        directional = [g for g in elig if g["fav_pf"] is not None and g["unfav_pf"] is not None and (g["fav_pf"] - g["unfav_pf"]) >= 0.2]
        usable = [g for g in grid if g["counts_as_usable"]]
        frac_dir = round(len(directional) / len(elig), 2) if elig else 0.0
        for g in grid:
            if g["thr"] in (0.0, 0.01):
                print(f"  lb={g['lookback']:>3} thr={g['thr']:<5} fav n={g['fav_n']:>4} ({g['fav_retain_pct']:>5}%) "
                      f"PF={g['fav_pf']} vs unfav PF={g['unfav_pf']} lift={g['lift_vs_base']} "
                      f"{'[USABLE]' if g['counts_as_usable'] else ''}", flush=True)
        # verdict
        if len(usable) >= max(3, len(grid) // 3) and frac_dir >= 0.7:
            verdict = "SEPARATE_SLEEVE_VARIANT_CANDIDATE"
        elif frac_dir >= 0.6 and elig:
            verdict = "ALLOCATION_RISK_TIMING_ONLY"
        else:
            verdict = "WEAK_OR_NOISE"
        print(f"  eligible(retention-ok) configs={len(elig)} | directional(fav>unfav+0.2)={len(directional)} ({frac_dir:.0%}) "
              f"| usable(lift+retain)={len(usable)} -> VERDICT: {verdict}\n", flush=True)
        results[f"{asset}-{entry}"] = {"baseline_pf": base_pf, "baseline_n": base_n, "expected_regime": want,
                                       "grid": grid, "eligible": len(elig), "directional": len(directional),
                                       "frac_directional": frac_dir, "usable": len(usable), "verdict": verdict}

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17a_gold_rates_boundary.json"
    out.write_text(json.dumps({"cycle": "2026-06-17a_gold_rates_boundary",
        "mode": "Lane B report-only; boundary-test gold/rates conditioning; NO-LOOKAHEAD; NON-WIRED",
        "floors": {"retain_pct": RETAIN_FLOOR, "n": N_FLOOR, "pf_lift": PF_LIFT}, "results": results,
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"Wrote: {out}", flush=True)
    print("(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
