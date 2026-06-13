"""Cycle 2026-06-12l — Event-conditioning batch on 3 GREEN Lane A candidates.

Per operator #208 A. 9-test build per methodology
(docs/fql_forge/event_conditioning_methodology_2026-06-12.md).

Candidates:
  1. WH-MNQ-stop_run_reversal
  2. WH-MNQ-first_impulse_pullback
  3. WH-MNQ-range_compression_break

Variants (pre-declared):
  V0 baseline (no exclusion)
  V1 FOMC only excluded
  V2 NFP only excluded
  V3 FOMC + NFP combined

Decision standard:
  - Risk improves + edge preserved → GREEN refinement / packet appendix
  - PF improves but kills sample / concentration → OBSERVATIONAL
  - No risk improvement, no edge change → ARCHIVE FILTER
  - Damages edge → ARCHIVE FILTER

Reporting (per operator):
  Lead with risk-cleanliness, not PF. Explicit Tradeify $2K/$3K DD,
  H1/H2, Era 3 PF, single-day loss, concentration.

Final line per candidate: "Should this change the Lane A packet?"

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _pf(pnl):
    arr = np.asarray(pnl)
    w = arr[arr > 0].sum(); l = -arr[arr < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def get_event_dates():
    """Return sets of NFP and FOMC dates."""
    nfp = {pd.to_datetime(c["actual_date"]).date()
           for c in build_verified_nfp_calendar(2019, 2026)}
    fomc = {pd.to_datetime(c["actual_date"]).date()
            for c in build_official_fomc_calendar()}
    return nfp, fomc


def filter_trades_by_excluded_dates(trades_df, excluded_dates):
    """Remove trades whose entry_date is in excluded_dates."""
    if trades_df.empty: return trades_df.copy()
    t = trades_df.copy()
    t["entry_dt"] = pd.to_datetime(t["entry_time"])
    t["entry_date"] = t["entry_dt"].dt.date
    return t[~t["entry_date"].isin(excluded_dates)].reset_index(drop=True)


def compute_intraday_risk_metrics(trades_df):
    """Compute risk metrics for intraday strategies (flat overnight)."""
    if trades_df.empty:
        return {"largest_single_day_loss": 0, "worst_trade": 0,
                "top_1_pct": 0, "top_3_pct": 0, "top_10_pct": 0,
                "max_yr_share_pct": 0, "instance_cv": 0}
    t = trades_df.copy()
    t["entry_dt"] = pd.to_datetime(t["entry_time"])
    t["date"] = t["entry_dt"].dt.date
    daily = t.groupby("date")["pnl"].sum()
    largest_single_day_loss = float(daily.min()) if len(daily) else 0
    worst_trade = float(t["pnl"].min()) if len(t) else 0
    net = float(t["pnl"].sum())
    sorted_pnl = t["pnl"].sort_values(ascending=False).reset_index(drop=True)
    top1 = float(sorted_pnl.iloc[0] / net * 100) if net != 0 and len(sorted_pnl) > 0 else 0
    top3 = float(sorted_pnl.iloc[:3].sum() / net * 100) if net != 0 and len(sorted_pnl) >= 3 else 0
    top10 = float(sorted_pnl.iloc[:10].sum() / net * 100) if net != 0 and len(sorted_pnl) >= 10 else 0
    t["year"] = t["entry_dt"].dt.year
    per_year_nets = t.groupby("year")["pnl"].sum()
    max_yr = float(per_year_nets.abs().max() / net * 100) if net != 0 else 0
    instance_cv = float(per_year_nets.std() / per_year_nets.mean()) if per_year_nets.mean() != 0 else float("inf")
    # Tradeify compat — single-day loss is the binding constraint for intraday
    tradeify_2k = abs(largest_single_day_loss) <= 2000
    tradeify_3k = abs(largest_single_day_loss) <= 3000
    return {
        "largest_single_day_loss": largest_single_day_loss,
        "worst_trade": worst_trade,
        "top_1_pct": top1, "top_3_pct": top3, "top_10_pct": top10,
        "max_yr_share_pct": max_yr, "instance_cv": instance_cv,
        "tradeify_2k_daily_dd_compatible": tradeify_2k,
        "tradeify_3k_daily_dd_compatible": tradeify_3k,
    }


def compute_perf_metrics(trades_df):
    if trades_df.empty:
        return {"n": 0, "pf": 0, "median": 0, "mean": 0, "net": 0,
                "h1_pf": 0, "h2_pf": 0, "era3_pf": 0,
                "year_excl_pf_min": 0, "year_excl_pf_max": 0}
    t = trades_df.copy()
    t["entry_dt"] = pd.to_datetime(t["entry_time"])
    pnl = t["pnl"].values
    pf = _pf(pnl); med = float(np.median(pnl)); mean = float(np.mean(pnl))
    net = float(pnl.sum())
    # H1/H2 split
    t_sorted = t.sort_values("entry_dt").reset_index(drop=True)
    mid = len(t_sorted) // 2
    h1 = t_sorted.iloc[:mid]["pnl"].values
    h2 = t_sorted.iloc[mid:]["pnl"].values
    h1_pf = _pf(h1) if len(h1) else 0
    h2_pf = _pf(h2) if len(h2) else 0
    # Era3
    cuts = np.linspace(0, len(t_sorted), 4).astype(int)
    era3 = t_sorted.iloc[cuts[2]:cuts[3]]["pnl"].values
    era3_pf = _pf(era3) if len(era3) else 0
    era3_med = float(np.median(era3)) if len(era3) else 0
    # Year excl
    t["year"] = t["entry_dt"].dt.year
    years = sorted(t["year"].unique())
    yr_excl_pfs = []
    for y in years:
        sub = t[t["year"] != y]
        yr_excl_pfs.append(_pf(sub["pnl"].values))
    return {
        "n": len(t), "pf": pf, "median": med, "mean": mean, "net": net,
        "h1_pf": h1_pf, "h2_pf": h2_pf, "era3_pf": era3_pf, "era3_median": era3_med,
        "year_excl_pf_min": min(yr_excl_pfs) if yr_excl_pfs else 0,
        "year_excl_pf_max": max(yr_excl_pfs) if yr_excl_pfs else 0,
    }


def _run_baseline(asset, entry):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]; costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name="profit_ladder",
                                       filter_name="ema_slope", params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    return res["trades_df"]


def classify_filter(baseline_perf, baseline_risk, filtered_perf, filtered_risk):
    """Per pre-declared decision standard."""
    # Edge: PF + median delta
    pf_delta = filtered_perf["pf"] - baseline_perf["pf"]
    median_delta = filtered_perf["median"] - baseline_perf["median"]
    edge_preserved = pf_delta >= -0.05 and median_delta >= -2.0
    edge_improved = pf_delta >= 0.05
    edge_damaged = pf_delta < -0.10 or filtered_perf["pf"] < 1.15

    # Risk improvement
    sdl_delta = baseline_risk["largest_single_day_loss"] - filtered_risk["largest_single_day_loss"]  # less negative = better
    tradeify_2k_improved = (not baseline_risk["tradeify_2k_daily_dd_compatible"]) and filtered_risk["tradeify_2k_daily_dd_compatible"]
    tradeify_3k_improved = (not baseline_risk["tradeify_3k_daily_dd_compatible"]) and filtered_risk["tradeify_3k_daily_dd_compatible"]
    concentration_improved = filtered_risk["top_3_pct"] < baseline_risk["top_3_pct"] - 2.0
    max_yr_improved = filtered_risk["max_yr_share_pct"] < baseline_risk["max_yr_share_pct"] - 2.0
    risk_materially_improved = tradeify_2k_improved or tradeify_3k_improved or sdl_delta > 200 or concentration_improved or max_yr_improved

    # Sample size collapse
    trade_loss_pct = (1 - filtered_perf["n"] / baseline_perf["n"]) * 100 if baseline_perf["n"] > 0 else 100
    sample_killed = trade_loss_pct > 50

    # Classification
    if edge_damaged:
        return "ARCHIVE FILTER (damages edge)", risk_materially_improved
    if risk_materially_improved and edge_preserved:
        return "GREEN refinement / packet appendix", True
    if edge_improved and not risk_materially_improved:
        if sample_killed:
            return "OBSERVATIONAL (PF improves but sample killed)", False
        return "OBSERVATIONAL (PF improves, risk unchanged)", False
    if not risk_materially_improved:
        return "ARCHIVE FILTER (no risk improvement, no edge change)", False
    return "OBSERVATIONAL (mixed signals)", risk_materially_improved


def run():
    print("Cycle 2026-06-12l — Event-conditioning batch on 3 GREEN Lane A candidates\n", flush=True)
    print("Per operator #208 A. Methodology: risk-cleanliness audit FIRST, not PF chasing.\n", flush=True)
    t_start = time.time()

    # Pre-compute event dates
    nfp_dates, fomc_dates = get_event_dates()
    print(f"Event dates: NFP {len(nfp_dates)}, FOMC {len(fomc_dates)}, combined {len(nfp_dates | fomc_dates)}", flush=True)

    candidates = [
        ("MNQ", "stop_run_reversal", "WH-MNQ-stop_run_reversal"),
        ("MNQ", "first_impulse_pullback", "WH-MNQ-first_impulse_pullback"),
        ("MNQ", "range_compression_break", "WH-MNQ-range_compression_break"),
    ]

    all_results = {}

    for asset, entry, label in candidates:
        print(f"\n{'='*80}\n=== {label} ===\n{'='*80}\n", flush=True)
        t0 = time.time()

        # Baseline
        t_baseline = _run_baseline(asset, entry)
        perf_baseline = compute_perf_metrics(t_baseline)
        risk_baseline = compute_intraday_risk_metrics(t_baseline)
        print(f"V0 baseline: n={perf_baseline['n']} PF={perf_baseline['pf']:.3f} med=${perf_baseline['median']:.2f}", flush=True)
        print(f"  Largest single-day loss: ${risk_baseline['largest_single_day_loss']:.0f}", flush=True)
        print(f"  Top-1/3/10 % of net: {risk_baseline['top_1_pct']:.1f}% / {risk_baseline['top_3_pct']:.1f}% / {risk_baseline['top_10_pct']:.1f}%", flush=True)
        print(f"  Max-yr: {risk_baseline['max_yr_share_pct']:.1f}%", flush=True)
        print(f"  Tradeify $2K/$3K DD: {risk_baseline['tradeify_2k_daily_dd_compatible']}/{risk_baseline['tradeify_3k_daily_dd_compatible']}", flush=True)
        print(f"  H1/H2 PF: {perf_baseline['h1_pf']:.3f} / {perf_baseline['h2_pf']:.3f}, Era 3 PF: {perf_baseline['era3_pf']:.3f}", flush=True)

        # Variants
        variants = [
            ("V1_FOMC_only", fomc_dates),
            ("V2_NFP_only", nfp_dates),
            ("V3_FOMC_plus_NFP", fomc_dates | nfp_dates),
        ]

        cand_result = {"baseline": {"perf": perf_baseline, "risk": risk_baseline},
                       "variants": {}}

        for vname, excl_dates in variants:
            t_filt = filter_trades_by_excluded_dates(t_baseline, excl_dates)
            perf_filt = compute_perf_metrics(t_filt)
            risk_filt = compute_intraday_risk_metrics(t_filt)
            events_removed = perf_baseline["n"] - perf_filt["n"]
            pf_delta = perf_filt["pf"] - perf_baseline["pf"]
            median_delta = perf_filt["median"] - perf_baseline["median"]
            sdl_delta = perf_filt["era3_pf"]  # placeholder
            classification, risk_improved = classify_filter(perf_baseline, risk_baseline, perf_filt, risk_filt)
            print(f"\n  {vname}: n={perf_filt['n']} (-{events_removed} trades) "
                  f"PF={perf_filt['pf']:.3f} (Δ{pf_delta:+.3f}) "
                  f"med=${perf_filt['median']:.2f} (Δ{median_delta:+.2f})", flush=True)
            print(f"    Largest single-day loss: ${risk_filt['largest_single_day_loss']:.0f} "
                  f"(baseline ${risk_baseline['largest_single_day_loss']:.0f})", flush=True)
            print(f"    Top-3 % of net: {risk_filt['top_3_pct']:.1f}% (baseline {risk_baseline['top_3_pct']:.1f}%)", flush=True)
            print(f"    Max-yr: {risk_filt['max_yr_share_pct']:.1f}% (baseline {risk_baseline['max_yr_share_pct']:.1f}%)", flush=True)
            print(f"    Tradeify $2K/$3K DD: {risk_filt['tradeify_2k_daily_dd_compatible']}/{risk_filt['tradeify_3k_daily_dd_compatible']}", flush=True)
            print(f"    H1/H2: {perf_filt['h1_pf']:.3f}/{perf_filt['h2_pf']:.3f}, Era3 PF: {perf_filt['era3_pf']:.3f}", flush=True)
            print(f"    → {classification}", flush=True)
            cand_result["variants"][vname] = {
                "perf": perf_filt, "risk": risk_filt,
                "events_removed": events_removed,
                "pf_delta": pf_delta, "median_delta": median_delta,
                "classification": classification,
                "risk_materially_improved": risk_improved,
            }

        # "Should this change the Lane A packet?" line
        any_green = any("GREEN refinement" in v["classification"] for v in cand_result["variants"].values())
        any_observational = any("OBSERVATIONAL" in v["classification"] for v in cand_result["variants"].values())
        if any_green:
            packet_impact = "Requires operator review — at least one variant qualifies as GREEN refinement / packet appendix"
        elif any_observational:
            packet_impact = "Appendix only — observational evidence, no change to Lane A baseline"
        else:
            packet_impact = "No change — all event filters archive cleanly; baseline retains the edge"
        print(f"\n  Should this change the Lane A packet? → {packet_impact}", flush=True)
        cand_result["lane_a_packet_impact"] = packet_impact

        cand_result["elapsed_s"] = time.time() - t0
        all_results[label] = cand_result

    print(f"\n{'='*80}\nTotal: {time.time() - t_start:.0f}s\n", flush=True)

    # Final summary
    print("=== FINAL SUMMARY ===\n", flush=True)
    for label, r in all_results.items():
        print(f"{label}:", flush=True)
        for vname, v in r["variants"].items():
            print(f"  {vname}: {v['classification']}", flush=True)
        print(f"  Lane A packet impact: {r['lane_a_packet_impact']}\n", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-12l_event_conditioning_batch.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Event-conditioning batch on 3 GREEN Lane A candidates per #208 A",
        "framing": "Risk-cleanliness audit FIRST, candidate-improvement test SECOND",
        "methodology": "docs/fql_forge/event_conditioning_methodology_2026-06-12.md",
        "results": all_results,
    }, indent=2, default=str))
    print(f"Wrote: {out}", flush=True)


if __name__ == "__main__":
    run()
