"""Noise-Boundary Breakout — MES Long-Side Focus.

Source: Zarattini, Aziz, Barbon (2024) — Swiss Finance Institute
"Beat the Market: An Effective Intraday Momentum Strategy for S&P 500 ETF"
Sharpe 1.33, 19.6% annualized (2007-2024), 1,985% total return.

Logic:
  1. Compute noise boundary = Open * (1 +/- avg absolute intraday return
     over last N days, scaled to time-of-day fraction).
  2. Adjust boundaries for overnight gap:
     - Gap-down widens upper boundary (mean-reversion tendency)
     - Gap-up widens lower boundary
  3. If price breaks above upper boundary: enter long.
  4. Trailing stop: exit if price crosses below session VWAP.
  5. Flat at close (all positions liquidated EOD).

Adaptations for 5m micro-futures:
  - Entry checks at each 5m bar (not just on the hour)
  - ATR-based stop as backstop to VWAP trail
  - One trade per day maximum

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

LOOKBACK_DAYS = 14          # Days to compute avg absolute intraday return
ATR_PERIOD = 14             # ATR for backstop stop
ATR_STOP_MULT = 3.0         # Wide backstop (VWAP trail is primary exit)
GAP_ADJUSTMENT = 0.5        # How much gap adjusts the noise boundary

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "09:45"       # Wait 15min for opening volatility
ENTRY_CUTOFF = "14:30"      # No new entries after 14:30
FLATTEN_TIME = "15:30"      # EOD flatten

TICK_SIZE = 0.25


# ── Helpers ──────────────────────────────────────────────────────────────────

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


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ATR
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # Session VWAP
    vwap = _compute_session_vwap(df)

    # Pre-compute daily OHLC for noise boundary calculation
    close_arr = df["close"].values
    open_arr = df["open"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    dates_arr = df["_date"].values
    time_arr = time_str.values

    # Compute daily absolute intraday returns for noise boundary
    # We need: for each day, the avg abs(high - low) / open over last N days
    daily_ranges = {}
    current_date = None
    day_open = 0.0
    day_high = -999999.0
    day_low = 999999.0

    for i in range(n):
        if dates_arr[i] != current_date:
            if current_date is not None and day_open > 0:
                daily_ranges[current_date] = (day_high - day_low) / day_open
            current_date = dates_arr[i]
            day_open = open_arr[i]
            day_high = high_arr[i]
            day_low = low_arr[i]
        else:
            if high_arr[i] > day_high:
                day_high = high_arr[i]
            if low_arr[i] < day_low:
                day_low = low_arr[i]

    if current_date is not None and day_open > 0:
        daily_ranges[current_date] = (day_high - day_low) / day_open

    # Sort dates for lookback
    sorted_dates = sorted(daily_ranges.keys())

    # Build avg absolute return per date (rolling lookback)
    avg_abs_return = {}
    for idx, d in enumerate(sorted_dates):
        start = max(0, idx - LOOKBACK_DAYS)
        window = [daily_ranges[sorted_dates[j]] for j in range(start, idx)]
        avg_abs_return[d] = np.mean(window) if window else 0.01  # Default 1%

    # Track session progress (time-of-day fraction for boundary scaling)
    # RTH = 09:30-16:00 = 390 minutes
    RTH_MINUTES = 390.0

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    trailing_stop = 0.0
    entry_price = 0.0
    traded_today = False
    current_date_track = None
    session_open_price = 0.0
    prev_day_close = 0.0

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_vwap = vwap[i]

        # New day reset
        if bar_date != current_date_track:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            if current_date_track is not None:
                prev_day_close = close_arr[i - 1]
            current_date_track = bar_date
            traded_today = False
            session_open_price = open_arr[i]

        # Session filter
        if bar_time < SESSION_START or bar_time >= SESSION_END:
            continue
        if np.isnan(bar_atr) or bar_atr == 0 or np.isnan(bar_vwap):
            continue

        # EOD flatten
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Exit logic: VWAP trail + ATR backstop
        if position == 1:
            # VWAP trail: exit if close drops below VWAP
            if close_arr[i] < bar_vwap:
                exit_sigs[i] = 1
                position = 0
                continue

            # ATR backstop
            if low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0
                continue

            # Update trailing stop (ratchet up)
            new_trail = high_arr[i] - bar_atr * ATR_STOP_MULT
            if new_trail > trailing_stop:
                trailing_stop = new_trail

        # Entry logic (long only for MES)
        if position == 0 and not traded_today and bar_time >= ENTRY_START and bar_time < ENTRY_CUTOFF:
            # Compute noise boundary
            avg_ret = avg_abs_return.get(bar_date, 0.01)

            # Time-of-day scaling: boundary widens as day progresses
            # Parse time to minutes since 09:30
            h, m = int(bar_time[:2]), int(bar_time[3:])
            minutes_since_open = (h - 9) * 60 + m - 30
            tod_fraction = max(0.1, min(1.0, minutes_since_open / RTH_MINUTES))

            # Noise boundary scaled by time-of-day
            boundary_width = avg_ret * np.sqrt(tod_fraction)

            # Gap adjustment
            if prev_day_close > 0 and session_open_price > 0:
                gap = (session_open_price - prev_day_close) / prev_day_close
                # Gap-down widens upper boundary (mean reversion)
                if gap < 0:
                    boundary_width *= (1.0 + abs(gap) * GAP_ADJUSTMENT * 10)

            upper_boundary = session_open_price * (1.0 + boundary_width)

            # Long entry: close breaks above upper noise boundary
            if close_arr[i] > upper_boundary and close_arr[i] > bar_vwap:
                signals_arr[i] = 1
                entry_price = close_arr[i]
                trailing_stop = entry_price - bar_atr * ATR_STOP_MULT
                stop_arr[i] = trailing_stop
                target_arr[i] = entry_price + bar_atr * 4.0  # Wide target
                position = 1
                traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
