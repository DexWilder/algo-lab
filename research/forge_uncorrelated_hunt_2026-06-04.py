"""Track 3: Uncorrelated specs hunt — non-MGC, non-NFP, non-XB-ORB families.

Per operator approval (#41, post-Packet-#1 diversification): prioritize
genuinely uncorrelated families.

Candidates this cycle (all using existing primitives):

  1. EVT-OpEx-Friday-MES-3rd-Friday-close  — 3rd Friday of each month at 16:00 ET
     (monthly OpEx for SPX/equity-index options). Tests post-OpEx drift / next-
     Monday open mean-reversion. Different time-of-day (close window) AND
     different mechanism (microstructure rebalance).

  2. EVT-OpEx-Friday-MES-3rd-Friday-morning  — same dates but 09:35 entry +
     6h hold (intraday OpEx-day drift). Different intraday window.

  3. EVT-Fed-Minutes-MES-Drift  — FOMC minutes released 3 weeks after each
     scheduled FOMC meeting at 14:00 ET. Different macro event from FOMC drift
     (which was killed); minutes have different information content than
     statement.

  4. EVT-Russell-Rebalance-MES-Long  — last Friday of June (annual Russell
     reconstitution) at 16:00 ET, plus quarterly rebalance days (last Friday
     of March/June/September/December). High-volume index rebalance flow.

  5. EVT-Month-End-MES-Last-Bus-Day  — last business day of each month at
     15:30 ET (pension/index rebalance flows). Cheap to test.

  6. EVT-First-Bus-Day-MES-First-Bus-Day  — first business day of each month
     at 09:35 ET (month-start inflows).

All non-MGC, non-NFP, non-XB-ORB family. Most are MES (equity index futures
microstructure events).

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
# Calendars
# ─────────────────────────────────────────────────────────────────────────────

def nth_weekday(year, month, weekday, n):
    """nth occurrence of weekday in (year, month). weekday 0=Mon..6=Sun."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return date(year, month, 1 + offset + (n - 1) * 7)


def third_friday(year, month):
    return nth_weekday(year, month, 4, 3)  # Fri=4


def last_friday(year, month):
    _, ndays = monthrange(year, month)
    last = date(year, month, ndays)
    offset = (last.weekday() - 4) % 7
    return last - timedelta(days=offset)


def last_business_day(year, month):
    _, ndays = monthrange(year, month)
    d = date(year, month, ndays)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def first_business_day(year, month):
    d = date(year, month, 1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def opex_calendar(start=2019, end=2026, time_str="16:00:00"):
    out = []
    for y in range(start, end + 1):
        for m in range(1, 13):
            out.append(pd.to_datetime(f"{third_friday(y, m)} {time_str}"))
    return out


def opex_morning_calendar(start=2019, end=2026, time_str="09:35:00"):
    out = []
    for y in range(start, end + 1):
        for m in range(1, 13):
            out.append(pd.to_datetime(f"{third_friday(y, m)} {time_str}"))
    return out


def russell_calendar(start=2019, end=2026, time_str="16:00:00"):
    """Last Friday of June (annual) + last Friday of March/September/December
    (quarterly rebalance)."""
    out = []
    for y in range(start, end + 1):
        for m in (3, 6, 9, 12):
            out.append(pd.to_datetime(f"{last_friday(y, m)} {time_str}"))
    return out


def month_end_calendar(start=2019, end=2026, time_str="15:30:00"):
    out = []
    for y in range(start, end + 1):
        for m in range(1, 13):
            out.append(pd.to_datetime(f"{last_business_day(y, m)} {time_str}"))
    return out


def first_day_calendar(start=2019, end=2026, time_str="09:35:00"):
    out = []
    for y in range(start, end + 1):
        for m in range(1, 13):
            out.append(pd.to_datetime(f"{first_business_day(y, m)} {time_str}"))
    return out


def fed_minutes_calendar(start=2019, end=2026, time_str="14:00:00"):
    """Approximation: 3 weeks (21 days) after each scheduled FOMC meeting.
    Source: FOMC scheduled-meeting dates 2019-2026 (from forge_fomc_drift_screen)."""
    from research.forge_fomc_drift_screen import FOMC_MEETINGS
    out = []
    for d_str in FOMC_MEETINGS:
        d = datetime.strptime(d_str, "%Y-%m-%d") + timedelta(days=21)
        out.append(pd.to_datetime(f"{d.date()} {time_str}"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Forge laws
# ─────────────────────────────────────────────────────────────────────────────

def _classify_cheap(m):
    n = m.get("n", 0); pf = m.get("pf", 0); median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 10:
        return f"KILL (n={n})"
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
                     "net": float(pnl.sum()),
                     "start": str(sub.iloc[0]["entry_dt"].date()),
                     "end": str(sub.iloc[-1]["entry_dt"].date())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year)}


def _doctrine(m, ts):
    v = _classify_cheap(m)
    if v != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v
    if ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (<50% yrs+)"
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)"
    if m["pf"] >= 1.30 and m["median"] > 0 and ts["yrs_pos"] >= ts["n_yrs"] * 0.75:
        return "WATCH_FOR_DEEP_SCREEN (passed temporal)"
    return "WATCH (passed temporal; modest)"


