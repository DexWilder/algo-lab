"""BB-COMPRESSION-GOLD — Bollinger Compression Fake-Breakout Reversion for Gold.

Gold-specific: exploits gold's tendency to fake breakouts then revert.
After a BB squeeze (low bandwidth), the first expansion often overshoots
then snaps back. This system fades the initial expansion move.

Logic:
- Detect: BB squeeze (bandwidth below rolling percentile)
- Wait: for squeeze release + initial expansion (1-3 bars outside band)
- Entry: price starts reversing back inside the bands (failed breakout)
  - Long: price was below lower band, now closing back above it
  - Short: price was above upper band, now closing back below it
- Exit: BB midline (SMA20) or ATR trailing stop
- Stop: ATR-based beyond the extreme of the fake breakout

Expected behavior:
- Win rate 50-60% (compression fakes are common on gold)
- Median hold 5-20 bars (quick snapback)
- Works best in LOW_VOL → NORMAL transitions (squeeze release)

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

BB_LENGTH = 20
BB_MULT = 2.0
ATR_PERIOD = 14
ATR_STOP_MULT = 1.5
ATR_TRAIL_MULT = 2.0
BW_LOOKBACK = 100         # Bandwidth percentile lookback
BW_SQUEEZE_PCT = 30       # Below 30th percentile = squeeze
BARS_OUTSIDE_MAX = 5      # Max bars outside band before entry (fake must happen quickly)
MIN_HOLD_BARS = 2

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "09:45"
ENTRY_CUTOFF = "14:45"
FLATTEN_TIME = "15:30"

TICK_SIZE = 0.10


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # Bollinger Bands
    sma = df["close"].rolling(window=BB_LENGTH, min_periods=BB_LENGTH).mean()
    std = df["close"].rolling(window=BB_LENGTH, min_periods=BB_LENGTH).std(ddof=0)
    upper_bb = sma + BB_MULT * std
    lower_bb = sma - BB_MULT * std

    # Bandwidth + squeeze detection
    bandwidth = ((upper_bb - lower_bb) / sma).values
    bw_series = pd.Series(bandwidth)
    bw_pctrank = bw_series.rolling(
        window=BW_LOOKBACK, min_periods=20
    ).apply(lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False).values

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
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values
    sma_arr = sma.values
    upper_arr = upper_bb.values
    lower_arr = lower_bb.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    trailing_stop = 0.0
    target_price = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    bars_in_trade = 0

    # Track squeeze state
    was_in_squeeze = False
    bars_below_lower = 0
    bars_above_upper = 0
    low_extreme = 0.0    # Lowest low during below-band excursion
    high_extreme = 0.0   # Highest high during above-band excursion

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]

        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False
            was_in_squeeze = False
            bars_below_lower = 0
            bars_above_upper = 0

        if not in_session_arr[i]:
            continue

        if (np.isnan(bar_atr) or np.isnan(sma_arr[i]) or
                np.isnan(upper_arr[i]) or np.isnan(lower_arr[i])):
            continue

        # Track squeeze state
        if not np.isnan(bw_pctrank[i]) and bw_pctrank[i] <= BW_SQUEEZE_PCT:
            was_in_squeeze = True

        # Track bars outside bands (post-squeeze expansion)
        if was_in_squeeze:
            if close_arr[i] < lower_arr[i]:
                bars_below_lower += 1
                bars_above_upper = 0
                if bars_below_lower == 1:
                    low_extreme = low_arr[i]
                else:
                    low_extreme = min(low_extreme, low_arr[i])
            elif close_arr[i] > upper_arr[i]:
                bars_above_upper += 1
                bars_below_lower = 0
                if bars_above_upper == 1:
                    high_extreme = high_arr[i]
                else:
                    high_extreme = max(high_extreme, high_arr[i])
            else:
                # Price back inside bands — check for entry
                if bars_below_lower > 0 and bars_below_lower <= BARS_OUTSIDE_MAX:
                    # Failed breakdown → long entry
                    if (not long_traded_today and entry_ok_arr[i]
                            and position == 0 and close_arr[i] > lower_arr[i]):
                        stop_level = low_extreme - bar_atr * ATR_STOP_MULT
                        signals_arr[i] = 1
                        stop_arr[i] = stop_level
                        target_arr[i] = sma_arr[i]
                        position = 1
                        trailing_stop = stop_level
                        target_price = sma_arr[i]
                        highest_since_entry = high_arr[i]
                        long_traded_today = True
                        bars_in_trade = 0

                elif bars_above_upper > 0 and bars_above_upper <= BARS_OUTSIDE_MAX:
                    # Failed breakout → short entry
                    if (not short_traded_today and entry_ok_arr[i]
                            and position == 0 and close_arr[i] < upper_arr[i]):
                        stop_level = high_extreme + bar_atr * ATR_STOP_MULT
                        signals_arr[i] = -1
                        stop_arr[i] = stop_level
                        target_arr[i] = sma_arr[i]
                        position = -1
                        trailing_stop = stop_level
                        target_price = sma_arr[i]
                        lowest_since_entry = low_arr[i]
                        short_traded_today = True
                        bars_in_trade = 0

                # Reset counters
                bars_below_lower = 0
                bars_above_upper = 0
                was_in_squeeze = False

        # Pre-close flatten
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Exits
        if position == 1:
            bars_in_trade += 1
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            if bars_in_trade >= MIN_HOLD_BARS and high_arr[i] >= sma_arr[i]:
                exit_sigs[i] = 1
                position = 0
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            bars_in_trade += 1
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]
                new_trail = lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            if bars_in_trade >= MIN_HOLD_BARS and low_arr[i] <= sma_arr[i]:
                exit_sigs[i] = -1
                position = 0
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
