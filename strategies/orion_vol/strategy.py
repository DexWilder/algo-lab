"""ORION-VOL — Hybrid Volatility Breakout (Compression → Expansion).

Source: ana_gagua — ORION: Hybrid Volatility Breakout Strategy
URL: https://www.tradingview.com/script/6xLkMWMC-ORION-Hybrid-Volatility-Breakout-Strategy/
Family: breakout (volatility compression)
Conversion: Faithful — original ORION parameters preserved.

Logic:
- Build compression box: highest high / lowest low over lookback (15 bars)
- Tightness filter: box range < ATR_MULT * ATR (2.5x)
- Flatness filter: abs(linear regression slope) < SLOPE_THRESHOLD (0.2)
- Trend filter: EMA 150 — longs above, shorts below
- Entry: close breaks outside box in trend direction
- Stop: opposite side of box
- Target: 1.9R from entry (R = entry-to-stop distance)
- Box expires after 45 bars if no breakout

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

LOOKBACK = 15              # Bars for box high/low
ATR_PERIOD = 14            # ATR period
ATR_MULT = 2.5             # Max range/ATR ratio for compression
SLOPE_THRESHOLD = 0.2      # Max abs(slope) for flatness
EMA_LENGTH = 150           # Trend filter EMA
RR_RATIO = 1.9             # Risk:reward ratio
BOX_EXPIRY = 45            # Box expires after N bars

SESSION_START = "09:30"
SESSION_END = "15:15"
ENTRY_CUTOFF = "14:30"     # No new entries in last 45 min

TICK_SIZE = 0.25            # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _linreg_slope(series: pd.Series, length: int) -> pd.Series:
    """Rolling linear regression slope."""
    result = np.full(len(series), np.nan)
    vals = series.values
    x = np.arange(length, dtype=float)
    x_mean = x.mean()
    ss_xx = np.sum((x - x_mean) ** 2)
    for i in range(length - 1, len(vals)):
        window = vals[i - length + 1:i + 1]
        if np.any(np.isnan(window)):
            continue
        y_mean = window.mean()
        ss_xy = np.sum((x - x_mean) * (window - y_mean))
        if ss_xx == 0:
            result[i] = 0.0
        else:
            result[i] = ss_xy / ss_xx
    return pd.Series(result, index=series.index)


def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate ORION volatility breakout signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    before_cutoff = time_str < ENTRY_CUTOFF

    # ── Indicators ────────────────────────────────────────────────────
    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)
    ema150 = df["close"].ewm(span=EMA_LENGTH, adjust=False).mean()

    # Rolling box boundaries
    box_high = df["high"].rolling(window=LOOKBACK, min_periods=LOOKBACK).max()
    box_low = df["low"].rolling(window=LOOKBACK, min_periods=LOOKBACK).min()
    box_range = box_high - box_low

    # Compression filters
    # Tightness: range < ATR_MULT * ATR
    is_tight = box_range < (ATR_MULT * atr)

    # Flatness: abs(slope of close) < threshold
    slope = _linreg_slope(df["close"], LOOKBACK)
    # Normalize slope by ATR to make it scale-independent
    norm_slope = slope.abs() / atr
    is_flat = norm_slope < SLOPE_THRESHOLD

    # Valid compression
    is_compressed = is_tight & is_flat

    # Trend filter
    above_ema = df["close"] > ema150
    below_ema = df["close"] < ema150

    # ── Stateful box tracking + entry/exit ────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values

    box_high_arr = box_high.values
    box_low_arr = box_low.values
    is_compressed_arr = is_compressed.fillna(False).values
    above_ema_arr = above_ema.values
    below_ema_arr = below_ema.values
    in_session_arr = in_session.values
    before_cutoff_arr = before_cutoff.values

    # Box state
    active_box = False
    box_top = 0.0
    box_bottom = 0.0
    box_age = 0

    # Position state
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    current_date = None
    traded_today = False

    for i in range(n):
        bar_date = dates_arr[i]

        # Day reset
        if bar_date != current_date:
            current_date = bar_date
            traded_today = False
            # Force close any overnight position
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0

        # EOD flatten
        if position != 0 and time_arr[i] >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # ── Check exits for open position ─────────────────────────────
        if position == 1:
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            elif high_arr[i] >= entry_target:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            if high_arr[i] >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            elif low_arr[i] <= entry_target:
                exit_sigs[i] = -1
                position = 0

        # Skip non-session bars for box/entry logic
        if not in_session_arr[i]:
            continue

        # ── Box management ────────────────────────────────────────────
        if active_box:
            box_age += 1
            if box_age >= BOX_EXPIRY:
                active_box = False

        # Check for new compression (update box if currently compressed)
        if is_compressed_arr[i] and not np.isnan(box_high_arr[i]):
            active_box = True
            box_top = box_high_arr[i]
            box_bottom = box_low_arr[i]
            box_age = 0

        # ── Entry: breakout from active box ───────────────────────────
        if position == 0 and active_box and before_cutoff_arr[i] and not traded_today:
            # Long breakout
            if close_arr[i] > box_top and above_ema_arr[i]:
                risk = close_arr[i] - box_bottom
                if risk > 0:
                    signals_arr[i] = 1
                    stop_arr[i] = box_bottom
                    target_arr[i] = close_arr[i] + risk * RR_RATIO
                    position = 1
                    entry_stop = box_bottom
                    entry_target = close_arr[i] + risk * RR_RATIO
                    active_box = False
                    traded_today = True

            # Short breakout
            elif close_arr[i] < box_bottom and below_ema_arr[i]:
                risk = box_top - close_arr[i]
                if risk > 0:
                    signals_arr[i] = -1
                    stop_arr[i] = box_top
                    target_arr[i] = close_arr[i] - risk * RR_RATIO
                    position = -1
                    entry_stop = box_top
                    entry_target = close_arr[i] - risk * RR_RATIO
                    active_box = False
                    traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
