"""ORB Fade — Opening Range False Breakout Reversion.

Detects failed OR breakouts and fades them back to OR midpoint.
Structurally opposite of ORB-009 (which takes continuation).
Should be negatively correlated with ORB-009 by construction.

Logic:
- Compute opening range (first 6 bars = 30 min)
- Wait for breakout attempt that FAILS (price breaks OR then reverses inside)
- Entry: false breakout confirmed (close back inside OR after breakout)
- Target: OR midpoint (mean reversion to center)
- Filter: ADX < 25 (ranging), OR width < 50th percentile (tight range)

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

OR_BARS = 6                   # First 6 bars = 30 min opening range
OR_WIDTH_MAX_PCTILE = 50      # Only trade tight OR (bottom 50%)
OR_WIDTH_LOOKBACK = 50        # Rolling lookback for OR width ranking

ADX_PERIOD = 14
ADX_THRESHOLD = 25            # Only trade when ADX < 25 (ranging)
CONFIRM_BARS = 5              # Max bars outside OR before entry opportunity expires

ATR_PERIOD = 14
ATR_CUSHION = 0.5             # Stop = breakout extreme + 0.5 ATR
MIN_HOLD_BARS = 2

SESSION_START = "09:30"
SESSION_END = "15:45"
OR_END = "10:00"
ENTRY_START = "10:00"
ENTRY_CUTOFF = "14:00"
FLATTEN_TIME = "15:30"

TICK_SIZE = 0.25


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    plus_dm = (high - prev_high).clip(lower=0)
    minus_dm = (prev_low - low).clip(lower=0)
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    atr_vals = _atr(high, low, close, period)
    plus_di = 100 * _ema(plus_dm, period) / atr_vals.replace(0, np.nan)
    minus_di = 100 * _ema(minus_dm, period) / atr_vals.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _ema(dx, period)


# ── Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    # Compute OR high/low per day
    in_or = (time_str >= SESSION_START) & (time_str < OR_END)
    or_bars_df = df[in_or].copy()

    if or_bars_df.empty:
        df["signal"] = 0
        df["exit_signal"] = 0
        df["stop_price"] = np.nan
        df["target_price"] = np.nan
        df.drop(columns=["_date"], inplace=True, errors="ignore")
        return df

    or_stats = or_bars_df.groupby("_date").agg(
        or_high=("high", "max"),
        or_low=("low", "min"),
    )
    or_stats["or_range"] = or_stats["or_high"] - or_stats["or_low"]
    or_stats["or_mid"] = (or_stats["or_high"] + or_stats["or_low"]) / 2

    # OR width percentile rank (rolling)
    or_width_series = or_stats["or_range"]
    or_stats["or_width_pctrank"] = or_width_series.rolling(
        window=OR_WIDTH_LOOKBACK, min_periods=10
    ).apply(lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False)

    df = df.merge(or_stats, left_on="_date", right_index=True, how="left")

    # ATR and ADX
    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD).values
    adx = _adx(df["high"], df["low"], df["close"], ADX_PERIOD).values

    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    or_high_arr = df["or_high"].values if "or_high" in df.columns else np.full(n, np.nan)
    or_low_arr = df["or_low"].values if "or_low" in df.columns else np.full(n, np.nan)
    or_mid_arr = df["or_mid"].values if "or_mid" in df.columns else np.full(n, np.nan)
    or_pctrank_arr = df["or_width_pctrank"].values if "or_width_pctrank" in df.columns else np.full(n, np.nan)

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    trailing_stop = 0.0
    target_price = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    bars_in_trade = 0

    # False breakout tracking per day
    broke_below = False
    broke_above = False
    bars_since_break_below = 0
    bars_since_break_above = 0
    breakout_low_extreme = 999999.0
    breakout_high_extreme = 0.0

    for i in range(1, n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_adx = adx[i]
        bar_or_high = or_high_arr[i]
        bar_or_low = or_low_arr[i]
        bar_or_mid = or_mid_arr[i]
        bar_or_pct = or_pctrank_arr[i]

        # Day reset
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False
            broke_below = False
            broke_above = False
            bars_since_break_below = 0
            bars_since_break_above = 0
            breakout_low_extreme = 999999.0
            breakout_high_extreme = 0.0

        if not in_session_arr[i]:
            continue
        if (np.isnan(bar_atr) or np.isnan(bar_or_high) or np.isnan(bar_or_low)
                or bar_atr == 0 or np.isnan(bar_adx)):
            continue

        # Skip OR period
        if bar_time < OR_END:
            continue

        # Pre-close flatten
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Track breakout attempts
        if low_arr[i] < bar_or_low:
            if not broke_below:
                broke_below = True
                bars_since_break_below = 0
                breakout_low_extreme = low_arr[i]
            else:
                bars_since_break_below += 1
                if low_arr[i] < breakout_low_extreme:
                    breakout_low_extreme = low_arr[i]

        if high_arr[i] > bar_or_high:
            if not broke_above:
                broke_above = True
                bars_since_break_above = 0
                breakout_high_extreme = high_arr[i]
            else:
                bars_since_break_above += 1
                if high_arr[i] > breakout_high_extreme:
                    breakout_high_extreme = high_arr[i]

        # Increment break counters
        if broke_below and low_arr[i] >= bar_or_low:
            bars_since_break_below += 1
        if broke_above and high_arr[i] <= bar_or_high:
            bars_since_break_above += 1

        # Exits
        if position == 1:
            bars_in_trade += 1
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_CUSHION * 2
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            if bars_in_trade >= MIN_HOLD_BARS and high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            bars_in_trade += 1
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]
                new_trail = lowest_since_entry + bar_atr * ATR_CUSHION * 2
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            if bars_in_trade >= MIN_HOLD_BARS and low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # Entries (false breakout detection)
        if position == 0 and bar_time >= ENTRY_START and bar_time < ENTRY_CUTOFF:

            # Filter: ADX < threshold (ranging market)
            if bar_adx >= ADX_THRESHOLD:
                continue
            # Filter: OR width must be tight
            if np.isnan(bar_or_pct) or bar_or_pct > OR_WIDTH_MAX_PCTILE:
                continue

            # False breakdown long: broke below OR low, now closing back above
            if (not long_traded_today
                and broke_below
                and bars_since_break_below <= CONFIRM_BARS
                and close_arr[i] > bar_or_low
                and close_arr[i] > close_arr[i-1]):

                initial_stop = breakout_low_extreme - bar_atr * ATR_CUSHION
                target = bar_or_mid
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = target
                position = 1
                trailing_stop = initial_stop
                target_price = target
                highest_since_entry = high_arr[i]
                long_traded_today = True
                bars_in_trade = 0

            # False breakup short: broke above OR high, now closing back below
            elif (not short_traded_today
                  and broke_above
                  and bars_since_break_above <= CONFIRM_BARS
                  and close_arr[i] < bar_or_high
                  and close_arr[i] < close_arr[i-1]):

                initial_stop = breakout_high_extreme + bar_atr * ATR_CUSHION
                target = bar_or_mid
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = target
                position = -1
                trailing_stop = initial_stop
                target_price = target
                lowest_since_entry = low_arr[i]
                short_traded_today = True
                bars_in_trade = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date", "or_high", "or_low", "or_range", "or_mid",
                      "or_width_pctrank"],
            inplace=True, errors="ignore")
    return df
