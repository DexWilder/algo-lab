"""Cycle 2026-06-15i — OPEX calendar-window directional bias (new SEASONAL family).

Lane B / REPORT-ONLY full-search. Harvest 2026-03-24_06. Genuinely new: a date-based
calendar-seasonal mechanism (not intraday momentum/reversion/vol — all exhausted).
No feed needed (OPEX = 3rd Friday monthly, computable). No promotion/wiring/mutation.

Mechanism: per monthly OPEX (3rd Friday):
  LONG window:  Mon of week-before-OPEX (Fri-11d) -> Tue of OPEX week (Fri-3d)
  SHORT window: Wed of OPEX week (Fri-2d) -> following Tue (Fri+4d)
Enter at first daily close >= window start, exit at last daily close <= window end.
Daily bars, multi-day holds. Tested on MES + MNQ.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402

ASSETS_T = ["MES", "MNQ"]


def third_fridays(y0=2019, y1=2026):
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d = date(y, m, 1)
            # first Friday
            d += timedelta(days=(4 - d.weekday()) % 7)
            out.append(d + timedelta(days=14))  # third Friday
    return out


def daily_close(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")[["datetime", "close"]]
    df["datetime"] = pd.to_datetime(df["datetime"]); df["d"] = df["datetime"].dt.date
    g = df.groupby("d")["close"].last()
    return g  # index=date, val=close


def window_trade(g, start, end, direction, pv, rt_cost):
    """Enter at first close>=start, exit at last close<=end. Return $pnl or None."""
    idx = [d for d in g.index if start <= d <= end]
    if len(idx) < 2:
        return None
    entry, exit_ = g.loc[idx[0]], g.loc[idx[-1]]
    gross = (exit_ - entry) * pv * (1 if direction == "long" else -1)
    return {"entry_date": idx[0], "exit_date": idx[-1], "pnl": gross - rt_cost}


def screen(asset):
    g = daily_close(asset)
    pv = ASSETS[asset]["point_value"]; c = get_cost_params(asset)
    rt = 2 * (c["commission_per_side"] + c["slippage_ticks"] * c["tick_size"] * pv)
    long_tr, short_tr = [], []
    for fri in third_fridays():
        lt = window_trade(g, fri - timedelta(days=11), fri - timedelta(days=3), "long", pv, rt)
        st = window_trade(g, fri - timedelta(days=2), fri + timedelta(days=4), "short", pv, rt)
        if lt: long_tr.append(lt)
        if st: short_tr.append(st)

    def metr(trs, label):
        if not trs:
            return {"label": label, "n": 0}
        td = pd.DataFrame(trs).rename(columns={"entry_date": "entry_time"})
        td["entry_time"] = pd.to_datetime(td["entry_time"])
        m = _metrics(td, label)
        pf = m.get("pf")
        return {"label": label, "n": int(m.get("n", 0)),
                "pf": round(float(pf), 3) if pf == pf else None,
                "median": round(float(m.get("median", 0)), 2),
                "net": round(float(m.get("net", 0)), 2),
                "win_rate_pct": round(float(m.get("win_rate_pct", 0)), 1),
                "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
                "gate_verdict": m.get("gate_verdict")}
    # combined (long + short as one book)
    comb = metr(long_tr + short_tr, f"{asset}-OPEX-combined")
    return {"asset": asset, "long": metr(long_tr, f"{asset}-OPEX-long"),
            "short": metr(short_tr, f"{asset}-OPEX-short"), "combined": comb}


def run():
    print("Cycle 2026-06-15i — OPEX calendar-window directional bias (REPORT-ONLY, new seasonal family)\n", flush=True)
    res = []
    for a in ASSETS_T:
        r = screen(a); res.append(r)
        for leg in ("long", "short", "combined"):
            x = r[leg]
            if x.get("n", 0):
                print(f"  {a} {leg:9s} n={x['n']:>3} PF={x['pf']} median=${x['median']} "
                      f"WR={x['win_rate_pct']}% maxyr={x['max_year_share_pct']}% -> {x['gate_verdict']}", flush=True)
            else:
                print(f"  {a} {leg:9s} no trades", flush=True)
    # any combined PF>=1.3 with reasonable concentration?
    hits = [r for r in res if r["combined"].get("pf") and r["combined"]["pf"] >= 1.3
            and r["combined"]["max_year_share_pct"] <= 50]
    print("\n=== SUMMARY ===", flush=True)
    print(f"  combined-book candidates (PF>=1.3, conc<=50%): {[r['asset'] for r in hits] or 'NONE'}", flush=True)
    print("  (seasonal n is small ~84 windows; treat as exploratory)", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15i_opex_calendar_window.json"
    out.write_text(json.dumps({"cycle": "2026-06-15i_opex_calendar_window", "mode": "Lane B report-only (new seasonal family)",
        "mechanism": "OPEX 3rd-Friday windows: long Fri-11..Fri-3, short Fri-2..Fri+4; daily closes",
        "results": res, "candidates": [r["asset"] for r in hits],
        "boundaries": "report-only; no promotion/wiring/mutation; no feed needed"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
