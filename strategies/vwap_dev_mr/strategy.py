"""VWAP Deviation Reversion — Session VWAP mean reversion with ADX ranging filter.

Fades price overextension from session VWAP during ranging (low ADX) conditions.

Key differences from failed RVWAP-MR:
- Session VWAP (daily reset) instead of rolling VWAP
- ADX < 25 inline ranging filter
- Reversal bar confirmation (not just band touch)
- Time window filter (skip first/last 30 min)

Expected behavior:
- Win rate 55-65%, median hold 5-20 bars
- Active during LOW_VOL_RANGING and NORMAL_RANGING regimes
- Near-zero correlation with existing trend/momentum parents

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

ATR_PERIOD = 14
ADX_PERIOD = 14
ADX_THRESHOLD = 25          # Only trade when ADX < 25 (ranging)

DEVIATION_MULT = 1.5        # Entry: price > 1.5 ATR from VWAP
ATR_STOP_MULT = 1.5         # Tight stop for MR
ATR_TRAIL_MULT = 2.0        # Trailing stop backup
MIN_HOLD_BARS = 2           # Quick MR

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "10:00"       # 30 min VWAP warmup
ENTRY_CUTOFF = "14:30"
FLATTEN_TIME = "15:30"

TICK_SIZE = 0.25


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_session_vwap(df: pd.DataFrame) -> np.ndarray:
    """Session-anchored VWAP (resets each day)."""
    dt = pd.to_datetime(df["datetime"])
    dates = dt.dt.date.values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
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


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


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


# ── Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    vwap = _compute_session_vwap(df)
    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD).values
    adx = _adx(df["high"], df["low"], df["close"], ADX_PERIOD).values

    close_arr = df["close"].values
    open_arr = df["open"].values
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

    position = 0
    trailing_stop = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    bars_in_trade = 0

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_vwap = vwap[i]
        bar_adx = adx[i]

        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue
        if np.isnan(bar_atr) or np.isnan(bar_vwap) or bar_atr == 0 or np.isnan(bar_adx):
            continue

        # Pre-close flatten
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        vwap_dist = (close_arr[i] - bar_vwap) / bar_atr

        # Exits
        if position == 1:
            bars_in_trade += 1
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            if bars_in_trade >= MIN_HOLD_BARS and high_arr[i] >= bar_vwap:
                exit_sigs[i] = 1
                position = 0
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            bars_in_trade += 1
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]
                new_trail = lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            if bars_in_trade >= MIN_HOLD_BARS and low_arr[i] <= bar_vwap:
                exit_sigs[i] = -1
                position = 0
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # Entries
        if position == 0 and entry_ok_arr[i] and bar_adx < ADX_THRESHOLD:
            # Long: price far below VWAP + bullish reversal bar
            if (not long_traded_today
                and vwap_dist < -DEVIATION_MULT
                and close_arr[i] > open_arr[i]
                and close_arr[i] > close_arr[i-1]):

                initial_stop = close_arr[i] - bar_atr * ATR_STOP_MULT
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = bar_vwap
                position = 1
                trailing_stop = initial_stop
                highest_since_entry = high_arr[i]
                long_traded_today = True
                bars_in_trade = 0

            # Short: price far above VWAP + bearish reversal bar
            elif (not short_traded_today
                  and vwap_dist > DEVIATION_MULT
                  and close_arr[i] < open_arr[i]
                  and close_arr[i] < close_arr[i-1]):

                initial_stop = close_arr[i] + bar_atr * ATR_STOP_MULT
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = bar_vwap
                position = -1
                trailing_stop = initial_stop
                lowest_since_entry = low_arr[i]
                short_traded_today = True
                bars_in_trade = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
