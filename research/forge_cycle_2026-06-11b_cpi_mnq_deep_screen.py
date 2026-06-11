"""Cycle 2026-06-11b — CPI-MNQ Long deep-screen + family review.

Per operator decision #153: deep-screen any WATCH candidate, family review
vs Packet #1, MNQ probation, MES ORB complements, BBKC-MNQ.

Two CPI-MNQ-Long candidates from cycle 11a:
  - CPI-MNQ-Long-1h: PF 1.198, median +$16.51, PASS_STRESS
  - CPI-MNQ-Long-2h: PF 1.151, median +$49.51, PASS_STRESS

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
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
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
    if trades.empty: return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": pf,
                         "median": float(np.median(pnl)), "net": float(pnl.sum())})
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
    total = sum(nets)
    max_yr_share = max(abs(n) for n in nets) / total * 100 if total > 0 else 0
    return {
        "per_year": per_year, "eras": eras,
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year),
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
        "max_yr_share_pct": max_yr_share,
    }


def _run_cpi(asset, events, exit_bars, direction, label):
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


def family_review(trades_a, trades_b, label_a, label_b):
    if trades_a.empty or trades_b.empty: return None
    days_a = set(pd.to_datetime(trades_a["entry_time"]).dt.date)
    days_b = set(pd.to_datetime(trades_b["entry_time"]).dt.date)
    overlap = days_a & days_b
    daily_a = trades_a.copy()
    daily_a["entry_dt"] = pd.to_datetime(daily_a["entry_time"])
    daily_a["date"] = daily_a["entry_dt"].dt.date
    pnl_a = daily_a.groupby("date")["pnl"].sum()
    daily_b = trades_b.copy()
    daily_b["entry_dt"] = pd.to_datetime(daily_b["entry_time"])
    daily_b["date"] = daily_b["entry_dt"].dt.date
    pnl_b = daily_b.groupby("date")["pnl"].sum()
    aligned = pd.concat([pnl_a, pnl_b], axis=1, keys=["a", "b"]).fillna(0.0)
    corr = float(aligned["a"].corr(aligned["b"]))
    return {
        "n_days_a": len(days_a), "n_days_b": len(days_b),
        "n_days_overlap": len(overlap),
        "overlap_pct_of_a": len(overlap) / len(days_a) * 100 if days_a else 0,
        "daily_pnl_corr": corr,
    }


def run():
    print("Cycle 2026-06-11b — CPI-MNQ-Long deep-screen + family review", flush=True)
    print("Per #153 explicit deep-screen + family review on WATCH candidates.\n", flush=True)

    df_mnq = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    cpi_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                  for c in build_verified_cpi_calendar()]
    cpi_clean = filter_clean_events(cpi_events, df_mnq)
    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]

    candidates_to_screen = [
        ("CPI-MNQ-Long-1h", 12),
        ("CPI-MNQ-Long-2h", 24),
    ]

    deep_screens = []
    for label, exit_bars in candidates_to_screen:
        print(f"\n--- Deep-screen: {label} ---", flush=True)
        m, t_cpi = _run_cpi("MNQ", cpi_clean, exit_bars, "long", label)
        ts = temporal_split(t_cpi)
        print(f"  n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}", flush=True)
        print(f"  yrs+: {ts['yrs_pos']}/{ts['n_yrs']}, max-yr: {ts['max_yr_share_pct']:.1f}%", flush=True)
        print(f"  Era1 PF: {ts['eras'][0]['pf']:.2f}, Era2 PF: {ts['eras'][1]['pf']:.2f}, Era3 PF: {ts['eras'][2]['pf']:.2f}", flush=True)
        print(f"  Era3 median: ${ts['era3_median']:.2f}", flush=True)
        print(f"  Per-year breakdown:")
        for y in ts["per_year"]:
            print(f"    {y['year']}: n={y['n']:2d} PF={y['pf']:.2f} med=${y['median']:.2f} net=${y['net']:.0f}", flush=True)

        # Strict #153 gates evaluation
        gates = {
            "positive_median": m["median"] > 0,
            "PF_>=_1.30": m["pf"] >= 1.30,
            "PASS_STRESS": True,  # confirmed in 11a
            "max_yr_<=_50pct": ts["max_yr_share_pct"] <= 50.0,
            "yrs_pos_>=_50pct": ts["yrs_pos"] / ts["n_yrs"] >= 0.5,
            "Era3_PF_>=_1.0": ts["era3_pf"] >= 1.0,
            "Era3_median_>=_0": ts["era3_median"] >= 0,
        }
        print(f"  Strict gates: {gates}", flush=True)
        print(f"  ALL pass: {all(gates.values())}", flush=True)

        deep_screens.append({
            "label": label, "exit_bars": exit_bars,
            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net")},
            "temporal_split": ts,
            "strict_gates": gates,
            "all_gates_pass": all(gates.values()),
            "trades_df": t_cpi,
        })

    # Family review: each candidate vs Packet #1, MNQ probation, MES ORB complements, BBKC-MNQ
    print(f"\n=== Family Review ===\n", flush=True)
    print("Computing Packet #1 NFP-MGC-Long-2h on clean events...", flush=True)
    df_mgc = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    nfp_clean = filter_clean_events(nfp_events, df_mgc)
    _, t_nfp = _run_cpi("MGC", nfp_clean, 24, "long", "NFP-MGC-Long-2h")

    print("Computing XB-ORB-EMA-Ladder-MNQ (probation baseline)...", flush=True)
    _, t_orb_mnq = _run_strategy("MNQ", "orb_breakout", "ema_slope", "profit_ladder",
                                  "both", {}, "XB-ORB-MNQ")

    print("Computing DIR-MES-ORB-Long-PL (portfolio complement)...", flush=True)
    _, t_mes_long = _run_strategy("MES", "orb_breakout", "ema_slope", "profit_ladder",
                                   "long", {}, "DIR-MES-ORB-Long")

    print("Computing BBKC-MNQ-Both-PL (BBKC sleeve)...", flush=True)
    _, t_bbkc = _run_strategy("MNQ", "bb_keltner_squeeze", "ema_slope", "profit_ladder",
                               "both", {}, "BBKC-MNQ")

    for ds in deep_screens:
        label = ds["label"]
        t_cpi = ds["trades_df"]
        print(f"\n--- {label} family review ---", flush=True)
        fam_nfp = family_review(t_cpi, t_nfp, label, "NFP-MGC-2h")
        fam_orb = family_review(t_cpi, t_orb_mnq, label, "XB-ORB-MNQ")
        fam_mes = family_review(t_cpi, t_mes_long, label, "DIR-MES-ORB-Long")
        fam_bbkc = family_review(t_cpi, t_bbkc, label, "BBKC-MNQ")
        print(f"  vs NFP-MGC-2h:  corr={fam_nfp['daily_pnl_corr']:.3f} overlap={fam_nfp['overlap_pct_of_a']:.1f}%", flush=True)
        print(f"  vs XB-ORB-MNQ:  corr={fam_orb['daily_pnl_corr']:.3f} overlap={fam_orb['overlap_pct_of_a']:.1f}%", flush=True)
        print(f"  vs MES-ORB-Long: corr={fam_mes['daily_pnl_corr']:.3f} overlap={fam_mes['overlap_pct_of_a']:.1f}%", flush=True)
        print(f"  vs BBKC-MNQ:    corr={fam_bbkc['daily_pnl_corr']:.3f} overlap={fam_bbkc['overlap_pct_of_a']:.1f}%", flush=True)
        ds["family_review"] = {
            "vs_NFP_MGC_2h": fam_nfp,
            "vs_XB_ORB_MNQ": fam_orb,
            "vs_MES_ORB_Long": fam_mes,
            "vs_BBKC_MNQ": fam_bbkc,
        }
        # Classify per family-review verdicts
        max_corr = max([fam_nfp["daily_pnl_corr"], fam_orb["daily_pnl_corr"],
                        fam_mes["daily_pnl_corr"], fam_bbkc["daily_pnl_corr"]])
        if max_corr < 0.30:
            ds["family_classification"] = "INDEPENDENT (max corr < 0.30)"
        elif max_corr < 0.50:
            ds["family_classification"] = "PORTFOLIO_COMPLEMENT (low-moderate corr)"
        elif max_corr < 0.70:
            ds["family_classification"] = "PORTFOLIO_COMPLEMENT (moderate corr)"
        else:
            ds["family_classification"] = "DUPLICATE_EXPOSURE_REJECT"
        print(f"  → Family classification: {ds['family_classification']}", flush=True)

    # Final disposition per candidate
    print(f"\n=== FINAL DISPOSITIONS ===\n", flush=True)
    for ds in deep_screens:
        label = ds["label"]
        m = ds["metrics"]
        all_pass = ds["all_gates_pass"]
        fam_cls = ds["family_classification"]
        if all_pass and "INDEPENDENT" in fam_cls:
            disposition = "PAPER_PACKET_CANDIDATE (calendar verification still required per #140)"
        elif all_pass and "PORTFOLIO_COMPLEMENT" in fam_cls:
            disposition = "PORTFOLIO_COMPLEMENT_CANDIDATE pending operator portfolio review + calendar verification"
        elif not all_pass:
            failed = [k for k, v in ds["strict_gates"].items() if not v]
            disposition = f"OBSERVATIONAL — fails gates: {', '.join(failed)}"
        else:
            disposition = "REJECT — DUPLICATE_EXPOSURE"
        print(f"  {label}: {disposition}", flush=True)
        ds["final_disposition"] = disposition

    # Save (exclude trades_df from JSON)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11b_cpi_mnq_deep_screen.json"
    serializable = []
    for ds in deep_screens:
        s = {k: v for k, v in ds.items() if k != "trades_df"}
        serializable.append(s)
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "CPI-MNQ-Long deep-screen + family review per #153",
        "boundaries": "report-only Lane B; calendar still DATA_REQUIRED per #140",
        "deep_screens": serializable,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