def run_event(asset, events, label, direction, entry_off=1, exit_off=24):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_off,
        exit_offset_bars=exit_off, direction=direction,
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    vc = _classify_cheap(m)
    ts = temporal_split(res["trades_df"]) if vc == "TEMPORAL_SPLIT_REQUIRED" else None
    v = _doctrine(m, ts)
    return m, ts, vc, v


def run():
    print("Track 3: Uncorrelated specs hunt — non-MGC, non-NFP, non-XB-ORB\n")

    families = [
        ("OpEx close", opex_calendar()),
        ("OpEx morning", opex_morning_calendar()),
        ("Russell rebalance (Mar/Jun/Sep/Dec)", russell_calendar()),
        ("Month-end (15:30 ET last bus day)", month_end_calendar()),
        ("First-of-month (09:35 ET)", first_day_calendar()),
        ("Fed minutes (FOMC + 21d)", fed_minutes_calendar()),
    ]

    results = []
    for fam_name, events in families:
        print(f"\n=== {fam_name} ({len(events)} events) ===")
        for asset in ("MES", "MNQ"):
            for direction in ("long", "short"):
                for exit_bars, exit_tag in [(6, "30min"), (24, "2h")]:
                    label = f"EVT-{fam_name.replace(' ', '-')[:24]}-{asset}-{direction[0].upper()}-{exit_tag}"
                    m, ts, vc, v = run_event(asset, events, label, direction,
                                              entry_off=1, exit_off=exit_bars)
                    max_yr = m.get("max_year_share_pct", float("nan"))
                    n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
                    yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
                    print(f"  {label:55s}: n={m['n']:3d} PF={m['pf']:.3f} median=${m['median']:8.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} → {v}")
                    results.append({
                        "family": fam_name,
                        "label": label,
                        "asset": asset,
                        "direction": direction,
                        "exit_bars": exit_bars,
                        "metrics": {k: m.get(k) for k in (
                            "n", "pf", "median", "net", "max_year_share_pct",
                            "top3_share_pct", "h1_pf", "h2_pf",
                            "years_positive", "n_years",
                        )},
                        "temporal_split": ts,
                        "cheap_verdict": vc,
                        "doctrine_verdict": v,
                    })

    # Aggregate
    watch_deep = [r for r in results if "WATCH_FOR_DEEP_SCREEN" in r["doctrine_verdict"]]
    arch_reject = [r for r in results if "ARCHITECTURAL_REJECT" in r["doctrine_verdict"]]
    watch_mod = [r for r in results if r["doctrine_verdict"].startswith("WATCH (passed")]
    kill = [r for r in results if r["doctrine_verdict"].startswith("KILL")]
    print(f"\n=== Aggregate ({len(results)} candidates) ===")
    print(f"  WATCH_FOR_DEEP_SCREEN: {len(watch_deep)}")
    print(f"  WATCH (modest):        {len(watch_mod)}")
    print(f"  ARCHITECTURAL_REJECT:  {len(arch_reject)}")
    print(f"  KILL:                  {len(kill)}")
    if watch_deep:
        print("\n  Headlines (WATCH_FOR_DEEP_SCREEN):")
        for r in watch_deep:
            print(f"    {r['label']}: PF={r['metrics']['pf']:.3f} median=${r['metrics']['median']:.2f}")

    # Save
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    (out_dir / f"forge_uncorrelated_hunt_{date_iso}.json").write_text(
        json.dumps({"date": date_iso,
                    "approval": "OK STRUCTURAL hunt + diversification (#38, #41)",
                    "results": results,
                    "aggregate": {
                        "total": len(results),
                        "watch_for_deep_screen": len(watch_deep),
                        "watch_modest": len(watch_mod),
                        "architectural_reject": len(arch_reject),
                        "kill": len(kill),
                    }}, indent=2, default=str)
    )
    print(f"\nWrote: forge_uncorrelated_hunt_{date_iso}.json")
    return results


if __name__ == "__main__":
    run()
