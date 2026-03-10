"""EMA-TREND-RIDER — EMA Pullback Trend Following.

Hand-built for Phase 10 — completes the trend family triangle:
  1. Donchian  → breakout trend (enters at new highs)
  2. VWAP Trend → continuation trend (enters at VWAP pullback)
  3. EMA Rider  → pullback trend (enters at EMA pullback in established trend)

Structurally distinct from both siblings:
- Does NOT use VWAP (unlike VWAP Trend)
- Does NOT enter at channel breakout (unlike Donchian)
- Enters at EMA pullback AFTER trend is confirmed by multi-EMA alignment
- Exit: close below fast EMA (trend exhaustion), or ATR trailing stop

Logic:
- Trend filter: EMA21 > EMA50 (long), EMA21 < EMA50 (short)
- Entry: price pulls back to EMA8 zone (within ATR proximity)
  - Long: close touches/crosses EMA8 from above, then re-enters above
  - Short: close touches/crosses EMA8 from below, then re-enters below
- Additional: EMA8 must be above EMA21 (long) for pullback-in-trend
- Stop: ATR-based, placed beyond EMA21 (structure protection)
- Exit 1: N consecutive closes below EMA8 (trend exhaustion)
- Exit 2: ATR trailing stop
- Pre-close session flatten
- Max 1 trade per direction per day

Expected behavior:
- Win rate 40-50% (pullback entries in confirmed trends)
- Median hold time 40-100+ bars (trend-riding DNA)
- Profits in LOW_RV grinding trends (structural edge)

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

EMA_FAST = 13             # Fast EMA for pullback entry/exit (~1hr on 5m)
EMA_MID = 21              # Mid EMA for trend structure
EMA_SLOW = 50             # Slow EMA for trend confirmation
ATR_PERIOD = 14           # ATR period for stop calculation
ATR_STOP_MULT = 2.5       # Initial stop = entry ± ATR × mult (beyond EMA21)
ATR_TRAIL_MULT = 3.0      # Trailing stop distance = ATR × mult (wider for trends)
PULLBACK_PROXIMITY = 0.6  # Entry zone: within ATR × mult of fast EMA
MIN_HOLD_BARS = 15        # Min bars before EMA exit activates (75 min floor)
CONSEC_CROSS = 3          # Consecutive closes beyond fast EMA to trigger exit
MIN_TREND_BARS = 12       # Min bars EMA21 > EMA50 before entries allowed

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "09:45"     # Brief warmup for EMA stabilization
ENTRY_CUTOFF = "14:30"    # Need room for trend to develop
FLATTEN_TIME = "15:30"    # Pre-close flatten

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate EMA pullback trend signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # ── EMAs ─────────────────────────────────────────────────────────
    ema_fast = df["close"].ewm(span=EMA_FAST, adjust=False).mean().values
    ema_mid = df["close"].ewm(span=EMA_MID, adjust=False).mean().values
    ema_slow = df["close"].ewm(span=EMA_SLOW, adjust=False).mean().values

    # ── ATR for stops ────────────────────────────────────────────────
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # ── Pre-compute arrays ───────────────────────────────────────────
    close_arr = df["close"].values
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

    # ── Stateful loop ────────────────────────────────────────────────
    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    bars_in_trade = 0
    consec_against = 0

    # Trend alignment tracking
    bars_trend_up = 0     # Consecutive bars with EMA21 > EMA50
    bars_trend_down = 0   # Consecutive bars with EMA21 < EMA50

    # Pullback state tracking
    was_above_ema8 = False   # Was price above EMA8 before pullback?
    was_below_ema8 = False

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_ema_fast = ema_fast[i]
        bar_ema_mid = ema_mid[i]
        bar_ema_slow = ema_slow[i]

        # ── Day reset ────────────────────────────────────────────────
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False
            was_above_ema8 = False
            was_below_ema8 = False
            # Don't reset trend counters — trend persists across days

        if not in_session_arr[i]:
            continue

        if np.isnan(bar_atr) or np.isnan(bar_ema_fast) or np.isnan(bar_ema_slow):
            continue

        # ── Track trend alignment ────────────────────────────────────
        if bar_ema_mid > bar_ema_slow:
            bars_trend_up += 1
            bars_trend_down = 0
        elif bar_ema_mid < bar_ema_slow:
            bars_trend_down += 1
            bars_trend_up = 0

        # ── Track pullback state ─────────────────────────────────────
        if close_arr[i] > bar_ema_fast:
            was_above_ema8 = True
        elif close_arr[i] < bar_ema_fast:
            was_below_ema8 = True

        # ── Pre-close flatten ────────────────────────────────────────
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # ── Check exits for open position ────────────────────────────
        if position == 1:
            bars_in_trade += 1

            # Update trailing stop
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Track consecutive closes below EMA8 (trend exhaustion)
            if close_arr[i] < bar_ema_fast:
                consec_against += 1
            else:
                consec_against = 0

            # Exit 1: EMA8 exhaustion exit (after min hold)
            if bars_in_trade >= MIN_HOLD_BARS and consec_against >= CONSEC_CROSS:
                exit_sigs[i] = 1
                position = 0

            # Exit 2: Trailing stop hit
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            bars_in_trade += 1

            # Update trailing stop
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]
                new_trail = lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            # Track consecutive closes above EMA8
            if close_arr[i] > bar_ema_fast:
                consec_against += 1
            else:
                consec_against = 0

            # Exit 1: EMA8 exhaustion exit
            if bars_in_trade >= MIN_HOLD_BARS and consec_against >= CONSEC_CROSS:
                exit_sigs[i] = -1
                position = 0

            # Exit 2: Trailing stop hit
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # ── Entry: Pullback to EMA8 in confirmed trend ───────────────
        if position == 0 and entry_ok_arr[i]:

            # Proximity check: price near EMA8
            ema8_dist = abs(close_arr[i] - bar_ema_fast)
            in_pullback_zone = ema8_dist <= bar_atr * PULLBACK_PROXIMITY

            # ── Long entry ───────────────────────────────────────────
            # Conditions:
            # 1. EMA21 > EMA50 for MIN_TREND_BARS (confirmed uptrend)
            # 2. EMA8 > EMA21 (fast above mid — trend is healthy)
            # 3. Price pulled back near EMA8 (in pullback zone)
            # 4. Close is above EMA8 (re-entered the fast trend)
            # 5. Price was above EMA8 before (this is a pullback, not first touch)
            if (not long_traded_today
                and bars_trend_up >= MIN_TREND_BARS
                and bar_ema_fast > bar_ema_mid
                and close_arr[i] > bar_ema_fast
                and in_pullback_zone
                and was_above_ema8):

                # Verify there was an actual pullback: check that price
                # was below or near EMA8 recently (last 5 bars)
                had_pullback = False
                for j in range(max(0, i - 5), i):
                    if close_arr[j] <= ema_fast[j] * 1.001:  # At or below EMA8
                        had_pullback = True
                        break

                if had_pullback:
                    # Stop beyond EMA21 for structure protection
                    stop_level = min(bar_ema_mid, close_arr[i] - bar_atr * ATR_STOP_MULT)
                    signals_arr[i] = 1
                    stop_arr[i] = stop_level
                    target_arr[i] = np.nan
                    position = 1
                    entry_price = close_arr[i]
                    trailing_stop = stop_level
                    highest_since_entry = high_arr[i]
                    long_traded_today = True
                    bars_in_trade = 0
                    consec_against = 0
                    was_above_ema8 = False  # Reset for next pullback

            # ── Short entry ──────────────────────────────────────────
            elif (not short_traded_today
                  and bars_trend_down >= MIN_TREND_BARS
                  and bar_ema_fast < bar_ema_mid
                  and close_arr[i] < bar_ema_fast
                  and in_pullback_zone
                  and was_below_ema8):

                had_pullback = False
                for j in range(max(0, i - 5), i):
                    if close_arr[j] >= ema_fast[j] * 0.999:
                        had_pullback = True
                        break

                if had_pullback:
                    stop_level = max(bar_ema_mid, close_arr[i] + bar_atr * ATR_STOP_MULT)
                    signals_arr[i] = -1
                    stop_arr[i] = stop_level
                    target_arr[i] = np.nan
                    position = -1
                    entry_price = close_arr[i]
                    trailing_stop = stop_level
                    lowest_since_entry = low_arr[i]
                    short_traded_today = True
                    bars_in_trade = 0
                    consec_against = 0
                    was_below_ema8 = False

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
