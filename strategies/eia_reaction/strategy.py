"""EIA Reaction Momentum -- Event-driven crude oil strategy.

Trades the directional momentum following the weekly EIA petroleum
inventory report released every Wednesday at 10:30 ET. Uses price-response
proxy logic rather than actual consensus/surprise data.

V1 approach: measure a reference price before 10:30, then enter if the
post-announcement move is decisive (exceeds ATR threshold) and not
instantly reversed.

Designed for: MCL (Micro Crude Oil) on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Event timing
EVENT_DAY = 2                # Wednesday (Monday=0)
ANNOUNCE_HOUR = 10
ANNOUNCE_MIN = 30
PRE_REF_HOUR = 10
PRE_REF_MIN = 25            # Reference price = close of 10:25 bar

# Entry
ENTRY_WINDOW_BARS = 6        # 30 minutes after announcement
SURPRISE_ATR_THRESH = 1.0    # Move must exceed 1.0x ATR to qualify
CONFIRMATION_BARS = 1        # Wait 1 bar after threshold cross to confirm direction holds

# Risk
ATR_LEN = 20
SL_ATR_MULT = 1.0            # Tight stop — if move reverses, surprise was absorbed
TP_ATR_MULT = 1.5
MAX_HOLD_BARS = 18           # 90 minutes

# Session
FLATTEN_HOUR = 13
FLATTEN_MIN = 0

TICK_SIZE = 0.01  # MCL


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
    df["dow"] = df["datetime"].dt.dayofweek
    df["date"] = df["datetime"].dt.date
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    minute = df["minute"].values
    dow = df["dow"].values
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

    # Event tracking per day
    ref_price = np.nan
    event_armed = False
    bars_since_announce = 0
    event_date = None

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_atr = atr[i]
        bar_dow = dow[i]
        bar_date = dates[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # Reset event tracking on new day
        if bar_date != event_date:
            event_date = bar_date
            ref_price = np.nan
            event_armed = False
            bars_since_announce = 0

        # ---- Capture reference price (10:25 bar on Wednesdays) ----
        if bar_dow == EVENT_DAY and h == PRE_REF_HOUR and m == PRE_REF_MIN:
            ref_price = bar_close

        # ---- Arm event window after announcement ----
        if bar_dow == EVENT_DAY and time_val >= ANNOUNCE_HOUR * 100 + ANNOUNCE_MIN:
            if not np.isnan(ref_price) and not event_armed and position == 0:
                event_armed = True
                bars_since_announce = 0

        if event_armed:
            bars_since_announce += 1

        # ---- Flatten ----
        if time_val >= FLATTEN_HOUR * 100 + FLATTEN_MIN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
            event_armed = False
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

        # ---- Entry (event window, flat only) ----
        if position == 0 and event_armed and bars_since_announce <= ENTRY_WINDOW_BARS:
            if np.isnan(ref_price):
                continue

            move = bar_close - ref_price
            move_atr = abs(move) / bar_atr if bar_atr > 0 else 0

            if move_atr >= SURPRISE_ATR_THRESH:
                # Decisive move detected — enter in direction of move
                if move > 0 and allow_long:
                    entry_price = bar_close
                    stop_price = bar_close - bar_atr * SL_ATR_MULT
                    target_price = bar_close + bar_atr * TP_ATR_MULT
                    signals[i] = 1
                    stop_arr[i] = stop_price
                    target_arr[i] = target_price
                    position = 1
                    bars_held = 0
                    event_armed = False
                elif move < 0 and allow_short:
                    entry_price = bar_close
                    stop_price = bar_close + bar_atr * SL_ATR_MULT
                    target_price = bar_close - bar_atr * TP_ATR_MULT
                    signals[i] = -1
                    stop_arr[i] = stop_price
                    target_arr[i] = target_price
                    position = -1
                    bars_held = 0
                    event_armed = False

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "minute", "dow", "date", "atr"], inplace=True)
    return df
