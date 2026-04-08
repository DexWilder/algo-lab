"""Standardized Macro Event Box Breakout.

Source: Harvest note 2026-03-25_05_standardized_macro_event_box.md
Factor: EVENT
Archetype: TAIL ENGINE (event-driven, ~30-40 events/year)

Logic:
  1. For scheduled macro releases (FOMC / CPI / NFP / PPI):
     - Event release time: 08:30 ET (CPI/NFP/PPI) or 14:00 ET (FOMC)
     - Build a "box" over 30 minutes starting at release: [0, 30] minutes
     - Record box high, box low, box midpoint, box height
  2. After box completes (T+30 min), wait for a close beyond box high/low
  3. Entry: first 5m close > box_high (long) or < box_low (short)
  4. Target: measured move = box_height
  5. Exit: target hit, or close back through breach level, or 15:55 ET cutoff

Event calendar (approximated from known release patterns):
  - NFP: First Friday of each month at 08:30 ET
  - CPI: Mid-month (10-14) release day at 08:30 ET — approximated
  - FOMC: 8 meetings/year, 2nd day at 14:00 ET — hard to predict from rules,
    so we use a hardcoded list of FOMC dates
  - PPI: Day after CPI at 08:30 ET — approximated

This is an approximation — real event calendars would be scraped from
a source. For calibration purposes we use heuristic date detection.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np
import datetime as dt

# Event detection heuristics (US ET times)
NFP_RELEASE_HHMM = 830
CPI_RELEASE_HHMM = 830
FOMC_RELEASE_HHMM = 1400
BOX_MINUTES = 30          # box duration after release
BOX_BARS = 6              # 6 × 5m = 30 min
EXIT_HHMM = 1555          # force flatten at 15:55 ET

TICK_SIZE = 0.25


# Hardcoded FOMC dates 2019-2026 (Day 2 of each meeting, at 14:00 ET)
# Source: Fed meeting schedule (publicly known)
FOMC_DATES = {
    dt.date(2019, 7, 31), dt.date(2019, 9, 18), dt.date(2019, 10, 30), dt.date(2019, 12, 11),
    dt.date(2020, 1, 29), dt.date(2020, 3, 15), dt.date(2020, 4, 29), dt.date(2020, 6, 10),
    dt.date(2020, 7, 29), dt.date(2020, 9, 16), dt.date(2020, 11, 5), dt.date(2020, 12, 16),
    dt.date(2021, 1, 27), dt.date(2021, 3, 17), dt.date(2021, 4, 28), dt.date(2021, 6, 16),
    dt.date(2021, 7, 28), dt.date(2021, 9, 22), dt.date(2021, 11, 3), dt.date(2021, 12, 15),
    dt.date(2022, 1, 26), dt.date(2022, 3, 16), dt.date(2022, 5, 4), dt.date(2022, 6, 15),
    dt.date(2022, 7, 27), dt.date(2022, 9, 21), dt.date(2022, 11, 2), dt.date(2022, 12, 14),
    dt.date(2023, 2, 1), dt.date(2023, 3, 22), dt.date(2023, 5, 3), dt.date(2023, 6, 14),
    dt.date(2023, 7, 26), dt.date(2023, 9, 20), dt.date(2023, 11, 1), dt.date(2023, 12, 13),
    dt.date(2024, 1, 31), dt.date(2024, 3, 20), dt.date(2024, 5, 1), dt.date(2024, 6, 12),
    dt.date(2024, 7, 31), dt.date(2024, 9, 18), dt.date(2024, 11, 7), dt.date(2024, 12, 18),
    dt.date(2025, 1, 29), dt.date(2025, 3, 19), dt.date(2025, 5, 7), dt.date(2025, 6, 18),
    dt.date(2025, 7, 30), dt.date(2025, 9, 17), dt.date(2025, 10, 29), dt.date(2025, 12, 10),
    dt.date(2026, 1, 28), dt.date(2026, 3, 18),
}


def _is_first_friday(date):
    """NFP = first Friday of month."""
    if date.weekday() != 4:  # 4 = Friday
        return False
    return date.day <= 7


def _is_cpi_day(date):
    """CPI is ~10th-14th business day at 08:30. Approximation: Wed/Thu around day 10-14."""
    if date.weekday() not in (2, 3):  # Wed/Thu
        return False
    return 10 <= date.day <= 14


def _event_info(trade_date):
    """Return (event_type, release_hhmm) or None if no event today."""
    if trade_date in FOMC_DATES:
        return "FOMC", FOMC_RELEASE_HHMM
    if _is_first_friday(trade_date):
        return "NFP", NFP_RELEASE_HHMM
    if _is_cpi_day(trade_date):
        return "CPI", CPI_RELEASE_HHMM
    return None


def EVENT_CLASSIFIER(trade_date):
    """Classifier used by batch_first_pass auto-decomposition.

    Returns an event type string for a given trade date, or None if the date
    is not a known event day. Picked up automatically by batch_first_pass
    when a composite event strategy is being tested.
    """
    info = _event_info(trade_date)
    return info[0] if info else None


def generate_signals(df):
    df = df.copy()
    dt_col = pd.to_datetime(df["datetime"])
    df["date"] = dt_col.dt.date
    df["hhmm"] = dt_col.dt.hour * 100 + dt_col.dt.minute
    n = len(df)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hhmm = df["hhmm"].values
    date = df["date"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # Per-event state
    current_event_date = None
    release_hhmm = None
    box_high = -np.inf
    box_low = np.inf
    box_start_hhmm = None
    box_complete = False
    traded = False

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    breach_level = 0.0

    for i in range(n):
        t = hhmm[i]
        d = date[i]

        # Detect event day
        if d != current_event_date:
            current_event_date = d
            event = _event_info(d)
            if event is None:
                release_hhmm = None
            else:
                _, release_hhmm = event
            box_high = -np.inf
            box_low = np.inf
            box_start_hhmm = release_hhmm
            box_complete = False
            traded = False
            if position != 0:
                exit_sigs[i] = position
                position = 0

        if release_hhmm is None:
            continue

        # Build box in the 30 minutes AT/after release
        if not box_complete and t >= release_hhmm and t < release_hhmm + 30:
            box_high = max(box_high, high[i])
            box_low = min(box_low, low[i])
            continue

        # Box complete after release+30min
        if not box_complete and t >= release_hhmm + 30:
            box_complete = True
            # Reject degenerate boxes
            if box_high <= -np.inf or box_low >= np.inf or box_high <= box_low:
                box_complete = False
                release_hhmm = None  # skip today

        # Manage position
        if position != 0:
            if position == 1:
                if low[i] <= stop_price:
                    exit_sigs[i] = 1
                    position = 0
                    continue
                if high[i] >= target_price:
                    exit_sigs[i] = 1
                    position = 0
                    continue
                # Close back through breach level
                if close[i] < breach_level:
                    exit_sigs[i] = 1
                    position = 0
                    continue
            elif position == -1:
                if high[i] >= stop_price:
                    exit_sigs[i] = -1
                    position = 0
                    continue
                if low[i] <= target_price:
                    exit_sigs[i] = -1
                    position = 0
                    continue
                if close[i] > breach_level:
                    exit_sigs[i] = -1
                    position = 0
                    continue

            # Force flatten
            if t >= EXIT_HHMM:
                exit_sigs[i] = position
                position = 0
                continue

        # Entry: box complete, not yet traded today
        if (position == 0 and box_complete and not traded
                and t >= release_hhmm + 30 and t < EXIT_HHMM):
            box_height = box_high - box_low
            if box_height <= 0:
                continue

            # Long: close above box_high
            if close[i] > box_high:
                position = 1
                entry_price = close[i]
                breach_level = box_high
                stop_price = box_low
                target_price = entry_price + box_height
                signals[i] = 1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                traded = True
            elif close[i] < box_low:
                position = -1
                entry_price = close[i]
                breach_level = box_low
                stop_price = box_high
                target_price = entry_price - box_height
                signals[i] = -1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                traded = True

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date", "hhmm"], inplace=True)
    return df
