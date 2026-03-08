"""VWAP Reversion — Mean Reversion Engine (experimental).

Extracted from Lucid v6.3 as the REV module.
Currently produces very few signals (~6 total across 3 assets over 2 years).
Needs significant threshold tuning or architectural rework before deployment.

Roster target: ALGO-CORE-VWAP-001-REV
Status: EXPERIMENTAL — not validated

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

# Indicators
FAST_EMA = 9
SLOW_EMA = 21
RSI_LEN = 14
ATR_LEN = 14

# Quality filters
VOL_MA_LEN = 20
VOL_MULT = 1.0

# Session (RTH eastern)
SESSION_START = "08:30"
SESSION_END = "15:15"
REV_BLACKOUT_MINS = 30

# Power windows
WIN1_START = "08:45"
WIN1_END = "11:00"
WIN2_START = "13:30"
WIN2_END = "15:10"

# Reversion params
REV_DIST_ATR = 1.2
REV_RSI_LOW = 40
REV_RSI_HIGH = 60
REV_NEUTRAL_SEP = 1.0
REV_ADX_MAX = 25.0
ADX_LEN = 14
VWAP_FLAT_MULT = 0.5
REJ_WICK_MIN = 0.4

# Exits
SL_ATR = 1.5
TP_ATR = 2.1
MIN_STOP_TICKS = 20
TICK_SIZE = 0.25


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()

def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    plus_dm = (high - prev_high).clip(lower=0)
    minus_dm = (prev_low - low).clip(lower=0)
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    atr_vals = _atr(high, low, close, period)
    plus_di = 100 * _ema(plus_dm, period) / atr_vals.replace(0, np.nan)
    minus_di = 100 * _ema(minus_dm, period) / atr_vals.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _ema(dx, period)

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate VWAP reversion signals from OHLCV data.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price, signal_type.
    signal_type is always "rev".
    """
    df = df.copy()
    n = len(df)

    # Indicators
    df["ema_fast"] = _ema(df["close"], FAST_EMA)
    df["ema_slow"] = _ema(df["close"], SLOW_EMA)
    df["rsi"] = _rsi(df["close"], RSI_LEN)
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)
    df["adx"] = _adx(df["high"], df["low"], df["close"], ADX_LEN)
    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)

    # VWAP
    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    has_volume = df["volume"].sum() > 0
    if has_volume:
        cum_vol = df.groupby("_date")["volume"].cumsum()
        cum_vp = (hlc3 * df["volume"]).groupby(df["_date"]).cumsum()
        df["vwap"] = cum_vp / cum_vol.replace(0, np.nan)
    else:
        cum_hlc3 = hlc3.groupby(df["_date"]).cumsum()
        cum_count = hlc3.groupby(df["_date"]).cumcount() + 1
        df["vwap"] = cum_hlc3 / cum_count

    # Session filters
    time_str = _parse_time(df["datetime"])
    df["in_session"] = (time_str >= SESSION_START) & (time_str < SESSION_END)
    session_start_mask = df["in_session"] & (~df["in_session"].shift(1, fill_value=False))
    df["_session_bar"] = session_start_mask.cumsum()
    df["_bars_since_open"] = df.groupby("_session_bar").cumcount()
    rev_blackout_bars = REV_BLACKOUT_MINS // 5
    df["rev_time_ok"] = df["in_session"] & (df["_bars_since_open"] >= rev_blackout_bars)

    in_win1 = (time_str >= WIN1_START) & (time_str < WIN1_END)
    in_win2 = (time_str >= WIN2_START) & (time_str < WIN2_END)
    df["allowed"] = df["in_session"] & df["rev_time_ok"] & (in_win1 | in_win2)

    # Quality (volume only — no ADX floor for ranging)
    if has_volume:
        vol_ok = df["volume"] > df["vol_ma"] * VOL_MULT
    else:
        vol_ok = pd.Series(True, index=df.index)

    # MTF filter
    df["ema_mtf"] = _ema(df["close"], 600)
    mtf_bull = df["close"] > df["ema_mtf"]
    mtf_bear = df["close"] < df["ema_mtf"]

    # Reversion conditions
    bar_range = df["high"] - df["low"]
    dist_atr = (df["close"] - df["vwap"]) / df["atr"].replace(0, np.nan)
    ema_sep = (df["ema_fast"] - df["ema_slow"]).abs() / df["atr"].replace(0, np.nan)
    neutralish = ema_sep < REV_NEUTRAL_SEP

    vwap_slope = df["vwap"] - df["vwap"].shift(5)
    vwap_flat = vwap_slope.abs() < df["atr"] * VWAP_FLAT_MULT

    body_size = (df["close"] - df["open"]).abs()
    wick_ratio = np.where(bar_range > 0, (bar_range - body_size) / bar_range, 0)
    strong_rej = wick_ratio >= REJ_WICK_MIN

    bull_rej = (df["close"] > df["open"]) & (df["close"] > (df["high"] + df["low"]) / 2) & strong_rej
    bear_rej = (df["close"] < df["open"]) & (df["close"] < (df["high"] + df["low"]) / 2) & strong_rej

    range_regime = (df["adx"] < REV_ADX_MAX) & neutralish

    rev_long = (
        range_regime & neutralish & vwap_flat &
        (dist_atr <= -REV_DIST_ATR) &
        (df["rsi"] <= REV_RSI_LOW) &
        bull_rej & mtf_bull
    )
    rev_short = (
        range_regime & neutralish & vwap_flat &
        (dist_atr >= REV_DIST_ATR) &
        (df["rsi"] >= REV_RSI_HIGH) &
        bear_rej & mtf_bear
    )

    # Final signals
    long_signal = df["allowed"] & vol_ok & rev_long
    short_signal = df["allowed"] & vol_ok & rev_short

    # Build output
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan
    df["signal_type"] = ""

    stop_dist = df["atr"] * SL_ATR
    stop_dist = stop_dist.clip(lower=MIN_STOP_TICKS * TICK_SIZE)
    target_dist = df["atr"] * TP_ATR

    long_mask = long_signal.fillna(False)
    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "close"] - stop_dist[long_mask]
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] + target_dist[long_mask]
    df.loc[long_mask, "signal_type"] = "rev"

    short_mask = short_signal.fillna(False)
    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "close"] + stop_dist[short_mask]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - target_dist[short_mask]
    df.loc[short_mask, "signal_type"] = "rev"

    # Exit signals
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    exit_sigs = np.zeros(n, dtype=int)

    for i in range(n):
        sig = df.iloc[i]["signal"]
        low_px = df.iloc[i]["low"]
        high_px = df.iloc[i]["high"]
        time_s = _parse_time(df["datetime"].iloc[i:i+1]).iloc[0]

        if position != 0 and time_s >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        if position == 1:
            if low_px <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            elif high_px >= entry_target:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            if high_px >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            elif low_px <= entry_target:
                exit_sigs[i] = -1
                position = 0

        if position == 0 and sig != 0:
            position = sig
            entry_stop = df.iloc[i]["stop_price"]
            entry_target = df.iloc[i]["target_price"]
            if pd.isna(entry_stop) or pd.isna(entry_target):
                position = 0

    df["exit_signal"] = exit_sigs
    df.drop(columns=["_date", "_session_bar", "_bars_since_open"], inplace=True)

    return df
