"""GAP-MOM — Gap Momentum System (Perry Kaufman, TASC 2024.01).

Source: PineCodersTASC — Gap Momentum System
URL: https://www.tradingview.com/script/52wKLj6P-TASC-2024-01-Gap-Momentum-System/
Family: ORB (gap-based)
Conversion: Faithful — original parameters preserved.

Logic:
- Compute daily gap: today's open minus yesterday's close
- Cumulative gap series (like OBV but for gaps)
- SMA signal line on cumulative gap
- Long when gap momentum crosses above signal line
- Exit when gap momentum crosses below signal line, or stop hit, or EOD
- Long-only strategy

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

SIGNAL_SMA = 20            # SMA length for signal line (days)
ATR_PERIOD = 14            # ATR for protective stop
SL_ATR = 2.0               # Stop = 2.0x ATR from entry

SESSION_START = "09:30"
SESSION_END = "15:15"
ENTRY_CUTOFF = "14:00"     # No new entries after 14:00

TICK_SIZE = 0.25            # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate gap momentum signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Identify session boundaries ────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    # ── Compute daily gap: today's open - yesterday's close ────────────
    # Get first bar of each session day (the open)
    session_start_mask = in_session & (~in_session.shift(1, fill_value=False))

    # Get last bar of each session day (previous close)
    dates = df["_date"]
    unique_dates = dates[in_session].unique()

    # Build per-day gap values
    day_gaps = {}
    prev_close = None
    for d in unique_dates:
        day_mask = (dates == d) & in_session
        day_bars = df[day_mask]
        if day_bars.empty:
            continue
        today_open = day_bars.iloc[0]["open"]
        if prev_close is not None:
            day_gaps[d] = today_open - prev_close
        else:
            day_gaps[d] = 0.0
        prev_close = day_bars.iloc[-1]["close"]

    # Map gap to each bar
    df["_daily_gap"] = dates.map(day_gaps).fillna(0.0)

    # ── Cumulative gap momentum ────────────────────────────────────────
    # One value per day — cumulate across days
    day_gap_series = pd.Series(day_gaps)
    cum_gap = day_gap_series.cumsum()

    # SMA signal line (computed on daily values)
    signal_line = cum_gap.rolling(window=SIGNAL_SMA, min_periods=1).mean()

    # Map daily values back to each bar, plus previous day's values
    df["_cum_gap"] = dates.map(cum_gap).astype(float)
    df["_signal_line"] = dates.map(signal_line).astype(float)

    # Build previous-day lookup for crossover detection
    date_list = list(cum_gap.index)
    prev_day_cum = {}
    prev_day_sig = {}
    for idx, d in enumerate(date_list):
        if idx > 0:
            prev_d = date_list[idx - 1]
            prev_day_cum[d] = cum_gap[prev_d]
            prev_day_sig[d] = signal_line[prev_d]

    df["_prev_cum"] = dates.map(prev_day_cum).astype(float)
    df["_prev_sig"] = dates.map(prev_day_sig).astype(float)

    # ── ATR for protective stops ───────────────────────────────────────
    df["_atr"] = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)

    # ── Entry conditions ───────────────────────────────────────────────
    # Long: gap momentum crosses above signal line (day-over-day)
    momentum_cross_up = (
        df["_prev_cum"].notna() &
        (df["_prev_cum"] <= df["_prev_sig"]) &
        (df["_cum_gap"] > df["_signal_line"])
    )

    # Also enter when momentum is above signal (trend continuation)
    momentum_above = (
        df["_cum_gap"].notna() &
        df["_signal_line"].notna() &
        (df["_cum_gap"] > df["_signal_line"])
    )

    # Only signal on session start bar (one signal per day max)
    before_cutoff = time_str < ENTRY_CUTOFF

    long_signal = (
        session_start_mask &
        in_session &
        before_cutoff &
        momentum_cross_up &
        df["_cum_gap"].notna() &
        df["_signal_line"].notna()
    )

    # ── Exit condition: momentum crosses below signal (day-over-day) ───
    momentum_cross_down = (
        df["_prev_cum"].notna() &
        (df["_prev_cum"] >= df["_prev_sig"]) &
        (df["_cum_gap"] < df["_signal_line"])
    )
    exit_on_cross = session_start_mask & momentum_cross_down

    # ── Build output ───────────────────────────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    stop_dist = df["_atr"] * SL_ATR

    long_mask = long_signal.fillna(False)
    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "close"] - stop_dist[long_mask]
    # No fixed target — exit on signal reversal or stop
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] * 1.10  # dummy high target

    # ── Exit loop: signal reversal + stop + EOD flatten ────────────────
    position = 0
    entry_stop = 0.0
    exit_sigs = np.zeros(n, dtype=int)
    signals_arr = df["signal"].values.copy()

    close_arr = df["close"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    exit_cross = exit_on_cross.values
    cum_gap_arr = df["_cum_gap"].values
    sig_line_arr = df["_signal_line"].values

    for i in range(n):
        sig = signals_arr[i]

        # EOD flatten
        if position != 0 and time_arr[i] >= SESSION_END:
            exit_sigs[i] = 1
            position = 0
            continue

        # Check exit conditions for long position
        if position == 1:
            # Stop hit
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            # Signal reversal: gap momentum drops below signal line
            elif cum_gap_arr[i] < sig_line_arr[i]:
                exit_sigs[i] = 1
                position = 0

        # Open new position (long only)
        if position == 0 and sig == 1:
            stop_p = df.iloc[i]["stop_price"]
            if pd.notna(stop_p):
                position = 1
                entry_stop = stop_p

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df.drop(columns=["_date", "_daily_gap", "_cum_gap", "_signal_line",
                      "_prev_cum", "_prev_sig", "_atr"],
            inplace=True, errors="ignore")

    return df
