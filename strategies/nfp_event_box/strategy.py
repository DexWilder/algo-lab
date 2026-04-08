"""NFP Event Box Breakout — salvaged from Macro Event Box.

Source: Salvage of strategies/macro_event_box/strategy.py after per-event
decomposition revealed that NFP alone had PF 1.22 while CPI (heuristic)
had PF 0.78 and FOMC had PF 0.89. Combining all three diluted the NFP edge.

Archetype: TAIL ENGINE (one instance per month = ~80 instances/6.7y)

Logic: same as Macro Event Box, but restricted to NFP releases only.
  1. NFP release: first Friday of each month at 08:30 ET
  2. Build 30-minute box from 08:30-09:00 ET (box high/low/mid)
  3. Entry: first 5m close > box_high (long) or < box_low (short) after box completes
  4. Target: measured move = box_height
  5. Exit: target, close back through breach, or 15:55 ET cutoff

Tested on MES, MNQ, MGC (equity and gold respond to NFP).

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

NFP_RELEASE_HHMM = 830
BOX_MINUTES = 30
EXIT_HHMM = 1555

TICK_SIZE = 0.25


def _is_first_friday(date):
    """NFP is always first Friday of the month."""
    if date.weekday() != 4:  # 4 = Friday
        return False
    return date.day <= 7


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
    is_nfp_day = False
    box_high = -np.inf
    box_low = np.inf
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

        if d != current_event_date:
            current_event_date = d
            is_nfp_day = _is_first_friday(d)
            box_high = -np.inf
            box_low = np.inf
            box_complete = False
            traded = False
            if position != 0:
                exit_sigs[i] = position
                position = 0

        if not is_nfp_day:
            continue

        # Build box during 08:30-09:00 ET
        if not box_complete and t >= NFP_RELEASE_HHMM and t < NFP_RELEASE_HHMM + BOX_MINUTES:
            box_high = max(box_high, high[i])
            box_low = min(box_low, low[i])
            continue

        # Box complete after release+30min
        if not box_complete and t >= NFP_RELEASE_HHMM + BOX_MINUTES:
            if box_high > -np.inf and box_low < np.inf and box_high > box_low:
                box_complete = True
            else:
                is_nfp_day = False  # skip today

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

            if t >= EXIT_HHMM:
                exit_sigs[i] = position
                position = 0
                continue

        # Entry
        if (position == 0 and box_complete and not traded
                and t >= NFP_RELEASE_HHMM + BOX_MINUTES and t < EXIT_HHMM):
            box_height = box_high - box_low
            if box_height <= 0:
                continue

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
