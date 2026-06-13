"""Multi-day exit module for daily/multi-day-hold strategies.

Built 2026-06-12 per operator #204 A. Stage 1 of Daily Test 2 harness.

Provides:
  - aggregate_to_daily: RTH-only 5-min → session bars (per harness §1)
  - find_next_session_open_idx: map daily signal date → 5-min entry idx
  - find_session_close_idx: map daily date → 5-min last-RTH bar idx
  - Multi-day exit variants A/B/C/D as functions taking entry state →
    returning exit timestamp/price

Designed for use OUTSIDE crossbreeding_engine (different execution model).

Boundaries: report-only. No registry mutation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd


def aggregate_to_daily(df_5min: pd.DataFrame,
                        rth_start_hour: int = 9, rth_start_minute: int = 30,
                        rth_end_hour: int = 16) -> pd.DataFrame:
    """Aggregate 5-min bars to RTH session bars (09:30-16:00 ET).

    Returns DataFrame with one row per trading session and columns:
      date, open, high, low, close, volume
    Per harness §1: Globex/overnight bars NOT aggregated.
    """
    df = df_5min.copy()
    df["dt"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["dt"].dt.hour
    df["minute"] = df["dt"].dt.minute
    df["date"] = df["dt"].dt.date
    # RTH filter: hour >= 9:30 AND hour < 16:00
    rth_mask = (
        ((df["hour"] == rth_start_hour) & (df["minute"] >= rth_start_minute)) |
        ((df["hour"] > rth_start_hour) & (df["hour"] < rth_end_hour))
    )
    rth = df[rth_mask].copy()
    if rth.empty:
        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume"])
    grouped = rth.groupby("date").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).reset_index()
    return grouped


def find_next_session_open_idx(df_5min: pd.DataFrame, target_date) -> Optional[int]:
    """Find the 5-min bar index for the OPEN of the session AFTER target_date.

    Per harness §2: confirmation at session-close on day T → entry at
    session-open of day T+1 (the first 09:30 ET bar on T+1).
    """
    df = df_5min.copy()
    df["dt"] = pd.to_datetime(df["datetime"])
    df["date"] = df["dt"].dt.date
    # Find first bar on a date STRICTLY > target_date AND at 09:30 ET
    target = pd.to_datetime(target_date).date()
    after = df[(df["date"] > target) &
                (df["dt"].dt.hour == 9) & (df["dt"].dt.minute == 30)]
    if after.empty:
        return None
    return int(after.index[0])


def find_session_open_idx(df_5min: pd.DataFrame, target_date) -> Optional[int]:
    """Find the 5-min bar index for the 09:30 ET open of `target_date`."""
    df = df_5min.copy()
    df["dt"] = pd.to_datetime(df["datetime"])
    df["date"] = df["dt"].dt.date
    target = pd.to_datetime(target_date).date()
    match = df[(df["date"] == target) &
                (df["dt"].dt.hour == 9) & (df["dt"].dt.minute == 30)]
    if match.empty:
        return None
    return int(match.index[0])


def find_session_close_idx(df_5min: pd.DataFrame, target_date) -> Optional[int]:
    """Find the 5-min bar index for the LAST RTH bar of target_date.

    Per harness §1: session close = 16:00 ET. If 16:00 bar missing,
    fall back to last bar before 16:00 within the session.
    """
    df = df_5min.copy()
    df["dt"] = pd.to_datetime(df["datetime"])
    df["date"] = df["dt"].dt.date
    target = pd.to_datetime(target_date).date()
    rth_mask = ((df["date"] == target) &
                 (df["dt"].dt.hour >= 9) & (df["dt"].dt.hour <= 16) &
                 ~((df["dt"].dt.hour == 9) & (df["dt"].dt.minute < 30)))
    rth_bars = df[rth_mask]
    if rth_bars.empty:
        return None
    return int(rth_bars.index[-1])


# ==================================================================
# Multi-day exit variants A/B/C/D
# Each returns (exit_idx, exit_price, exit_reason) or (None, None, "no_exit")
# Entry direction is passed for invalidation logic.
# ==================================================================

@dataclass
class TradeContext:
    """Per-trade context for exit evaluation."""
    entry_idx: int               # 5-min bar index of entry
    entry_date: pd.Timestamp     # Session date of entry
    entry_price: float
    direction: int               # +1 LONG, -1 SHORT
    daily_bars: pd.DataFrame     # all daily bars (date-indexed)
    df_5min: pd.DataFrame        # 5-min bars
    invalidation_level: Optional[float] = None  # for variant C


def exit_fixed_n_day_hold(ctx: TradeContext, n_days: int):
    """Variant A/B: exit at OPEN of session entry_date + n_days.

    Per harness §3 A: 3-day hold; B: 5-day hold.
    """
    target_date = pd.to_datetime(ctx.entry_date).date()
    # Find n_days trading sessions after entry_date
    sessions = ctx.daily_bars["date"].tolist()
    if pd.to_datetime(target_date).date() not in [pd.to_datetime(s).date() for s in sessions]:
        return None, None, "entry_date_not_in_daily_bars"
    try:
        entry_pos = next(i for i, s in enumerate(sessions)
                          if pd.to_datetime(s).date() == pd.to_datetime(target_date).date())
    except StopIteration:
        return None, None, "entry_date_not_in_daily_bars"
    exit_session_pos = entry_pos + n_days
    if exit_session_pos >= len(sessions):
        return None, None, "hold_exceeds_data"
    exit_date = sessions[exit_session_pos]
    exit_idx = find_session_open_idx(ctx.df_5min, exit_date)
    if exit_idx is None:
        return None, None, "exit_session_open_missing"
    exit_price = float(ctx.df_5min.iloc[exit_idx]["open"])
    return exit_idx, exit_price, f"fixed_{n_days}_day_hold"


def exit_daily_invalidation(ctx: TradeContext, max_days: int = 5):
    """Variant C: exit at OPEN of session N+1 if daily close on session N
    is on the WRONG side of invalidation_level. Combine with max_days upper bound.

    For LONG: invalidation_level = prior-day high (i.e., the level the broke
    happened OUT of). If daily close < invalidation_level, position invalidated.
    For SHORT: invalidation_level = prior-day low. If daily close > invalidation_level,
    position invalidated.

    Per harness §3 C.
    """
    if ctx.invalidation_level is None:
        return None, None, "invalidation_level_not_set"
    target_date = pd.to_datetime(ctx.entry_date).date()
    sessions = [pd.to_datetime(s).date() for s in ctx.daily_bars["date"].tolist()]
    daily_close_col = ctx.daily_bars.set_index("date")["close"]
    try:
        entry_pos = sessions.index(target_date)
    except ValueError:
        return None, None, "entry_date_not_in_daily_bars"
    # Check each subsequent session's close against invalidation
    for offset in range(0, max_days):
        check_session_pos = entry_pos + offset
        if check_session_pos >= len(sessions):
            return None, None, "max_days_exceeded_data"
        check_date = sessions[check_session_pos]
        # Get daily close
        check_close = float(daily_close_col.loc[ctx.daily_bars["date"].iloc[check_session_pos]])
        invalidated = ((ctx.direction == 1 and check_close < ctx.invalidation_level) or
                        (ctx.direction == -1 and check_close > ctx.invalidation_level))
        if invalidated:
            # Exit at next session's open
            exit_session_pos = check_session_pos + 1
            if exit_session_pos >= len(sessions):
                return None, None, "invalidation_at_data_end"
            exit_date = sessions[exit_session_pos]
            exit_idx = find_session_open_idx(ctx.df_5min, exit_date)
            if exit_idx is None:
                return None, None, "exit_open_missing"
            exit_price = float(ctx.df_5min.iloc[exit_idx]["open"])
            return exit_idx, exit_price, f"daily_invalidation_day_{offset + 1}"
    # max_days reached without invalidation → exit at max_days session open
    exit_session_pos = entry_pos + max_days
    if exit_session_pos >= len(sessions):
        return None, None, "max_days_exceeded_data"
    exit_date = sessions[exit_session_pos]
    exit_idx = find_session_open_idx(ctx.df_5min, exit_date)
    if exit_idx is None:
        return None, None, "exit_open_missing"
    exit_price = float(ctx.df_5min.iloc[exit_idx]["open"])
    return exit_idx, exit_price, f"max_days_{max_days}"


def exit_daily_trailing_stop(ctx: TradeContext, max_days: int = 5,
                              initial_stop_buffer_atr: float = 0.0,
                              ratchet_pct: float = 0.5):
    """Variant D (OPTIONAL — secondary): trailing stop ratcheted on DAILY bars.

    Per harness §3 D — only use if explicitly pre-declared.
    """
    target_date = pd.to_datetime(ctx.entry_date).date()
    sessions = [pd.to_datetime(s).date() for s in ctx.daily_bars["date"].tolist()]
    try:
        entry_pos = sessions.index(target_date)
    except ValueError:
        return None, None, "entry_date_not_in_daily_bars"
    entry_row = ctx.daily_bars.iloc[entry_pos]
    initial_stop = entry_row["low"] if ctx.direction == 1 else entry_row["high"]
    trailing_stop = initial_stop
    # Iterate through up to max_days subsequent sessions
    for offset in range(1, max_days + 1):
        check_session_pos = entry_pos + offset
        if check_session_pos >= len(sessions):
            return None, None, "max_days_exceeded_data"
        check_row = ctx.daily_bars.iloc[check_session_pos]
        day_high = float(check_row["high"]); day_low = float(check_row["low"]); day_close = float(check_row["close"])
        # Check stop hit during the day
        if ctx.direction == 1 and day_low <= trailing_stop:
            # Exit at OPEN of next session
            exit_session_pos = check_session_pos + 1
            if exit_session_pos >= len(sessions):
                return None, None, "stop_at_data_end"
            exit_date = sessions[exit_session_pos]
            exit_idx = find_session_open_idx(ctx.df_5min, exit_date)
            if exit_idx is None:
                return None, None, "exit_open_missing"
            return exit_idx, float(ctx.df_5min.iloc[exit_idx]["open"]), f"trailing_stop_hit_day_{offset}"
        if ctx.direction == -1 and day_high >= trailing_stop:
            exit_session_pos = check_session_pos + 1
            if exit_session_pos >= len(sessions):
                return None, None, "stop_at_data_end"
            exit_date = sessions[exit_session_pos]
            exit_idx = find_session_open_idx(ctx.df_5min, exit_date)
            if exit_idx is None:
                return None, None, "exit_open_missing"
            return exit_idx, float(ctx.df_5min.iloc[exit_idx]["open"]), f"trailing_stop_hit_day_{offset}"
        # Ratchet
        prev_high = float(entry_row["high"]) if offset == 1 else float(ctx.daily_bars.iloc[check_session_pos - 1]["high"])
        prev_low = float(entry_row["low"]) if offset == 1 else float(ctx.daily_bars.iloc[check_session_pos - 1]["low"])
        day_range = prev_high - prev_low
        if ctx.direction == 1 and day_close > entry_row["close"]:
            new_stop = day_low - day_range * (1 - ratchet_pct)
            trailing_stop = max(trailing_stop, new_stop)
        if ctx.direction == -1 and day_close < entry_row["close"]:
            new_stop = day_high + day_range * (1 - ratchet_pct)
            trailing_stop = min(trailing_stop, new_stop)
    # Max days reached → exit at next session open
    exit_session_pos = entry_pos + max_days
    if exit_session_pos >= len(sessions):
        return None, None, "max_days_exceeded_data"
    exit_date = sessions[exit_session_pos]
    exit_idx = find_session_open_idx(ctx.df_5min, exit_date)
    if exit_idx is None:
        return None, None, "exit_open_missing"
    return exit_idx, float(ctx.df_5min.iloc[exit_idx]["open"]), f"max_days_{max_days}"


EXIT_VARIANTS = {
    "A_fixed_3_day": lambda ctx: exit_fixed_n_day_hold(ctx, n_days=3),
    "B_fixed_5_day": lambda ctx: exit_fixed_n_day_hold(ctx, n_days=5),
    "C_daily_invalidation": lambda ctx: exit_daily_invalidation(ctx, max_days=5),
    "D_daily_trailing_stop": lambda ctx: exit_daily_trailing_stop(ctx, max_days=5),
}
