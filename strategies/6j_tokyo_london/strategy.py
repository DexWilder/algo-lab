"""6J Tokyo-to-London Session Transition -- Two distinct setups.

Setup A: Tokyo Squeeze -> London Expansion
  Tokyo session builds a compressed range. At London open, trade the
  breakout of that compressed box. Requires range to be tighter than
  recent sessions (compression filter). Entry in first 90 minutes of
  London on a close beyond the Tokyo extreme.

Setup B: Tokyo False-Break Reclaim
  Late Tokyo session probes beyond the range but fails to hold.
  Price reclaims inside the box -> fade the false break.
  Entry on the reclaim, target is range midpoint then opposite edge.
  Stop just beyond the false-break extreme.

Designed specifically for 6J (Japanese Yen futures). Tokyo session
is structurally meaningful for JPY pricing, and the London open
injects the first European liquidity wave.

Session definitions (Eastern Time):
  Tokyo:  18:00-03:00 ET (Sunday-Thursday)
  London: 03:00-08:00 ET
  NY:     08:00-16:00 ET

Source: OpenClaw harvest notes 16, 17
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Tokyo session (ET)
TOKYO_START = 18    # 18:00 ET previous day
TOKYO_END = 3       # 03:00 ET

# London entry window
LONDON_START = 3
LONDON_ENTRY_END = 5  # First 2 hours of London (03:00-05:00)

# False-break window (late Tokyo)
FALSE_BREAK_START = 1   # 01:00 ET (last 2 hours of Tokyo)
FALSE_BREAK_END = 3     # 03:00 ET

# Session close
SESSION_FLATTEN = 8     # Flatten at NY open (08:00 ET)

# ---- Setup A: Squeeze -> Expansion ----
COMPRESSION_LOOKBACK = 10  # Compare Tokyo range to last N sessions
COMPRESSION_PERCENTILE = 40  # Range must be below this percentile (tight)
BREAKOUT_CONFIRM_BARS = 1  # Bars above/below range to confirm breakout

# ---- Setup B: False-Break Reclaim ----
FALSE_BREAK_MIN_TICKS = 3   # Minimum probe beyond range (in ticks)
RECLAIM_BARS = 3             # Must reclaim within N bars

# ---- Risk (shared) ----
ATR_LEN = 20
SL_ATR_MULT = 1.5   # Stop distance
TP_RANGE_MULT_A = 1.0  # Setup A: target = 1x Tokyo range from entry
TP_RANGE_MULT_B_1 = 0.5  # Setup B first target: range midpoint
MIN_BARS_BETWEEN = 6  # 30 min cooldown

TICK_SIZE = 0.0000005  # 6J default


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
    """Generate 6J Tokyo->London transition signals.

    Returns DataFrame with signal, exit_signal, stop_price, target_price,
    plus setup_type column ("SQUEEZE_EXPANSION" or "FALSE_BREAK_RECLAIM").
    """
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["date"] = df["datetime"].dt.date
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    dates = df["date"].values
    atr = df["atr"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)
    setup_types = [""] * n

    # Session tracking
    tokyo_high = np.nan
    tokyo_low = np.nan
    in_tokyo = False
    tokyo_range_ready = False
    tokyo_range = 0.0

    # Historical Tokyo ranges for compression detection
    tokyo_range_history = []

    # False-break tracking
    false_break_direction = 0  # 1=upside probe, -1=downside probe
    false_break_extreme = 0.0
    false_break_bar = 0
    false_break_armed = False

    # Position state
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    bars_since_trade = MIN_BARS_BETWEEN

    for i in range(n):
        h = hour[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_atr = atr[i]

        if np.isnan(bar_atr) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Tokyo session range accumulation ----
        if h >= TOKYO_START or h < TOKYO_END:
            if not in_tokyo:
                tokyo_high = bar_high
                tokyo_low = bar_low
                in_tokyo = True
                tokyo_range_ready = False
                false_break_armed = False
                false_break_direction = 0
            else:
                tokyo_high = max(tokyo_high, bar_high)
                tokyo_low = min(tokyo_low, bar_low)

            # ---- Setup B: Detect false breaks in late Tokyo ----
            if FALSE_BREAK_START <= h < FALSE_BREAK_END and not np.isnan(tokyo_high):
                tok_rng = tokyo_high - tokyo_low
                if tok_rng > 0:
                    # Upside false break: bar pokes above range then closes back inside
                    if bar_high > tokyo_high + TICK_SIZE * FALSE_BREAK_MIN_TICKS:
                        if bar_close < tokyo_high:
                            false_break_direction = 1  # Upside probe failed
                            false_break_extreme = bar_high
                            false_break_bar = i
                            false_break_armed = True

                    # Downside false break
                    if bar_low < tokyo_low - TICK_SIZE * FALSE_BREAK_MIN_TICKS:
                        if bar_close > tokyo_low:
                            false_break_direction = -1  # Downside probe failed
                            false_break_extreme = bar_low
                            false_break_bar = i
                            false_break_armed = True

        elif in_tokyo and h >= TOKYO_END:
            in_tokyo = False
            tokyo_range = tokyo_high - tokyo_low
            tokyo_range_ready = True
            tokyo_range_history.append(tokyo_range)
            if len(tokyo_range_history) > 50:
                tokyo_range_history = tokyo_range_history[-50:]

        # ---- Flatten at session end ----
        if h >= SESSION_FLATTEN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
                bars_since_trade = 0
            continue

        # ---- Manage position ----
        if position == 1:
            if bar_low <= stop_price:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue
            if bar_high >= target_price:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue

        elif position == -1:
            if bar_high >= stop_price:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0
                continue
            if bar_low <= target_price:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0
                continue

        # ---- Entry logic (flat only) ----
        if position == 0:
            bars_since_trade += 1
            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            # ---- Setup A: Squeeze -> Expansion (London window) ----
            if tokyo_range_ready and LONDON_START <= h < LONDON_ENTRY_END:
                if len(tokyo_range_history) >= COMPRESSION_LOOKBACK:
                    recent = sorted(tokyo_range_history[-COMPRESSION_LOOKBACK:])
                    pct_idx = int(len(recent) * COMPRESSION_PERCENTILE / 100)
                    threshold = recent[min(pct_idx, len(recent) - 1)]

                    if tokyo_range <= threshold and tokyo_range > 0:
                        # Compressed Tokyo -> arm for London breakout
                        # Long breakout
                        if allow_long and bar_close > tokyo_high:
                            entry_price = bar_close
                            stop_price = tokyo_low - bar_atr * SL_ATR_MULT
                            target_price = bar_close + tokyo_range * TP_RANGE_MULT_A
                            if target_price <= entry_price:
                                target_price = entry_price + bar_atr * 1.5
                            signals[i] = 1
                            stop_arr[i] = stop_price
                            target_arr[i] = target_price
                            setup_types[i] = "SQUEEZE_EXPANSION"
                            position = 1
                            bars_since_trade = 0
                            tokyo_range_ready = False
                            continue

                        # Short breakout
                        if allow_short and bar_close < tokyo_low:
                            entry_price = bar_close
                            stop_price = tokyo_high + bar_atr * SL_ATR_MULT
                            target_price = bar_close - tokyo_range * TP_RANGE_MULT_A
                            if target_price >= entry_price:
                                target_price = entry_price - bar_atr * 1.5
                            signals[i] = -1
                            stop_arr[i] = stop_price
                            target_arr[i] = target_price
                            setup_types[i] = "SQUEEZE_EXPANSION"
                            position = -1
                            bars_since_trade = 0
                            tokyo_range_ready = False
                            continue

            # ---- Setup B: False-Break Reclaim (late Tokyo / early London) ----
            if false_break_armed and (h >= FALSE_BREAK_START or h < LONDON_ENTRY_END):
                bars_since_fb = i - false_break_bar
                if bars_since_fb <= RECLAIM_BARS * 12:  # ~1 hour window on 5m bars
                    tok_mid = (tokyo_high + tokyo_low) / 2

                    # Upside false break -> short (fade the failed probe)
                    if false_break_direction == 1 and allow_short:
                        if bar_close < tokyo_high and bar_close > tokyo_low:
                            entry_price = bar_close
                            stop_price = false_break_extreme + bar_atr * 0.5
                            target_price = tok_mid  # First target: midpoint
                            signals[i] = -1
                            stop_arr[i] = stop_price
                            target_arr[i] = target_price
                            setup_types[i] = "FALSE_BREAK_RECLAIM"
                            position = -1
                            bars_since_trade = 0
                            false_break_armed = False
                            continue

                    # Downside false break -> long (fade the failed probe)
                    if false_break_direction == -1 and allow_long:
                        if bar_close > tokyo_low and bar_close < tokyo_high:
                            entry_price = bar_close
                            stop_price = false_break_extreme - bar_atr * 0.5
                            target_price = tok_mid
                            signals[i] = 1
                            stop_arr[i] = stop_price
                            target_arr[i] = target_price
                            setup_types[i] = "FALSE_BREAK_RECLAIM"
                            position = 1
                            bars_since_trade = 0
                            false_break_armed = False
                            continue

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df["setup_type"] = setup_types
    df.drop(columns=["hour", "date", "atr"], inplace=True)
    return df
