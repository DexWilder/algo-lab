"""London Pre-Open Currency Futures Breakout.

Source: Harvest note 2026-03-26_08_london_preopen_currency_futures_breakout.md
Factor: STRUCTURAL (session handoff)
Archetype: TAIL ENGINE (session-specific, ~1 trade/day max)

Logic:
  1. Pre-London window: 07:00-07:59 GMT = 02:00-02:55 ET (standard time)
     For simplicity we use 02:00-02:55 ET year-round (ignoring DST).
  2. Record pre-London window high and low.
  3. After 08:00 GMT (03:00 ET), enter long on break of upper or short on break of lower.
  4. Abnormal volatility gate: reject if opening bar range > 2x average of setup window bars
  5. Flatten by end of London hour (04:00 ET).

Notes:
  - DST not handled — using fixed 02:00-02:55 ET anchor
  - Tests on 6E, 6B, 6J (major FX majors where London matters)
  - Expected ~1 trade/day max, ~250 trades/year

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

SETUP_START_HHMM = 200   # 02:00 ET = 07:00 GMT
SETUP_END_HHMM = 255     # 02:55 ET = 07:55 GMT (exclusive at 03:00)
ENTRY_START_HHMM = 300   # 03:00 ET = 08:00 GMT
ENTRY_END_HHMM = 355     # stop taking entries
FLATTEN_HHMM = 400       # flatten all positions

ABNORMAL_VOL_MULT = 2.0   # opening bar range must be < 2x avg setup range
ATR_STOP_MULT = 0.5       # stop below/above breakout level
TARGET_RANGE_MULT = 1.5   # target = breakout ± (setup_range * 1.5)

TICK_SIZE = 0.00005  # 6E default


def _compute_features(df):
    df = df.copy()
    dt = pd.to_datetime(df["datetime"])
    df["date"] = dt.dt.date
    df["hhmm"] = dt.dt.hour * 100 + dt.dt.minute
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(span=14, adjust=False).mean()
    return df


def generate_signals(df):
    df = _compute_features(df)
    n = len(df)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    atr = df["atr"].values
    hhmm = df["hhmm"].values
    date = df["date"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # Session state
    setup_date = None
    setup_high = -np.inf
    setup_low = np.inf
    setup_bar_ranges = []
    setup_complete = False
    traded_today = False

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0

    for i in range(n):
        t = hhmm[i]
        d = date[i]
        a = atr[i]
        if np.isnan(a) or a == 0:
            continue

        # Reset per day (use the date of the setup window)
        if setup_date != d and SETUP_START_HHMM <= t < SETUP_END_HHMM + 5:
            setup_date = d
            setup_high = -np.inf
            setup_low = np.inf
            setup_bar_ranges = []
            setup_complete = False
            traded_today = False
            # Close stale position
            if position != 0:
                exit_sigs[i] = position
                position = 0

        # Accumulate setup window
        if setup_date == d and SETUP_START_HHMM <= t < ENTRY_START_HHMM:
            setup_high = max(setup_high, high[i])
            setup_low = min(setup_low, low[i])
            setup_bar_ranges.append(high[i] - low[i])
            continue  # no entries during setup window

        if setup_date == d and t >= ENTRY_START_HHMM and not setup_complete:
            if setup_high > -np.inf and setup_low < np.inf and len(setup_bar_ranges) > 0:
                setup_complete = True
            else:
                continue

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
            elif position == -1:
                if high[i] >= stop_price:
                    exit_sigs[i] = -1
                    position = 0
                    continue
                if low[i] <= target_price:
                    exit_sigs[i] = -1
                    position = 0
                    continue

            if t >= FLATTEN_HHMM:
                exit_sigs[i] = position
                position = 0
                continue

        # Entries: after 03:00, before 03:55, setup complete, not already traded
        if (position == 0 and setup_complete and not traded_today
                and setup_date == d
                and ENTRY_START_HHMM <= t < ENTRY_END_HHMM):
            # Abnormal-volatility gate: current bar range vs avg setup range
            avg_setup_range = np.mean(setup_bar_ranges) if setup_bar_ranges else 0
            bar_range = high[i] - low[i]
            if avg_setup_range > 0 and bar_range > ABNORMAL_VOL_MULT * avg_setup_range:
                continue  # reject abnormal vol

            setup_range = setup_high - setup_low
            if setup_range <= 0:
                continue

            # Long breakout
            if close[i] > setup_high:
                position = 1
                entry_price = close[i]
                stop_price = setup_low - ATR_STOP_MULT * a
                target_price = entry_price + setup_range * TARGET_RANGE_MULT
                signals[i] = 1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                traded_today = True
            elif close[i] < setup_low:
                position = -1
                entry_price = close[i]
                stop_price = setup_high + ATR_STOP_MULT * a
                target_price = entry_price - setup_range * TARGET_RANGE_MULT
                signals[i] = -1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
                traded_today = True

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date", "hhmm", "atr"], inplace=True)
    return df
