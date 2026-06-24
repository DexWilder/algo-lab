"""Cycle 2026-06-24a — first_impulse_pullback sleeve-addition battery vs deployed MNQ ORB (report-only).

Truth test for the Batch-4 lead. NOT standalone celebration. Question: does FIP ADD what ORB doesn't already
capture, or is it ORB-lite (same days, same losses = just extra MNQ risk)?

Both via the proven engine on MNQ, equal 1-contract sizing:
  ORB = orb_breakout | ema_slope | profit_ladder   (deployed WH)
  FIP = first_impulse_pullback | ema_slope | profit_ladder   (lead)
Battery: (1) trade-day overlap + direction conflict; (2) PnL relationship + bad-day OFFSET;
(3) combined book quality (PF, per-year, H1/H2, maxDD, worst day/wk/mo, max-yr conc, top-k);
(4) prop-fit (Tradeify-style daily-loss worst-day, both-fire worst day); (5) classification.
Report-only; no mutation. PnL is in $ (run_backtest applies point_value/commission/slippage).
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
TRADEIFY_50K_DLL = 1100.0   # ~Tradeify 50k daily loss limit ($); assumption, flagged


def _pf(s):
    s = np.asarray(s, float); w = s[s > 0].sum(); l = -s[s < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def get_trades(entry):
    cfg = get_asset("MNQ"); df = pd.read_csv(ROOT / "data/processed/MNQ_5m.csv"); df["datetime"] = pd.to_datetime(df["datetime"])
    sig = generate_crossbred_signals(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params=PARAMS)
    r = run_backtest(df, sig, mode="both", point_value=cfg["point_value"], tick_size=cfg["tick_size"],
                     commission_per_side=cfg["commission_per_side"], slippage_ticks=cfg["slippage_ticks"])
    t = r["trades_df"].copy(); t["entry_time"] = pd.to_datetime(t["entry_time"]); t["day"] = t["entry_time"].dt.normalize()
    for c in ("direction", "side", "dir"):
        if c in t.columns:
            t["dir"] = np.sign(pd.to_numeric(t[c], errors="coerce").fillna(0)) if t[c].dtype.kind in "if" else t[c].map({"long": 1, "short": -1, "L": 1, "S": -1}).fillna(0)
            break
    else:
        t["dir"] = 0
    return t


def daily(t):
    return t.groupby("day")["pnl"].sum()


def book_metrics(dser, t):
    p = t["pnl"].to_numpy(); sp = np.sort(p)[::-1]; tot = p[p > 0].sum()
    eq = dser.sort_index().cumsum(); dd = eq - eq.cummax()
    yr = dser.groupby(dser.index.year).sum()
    wk = dser.resample("W").sum(); mo = dser.resample("ME").sum()
    h = len(p) // 2
    return {"n_trades": len(p), "pf": round(_pf(p), 3), "net_$": round(float(p.sum()), 0), "expectancy_$": round(float(p.mean()), 2),
            "median_$": round(float(np.median(p)), 2), "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "maxDD_$": round(float(dd.min()), 0), "worst_day_$": round(float(dser.min()), 0), "worst_week_$": round(float(wk.min()), 0),
            "worst_month_$": round(float(mo.min()), 0), "yrs_pos": f"{int((yr>0).sum())}/{yr.shape[0]}",
            "maxyr_conc_pct": round(float(yr.max()) / yr[yr > 0].sum() * 100, 1) if (yr > 0).any() else None,
            "top10_pct": round(float(sp[:10].sum()) / tot * 100, 1) if tot > 0 else None,
            "per_year_$": {int(y): round(float(v), 0) for y, v in yr.items()}}


def run():
    print("Cycle 2026-06-24a — FIP sleeve-addition vs MNQ ORB (report-only)\n", flush=True)
    orb, fip = get_trades("orb_breakout"), get_trades("first_impulse_pullback")
    od, fd = daily(orb), daily(fip)
    alldays = od.index.union(fd.index)
    odA, fdA = od.reindex(alldays, fill_value=0.0), fd.reindex(alldays, fill_value=0.0)
    comb = odA + fdA

    OUT = {"cycle": "2026-06-24a_fip_sleeve_addition", "status": "report-only; sleeve-addition truth test"}
    # (1) overlap
    od_days, fd_days = set(od.index), set(fd.index)
    both = od_days & fd_days
    OUT["overlap"] = {"orb_trade_days": len(od_days), "fip_trade_days": len(fd_days), "both_trade_days": len(both),
                      "overlap_rate_of_fip_pct": round(len(both) / max(1, len(fd_days)) * 100, 1),
                      "jaccard": round(len(both) / max(1, len(od_days | fd_days)), 3)}
    # direction conflict on overlap days (if dir available)
    if (orb["dir"] != 0).any() and (fip["dir"] != 0).any():
        od_dir = orb.groupby("day")["dir"].mean().reindex(sorted(both))
        fd_dir = fip.groupby("day")["dir"].mean().reindex(sorted(both))
        same = int(((od_dir > 0) & (fd_dir > 0)).sum() + ((od_dir < 0) & (fd_dir < 0)).sum())
        conflict = int(((od_dir > 0) & (fd_dir < 0)).sum() + ((od_dir < 0) & (fd_dir > 0)).sum())
        OUT["overlap"]["same_dir_days"] = same; OUT["overlap"]["conflict_dir_days"] = conflict
    # (2) PnL relationship + bad-day offset
    corr_all = float(np.corrcoef(odA.values, fdA.values)[0, 1])
    co = comb.index.isin(sorted(both))
    corr_co = float(np.corrcoef(odA[co].values, fdA[co].values)[0, 1]) if co.sum() > 5 else None
    worstN = odA.nsmallest(20)                       # ORB's 20 worst days
    OUT["pnl_relationship"] = {"daily_corr_all": round(corr_all, 3), "daily_corr_cotrade": round(corr_co, 3) if corr_co is not None else None,
        "fip_mean_on_ORB_worst20_$": round(float(fdA.reindex(worstN.index).mean()), 1),
        "orb_mean_worst20_$": round(float(worstN.mean()), 1),
        "bad_day_offset": "OFFSETS" if float(fdA.reindex(worstN.index).mean()) > 0 else ("FLAT" if abs(float(fdA.reindex(worstN.index).mean())) < 10 else "ADDS_LOSS")}
    # (3) book quality
    OUT["orb_alone"] = book_metrics(odA, orb)
    OUT["fip_alone"] = book_metrics(fdA, fip)
    OUT["combined"] = book_metrics(comb, pd.concat([orb, fip], ignore_index=True))
    # (4) prop-fit
    bothfire = comb.reindex(sorted(both))
    OUT["prop_fit"] = {"combined_worst_day_$": round(float(comb.min()), 0), "orb_worst_day_$": round(float(odA.min()), 0),
        "bothfire_worst_day_$": round(float(bothfire.min()), 0), "tradeify_50k_DLL_assumed_$": TRADEIFY_50K_DLL,
        "combined_worst_day_breaches_DLL": bool(abs(float(comb.min())) > TRADEIFY_50K_DLL),
        "n_days_combined_breaches_DLL": int((comb < -TRADEIFY_50K_DLL).sum()), "n_days_orb_breaches_DLL": int((odA < -TRADEIFY_50K_DLL).sum())}
    # (5) classification
    c, o = OUT["combined"], OUT["orb_alone"]
    dd_worse = c["maxDD_$"] < o["maxDD_$"] * 1.15        # combined DD not materially worse (more negative) than 1.15x ORB
    pf_help = c["pf"] >= o["pf"] - 0.03
    low_corr = abs(corr_all) < 0.3
    offset = OUT["pnl_relationship"]["bad_day_offset"] in ("OFFSETS", "FLAT")
    new_dll = OUT["prop_fit"]["n_days_combined_breaches_DLL"] <= OUT["prop_fit"]["n_days_orb_breaches_DLL"]
    if (low_corr or offset) and pf_help and not (c["maxDD_$"] < o["maxDD_$"] * 1.4):
        verdict = "ADDITION_CANDIDATE"
    elif low_corr and OUT["overlap"]["overlap_rate_of_fip_pct"] < 50:
        verdict = "ADDITION_CANDIDATE_weak"
    elif corr_all > 0.6 and OUT["overlap"]["overlap_rate_of_fip_pct"] > 60:
        verdict = "KILL_ORB_lite"
    else:
        verdict = "WATCH"
    OUT["verdict"] = verdict

    print("=== OVERLAP ===", OUT["overlap"], flush=True)
    print("\n=== PnL RELATIONSHIP / BAD-DAY OFFSET ===", OUT["pnl_relationship"], flush=True)
    print("\n=== BOOK QUALITY ===", flush=True)
    for nm in ("orb_alone", "fip_alone", "combined"):
        m = OUT[nm]; print(f"  {nm:10s}: PF={m['pf']} net=${m['net_$']} maxDD=${m['maxDD_$']} worstday=${m['worst_day_$']} worstwk=${m['worst_week_$']} worstmo=${m['worst_month_$']} yrs+={m['yrs_pos']} maxyr={m['maxyr_conc_pct']}% top10={m['top10_pct']}% H1/H2={m['h1_pf']}/{m['h2_pf']}", flush=True)
    print(f"  combined per-year $: {OUT['combined']['per_year_$']}", flush=True)
    print(f"  orb      per-year $: {OUT['orb_alone']['per_year_$']}", flush=True)
    print("\n=== PROP-FIT ===", OUT["prop_fit"], flush=True)
    print(f"\n=== VERDICT: {verdict} ===", flush=True)
    print(f"  (corr={corr_all:.3f}, overlap_of_fip={OUT['overlap']['overlap_rate_of_fip_pct']}%, bad-day={OUT['pnl_relationship']['bad_day_offset']}, "
          f"combined PF {c['pf']} vs ORB {o['pf']}, combined maxDD ${c['maxDD_$']} vs ORB ${o['maxDD_$']})", flush=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "forge_cycle_2026-06-24a_fip_sleeve_addition.json").write_text(json.dumps(OUT, indent=2, default=str))
    print("\nWrote sleeve-addition JSON.\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
