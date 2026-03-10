"""BB Range Reversion — Bollinger Band MR with EMA convergence filter.

Adapts BB Equilibrium for multi-asset ranging conditions.
Key change: replaces directional trend filter (EMA slope for/against)
with EMA convergence filter (EMAs close together = ranging market).

Hypothesis: BB reversion works on MES/MNQ during RANGING days but fails
during TRENDING because trends override mean reversion. EMA convergence
detects ranging conditions inline without external regime engine.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

BB_LENGTH = 20
BB_MULT = 2.0
RSI_PERIOD = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65

# Ranging filters
EMA_FAST = 9
EMA_SLOW = 21
EMA_CONVERGENCE = 1.5       # |EMA9 - EMA21| / ATR < 1.5 = ranging

BW_LOOKBACK = 100
BW_MIN_PCT = 15              # Bandwidth floor (avoid dead zones)
BW_MAX_PCT = 60              # Bandwidth ceiling (avoid expansion)

ATR_PERIOD = 14
ATR_STOP_MULT = 1.5
ATR_TRAIL_MULT = 2.0
MIN_HOLD_BARS = 3

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "09:45"
ENTRY_CUTOFF = "14:45"
FLATTEN_TIME = "15:30"

TICK_SIZE = 0.25


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _rsi(series: pd.Series, period: int) -> np.ndarray:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.values


# ── Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # Bollinger Bands
    sma = df["close"].rolling(window=BB_LENGTH, min_periods=BB_LENGTH).mean()
    std = df["close"].rolling(window=BB_LENGTH, min_periods=BB_LENGTH).std(ddof=0)
    upper_bb = sma + BB_MULT * std
    lower_bb = sma - BB_MULT * std

    # Bandwidth percentile rank
    bandwidth = ((upper_bb - lower_bb) / sma).values
    bw_series = pd.Series(bandwidth)
    bw_pctrank = bw_series.rolling(
        window=BW_LOOKBACK, min_periods=20
    ).apply(lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False).values

    # RSI
    rsi = _rsi(df["close"], RSI_PERIOD)

    # EMA convergence (ranging detection)
    ema_fast = df["close"].ewm(span=EMA_FAST, adjust=False).mean().values
    ema_slow = df["close"].ewm(span=EMA_SLOW, adjust=False).mean().values

    # ATR
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # EMA convergence ratio
    ema_conv = np.where(atr > 0, np.abs(ema_fast - ema_slow) / atr, 999.0)

    # Pre-compute arrays
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values
    sma_arr = sma.values
    upper_arr = upper_bb.values
    lower_arr = lower_bb.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    trailing_stop = 0.0
    target_price = 0.0
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
        bar_sma = sma_arr[i]
        bar_upper = upper_arr[i]
        bar_lower = lower_arr[i]
        bar_rsi = rsi[i]
        bar_bw_pct = bw_pctrank[i]
        bar_conv = ema_conv[i]

        # Day reset
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue

        if (np.isnan(bar_atr) or np.isnan(bar_sma) or np.isnan(bar_upper)
                or np.isnan(bar_lower) or np.isnan(bar_rsi)):
            continue

        # Pre-close flatten
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Exits
        if position == 1:
            bars_in_trade += 1
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            if bars_in_trade >= MIN_HOLD_BARS and high_arr[i] >= target_price:
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

            if bars_in_trade >= MIN_HOLD_BARS and low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # Entries
        if position == 0 and entry_ok_arr[i]:
            # Ranging filter: EMAs must be converging
            if bar_conv >= EMA_CONVERGENCE:
                continue
            # Bandwidth filter: not too compressed, not too wide
            if np.isnan(bar_bw_pct) or bar_bw_pct < BW_MIN_PCT or bar_bw_pct > BW_MAX_PCT:
                continue

            # Long: bounce off lower band
            if (not long_traded_today
                and low_arr[i - 1] <= lower_arr[i - 1]
                and close_arr[i] > lower_arr[i]
                and bar_rsi < RSI_OVERSOLD):

                initial_stop = close_arr[i] - bar_atr * ATR_STOP_MULT
                target = bar_sma
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = target
                position = 1
                trailing_stop = initial_stop
                target_price = target
                highest_since_entry = high_arr[i]
                long_traded_today = True
                bars_in_trade = 0

            # Short: reject from upper band
            elif (not short_traded_today
                  and high_arr[i - 1] >= upper_arr[i - 1]
                  and close_arr[i] < upper_arr[i]
                  and bar_rsi > RSI_OVERBOUGHT):

                initial_stop = close_arr[i] + bar_atr * ATR_STOP_MULT
                target = bar_sma
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = target
                position = -1
                trailing_stop = initial_stop
                target_price = target
                lowest_since_entry = low_arr[i]
                short_traded_today = True
                bars_in_trade = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
