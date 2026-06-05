"""Track 2: MNQ family review — XB-ORB-EMA-Ladder-MNQ vs XB-ORB-EMA-VolLow30-MNQ.

Per operator approval 2026-06-04 (#39 clarification). Run all 5 possibilities:
  REPLACEMENT / PARALLEL_COMPLEMENT / BLENDED_WORKHORSE /
  CONTROLLER_VARIANT / DUPLICATE_EXPOSURE_REJECT

Required tests:
  1. Trade overlap (same-day, same-direction, time separation, uniques)
  2. PnL correlation (daily, drawdown overlap, losing-day overlap)
  3. Combined portfolio (5 configurations)
  4. Prop survivability proxy (max trailing DD vs $4,000 prop threshold)

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

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


def run_candidate(asset, filter_name, params, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(
        df, entry_name="orb_breakout", exit_name="profit_ladder",
        filter_name=filter_name, params=params or {},
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    trades = res["trades_df"].copy()
    if not trades.empty:
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        trades["exit_dt"] = pd.to_datetime(trades["exit_time"])
        trades["entry_date"] = trades["entry_dt"].dt.date
    return trades


def trade_overlap_analysis(t_a, t_b, label_a, label_b):
    """Same-day / same-direction overlap + unique-trade counts."""
    dates_a = set(t_a["entry_date"])
    dates_b = set(t_b["entry_date"])
    same_day = dates_a & dates_b
    only_a = dates_a - dates_b
    only_b = dates_b - dates_a
    # Same-direction overlap on same-day trades
    same_dir = 0
    opp_dir = 0
    for d in same_day:
        sides_a = set(t_a[t_a["entry_date"] == d]["side"])
        sides_b = set(t_b[t_b["entry_date"] == d]["side"])
        if sides_a & sides_b:
            same_dir += 1
        if (sides_a - sides_b) or (sides_b - sides_a):
            opp_dir += 1
    # Average time separation on same-day trades
    time_seps = []
    for d in same_day:
        ta = t_a[t_a["entry_date"] == d]["entry_dt"]
        tb = t_b[t_b["entry_date"] == d]["entry_dt"]
        if len(ta) and len(tb):
            sep = (ta.iloc[0] - tb.iloc[0]).total_seconds() / 60
            time_seps.append(abs(sep))
    avg_time_sep_min = float(np.mean(time_seps)) if time_seps else None
    return {
        "n_trades_a": int(len(t_a)),
        "n_trades_b": int(len(t_b)),
        "trading_days_a": int(len(dates_a)),
        "trading_days_b": int(len(dates_b)),
        "same_day_count": int(len(same_day)),
        "only_a_days": int(len(only_a)),
        "only_b_days": int(len(only_b)),
        "same_day_pct_of_a": float(len(same_day) / len(dates_a) * 100) if dates_a else 0,
        "same_day_pct_of_b": float(len(same_day) / len(dates_b) * 100) if dates_b else 0,
        "same_direction_days": same_dir,
        "opposite_direction_days": opp_dir,
        "avg_time_separation_minutes_same_day": avg_time_sep_min,
    }


def daily_pnl_series(trades, date_range):
    """Sum trade pnl per calendar day; reindex to common date range."""
    if trades.empty:
        return pd.Series(0.0, index=date_range)
    df = trades.copy()
    df["entry_date"] = pd.to_datetime(df["entry_date"])
    daily = df.groupby("entry_date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily.reindex(date_range).fillna(0)


def pnl_correlation(t_a, t_b):
    all_dates = pd.to_datetime(
        sorted(set(t_a["entry_date"]) | set(t_b["entry_date"]))
    )
    pnl_a = daily_pnl_series(t_a, all_dates)
    pnl_b = daily_pnl_series(t_b, all_dates)
    daily_corr = float(pnl_a.corr(pnl_b))
    # Weekly resample
    weekly_a = pnl_a.resample("W").sum()
    weekly_b = pnl_b.resample("W").sum()
    weekly_corr = float(weekly_a.corr(weekly_b))
    # Drawdown overlap: define DD day as cumsum below prior peak
    eq_a = pnl_a.cumsum()
    eq_b = pnl_b.cumsum()
    in_dd_a = eq_a < eq_a.cummax()
    in_dd_b = eq_b < eq_b.cummax()
    dd_overlap_pct = float((in_dd_a & in_dd_b).mean() * 100)
    # Losing day overlap
    losing_a = pnl_a < 0
    losing_b = pnl_b < 0
    losing_overlap_pct = float((losing_a & losing_b).mean() * 100)
    losing_a_pct = float(losing_a.mean() * 100)
    losing_b_pct = float(losing_b.mean() * 100)
    return {
        "daily_corr": daily_corr,
        "weekly_corr": weekly_corr,
        "drawdown_overlap_pct_of_days": dd_overlap_pct,
        "losing_day_overlap_pct": losing_overlap_pct,
        "losing_day_pct_a": losing_a_pct,
        "losing_day_pct_b": losing_b_pct,
        "n_common_days": int(len(all_dates)),
    }


def portfolio_metrics(pnl_series, label):
    if len(pnl_series) == 0:
        return {"label": label, "n_days": 0}
    total = float(pnl_series.sum())
    eq = pnl_series.cumsum()
    peak = eq.cummax()
    dd = eq - peak
    max_dd = float(dd.min())
    # Worst day / consecutive losing days
    worst_day = float(pnl_series.min())
    losing = pnl_series < 0
    streaks = []
    cur = 0
    for x in losing:
        if x:
            cur += 1
        else:
            if cur:
                streaks.append(cur)
            cur = 0
    if cur:
        streaks.append(cur)
    max_consec = max(streaks) if streaks else 0
    # Rolling 60-day PF
    pos_60 = pnl_series.rolling(60).apply(
        lambda x: x[x > 0].sum() / max(-x[x < 0].sum(), 1e-9), raw=True
    )
    pos_60_finite = pos_60.dropna()
    worst_rolling_pf = float(pos_60_finite.min()) if len(pos_60_finite) else float("nan")
    pct_rolling_above_1 = float((pos_60_finite > 1.0).mean() * 100) if len(pos_60_finite) else float("nan")
    # Annualized
    n_yrs = len(pnl_series) / 252
    annual_pnl = total / n_yrs if n_yrs > 0 else 0
    annual_vol = float(pnl_series.std() * np.sqrt(252))
    sharpe = annual_pnl / annual_vol if annual_vol > 0 else float("nan")
    # Prop-survivability: did equity ever breach $-4,000 drawdown from peak?
    prop_threshold = -4000
    breach = bool((dd <= prop_threshold).any())
    days_to_breach = int((dd <= prop_threshold).idxmax().toordinal() - dd.index[0].toordinal()) if breach else None
    return {
        "label": label,
        "n_days": int(len(pnl_series)),
        "total_pnl": total,
        "annual_pnl_est": annual_pnl,
        "annual_vol_est": annual_vol,
        "sharpe_est": sharpe,
        "max_drawdown": max_dd,
        "worst_day": worst_day,
        "max_consecutive_losing_days": max_consec,
        "worst_rolling_60d_pf": worst_rolling_pf,
        "pct_rolling_60d_pf_gt_1": pct_rolling_above_1,
        "prop_threshold": prop_threshold,
        "prop_breach": breach,
        "days_to_first_breach": days_to_breach,
    }


def controller_combined_series(t_baseline, t_volow, all_dates):
    """Controller variant: use VolLow30 on days where (we approximate) vol is low,
    else use baseline. Free proxy: low-vol day = baseline didn't fire (no entry)
    since vol_low filter is more restrictive — i.e., use VolLow30 whenever it
    fires, fallback to baseline on days where VolLow30 doesn't fire.
    """
    pnl_base = daily_pnl_series(t_baseline, all_dates)
    pnl_volow = daily_pnl_series(t_volow, all_dates)
    # VolLow priority — if VolLow fires (any non-zero PnL contribution) use that,
    # else baseline
    vol_fired = (pnl_volow != 0) | t_volow.assign(d=pd.to_datetime(t_volow["entry_date"])).set_index("d").index.isin(all_dates).any() if False else (pnl_volow != 0)
    # Simpler: VolLow when its PnL would have been computed (i.e. it traded)
    # ↓ Days where VolLow has any traded value (incl 0 if it entered and exited flat)
    volow_traded_days = set(pd.to_datetime(t_volow["entry_date"]))
    use_volow = pd.Series([d in volow_traded_days for d in all_dates], index=all_dates)
    result = pnl_volow.where(use_volow, pnl_base)
    return result


def classify_family_review(stand_a, stand_b, combined_full, combined_half,
                            controller, overlap, corr):
    """Apply operator classification rules."""
    # Reference: baseline = XB-ORB-EMA-Ladder-MNQ; new = XB-ORB-EMA-VolLow30-MNQ
    notes = []
    base_dd = stand_a["max_drawdown"]
    new_dd = stand_b["max_drawdown"]
    base_total = stand_a["total_pnl"]
    new_total = stand_b["total_pnl"]
    full_total = combined_full["total_pnl"]
    full_dd = combined_full["max_drawdown"]
    half_dd = combined_half["max_drawdown"]
    half_total = combined_half["total_pnl"]
    ctrl_total = controller["total_pnl"]
    ctrl_dd = controller["max_drawdown"]

    # Check 1: REPLACEMENT — VolLow30 dominates baseline on most metrics
    dom_metrics = 0
    if stand_b["total_pnl"] >= stand_a["total_pnl"]: dom_metrics += 1
    if abs(stand_b["max_drawdown"]) <= abs(stand_a["max_drawdown"]): dom_metrics += 1
    if (stand_b.get("sharpe_est", 0) or 0) >= (stand_a.get("sharpe_est", 0) or 0): dom_metrics += 1
    if stand_b["max_consecutive_losing_days"] <= stand_a["max_consecutive_losing_days"]: dom_metrics += 1
    if abs(stand_b["worst_day"]) <= abs(stand_a["worst_day"]): dom_metrics += 1
    replacement_dom = dom_metrics >= 4

    # Check 2: DUPLICATE — high correlation + drawdown stacks
    high_corr = corr["daily_corr"] > 0.65
    dd_stacks = abs(full_dd) > max(abs(base_dd), abs(new_dd)) * 1.30  # stacks worse than 30% above max
    high_overlap = overlap["same_day_pct_of_a"] > 60 or overlap["same_day_pct_of_b"] > 60
    duplicate = high_corr and dd_stacks and high_overlap

    # Check 3: PARALLEL_COMPLEMENT — full-size both improves returns AND not materially worse DD
    full_better_return = full_total > max(base_total, new_total) * 1.10
    full_not_worse_dd = abs(full_dd) <= max(abs(base_dd), abs(new_dd)) * 1.15
    parallel_complement = full_better_return and full_not_worse_dd

    # Check 4: BLENDED_WORKHORSE — half-size each smoother (better DD/total ratio) than either alone
    blend_ratio = half_total / abs(half_dd) if half_dd != 0 else float("inf")
    base_ratio = base_total / abs(base_dd) if base_dd != 0 else float("inf")
    new_ratio = new_total / abs(new_dd) if new_dd != 0 else float("inf")
    blended_smoother = blend_ratio > max(base_ratio, new_ratio) * 1.05

    # Check 5: CONTROLLER_VARIANT — each works in different regimes (i.e., low PnL overlap on losing days)
    low_losing_overlap = corr["losing_day_overlap_pct"] < 30
    ctrl_better_than_base = ctrl_total > base_total * 1.05 and abs(ctrl_dd) <= abs(base_dd)
    controller_variant = low_losing_overlap and ctrl_better_than_base

    # Verdict priority (most-stringent first)
    if duplicate:
        return "DUPLICATE_EXPOSURE_REJECT", notes + [
            f"daily corr {corr['daily_corr']:.2f} > 0.65",
            f"DD stacks {full_dd:.0f} > max(base,new)*1.30",
            f"overlap day pct {overlap['same_day_pct_of_a']:.0f}/{overlap['same_day_pct_of_b']:.0f}",
        ]
    if replacement_dom:
        return "REPLACEMENT_CANDIDATE", notes + [
            f"VolLow30 dominates on {dom_metrics}/5 metrics"
        ]
    if parallel_complement:
        return "PARALLEL_COMPLEMENT_CANDIDATE", notes + [
            f"full-size total {full_total:.0f} > 1.10× max(base,new)",
            f"full-size DD {full_dd:.0f} within 1.15× of max alone",
        ]
    if blended_smoother:
        return "BLENDED_WORKHORSE_CANDIDATE", notes + [
            f"blend pnl/DD ratio {blend_ratio:.2f} > 1.05× max alone ({max(base_ratio, new_ratio):.2f})"
        ]
    if controller_variant:
        return "CONTROLLER_VARIANT_CANDIDATE", notes + [
            f"losing-day overlap {corr['losing_day_overlap_pct']:.0f}% < 30%",
            f"controller total {ctrl_total:.0f} > 1.05× base",
        ]
    return "INCONCLUSIVE / WATCH_FOR_LONGER_OBSERVATION", notes + [
        "no single category dominates; manual operator inspection recommended"
    ]


def run():
    print("MNQ workhorse family review:\n")
    t_base = run_candidate("MNQ", "ema_slope", {},
                            "XB-ORB-EMA-Ladder-MNQ")
    t_new = run_candidate("MNQ", "ema_slope_vol_low", {"vr_threshold": 30},
                           "XB-ORB-EMA-VolLow30-MNQ")
    print(f"  baseline (ema_slope): n={len(t_base)} trades, "
          f"dates {t_base['entry_dt'].min().date() if not t_base.empty else 'n/a'} → {t_base['entry_dt'].max().date() if not t_base.empty else 'n/a'}")
    print(f"  new (vol_low_30):     n={len(t_new)} trades, "
          f"dates {t_new['entry_dt'].min().date() if not t_new.empty else 'n/a'} → {t_new['entry_dt'].max().date() if not t_new.empty else 'n/a'}")

    # Trade overlap
    print("\n[1] Trade overlap:")
    overlap = trade_overlap_analysis(t_base, t_new, "Ladder", "VolLow30")
    for k, v in overlap.items():
        print(f"    {k}: {v}")

    # PnL correlation
    print("\n[2] PnL correlation + drawdown overlap:")
    corr = pnl_correlation(t_base, t_new)
    for k, v in corr.items():
        print(f"    {k}: {v}")

    # Combined portfolios
    all_dates = pd.to_datetime(
        sorted(set(t_base["entry_date"]) | set(t_new["entry_date"]))
    )
    pnl_base = daily_pnl_series(t_base, all_dates)
    pnl_new = daily_pnl_series(t_new, all_dates)
    pnl_full = pnl_base + pnl_new                # both full-size
    pnl_half = (pnl_base + pnl_new) / 2.0        # both half-size each
    pnl_ctrl = controller_combined_series(t_base, t_new, all_dates)

    print("\n[3] Portfolio metrics — 5 configurations:")
    configs = {
        "A_baseline_alone": portfolio_metrics(pnl_base, "Ladder alone"),
        "B_vollow30_alone": portfolio_metrics(pnl_new, "VolLow30 alone"),
        "C_both_full_size": portfolio_metrics(pnl_full, "Both at full size"),
        "D_both_half_size": portfolio_metrics(pnl_half, "Both at half size"),
        "E_controller_variant": portfolio_metrics(pnl_ctrl, "VolLow30 when fires else baseline"),
    }
    for key, m in configs.items():
        print(f"\n  {key}:")
        for kk, vv in m.items():
            print(f"    {kk}: {vv}")

    # Classification
    print("\n[4] Family-review classification:")
    verdict, notes = classify_family_review(
        configs["A_baseline_alone"], configs["B_vollow30_alone"],
        configs["C_both_full_size"], configs["D_both_half_size"],
        configs["E_controller_variant"], overlap, corr,
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
        "approval": "OK family-review (#39 clarification)",
        "trade_overlap": overlap,
        "pnl_correlation": corr,
        "configurations": configs,
        "verdict": verdict,
        "notes": notes,
    }
    (out_dir / f"forge_mnq_family_review_{date_iso}.json").write_text(
        json.dumps(payload, indent=2, default=str)
    )
    print(f"\nWrote: forge_mnq_family_review_{date_iso}.json")
    return payload


if __name__ == "__main__":
    run()
