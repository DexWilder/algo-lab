"""Gold BandWidth Squeeze -- Volatility compression to expansion on daily gold.

Trade the expansion after extreme Bollinger BandWidth compression on MGC.
Direction from close relative to midline at squeeze release.

Logic:
  - Squeeze: BandWidth < 20th percentile of 120-day range, held 5+ bars
  - Release: BandWidth expands above threshold
  - Long if close > midline at release, short if below
  - Exit: ATR trail, midline cross, or time stop

Designed for: MGC on 5-minute bars (resampled to daily internally).
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

BB_LEN = 20
BB_MULT = 2.0
BW_PERCENTILE_LOOKBACK = 120
BW_SQUEEZE_THRESHOLD = 20     # Bottom 20th percentile
MIN_SQUEEZE_BARS = 5

ATR_LEN = 20
TRAIL_ATR_MULT = 2.0
MAX_HOLD_BARS = 20            # Time stop (daily bars)

# Exit variant: "full" (trail + midline + time) or "trail_only" or "time_only"
EXIT_VARIANT = "full"

VOLUME_FILTER = False
VOLUME_MULT = 1.2

TICK_SIZE = 0.10  # MGC default


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
    if n < BW_PERCENTILE_LOOKBACK + 10:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Compute Bollinger Bands
    daily["sma"] = daily["close"].rolling(BB_LEN).mean()
    daily["std"] = daily["close"].rolling(BB_LEN).std()
    daily["upper"] = daily["sma"] + BB_MULT * daily["std"]
    daily["lower"] = daily["sma"] - BB_MULT * daily["std"]
    daily["bandwidth"] = (daily["upper"] - daily["lower"]) / daily["sma"]

    # BandWidth percentile rank over lookback
    daily["bw_pctrank"] = daily["bandwidth"].rolling(
        BW_PERCENTILE_LOOKBACK, min_periods=60
    ).apply(lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False)

    daily["atr"] = _atr(daily["high"], daily["low"], daily["close"], ATR_LEN)
    daily["vol_avg"] = daily["volume"].rolling(20, min_periods=5).mean()

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    close = daily["close"].values
    high = daily["high"].values
    low = daily["low"].values
    sma = daily["sma"].values
    bw_pct = daily["bw_pctrank"].values
    atr = daily["atr"].values
    volume = daily["volume"].values
    vol_avg = daily["vol_avg"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    best_price = 0.0
    bars_held = 0
    squeeze_count = 0   # Consecutive bars in squeeze

    for i in range(n):
        c = close[i]
        h = high[i]
        l = low[i]
        bar_sma = sma[i]
        bar_bw_pct = bw_pct[i]
        bar_atr = atr[i]
        bar_vol = volume[i]
        bar_vol_avg = vol_avg[i]

        if np.isnan(bar_atr) or np.isnan(bar_bw_pct) or bar_atr == 0:
            continue

        # Track squeeze state
        in_squeeze = bar_bw_pct <= BW_SQUEEZE_THRESHOLD
        if in_squeeze:
            squeeze_count += 1
        else:
            was_squeezing = squeeze_count >= MIN_SQUEEZE_BARS
            squeeze_count = 0

            # ---- Squeeze release: potential entry ----
            if was_squeezing and position == 0:
                # Volume filter
                if VOLUME_FILTER and bar_vol_avg > 0 and bar_vol < bar_vol_avg * VOLUME_MULT:
                    continue

                # Direction from close vs midline
                if c > bar_sma and allow_long:
                    entry_price = c
                    trailing_stop = c - bar_atr * TRAIL_ATR_MULT
                    best_price = c
                    signals[i] = 1
                    stop_arr[i] = trailing_stop
                    position = 1
                    bars_held = 0
                    continue

                if c < bar_sma and allow_short:
                    entry_price = c
                    trailing_stop = c + bar_atr * TRAIL_ATR_MULT
                    best_price = c
                    signals[i] = -1
                    stop_arr[i] = trailing_stop
                    position = -1
                    bars_held = 0
                    continue

        # ---- Manage position ----
        if position != 0:
            bars_held += 1

            if position == 1:
                if c > best_price:
                    best_price = c
                new_trail = best_price - bar_atr * TRAIL_ATR_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

                should_exit = False

                if EXIT_VARIANT in ("full", "trail_only"):
                    if l <= trailing_stop:
                        should_exit = True

                if EXIT_VARIANT == "full" and c < bar_sma and not np.isnan(bar_sma):
                    should_exit = True  # Midline cross

                if EXIT_VARIANT in ("full", "time_only"):
                    if bars_held >= MAX_HOLD_BARS:
                        should_exit = True

                if should_exit:
                    exit_sigs[i] = 1; position = 0; continue

            elif position == -1:
                if c < best_price:
                    best_price = c
                new_trail = best_price + bar_atr * TRAIL_ATR_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

                should_exit = False

                if EXIT_VARIANT in ("full", "trail_only"):
                    if h >= trailing_stop:
                        should_exit = True

                if EXIT_VARIANT == "full" and c > bar_sma and not np.isnan(bar_sma):
                    should_exit = True

                if EXIT_VARIANT in ("full", "time_only"):
                    if bars_held >= MAX_HOLD_BARS:
                        should_exit = True

                if should_exit:
                    exit_sigs[i] = -1; position = 0; continue

    daily["signal"] = signals
    daily["exit_signal"] = exit_sigs
    daily["stop_price"] = stop_arr
    daily["target_price"] = target_arr

    drop = ["sma", "std", "upper", "lower", "bandwidth", "bw_pctrank", "atr", "vol_avg"]
    daily.drop(columns=[c for c in drop if c in daily.columns], inplace=True, errors="ignore")
    return daily
