"""TREND-CONTINUATION — Multi-Bar Consolidation Breakout in Trend.

!!! BROKEN — DO NOT TEST !!!
Discovered 2026-04-08: produces 0 signals across 474K MES bars despite
clean signature and no errors. The multi-bar consolidation tracking logic
has a latent bug that never fires entries. Silent failure detector in
batch_first_pass now flags it if run.

Left in place for historical reference. To re-enable: debug the
consolidation state machine in the main loop, remove BROKEN flag, and
re-run through mass_screen.

Tail engine strategy — low frequency, large winners, convex payoff.
Targets sustained trend moves after tight consolidation near the 20-EMA.

Logic:
- Trend: triple EMA alignment (20 > 50 > 100 for longs, reversed for shorts)
- Pullback: price retraces within 0.5x ATR of the 20-EMA
- Consolidation: at least 5 bars near 20-EMA with range < 1.0x ATR
- Breakout: price breaks above consolidation high (long) with volume > 1.2x avg
- EMA slope filter: 50-EMA must slope in trade direction over last 10 bars
- Stop: below consolidation low (longs), above consolidation high (shorts)
- Target: 4.0x ATR — designed for large trend captures
- Trail: after 1.5R, trail at 2.0x ATR from highest high since entry

Expected behavior:
- Low win rate (25-40%), very large average winners
- Trades clustered on trending days after pullback compression
- Median hold time 40-100+ bars

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# Broken flag — honored by mass_screen to skip this strategy in auto-testing.
# Remove this line once the consolidation state machine is debugged.
BROKEN = True


# ── Parameters ───────────────────────────────────────────────────────────────

# EMA setup
EMA_FAST = 20              # Fast EMA for trend + pullback detection
EMA_MID = 50               # Mid EMA for trend alignment + slope filter
EMA_SLOW = 100             # Slow EMA for trend alignment

# Pullback & consolidation
PULLBACK_ATR_DIST = 0.5    # Max distance from 20-EMA to count as "near" (ATR mult)
CONSOL_MIN_BARS = 5        # Min bars in consolidation zone before breakout
CONSOL_MAX_RANGE_ATR = 1.0 # Max range of consolidation (ATR mult)
CONSOL_MAX_BARS = 30       # Consolidation resets after this many bars (stale)

# Breakout & volume
VOLUME_MULT = 1.2          # Breakout bar volume must exceed avg × this
VOLUME_AVG_PERIOD = 20     # Volume average lookback

# ATR
ATR_PERIOD = 14            # ATR period for stops and sizing

# Risk & reward
TARGET_ATR_MULT = 4.0      # Target = entry ± ATR × mult
STOP_BUFFER_ATR = 0.1      # Extra buffer below consol low / above consol high
TRAIL_ACTIVATION_R = 1.5   # Start trailing after this R-multiple
ATR_TRAIL_MULT = 2.0       # Trail distance = ATR × mult from peak

# EMA slope filter
SLOPE_LOOKBACK = 10        # Bars to measure 50-EMA slope

# Session & cooldown
SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_CUTOFF = "14:00"     # No entries after 14:00
FLATTEN_TIME = "15:30"     # Pre-close flatten
COOLDOWN_BARS = 20         # Min bars between trades

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _round_to_tick(price: float) -> float:
    """Round price to nearest tick."""
    if TICK_SIZE <= 0:
        return price
    return round(round(price / TICK_SIZE) * TICK_SIZE, 10)


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate trend continuation breakout signals.

    Stateful consolidation tracking: when price is near 20-EMA in a trending
    market, track the consolidation high/low and bar count. Fire a signal
    when price breaks out of the consolidation range on above-average volume.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= SESSION_START) & (time_str < ENTRY_CUTOFF)

    # ── EMAs ──────────────────────────────────────────────────────────
    ema_fast = df["close"].ewm(span=EMA_FAST, adjust=False).mean()
    ema_mid = df["close"].ewm(span=EMA_MID, adjust=False).mean()
    ema_slow = df["close"].ewm(span=EMA_SLOW, adjust=False).mean()

    # ── ATR ───────────────────────────────────────────────────────────
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean()

    # ── Volume average ────────────────────────────────────────────────
    vol_avg = df["volume"].rolling(window=VOLUME_AVG_PERIOD, min_periods=VOLUME_AVG_PERIOD).mean()

    # ── EMA slope (50-EMA change over SLOPE_LOOKBACK bars) ────────────
    ema_mid_slope = ema_mid - ema_mid.shift(SLOPE_LOOKBACK)

    # ── Pre-compute arrays for stateful loop ──────────────────────────
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    volume_arr = df["volume"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values

    ema_fast_arr = ema_fast.values
    ema_mid_arr = ema_mid.values
    ema_slow_arr = ema_slow.values
    atr_arr = atr.values
    vol_avg_arr = vol_avg.values
    ema_slope_arr = ema_mid_slope.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # ── Consolidation state ───────────────────────────────────────────
    consol_active = False         # Currently tracking a consolidation
    consol_direction = 0          # 1 = long setup, -1 = short setup
    consol_high = 0.0             # Highest high during consolidation
    consol_low = 0.0              # Lowest low during consolidation
    consol_bar_count = 0          # How many bars in current consolidation

    # ── Trade state ───────────────────────────────────────────────────
    position = 0
    entry_price = 0.0
    initial_risk = 0.0            # |entry - stop| for R-multiple calc
    trailing_stop = 0.0
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    trail_activated = False

    current_date = None
    bars_since_last_trade = COOLDOWN_BARS  # Allow first trade immediately

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr_arr[i]

        bars_since_last_trade += 1

        # ── Day reset ────────────────────────────────────────────────
        if bar_date != current_date:
            # Force close any open position from previous day
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
                trail_activated = False
            current_date = bar_date
            # Reset consolidation on new day (avoid overnight gaps)
            consol_active = False
            consol_bar_count = 0

        if not in_session_arr[i]:
            continue

        # ── Pre-close flatten ────────────────────────────────────────
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            trail_activated = False
            continue

        # ── Check exits for open position ────────────────────────────
        if position == 1:
            # Update highest since entry
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]

            # Check if trailing should activate (1.5R reached)
            if not trail_activated and initial_risk > 0:
                unrealized_r = (highest_since_entry - entry_price) / initial_risk
                if unrealized_r >= TRAIL_ACTIVATION_R:
                    trail_activated = True
                    trailing_stop = _round_to_tick(
                        highest_since_entry - bar_atr * ATR_TRAIL_MULT
                    )

            # Update trail if active
            if trail_activated:
                new_trail = _round_to_tick(
                    highest_since_entry - bar_atr * ATR_TRAIL_MULT
                )
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Check stop hit (trailing_stop holds initial stop until trail activates)
            if low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0
                trail_activated = False
                bars_since_last_trade = 0

        elif position == -1:
            # Update lowest since entry
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]

            # Check if trailing should activate (1.5R reached)
            if not trail_activated and initial_risk > 0:
                unrealized_r = (entry_price - lowest_since_entry) / initial_risk
                if unrealized_r >= TRAIL_ACTIVATION_R:
                    trail_activated = True
                    trailing_stop = _round_to_tick(
                        lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                    )

            # Update trail if active
            if trail_activated:
                new_trail = _round_to_tick(
                    lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                )
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            # Check stop hit (trailing_stop holds initial stop until trail activates)
            if high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0
                trail_activated = False
                bars_since_last_trade = 0

        # ── Skip entry logic if in position or cooling down ──────────
        if position != 0:
            # Still update consolidation tracking while in position
            continue

        if not entry_ok_arr[i]:
            continue

        if bars_since_last_trade < COOLDOWN_BARS:
            continue

        # ── Guard: need valid indicators ─────────────────────────────
        if (np.isnan(bar_atr) or np.isnan(ema_fast_arr[i])
                or np.isnan(ema_mid_arr[i]) or np.isnan(ema_slow_arr[i])
                or np.isnan(vol_avg_arr[i]) or np.isnan(ema_slope_arr[i])):
            continue

        if bar_atr <= 0:
            continue

        # ── Determine trend direction ────────────────────────────────
        long_trend = (ema_fast_arr[i] > ema_mid_arr[i] > ema_slow_arr[i]
                      and ema_slope_arr[i] > 0)
        short_trend = (ema_fast_arr[i] < ema_mid_arr[i] < ema_slow_arr[i]
                       and ema_slope_arr[i] < 0)

        if not long_trend and not short_trend:
            # No valid trend — reset consolidation
            consol_active = False
            consol_bar_count = 0
            continue

        current_direction = 1 if long_trend else -1

        # ── Check if price is near 20-EMA (pullback zone) ───────────
        dist_to_ema = abs(close_arr[i] - ema_fast_arr[i])
        near_ema = dist_to_ema <= PULLBACK_ATR_DIST * bar_atr

        if near_ema:
            if not consol_active or consol_direction != current_direction:
                # Start new consolidation
                consol_active = True
                consol_direction = current_direction
                consol_high = high_arr[i]
                consol_low = low_arr[i]
                consol_bar_count = 1
            else:
                # Extend existing consolidation
                consol_high = max(consol_high, high_arr[i])
                consol_low = min(consol_low, low_arr[i])
                consol_bar_count += 1

                # Check if consolidation range is too wide (not tight)
                if (consol_high - consol_low) > CONSOL_MAX_RANGE_ATR * bar_atr:
                    # Reset — consolidation is too loose
                    consol_active = False
                    consol_bar_count = 0
                    continue

                # Check if consolidation is too old
                if consol_bar_count > CONSOL_MAX_BARS:
                    consol_active = False
                    consol_bar_count = 0
                    continue
        else:
            # Price moved away from EMA — check for breakout or reset
            if consol_active and consol_bar_count >= CONSOL_MIN_BARS:
                consol_range = consol_high - consol_low

                # Verify consolidation was tight enough
                if consol_range <= CONSOL_MAX_RANGE_ATR * bar_atr:
                    # ── Long breakout ────────────────────────────────
                    if (consol_direction == 1
                            and close_arr[i] > consol_high
                            and volume_arr[i] > VOLUME_MULT * vol_avg_arr[i]):

                        stop = _round_to_tick(
                            consol_low - STOP_BUFFER_ATR * bar_atr
                        )
                        risk = close_arr[i] - stop
                        if risk <= 0:
                            consol_active = False
                            consol_bar_count = 0
                            continue

                        target = _round_to_tick(
                            close_arr[i] + TARGET_ATR_MULT * bar_atr
                        )

                        signals_arr[i] = 1
                        stop_arr[i] = stop
                        target_arr[i] = target
                        position = 1
                        entry_price = close_arr[i]
                        initial_risk = risk
                        trailing_stop = stop
                        highest_since_entry = high_arr[i]
                        trail_activated = False
                        bars_since_last_trade = 0

                        # Reset consolidation after entry
                        consol_active = False
                        consol_bar_count = 0
                        continue

                    # ── Short breakout ───────────────────────────────
                    elif (consol_direction == -1
                            and close_arr[i] < consol_low
                            and volume_arr[i] > VOLUME_MULT * vol_avg_arr[i]):

                        stop = _round_to_tick(
                            consol_high + STOP_BUFFER_ATR * bar_atr
                        )
                        risk = stop - close_arr[i]
                        if risk <= 0:
                            consol_active = False
                            consol_bar_count = 0
                            continue

                        target = _round_to_tick(
                            close_arr[i] - TARGET_ATR_MULT * bar_atr
                        )

                        signals_arr[i] = -1
                        stop_arr[i] = stop
                        target_arr[i] = target
                        position = -1
                        entry_price = close_arr[i]
                        initial_risk = risk
                        trailing_stop = stop
                        lowest_since_entry = low_arr[i]
                        trail_activated = False
                        bars_since_last_trade = 0

                        # Reset consolidation after entry
                        consol_active = False
                        consol_bar_count = 0
                        continue

            # Not a valid breakout — reset consolidation
            consol_active = False
            consol_bar_count = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
