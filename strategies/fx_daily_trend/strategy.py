"""FX Daily-Bar Trend Following -- Multi-horizon expansion strategy.

FX markets trend well on daily timeframes, driven by macro fundamentals
(interest rate differentials, trade flows, risk appetite). This is a
well-documented academic factor with decades of evidence.

This strategy opens FQL's multi-horizon research lane by operating on
daily bars rather than 5-minute bars. It uses simple, robust trend
structures designed to capture multi-day to multi-week moves.

Logic:
  - Direction: 50-day EMA slope determines trend direction
  - Confirmation: price above/below 20-day Donchian channel midline
  - Entry: Donchian breakout (new 20-day high for longs, new 20-day low for shorts)
  - Filter: ATR expansion filter (ATR > 0.8x of 50-day ATR average, avoids dead markets)
  - Stop: 2.0x ATR(20) trailing stop
  - Exit: trailing stop hit or trend reversal (price crosses 50-EMA against position)
  - No fixed target (let trends run)

Operates on resampled daily OHLCV from 5-minute data.

Designed for: 6E (Euro), 6J (Yen), 6B (Pound).

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Trend
EMA_TREND_LEN = 50           # Trend direction EMA (days)
DONCHIAN_LEN = 20            # Breakout channel length (days)

# ATR
ATR_LEN = 20                 # ATR period (days)
ATR_EXPANSION_FILTER = 0.8   # ATR must be > 0.8x of 50-day ATR mean (skip dead markets)
ATR_LOOKBACK = 50            # Lookback for ATR average

# Risk
TRAIL_ATR_MULT = 2.0         # Trailing stop distance = 2.0x ATR
TREND_EXIT_ENABLED = True    # Also exit if price crosses 50-EMA against position

# Cooldown
MIN_BARS_BETWEEN = 3         # 3 days between trades

TICK_SIZE = 0.00005           # Default 6E, patched per asset


# ---- Helpers ----

def _resample_daily(df):
    """Resample 5m bars to daily OHLCV."""
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
    """Generate daily-bar FX trend following signals.

    Accepts 5-minute data (resamples internally to daily) or daily data.
    """
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Detect if already daily or needs resampling
    if len(df) > 0:
        time_diff = df["datetime"].diff().median()
        if time_diff < pd.Timedelta(hours=1):
            # 5-minute or intraday data - resample to daily
            daily = _resample_daily(df)
        else:
            daily = df.copy()
    else:
        return df

    n = len(daily)
    if n < EMA_TREND_LEN + 10:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Compute indicators on daily bars
    daily["ema_trend"] = daily["close"].ewm(span=EMA_TREND_LEN, adjust=False).mean()
    daily["atr"] = _atr(daily["high"], daily["low"], daily["close"], ATR_LEN)
    daily["atr_avg"] = daily["atr"].rolling(ATR_LOOKBACK, min_periods=20).mean()
    daily["donch_high"] = daily["high"].rolling(DONCHIAN_LEN, min_periods=DONCHIAN_LEN).max()
    daily["donch_low"] = daily["low"].rolling(DONCHIAN_LEN, min_periods=DONCHIAN_LEN).min()
    daily["donch_mid"] = (daily["donch_high"] + daily["donch_low"]) / 2

    # Shift Donchian to avoid lookahead (use previous day's channel)
    daily["donch_high_prev"] = daily["donch_high"].shift(1)
    daily["donch_low_prev"] = daily["donch_low"].shift(1)
    daily["donch_mid_prev"] = daily["donch_mid"].shift(1)

    close = daily["close"].values
    high = daily["high"].values
    low = daily["low"].values
    ema = daily["ema_trend"].values
    atr = daily["atr"].values
    atr_avg = daily["atr_avg"].values
    donch_h = daily["donch_high_prev"].values
    donch_l = daily["donch_low_prev"].values

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
        bar_atr_avg = atr_avg[i]
        bar_ema = ema[i]
        bar_donch_h = donch_h[i]
        bar_donch_l = donch_l[i]

        if np.isnan(bar_atr) or np.isnan(bar_ema) or np.isnan(bar_donch_h) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Manage position ----
        if position == 1:
            if c > best_price:
                best_price = c
            new_trail = best_price - bar_atr * TRAIL_ATR_MULT
            if new_trail > trailing_stop:
                trailing_stop = new_trail

            # Trailing stop hit
            if l <= trailing_stop:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue
            # Trend reversal exit
            if TREND_EXIT_ENABLED and c < bar_ema:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue

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
            if TREND_EXIT_ENABLED and c > bar_ema:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0
                continue

        # ---- Entry (flat only) ----
        if position == 0:
            bars_since_trade += 1
            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            # ATR expansion filter
            if not np.isnan(bar_atr_avg) and bar_atr < bar_atr_avg * ATR_EXPANSION_FILTER:
                continue

            # Long: Donchian breakout + EMA trend up
            if allow_long and c > bar_donch_h and c > bar_ema:
                entry_price = c
                trailing_stop = c - bar_atr * TRAIL_ATR_MULT
                best_price = c
                signals[i] = 1
                stop_arr[i] = trailing_stop
                position = 1
                bars_since_trade = 0
                continue

            # Short: Donchian breakout + EMA trend down
            if allow_short and c < bar_donch_l and c < bar_ema:
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

    # Clean up
    drop_cols = ["ema_trend", "atr", "atr_avg", "donch_high", "donch_low",
                 "donch_mid", "donch_high_prev", "donch_low_prev", "donch_mid_prev"]
    daily.drop(columns=[c for c in drop_cols if c in daily.columns], inplace=True, errors="ignore")

    return daily
