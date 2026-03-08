"""VWAP-006 — VWAP-RSI Scalper FINAL v1.

Source: michaelriggs — VWAP-RSI Scalper FINAL v1
URL: https://www.tradingview.com/script/S9hY3huK-VWAP-RSI-Scalper-FINAL-v1/
Family: VWAP
Conversion: Faithful — no optimization, original parameters preserved.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

RSI_PERIOD = 3
RSI_LOW = 30              # Long: RSI crosses above this
RSI_HIGH = 70             # Short: RSI crosses below this
FAST_EMA = 9
SLOW_EMA = 21
ATR_LEN = 14
SL_ATR = 1.5              # Stop = 1.5x ATR
TP_ATR = 3.0              # Target = 3.0x ATR

SESSION_START = "09:30"
SESSION_END = "15:15"
WARMUP_MINS = 15          # 15 min warmup after open

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


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
    """Generate VWAP-RSI scalper signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    # ── Indicators ───────────────────────────────────────────────────────
    df["ema_fast"] = _ema(df["close"], FAST_EMA)
    df["ema_slow"] = _ema(df["close"], SLOW_EMA)
    df["rsi"] = _rsi(df["close"], RSI_PERIOD)
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    # VWAP (daily reset)
    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
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

    # ── Session filter ───────────────────────────────────────────────────
    time_str = _parse_time(df["datetime"])
    df["in_session"] = (time_str >= SESSION_START) & (time_str < SESSION_END)
    session_start_mask = df["in_session"] & (~df["in_session"].shift(1, fill_value=False))
    df["_session_bar"] = session_start_mask.cumsum()
    df["_bars_since_open"] = df.groupby("_session_bar").cumcount()
    warmup_bars = WARMUP_MINS // 5
    df["past_warmup"] = df["in_session"] & (df["_bars_since_open"] >= warmup_bars)

    # ── RSI crossover detection ──────────────────────────────────────────
    rsi_prev = df["rsi"].shift(1)
    rsi_cross_above_30 = (rsi_prev <= RSI_LOW) & (df["rsi"] > RSI_LOW)
    rsi_cross_below_70 = (rsi_prev >= RSI_HIGH) & (df["rsi"] < RSI_HIGH)

    # ── Entry conditions ─────────────────────────────────────────────────
    long_signal = (
        df["past_warmup"] &
        (df["close"] > df["vwap"]) &
        (df["ema_fast"] > df["ema_slow"]) &
        rsi_cross_above_30
    )
    short_signal = (
        df["past_warmup"] &
        (df["close"] < df["vwap"]) &
        (df["ema_fast"] < df["ema_slow"]) &
        rsi_cross_below_70
    )

    # ── Build output ─────────────────────────────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    stop_dist = df["atr"] * SL_ATR
    target_dist = df["atr"] * TP_ATR

    long_mask = long_signal.fillna(False)
    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "close"] - stop_dist[long_mask]
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] + target_dist[long_mask]

    short_mask = short_signal.fillna(False)
    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "close"] + stop_dist[short_mask]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - target_dist[short_mask]

    # ── Exit loop (stop/target + EOD flatten) ────────────────────────────
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    exit_sigs = np.zeros(n, dtype=int)

    for i in range(n):
        sig = df.iloc[i]["signal"]
        low_px = df.iloc[i]["low"]
        high_px = df.iloc[i]["high"]
        time_s = _parse_time(df["datetime"].iloc[i:i+1]).iloc[0]

        # EOD flatten
        if position != 0 and time_s >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Check stop/target
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

        # Open new position
        if position == 0 and sig != 0:
            stop_p = df.iloc[i]["stop_price"]
            target_p = df.iloc[i]["target_price"]
            if pd.notna(stop_p) and pd.notna(target_p):
                position = sig
                entry_stop = stop_p
                entry_target = target_p

    df["exit_signal"] = exit_sigs
    df.drop(columns=["_date", "_session_bar", "_bars_since_open",
                      "ema_fast", "ema_slow", "rsi", "atr", "vwap",
                      "in_session", "past_warmup"],
            inplace=True, errors="ignore")

    return df
