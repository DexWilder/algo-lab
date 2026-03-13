"""Momentum Pullback Trend — Higher-Timeframe Trend + Pullback Entries.

Designed for bond futures (ZN/ZB) but works on any asset.
Bonds trend slowly but persistently — this strategy uses a long-lookback
EMA for trend direction with pullback entries at a shorter EMA.

Logic:
- Trend: 200-bar EMA on 5m (~17 hours) establishes direction
- Momentum: RSI(20) confirms trend strength (>55 bull, <45 bear)
- Pullback: price retraces to 50-bar EMA, then bounces/rejects
- Stop: 2.0 ATR(20) beyond pullback extreme
- Target: 3.0 ATR(20) from entry (wider for bond trend persistence)
- Trail: after 1.5R, trail at 1.0 ATR(20) below highest close (longs)
- Cooldown: minimum 10 bars between trades to avoid chop

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

# Trend & momentum
TREND_EMA_LEN = 200       # Long-term trend direction (~17 hours on 5m)
PULLBACK_EMA_LEN = 50     # Pullback target / short-term MA
RSI_LEN = 20              # Momentum confirmation period
RSI_BULL_THRESH = 55      # RSI above this for uptrend confirmation
RSI_BEAR_THRESH = 45      # RSI below this for downtrend confirmation

# ATR & exits
ATR_LEN = 20              # ATR period
SL_ATR_MULT = 2.0         # Stop distance = ATR × 2.0
TP_ATR_MULT = 3.0         # Target distance = ATR × 3.0 (wider for bond trends)
TRAIL_ACTIVATION_R = 1.5  # Activate trailing stop after 1.5R profit
TRAIL_ATR_MULT = 1.0      # Trail distance = ATR × 1.0 below swing high/low

# Filters
MIN_BARS_BETWEEN = 10     # Minimum bars between trades (anti-chop)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Average True Range using EMA smoothing."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(
    df: pd.DataFrame,
    asset: str | None = None,
    mode: str = "long",
) -> pd.DataFrame:
    """Generate momentum pullback trend signals from OHLCV data.

    Parameters
    ----------
    df : DataFrame with columns: open, high, low, close, volume (5m bars).
    asset : Optional asset name (unused — strategy is asset-agnostic).
    mode : "long", "short", or "both" (default "long").

    Returns
    -------
    DataFrame with added columns: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    # ── Compute indicators ─────────────────────────────────────────────
    df["ema_trend"] = _ema(df["close"], TREND_EMA_LEN)
    df["ema_pb"] = _ema(df["close"], PULLBACK_EMA_LEN)
    df["rsi"] = _rsi(df["close"], RSI_LEN)
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    # Pre-compute numpy arrays for the stateful loop
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    ema_trend = df["ema_trend"].values
    ema_pb = df["ema_pb"].values
    rsi_arr = df["rsi"].values
    atr_arr = df["atr"].values

    # ── Pullback detection ─────────────────────────────────────────────
    # "Touched" EMA50: bar's low touched or crossed below EMA50 (longs),
    # or bar's high touched or crossed above EMA50 (shorts).
    # "Bounced": close recovers above/below EMA50 on the same or next bar.
    touched_pb_low = low_arr <= ema_pb        # Wick touched EMA50 from above
    touched_pb_high = high_arr >= ema_pb      # Wick touched EMA50 from below
    close_above_pb = close_arr > ema_pb       # Close recovered above EMA50
    close_below_pb = close_arr < ema_pb       # Close rejected below EMA50

    # Bounce: touched the pullback EMA and closed back on the trend side
    pb_bounce_long = touched_pb_low & close_above_pb    # Pulled back, bounced up
    pb_reject_short = touched_pb_high & close_below_pb  # Pulled back, rejected down

    # ── Trend + momentum conditions ────────────────────────────────────
    trend_bull = (close_arr > ema_trend) & (rsi_arr > RSI_BULL_THRESH)
    trend_bear = (close_arr < ema_trend) & (rsi_arr < RSI_BEAR_THRESH)

    # ── Raw entry conditions (before cooldown & mode filter) ───────────
    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    raw_long = trend_bull & pb_bounce_long if allow_long else np.zeros(n, dtype=bool)
    raw_short = trend_bear & pb_reject_short if allow_short else np.zeros(n, dtype=bool)

    # ── Output arrays ──────────────────────────────────────────────────
    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # ── Stateful loop: entries, exits, trailing stop, cooldown ─────────
    position = 0            # 1 = long, -1 = short, 0 = flat
    entry_price = 0.0
    entry_atr = 0.0
    stop_price = 0.0
    target_price = 0.0
    trail_active = False
    trailing_stop = 0.0
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    bars_since_last_trade = MIN_BARS_BETWEEN  # Allow first trade immediately

    for i in range(n):
        bar_close = close_arr[i]
        bar_high = high_arr[i]
        bar_low = low_arr[i]
        bar_atr = atr_arr[i]

        # Skip bars where indicators haven't warmed up
        if np.isnan(ema_trend[i]) or np.isnan(ema_pb[i]) or np.isnan(rsi_arr[i]) or np.isnan(bar_atr):
            bars_since_last_trade += 1
            continue

        # ── Manage open position ────────────────────────────────────
        if position == 1:
            # Track highest close for trailing stop
            if bar_close > highest_since_entry:
                highest_since_entry = bar_close

            # Check trailing stop activation: 1.5R profit reached
            r_dist = entry_atr * SL_ATR_MULT  # 1R = stop distance
            if not trail_active and (highest_since_entry - entry_price) >= TRAIL_ACTIVATION_R * r_dist:
                trail_active = True
                trailing_stop = highest_since_entry - bar_atr * TRAIL_ATR_MULT

            # Update trailing stop if active
            if trail_active:
                new_trail = highest_since_entry - bar_atr * TRAIL_ATR_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Exit check: trailing stop (if active) or initial stop
            active_stop = trailing_stop if trail_active else stop_price
            if bar_low <= active_stop:
                exit_sigs[i] = 1
                position = 0
                bars_since_last_trade = 0
            # Exit check: target hit
            elif bar_high >= target_price:
                exit_sigs[i] = 1
                position = 0
                bars_since_last_trade = 0

        elif position == -1:
            # Track lowest close for trailing stop
            if bar_close < lowest_since_entry:
                lowest_since_entry = bar_close

            # Check trailing stop activation: 1.5R profit reached
            r_dist = entry_atr * SL_ATR_MULT
            if not trail_active and (entry_price - lowest_since_entry) >= TRAIL_ACTIVATION_R * r_dist:
                trail_active = True
                trailing_stop = lowest_since_entry + bar_atr * TRAIL_ATR_MULT

            # Update trailing stop if active
            if trail_active:
                new_trail = lowest_since_entry + bar_atr * TRAIL_ATR_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            # Exit check: trailing stop (if active) or initial stop
            active_stop = trailing_stop if trail_active else stop_price
            if bar_high >= active_stop:
                exit_sigs[i] = -1
                position = 0
                bars_since_last_trade = 0
            # Exit check: target hit
            elif bar_low <= target_price:
                exit_sigs[i] = -1
                position = 0
                bars_since_last_trade = 0

        # ── Entry logic (only when flat) ────────────────────────────
        if position == 0:
            bars_since_last_trade += 1

            if bars_since_last_trade >= MIN_BARS_BETWEEN:
                # Long entry
                if raw_long[i]:
                    entry_price = bar_close
                    entry_atr = bar_atr
                    stop_price = bar_low - bar_atr * SL_ATR_MULT   # Below pullback low
                    target_price = bar_close + bar_atr * TP_ATR_MULT

                    signals_arr[i] = 1
                    stop_arr[i] = stop_price
                    target_arr[i] = target_price

                    position = 1
                    trail_active = False
                    trailing_stop = stop_price
                    highest_since_entry = bar_close
                    bars_since_last_trade = 0

                # Short entry
                elif raw_short[i]:
                    entry_price = bar_close
                    entry_atr = bar_atr
                    stop_price = bar_high + bar_atr * SL_ATR_MULT  # Above pullback high
                    target_price = bar_close - bar_atr * TP_ATR_MULT

                    signals_arr[i] = -1
                    stop_arr[i] = stop_price
                    target_arr[i] = target_price

                    position = -1
                    trail_active = False
                    trailing_stop = stop_price
                    lowest_since_entry = bar_close
                    bars_since_last_trade = 0

    # ── Write output columns ───────────────────────────────────────────
    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr

    # Clean up intermediate columns
    df.drop(columns=["ema_trend", "ema_pb", "rsi", "atr"], inplace=True)

    return df
