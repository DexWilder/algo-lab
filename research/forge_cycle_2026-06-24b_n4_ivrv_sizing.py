"""Cycle 2026-06-24b — N4 IV-RV sizing overlay on the deployed ORB book (report-only).

NOT a new standalone WH. An ORB book-IMPROVEMENT / risk-sizing candidate. Must beat FLAT 1x on RISK-ADJUSTED
terms (Sharpe/MAR/DD/prop-fit), not gross $, AND beat simpler realized-vol-only and VIX-only sizing
(incremental value), AND we must show whether any gain comes from TIMING bad days vs just REDUCING exposure.

Book: orb_breakout|ema_slope|profit_ladder (deployed WH). Daily PnL ($) from engine. Sizing multiplier known
BEFORE each day (no-lookahead: VIX prior close, realized vol from MNQ daily returns up to prior close).
Schemes (predeclared, textbook direction; bounds [0.25,2.0], normalized to avg-exposure~1):
  flat=1.0 | inv_vol (vol-target: de-risk in high RV) | vix_reduce (de-risk in high VIX) |
  ivrv (Sinclair: size UP when IV-RV rich = calm ahead).
Exposure-neutral judging: Sharpe & MAR (exposure-invariant) + avg_exposure reported, so a rule that merely
scales down gets no free credit. Report-only; no mutation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals

REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"
PARAMS = {"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5}
DLL = {"MNQ": 1100.0, "MES": 1100.0, "MGC": 1100.0}   # assumed Tradeify-50k-style daily loss limit ($)


def orb_daily(asset):
    cfg = get_asset(asset); df = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"])
    sig = generate_crossbred_signals(df, entry_name="orb_breakout", exit_name="profit_ladder", filter_name="ema_slope", params=PARAMS)
    r = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"],
                     commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = r["trades_df"].copy(); t["day"] = pd.to_datetime(t["entry_time"]).dt.normalize()
    return t.groupby("day")["pnl"].sum()


def zlast(s, w=120):
    return ((s - s.rolling(w, min_periods=40).mean()) / s.rolling(w, min_periods=40).std())


def metrics(pnl, dll):
    p = pnl.values; eq = np.cumsum(p); dd = eq - np.maximum.accumulate(eq)
    yr = pnl.groupby(pnl.index.year).sum(); wk = pnl.resample("W").sum(); mo = pnl.resample("ME").sum()
    sd = p.std()
    return {"net_$": round(float(p.sum()), 0), "sharpe_ann": round(float(p.mean()) / sd * np.sqrt(252), 2) if sd > 0 else None,
            "MAR": round(float(p.sum()) / abs(dd.min()), 2) if dd.min() < 0 else None,
            "maxDD_$": round(float(dd.min()), 0), "worst_day_$": round(float(pnl.min()), 0),
            "worst_wk_$": round(float(wk.min()), 0), "worst_mo_$": round(float(mo.min()), 0),
            "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}", "DLL_breach_days": int((pnl < -dll).sum()),
            "pf": round(float(p[p > 0].sum() / -p[p < 0].sum()), 3) if (p < 0).any() else None}


def run():
    print("Cycle 2026-06-24b — N4 IV-RV sizing overlay on ORB book (report-only)\n", flush=True)
    vix = pd.read_csv(ROOT / "data" / "feeds" / "vix.csv", parse_dates=["date"]).set_index("date")["vix"]
    vix_z = zlast(vix); vix_z.index = vix_z.index + pd.Timedelta(days=1)        # prior close -> today (no lookahead)
    OUT = {"cycle": "2026-06-24b_n4_ivrv_sizing", "status": "report-only; ORB book-improvement overlay"}
    for asset in ("MNQ", "MES", "MGC"):
        od = orb_daily(asset)
        ret = od.index.to_series()  # placeholder
        # realized vol from the ASSET daily close returns (proxy from ORB trading days' own price not available; use 5m daily close)
        dfp = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv"); dtv = pd.to_datetime(dfp["datetime"])
        dret = dfp.assign(d=dtv.dt.normalize()).groupby("d")["close"].last().pct_change()
        rv = dret.rolling(20, min_periods=10).std() * np.sqrt(252) * 100        # annualized vol points
        rv_prior = rv.shift(1)                                                  # known before today
        ivrv = (vix.reindex(rv.index, method="ffill") - rv)                     # IV - RV
        ivrv_z = zlast(ivrv); ivrv_z = ivrv_z.shift(1)
        rv_z = zlast(rv).shift(1)
        # align to ORB trading days
        idx = od.index
        vz = vix_z.reindex(idx).ffill(); rvp = rv_prior.reindex(idx); rvz = rv_z.reindex(idx); ivz = ivrv_z.reindex(idx)
        rv_med = float(rvp.median())
        def szclip(x): return np.clip(x, 0.25, 2.0)
        schemes = {
            "flat": pd.Series(1.0, index=idx),
            "inv_vol_target": szclip(rv_med / rvp).fillna(1.0),                 # de-risk in high RV
            "vix_reduce": szclip(1 - 0.5 * vz).fillna(1.0),                     # de-risk in high VIX
            "ivrv_sinclair": szclip(1 + 0.5 * ivz).fillna(1.0),                # size UP when IV-RV rich
        }
        res = {}
        flat_pnl = od.copy()
        worst20 = flat_pnl.nsmallest(20).index
        for name, size in schemes.items():
            size = size.reindex(idx).fillna(1.0)
            sized = od * size
            m = metrics(sized, DLL[asset])
            m["avg_exposure"] = round(float(size.mean()), 3)
            m["avg_size_on_ORBworst20"] = round(float(size.reindex(worst20).mean()), 3)
            m["sharpe_per_exposure"] = round(m["sharpe_ann"], 2) if m["sharpe_ann"] is not None else None
            if name != "flat":
                m["days_reduced_vs_flat"] = int((size < 0.95).sum()); m["days_increased"] = int((size > 1.05).sum())
            res[name] = m
        OUT[asset] = res
        f = res["flat"]
        print(f"=== {asset} (ORB book, {len(od)} trading days) ===", flush=True)
        print(f"  {'scheme':16s} {'net$':>8s} {'Sharpe':>6s} {'MAR':>5s} {'maxDD$':>8s} {'worstday$':>9s} {'DLLbreach':>9s} {'avgExp':>6s} {'sizeOnWorst20':>13s} yrs+", flush=True)
        for name, m in res.items():
            print(f"  {name:16s} {m['net_$']:>8.0f} {str(m['sharpe_ann']):>6s} {str(m['MAR']):>5s} {m['maxDD_$']:>8.0f} {m['worst_day_$']:>9.0f} {m['DLL_breach_days']:>9d} {m.get('avg_exposure',1.0):>6.2f} {str(m.get('avg_size_on_ORBworst20','-')):>13s} {m['yrs_pos']}", flush=True)
        print("", flush=True)

    # verdict (MNQ primary): does ivrv beat flat on Sharpe AND beat inv_vol/vix_reduce, exposure-considered?
    mnq = OUT["MNQ"]
    iv, fl, ivv, vx = mnq["ivrv_sinclair"], mnq["flat"], mnq["inv_vol_target"], mnq["vix_reduce"]
    beats_flat = (iv["sharpe_ann"] or 0) > (fl["sharpe_ann"] or 0) and (iv["MAR"] or 0) > (fl["MAR"] or 0)
    beats_simple = (iv["sharpe_ann"] or 0) >= max(ivv["sharpe_ann"] or 0, vx["sharpe_ann"] or 0)
    # timing vs de-risk: did best risk-reducer cut size on ORB's worst days more than its overall avg?
    best_safe = min([("inv_vol_target", ivv), ("vix_reduce", vx), ("ivrv_sinclair", iv)], key=lambda kv: kv[1]["maxDD_$"])
    timing = best_safe[1]["avg_size_on_ORBworst20"] < best_safe[1]["avg_exposure"] * 0.9
    OUT["verdict"] = {"ivrv_beats_flat_riskadj": bool(beats_flat), "ivrv_beats_simpler_rules": bool(beats_simple),
        "best_DD_reducer": best_safe[0], "best_reducer_times_bad_days": bool(timing),
        "call": ("IVRV_ADDS_VALUE" if beats_flat and beats_simple else
                 ("SIMPLE_VOL_SIZING_HELPS" if (ivv["sharpe_ann"] or 0) > (fl["sharpe_ann"] or 0) or (vx["sharpe_ann"] or 0) > (fl["sharpe_ann"] or 0) else "NO_SIZING_EDGE_flat_is_fine"))}
    print(f"=== VERDICT (MNQ): {OUT['verdict']['call']} ===", flush=True)
    print(f"  ivrv beats flat (Sharpe&MAR): {beats_flat} | ivrv beats simpler rules: {beats_simple} | "
          f"best DD-reducer={best_safe[0]} times-bad-days={timing}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24b_n4_ivrv_sizing.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote N4 JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
