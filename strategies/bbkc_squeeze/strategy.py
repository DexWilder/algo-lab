"""BBKC-SQUEEZE — Bollinger Band / Keltner Channel Squeeze Momentum.

Source: LazyBear — Trading Strategy based on BB/KC Squeeze
URL: https://www.tradingview.com/script/x9r2dOhI-Trading-Strategy-based-on-BB-KC-squeeze/
Family: breakout (volatility compression)
Conversion: Faithful — original LazyBear squeeze logic preserved.

Logic:
- Bollinger Bands (SMA 14, mult 2.0) inside Keltner Channel (SMA 16, mult 1.5) = SQUEEZE
- Momentum histogram = linreg(close - midline, KC_length, 0)
- Entry on squeeze RELEASE (BB exits KC) + momentum direction:
    - Long: squeeze releases + momentum > 0 and rising (lime)
    - Short: squeeze releases + momentum < 0 and falling (red)
- Exit on momentum deceleration:
    - Long exit: momentum still positive but falling (green)
    - Short exit: momentum still negative but rising (maroon)
- Added: ATR protective stop + session management + EOD flatten

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

BB_LENGTH = 14             # Bollinger Band SMA length
BB_MULT = 2.0              # BB standard deviation multiplier
KC_LENGTH = 16             # Keltner Channel SMA length
KC_MULT = 1.5              # KC ATR multiplier
USE_TRUE_RANGE = True      # KC: True Range vs High-Low

ATR_PERIOD = 14            # ATR for protective stop
SL_ATR = 2.0               # Stop = 2.0x ATR from entry

SESSION_START = "09:30"
SESSION_END = "15:15"
ENTRY_CUTOFF = "14:30"     # No new entries in last 45 min

TICK_SIZE = 0.25            # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def _stdev(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).std(ddof=0)


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    tr = _true_range(high, low, close)
    return tr.ewm(span=period, adjust=False).mean()


def _linreg(series: pd.Series, length: int) -> pd.Series:
    """Rolling linear regression value at current bar (offset=0)."""
    result = np.full(len(series), np.nan)
    vals = series.values
    for i in range(length - 1, len(vals)):
        window = vals[i - length + 1:i + 1]
        if np.any(np.isnan(window)):
            continue
        x = np.arange(length, dtype=float)
        # Linear regression: y = mx + b, evaluate at x = length-1 (current bar)
        x_mean = x.mean()
        y_mean = window.mean()
        ss_xy = np.sum((x - x_mean) * (window - y_mean))
        ss_xx = np.sum((x - x_mean) ** 2)
        if ss_xx == 0:
            result[i] = y_mean
        else:
            slope = ss_xy / ss_xx
            intercept = y_mean - slope * x_mean
            result[i] = slope * (length - 1) + intercept
    return pd.Series(result, index=series.index)


def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate BB/KC squeeze momentum signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    # ── Bollinger Bands ───────────────────────────────────────────────
    bb_basis = _sma(df["close"], BB_LENGTH)
    bb_dev = BB_MULT * _stdev(df["close"], BB_LENGTH)
    upper_bb = bb_basis + bb_dev
    lower_bb = bb_basis - bb_dev

    # ── Keltner Channel ───────────────────────────────────────────────
    kc_ma = _sma(df["close"], KC_LENGTH)
    if USE_TRUE_RANGE:
        kc_range = _true_range(df["high"], df["low"], df["close"])
    else:
        kc_range = df["high"] - df["low"]
    kc_rangema = _sma(kc_range, KC_LENGTH)
    upper_kc = kc_ma + kc_rangema * KC_MULT
    lower_kc = kc_ma - kc_rangema * KC_MULT

    # ── Squeeze detection ─────────────────────────────────────────────
    sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)    # BB inside KC
    sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)   # BB outside KC
    # noSqz = ~sqz_on & ~sqz_off  # transitional

    # ── Momentum histogram ────────────────────────────────────────────
    # val = linreg(close - avg(avg(highest(high,KC_LENGTH), lowest(low,KC_LENGTH)), sma(close,KC_LENGTH)), KC_LENGTH, 0)
    hh = df["high"].rolling(window=KC_LENGTH, min_periods=KC_LENGTH).max()
    ll = df["low"].rolling(window=KC_LENGTH, min_periods=KC_LENGTH).min()
    donchian_mid = (hh + ll) / 2
    sma_close = _sma(df["close"], KC_LENGTH)
    midline = (donchian_mid + sma_close) / 2
    delta = df["close"] - midline

    mom = _linreg(delta, KC_LENGTH)

    # Momentum color states
    mom_prev = mom.shift(1)
    # lime:   val > 0 and val > val[1]  (positive, increasing)
    # green:  val > 0 and val <= val[1] (positive, decreasing)
    # red:    val < 0 and val < val[1]  (negative, decreasing)
    # maroon: val < 0 and val >= val[1] (negative, increasing)

    is_lime = (mom > 0) & (mom > mom_prev)
    is_green = (mom > 0) & (mom <= mom_prev)
    is_red = (mom < 0) & (mom < mom_prev)
    is_maroon = (mom < 0) & (mom >= mom_prev)

    # ── Entry: squeeze release + momentum direction ───────────────────
    # Long: sqz_off just fired (previous bar NOT sqz_off) + momentum lime
    sqz_release = sqz_off & ~sqz_off.shift(1, fill_value=False)

    long_signal = sqz_release & is_lime & in_session & (time_str < ENTRY_CUTOFF)
    short_signal = sqz_release & is_red & in_session & (time_str < ENTRY_CUTOFF)

    # ── ATR for protective stops ──────────────────────────────────────
    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)

    # ── Build output ──────────────────────────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    long_mask = long_signal.fillna(False)
    short_mask = short_signal.fillna(False)

    stop_dist = atr * SL_ATR

    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "close"] - stop_dist[long_mask]
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] * 1.10  # dummy (exit on momentum)

    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "close"] + stop_dist[short_mask]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] * 0.90  # dummy

    # ── Exit loop: momentum deceleration + stop + EOD ─────────────────
    position = 0
    entry_stop = 0.0
    exit_sigs = np.zeros(n, dtype=int)
    signals_arr = df["signal"].values.copy()

    close_arr = df["close"].values
    low_arr = df["low"].values
    high_arr = df["high"].values
    time_arr = time_str.values
    is_green_arr = is_green.fillna(False).values
    is_maroon_arr = is_maroon.fillna(False).values
    traded_today = None

    dates_arr = df["_date"].values

    for i in range(n):
        sig = signals_arr[i]
        bar_date = dates_arr[i]

        # Day reset
        if bar_date != traded_today:
            if position != 0:
                # Force close from previous day
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0

        # EOD flatten
        if position != 0 and time_arr[i] >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            traded_today = bar_date
            continue

        # Check exits for open position
        if position == 1:
            # Stop hit
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            # Momentum deceleration: lime -> green
            elif is_green_arr[i]:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            # Stop hit
            if high_arr[i] >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            # Momentum deceleration: red -> maroon
            elif is_maroon_arr[i]:
                exit_sigs[i] = -1
                position = 0

        # Open new position
        if position == 0 and sig != 0:
            stop_p = df.iloc[i]["stop_price"]
            if pd.notna(stop_p):
                position = sig
                entry_stop = stop_p
                traded_today = bar_date

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
