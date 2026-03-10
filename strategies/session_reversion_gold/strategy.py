"""SESSION-REVERSION-GOLD — Session-Based Mean Reversion for Gold.

Gold-specific: exploits the tendency for NY session to fade the overnight
(Asia/Europe) move. Gold's global macro flows create overnight dislocations
that frequently revert during NY hours.

Logic:
- Measure: overnight move = NY open vs prior day close
- If overnight gap is large (> threshold ATR), fade it
  - Large gap up → short (expect reversion down)
  - Large gap down → long (expect reversion up)
- Confirm: price shows early rejection of the gap direction
  - Long: first 30min makes a higher low (buyers stepping in)
  - Short: first 30min makes a lower high (sellers stepping in)
- Exit: prior day close (full gap fill) or partial target (50% reversion)
- Stop: ATR-based beyond the session extreme
- Only trade once per day (the gap fade)

Expected behavior:
- Win rate 50-60% (gap fills are reliable on gold)
- 1 trade/day max
- Median hold 15-40 bars (gap fills take time)

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

ATR_PERIOD = 14
ATR_STOP_MULT = 2.0       # Stop beyond session extreme
GAP_THRESHOLD_ATR = 0.8   # Min gap size in ATR units to trigger
PARTIAL_TARGET_PCT = 0.5  # Exit at 50% gap fill (conservative)
CONFIRM_BARS = 6          # Wait 6 bars (30 min) for confirmation
MIN_HOLD_BARS = 4

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "10:00"     # After 30min confirmation window
ENTRY_CUTOFF = "13:00"    # Gap fades need time — early entries only
FLATTEN_TIME = "15:30"

TICK_SIZE = 0.10


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # ATR
    prev_close_bar = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close_bar).abs(),
        (df["low"] - prev_close_bar).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    close_arr = df["close"].values
    open_arr = df["open"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    trailing_stop = 0.0
    target_price = 0.0
    current_date = None
    traded_today = False
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    bars_in_trade = 0

    # Daily state
    prior_close = np.nan
    session_open = np.nan
    session_high = np.nan
    session_low = np.nan
    gap_direction = 0       # +1 = gap up, -1 = gap down
    gap_size = 0.0
    session_bar_count = 0
    confirmed = False

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]

        # Day reset
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0

            # Save prior day's close
            if current_date is not None:
                # Find last bar of prior day
                prior_close = close_arr[i - 1]

            current_date = bar_date
            traded_today = False
            session_open = np.nan
            session_high = -np.inf
            session_low = np.inf
            gap_direction = 0
            gap_size = 0.0
            session_bar_count = 0
            confirmed = False

        if not in_session_arr[i]:
            continue

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # Track session OHLC
        session_bar_count += 1
        if session_bar_count == 1:
            session_open = open_arr[i]
            # Compute gap
            if not np.isnan(prior_close):
                gap_size = (session_open - prior_close) / bar_atr
                if gap_size > GAP_THRESHOLD_ATR:
                    gap_direction = 1    # Gap up → fade short
                elif gap_size < -GAP_THRESHOLD_ATR:
                    gap_direction = -1   # Gap down → fade long
                else:
                    gap_direction = 0    # No significant gap

        session_high = max(session_high, high_arr[i])
        session_low = min(session_low, low_arr[i])

        # Pre-close flatten
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Exits
        if position == 1:
            bars_in_trade += 1
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]

            # Exit: target reached (partial gap fill)
            if bars_in_trade >= MIN_HOLD_BARS and high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0
            # Exit: stop
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            bars_in_trade += 1
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]

            # Exit: target reached
            if bars_in_trade >= MIN_HOLD_BARS and low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
            # Exit: stop
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # Confirmation check (after CONFIRM_BARS bars)
        if (gap_direction != 0 and not confirmed
                and session_bar_count >= CONFIRM_BARS):
            if gap_direction == -1:
                # Gap down: confirm if price is making higher lows
                # (session low was set early, price is recovering)
                if close_arr[i] > session_low and close_arr[i] > close_arr[i-1]:
                    confirmed = True
            elif gap_direction == 1:
                # Gap up: confirm if price is making lower highs
                if close_arr[i] < session_high and close_arr[i] < close_arr[i-1]:
                    confirmed = True

        # Entry: fade the gap after confirmation
        if (position == 0 and entry_ok_arr[i] and not traded_today
                and confirmed and not np.isnan(prior_close)):

            if gap_direction == -1:
                # Gap down → long (fade toward prior close)
                reversion_target = session_open + (prior_close - session_open) * PARTIAL_TARGET_PCT
                initial_stop = session_low - bar_atr * ATR_STOP_MULT
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = reversion_target
                position = 1
                trailing_stop = initial_stop
                target_price = reversion_target
                highest_since_entry = high_arr[i]
                traded_today = True
                bars_in_trade = 0

            elif gap_direction == 1:
                # Gap up → short (fade toward prior close)
                reversion_target = session_open - (session_open - prior_close) * PARTIAL_TARGET_PCT
                initial_stop = session_high + bar_atr * ATR_STOP_MULT
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = reversion_target
                position = -1
                trailing_stop = initial_stop
                target_price = reversion_target
                lowest_since_entry = low_arr[i]
                traded_today = True
                bars_in_trade = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
