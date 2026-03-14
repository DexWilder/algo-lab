"""CLOSE-VWAP-REVERSION — Close Session VWAP Mean Reversion.

Fills the 15:00-16:00 ET session gap in the portfolio.
Type: stabilizer/mean-reversion — fade overextension back to VWAP into the close.

Logic:
- Session VWAP with deviation bands (rolling std of close-VWAP)
- Entry window: 15:00-15:50 ET only
- Long: close below lower band (VWAP - 2 sigma) + RSI < 30
- Short: close above upper band (VWAP + 2 sigma) + RSI > 70
- Volume confirmation: bar volume > 1.0x 20-bar SMA
- Target: VWAP (fade back to mean)
- Stop: 1.5x ATR(14) from entry
- Time exit: force close at 15:55 (5 min before session end)
- No trailing — quick mean-reversion trades, target or stop
- Cooldown: 6 bars (30 min on 5m)
- Max 1 trade per session per direction

Expected behavior:
- Win rate 50-65% (mean-reversion at extreme deviation)
- Median hold time 2-10 bars (quick reversion into close)
- Should profit in all volatility regimes (session close is structural)

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ---------------------------------------------------------------

ATR_PERIOD = 14            # ATR period for stop calculation
ATR_STOP_MULT = 1.5        # Stop distance = ATR x mult
RSI_PERIOD = 14            # RSI lookback
RSI_OVERSOLD = 30          # Long entry threshold
RSI_OVERBOUGHT = 70        # Short entry threshold
VWAP_DEV_PERIOD = 50       # Rolling window for VWAP deviation std
VWAP_DEV_MULT = 2.0        # Band width = std x mult
VOL_CONFIRM_MULT = 1.0     # Bar volume > mult x 20-bar avg
VOL_AVG_PERIOD = 20        # Volume average lookback
COOLDOWN_BARS = 6          # Min bars between trades (30 min on 5m)

ENTRY_START = "15:00"      # Earliest entry time
ENTRY_CUTOFF = "15:50"     # Latest entry time
TIME_EXIT = "15:55"        # Force close — never hold overnight

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

    # Seed with SMA
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - 100.0 / (1.0 + rs)

    # EMA smoothing
    alpha = 1.0 / period
    for i in range(period, len(deltas)):
        avg_gain = avg_gain * (1 - alpha) + gains[i] * alpha
        avg_loss = avg_loss * (1 - alpha) + losses[i] * alpha
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100.0 - 100.0 / (1.0 + rs)

    return rsi


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate close-session VWAP reversion signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Entry window ----------------------------------------------------------
    entry_ok = (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # -- Session VWAP ----------------------------------------------------------
    vwap = _compute_session_vwap(df)

    # -- VWAP deviation bands --------------------------------------------------
    close_arr = df["close"].values
    vwap_dev = close_arr - vwap  # deviation from VWAP

    # Rolling std of deviation (pandas for convenience, then extract)
    dev_std = pd.Series(vwap_dev).rolling(VWAP_DEV_PERIOD, min_periods=VWAP_DEV_PERIOD).std().values
    upper_band = vwap + VWAP_DEV_MULT * dev_std
    lower_band = vwap - VWAP_DEV_MULT * dev_std

    # -- RSI -------------------------------------------------------------------
    rsi = _compute_rsi(close_arr, RSI_PERIOD)

    # -- ATR -------------------------------------------------------------------
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # -- Volume confirmation ---------------------------------------------------
    volume = df["volume"].values if "volume" in df.columns else np.ones(n)
    vol_sma = pd.Series(volume).rolling(VOL_AVG_PERIOD, min_periods=VOL_AVG_PERIOD).mean().values
    vol_ok = volume > VOL_CONFIRM_MULT * vol_sma

    # -- Pre-compute arrays ----------------------------------------------------
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    entry_ok_arr = entry_ok.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful loop ---------------------------------------------------------
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    bars_since_last_trade = COOLDOWN_BARS  # Allow first trade immediately

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_vwap = vwap[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False
            bars_since_last_trade = COOLDOWN_BARS

        # Skip if indicators not ready
        if (np.isnan(bar_vwap) or np.isnan(bar_atr) or np.isnan(rsi[i])
                or np.isnan(dev_std[i])):
            bars_since_last_trade += 1
            continue

        # -- Time exit at 15:55 — CRITICAL, never hold overnight ---------------
        if position != 0 and bar_time >= TIME_EXIT:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            bars_since_last_trade = 0
            continue

        # -- Check exits for open position -------------------------------------
        if position == 1:
            bars_since_last_trade += 1

            # Target hit: price reached VWAP (mean reversion complete)
            if high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0
                continue

            # Stop hit
            if low_arr[i] <= stop_price:
                exit_sigs[i] = 1
                position = 0
                continue

        elif position == -1:
            bars_since_last_trade += 1

            # Target hit: price reached VWAP
            if low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
                continue

            # Stop hit
            if high_arr[i] >= stop_price:
                exit_sigs[i] = -1
                position = 0
                continue

        # -- Entry logic -------------------------------------------------------
        if position == 0 and entry_ok_arr[i] and bars_since_last_trade >= COOLDOWN_BARS:

            # -- Long: oversold below lower band, fade back to VWAP ------------
            if (not long_traded_today
                    and close_arr[i] < lower_band[i]
                    and rsi[i] < RSI_OVERSOLD
                    and vol_ok[i]):

                initial_stop = close_arr[i] - bar_atr * ATR_STOP_MULT
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = bar_vwap
                position = 1
                entry_price = close_arr[i]
                stop_price = initial_stop
                target_price = bar_vwap
                long_traded_today = True
                bars_since_last_trade = 0

            # -- Short: overbought above upper band, fade back to VWAP ---------
            elif (not short_traded_today
                  and close_arr[i] > upper_band[i]
                  and rsi[i] > RSI_OVERBOUGHT
                  and vol_ok[i]):

                initial_stop = close_arr[i] + bar_atr * ATR_STOP_MULT
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = bar_vwap
                position = -1
                entry_price = close_arr[i]
                stop_price = initial_stop
                target_price = bar_vwap
                short_traded_today = True
                bars_since_last_trade = 0

        bars_since_last_trade += 1

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
