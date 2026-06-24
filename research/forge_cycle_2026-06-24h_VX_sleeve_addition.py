"""Cycle 2026-06-24h — VX-carry sleeve-addition battery vs ORB (report-only).

Decisive question (NOT standalone significance): does VX-carry OFFSET ORB's worst days (real diversifier ->
ADVANCE) or COMPOUND them (coincident risk-off drawdown -> ARCHIVE despite standalone edge)? The 0.50 full-
sample corr + short-vol's stress-crash nature make this the whole ballgame.

Battery: (1) ORB bad-day interaction (VX on ORB worst 10/20/50 + stress-window corr); (2) combined book at
several VX $-allocations (PF/Sharpe/maxDD/worst-day/per-year/DLL); (3) tail-sizing/prop-fit (alloc where
worst-day Tradeify-compatible + edge survives); (4) crash regimes 2018/2020/2022; (5) controls (vs uncond
short-vol; corr ex-crisis). ORB = orb_breakout|ema_slope|profit_ladder MNQ ($/1 contract). VX = contango-only
short-vol timed daily return. Report-only; no mutation.
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
DLL = 1100.0  # Tradeify-50k-style daily loss limit ($)


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
            "DLL_breaches": int((s < -DLL).sum()), "MAR": round(float(p.sum()) / abs(dd.min()), 2) if dd.min() < 0 else None}


def run():
    print("Cycle 2026-06-24h — VX sleeve-addition vs ORB (report-only)\n", flush=True)
    # ORB daily $ PnL (1 MNQ contract)
    cfg = get_asset("MNQ"); df = pd.read_csv(ROOT / "data/processed/MNQ_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"])
    sig = generate_crossbred_signals(df, entry_name="orb_breakout", exit_name="profit_ladder", filter_name="ema_slope", params={"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5})
    res = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"], commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = res["trades_df"].copy(); t["day"] = pd.to_datetime(t["entry_time"]).dt.normalize()
    orb = t.groupby("day")["pnl"].sum()
    # VX timed daily return
    vix, vix3m, svxy = yahoo("^VIX"), yahoo("^VIX3M"), yahoo("SVXY")
    v = pd.DataFrame({"vix": vix, "vix3m": vix3m, "svxy": svxy}).dropna().sort_index()
    v["regime"] = (v["vix3m"] / v["vix"] - 1).shift(1).gt(0).astype(float)        # prior-close contango -> today
    vx_ret = (v["regime"] * v["svxy"].pct_change()).dropna()                       # timed short-vol daily return

    idx = orb.index.intersection(vx_ret.index)
    orb = orb.reindex(idx).fillna(0.0); vx_ret = vx_ret.reindex(idx).fillna(0.0)
    print(f"  aligned {len(idx)} days {idx.min().date()}..{idx.max().date()} | full-sample corr(ORB$,VXret)={np.corrcoef(orb.values, vx_ret.values)[0,1]:.3f}", flush=True)

    OUT = {"cycle": "2026-06-24h_VX_sleeve_addition", "n_days": len(idx)}
    # (1) DECISIVE — VX on ORB's worst days
    bad = {}
    for k in (10, 20, 50):
        wd = orb.nsmallest(k).index
        bad[f"worst{k}"] = {"ORB_mean_$": round(float(orb.reindex(wd).mean()), 0), "VX_mean_ret_on_those_days_pct": round(float(vx_ret.reindex(wd).mean()) * 100, 2),
                            "VX_offsets": bool(vx_ret.reindex(wd).mean() > 0)}
    # stress-window corr: ORB's bottom-quartile days
    q = orb.quantile(0.25); stress = orb[orb <= q].index
    stress_corr = round(float(np.corrcoef(orb.reindex(stress).values, vx_ret.reindex(stress).values)[0, 1]), 3)
    OUT["bad_day_interaction"] = bad
    OUT["stress_window_corr"] = stress_corr
    OUT["interaction_verdict"] = "OFFSETS" if all(b["VX_offsets"] for b in bad.values()) else ("MIXED" if any(b["VX_offsets"] for b in bad.values()) else "COMPOUNDS")

    # (2)+(3) combined book at several VX allocations (vol-target VX to a $/day risk, + small fixed)
    orb_std = float(orb[orb != 0].std())
    OUT["orb_alone"] = book(orb)
    combos = {}
    for label, alloc in [("VX_$2k", 2000), ("VX_$5k", 5000), ("VX_$10k", 10000), ("VX_voltarget_halfORB", None)]:
        if alloc is None:
            # size VX so its daily $ std ~ half ORB's daily std
            vx_std = float(vx_ret[vx_ret != 0].std()); alloc = (0.5 * orb_std) / vx_std if vx_std > 0 else 0
        comb = orb + alloc * vx_ret
        b = book(comb); b["vx_alloc_$"] = round(alloc, 0)
        combos[label] = b
    OUT["combined"] = combos

    # (4) crash regimes (combined at $5k VX)
    c5 = orb + 5000 * vx_ret
    def win(s, a, b): return round(float(s[(s.index >= a) & (s.index <= b)].sum()), 0)
    OUT["crash_combined_$5kVX_vs_ORBalone"] = {
        "feb2018": [win(c5, "2018-01-25", "2018-02-15"), win(orb, "2018-01-25", "2018-02-15")],
        "mar2020": [win(c5, "2020-02-20", "2020-03-31"), win(orb, "2020-02-20", "2020-03-31")],
        "2022": [win(c5, "2022-01-01", "2022-12-31"), win(orb, "2022-01-01", "2022-12-31")]}
    # (5) control: corr ex-crisis
    noncrisis = idx[~(((idx >= "2018-01-25") & (idx <= "2018-02-28")) | ((idx >= "2020-02-20") & (idx <= "2020-04-30")))]
    OUT["corr_ex_crisis"] = round(float(np.corrcoef(orb.reindex(noncrisis).values, vx_ret.reindex(noncrisis).values)[0, 1]), 3)

    # verdict
    oa = OUT["orb_alone"]; c5b = combos["VX_$5k"]
    offsets = OUT["interaction_verdict"] in ("OFFSETS", "MIXED")
    improves = (c5b["sharpe"] or 0) >= (oa["sharpe"] or 0) and (c5b["MAR"] or 0) >= (oa["MAR"] or 0)
    not_worse_tail = c5b["worst_day_$"] >= oa["worst_day_$"] * 1.5 and c5b["DLL_breaches"] <= oa["DLL_breaches"] + 2
    if OUT["interaction_verdict"] == "COMPOUNDS":
        v = "ARCHIVE_compounds_ORB_drawdowns"
    elif offsets and improves and not_worse_tail:
        v = "ADVANCE_research_candidate"
    elif offsets and improves:
        v = "WATCH_tail_or_sizing_unresolved"
    else:
        v = "ARCHIVE"
    OUT["verdict"] = v

    print("\n=== (1) DECISIVE: VX on ORB worst days ===", flush=True)
    for k, b in bad.items():
        print(f"  ORB {k}: ORB mean ${b['ORB_mean_$']} | VX mean {b['VX_mean_ret_on_those_days_pct']}% -> offsets={b['VX_offsets']}", flush=True)
    print(f"  stress-window corr (ORB bottom-quartile)={stress_corr} | full-sample 0.50 | ex-crisis corr={OUT['corr_ex_crisis']} -> {OUT['interaction_verdict']}", flush=True)
    print("\n=== (2/3) COMBINED BOOK ===", flush=True)
    print(f"  ORB alone: Sharpe={oa['sharpe']} net=${oa['net_$']} maxDD=${oa['maxDD_$']} worstday=${oa['worst_day_$']} DLLbreach={oa['DLL_breaches']} MAR={oa['MAR']} yrs+={oa['yrs_pos']}", flush=True)
    for label, b in combos.items():
        print(f"  +{label} (${b['vx_alloc_$']}): Sharpe={b['sharpe']} net=${b['net_$']} maxDD=${b['maxDD_$']} worstday=${b['worst_day_$']} DLLbreach={b['DLL_breaches']} MAR={b['MAR']} yrs+={b['yrs_pos']}", flush=True)
    print(f"\n=== (4) CRASH (combined $5kVX vs ORB alone) ===  {OUT['crash_combined_$5kVX_vs_ORBalone']}", flush=True)
    print(f"\n=== VERDICT: {v} ===", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24h_VX_sleeve_addition.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote VX sleeve-addition JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
