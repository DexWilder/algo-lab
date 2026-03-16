"""Rate Daily-Bar Macro Momentum -- Trend following for Treasury futures.

Rates trend well on daily+ timeframes driven by Fed policy expectations,
inflation data, and macro sentiment shifts. Unlike equities which can
gap and reverse intraday, rates trends tend to be slow, persistent,
and macro-anchored.

Key differences from FX daily trend:
  - Rates move in smaller absolute ranges but trend more persistently
  - Longer lookback for trend (100-day EMA vs 50 for FX)
  - Wider Donchian channel (30-day vs 20) to avoid whipsaw in tight ranges
  - Tighter trailing stop (1.5x ATR vs 2.0) because rates reversals are sharp
  - No ATR expansion filter (rates trend in low-vol environments too)
  - EMA trend exit disabled (rates can consolidate around EMA without reversing)

Also implements a simple time-series momentum variant:
  - If 60-day return is positive -> long bias
  - If 60-day return is negative -> short bias
  - Combined with Donchian breakout for entry timing

Designed for: ZN (10Y Note), ZB (30Y Bond), ZF (5Y Note).
Operates on resampled daily OHLCV from 5-minute data.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Trend
EMA_TREND_LEN = 100          # Slower trend EMA for rates (macro-driven)
DONCHIAN_LEN = 30             # Wider channel (rates are tighter-ranging)
TSM_LOOKBACK = 60             # Time-series momentum: 60-day return

# ATR
ATR_LEN = 20

# Risk
TRAIL_ATR_MULT = 1.5          # Tighter trail (rates reversals are sharp)
INITIAL_STOP_ATR = 2.0        # Initial stop before trail activates

# No ATR expansion filter (rates trend in low vol too)
# No EMA trend exit (rates consolidate around EMA without reversing)

# Cooldown
MIN_BARS_BETWEEN = 5          # 5 trading days

TICK_SIZE = 0.015625           # Default ZN


# ---- Helpers ----

def _resample_daily(df):
    """Resample 5m bars to daily OHLCV."""
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
    """Generate daily-bar rate momentum signals."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Detect if intraday -> resample
    if len(df) > 0:
        time_diff = df["datetime"].diff().median()
        if time_diff < pd.Timedelta(hours=1):
            daily = _resample_daily(df)
        else:
            daily = df.copy()
    else:
        return df

    n = len(daily)
    if n < EMA_TREND_LEN + 10:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Indicators
    daily["ema"] = daily["close"].ewm(span=EMA_TREND_LEN, adjust=False).mean()
    daily["atr"] = _atr(daily["high"], daily["low"], daily["close"], ATR_LEN)
    daily["donch_high"] = daily["high"].rolling(DONCHIAN_LEN, min_periods=DONCHIAN_LEN).max().shift(1)
    daily["donch_low"] = daily["low"].rolling(DONCHIAN_LEN, min_periods=DONCHIAN_LEN).min().shift(1)

    # Time-series momentum: 60-day return direction
    daily["tsm_return"] = daily["close"].pct_change(TSM_LOOKBACK)

    close = daily["close"].values
    high = daily["high"].values
    low = daily["low"].values
    ema = daily["ema"].values
    atr_vals = daily["atr"].values
    donch_h = daily["donch_high"].values
    donch_l = daily["donch_low"].values
    tsm = daily["tsm_return"].values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    initial_stop = 0.0
    trailing_stop = 0.0
    best_price = 0.0
    bars_since_trade = MIN_BARS_BETWEEN

    for i in range(n):
        c = close[i]
        h = high[i]
        l = low[i]
        bar_atr = atr_vals[i]
        bar_ema = ema[i]
        dh = donch_h[i]
        dl = donch_l[i]
        bar_tsm = tsm[i]

        if np.isnan(bar_atr) or np.isnan(bar_ema) or np.isnan(dh) or bar_atr == 0:
            bars_since_trade += 1
            continue

        # ---- Manage position ----
        if position == 1:
            if c > best_price:
                best_price = c
            new_trail = best_price - bar_atr * TRAIL_ATR_MULT
            if new_trail > trailing_stop:
                trailing_stop = new_trail
            # Use the better of initial stop and trailing stop
            active_stop = max(initial_stop, trailing_stop)
            if l <= active_stop:
                exit_sigs[i] = 1
                position = 0
                bars_since_trade = 0
                continue

        elif position == -1:
            if c < best_price:
                best_price = c
            new_trail = best_price + bar_atr * TRAIL_ATR_MULT
            if new_trail < trailing_stop:
                trailing_stop = new_trail
            active_stop = min(initial_stop, trailing_stop)
            if h >= active_stop:
                exit_sigs[i] = -1
                position = 0
                bars_since_trade = 0
                continue

        # ---- Entry (flat only) ----
        if position == 0:
            bars_since_trade += 1
            if bars_since_trade < MIN_BARS_BETWEEN:
                continue

            # TSM direction filter (skip if no clear macro direction)
            if np.isnan(bar_tsm):
                continue

            # Long: Donchian breakout + EMA above + positive TSM
            if allow_long and c > dh and c > bar_ema and bar_tsm > 0:
                entry_price = c
                initial_stop = c - bar_atr * INITIAL_STOP_ATR
                trailing_stop = initial_stop
                best_price = c
                signals[i] = 1
                stop_arr[i] = initial_stop
                position = 1
                bars_since_trade = 0
                continue

            # Short: Donchian breakout + EMA below + negative TSM
            if allow_short and c < dl and c < bar_ema and bar_tsm < 0:
                entry_price = c
                initial_stop = c + bar_atr * INITIAL_STOP_ATR
                trailing_stop = initial_stop
                best_price = c
                signals[i] = -1
                stop_arr[i] = initial_stop
                position = -1
                bars_since_trade = 0
                continue

    daily["signal"] = signals
    daily["exit_signal"] = exit_sigs
    daily["stop_price"] = stop_arr
    daily["target_price"] = target_arr

    drop_cols = ["ema", "atr", "donch_high", "donch_low", "tsm_return"]
    daily.drop(columns=[c for c in drop_cols if c in daily.columns], inplace=True, errors="ignore")
    return daily
