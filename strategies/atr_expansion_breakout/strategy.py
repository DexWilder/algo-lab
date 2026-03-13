"""ATR-EXP — ATR Expansion Breakout.

Detects range compression (quiet periods) followed by volatility expansion,
then enters in the direction of the breakout from the compression range.

Designed for Crude Oil futures (MCL) but works on any asset.

Logic:
- Compression: ATR(14) < 0.6 * ATR 50-bar rolling mean for 8+ consecutive bars
- Expansion: ATR(14) > 1.3 * ATR 50-bar rolling mean
- Long: expansion bar closes above compression range high
- Short: expansion bar closes below compression range low
- Stop: opposite end of compression range (natural S/R)
- Target: 2.0 * compression range width from entry
- Cooldown: 10 bars after trade entry before next signal qualifies

Why this works:
- Compression = coiled energy; expansion = directional release
- Stop at opposite range boundary = structural level with meaning
- Wide target rewards patience through full expansion move

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

ATR_PERIOD = 14              # ATR lookback
ATR_MEAN_PERIOD = 50         # Rolling mean of ATR for compression/expansion detection
COMPRESSION_RATIO = 0.6      # ATR < this * mean = compressed
EXPANSION_RATIO = 1.3        # ATR > this * mean = expanding
MIN_COMPRESSION_BARS = 8     # Min consecutive compression bars to qualify
TARGET_MULT = 2.0            # Target = range_width * this from entry
COOLDOWN_BARS = 10           # Bars to wait after a trade before next entry

TICK_SIZE = 0.01             # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray,
         period: int) -> np.ndarray:
    """Compute ATR using Wilder smoothing (exponential)."""
    n = len(high)
    tr = np.empty(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    atr = np.full(n, np.nan)
    # Seed with simple mean
    if n >= period:
        atr[period - 1] = np.mean(tr[:period])
        alpha = 1.0 / period
        for i in range(period, n):
            atr[i] = atr[i - 1] * (1 - alpha) + tr[i] * alpha
    return atr


def _rolling_mean(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple rolling mean, NaN until enough data."""
    n = len(arr)
    out = np.full(n, np.nan)
    cumsum = 0.0
    valid = 0
    for i in range(n):
        if np.isnan(arr[i]):
            continue
        cumsum += arr[i]
        valid += 1
        if valid > window:
            cumsum -= arr[i - window]
            valid = window
        if valid == window:
            out[i] = cumsum / window
    return out


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, asset: str = None,
                     mode: str = "long") -> pd.DataFrame:
    """Generate ATR expansion breakout signals.

    Parameters
    ----------
    df : DataFrame with columns: open, high, low, close, volume (5-min bars).
    asset : Optional asset name (unused — strategy is asset-agnostic).
    mode : "long", "short", or "both" — which direction(s) to trade.

    Returns DataFrame with added columns:
        signal (1=long, -1=short, 0=none),
        exit_signal (1=exit long, -1=exit short, 0=none),
        stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    # ── ATR and rolling mean ──────────────────────────────────────────────
    atr = _atr(high, low, close, ATR_PERIOD)
    atr_mean = _rolling_mean(atr, ATR_MEAN_PERIOD)

    # ── Detect compression zones ──────────────────────────────────────────
    # Track consecutive compression bars and the high/low of each zone.
    compression_count = np.zeros(n, dtype=int)   # consecutive compressed bars ending here
    comp_high = np.full(n, np.nan)               # running high of current compression zone
    comp_low = np.full(n, np.nan)                # running low of current compression zone

    for i in range(n):
        if np.isnan(atr[i]) or np.isnan(atr_mean[i]):
            continue

        is_compressed = atr[i] < COMPRESSION_RATIO * atr_mean[i]

        if is_compressed:
            if i > 0 and compression_count[i - 1] > 0:
                # Continue existing compression zone
                compression_count[i] = compression_count[i - 1] + 1
                comp_high[i] = max(comp_high[i - 1], high[i])
                comp_low[i] = min(comp_low[i - 1], low[i])
            else:
                # Start new compression zone
                compression_count[i] = 1
                comp_high[i] = high[i]
                comp_low[i] = low[i]

    # ── Detect expansion + breakout entry bars ────────────────────────────
    # An expansion bar must:
    #   1. Have ATR > EXPANSION_RATIO * atr_mean
    #   2. Follow a qualified compression zone (>= MIN_COMPRESSION_BARS)
    #   3. Close beyond the compression range high (long) or low (short)
    #
    # We carry forward the most recent qualified compression range so that
    # the expansion bar (which is NOT compressed) can reference it.

    raw_signal = np.zeros(n, dtype=int)
    raw_stop = np.full(n, np.nan)
    raw_target = np.full(n, np.nan)

    # Carry-forward: last qualified compression range
    last_comp_high = np.nan
    last_comp_low = np.nan
    last_comp_valid = False

    for i in range(n):
        # Update carried range: if bar i-1 ended a qualified compression zone
        # (i.e. compression ended because bar i is NOT compressed, or is the
        # first bar of a new zone).
        if i > 0 and compression_count[i - 1] >= MIN_COMPRESSION_BARS:
            # Previous bar was compressed and zone was long enough
            if compression_count[i] == 0:
                # Current bar broke out of compression — lock in the range
                last_comp_high = comp_high[i - 1]
                last_comp_low = comp_low[i - 1]
                last_comp_valid = True

        if np.isnan(atr[i]) or np.isnan(atr_mean[i]):
            continue

        is_expanding = atr[i] > EXPANSION_RATIO * atr_mean[i]

        if is_expanding and last_comp_valid:
            range_width = last_comp_high - last_comp_low

            if range_width <= 0:
                continue

            # Long breakout: close above compression high
            if close[i] > last_comp_high:
                raw_signal[i] = 1
                raw_stop[i] = last_comp_low          # stop at compression low
                raw_target[i] = close[i] + TARGET_MULT * range_width

            # Short breakout: close below compression low
            elif close[i] < last_comp_low:
                raw_signal[i] = -1
                raw_stop[i] = last_comp_high          # stop at compression high
                raw_target[i] = close[i] - TARGET_MULT * range_width

    # ── Apply mode filter ─────────────────────────────────────────────────
    if mode == "long":
        raw_signal[raw_signal == -1] = 0
    elif mode == "short":
        raw_signal[raw_signal == 1] = 0
    # "both" keeps everything

    # ── Exit loop: enforce cooldown, stop/target management ───────────────
    signals_out = np.zeros(n, dtype=int)
    exit_out = np.zeros(n, dtype=int)
    stop_out = np.full(n, np.nan)
    target_out = np.full(n, np.nan)

    position = 0          # 0=flat, 1=long, -1=short
    entry_stop = 0.0
    entry_target = 0.0
    bars_since_entry = 0  # for cooldown after exit

    for i in range(n):
        sig = raw_signal[i]

        # ── Manage open position ──────────────────────────────────────
        if position == 1:
            bars_since_entry += 1
            # Check stop (hit if low touches)
            if low[i] <= entry_stop:
                exit_out[i] = 1
                position = 0
                bars_since_entry = 0
                continue
            # Check target (hit if high touches)
            if high[i] >= entry_target:
                exit_out[i] = 1
                position = 0
                bars_since_entry = 0
                continue

        elif position == -1:
            bars_since_entry += 1
            # Check stop (hit if high touches)
            if high[i] >= entry_stop:
                exit_out[i] = -1
                position = 0
                bars_since_entry = 0
                continue
            # Check target (hit if low touches)
            if low[i] <= entry_target:
                exit_out[i] = -1
                position = 0
                bars_since_entry = 0
                continue

        # ── New entry ─────────────────────────────────────────────────
        if position == 0 and sig != 0:
            # Cooldown check
            if bars_since_entry < COOLDOWN_BARS and bars_since_entry > 0:
                continue
            bars_since_entry += 1

            position = sig
            entry_stop = raw_stop[i]
            entry_target = raw_target[i]
            signals_out[i] = sig
            stop_out[i] = raw_stop[i]
            target_out[i] = raw_target[i]
            bars_since_entry = 1

        # Increment cooldown counter even when flat
        if position == 0 and bars_since_entry > 0:
            bars_since_entry += 1

    # ── Write output columns ──────────────────────────────────────────────
    df["signal"] = signals_out
    df["exit_signal"] = exit_out
    df["stop_price"] = stop_out
    df["target_price"] = target_out

    return df
