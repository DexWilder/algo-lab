"""VOL-COMPRESSION-BREAKOUT — Volatility Compression Breakout.

Designed for Russell 2000 futures (M2K) but works on any asset.
Detects periods of volatility compression via Bollinger Band width contraction
and ATR squeeze, then enters on breakout from the compression zone.

Logic:
- Compression detected: BB width below 20th percentile of its 20-bar rolling window
  AND ATR(14) < 0.7 * ATR(14) 50-bar rolling mean
- Minimum 5 consecutive bars of compression required before breakout
- Long entry: compression + close breaks above upper Bollinger Band
- Short entry: compression + close breaks below lower Bollinger Band
- Stop: 1.5 * ATR(14) from entry
- Target: 3.0 * ATR(14) from entry (2:1 reward-risk)
- Max 1 trade per direction per day
- Session flatten at 15:30 ET

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ----------------------------------------------------------------

BB_PERIOD = 20              # Bollinger Band lookback
BB_STD = 2.0               # BB standard deviation multiplier
BB_WIDTH_LOOKBACK = 20      # Rolling window for BB width percentile
BB_WIDTH_PCTL = 20          # Compression threshold: below this percentile

ATR_PERIOD = 14             # ATR lookback
ATR_SQUEEZE_LOOKBACK = 50   # Rolling mean lookback for ATR squeeze
ATR_SQUEEZE_RATIO = 0.70    # Current ATR must be < ratio * rolling mean ATR

MIN_COMPRESSION_BARS = 5    # Minimum consecutive bars in compression before entry

STOP_ATR_MULT = 1.5         # Stop distance = ATR * mult
TARGET_ATR_MULT = 3.0       # Target distance = ATR * mult (2:1 R:R)

SESSION_START = "09:30"
ENTRY_START = "10:00"       # Wait for indicators to stabilize
ENTRY_CUTOFF = "15:00"      # No new entries after this
SESSION_END = "15:45"
FLATTEN_TIME = "15:30"      # Pre-close flatten

TICK_SIZE = 0.25            # Patched per asset by runner


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
                 period: int) -> np.ndarray:
    """Compute ATR using Wilder smoothing (EMA)."""
    n = len(close)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))

    atr = np.full(n, np.nan)
    if n < period:
        return atr

    # Seed with SMA
    atr[period - 1] = np.mean(tr[:period])
    alpha = 1.0 / period
    for i in range(period, n):
        atr[i] = atr[i - 1] + alpha * (tr[i] - atr[i - 1])

    return atr


def _rolling_percentile(arr: np.ndarray, window: int,
                        pctl: float) -> np.ndarray:
    """Return the rolling percentile threshold for each bar."""
    n = len(arr)
    result = np.full(n, np.nan)
    for i in range(window - 1, n):
        chunk = arr[i - window + 1: i + 1]
        valid = chunk[~np.isnan(chunk)]
        if len(valid) > 0:
            result[i] = np.percentile(valid, pctl)
    return result


def _rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple rolling mean, NaN-aware."""
    n = len(arr)
    result = np.full(n, np.nan)
    for i in range(window - 1, n):
        chunk = arr[i - window + 1: i + 1]
        valid = chunk[~np.isnan(chunk)]
        if len(valid) > 0:
            result[i] = np.mean(valid)
    return result


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset: str = None,
                     mode: str = "both") -> pd.DataFrame:
    """Generate volatility compression breakout signals.

    Parameters
    ----------
    df : DataFrame with columns: open, high, low, close, volume, datetime
         (5-minute bars, datetime index or column)
    asset : str, optional
        Asset symbol (unused, kept for interface compatibility).
    mode : str, optional
        "long", "short", or "both" (default "both").

    Returns
    -------
    DataFrame with added columns: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Session boundaries ----------------------------------------------------
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # -- Bollinger Bands -------------------------------------------------------
    close_s = df["close"]
    bb_mid = close_s.rolling(window=BB_PERIOD).mean().values
    bb_std = close_s.rolling(window=BB_PERIOD).std(ddof=0).values
    bb_upper = bb_mid + BB_STD * bb_std
    bb_lower = bb_mid - BB_STD * bb_std

    # BB width (normalized)
    bb_width = np.where(bb_mid > 0, (bb_upper - bb_lower) / bb_mid, np.nan)

    # Rolling percentile of BB width for compression detection
    bb_width_pctl_threshold = _rolling_percentile(bb_width, BB_WIDTH_LOOKBACK,
                                                  BB_WIDTH_PCTL)

    # -- ATR and ATR squeeze ---------------------------------------------------
    high_arr = df["high"].values
    low_arr = df["low"].values
    close_arr = df["close"].values

    atr = _compute_atr(high_arr, low_arr, close_arr, ATR_PERIOD)
    atr_rolling_mean = _rolling_mean(atr, ATR_SQUEEZE_LOOKBACK)

    # -- Compression detection (per-bar boolean) -------------------------------
    # Both conditions must hold:
    # 1. BB width below its rolling percentile threshold
    # 2. ATR below ratio * rolling mean ATR
    compression = np.zeros(n, dtype=bool)
    for i in range(n):
        if (not np.isnan(bb_width[i])
                and not np.isnan(bb_width_pctl_threshold[i])
                and not np.isnan(atr[i])
                and not np.isnan(atr_rolling_mean[i])):
            compression[i] = (bb_width[i] <= bb_width_pctl_threshold[i]
                              and atr[i] < ATR_SQUEEZE_RATIO * atr_rolling_mean[i])

    # Count consecutive compression bars
    consec_compression = np.zeros(n, dtype=int)
    for i in range(n):
        if compression[i]:
            consec_compression[i] = (consec_compression[i - 1] + 1) if i > 0 else 1
        else:
            consec_compression[i] = 0

    # -- Pre-compute arrays ----------------------------------------------------
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful loop ---------------------------------------------------------
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue

        if np.isnan(bar_atr) or np.isnan(bb_upper[i]) or np.isnan(bb_lower[i]):
            continue

        # -- Pre-close flatten -------------------------------------------------
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # -- Check exits for open position -------------------------------------
        if position == 1:
            # Stop hit
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            # Target hit
            elif high_arr[i] >= entry_target:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            # Stop hit
            if high_arr[i] >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            # Target hit
            elif low_arr[i] <= entry_target:
                exit_sigs[i] = -1
                position = 0

        # -- Entry: Compression breakout ---------------------------------------
        if position == 0 and entry_ok_arr[i]:

            # Must have had at least MIN_COMPRESSION_BARS of compression
            # (current bar or previous bar still in compression counts)
            # The breakout bar itself may break out of compression, so check
            # that the prior bar had enough compression.
            prior_comp = consec_compression[i - 1] if i > 0 else 0

            # -- Long entry ----------------------------------------------------
            if (allow_long
                    and not long_traded_today
                    and prior_comp >= MIN_COMPRESSION_BARS
                    and close_arr[i] > bb_upper[i]):

                stop_p = close_arr[i] - STOP_ATR_MULT * bar_atr
                target_p = close_arr[i] + TARGET_ATR_MULT * bar_atr

                signals_arr[i] = 1
                stop_arr[i] = stop_p
                target_arr[i] = target_p
                position = 1
                entry_stop = stop_p
                entry_target = target_p
                long_traded_today = True

            # -- Short entry ---------------------------------------------------
            elif (allow_short
                  and not short_traded_today
                  and prior_comp >= MIN_COMPRESSION_BARS
                  and close_arr[i] < bb_lower[i]):

                stop_p = close_arr[i] + STOP_ATR_MULT * bar_atr
                target_p = close_arr[i] - TARGET_ATR_MULT * bar_atr

                signals_arr[i] = -1
                stop_arr[i] = stop_p
                target_arr[i] = target_p
                position = -1
                entry_stop = stop_p
                entry_target = target_p
                short_traded_today = True

    # -- Build output ----------------------------------------------------------
    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
