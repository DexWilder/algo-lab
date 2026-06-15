"""Cycle 2026-06-15j — pre-OPEX long-window seasonal: FULL robustness/prop validation.

Lane B / REPORT-ONLY. Validates the WATCH find (long equity index ~N..M trading days
before monthly OPEX). Tightened per operator spec: window-family robustness, beta
controls, era/LOO robustness, prop survivability, cost stress, OPEX integrity.
LONG-ONLY (the OPEX-week short leg was KILLed). No promotion/wiring/mutation.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402

PRIMARY = ["MES", "MNQ"]
OPTIONAL = ["MYM", "M2K"]
VARIANTS = [(11, 3), (12, 3), (10, 3), (11, 2), (11, 4), (10, 2), (12, 4)]  # (start,end) trading days before OPEX
BASE = (11, 3)


def third_friday(y, m):
    d = date(y, m, 1)
    d += timedelta(days=(4 - d.weekday()) % 7)
    return d + timedelta(days=14)


def daily_ohlc(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"]); df["d"] = df["datetime"].dt.date
    g = df.groupby("d").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
    g = g.reset_index().rename(columns={"d": "date"})
    return g


def opex_trading_indices(dates):
    """For each monthly OPEX (3rd Fri; holiday->prior trading day), the trading-day index."""
    dset = list(dates); idxmap = {dt: i for i, dt in enumerate(dset)}
    out = []
    yrs = sorted(set(d.year for d in dset))
    for y in yrs:
        for m in range(1, 13):
            tf = third_friday(y, m)
            # last trading day <= 3rd Friday (handles Good Friday etc.)
            cand = [i for i, dt in enumerate(dset) if dt <= tf]
            if not cand:
                continue
            i = cand[-1]
            if dset[i] < tf - timedelta(days=4):  # OPEX month not covered by data
                continue
            out.append((tf, i, dset[i] != tf))  # (opex_date, td_idx, holiday_adjusted)
    return out


def windows(g, start, end):
    """Long windows: entry close at opex_idx-start, exit close at opex_idx-end. Returns list of dicts."""
    dates = list(g["date"]); c = g["c"].values; o = g["o"].values; h = g["h"].values; lo = g["l"].values
    n = len(dates); trs = []
    for opx, i, hol in opex_trading_indices(dates):
        ei, xi = i - start, i - end
        if ei < 0 or xi >= n or xi <= ei:
            continue
        entry, exit_ = c[ei], c[xi]
        # intra-window worst MTM (low vs entry) and worst overnight gap (open vs prior close)
        seg_lo = lo[ei:xi + 1].min()
        mtm_worst = seg_lo - entry  # price units (negative = drawdown)
        gaps = o[ei + 1:xi + 1] - c[ei:xi]
        worst_gap = gaps.min() if len(gaps) else 0.0
        trs.append({"opex": opx, "entry_date": dates[ei], "exit_date": dates[xi],
                    "ret": exit_ / entry - 1, "px_pnl": exit_ - entry,
                    "mtm_worst_px": mtm_worst, "worst_gap_px": worst_gap,
                    "hold_td": xi - ei, "holiday_adj": hol, "year": dates[ei].year})
    return trs


def _pf(pnls):
    pnls = np.array(pnls); g = pnls[pnls > 0].sum(); b = -pnls[pnls < 0].sum()
    return float(g / b) if b > 0 else float("inf") if g > 0 else 0.0


def metrics(trs, pv, rt_cost, cost_mult=1.0):
    pnl = np.array([t["px_pnl"] * pv - rt_cost * cost_mult for t in trs])
    n = len(pnl)
    if n == 0:
        return {"n": 0}
    yrs = np.array([t["year"] for t in trs])
    by_year = {int(y): round(float(pnl[yrs == y].sum()), 0) for y in sorted(set(yrs))}
    yr_tot = {y: v for y, v in by_year.items()}
    pos_sum = sum(v for v in yr_tot.values() if v > 0)
    maxyr = round(100 * max(yr_tot.values()) / pos_sum, 1) if pos_sum > 0 else 0.0
    # LOO PF
    loo = {}
    for y in sorted(set(yrs)):
        m = yrs != y
        loo[int(y)] = round(_pf(pnl[m]), 3)
    half = n // 2
    # consecutive losses
    mc = c = 0
    for p in pnl:
        c = c + 1 if p < 0 else 0; mc = max(mc, c)
    return {
        "n": n, "pf": round(_pf(pnl), 3), "median": round(float(np.median(pnl)), 2),
        "mean": round(float(pnl.mean()), 2), "net": round(float(pnl.sum()), 0),
        "win_rate_pct": round(100 * float((pnl > 0).mean()), 1),
        "by_year_net": by_year, "max_year_share_pct": maxyr,
        "loo_pf": loo, "h1_pf": round(_pf(pnl[:half]), 3), "h2_pf": round(_pf(pnl[half:]), 3),
        "pre2020_pf": round(_pf(pnl[yrs < 2020]), 3) if (yrs < 2020).any() else None,
        "post2020_pf": round(_pf(pnl[yrs >= 2020]), 3) if (yrs >= 2020).any() else None,
        "y2022_net": by_year.get(2022), "y2022_pf": round(_pf(pnl[yrs == 2022]), 3) if (yrs == 2022).any() else None,
        "largest_window_loss": round(float(pnl.min()), 2),
        "max_consecutive_losses": mc,
        "worst_mtm_dd_usd": round(float(min(t["mtm_worst_px"] for t in trs) * pv), 2),
        "worst_overnight_gap_usd": round(float(min(t["worst_gap_px"] for t in trs) * pv), 2),
        "all_windows_overnight": True, "n_holiday_adjusted_opex": int(sum(t["holiday_adj"] for t in trs)),
        "med_hold_td": int(np.median([t["hold_td"] for t in trs])),
    }


def beta_control(g, pv, rt_cost, hold_td):
    c = g["c"].values; n = len(c)
    # generic rolling hold of same length (all start points)
    gen = np.array([c[i + hold_td] / c[i] - 1 for i in range(n - hold_td)])
    gen_pnl = np.array([(c[i + hold_td] - c[i]) * pv - rt_cost for i in range(n - hold_td)])
    return {"generic_mean_ret_pct": round(float(gen.mean() * 100), 3),
            "generic_winrate_pct": round(float((gen > 0).mean() * 100), 1),
            "generic_pf": round(_pf(gen_pnl), 3),
            "always_long_total_ret_pct": round(float((c[-1] / c[0] - 1) * 100), 1)}


def run():
    print("Cycle 2026-06-15j — pre-OPEX long robustness/prop validation (REPORT-ONLY)\n", flush=True)
    report = {"cycle": "2026-06-15j_opex_robustness", "mode": "Lane B report-only",
              "variants_tested": VARIANTS, "base": BASE, "long_only": True, "assets": {}}
    for asset in PRIMARY + OPTIONAL:
        g = daily_ohlc(asset); pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
        rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
        print(f"\n===== {asset} (pv=${pv}, round-trip cost=${rt:.2f}) =====", flush=True)
        # variant grid
        grid = {}
        for (s, e) in VARIANTS:
            m = metrics(windows(g, s, e), pv, rt)
            grid[f"{s}->{e}"] = {"pf": m.get("pf"), "median": m.get("median"),
                                 "win_rate_pct": m.get("win_rate_pct"), "n": m.get("n"),
                                 "max_year_share_pct": m.get("max_year_share_pct")}
        print("  window-family grid (pf | median | wr% | maxyr%):", flush=True)
        for k, v in grid.items():
            print(f"    {k:8s} PF={v['pf']} med=${v['median']} WR={v['win_rate_pct']}% maxyr={v['max_year_share_pct']}%", flush=True)
        # base deep dive
        base_trs = windows(g, *BASE)
        base = metrics(base_trs, pv, rt)
        bc = beta_control(g, pv, rt, base["med_hold_td"])
        stress = {f"{cm}x": metrics(base_trs, pv, rt, cost_mult=cm)["pf"] for cm in (1, 2, 5)}
        print(f"  BASE {BASE[0]}->{BASE[1]}: PF={base['pf']} median=${base['median']} WR={base['win_rate_pct']}% "
              f"maxyr={base['max_year_share_pct']}% H1/H2={base['h1_pf']}/{base['h2_pf']}", flush=True)
        print(f"    era: pre2020 PF={base['pre2020_pf']} post2020 PF={base['post2020_pf']} | 2022 net=${base['y2022_net']} PF={base['y2022_pf']}", flush=True)
        print(f"    LOO PF range: {min(base['loo_pf'].values())}-{max(base['loo_pf'].values())}", flush=True)
        print(f"    beta-control: OPEX mean=${base['mean']} vs generic{base['med_hold_td']}td PF={bc['generic_pf']} mean_ret={bc['generic_mean_ret_pct']}% | OPEX PF {base['pf']} vs generic PF {bc['generic_pf']}", flush=True)
        print(f"    prop: largest_window_loss=${base['largest_window_loss']} worst_MTM_DD=${base['worst_mtm_dd_usd']} "
              f"worst_overnight_gap=${base['worst_overnight_gap_usd']} max_consec_losses={base['max_consecutive_losses']}", flush=True)
        print(f"    Tradeify $2K (1 micro): worst daily MTM DD ${base['worst_mtm_dd_usd']} -> {'BREACH' if abs(base['worst_mtm_dd_usd'])>2000 else 'OK'}", flush=True)
        print(f"    cost-stress PF 1x/2x/5x: {stress['1x']}/{stress['2x']}/{stress['5x']}", flush=True)
        print(f"    OPEX integrity: {base['n']} windows, holiday-adjusted OPEX={base['n_holiday_adjusted_opex']}, all multi-day holds", flush=True)
        report["assets"][asset] = {"grid": grid, "base": base, "beta_control": bc, "cost_stress_pf": stress}

    # verdict (primary assets)
    def verdict(a):
        b = report["assets"][a]["base"]; bc = report["assets"][a]["beta_control"]; st = report["assets"][a]["cost_stress_pf"]
        alpha = b["pf"] >= 1.3 and bc["generic_pf"] and b["pf"] >= 1.4 * bc["generic_pf"]
        robust = (b["max_year_share_pct"] <= 50 and b["h1_pf"] > 1.0 and b["h2_pf"] > 1.0
                  and min(report["assets"][a]["base"]["loo_pf"].values()) > 1.0 and st["2x"] >= 1.2)
        if alpha and robust:
            return "WATCH_SEASONAL (beta-laden; SEASONAL_BETA_TIMING — review-only candidate, NOT diversifier)"
        if b["pf"] >= 1.3:
            return "DEFER (passes some gates; blocker = " + (
                "concentration" if b["max_year_share_pct"] > 50 else
                "era/LOO" if min(report["assets"][a]["base"]["loo_pf"].values()) <= 1.0 else
                "cost-fragile" if st["2x"] < 1.2 else "beta-control") + ")"
        return "KILL"
    print("\n=== VERDICTS (primary) ===", flush=True)
    for a in PRIMARY:
        v = verdict(a); report["assets"][a]["verdict"] = v
        print(f"  {a}: {v}", flush=True)
    report["boundaries"] = "report-only; no promotion/wiring/mutation; long-only; OPEX-week short leg KILLed"
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15j_opex_robustness.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
