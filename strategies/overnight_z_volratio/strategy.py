"""Overnight Z-VolRatio Open-Drive — Volatility-conditioned overnight continuation.

Tests whether a z-score filter on overnight range + volume ratio filter
on opening participation transforms the marginal overnight drift signal
(PF ~1.09 unconditional) into a tradeable edge.

Logic:
  - Compute overnight range (18:00-09:25 ET) and direction
  - Z-score = (today's range - 20d mean) / 20d std
  - Volume ratio = first-15m RTH volume / 20d mean of same
  - Entry at 09:45 ET IF z > threshold AND vol_ratio > threshold
  - Direction follows overnight tilt (long if up, short if down)
  - Exit at 11:00 ET or stop at 1.5x ATR

Supports 4 decomposition variants via module-level flags:
  USE_Z_FILTER = True/False
  USE_VOL_FILTER = True/False
Set both False for unconditional baseline (Variant A).

Designed for: MES, MNQ on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

Z_THRESHOLD = 1.5           # Overnight range z-score threshold
VOL_THRESHOLD = 1.2         # Opening volume ratio threshold
OVERNIGHT_LOOKBACK = 20     # Days for z-score and volume baselines
ATR_LEN = 20                # For stop calculation
SL_ATR_MULT = 1.5           # Stop distance in ATR multiples

TICK_SIZE = 0.25             # MES default, overridden by runner

# Session times (ET — data is assumed ET-aligned)
OVERNIGHT_START_HOUR = 18   # Prior day 18:00
OVERNIGHT_END_HOUR = 9
OVERNIGHT_END_MINUTE = 25   # 09:25 — last bar before RTH
ENTRY_HOUR = 9
ENTRY_MINUTE = 45           # 09:45 — entry bar
EXIT_HOUR = 11
EXIT_MINUTE = 0             # 11:00 — fixed time exit

# Volume confirmation window: 09:30, 09:35, 09:40 (3 bars × 5m)
VOL_WINDOW_START_HOUR = 9
VOL_WINDOW_START_MINUTE = 30
VOL_WINDOW_END_HOUR = 9
VOL_WINDOW_END_MINUTE = 40  # inclusive (09:40 bar)

# Decomposition flags — toggle to run variants A/B/C/D
USE_Z_FILTER = True          # Variant B/D: z-score filter active
USE_VOL_FILTER = True        # Variant C/D: volume ratio filter active


# ---- Helpers ----

def _compute_atr(highs, lows, closes, period=20):
    """True Range → ATR."""
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _build_daily_sessions(df):
    """Build per-trading-day overnight and opening session summaries.

    Returns a DataFrame indexed by trading date with columns:
        overnight_range, overnight_dir, overnight_high, overnight_low,
        opening_volume, daily_atr
    """
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute

    # Assign each bar to a trading date.
    # Bars from 18:00 onward belong to the NEXT trading date.
    # Bars from 00:00-17:59 belong to the current calendar date.
    df["cal_date"] = df["datetime"].dt.date
    df["trading_date"] = df["cal_date"]
    mask_evening = df["hour"] >= OVERNIGHT_START_HOUR
    df.loc[mask_evening, "trading_date"] = (
        pd.to_datetime(df.loc[mask_evening, "cal_date"]) + pd.Timedelta(days=1)
    ).dt.date

    records = []
    for tdate, grp in df.groupby("trading_date"):
        # Overnight: 18:00 prior day through 09:25 current day
        overnight = grp[
            (grp["hour"] < OVERNIGHT_END_HOUR) |
            ((grp["hour"] == OVERNIGHT_END_HOUR) & (grp["minute"] <= OVERNIGHT_END_MINUTE)) |
            (grp["hour"] >= OVERNIGHT_START_HOUR)
        ]

        if overnight.empty or len(overnight) < 5:
            continue

        on_high = overnight["high"].max()
        on_low = overnight["low"].min()
        on_range = on_high - on_low

        # Direction: close of last overnight bar vs open of first overnight bar
        on_open = overnight.iloc[0]["open"]
        on_close = overnight.iloc[-1]["close"]
        if on_close > on_open:
            on_dir = 1
        elif on_close < on_open:
            on_dir = -1
        else:
            on_dir = 0

        # Opening volume: 09:30 through 09:40 (3 bars)
        vol_window = grp[
            (grp["hour"] == VOL_WINDOW_START_HOUR) &
            (grp["minute"] >= VOL_WINDOW_START_MINUTE) &
            (grp["minute"] <= VOL_WINDOW_END_MINUTE)
        ]
        opening_vol = vol_window["volume"].sum() if not vol_window.empty else 0

        # Entry bar (09:45)
        entry_bar = grp[
            (grp["hour"] == ENTRY_HOUR) & (grp["minute"] == ENTRY_MINUTE)
        ]
        entry_price = entry_bar.iloc[0]["open"] if not entry_bar.empty else np.nan

        # Exit bar (11:00 — use open of 11:00 bar as exit price)
        exit_bar = grp[
            (grp["hour"] == EXIT_HOUR) & (grp["minute"] == EXIT_MINUTE)
        ]
        exit_price = exit_bar.iloc[0]["open"] if not exit_bar.empty else np.nan

        # Session high/low for ATR (full RTH: 09:30-16:00)
        rth = grp[(grp["hour"] >= 9) & (grp["hour"] < 16)]
        rth_high = rth["high"].max() if not rth.empty else np.nan
        rth_low = rth["low"].min() if not rth.empty else np.nan
        rth_close = rth.iloc[-1]["close"] if not rth.empty else np.nan

        records.append({
            "trading_date": tdate,
            "overnight_range": on_range,
            "overnight_dir": on_dir,
            "overnight_high": on_high,
            "overnight_low": on_low,
            "opening_volume": opening_vol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "rth_high": rth_high,
            "rth_low": rth_low,
            "rth_close": rth_close,
        })

    daily = pd.DataFrame(records)
    if daily.empty:
        return daily

    daily["trading_date"] = pd.to_datetime(daily["trading_date"])
    daily = daily.sort_values("trading_date").reset_index(drop=True)

    # Compute rolling stats
    daily["on_range_mean"] = daily["overnight_range"].rolling(
        OVERNIGHT_LOOKBACK, min_periods=OVERNIGHT_LOOKBACK
    ).mean()
    daily["on_range_std"] = daily["overnight_range"].rolling(
        OVERNIGHT_LOOKBACK, min_periods=OVERNIGHT_LOOKBACK
    ).std()
    daily["overnight_z"] = (
        (daily["overnight_range"] - daily["on_range_mean"]) / daily["on_range_std"]
    )

    daily["vol_mean"] = daily["opening_volume"].rolling(
        OVERNIGHT_LOOKBACK, min_periods=OVERNIGHT_LOOKBACK
    ).mean()
    daily["volume_ratio"] = daily["opening_volume"] / daily["vol_mean"]

    # ATR from daily RTH bars
    daily["atr"] = _compute_atr(
        daily["rth_high"], daily["rth_low"], daily["rth_close"], ATR_LEN
    )

    return daily


# ---- Signal Generator (standard interface) ----

def generate_signals(df, mode="both"):
    """Generate signals on 5-minute OHLCV data.

    Returns a daily-resampled DataFrame with signal/exit_signal columns.
    The backtest engine handles the fill-at-next-open logic.

    Parameters
    ----------
    df : DataFrame with columns [datetime, open, high, low, close, volume]
    mode : "both", "long", or "short"
    """
    daily = _build_daily_sessions(df)

    if daily.empty:
        out = pd.DataFrame({
            "datetime": pd.Series(dtype="datetime64[ns]"),
            "open": pd.Series(dtype=float),
            "high": pd.Series(dtype=float),
            "low": pd.Series(dtype=float),
            "close": pd.Series(dtype=float),
            "volume": pd.Series(dtype=float),
            "signal": pd.Series(dtype=int),
            "exit_signal": pd.Series(dtype=int),
            "stop_price": pd.Series(dtype=float),
            "target_price": pd.Series(dtype=float),
        })
        return out

    n = len(daily)
    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)
    stop_prices = np.full(n, np.nan)
    target_prices = np.full(n, np.nan)

    position = 0  # 0 = flat, 1 = long, -1 = short

    for i in range(OVERNIGHT_LOOKBACK + 1, n):
        row = daily.iloc[i]

        # Skip if missing data
        if np.isnan(row["entry_price"]) or np.isnan(row["exit_price"]):
            continue
        if np.isnan(row["atr"]) or row["atr"] <= 0:
            continue
        if row["overnight_dir"] == 0:
            continue

        # Exit any open position (each trade is intraday, 1 day max)
        if position != 0:
            exit_signals[i] = position
            position = 0

        # Check filters
        z_pass = True
        vol_pass = True

        if USE_Z_FILTER:
            if np.isnan(row["overnight_z"]):
                continue
            z_pass = row["overnight_z"] > Z_THRESHOLD

        if USE_VOL_FILTER:
            if np.isnan(row["volume_ratio"]):
                continue
            vol_pass = row["volume_ratio"] > VOL_THRESHOLD

        if not (z_pass and vol_pass):
            continue

        # Direction filter
        direction = int(row["overnight_dir"])
        if mode == "long" and direction != 1:
            continue
        if mode == "short" and direction != -1:
            continue

        # Entry
        signals[i] = direction
        position = direction

        # Stop price
        atr = row["atr"]
        if direction == 1:
            stop_prices[i] = row["entry_price"] - SL_ATR_MULT * atr
        else:
            stop_prices[i] = row["entry_price"] + SL_ATR_MULT * atr

    # Final exit if still in position
    if position != 0 and n > 0:
        exit_signals[n - 1] = position

    # Build output DataFrame in daily format
    result = pd.DataFrame({
        "datetime": daily["trading_date"],
        "open": daily["entry_price"],    # Entry price for backtest
        "high": daily["rth_high"],
        "low": daily["rth_low"],
        "close": daily["exit_price"],    # Exit price for backtest
        "volume": daily["opening_volume"],
        "signal": signals,
        "exit_signal": exit_signals,
        "stop_price": stop_prices,
        "target_price": target_prices,
    })

    return result
