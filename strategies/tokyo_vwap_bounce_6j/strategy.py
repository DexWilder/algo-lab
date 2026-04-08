"""Tokyo Session VWAP Bounce on JPY Futures (6J).

Source: Harvest note 2026-03-25_10_tokyo_vwap_bounce_6j.md
Factor: STRUCTURAL (session microstructure)
Archetype: TAIL ENGINE (session-specific, ~1 trade/day max)

Logic:
  1. Tokyo session open: 19:00 ET
  2. Entry window: first 2 hours of Tokyo (19:00-21:00 ET)
  3. Session VWAP starts accumulating at 19:00 ET
  4. Setup: 2-candle VWAP bounce confirmation
     Long:  price > VWAP, then bar 1 wicks through VWAP, bar 2 closes back above
     Short: price < VWAP, then bar 1 wicks above VWAP, bar 2 closes back below
  5. Exit 50% at 1R, rest at 2R (or at 21:00 ET cutoff)

Notes:
  - 6J data starts 2024-02-29, so only ~2 years of history (short sample)
  - 5m bars treated as "candles"
  - Tokyo cash session: 19:00 ET (winter) / 20:00 ET (DST) — we use 19:00 anchor

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# Parameters
TOKYO_OPEN_HHMM = 1900       # Tokyo session start (ET)
ENTRY_END_HHMM = 2100        # Entry cutoff — first 2 hours only
SESSION_END_HHMM = 2155      # Force flatten before crossing into London

# VWAP session start (same as Tokyo open)
# Wick tolerance: how far through VWAP counts as "test"
WICK_THROUGH_ATR = 0.10
# Min distance from VWAP for initial "above/below" classification
VWAP_DIR_THRESHOLD_ATR = 0.05

TICK_SIZE = 0.0000005  # 6J default


def _compute_features(df):
    df = df.copy()
    dt = pd.to_datetime(df["datetime"])
    df["date"] = dt.dt.date
    df["hhmm"] = dt.dt.hour * 100 + dt.dt.minute

    # Build "Tokyo session date" — bars from 19:00 ET one day to 02:55 ET next
    # belong to the same Tokyo session.
    df["session_date"] = df["date"]
    # If bar is before Tokyo open (before 19:00), belongs to previous session's
    # Asian continuation — but for entry window we only care about 19:00-21:00 ET
    # which is always same calendar date.

    # ATR (14 bars)
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(span=14, adjust=False).mean()

    return df


def generate_signals(df):
    df = _compute_features(df)
    n = len(df)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    open_ = df["open"].values
    volume = df["volume"].values if "volume" in df.columns else np.ones(n)
    atr = df["atr"].values
    hhmm = df["hhmm"].values
    date = df["date"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # Session-scoped state
    session_vwap_num = 0.0  # cumulative price*volume within Tokyo session
    session_vwap_den = 0.0  # cumulative volume
    session_active_date = None
    last_bar_dir = 0  # track bar direction for 2-candle setup
    last_bar_above_vwap = None  # True/False/None

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    initial_risk = 0.0
    scaled_out = False

    for i in range(1, n):
        t = hhmm[i]
        d = date[i]
        a = atr[i]
        if np.isnan(a) or a == 0:
            continue

        # Detect session start (19:00 ET on new day)
        if t >= TOKYO_OPEN_HHMM and (session_active_date != d):
            # Reset session
            session_active_date = d
            session_vwap_num = 0.0
            session_vwap_den = 0.0
            last_bar_dir = 0
            last_bar_above_vwap = None
            # Force close any stale position
            if position != 0:
                exit_sigs[i] = position
                position = 0

        # Accumulate VWAP only during Tokyo session window
        in_session = (session_active_date == d) and (t >= TOKYO_OPEN_HHMM) and (t < SESSION_END_HHMM)
        if in_session:
            typical = (high[i] + low[i] + close[i]) / 3
            vol = max(volume[i], 1)  # avoid div zero
            session_vwap_num += typical * vol
            session_vwap_den += vol

        # Manage position
        if position != 0:
            # Long exits
            if position == 1:
                # Stop
                if low[i] <= stop_price:
                    exit_sigs[i] = 1
                    position = 0
                    continue
                # Scale out at 1R
                if not scaled_out and high[i] >= entry_price + initial_risk:
                    scaled_out = True
                    # Move stop to breakeven on remaining
                    stop_price = max(stop_price, entry_price)
                # Target 2R
                if high[i] >= target_price:
                    exit_sigs[i] = 1
                    position = 0
                    continue
            elif position == -1:
                if high[i] >= stop_price:
                    exit_sigs[i] = -1
                    position = 0
                    continue
                if not scaled_out and low[i] <= entry_price - initial_risk:
                    scaled_out = True
                    stop_price = min(stop_price, entry_price)
                if low[i] <= target_price:
                    exit_sigs[i] = -1
                    position = 0
                    continue

            # Force flatten at session end
            if t >= SESSION_END_HHMM:
                exit_sigs[i] = position
                position = 0
                continue

        # Entry: only within first 2 hours of Tokyo session AND vwap is defined
        if position == 0 and in_session and t < ENTRY_END_HHMM and session_vwap_den > 0:
            vwap = session_vwap_num / session_vwap_den
            dist_from_vwap = (close[i] - vwap) / a

            # Classify whether previous bar was "above" or "below" VWAP (with tolerance)
            prev_above = last_bar_above_vwap

            # 2-candle setup check (simplified):
            # Long: previous bar wicked THROUGH VWAP to the downside, current closes back above
            if prev_above is True and low[i] <= vwap - WICK_THROUGH_ATR * a and close[i] > vwap:
                # Bullish reversal bounce off VWAP
                position = 1
                entry_price = close[i]
                # Stop = below the wick of bar 1 (use prev low) or atr-based
                stop_price = min(low[i], low[i-1]) - 0.1 * a
                initial_risk = entry_price - stop_price
                if initial_risk <= 0:
                    position = 0
                    continue
                target_price = entry_price + 2 * initial_risk
                scaled_out = False
                signals[i] = 1
                stop_arr[i] = stop_price
                target_arr[i] = target_price
            elif prev_above is False and high[i] >= vwap + WICK_THROUGH_ATR * a and close[i] < vwap:
                position = -1
                entry_price = close[i]
                stop_price = max(high[i], high[i-1]) + 0.1 * a
                initial_risk = stop_price - entry_price
                if initial_risk <= 0:
                    position = 0
                    continue
                target_price = entry_price - 2 * initial_risk
                scaled_out = False
                signals[i] = -1
                stop_arr[i] = stop_price
                target_arr[i] = target_price

            # Update bar direction for next iteration
            if dist_from_vwap > VWAP_DIR_THRESHOLD_ATR:
                last_bar_above_vwap = True
            elif dist_from_vwap < -VWAP_DIR_THRESHOLD_ATR:
                last_bar_above_vwap = False
            # Otherwise leave unchanged (still near VWAP)

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date", "hhmm", "session_date", "atr"], inplace=True)
    return df
