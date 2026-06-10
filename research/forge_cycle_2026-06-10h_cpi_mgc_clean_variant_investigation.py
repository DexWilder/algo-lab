"""Cycle 2026-06-10h — CPI-MGC clean-events variant investigation (BOUNDED).

Per operator decision #144 (A/C hybrid): archive CPI-MGC-Long-2h as packet
candidate, but allow ONE bounded clean-variant investigation. No discretion
exceptions to strict gates.

Variants tested on CLEAN events only (gap < 1h):
  - CPI-MGC-Long-2h (re-check on clean — already shown to fail concentration)
  - CPI-MGC-Long-EOD (clean re-check)
  - Optional recent-era OBSERVATIONAL note (2022+ subsample)

NO broad parameter grid. NO curve-fitting to reduce 2024 concentration.

Acceptance gates per #144:
  - max-year ≤ 50%
  - positive median
  - PASS_STRESS
  - temporal split acceptable
  - Era 3 positive
  - official calendar verified (still DATA_REQUIRED per #140 — bounds investigation)
  - data integrity clean

If no clean variant passes: archive CPI-MGC as RESEARCH_ONLY / OBSERVATIONAL.

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
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def filter_clean_events(events, df, max_gap_minutes=60):
    """Apply clean-events filter per #146 doctrine."""
    df_dt = pd.to_datetime(df["datetime"])
    clean, contaminated = [], []
    for ev in events:
        after = df[df_dt > ev].head(1)
        if len(after) == 0:
            contaminated.append((ev, "no future bar"))
            continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes:
            clean.append(ev)
        else:
            contaminated.append((ev, f"{gap_min/60:.1f}h gap"))
    return clean, contaminated


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
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year),
            "era3_pf": eras[-1]["pf"] if eras else float("nan"),
            "era3_median": eras[-1]["median"] if eras else float("nan")}


def _run(events, exit_bars=24, direction="long",
         commission_mult=1.0, slippage_mult=1.0, label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    costs = get_cost_params("MGC")
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=1,
        exit_offset_bars=exit_bars, direction=direction,
    )
    res = run_backtest(
        df, sigs, mode="both", point_value=cfg["point_value"], symbol="MGC",
        commission_per_side=costs["commission_per_side"] * commission_mult,
        slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slippage_mult)),
        tick_size=costs["tick_size"],
    )
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


def family_review(trades_a, trades_b):
    if trades_a.empty or trades_b.empty: return None
    days_a = set(pd.to_datetime(trades_a["entry_time"]).dt.date)
    days_b = set(pd.to_datetime(trades_b["entry_time"]).dt.date)
    overlap = days_a & days_b
    daily_a = trades_a.copy(); daily_a["entry_dt"] = pd.to_datetime(daily_a["entry_time"]); daily_a["date"] = daily_a["entry_dt"].dt.date
    pnl_a = daily_a.groupby("date")["pnl"].sum()
    daily_b = trades_b.copy(); daily_b["entry_dt"] = pd.to_datetime(daily_b["entry_time"]); daily_b["date"] = daily_b["entry_dt"].dt.date
    pnl_b = daily_b.groupby("date")["pnl"].sum()
    aligned = pd.concat([pnl_a, pnl_b], axis=1, keys=["a", "b"]).fillna(0.0)
    return {"n_days_overlap": len(overlap), "overlap_pct_of_a": len(overlap)/len(days_a)*100 if days_a else 0,
            "daily_pnl_corr": float(aligned["a"].corr(aligned["b"]))}


