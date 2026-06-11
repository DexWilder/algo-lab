"""Cycle 2026-06-11f — FOMC-MGC-Long-4h deep-screen + family review.

Per #157 strict deep-screen gates on the single PAPER_PACKET tier candidate.

Required gates:
  - positive median (already known: +$40.76)
  - PF >= 1.30 (already known: 1.403)
  - PASS_STRESS (already known: PASS_STRESS)
  - max-yr concentration <= 50%
  - yrs+ >= 50%
  - Era 3 PF >= 1.0
  - Era 3 median >= 0
  - family review vs Packet #1 NFP-MGC, CPI-MGC archived, BBKC-MNQ

Calendar source: OFFICIAL Fed.gov (per #157 calendar verification requirement met).

Boundaries: report-only Lane B. No promotion. No registry/scheduler mutation.
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

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def filter_clean_events(events, df, max_gap_minutes=60):
    df_dt = pd.to_datetime(df["datetime"])
    clean = []
    for ev in events:
        if ev < df_dt.iloc[0]:
            continue
        after = df[df_dt > ev].head(1)
        if len(after) == 0:
            continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes:
            clean.append(ev)
    return clean


def temporal_split(trades):
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)), "net": float(pnl.sum()),
                         "win_rate": float((pnl > 0).mean())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    nets = [y["net"] for y in per_year]
    total_net = sum(nets)
    max_yr_share = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
    return {
        "per_year": per_year, "eras": eras,
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year),
        "total_net": total_net,
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
        "max_yr_share_pct": max_yr_share,
    }


def _run_event(asset, events, exit_bars, direction, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=1,
        exit_offset_bars=exit_bars, direction=direction,
    )
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"],
                       symbol=asset, commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def _run_strategy(asset, entry, filter_name, exit_name, mode, params, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name,
                                       filter_name=filter_name, params=params)
    res = run_backtest(df, sigs, mode=mode, point_value=cfg["point_value"],
                       symbol=asset, commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def family_review(trades_a, trades_b):
    if trades_a.empty or trades_b.empty: return None
    days_a = set(pd.to_datetime(trades_a["entry_time"]).dt.date)
    days_b = set(pd.to_datetime(trades_b["entry_time"]).dt.date)
    overlap = days_a & days_b
    da = trades_a.copy(); da["entry_dt"] = pd.to_datetime(da["entry_time"]); da["date"] = da["entry_dt"].dt.date
    db = trades_b.copy(); db["entry_dt"] = pd.to_datetime(db["entry_time"]); db["date"] = db["entry_dt"].dt.date
    pa = da.groupby("date")["pnl"].sum()
    pb = db.groupby("date")["pnl"].sum()
    aligned = pd.concat([pa, pb], axis=1, keys=["a", "b"]).fillna(0.0)
    corr = float(aligned["a"].corr(aligned["b"]))
    if overlap:
        pa_ov = pa[pa.index.isin(overlap)]; pb_ov = pb[pb.index.isin(overlap)]
        aligned_ov = pd.concat([pa_ov, pb_ov], axis=1, keys=["a", "b"]).fillna(0.0)
        corr_ov = float(aligned_ov["a"].corr(aligned_ov["b"]))
    else:
        corr_ov = float("nan")
    return {
        "n_days_a": len(days_a), "n_days_b": len(days_b),
        "n_days_overlap": len(overlap),
        "overlap_pct_of_a": len(overlap) / len(days_a) * 100 if days_a else 0,
        "daily_pnl_corr": corr,
        "overlap_day_pnl_corr": corr_ov,
    }


def run():
    print("Cycle 2026-06-11f — FOMC-MGC-Long-4h deep-screen + family review", flush=True)
    print("Per #157 explicit deep-screen + family review on PAPER_PACKET tier.\n", flush=True)

    fomc_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                   for c in build_official_fomc_calendar()]
    df_mgc = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    fomc_clean = filter_clean_events(fomc_events, df_mgc)

    print(f"--- Deep-screen: FOMC-MGC-Long-4h ---", flush=True)
    print(f"  Clean FOMC events: {len(fomc_clean)}", flush=True)
    m, t_cand = _run_event("MGC", fomc_clean, 48, "long", "FOMC-MGC-Long-4h")
    ts = temporal_split(t_cand)
    print(f"  n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} net=${ts['total_net']:.0f}", flush=True)
    print(f"  yrs+: {ts['yrs_pos']}/{ts['n_yrs']}, max-yr share: {ts['max_yr_share_pct']:.1f}%", flush=True)
    print(f"  Era1 PF: {ts['eras'][0]['pf']:.2f} med=${ts['eras'][0]['median']:.2f} net=${ts['eras'][0]['net']:.0f}", flush=True)
    print(f"  Era2 PF: {ts['eras'][1]['pf']:.2f} med=${ts['eras'][1]['median']:.2f} net=${ts['eras'][1]['net']:.0f}", flush=True)
    print(f"  Era3 PF: {ts['eras'][2]['pf']:.2f} med=${ts['eras'][2]['median']:.2f} net=${ts['eras'][2]['net']:.0f}", flush=True)
    for y in ts["per_year"]:
        print(f"    {y['year']}: n={y['n']:2d} PF={y['pf']:.2f} med=${y['median']:.2f} net=${y['net']:.0f} wr={y['win_rate']:.0%}", flush=True)

    gates = {
        "positive_median": m["median"] > 0,
        "PF_>=_1.30": m["pf"] >= 1.30,
        "PASS_STRESS": True,  # confirmed in cycle 11e
        "max_yr_<=_50pct": ts["max_yr_share_pct"] <= 50.0,
        "yrs_pos_>=_50pct": ts["yrs_pos"] / ts["n_yrs"] >= 0.5,
        "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
        "Era3_median_>=_0": ts["era3_median"] >= 0,
    }
    print(f"\n  Strict gates: {gates}", flush=True)
    print(f"  ALL pass: {all(gates.values())}", flush=True)

    # Family review
    print(f"\n--- Family review ---", flush=True)
    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]
    nfp_clean = filter_clean_events(nfp_events, df_mgc)
    print(f"  Packet #1 NFP-MGC-Long-2h ({len(nfp_clean)} clean events)...", flush=True)
    _, t_packet1 = _run_event("MGC", nfp_clean, 24, "long", "NFP-MGC-Long-2h")

    cpi_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                  for c in build_verified_cpi_calendar()]
    cpi_clean = filter_clean_events(cpi_events, df_mgc)
    print(f"  CPI-MGC-Long-1h (archived; {len(cpi_clean)} clean events)...", flush=True)
    _, t_cpi_mgc = _run_event("MGC", cpi_clean, 12, "long", "CPI-MGC-Long-1h")

    print(f"  BBKC-MNQ portfolio complement...", flush=True)
    _, t_bbkc = _run_strategy("MNQ", "bb_keltner_squeeze", "ema_slope", "profit_ladder",
                               "both", {}, "BBKC-MNQ")

    print(f"  XB-ORB-EMA-Ladder-MNQ probation...", flush=True)
    _, t_orb_mnq = _run_strategy("MNQ", "orb_breakout", "ema_slope", "profit_ladder",
                                  "both", {}, "XB-ORB-MNQ")

    print(f"\n  Family-review correlations:", flush=True)
    fam_p1 = family_review(t_cand, t_packet1)
    fam_cpi = family_review(t_cand, t_cpi_mgc)
    fam_bbkc = family_review(t_cand, t_bbkc)
    fam_orb = family_review(t_cand, t_orb_mnq)
    print(f"    vs Packet #1 NFP-MGC-2h: corr={fam_p1['daily_pnl_corr']:.3f} overlap={fam_p1['overlap_pct_of_a']:.1f}% overlap-day-corr={fam_p1['overlap_day_pnl_corr']:.3f}", flush=True)
    print(f"    vs CPI-MGC-Long-1h:      corr={fam_cpi['daily_pnl_corr']:.3f} overlap={fam_cpi['overlap_pct_of_a']:.1f}% overlap-day-corr={fam_cpi['overlap_day_pnl_corr']:.3f}", flush=True)
    print(f"    vs BBKC-MNQ:             corr={fam_bbkc['daily_pnl_corr']:.3f} overlap={fam_bbkc['overlap_pct_of_a']:.1f}%", flush=True)
    print(f"    vs XB-ORB-MNQ probation: corr={fam_orb['daily_pnl_corr']:.3f} overlap={fam_orb['overlap_pct_of_a']:.1f}%", flush=True)

    max_corr = max([fam_p1["daily_pnl_corr"], fam_cpi["daily_pnl_corr"],
                    fam_bbkc["daily_pnl_corr"], fam_orb["daily_pnl_corr"]])
    p1_ov = fam_p1["overlap_day_pnl_corr"]
    if not np.isnan(p1_ov) and p1_ov > 0.7:
        fam_cls = "DUPLICATE_EXPOSURE_REJECT (Packet #1 same-day)"
    elif not np.isnan(p1_ov) and p1_ov > 0.5:
        fam_cls = "PORTFOLIO_COMPLEMENT (Packet #1 same-day moderate corr)"
    elif max_corr > 0.5:
        fam_cls = "PORTFOLIO_COMPLEMENT (moderate corr)"
    elif max_corr > 0.3:
        fam_cls = "PORTFOLIO_COMPLEMENT (low-moderate corr)"
    else:
        fam_cls = "INDEPENDENT (max corr < 0.30)"
    print(f"  → Family classification: {fam_cls}", flush=True)

    # Final disposition
    if all(gates.values()) and "INDEPENDENT" in fam_cls:
        disposition = "PAPER_PACKET_CANDIDATE (all 7 strict gates pass + INDEPENDENT)"
        next_step = "Proceed to 8-dim audit (lookahead, calendar provenance, survivorship, duplicate exposure, cost stress, edge quality, artifact determinism, calendar verification — already OFFICIAL Fed.gov)"
    elif all(gates.values()) and "PORTFOLIO_COMPLEMENT" in fam_cls:
        disposition = "PORTFOLIO_COMPLEMENT_CANDIDATE (gates pass but moderate corr to existing)"
        next_step = "Operator portfolio review required"
    elif not all(gates.values()) and "INDEPENDENT" in fam_cls:
        failed = [k for k, v in gates.items() if not v]
        disposition = f"OBSERVATIONAL — independent but fails gates: {', '.join(failed)}"
        next_step = "Lock as observational near-miss; consider REOPENABLE criteria"
    elif "DUPLICATE_EXPOSURE_REJECT" in fam_cls:
        disposition = "REJECT — DUPLICATE_EXPOSURE with Packet #1"
        next_step = "Archive"
    else:
        failed = [k for k, v in gates.items() if not v]
        disposition = f"OBSERVATIONAL — fails gates ({', '.join(failed)}) + high family corr"
        next_step = "Archive or hold"

    print(f"\n=== FINAL DISPOSITION ===", flush=True)
    print(f"  {disposition}", flush=True)
    print(f"  Next step: {next_step}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11f_fomc_mgc_deep_screen.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "FOMC-MGC-Long-4h deep-screen + family review per #157",
        "calendar_source": "OFFICIAL federalreserve.gov",
        "boundaries": "report-only Lane B; calendar verification SATISFIED via Fed.gov",
        "candidate": "FOMC-MGC-Long-4h",
        "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net")},
        "temporal_split": ts,
        "strict_gates": gates,
        "all_gates_pass": all(gates.values()),
        "family_review": {
            "vs_Packet1_NFP_MGC_2h": fam_p1,
            "vs_CPI_MGC_Long_1h_archived": fam_cpi,
            "vs_BBKC_MNQ": fam_bbkc,
            "vs_XB_ORB_MNQ_probation": fam_orb,
        },
        "family_classification": fam_cls,
        "final_disposition": disposition,
        "next_step": next_step,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
