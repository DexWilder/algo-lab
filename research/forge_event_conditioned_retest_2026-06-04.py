"""Retest 3 paused families with event-conditioned discriminator.

Per operator approval 2026-06-04 (#43 follow-on, validation rule).
Goal: determine whether event-conditioned features unlock signal,
not overfit one event family.

Families retested:
  1. Russell rebalance (Mar/Jun/Sep/Dec last Friday) on MES
  2. CPI (rule-approx 13th business day) on MES
  3. CPI on MGC (cross-asset / non-equity test)

Each family × 6 filter modes (fade_pre, follow_pre, expansion, compression,
vol_above, vol_below) × 1 exit window (2h baseline).

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import json
import sys
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Calendars (same as Track 3)
# ─────────────────────────────────────────────────────────────────────────────

def nth_business_day(year, month, n=13):
    d = date(year, month, 1)
    count = 0
    while True:
        if d.weekday() < 5:
            count += 1
            if count == n:
                return d
        d += timedelta(days=1)


def last_friday(year, month):
    _, ndays = monthrange(year, month)
    last = date(year, month, ndays)
    offset = (last.weekday() - 4) % 7
    return last - timedelta(days=offset)


def cpi_calendar(start=2019, end=2026, time_str="08:30:00"):
    out = []
    for y in range(start, end + 1):
        for m in range(1, 13):
            out.append(pd.to_datetime(f"{nth_business_day(y, m, 13)} {time_str}"))
    return out


def russell_calendar(start=2019, end=2026, time_str="16:00:00"):
    out = []
    for y in range(start, end + 1):
        for m in (3, 6, 9, 12):
            out.append(pd.to_datetime(f"{last_friday(y, m)} {time_str}"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Classification + temporal split
# ─────────────────────────────────────────────────────────────────────────────

def _classify(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 8:
        return f"KILL (n={n} too small)"
    if median < 0:
        return "KILL (median neg)"
    if pf < 1.15:
        return "KILL (PF<1.15)"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


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
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": pf, "net": float(pnl.sum())})
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
                     "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year)}


def _doctrine(m, ts):
    v = _classify(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)"
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (passed temporal)"
    return "WATCH (passed temporal; modest)"


# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

def run_event(asset, events, label, direction, event_filter=None,
              event_filter_params=None, entry_off=1, exit_off=24):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_off,
        exit_offset_bars=exit_off, direction=direction,
        event_filter=event_filter,
        event_filter_params=event_filter_params,
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    vc = _classify(m)
    ts = temporal_split(res["trades_df"]) if vc == "TEMPORAL_SPLIT_REQUIRED" else None
    v = _doctrine(m, ts)
    return m, ts, vc, v


FILTER_VARIANTS = [
    ("baseline (no filter)", None, None),
    ("fade_pre_5bar", "fade_pre_event_move",
     {"prior_bars": 5, "threshold_pct": 0.001}),
    ("follow_pre_5bar", "follow_pre_event_move",
     {"prior_bars": 5, "threshold_pct": 0.001}),
    ("require_expansion_1.5x", "require_event_bar_expansion",
     {"expansion_threshold": 1.5}),
    ("require_compression_0.7x", "require_event_bar_compression",
     {"compression_threshold": 0.7}),
    ("require_vol_above_70", "require_vol_above_percentile",
     {"vol_threshold": 70}),
    ("require_vol_below_30", "require_vol_below_percentile",
     {"vol_threshold": 30}),
]


def run():
    russell_events = russell_calendar()
    cpi_events = cpi_calendar()

    families = [
        ("Russell-rebalance-MES-Long", "MES", russell_events, "long"),
        ("Russell-rebalance-MES-Short", "MES", russell_events, "short"),
        ("CPI-MES-Long", "MES", cpi_events, "long"),
        ("CPI-MES-Short", "MES", cpi_events, "short"),
        ("CPI-MGC-Long", "MGC", cpi_events, "long"),
        ("CPI-MGC-Short", "MGC", cpi_events, "short"),
    ]

    results = []
    print(f"Event-conditioned filter retest — {len(families)} family×direction × {len(FILTER_VARIANTS)} filter variants\n")
    for fam_label, asset, events, dir_ in families:
        print(f"\n=== {fam_label} ({len(events)} events) ===")
        for variant_label, ef_name, ef_params in FILTER_VARIANTS:
            label = f"EVT-{fam_label}-{variant_label}"
            try:
                m, ts, vc, v = run_event(asset, events, label, dir_,
                                          event_filter=ef_name,
                                          event_filter_params=ef_params,
                                          entry_off=1, exit_off=24)
            except Exception as e:
                print(f"  {variant_label}: ERROR {e}")
                continue
            max_yr = m.get("max_year_share_pct", float("nan"))
            n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
            yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
            print(f"  {variant_label:30s}: n={m['n']:4d} PF={m['pf']:.3f} median=${m['median']:8.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} → {v}")
            results.append({
                "family": fam_label,
                "variant": variant_label,
                "event_filter": ef_name,
                "event_filter_params": ef_params,
                "metrics": {k: m.get(k) for k in (
                    "n", "pf", "median", "net", "max_year_share_pct",
                    "h1_pf", "h2_pf", "years_positive", "n_years",
                )},
                "temporal_split": ts,
                "cheap_verdict": vc,
                "doctrine_verdict": v,
            })

    # Aggregate
    watch_deep = [r for r in results if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"]]
    arch_reject = [r for r in results if "ARCHITECTURAL_REJECT" in r["doctrine_verdict"]]
    kill = [r for r in results if r["doctrine_verdict"].startswith("KILL")]
    print(f"\n=== Aggregate ({len(results)} candidates) ===")
    print(f"  WATCH_FOR_DEEP_SCREEN: {len(watch_deep)}")
    print(f"  ARCHITECTURAL_REJECT:  {len(arch_reject)}")
    print(f"  KILL:                  {len(kill)}")
    if watch_deep:
        print("\n  Headlines (WATCH_FOR_DEEP_SCREEN):")
        for r in watch_deep:
            print(f"    {r['family']} / {r['variant']}: PF={r['metrics']['pf']:.3f} median=${r['metrics']['median']:.2f} max-yr={r['metrics'].get('max_year_share_pct', float('nan')):.1f}%")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    (out_dir / f"forge_event_conditioned_retest_{date_iso}.json").write_text(
        json.dumps({"date": date_iso,
                    "approval": "OK event-conditioned filter (#43); retest 2-3 paused families",
                    "results": results,
                    "aggregate": {"total": len(results),
                                  "watch_for_deep_screen": len(watch_deep),
                                  "architectural_reject": len(arch_reject),
                                  "kill": len(kill)}}, indent=2, default=str))
    print(f"\nWrote: forge_event_conditioned_retest_{date_iso}.json")
    return results


if __name__ == "__main__":
    run()
