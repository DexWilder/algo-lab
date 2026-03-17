"""Pre-FOMC Drift v2 -- Calendar-driven equity long before FOMC.

Equity indices drift higher in the ~24 hours before scheduled FOMC
announcements. Documented by Lucca & Moench (NY Fed, 2015).

Logic:
  - Entry: long at close of day before FOMC announcement
  - Exit variant A: 13:55 ET on FOMC day (before 14:00 announcement)
  - Exit variant B: close of FOMC day (capture any continuation)
  - Stop: toggle (none or 1.5x ATR)
  - 8 trades per year (known FOMC calendar)

V2 differences from rejected pre_fomc_drift:
  - Strictly FOMC-only (not broader events)
  - Day-before-close entry (not intraday)
  - Two exit variants tested
  - Stop as toggle

Designed for: MES, MNQ on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Exit variant: "pre_announcement" (13:55 ET) or "close" (16:00 ET on FOMC day)
EXIT_VARIANT = "pre_announcement"

# Stop toggle
USE_STOP = True
ATR_LEN = 20
SL_ATR_MULT = 1.5

TICK_SIZE = 0.25  # MES default

# FOMC announcement dates (2019-2026)
# Source: Federal Reserve Board calendar
# Each date is the ANNOUNCEMENT day (the day the decision is released at 14:00 ET)
FOMC_DATES = [
    # 2019
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
    "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    # 2020
    "2020-01-29", "2020-03-03", "2020-03-15", "2020-04-29",
    "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    # 2021
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
    "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    # 2022
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    # 2023
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # 2025
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-17",
    # 2026
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-16",
]


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
    """Generate pre-FOMC drift signals. Long only by design."""
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    df["date_str"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    # Build set of FOMC dates and pre-FOMC dates (day before)
    fomc_set = set(FOMC_DATES)
    fomc_dates_pd = [pd.Timestamp(d) for d in FOMC_DATES]
    pre_fomc_dates = set()
    for fd in fomc_dates_pd:
        # Day before FOMC — handle weekends
        pre = fd - pd.Timedelta(days=1)
        while pre.weekday() >= 5:  # Skip weekends
            pre -= pd.Timedelta(days=1)
        pre_fomc_dates.add(pre.strftime("%Y-%m-%d"))

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    minute = df["minute"].values
    date_str = df["date_str"].values
    atr = df["atr"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    entry_date = ""

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_low = low[i]
        bar_high = high[i]
        bar_atr = atr[i]
        bar_date = date_str[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # ---- Exit logic ----
        if position == 1:
            should_exit = False

            # Stop loss (if enabled)
            if USE_STOP and bar_low <= stop_price:
                should_exit = True

            # Exit on FOMC day
            if bar_date in fomc_set:
                if EXIT_VARIANT == "pre_announcement" and time_val >= 1355:
                    should_exit = True
                elif EXIT_VARIANT == "close" and time_val >= 1555:
                    should_exit = True

            if should_exit:
                exit_sigs[i] = 1
                position = 0
                continue

        # ---- Entry logic ----
        if position == 0:
            # Entry: last bar of pre-FOMC day (close, ~15:55)
            if bar_date in pre_fomc_dates and time_val >= 1555:
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
    df.drop(columns=["date", "date_str", "hour", "minute", "atr"], inplace=True)
    return df
