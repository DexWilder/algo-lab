"""Cycle 2026-06-15e — EVENT-window screen harness (CPI + Treasury-auction proxy).

Fork B (EVENT infra). Lane B / REPORT-ONLY. Assembles existing event infra into a
systematic multi-window screen. No promotion, no wiring.

Reuses:
  - research/forge_cpi_calendar_verified.build_verified_cpi_calendar  (90 events,
    grade DATA_REQUIRED = BLS-recall, operator-verifiable; NOT machine-fetched-official)
  - research/event_window_engine.generate_event_window_signals (entry/exit offsets,
    session-close, long/short)

Window configs per (calendar, asset):
  pre_drift_L/S : entry -12 bars (~1h before), exit at event (+12)   [pre-event drift]
  post_L_30/60/120 : entry +1 bar, hold 6/12/24 bars                 [post-event continuation, long]
  post_S_60      : entry +1 bar, hold 12 bars, short                  [post-event reversal proxy]

Calendars:
  CPI  -> verified recall calendar (DATA_REQUIRED). Assets: MNQ/MES/MGC/6E/6J.
  AUCTION -> 2nd-Wed/13:00 PROXY (LOW_GRADE, blocked_by_data for promotion).
            Assets: ZN/ZF/ZB. Sniff-test ONLY — a real TreasuryDirect multi-tenor
            calendar is required before any auction candidate is credible.

Output per config: event count, PF, median, largest event-day loss, overnight-hold
exposure, year concentration, H1/H2 split, gate verdict, calendar grade.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402

CPI_ASSETS = ["MNQ", "MES", "MGC", "6E", "6J"]
AUCTION_ASSETS = ["ZN", "ZF", "ZB"]

# entry_offset, exit_offset, session_close, direction, label
CONFIGS = [
    (-12, 12, False, "long", "pre_drift_L"),
    (-12, 12, False, "short", "pre_drift_S"),
    (1, 6, False, "long", "post_L_30m"),
    (1, 12, False, "long", "post_L_60m"),
    (1, 24, False, "long", "post_L_120m"),
    (1, 12, False, "short", "post_S_60m"),
]

_DF_CACHE = {}


def _df(asset):
    if asset not in _DF_CACHE:
        p = ROOT / "data" / "processed" / f"{asset}_5m.csv"
        _DF_CACHE[asset] = pd.read_csv(p) if p.exists() else None
    return _DF_CACHE[asset]


def _second_wed(y, m):
    d = datetime(y, m, 1)
    wed = d + timedelta(days=(2 - d.weekday()) % 7)
    return wed + timedelta(days=7)


def auction_proxy_calendar(start=2019, end=2026):
    out = []
    for y in range(start, end + 1):
        for m in range(1, 13):
            dt = _second_wed(y, m)
            out.append(pd.Timestamp(f"{dt.date()} 13:00:00"))
    return out


def cpi_events():
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
            for c in build_verified_cpi_calendar()]


def screen(asset, events, cfg) -> dict:
    eo, xo, close, direction, label = cfg
    df = _df(asset)
    if df is None:
        return {"asset": asset, "config": label, "error": "no_data"}
    cfg_a = ASSETS[asset]
    costs = get_cost_params(asset)
    # clean events: only those within data span
    dts = pd.to_datetime(df["datetime"])
    span0, span1 = dts.iloc[0], dts.iloc[-1]
    ev = [e for e in events if span0 <= e <= span1]
    sigs = generate_event_window_signals(df, events=ev, entry_offset_bars=eo,
                                         exit_offset_bars=(None if close else xo),
                                         exit_at_session_close=close,
                                         session_close_hour=(16 if close else None),
                                         direction=direction)
    res = run_backtest(df, sigs, mode="both", point_value=cfg_a["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    trades = res["trades_df"]
    m = _metrics(trades, f"{asset}-{label}", costs=res["stats"]["costs"])
    largest_day = overnight = None
    if trades is not None and not trades.empty and "pnl" in trades.columns:
        et = pd.to_datetime(trades["entry_time"])
        largest_day = round(float(trades["pnl"].astype(float).groupby(et.dt.date).sum().min()), 2)
        if "exit_time" in trades.columns:
            xt = pd.to_datetime(trades["exit_time"])
            overnight = int((xt.dt.date > et.dt.date).sum())
    return {
        "asset": asset, "config": label, "n": int(m.get("n", 0)),
        "pf": round(float(m.get("pf")), 3) if m.get("pf") == m.get("pf") else None,
        "median": round(float(m.get("median", 0)), 2),
        "win_rate_pct": round(float(m.get("win_rate_pct", 0)), 1),
        "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
        "h1_pf": round(float(m.get("h1_pf")), 3) if m.get("h1_pf") == m.get("h1_pf") else None,
        "h2_pf": round(float(m.get("h2_pf")), 3) if m.get("h2_pf") == m.get("h2_pf") else None,
        "largest_event_day_loss": largest_day,
        "overnight_holds": overnight,
        "archetype": m.get("archetype"), "gate_verdict": m.get("gate_verdict"),
    }


def run_calendar(name, events, assets, grade) -> list:
    print(f"\n===== {name} (grade={grade}, {len(events)} raw events) =====", flush=True)
    rows = []
    for asset in assets:
        for cfg in CONFIGS:
            r = screen(asset, events, cfg)
            r["calendar"] = name
            r["calendar_grade"] = grade
            rows.append(r)
            if "error" not in r:
                print(f"  {asset:4s} {r['config']:12s} n={r['n']:>3} PF={r['pf']} "
                      f"med=${r['median']} maxyr={r['max_year_share_pct']}% "
                      f"H1/H2={r['h1_pf']}/{r['h2_pf']} dayLoss=${r['largest_event_day_loss']} "
                      f"ON={r['overnight_holds']} {r['gate_verdict']}", flush=True)
            else:
                print(f"  {asset:4s} {r['config']:12s} {r['error']}", flush=True)
    return rows


def run():
    print("Cycle 2026-06-15e — EVENT-window screen harness (REPORT-ONLY)", flush=True)
    t0 = time.time()
    results = []
    results += run_calendar("CPI", cpi_events(), CPI_ASSETS,
                            "DATA_REQUIRED (BLS recall, operator-verifiable; NOT machine-fetched)")
    results += run_calendar("AUCTION_PROXY", auction_proxy_calendar(), AUCTION_ASSETS,
                            "LOW_GRADE_PROXY (2nd-Wed/13:00; blocked_by_data — needs TreasuryDirect official)")

    ok = [r for r in results if "error" not in r]
    interesting = [r for r in ok if r.get("pf") and r["pf"] >= 1.3 and r["n"] >= 20
                   and r.get("h1_pf") and r.get("h2_pf") and r["h1_pf"] > 1.0 and r["h2_pf"] > 1.0]
    print("\n=== SUMMARY ===", flush=True)
    print(f"  configs screened: {len(ok)}", flush=True)
    print(f"  candidates (PF>=1.3, n>=20, both halves PF>1): {len(interesting)}", flush=True)
    for r in sorted(interesting, key=lambda x: x['pf'], reverse=True):
        print(f"   ** {r['calendar']}/{r['asset']}/{r['config']}: PF={r['pf']} n={r['n']} "
              f"med=${r['median']} maxyr={r['max_year_share_pct']}% [{r['calendar_grade'].split('(')[0].strip()}]", flush=True)
    if not interesting:
        print("   (none clear the screen bar)", flush=True)
    print(f"  Total: {time.time()-t0:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15e_event_window_harness.json"
    out.write_text(json.dumps({
        "cycle": "2026-06-15e_event_window_harness", "mode": "Lane B report-only (Phase 1C frozen)",
        "configs": [c[4] for c in CONFIGS], "results": results,
        "candidates": interesting,
        "data_integrity": {
            "CPI": "DATA_REQUIRED — BLS training-recall calendar, operator-verifiable vs bls.gov; NOT machine-fetched-official",
            "AUCTION_PROXY": "LOW_GRADE_PROXY — 2nd-Wed/13:00 placeholder; real TreasuryDirect multi-tenor calendar REQUIRED before any auction candidate is credible (blocked_by_data)",
        },
        "boundaries": "report-only; no promotion/wiring; calendars below MACHINE_FETCHED_OFFICIAL cannot promote",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
