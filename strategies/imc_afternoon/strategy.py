"""Intraday Momentum Continuation (IMC) — Afternoon Session Strategy.

Source: Gao, Han, Li, Zhou (2018) — "Market Intraday Momentum"
Journal of Financial Economics. Predictive R-squared 1.6%.
Annualized certainty-equivalent gains of 6.02%.

Logic:
  1. At 15:30 ET, compute return from previous close to current price.
  2. If return > 0: go long (momentum continues into close).
  3. If return < 0: go short (momentum continues into close).
  4. Exit at 15:55 ET (before market close).
  5. Filter: only trade on volatile days (ATR above median).

Key insight from paper:
  - Intraday momentum is driven by informed trading + late-day hedging
  - Effect is stronger when:
    a) VIX is elevated (>20)
    b) Volume is above average
    c) Macro news released that day
  - The last 30 minutes capture ~40% of daily directional information

Adaptations for 5m micro-futures:
  - Use ATR percentile as volatility proxy instead of VIX
  - Single entry at 15:30, single exit at 15:55
  - One trade per day maximum

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

ATR_PERIOD = 14
ATR_PERCENTILE_MIN = 50     # Only trade when ATR > median (volatile days)
MIN_RETURN_THRESHOLD = 0.001  # Minimum 0.1% return to trigger (noise filter)
ATR_STOP_MULT = 2.0         # Protective stop = 2x ATR

ENTRY_TIME = "15:30"         # Entry bar
EXIT_TIME = "15:55"          # Exit before close
SESSION_START = "09:30"

TICK_SIZE = 0.25


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


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

    # Rolling ATR percentile (50-day window)
    atr_series = pd.Series(atr)
    atr_rank = atr_series.rolling(50 * 78, min_periods=100).rank(pct=True).values  # 50 days * ~78 bars

    close_arr = df["close"].values
    open_arr = df["open"].values
    dates_arr = df["_date"].values
    time_arr = time_str.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    current_date = None
    prev_day_close = 0.0
    traded_today = False

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_atr_rank = atr_rank[i] if not np.isnan(atr_rank[i]) else 0.5

        # New day
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            if current_date is not None:
                # Find the last bar of the previous day
                prev_day_close = close_arr[i - 1]
            current_date = bar_date
            traded_today = False

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # Exit at 15:55
        if position != 0 and bar_time >= EXIT_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Entry at 15:30
        if position == 0 and not traded_today and bar_time == ENTRY_TIME:
            # Volatility filter: only trade on volatile days
            if bar_atr_rank < ATR_PERCENTILE_MIN / 100.0:
                continue

            # Compute return from prev close to current price
            if prev_day_close <= 0:
                continue

            day_return = (close_arr[i] - prev_day_close) / prev_day_close

            # Minimum return threshold (filter noise)
            if abs(day_return) < MIN_RETURN_THRESHOLD:
                continue

            if day_return > 0:
                # Momentum long
                signals_arr[i] = 1
                stop_arr[i] = close_arr[i] - bar_atr * ATR_STOP_MULT
                target_arr[i] = close_arr[i] + bar_atr * 2.0
                position = 1
                traded_today = True
            elif day_return < 0:
                # Momentum short
                signals_arr[i] = -1
                stop_arr[i] = close_arr[i] + bar_atr * ATR_STOP_MULT
                target_arr[i] = close_arr[i] - bar_atr * 2.0
                position = -1
                traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
