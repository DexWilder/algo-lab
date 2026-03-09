"""ORB_COMPRESSION — ORB-009 + ORB + ORION compression pre-filter: only enter breakout when market is in compression zone.

Source: luiscaballero — ORB Breakout Strategy with VWAP and Volume Filters
URL: https://www.tradingview.com/script/wLSGHPUe-ORB-Breakout-Strategy-with-VWAP-and-Volume-Filters/
Family: ORB
Conversion: Faithful — no optimization, original parameters preserved.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np
from research.evolution.mutations import compute_compression


# ── Parameters ───────────────────────────────────────────────────────────────

OR_MINUTES = 30           # Opening range: 09:30-10:00 ET
VWAP_SLOPE_BARS = 5       # VWAP slope lookback
VOL_MULT = 1.5            # Volume must exceed 1.5x 20-bar MA
VOL_MA_LEN = 20           # Volume MA period
CANDLE_STRENGTH = 0.30    # Close in top/bottom 30% of range
TP_MULT = 2.0             # TP = entry ± OR_range × 2.0
BE_PCT = 0.50             # Move SL to entry at 50% of TP distance

SESSION_START = "09:30"
OR_END = "10:00"
ENTRY_END = "15:00"
SESSION_END = "15:15"

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()


def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate ORB breakout signals with VWAP, volume, and candle filters.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── VWAP ─────────────────────────────────────────────────────────────
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    has_volume = df["volume"].sum() > 0
    if has_volume:
        cum_vol = df.groupby("_date")["volume"].cumsum()
        cum_vp = (hlc3 * df["volume"]).groupby(df["_date"]).cumsum()
        df["vwap"] = cum_vp / cum_vol.replace(0, np.nan)
    else:
        cum_hlc3 = hlc3.groupby(df["_date"]).cumsum()
        cum_count = hlc3.groupby(df["_date"]).cumcount() + 1
        df["vwap"] = cum_hlc3 / cum_count

    # Volume MA
    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)

    # ── Evolution mutation ──
    df = compute_compression(df)

    # ── Build Opening Range per day ──────────────────────────────────────
    in_or = (time_str >= SESSION_START) & (time_str < OR_END)
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    # Pre-compute OR high/low per date
    or_bars = df[in_or].copy()
    if or_bars.empty:
        df["signal"] = 0
        df["exit_signal"] = 0
        df["stop_price"] = np.nan
        df["target_price"] = np.nan
        df.drop(columns=["_date"], inplace=True)
        return df

    or_stats = or_bars.groupby("_date").agg(
        or_high=("high", "max"),
        or_low=("low", "min"),
    )
    or_stats["or_range"] = or_stats["or_high"] - or_stats["or_low"]
    df = df.merge(or_stats, left_on="_date", right_index=True, how="left")

    # ── Entry conditions ─────────────────────────────────────────────────
    after_or = time_str >= OR_END
    before_cutoff = time_str < ENTRY_END
    entry_window = in_session & after_or & before_cutoff

    # Filter 1: VWAP slope
    vwap_slope = df["vwap"] - df["vwap"].shift(VWAP_SLOPE_BARS)
    vwap_slope_long = vwap_slope > 0
    vwap_slope_short = vwap_slope < 0

    # Filter 2: Volume surge
    if has_volume:
        vol_ok = df["volume"] > df["vol_ma"] * VOL_MULT
    else:
        vol_ok = pd.Series(True, index=df.index)

    # Filter 3: Candle strength
    bar_range = df["high"] - df["low"]
    close_pos = np.where(bar_range > 0, (df["close"] - df["low"]) / bar_range, 0.5)
    strong_close_long = close_pos >= (1.0 - CANDLE_STRENGTH)   # top 30%
    strong_close_short = close_pos <= CANDLE_STRENGTH           # bottom 30%

    # Breakout signals
    long_break = df["close"] > df["or_high"]
    short_break = df["close"] < df["or_low"]

    long_signal = (
        entry_window &
        long_break &
        vwap_slope_long &
        vol_ok &
        strong_close_long &
        df["compression_active"]
    )
    short_signal = (
        entry_window &
        short_break &
        vwap_slope_short &
        vol_ok &
        strong_close_short &
        df["compression_active"]
    )

    # ── Build output ─────────────────────────────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    # Long: SL = OR_low, TP = entry + OR_range * TP_MULT
    long_mask = long_signal.fillna(False)
    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "or_low"]
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] + df.loc[long_mask, "or_range"] * TP_MULT

    # Short: SL = OR_high, TP = entry - OR_range * TP_MULT
    short_mask = short_signal.fillna(False)
    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "or_high"]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - df.loc[short_mask, "or_range"] * TP_MULT

    # ── Exit loop (max 1 trade/direction/day, BE logic, EOD flatten) ─────
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    entry_price = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    exit_sigs = np.zeros(n, dtype=int)
    # Zero out duplicate signals (enforce max 1/direction/day via loop)
    signals_arr = df["signal"].values.copy()

    for i in range(n):
        bar_date = df.iloc[i]["_date"]
        time_s = _parse_time(df["datetime"].iloc[i:i+1]).iloc[0]

        # Day reset
        if bar_date != current_date:
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        sig = signals_arr[i]

        # Enforce max 1 trade per direction per day
        if sig == 1 and long_traded_today:
            signals_arr[i] = 0
            sig = 0
        if sig == -1 and short_traded_today:
            signals_arr[i] = 0
            sig = 0

        # EOD flatten
        if position != 0 and time_s >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Check stop/target with BE logic
        if position == 1:
            low_px = df.iloc[i]["low"]
            high_px = df.iloc[i]["high"]
            # Breakeven: move stop to entry when price reaches 50% of TP distance
            tp_dist = entry_target - entry_price
            if tp_dist > 0 and high_px >= entry_price + tp_dist * BE_PCT:
                entry_stop = max(entry_stop, entry_price)
            if low_px <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            elif high_px >= entry_target:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            low_px = df.iloc[i]["low"]
            high_px = df.iloc[i]["high"]
            tp_dist = entry_price - entry_target
            if tp_dist > 0 and low_px <= entry_price - tp_dist * BE_PCT:
                entry_stop = min(entry_stop, entry_price)
            if high_px >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            elif low_px <= entry_target:
                exit_sigs[i] = -1
                position = 0

        # Open new position
        if position == 0 and sig != 0:
            stop_p = df.iloc[i]["stop_price"]
            target_p = df.iloc[i]["target_price"]
            if pd.notna(stop_p) and pd.notna(target_p):
                position = sig
                entry_stop = stop_p
                entry_target = target_p
                entry_price = df.iloc[i]["close"]
                if sig == 1:
                    long_traded_today = True
                else:
                    short_traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df.drop(columns=["_date", "or_high", "or_low", "or_range", "vwap", "vol_ma", "compression_active"], inplace=True, errors="ignore")

    return df
