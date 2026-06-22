"""Cycle 2026-06-22e — Lane-2 overlay robustness + new family (report-only).

(1) ROBUSTNESS CONFIRMATION (NOT optimization) of the MGC-ORB low-vol exclusion: test the SAME
    overlay at PREDECLARED nearby thresholds {0.10,0.15,0.20,0.25,0.30}. Verdict ROBUST only if the
    DD-improvement holds across MOST of the band (effect stable, not a single lucky point); do NOT
    pick the best threshold.
(2) NEW OVERLAY FAMILY: day-after-loss-day THROTTLE (skip trades the day after the book had a losing
    day -> tests loss-clustering/persistence). Contrast: skip-after-WIN (sanity). On all 3 strong books.
Overfit-guarded (retention>=60%, OOS halves, net not gutted). Report-only; no mutation/wiring.
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


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def _maxdd(daily):
    c = daily.sort_index().cumsum(); return float((c - c.cummax()).min())


def book_trades(asset, entry):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); cfg = ASSETS[asset]; cp = get_cost_params(asset)
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    tr = run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol=asset,
                      commission_per_side=cp["commission_per_side"], slippage_ticks=cp["slippage_ticks"], tick_size=cp["tick_size"])["trades_df"]
    tr = tr.copy(); tr["date"] = pd.to_datetime(tr["entry_time"]).dt.normalize().astype("datetime64[ns]"); return tr


def daily_atr_pctile(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    g = df.assign(date=dt.dt.normalize()).groupby("date").agg(h=("high", "max"), l=("low", "min"))
    atr = (g["h"] - g["l"]).rolling(14).mean()
    pct = atr.rolling(252, min_periods=60).apply(lambda x: (x.iloc[-1] >= x).mean(), raw=False).shift(1)
    pct.index = pd.to_datetime(pct.index).astype("datetime64[ns]"); return pct


def st(tr):
    p = tr["pnl"].to_numpy()
    if len(p) < 50:
        return {"n": len(p), "pf": None, "net": 0, "max_dd": 0, "h1_pf": None, "h2_pf": None}
    daily = tr.groupby("date")["pnl"].sum(); so = tr.sort_values("date"); h = len(p) // 2
    return {"n": len(p), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "max_dd": round(_maxdd(daily), 0),
            "h1_pf": round(_pf(so["pnl"].to_numpy()[:h]), 3), "h2_pf": round(_pf(so["pnl"].to_numpy()[h:]), 3)}


def run():
    print("Cycle 2026-06-22e — Lane-2 overlay robustness + new family (REPORT-ONLY)\n", flush=True)

    # (1) MGC-ORB low-vol exclusion robustness band
    print("(1) MGC-ORB low-vol exclusion ROBUSTNESS (predeclared thresholds; confirm stability, NOT optimize):", flush=True)
    tr = book_trades("MGC", "orb_breakout"); pct = daily_atr_pctile("MGC")
    tr["regime"] = pct.reindex(tr["date"]).values; tr = tr.dropna(subset=["regime"])
    base = st(tr); print(f"  baseline: n={base['n']} PF={base['pf']} net=${base['net']} maxDD=${base['max_dd']}", flush=True)
    band = {}
    improved_count = 0
    for thr in (0.10, 0.15, 0.20, 0.25, 0.30):
        sub = tr[tr["regime"] >= thr]; s = st(sub); retain = round(len(sub) / base["n"] * 100, 1)
        dd_better = s["max_dd"] > base["max_dd"] + 100; net_ok = s["net"] >= 0.9 * base["net"]; pf_ok = (s["pf"] or 0) >= base["pf"] - 0.03
        good = dd_better and net_ok and pf_ok and retain >= 60
        improved_count += good
        band[str(thr)] = {**s, "retain_pct": retain, "dd_better": dd_better, "good": good}
        print(f"    thr={thr}: n={s['n']} ({retain}%) PF={s['pf']} net=${s['net']} maxDD=${s['max_dd']} {'[DD-better]' if dd_better else ''} {'OK' if good else ''}", flush=True)
    rob = "ROBUST" if improved_count >= 4 else ("PARTIAL" if improved_count >= 3 else "FRAGILE(single-point)")
    print(f"  -> band DD-improvement holds at {improved_count}/5 thresholds -> {rob}", flush=True)

    # (2) day-after-loss-day throttle (new overlay family) on 3 books
    print("\n(2) DAY-AFTER-LOSS THROTTLE (new family; skip day after a losing book-day; +contrast skip-after-win):", flush=True)
    throttle = {}
    for asset, entry in (("MNQ", "stop_run_reversal"), ("MNQ", "orb_breakout"), ("MGC", "orb_breakout")):
        t = book_trades(asset, entry)
        daily = t.groupby("date")["pnl"].sum().sort_index()
        prior_loss = (daily.shift(1) < 0)  # was prior book-trading-day a loss?
        prior_win = (daily.shift(1) > 0)
        loss_days = set(daily.index[prior_loss.fillna(False)]); win_days = set(daily.index[prior_win.fillna(False)])
        base = st(t)
        after_nonloss = st(t[~t["date"].isin(loss_days)])     # throttle: skip day-after-loss
        after_nonwin = st(t[~t["date"].isin(win_days)])       # contrast: skip day-after-win
        rt_n = round(after_nonloss["n"] / base["n"] * 100, 1)
        dd_better = after_nonloss["max_dd"] > base["max_dd"] + 200; net_ok = after_nonloss["net"] >= 0.85 * base["net"]
        pf_better = (after_nonloss["pf"] or 0) >= base["pf"] + 0.1
        oos = (after_nonloss["h1_pf"] or 0) > 1.0 and (after_nonloss["h2_pf"] or 0) > 1.0
        v = "THROTTLE_IMPROVES" if ((dd_better or pf_better) and net_ok and oos and rt_n >= 60) else ("OVERFIT_RISK" if (dd_better or pf_better) and rt_n < 60 else "no-improvement")
        throttle[f"{asset}-{entry}"] = {"baseline": base, "skip_after_loss": {**after_nonloss, "retain_pct": rt_n}, "skip_after_win": after_nonwin, "verdict": v}
        print(f"  {asset}-{entry}: base PF={base['pf']} net=${base['net']} DD=${base['max_dd']}", flush=True)
        print(f"     skip-after-LOSS: n={after_nonloss['n']} ({rt_n}%) PF={after_nonloss['pf']} net=${after_nonloss['net']} DD=${after_nonloss['max_dd']} -> {v}", flush=True)
        print(f"     skip-after-WIN (contrast): PF={after_nonwin['pf']} net=${after_nonwin['net']} DD=${after_nonwin['max_dd']}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22e_overlay_robustness.json"
    out.write_text(json.dumps({"cycle": "2026-06-22e_overlay_robustness", "mode": "Lane-2 report-only; overlay robustness + new family; NON-WIRED",
        "mgc_lowvol_band": band, "mgc_lowvol_robustness": rob, "day_after_loss_throttle": throttle,
        "boundaries": "predeclared thresholds (not optimized); overfit-guarded; no mutation/wiring"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
