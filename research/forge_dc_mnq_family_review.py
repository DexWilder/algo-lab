"""DAILY-DC-EMA-MNQ family review vs XB-ORB-EMA-Ladder-MNQ.

Per operator approval 2026-06-04 (#48). Full 5-test protocol with all 5
classification possibilities open: REPLACEMENT / PARALLEL_COMPLEMENT /
BLENDED_WORKHORSE / CONTROLLER_VARIANT / DUPLICATE_EXPOSURE_REJECT.

The two candidates share asset (MNQ), filter (ema_slope), and exit
(profit_ladder) but differ in entry primitive (orb_breakout vs donchian_breakout).
Same-asset same-filter+exit family — duplicate-exposure risk must be measured
before any deep-screen.

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Reuse helpers from the original MNQ family review
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "mnq_review_lib", ROOT / "research" / "forge_mnq_family_review.py"
)
_lib = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lib)

run_candidate = _lib.run_candidate  # asset, filter_name, params, label
trade_overlap_analysis = _lib.trade_overlap_analysis
pnl_correlation = _lib.pnl_correlation
daily_pnl_series = _lib.daily_pnl_series
portfolio_metrics = _lib.portfolio_metrics
controller_combined_series = _lib.controller_combined_series
classify_family_review = _lib.classify_family_review

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


def run_dc_candidate():
    """DAILY-DC-EMA-MNQ — donchian_breakout entry, ema_slope filter, profit_ladder exit."""
    df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    cfg = ASSETS["MNQ"]
    sigs = generate_crossbred_signals(
        df, entry_name="donchian_breakout", exit_name="profit_ladder",
        filter_name="ema_slope", params={},
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol="MNQ")
    trades = res["trades_df"].copy()
    if not trades.empty:
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        trades["exit_dt"] = pd.to_datetime(trades["exit_time"])
        trades["entry_date"] = trades["entry_dt"].dt.date
    return trades


def run_orb_candidate():
    """XB-ORB-EMA-Ladder-MNQ — orb_breakout entry, ema_slope filter, profit_ladder exit.
    Existing probation workhorse."""
    df = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    cfg = ASSETS["MNQ"]
    sigs = generate_crossbred_signals(
        df, entry_name="orb_breakout", exit_name="profit_ladder",
        filter_name="ema_slope", params={},
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol="MNQ")
    trades = res["trades_df"].copy()
    if not trades.empty:
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        trades["exit_dt"] = pd.to_datetime(trades["exit_time"])
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
    max_dd_pnl = float((eq - peak).min())
    return {
        "label": label,
        "n": int(len(trades)),
        "pf": float(pf),
        "median": float(np.median(pnl)),
        "net_pnl": float(pnl.sum()),
        "max_dd_trade_equity": max_dd_pnl,
        "win_rate_pct": float((pnl > 0).mean() * 100),
        "avg_win": float(wins.mean()) if len(wins) else float("nan"),
        "avg_loss": float(losses.mean()) if len(losses) else float("nan"),
    }


def temporal_split(trades):
    if trades.empty:
        return {}
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": pf, "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        pf = float(w/l) if l > 0 else float("inf")
        eras.append({"era": i+1, "n": int(len(sub)), "pf": pf,
                     "net": float(pnl.sum())})
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
            "n_yrs": len(per_year)}


def time_of_day_breakdown(trades, label):
    """Avg entry hour distribution — useful for overlap-by-session diagnostic."""
    if trades.empty:
        return {}
    hr = pd.to_datetime(trades["entry_time"]).dt.hour
    return {
        "label": label,
        "by_hour": hr.value_counts().sort_index().to_dict(),
    }


def run():
    print("DAILY-DC-EMA-MNQ family review vs XB-ORB-EMA-Ladder-MNQ\n")

    print("[Loading candidates]")
    t_orb = run_orb_candidate()
    t_dc = run_dc_candidate()
    print(f"  XB-ORB-EMA-Ladder-MNQ: n={len(t_orb)} trades")
    print(f"  DAILY-DC-EMA-MNQ:      n={len(t_dc)} trades")

    print("\n[1] Standalone comparison:")
    summ_orb = trade_summary(t_orb, "XB-ORB-EMA-Ladder-MNQ")
    summ_dc = trade_summary(t_dc, "DAILY-DC-EMA-MNQ")
    for k in ("n", "pf", "median", "net_pnl", "max_dd_trade_equity", "win_rate_pct",
              "avg_win", "avg_loss"):
        print(f"    {k}: ORB={summ_orb.get(k)}  |  DC={summ_dc.get(k)}")
    ts_orb = temporal_split(t_orb)
    ts_dc = temporal_split(t_dc)
    orb_eras_str = ", ".join(f"E{e['era']}={e['pf']:.2f}" for e in ts_orb.get('eras', []))
    dc_eras_str = ", ".join(f"E{e['era']}={e['pf']:.2f}" for e in ts_dc.get('eras', []))
    print(f"    eras ORB: {orb_eras_str}")
    print(f"    eras DC:  {dc_eras_str}")
    print(f"    yrs+ ORB: {ts_orb.get('yrs_pos')}/{ts_orb.get('n_yrs')}")
    print(f"    yrs+ DC:  {ts_dc.get('yrs_pos')}/{ts_dc.get('n_yrs')}")

    print("\n[2] Trade overlap:")
    overlap = trade_overlap_analysis(t_orb, t_dc, "ORB", "DC")
    for k, v in overlap.items():
        print(f"    {k}: {v}")

    print("\n[3] PnL correlation + drawdown overlap:")
    corr = pnl_correlation(t_orb, t_dc)
    for k, v in corr.items():
        print(f"    {k}: {v}")

    print("\n[4] Portfolio configurations:")
    all_dates = pd.to_datetime(
        sorted(set(t_orb["entry_date"]) | set(t_dc["entry_date"]))
    )
    pnl_orb = daily_pnl_series(t_orb, all_dates)
    pnl_dc = daily_pnl_series(t_dc, all_dates)
    pnl_full = pnl_orb + pnl_dc
    pnl_half = (pnl_orb + pnl_dc) / 2
    pnl_ctrl = controller_combined_series(t_orb, t_dc, all_dates)
    # Replacement mode: DC replaces ORB entirely (=DC alone)
    pnl_replace = pnl_dc.copy()

    configs = {
        "A_orb_baseline_alone": portfolio_metrics(pnl_orb, "ORB alone (existing probation)"),
        "B_dc_new_alone": portfolio_metrics(pnl_dc, "DC alone (new candidate)"),
        "C_both_full_size": portfolio_metrics(pnl_full, "Both at full size"),
        "D_both_half_size": portfolio_metrics(pnl_half, "Both at half size"),
        "E_controller_dc_when_fires": portfolio_metrics(pnl_ctrl, "DC when fires else ORB"),
        "F_replacement_dc_only": portfolio_metrics(pnl_replace, "DC replaces ORB"),
    }
    for key, m in configs.items():
        print(f"\n  {key}:")
        for kk, vv in m.items():
            print(f"    {kk}: {vv}")

    print("\n[5] Family-review classification:")
    verdict, notes = classify_family_review(
        configs["A_orb_baseline_alone"], configs["B_dc_new_alone"],
        configs["C_both_full_size"], configs["D_both_half_size"],
        configs["E_controller_dc_when_fires"], overlap, corr,
    )
    print(f"\n  VERDICT: {verdict}")
    for n in notes:
        print(f"    - {n}")

    # Save
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    payload = {
        "date": date_iso,
        "approval": "OK MNQ family review (#48)",
        "candidates": {
            "existing_probation": "XB-ORB-EMA-Ladder-MNQ",
            "new_candidate": "DAILY-DC-EMA-MNQ",
        },
        "standalone": {"orb": summ_orb, "dc": summ_dc,
                       "orb_temporal": ts_orb, "dc_temporal": ts_dc},
        "trade_overlap": overlap,
        "pnl_correlation": corr,
        "configurations": configs,
        "verdict": verdict,
        "notes": notes,
    }
    (out_dir / f"forge_dc_mnq_family_review_{date_iso}.json").write_text(
        json.dumps(payload, indent=2, default=str)
    )
    print(f"\nWrote: forge_dc_mnq_family_review_{date_iso}.json")
    return payload


if __name__ == "__main__":
    run()
