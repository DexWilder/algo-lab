"""VIX_TIGHT_TARGETS — VIX Channel + ATR-based risk model.

Source: exlux — NY VIX Channel Trend US Futures Day Trade Strategy
URL: https://www.tradingview.com/script/TlOcVraF-NY-VIX-Channel-Trend-US-Futures-Day-Trade-Strategy/
Family: session (trend following)
Conversion: Adapted — uses realized volatility proxy instead of VIX data feed.

Logic:
- Compute daily implied move channel from realized volatility (ATR proxy for VIX)
- Channel anchored at session open price ± implied move
- Wait N minutes (observation window) to detect trend direction
- One trade per day in detected direction
- Exit: VIX channel boundary, TP/SL (VIX-scaled), or pre-close flatten
- TP = implied_move * TP_FACTOR, SL = implied_move * SL_FACTOR

VIX Proxy:
- VIX ≈ annualized realized volatility = ATR/close * sqrt(252) * 100
- Computed on daily close-to-close returns, 14-day rolling

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

WINDOW_MINUTES = 30        # Observation window (5-120 min)
TP_FACTOR = 1.0            # TP as multiple of implied move
SL_FACTOR = 0.5            # SL as multiple of implied move
EXIT_MINUTES_BEFORE = 30   # Flatten N minutes before session end
VOL_LOOKBACK = 14          # Days for realized vol calculation

SESSION_START = "09:30"
SESSION_END = "15:45"      # 16:00 RTH, flatten 15 min early
ENTRY_CUTOFF = "14:00"     # No entries after 14:00

TICK_SIZE = 0.25            # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _time_to_minutes(time_str: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    h, m = time_str.split(":")
    return int(h) * 60 + int(m)


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate VIX channel trend signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    # ── Compute daily OHLC for realized vol ───────────────────────────
    dates = df["_date"]
    unique_dates = dates[in_session].unique()

    # Build daily close map
    daily_close = {}
    daily_open = {}
    for d in unique_dates:
        day_mask = (dates == d) & in_session
        day_bars = df[day_mask]
        if day_bars.empty:
            continue
        daily_open[d] = day_bars.iloc[0]["open"]
        daily_close[d] = day_bars.iloc[-1]["close"]

    # Compute rolling realized volatility (VIX proxy)
    # RV = stdev(daily returns) * sqrt(252) * 100
    date_list = sorted(daily_close.keys())
    close_series = pd.Series({d: daily_close[d] for d in date_list})
    daily_returns = close_series.pct_change()
    rolling_rv = daily_returns.rolling(window=VOL_LOOKBACK, min_periods=5).std() * np.sqrt(252) * 100

    # Compute per-day implied move
    # implied_move = session_open * (rv / sqrt(252)) / 100
    day_implied_move = {}
    day_channel_top = {}
    day_channel_bottom = {}

    for d in date_list:
        if d not in daily_open or pd.isna(rolling_rv.get(d)):
            continue
        rv = rolling_rv[d]
        if pd.isna(rv) or rv <= 0:
            continue
        anchor = daily_open[d]
        one_sigma_pct = (rv / np.sqrt(252)) / 100
        implied_move = anchor * one_sigma_pct
        day_implied_move[d] = implied_move
        day_channel_top[d] = anchor + implied_move
        day_channel_bottom[d] = anchor - implied_move

    # ── Determine window end time ─────────────────────────────────────
    session_start_min = _time_to_minutes(SESSION_START)
    window_end_min = session_start_min + WINDOW_MINUTES
    window_end_time = f"{window_end_min // 60:02d}:{window_end_min % 60:02d}"

    flatten_min = _time_to_minutes(SESSION_END) - EXIT_MINUTES_BEFORE
    flatten_time = f"{flatten_min // 60:02d}:{flatten_min % 60:02d}"

    # ── ATR risk model (mutation) ──
    _prev_close = df['close'].shift(1)
    _tr = pd.concat([df['high'] - df['low'], (df['high'] - _prev_close).abs(), (df['low'] - _prev_close).abs()], axis=1).max(axis=1)
    _atr = _tr.ewm(span=14, adjust=False).mean()
    atr_arr = _atr.values

    # ── Stateful entry/exit loop ──────────────────────────────────────
    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values

    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    current_date = None
    direction_decided = False
    day_direction = 0
    traded_today = False
    channel_top = 0.0
    channel_bottom = 0.0

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]

        # ── Day reset ─────────────────────────────────────────────────
        if bar_date != current_date:
            # Force close from previous day
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            direction_decided = False
            day_direction = 0
            traded_today = False
            channel_top = day_channel_top.get(bar_date, 0.0)
            channel_bottom = day_channel_bottom.get(bar_date, 0.0)

        if not in_session_arr[i]:
            continue

        # ── Pre-close flatten ─────────────────────────────────────────
        if position != 0 and bar_time >= flatten_time:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # ── Check exits for open position ─────────────────────────────
        if position == 1:
            # Stop
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            # Target
            elif high_arr[i] >= entry_target:
                exit_sigs[i] = 1
                position = 0
            # Channel boundary
            elif channel_top > 0 and high_arr[i] >= channel_top:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            if high_arr[i] >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            elif low_arr[i] <= entry_target:
                exit_sigs[i] = -1
                position = 0
            elif channel_bottom > 0 and low_arr[i] <= channel_bottom:
                exit_sigs[i] = -1
                position = 0

        # ── Window direction detection ────────────────────────────────
        if not direction_decided and bar_time >= window_end_time:
            anchor = daily_open.get(bar_date)
            if anchor is not None:
                if close_arr[i] > anchor:
                    day_direction = 1
                elif close_arr[i] < anchor:
                    day_direction = -1
                else:
                    day_direction = 0
                direction_decided = True

        # ── Entry ─────────────────────────────────────────────────────
        if (position == 0 and direction_decided and day_direction != 0
                and not traded_today and bar_time < ENTRY_CUTOFF):
            implied_move = day_implied_move.get(bar_date, 0.0)
            if implied_move <= 0:
                continue

            _bar_atr = atr_arr[i] if not np.isnan(atr_arr[i]) else implied_move * SL_FACTOR
            tp_dist = _bar_atr * 1.0
            sl_dist = _bar_atr * 1.0

            if day_direction == 1:
                signals_arr[i] = 1
                stop_arr[i] = close_arr[i] - sl_dist
                target_arr[i] = close_arr[i] + tp_dist
                position = 1
                entry_stop = close_arr[i] - sl_dist
                entry_target = close_arr[i] + tp_dist
                traded_today = True
            elif day_direction == -1:
                signals_arr[i] = -1
                stop_arr[i] = close_arr[i] + sl_dist
                target_arr[i] = close_arr[i] - tp_dist
                position = -1
                entry_stop = close_arr[i] + sl_dist
                entry_target = close_arr[i] - tp_dist
                traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
