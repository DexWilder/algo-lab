"""Multi-day risk accounting reporter for Daily Test 2.

Built 2026-06-12 per operator #204 A. Stage 1.5 of Daily Test 2 harness.

Per harness §4 (operator expanded, non-negotiable):

Per-trade risk:
  - worst_overnight_gap_per_trade
  - largest_single_day_loss
  - worst_close_to_open_loss
  - worst_open_to_open_loss
  - max_adverse_excursion_during_hold
  - max_cumulative_unrealized_loss

Event-day exposure:
  - event_day_exposure_count + %
  - FOMC exposure %

Hold duration:
  - trading/calendar days avg/max
  - overnight_exposure_pct

Concentration:
  - top-1/3/10 trade % of net
  - max-year, instance CV

Prop-firm compatibility note:
  - Tradeify daily DD (~$2-3K) compatibility
  - Trailing DD (~$5-10K) compatibility
  - Max consecutive losing trade days
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402


def _event_dates():
    """Return set of NFP + FOMC event dates."""
    nfp = build_verified_nfp_calendar(2019, 2026)
    fomc = build_official_fomc_calendar()
    nfp_dates = {pd.to_datetime(c["actual_date"]).date() for c in nfp}
    fomc_dates = {pd.to_datetime(c["actual_date"]).date() for c in fomc}
    return nfp_dates, fomc_dates


def compute_per_trade_risk(trade, daily_bars, df_5min):
    """Compute per-trade risk metrics for a single trade.

    trade: dict with entry_idx, exit_idx, entry_date, exit_date, direction,
           entry_price, exit_price, contracts, point_value.
    """
    entry_idx = trade["entry_idx"]; exit_idx = trade["exit_idx"]
    direction = trade["direction"]; entry_price = trade["entry_price"]
    contracts = trade.get("contracts", 1); pv = trade["point_value"]
    # Slice the 5-min bars during hold
    hold_5min = df_5min.iloc[entry_idx:exit_idx + 1].copy()
    hold_5min["dt"] = pd.to_datetime(hold_5min["datetime"])
    hold_5min["date"] = hold_5min["dt"].dt.date
    # Per-bar unrealized PnL (direction-aware)
    hold_5min["unrealized_pnl"] = (hold_5min["close"] - entry_price) * direction * contracts * pv
    # Max adverse excursion: worst single bar low (long) or high (short)
    if direction == 1:
        hold_5min["bar_low_pnl"] = (hold_5min["low"] - entry_price) * 1 * contracts * pv
        mae = float(hold_5min["bar_low_pnl"].min())
    else:
        hold_5min["bar_high_pnl"] = (hold_5min["high"] - entry_price) * -1 * contracts * pv
        mae = float(hold_5min["bar_high_pnl"].min())
    # Max cumulative unrealized loss (running min of unrealized PnL)
    max_cum_unrealized_loss = float(hold_5min["unrealized_pnl"].min())
    # Largest single-day loss: max loss WITHIN a single session
    daily_minmax = hold_5min.groupby("date").agg(
        intraday_max_loss=("unrealized_pnl", lambda s: float(s.max() - s.min())))
    largest_single_day_loss = float(daily_minmax["intraday_max_loss"].max()) if len(daily_minmax) else 0
    # Close-to-open and open-to-open losses
    daily_co = hold_5min.groupby("date").agg(
        first_open=("open", "first"),
        last_close=("close", "last")).reset_index()
    co_losses = []
    oo_losses = []
    for i in range(1, len(daily_co)):
        prev_close = daily_co.iloc[i - 1]["last_close"]
        today_open = daily_co.iloc[i]["first_open"]
        co_pnl = (today_open - prev_close) * direction * contracts * pv
        co_losses.append(co_pnl)
        if i > 1:
            prev_open = daily_co.iloc[i - 1]["first_open"]
            oo_pnl = (today_open - prev_open) * direction * contracts * pv
            oo_losses.append(oo_pnl)
    worst_co_loss = float(min(co_losses)) if co_losses else 0
    worst_oo_loss = float(min(oo_losses)) if oo_losses else 0
    # Overnight gap (entry session close → next session open)
    if len(daily_co) >= 2:
        first_close = daily_co.iloc[0]["last_close"]
        second_open = daily_co.iloc[1]["first_open"]
        overnight_gap_pnl = float((second_open - first_close) * direction * contracts * pv)
    else:
        overnight_gap_pnl = 0
    return {
        "worst_overnight_gap_pnl": overnight_gap_pnl,
        "largest_single_day_loss": largest_single_day_loss,
        "worst_close_to_open_loss": worst_co_loss,
        "worst_open_to_open_loss": worst_oo_loss,
        "max_adverse_excursion": mae,
        "max_cumulative_unrealized_loss": max_cum_unrealized_loss,
        "n_sessions_held": len(daily_co),
    }


def compute_full_risk_report(trades_df: pd.DataFrame, daily_bars: pd.DataFrame,
                              df_5min: pd.DataFrame, point_value: float,
                              avg_winning_trade_for_gap_check: Optional[float] = None) -> Dict:
    """Build the full expanded risk report per harness §4.

    Returns dict with all risk metrics + prop-firm compatibility note.
    """
    if trades_df.empty:
        return {"n_trades": 0, "no_trades": True}

    trades_df = trades_df.copy()
    trades_df["entry_dt"] = pd.to_datetime(trades_df["entry_time"])
    trades_df["exit_dt"] = pd.to_datetime(trades_df["exit_time"])
    trades_df["entry_date"] = trades_df["entry_dt"].dt.date
    trades_df["exit_date"] = trades_df["exit_dt"].dt.date

    # Compute per-trade metrics
    per_trade = []
    for _, row in trades_df.iterrows():
        # Build trade dict
        trade_d = {
            "entry_idx": int(row["entry_idx"]) if "entry_idx" in row else 0,
            "exit_idx": int(row["exit_idx"]) if "exit_idx" in row else 0,
            "entry_date": row["entry_date"], "exit_date": row["exit_date"],
            "direction": int(row["direction"]) if "direction" in row else (1 if row["pnl"] > 0 else 1),
            "entry_price": float(row.get("entry_price", 0)),
            "exit_price": float(row.get("exit_price", 0)),
            "contracts": 1, "point_value": point_value,
        }
        if trade_d["entry_idx"] > 0 and trade_d["exit_idx"] > 0:
            per_trade.append(compute_per_trade_risk(trade_d, daily_bars, df_5min))

    if not per_trade:
        return {"n_trades": len(trades_df), "no_per_trade_risk_computed": True}

    # Aggregate worst-case across trades
    worst_overnight_gap = float(min(t["worst_overnight_gap_pnl"] for t in per_trade))
    largest_single_day_loss = float(max(t["largest_single_day_loss"] for t in per_trade))
    worst_co_loss = float(min(t["worst_close_to_open_loss"] for t in per_trade))
    worst_oo_loss = float(min(t["worst_open_to_open_loss"] for t in per_trade))
    worst_mae = float(min(t["max_adverse_excursion"] for t in per_trade))
    worst_cum_unrealized = float(min(t["max_cumulative_unrealized_loss"] for t in per_trade))

    # Event-day exposure
    nfp_dates, fomc_dates = _event_dates()
    n_trades_with_nfp = 0; n_trades_with_fomc = 0
    for _, row in trades_df.iterrows():
        entry_d = row["entry_date"]; exit_d = row["exit_date"]
        # Check if any day in hold range is an event day
        if isinstance(entry_d, pd.Timestamp): entry_d = entry_d.date()
        if isinstance(exit_d, pd.Timestamp): exit_d = exit_d.date()
        date_range = pd.date_range(entry_d, exit_d, freq="D").date
        if any(d in nfp_dates for d in date_range):
            n_trades_with_nfp += 1
        if any(d in fomc_dates for d in date_range):
            n_trades_with_fomc += 1
    event_day_exposure_count = n_trades_with_nfp + n_trades_with_fomc

    # Hold duration
    trades_df["trading_days"] = trades_df.apply(
        lambda r: max(1, np.busday_count(np.datetime64(r["entry_date"], "D"),
                                            np.datetime64(r["exit_date"], "D")) + 1), axis=1)
    trades_df["calendar_days"] = (trades_df["exit_dt"] - trades_df["entry_dt"]).dt.days
    avg_trading_days = float(trades_df["trading_days"].mean())
    max_trading_days = int(trades_df["trading_days"].max())
    avg_calendar_days = float(trades_df["calendar_days"].mean())
    max_calendar_days = int(trades_df["calendar_days"].max())

    overnight_pct = float((trades_df["exit_date"] != trades_df["entry_date"]).mean() * 100)

    # Concentration
    n = len(trades_df); net = float(trades_df["pnl"].sum())
    sorted_pnl = trades_df["pnl"].sort_values(ascending=False).reset_index(drop=True)
    top1_pct = float(sorted_pnl.iloc[0] / net * 100) if net != 0 else 0
    top3_pct = float(sorted_pnl.iloc[:3].sum() / net * 100) if net != 0 else 0
    top10_pct = float(sorted_pnl.iloc[:10].sum() / net * 100) if net != 0 else 0

    trades_df["year"] = trades_df["entry_dt"].dt.year
    per_year_nets = trades_df.groupby("year")["pnl"].sum()
    max_yr_share = float(per_year_nets.abs().max() / net * 100) if net != 0 else 0
    instance_cv = float(per_year_nets.std() / per_year_nets.mean()) if per_year_nets.mean() != 0 else float("inf")

    # Max consecutive losing TRADE DAYS
    trades_sorted = trades_df.sort_values("entry_dt").reset_index(drop=True)
    daily_pnl_by_date = trades_sorted.groupby("entry_date")["pnl"].sum()
    daily_pnl_by_date = daily_pnl_by_date.sort_index()
    max_consec_loss = 0; current = 0
    for v in daily_pnl_by_date.values:
        if v < 0: current += 1; max_consec_loss = max(max_consec_loss, current)
        else: current = 0

    # Prop-firm compatibility — Tradeify style
    avg_winner = float(trades_df[trades_df["pnl"] > 0]["pnl"].mean()) if (trades_df["pnl"] > 0).any() else 0
    catastrophic_gap_threshold = avg_winner * 3 if avg_winner > 0 else float("inf")
    gap_protection_pass = abs(worst_overnight_gap) <= catastrophic_gap_threshold
    daily_dll_2k_compatible = abs(worst_co_loss) <= 2000 and largest_single_day_loss <= 2000
    daily_dll_3k_compatible = abs(worst_co_loss) <= 3000 and largest_single_day_loss <= 3000
    trailing_dd_5k_compatible = abs(worst_cum_unrealized) <= 5000
    trailing_dd_10k_compatible = abs(worst_cum_unrealized) <= 10000

    prop_firm_note = (
        f"Worst overnight gap: ${worst_overnight_gap:.0f}. "
        f"Largest single-day loss: ${largest_single_day_loss:.0f}. "
        f"Worst close-to-open: ${worst_co_loss:.0f}. "
        f"Worst cumulative unrealized loss: ${worst_cum_unrealized:.0f}. "
        f"Max consecutive losing trade-days: {max_consec_loss}. "
        f"Gap protection (gap ≤ 3× avg win ${avg_winner:.0f}): "
        f"{'PASS' if gap_protection_pass else 'FAIL'}. "
        f"Tradeify $2K daily DD: {'PASS' if daily_dll_2k_compatible else 'FAIL'}. "
        f"Tradeify $3K daily DD: {'PASS' if daily_dll_3k_compatible else 'FAIL'}. "
        f"$5K trailing DD: {'PASS' if trailing_dd_5k_compatible else 'FAIL'}. "
        f"$10K trailing DD: {'PASS' if trailing_dd_10k_compatible else 'FAIL'}."
    )

    # Per operator #207: deployment suitability summary line
    intraday_prop_compatible = overnight_pct == 0  # only intraday-flat strategies
    failure_reasons = []
    if not daily_dll_2k_compatible:
        failure_reasons.append(f"largest single-day loss ${largest_single_day_loss:.0f} > $2K")
    if not daily_dll_3k_compatible and largest_single_day_loss > 3000:
        failure_reasons.append(f"largest single-day loss > $3K")
    if not trailing_dd_5k_compatible:
        failure_reasons.append(f"cumulative unrealized DD ${abs(worst_cum_unrealized):.0f} > $5K")
    if not gap_protection_pass:
        failure_reasons.append(f"overnight gap ${abs(worst_overnight_gap):.0f} > 3× avg win")

    deployment_suitability = {
        "intraday_prop_account_compatible": intraday_prop_compatible,
        "tradeify_2k_daily_dd_compatible": daily_dll_2k_compatible,
        "tradeify_3k_daily_dd_compatible": daily_dll_3k_compatible,
        "trailing_5k_dd_compatible": trailing_dd_5k_compatible,
        "trailing_10k_dd_compatible": trailing_dd_10k_compatible,
        "primary_failure_reason": failure_reasons[0] if failure_reasons else "None - all compatible",
        "all_failure_reasons": failure_reasons,
        "summary_line": (
            f"DEPLOYMENT SUITABILITY: "
            f"intraday-prop {'YES' if intraday_prop_compatible else 'NO (overnight)'} | "
            f"$2K DLL {'YES' if daily_dll_2k_compatible else 'NO'} | "
            f"$3K DLL {'YES' if daily_dll_3k_compatible else 'NO'} | "
            f"$5K trailing {'YES' if trailing_dd_5k_compatible else 'NO'} | "
            f"reason: {failure_reasons[0] if failure_reasons else 'all PASS'}"
        ),
    }

    return {
        "n_trades": n,
        "net_pnl": net,
        "per_trade_risk_aggregated": {
            "worst_overnight_gap_pnl": worst_overnight_gap,
            "largest_single_day_loss": largest_single_day_loss,
            "worst_close_to_open_loss": worst_co_loss,
            "worst_open_to_open_loss": worst_oo_loss,
            "max_adverse_excursion": worst_mae,
            "max_cumulative_unrealized_loss": worst_cum_unrealized,
        },
        "event_day_exposure": {
            "n_trades_with_nfp_in_hold": n_trades_with_nfp,
            "n_trades_with_fomc_in_hold": n_trades_with_fomc,
            "pct_trades_with_fomc_exposure": float(n_trades_with_fomc / n * 100),
            "event_day_exposure_count": event_day_exposure_count,
            "event_day_exposure_pct_of_trades": float(event_day_exposure_count / n * 100),
        },
        "hold_duration": {
            "avg_trading_days": avg_trading_days,
            "max_trading_days": max_trading_days,
            "avg_calendar_days": avg_calendar_days,
            "max_calendar_days": max_calendar_days,
            "overnight_exposure_pct": overnight_pct,
        },
        "concentration": {
            "top_1_trade_pct_of_net": top1_pct,
            "top_3_trades_pct_of_net": top3_pct,
            "top_10_trades_pct_of_net": top10_pct,
            "max_year_share_pct": max_yr_share,
            "instance_cv": instance_cv,
        },
        "max_consecutive_losing_trade_days": max_consec_loss,
        "prop_firm_compatibility": {
            "tradeify_2k_daily_dd_compatible": daily_dll_2k_compatible,
            "tradeify_3k_daily_dd_compatible": daily_dll_3k_compatible,
            "trailing_dd_5k_compatible": trailing_dd_5k_compatible,
            "trailing_dd_10k_compatible": trailing_dd_10k_compatible,
            "gap_protection_pass_3x_avg_win": gap_protection_pass,
            "note": prop_firm_note,
        },
        "deployment_suitability": deployment_suitability,
    }
