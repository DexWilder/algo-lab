"""RSI(2) Oversold Bounce -- Mean reversion for M2K micro futures.

Russell 2000 micro futures overshoot on the downside intraday due to
thin liquidity. RSI(2) reaching extreme oversold levels in an uptrend
creates a high-probability mean-reversion long entry.

Documented edge: Connors & Alvarez "Short Term Trading Strategies That
Work" — RSI(2) < 10 on SPY shows 78%+ win rate historically.

Logic:
  - Entry: RSI(2) < threshold (default 10, also test 5)
  - Trend filter (toggle): price above 200-bar EMA (only buy dips in uptrends)
  - Dip confirmation: close below 20-bar EMA
  - Exit: close above 20-bar EMA (reverted to mean)
  - Stop: 2.0x ATR below entry
  - Time stop: 30 bars (2.5 hours)
  - Long only (short-side RSI(2) is weaker on equities)

Designed for: M2K (Micro Russell 2000) on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# RSI
RSI_LEN = 2
RSI_ENTRY_THRESH = 10       # Test both 10 and 5

# Trend filter (toggle)
TREND_FILTER = True          # Set False to test without 200 EMA filter
TREND_EMA_LEN = 200

# Pullback / exit EMA
PULLBACK_EMA_LEN = 20

# ATR
ATR_LEN = 20
SL_ATR_MULT = 2.0

# Time stop
MAX_HOLD_BARS = 30           # 2.5 hours on 5m

# Session
ENTRY_START_HOUR = 9
ENTRY_START_MIN = 45
ENTRY_END_HOUR = 14
ENTRY_END_MIN = 30
FLATTEN_HOUR = 15
FLATTEN_MIN = 0

# Cooldown
MIN_BARS_BETWEEN = 6

TICK_SIZE = 0.10  # M2K default


# ---- Helpers ----

def _rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


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
    """Generate RSI(2) oversold bounce signals. Long only by design."""
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["rsi"] = _rsi(df["close"], RSI_LEN)
    df["ema_trend"] = df["close"].ewm(span=TREND_EMA_LEN, adjust=False).mean()
    df["ema_pb"] = df["close"].ewm(span=PULLBACK_EMA_LEN, adjust=False).mean()
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    minute = df["minute"].values
    rsi = df["rsi"].values
    ema_trend = df["ema_trend"].values
    ema_pb = df["ema_pb"].values
    atr = df["atr"].values

    # This strategy is long-only by design
    # mode parameter is accepted for batch_first_pass compatibility
    # but short signals are never generated
    allow_long = mode in ("long", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    bars_held = 0
    bars_since_trade = MIN_BARS_BETWEEN

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_rsi = rsi[i]
        bar_ema_trend = ema_trend[i]
        bar_ema_pb = ema_pb[i]
        bar_atr = atr[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or np.isnan(bar_rsi) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Flatten at session end ----
        if time_val >= FLATTEN_HOUR * 100 + FLATTEN_MIN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
                bars_since_trade = 0
            continue

        # ---- Manage position ----
        if position == 1:
            bars_held += 1

            # Mean reversion exit: close above short-term EMA
            if bar_close > bar_ema_pb:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue

            # Stop loss
            if bar_low <= stop_price:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue

            # Time stop
            if bars_held >= MAX_HOLD_BARS:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue

        # ---- Entry (flat, long only) ----
        if position == 0 and allow_long:
            bars_since_trade += 1
            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            # Session window
            entry_start = ENTRY_START_HOUR * 100 + ENTRY_START_MIN
            entry_end = ENTRY_END_HOUR * 100 + ENTRY_END_MIN
            if time_val < entry_start or time_val >= entry_end:
                continue

            # RSI oversold
            if bar_rsi >= RSI_ENTRY_THRESH:
                continue

            # Trend filter (if enabled): price must be above 200 EMA
            if TREND_FILTER and not np.isnan(bar_ema_trend):
                if bar_close <= bar_ema_trend:
                    continue

            # Dip confirmation: close must be below 20 EMA
            if not np.isnan(bar_ema_pb):
                if bar_close >= bar_ema_pb:
                    continue

            # Entry
            entry_price = bar_close
            stop_price = bar_close - bar_atr * SL_ATR_MULT
            signals[i] = 1
            stop_arr[i] = stop_price
            target_arr[i] = bar_ema_pb  # Target = reversion to 20 EMA
            position = 1
            bars_held = 0
            bars_since_trade = 0

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "minute", "rsi", "ema_trend", "ema_pb", "atr"], inplace=True)
    return df
