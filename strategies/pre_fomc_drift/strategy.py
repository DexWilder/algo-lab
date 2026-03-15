"""Pre-FOMC Announcement Drift — Event-Driven Strategy.

Source: Lucca & Moench (NY Fed Staff Report 512)
"The Pre-FOMC Announcement Drift"
49 bps average return in 24h window before FOMC announcement.
Still alive through 2024 per QuantSeeker analysis.

Logic:
  1. On the day BEFORE a scheduled FOMC announcement, enter long at 14:00 ET.
  2. Hold through the announcement day.
  3. Exit at 14:00 ET on announcement day (15 min before typical release time).
  4. Wide stop: 3x ATR (this is a swing hold, not a scalp).
  5. Only 8 trades per year (scheduled FOMC meetings).

For 5m intraday simulation:
  - Since we can't hold overnight in the backtest engine (fill-at-next-open, EOD),
    we approximate by entering at 14:00 on FOMC day and holding until 14:00 next day.
  - Actually: enter long at session open on FOMC announcement day, exit at 14:00 ET.
  - This captures the pre-announcement drift that accumulates morning of announcement.

FOMC Schedule (8 meetings per year, fixed dates):
  The strategy uses a calendar of FOMC dates embedded in the code.
  These must be updated annually.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

ATR_PERIOD = 14
ATR_STOP_MULT = 3.0         # Wide stop for event trade
ATR_TARGET_MULT = 4.0       # Wide target

ENTRY_TIME = "09:35"         # Enter shortly after open on FOMC day
EXIT_TIME = "13:45"          # Exit before 14:00 announcement
SESSION_START = "09:30"

TICK_SIZE = 0.25

# ── FOMC Meeting Dates (announcement days) ──────────────────────────────────
# These are the FOMC announcement dates. Enter long morning of these dates.
# Update annually. Source: Federal Reserve calendar.

FOMC_DATES = {
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
    "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    df["_date_str"] = dt.dt.strftime("%Y-%m-%d")
    time_str = _parse_time(df["datetime"])

    # ATR
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    dates_arr = df["_date"].values
    date_str_arr = df["_date_str"].values
    time_arr = time_str.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    trailing_stop = 0.0
    current_date = None
    traded_today = False

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        date_s = date_str_arr[i]

        # New day
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            traded_today = False

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # Exit at 13:45 on FOMC day (before 14:00 announcement)
        if position != 0 and bar_time >= EXIT_TIME:
            exit_sigs[i] = 1
            position = 0
            continue

        # Stop check
        if position == 1 and low_arr[i] <= trailing_stop:
            exit_sigs[i] = 1
            position = 0
            continue

        # Entry: long at 09:35 on FOMC announcement day
        if (position == 0
            and not traded_today
            and bar_time == ENTRY_TIME
            and date_s in FOMC_DATES):

            signals_arr[i] = 1
            entry_price = close_arr[i]
            trailing_stop = entry_price - bar_atr * ATR_STOP_MULT
            stop_arr[i] = trailing_stop
            target_arr[i] = entry_price + bar_atr * ATR_TARGET_MULT
            position = 1
            traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date", "_date_str"], inplace=True, errors="ignore")
    return df
