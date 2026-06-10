"""Cycle 2026-06-10f — CPI-MGC re-run on VERIFIED CPI calendar.

Per operator decision #136-138: replace rule-based calendar with verified
BLS dates, re-run, compare metrics. If candidate still passes gates, proceed
to 8-dim audit.

Reruns the 4 candidates from cycle 10d using the verified calendar from
forge_cpi_calendar_verified.py. Compares head-to-head against rule-based.

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
from research.forge_cpi_calendar import build_cpi_release_calendar as build_rule_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _bake_calendar(cal_dicts):
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in cal_dicts]


def _bake_nfp():
    cal = build_verified_nfp_calendar(2019, 2026)
    return [pd.to_datetime(f"{c['actual_date']} 08:30:00") for c in cal]


def _run_event(events, exit_bars=24, entry_bars=1, direction="long",
               commission_mult=1.0, slippage_mult=1.0, label=""):
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]
    costs = get_cost_params("MGC")
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_bars,
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
    return {
        "per_year": per_year, "eras": eras,
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year),
        "era3_pf": eras[-1]["pf"] if eras else float("nan"),
        "era3_median": eras[-1]["median"] if eras else float("nan"),
    }


def family_review(trades_a, trades_b):
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
    return {
        "n_days_a": len(days_a), "n_days_b": len(days_b),
        "n_days_overlap": len(overlap),
        "overlap_pct_of_a": len(overlap) / len(days_a) * 100 if days_a else 0,
        "daily_pnl_corr": float(aligned["a"].corr(aligned["b"])),
    }


def stress_screen(events, exit_bars, direction, label):
    rows = []
    for stress_label, cm, sm in [
        ("baseline (1x)", 1.0, 1.0),
        ("1.5x cost + 1 tick slip", 1.5, 2.0),
        ("2x cost + 1 tick slip", 2.0, 2.0),
        ("2x cost + 2 ticks slip", 2.0, 3.0),
        ("4x cost + 2 ticks slip", 4.0, 3.0),
    ]:
        m, _ = _run_event(events, exit_bars=exit_bars, direction=direction,
                          commission_mult=cm, slippage_mult=sm, label=f"{label}-{stress_label}")
        rows.append({"stress": stress_label, "n": m["n"], "pf": float(m["pf"]),
                     "median": float(m["median"]), "net": float(m["net"])})
    moderate = next(r for r in rows if r["stress"] == "2x cost + 2 ticks slip")
    extreme = next(r for r in rows if r["stress"] == "4x cost + 2 ticks slip")
    if moderate["median"] <= 0:
        verdict = "FAIL_STRESS"
    elif moderate["median"] < 1.0:
        verdict = "KNIFE_EDGE"
    elif extreme["median"] <= 0:
        verdict = "KNIFE_EDGE (4x stress)"
    else:
        verdict = "PASS_STRESS"
    return {"rows": rows, "verdict": verdict}


def run():
    print("Cycle 2026-06-10f — CPI-MGC VERIFIED calendar re-run (#136-138)", flush=True)
    print("Comparing rule-based vs verified BLS dates.\n", flush=True)
    rule_events = _bake_calendar(build_rule_calendar(2019, 2026))
    verified_events = _bake_calendar(build_verified_cpi_calendar())
    nfp_events = _bake_nfp()
    print(f"Rule calendar:     {len(rule_events)} events", flush=True)
    print(f"Verified calendar: {len(verified_events)} events", flush=True)
    print(f"NFP baseline:      {len(nfp_events)} events\n", flush=True)

    # Compute NFP baseline for family review
    _, t_nfp = _run_event(nfp_events, exit_bars=24, direction="long", label="NFP-MGC-Long-2h")

    SPECS = [
        ("CPI-MGC-Long-1h", 12),
        ("CPI-MGC-Long-2h", 24),
        ("CPI-MGC-Long-EOD", 72),
    ]
    results = []
    for label, exit_bars in SPECS:
        print(f"\n--- {label} (exit={exit_bars}b) ---", flush=True)
        # Rule-based
        m_rule, t_rule = _run_event(rule_events, exit_bars=exit_bars, direction="long",
                                     label=f"{label}-RULE")
        ts_rule = temporal_split(t_rule)
        # Verified
        m_ver, t_ver = _run_event(verified_events, exit_bars=exit_bars, direction="long",
                                   label=f"{label}-VERIFIED")
        ts_ver = temporal_split(t_ver)
        # Family review verified vs NFP
        fam = family_review(t_ver, t_nfp)
        # Concentration
        nets = [y["net"] for y in ts_ver["per_year"]] if ts_ver else []
        total_signed = sum(nets) if nets else 0
        max_yr_share = max(abs(n) for n in nets) / total_signed * 100 if total_signed > 0 else 0
        # Stress on verified
        stress_ver = stress_screen(verified_events, exit_bars, "long", f"{label}-VERIFIED")

        print(f"  RULE     : n={m_rule['n']:4d} PF={m_rule['pf']:.3f} med=${m_rule['median']:.2f}", flush=True)
        print(f"  VERIFIED : n={m_ver['n']:4d} PF={m_ver['pf']:.3f} med=${m_ver['median']:.2f}", flush=True)
        if ts_ver:
            print(f"  VER yrs+: {ts_ver['yrs_pos']}/{ts_ver['n_yrs']}, "
                  f"max-yr {max_yr_share:.1f}%, "
                  f"Era3 PF {ts_ver['era3_pf']:.2f} median ${ts_ver['era3_median']:.2f}", flush=True)
            print(f"  VER per-year:")
            for y in ts_ver["per_year"]:
                print(f"    {y['year']}: n={y['n']:3d} PF={y['pf']:.2f} med=${y['median']:.2f} net=${y['net']:.0f}", flush=True)
        if fam:
            print(f"  VER family review vs NFP: corr={fam['daily_pnl_corr']:.3f} "
                  f"overlap={fam['n_days_overlap']}/{fam['n_days_a']} ({fam['overlap_pct_of_a']:.1f}%)", flush=True)
        print(f"  VER stress: {stress_ver['verdict']}", flush=True)

        results.append({
            "label": label, "exit_bars": exit_bars,
            "rule_based": {
                "n": int(m_rule["n"]), "pf": float(m_rule["pf"]),
                "median": float(m_rule["median"]), "net": float(m_rule["net"]),
            },
            "verified": {
                "n": int(m_ver["n"]), "pf": float(m_ver["pf"]),
                "median": float(m_ver["median"]), "net": float(m_ver["net"]),
                "temporal_split": ts_ver,
                "max_yr_share_pct": max_yr_share,
                "family_review_vs_NFP": fam,
                "stress": stress_ver,
            },
        })

    print(f"\n=== Summary: RULE vs VERIFIED ===")
    for r in results:
        rb = r["rule_based"]; vr = r["verified"]
        print(f"  {r['label']:20s}: RULE PF={rb['pf']:.2f} med=${rb['median']:.2f} | "
              f"VERIFIED PF={vr['pf']:.2f} med=${vr['median']:.2f} "
              f"max-yr={vr['max_yr_share_pct']:.1f}% stress={vr['stress']['verdict'].split()[0]}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-10f_verified_calendar.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "CPI-MGC re-run on VERIFIED BLS calendar (#136-138)",
        "boundaries": "report-only Lane B; no registry/scheduler/portfolio/promotion mutation",
        "calendar_source": "research/forge_cpi_calendar_verified.py — operator-verifiable against bls.gov",
        "comparison": results,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
