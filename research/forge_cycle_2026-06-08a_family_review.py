"""Family review of new MES candidates vs existing XB-ORB-EMA-Ladder-MNQ.

Track B of cycle 2026-06-08a flagged 4 candidates as WATCH_FOR_DEEP_SCREEN +
PASS_STRESS:
  - DIR-MES-ORB-Long-PL
  - DIR-MES-ORB-Short-PL
  - DIR-MYM-ORB-Long-PL  (likely subset of existing XB-ORB-EMA-Ladder-MYM)
  - DIR-MYM-ORB-Short-PL (likely subset of existing XB-ORB-EMA-Ladder-MYM)

Per operator rule: "any same-family subset = insight, not packet."

This family review computes:
  - Trade-day overlap (% of MES Long days that overlap with MNQ Both days)
  - Daily-PnL correlation (cross-asset; aggregated to daily)
  - Trade-count comparison
  - Subset verdict per directional doctrine

If MES correlates heavily with MNQ → MES is a PORTFOLIO_COMPLEMENT only if
diversification value is clear (separate sleeve, sizing diversification, etc.)
or otherwise DUPLICATE_EXPOSURE.

If MES is genuinely independent → potential new PAPER_PACKET_CANDIDATE.

MYM Long/Short are explicitly directional subsets of XB-ORB-EMA-Ladder-MYM
(both directions). They are NOT new candidates. They are directional
insights for the existing MYM probation strategy.
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

from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    generate_crossbred_signals,
)
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def run_xb_orb(asset, mode):
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    sigs = generate_crossbred_signals(
        df, entry_name="orb_breakout", exit_name="profit_ladder",
        filter_name="ema_slope", params={},
    )
    res = run_backtest(
        df, sigs, mode=mode, point_value=cfg["point_value"],
        symbol=asset,
        commission_per_side=costs["commission_per_side"],
        slippage_ticks=costs["slippage_ticks"],
        tick_size=costs["tick_size"],
    )
    return res["trades_df"]


def daily_pnl(trades):
    if trades.empty:
        return pd.Series(dtype=float)
    df = trades.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["date"] = df["entry_dt"].dt.date
    return df.groupby("date")["pnl"].sum()


def trade_day_overlap(trades_a, trades_b):
    days_a = set(pd.to_datetime(trades_a["entry_time"]).dt.date)
    days_b = set(pd.to_datetime(trades_b["entry_time"]).dt.date)
    if not days_a or not days_b:
        return None
    inter = days_a & days_b
    return {
        "n_days_a": len(days_a),
        "n_days_b": len(days_b),
        "n_days_overlap": len(inter),
        "overlap_pct_of_a": len(inter) / len(days_a) * 100,
        "overlap_pct_of_b": len(inter) / len(days_b) * 100,
    }


def pnl_correlation(trades_a, trades_b):
    pnl_a = daily_pnl(trades_a)
    pnl_b = daily_pnl(trades_b)
    if pnl_a.empty or pnl_b.empty:
        return None
    aligned = pd.concat([pnl_a, pnl_b], axis=1, keys=["a", "b"]).fillna(0.0)
    if len(aligned) < 30:
        return None
    return {
        "n_aligned_days": int(len(aligned)),
        "pearson_corr": float(aligned["a"].corr(aligned["b"])),
        "both_traded_days": int(((aligned["a"] != 0) & (aligned["b"] != 0)).sum()),
    }


def classify_family_review(overlap, pnl_corr, is_subset_of_existing):
    """Per family-review doctrine."""
    if is_subset_of_existing:
        return "DIRECTIONAL_INSIGHT_OF_EXISTING_PROBATION (not a new candidate)"
    if overlap is None or pnl_corr is None:
        return "INSUFFICIENT_DATA"
    if pnl_corr["pearson_corr"] > 0.7 and overlap["overlap_pct_of_a"] > 80:
        return "DUPLICATE_EXPOSURE_REJECT (corr>0.7, day-overlap>80%)"
    if pnl_corr["pearson_corr"] > 0.5:
        return "PORTFOLIO_COMPLEMENT_CANDIDATE (moderate corr — diversification value bounded)"
    if pnl_corr["pearson_corr"] > 0.3:
        return "PORTFOLIO_COMPLEMENT_CANDIDATE (low-moderate corr)"
    return "PAPER_PACKET_CANDIDATE_LIKELY (corr ≤ 0.3 — genuinely independent)"


def run():
    print("Family review — Track B WATCH candidates vs existing probation\n", flush=True)

    # Compute MES, MYM, and MNQ XB-ORB baselines
    print("Computing MNQ XB-ORB-EMA-Ladder baseline (both, mode)...", flush=True)
    mnq_both = run_xb_orb("MNQ", "both")
    print(f"  MNQ both: n={len(mnq_both)}, net=${mnq_both['pnl'].sum():.0f}", flush=True)

    print("Computing MES XB-ORB-EMA-Ladder directional splits...", flush=True)
    mes_long = run_xb_orb("MES", "long")
    mes_short = run_xb_orb("MES", "short")
    print(f"  MES long: n={len(mes_long)}, net=${mes_long['pnl'].sum():.0f}", flush=True)
    print(f"  MES short: n={len(mes_short)}, net=${mes_short['pnl'].sum():.0f}", flush=True)

    print("Computing MYM XB-ORB-EMA-Ladder (both, baseline probation) + directional...", flush=True)
    mym_both = run_xb_orb("MYM", "both")
    mym_long = run_xb_orb("MYM", "long")
    mym_short = run_xb_orb("MYM", "short")
    print(f"  MYM both: n={len(mym_both)}, net=${mym_both['pnl'].sum():.0f}", flush=True)
    print(f"  MYM long: n={len(mym_long)}, net=${mym_long['pnl'].sum():.0f}", flush=True)
    print(f"  MYM short: n={len(mym_short)}, net=${mym_short['pnl'].sum():.0f}", flush=True)

    # MES vs MNQ — cross-asset family review (NOT subset)
    mes_long_overlap = trade_day_overlap(mes_long, mnq_both)
    mes_long_corr = pnl_correlation(mes_long, mnq_both)
    mes_short_overlap = trade_day_overlap(mes_short, mnq_both)
    mes_short_corr = pnl_correlation(mes_short, mnq_both)

    mes_long_class = classify_family_review(mes_long_overlap, mes_long_corr, is_subset_of_existing=False)
    mes_short_class = classify_family_review(mes_short_overlap, mes_short_corr, is_subset_of_existing=False)

    # MYM Long/Short — explicit subsets of existing MYM both-direction probation
    mym_long_overlap = trade_day_overlap(mym_long, mym_both)
    mym_long_corr = pnl_correlation(mym_long, mym_both)
    mym_short_overlap = trade_day_overlap(mym_short, mym_both)
    mym_short_corr = pnl_correlation(mym_short, mym_both)

    mym_long_class = classify_family_review(mym_long_overlap, mym_long_corr, is_subset_of_existing=True)
    mym_short_class = classify_family_review(mym_short_overlap, mym_short_corr, is_subset_of_existing=True)

    print("\n=== MES vs XB-ORB-EMA-Ladder-MNQ (cross-asset family review) ===", flush=True)
    print(f"\nMES-Long vs MNQ-both:", flush=True)
    print(f"  Trade-day overlap: {mes_long_overlap}", flush=True)
    print(f"  Daily PnL corr: {mes_long_corr}", flush=True)
    print(f"  → Classification: {mes_long_class}", flush=True)
    print(f"\nMES-Short vs MNQ-both:", flush=True)
    print(f"  Trade-day overlap: {mes_short_overlap}", flush=True)
    print(f"  Daily PnL corr: {mes_short_corr}", flush=True)
    print(f"  → Classification: {mes_short_class}", flush=True)

    print("\n=== MYM directional split vs MYM both-direction probation ===", flush=True)
    print(f"\nMYM-Long vs MYM-both:", flush=True)
    print(f"  Trade-day overlap: {mym_long_overlap}", flush=True)
    print(f"  Daily PnL corr: {mym_long_corr}", flush=True)
    print(f"  → Classification: {mym_long_class}", flush=True)
    print(f"\nMYM-Short vs MYM-both:", flush=True)
    print(f"  Trade-day overlap: {mym_short_overlap}", flush=True)
    print(f"  Daily PnL corr: {mym_short_corr}", flush=True)
    print(f"  → Classification: {mym_short_class}", flush=True)

    # Per-direction PnL summary for directional asymmetry insight
    def pnl_summary(trades, label):
        if trades.empty:
            return {"label": label, "n": 0}
        pnl = trades["pnl"].values
        w = pnl[pnl > 0].sum(); l = -pnl[pnl < 0].sum()
        return {
            "label": label, "n": int(len(trades)),
            "net": float(pnl.sum()), "pf": float(w/l) if l > 0 else float("inf"),
            "median": float(np.median(pnl)),
            "win_rate": float((pnl > 0).sum() / len(pnl)),
        }

    print("\n=== MYM directional asymmetry summary ===", flush=True)
    for trades, label in [(mym_both, "MYM-both"), (mym_long, "MYM-long"), (mym_short, "MYM-short")]:
        s = pnl_summary(trades, label)
        print(f"  {s['label']}: n={s['n']} PF={s['pf']:.3f} median=${s['median']:.2f} net=${s['net']:.0f}", flush=True)

    print("\n=== MES vs MNQ asymmetry summary (for context) ===", flush=True)
    for trades, label in [(mnq_both, "MNQ-both"), (mes_long, "MES-long"), (mes_short, "MES-short")]:
        s = pnl_summary(trades, label)
        print(f"  {s['label']}: n={s['n']} PF={s['pf']:.3f} median=${s['median']:.2f} net=${s['net']:.0f}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-08a_family_review.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Family review for Track B WATCH candidates before classification",
        "results": {
            "MES_Long_vs_MNQ_both": {
                "overlap": mes_long_overlap, "pnl_correlation": mes_long_corr,
                "classification": mes_long_class,
            },
            "MES_Short_vs_MNQ_both": {
                "overlap": mes_short_overlap, "pnl_correlation": mes_short_corr,
                "classification": mes_short_class,
            },
            "MYM_Long_vs_MYM_both": {
                "overlap": mym_long_overlap, "pnl_correlation": mym_long_corr,
                "classification": mym_long_class,
            },
            "MYM_Short_vs_MYM_both": {
                "overlap": mym_short_overlap, "pnl_correlation": mym_short_corr,
                "classification": mym_short_class,
            },
        },
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
