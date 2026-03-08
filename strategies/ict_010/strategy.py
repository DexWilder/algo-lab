"""ICT-010 — Captain Backtest Model [TFO].

Source: tradeforopp — Captain Backtest Model [TFO]
URL: https://www.tradingview.com/script/tOQ8gnxj-Captain-Backtest-Model-TFO/
Family: ICT
Conversion: Faithful — no optimization, original parameters preserved.

State machine: WAITING → RANGE_FORMED → SWEEP_DETECTED → PULLBACK_ENTRY
Session range sweep determines bias, then enters on pullback confirmation.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

RANGE_MINUTES = 30         # First 30 min = range (09:30-10:00 ET)
SWEEP_DEADLINE = "11:15"   # Sweep must occur by 11:15 ET
ENTRY_DEADLINE = "14:00"   # Entry must occur by 14:00 ET
RR_RATIO = 2.0             # Risk:reward = 1:2

SESSION_START = "09:30"
RANGE_END = "10:00"
SESSION_END = "15:15"

# Fixed stop distances per asset (points)
STOP_POINTS = {
    "MES": 5.0,
    "MNQ": 25.0,
    "MGC": 5.0,
}
DEFAULT_STOP_POINTS = 5.0

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, asset: str = "MES") -> pd.DataFrame:
    """Generate ICT session sweep → pullback signals.

    State machine resets daily:
    1. RANGE (09:30-10:00): Track range high/low
    2. SWEEP (10:00-11:15): Detect wick sweep of range, set bias
    3. ENTRY (after sweep, before 14:00): Enter on pullback confirmation
    Max 1 trade per day.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    stop_pts = STOP_POINTS.get(asset, DEFAULT_STOP_POINTS)

    # ── Build session range per day ──────────────────────────────────────
    in_range = (time_str >= SESSION_START) & (time_str < RANGE_END)
    range_bars = df[in_range].copy()

    if range_bars.empty:
        df["signal"] = 0
        df["exit_signal"] = 0
        df["stop_price"] = np.nan
        df["target_price"] = np.nan
        df.drop(columns=["_date"], inplace=True)
        return df

    range_stats = range_bars.groupby("_date").agg(
        range_high=("high", "max"),
        range_low=("low", "min"),
    )
    df = df.merge(range_stats, left_on="_date", right_index=True, how="left")

    # ── State machine (iterate bar by bar) ───────────────────────────────
    signals_arr = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)
    exit_sigs = np.zeros(n, dtype=int)

    # Daily state
    state = "WAITING"       # WAITING | RANGE_FORMED | SWEEP_LONG | SWEEP_SHORT | DONE
    current_date = None
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    pullback_armed = False  # True after pullback bar 1 detected
    traded_today = False

    for i in range(n):
        bar_date = df.iloc[i]["_date"]
        time_s = time_str.iloc[i]
        high_px = df.iloc[i]["high"]
        low_px = df.iloc[i]["low"]
        close_px = df.iloc[i]["close"]
        r_high = df.iloc[i]["range_high"]
        r_low = df.iloc[i]["range_low"]

        # Day reset
        if bar_date != current_date:
            current_date = bar_date
            state = "WAITING"
            pullback_armed = False
            traded_today = False
            prev_high = np.nan
            prev_low = np.nan

        # EOD flatten
        if position != 0 and time_s >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Check stop/target for open position
        if position == 1:
            if low_px <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            elif high_px >= entry_target:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            if high_px >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            elif low_px <= entry_target:
                exit_sigs[i] = -1
                position = 0

        # ── Phase 1: Range formation ────────────────────────────────────
        if state == "WAITING" and time_s >= RANGE_END and pd.notna(r_high):
            state = "RANGE_FORMED"

        # ── Phase 2: Sweep detection ────────────────────────────────────
        if state == "RANGE_FORMED" and not traded_today:
            if time_s > SWEEP_DEADLINE:
                state = "DONE"  # No sweep by deadline
            elif pd.notna(r_low) and pd.notna(r_high):
                # Low sweep: wick below range_low, close above → LONG bias
                if low_px < r_low and close_px > r_low:
                    state = "SWEEP_LONG"
                    pullback_armed = False
                # High sweep: wick above range_high, close below → SHORT bias
                elif high_px > r_high and close_px < r_high:
                    state = "SWEEP_SHORT"
                    pullback_armed = False

        # ── Phase 3: Pullback entry ─────────────────────────────────────
        if state in ("SWEEP_LONG", "SWEEP_SHORT") and position == 0 and not traded_today:
            if time_s >= ENTRY_DEADLINE:
                state = "DONE"
            elif pd.notna(prev_high) and pd.notna(prev_low):
                if state == "SWEEP_LONG":
                    # Bar 1: close below prior bar's low
                    if not pullback_armed:
                        if close_px < prev_low:
                            pullback_armed = True
                    else:
                        # Bar 2: close above prior bar's high → enter long
                        if close_px > prev_high:
                            signals_arr[i] = 1
                            stop_arr[i] = close_px - stop_pts
                            target_arr[i] = close_px + stop_pts * RR_RATIO
                            position = 1
                            entry_stop = stop_arr[i]
                            entry_target = target_arr[i]
                            traded_today = True
                            state = "DONE"
                            pullback_armed = False
                        elif close_px >= prev_low:
                            # Reset if no longer pulling back
                            pullback_armed = False

                elif state == "SWEEP_SHORT":
                    # Bar 1: close above prior bar's high
                    if not pullback_armed:
                        if close_px > prev_high:
                            pullback_armed = True
                    else:
                        # Bar 2: close below prior bar's low → enter short
                        if close_px < prev_low:
                            signals_arr[i] = -1
                            stop_arr[i] = close_px + stop_pts
                            target_arr[i] = close_px - stop_pts * RR_RATIO
                            position = -1
                            entry_stop = stop_arr[i]
                            entry_target = target_arr[i]
                            traded_today = True
                            state = "DONE"
                            pullback_armed = False
                        elif close_px <= prev_high:
                            pullback_armed = False

        prev_high = high_px
        prev_low = low_px

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date", "range_high", "range_low"], inplace=True, errors="ignore")

    return df
