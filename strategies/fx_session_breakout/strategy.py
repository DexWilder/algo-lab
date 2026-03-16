"""FX Session Breakout -- Native FX strategy for session-transition volatility.

FX markets have well-documented volatility clustering around major session
opens: London (03:00 ET), NY (08:00 ET), and the London/NY overlap
(08:00-12:00 ET). This strategy trades breakouts from pre-session
consolidation ranges at these transition points.

Unlike equity ORB which uses a fixed opening range after 09:30 ET, this
strategy adapts to the FX session structure:
  - Asian range (18:00-03:00 ET) defines the pre-London consolidation
  - London morning range (03:00-08:00 ET) defines pre-NY consolidation
  - Breakout = price exceeds range + ATR filter

Designed for: 6E (Euro), 6J (Yen), 6B (Pound) on 5-minute bars.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Session definitions (Eastern Time)
ASIAN_START = 18     # 18:00 ET (previous day)
ASIAN_END = 3        # 03:00 ET (London open)
LONDON_START = 3     # 03:00 ET
LONDON_END = 8       # 08:00 ET (NY open)
NY_START = 8         # 08:00 ET
OVERLAP_END = 12     # 12:00 ET (London close)
SESSION_CLOSE = 16   # 16:00 ET (flatten)

# Breakout parameters
ATR_LEN = 20                # ATR period for volatility normalization
BREAKOUT_ATR_FILTER = 0.3   # Range must be > 0.3x ATR (not too tight)
BREAKOUT_ATR_MAX = 3.0      # Range must be < 3.0x ATR (not already extended)

# Risk parameters
SL_ATR_MULT = 1.5           # Stop = 1.5 ATR beyond range boundary
TP_ATR_MULT = 2.5           # Target = 2.5 ATR from entry
TRAIL_ACTIVATION_R = 1.5    # Trail after 1.5R profit
TRAIL_ATR_MULT = 1.0        # Trail distance

# Filters
MIN_BARS_BETWEEN = 6        # Cooldown (30 min on 5m)
VOLUME_MULT = 1.2           # Volume must exceed 1.2x rolling average at breakout

# Which sessions to trade (can be configured per asset)
TRADE_LONDON_OPEN = True     # Trade breakout of Asian range at London open
TRADE_NY_OPEN = True         # Trade breakout of London range at NY open

TICK_SIZE = 0.00005          # Default for 6E, patched per asset


# ---- Helpers ----

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
    """Generate FX session breakout signals.

    Parameters
    ----------
    df : DataFrame with datetime, open, high, low, close, volume (5m bars)
    asset : Optional asset name (unused)
    mode : "long", "short", or "both"

    Returns
    -------
    DataFrame with signal, exit_signal, stop_price, target_price columns
    """
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["date"] = df["datetime"].dt.date
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    # Rolling volume average for volume filter
    df["vol_avg"] = df["volume"].rolling(50, min_periods=10).mean()

    # Pre-compute arrays
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    dates = df["date"].values
    atr = df["atr"].values
    volume = df["volume"].values
    vol_avg = df["vol_avg"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    # Output arrays
    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # Session range tracking
    asian_high = np.nan
    asian_low = np.nan
    london_high = np.nan
    london_low = np.nan
    current_date = None
    in_asian = False
    in_london = False
    asian_range_ready = False
    london_range_ready = False

    # Position state
    position = 0
    entry_price = 0.0
    entry_atr = 0.0
    stop_price = 0.0
    target_price = 0.0
    trail_active = False
    trailing_stop = 0.0
    best_price = 0.0
    bars_since_trade = MIN_BARS_BETWEEN

    for i in range(n):
        h = hour[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_close = close[i]
        bar_atr = atr[i]
        bar_vol = volume[i]
        bar_vol_avg = vol_avg[i]
        bar_date = dates[i]

        if np.isnan(bar_atr) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Session range accumulation ----

        # Asian session: 18:00 - 03:00 ET
        if h >= ASIAN_START or h < ASIAN_END:
            if not in_asian:
                asian_high = bar_high
                asian_low = bar_low
                in_asian = True
                asian_range_ready = False
            else:
                asian_high = max(asian_high, bar_high)
                asian_low = min(asian_low, bar_low)
        elif in_asian and h >= ASIAN_END:
            in_asian = False
            asian_range_ready = True

        # London morning: 03:00 - 08:00 ET
        if LONDON_START <= h < LONDON_END:
            if not in_london:
                london_high = bar_high
                london_low = bar_low
                in_london = True
                london_range_ready = False
            else:
                london_high = max(london_high, bar_high)
                london_low = min(london_low, bar_low)
        elif in_london and h >= LONDON_END:
            in_london = False
            london_range_ready = True

        # Reset at end of day
        if h >= SESSION_CLOSE:
            # Flatten any open position
            if position != 0:
                exit_sigs[i] = position
                position = 0
                bars_since_trade = 0
            continue

        # ---- Manage open position ----
        if position == 1:
            if bar_close > best_price:
                best_price = bar_close
            r_dist = entry_atr * SL_ATR_MULT
            if not trail_active and (best_price - entry_price) >= TRAIL_ACTIVATION_R * r_dist:
                trail_active = True
                trailing_stop = best_price - bar_atr * TRAIL_ATR_MULT
            if trail_active:
                new_trail = best_price - bar_atr * TRAIL_ATR_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail
            active_stop = trailing_stop if trail_active else stop_price
            if bar_low <= active_stop:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
            elif bar_high >= target_price:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0

        elif position == -1:
            if bar_close < best_price:
                best_price = bar_close
            r_dist = entry_atr * SL_ATR_MULT
            if not trail_active and (entry_price - best_price) >= TRAIL_ACTIVATION_R * r_dist:
                trail_active = True
                trailing_stop = best_price + bar_atr * TRAIL_ATR_MULT
            if trail_active:
                new_trail = best_price + bar_atr * TRAIL_ATR_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail
            active_stop = trailing_stop if trail_active else stop_price
            if bar_high >= active_stop:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0
            elif bar_low <= target_price:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0

        # ---- Entry logic (flat only) ----
        if position == 0:
            bars_since_trade += 1
            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            # Volume filter
            if bar_vol_avg > 0 and bar_vol < bar_vol_avg * VOLUME_MULT:
                continue

            # London open breakout (trade the Asian range break at 03:00-08:00)
            if TRADE_LONDON_OPEN and asian_range_ready and ASIAN_END <= h < LONDON_END:
                rng = asian_high - asian_low
                if rng > 0 and rng > bar_atr * BREAKOUT_ATR_FILTER and rng < bar_atr * BREAKOUT_ATR_MAX:
                    # Long breakout
                    if allow_long and bar_close > asian_high:
                        entry_price = bar_close
                        entry_atr = bar_atr
                        stop_price = asian_low - bar_atr * SL_ATR_MULT
                        target_price = bar_close + bar_atr * TP_ATR_MULT
                        signals[i] = 1
                        stop_arr[i] = stop_price
                        target_arr[i] = target_price
                        position = 1
                        trail_active = False
                        trailing_stop = stop_price
                        best_price = bar_close
                        bars_since_trade = 0
                        asian_range_ready = False
                        continue
                    # Short breakout
                    if allow_short and bar_close < asian_low:
                        entry_price = bar_close
                        entry_atr = bar_atr
                        stop_price = asian_high + bar_atr * SL_ATR_MULT
                        target_price = bar_close - bar_atr * TP_ATR_MULT
                        signals[i] = -1
                        stop_arr[i] = stop_price
                        target_arr[i] = target_price
                        position = -1
                        trail_active = False
                        trailing_stop = stop_price
                        best_price = bar_close
                        bars_since_trade = 0
                        asian_range_ready = False
                        continue

            # NY open breakout (trade the London range break at 08:00-12:00)
            if TRADE_NY_OPEN and london_range_ready and NY_START <= h < OVERLAP_END:
                rng = london_high - london_low
                if rng > 0 and rng > bar_atr * BREAKOUT_ATR_FILTER and rng < bar_atr * BREAKOUT_ATR_MAX:
                    # Long breakout
                    if allow_long and bar_close > london_high:
                        entry_price = bar_close
                        entry_atr = bar_atr
                        stop_price = london_low - bar_atr * SL_ATR_MULT
                        target_price = bar_close + bar_atr * TP_ATR_MULT
                        signals[i] = 1
                        stop_arr[i] = stop_price
                        target_arr[i] = target_price
                        position = 1
                        trail_active = False
                        trailing_stop = stop_price
                        best_price = bar_close
                        bars_since_trade = 0
                        london_range_ready = False
                        continue
                    # Short breakout
                    if allow_short and bar_close < london_low:
                        entry_price = bar_close
                        entry_atr = bar_atr
                        stop_price = london_high + bar_atr * SL_ATR_MULT
                        target_price = bar_close - bar_atr * TP_ATR_MULT
                        signals[i] = -1
                        stop_arr[i] = stop_price
                        target_arr[i] = target_price
                        position = -1
                        trail_active = False
                        trailing_stop = stop_price
                        best_price = bar_close
                        bars_since_trade = 0
                        london_range_ready = False
                        continue

    # Write output
    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["hour", "date", "atr", "vol_avg"], inplace=True)
    return df
