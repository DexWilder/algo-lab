"""NR7 Breakout -- Volatility compression then expansion.

When a bar's range is the narrowest of the last 7 bars, volatility
compression signals an imminent directional move. Trade the breakout
from the NR7 bar's range on the next bar.

Classic Crabel (1990) pattern. Designed to be asset-agnostic so
batch_first_pass can test across M2K, MES, MNQ and others.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# NR detection
NR_LOOKBACK = 7              # Classic NR7
COMPRESSION_ATR_MAX = 0.6    # NR bar range must be < this * ATR (configurable)

# ATR
ATR_LEN = 20

# Risk
SL_BUFFER_ATR = 0.5          # Stop beyond opposite NR7 edge + buffer
TP_ATR_MULT = 2.0
TRAIL_ACTIVATION_R = 1.0     # Trail after 1.0R
TRAIL_ATR_MULT = 1.0

# Time
MAX_HOLD_BARS = 24           # 2 hours
MIN_BARS_BETWEEN = 6
ENTRY_START_HOUR = 9
ENTRY_START_MIN = 45
ENTRY_END_HOUR = 14
ENTRY_END_MIN = 30
FLATTEN_HOUR = 15
FLATTEN_MIN = 0

TICK_SIZE = 0.10  # M2K default, patched per asset


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
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)
    df["range"] = df["high"] - df["low"]

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    minute = df["minute"].values
    atr = df["atr"].values
    bar_range = df["range"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # Position state
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    trail_active = False
    trailing_stop = 0.0
    best_price = 0.0
    bars_held = 0
    bars_since_trade = MIN_BARS_BETWEEN

    # NR7 state
    nr7_armed = False
    nr7_high = 0.0
    nr7_low = 0.0

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_atr = atr[i]
        br = bar_range[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0 or i < NR_LOOKBACK:
            bars_since_trade += 1
            continue

        # ---- Flatten ----
        if time_val >= FLATTEN_HOUR * 100 + FLATTEN_MIN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
                bars_since_trade = 0
            nr7_armed = False
            continue

        # ---- Manage position ----
        if position != 0:
            bars_held += 1
            if position == 1:
                if bar_close > best_price:
                    best_price = bar_close
                r_dist = abs(entry_price - stop_price)
                if not trail_active and r_dist > 0 and (best_price - entry_price) >= TRAIL_ACTIVATION_R * r_dist:
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
                r_dist = abs(stop_price - entry_price)
                if not trail_active and r_dist > 0 and (entry_price - best_price) >= TRAIL_ACTIVATION_R * r_dist:
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

            if bars_held >= MAX_HOLD_BARS:
                exit_sigs[i] = position; position = 0; bars_since_trade = 0; continue

        # ---- NR7 Detection ----
        # Check if current bar is the narrowest of last NR_LOOKBACK bars
        if i >= NR_LOOKBACK and not nr7_armed and position == 0:
            recent_ranges = bar_range[i - NR_LOOKBACK + 1:i + 1]
            if br == recent_ranges.min() and br > 0:
                # Compression filter: range must be < threshold * ATR
                if br < bar_atr * COMPRESSION_ATR_MAX:
                    nr7_armed = True
                    nr7_high = bar_high
                    nr7_low = bar_low

        # ---- Entry (flat, NR7 armed, next bar) ----
        if position == 0 and nr7_armed:
            bars_since_trade += 1
            nr7_armed = False  # Consume the signal (one-bar window)

            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            entry_start = ENTRY_START_HOUR * 100 + ENTRY_START_MIN
            entry_end = ENTRY_END_HOUR * 100 + ENTRY_END_MIN
            if time_val < entry_start or time_val >= entry_end:
                continue

            # Long breakout above NR7 high
            if allow_long and bar_close > nr7_high:
                entry_price = bar_close
                stop_price = nr7_low - bar_atr * SL_BUFFER_ATR
                target_price = bar_close + bar_atr * TP_ATR_MULT
                signals[i] = 1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                position = 1
                trail_active = False
                trailing_stop = stop_price
                best_price = bar_close
                bars_held = 0
                bars_since_trade = 0
                continue

            # Short breakout below NR7 low
            if allow_short and bar_close < nr7_low:
                entry_price = bar_close
                stop_price = nr7_high + bar_atr * SL_BUFFER_ATR
                target_price = bar_close - bar_atr * TP_ATR_MULT
                signals[i] = -1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                position = -1
                trail_active = False
                trailing_stop = stop_price
                best_price = bar_close
                bars_held = 0
                bars_since_trade = 0
                continue
        elif position == 0:
            bars_since_trade += 1

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "minute", "atr", "range"], inplace=True)
    return df
