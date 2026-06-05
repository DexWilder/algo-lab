"""DIR-MGC-ORB-Short-PL family review vs XB-ORB-EMA-Ladder-MGC.

Per operator approval 2026-06-05 (#73 priority). Operator hypothesis: short-
only direction may add asymmetric directional exposure against the existing
both-direction MGC workhorse.

Full 5-test protocol with all 5 outcome possibilities open.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Reuse helpers
_spec = importlib.util.spec_from_file_location(
    "mnq_review_lib", ROOT / "research" / "forge_mnq_family_review.py"
)
_lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lib)

trade_overlap_analysis = _lib.trade_overlap_analysis
pnl_correlation = _lib.pnl_correlation
daily_pnl_series = _lib.daily_pnl_series
portfolio_metrics = _lib.portfolio_metrics
controller_combined_series = _lib.controller_combined_series
classify_family_review = _lib.classify_family_review

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


def _run(asset, entry, filter_name, exit_name, params, mode, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(
        df, entry_name=entry, exit_name=exit_name,
        filter_name=filter_name, params=params or {},
    )
    res = run_backtest(df, sigs, mode=mode,
                       point_value=cfg["point_value"], symbol=asset)
    trades = res["trades_df"].copy()
    if not trades.empty:
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        trades["entry_date"] = trades["entry_dt"].dt.date
    return trades


def trade_summary(trades, label):
    if trades.empty:
        return {"label": label, "n": 0}
    pnl = trades["pnl"].values
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]
    pf = wins.sum() / -losses.sum() if losses.sum() < 0 else float("inf")
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    return {
        "label": label, "n": int(len(trades)),
        "pf": float(pf), "median": float(np.median(pnl)),
        "net_pnl": float(pnl.sum()),
        "max_dd_trade_equity": float((eq - peak).min()),
        "win_rate_pct": float((pnl > 0).mean() * 100),
        "avg_win": float(wins.mean()) if len(wins) else float("nan"),
        "avg_loss": float(losses.mean()) if len(losses) else float("nan"),
    }


def run():
    print("DIR-MGC-ORB-Short-PL family review vs XB-ORB-EMA-Ladder-MGC", flush=True)
    print("Priority test per operator #73.\n", flush=True)

    print("[Loading candidates]", flush=True)
    t_base = _run("MGC", "orb_breakout", "ema_slope", "profit_ladder", {},
                   "both", "XB-ORB-EMA-Ladder-MGC")
    t_short = _run("MGC", "orb_breakout", "ema_slope", "profit_ladder", {},
                    "short", "DIR-MGC-ORB-Short-PL")
    print(f"  Baseline (both): n={len(t_base)} trades", flush=True)
    print(f"  Short-only:      n={len(t_short)} trades", flush=True)

    print("\n[1] Standalone comparison:", flush=True)
    summ_base = trade_summary(t_base, "XB-ORB-EMA-Ladder-MGC (both)")
    summ_short = trade_summary(t_short, "DIR-MGC-ORB-Short-PL")
    for k in ("n", "pf", "median", "net_pnl", "max_dd_trade_equity",
              "win_rate_pct", "avg_win", "avg_loss"):
        print(f"    {k}: BASE={summ_base.get(k)}  |  SHORT={summ_short.get(k)}", flush=True)

    print("\n[2] Trade overlap:", flush=True)
    overlap = trade_overlap_analysis(t_base, t_short, "BASE", "SHORT")
    for k, v in overlap.items():
        print(f"    {k}: {v}", flush=True)

    print("\n[3] PnL correlation + drawdown overlap:", flush=True)
    corr = pnl_correlation(t_base, t_short)
    for k, v in corr.items():
        print(f"    {k}: {v}", flush=True)

    print("\n[4] Portfolio configurations:", flush=True)
    all_dates = pd.to_datetime(
        sorted(set(t_base["entry_date"]) | set(t_short["entry_date"]))
    )
    pnl_base = daily_pnl_series(t_base, all_dates)
    pnl_short = daily_pnl_series(t_short, all_dates)
    pnl_full = pnl_base + pnl_short
    pnl_half = (pnl_base + pnl_short) / 2

    configs = {
        "A_baseline_alone": portfolio_metrics(pnl_base, "Baseline (both) alone"),
        "B_short_only_alone": portfolio_metrics(pnl_short, "Short-only alone"),
        "C_both_full_size": portfolio_metrics(pnl_full, "Both at full size"),
        "D_both_half_size": portfolio_metrics(pnl_half, "Both at half size"),
        "E_controller_short_when_fires": portfolio_metrics(
            controller_combined_series(t_base, t_short, all_dates),
            "Short when fires else baseline"
        ),
    }
    for key, m in configs.items():
        print(f"\n  {key}:", flush=True)
        print(f"    total_pnl: ${m.get('total_pnl', 0):.0f}", flush=True)
        print(f"    max_drawdown: ${m.get('max_drawdown', 0):.0f}", flush=True)
        print(f"    sharpe_est: {m.get('sharpe_est', 0):.3f}", flush=True)
        print(f"    prop_breach: {m.get('prop_breach')}", flush=True)
        print(f"    max_consec_losing: {m.get('max_consecutive_losing_days')}", flush=True)

    print("\n[5] Family-review classification:", flush=True)
    verdict, notes = classify_family_review(
        configs["A_baseline_alone"], configs["B_short_only_alone"],
        configs["C_both_full_size"], configs["D_both_half_size"],
        configs["E_controller_short_when_fires"], overlap, corr,
    )
    print(f"\n  VERDICT: {verdict}", flush=True)
    for n in notes:
        print(f"    - {n}", flush=True)

    # Save
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_dir_mgc_orb_short_family_review_{date.today().isoformat()}.json"
    payload = {
        "date": date.today().isoformat(),
        "approval": "OK family-review top 3, Short-PL priority (#73)",
        "candidates": {
            "baseline": "XB-ORB-EMA-Ladder-MGC (both directions, profit_ladder)",
            "new": "DIR-MGC-ORB-Short-PL (short-only, profit_ladder)",
        },
        "standalone": {"baseline": summ_base, "short": summ_short},
        "trade_overlap": overlap,
        "pnl_correlation": corr,
        "configurations": configs,
        "verdict": verdict,
        "notes": notes,
    }
    out.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    return payload


if __name__ == "__main__":
    run()
