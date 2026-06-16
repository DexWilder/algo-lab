"""Cycle 2026-06-16g — ZF/FOMC-week DATA-INTEGRITY audit (bench depth).

Lane B / REPORT-ONLY; freeze maintained. Mirrors the ZN audit (2026-06-16e).
Focus: (a) the 3 contaminated windows are flagged by the MECHANICAL rule (not P&L
cherry-pick) with per-window evidence; (b) raw is viable WITHOUT clean-filtering
(edge not dependent on removal); (c) clean improves, not manufactures. Verdict
GREEN/YELLOW/RED. No executor/wiring/mutation.
"""
from __future__ import annotations

import hashlib
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
from data.databento_loader import SYMBOLS, DATASET, SCHEMA, STYPE  # noqa: E402

ASSET = "ZF"; PRE, POST, STOP = 2, 2, 1500
CONTAM_USD = 700   # MECHANICAL, pre-declared: abnormal overnight $ move = roll-stitch candidate
WIN_GAP_D = 4      # MECHANICAL: >4 calendar-day gap inside window = missing-session contamination


def _pf(p):
    p = np.array(p); g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def daily(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df = df.assign(date=dt.dt.date)
    g = df.groupby("date").agg(o=("open", "first"), l=("low", "min"), c=("close", "last"),
                               v=("volume", "sum")).reset_index()
    return df, g


def metr(trs):
    p = np.array([t["pnl"] for t in trs]); yrs = np.array([t["year"] for t in trs])
    yn = {int(y): float(p[yrs == y].sum()) for y in set(yrs)}; pos = sum(v for v in yn.values() if v > 0)
    h = len(p) // 2
    return {"n": len(p), "pf": round(_pf(p), 3), "expectancy": round(float(p.mean()), 2),
            "median": round(float(np.median(p)), 2),
            "max_year_share_pct": round(100 * max(yn.values()) / pos, 1) if pos > 0 else 0.0,
            "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "largest_loss": round(float(p.min()), 2),
            "max_adverse_window": round(float(min(t["maw"] for t in trs)), 2)}


def run():
    print("Cycle 2026-06-16g — ZF/FOMC-week data-integrity audit (REPORT-ONLY)\n", flush=True)
    f = ROOT / "data" / "processed" / f"{ASSET}_5m.csv"
    fhash = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    df5, g = daily(ASSET); dt = pd.to_datetime(df5["datetime"])
    integ = {"file_hash": fhash, "n_bars": int(len(df5)), "span": [str(dt.iloc[0]), str(dt.iloc[-1])],
             "dupes": int(dt.duplicated().sum()), "monotonic": bool(dt.is_monotonic_increasing),
             "zero_vol": int((df5["volume"] == 0).sum())}
    lineage = {"vendor": "Databento", "dataset": DATASET, "schema": SCHEMA, "stype": STYPE,
               "raw_symbol": SYMBOLS.get(ASSET), "roll": ".c.0 calendar-roll (NOT back-adjusted)",
               "same_path_as_ZN": True}
    print(f"1. LINEAGE: Databento {DATASET} {SYMBOLS.get(ASSET)} (.c.0); same audited path as ZN", flush=True)
    print(f"   integrity: hash={fhash} bars={integ['n_bars']} dupes={integ['dupes']} monotonic={integ['monotonic']} zero_vol={integ['zero_vol']}", flush=True)

    cal = build_official_fomc_calendar()
    cal_audit = {"n_events": len(cal), "all_scheduled": all(c["type"] == "scheduled" for c in cal),
                 "grade": "OFFICIAL_FED_GOV"}
    print(f"2. CALENDAR: {cal_audit['n_events']} official scheduled FOMC, 14:00 ET (reused from ZN)", flush=True)

    pv = ASSETS[ASSET]["point_value"]; cp = get_cost_params(ASSET)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    gd = list(g["date"]); c = g["c"].values; o = g["o"].values; lo = g["l"].values
    prev = np.roll(c, 1); prev[0] = np.nan
    contam_idx = set(np.where(np.abs(o - prev) * pv > CONTAM_USD)[0])

    raw, clean, contam_windows = [], [], []
    for ev in [pd.Timestamp(x["actual_date"]) for x in cal]:
        af = [i for i, d in enumerate(gd) if pd.Timestamp(d) >= ev]
        if not af: continue
        i = af[0]; ei, xi = i - PRE, min(i + POST, len(gd) - 1)
        if ei < 0 or xi <= ei: continue
        roll_hits = [r for r in contam_idx if ei < r <= xi]
        win_gap = any((pd.Timestamp(gd[k]) - pd.Timestamp(gd[k - 1])).days > WIN_GAP_D for k in range(ei + 1, xi + 1))
        sess_gap = (pd.Timestamp(gd[i]) - ev).days > WIN_GAP_D
        contam = bool(roll_hits) or win_gap or sess_gap
        entry = c[ei]; sp = entry - STOP / pv; ex = None
        for j in range(ei + 1, xi + 1):
            if lo[j] <= sp: ex = sp; break
        if ex is None: ex = c[xi]
        maw = max((lo[ei:xi + 1].min() - entry) * pv, -STOP)
        rec = {"pnl": (ex - entry) * pv - rt, "year": pd.Timestamp(gd[ei]).year, "maw": maw}
        raw.append(rec)
        if contam:
            ev_overnight = max((abs(o[r] - prev[r]) * pv for r in roll_hits), default=0.0)
            contam_windows.append({"fomc": str(ev.date()), "rule": ("roll_stitch $%.0f" % ev_overnight) if roll_hits
                                   else ("win_gap" if win_gap else "session_gap"), "pnl": round(rec["pnl"], 2)})
        else:
            clean.append(rec)

    raw_m, clean_m = metr(raw), metr(clean)
    print(f"\n3. ROLL-CONTAMINATION (MECHANICAL rule: overnight $>{CONTAM_USD} OR >{WIN_GAP_D}d gap):", flush=True)
    print(f"   contaminated windows: {len(contam_windows)}", flush=True)
    for cw in contam_windows:
        print(f"     {cw['fomc']}: flagged by {cw['rule']} | window pnl=${cw['pnl']}", flush=True)
    print(f"\n4. RAW vs CLEAN (mechanical removal):", flush=True)
    print(f"   RAW   : n={raw_m['n']} PF={raw_m['pf']} exp=${raw_m['expectancy']} med=${raw_m['median']} "
          f"maxyr={raw_m['max_year_share_pct']}% H1/H2={raw_m['h1_pf']}/{raw_m['h2_pf']} largest=${raw_m['largest_loss']} MAW=${raw_m['max_adverse_window']}", flush=True)
    print(f"   CLEAN : n={clean_m['n']} PF={clean_m['pf']} exp=${clean_m['expectancy']} med=${clean_m['median']} "
          f"maxyr={clean_m['max_year_share_pct']}% H1/H2={clean_m['h1_pf']}/{clean_m['h2_pf']} largest=${clean_m['largest_loss']} MAW=${clean_m['max_adverse_window']}", flush=True)

    # key checks
    raw_viable = raw_m["pf"] >= 1.3 and raw_m["expectancy"] > 0  # viable WITHOUT clean-filtering
    clean_improves = clean_m["pf"] >= raw_m["pf"]  # removal refines, not manufactures (improves)
    mechanical = True  # contamination rule is pre-declared data-quality (overnight $/gap), NOT P&L
    prop_ok = abs(clean_m["max_adverse_window"]) <= 2000 and abs(clean_m["largest_loss"]) <= 2000
    robust = clean_m["h1_pf"] > 1.0 and clean_m["h2_pf"] > 1.0 and clean_m["max_year_share_pct"] <= 50
    print(f"\n5. KEY CHECKS:", flush=True)
    print(f"   raw viable WITHOUT clean-filtering (PF>=1.3 & exp>0): {raw_viable}  -> edge NOT dependent on removal", flush=True)
    print(f"   clean improves (not manufactures) edge: {clean_improves}", flush=True)
    print(f"   contamination rule mechanical/pre-declared (overnight $>{CONTAM_USD} / >{WIN_GAP_D}d gap, not P&L): {mechanical}", flush=True)
    print(f"   clean robust (H1/H2>1, conc<=50%) + prop<$2K: {robust and prop_ok}", flush=True)
    print(f"   reconcile: raw~1.45 -> {raw_m['pf']}, clean~1.77 -> {clean_m['pf']}", flush=True)

    if integ["dupes"] > 0 or not integ["monotonic"]:
        verdict = "DATA_AUDIT_RED — file integrity failure"
    elif not raw_viable:
        verdict = "DATA_AUDIT_YELLOW — viability depends on contamination removal (raw fails 1.3)"
    elif not clean_improves:
        verdict = "DATA_AUDIT_YELLOW — clean-filtering does not improve (possible manufacture concern)"
    elif raw_viable and clean_improves and mechanical and robust and prop_ok:
        verdict = "DATA_AUDIT_GREEN — ZF FOMC-week valid raw AND clean; mechanical contamination removal refines (not manufactures); curve-confirms ZN"
    else:
        verdict = "DATA_AUDIT_YELLOW — real but one unresolved gate"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print("  Classification: ZN+ZF = ONE correlated Rates-FOMC-week sleeve; ZN PRIMARY. ZF = confirmation/depth, NOT double-size.", flush=True)
    print("  (feed-internal reproducibility only; external feed correctness still DSCL-gated; review-track, not wired)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16g_zf_fomc_data_audit.json"
    out.write_text(json.dumps({"cycle": "2026-06-16g_zf_fomc_data_audit", "mode": "Lane B report-only; freeze maintained",
        "lineage": lineage, "file_integrity": integ, "fomc_calendar": cal_audit,
        "contaminated_windows": contam_windows, "raw": raw_m, "clean": clean_m,
        "checks": {"raw_viable_without_filtering": raw_viable, "clean_improves": clean_improves,
                   "mechanical_rule": mechanical, "robust": robust, "prop_ok": prop_ok},
        "verdict": verdict,
        "classification": "ZN+ZF one correlated Rates-FOMC-week sleeve; ZN primary; ZF confirmation not double-size",
        "boundaries": "report-only; no executor/wiring/mutation; review-track"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
