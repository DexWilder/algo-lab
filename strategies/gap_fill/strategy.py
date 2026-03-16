"""Gap Fill -- Fade overnight gaps on equity index futures.

Equity index futures gap at the open relative to the prior session close.
Institutional rebalancing and overnight position unwinding create a
structural tendency for gaps to fill within 2-3 hours.

Logic:
  - Gap = 09:30 ET open minus prior RTH close (last bar before 16:00)
  - Fade the gap if size is 0.5-3.0x ATR (skip noise and trend days)
  - Target: prior session close (full gap fill)
  - Stop: 1.5x ATR beyond opening price in gap direction
  - One trade per day maximum

Designed for: M2K (Micro Russell 2000) on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Session
SESSION_OPEN_HOUR = 9
SESSION_OPEN_MIN = 30
PRIOR_CLOSE_HOUR = 15
PRIOR_CLOSE_MIN = 55

# Entry
ENTRY_DELAY_BARS = 1         # Enter 1 bar after open (09:35)
ENTRY_END_HOUR = 10
ENTRY_END_MIN = 0            # Must enter within first 30 minutes

# Gap filter
GAP_ATR_MIN = 0.5            # Minimum gap (skip noise)
GAP_ATR_MAX = 3.0            # Maximum gap (skip trend days)
ATR_LEN = 20

# Risk
SL_ATR_MULT = 1.5            # Stop beyond open in gap direction
MAX_HOLD_BARS = 36           # 3 hours
FLATTEN_HOUR = 13
FLATTEN_MIN = 0

TICK_SIZE = 0.10  # M2K default


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

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    open_ = df["open"].values
    hour = df["hour"].values
    minute = df["minute"].values
    dates = df["date"].values
    atr = df["atr"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # State
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    bars_held = 0

    # Day tracking
    current_date = None
    prior_close = np.nan
    session_open_price = np.nan
    gap_traded_today = False
    bars_since_open = 0

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_open = open_[i]
        bar_atr = atr[i]
        bar_date = dates[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # ---- Track prior session close ----
        if h == PRIOR_CLOSE_HOUR and m == PRIOR_CLOSE_MIN:
            prior_close = bar_close

        # ---- New day detection ----
        if bar_date != current_date:
            current_date = bar_date
            session_open_price = np.nan
            gap_traded_today = False
            bars_since_open = 0

        # ---- Capture session open ----
        if h == SESSION_OPEN_HOUR and m == SESSION_OPEN_MIN:
            session_open_price = bar_open
            bars_since_open = 0

        if time_val >= SESSION_OPEN_HOUR * 100 + SESSION_OPEN_MIN:
            bars_since_open += 1

        # ---- Flatten ----
        if time_val >= FLATTEN_HOUR * 100 + FLATTEN_MIN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
            continue

        # ---- Manage position ----
        if position != 0:
            bars_held += 1
            if position == 1:
                if bar_low <= stop_price:
                    exit_sigs[i] = 1; position = 0; continue
                if bar_high >= target_price:
                    exit_sigs[i] = 1; position = 0; continue
            elif position == -1:
                if bar_high >= stop_price:
                    exit_sigs[i] = -1; position = 0; continue
                if bar_low <= target_price:
                    exit_sigs[i] = -1; position = 0; continue
            if bars_held >= MAX_HOLD_BARS:
                exit_sigs[i] = position; position = 0; continue

        # ---- Entry (flat, one per day, after delay) ----
        if position == 0 and not gap_traded_today:
            if bars_since_open < ENTRY_DELAY_BARS + 1:
                continue
            if time_val >= ENTRY_END_HOUR * 100 + ENTRY_END_MIN:
                continue
            if np.isnan(prior_close) or np.isnan(session_open_price):
                continue

            gap = session_open_price - prior_close
            gap_atr = abs(gap) / bar_atr if bar_atr > 0 else 0

            if gap_atr < GAP_ATR_MIN or gap_atr > GAP_ATR_MAX:
                gap_traded_today = True  # Skip this day
                continue

            # Gap up -> short (fade toward prior close)
            if gap > 0 and allow_short:
                entry_price = bar_close
                stop_price = session_open_price + bar_atr * SL_ATR_MULT
                target_price = prior_close
                signals[i] = -1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                position = -1
                bars_held = 0
                gap_traded_today = True
                continue

            # Gap down -> long (fade toward prior close)
            if gap < 0 and allow_long:
                entry_price = bar_close
                stop_price = session_open_price - bar_atr * SL_ATR_MULT
                target_price = prior_close
                signals[i] = 1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                position = 1
                bars_held = 0
                gap_traded_today = True
                continue

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "minute", "date", "atr"], inplace=True)
    return df
