"""STRUCTURAL hunt — diversification track (next packet candidate).

Per operator approval (#38, post-Packet-#1): hunt for next uncorrelated packet
candidate. Non-MGC, non-NFP preferred. Use existing primitives only.

Four candidates this cycle (all canonical-rule-based calendars):

  A. EVT-EIA-MCL-Long-2h
     Event: weekly EIA Weekly Petroleum Status, Wed 10:30 ET (skip-Mondays
     in holiday weeks → Thursday). Calendar approximation: every Wednesday
     at 10:30 ET. MCL long after release. Diversifies from NFP-MGC by
     asset (crude vs gold) and event (EIA vs NFP). Different time-of-day
     (10:30 vs 08:30).

  B. EVT-EIA-MCL-Short-2h — same event, opposite direction.

  C. STRUCTURAL-CL-Settlement-Reversion — every weekday at 14:25 ET (NYMEX
     CL settlement window). Enter SHORT MCL at 14:30 (fading move into
     settlement); exit at 15:00. Different mechanism (microstructure) +
     different time-of-day (afternoon).

  D. XB-ORB-EMA-Ladder-MNQ-Afternoon — opening range break + ema_slope_vol_low
     using session_afternoon filter. Different time-of-day for equity
     index, different cohort than morning ORB workhorses.

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Calendars
# ─────────────────────────────────────────────────────────────────────────────

def build_eia_calendar(start_year=2019, end_year=2026, time_str="10:30:00"):
    """Every Wednesday at 10:30 ET — canonical EIA Weekly Petroleum Status.

    Holiday-week deferrals (release shifts to Thursday) are NOT modeled in v1;
    flag as approximation. Match rate vs actual EIA release expected ~95%.
    """
    events = []
    d = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    while d <= end:
        if d.weekday() == 2:  # Wednesday
            events.append(pd.to_datetime(f"{d.date()} {time_str}"))
        d += timedelta(days=1)
    return events


def build_cl_settlement_calendar(start_year=2019, end_year=2026, time_str="14:25:00"):
    """Every weekday at 14:25 ET — NYMEX CL settlement window approximation."""
    events = []
    d = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    while d <= end:
        if d.weekday() < 5:  # Mon-Fri
            events.append(pd.to_datetime(f"{d.date()} {time_str}"))
        d += timedelta(days=1)
    return events


# ─────────────────────────────────────────────────────────────────────────────
# Forge cheap-screen classifier (hard laws)
# ─────────────────────────────────────────────────────────────────────────────

def _classify_cheap(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 10:
        return f"KILL (insufficient-n, n={n})"
    if median < 0:
        return "KILL (median negative)"
    if pf < 1.15:
        return "KILL (PF < 1.15)"
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
        pf = float(w / l) if l > 0 else float("inf")
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
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "net": float(pnl.sum()),
                     "start": str(sub.iloc[0]["entry_dt"].date()),
                     "end": str(sub.iloc[-1]["entry_dt"].date())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year)}


def _doctrine_verdict(m, ts):
    v = _classify_cheap(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v
    if ts["n_yrs"] > 0 and ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (< 50% yrs positive)"
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (passed temporal robustness)"
    return "WATCH (passed temporal robustness; not strong enough for deep-screen)"


# ─────────────────────────────────────────────────────────────────────────────
# Runners
# ─────────────────────────────────────────────────────────────────────────────

def run_event_candidate(asset, events, label, direction, entry_offset=1,
                        exit_offset=24):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_offset,
        exit_offset_bars=exit_offset, direction=direction,
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    v_cheap = _classify_cheap(m)
    ts = None
    if v_cheap == "TEMPORAL_SPLIT_REQUIRED":
        ts = temporal_split(res["trades_df"])
    v = _doctrine_verdict(m, ts)
    return m, ts, v_cheap, v


def run_xb_candidate(asset, entry, filt, exit_name, label, params=None):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(
        df, entry_name=entry, exit_name=exit_name, filter_name=filt,
        params=params or {},
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    v_cheap = _classify_cheap(m)
    ts = None
    if v_cheap == "TEMPORAL_SPLIT_REQUIRED":
        ts = temporal_split(res["trades_df"])
    v = _doctrine_verdict(m, ts)
    return m, ts, v_cheap, v


def run():
    eia_events = build_eia_calendar(2019, 2026)
    cl_settle_events = build_cl_settlement_calendar(2019, 2026)

    print(f"\nA. EIA-MCL event-window screens (Wed 10:30 ET, {len(eia_events)} events):")
    results = []

    # A. EIA-MCL Long 2h
    m, ts, vc, v = run_event_candidate("MCL", eia_events, "EVT-EIA-MCL-Long-2h",
                                        "long", entry_offset=1, exit_offset=24)
    print(f"  EVT-EIA-MCL-Long-2h:  n={m['n']:4d} PF={m['pf']:.3f} median=${m['median']:7.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    results.append({"label": "EVT-EIA-MCL-Long-2h", "category": "EIA event-window",
                    "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net",
                                "max_year_share_pct", "top3_share_pct", "top10_share_pct",
                                "h1_pf", "h2_pf", "years_positive", "n_years")},
                    "temporal": ts, "cheap_verdict": vc, "doctrine_verdict": v})

    # B. EIA-MCL Short 2h
    m, ts, vc, v = run_event_candidate("MCL", eia_events, "EVT-EIA-MCL-Short-2h",
                                        "short", entry_offset=1, exit_offset=24)
    print(f"  EVT-EIA-MCL-Short-2h: n={m['n']:4d} PF={m['pf']:.3f} median=${m['median']:7.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    results.append({"label": "EVT-EIA-MCL-Short-2h", "category": "EIA event-window",
                    "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net",
                                "max_year_share_pct", "top3_share_pct", "top10_share_pct",
                                "h1_pf", "h2_pf", "years_positive", "n_years")},
                    "temporal": ts, "cheap_verdict": vc, "doctrine_verdict": v})

    # Also test 30min and 4h exits as quick diagnostic
    for ex_bars, ex_tag in [(6, "30min"), (48, "4h")]:
        m, ts, vc, v = run_event_candidate("MCL", eia_events,
                                            f"EVT-EIA-MCL-Long-{ex_tag}",
                                            "long", entry_offset=1, exit_offset=ex_bars)
        print(f"  EVT-EIA-MCL-Long-{ex_tag}: n={m['n']:4d} PF={m['pf']:.3f} median=${m['median']:7.2f} → {v}")
        results.append({"label": f"EVT-EIA-MCL-Long-{ex_tag}", "category": "EIA event-window",
                        "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net",
                                    "max_year_share_pct", "h1_pf", "h2_pf",
                                    "years_positive", "n_years")},
                        "temporal": ts, "cheap_verdict": vc, "doctrine_verdict": v})

    # C. STRUCTURAL: CL settlement reversion — short 5min after 14:25
    print(f"\nC. STRUCTURAL CL settlement reversion (weekday 14:25 ET, {len(cl_settle_events)} events):")
    for direction in ("long", "short"):
        for ex_bars, ex_tag in [(6, "30min-post-settle"), (12, "1h-post-settle")]:
            m, ts, vc, v = run_event_candidate("MCL", cl_settle_events,
                                                f"STR-CL-Settle-{direction.title()}-{ex_tag}",
                                                direction, entry_offset=1, exit_offset=ex_bars)
            print(f"  STR-CL-Settle-{direction.title()}-{ex_tag}: n={m['n']:4d} PF={m['pf']:.3f} median=${m['median']:7.2f} → {v}")
            results.append({"label": f"STR-CL-Settle-{direction.title()}-{ex_tag}",
                            "category": "STRUCTURAL settlement",
                            "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net",
                                        "max_year_share_pct", "h1_pf", "h2_pf",
                                        "years_positive", "n_years")},
                            "temporal": ts, "cheap_verdict": vc, "doctrine_verdict": v})

    # D. MNQ Afternoon ORB with proven trio defaults
    print(f"\nD. MNQ Afternoon ORB variants:")
    for filt, tag in [("session_afternoon", "afternoon-only"),
                       ("ema_slope_vol_low", "ema-volow-30")]:
        m, ts, vc, v = run_xb_candidate(
            "MNQ", "orb_breakout", filt, "profit_ladder",
            f"XB-ORB-EMA-{tag}-MNQ", params={"vr_threshold": 30}
        )
        print(f"  XB-ORB-EMA-{tag}-MNQ: n={m['n']:4d} PF={m['pf']:.3f} median=${m['median']:7.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
        results.append({"label": f"XB-ORB-EMA-{tag}-MNQ", "category": "MNQ ORB diversification",
                        "metrics": {k: m.get(k) for k in ("n", "pf", "median", "net",
                                    "max_year_share_pct", "top3_share_pct",
                                    "h1_pf", "h2_pf", "years_positive", "n_years")},
                        "temporal": ts, "cheap_verdict": vc, "doctrine_verdict": v})

    # Aggregate
    n_watch_deep = sum(1 for r in results if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"])
    n_watch = sum(1 for r in results if r["doctrine_verdict"].startswith("WATCH"))
    n_kill = sum(1 for r in results if r["doctrine_verdict"].startswith("KILL"))
    n_reject = sum(1 for r in results if "ARCHITECTURAL_REJECT" in r["doctrine_verdict"])
    print(f"\nAggregate ({len(results)} candidates): {n_watch_deep} WATCH_FOR_DEEP_SCREEN, "
          f"{n_watch} WATCH, {n_reject} ARCHITECTURAL_REJECT, {n_kill} KILL")

    # Write outputs
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    (out_dir / f"forge_structural_hunt_{date_iso}.json").write_text(
        json.dumps({"date": date_iso,
                    "operator_approval": "OK STRUCTURAL hunt (#38)",
                    "results": results,
                    "aggregate": {"total": len(results),
                                  "watch_for_deep_screen": n_watch_deep,
                                  "watch": n_watch, "reject": n_reject,
                                  "kill": n_kill}},
                   indent=2, default=str))
    print(f"\nWrote: forge_structural_hunt_{date_iso}.json")
    return results


if __name__ == "__main__":
    run()
