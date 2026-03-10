"""VWAP-MR-GOLD — VWAP Mean Reversion for Gold.

Gold-specific mean reversion exploiting intraday VWAP snapback behavior.
Gold's macro/hedging flows create overextension from VWAP that reliably reverts.

Logic:
- Measure: distance from session VWAP in ATR units
- Entry: price overextended from VWAP (> threshold ATR units away), then shows
  reversal bar (close moving back toward VWAP)
- Long: price far below VWAP + bullish reversal bar
- Short: price far above VWAP + bearish reversal bar
- Exit: price touches/crosses VWAP (mean reversion target)
- Stop: ATR-based (tight — reversion targets are close)
- No trades in first 30min (VWAP needs volume to stabilize)
- Max 1 trade per direction per day

Expected behavior:
- Win rate 55-65% (VWAP reversion is high probability on gold)
- Median hold 5-25 bars (quick reversion trades)
- Works best in RANGING and NORMAL_TRENDING regimes

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

ATR_PERIOD = 14
ATR_STOP_MULT = 1.5       # Tight stop for MR
ATR_TRAIL_MULT = 2.0      # Trailing stop backup
VWAP_DIST_ENTRY = 1.2     # Entry: price > 1.2 ATR from VWAP
VWAP_DIST_EXIT = 0.1      # Exit: price within 0.1 ATR of VWAP (near touch)
MIN_HOLD_BARS = 2         # Min bars before VWAP exit activates

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "10:00"     # 30min warmup for VWAP stability
ENTRY_CUTOFF = "14:45"    # MR trades are quick
FLATTEN_TIME = "15:30"

TICK_SIZE = 0.10           # Gold tick


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_session_vwap(df: pd.DataFrame) -> np.ndarray:
    """Session-anchored VWAP (resets each day)."""
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

    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

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
    entry_price = 0.0
    trailing_stop = 0.0
    target_vwap = 0.0
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

        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue
        if np.isnan(bar_atr) or np.isnan(bar_vwap) or bar_atr == 0:
            continue

        # Pre-close flatten
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Distance from VWAP in ATR units
        vwap_dist = (close_arr[i] - bar_vwap) / bar_atr

        # Exits
        if position == 1:
            bars_in_trade += 1
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Exit 1: VWAP touch (target reached)
            if bars_in_trade >= MIN_HOLD_BARS and high_arr[i] >= bar_vwap:
                exit_sigs[i] = 1
                position = 0
            # Exit 2: Stop
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

            # Exit 1: VWAP touch
            if bars_in_trade >= MIN_HOLD_BARS and low_arr[i] <= bar_vwap:
                exit_sigs[i] = -1
                position = 0
            # Exit 2: Stop
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # Entries
        if position == 0 and entry_ok_arr[i]:

            # Long: price far below VWAP + bullish reversal bar
            if (not long_traded_today
                and vwap_dist < -VWAP_DIST_ENTRY
                and close_arr[i] > open_arr[i]      # Bullish bar
                and close_arr[i] > close_arr[i-1]):  # Closing higher than prior

                initial_stop = close_arr[i] - bar_atr * ATR_STOP_MULT
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = bar_vwap
                position = 1
                entry_price = close_arr[i]
                trailing_stop = initial_stop
                target_vwap = bar_vwap
                highest_since_entry = high_arr[i]
                long_traded_today = True
                bars_in_trade = 0

            # Short: price far above VWAP + bearish reversal bar
            elif (not short_traded_today
                  and vwap_dist > VWAP_DIST_ENTRY
                  and close_arr[i] < open_arr[i]      # Bearish bar
                  and close_arr[i] < close_arr[i-1]):  # Closing lower than prior

                initial_stop = close_arr[i] + bar_atr * ATR_STOP_MULT
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = bar_vwap
                position = -1
                entry_price = close_arr[i]
                trailing_stop = initial_stop
                target_vwap = bar_vwap
                lowest_since_entry = low_arr[i]
                short_traded_today = True
                bars_in_trade = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
