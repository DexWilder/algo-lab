"""RVWAP-MR — Rolling VWAP Mean Reversion with StDev Bands.

Source: vvedding — RVWAP Mean Reversion Strategy
URL: https://www.tradingview.com/script/oZcWZsvU-RVWAP-Mean-Reversion-Strategy/
Family: VWAP
Conversion: Faithful — original parameters preserved.

Logic:
- Session-anchored VWAP with rolling standard deviation bands
- Long: price dips below lower band then crosses back above
- Short: price rises above upper band then crosses back below
- Exit: price crosses back to VWAP center (mean reversion target)
- Stop: ATR-based protective stop

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

STDEV_MULT = 2.0           # Band width: VWAP ± N * stdev
STDEV_LOOKBACK = 20        # Rolling stdev period (bars)
ATR_PERIOD = 14            # ATR for protective stop
SL_ATR = 2.0               # Stop = 2.0x ATR from entry

SESSION_START = "09:30"
SESSION_END = "15:15"
WARMUP_MINS = 30           # 30 min warmup (6 bars) for VWAP to stabilize

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
    """Generate RVWAP mean reversion signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session-anchored VWAP ──────────────────────────────────────────
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

    # ── Rolling StDev of price deviation from VWAP ─────────────────────
    deviation = df["close"] - df["vwap"]
    df["stdev"] = deviation.rolling(window=STDEV_LOOKBACK, min_periods=5).std()

    df["upper_band"] = df["vwap"] + STDEV_MULT * df["stdev"]
    df["lower_band"] = df["vwap"] - STDEV_MULT * df["stdev"]

    # ── ATR for protective stops ───────────────────────────────────────
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)

    # ── Session and warmup filter ──────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    session_start_mask = in_session & (~in_session.shift(1, fill_value=False))
    df["_session_bar"] = session_start_mask.cumsum()
    df["_bars_since_open"] = df.groupby("_session_bar").cumcount()
    warmup_bars = WARMUP_MINS // 5
    past_warmup = in_session & (df["_bars_since_open"] >= warmup_bars)

    # ── Crossover detection (mean reversion entries) ───────────────────
    # Long: price was below lower band and crosses back above
    prev_close = df["close"].shift(1)
    long_cross = (prev_close <= df["lower_band"].shift(1)) & (df["close"] > df["lower_band"])

    # Short: price was above upper band and crosses back below
    short_cross = (prev_close >= df["upper_band"].shift(1)) & (df["close"] < df["upper_band"])

    # ── Entry conditions ───────────────────────────────────────────────
    valid_bands = df["stdev"].notna() & (df["stdev"] > 0)
    long_signal = past_warmup & valid_bands & long_cross
    short_signal = past_warmup & valid_bands & short_cross

    # ── Build output ───────────────────────────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    stop_dist = df["atr"] * SL_ATR

    long_mask = long_signal.fillna(False)
    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "close"] - stop_dist[long_mask]
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "vwap"]  # target = VWAP center

    short_mask = short_signal.fillna(False)
    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "close"] + stop_dist[short_mask]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "vwap"]  # target = VWAP center

    # ── Exit loop: dynamic VWAP cross exit + stop + EOD flatten ────────
    position = 0
    entry_stop = 0.0
    entry_price = 0.0
    exit_sigs = np.zeros(n, dtype=int)
    signals_arr = df["signal"].values.copy()

    close_arr = df["close"].values
    low_arr = df["low"].values
    high_arr = df["high"].values
    vwap_arr = df["vwap"].values
    time_arr = time_str.values

    for i in range(n):
        sig = signals_arr[i]

        # EOD flatten
        if position != 0 and time_arr[i] >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Check exit conditions
        if position == 1:
            # Stop hit
            if low_arr[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            # Mean reversion complete: price crosses above VWAP
            elif close_arr[i] >= vwap_arr[i] and entry_price < vwap_arr[i]:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            # Stop hit
            if high_arr[i] >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            # Mean reversion complete: price crosses below VWAP
            elif close_arr[i] <= vwap_arr[i] and entry_price > vwap_arr[i]:
                exit_sigs[i] = -1
                position = 0

        # Open new position
        if position == 0 and sig != 0:
            stop_p = df.iloc[i]["stop_price"]
            if pd.notna(stop_p):
                position = sig
                entry_stop = stop_p
                entry_price = close_arr[i]

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df.drop(columns=["_date", "vwap", "stdev", "upper_band", "lower_band",
                      "atr", "_session_bar", "_bars_since_open"],
            inplace=True, errors="ignore")

    return df
