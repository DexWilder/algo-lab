"""Cycle 2026-06-16e — ZN/FOMC-week DATA-INTEGRITY + CALENDAR audit (review-track).

Lane B / REPORT-ONLY. Audits the ZN/FOMC-week candidate before it can advance.
Freeze maintained: no registry/scheduler/portfolio mutation, no executor build, no wiring.

Checks: ZN lineage; file integrity (hash/span/dupes/monotonic/gaps); FOMC calendar
provenance (official scheduled only); per-window session validity; ROLL-STITCH
contamination detection inside holding windows; clean-events REBUILD (+reconcile to
packet). Verdict: DATA_AUDIT_GREEN / YELLOW / RED.
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

ASSET = "ZN"; PRE, POST, STOP = 2, 2, 1200
# packet-cited numbers to reconcile
PKT = {"pf": 1.945, "expectancy": 242.85, "median": 43.78, "n": 54,
       "largest_loss": -1234.35, "maw": -1200.0, "maxyr": 30.2}


def _pf(p):
    p = np.array(p); g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def daily(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df = df.assign(dtt=dt, date=dt.dt.date)
    g = df.groupby("date").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"),
                               c=("close", "last"), v=("volume", "sum"), nbars=("close", "size")).reset_index()
    return df, g


def run():
    print("Cycle 2026-06-16e — ZN/FOMC-week data-integrity + calendar audit (REPORT-ONLY)\n", flush=True)
    rep = {"cycle": "2026-06-16e_zn_fomc_data_audit", "mode": "Lane B report-only; freeze maintained"}

    # ---- 1. lineage + file integrity ----
    f = ROOT / "data" / "processed" / f"{ASSET}_5m.csv"
    fhash = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
    df5, g = daily(ASSET)
    dt = pd.to_datetime(df5["datetime"])
    diffs = dt.diff().dt.total_seconds() / 60
    lineage = {"vendor": "Databento", "dataset": DATASET, "schema": SCHEMA, "stype": STYPE,
               "raw_symbol": SYMBOLS.get(ASSET), "roll": ".c.0 calendar-roll continuous (NOT back-adjusted)"}
    integ = {"file_hash": fhash, "n_bars": int(len(df5)), "span": [str(dt.iloc[0]), str(dt.iloc[-1])],
             "duplicate_ts": int(dt.duplicated().sum()), "monotonic": bool(dt.is_monotonic_increasing),
             "n_zero_volume_bars": int((df5["volume"] == 0).sum()) if "volume" in df5 else None,
             "gaps_gt_3d": int((diffs > 4320).sum()), "trading_days": int(len(g))}
    print(f"1. LINEAGE: {lineage['vendor']} {lineage['dataset']} {lineage['raw_symbol']} ({lineage['roll']})", flush=True)
    print(f"   integrity: hash={fhash} bars={integ['n_bars']} span {integ['span'][0]}..{integ['span'][1]} "
          f"dupes={integ['duplicate_ts']} monotonic={integ['monotonic']} zero_vol={integ['n_zero_volume_bars']}", flush=True)

    # ---- 2. FOMC calendar provenance ----
    cal = build_official_fomc_calendar()
    cal_audit = {"n_events": len(cal), "all_scheduled": all(c["type"] == "scheduled" for c in cal),
                 "all_1400ET": all(c["actual_time_et"] == "14:00:00" for c in cal),
                 "sources": sorted(set(c["source"] for c in cal)),
                 "grade": "OFFICIAL_FED_GOV (scheduled only; emergency/notation excluded by module)"}
    print(f"\n2. FOMC CALENDAR: {cal_audit['n_events']} events, all_scheduled={cal_audit['all_scheduled']}, "
          f"all 14:00 ET={cal_audit['all_1400ET']}, src={cal_audit['sources']}", flush=True)

    # ---- 3. roll-stitch detection (ZN .c.0 overnight gaps) ----
    o = g["o"].values; c = g["c"].values; prev_c = np.roll(c, 1); prev_c[0] = np.nan
    overnight_gap = np.abs(o - prev_c)  # points
    roll_thresh = 0.5  # >0.5 ZN points (~$500) overnight = likely roll-stitch / abnormal
    roll_idx = set(np.where(overnight_gap > roll_thresh)[0])
    gdates = list(g["date"])
    print(f"\n3. ROLL-STITCH SCAN: {len(roll_idx)} ZN daily overnight gaps > {roll_thresh}pt "
          f"(candidate roll/contamination dates)", flush=True)

    # ---- 4. per-FOMC-window validity + contamination + REBUILD ----
    pv = ASSETS[ASSET]["point_value"]; cp = get_cost_params(ASSET)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    dates_idx = {d: i for i, d in enumerate(gdates)}
    fomc_dts = [pd.Timestamp(x["actual_date"]) for x in cal]
    sigvals = []
    raw_tr, clean_tr, contaminated = [], [], []
    win_audit = []
    for ev in fomc_dts:
        af = [i for i, d in enumerate(gdates) if pd.Timestamp(d) >= ev]
        if not af:
            continue
        i = af[0]; ei, xi = i - PRE, min(i + POST, len(gdates) - 1)
        if ei < 0 or xi <= ei:
            continue
        # session validity: FOMC date must map to a real trading day at/just after ev
        sess_gap_days = (pd.Timestamp(gdates[i]) - ev).days
        # window contiguity (no >3d gap) and roll-stitch inside [ei..xi]
        win_dates = gdates[ei:xi + 1]
        win_diffs = [(pd.Timestamp(win_dates[k]) - pd.Timestamp(win_dates[k - 1])).days for k in range(1, len(win_dates))]
        has_gap = any(dd > 4 for dd in win_diffs)
        roll_in_win = any((ei < r <= xi) for r in roll_idx)
        # rebuild trade (long, $1200 stop)
        entry = c[ei]; sp = entry - STOP / pv; lo = g["l"].values; exit_px = None
        for j in range(ei + 1, xi + 1):
            if lo[j] <= sp:
                exit_px = sp; break
        if exit_px is None:
            exit_px = c[xi]
        pnl = (exit_px - entry) * pv - rt
        yr = pd.Timestamp(gdates[ei]).year
        rec = {"pnl": pnl, "year": yr}
        sigvals.append(round(float(exit_px - entry), 5))
        raw_tr.append(rec)
        contam = has_gap or roll_in_win or sess_gap_days > 4
        if contam:
            contaminated.append({"fomc": str(ev.date()), "has_gap": has_gap, "roll_in_win": roll_in_win,
                                 "sess_gap_days": sess_gap_days})
        else:
            clean_tr.append(rec)
        win_audit.append({"fomc": str(ev.date()), "entry": str(win_dates[0]), "exit": str(win_dates[-1]),
                          "contaminated": contam})

    def m(trs):
        if not trs:
            return {"n": 0}
        p = np.array([t["pnl"] for t in trs]); yrs = np.array([t["year"] for t in trs])
        yn = {int(y): float(p[yrs == y].sum()) for y in set(yrs)}; pos = sum(v for v in yn.values() if v > 0)
        return {"n": len(p), "pf": round(_pf(p), 3), "expectancy": round(float(p.mean()), 2),
                "median": round(float(np.median(p)), 2), "largest_loss": round(float(p.min()), 2),
                "maxyr": round(100 * max(yn.values()) / pos, 1) if pos > 0 else 0.0}
    raw_m, clean_m = m(raw_tr), m(clean_tr)
    sig_hash = hashlib.sha256(np.array(sigvals).tobytes()).hexdigest()[:16]
    print(f"\n4. WINDOWS: {len(raw_tr)} total | contaminated (gap/roll/session) = {len(contaminated)}", flush=True)
    for cc in contaminated[:8]:
        print(f"     contaminated: {cc}", flush=True)
    print(f"   RAW rebuild:   n={raw_m['n']} PF={raw_m['pf']} exp=${raw_m['expectancy']} med=${raw_m['median']} "
          f"largest=${raw_m['largest_loss']} maxyr={raw_m['maxyr']}% sig_hash={sig_hash}", flush=True)
    print(f"   CLEAN rebuild: n={clean_m['n']} PF={clean_m['pf']} exp=${clean_m['expectancy']} med=${clean_m['median']} "
          f"largest=${clean_m['largest_loss']} maxyr={clean_m['maxyr']}%", flush=True)

    # ---- 5. reconcile to packet ----
    recon = {k: {"packet": PKT[k], "rebuilt": raw_m.get(k if k != "maw" else "largest_loss")} for k in ("pf", "expectancy", "median", "n", "largest_loss", "maxyr")}
    matches = (raw_m["pf"] == PKT["pf"] and raw_m["n"] == PKT["n"]
               and abs(raw_m["expectancy"] - PKT["expectancy"]) < 1 and abs(raw_m["median"] - PKT["median"]) < 1
               and abs(raw_m["largest_loss"] - PKT["largest_loss"]) < 1)
    print(f"\n5. PACKET RECONCILE: rebuilt vs packet match = {matches}", flush=True)
    if not matches:
        print(f"   MISMATCH: rebuilt PF={raw_m['pf']} exp={raw_m['expectancy']} n={raw_m['n']} vs packet {PKT}", flush=True)

    # ---- verdict ----
    edge_survives_clean = (clean_m.get("pf", 0) >= 1.3 and clean_m.get("expectancy", 0) > 0
                           and clean_m.get("maxyr", 100) <= 55 and clean_m["n"] >= 0.7 * raw_m["n"])
    if not matches:
        verdict = "DATA_AUDIT_YELLOW — packet/source reconciliation mismatch (reconcile before advancing)"
    elif integ["duplicate_ts"] > 0 or not integ["monotonic"]:
        verdict = "DATA_AUDIT_RED — ZN file integrity failure (dupes/non-monotonic)"
    elif len(contaminated) > 0 and not edge_survives_clean:
        verdict = "DATA_AUDIT_RED — edge does not survive clean-events (roll/gap contamination)"
    elif len(contaminated) > 0 and edge_survives_clean:
        verdict = f"DATA_AUDIT_YELLOW — {len(contaminated)} contaminated window(s) but edge survives clean (clean PF {clean_m['pf']}); document + prefer clean metrics"
    else:
        verdict = "DATA_AUDIT_GREEN — ZN feed-internally reproducible, FOMC calendar official, no window contamination, packet reconciles"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print("  (DATA_AUDIT_GREEN = feed-internal reproducibility only; external feed correctness still DSCL-gated)", flush=True)

    rep.update({"lineage": lineage, "file_integrity": integ, "fomc_calendar": cal_audit,
                "roll_stitch_candidates": len(roll_idx), "n_windows": len(raw_tr),
                "contaminated_windows": contaminated, "raw_rebuild": raw_m, "clean_rebuild": clean_m,
                "signal_hash": sig_hash, "packet_reconcile": {"match": matches, "detail": recon},
                "verdict": verdict, "boundaries": "report-only; freeze maintained; no executor/wiring/mutation"})
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16e_zn_fomc_data_audit.json"
    out.write_text(json.dumps(rep, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
