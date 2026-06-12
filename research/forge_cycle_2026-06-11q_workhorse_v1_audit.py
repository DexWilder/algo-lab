"""Cycle 2026-06-11q — V1 8-dim audit + family review for the 2 daily
workhorse PAPER_PACKET_CANDIDATEs from cycle 11p.

Per operator #176 amended trigger: candidates reached PAPER_PACKET_CANDIDATE.

Candidates:
  1. WH-MNQ-range_compression_break-ema_slope-PL (PF 1.370, n=1244)
  2. WH-MNQ-stop_run_reversal-ema_slope-PL (PF 1.477, n=1414)

CRITICAL family review checks:
  - vs XB-ORB-EMA-Ladder-MNQ probation (SAME ASSET, SAME FILTER, SAME EXIT —
    only entry differs; expect significant correlation)
  - vs FOMC-MNQ-Long-1h (tail-engine event-window)
  - vs Packet #1 archive (NFP-MGC)
  - vs BBKC-MNQ archive (same asset)
  - pairwise: range_compression_break vs stop_run_reversal

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def strict_filter(events, df, max_gap_minutes=60):
    df_dt = pd.to_datetime(df["datetime"])
    clean = []
    for ev in events:
        if ev < df_dt.iloc[0]: continue
        after = df[df_dt > ev].head(1)
        if len(after) == 0: continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes: clean.append(ev)
    return clean


def _run_xb(asset, entry, exit_name, filter_name, label, cost_mult=1.0, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name,
                                       filter_name=filter_name, params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    sig_hash = hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16]
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"], sig_hash


def _run_event(asset, events, exit_bars, direction, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(df, events=events, entry_offset_bars=1,
                                          exit_offset_bars=exit_bars, direction=direction)
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def family_review(trades_a, trades_b):
    if trades_a.empty or trades_b.empty: return None
    da = trades_a.copy(); da["entry_dt"] = pd.to_datetime(da["entry_time"]); da["date"] = da["entry_dt"].dt.date
    db = trades_b.copy(); db["entry_dt"] = pd.to_datetime(db["entry_time"]); db["date"] = db["entry_dt"].dt.date
    pa = da.groupby("date")["pnl"].sum()
    pb = db.groupby("date")["pnl"].sum()
    aligned = pd.concat([pa, pb], axis=1, keys=["a", "b"]).fillna(0.0)
    corr = float(aligned["a"].corr(aligned["b"]))
    days_a = set(da["date"]); days_b = set(db["date"])
    overlap = days_a & days_b
    overlap_pct_a = len(overlap) / len(days_a) * 100 if days_a else 0
    if overlap:
        pa_ov = pa[pa.index.isin(overlap)]; pb_ov = pb[pb.index.isin(overlap)]
        aligned_ov = pd.concat([pa_ov, pb_ov], axis=1, keys=["a", "b"]).fillna(0.0)
        corr_ov = float(aligned_ov["a"].corr(aligned_ov["b"]))
    else:
        corr_ov = float("nan")
    if corr > 0.7 and overlap_pct_a > 80:
        cls = "DUPLICATE_EXPOSURE_REJECT"
    elif corr > 0.5:
        cls = "PORTFOLIO_COMPLEMENT (moderate corr)"
    elif corr > 0.3:
        cls = "PORTFOLIO_COMPLEMENT (low-moderate corr)"
    else:
        cls = "INDEPENDENT (corr < 0.30)"
    return {
        "n_days_a": len(days_a), "n_days_b": len(days_b),
        "n_days_overlap": len(overlap),
        "overlap_pct_of_a": overlap_pct_a,
        "daily_pnl_corr": corr,
        "overlap_day_pnl_corr": corr_ov,
        "classification": cls,
    }


def audit_workhorse(entry, label):
    print(f"\n=== V1 8-DIM AUDIT: {label} ===\n", flush=True)
    asset = "MNQ"
    m, trades, hash1 = _run_xb(asset, entry, "profit_ladder", "ema_slope", label)
    _, _, hash2 = _run_xb(asset, entry, "profit_ladder", "ema_slope", label + "-rerun")
    m_stress, _, _ = _run_xb(asset, entry, "profit_ladder", "ema_slope",
                              label + "-stress", cost_mult=2.0, slip_mult=3.0)

    # Quick gates
    print(f"  Baseline n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    print(f"  Stress (2x+2t): PF={m_stress['pf']:.3f} median=${m_stress['median']:.2f}", flush=True)
    print(f"  Win rate: {(trades['pnl']>0).mean()*100:.1f}%", flush=True)
    print(f"  Signal hash: {hash1} == {hash2}: {hash1 == hash2}", flush=True)

    # Family review
    print(f"\n  Family review:", flush=True)
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    df_mnq = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    # vs XB-ORB-MNQ probation (CRITICAL — same asset, same filter, same exit)
    _, t_orb_mnq, _ = _run_xb("MNQ", "orb_breakout", "profit_ladder", "ema_slope", "XB-ORB-MNQ")
    fam_orb = family_review(trades, t_orb_mnq)
    # vs FOMC-MNQ-Long-1h
    fomc_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                   for c in build_official_fomc_calendar()]
    fomc_clean = strict_filter(fomc_events, df_mnq)
    _, t_fomc = _run_event("MNQ", fomc_clean, 12, "long", "FOMC-MNQ-Long-1h")
    fam_fomc = family_review(trades, t_fomc)
    # vs Packet #1 archive (NFP-MGC)
    df_mgc = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]
    nfp_clean = strict_filter(nfp_events, df_mgc)
    _, t_packet1 = _run_event("MGC", nfp_clean, 24, "long", "NFP-MGC")
    fam_packet1 = family_review(trades, t_packet1)
    # vs BBKC-MNQ archive
    _, t_bbkc, _ = _run_xb("MNQ", "bb_keltner_squeeze", "profit_ladder", "ema_slope", "BBKC-MNQ")
    fam_bbkc = family_review(trades, t_bbkc)
    print(f"    vs XB-ORB-MNQ probation: corr={fam_orb['daily_pnl_corr']:+.3f} overlap={fam_orb['overlap_pct_of_a']:.1f}% → {fam_orb['classification']}", flush=True)
    print(f"    vs FOMC-MNQ-Long-1h:     corr={fam_fomc['daily_pnl_corr']:+.3f} overlap={fam_fomc['overlap_pct_of_a']:.1f}% → {fam_fomc['classification']}", flush=True)
    print(f"    vs Packet #1 NFP-MGC:    corr={fam_packet1['daily_pnl_corr']:+.3f} overlap={fam_packet1['overlap_pct_of_a']:.1f}% → {fam_packet1['classification']}", flush=True)
    print(f"    vs BBKC-MNQ archive:     corr={fam_bbkc['daily_pnl_corr']:+.3f} overlap={fam_bbkc['overlap_pct_of_a']:.1f}% → {fam_bbkc['classification']}", flush=True)

    # Family verdict — XB-ORB is the critical one
    if "DUPLICATE" in fam_orb["classification"]:
        family_verdict = "DUPLICATE_EXPOSURE_REJECT vs XB-ORB-MNQ probation"
    elif "PORTFOLIO_COMPLEMENT" in fam_orb["classification"]:
        family_verdict = f"PORTFOLIO_COMPLEMENT vs XB-ORB-MNQ probation ({fam_orb['classification']})"
    else:
        family_verdict = "INDEPENDENT (clean of all existing candidates)"
    print(f"  Family verdict: {family_verdict}", flush=True)

    return {
        "label": label, "asset": asset, "entry": entry,
        "baseline": {"n": int(m["n"]), "pf": float(m["pf"]), "median": float(m["median"]),
                     "net": float(m["net"]), "win_rate": float((trades["pnl"]>0).mean())},
        "stress": {"pf": float(m_stress["pf"]), "median": float(m_stress["median"])},
        "reproducible": hash1 == hash2,
        "family_review": {
            "vs_XB_ORB_MNQ_probation": fam_orb,
            "vs_FOMC_MNQ_Long_1h": fam_fomc,
            "vs_Packet1_NFP_MGC_archive": fam_packet1,
            "vs_BBKC_MNQ_archive": fam_bbkc,
        },
        "family_verdict": family_verdict,
        "trades_for_pairwise": trades,
    }


def run():
    print("Cycle 2026-06-11q — Daily workhorse V1 8-dim audit + family review", flush=True)
    print("Per #176 trigger.\n", flush=True)
    t_start = time.time()

    audit1 = audit_workhorse("range_compression_break", "WH-MNQ-range_compression_break")
    audit2 = audit_workhorse("stop_run_reversal", "WH-MNQ-stop_run_reversal")

    # CRITICAL pairwise check between the 2 workhorse candidates
    print(f"\n=== PAIRWISE: range_compression_break vs stop_run_reversal ===", flush=True)
    fam_pair = family_review(audit1["trades_for_pairwise"], audit2["trades_for_pairwise"])
    print(f"  corr={fam_pair['daily_pnl_corr']:+.3f} overlap={fam_pair['overlap_pct_of_a']:.1f}% → {fam_pair['classification']}", flush=True)

    # Strip trades for serialization
    for a in (audit1, audit2):
        a.pop("trades_for_pairwise", None)

    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11q_workhorse_v1_audit.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Daily workhorse V1 8-dim audit + family review per #176 amended trigger",
        "audits": [audit1, audit2],
        "pairwise_workhorse_review": fam_pair,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
