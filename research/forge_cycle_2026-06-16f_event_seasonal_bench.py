"""Cycle 2026-06-16f — Non-equity EVENT-seasonal BENCH (around ZN/FOMC-week).

Lane B / REPORT-ONLY. Mission: build a small bench of audited non-equity event/calendar
candidates. Proven ZN/FOMC methodology applied across calendars x assets:
long, 2td-pre -> 2td-post, $1500 stop (prop-cap), beta-control, concentration,
contamination/clean-rebuild, per-instrument. Calendar-grade-aware verdicts.

Calendars: FOMC (OFFICIAL_FED_GOV), NFP (DETERMINISTIC 1st-Friday+shifts),
CPI (DATA_REQUIRED recall -> caps at WATCH). Auction/OPEC = DEFER (no calendar).
Assets: ZN/ZF/ZB (rates), MGC (gold, prop-DD watch). FREEZE maintained: no executor/
wiring/mutation. ZN/FOMC stays review-track (reference).
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
from engine.backtest import get_cost_params  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402

PRE, POST, STOP = 2, 2, 1500
CONTAM_USD = 700  # abnormal overnight $ move => roll/contamination candidate


def _pf(p):
    p = np.array(p); g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def daily(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df = df.assign(date=dt.dt.date)
    return df.groupby("date").agg(o=("open", "first"), l=("low", "min"), c=("close", "last")).reset_index()


def calendars():
    return {
        "FOMC": ("OFFICIAL_FED_GOV", [pd.Timestamp(c["actual_date"]) for c in build_official_fomc_calendar()]),
        "NFP": ("DETERMINISTIC", [pd.Timestamp(c["actual_date"]) for c in build_verified_nfp_calendar(2019, 2026)]),
        "CPI": ("DATA_REQUIRED_recall", [pd.Timestamp(c["actual_date"]) for c in build_verified_cpi_calendar()]),
    }


def screen(asset, events, stop):
    g = daily(asset); pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    gd = list(g["date"]); c = g["c"].values; o = g["o"].values; lo = g["l"].values
    prev_c = np.roll(c, 1); prev_c[0] = np.nan
    contam_idx = set(np.where(np.abs(o - prev_c) * pv > CONTAM_USD)[0])
    trs, contaminated = [], 0
    for ev in events:
        af = [i for i, d in enumerate(gd) if pd.Timestamp(d) >= ev]
        if not af: continue
        i = af[0]; ei, xi = i - PRE, min(i + POST, len(gd) - 1)
        if ei < 0 or xi <= ei: continue
        win_dates = gd[ei:xi + 1]
        win_gap = any((pd.Timestamp(win_dates[k]) - pd.Timestamp(win_dates[k - 1])).days > 4 for k in range(1, len(win_dates)))
        roll_in = any(ei < r <= xi for r in contam_idx)
        sess_gap = (pd.Timestamp(gd[i]) - ev).days > 4
        contam = win_gap or roll_in or sess_gap
        if contam: contaminated += 1
        entry = c[ei]; exit_px = None
        if stop:
            sp = entry - stop / pv
            for j in range(ei + 1, xi + 1):
                if lo[j] <= sp: exit_px = sp; break
        if exit_px is None: exit_px = c[xi]
        maw = (lo[ei:xi + 1].min() - entry) * pv
        if stop: maw = max(maw, -stop)
        trs.append({"pnl": (exit_px - entry) * pv - rt, "year": pd.Timestamp(gd[ei]).year, "maw": maw})
    if len(trs) < 10:
        return {"n": len(trs), "note": "low_n"}
    p = np.array([t["pnl"] for t in trs]); yrs = np.array([t["year"] for t in trs])
    yn = {int(y): float(p[yrs == y].sum()) for y in set(yrs)}; pos = sum(v for v in yn.values() if v > 0)
    half = len(p) // 2
    # generic beta-control
    hold = PRE + POST
    gp = np.array([(c[k + hold] - c[k]) * pv - rt for k in range(len(c) - hold)])
    return {"n": len(p), "pf": round(_pf(p), 3), "generic_pf": round(_pf(gp), 3),
            "expectancy": round(float(p.mean()), 2), "median": round(float(np.median(p)), 2),
            "max_year_share_pct": round(100 * max(yn.values()) / pos, 1) if pos > 0 else 0.0,
            "h1_pf": round(_pf(p[:half]), 3), "h2_pf": round(_pf(p[half:]), 3),
            "largest_loss": round(float(p.min()), 2), "max_adverse_window": round(float(min(t["maw"] for t in trs)), 2),
            "contaminated": contaminated}


def verdict(m, grade):
    if not m or m.get("n", 0) < 10:
        return "DEFER/low_n"
    pf, exp, gen = m["pf"], m["expectancy"], m["generic_pf"]
    beta_ok = gen is None or (gen > 0 and pf >= 1.4 * gen) or (gen <= 1.0 and pf >= 1.3)
    robust = m["h1_pf"] > 1.0 and m["h2_pf"] > 1.0 and m["max_year_share_pct"] <= 50
    prop_ok = abs(m["max_adverse_window"]) <= 2000 and abs(m["largest_loss"]) <= 2000
    contam_ok = m["contaminated"] == 0
    if pf < 1.15 and not beta_ok:
        return "KILL"
    strong = pf >= 1.3 and exp > 0 and beta_ok and robust and prop_ok and contam_ok
    if strong and grade in ("OFFICIAL_FED_GOV", "DETERMINISTIC"):
        return "PASS_REVIEW_TRACK"
    if strong and grade == "DATA_REQUIRED_recall":
        return "WATCH (blocker: calendar recall-grade — needs official)"
    if pf >= 1.3 and exp > 0 and beta_ok:
        b = ("prop-DD" if not prop_ok else "contamination" if not contam_ok else
             "concentration" if m["max_year_share_pct"] > 50 else "era" if not robust else "?")
        return f"WATCH (blocker: {b})"
    return "KILL"


def run():
    print("Cycle 2026-06-16f — non-equity event-seasonal BENCH (REPORT-ONLY)\n", flush=True)
    cals = calendars(); rep = {"cycle": "2026-06-16f_event_seasonal_bench", "mode": "Lane B report-only; freeze maintained",
                               "window": f"{PRE}td-pre->{POST}td-post long, ${STOP} stop", "bench": {}}
    asset_map = {"FOMC": ["ZN", "ZF", "ZB", "MGC"], "NFP": ["ZN", "ZF", "ZB", "MGC"], "CPI": ["ZN", "ZF", "ZB", "MGC"]}
    bench_pass, bench_watch = [], []
    for cal_name, (grade, events) in cals.items():
        print(f"\n===== {cal_name} ({grade}, {len(events)} events) =====", flush=True)
        for a in asset_map[cal_name]:
            m = screen(a, events, STOP)
            if m.get("n", 0) < 10:
                print(f"  {a}: low_n", flush=True); continue
            v = verdict(m, grade); key = f"{cal_name}/{a}"
            rep["bench"][key] = {**m, "grade": grade, "verdict": v}
            if "PASS" in v: bench_pass.append(key)
            elif "WATCH" in v: bench_watch.append(f"{key}: {v}")
            print(f"  {a}: n={m['n']} PF={m['pf']} (gen {m['generic_pf']}) exp=${m['expectancy']} med=${m['median']} "
                  f"maxyr={m['max_year_share_pct']}% H1/H2={m['h1_pf']}/{m['h2_pf']} MAW=${m['max_adverse_window']} "
                  f"contam={m['contaminated']} -> {v}", flush=True)
    rep["deferred_no_calendar"] = ["Treasury-auction (no official calendar)", "OPEC (no calendar)"]
    print("\n=== BENCH SUMMARY ===", flush=True)
    print(f"  PASS_REVIEW_TRACK: {bench_pass or 'none'}", flush=True)
    print(f"  WATCH: {bench_watch or 'none'}", flush=True)
    print(f"  DEFER (no calendar): Treasury-auction, OPEC. (ZN/FOMC = prior GREEN reference.)", flush=True)
    rep["bench_pass"] = bench_pass; rep["bench_watch"] = bench_watch
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16f_event_seasonal_bench.json"
    out.write_text(json.dumps(rep, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
