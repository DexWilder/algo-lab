"""Rate Intraday Mean Reversion -- Native strategy for Treasury futures.

Rates (ZN/ZB/ZF) are strongly mean-reverting intraday due to dealer inventory
management, hedging flows, and macro-anchored fair value. This strategy fades
extreme deviations from session VWAP during US trading hours.

Key differences from equity VWAP reversion:
  - 23-hour market: session VWAP resets at a defined anchor, not at 09:30 ET
  - Rates move in smaller, more persistent ranges than equities
  - Mean reversion is the dominant intraday behavior, not a secondary edge
  - Volume profile is spread across the day, not front-loaded

Session logic:
  - VWAP computed from US RTH start (08:20 ET for CBOT)
  - Entry window: 09:00-14:30 ET (after initial price discovery, before close)
  - Deviation threshold: price > VWAP + N*ATR (short) or < VWAP - N*ATR (long)
  - Exit: reversion to VWAP or time-based flatten
  - EOD flatten at 14:45 ET (before 15:00 close)

Designed for: ZN (10Y Note), ZB (30Y Bond), ZF (5Y Note) on 5-minute bars.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Session (CBOT Treasury hours, Eastern Time)
SESSION_START_HOUR = 8
SESSION_START_MIN = 20       # CBOT opens 08:20 ET
ENTRY_START_HOUR = 9         # Allow entries after initial price discovery
ENTRY_START_MIN = 0
ENTRY_END_HOUR = 14
ENTRY_END_MIN = 30
FLATTEN_HOUR = 14
FLATTEN_MIN = 45

# VWAP deviation
DEV_ENTRY_MULT = 1.8        # Enter when price deviates > 1.8x ATR from VWAP
DEV_EXIT_MULT = 0.3         # Exit when price reverts within 0.3x ATR of VWAP

# ATR
ATR_LEN = 20                # ATR period

# Risk
SL_ATR_MULT = 2.5           # Stop = 2.5 ATR beyond entry (wider for rates)
MAX_HOLD_BARS = 60           # Max hold = 5 hours on 5m bars (time stop)

# Filters
MIN_BARS_BETWEEN = 8        # 40 min cooldown
RSI_LEN = 14                # RSI for overextension confirmation
RSI_OVERBOUGHT = 70         # Short when RSI > 70 AND price > VWAP + dev
RSI_OVERSOLD = 30           # Long when RSI < 30 AND price < VWAP - dev

TICK_SIZE = 0.015625         # Default ZN, patched per asset


# ---- Helpers ----

def _atr(high, low, close, period):
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ---- Signal Generator ----

def generate_signals(df, asset=None, mode="both"):
    """Generate rate intraday mean reversion signals.

    Parameters
    ----------
    df : DataFrame with datetime, open, high, low, close, volume (5m bars)
    mode : "long", "short", or "both"
    """
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["date"] = df["datetime"].dt.date
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)
    df["rsi"] = _rsi(df["close"], RSI_LEN)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values
    hour = df["hour"].values
    minute = df["minute"].values
    dates = df["date"].values
    atr = df["atr"].values
    rsi = df["rsi"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    # Output
    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # Session VWAP state
    vwap_num = 0.0           # cumulative (typical_price * volume)
    vwap_den = 0.0           # cumulative volume
    vwap = np.nan
    current_date = None
    session_active = False

    # Position state
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
        bar_vol = volume[i]
        bar_atr = atr[i]
        bar_rsi = rsi[i]
        bar_date = dates[i]

        if np.isnan(bar_atr) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Session VWAP management ----
        time_val = h * 100 + m

        # New day or session start: reset VWAP
        if bar_date != current_date:
            current_date = bar_date
            vwap_num = 0.0
            vwap_den = 0.0
            session_active = False

        # Session active: accumulate VWAP from session start
        if time_val >= SESSION_START_HOUR * 100 + SESSION_START_MIN:
            session_active = True

        if session_active and bar_vol > 0:
            typical_price = (bar_high + bar_low + bar_close) / 3.0
            vwap_num += typical_price * bar_vol
            vwap_den += bar_vol
            vwap = vwap_num / vwap_den if vwap_den > 0 else bar_close

        # ---- Flatten at session end ----
        if time_val >= FLATTEN_HOUR * 100 + FLATTEN_MIN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
                bars_since_trade = 0
            continue

        # ---- Manage open position ----
        if position != 0:
            bars_held += 1

            # Time stop
            if bars_held >= MAX_HOLD_BARS:
                exit_sigs[i] = position
                position = 0
                bars_since_trade = 0
                continue

            # Stop loss
            if position == 1 and bar_low <= stop_price:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue
            elif position == -1 and bar_high >= stop_price:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0
                continue

            # Mean reversion exit: price returned near VWAP
            if not np.isnan(vwap):
                dev = abs(bar_close - vwap)
                if dev <= bar_atr * DEV_EXIT_MULT:
                    exit_sigs[i] = position
                    position = 0
                    bars_since_trade = 0
                    continue

        # ---- Entry logic (flat only, within entry window) ----
        if position == 0:
            bars_since_trade += 1

            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            # Must be in entry window
            if time_val < ENTRY_START_HOUR * 100 + ENTRY_START_MIN:
                continue
            if time_val >= ENTRY_END_HOUR * 100 + ENTRY_END_MIN:
                continue

            if np.isnan(vwap) or np.isnan(bar_rsi):
                continue

            deviation = bar_close - vwap

            # Short: price above VWAP + threshold AND overbought
            if allow_short and deviation > bar_atr * DEV_ENTRY_MULT and bar_rsi > RSI_OVERBOUGHT:
                entry_price = bar_close
                stop_price = bar_close + bar_atr * SL_ATR_MULT
                signals[i] = -1
                stop_arr[i] = stop_price
                target_arr[i] = vwap  # Target = reversion to VWAP
                position = -1
                bars_held = 0
                bars_since_trade = 0
                continue

            # Long: price below VWAP - threshold AND oversold
            if allow_long and deviation < -(bar_atr * DEV_ENTRY_MULT) and bar_rsi < RSI_OVERSOLD:
                entry_price = bar_close
                stop_price = bar_close - bar_atr * SL_ATR_MULT
                signals[i] = 1
                stop_arr[i] = stop_price
                target_arr[i] = vwap  # Target = reversion to VWAP
                position = 1
                bars_held = 0
                bars_since_trade = 0
                continue

    # Write output
    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "minute", "date", "atr", "rsi"], inplace=True)
    return df
