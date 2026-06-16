"""Cycle 2026-06-16b — Overnight gap-bucket (BOUNDARY-COMPLETION test).

Lane B / REPORT-ONLY. Harvest 2026-03-25_08. Last generic testable-now surface.
Classify overnight gap by size bucket vs recent RTH range; small/moderate -> gap-FILL
(fade toward prior close), large -> gap-HOLD (continuation). Intraday-flat (exit by
session close) -> prop-friendly by construction. Per-instrument gate (MES/MNQ/MGC/MCL).
No promotion/wiring/mutation. Boundary completion, not high-expectancy discovery.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402

ASSETS_T = ["MES", "MNQ", "MGC", "MCL"]
SMALL_MAX = 0.75   # |gap/atr| <= this -> gap-fill (fade); above -> gap-hold (continuation)


def _pf(p):
    p = np.array(p); g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def daily_rth(df):
    rth = df[(df["hm"] >= "09:30") & (df["hm"] < "16:00")]
    g = rth.groupby("date").agg(o=("open", "first"), c=("close", "last"),
                                h=("high", "max"), l=("low", "min"))
    g["rng"] = g["h"] - g["l"]; g["atr"] = g["rng"].rolling(14).mean()
    return g, rth


def screen(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    df = df.assign(date=dt.dt.date, hm=dt.dt.strftime("%H:%M"))
    g, rth = daily_rth(df)
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    dates = list(g.index)
    fill, hold = [], []
    rth_by_date = {d: x.reset_index(drop=True) for d, x in rth.groupby("date")}
    for k in range(1, len(dates)):
        d, pd_ = dates[k], dates[k - 1]
        atr = g["atr"].iloc[k - 1]; pc = g["c"].iloc[k - 1]
        if not np.isfinite(atr) or atr <= 0:
            continue
        day = rth_by_date.get(d)
        if day is None or len(day) < 5:
            continue
        op = day["close"].iloc[0]  # RTH open (first bar close)
        gap = op - pc; gatr = gap / atr
        if abs(gatr) < 0.05:
            continue
        # walk intraday for stop/target/close
        hi = day["high"].values; lo = day["low"].values; cl = day["close"].values
        if abs(gatr) <= SMALL_MAX:  # gap-FILL: fade toward prior close
            direction = -int(np.sign(gap))
            target = pc; stop = op + np.sign(gap) * abs(gap)  # gap extends -> stop
            book = fill
        else:  # gap-HOLD: continuation
            direction = int(np.sign(gap))
            stop = pc; target = op + np.sign(gap) * abs(gap)  # extend
            book = hold
        exit_px = None
        for j in range(1, len(day)):
            if direction == 1:
                if lo[j] <= min(stop, target) and stop < target: exit_px = stop; break
                if hi[j] >= target and target > stop: exit_px = target; break
                if lo[j] <= stop and stop < op: exit_px = stop; break
            else:
                if hi[j] >= max(stop, target) and stop > target: exit_px = stop; break
                if lo[j] <= target and target < stop: exit_px = target; break
                if hi[j] >= stop and stop > op: exit_px = stop; break
        if exit_px is None:
            exit_px = cl[-1]
        pnl = direction * (exit_px - op) * pv - rt
        book.append({"year": pd.Timestamp(d).year, "pnl": pnl})

    def book_metrics(b, label):
        if not b:
            return {"label": label, "n": 0}
        p = np.array([t["pnl"] for t in b]); yrs = np.array([t["year"] for t in b])
        yn = {int(y): float(p[yrs == y].sum()) for y in set(yrs)}
        pos = sum(v for v in yn.values() if v > 0)
        maxyr = round(100 * max(yn.values()) / pos, 1) if pos > 0 else 0.0
        half = len(p) // 2
        return {"label": label, "n": len(p), "pf": round(_pf(p), 3),
                "median": round(float(np.median(p)), 2), "win_rate_pct": round(100 * float((p > 0).mean()), 1),
                "max_year_share_pct": maxyr, "h1_pf": round(_pf(p[:half]), 3), "h2_pf": round(_pf(p[half:]), 3),
                "largest_day_loss": round(float(p.min()), 2)}
    return {"asset": asset, "gap_fill": book_metrics(fill, f"{asset}-gapfill"),
            "gap_hold": book_metrics(hold, f"{asset}-gaphold")}


def viable(m):
    return (m.get("pf") and m["pf"] >= 1.3 and m.get("median", -1) > 0
            and m.get("h1_pf", 0) > 1.0 and m.get("h2_pf", 0) > 1.0
            and m.get("max_year_share_pct", 100) <= 50 and abs(m.get("largest_day_loss", 1e9)) <= 2000)


def run():
    print("Cycle 2026-06-16b — overnight gap-bucket (REPORT-ONLY, boundary completion)\n", flush=True)
    res = {}; any_v = False
    for a in ASSETS_T:
        r = screen(a); res[a] = r
        for leg in ("gap_fill", "gap_hold"):
            m = r[leg]
            if m.get("n", 0):
                v = viable(m); any_v = any_v or v
                print(f"  {a} {leg:9s} n={m['n']:>4} PF={m['pf']} med=${m['median']} WR={m['win_rate_pct']}% "
                      f"maxyr={m['max_year_share_pct']}% H1/H2={m['h1_pf']}/{m['h2_pf']} dayLoss=${m['largest_day_loss']} "
                      f"{'VIABLE' if v else ''}", flush=True)
            else:
                print(f"  {a} {leg:9s} no trades", flush=True)
    verdict = "WATCH — >=1 gap book independently viable" if any_v else "KILL — no gap book independently viable"
    print(f"\n  VERDICT: {verdict}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16b_overnight_gap_bucket.json"
    out.write_text(json.dumps({"cycle": "2026-06-16b_overnight_gap_bucket", "mode": "Lane B report-only (boundary completion)",
        "small_max_gap_atr": SMALL_MAX, "results": res, "verdict": verdict,
        "boundaries": "report-only; no promotion/wiring/mutation; intraday-flat; per-instrument gate"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
