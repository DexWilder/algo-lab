"""PB-VolLow-MNQ family review vs XB-ORB-EMA-Ladder-MNQ (confirmation test).

Per operator approval #56 — treat as confirmation, not headline opportunity.
Same 5-test protocol as DC-MNQ review.
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


def _run(asset, entry, filter_name, exit_name, params, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(
        df, entry_name=entry, exit_name=exit_name,
        filter_name=filter_name, params=params or {},
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    trades = res["trades_df"].copy()
    if not trades.empty:
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        trades["entry_date"] = trades["entry_dt"].dt.date
    return trades


def run():
    print("PB-VolLow-MNQ family review vs XB-ORB-EMA-Ladder-MNQ (CONFIRMATION)\n")
    t_orb = _run("MNQ", "orb_breakout", "ema_slope", "profit_ladder", {},
                  "XB-ORB-EMA-Ladder-MNQ")
    t_pbvol = _run("MNQ", "pb_pullback", "ema_slope_vol_low", "profit_ladder",
                    {"vr_threshold": 40}, "DAILY-PB-VolLow-MNQ")
    print(f"  ORB: n={len(t_orb)} trades")
    print(f"  PB-VolLow: n={len(t_pbvol)} trades")

    overlap = trade_overlap_analysis(t_orb, t_pbvol, "ORB", "PB-VolLow")
    print("\n[Overlap]")
    for k, v in overlap.items():
        print(f"  {k}: {v}")

    corr = pnl_correlation(t_orb, t_pbvol)
    print("\n[Correlation]")
    for k, v in corr.items():
        print(f"  {k}: {v}")

    all_dates = pd.to_datetime(
        sorted(set(t_orb["entry_date"]) | set(t_pbvol["entry_date"]))
    )
    pnl_orb = daily_pnl_series(t_orb, all_dates)
    pnl_pb = daily_pnl_series(t_pbvol, all_dates)
    configs = {
        "A_orb_alone": portfolio_metrics(pnl_orb, "ORB alone"),
        "B_pb_vollow_alone": portfolio_metrics(pnl_pb, "PB-VolLow alone"),
        "C_both_full": portfolio_metrics(pnl_orb + pnl_pb, "Both full"),
        "D_both_half": portfolio_metrics((pnl_orb + pnl_pb) / 2, "Both half"),
        "E_controller": portfolio_metrics(
            controller_combined_series(t_orb, t_pbvol, all_dates), "Controller"
        ),
    }
    print("\n[Portfolio configs]")
    for k, m in configs.items():
        print(f"  {k}: total=${m.get('total_pnl', 0):.0f} maxDD=${m.get('max_drawdown', 0):.0f} "
              f"propBreach={m.get('prop_breach')}")

    verdict, notes = classify_family_review(
        configs["A_orb_alone"], configs["B_pb_vollow_alone"],
        configs["C_both_full"], configs["D_both_half"],
        configs["E_controller"], overlap, corr,
    )
    print(f"\nVERDICT: {verdict}")
    for n in notes:
        print(f"  - {n}")

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / f"forge_pbvollow_mnq_family_review_{date.today().isoformat()}.json"
    out.write_text(json.dumps({
        "verdict": verdict, "notes": notes,
        "overlap": overlap, "correlation": corr,
        "configs": configs,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