def stress_screen(events, exit_bars, direction, label):
    rows = []
    for stress_label, cm, sm in [
        ("baseline (1x)", 1.0, 1.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
        ("4x cost + 2 ticks slip", 4.0, 3.0),
    ]:
        m, _ = _run(events, exit_bars=exit_bars, direction=direction,
                    commission_mult=cm, slippage_mult=sm, label=f"{label}-{stress_label}")
        rows.append({"stress": stress_label, "n": m["n"], "pf": float(m["pf"]),
                     "median": float(m["median"])})
    moderate = next(r for r in rows if r["stress"] == "2x cost + 2 ticks slip")
    extreme = next(r for r in rows if r["stress"] == "4x cost + 2 ticks slip")
    if moderate["median"] <= 0: return {"rows": rows, "verdict": "FAIL_STRESS"}
    if moderate["median"] < 1.0: return {"rows": rows, "verdict": "KNIFE_EDGE"}
    if extreme["median"] <= 0: return {"rows": rows, "verdict": "KNIFE_EDGE (4x)"}
    return {"rows": rows, "verdict": "PASS_STRESS"}


def evaluate_strict_gates(m, ts, stress, max_yr_share):
    """Per #144: max-yr ≤ 50%, positive median, PASS_STRESS, temporal acceptable, Era3 positive."""
    gates = {}
    gates["positive_median"] = m["median"] > 0
    gates["max_yr_50_pct"] = max_yr_share <= 50.0
    gates["PASS_STRESS"] = stress["verdict"] == "PASS_STRESS"
    gates["yrs_pos_50_pct"] = (ts["yrs_pos"] / ts["n_yrs"] >= 0.5) if ts else False
    gates["era3_positive_pf"] = ts["era3_pf"] >= 1.0 if ts else False
    gates["era3_positive_median"] = ts["era3_median"] > 0 if ts else False
    gates["all_passed"] = all(gates.values())
    return gates


def run():
    print("Cycle 2026-06-10h — CPI-MGC CLEAN-EVENTS variant investigation (#144 bounded)", flush=True)
    print("Strict gates only — NO discretion exceptions.\n", flush=True)

    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cpi_events_all = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in build_verified_cpi_calendar()]
    cpi_clean, cpi_contaminated = filter_clean_events(cpi_events_all, df, max_gap_minutes=60)

    nfp_events_all = [pd.to_datetime(f"{c['actual_date']} 08:30:00") for c in build_verified_nfp_calendar(2019, 2026)]
    nfp_clean, _ = filter_clean_events(nfp_events_all, df, max_gap_minutes=60)

    print(f"CPI events: {len(cpi_events_all)} total, {len(cpi_clean)} clean ({len(cpi_clean)/len(cpi_events_all)*100:.1f}%)", flush=True)
    print(f"Contaminated: {len(cpi_contaminated)} excluded", flush=True)
    print(f"NFP clean baseline: {len(nfp_clean)} events\n", flush=True)

    # NFP baseline for family review
    _, t_nfp = _run(nfp_clean, exit_bars=24, direction="long", label="NFP-MGC-Long-2h-CLEAN")

    variants = [
        ("CPI-MGC-Long-2h-CLEAN", 24),
        ("CPI-MGC-Long-EOD-CLEAN", 72),
    ]
    results = []
    for label, exit_bars in variants:
        print(f"\n--- {label} (exit={exit_bars}b) ---", flush=True)
        m, trades = _run(cpi_clean, exit_bars=exit_bars, direction="long", label=label)
        ts = temporal_split(trades)
        nets = [y["net"] for y in ts["per_year"]] if ts else []
        total_net = sum(nets) if nets else 0
        max_yr_share = max(abs(n) for n in nets) / total_net * 100 if total_net > 0 else 0
        stress = stress_screen(cpi_clean, exit_bars, "long", label)
        fam = family_review(trades, t_nfp)
        gates = evaluate_strict_gates(m, ts, stress, max_yr_share)

        print(f"  n={m['n']}, PF={m['pf']:.3f}, median=${m['median']:.2f}", flush=True)
        print(f"  Max-yr share: {max_yr_share:.1f}% (gate: ≤50%)", flush=True)
        print(f"  Yrs+: {ts['yrs_pos']}/{ts['n_yrs']}", flush=True)
        print(f"  Era3 PF: {ts['era3_pf']:.2f}, Era3 median: ${ts['era3_median']:.2f}", flush=True)
        print(f"  Stress: {stress['verdict']}", flush=True)
        print(f"  Family vs NFP-CLEAN: corr={fam['daily_pnl_corr']:.3f} overlap={fam['n_days_overlap']}", flush=True)
        print(f"  STRICT GATES: {gates}", flush=True)
        print(f"  → {'ALL GATES PASS' if gates['all_passed'] else 'FAILS strict gates'}", flush=True)

        results.append({
            "label": label, "exit_bars": exit_bars,
            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net", "max_dd")},
            "max_yr_share_pct": max_yr_share,
            "temporal_split": ts,
            "stress": stress,
            "family_review": fam,
            "gates": gates,
            "verdict": "PASSES STRICT GATES" if gates["all_passed"] else "FAILS strict gates",
        })

    # Recent-era (2022+) observational note
    print(f"\n--- OBSERVATIONAL: 2022+ recent-era subsample (NOT a packet candidate) ---", flush=True)
    cpi_clean_recent = [e for e in cpi_clean if e.year >= 2022]
    print(f"  Recent-era events: {len(cpi_clean_recent)} (2022-2026)", flush=True)
    m_recent, t_recent = _run(cpi_clean_recent, exit_bars=24, direction="long",
                               label="CPI-MGC-Long-2h-CLEAN-2022plus-OBSERVATIONAL")
    print(f"  n={m_recent['n']}, PF={m_recent['pf']:.3f}, median=${m_recent['median']:.2f}, net=${m_recent['net']:.2f}", flush=True)
    print(f"  NOTE: This is OBSERVATIONAL ONLY per #144 — not a packet candidate.", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-10h_cpi_clean_variants.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "CPI-MGC clean-events variant investigation (#144 bounded)",
        "boundaries": "report-only Lane B; no discretion exceptions to strict gates",
        "clean_event_filter": "gap < 1h (per #146 doctrine)",
        "clean_events_count": len(cpi_clean),
        "contaminated_excluded": len(cpi_contaminated),
        "variants": results,
        "observational_recent_era_2022plus": {
            "n": int(m_recent["n"]),
            "pf": float(m_recent["pf"]),
            "median": float(m_recent["median"]),
            "net": float(m_recent["net"]),
            "note": "OBSERVATIONAL ONLY — not packet candidate per #144",
        },
        "final_disposition": "ARCHIVED unless any variant ALL GATES PASS",
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
