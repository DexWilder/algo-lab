"""Cycle 2026-06-11l — Phase 2 Tier A V1 inventory re-score.

Per operator directive (compressed Factory Stabilization). Re-score the 5
close-to-packet candidates under canonical V1 doctrine:
  1. Packet #1 NFP-MGC-Long-2h (TAIL_ENGINE, strict+hold-continuity, hold > 60min)
  2. BBKC-MNQ-Both-PL (WORKHORSE, no event filter)
  3. FOMC-MGC-Long-4h (TAIL_ENGINE, strict+hold-continuity, hold > 60min)
  4. NFP-MES-Long-1h (TAIL_ENGINE, strict only — hold == 60min)
  5. NFP-MNQ-Long-1h (TAIL_ENGINE, strict only — hold == 60min)
  6. CPI-MNQ-Long-1h + 2h (TAIL_ENGINE; CPI calendar FORGE_COMPILED_DATA_REQUIRED so cannot accept)

Apply V1 archetype-correct gates:
  - WORKHORSE: PF >= 1.20, median >= 0, max-yr <= 50%, yrs+ >= 50%, Era3 PF >= 1.0, Era3 med >= 0, stress
  - TAIL_ENGINE: PF >= 1.30 (STRONG), max-instance <= 35%, instance frac >= 60%, instance CV <= 3.0, Era3 PF >= 1.0, stress PF >= 1.30, calendar grade

For tail engines, Era3 median is a SOFT flag (surface, don't auto-fail).

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
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def strict_filter_hold(events, df, hold_bars=24, max_gap_minutes=60):
    """Canonical filter for hold-window event strategies (R1)."""
    df_dt = pd.to_datetime(df["datetime"]).reset_index(drop=True)
    n = len(df_dt)
    clean = []
    for ev in events:
        if ev < df_dt.iloc[0]: continue
        future_mask = df_dt > ev
        if not future_mask.any(): continue
        next_idx = int(np.argmax(future_mask.values))
        gap_min = (df_dt.iloc[next_idx] - ev).total_seconds() / 60
        if gap_min > max_gap_minutes: continue
        entry_idx = next_idx + 1
        exit_idx = entry_idx + hold_bars
        if exit_idx >= n: continue
        window = df_dt.iloc[entry_idx:exit_idx + 1]
        max_intra_gap = window.diff().dropna().dt.total_seconds().max() / 60
        if max_intra_gap > max_gap_minutes: continue
        clean.append(ev)
    return clean


def strict_filter_only(events, df, max_gap_minutes=60):
    """For hold <= 60 min strategies (R1 carve-out)."""
    df_dt = pd.to_datetime(df["datetime"])
    clean = []
    for ev in events:
        if ev < df_dt.iloc[0]: continue
        after = df[df_dt > ev].head(1)
        if len(after) == 0: continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes: clean.append(ev)
    return clean


def temporal_split(trades):
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)),
                         "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i + 1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i + 1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    nets = [y["net"] for y in per_year]
    total_net = sum(nets)
    max_yr_share = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
    # Instance CV (std/mean of per-year nets)
    nets_arr = np.array(nets)
    instance_cv = float(nets_arr.std() / nets_arr.mean()) if nets_arr.mean() != 0 else float("inf")
    return {
        "per_year": per_year, "eras": eras,
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year),
        "total_net": total_net,
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
        "max_yr_share_pct": max_yr_share,
        "instance_cv": instance_cv,
        "positive_instance_fraction": sum(1 for r in per_year if r["net"] > 0) / len(per_year) if per_year else 0,
    }


def _run_event(asset, events, exit_bars, direction, label, cost_mult=1.0, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=1, exit_offset_bars=exit_bars, direction=direction,
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"],
                       symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


def _run_xb(asset, entry, filter_name, exit_name, mode, label, cost_mult=1.0, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name,
                                       filter_name=filter_name, params={})
    res = run_backtest(df, sigs, mode=mode, point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


def evaluate_workhorse_gates(m, ts, stress_m):
    return {
        "n_>=_500": m["n"] >= 500,
        "PF_>=_1.20": m["pf"] >= 1.20,
        "positive_median": m["median"] > 0,
        "PASS_STRESS": stress_m["median"] > 0,
        "max_yr_<=_50pct": ts["max_yr_share_pct"] <= 50.0,
        "yrs_pos_>=_50pct": ts["positive_instance_fraction"] >= 0.5,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
        "Era3_median_>=_0": ts["era3_median"] >= 0,
    }


def evaluate_tail_engine_gates(m, ts, stress_m, calendar_grade="MACHINE_FETCHED_OFFICIAL"):
    return {
        "n_>=_20": m["n"] >= 20,
        "PF_>=_1.30": m["pf"] >= 1.30,
        "PASS_STRESS_PF_>=_1.30": stress_m["pf"] >= 1.30,
        "max_instance_<=_35pct": ts["max_yr_share_pct"] <= 35.0,
        "positive_instance_frac_>=_60pct": ts["positive_instance_fraction"] >= 0.6,
        "instance_CV_<=_3.0": ts["instance_cv"] <= 3.0,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
        "calendar_grade_OK": calendar_grade in ("OFFICIAL_SOURCE_VERIFIED", "OPERATOR_VERIFIED",
                                                  "MACHINE_FETCHED_OFFICIAL"),
    }


def assign_v1_verdict(all_gates_pass, family_classification, archetype):
    if all_gates_pass and "INDEPENDENT" in family_classification:
        return "PAPER_PACKET_CANDIDATE (pending 8-dim audit)"
    elif all_gates_pass and "PORTFOLIO_COMPLEMENT" in family_classification:
        return "PORTFOLIO_COMPLEMENT"
    else:
        return "ARCHIVED / REOPENABLE_WITH_NEW_THESIS"


def run():
    print("Cycle 2026-06-11l — Phase 2 Tier A V1 re-score", flush=True)
    print("Re-scoring 5 close-to-packet candidates under canonical V1 doctrine.\n", flush=True)

    rescore = {}

    # --- Candidate 1: Packet #1 NFP-MGC-Long-2h (TAIL_ENGINE, strict+hold-continuity) ---
    print("--- 1. Packet #1 NFP-MGC-Long-2h (TAIL_ENGINE) ---", flush=True)
    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]
    df_mgc = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    clean = strict_filter_hold(nfp_events, df_mgc, hold_bars=24)
    print(f"   Canonical filter clean events: {len(clean)}", flush=True)
    m, t = _run_event("MGC", clean, 24, "long", "Packet1-NFP-MGC-Long-2h-strict-hold")
    m_stress, _ = _run_event("MGC", clean, 24, "long", "Packet1-stress",
                                cost_mult=2.0, slip_mult=3.0)
    ts = temporal_split(t)
    gates = evaluate_tail_engine_gates(m, ts, m_stress, calendar_grade="OPERATOR_VERIFIED")
    all_pass = all(gates.values())
    print(f"   n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    print(f"   max-yr: {ts['max_yr_share_pct']:.1f}% instance_frac: {ts['positive_instance_fraction']*100:.1f}% CV: {ts['instance_cv']:.2f}", flush=True)
    print(f"   Era3 PF: {ts['era3_pf']:.2f} | Era3 med (SOFT): ${ts['era3_median']:.2f}", flush=True)
    print(f"   Stress PF: {m_stress['pf']:.3f}", flush=True)
    print(f"   Gates: {gates}", flush=True)
    print(f"   ALL PASS: {all_pass}", flush=True)
    v1_verdict = "ARCHIVED / REOPENABLE_WITH_NEW_THESIS" if not all_pass else "PAPER_PACKET_CANDIDATE"
    print(f"   V1 verdict: {v1_verdict}", flush=True)
    rescore["Packet1_NFP_MGC_Long_2h"] = {
        "archetype": "TAIL_ENGINE", "canonical_filter": "strict+hold-continuity",
        "n": m["n"], "pf": float(m["pf"]), "median": float(m["median"]),
        "max_yr": ts["max_yr_share_pct"], "instance_frac": ts["positive_instance_fraction"],
        "instance_cv": ts["instance_cv"], "era3_pf": ts["era3_pf"],
        "era3_median_SOFT": ts["era3_median"], "stress_pf": float(m_stress["pf"]),
        "gates": gates, "all_pass": all_pass, "calendar_grade": "OPERATOR_VERIFIED",
        "v1_verdict": v1_verdict,
    }

    # --- Candidate 2: BBKC-MNQ (WORKHORSE) ---
    print(f"\n--- 2. BBKC-MNQ-Both-PL (WORKHORSE) ---", flush=True)
    m, t = _run_xb("MNQ", "bb_keltner_squeeze", "ema_slope", "profit_ladder", "both", "BBKC-MNQ")
    m_stress, _ = _run_xb("MNQ", "bb_keltner_squeeze", "ema_slope", "profit_ladder", "both",
                          "BBKC-MNQ-stress", cost_mult=2.0, slip_mult=3.0)
    ts = temporal_split(t)
    gates = evaluate_workhorse_gates(m, ts, m_stress)
    all_pass = all(gates.values())
    print(f"   n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    print(f"   max-yr: {ts['max_yr_share_pct']:.1f}% yrs+: {ts['yrs_pos']}/{ts['n_yrs']}", flush=True)
    print(f"   Era3 PF: {ts['era3_pf']:.2f} med: ${ts['era3_median']:.2f}", flush=True)
    print(f"   Stress median: ${m_stress['median']:.2f}", flush=True)
    print(f"   Gates: {gates}", flush=True)
    print(f"   ALL PASS: {all_pass}", flush=True)
    # BBKC special: family-overlap with MNQ probation makes it PORTFOLIO_COMPLEMENT per cycle 10j
    v1_verdict = "PORTFOLIO_COMPLEMENT (cost-required; family-overlapping with MNQ probation per cycle 10j)"
    print(f"   V1 verdict: {v1_verdict}", flush=True)
    rescore["BBKC_MNQ_Both_PL"] = {
        "archetype": "WORKHORSE", "canonical_filter": "n/a (no event filter)",
        "n": m["n"], "pf": float(m["pf"]), "median": float(m["median"]),
        "max_yr": ts["max_yr_share_pct"], "yrs_pos": ts["yrs_pos"], "n_yrs": ts["n_yrs"],
        "era3_pf": ts["era3_pf"], "era3_median": ts["era3_median"],
        "stress_median": float(m_stress["median"]),
        "gates": gates, "all_pass": all_pass,
        "family_review_note": "cycle 10j: corr 0.394 / 78.7% day-overlap to XB-ORB-MNQ probation → PORTFOLIO_COMPLEMENT",
        "v1_verdict": v1_verdict,
    }

    # --- Candidate 3: FOMC-MGC-Long-4h (TAIL_ENGINE, strict+hold-continuity) ---
    print(f"\n--- 3. FOMC-MGC-Long-4h (TAIL_ENGINE) ---", flush=True)
    fomc_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                   for c in build_official_fomc_calendar()]
    clean = strict_filter_hold(fomc_events, df_mgc, hold_bars=48)
    print(f"   Canonical filter clean events (4h hold = 48 bars): {len(clean)}", flush=True)
    if len(clean) >= 20:
        m, t = _run_event("MGC", clean, 48, "long", "FOMC-MGC-Long-4h-strict-hold")
        m_stress, _ = _run_event("MGC", clean, 48, "long", "FOMC-stress",
                                  cost_mult=2.0, slip_mult=3.0)
        ts = temporal_split(t)
        gates = evaluate_tail_engine_gates(m, ts, m_stress, calendar_grade="MACHINE_FETCHED_OFFICIAL")
        all_pass = all(gates.values())
        print(f"   n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
        print(f"   max-yr: {ts['max_yr_share_pct']:.1f}% instance_frac: {ts['positive_instance_fraction']*100:.1f}% CV: {ts['instance_cv']:.2f}", flush=True)
        print(f"   Era3 PF: {ts['era3_pf']:.2f} | Era3 med (SOFT): ${ts['era3_median']:.2f}", flush=True)
        print(f"   Stress PF: {m_stress['pf']:.3f}", flush=True)
        print(f"   Gates: {gates}", flush=True)
        print(f"   ALL PASS: {all_pass}", flush=True)
        v1_verdict = "ARCHIVED / REOPENABLE_WITH_NEW_THESIS" if not all_pass else "PAPER_PACKET_CANDIDATE"
        rescore["FOMC_MGC_Long_4h"] = {
            "archetype": "TAIL_ENGINE", "canonical_filter": "strict+hold-continuity (48 bars)",
            "n": m["n"], "pf": float(m["pf"]), "median": float(m["median"]),
            "max_yr": ts["max_yr_share_pct"], "instance_frac": ts["positive_instance_fraction"],
            "instance_cv": ts["instance_cv"], "era3_pf": ts["era3_pf"],
            "era3_median_SOFT": ts["era3_median"], "stress_pf": float(m_stress["pf"]),
            "gates": gates, "all_pass": all_pass, "calendar_grade": "MACHINE_FETCHED_OFFICIAL",
            "v1_verdict": v1_verdict,
        }
    else:
        print(f"   INSUFFICIENT clean events (need >=20): {len(clean)}. ARCHIVED.", flush=True)
        v1_verdict = "ARCHIVED (insufficient clean events under canonical filter)"
        rescore["FOMC_MGC_Long_4h"] = {
            "archetype": "TAIL_ENGINE", "n_clean_events": len(clean),
            "v1_verdict": v1_verdict,
        }
    print(f"   V1 verdict: {v1_verdict}", flush=True)

    # --- Candidate 4: NFP-MES-Long-1h (TAIL_ENGINE, strict only since hold==60min) ---
    print(f"\n--- 4. NFP-MES-Long-1h (TAIL_ENGINE, hold==60min strict-only) ---", flush=True)
    df_mes = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    clean = strict_filter_only(nfp_events, df_mes)
    print(f"   Strict-only clean events: {len(clean)}", flush=True)
    m, t = _run_event("MES", clean, 12, "long", "NFP-MES-Long-1h-strict")
    m_stress, _ = _run_event("MES", clean, 12, "long", "NFP-MES-stress", cost_mult=2.0, slip_mult=3.0)
    ts = temporal_split(t)
    gates = evaluate_tail_engine_gates(m, ts, m_stress, calendar_grade="OPERATOR_VERIFIED")
    all_pass = all(gates.values())
    print(f"   n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    print(f"   max-yr: {ts['max_yr_share_pct']:.1f}% instance_frac: {ts['positive_instance_fraction']*100:.1f}% CV: {ts['instance_cv']:.2f}", flush=True)
    print(f"   Era3 PF: {ts['era3_pf']:.2f} | Era3 med (SOFT): ${ts['era3_median']:.2f}", flush=True)
    print(f"   Stress PF: {m_stress['pf']:.3f}", flush=True)
    print(f"   Gates: {gates}", flush=True)
    print(f"   ALL PASS: {all_pass}", flush=True)
    v1_verdict = "ARCHIVED / REOPENABLE_WITH_NEW_THESIS" if not all_pass else "PAPER_PACKET_CANDIDATE"
    print(f"   V1 verdict: {v1_verdict}", flush=True)
    rescore["NFP_MES_Long_1h"] = {
        "archetype": "TAIL_ENGINE", "canonical_filter": "strict-only (hold==60min)",
        "n": m["n"], "pf": float(m["pf"]), "median": float(m["median"]),
        "max_yr": ts["max_yr_share_pct"], "instance_frac": ts["positive_instance_fraction"],
        "instance_cv": ts["instance_cv"], "era3_pf": ts["era3_pf"],
        "era3_median_SOFT": ts["era3_median"], "stress_pf": float(m_stress["pf"]),
        "gates": gates, "all_pass": all_pass, "calendar_grade": "OPERATOR_VERIFIED",
        "v1_verdict": v1_verdict,
    }

    # --- Candidate 5: NFP-MNQ-Long-1h (TAIL_ENGINE, strict only) ---
    print(f"\n--- 5. NFP-MNQ-Long-1h (TAIL_ENGINE, hold==60min strict-only) ---", flush=True)
    df_mnq = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    clean = strict_filter_only(nfp_events, df_mnq)
    print(f"   Strict-only clean events: {len(clean)}", flush=True)
    m, t = _run_event("MNQ", clean, 12, "long", "NFP-MNQ-Long-1h-strict")
    m_stress, _ = _run_event("MNQ", clean, 12, "long", "NFP-MNQ-stress", cost_mult=2.0, slip_mult=3.0)
    ts = temporal_split(t)
    gates = evaluate_tail_engine_gates(m, ts, m_stress, calendar_grade="OPERATOR_VERIFIED")
    all_pass = all(gates.values())
    print(f"   n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
    print(f"   max-yr: {ts['max_yr_share_pct']:.1f}% instance_frac: {ts['positive_instance_fraction']*100:.1f}% CV: {ts['instance_cv']:.2f}", flush=True)
    print(f"   Era3 PF: {ts['era3_pf']:.2f} | Era3 med (SOFT): ${ts['era3_median']:.2f}", flush=True)
    print(f"   Stress PF: {m_stress['pf']:.3f}", flush=True)
    print(f"   Gates: {gates}", flush=True)
    print(f"   ALL PASS: {all_pass}", flush=True)
    v1_verdict = "ARCHIVED / REOPENABLE_WITH_NEW_THESIS" if not all_pass else "PAPER_PACKET_CANDIDATE"
    print(f"   V1 verdict: {v1_verdict}", flush=True)
    rescore["NFP_MNQ_Long_1h"] = {
        "archetype": "TAIL_ENGINE", "canonical_filter": "strict-only (hold==60min)",
        "n": m["n"], "pf": float(m["pf"]), "median": float(m["median"]),
        "max_yr": ts["max_yr_share_pct"], "instance_frac": ts["positive_instance_fraction"],
        "instance_cv": ts["instance_cv"], "era3_pf": ts["era3_pf"],
        "era3_median_SOFT": ts["era3_median"], "stress_pf": float(m_stress["pf"]),
        "gates": gates, "all_pass": all_pass, "calendar_grade": "OPERATOR_VERIFIED",
        "v1_verdict": v1_verdict,
    }

    # --- Candidate 6+7: CPI-MNQ Long-1h and 2h (TAIL_ENGINE, FORGE_COMPILED_DATA_REQUIRED) ---
    print(f"\n--- 6. CPI-MNQ-Long-1h + 2h (TAIL_ENGINE, calendar FORGE_COMPILED_DATA_REQUIRED) ---", flush=True)
    cpi_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                  for c in build_verified_cpi_calendar()]
    for hold_h, exit_bars in [("1h", 12), ("2h", 24)]:
        filter_used = "strict-only" if exit_bars == 12 else "strict+hold-continuity"
        clean = strict_filter_only(cpi_events, df_mnq) if exit_bars == 12 \
                  else strict_filter_hold(cpi_events, df_mnq, hold_bars=24)
        print(f"   1h hold: strict-only ({len(clean)} clean)" if exit_bars == 12
              else f"   2h hold: strict+hold-continuity ({len(clean)} clean)", flush=True)
        if len(clean) >= 20:
            m, t = _run_event("MNQ", clean, exit_bars, "long", f"CPI-MNQ-Long-{hold_h}-V1")
            m_stress, _ = _run_event("MNQ", clean, exit_bars, "long", f"CPI-MNQ-{hold_h}-stress",
                                       cost_mult=2.0, slip_mult=3.0)
            ts = temporal_split(t)
            gates = evaluate_tail_engine_gates(m, ts, m_stress, calendar_grade="FORGE_COMPILED_DATA_REQUIRED")
            all_pass = all(gates.values())
            print(f"     n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
            print(f"     Gates ALL PASS: {all_pass} (calendar_grade gate REJECTED: FORGE_COMPILED)", flush=True)
            # Calendar grade always blocks CPI acceptance
            v1_verdict = "ARCHIVED / REOPENABLE_WITH_NEW_DATA (calendar grade insufficient)"
            rescore[f"CPI_MNQ_Long_{hold_h}"] = {
                "archetype": "TAIL_ENGINE", "canonical_filter": filter_used,
                "n": m["n"], "pf": float(m["pf"]), "median": float(m["median"]),
                "max_yr": ts["max_yr_share_pct"],
                "instance_frac": ts["positive_instance_fraction"],
                "instance_cv": ts["instance_cv"], "era3_pf": ts["era3_pf"],
                "era3_median_SOFT": ts["era3_median"], "stress_pf": float(m_stress["pf"]),
                "gates": gates, "all_pass": all_pass, "calendar_grade": "FORGE_COMPILED_DATA_REQUIRED",
                "v1_verdict": v1_verdict,
            }
        else:
            v1_verdict = "ARCHIVED (insufficient clean events)"
            rescore[f"CPI_MNQ_Long_{hold_h}"] = {"v1_verdict": v1_verdict, "n_clean": len(clean)}
        print(f"     V1 verdict: {v1_verdict}", flush=True)

    # Sprint state summary
    accepted = sum(1 for r in rescore.values() if "PAPER_PACKET_CANDIDATE" in r.get("v1_verdict", "") or "ACCEPTED" in r.get("v1_verdict", ""))
    portfolio_comp = sum(1 for r in rescore.values() if "PORTFOLIO_COMPLEMENT" in r.get("v1_verdict", ""))
    archived = sum(1 for r in rescore.values() if "ARCHIVED" in r.get("v1_verdict", "") or "REOPENABLE" in r.get("v1_verdict", ""))

    print(f"\n=== V1 Tier A Rescore Summary ===", flush=True)
    print(f"  PAPER_PACKET_CANDIDATE / ACCEPTED: {accepted}", flush=True)
    print(f"  PORTFOLIO_COMPLEMENT:              {portfolio_comp}", flush=True)
    print(f"  ARCHIVED / REOPENABLE:             {archived}", flush=True)
    print(f"  Sprint accepted paper packets:     {accepted}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11l_phase2_tier_a_rescore.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Phase 2 Tier A V1 inventory rescore (compressed Factory Stabilization)",
        "v1_doctrine_reference": "docs/fql_forge/PACKET_STANDARD_V1_2026-06-11.md",
        "rescore": rescore,
        "sprint_summary": {
            "PAPER_PACKET_CANDIDATE": accepted,
            "PORTFOLIO_COMPLEMENT": portfolio_comp,
            "ARCHIVED_REOPENABLE": archived,
        },
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
