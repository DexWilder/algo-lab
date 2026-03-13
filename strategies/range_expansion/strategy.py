"""Range Expansion Breakout — Tail Engine Strategy.

Family: breakout / range_expansion
Target: MNQ, M2K, MES (trend-friendly indices)
Timeframe: 5m bars

Concept: Detect narrow-range sessions (compression), then trade the
expansion bar when volatility expands. Low frequency, large winners,
convex payoff profile.

Logic:
  1. Track session high/low (new session on date change).
  2. Narrow range = developing session range < 0.6x 10-day avg daily range.
  3. Expansion bar = bar range > 1.5x ATR(14).
  4. Direction from expansion bar close vs open.
  5. Volume confirmation: bar volume > 1.3x 20-bar MA.
  6. Stop at opposite session extreme (session low for longs, session high for shorts).
  7. Target at 3.5x ATR(14) for trend capture.
  8. Profit ladder trailing: 1R->lock 0.25R, 2R->lock 1R, 3R->lock 2R.
  9. 25-bar cooldown between trades.
 10. Time filter: 09:30-14:00 ET only.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

# Range detection
DAILY_RANGE_LOOKBACK = 10       # Days of history for average daily range
NARROW_RANGE_MULT = 0.6         # Session range must be < 0.6x avg daily range

# Expansion detection
ATR_PERIOD = 14                 # ATR lookback for expansion & targets
EXPANSION_ATR_MULT = 1.5        # Bar range must exceed 1.5x ATR

# Volume filter
VOL_MULT = 1.3                  # Volume must exceed 1.3x 20-bar MA
VOL_MA_LEN = 20                 # Volume MA period

# Targets & stops
TARGET_ATR_MULT = 3.5           # TP = 3.5x ATR (large target for trend capture)

# Profit ladder (R-multiples for trailing stop ratchet)
LADDER_1R_LOCK = 0.25           # At 1R profit, lock 0.25R
LADDER_2R_LOCK = 1.0            # At 2R profit, lock 1.0R
LADDER_3R_LOCK = 2.0            # At 3R profit, lock 2.0R

# Trade management
COOLDOWN_BARS = 25              # Minimum bars between trades
SESSION_START = "09:30"
ENTRY_END = "14:00"             # No new entries after 14:00 ET
SESSION_END = "15:15"           # EOD flatten

TICK_SIZE = 0.25                # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Compute Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=1).mean()


def _parse_time(dt_series: pd.Series) -> pd.Series:
    """Extract HH:MM time string from datetime column."""
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate range expansion breakout signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── ATR ────────────────────────────────────────────────────────────
    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)
    df["_atr"] = atr

    # ── Volume MA ──────────────────────────────────────────────────────
    has_volume = df["volume"].sum() > 0
    df["_vol_ma"] = df["volume"].rolling(window=VOL_MA_LEN, min_periods=1).mean()

    # ── Daily range history (previous completed days) ──────────────────
    daily_stats = df.groupby("_date").agg(
        day_high=("high", "max"),
        day_low=("low", "min"),
    )
    daily_stats["day_range"] = daily_stats["day_high"] - daily_stats["day_low"]
    daily_stats["avg_daily_range"] = (
        daily_stats["day_range"]
        .shift(1)
        .rolling(window=DAILY_RANGE_LOOKBACK, min_periods=3)
        .mean()
    )
    df = df.merge(
        daily_stats[["avg_daily_range"]],
        left_on="_date", right_index=True, how="left",
    )

    # ── Session tracking + signal detection (vectorised where possible) ─
    # Build session high/low as running max/min within each date
    df["_session_high"] = df.groupby("_date")["high"].cummax()
    df["_session_low"] = df.groupby("_date")["low"].cummin()
    df["_session_range"] = df["_session_high"] - df["_session_low"]

    # Narrow range condition: developing session range < threshold
    narrow_range = df["_session_range"] < (df["avg_daily_range"] * NARROW_RANGE_MULT)

    # Expansion bar: bar range > 1.5x ATR
    bar_range = df["high"] - df["low"]
    expansion_bar = bar_range > (atr * EXPANSION_ATR_MULT)

    # Direction from expansion bar
    bullish_bar = df["close"] > df["open"]
    bearish_bar = df["close"] < df["open"]

    # Volume confirmation
    if has_volume:
        vol_ok = df["volume"] > (df["_vol_ma"] * VOL_MULT)
    else:
        vol_ok = pd.Series(True, index=df.index)

    # Time filter
    in_entry_window = (time_str >= SESSION_START) & (time_str < ENTRY_END)
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    # Combined entry conditions (before cooldown filtering)
    long_signal = (
        narrow_range &
        expansion_bar &
        bullish_bar &
        vol_ok &
        in_entry_window &
        df["avg_daily_range"].notna()
    ).fillna(False)

    short_signal = (
        narrow_range &
        expansion_bar &
        bearish_bar &
        vol_ok &
        in_entry_window &
        df["avg_daily_range"].notna()
    ).fillna(False)

    # ── Build raw signal + stop/target arrays ──────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    long_mask = long_signal.values
    short_mask = short_signal.values

    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "_session_low"]
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] + atr.loc[long_mask] * TARGET_ATR_MULT

    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "_session_high"]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - atr.loc[short_mask] * TARGET_ATR_MULT

    # ── Exit loop: cooldown, profit ladder, EOD flatten ────────────────
    position = 0
    entry_price = 0.0
    entry_stop = 0.0
    entry_target = 0.0
    risk = 0.0               # 1R distance
    trailing_stop = 0.0
    bars_since_last_trade = COOLDOWN_BARS  # Allow first trade immediately
    current_date = None

    signals_arr = df["signal"].values.copy()
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = df["stop_price"].values.copy()
    target_arr = df["target_price"].values.copy()

    dates = df["_date"].values
    times = time_str.values
    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values

    for i in range(n):
        bar_date = dates[i]
        time_s = times[i]

        # Day reset — reset narrow range tracking is handled vectorised
        if bar_date != current_date:
            current_date = bar_date

        sig = signals_arr[i]

        # Enforce cooldown
        if sig != 0 and bars_since_last_trade < COOLDOWN_BARS:
            signals_arr[i] = 0
            stop_arr[i] = np.nan
            target_arr[i] = np.nan
            sig = 0

        # Don't enter while already in a position
        if sig != 0 and position != 0:
            signals_arr[i] = 0
            stop_arr[i] = np.nan
            target_arr[i] = np.nan
            sig = 0

        # EOD flatten
        if position != 0 and time_s >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # ── Manage open position: profit ladder trailing ───────────
        if position == 1:
            # Check profit ladder and ratchet trailing stop
            unrealised = highs[i] - entry_price
            r_multiple = unrealised / risk if risk > 0 else 0.0

            if r_multiple >= 3.0:
                trailing_stop = max(trailing_stop, entry_price + risk * LADDER_3R_LOCK)
            elif r_multiple >= 2.0:
                trailing_stop = max(trailing_stop, entry_price + risk * LADDER_2R_LOCK)
            elif r_multiple >= 1.0:
                trailing_stop = max(trailing_stop, entry_price + risk * LADDER_1R_LOCK)

            effective_stop = max(entry_stop, trailing_stop)

            if lows[i] <= effective_stop:
                exit_sigs[i] = 1
                position = 0
            elif highs[i] >= entry_target:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            unrealised = entry_price - lows[i]
            r_multiple = unrealised / risk if risk > 0 else 0.0

            if r_multiple >= 3.0:
                trailing_stop = min(trailing_stop, entry_price - risk * LADDER_3R_LOCK)
            elif r_multiple >= 2.0:
                trailing_stop = min(trailing_stop, entry_price - risk * LADDER_2R_LOCK)
            elif r_multiple >= 1.0:
                trailing_stop = min(trailing_stop, entry_price - risk * LADDER_1R_LOCK)

            effective_stop = min(entry_stop, trailing_stop)

            if highs[i] >= effective_stop:
                exit_sigs[i] = -1
                position = 0
            elif lows[i] <= entry_target:
                exit_sigs[i] = -1
                position = 0

        # ── Open new position ──────────────────────────────────────
        if position == 0 and sig != 0:
            sp = stop_arr[i]
            tp = target_arr[i]
            if not np.isnan(sp) and not np.isnan(tp):
                position = sig
                entry_price = closes[i]
                entry_stop = sp
                entry_target = tp
                risk = abs(entry_price - sp)
                trailing_stop = sp  # Start trailing at initial stop
                bars_since_last_trade = 0

        bars_since_last_trade += 1

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr

    # Clean up internal columns
    drop_cols = [
        "_date", "_atr", "_vol_ma", "avg_daily_range",
        "_session_high", "_session_low", "_session_range",
    ]
    df.drop(columns=drop_cols, inplace=True, errors="ignore")

    return df
