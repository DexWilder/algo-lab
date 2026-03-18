"""Commodity Carry Proxy -- 60-day trailing return as carry-direction signal.

This is a CARRY-PROXY test, not true term-structure carry. We only have
continuous front-contract data, so the 60-day trailing return conflates
carry with momentum. The first-pass question is whether this proxy
produces a tradeable edge on MCL and MGC.

Logic:
  - Resample 5m bars to daily OHLCV
  - Compute 60-day trailing return as carry score
  - Monthly rebalance: go long if carry score > 0, short if < 0
  - Two variants via MIN_SPREAD_PCT parameter:
    Variant A (filtered): only trade if |carry_score| > 2%
    Variant B (unfiltered): always trade the rank signal
  - Optional ATR trailing stop
  - Hold through the month until next rebalance

Designed for: MCL (Micro Crude), MGC (Micro Gold).
Single-asset mode -- run on each asset independently.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

CARRY_LOOKBACK_DAYS = 60       # Trailing return window (trading days)
MIN_SPREAD_PCT = 0.02          # Min |carry_score| to trade (0.0 = unfiltered)
ATR_LEN = 20                   # ATR period for stop
USE_STOP = False               # Toggle trailing stop
SL_ATR_MULT = 2.5              # Stop distance in ATR multiples
MIN_BARS_BETWEEN = 0           # No cooldown (monthly rebalance handles spacing)

TICK_SIZE = 0.01               # MCL default, patched per asset


# ---- Helpers ----

def _resample_daily(df):
    """Resample 5m bars to daily OHLCV."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date

    daily = df.groupby("date").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).reset_index()
    daily["datetime"] = pd.to_datetime(daily["date"])
    return daily


def _atr(high, low, close, period):
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _is_month_end(dates):
    """Mark the last trading day of each month."""
    result = np.zeros(len(dates), dtype=bool)
    for i in range(len(dates) - 1):
        if dates[i].month != dates[i + 1].month:
            result[i] = True
    # Last bar is always a month-end for signal purposes
    if len(dates) > 0:
        result[-1] = True
    return result


# ---- Signal Generator ----

def generate_signals(df, asset=None, mode="both"):
    """Generate carry-proxy signals on daily bars.

    Accepts 5-minute data (resamples internally) or daily data.
    Runs on a single asset -- cross-sectional ranking is done externally
    if/when we have multiple assets in a portfolio context.
    """
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Detect if already daily or needs resampling
    if len(df) > 0:
        time_diff = df["datetime"].diff().median()
        if time_diff < pd.Timedelta(hours=1):
            daily = _resample_daily(df)
        else:
            daily = df.copy()
    else:
        return df

    n = len(daily)
    if n < CARRY_LOOKBACK_DAYS + 10:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Compute carry proxy: trailing return over lookback window
    daily["carry_score"] = daily["close"].pct_change(CARRY_LOOKBACK_DAYS)
    daily["atr"] = _atr(daily["high"], daily["low"], daily["close"], ATR_LEN)

    # Identify month-end rebalance dates
    dates_dt = pd.to_datetime(daily["date"]).values.astype("datetime64[D]")
    dates_as_dt = [pd.Timestamp(d) for d in dates_dt]
    month_end = _is_month_end(dates_as_dt)

    close = daily["close"].values
    high = daily["high"].values
    low = daily["low"].values
    carry = daily["carry_score"].values
    atr = daily["atr"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    trailing_stop = 0.0
    best_price = 0.0
    pending_signal = 0  # Signal decided at month-end, executed next bar

    for i in range(n):
        c = close[i]
        h = high[i]
        l = low[i]
        bar_atr = atr[i]
        bar_carry = carry[i]

        if np.isnan(bar_atr) or bar_atr == 0 or np.isnan(bar_carry):
            continue

        # ---- Execute pending signal from prior month-end ----
        if pending_signal != 0:
            new_dir = pending_signal
            pending_signal = 0

            # Close existing position if direction changed
            if position != 0 and position != new_dir:
                exit_sigs[i] = position
                position = 0

            # Open new position
            if position == 0 and new_dir != 0:
                if (new_dir == 1 and allow_long) or (new_dir == -1 and allow_short):
                    signals[i] = new_dir
                    position = new_dir
                    best_price = c
                    if USE_STOP:
                        if new_dir == 1:
                            trailing_stop = c - bar_atr * SL_ATR_MULT
                        else:
                            trailing_stop = c + bar_atr * SL_ATR_MULT
                        stop_arr[i] = trailing_stop
                    continue

            # If pending was flat signal (0 after filter), we already exited above
            continue

        # ---- Manage position: trailing stop ----
        if position == 1 and USE_STOP:
            if c > best_price:
                best_price = c
            new_trail = best_price - bar_atr * SL_ATR_MULT
            if new_trail > trailing_stop:
                trailing_stop = new_trail

            if l <= trailing_stop:
                exit_sigs[i] = 1
                position = 0
                continue

        elif position == -1 and USE_STOP:
            if c < best_price:
                best_price = c
            new_trail = best_price + bar_atr * SL_ATR_MULT
            if new_trail < trailing_stop:
                trailing_stop = new_trail

            if h >= trailing_stop:
                exit_sigs[i] = -1
                position = 0
                continue

        # ---- Month-end: evaluate carry signal for next bar ----
        if month_end[i]:
            # Determine direction from carry score
            if abs(bar_carry) < MIN_SPREAD_PCT:
                # Below threshold -- go flat
                if position != 0:
                    pending_signal = 0
                    # Exit on next bar
                    exit_sigs[i] = position
                    position = 0
            elif bar_carry > 0:
                if position != 1:
                    pending_signal = 1
            else:
                if position != -1:
                    pending_signal = -1

    daily["signal"] = signals
    daily["exit_signal"] = exit_sigs
    daily["stop_price"] = stop_arr
    daily["target_price"] = target_arr

    # Clean up
    drop_cols = ["carry_score", "atr", "date"]
    daily.drop(columns=[c for c in drop_cols if c in daily.columns],
               inplace=True, errors="ignore")

    return daily
