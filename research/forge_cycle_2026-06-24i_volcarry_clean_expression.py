"""Cycle 2026-06-24i — vol-carry CLEANER expression (ONE disciplined attempt; report-only).

Premium VALIDATED (decorrelated -0.16, offsets ORB worst days); raw SVXY-contango expression ARCHIVED (marginal,
tail-heavy). This is the SINGLE better-expression shot the premium earned. Cleaner vehicle + graded exposure +
predeclared crash guards. Judged ONLY on the combined ORB book; require MATERIAL improvement, not +0.06 dust.
If still marginal -> STOP vol-carry branch, retain premium as validated-but-small, pivot to next premium.

Vehicle: SHORT VXX (2018+, no SVXY -1x->-0.5x leverage-reset artifact). Exposure GRADED by term-structure slope
magnitude (not binary). Crash guards (predeclared, ALL must clear, prior-close = no lookahead):
  contango (slope>0) AND VIX<30 AND VIX9D<VIX (no front stress) AND 5d VIX change<+30% (no recent shock).
Report-only; no mutation.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.backtest import run_backtest
from engine.asset_config import get_asset
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals

REPORTS = ROOT / "research" / "data" / "fql_forge" / "reports"
DLL = 1100.0


def yahoo(sym):
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10y&interval=1d"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read())
    res = r["chart"]["result"][0]; s = pd.Series(res["indicators"]["quote"][0]["close"], index=pd.to_datetime(res["timestamp"], unit="s").normalize()).dropna()
    return s[~s.index.duplicated()]


def _pf(a):
    a = np.asarray(a, float); a = a[~np.isnan(a)]; l = -a[a < 0].sum()
    return float(a[a > 0].sum() / l) if l > 0 else float("inf")


def book(s):
    p = s.values; eq = np.cumsum(p); dd = eq - np.maximum.accumulate(eq); sd = p.std()
    yr = s.groupby(s.index.year).sum(); wk = s.resample("W").sum(); mo = s.resample("ME").sum()
    return {"net_$": round(float(p.sum()), 0), "sharpe": round(float(p.mean()) / sd * np.sqrt(252), 2) if sd > 0 else None,
            "maxDD_$": round(float(dd.min()), 0), "worst_day_$": round(float(s.min()), 0), "worst_wk_$": round(float(wk.min()), 0),
            "worst_mo_$": round(float(mo.min()), 0), "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}",
            "DLL_breaches": int((s < -DLL).sum()), "MAR": round(float(p.sum()) / abs(dd.min()), 2) if dd.min() < 0 else None,
            "per_year_$": {int(y): round(float(v), 0) for y, v in yr.items()}}


def run():
    print("Cycle 2026-06-24i — vol-carry cleaner expression (one shot; report-only)\n", flush=True)
    cfg = get_asset("MNQ"); df = pd.read_csv(ROOT / "data/processed/MNQ_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"])
    sig = generate_crossbred_signals(df, entry_name="orb_breakout", exit_name="profit_ladder", filter_name="ema_slope", params={"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5})
    res = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"], commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = res["trades_df"].copy(); t["day"] = pd.to_datetime(t["entry_time"]).dt.normalize(); orb = t.groupby("day")["pnl"].sum()

    vix, vix3m, vix9d, vxx = yahoo("^VIX"), yahoo("^VIX3M"), yahoo("^VIX9D"), yahoo("VXX")
    v = pd.DataFrame({"vix": vix, "vix3m": vix3m, "vix9d": vix9d, "vxx": vxx}).dropna().sort_index()
    v["slope"] = v["vix3m"] / v["vix"] - 1
    v["shock5"] = v["vix"] / v["vix"].shift(5) - 1
    guards = (v["slope"] > 0) & (v["vix"] < 30) & (v["vix9d"] < v["vix"]) & (v["shock5"] < 0.30)
    expo = np.clip(v["slope"] / 0.10, 0, 1) * guards.astype(float)        # graded by slope, 0 if any guard fails
    v["expo"] = expo.shift(1)                                              # prior close -> today (no lookahead)
    v["shortvol_ret"] = -v["vxx"].pct_change()
    vx_ret = (v["expo"] * v["shortvol_ret"]).dropna()

    idx = orb.index.intersection(vx_ret.index)
    orb = orb.reindex(idx).fillna(0.0); vx_ret = vx_ret.reindex(idx).fillna(0.0)
    corr = float(np.corrcoef(orb.values, vx_ret.values)[0, 1])
    print(f"  aligned {len(idx)} days {idx.min().date()}..{idx.max().date()} | corr(ORB$,cleanVXret)={corr:.3f} | avg exposure {float(v['expo'].mean()):.2f}", flush=True)

    OUT = {"cycle": "2026-06-24i_volcarry_clean_expression", "corr_to_ORB": round(corr, 3)}
    # bad-day offset
    bad = {}
    for k in (10, 20, 50):
        wd = orb.nsmallest(k).index
        bad[f"worst{k}"] = {"VX_mean_ret_pct": round(float(vx_ret.reindex(wd).mean()) * 100, 2), "offsets": bool(vx_ret.reindex(wd).mean() > 0)}
    OUT["bad_day_offset"] = bad
    OUT["orb_alone"] = book(orb)
    # combined at allocations
    orb_std = float(orb[orb != 0].std()); vx_std = float(vx_ret[vx_ret != 0].std())
    combos = {}
    for label, alloc in [("VX_$3k", 3000), ("VX_$6k", 6000), ("VX_$10k", 10000), ("voltarget_halfORB", (0.5 * orb_std) / vx_std if vx_std > 0 else 0)]:
        b = book(orb + alloc * vx_ret); b["alloc_$"] = round(alloc, 0); combos[label] = b
    OUT["combined"] = combos
    # crash windows (combined $6k)
    c = orb + 6000 * vx_ret
    def win(s, a, b): return round(float(s[(s.index >= a) & (s.index <= b)].sum()), 0)
    OUT["crash_$6k_vs_ORBalone"] = {"mar2020": [win(c, "2020-02-20", "2020-03-31"), win(orb, "2020-02-20", "2020-03-31")],
                                    "2022": [win(c, "2022-01-01", "2022-12-31"), win(orb, "2022-01-01", "2022-12-31")]}

    oa = OUT["orb_alone"]
    # pick best SAFE allocation = largest alloc with DLL_breaches<=oa+0 and worst_day>=1.4*oa
    safe = [(lbl, b) for lbl, b in combos.items() if b["DLL_breaches"] <= oa["DLL_breaches"] and b["worst_day_$"] >= oa["worst_day_$"] * 1.4]
    best = max(safe, key=lambda kv: kv[1]["sharpe"] or 0) if safe else (None, None)
    OUT["best_safe_alloc"] = best[0]
    sharpe_lift = (best[1]["sharpe"] - oa["sharpe"]) if best[1] else 0
    offsets = all(b["offsets"] for b in bad.values())
    MATERIAL = 0.15
    if best[1] and sharpe_lift >= MATERIAL and (best[1]["MAR"] or 0) >= (oa["MAR"] or 0) and offsets:
        v_ = "ADVANCE_vol_carry_research_candidate"
    elif best[1] and sharpe_lift > 0.03 and offsets:
        v_ = "STILL_MARGINAL_stop_branch_retain_premium"
    else:
        v_ = "STOP_branch_retain_premium_validated_small"
    OUT["sharpe_lift_at_best_safe"] = round(sharpe_lift, 3); OUT["material_bar"] = MATERIAL; OUT["verdict"] = v_

    print(f"\n  bad-day offset: {[(k, b['VX_mean_ret_pct'], b['offsets']) for k,b in bad.items()]}", flush=True)
    print(f"  ORB alone: Sharpe={oa['sharpe']} MAR={oa['MAR']} maxDD=${oa['maxDD_$']} worstday=${oa['worst_day_$']} DLL={oa['DLL_breaches']} net=${oa['net_$']}", flush=True)
    for lbl, b in combos.items():
        print(f"  +{lbl} (${b['alloc_$']}): Sharpe={b['sharpe']} MAR={b['MAR']} maxDD=${b['maxDD_$']} worstday=${b['worst_day_$']} DLL={b['DLL_breaches']} net=${b['net_$']}", flush=True)
    print(f"  crash $6k vs ORB: {OUT['crash_$6k_vs_ORBalone']}", flush=True)
    print(f"\n  best safe alloc={best[0]} Sharpe-lift={round(sharpe_lift,3)} (material bar {MATERIAL}) offsets={offsets}", flush=True)
    print(f"  -> VERDICT: {v_}", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24i_volcarry_clean_expression.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote cleaner-vol-carry JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
