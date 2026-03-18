"""Treasury Time-Series Momentum -- Macro momentum on rate futures.

12-month (or 6-month) trailing return determines direction.
Monthly rebalance. The simplest possible rates macro strategy.

Logic:
  - Compute trailing N-day return on daily bars
  - Positive return → long. Negative return → short.
  - Rebalance on last trading day of each month
  - Hold until next rebalance (no intra-month trading)
  - Optional ATR stop

Designed for: ZN, ZF, ZB on 5-minute bars (resampled to daily).
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

LOOKBACK_DAYS = 252          # 12-month (toggle to 126 for 6-month)

USE_STOP = False
ATR_LEN = 20
SL_ATR_MULT = 2.0

TICK_SIZE = 0.015625  # ZN default


# ---- Helpers ----

def _resample_daily(df):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    daily = df.groupby("date").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).reset_index()
    daily["datetime"] = pd.to_datetime(daily["date"])
    return daily


def _atr(high, low, close, period):
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ---- Signal Generator ----

def generate_signals(df, asset=None, mode="both"):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Resample to daily if intraday
    if len(df) > 0:
        time_diff = df["datetime"].diff().median()
        if time_diff < pd.Timedelta(hours=1):
            daily = _resample_daily(df)
        else:
            daily = df.copy()
    else:
        return df

    n = len(daily)
    if n < LOOKBACK_DAYS + 30:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Compute indicators
    daily["atr"] = _atr(daily["high"], daily["low"], daily["close"], ATR_LEN)
    daily["trailing_return"] = daily["close"].pct_change(LOOKBACK_DAYS)

    # Identify last trading day of each month for rebalance
    daily["year_month"] = daily["datetime"].dt.to_period("M")
    daily["is_month_end"] = daily["year_month"] != daily["year_month"].shift(-1)

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    close = daily["close"].values
    high = daily["high"].values
    low = daily["low"].values
    atr = daily["atr"].values
    trailing_ret = daily["trailing_return"].values
    is_rebal = daily["is_month_end"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    stop_price = 0.0

    for i in range(n):
        c = close[i]
        h = high[i]
        l = low[i]
        bar_atr = atr[i]
        ret = trailing_ret[i]
        rebal = is_rebal[i]

        if np.isnan(bar_atr) or np.isnan(ret) or bar_atr == 0:
            continue

        # ---- Stop check (if enabled, any day) ----
        if position != 0 and USE_STOP:
            if position == 1 and l <= stop_price:
                exit_sigs[i] = 1; position = 0; continue
            elif position == -1 and h >= stop_price:
                exit_sigs[i] = -1; position = 0; continue

        # ---- Rebalance day: evaluate signal ----
        if rebal:
            new_direction = 0
            if ret > 0 and allow_long:
                new_direction = 1
            elif ret < 0 and allow_short:
                new_direction = -1

            # If position needs to change
            if position != new_direction:
                # Exit current
                if position != 0:
                    exit_sigs[i] = position
                    position = 0

                # Enter new (on rebalance bar itself for daily strategies)
                if new_direction != 0:
                    entry_price = c
                    if new_direction == 1:
                        stop_price = c - bar_atr * SL_ATR_MULT if USE_STOP else 0
                        signals[i] = 1
                    else:
                        stop_price = c + bar_atr * SL_ATR_MULT if USE_STOP else 0
                        signals[i] = -1
                    stop_arr[i] = stop_price if USE_STOP else np.nan
                    position = new_direction

    daily["signal"] = signals
    daily["exit_signal"] = exit_sigs
    daily["stop_price"] = stop_arr
    daily["target_price"] = target_arr

    drop = ["atr", "trailing_return", "year_month", "is_month_end"]
    daily.drop(columns=[c for c in drop if c in daily.columns], inplace=True, errors="ignore")
    return daily
