"""VWAP Mean Reversion — Fade extremes back to session VWAP.

Designed for Crude Oil futures (MCL) but asset-agnostic.
Enters when price reaches VWAP +/- 2.0 sigma and shows reversal,
targeting a fade back to VWAP (the mean).

Logic:
- Session VWAP with standard deviation bands (1.5 and 2.0 sigma)
- Entry LONG: price touches -2.0 sigma, bar is bullish (close > open), RSI < 30
- Entry SHORT: price touches +2.0 sigma, bar is bearish (close < open), RSI > 70
- Stop: 1.5 * ATR(14) beyond the extreme
- Target: session VWAP (mean reversion target)
- Time filter: 09:30-15:30 ET only (avoid open/close noise)

Expected behavior:
- Win rate 50-65% (mean reversion with confirmation)
- Median hold time 10-40 bars (fading back to mean)
- Best in range-bound / normal volatility regimes

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ---------------------------------------------------------------

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

ATR_PERIOD = 14
ATR_STOP_MULT = 1.5       # Stop distance = ATR x mult beyond the extreme

VWAP_INNER_SIGMA = 1.5    # Inner band (reference only, not used for entry)
VWAP_OUTER_SIGMA = 2.0    # Entry trigger band

SESSION_START = "09:30"
SESSION_END   = "15:30"
ENTRY_START   = "09:30"
ENTRY_CUTOFF  = "15:00"   # No new entries in last 30 min

TICK_SIZE = 0.01           # Patched per asset by runner


# -- Helpers ------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    """Convert datetime series to HH:MM string series."""
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _rsi(series: pd.Series, period: int) -> pd.Series:
    """Wilder-smoothed RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Exponential ATR."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _compute_session_vwap_and_bands(df: pd.DataFrame) -> tuple:
    """Compute session-anchored VWAP and standard deviation bands.

    Returns (vwap, upper_inner, lower_inner, upper_outer, lower_outer) as numpy arrays.
    Bands are VWAP +/- N * rolling standard deviation of (typical_price - VWAP).
    """
    dt = pd.to_datetime(df["datetime"])
    dates = dt.dt.date.values
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

    # Typical price
    tp = (high + low + close) / 3.0

    n = len(df)
    vwap = np.full(n, np.nan)
    upper_inner = np.full(n, np.nan)
    lower_inner = np.full(n, np.nan)
    upper_outer = np.full(n, np.nan)
    lower_outer = np.full(n, np.nan)

    cum_tp_vol = 0.0
    cum_vol = 0.0
    cum_tp2_vol = 0.0       # For variance: cumsum(tp^2 * vol)
    current_date = None

    for i in range(n):
        if dates[i] != current_date:
            current_date = dates[i]
            cum_tp_vol = 0.0
            cum_vol = 0.0
            cum_tp2_vol = 0.0

        vol = max(volume[i], 1.0)   # Avoid zero volume
        cum_tp_vol += tp[i] * vol
        cum_tp2_vol += (tp[i] ** 2) * vol
        cum_vol += vol

        v = cum_tp_vol / cum_vol
        vwap[i] = v

        # Population variance: E[X^2] - (E[X])^2
        variance = (cum_tp2_vol / cum_vol) - (v ** 2)
        std = np.sqrt(max(variance, 0.0))

        upper_inner[i] = v + VWAP_INNER_SIGMA * std
        lower_inner[i] = v - VWAP_INNER_SIGMA * std
        upper_outer[i] = v + VWAP_OUTER_SIGMA * std
        lower_outer[i] = v - VWAP_OUTER_SIGMA * std

    return vwap, upper_inner, lower_inner, upper_outer, lower_outer


# -- Signal Generator ---------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset: str = None, mode: str = "long") -> pd.DataFrame:
    """Generate VWAP mean reversion signals from OHLCV data.

    Parameters
    ----------
    df : DataFrame with columns open, high, low, close, volume (5-min bars).
    asset : Optional asset name (unused — strategy is asset-agnostic).
    mode : "long", "short", or "both" (default "long").

    Returns
    -------
    DataFrame with added columns: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Session boundaries ---------------------------------------------------
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # -- Indicators -----------------------------------------------------------
    vwap, upper_inner, lower_inner, upper_outer, lower_outer = \
        _compute_session_vwap_and_bands(df)

    rsi = _rsi(df["close"], RSI_PERIOD).values
    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD).values

    # -- Pre-compute arrays ---------------------------------------------------
    open_arr = df["open"].values
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful loop --------------------------------------------------------
    position = 0          # 1 = long, -1 = short, 0 = flat
    entry_stop = 0.0
    entry_target = 0.0
    current_date = None

    for i in range(n):
        bar_date = dates_arr[i]
        bar_atr = atr[i]
        bar_rsi = rsi[i]
        bar_vwap = vwap[i]

        # -- Day reset (flatten any open position) ----------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date

        if not in_session_arr[i]:
            continue

        if np.isnan(bar_vwap) or np.isnan(bar_atr) or np.isnan(bar_rsi):
            continue

        # -- Session-end flatten ----------------------------------------------
        if position != 0 and time_arr[i] >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # -- Exit logic for open positions ------------------------------------
        if position == 1:
            # Stop hit
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            # Target hit (VWAP)
            elif high_arr[i] >= entry_target:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            # Stop hit
            if high_arr[i] >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            # Target hit (VWAP)
            elif low_arr[i] <= entry_target:
                exit_sigs[i] = -1
                position = 0

        # -- Entry logic (only when flat) -------------------------------------
        if position == 0 and entry_ok_arr[i]:

            # Long: price touches lower outer band + bullish bar + RSI oversold
            if (allow_long
                    and low_arr[i] <= lower_outer[i]
                    and close_arr[i] > open_arr[i]
                    and bar_rsi < RSI_OVERSOLD):

                stop = close_arr[i] - ATR_STOP_MULT * bar_atr
                target = bar_vwap

                # Only enter if target is above entry (positive R:R)
                if target > close_arr[i]:
                    signals_arr[i] = 1
                    stop_arr[i] = stop
                    target_arr[i] = target
                    position = 1
                    entry_stop = stop
                    entry_target = target

            # Short: price touches upper outer band + bearish bar + RSI overbought
            elif (allow_short
                      and high_arr[i] >= upper_outer[i]
                      and close_arr[i] < open_arr[i]
                      and bar_rsi > RSI_OVERBOUGHT):

                stop = close_arr[i] + ATR_STOP_MULT * bar_atr
                target = bar_vwap

                # Only enter if target is below entry (positive R:R)
                if target < close_arr[i]:
                    signals_arr[i] = -1
                    stop_arr[i] = stop
                    target_arr[i] = target
                    position = -1
                    entry_stop = stop
                    entry_target = target

    # -- Build output ---------------------------------------------------------
    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
