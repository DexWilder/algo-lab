"""DONCHIAN-TREND — Donchian Channel Breakout + ATR Trailing Stop.

Hand-built for Phase 10 — targets HIGH_VOL_TRENDING_LOW_RV regime.
Designed for sustained directional grinds (GRINDING persistence).

Logic:
- Entry: close breaks above N-bar high (long) or below N-bar low (short)
- Stop: ATR-based initial stop, trails with price using ATR distance
- No fixed target — trail captures full trend move
- Exit: trailing stop hit, or pre-close session flatten
- Max 1 trade per direction per day

Expected behavior:
- Low win rate (30-45%), large average winners
- Median hold time 60-200+ bars (trend-following DNA)
- Profits concentrated on GRINDING days

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

CHANNEL_LEN = 30          # Donchian channel lookback (2.5 hrs on 5m)
ATR_PERIOD = 14           # ATR period for stop calculation
ATR_STOP_MULT = 2.5       # Initial stop = entry ± ATR × mult
ATR_TRAIL_MULT = 3.0      # Trailing stop distance = ATR × mult
MIN_CHANNEL_WIDTH = 0.0   # Min channel width (0 = no filter)

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_CUTOFF = "14:00"    # No entries after 14:00 (need room for trend)
FLATTEN_TIME = "15:30"    # Pre-close flatten

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate Donchian channel breakout signals with ATR trailing stops.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= SESSION_START) & (time_str < ENTRY_CUTOFF)

    # ── Donchian Channel ──────────────────────────────────────────────
    # Use session bars only for channel computation to avoid overnight gaps
    high_channel = df["high"].rolling(window=CHANNEL_LEN, min_periods=CHANNEL_LEN).max()
    low_channel = df["low"].rolling(window=CHANNEL_LEN, min_periods=CHANNEL_LEN).min()
    channel_width = high_channel - low_channel

    # Shift by 1 to avoid look-ahead — channel based on prior bars
    high_channel = high_channel.shift(1)
    low_channel = low_channel.shift(1)
    channel_width = channel_width.shift(1)

    # ── ATR for stops ─────────────────────────────────────────────────
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (low_channel - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean()

    # ── Pre-compute arrays for stateful loop ──────────────────────────
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values
    high_ch_arr = high_channel.values
    low_ch_arr = low_channel.values
    atr_arr = atr.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # ── Stateful entry/exit loop ──────────────────────────────────────
    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    highest_since_entry = 0.0
    lowest_since_entry = 0.0

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr_arr[i]

        # ── Day reset ─────────────────────────────────────────────────
        if bar_date != current_date:
            # Force close any open position from previous day
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue

        # ── Pre-close flatten ─────────────────────────────────────────
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # ── Check exits for open position ─────────────────────────────
        if position == 1:
            # Update highest since entry for trailing stop
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                # Trail the stop up
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Check trailing stop hit
            if low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            # Update lowest since entry for trailing stop
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]
                # Trail the stop down
                new_trail = lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            # Check trailing stop hit
            if high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # ── Entry ─────────────────────────────────────────────────────
        if position == 0 and entry_ok_arr[i]:
            upper = high_ch_arr[i]
            lower = low_ch_arr[i]

            if np.isnan(upper) or np.isnan(lower) or np.isnan(bar_atr):
                continue

            # Long breakout: close breaks above channel high
            if not long_traded_today and close_arr[i] > upper:
                initial_stop = close_arr[i] - bar_atr * ATR_STOP_MULT
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = np.nan  # No fixed target — trail exits
                position = 1
                entry_price = close_arr[i]
                trailing_stop = initial_stop
                highest_since_entry = high_arr[i]
                long_traded_today = True

            # Short breakout: close breaks below channel low
            elif not short_traded_today and close_arr[i] < lower:
                initial_stop = close_arr[i] + bar_atr * ATR_STOP_MULT
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = np.nan  # No fixed target — trail exits
                position = -1
                entry_price = close_arr[i]
                trailing_stop = initial_stop
                lowest_since_entry = low_arr[i]
                short_traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
