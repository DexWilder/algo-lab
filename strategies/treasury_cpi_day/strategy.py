"""Treasury CPI Day -- Rates-native EVENT strategy around CPI releases.

Trade Treasury futures around the monthly CPI release. Entry at close
of day before CPI, exit at close of CPI day or next-day open.

Logic:
  - Entry: position at last bar before close (~15:55 ET) day before CPI
  - Exit variant A: close of CPI day (~15:55 ET)
  - Exit variant B: open of day after CPI (~09:35 ET next day)
  - Direction: configurable (long/short/both) for regime analysis
  - Stop: toggle (none or 1.5x ATR)
  - 12 trades per year

Designed for: ZN, ZF, ZB on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Exit variant: "cpi_close" or "next_open"
EXIT_VARIANT = "cpi_close"

# Direction: "long", "short", or "both"
DIRECTION = "long"

# Stop toggle
USE_STOP = False
ATR_LEN = 20
SL_ATR_MULT = 1.5

TICK_SIZE = 0.015625  # ZN default

# CPI release dates (2019-2026)
# Source: Bureau of Labor Statistics release calendar
# Each date is the CPI release day (data published at 08:30 ET)
CPI_DATES = [
    # 2019
    "2019-01-11", "2019-02-13", "2019-03-12", "2019-04-10",
    "2019-05-10", "2019-06-12", "2019-07-11", "2019-08-13",
    "2019-09-12", "2019-10-10", "2019-11-13", "2019-12-11",
    # 2020
    "2020-01-14", "2020-02-13", "2020-03-11", "2020-04-10",
    "2020-05-12", "2020-06-10", "2020-07-14", "2020-08-12",
    "2020-09-11", "2020-10-13", "2020-11-12", "2020-12-10",
    # 2021
    "2021-01-13", "2021-02-10", "2021-03-10", "2021-04-13",
    "2021-05-12", "2021-06-10", "2021-07-13", "2021-08-11",
    "2021-09-14", "2021-10-13", "2021-11-10", "2021-12-10",
    # 2022
    "2022-01-12", "2022-02-10", "2022-03-10", "2022-04-12",
    "2022-05-11", "2022-06-10", "2022-07-13", "2022-08-10",
    "2022-09-13", "2022-10-13", "2022-11-10", "2022-12-13",
    # 2023
    "2023-01-12", "2023-02-14", "2023-03-14", "2023-04-12",
    "2023-05-10", "2023-06-13", "2023-07-12", "2023-08-10",
    "2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
    # 2024
    "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10",
    "2024-05-15", "2024-06-12", "2024-07-11", "2024-08-14",
    "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
    # 2025
    "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10",
    "2025-05-13", "2025-06-11", "2025-07-15", "2025-08-12",
    "2025-09-10", "2025-10-14", "2025-11-12", "2025-12-10",
    # 2026
    "2026-01-13", "2026-02-11", "2026-03-11", "2026-04-14",
    "2026-05-12", "2026-06-10", "2026-07-14", "2026-08-12",
    "2026-09-15", "2026-10-13", "2026-11-12", "2026-12-09",
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

def generate_signals(df, asset=None, mode=None):
    """Generate Treasury CPI day signals."""
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date_str"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    # Use mode parameter if provided, otherwise use module-level DIRECTION
    direction = mode if mode else DIRECTION

    # Build pre-CPI dates (trading day before CPI)
    cpi_set = set(CPI_DATES)
    cpi_dates_pd = [pd.Timestamp(d) for d in CPI_DATES]
    pre_cpi_dates = set()
    cpi_to_pre = {}
    for cd in cpi_dates_pd:
        pre = cd - pd.Timedelta(days=1)
        while pre.weekday() >= 5:
            pre -= pd.Timedelta(days=1)
        pre_str = pre.strftime("%Y-%m-%d")
        pre_cpi_dates.add(pre_str)
        cpi_to_pre[cd.strftime("%Y-%m-%d")] = pre_str

    # Build day-after-CPI dates for next_open exit variant
    post_cpi_dates = set()
    for cd in cpi_dates_pd:
        post = cd + pd.Timedelta(days=1)
        while post.weekday() >= 5:
            post += pd.Timedelta(days=1)
        post_cpi_dates.add(post.strftime("%Y-%m-%d"))

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
        bar_high = high[i]
        bar_low = low[i]
        bar_atr = atr[i]
        bar_date = date_str[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # ---- Exit logic ----
        if position != 0:
            should_exit = False

            # Stop
            if USE_STOP:
                if position == 1 and bar_low <= stop_price:
                    should_exit = True
                elif position == -1 and bar_high >= stop_price:
                    should_exit = True

            # CPI-day close exit (CBOT RTH close ~15:00, use 14:55-15:05 window)
            if EXIT_VARIANT == "cpi_close":
                if bar_date in cpi_set and bar_date != entry_date and 1455 <= time_val <= 1505:
                    should_exit = True

            # Next-day open exit (CBOT RTH open ~08:20, use 08:20-08:35 window)
            elif EXIT_VARIANT == "next_open":
                if bar_date in post_cpi_dates and 820 <= time_val <= 835:
                    should_exit = True

            # Safety: force exit if held > 48 hours (prevents month-long holds from bugs)
            if not should_exit and position != 0 and i > 0:
                entry_idx = max(0, i - 600)  # ~50 hours of 5m bars
                if signals[entry_idx:i+1].sum() == 0 and bar_date not in cpi_set and bar_date != entry_date:
                    # Check if we've passed the CPI day already
                    if bar_date > entry_date:
                        days_held = (pd.Timestamp(bar_date) - pd.Timestamp(entry_date)).days
                        if days_held > 2:
                            should_exit = True

            if should_exit:
                exit_sigs[i] = position
                position = 0
                continue

        # ---- Entry logic ----
        # Entry at CBOT RTH close (~15:00 ET) on pre-CPI day
        # Use 14:55-15:05 window to catch the nearest bar
        if position == 0:
            if bar_date in pre_cpi_dates and 1455 <= time_val <= 1505:
                if direction in ("long", "both"):
                    entry_price = bar_close
                    stop_price = bar_close - bar_atr * SL_ATR_MULT if USE_STOP else 0
                    signals[i] = 1
                    stop_arr[i] = stop_price if USE_STOP else np.nan
                    position = 1
                    entry_date = bar_date
                elif direction == "short":
                    entry_price = bar_close
                    stop_price = bar_close + bar_atr * SL_ATR_MULT if USE_STOP else 0
                    signals[i] = -1
                    stop_arr[i] = stop_price if USE_STOP else np.nan
                    position = -1
                    entry_date = bar_date

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date_str", "hour", "minute", "atr"], inplace=True)
    return df
