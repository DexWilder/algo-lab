"""MOMENTUM-IGNITION — Tail Engine for Institutional Momentum Bursts.

Low-frequency, large-winner strategy targeting explosive directional moves
triggered by volume surges at key VWAP levels. Designed for convex payoff:
most trades scratch or take small losses, winners are 3-4R.

Logic:
- VWAP cross: price crosses session VWAP in trade direction
- Volume surge: bar volume > 2x 20-bar average (institutional participation)
- Momentum confirmation: RSI(14) > 60 long / < 40 short
- Trend alignment: 50-bar EMA slope confirms direction
- Profit ladder exit: ratcheting stops at R-milestones (1.5R->1R, 3R->2R)
- Cooldown: 15 bars between trades to avoid overtrading

Expected behavior:
- Win rate 30-40% (wide stops, strict filters)
- Large average winner vs small average loser (4R target)
- Low frequency: 1-3 trades per day max
- Best in trending + high-volume regimes

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ----------------------------------------------------------------

# VWAP
# (computed from cumulative typical_price * volume, reset daily)

# Volume surge
VOL_AVG_PERIOD = 20       # Lookback for average volume
VOL_SURGE_MULT = 2.0      # Current bar volume must exceed this multiple of avg

# RSI
RSI_PERIOD = 14           # RSI lookback
RSI_LONG_THRESH = 60      # RSI must be above this for long entries
RSI_SHORT_THRESH = 40     # RSI must be below this for short entries

# Trend alignment
TREND_EMA_LEN = 50        # EMA period for trend direction
TREND_SLOPE_BARS = 5      # Bars to compute EMA slope over

# ATR / risk
ATR_PERIOD = 14           # ATR lookback
ATR_STOP_MULT = 1.5       # Initial stop = 1.5x ATR from entry
ATR_TARGET_MULT = 4.0     # Target = 4.0x ATR from entry (tail capture)

# Profit ladder (trailing stop ratchets)
LADDER_R1 = 1.5           # After 1.5R of profit, lock stop at 1R
LADDER_LOCK1 = 1.0        # Stop moves to entry + 1R
LADDER_R2 = 3.0           # After 3R of profit, lock stop at 2R
LADDER_LOCK2 = 2.0        # Stop moves to entry + 2R

# Cooldown
COOLDOWN_BARS = 15        # Minimum bars between trades

# Session times
SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "09:45"     # Wait 15 min for VWAP + volume to stabilize
ENTRY_CUTOFF = "14:30"    # No new entries in last hour
FLATTEN_TIME = "15:30"    # Pre-close flatten

TICK_SIZE = 0.25           # Patched per asset by runner


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_session_vwap(df: pd.DataFrame) -> np.ndarray:
    """Compute session-anchored VWAP (resets each day)."""
    dt = pd.to_datetime(df["datetime"])
    dates = dt.dt.date.values
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
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


def _compute_rsi(close: np.ndarray, period: int) -> np.ndarray:
    """Compute RSI using exponential moving average of gains/losses."""
    n = len(close)
    rsi = np.full(n, np.nan)

    if n < period + 1:
        return rsi

    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Seed with simple average
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - 100.0 / (1.0 + rs)

    # EMA smoothing
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)

    return rsi


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate momentum ignition signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Session boundaries ----------------------------------------------------
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # -- VWAP ------------------------------------------------------------------
    vwap = _compute_session_vwap(df)

    # -- Trend EMA -------------------------------------------------------------
    ema = df["close"].ewm(span=TREND_EMA_LEN, adjust=False).mean().values

    # -- ATR -------------------------------------------------------------------
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # -- RSI -------------------------------------------------------------------
    rsi = _compute_rsi(df["close"].values, RSI_PERIOD)

    # -- Volume average --------------------------------------------------------
    vol_series = df["volume"] if "volume" in df.columns else pd.Series(np.ones(n))
    vol_avg = vol_series.rolling(VOL_AVG_PERIOD, min_periods=VOL_AVG_PERIOD).mean().values
    vol_arr = vol_series.values

    # -- Pre-compute arrays ----------------------------------------------------
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful loop ---------------------------------------------------------
    position = 0
    entry_price = 0.0
    initial_risk = 0.0        # 1R in dollar terms
    trailing_stop = 0.0
    current_date = None
    cooldown_remaining = 0
    bars_in_trade = 0

    # Previous bar VWAP side (for cross detection)
    prev_above_vwap = False
    prev_below_vwap = False

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_vwap = vwap[i]
        bar_ema = ema[i]
        bar_rsi = rsi[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            cooldown_remaining = 0
            prev_above_vwap = False
            prev_below_vwap = False

        if not in_session_arr[i]:
            continue

        if np.isnan(bar_vwap) or np.isnan(bar_atr) or np.isnan(bar_ema) or np.isnan(bar_rsi):
            # Still track VWAP side even with NaN indicators
            if not np.isnan(bar_vwap):
                prev_above_vwap = close_arr[i] > bar_vwap
                prev_below_vwap = close_arr[i] < bar_vwap
            continue

        # Track VWAP side for cross detection
        curr_above_vwap = close_arr[i] > bar_vwap
        curr_below_vwap = close_arr[i] < bar_vwap

        # Detect VWAP crosses
        vwap_cross_up = curr_above_vwap and prev_below_vwap
        vwap_cross_down = curr_below_vwap and prev_above_vwap

        # Decrement cooldown
        if cooldown_remaining > 0:
            cooldown_remaining -= 1

        # -- Pre-close flatten -------------------------------------------------
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            prev_above_vwap = curr_above_vwap
            prev_below_vwap = curr_below_vwap
            continue

        # -- Manage open position (profit ladder exit) -------------------------
        if position == 1:
            bars_in_trade += 1
            unrealized_r = (high_arr[i] - entry_price) / initial_risk if initial_risk > 0 else 0

            # Profit ladder: ratchet stop at R-milestones
            if unrealized_r >= LADDER_R2:
                new_stop = entry_price + initial_risk * LADDER_LOCK2
                if new_stop > trailing_stop:
                    trailing_stop = new_stop
            elif unrealized_r >= LADDER_R1:
                new_stop = entry_price + initial_risk * LADDER_LOCK1
                if new_stop > trailing_stop:
                    trailing_stop = new_stop

            # Check stop hit
            if low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0
                cooldown_remaining = COOLDOWN_BARS

            # Check target hit
            elif high_arr[i] >= entry_price + initial_risk * ATR_TARGET_MULT / ATR_STOP_MULT:
                exit_sigs[i] = 1
                position = 0
                cooldown_remaining = COOLDOWN_BARS

        elif position == -1:
            bars_in_trade += 1
            unrealized_r = (entry_price - low_arr[i]) / initial_risk if initial_risk > 0 else 0

            # Profit ladder: ratchet stop at R-milestones
            if unrealized_r >= LADDER_R2:
                new_stop = entry_price - initial_risk * LADDER_LOCK2
                if new_stop < trailing_stop:
                    trailing_stop = new_stop
            elif unrealized_r >= LADDER_R1:
                new_stop = entry_price - initial_risk * LADDER_LOCK1
                if new_stop < trailing_stop:
                    trailing_stop = new_stop

            # Check stop hit
            if high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0
                cooldown_remaining = COOLDOWN_BARS

            # Check target hit
            elif low_arr[i] <= entry_price - initial_risk * ATR_TARGET_MULT / ATR_STOP_MULT:
                exit_sigs[i] = -1
                position = 0
                cooldown_remaining = COOLDOWN_BARS

        # -- Entry logic -------------------------------------------------------
        if position == 0 and entry_ok_arr[i] and cooldown_remaining == 0:

            # Volume surge check
            if np.isnan(vol_avg[i]) or vol_avg[i] <= 0:
                prev_above_vwap = curr_above_vwap
                prev_below_vwap = curr_below_vwap
                continue
            volume_surge = vol_arr[i] > vol_avg[i] * VOL_SURGE_MULT

            # EMA slope for trend alignment
            if i >= TREND_SLOPE_BARS:
                ema_slope = ema[i] - ema[i - TREND_SLOPE_BARS]
            else:
                ema_slope = 0.0

            # -- Long entry ----------------------------------------------------
            # VWAP cross up + volume surge + RSI momentum + trend alignment
            if (vwap_cross_up
                    and volume_surge
                    and bar_rsi > RSI_LONG_THRESH
                    and ema_slope > 0):

                risk = bar_atr * ATR_STOP_MULT
                stop = close_arr[i] - risk
                target = close_arr[i] + bar_atr * ATR_TARGET_MULT

                signals_arr[i] = 1
                stop_arr[i] = stop
                target_arr[i] = target
                position = 1
                entry_price = close_arr[i]
                initial_risk = risk
                trailing_stop = stop
                bars_in_trade = 0
                cooldown_remaining = 0

            # -- Short entry ---------------------------------------------------
            elif (vwap_cross_down
                  and volume_surge
                  and bar_rsi < RSI_SHORT_THRESH
                  and ema_slope < 0):

                risk = bar_atr * ATR_STOP_MULT
                stop = close_arr[i] + risk
                target = close_arr[i] - bar_atr * ATR_TARGET_MULT

                signals_arr[i] = -1
                stop_arr[i] = stop
                target_arr[i] = target
                position = -1
                entry_price = close_arr[i]
                initial_risk = risk
                trailing_stop = stop
                bars_in_trade = 0
                cooldown_remaining = 0

        # Update previous VWAP side
        prev_above_vwap = curr_above_vwap
        prev_below_vwap = curr_below_vwap

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
