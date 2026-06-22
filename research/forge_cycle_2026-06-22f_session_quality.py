"""Cycle 2026-06-22f — Lane-2: SESSION-QUALITY overlay (prior-day trend-efficiency) (report-only).

New overlay family (genuinely different from vol-magnitude regime): prior-day TREND EFFICIENCY
ratio = |close-open| / (high-low) in [0,1] (high=clean trend day, low=chop/whipsaw day), LAGGED
(prior trading day -> known before today's entry, no-lookahead). Hypothesis: breakout/momentum books
(ORB, stop_run_reversal) underperform AFTER choppy tape. Overlay = filter today's trades by prior-day
efficiency regime. Overfit-guarded (retention>=60%, OOS halves, net not gutted), predeclared terciles
(NOT optimized). Books: MNQ-stop_run_reversal, MNQ-orb_breakout, MGC-orb_breakout. Report-only; no mutation.
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


def prior_day_efficiency(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    g = df.assign(date=dt.dt.normalize()).groupby("date").agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last"))
    eff = (g["c"] - g["o"]).abs() / (g["h"] - g["l"]).replace(0, np.nan)
    eff = eff.clip(0, 1).shift(1)   # PRIOR day, lagged -> no-lookahead
    eff.index = pd.to_datetime(eff.index).astype("datetime64[ns]"); return eff


def st(tr):
    p = tr["pnl"].to_numpy()
    if len(p) < 50:
        return {"n": len(p), "pf": None, "net": 0, "max_dd": 0, "h1_pf": None, "h2_pf": None}
    daily = tr.groupby("date")["pnl"].sum(); so = tr.sort_values("date"); h = len(p) // 2
    return {"n": len(p), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "max_dd": round(_maxdd(daily), 0),
            "h1_pf": round(_pf(so["pnl"].to_numpy()[:h]), 3), "h2_pf": round(_pf(so["pnl"].to_numpy()[h:]), 3)}


def run():
    print("Cycle 2026-06-22f — Lane-2 SESSION-QUALITY overlay (prior-day trend-efficiency) (REPORT-ONLY)\n", flush=True)
    print("Prior-day efficiency |c-o|/(h-l) lagged; hypothesis: momentum books bleed after choppy tape.\n", flush=True)
    results = {}
    survivors = []
    for asset, entry in (("MNQ", "stop_run_reversal"), ("MNQ", "orb_breakout"), ("MGC", "orb_breakout")):
        tr = book_trades(asset, entry); eff = prior_day_efficiency(asset)
        tr["eff"] = eff.reindex(tr["date"]).values; tr = tr.dropna(subset=["eff"])
        base = st(tr)
        # predeclared: exclude choppy-prior (eff<0.3 = whipsaw); also contrast exclude trend-prior (eff>0.7)
        parts = {"excl_choppy_prior(keep eff>=0.3)": tr[tr["eff"] >= 0.3],
                 "excl_trend_prior(keep eff<=0.7)": tr[tr["eff"] <= 0.7],
                 "trend_prior_only(eff>=0.5)": tr[tr["eff"] >= 0.5]}
        print(f"  {asset}-{entry}: baseline n={base['n']} PF={base['pf']} net=${base['net']} maxDD=${base['max_dd']}", flush=True)
        best = None
        for tag, sub in parts.items():
            if len(sub) < 150:
                print(f"    {tag:<34} n={len(sub)} (too few)", flush=True); continue
            s = st(sub); retain = round(len(sub) / base["n"] * 100, 1)
            dd_better = s["max_dd"] > base["max_dd"] + 200; pf_better = (s["pf"] or 0) >= base["pf"] + 0.1
            net_ok = s["net"] >= 0.9 * base["net"]; oos = (s["h1_pf"] or 0) > 1.0 and (s["h2_pf"] or 0) > 1.0; ok_ret = retain >= 60
            v = ("SESSIONQ_IMPROVES" if ((dd_better or pf_better) and net_ok and oos and ok_ret)
                 else ("OVERFIT_RISK" if (dd_better or pf_better) and not ok_ret else "no-improvement"))
            print(f"    {tag:<34} n={s['n']} ({retain}%) PF={s['pf']} net=${s['net']} maxDD=${s['max_dd']} H1/H2={s['h1_pf']}/{s['h2_pf']} -> {v}", flush=True)
            if v == "SESSIONQ_IMPROVES":
                best = {"tag": tag, **s, "retain_pct": retain}
        results[f"{asset}-{entry}"] = {"baseline": base, "improving": best, "verdict": "SESSIONQ_IMPROVES" if best else "NO_IMPROVEMENT"}
        if best:
            survivors.append(f"{asset}-{entry}")
    print(f"\n  books improved by session-quality overlay: {survivors or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22f_session_quality.json"
    out.write_text(json.dumps({"cycle": "2026-06-22f_session_quality", "mode": "Lane-2 report-only; session-quality overlay; NON-WIRED",
        "results": results, "survivors": survivors, "boundaries": "predeclared terciles; overfit-guarded; no mutation/wiring"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; Lane-2 overlay; no mutation)", flush=True)


if __name__ == "__main__":
    run()
