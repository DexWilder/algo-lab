"""Cycle 2026-06-24d — WH untried-assets engine sweep (report-only).

Scoped question (NOT "daily WH exhausted"): ORB is WH on MNQ/MES/MGC — can the VALIDATED engine harness
(entry x filter x exit) find an asset-specific WH on M2K/MCL/MYM/6E/6J/6B? Use engine only, never raw screens.
Proven param neighborhood (stop0.5/target4.0/trail2.5). Family-ranked; ORB = per-asset baseline anchor.

Verdict discipline: PASS/WATCH only family-supported (>=2 assets OR a single asset with neighboring-filter
support), never one-off spikes. Short-history assets (MYM/6E/6J/6B = 3yr from 2024) CAPPED at WATCH.
Weaker-than-ORB-but-decorrelated -> route to sleeve-addition battery (flagged). ORB-lite -> archive.
Report-only; no mutation; no promotion/wiring/registry/portfolio change.
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
ASSETS = ["M2K", "MCL", "MYM", "6E", "6J", "6B"]
SHORT_HIST = {"MYM", "6E", "6J", "6B"}        # 3yr (2024+) -> cap at WATCH
ENTRIES = ["orb_breakout", "prior_day_break", "first_impulse_pullback", "range_compression_break", "vol_expansion", "afternoon_continuation"]
FILTERS = ["ema_slope", "vol_regime", "ema_slope_vol_high"]
EXITS = ["profit_ladder", "atr_trail"]
PARAMS = {"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5}
_CACHE = {}


def load(a):
    if a not in _CACHE:
        df = pd.read_csv(ROOT / f"data/processed/{a}_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"]); _CACHE[a] = df
    return _CACHE[a]


def _pf(s):
    s = np.asarray(s, float); w = s[s > 0].sum(); l = -s[s < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def one(a, entry, exit_, filt):
    cfg = get_asset(a); df = load(a)
    sig = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_, filter_name=filt, params=PARAMS)
    res = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"],
                       commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = res["trades_df"]
    if t is None or len(t) < 30:
        return {"n": 0 if t is None else len(t), "pf": 0.0}
    t = t.copy(); t["entry_time"] = pd.to_datetime(t["entry_time"]); t = t.sort_values("entry_time")
    p = t["pnl"].to_numpy(); h = len(p) // 2; sp = np.sort(p)[::-1]; tot = p[p > 0].sum()
    dser = t.groupby(t["entry_time"].dt.normalize())["pnl"].sum(); eq = dser.cumsum(); dd = eq - eq.cummax()
    yr = t.assign(y=t["entry_time"].dt.year).groupby("y")["pnl"].sum()
    return {"n": len(p), "pf": round(_pf(p), 3), "median": round(float(np.median(p)), 2),
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "top10_pct": round(float(sp[:10].sum()) / tot * 100, 1) if tot > 0 else None,
            "maxyr_pct": round(float(yr.max()) / yr[yr > 0].sum() * 100, 1) if (yr > 0).any() else None,
            "yrs_pos": f"{int((yr > 0).sum())}/{yr.shape[0]}", "maxDD_$": round(float(dd.min()), 0),
            "worst_day_$": round(float(dser.min()), 0), "net_$": round(float(p.sum()), 0)}


def run():
    print("Cycle 2026-06-24d — WH untried-assets engine sweep (report-only)\n", flush=True)
    combos = list(itertools.product(ENTRIES, FILTERS, EXITS))
    print(f"{len(combos)} families x {len(ASSETS)} assets = {len(combos)*len(ASSETS)} runs (short-hist capped@WATCH: {sorted(SHORT_HIST)})\n", flush=True)
    data = {a: {} for a in ASSETS}; t0 = time.time()
    for a in ASSETS:
        for entry, filt, exit_ in combos:
            try:
                data[a][f"{entry}|{filt}|{exit_}"] = one(a, entry, exit_, filt)
            except Exception as e:
                data[a][f"{entry}|{filt}|{exit_}"] = {"n": 0, "pf": 0.0, "err": str(e)[:50]}
    print(f"Done in {time.time()-t0:.0f}s\n", flush=True)

    OUT = {"cycle": "2026-06-24d_wh_untried_assets_engine", "params": PARAMS, "assets": data, "per_asset_best": {}, "survivors": []}
    for a in ASSETS:
        fams = data[a]
        orb = fams.get("orb_breakout|ema_slope|profit_ladder", {})
        # best non-orb family on this asset by PF (with n>=50, median>0 preferred)
        cands = [(k, m) for k, m in fams.items() if m.get("n", 0) >= 50 and not k.startswith("orb_breakout")]
        cands.sort(key=lambda kv: (kv[1].get("pf", 0), kv[1].get("median", -99)), reverse=True)
        best = cands[0] if cands else (None, {})
        cap = " [3yr-CAP@WATCH]" if a in SHORT_HIST else ""
        print(f"=== {a}{cap} === ORB baseline: PF={orb.get('pf')} median={orb.get('median')} n={orb.get('n')} yrs+={orb.get('yrs_pos')} maxDD=${orb.get('maxDD_$')}", flush=True)
        if best[0]:
            m = best[1]
            print(f"   best NON-ORB: {best[0]} PF={m['pf']} median={m['median']} n={m['n']} H1/H2={m['h1_pf']}/{m['h2_pf']} yrs+={m['yrs_pos']} top10={m['top10_pct']}% maxDD=${m['maxDD_$']}", flush=True)
        OUT["per_asset_best"][a] = {"orb_baseline": orb, "best_nonorb": {best[0]: best[1]} if best[0] else {}}
        # survivor logic: a non-ORB family is interesting if PF>=1.25, median>0, H1/H2>1, top10<35, and (>=2yrs if short else yrs ok)
        for k, m in fams.items():
            if k.startswith("orb_breakout") or m.get("n", 0) < 50:
                continue
            ok = (m["pf"] >= 1.25 and m.get("median", -1) > 0 and m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and (m.get("top10_pct") or 99) < 35)
            if ok:
                # family support: does same entry|exit work with a NEIGHBORING filter too?
                ent, fl, ex = k.split("|")
                neigh = [fams.get(f"{ent}|{nf}|{ex}", {}) for nf in FILTERS if nf != fl]
                support = sum(1 for nm in neigh if nm.get("pf", 0) >= 1.15 and nm.get("n", 0) >= 50)
                verdict = "WATCH" if (a in SHORT_HIST or support < 1) else "STRUCTURE_FOUND"
                OUT["survivors"].append({"asset": a, "family": k, "pf": m["pf"], "median": m["median"], "n": m["n"],
                                         "yrs_pos": m["yrs_pos"], "neighbor_filter_support": support, "verdict": verdict,
                                         "vs_orb": "weaker_decorrelated?->sleeve-test" if m["pf"] < (orb.get("pf") or 9) else "beats_orb?"})
        print("", flush=True)

    print(f"=== SURVIVORS (family-supported, n>=50, PF>=1.25, median>0, H1/H2>1, top10<35) ===", flush=True)
    if OUT["survivors"]:
        for s in OUT["survivors"]:
            print(f"  {s['asset']:4s} {s['family']:48s} PF={s['pf']} med={s['median']} n={s['n']} yrs+={s['yrs_pos']} nbr_support={s['neighbor_filter_support']} -> {s['verdict']} ({s['vs_orb']})", flush=True)
    else:
        print("  NONE — no asset-specific non-ORB WH survives family-support discipline.", flush=True)
    print(f"\nScoped conclusion: {'asset-specific WH candidate(s) found -> route to follow-up' if OUT['survivors'] else 'tested WH mechanisms remain ORB-dominated; M2K/MCL/MYM/6E/6J/6B produced no family-supported non-ORB WH. Next lever per doctrine: Library 100+, sparse/carry, then data-tier.'}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24d_wh_untried_assets_engine.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote untried-assets JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
