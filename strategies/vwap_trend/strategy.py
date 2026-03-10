"""VWAP-TREND — VWAP Trend Continuation (Pullback Entry).

Hand-built for Phase 10 — targets HIGH_VOL_TRENDING_LOW_RV regime.
Designed for sustained directional grinds where breakout entries fail.

Logic:
- Trend filter: EMA slope confirms direction
- Entry: price pulls back to session VWAP after establishing trend
  - Long: price was above VWAP, pulls back to touch/cross VWAP, re-enters above
  - Short: price was below VWAP, pulls back to touch/cross VWAP, re-enters below
- Stop: ATR-based, placed beyond VWAP (tighter than breakout stops)
- Exit: close crosses VWAP against position, or ATR trailing stop
- Pre-close session flatten
- Max 1 trade per direction per day

Why this is structurally different from Donchian/Keltner:
- Does NOT need a breakout or new high/low
- Enters at pullback (better price, tighter stop)
- Works in LOW_RV because entry is at natural support (VWAP)
- VWAP acts as dynamic support/resistance in trending markets

Expected behavior:
- Win rate 40-55% (pullback entries have better fills)
- Median hold time 40-100 bars (trend continuation DNA)
- Should profit in LOW_RV grinding environments

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

TREND_EMA_LEN = 20        # EMA period for trend confirmation
TREND_SLOPE_BARS = 5      # Bars to compute EMA slope over
ATR_PERIOD = 14           # ATR period for stop calculation
ATR_STOP_MULT = 1.5       # Initial stop = entry ± ATR × mult (tighter — VWAP is support)
ATR_TRAIL_MULT = 2.5      # Trailing stop distance = ATR × mult
VWAP_PROXIMITY = 0.5      # Pullback zone: within ATR × 0.5 of VWAP (wider for more trades)
MIN_TREND_BARS = 6        # Min bars above/below VWAP before pullback counts
MIN_HOLD_BARS = 10        # Min bars before VWAP exit activates (avoid 5m noise)
CONSEC_CROSS = 2          # Require N consecutive closes below VWAP to exit

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "10:00"     # Wait for VWAP to stabilize (30 min)
ENTRY_CUTOFF = "14:30"    # Later cutoff — continuation trades need less room
FLATTEN_TIME = "15:30"    # Pre-close flatten

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_session_vwap(df: pd.DataFrame) -> np.ndarray:
    """Compute session-anchored VWAP (resets each day)."""
    dt = pd.to_datetime(df["datetime"])
    dates = dt.dt.date.values
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values if "volume" in df.columns else np.ones(len(df))

    # Typical price
    tp = (high + low + close) / 3.0

    n = len(df)
    vwap = np.full(n, np.nan)
    cum_tp_vol = 0.0
    cum_vol = 0.0
    current_date = None

    for i in range(n):
        if dates[i] != current_date:
            current_date = dates[i]
            cum_tp_vol = 0.0
            cum_vol = 0.0

        vol = max(volume[i], 1.0)  # Avoid zero volume
        cum_tp_vol += tp[i] * vol
        cum_vol += vol
        vwap[i] = cum_tp_vol / cum_vol

    return vwap


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate VWAP trend continuation signals with pullback entries.

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

    # ── VWAP ─────────────────────────────────────────────────────────
    vwap = _compute_session_vwap(df)

    # ── Trend EMA ────────────────────────────────────────────────────
    ema = df["close"].ewm(span=TREND_EMA_LEN, adjust=False).mean().values

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

    # Pullback tracking
    bars_above_vwap = 0     # Consecutive bars with close > VWAP
    bars_below_vwap = 0     # Consecutive bars with close < VWAP
    bars_in_trade = 0       # Bars since entry
    consec_against = 0      # Consecutive closes against position (for exit)

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_vwap = vwap[i]
        bar_ema = ema[i]

        # ── Day reset ────────────────────────────────────────────────
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False
            bars_above_vwap = 0
            bars_below_vwap = 0

        if not in_session_arr[i]:
            continue

        if np.isnan(bar_vwap) or np.isnan(bar_atr) or np.isnan(bar_ema):
            continue

        # ── Track VWAP position ──────────────────────────────────────
        if close_arr[i] > bar_vwap:
            bars_above_vwap += 1
            bars_below_vwap = 0
        elif close_arr[i] < bar_vwap:
            bars_below_vwap += 1
            bars_above_vwap = 0
        # Close == VWAP: don't reset either counter

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

            # Track consecutive closes below VWAP
            if close_arr[i] < bar_vwap:
                consec_against += 1
            else:
                consec_against = 0

            # Exit 1: Confirmed VWAP cross (N consecutive closes below VWAP)
            # Only after minimum hold to avoid 5m noise
            if bars_in_trade >= MIN_HOLD_BARS and consec_against >= CONSEC_CROSS:
                exit_sigs[i] = 1
                position = 0

            # Exit 2: Trailing stop hit (always active)
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

            # Track consecutive closes above VWAP
            if close_arr[i] > bar_vwap:
                consec_against += 1
            else:
                consec_against = 0

            # Exit 1: Confirmed VWAP cross
            if bars_in_trade >= MIN_HOLD_BARS and consec_against >= CONSEC_CROSS:
                exit_sigs[i] = -1
                position = 0

            # Exit 2: Trailing stop hit
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # ── Entry: Pullback to VWAP in trend ─────────────────────────
        if position == 0 and entry_ok_arr[i]:

            # Proximity check: price near VWAP
            vwap_dist = abs(close_arr[i] - bar_vwap)
            in_pullback_zone = vwap_dist <= bar_atr * VWAP_PROXIMITY

            # Trend direction from EMA slope
            if i >= TREND_SLOPE_BARS:
                ema_slope = (ema[i] - ema[i - TREND_SLOPE_BARS]) / TREND_SLOPE_BARS
            else:
                ema_slope = 0.0

            # ── Long entry ───────────────────────────────────────────
            # Conditions:
            # 1. EMA trending up (positive slope)
            # 2. Price was above VWAP for MIN_TREND_BARS (established trend)
            # 3. Price pulled back near VWAP (in pullback zone)
            # 4. Close is above VWAP (re-entered the trend)
            if (not long_traded_today
                and ema_slope > 0
                and bars_above_vwap >= 1  # Just crossed back above
                and close_arr[i] > bar_vwap
                and in_pullback_zone):

                # Check recent history: was price above VWAP before the pullback?
                # Look back to find if we had MIN_TREND_BARS above VWAP recently
                had_trend = False
                lookback_start = max(0, i - MIN_TREND_BARS - 10)
                consecutive = 0
                for j in range(lookback_start, i):
                    if not np.isnan(vwap[j]) and close_arr[j] > vwap[j]:
                        consecutive += 1
                        if consecutive >= MIN_TREND_BARS:
                            had_trend = True
                            break
                    else:
                        consecutive = 0

                if had_trend:
                    initial_stop = bar_vwap - bar_atr * ATR_STOP_MULT
                    signals_arr[i] = 1
                    stop_arr[i] = initial_stop
                    target_arr[i] = np.nan
                    position = 1
                    entry_price = close_arr[i]
                    trailing_stop = initial_stop
                    highest_since_entry = high_arr[i]
                    long_traded_today = True
                    bars_in_trade = 0
                    consec_against = 0

            # ── Short entry ──────────────────────────────────────────
            elif (not short_traded_today
                  and ema_slope < 0
                  and bars_below_vwap >= 1
                  and close_arr[i] < bar_vwap
                  and in_pullback_zone):

                had_trend = False
                lookback_start = max(0, i - MIN_TREND_BARS - 10)
                consecutive = 0
                for j in range(lookback_start, i):
                    if not np.isnan(vwap[j]) and close_arr[j] < vwap[j]:
                        consecutive += 1
                        if consecutive >= MIN_TREND_BARS:
                            had_trend = True
                            break
                    else:
                        consecutive = 0

                if had_trend:
                    initial_stop = bar_vwap + bar_atr * ATR_STOP_MULT
                    signals_arr[i] = -1
                    stop_arr[i] = initial_stop
                    target_arr[i] = np.nan
                    position = -1
                    entry_price = close_arr[i]
                    trailing_stop = initial_stop
                    lowest_since_entry = low_arr[i]
                    short_traded_today = True
                    bars_in_trade = 0
                    consec_against = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
