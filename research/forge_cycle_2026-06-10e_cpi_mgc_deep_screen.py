"""Cycle 2026-06-10e — CPI-MGC deep-screen: temporal split + family review vs Packet #1.

Per operator #132 + #128: any survivor of CPI-MGC first batch requires
family review vs Packet #1 NFP-MGC + temporal split before packet classification.

Runs on the 4 surviving Long variants from cycle 10d.

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

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_cpi_calendar import build_cpi_release_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _bake_cpi_calendar():
    cal = build_cpi_release_calendar(2019, 2026)
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in cal]


def _bake_nfp_calendar():
    cal = build_verified_nfp_calendar(2019, 2026)
    return [pd.to_datetime(f"{c['actual_date']} 08:30:00") for c in cal]


def _run_event(events, exit_bars=24, entry_bars=1, direction="long", label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    costs = get_cost_params("MGC")
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_bars,
        exit_offset_bars=exit_bars, direction=direction,
    )
    res = run_backtest(
        df, sigs, mode="both", point_value=cfg["point_value"], symbol="MGC",
        commission_per_side=costs["commission_per_side"],
        slippage_ticks=costs["slippage_ticks"],
        tick_size=costs["tick_size"],
    )
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


def temporal_split(trades):
    if trades.empty:
        return None
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({
            "year": int(y), "n": int(len(g)),
            "pf": pf, "median": float(np.median(pnl)),
            "net": float(pnl.sum()),
        })
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty:
            continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({
            "era": i+1, "n": int(len(sub)), "pf": pf,
            "median": float(np.median(pnl)), "net": float(pnl.sum()),
        })
    yrs_pos = sum(1 for r in per_year if r["net"] > 0)
    return {
        "per_year": per_year, "eras": eras,
        "yrs_pos": yrs_pos, "n_yrs": len(per_year),
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
    }


def family_review(trades_a, trades_b, label_a, label_b):
    """Compute trade-day overlap and daily-PnL correlation."""
    if trades_a.empty or trades_b.empty:
        return None
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
        "label_a": label_a, "label_b": label_b,
        "n_days_a": len(days_a), "n_days_b": len(days_b),
        "n_days_overlap": len(overlap),
        "overlap_pct_of_a": len(overlap) / len(days_a) * 100 if days_a else 0,
        "overlap_pct_of_b": len(overlap) / len(days_b) * 100 if days_b else 0,
        "daily_pnl_corr": corr,
    }


def run():
    print("Cycle 2026-06-10e — CPI-MGC deep-screen: temporal + family review vs NFP-MGC", flush=True)
    print("Per #132 + #128: mandatory before any packet classification.\n", flush=True)
    cpi_events = _bake_cpi_calendar()
    nfp_events = _bake_nfp_calendar()
    print(f"CPI calendar: {len(cpi_events)} events (rule-based, audit pending)", flush=True)
    print(f"NFP calendar: {len(nfp_events)} events (verified per Packet #1)\n", flush=True)

    # Run NFP-MGC-Long-2h for family review baseline
    print("Computing NFP-MGC-Long-2h baseline (Packet #1)...", flush=True)
    m_nfp, t_nfp = _run_event(nfp_events, exit_bars=24, direction="long",
                              label="NFP-MGC-Long-2h")
    print(f"  NFP-MGC-Long-2h: n={m_nfp['n']} PF={m_nfp['pf']:.3f} median=${m_nfp['median']:.2f}",
          flush=True)

    # CPI-MGC survivors from 10d
    SURVIVORS = [
        ("CPI-MGC-Long-2h", 24),
        ("CPI-MGC-Long-1h", 12),
        ("CPI-MGC-Long-4h", 48),
        ("CPI-MGC-Long-EOD", 72),
    ]
    candidates = []
    print("\n=== Per-candidate deep-screen ===", flush=True)
    for label, exit_bars in SURVIVORS:
        print(f"\n--- {label} (exit={exit_bars}b) ---", flush=True)
        m, trades = _run_event(cpi_events, exit_bars=exit_bars, direction="long",
                               label=label)
        ts = temporal_split(trades)
        fam = family_review(trades, t_nfp, label, "NFP-MGC-Long-2h")
        # Concentration metrics
        net_per_year = [y["net"] for y in ts["per_year"]] if ts else []
        total_net = sum(abs(n) for n in net_per_year) if net_per_year else 1
        max_yr_share = max(abs(n) for n in net_per_year) / sum(net_per_year) * 100 if sum(net_per_year) > 0 else 0
        print(f"  n={m['n']}, PF={m['pf']:.3f}, median=${m['median']:.2f}", flush=True)
        if ts:
            print(f"  yrs_pos: {ts['yrs_pos']}/{ts['n_yrs']}", flush=True)
            print(f"  per-year (n / pf / median / net):", flush=True)
            for y in ts["per_year"]:
                print(f"    {y['year']}: n={y['n']:3d} PF={y['pf']:.2f} med=${y['median']:.2f} net=${y['net']:.0f}",
                      flush=True)
            print(f"  eras: Era1 PF {ts['eras'][0]['pf']:.2f}, Era2 PF {ts['eras'][1]['pf']:.2f}, Era3 PF {ts['eras'][2]['pf']:.2f}",
                  flush=True)
            print(f"  Era3 median: ${ts['era3_median']:.2f}", flush=True)
        if fam:
            print(f"  Family review vs NFP-MGC: corr={fam['daily_pnl_corr']:.3f}, "
                  f"day-overlap={fam['n_days_overlap']}/{fam['n_days_a']} ({fam['overlap_pct_of_a']:.1f}%)",
                  flush=True)
        candidates.append({
            "label": label,
            "exit_bars": exit_bars,
            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
            "temporal_split": ts,
            "family_review_vs_NFP-MGC": fam,
            "max_yr_share_pct": max_yr_share,
        })

    print("\n=== Summary ===", flush=True)
    for c in candidates:
        m = c["metrics"]; ts = c["temporal_split"]; fam = c["family_review_vs_NFP-MGC"]
        print(f"  {c['label']:25s}: PF {m['pf']:.2f} med ${m['median']:.2f} "
              f"yrs+ {ts['yrs_pos']}/{ts['n_yrs']} Era3-med ${ts['era3_median']:.2f} "
              f"corr-NFP {fam['daily_pnl_corr']:.3f} overlap {fam['overlap_pct_of_a']:.1f}%",
              flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-10e_deep_screen.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "CPI-MGC deep-screen: temporal split + family review vs Packet #1 NFP-MGC",
        "boundaries": "report-only Lane B; no registry/scheduler/portfolio/promotion mutation",
        "nfp_baseline": {
            "n": m_nfp["n"], "pf": float(m_nfp["pf"]), "median": float(m_nfp["median"]),
        },
        "candidates": candidates,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
