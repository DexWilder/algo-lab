"""Volatility-Managed Equity Index — Inverse-vol position scaling.

This is a risk-transformation mechanism, not a directional timing edge.
The strategy is always long. The only variable is HOW MUCH — scaled
inversely with recent realized volatility.

Logic:
  - Resample 5m bars to daily OHLCV
  - Compute 20-day realized volatility (annualized)
  - Weight = target_vol / realized_vol, capped at [MIN_WEIGHT, MAX_WEIGHT]
  - PnL = daily_return × weight × point_value
  - Rebalance daily (weight changes as vol changes)

Source: Moreira & Muir (2017), Journal of Finance.

Designed for: MES, MNQ on daily bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

VOL_LOOKBACK = 20          # Days for realized vol estimate
TARGET_VOL = 0.15          # 15% annualized target
MIN_WEIGHT = 0.25          # Never below 25% position
MAX_WEIGHT = 2.0           # Never above 2x leverage
TICK_SIZE = 0.25           # MES default


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


# ---- Signal Generator ----

def generate_signals(df, asset=None, mode="both"):
    """Generate vol-managed equity signals on daily bars.

    This strategy is always long. The 'mode' parameter is accepted for
    interface compatibility but only 'long' and 'both' produce signals.
    'short' mode returns zero signals (strategy never shorts).

    The sizing weight is embedded in the signal output. For backtest
    purposes, PnL should be computed as:
        daily_pnl = daily_return × weight × point_value

    The 'signal' column is 1 on every day (always long). The 'weight'
    column contains the vol-managed position size (0.25 to 2.0).
    """
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
    if n < VOL_LOOKBACK + 10:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        daily["weight"] = 0.0
        return daily

    # Compute daily returns and realized vol
    daily["ret"] = daily["close"].pct_change()
    daily["realized_vol"] = daily["ret"].rolling(VOL_LOOKBACK).std() * np.sqrt(252)

    # Compute weight: target_vol / realized_vol, capped
    daily["weight"] = TARGET_VOL / daily["realized_vol"]
    daily["weight"] = daily["weight"].clip(MIN_WEIGHT, MAX_WEIGHT)
    daily["weight"] = daily["weight"].fillna(MIN_WEIGHT)

    # Compute vol-managed return for backtest
    daily["vm_return"] = daily["ret"] * daily["weight"]

    # Signal: always long (unless mode=short)
    allow_long = mode in ("long", "both")

    if allow_long:
        signals = np.ones(n, dtype=int)
        # Zero out the warmup period
        signals[:VOL_LOOKBACK + 1] = 0
    else:
        signals = np.zeros(n, dtype=int)

    daily["signal"] = signals
    daily["exit_signal"] = np.zeros(n, dtype=int)
    daily["stop_price"] = np.nan
    daily["target_price"] = np.nan

    # Clean up
    drop = ["ret", "realized_vol", "vm_return", "date"]
    daily.drop(columns=[c for c in drop if c in daily.columns],
               inplace=True, errors="ignore")

    return daily
