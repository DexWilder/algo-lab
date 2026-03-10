"""KELTNER-CHANNEL — Keltner Channel Breakout + EMA Reversion Exit.

Hand-built for Phase 10 — targets HIGH_VOL_TRENDING_LOW_RV regime.
Designed for sustained directional grinds (GRINDING persistence).

Logic:
- Entry: close breaks above upper KC (EMA + ATR*mult) for long,
         close breaks below lower KC (EMA - ATR*mult) for short
- Exit primary: close crosses back below EMA (long) or above EMA (short)
- Exit safety: ATR trailing stop as protection against sharp reversals
- Pre-close session flatten
- Max 1 trade per direction per day

Differences from Donchian:
- Smoother channel (EMA-based vs N-bar high/low)
- EMA reversion exit captures profit before trailing stop
- Should produce more trades and smoother equity curve
- Better for sustained trends where price rides above/below EMA

Expected behavior:
- Win rate 35-50% (slightly higher than Donchian due to EMA exit)
- Median hold time 30-100+ bars (trend-following DNA)
- Profits concentrated on GRINDING days

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

KC_EMA_LEN = 20           # Keltner Channel EMA period (entry)
KC_ATR_LEN = 14           # ATR period for channel width
KC_MULT = 2.0             # Channel width = EMA ± ATR × mult
EXIT_EMA_LEN = 50         # Slower EMA for exit — prevents premature exit on 5m bars
ATR_TRAIL_MULT = 3.0      # Safety trailing stop = ATR × mult
MIN_HOLD_BARS = 10        # Minimum hold before EMA exit active

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
    """Generate Keltner Channel breakout signals with EMA reversion + ATR trail.

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

    # ── Keltner Channel ──────────────────────────────────────────────
    # EMA of close
    ema = df["close"].ewm(span=KC_EMA_LEN, adjust=False).mean()

    # ATR for channel width
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=KC_ATR_LEN, adjust=False).mean()

    # Channel bands (shift by 1 to avoid look-ahead)
    upper_kc = (ema + atr * KC_MULT).shift(1)
    lower_kc = (ema - atr * KC_MULT).shift(1)

    # Slower EMA for exit — prevents premature exit on 5m bars
    exit_ema = df["close"].ewm(span=EXIT_EMA_LEN, adjust=False).mean()
    exit_ema_arr = exit_ema.values

    # ── Pre-compute arrays for stateful loop ──────────────────────────
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values
    upper_kc_arr = upper_kc.values
    lower_kc_arr = lower_kc.values
    ema_exit_arr = exit_ema_arr
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
    bars_in_trade = 0

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr_arr[i]

        # ── Day reset ─────────────────────────────────────────────────
        if bar_date != current_date:
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
            bars_in_trade += 1

            # Update highest since entry for trailing stop
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Exit 1: EMA reversion — close crosses below slow exit EMA
            if bars_in_trade >= MIN_HOLD_BARS and close_arr[i] < ema_exit_arr[i]:
                exit_sigs[i] = 1
                position = 0

            # Exit 2: Safety trailing stop hit
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            bars_in_trade += 1

            # Update lowest since entry for trailing stop
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]
                new_trail = lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            # Exit 1: EMA reversion — close crosses above slow exit EMA
            if bars_in_trade >= MIN_HOLD_BARS and close_arr[i] > ema_exit_arr[i]:
                exit_sigs[i] = -1
                position = 0

            # Exit 2: Safety trailing stop hit
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # ── Entry ─────────────────────────────────────────────────────
        if position == 0 and entry_ok_arr[i]:
            upper = upper_kc_arr[i]
            lower = lower_kc_arr[i]

            if np.isnan(upper) or np.isnan(lower) or np.isnan(bar_atr):
                continue

            # Long breakout: close breaks above upper KC
            if not long_traded_today and close_arr[i] > upper:
                initial_stop = close_arr[i] - bar_atr * ATR_TRAIL_MULT
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = np.nan  # No fixed target — EMA exit + trail
                position = 1
                entry_price = close_arr[i]
                trailing_stop = initial_stop
                highest_since_entry = high_arr[i]
                long_traded_today = True
                bars_in_trade = 0

            # Short breakout: close breaks below lower KC
            elif not short_traded_today and close_arr[i] < lower:
                initial_stop = close_arr[i] + bar_atr * ATR_TRAIL_MULT
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = np.nan
                position = -1
                entry_price = close_arr[i]
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
