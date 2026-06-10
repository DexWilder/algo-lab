"""Cycle 2026-06-10j — BBKC-MNQ vs XB-ORB-EMA-Ladder-MNQ probation family review.

Per operator decision #152 BBKC audit prep work. Critical duplicate-exposure
check: BBKC-MNQ and XB-ORB-EMA-Ladder-MNQ are both intraday strategies on
MNQ. If correlation is high, BBKC-MNQ would be portfolio_complement
or duplicate, not a true Packet #2.

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def run_strategy(spec):
    cfg = ASSETS[spec["asset"]]
    costs = get_cost_params(spec["asset"])
    df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
    sigs = generate_crossbred_signals(
        df, entry_name=spec["entry"], exit_name=spec["exit"],
        filter_name=spec["filter"], params=spec.get("params", {}),
    )
    res = run_backtest(
        df, sigs, mode=spec.get("mode", "both"),
        point_value=cfg["point_value"], symbol=spec["asset"],
        commission_per_side=costs["commission_per_side"],
        slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"],
    )
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    return m, res["trades_df"]


def family_review(trades_a, trades_b, label_a, label_b):
    days_a = set(pd.to_datetime(trades_a["entry_time"]).dt.date)
    days_b = set(pd.to_datetime(trades_b["entry_time"]).dt.date)
    overlap = days_a & days_b
    daily_a = trades_a.copy()
    daily_a["entry_dt"] = pd.to_datetime(daily_a["entry_time"])
    daily_a["date"] = daily_a["entry_dt"].dt.date
    pnl_a = daily_a.groupby("date")["pnl"].sum()
    daily_b = trades_b.copy()
    daily_b["entry_dt"] = pd.to_datetime(daily_b["entry_time"])
    daily_b["date"] = daily_b["entry_dt"].dt.date
    pnl_b = daily_b.groupby("date")["pnl"].sum()
    aligned = pd.concat([pnl_a, pnl_b], axis=1, keys=["a", "b"]).fillna(0.0)
    corr = float(aligned["a"].corr(aligned["b"]))
    # Both-traded days
    both_traded = int(((aligned["a"] != 0) & (aligned["b"] != 0)).sum())
    # Classification per duplicate exposure doctrine
    if corr > 0.7 and len(overlap) / len(days_a) * 100 > 80:
        classification = "DUPLICATE_EXPOSURE_REJECT"
    elif corr > 0.5:
        classification = "PORTFOLIO_COMPLEMENT (moderate corr — bounded diversification)"
    elif corr > 0.3:
        classification = "PORTFOLIO_COMPLEMENT (low-moderate corr)"
    else:
        classification = "INDEPENDENT (corr ≤ 0.3 — genuinely uncorrelated)"
    return {
        "n_days_a": len(days_a), "n_days_b": len(days_b),
        "n_days_overlap": len(overlap),
        "overlap_pct_of_a": len(overlap) / len(days_a) * 100 if days_a else 0,
        "overlap_pct_of_b": len(overlap) / len(days_b) * 100 if days_b else 0,
        "daily_pnl_corr": corr,
        "both_traded_days": both_traded,
        "classification": classification,
    }


BBKC = {
    "label": "BBKC-MNQ-Both-PL",
    "asset": "MNQ",
    "entry": "bb_keltner_squeeze",
    "filter": "ema_slope",
    "exit": "profit_ladder",
    "mode": "both",
}

XB_ORB_MNQ = {
    "label": "XB-ORB-EMA-Ladder-MNQ",
    "asset": "MNQ",
    "entry": "orb_breakout",
    "filter": "ema_slope",
    "exit": "profit_ladder",
    "mode": "both",
}


def run():
    print("Cycle 2026-06-10j — BBKC-MNQ vs MNQ probation family review", flush=True)
    print("Per #152 BBKC audit prep.\n", flush=True)
    t_start = time.time()

    print("Running BBKC-MNQ-Both-PL...", flush=True)
    m_bbkc, t_bbkc = run_strategy(BBKC)
    print(f"  BBKC: n={m_bbkc['n']} PF={m_bbkc['pf']:.3f} med=${m_bbkc['median']:.2f}", flush=True)

    print("\nRunning XB-ORB-EMA-Ladder-MNQ (probation baseline)...", flush=True)
    m_orb, t_orb = run_strategy(XB_ORB_MNQ)
    print(f"  XB-ORB-MNQ: n={m_orb['n']} PF={m_orb['pf']:.3f} med=${m_orb['median']:.2f}", flush=True)

    print(f"\nFamily review BBKC-MNQ vs XB-ORB-EMA-Ladder-MNQ:", flush=True)
    fam = family_review(t_bbkc, t_orb, "BBKC-MNQ", "XB-ORB-MNQ")
    for k, v in fam.items():
        print(f"  {k}: {v}", flush=True)

    print(f"\nTotal: {time.time() - t_start:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-10j_BBKC_vs_MNQ_probation.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "BBKC-MNQ vs XB-ORB-EMA-Ladder-MNQ duplicate exposure family review",
        "BBKC-MNQ_baseline": {
            "n": int(m_bbkc["n"]), "pf": float(m_bbkc["pf"]),
            "median": float(m_bbkc["median"]),
        },
        "XB-ORB-MNQ_baseline": {
            "n": int(m_orb["n"]), "pf": float(m_orb["pf"]),
            "median": float(m_orb["median"]),
        },
        "family_review": fam,
    }, indent=2, default=str))
    print(f"\nWrote: {out}")


if __name__ == "__main__":
    run()
