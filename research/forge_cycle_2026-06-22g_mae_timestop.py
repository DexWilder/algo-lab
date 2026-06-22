"""Cycle 2026-06-22g — Lane-2: MAE-guard + TIME-STOP overlays (intra-trade path) (report-only).

Two genuinely-different overlay families needing the intra-trade path (reconstructed from 5m bars
between entry/exit per trade, using side+entry_price). PREDECLARED sparse thresholds (NOT optimized).
  (A) MAE GUARD: hard stop at adverse-excursion level L. If trade's MAE <= -L, assume stopped at -L
      (turns deep losers into -L; cost = stops out some trades that would've recovered). Good guard
      cuts left-tail/DD without gutting net. Predeclared L per instrument.
  (B) TIME-STOP / no-progress: if unrealized PnL <= 0 at bar N, exit at bar N (cut trades that never
      worked). Predeclared N in {6,12,24} bars (30/60/120 min). Not optimized for best bar.
Books: MNQ-stop_run_reversal (worst DD -4018, wired), MNQ-orb_breakout, MGC-orb_breakout.
Overfit lens: report all thresholds, look for STABLE improvement, net not gutted. Report-only; no mutation.
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
from engine.backtest import get_cost_params, run_backtest  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals as gcs  # noqa: E402

MAE_LEVELS = {"MNQ": [150, 250, 400], "MGC": [150, 250, 400]}   # $ per contract, predeclared
NBARS = [6, 12, 24]


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def _dd(daily):
    c = daily.sort_index().cumsum(); return float((c - c.cummax()).min())


def analyze(asset, entry):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["dt"] = pd.to_datetime(df["datetime"]); cfg = ASSETS[asset]; cp = get_cost_params(asset); pv = cfg["point_value"]
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
    s = gcs(df.drop(columns=["dt"]), entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    res = run_backtest(df.drop(columns=["dt"]), s, mode="both", point_value=pv, symbol=asset,
                       commission_per_side=cp["commission_per_side"], slippage_ticks=cp["slippage_ticks"], tick_size=cp["tick_size"])
    tr = res["trades_df"].copy()
    idx = df.set_index("dt")[["high", "low", "close"]].sort_index()
    # per-trade MAE + pnl-at-bar-N
    mae = np.zeros(len(tr)); pnlN = {n: np.zeros(len(tr)) for n in NBARS}
    et = pd.to_datetime(tr["entry_time"]).values; xt = pd.to_datetime(tr["exit_time"]).values
    sign = np.where(tr["side"].values == "long", 1.0, -1.0); ep = tr["entry_price"].values
    actual = tr["pnl"].values
    ii = idx.index.values; H = idx["high"].values; L = idx["low"].values; C = idx["close"].values
    for k in range(len(tr)):
        a = np.searchsorted(ii, et[k]); b = np.searchsorted(ii, xt[k], side="right")
        if b <= a:
            mae[k] = 0.0
            for n in NBARS:
                pnlN[n][k] = actual[k]
            continue
        hh = H[a:b]; ll = L[a:b]; cc = C[a:b]
        # adverse excursion ($, negative)
        if sign[k] == 1:
            mae[k] = (ll.min() - ep[k]) * pv
        else:
            mae[k] = (ep[k] - hh.max()) * pv
        for n in NBARS:
            j = min(n, len(cc)) - 1
            pnlN[n][k] = sign[k] * (cc[j] - ep[k]) * pv - rt
    tr["mae"] = mae; tr["date"] = pd.to_datetime(tr["entry_time"]).dt.normalize()
    for n in NBARS:
        tr[f"pnlN{n}"] = pnlN[n]
    return tr, actual, rt


def book_stats(pnl, dates):
    p = np.asarray(pnl, float); daily = pd.Series(p, index=pd.to_datetime(dates)).groupby(level=0).sum()
    return {"pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "max_dd": round(_dd(daily), 0),
            "worst": round(float(p.min()), 0)}


def run():
    print("Cycle 2026-06-22g — Lane-2 MAE-guard + TIME-STOP overlays (REPORT-ONLY)\n", flush=True)
    out_all = {}
    for asset, entry in (("MNQ", "stop_run_reversal"), ("MNQ", "orb_breakout"), ("MGC", "orb_breakout")):
        tr, actual, rt = analyze(asset, entry)
        base = book_stats(actual, tr["date"]); dates = tr["date"].values
        print(f"  {asset}-{entry}: baseline PF={base['pf']} net=${base['net']} maxDD=${base['max_dd']} worst=${base['worst']} n={len(tr)}", flush=True)
        res = {"baseline": base, "mae_guard": {}, "time_stop": {}}
        # (A) MAE guard
        for L in MAE_LEVELS[asset.replace('MNQ', 'MNQ').replace('MGC', 'MGC') if asset in ('MNQ', 'MGC') else asset] if asset in MAE_LEVELS else MAE_LEVELS.get(asset, [200]):
            stopped = np.where(tr["mae"].values <= -L, -L, actual)
            s = book_stats(stopped, dates)
            dd_better = s["max_dd"] > base["max_dd"] + 150; worst_better = s["worst"] > base["worst"] + 50
            net_ok = s["net"] >= 0.85 * base["net"]
            v = "IMPROVES" if (dd_better or worst_better) and net_ok and (s["pf"] >= base["pf"] - 0.03) else "no-improvement"
            res["mae_guard"][f"L{L}"] = {**s, "verdict": v}
            print(f"    MAE-stop ${L}: PF={s['pf']} net=${s['net']} maxDD=${s['max_dd']} worst=${s['worst']} -> {v}", flush=True)
        # (B) time-stop / no-progress
        for n in NBARS:
            ts = np.where(tr[f"pnlN{n}"].values <= 0, tr[f"pnlN{n}"].values, actual)
            s = book_stats(ts, dates)
            dd_better = s["max_dd"] > base["max_dd"] + 150; net_ok = s["net"] >= 0.85 * base["net"]
            v = "IMPROVES" if (dd_better or s["pf"] >= base["pf"] + 0.1) and net_ok else "no-improvement"
            res["time_stop"][f"N{n}"] = {**s, "verdict": v}
            print(f"    time-stop@{n}bars(no-progress): PF={s['pf']} net=${s['net']} maxDD=${s['max_dd']} worst=${s['worst']} -> {v}", flush=True)
        out_all[f"{asset}-{entry}"] = res
        print("", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22g_mae_timestop.json"
    out.write_text(json.dumps({"cycle": "2026-06-22g_mae_timestop", "mode": "Lane-2 report-only; MAE+time-stop overlays; NON-WIRED",
        "results": out_all, "note": "intra-trade path reconstructed from 5m; predeclared sparse thresholds; MAE-stop fill approx at -L (caveat)",
        "boundaries": "no optimization/mutation/wiring"}, indent=2, default=str))
    print(f"Wrote: {out}\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
