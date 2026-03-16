"""DualThrust Daily -- Classic CTA range-based breakout system.

Computes a dynamic range from the previous N days' OHLC, then trades
breakouts of that range on the current day. Widely used by professional
commodity trading advisors since the 1990s (attributed to Michael Chalek).

Unlike fixed-channel breakouts (Donchian), DualThrust adapts its trigger
levels daily based on recent price action.

Logic:
  - Range = max(HH - LC, HC - LL) over last N days
  - Buy trigger = today's open + K1 * Range
  - Sell trigger = today's open - K2 * Range
  - Long if close > buy trigger; Short if close < sell trigger
  - Exit: ATR trailing stop or range flip (close crosses opposite trigger)

Operates on resampled daily OHLCV from 5-minute data.
Designed for multi-asset portability across liquid futures.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

N_DAYS = 4              # Lookback for range calculation
K1 = 0.5               # Buy trigger multiplier
K2 = 0.5               # Sell trigger multiplier
ATR_LEN = 20
TRAIL_ATR_MULT = 2.0
MIN_BARS_BETWEEN = 1   # 1 day cooldown (daily bars)

TICK_SIZE = 0.25        # Default MES, patched per asset


# ---- Helpers ----

def _resample_daily(df):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    daily = df.groupby("date").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).reset_index()
    daily["datetime"] = pd.to_datetime(daily["date"])
    return daily


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
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Detect if intraday -> resample
    if len(df) > 0:
        time_diff = df["datetime"].diff().median()
        if time_diff < pd.Timedelta(hours=1):
            daily = _resample_daily(df)
        else:
            daily = df.copy()
    else:
        return df

    n = len(daily)
    if n < N_DAYS + ATR_LEN + 5:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Compute indicators
    daily["atr"] = _atr(daily["high"], daily["low"], daily["close"], ATR_LEN)

    # Rolling range metrics over N_DAYS
    daily["hh"] = daily["high"].rolling(N_DAYS).max().shift(1)
    daily["hc"] = daily["close"].rolling(N_DAYS).max().shift(1)
    daily["lc"] = daily["close"].rolling(N_DAYS).min().shift(1)
    daily["ll"] = daily["low"].rolling(N_DAYS).min().shift(1)

    # DualThrust range
    daily["range1"] = daily["hh"] - daily["lc"]
    daily["range2"] = daily["hc"] - daily["ll"]
    daily["dt_range"] = daily[["range1", "range2"]].max(axis=1)

    # Triggers (based on current day's open)
    daily["buy_trigger"] = daily["open"] + K1 * daily["dt_range"]
    daily["sell_trigger"] = daily["open"] - K2 * daily["dt_range"]

    close = daily["close"].values
    high = daily["high"].values
    low = daily["low"].values
    open_ = daily["open"].values
    atr = daily["atr"].values
    buy_trig = daily["buy_trigger"].values
    sell_trig = daily["sell_trigger"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    best_price = 0.0
    bars_since_trade = MIN_BARS_BETWEEN

    for i in range(n):
        c = close[i]
        h = high[i]
        l = low[i]
        bar_atr = atr[i]
        bt = buy_trig[i]
        st = sell_trig[i]

        if np.isnan(bar_atr) or np.isnan(bt) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Manage position ----
        if position == 1:
            if c > best_price:
                best_price = c
            new_trail = best_price - bar_atr * TRAIL_ATR_MULT
            if new_trail > trailing_stop:
                trailing_stop = new_trail

            # Trailing stop
            if l <= trailing_stop:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue
            # Range flip: close crosses sell trigger -> exit and potentially reverse
            if c < st:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                # Don't continue — allow short entry below

        elif position == -1:
            if c < best_price:
                best_price = c
            new_trail = best_price + bar_atr * TRAIL_ATR_MULT
            if new_trail < trailing_stop:
                trailing_stop = new_trail

            if h >= trailing_stop:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0
                continue
            if c > bt:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0

        # ---- Entry ----
        if position == 0:
            bars_since_trade += 1
            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            # Long breakout
            if allow_long and c > bt:
                entry_price = c
                trailing_stop = c - bar_atr * TRAIL_ATR_MULT
                best_price = c
                signals[i] = 1
                stop_arr[i] = trailing_stop
                position = 1
                bars_since_trade = 0
                continue

            # Short breakout
            if allow_short and c < st:
                entry_price = c
                trailing_stop = c + bar_atr * TRAIL_ATR_MULT
                best_price = c
                signals[i] = -1
                stop_arr[i] = trailing_stop
                position = -1
                bars_since_trade = 0
                continue

    daily["signal"] = signals
    daily["exit_signal"] = exit_sigs
    daily["stop_price"] = stop_arr
    daily["target_price"] = target_arr

    drop_cols = ["atr", "hh", "hc", "lc", "ll", "range1", "range2",
                 "dt_range", "buy_trigger", "sell_trigger"]
    daily.drop(columns=[c for c in drop_cols if c in daily.columns], inplace=True, errors="ignore")
    return daily
