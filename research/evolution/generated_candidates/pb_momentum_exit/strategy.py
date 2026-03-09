"""PB_MOMENTUM_EXIT — PB Trend + momentum deceleration exit.

Extracted from Lucid v6.3 as the validated PB module.
This is the pullback-only signal generator — no VWAP reversion logic.

Roster target: ALGO-CORE-PB-MGC-001
Primary asset: MGC (Micro Gold)
Secondary: MNQ (long-only), MES (short-only)

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np
from research.evolution.mutations import compute_momentum_state


# ── Parameters ───────────────────────────────────────────────────────────────

# Indicators
FAST_EMA = 9
SLOW_EMA = 21
TREND_EMA = 200
RSI_LEN = 14
ATR_LEN = 14

# Quality filters
ADX_LEN = 14
ADX_MIN = 14.0
VOL_MA_LEN = 20
VOL_MULT = 1.0

# Session (RTH eastern)
SESSION_START = "08:30"
SESSION_END = "15:15"
WARMUP_MINS = 15

# Power windows
WIN1_START = "08:45"
WIN1_END = "11:00"
WIN2_START = "13:30"
WIN2_END = "15:10"

# Exits (ATR multiples)
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
    """Generate PB trend-following signals from OHLCV data.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price, signal_type.
    signal_type is always "pb".
    """
    df = df.copy()
    n = len(df)

    # Indicators
    df["ema_fast"] = _ema(df["close"], FAST_EMA)
    df["ema_slow"] = _ema(df["close"], SLOW_EMA)
    df["ema_trend"] = _ema(df["close"], TREND_EMA)
    df["rsi"] = _rsi(df["close"], RSI_LEN)
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)
    df["adx"] = _adx(df["high"], df["low"], df["close"], ADX_LEN)
    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)

    # ── Evolution mutation: momentum state ──
    df = compute_momentum_state(df)

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
    warmup_bars = WARMUP_MINS // 5
    df["past_warmup"] = df["in_session"] & (df["_bars_since_open"] >= warmup_bars)

    in_win1 = (time_str >= WIN1_START) & (time_str < WIN1_END)
    in_win2 = (time_str >= WIN2_START) & (time_str < WIN2_END)
    df["in_windows"] = in_win1 | in_win2
    df["allowed"] = df["in_session"] & df["past_warmup"] & df["in_windows"]

    # Quality filters
    if has_volume:
        vol_ok = df["volume"] > df["vol_ma"] * VOL_MULT
    else:
        vol_ok = pd.Series(True, index=df.index)
    adx_ok = df["adx"] >= ADX_MIN
    quality_ok = adx_ok & vol_ok

    bar_range = df["high"] - df["low"]
    avg_range = bar_range.rolling(10).mean()
    range_ok = bar_range >= avg_range * 0.6

    # MTF filter
    df["ema_mtf"] = _ema(df["close"], 600)
    mtf_bull = df["close"] > df["ema_mtf"]
    mtf_bear = df["close"] < df["ema_mtf"]

    # Trend conditions
    trend_bull = (
        (df["ema_fast"] > df["ema_slow"]) &
        (df["close"] > df["ema_trend"]) &
        (df["close"] > df["vwap"]) &
        mtf_bull
    )
    trend_bear = (
        (df["ema_fast"] < df["ema_slow"]) &
        (df["close"] < df["ema_trend"]) &
        (df["close"] < df["vwap"]) &
        mtf_bear
    )

    # Strong close
    close_pos = np.where(bar_range > 0, (df["close"] - df["low"]) / bar_range, 0.5)
    strong_close_up = close_pos >= 0.80
    strong_close_down = close_pos <= 0.20

    # Pullback signals
    pb_long = (
        trend_bull &
        (df["low"] <= df["ema_slow"]) &
        (df["close"] > df["ema_fast"]) &
        ((df["close"] > df["high"].shift(1)) | strong_close_up) &
        range_ok
    )
    pb_short = (
        trend_bear &
        (df["high"] >= df["ema_slow"]) &
        (df["close"] < df["ema_fast"]) &
        ((df["close"] < df["low"].shift(1)) | strong_close_down) &
        range_ok
    )

    # Regime gate (trend only)
    vwap_slope = df["vwap"] - df["vwap"].shift(5)
    ema_slope = df["ema_fast"] - df["ema_fast"].shift(5)
    trend_regime = (
        (df["adx"] >= ADX_MIN) &
        (ema_slope.abs() > TICK_SIZE * 2) &
        (vwap_slope.abs() > TICK_SIZE * 2)
    )

    # Final signals
    long_signal = df["allowed"] & quality_ok & trend_regime & pb_long
    short_signal = df["allowed"] & quality_ok & trend_regime & pb_short

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
    df.loc[long_mask, "signal_type"] = "pb"

    short_mask = short_signal.fillna(False)
    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "close"] + stop_dist[short_mask]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - target_dist[short_mask]
    df.loc[short_mask, "signal_type"] = "pb"

    # Exit signals
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    exit_sigs = np.zeros(n, dtype=int)
    mom_green_arr = df['mom_green'].fillna(False).values
    mom_maroon_arr = df['mom_maroon'].fillna(False).values

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
            elif mom_green_arr[i]:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            if high_px >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            elif low_px <= entry_target:
                exit_sigs[i] = -1
                position = 0
            elif mom_maroon_arr[i]:
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
