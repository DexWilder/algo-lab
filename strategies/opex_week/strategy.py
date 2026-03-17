"""OPEX Week Effect -- Equity long during monthly options expiration week.

Dealer gamma hedging around monthly options expiration creates a
positive drift in equity indices during OPEX week (third Friday).

Logic:
  - OPEX week: Monday through Friday of the week containing the third Friday
  - Entry: Monday RTH open (~09:35 ET)
  - Exit variant A: Thursday close (~15:55 ET, avoid pin risk)
  - Exit variant B: Friday close (~15:55 ET, full OPEX week)
  - Stop: toggle (none or 2.0x ATR)
  - 12 trades per year

Designed for: MES, MNQ on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta

# ---- Parameters ----

# Exit variant: "thursday" or "friday"
EXIT_VARIANT = "friday"

# Direction
DIRECTION = "long"

# Stop
USE_STOP = False
ATR_LEN = 20
SL_ATR_MULT = 2.0

# Session
ENTRY_HOUR = 9
ENTRY_MIN = 35
EXIT_HOUR = 15
EXIT_MIN = 55

TICK_SIZE = 0.25  # MES default


def _compute_opex_weeks(start_year=2019, end_year=2026):
    """Compute OPEX weeks: Monday-Friday of the week containing the third Friday."""
    opex_weeks = {}  # date_str -> {"monday": str, "thursday": str, "friday": str, "role": str}

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Find third Friday: first day of month, advance to first Friday, then +14 days
            first_day = date(year, month, 1)
            # Days until Friday (4 = Friday)
            days_to_friday = (4 - first_day.weekday()) % 7
            first_friday = first_day + timedelta(days=days_to_friday)
            third_friday = first_friday + timedelta(days=14)

            # OPEX week: Monday through Friday
            monday = third_friday - timedelta(days=4)  # Friday - 4 = Monday

            for d in range(5):  # Mon through Fri
                day = monday + timedelta(days=d)
                day_str = day.strftime("%Y-%m-%d")
                weekday_name = ["monday", "tuesday", "wednesday", "thursday", "friday"][d]
                opex_weeks[day_str] = {
                    "role": weekday_name,
                    "monday": monday.strftime("%Y-%m-%d"),
                    "friday": third_friday.strftime("%Y-%m-%d"),
                    "thursday": (third_friday - timedelta(days=1)).strftime("%Y-%m-%d"),
                }

    return opex_weeks


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
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date_str"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    direction = mode if mode else DIRECTION
    opex_weeks = _compute_opex_weeks()

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
    current_opex_monday = ""

    # Determine exit day based on variant
    exit_role = "thursday" if EXIT_VARIANT == "thursday" else "friday"

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

        opex_info = opex_weeks.get(bar_date)

        # ---- Exit logic ----
        if position != 0:
            should_exit = False

            # Stop
            if USE_STOP:
                if position == 1 and bar_low <= stop_price:
                    should_exit = True
                elif position == -1 and bar_high >= stop_price:
                    should_exit = True

            # Exit on target day at close
            if opex_info and opex_info["role"] == exit_role and time_val >= EXIT_HOUR * 100 + EXIT_MIN:
                if opex_info["monday"] == current_opex_monday:
                    should_exit = True

            # Safety: exit if we're past OPEX Friday (shouldn't happen but protect)
            if opex_info is None and position != 0 and bar_date > current_opex_monday:
                # Check if we've left the OPEX week
                should_exit = True

            if should_exit:
                exit_sigs[i] = position
                position = 0
                continue

        # ---- Entry logic ----
        if position == 0:
            if opex_info and opex_info["role"] == "monday" and time_val >= ENTRY_HOUR * 100 + ENTRY_MIN:
                # Only enter once per OPEX week
                if opex_info["monday"] != current_opex_monday:
                    current_opex_monday = opex_info["monday"]

                    if direction in ("long", "both"):
                        entry_price = bar_close
                        stop_price = bar_close - bar_atr * SL_ATR_MULT if USE_STOP else 0
                        signals[i] = 1
                        stop_arr[i] = stop_price if USE_STOP else np.nan
                        position = 1
                    elif direction == "short":
                        entry_price = bar_close
                        stop_price = bar_close + bar_atr * SL_ATR_MULT if USE_STOP else 0
                        signals[i] = -1
                        stop_arr[i] = stop_price if USE_STOP else np.nan
                        position = -1

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date_str", "hour", "minute", "atr"], inplace=True)
    return df
