"""Cycle 2026-06-16 — FX London-open session breakout (new asset class / session).

Lane B / REPORT-ONLY full-search. Harvest 2026-04-09_04. Genuinely new surface:
non-equity FX, pre-RTH London session (crossbreeding engine is RTH-only). Targets
the actual non-MNQ diversification goal. No promotion/wiring/mutation.

Mechanism: record pre-London range [Rs,Re) high/low; after Re, enter on first 5m
close breaching the range (long above / short below) within an entry window; exit at
time-stop (~1h), opposite-range stop, or 1x-range-width target. One trade/day/contract.

PER-INSTRUMENT GATE (operator 2026-06-16): 6E, 6J, 6B evaluated INDIVIDUALLY. No
pooled FX-family pass unless >=1 contract is independently viable after costs +
session-slippage stress + concentration + prop-DD.

GMT->ET DST ambiguity: data is ET-naive; London 07:00-08:00 GMT ~= 02:00-03:00 ET
(EST) or 03:00-04:00 ET (EDT). Test BOTH window mappings; require an effect to hold
in a sensible window, not be a mapping artifact.
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

FX = ["6E", "6J", "6B"]
# (range_start_ET, range_end_ET) — two candidate mappings for London 07-08 GMT
WINDOWS = {"ET_0200_0300": ("02:00", "03:00"), "ET_0300_0400": ("03:00", "04:00")}
ENTRY_SCAN_BARS = 6   # 30 min after range end to find breakout
HOLD_BARS = 12        # ~1h time-stop


def _pf(p):
    p = np.array(p); g = p[p > 0].sum(); b = -p[p < 0].sum()
    return float(g / b) if b > 0 else (float("inf") if g > 0 else 0.0)


def screen(asset, rs, re_, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    df = df.assign(dtt=dt, date=dt.dt.date, hm=dt.dt.strftime("%H:%M"))
    pv = ASSETS[asset]["point_value"]; cp = get_cost_params(asset)
    per_side = cp["commission_per_side"] + slip_mult * cp["slippage_ticks"] * cp["tick_size"] * pv
    rt = 2 * per_side
    trades = []
    for d, day in df.groupby("date", sort=True):
        day = day.reset_index(drop=True)
        rng = day[(day["hm"] >= rs) & (day["hm"] < re_)]
        if len(rng) < 6:
            continue
        rhi, rlo = rng["high"].max(), rng["low"].min()
        post = day[day["hm"] >= re_].reset_index(drop=True)
        if len(post) < 2:
            continue
        scan = post.iloc[:ENTRY_SCAN_BARS]
        entry_i = direction = None
        for i in range(len(scan)):
            c = scan["close"].iloc[i]
            if c > rhi:
                entry_i, direction = i, 1; break
            if c < rlo:
                entry_i, direction = i, -1; break
        if entry_i is None:
            continue
        entry_px = post["close"].iloc[entry_i]
        width = rhi - rlo
        stop = rlo if direction == 1 else rhi
        target = entry_px + direction * width
        # walk forward up to HOLD_BARS for stop/target/time-exit
        exit_px = None
        end_i = min(entry_i + HOLD_BARS, len(post) - 1)
        for j in range(entry_i + 1, end_i + 1):
            hi, lo = post["high"].iloc[j], post["low"].iloc[j]
            if direction == 1:
                if lo <= stop: exit_px = stop; break
                if hi >= target: exit_px = target; break
            else:
                if hi >= stop: exit_px = stop; break
                if lo <= target: exit_px = target; break
        if exit_px is None:
            exit_px = post["close"].iloc[end_i]
        pnl = direction * (exit_px - entry_px) * pv - rt
        trades.append({"date": d, "year": pd.Timestamp(d).year, "pnl": pnl, "dir": direction})
    if not trades:
        return {"asset": asset, "n": 0}
    p = np.array([t["pnl"] for t in trades]); yrs = np.array([t["year"] for t in trades])
    yr_net = {int(y): float(p[yrs == y].sum()) for y in sorted(set(yrs))}
    pos = sum(v for v in yr_net.values() if v > 0)
    maxyr = round(100 * max(yr_net.values()) / pos, 1) if pos > 0 else 0.0
    half = len(p) // 2
    return {"asset": asset, "n": len(p), "pf": round(_pf(p), 3),
            "median": round(float(np.median(p)), 2), "net": round(float(p.sum()), 0),
            "win_rate_pct": round(100 * float((p > 0).mean()), 1),
            "max_year_share_pct": maxyr, "h1_pf": round(_pf(p[:half]), 3), "h2_pf": round(_pf(p[half:]), 3),
            "largest_day_loss": round(float(p.min()), 2),
            "intraday_flat": True}  # ~1h hold, same-session


def run():
    print("Cycle 2026-06-16 — FX London-open breakout (REPORT-ONLY, per-instrument gate)\n", flush=True)
    report = {"cycle": "2026-06-16_fx_london_open_breakout", "mode": "Lane B report-only",
              "windows": WINDOWS, "per_instrument_gate": True, "results": {}}
    for wname, (rs, re_) in WINDOWS.items():
        print(f"\n===== window {wname} ({rs}-{re_} ET) =====", flush=True)
        report["results"][wname] = {}
        for a in FX:
            r = screen(a, rs, re_)
            rs2 = screen(a, rs, re_, slip_mult=2.0)  # session-slippage stress
            r["pf_2x_slip"] = rs2.get("pf") if rs2.get("n") else None
            report["results"][wname][a] = r
            if r.get("n", 0):
                print(f"  {a}: n={r['n']} PF={r['pf']} (2xslip {r['pf_2x_slip']}) median=${r['median']} "
                      f"WR={r['win_rate_pct']}% maxyr={r['max_year_share_pct']}% H1/H2={r['h1_pf']}/{r['h2_pf']} "
                      f"dayLoss=${r['largest_day_loss']}", flush=True)
            else:
                print(f"  {a}: no trades", flush=True)

    # per-instrument viability (must pass individually)
    def viable(r):
        return (r.get("pf") and r["pf"] >= 1.3 and r.get("pf_2x_slip") and r["pf_2x_slip"] >= 1.2
                and r.get("median", -1) > 0 and r.get("h1_pf", 0) > 1.0 and r.get("h2_pf", 0) > 1.0
                and r.get("max_year_share_pct", 100) <= 50 and abs(r.get("largest_day_loss", 1e9)) <= 2000)
    print("\n=== PER-INSTRUMENT VIABILITY (no pooled pass) ===", flush=True)
    any_viable = False
    for wname in WINDOWS:
        for a in FX:
            r = report["results"][wname][a]
            v = viable(r)
            if v: any_viable = True
            if r.get("n", 0):
                print(f"  {wname}/{a}: {'VIABLE' if v else 'not viable'} "
                      f"(PF {r.get('pf')}, 2xslip {r.get('pf_2x_slip')}, med ${r.get('median')}, "
                      f"maxyr {r.get('max_year_share_pct')}%, dayLoss ${r.get('largest_day_loss')})", flush=True)
    verdict = ("WATCH — >=1 FX contract independently viable" if any_viable
               else "KILL — no FX contract independently viable (no pooled pass)")
    report["verdict"] = verdict
    print(f"\n  VERDICT: {verdict}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16_fx_london_open_breakout.json"
    out.write_text(json.dumps(report, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
