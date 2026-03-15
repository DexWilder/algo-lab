"""Russell ORB — Opening Range Breakout for M2K (Micro Russell 2000), Long-Side Focus.

Source: Academic ORB research — 15-minute opening range breakout.
Asset: M2K (Micro Russell 2000 futures)

Logic:
  1. Compute 15-minute opening range (09:30-09:45 ET): high and low of that window.
  2. After 09:45, if price breaks ABOVE the opening range high -> go long.
  3. Stop: below the opening range low (or ATR-based backstop, whichever is tighter).
  4. Target: 2x the opening range width from entry.
  5. Exit by 15:30 ET (EOD flatten).
  6. Filters:
     - Only trade if OR width > 0.5 * ATR and < 2.0 * ATR.
     - One trade per day maximum.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

ATR_PERIOD = 14             # ATR period (EWM)
OR_WIDTH_MIN = 0.5          # Minimum OR width as fraction of ATR
OR_WIDTH_MAX = 2.0          # Maximum OR width as fraction of ATR
TP_MULT = 2.0               # Target = entry + OR_range * 2.0

SESSION_START = "09:30"
OR_END = "09:45"            # 15-minute opening range
ENTRY_CUTOFF = "14:30"      # No new entries after 14:30
FLATTEN_TIME = "15:30"      # EOD flatten
SESSION_END = "15:45"       # Session boundary

TICK_SIZE = 0.10            # M2K tick size


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _round_tick(price: float, tick: float) -> float:
    """Round price to nearest tick."""
    return round(round(price / tick) * tick, 10)


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate Russell ORB long-only breakout signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── ATR (EWM) ─────────────────────────────────────────────────────────
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # ── Pre-compute arrays ────────────────────────────────────────────────
    close_arr = df["close"].values
    open_arr = df["open"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    dates_arr = df["_date"].values
    time_arr = time_str.values

    # ── Output arrays ─────────────────────────────────────────────────────
    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # ── State tracking ────────────────────────────────────────────────────
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    traded_today = False
    current_date = None

    # Opening range state (built bar-by-bar during 09:30-09:45)
    or_high = -np.inf
    or_low = np.inf
    or_ready = False        # True once we pass OR_END

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]

        # ── New day reset ─────────────────────────────────────────────
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1  # long-only, so always exit long
                position = 0
            current_date = bar_date
            traded_today = False
            or_high = -np.inf
            or_low = np.inf
            or_ready = False

        # ── Session filter ────────────────────────────────────────────
        if bar_time < SESSION_START or bar_time >= SESSION_END:
            continue
        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # ── Build opening range (09:30 <= time < 09:45) ──────────────
        if bar_time >= SESSION_START and bar_time < OR_END:
            if high_arr[i] > or_high:
                or_high = high_arr[i]
            if low_arr[i] < or_low:
                or_low = low_arr[i]
            continue  # No trading during OR window

        # ── Mark OR as ready once we exit the OR window ───────────────
        if not or_ready:
            if or_high == -np.inf or or_low == np.inf:
                continue  # No OR data yet (shouldn't happen after OR_END)
            or_ready = True

        # ── EOD flatten ───────────────────────────────────────────────
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1  # long-only exit
            position = 0
            continue

        # ── Exit logic: stop and target ───────────────────────────────
        if position == 1:
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
                continue
            if high_arr[i] >= entry_target:
                exit_sigs[i] = 1
                position = 0
                continue

        # ── Entry logic (long only) ──────────────────────────────────
        if position == 0 and not traded_today and bar_time >= OR_END and bar_time < ENTRY_CUTOFF:
            or_range = or_high - or_low

            # Filter: OR width must be between 0.5x and 2.0x ATR
            if or_range < OR_WIDTH_MIN * bar_atr:
                continue
            if or_range > OR_WIDTH_MAX * bar_atr:
                continue

            # Breakout: close above opening range high
            if close_arr[i] > or_high:
                # Stop: OR low or ATR backstop, whichever is tighter (higher)
                stop_or = _round_tick(or_low, TICK_SIZE)
                stop_atr = _round_tick(close_arr[i] - bar_atr, TICK_SIZE)
                stop = max(stop_or, stop_atr)

                # Target: 2x OR range from entry
                target = _round_tick(close_arr[i] + or_range * TP_MULT, TICK_SIZE)

                signals_arr[i] = 1
                stop_arr[i] = stop
                target_arr[i] = target
                entry_stop = stop
                entry_target = target
                position = 1
                traded_today = True

    # ── Assign outputs ────────────────────────────────────────────────────
    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr

    # ── Drop temp columns ─────────────────────────────────────────────────
    df.drop(columns=["_date"], inplace=True, errors="ignore")
    return df
