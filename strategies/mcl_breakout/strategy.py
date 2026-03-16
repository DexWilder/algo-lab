"""MCL Opening Range Breakout -- Crude oil intraday momentum.

Crude oil exhibits strong intraday momentum after breaking out of the
NYMEX opening range. Energy sector news, inventory positioning, and
institutional order clustering drive the first-hour price discovery.

Logic:
  - Opening range: 09:00-09:30 ET (first 30 minutes of NYMEX session)
  - Entry: close above OR high (long) or below OR low (short) after 09:30
  - Filter: opening range must be 0.3-2.5x ATR (skip abnormal ranges)
  - Volume: optional confirmation toggle (1.2x average)
  - Stop: 1.5x ATR beyond opposite side of OR
  - Target: 2.0x ATR from entry
  - Trail: after 1.5R, trail at 1.0x ATR
  - Flatten: 14:00 ET

Designed for: MCL (Micro Crude Oil) on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Opening range
OR_START_HOUR = 9
OR_START_MIN = 0
OR_END_HOUR = 9
OR_END_MIN = 30

# Entry window (after OR closes)
ENTRY_START_HOUR = 9
ENTRY_START_MIN = 30
ENTRY_END_HOUR = 12
ENTRY_END_MIN = 0

# Flatten
FLATTEN_HOUR = 14
FLATTEN_MIN = 0

# Range filters
ATR_LEN = 20
OR_ATR_MIN = 0.3      # Skip if OR < 0.3x ATR (too tight, likely false break)
OR_ATR_MAX = 2.5      # Skip if OR > 2.5x ATR (already extended)

# Volume (toggle)
VOLUME_FILTER = False  # Set True to require volume confirmation
VOLUME_MULT = 1.2      # Bar volume > 1.2x rolling average

# Risk
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.0
TRAIL_ACTIVATION_R = 1.5
TRAIL_ATR_MULT = 1.0

# Cooldown
MIN_BARS_BETWEEN = 6

TICK_SIZE = 0.01  # MCL default


# ---- Helpers ----

def _atr(high, low, close, period):
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ---- Signal Generator ----

def generate_signals(df, asset=None, mode="both"):
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["date"] = df["datetime"].dt.date
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)
    df["vol_avg"] = df["volume"].rolling(50, min_periods=10).mean()

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    minute = df["minute"].values
    dates = df["date"].values
    atr = df["atr"].values
    volume = df["volume"].values
    vol_avg = df["vol_avg"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # OR tracking
    or_high = np.nan
    or_low = np.nan
    or_ready = False
    current_date = None
    in_or = False

    # Position state
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    trail_active = False
    trailing_stop = 0.0
    best_price = 0.0
    bars_since_trade = MIN_BARS_BETWEEN

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_atr = atr[i]
        bar_vol = volume[i]
        bar_vol_avg = vol_avg[i]
        bar_date = dates[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Opening range accumulation ----
        if bar_date != current_date:
            current_date = bar_date
            or_high = np.nan
            or_low = np.nan
            or_ready = False
            in_or = False

        or_start = OR_START_HOUR * 100 + OR_START_MIN
        or_end = OR_END_HOUR * 100 + OR_END_MIN

        if time_val >= or_start and time_val < or_end:
            if not in_or:
                or_high = bar_high
                or_low = bar_low
                in_or = True
            else:
                or_high = max(or_high, bar_high)
                or_low = min(or_low, bar_low)
        elif in_or and time_val >= or_end:
            in_or = False
            or_ready = True

        # ---- Flatten ----
        if time_val >= FLATTEN_HOUR * 100 + FLATTEN_MIN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
                bars_since_trade = 0
            continue

        # ---- Manage position ----
        if position == 1:
            if bar_close > best_price:
                best_price = bar_close
            r_dist = bar_atr * SL_ATR_MULT
            if not trail_active and (best_price - entry_price) >= TRAIL_ACTIVATION_R * r_dist:
                trail_active = True
                trailing_stop = best_price - bar_atr * TRAIL_ATR_MULT
            if trail_active:
                new_trail = best_price - bar_atr * TRAIL_ATR_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail
            active_stop = trailing_stop if trail_active else stop_price
            if bar_low <= active_stop:
                exit_sigs[i] = 1; position = 0; bars_since_trade = 0; continue
            if bar_high >= target_price:
                exit_sigs[i] = 1; position = 0; bars_since_trade = 0; continue

        elif position == -1:
            if bar_close < best_price:
                best_price = bar_close
            r_dist = bar_atr * SL_ATR_MULT
            if not trail_active and (entry_price - best_price) >= TRAIL_ACTIVATION_R * r_dist:
                trail_active = True
                trailing_stop = best_price + bar_atr * TRAIL_ATR_MULT
            if trail_active:
                new_trail = best_price + bar_atr * TRAIL_ATR_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail
            active_stop = trailing_stop if trail_active else stop_price
            if bar_high >= active_stop:
                exit_sigs[i] = -1; position = 0; bars_since_trade = 0; continue
            if bar_low <= target_price:
                exit_sigs[i] = -1; position = 0; bars_since_trade = 0; continue

        # ---- Entry (flat, after OR, within entry window) ----
        if position == 0:
            bars_since_trade += 1
            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            entry_start = ENTRY_START_HOUR * 100 + ENTRY_START_MIN
            entry_end = ENTRY_END_HOUR * 100 + ENTRY_END_MIN
            if time_val < entry_start or time_val >= entry_end:
                continue
            if not or_ready or np.isnan(or_high):
                continue

            or_range = or_high - or_low
            if or_range <= 0:
                continue
            if or_range < bar_atr * OR_ATR_MIN or or_range > bar_atr * OR_ATR_MAX:
                continue

            # Volume filter (if enabled)
            if VOLUME_FILTER and bar_vol_avg > 0 and bar_vol < bar_vol_avg * VOLUME_MULT:
                continue

            # Long breakout
            if allow_long and bar_close > or_high:
                entry_price = bar_close
                stop_price = or_low - bar_atr * SL_ATR_MULT
                target_price = bar_close + bar_atr * TP_ATR_MULT
                signals[i] = 1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                position = 1
                trail_active = False
                trailing_stop = stop_price
                best_price = bar_close
                bars_since_trade = 0
                or_ready = False
                continue

            # Short breakout
            if allow_short and bar_close < or_low:
                entry_price = bar_close
                stop_price = or_high + bar_atr * SL_ATR_MULT
                target_price = bar_close - bar_atr * TP_ATR_MULT
                signals[i] = -1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                position = -1
                trail_active = False
                trailing_stop = stop_price
                best_price = bar_close
                bars_since_trade = 0
                or_ready = False
                continue

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "minute", "date", "atr", "vol_avg"], inplace=True)
    return df
