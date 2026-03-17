"""Equity Overnight Drift -- Structural overnight premium capture.

Buy at the close, sell at the next open. Captures the documented
overnight equity premium (close-to-open returns > open-to-close).

Logic:
  - Entry: long at last bar before close (~15:55 ET)
  - Exit variant A: sell at 09:35 ET (first bar after open)
  - Exit variant B: sell at 10:00 ET (let opening settle)
  - Stop: toggle (none or 1.5x ATR)
  - Trades every day (~250/year)

Designed for: MES, MNQ on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

ENTRY_HOUR = 15
ENTRY_MIN = 55

# Exit variant: "open" (09:35) or "settled" (10:00)
EXIT_VARIANT = "open"
EXIT_OPEN_HOUR = 9
EXIT_OPEN_MIN = 35
EXIT_SETTLED_HOUR = 10
EXIT_SETTLED_MIN = 0

# Stop toggle
USE_STOP = False
ATR_LEN = 20
SL_ATR_MULT = 1.5

TICK_SIZE = 0.25  # MES default


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
    """Generate overnight drift signals. Long only by design."""
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
    hour = df["hour"].values
    minute = df["minute"].values
    dates = df["date"].values
    atr = df["atr"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    entry_date = None

    # Determine exit time based on variant
    if EXIT_VARIANT == "open":
        exit_h, exit_m = EXIT_OPEN_HOUR, EXIT_OPEN_MIN
    else:
        exit_h, exit_m = EXIT_SETTLED_HOUR, EXIT_SETTLED_MIN

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_atr = atr[i]
        bar_date = dates[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # ---- Exit logic ----
        if position == 1:
            should_exit = False

            # Stop loss (if enabled)
            if USE_STOP and bar_low <= stop_price:
                should_exit = True

            # Exit at target time on a DIFFERENT date than entry
            if bar_date != entry_date and time_val >= exit_h * 100 + exit_m:
                should_exit = True

            if should_exit:
                exit_sigs[i] = 1
                position = 0
                continue

        # ---- Entry logic ----
        if position == 0:
            # Entry at close (~15:55)
            if h == ENTRY_HOUR and m == ENTRY_MIN:
                entry_price = bar_close
                stop_price = bar_close - bar_atr * SL_ATR_MULT if USE_STOP else 0
                signals[i] = 1
                stop_arr[i] = stop_price if USE_STOP else np.nan
                position = 1
                entry_date = bar_date

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "minute", "date", "atr"], inplace=True)
    return df
