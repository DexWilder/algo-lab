"""CLOSE-MOMENTUM-IGNITION — Tail Engine for 15:00-16:00 ET Session Gap.

Low-frequency, large-winner strategy capturing close-session momentum bursts
triggered by range compression followed by volume-driven breakouts in the
final hour of trading.

Logic:
- Entry window: 15:00-15:45 ET only (close-session momentum window)
- Range compression: 10-bar range < 0.7x ATR(20) (market has been quiet)
- Volume surge: bar volume > 2.0x 20-bar average (institutional participation)
- Breakout: close above 10-bar high (long) or below 10-bar low (short)
- Momentum confirmation: close in top 25% of bar range (long) / bottom 25% (short)
- Stop: opposite side of 10-bar range (natural support/resistance)
- Target: 3.0x ATR(14) from entry (tail capture)
- Time exit: force close at 15:55 ET if target/stop not hit
- Cooldown: 10 bars between trades
- Max 1 trade per close session

Expected behavior:
- Win rate 25-35% (wide stops, strict filters)
- Large average winner vs small average loser (3R+ target)
- Very low frequency: 0-1 trades per day
- Best in late-session momentum regimes

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ----------------------------------------------------------------

# Entry window (ET)
ENTRY_START = "15:00"         # Earliest entry time
ENTRY_CUTOFF = "15:45"        # No new entries after this
FLATTEN_TIME = "15:55"        # Force close any open position

# Range compression
RANGE_LOOKBACK = 10           # Bars for range calculation (highest high - lowest low)
ATR_COMPRESSION_PERIOD = 20   # ATR period for compression comparison
COMPRESSION_MULT = 0.7        # Range must be < this multiple of ATR(20)

# Volume surge
VOL_AVG_PERIOD = 20           # Lookback for average volume
VOL_SURGE_MULT = 2.0          # Current bar volume must exceed this multiple of avg

# Breakout confirmation
BREAKOUT_LOOKBACK = 10        # Bars for high/low breakout detection
CLOSE_STRENGTH_PCT = 0.25     # Close must be in top/bottom 25% of bar range

# Risk / reward
ATR_PERIOD = 14               # ATR lookback for target calculation
ATR_TARGET_MULT = 3.0         # Target = 3.0x ATR(14) from entry

# Cooldown
COOLDOWN_BARS = 10            # Minimum bars between trades

TICK_SIZE = 0.25              # Patched per asset by runner


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    """Extract HH:MM string from datetime column."""
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate close-session momentum ignition signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Session boundaries ----------------------------------------------------
    entry_ok = (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # -- ATR (for target) ------------------------------------------------------
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr_target = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # -- ATR (for compression reference) ---------------------------------------
    atr_compression = tr.ewm(span=ATR_COMPRESSION_PERIOD, adjust=False).mean().values

    # -- Volume average --------------------------------------------------------
    vol_series = df["volume"] if "volume" in df.columns else pd.Series(np.ones(n))
    vol_avg = vol_series.rolling(VOL_AVG_PERIOD, min_periods=VOL_AVG_PERIOD).mean().values
    vol_arr = vol_series.values

    # -- Rolling high/low for breakout and range -------------------------------
    rolling_high = df["high"].rolling(RANGE_LOOKBACK, min_periods=RANGE_LOOKBACK).max().values
    rolling_low = df["low"].rolling(RANGE_LOOKBACK, min_periods=RANGE_LOOKBACK).min().values

    # Shift by 1 so we compare current bar close against PREVIOUS 10-bar high/low
    # (the breakout must be the current bar closing beyond the prior range)
    prev_rolling_high = np.full(n, np.nan)
    prev_rolling_low = np.full(n, np.nan)
    prev_rolling_high[1:] = rolling_high[:-1]
    prev_rolling_low[1:] = rolling_low[:-1]

    # Range for compression: use the shifted (prior) rolling values
    range_10 = prev_rolling_high - prev_rolling_low

    # -- Pre-compute arrays ----------------------------------------------------
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    entry_ok_arr = entry_ok.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful loop ---------------------------------------------------------
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    current_date = None
    cooldown_remaining = 0
    traded_this_session = False

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            cooldown_remaining = 0
            traded_this_session = False

        # Decrement cooldown
        if cooldown_remaining > 0:
            cooldown_remaining -= 1

        # Skip bars with insufficient data
        if (np.isnan(atr_target[i]) or np.isnan(atr_compression[i])
                or np.isnan(prev_rolling_high[i]) or np.isnan(prev_rolling_low[i])
                or np.isnan(range_10[i])):
            continue

        # -- Time exit at 15:55 ------------------------------------------------
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # -- Manage open position (stop/target) --------------------------------
        if position == 1:
            # Check stop hit
            if low_arr[i] <= stop_price:
                exit_sigs[i] = 1
                position = 0
                cooldown_remaining = COOLDOWN_BARS
            # Check target hit
            elif high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0
                cooldown_remaining = COOLDOWN_BARS

        elif position == -1:
            # Check stop hit
            if high_arr[i] >= stop_price:
                exit_sigs[i] = -1
                position = 0
                cooldown_remaining = COOLDOWN_BARS
            # Check target hit
            elif low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
                cooldown_remaining = COOLDOWN_BARS

        # -- Entry logic -------------------------------------------------------
        if (position == 0
                and entry_ok_arr[i]
                and cooldown_remaining == 0
                and not traded_this_session):

            # Volume surge check
            if np.isnan(vol_avg[i]) or vol_avg[i] <= 0:
                continue
            volume_surge = vol_arr[i] > vol_avg[i] * VOL_SURGE_MULT

            if not volume_surge:
                continue

            # Range compression check: 10-bar range < 0.7x ATR(20)
            compressed = range_10[i] < atr_compression[i] * COMPRESSION_MULT

            if not compressed:
                continue

            # Bar range for close-strength check
            bar_range = high_arr[i] - low_arr[i]
            if bar_range <= 0:
                continue

            close_position_in_bar = (close_arr[i] - low_arr[i]) / bar_range

            # -- Long entry: close above prior 10-bar high --------------------
            if close_arr[i] > prev_rolling_high[i]:
                # Momentum: close in top 25% of bar range
                if close_position_in_bar >= (1.0 - CLOSE_STRENGTH_PCT):
                    stop = prev_rolling_low[i]
                    target = close_arr[i] + atr_target[i] * ATR_TARGET_MULT

                    signals_arr[i] = 1
                    stop_arr[i] = stop
                    target_arr[i] = target
                    position = 1
                    entry_price = close_arr[i]
                    stop_price = stop
                    target_price = target
                    traded_this_session = True
                    cooldown_remaining = 0

            # -- Short entry: close below prior 10-bar low --------------------
            elif close_arr[i] < prev_rolling_low[i]:
                # Momentum: close in bottom 25% of bar range
                if close_position_in_bar <= CLOSE_STRENGTH_PCT:
                    stop = prev_rolling_high[i]
                    target = close_arr[i] - atr_target[i] * ATR_TARGET_MULT

                    signals_arr[i] = -1
                    stop_arr[i] = stop
                    target_arr[i] = target
                    position = -1
                    entry_price = close_arr[i]
                    stop_price = stop
                    target_price = target
                    traded_this_session = True
                    cooldown_remaining = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
