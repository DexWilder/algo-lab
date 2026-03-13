"""VOL-COMPRESSION-BREAKOUT-V2 — Tail Engine Volatility Compression Breakout.

Low-frequency, convex-payoff strategy targeting explosive moves after sustained
volatility compression. Designed for trend-friendly index futures (MNQ, M2K, MES).

Structurally different from v1:
- v1: BB width + ATR squeeze dual filter, 5-bar minimum, simple bracket exit
- v2: BB width percentile only (cleaner), 8-bar sustained squeeze, volume
  confirmation, compression-range stop, 3R ATR target, profit-ladder trailing

Structurally different from bb_equilibrium:
- bb_equilibrium: mean reversion INTO bands (counter-trend, high win rate, small wins)
- vol_compression_v2: breakout OUT OF bands (trend-continuation, low win rate, large wins)

Logic:
- Compression: BB width (20-period) drops below 20th percentile of its 50-bar
  rolling window. Must persist for at least 8 consecutive bars.
- Entry: after compression ends, close breaks above upper BB (long) or below
  lower BB (short).
- Volume confirmation: bar volume > 1.5x 20-bar average volume.
- Stop: opposite side of compression range (low of compression for longs,
  high of compression for shorts). Capped at 3.5x ATR.
- Target: 3.0x ATR(14) from entry.
- Trailing: after 2R profit, trail stop at 1R from highs/lows.
- Cooldown: 20 bars between trades (low frequency by design).
- Session flatten at 15:30 ET.

Expected behavior:
- Win rate 25-40% (tail strategy — most trades are small losses or scratches)
- When it wins, wins are 3-5R (convex payoff)
- Low trade count (5-15 per month per asset)
- Best regimes: post-compression expansion, GRINDING days
- Median hold time: 20-60+ bars

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

# Bollinger Band settings
BB_LENGTH = 20                # BB SMA period
BB_MULT = 2.0                 # BB standard deviation multiplier

# Compression detection
BW_LOOKBACK = 50              # Rolling window for BB width percentile
BW_COMPRESS_PCTL = 20         # Below this percentile = compressed
MIN_COMPRESSION_BARS = 8      # Sustained squeeze: must compress for N bars

# Volume confirmation
VOL_AVG_PERIOD = 20           # Volume averaging period
VOL_BREAKOUT_MULT = 1.5       # Breakout bar volume must exceed this × average

# Risk management
ATR_PERIOD = 14               # ATR period
TARGET_ATR_MULT = 3.0         # Target = entry ± ATR × mult (big target)
STOP_ATR_CAP = 3.5            # Max stop distance = ATR × cap (safety valve)
TRAIL_ENGAGE_R = 2.0          # Trail activates after this many R of profit
TRAIL_LOCK_R = 1.0            # Once trailing, lock this many R from peak

# Trade management
COOLDOWN_BARS = 20            # Minimum bars between trades

# Session timing
SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "10:00"         # Wait for indicators + first 30min noise
ENTRY_CUTOFF = "14:30"        # Need room for expansion move
FLATTEN_TIME = "15:30"        # Pre-close flatten

TICK_SIZE = 0.25              # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate volatility compression breakout signals.

    Parameters
    ----------
    df : DataFrame with columns: datetime, open, high, low, close, volume
         (5-minute bars)
    asset : str, optional
        Asset symbol (unused, kept for interface compatibility).

    Returns
    -------
    DataFrame with added columns: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # ── Bollinger Bands ───────────────────────────────────────────────────
    close_s = df["close"]
    bb_mid = close_s.rolling(window=BB_LENGTH, min_periods=BB_LENGTH).mean()
    bb_std = close_s.rolling(window=BB_LENGTH, min_periods=BB_LENGTH).std(ddof=0)
    bb_upper = (bb_mid + BB_MULT * bb_std).values
    bb_lower = (bb_mid - BB_MULT * bb_std).values
    bb_mid_arr = bb_mid.values

    # BB width (normalized by midline)
    bb_width = np.where(bb_mid_arr > 0,
                        (bb_upper - bb_lower) / bb_mid_arr,
                        np.nan)

    # Rolling percentile rank of current BB width within lookback window
    bw_series = pd.Series(bb_width)
    bw_pctrank = bw_series.rolling(
        window=BW_LOOKBACK, min_periods=20
    ).apply(lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False).values

    # ── Compression detection ─────────────────────────────────────────────
    # A bar is "compressed" if BB width percentile rank <= threshold
    compressed = np.zeros(n, dtype=bool)
    for i in range(n):
        if not np.isnan(bw_pctrank[i]):
            compressed[i] = bw_pctrank[i] <= BW_COMPRESS_PCTL

    # Count consecutive compression bars
    consec_compress = np.zeros(n, dtype=int)
    for i in range(n):
        if compressed[i]:
            consec_compress[i] = (consec_compress[i - 1] + 1) if i > 0 else 1

    # Track compression range: rolling high/low during compression
    compress_high = np.full(n, np.nan)
    compress_low = np.full(n, np.nan)
    for i in range(n):
        if consec_compress[i] >= 1:
            bars_back = consec_compress[i]
            start_idx = max(0, i - bars_back + 1)
            compress_high[i] = np.max(df["high"].values[start_idx:i + 1])
            compress_low[i] = np.min(df["low"].values[start_idx:i + 1])

    # ── ATR ───────────────────────────────────────────────────────────────
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # ── Volume average ────────────────────────────────────────────────────
    vol_avg = df["volume"].rolling(window=VOL_AVG_PERIOD, min_periods=10).mean().values

    # ── Pre-compute arrays ────────────────────────────────────────────────
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    volume_arr = df["volume"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # ── Stateful loop ─────────────────────────────────────────────────────
    position = 0
    entry_price = 0.0
    initial_stop = 0.0
    trailing_stop = 0.0
    target_price = 0.0
    risk_per_r = 0.0          # dollar distance of 1R (for trail calculation)
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    trail_engaged = False
    current_date = None
    bars_since_last_trade = COOLDOWN_BARS  # Start ready to trade

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]

        bars_since_last_trade += 1

        # ── Day reset ────────────────────────────────────────────────────
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date

        if not in_session_arr[i]:
            continue

        if np.isnan(bar_atr) or np.isnan(bb_upper[i]) or np.isnan(bb_lower[i]):
            continue

        # ── Pre-close flatten ────────────────────────────────────────────
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # ── Check exits for open position ────────────────────────────────
        if position == 1:
            # Update high watermark
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]

            # Check if trail should engage (profit >= TRAIL_ENGAGE_R × 1R)
            unrealized_r = (highest_since_entry - entry_price) / risk_per_r if risk_per_r > 0 else 0
            if not trail_engaged and unrealized_r >= TRAIL_ENGAGE_R:
                trail_engaged = True

            # Update trailing stop if engaged
            if trail_engaged:
                new_trail = highest_since_entry - risk_per_r * TRAIL_LOCK_R
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Exit: target hit
            if high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0
            # Exit: stop/trail hit
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            # Update low watermark
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]

            # Check if trail should engage
            unrealized_r = (entry_price - lowest_since_entry) / risk_per_r if risk_per_r > 0 else 0
            if not trail_engaged and unrealized_r >= TRAIL_ENGAGE_R:
                trail_engaged = True

            # Update trailing stop if engaged
            if trail_engaged:
                new_trail = lowest_since_entry + risk_per_r * TRAIL_LOCK_R
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            # Exit: target hit
            if low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
            # Exit: stop/trail hit
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # ── Entry: compression breakout ──────────────────────────────────
        if position == 0 and entry_ok_arr[i]:

            # Cooldown check
            if bars_since_last_trade < COOLDOWN_BARS:
                continue

            # Prior bar must have had sustained compression
            prior_consec = consec_compress[i - 1] if i > 0 else 0
            if prior_consec < MIN_COMPRESSION_BARS:
                continue

            # Volume confirmation
            if (np.isnan(vol_avg[i]) or vol_avg[i] <= 0
                    or volume_arr[i] < VOL_BREAKOUT_MULT * vol_avg[i]):
                continue

            # Compression range for stop placement
            comp_hi = compress_high[i - 1]
            comp_lo = compress_low[i - 1]
            if np.isnan(comp_hi) or np.isnan(comp_lo):
                continue

            # ── Long entry: close breaks above upper BB ──────────────────
            if close_arr[i] > bb_upper[i]:
                # Stop = low of compression range (or ATR cap, whichever tighter)
                raw_stop = comp_lo
                atr_cap_stop = close_arr[i] - STOP_ATR_CAP * bar_atr
                stop_p = max(raw_stop, atr_cap_stop)  # tighter of the two

                risk = close_arr[i] - stop_p
                if risk <= 0:
                    continue  # degenerate stop, skip

                target_p = close_arr[i] + TARGET_ATR_MULT * bar_atr

                signals_arr[i] = 1
                stop_arr[i] = stop_p
                target_arr[i] = target_p
                position = 1
                entry_price = close_arr[i]
                initial_stop = stop_p
                trailing_stop = stop_p
                target_price = target_p
                risk_per_r = risk
                highest_since_entry = high_arr[i]
                trail_engaged = False
                bars_since_last_trade = 0

            # ── Short entry: close breaks below lower BB ─────────────────
            elif close_arr[i] < bb_lower[i]:
                # Stop = high of compression range (or ATR cap, whichever tighter)
                raw_stop = comp_hi
                atr_cap_stop = close_arr[i] + STOP_ATR_CAP * bar_atr
                stop_p = min(raw_stop, atr_cap_stop)  # tighter of the two

                risk = stop_p - close_arr[i]
                if risk <= 0:
                    continue  # degenerate stop, skip

                target_p = close_arr[i] - TARGET_ATR_MULT * bar_atr

                signals_arr[i] = -1
                stop_arr[i] = stop_p
                target_arr[i] = target_p
                position = -1
                entry_price = close_arr[i]
                initial_stop = stop_p
                trailing_stop = stop_p
                target_price = target_p
                risk_per_r = risk
                lowest_since_entry = low_arr[i]
                trail_engaged = False
                bars_since_last_trade = 0

    # ── Build output ──────────────────────────────────────────────────────
    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
