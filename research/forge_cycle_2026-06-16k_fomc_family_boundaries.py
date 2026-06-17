"""Cycle 2026-06-16k — FOMC event-FAMILY boundary mapping (report-only).

Extends the ZN regime-discipline (cycle 16j) to the rest of the FOMC family so the
sleeve is a *mapped* family with known boundaries, not a one-off ZN edge:
  - ZF-FOMC: same rate-trend regime grid as ZN (is the easing/hiking split present + robust?)
  - FOMC-MNQ-1h: (a) regime grid tested against TWO candidate drivers — MNQ's own equity
    trend AND the ZN rate trend (which macro factor, if any, conditions the equity reaction?)
    and (b) hold-length sensitivity (does the edge survive different exit horizons, or is
    12 bars a tuned sweet-spot?).

Reuses the FIDELITY-GREEN executor (engine/event_executor.replay). NO mutation; NON-WIRED.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.event_executor import EventStrategySpec, replay  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402


def _pf(p):
    p = np.asarray(p, float)
    g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def _daily_close(df5):
    dt = pd.to_datetime(df5["datetime"])
    g = df5.assign(date=dt.dt.normalize()).groupby("date").agg(c=("close", "last")).reset_index()
    return g["date"].to_numpy(), g["c"].to_numpy(float)


def regime_value(dates, closes, ev_date, lookback):
    evd = pd.Timestamp(ev_date).normalize().to_datetime64()
    idx = np.searchsorted(dates, evd, side="right") - 1
    if idx < lookback or idx < 0:
        return None
    return float((closes[idx] - closes[idx - lookback]) / closes[idx - lookback])


def spec_for(name, inst, tf, eoff, xoff, **kw):
    cp = get_cost_params(inst); cfg = ASSETS[inst]
    return EventStrategySpec(name=name, instrument=inst, calendar="FOMC_official", timeframe=tf,
                             direction=1, entry_offset=eoff, exit_offset=xoff, point_value=cfg["point_value"],
                             commission_per_side=cp["commission_per_side"], slippage_ticks=cp["slippage_ticks"],
                             tick_size=cp["tick_size"], **kw)


def regime_grid(per_event, classifier_key):
    """grid over lookback x threshold for one regime classifier; returns rows + robustness."""
    grid = []
    for lb in (21, 42, 63, 84, 126):
        for thr in (0.0, 0.005, 0.01):
            up = [e["pnl"] for e in per_event if e["rv"][classifier_key].get(lb) is not None and e["rv"][classifier_key][lb] > thr]
            dn = [e["pnl"] for e in per_event if e["rv"][classifier_key].get(lb) is not None and e["rv"][classifier_key][lb] <= thr]
            grid.append({"lookback_td": lb, "threshold": thr,
                         "up": {"n": len(up), "pf": round(_pf(up), 3), "net": round(float(np.sum(up)), 2)} if up else {"n": 0},
                         "down": {"n": len(dn), "pf": round(_pf(dn), 3), "net": round(float(np.sum(dn)), 2)} if dn else {"n": 0}})
    valid = [r for r in grid if r["up"].get("n", 0) >= 8 and r["down"].get("n", 0) >= 8]
    sep = [r for r in valid if r["up"].get("pf", 0) - r["down"].get("pf", 0) >= 0.8]
    up_edge = [r for r in valid if r["up"].get("pf", 0) >= 1.5]
    frac_sep = len(sep) / len(valid) if valid else 0.0
    frac_up = len(up_edge) / len(valid) if valid else 0.0
    directional = (frac_up >= 0.9 and frac_sep >= 0.9) if valid else False
    return grid, {"valid": len(valid), "frac_up_edge": round(frac_up, 3), "frac_sep": round(frac_sep, 3),
                  "directional_robust": directional}


def clean_fomc_events(df5, fomc):
    dt = pd.to_datetime(df5["datetime"])
    ev = []
    for e in fomc:
        if e < dt.iloc[0] or e > dt.iloc[-1]:
            continue
        after = df5[dt > e].head(1)
        if len(after) and (pd.to_datetime(after["datetime"].iloc[0]) - e).total_seconds() / 60 <= 60:
            ev.append(e)
    return ev


def run():
    print("Cycle 2026-06-16k — FOMC event-family boundary mapping (REPORT-ONLY)\n", flush=True)
    fomc = [pd.Timestamp(f"{c['actual_date']} {c['actual_time_et']}") for c in build_official_fomc_calendar()]
    zn_df = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    zn_dates, zn_closes = _daily_close(zn_df)
    result = {}

    # ===== ZF-FOMC: rate-trend regime grid (mirror ZN) =====
    zf_spec = spec_for("Rates-FOMC-week-ZF", "ZF", "daily", -2, 4, stop_usd=1500, archetype="EVENT_TAIL")
    zf_df = pd.read_csv(ROOT / "data" / "processed" / "ZF_5m.csv")
    zf_dates, zf_closes = _daily_close(zf_df)
    zf_pe = []
    for ev in fomc:
        tr = replay(zf_spec, zf_df, [ev])
        if tr.empty:
            continue
        zf_pe.append({"pnl": float(tr["pnl"].iloc[0]),
                      "rv": {"own": {lb: regime_value(zf_dates, zf_closes, ev, lb) for lb in (21, 42, 63, 84, 126)}}})
    zf_base = {"n": len(zf_pe), "pf": round(_pf([e["pnl"] for e in zf_pe]), 3),
               "net": round(float(np.sum([e["pnl"] for e in zf_pe])), 2)}
    zf_grid, zf_rob = regime_grid(zf_pe, "own")
    pre = next((r for r in zf_grid if r["lookback_td"] == 42 and r["threshold"] == 0.0), None)
    print(f"ZF-FOMC baseline: {zf_base}", flush=True)
    print(f"  regime grid robustness: {zf_rob}", flush=True)
    if pre:
        print(f"  pre-registered cut (42td, sign): UP {pre['up']} / DOWN {pre['down']}", flush=True)
    result["ZF"] = {"baseline": zf_base, "regime_robustness_own_trend": zf_rob, "preregistered_42td_sign": pre}

    # ===== FOMC-MNQ-1h: two regime drivers + hold-length sensitivity =====
    mnq_df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    mnq_dates, mnq_closes = _daily_close(mnq_df)
    clean_ev = clean_fomc_events(mnq_df, fomc)
    mnq_spec = spec_for("FOMC-MNQ-Long-1h", "MNQ", "intraday_5m", 1, 12, archetype="EVENT_TAIL")
    mnq_pe = []
    for ev in clean_ev:
        tr = replay(mnq_spec, mnq_df, [ev])
        if tr.empty:
            continue
        mnq_pe.append({"pnl": float(tr["pnl"].iloc[0]),
                       "rv": {"mnq_equity": {lb: regime_value(mnq_dates, mnq_closes, ev, lb) for lb in (21, 42, 63, 84, 126)},
                              "zn_rate": {lb: regime_value(zn_dates, zn_closes, ev, lb) for lb in (21, 42, 63, 84, 126)}}})
    mnq_base = {"n": len(mnq_pe), "pf": round(_pf([e["pnl"] for e in mnq_pe]), 3),
                "net": round(float(np.sum([e["pnl"] for e in mnq_pe])), 2)}
    _, mnq_eq_rob = regime_grid(mnq_pe, "mnq_equity")
    _, mnq_rate_rob = regime_grid(mnq_pe, "zn_rate")
    print(f"\nFOMC-MNQ-1h baseline (clean events): {mnq_base}", flush=True)
    print(f"  regime grid (MNQ equity-trend driver): {mnq_eq_rob}", flush=True)
    print(f"  regime grid (ZN rate-trend driver):    {mnq_rate_rob}", flush=True)

    # hold-length sensitivity: is 12 bars tuned?
    holds = {}
    for h in (6, 8, 10, 12, 16, 20):
        sp = spec_for("FOMC-MNQ-Long-1h", "MNQ", "intraday_5m", 1, h, archetype="EVENT_TAIL")
        tr = replay(sp, mnq_df, clean_ev)
        p = tr["pnl"].to_numpy() if not tr.empty else np.array([])
        holds[h] = {"n": int(len(p)), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 2)} if len(p) else {"n": 0}
    print("  hold-length sensitivity (bars -> n/PF/net):", flush=True)
    for h, m in holds.items():
        print(f"    {h:>2}: {m}", flush=True)
    hold_pfs = [m["pf"] for m in holds.values() if m.get("n", 0) >= 20]
    hold_robust = (min(hold_pfs) >= 1.2) if hold_pfs else False
    result["MNQ"] = {"baseline": mnq_base, "regime_mnq_equity": mnq_eq_rob, "regime_zn_rate": mnq_rate_rob,
                     "hold_sensitivity": holds, "hold_robust_all_pf_ge_1.2": hold_robust}

    # ===== family verdict =====
    print("\n--- FOMC FAMILY MAP ---", flush=True)
    print(f"  ZN: regime-gated (DIRECTIONALLY_ROBUST, cycle 16j) — PRIMARY rates sleeve", flush=True)
    zf_note = ("regime-gated like ZN (confirms family)" if zf_rob["directional_robust"]
               else "regime split NOT directionally robust on own trend — treat ZF as confirmation depth only, gate off ZN")
    print(f"  ZF: {zf_note}", flush=True)
    mnq_driver = ("MNQ-equity-trend" if mnq_eq_rob["directional_robust"]
                  else ("ZN-rate-trend" if mnq_rate_rob["directional_robust"] else "NO clean regime driver"))
    print(f"  MNQ-1h: regime driver = {mnq_driver}; hold-length robust(all PF>=1.2 @n>=20)={hold_robust}", flush=True)
    print("\n  (report-only; reuses fidelity-green executor; NON-WIRED; no mutation)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16k_fomc_family_boundaries.json"
    out.write_text(json.dumps({"cycle": "2026-06-16k_fomc_family_boundaries",
        "mode": "Lane B report-only; reuses fidelity-green executor; NON-WIRED",
        "zf": result["ZF"], "mnq": result["MNQ"],
        "family_map": {"ZN": "regime-gated PRIMARY (16j)", "ZF": zf_note, "MNQ_1h_driver": mnq_driver,
                       "MNQ_hold_robust": hold_robust},
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
