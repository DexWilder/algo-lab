"""CL VWAP Bounce — Morning VWAP pullback bounce on MCL (micro crude oil).

Source: Anthony Crudele — morning VWAP pullback concept.
Family: VWAP
Side: Long-only

Logic: After bullish session open (price above VWAP), wait for pullback
to VWAP bounce zone (within 0.5 ATR), enter long when bar closes back
above VWAP. Morning window only (09:45-12:00 ET). One trade per day max.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ----------------------------------------------------------------

ATR_PERIOD = 14
BOUNCE_ZONE_MULT = 0.5       # Pullback within 0.5 ATR of VWAP
STOP_ATR_MULT = 1.5          # Stop = VWAP - 1.5 ATR
TARGET_ATR_MULT = 2.5        # Target = entry + 2.5 ATR
TRAIL_TRIGGER_MULT = 1.5     # Trail activates at 1.5 ATR profit
TICK_SIZE = 0.01              # MCL tick size

ENTRY_START = "09:45"
ENTRY_END = "12:00"
FLATTEN_TIME = "14:00"


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_session_vwap(df):
    dt = pd.to_datetime(df["datetime"])
    dates = dt.dt.date.values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))
    tp = (high + low + close) / 3.0
    n = len(df)
    vwap = np.full(n, np.nan)
    cum_tp_vol = 0.0
    cum_vol = 0.0
    current_date = None
    for i in range(n):
        if dates[i] != current_date:
            current_date = dates[i]
            cum_tp_vol = 0.0
            cum_vol = 0.0
        vol = max(volume[i], 1.0)
        cum_tp_vol += tp[i] * vol
        cum_vol += vol
        vwap[i] = cum_tp_vol / cum_vol
    return vwap


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate CL VWAP bounce signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # Session VWAP
    vwap = _compute_session_vwap(df)

    # ATR
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # ATR median filter (rolling 50-bar median)
    atr_series = pd.Series(atr)
    atr_median = atr_series.rolling(window=50, min_periods=20).median().values

    # Extract arrays for bar-by-bar loop
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    current_stop = 0.0
    current_target = 0.0
    current_date = None
    traded_today = False
    session_bullish = False       # Price above VWAP early in session

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_vwap = vwap[i]

        # -- New day reset --
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1
                position = 0
            current_date = bar_date
            traded_today = False
            session_bullish = False

        if np.isnan(bar_atr) or np.isnan(bar_vwap) or bar_atr == 0:
            continue

        # Determine session bias: once price is above VWAP in entry window,
        # set bullish for the day
        if not session_bullish and bar_time >= ENTRY_START and bar_time < ENTRY_END:
            if close_arr[i] > bar_vwap:
                session_bullish = True

        # -- EOD flatten at 14:00 ET --
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1
            position = 0
            continue

        # -- Manage open position --
        if position == 1:
            # Trail: if price moved 1.5*ATR in profit, trail stop to VWAP
            if close_arr[i] - entry_price >= TRAIL_TRIGGER_MULT * bar_atr:
                trail_stop = bar_vwap
                if trail_stop > current_stop:
                    current_stop = trail_stop

            # Check stop
            if low_arr[i] <= current_stop:
                exit_sigs[i] = 1
                position = 0
                continue

            # Check target
            if high_arr[i] >= current_target:
                exit_sigs[i] = 1
                position = 0
                continue

        # -- Entry conditions (long only) --
        if position == 0 and not traded_today and bar_time >= ENTRY_START and bar_time < ENTRY_END:
            if np.isnan(atr_median[i]):
                continue

            # ATR volatility filter: only trade when ATR > rolling median
            if bar_atr <= atr_median[i]:
                continue

            # Session must have shown bullish bias
            if not session_bullish:
                continue

            # Pullback: previous bar was below or near VWAP
            prev_near_vwap = close_arr[i - 1] <= bar_vwap + BOUNCE_ZONE_MULT * bar_atr

            # Bounce zone: price pulled back to within 0.5 ATR of VWAP from above
            pullback_to_zone = abs(low_arr[i] - bar_vwap) <= BOUNCE_ZONE_MULT * bar_atr

            # Bounce confirmed: current bar closes back above VWAP
            closes_above = close_arr[i] > bar_vwap

            if prev_near_vwap and pullback_to_zone and closes_above:
                entry_price = close_arr[i]
                current_stop = bar_vwap - STOP_ATR_MULT * bar_atr
                current_target = entry_price + TARGET_ATR_MULT * bar_atr

                signals_arr[i] = 1
                stop_arr[i] = current_stop
                target_arr[i] = current_target
                position = 1
                traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
