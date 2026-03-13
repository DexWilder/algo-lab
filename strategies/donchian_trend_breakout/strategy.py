"""DONCHIAN-TREND-BREAKOUT — Long-lookback Donchian for Bond Futures.

Designed for slower-trending markets like ZN/ZB, but works on any asset.
Uses 40-bar Donchian channel (vs 30 in donchian_trend) with EMA slope
confirmation and volume filter to avoid thin breakouts.

This is a SEPARATE strategy from donchian_trend (GRINDING variant).
Key differences:
- 40-bar channel (bonds trend slower than index futures)
- 100-bar EMA slope filter (trend confirmation)
- Volume filter (0.8 × 20-bar avg)
- Profit Ladder exit (ratcheting stops at R-milestones)
- 5-bar cooldown after exit

Logic:
- Entry LONG: close > upper channel AND EMA slope rising AND volume OK
- Entry SHORT: close < lower channel AND EMA slope falling AND volume OK
- Stop: 2.0 × ATR(20) from entry
- Exit: Profit Ladder — 1R→lock 0.25R, 2R→lock 1R, 3R→lock 2R
- Session flatten at 15:30, no entries after 14:00

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

# Donchian channel
CHANNEL_LEN = 40              # Lookback bars (longer for bonds' slower trends)

# Trend confirmation
EMA_LEN = 100                 # EMA period for slope filter
EMA_SLOPE_BARS = 5            # Bars to measure EMA slope over

# Volume filter
VOL_MA_LEN = 20               # Volume moving average period
VOL_MULT = 0.8                # Min volume as fraction of MA

# ATR / Stops
ATR_PERIOD = 20               # ATR period (wider for bonds)
ATR_STOP_MULT = 2.0           # Initial stop = entry ± ATR × mult

# Profit Ladder thresholds (in R-multiples)
LADDER_1R_LOCK = 0.25         # At 1R profit, lock 0.25R
LADDER_2R_LOCK = 1.0          # At 2R profit, lock 1.0R
LADDER_3R_LOCK = 2.0          # At 3R profit, lock 2.0R

# Cooldown
COOLDOWN_BARS = 5             # Bars to wait after exit before re-entry

# Session (RTH Eastern)
SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_CUTOFF = "14:00"        # No entries after 14:00
FLATTEN_TIME = "15:30"        # Pre-close flatten

TICK_SIZE = 0.25              # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, asset=None, mode="long") -> pd.DataFrame:
    """Generate Donchian channel breakout signals with Profit Ladder exits.

    Parameters
    ----------
    df : DataFrame with columns: open, high, low, close, volume, datetime
    asset : str or None — unused here but accepted for interface compat
    mode : "long", "short", or "both" — which direction(s) to trade

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str < ENTRY_CUTOFF)

    # ── Donchian Channel (shifted by 1 to avoid look-ahead) ──────────
    high_channel = df["high"].rolling(window=CHANNEL_LEN, min_periods=CHANNEL_LEN).max().shift(1)
    low_channel = df["low"].rolling(window=CHANNEL_LEN, min_periods=CHANNEL_LEN).min().shift(1)

    # ── Trend confirmation: EMA slope ─────────────────────────────────
    ema = df["close"].ewm(span=EMA_LEN, adjust=False).mean()
    ema_slope = ema - ema.shift(EMA_SLOPE_BARS)

    # ── Volume filter ─────────────────────────────────────────────────
    has_volume = df["volume"].sum() > 0
    if has_volume:
        vol_ma = df["volume"].rolling(window=VOL_MA_LEN, min_periods=1).mean()
        vol_ok = df["volume"] > vol_ma * VOL_MULT
    else:
        vol_ok = pd.Series(True, index=df.index)

    # ── ATR for stops ─────────────────────────────────────────────────
    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)

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
    ema_slope_arr = ema_slope.values
    vol_ok_arr = vol_ok.values
    atr_arr = atr.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # ── Stateful entry/exit loop ──────────────────────────────────────
    position = 0          # 0=flat, 1=long, -1=short
    entry_price = 0.0
    risk_per_r = 0.0      # Dollar distance of 1R (always positive)
    current_stop = 0.0    # Active stop (ratchets via Profit Ladder)
    current_date = None
    long_traded_today = False
    short_traded_today = False
    bars_since_exit = COOLDOWN_BARS  # Start ready to trade
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
                bars_since_exit = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue

        # Track cooldown
        if position == 0:
            bars_since_exit += 1

        # ── Pre-close flatten ─────────────────────────────────────────
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            bars_since_exit = 0
            continue

        # ── Check exits for open position (Profit Ladder) ────────────
        if position == 1:
            # Update high-water mark
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]

            # Compute current R from high-water mark
            max_r = (highest_since_entry - entry_price) / risk_per_r if risk_per_r > 0 else 0.0

            # Ratchet stop via Profit Ladder
            if max_r >= 3.0:
                ladder_stop = entry_price + LADDER_3R_LOCK * risk_per_r
            elif max_r >= 2.0:
                ladder_stop = entry_price + LADDER_2R_LOCK * risk_per_r
            elif max_r >= 1.0:
                ladder_stop = entry_price + LADDER_1R_LOCK * risk_per_r
            else:
                ladder_stop = current_stop  # No change below 1R

            # Stop only ratchets up, never down
            if ladder_stop > current_stop:
                current_stop = ladder_stop

            # Check stop hit
            if low_arr[i] <= current_stop:
                exit_sigs[i] = 1
                position = 0
                bars_since_exit = 0

        elif position == -1:
            # Update low-water mark
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]

            # Compute current R from low-water mark
            max_r = (entry_price - lowest_since_entry) / risk_per_r if risk_per_r > 0 else 0.0

            # Ratchet stop via Profit Ladder
            if max_r >= 3.0:
                ladder_stop = entry_price - LADDER_3R_LOCK * risk_per_r
            elif max_r >= 2.0:
                ladder_stop = entry_price - LADDER_2R_LOCK * risk_per_r
            elif max_r >= 1.0:
                ladder_stop = entry_price - LADDER_1R_LOCK * risk_per_r
            else:
                ladder_stop = current_stop

            # Stop only ratchets down (lower = tighter for short)
            if ladder_stop < current_stop:
                current_stop = ladder_stop

            # Check stop hit
            if high_arr[i] >= current_stop:
                exit_sigs[i] = -1
                position = 0
                bars_since_exit = 0

        # ── Entry ─────────────────────────────────────────────────────
        if position == 0 and entry_ok_arr[i] and bars_since_exit >= COOLDOWN_BARS:
            upper = high_ch_arr[i]
            lower = low_ch_arr[i]
            slope = ema_slope_arr[i]

            if np.isnan(upper) or np.isnan(lower) or np.isnan(bar_atr) or np.isnan(slope):
                continue

            # Long breakout
            if (allow_long
                    and not long_traded_today
                    and close_arr[i] > upper
                    and slope > 0
                    and vol_ok_arr[i]):
                risk = bar_atr * ATR_STOP_MULT
                initial_stop = close_arr[i] - risk

                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = np.nan  # No fixed target — Profit Ladder exits

                position = 1
                entry_price = close_arr[i]
                risk_per_r = risk
                current_stop = initial_stop
                highest_since_entry = high_arr[i]
                long_traded_today = True

            # Short breakout
            elif (allow_short
                      and not short_traded_today
                      and close_arr[i] < lower
                      and slope < 0
                      and vol_ok_arr[i]):
                risk = bar_atr * ATR_STOP_MULT
                initial_stop = close_arr[i] + risk

                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = np.nan

                position = -1
                entry_price = close_arr[i]
                risk_per_r = risk
                current_stop = initial_stop
                lowest_since_entry = low_arr[i]
                short_traded_today = True

    # ── Write output columns ──────────────────────────────────────────
    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
