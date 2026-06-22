"""Cycle 2026-06-22d — Lane-2: VOL-REGIME OVERLAY on existing strong books (report-only).

Active-by-default lane (NOT a WH2 price-pattern screen — that class is mapped). Improve EXISTING
books via a risk OVERLAY (no new entry): does excluding the worst realized-vol regime lift net-PF
and/or cut max-DD with acceptable retention? Targets the real prize: DD reduction on the wired/strong
books. Overlay = entry-day ATR-percentile regime (LAGGED, no-lookahead) partition of the book's own trades.

Books: MNQ-stop_run_reversal (worst incumbent DD -$4018), MNQ-orb_breakout, MGC-orb_breakout.
Discipline: overfit guard (retention >=60%, n>=150), per-year, OOS halves. Classify
OVERLAY_IMPROVES (clearly better net-PF or DD, retention OK, OOS-consistent) / NO_IMPROVEMENT / OVERFIT_RISK.
No sweep, no mutation, no wiring (report-only research even on the wired book).
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
    g = df.assign(date=dt.dt.normalize()).groupby("date").agg(h=("high", "max"), l=("low", "min"), c=("close", "last"))
    tr_range = (g["h"] - g["l"])
    atr = tr_range.rolling(14).mean()
    # percentile rank of today's ATR vs trailing 252d (LAGGED: use prior-day atr for entry-day regime)
    pct = atr.rolling(252, min_periods=60).apply(lambda x: (x.iloc[-1] >= x).mean(), raw=False)
    out = pd.DataFrame({"atr_pct": pct.shift(1)})  # shift -> regime known before entry day
    out.index = pd.to_datetime(out.index).astype("datetime64[ns]"); return out["atr_pct"]


def stats(tr):
    p = tr["pnl"].to_numpy();
    if len(p) < 50:
        return {"n": len(p), "pf": None}
    daily = tr.groupby("date")["pnl"].sum()
    py = tr.assign(yr=pd.to_datetime(tr["date"]).dt.year).groupby("yr")["pnl"].sum()
    h = len(p) // 2; so = tr.sort_values("date")
    return {"n": len(p), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0), "max_dd": round(_maxdd(daily), 0),
            "median": round(float(np.median(p)), 2), "h1_pf": round(_pf(so["pnl"].to_numpy()[:h]), 3),
            "h2_pf": round(_pf(so["pnl"].to_numpy()[h:]), 3), "yrs_pos": f"{int((py>0).sum())}/{int(py.shape[0])}"}


def run():
    print("Cycle 2026-06-22d — Lane-2 VOL-REGIME OVERLAY on existing books (REPORT-ONLY)\n", flush=True)
    print("No new entry; filter existing trades by lagged entry-day ATR-percentile regime. Prize = DD reduction.\n", flush=True)
    BOOKS = [("MNQ", "stop_run_reversal"), ("MNQ", "orb_breakout"), ("MGC", "orb_breakout")]
    results = {}
    for asset, entry in BOOKS:
        tr = book_trades(asset, entry)
        atrp = daily_atr_pctile(asset)
        tr["regime"] = atrp.reindex(tr["date"]).values
        tr = tr.dropna(subset=["regime"])
        base = stats(tr); base_dd = base["max_dd"]
        print(f"  {asset}-{entry}: baseline n={base['n']} PF={base['pf']} net=${base['net']} maxDD=${base_dd} yrs+={base['yrs_pos']}", flush=True)
        # predeclared overlays: exclude high-vol (>0.8), exclude low-vol (<0.2), keep mid (0.2-0.8)
        parts = {"excl_high_vol(keep<=0.8)": tr[tr["regime"] <= 0.8],
                 "excl_low_vol(keep>=0.2)": tr[tr["regime"] >= 0.2],
                 "mid_vol_only(0.2-0.8)": tr[(tr["regime"] >= 0.2) & (tr["regime"] <= 0.8)]}
        best = None
        for tag, sub in parts.items():
            if len(sub) < 150:
                print(f"    {tag:<26} n={len(sub)} (too few)", flush=True); continue
            s = stats(sub); retain = round(len(sub) / base["n"] * 100, 1)
            dd_better = s["max_dd"] > base_dd + 200      # less negative by >$200
            pf_better = (s["pf"] or 0) >= (base["pf"] or 0) + 0.1
            net_keeps = (s["net"] or 0) >= 0.9 * (base["net"] or 0)   # didn't gut returns
            oos_ok = (s["h1_pf"] or 0) > 1.0 and (s["h2_pf"] or 0) > 1.0
            ok_retain = retain >= 60
            verdict = ("OVERLAY_IMPROVES" if ((dd_better or pf_better) and net_keeps and oos_ok and ok_retain)
                       else ("OVERFIT_RISK" if (dd_better or pf_better) and not ok_retain else "no-improvement"))
            print(f"    {tag:<26} n={s['n']} ({retain}%) PF={s['pf']} net=${s['net']} maxDD=${s['max_dd']} "
                  f"H1/H2={s['h1_pf']}/{s['h2_pf']} -> {verdict}", flush=True)
            if verdict == "OVERLAY_IMPROVES":
                best = {"tag": tag, **s, "retain_pct": retain}
        results[f"{asset}-{entry}"] = {"baseline": base, "improving_overlay": best,
                                       "verdict": "OVERLAY_IMPROVES" if best else "NO_IMPROVEMENT"}
    survivors = [k for k, v in results.items() if v["verdict"] == "OVERLAY_IMPROVES"]
    print(f"\n  books improved by vol-regime overlay: {survivors or 'none'}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-22d_vol_regime_overlay.json"
    out.write_text(json.dumps({"cycle": "2026-06-22d_vol_regime_overlay", "mode": "Lane-2 report-only; risk overlay; NON-WIRED",
        "results": results, "survivors": survivors, "note": "overlay on existing books (no new entry); overfit-guarded; report-only even on wired book",
        "boundaries": "no sweep/mutation/wiring"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; Lane-2 overlay; no mutation)", flush=True)


if __name__ == "__main__":
    run()
