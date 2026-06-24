"""Cycle 2026-06-23p — WH Batch-4: engine-based crossbred sweep (report-only).

Correctly-instrumented WH hunt: route momentum/ORB-adjacent ENTRIES through the proven crossbreeding engine
(entry x filter x exit), NOT raw entry->horizon screens. "Book research didn't fail; the raw-entry harness did."

Grid: 8 entries x 3 filters x 2 exits x 3 assets at the PROVEN param neighborhood (stop0.5/target4.0/trail2.5)
— no single-config fishing. Rank by FAMILY (entry x filter x exit, aggregated across assets):
  cross-asset consistency (#assets PF>1.2) > positive median > low top-10 concentration > per-year stability >
  PF (tiebreak). Baseline anchor = orb_breakout/ema_slope/profit_ladder (the deployed MNQ WH ~PF 1.6).
Anti-overfit: family must work across >=2 assets AND not depend on one magic filter. Report-only; no mutation.
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals

REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"
ASSETS = ["MNQ", "MES", "MGC"]
ENTRIES = ["orb_breakout", "prior_day_break", "vol_expansion", "range_compression_break",
           "afternoon_continuation", "first_impulse_pullback", "vwap_continuation", "abnormal_range_followup"]
FILTERS = ["none", "ema_slope", "vol_regime"]
EXITS = ["profit_ladder", "atr_trail"]
PARAMS = {"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5}
_CACHE = {}


def load(asset):
    if asset not in _CACHE:
        df = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"])
        _CACHE[asset] = df
    return _CACHE[asset]


def _pf(s):
    w = s[s > 0].sum(); l = -s[s < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def one(asset, entry, exit_, filt):
    cfg = get_asset(asset); df = load(asset)
    sig = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_, filter_name=filt, params=PARAMS)
    res = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"],
                       commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = res["trades_df"]
    if t is None or len(t) < 30:
        return {"n": 0 if t is None else len(t), "pf": 0.0}
    t = t.copy(); t["entry_time"] = pd.to_datetime(t["entry_time"]); t = t.sort_values("entry_time")
    p = t["pnl"].to_numpy(); h = len(p) // 2; tot = p[p > 0].sum()
    sp = np.sort(p)[::-1]
    yr = t.assign(y=t["entry_time"].dt.year).groupby("y")["pnl"].sum()
    return {"n": len(p), "pf": round(_pf(p), 3), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "top10_pct": round(float(sp[:10].sum()) / tot * 100, 1) if tot > 0 else None,
            "maxyr_pct": round(float(yr.max()) / yr[yr > 0].sum() * 100, 1) if (yr > 0).any() else None,
            "yrs_pos": f"{int((yr > 0).sum())}/{yr.shape[0]}", "pnl": round(float(p.sum()), 0)}


def run():
    print("Cycle 2026-06-23p — WH Batch-4 engine crossbred sweep (report-only)\n", flush=True)
    combos = list(itertools.product(ENTRIES, FILTERS, EXITS))
    print(f"{len(combos)} families x {len(ASSETS)} assets = {len(combos)*len(ASSETS)} runs\n", flush=True)
    fam = {}; t0 = time.time(); rn = 0
    for entry, filt, exit_ in combos:
        key = f"{entry}|{filt}|{exit_}"; per = {}
        for a in ASSETS:
            rn += 1
            try:
                per[a] = one(a, entry, exit_, filt)
            except Exception as e:
                per[a] = {"n": 0, "pf": 0.0, "err": str(e)[:60]}
        pfs = [per[a]["pf"] for a in ASSETS if per[a].get("n", 0) >= 30]
        n_ok = sum(1 for a in ASSETS if per[a].get("n", 0) >= 30 and per[a]["pf"] >= 1.2)
        med_ok = sum(1 for a in ASSETS if per[a].get("n", 0) >= 30 and per[a].get("median", -1) > 0)
        fam[key] = {"per_asset": per, "n_assets_pf>1.2": n_ok, "n_assets_median>0": med_ok,
                    "mean_pf": round(float(np.mean(pfs)), 3) if pfs else 0.0, "n_tradeable": len(pfs)}
    dt = time.time() - t0
    # rank: cross-asset consistency, then median-positive count, then mean PF
    ranked = sorted(fam.items(), key=lambda kv: (kv[1]["n_assets_pf>1.2"], kv[1]["n_assets_median>0"], kv[1]["mean_pf"]), reverse=True)
    base = fam.get("orb_breakout|ema_slope|profit_ladder", {})
    print(f"Done in {dt:.0f}s. BASELINE orb_breakout|ema_slope|profit_ladder: "
          f"{base.get('n_assets_pf>1.2')}/3 assets PF>1.2, mean_pf={base.get('mean_pf')}, "
          f"MNQ={base.get('per_asset',{}).get('MNQ',{}).get('pf')}\n", flush=True)
    print(f"{'family (entry|filter|exit)':54s} {'A>1.2':>5s} {'med+':>4s} {'meanPF':>7s}  MNQ/MES/MGC PF", flush=True)
    survivors = []
    for k, v in ranked:
        if v["n_tradeable"] == 0:
            continue
        pfs = "/".join(str(v["per_asset"][a].get("pf", "-")) for a in ASSETS)
        flag = ""
        if v["n_assets_pf>1.2"] >= 2 and v["n_assets_median>0"] >= 2:
            flag = " <-- cross-asset survivor"
            survivors.append((k, v))
        print(f"{k:54s} {v['n_assets_pf>1.2']:>5d} {v['n_assets_median>0']:>4d} {v['mean_pf']:>7.3f}  {pfs}{flag}", flush=True)

    print(f"\nCROSS-ASSET SURVIVORS (>=2 assets PF>1.2 AND median>0): {len(survivors)}", flush=True)
    for k, v in survivors:
        nonbase = "BASELINE-FAMILY" if k.startswith("orb_breakout") else "NON-BASELINE"
        print(f"  {k}  [{nonbase}] per-asset: " + ", ".join(f"{a}:PF{v['per_asset'][a].get('pf')}/n{v['per_asset'][a].get('n')}/yr{v['per_asset'][a].get('yrs_pos')}/top10{v['per_asset'][a].get('top10_pct')}%" for a in ASSETS if v['per_asset'][a].get('n',0)>=30), flush=True)
    OUT = {"cycle": "2026-06-23p_wh_batch4_engine_sweep", "params": PARAMS, "baseline": base,
           "families": fam, "ranked_top": [k for k, _ in ranked[:15]], "survivors": [k for k, _ in survivors],
           "note": "engine crossbred sweep; proven param neighborhood; family-ranked; report-only"}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-23p_wh_batch4_engine_sweep.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote Batch-4 JSON.\n(report-only; no mutation; family-ranked, anti-overfit)", flush=True)


if __name__ == "__main__":
    run()
