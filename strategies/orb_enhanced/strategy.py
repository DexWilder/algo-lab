"""ORB-ENHANCED — Enhanced Opening Range Breakout with Volatility & Volume Filters.

Target asset: M2K (Russell 2000 micro futures), 5-minute bars.
Enhancement over ORB-009: range filter, volume confirmation, ATR stops, profit ladder exit.

Logic:
- Opening range: first 6 bars (09:30-10:00 ET)
- Entry: close breaks above/below opening range high/low
- Range filter: OR must be 0.5x-2.0x the 10-day average OR (skip abnormal ranges)
- Volume confirmation: breakout bar volume > 1.2x mean OR bar volume
- ATR-based stop: 1.5 * ATR(14) from entry price
- Profit ladder exit: lock 0.25R at 1R, lock 1R at 2R, lock 2R at 3R
- Time filter: entries only 10:00-14:00 ET
- Max 1 trade per direction per day
- EOD flatten at 15:30

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ----------------------------------------------------------------

OR_BARS = 6                  # First 6 bars = 30 min opening range
ATR_PERIOD = 14              # ATR lookback
ATR_STOP_MULT = 1.5          # Stop = 1.5 * ATR from entry
RANGE_AVG_DAYS = 10          # Lookback for average opening range
RANGE_MIN_MULT = 0.5         # OR must be >= 0.5x average
RANGE_MAX_MULT = 2.0         # OR must be <= 2.0x average
VOL_CONFIRM_MULT = 1.2       # Breakout bar vol > 1.2x mean OR bar vol

# Profit ladder: at N*R, lock M*R as trailing stop floor
LADDER_RUNGS = [
    (1.0, 0.25),   # At 1R profit, lock 0.25R
    (2.0, 1.0),    # At 2R profit, lock 1.0R
    (3.0, 2.0),    # At 3R profit, lock 2.0R
]

SESSION_START = "09:30"
OR_END = "10:00"
ENTRY_START = "10:00"
ENTRY_END = "14:00"
FLATTEN_TIME = "15:30"
SESSION_END = "15:45"

TICK_SIZE = 0.25              # Patched per asset by runner


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset=None, mode="long") -> pd.DataFrame:
    """Generate enhanced ORB breakout signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- ATR -------------------------------------------------------------------
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean()

    # -- Opening Range per day -------------------------------------------------
    in_or = (time_str >= SESSION_START) & (time_str < OR_END)
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    or_bars = df[in_or].copy()
    if or_bars.empty:
        df["signal"] = 0
        df["exit_signal"] = 0
        df["stop_price"] = np.nan
        df["target_price"] = np.nan
        df.drop(columns=["_date"], inplace=True)
        return df

    or_stats = or_bars.groupby("_date").agg(
        or_high=("high", "max"),
        or_low=("low", "min"),
    )
    or_stats["or_range"] = or_stats["or_high"] - or_stats["or_low"]

    # Average opening range volume per bar (for volume confirmation)
    or_vol_mean = or_bars.groupby("_date")["volume"].mean().rename("or_vol_mean")
    or_stats = or_stats.join(or_vol_mean)

    # Rolling average OR range over past N days (for range filter)
    or_stats["avg_or_range"] = (
        or_stats["or_range"]
        .shift(1)
        .rolling(window=RANGE_AVG_DAYS, min_periods=3)
        .mean()
    )

    # Range filter flags
    or_stats["range_ok"] = (
        (or_stats["or_range"] >= or_stats["avg_or_range"] * RANGE_MIN_MULT) &
        (or_stats["or_range"] <= or_stats["avg_or_range"] * RANGE_MAX_MULT)
    )
    # If avg_or_range is NaN (first few days), allow the trade
    or_stats.loc[or_stats["avg_or_range"].isna(), "range_ok"] = True

    df = df.merge(or_stats, left_on="_date", right_index=True, how="left")
    df["_atr"] = atr.values

    # -- Pre-compute arrays for stateful loop ----------------------------------
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    volume_arr = df["volume"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    atr_arr = df["_atr"].values
    or_high_arr = df["or_high"].values
    or_low_arr = df["or_low"].values
    or_range_arr = df["or_range"].values
    range_ok_arr = df["range_ok"].values
    or_vol_mean_arr = df["or_vol_mean"].values

    has_volume = df["volume"].sum() > 0

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful entry/exit loop ----------------------------------------------
    position = 0
    entry_price = 0.0
    initial_risk = 0.0        # 1R = distance from entry to initial stop
    trailing_stop = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue

        # -- Pre-close flatten -------------------------------------------------
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # -- Check exits for open position (profit ladder) ---------------------
        if position == 1:
            # Walk the ladder: check each rung from highest to lowest
            for r_mult, lock_mult in reversed(LADDER_RUNGS):
                threshold = entry_price + initial_risk * r_mult
                if high_arr[i] >= threshold:
                    lock_level = entry_price + initial_risk * lock_mult
                    if lock_level > trailing_stop:
                        trailing_stop = lock_level
                    break

            if low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            for r_mult, lock_mult in reversed(LADDER_RUNGS):
                threshold = entry_price - initial_risk * r_mult
                if low_arr[i] <= threshold:
                    lock_level = entry_price - initial_risk * lock_mult
                    if lock_level < trailing_stop:
                        trailing_stop = lock_level
                    break

            if high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # -- Entry logic -------------------------------------------------------
        if position == 0 and bar_time >= ENTRY_START and bar_time < ENTRY_END:
            or_h = or_high_arr[i]
            or_l = or_low_arr[i]
            bar_atr = atr_arr[i]

            if np.isnan(or_h) or np.isnan(or_l) or np.isnan(bar_atr):
                continue

            # Range filter
            if not range_ok_arr[i]:
                continue

            # Volume confirmation
            if has_volume:
                or_vol = or_vol_mean_arr[i]
                if np.isnan(or_vol) or or_vol <= 0:
                    vol_ok = True  # no volume data for this day, allow
                else:
                    vol_ok = volume_arr[i] > or_vol * VOL_CONFIRM_MULT
            else:
                vol_ok = True

            if not vol_ok:
                continue

            stop_dist = bar_atr * ATR_STOP_MULT
            if stop_dist <= 0:
                continue

            # Long breakout
            if not long_traded_today and close_arr[i] > or_h:
                if mode in ("long", "both"):
                    entry_px = close_arr[i]
                    stop_px = entry_px - stop_dist
                    # Target: 3R (for target_price column; actual exit via ladder)
                    target_px = entry_px + stop_dist * 3.0

                    signals_arr[i] = 1
                    stop_arr[i] = stop_px
                    target_arr[i] = target_px

                    position = 1
                    entry_price = entry_px
                    initial_risk = stop_dist
                    trailing_stop = stop_px
                    long_traded_today = True

            # Short breakout
            elif not short_traded_today and close_arr[i] < or_l:
                if mode in ("short", "both"):
                    entry_px = close_arr[i]
                    stop_px = entry_px + stop_dist
                    target_px = entry_px - stop_dist * 3.0

                    signals_arr[i] = -1
                    stop_arr[i] = stop_px
                    target_arr[i] = target_px

                    position = -1
                    entry_price = entry_px
                    initial_risk = stop_dist
                    trailing_stop = stop_px
                    short_traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(
        columns=["_date", "or_high", "or_low", "or_range", "or_vol_mean",
                 "avg_or_range", "range_ok", "_atr"],
        inplace=True,
        errors="ignore",
    )

    return df
