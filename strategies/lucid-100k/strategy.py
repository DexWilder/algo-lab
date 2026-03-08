"""Lucid 100K v6.3 — Trend Pullback + VWAP Reversion (platform-agnostic).

Converted from lucid_v6_final.pine following the strategy Python contract.
See docs/strategy_python_contract.md for contract spec.
See strategies/lucid-100k/CONVERSION_NOTES.md for assumptions and gaps.

PLATFORM-AGNOSTIC: This module contains ONLY pure trading signal logic.
No prop rules, no phase sizing, no guardrails, no drawdown limits.
Those belong in controllers/prop_controller.py.

Dual-algo strategy with regime switching:
  - Algo 1: Trend Pullback (EMA alignment + pullback to slow EMA + strong close)
  - Algo 2: VWAP Mean Reversion (overextension from VWAP + RSI + rejection candle)
  - Regime gate: ADX + EMA slope determines which algo is active
  - Session filter: RTH window with warmup period
  - MTF filter: approximated via higher-timeframe EMA (see conversion notes)
"""

import pandas as pd
import numpy as np


# ── Parameters (from Pine input defaults) ────────────────────────────────────

# Indicators
FAST_EMA = 9
SLOW_EMA = 21
TREND_EMA = 200
RSI_LEN = 14
ATR_LEN = 14

# Quality filters
ADX_LEN = 14
ADX_MIN = 14.0
VOL_MA_LEN = 20
VOL_MULT = 1.0

# Session (RTH eastern)
SESSION_START = "08:30"
SESSION_END = "15:15"
WARMUP_MINS = 15
REV_BLACKOUT_MINS = 30

# Power windows
WIN1_START = "08:45"
WIN1_END = "11:00"
WIN2_START = "13:30"
WIN2_END = "15:10"

# Reversion params
REV_DIST_ATR = 1.2
REV_RSI_LOW = 40
REV_RSI_HIGH = 60
REV_NEUTRAL_SEP = 1.0   # max EMA fast/slow separation in ATR units
REV_ADX_MAX = 25.0       # regime gate: ADX must be below this for ranging

# Exits (ATR multiples — used for signal-level stop/target)
SL_ATR = 1.5
TP_ATR = 2.1
MIN_STOP_TICKS = 20
TICK_SIZE = 0.25  # MES tick size

# Regime
MODE = "auto"  # "trend", "reversion", "both", "auto"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window).mean()


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


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Compute ADX. Returns ADX series only (not DI+/DI-)."""
    prev_high = high.shift(1)
    prev_low = low.shift(1)

    plus_dm = (high - prev_high).clip(lower=0)
    minus_dm = (prev_low - low).clip(lower=0)

    # Zero out when the other is larger
    plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)

    atr_vals = _atr(high, low, close, period)

    plus_di = 100 * _ema(plus_dm, period) / atr_vals.replace(0, np.nan)
    minus_di = 100 * _ema(minus_dm, period) / atr_vals.replace(0, np.nan)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = _ema(dx, period)
    return adx


def _parse_time(dt_series: pd.Series) -> pd.Series:
    """Extract time string HH:MM from datetime column."""
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# ── Main Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate trading signals from OHLCV data.

    Returns the original DataFrame with added columns:
    - signal: 1 (long), -1 (short), 0 (none)
    - exit_signal: 1 (exit long), -1 (exit short), 0 (none)
    - stop_price: ATR-based stop level at signal bar
    - target_price: ATR-based target level at signal bar
    - signal_type: "pb" (pullback) or "rev" (reversion) or ""
    Plus intermediate indicator columns for debugging.
    """
    df = df.copy()
    n = len(df)

    # ── Indicators ────────────────────────────────────────────────────────
    df["ema_fast"] = _ema(df["close"], FAST_EMA)
    df["ema_slow"] = _ema(df["close"], SLOW_EMA)
    df["ema_trend"] = _ema(df["close"], TREND_EMA)
    df["rsi"] = _rsi(df["close"], RSI_LEN)
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)
    df["adx"] = _adx(df["high"], df["low"], df["close"], ADX_LEN)
    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)

    # VWAP (daily reset — approximated by cumulative within each day)
    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    hlc3 = (df["high"] + df["low"] + df["close"]) / 3
    has_volume = df["volume"].sum() > 0
    if has_volume:
        cum_vol = df.groupby("_date")["volume"].cumsum()
        cum_vp = (hlc3 * df["volume"]).groupby(df["_date"]).cumsum()
        df["vwap"] = cum_vp / cum_vol.replace(0, np.nan)
    else:
        # No volume data — use equal-weighted cumulative HLC3 per session day
        cum_hlc3 = hlc3.groupby(df["_date"]).cumsum()
        cum_count = hlc3.groupby(df["_date"]).cumcount() + 1
        df["vwap"] = cum_hlc3 / cum_count

    # ── Session & Window Filters ──────────────────────────────────────────
    time_str = _parse_time(df["datetime"])
    df["in_session"] = (time_str >= SESSION_START) & (time_str < SESSION_END)

    # Warmup: first N minutes after session open
    session_start_mask = df["in_session"] & (~df["in_session"].shift(1, fill_value=False))
    df["_session_bar"] = session_start_mask.cumsum()
    df["_bars_since_open"] = df.groupby("_session_bar").cumcount()
    warmup_bars = WARMUP_MINS // 5  # assumes 5m timeframe
    rev_blackout_bars = REV_BLACKOUT_MINS // 5
    df["past_warmup"] = df["in_session"] & (df["_bars_since_open"] >= warmup_bars)
    df["rev_time_ok"] = df["in_session"] & (df["_bars_since_open"] >= rev_blackout_bars)

    # Power windows
    in_win1 = (time_str >= WIN1_START) & (time_str < WIN1_END)
    in_win2 = (time_str >= WIN2_START) & (time_str < WIN2_END)
    df["in_windows"] = in_win1 | in_win2

    df["allowed"] = df["in_session"] & df["past_warmup"] & df["in_windows"]

    # ── Quality Filters ───────────────────────────────────────────────────
    # Bypass volume filter when volume data is unavailable (all zeros)
    has_volume = df["volume"].sum() > 0
    if has_volume:
        vol_ok = df["volume"] > df["vol_ma"] * VOL_MULT
    else:
        vol_ok = pd.Series(True, index=df.index)
    adx_ok = df["adx"] >= ADX_MIN
    # PB needs trending ADX + volume; REV needs volume only (low ADX by design)
    df["quality_pb"] = adx_ok & vol_ok
    df["quality_rev"] = vol_ok

    bar_range = df["high"] - df["low"]
    avg_range = bar_range.rolling(10).mean()
    df["range_ok"] = bar_range >= avg_range * 0.6

    # ── MTF Filter (approximation) ────────────────────────────────────────
    # Pine uses request.security for 15m/60m EMA200.
    # We approximate with a longer EMA on 5m data:
    # 15m EMA200 ≈ 5m EMA600, 60m EMA200 ≈ 5m EMA2400
    # Using 5m EMA600 as the primary MTF filter (conservative approximation).
    df["ema_mtf"] = _ema(df["close"], 600)
    mtf_bull = df["close"] > df["ema_mtf"]
    mtf_bear = df["close"] < df["ema_mtf"]

    # ── Trend Pullback Signals ────────────────────────────────────────────
    trend_bull = (
        (df["ema_fast"] > df["ema_slow"]) &
        (df["close"] > df["ema_trend"]) &
        (df["close"] > df["vwap"]) &
        mtf_bull
    )
    trend_bear = (
        (df["ema_fast"] < df["ema_slow"]) &
        (df["close"] < df["ema_trend"]) &
        (df["close"] < df["vwap"]) &
        mtf_bear
    )

    # Strong close: close in top/bottom 20% of bar range
    close_pos = np.where(bar_range > 0, (df["close"] - df["low"]) / bar_range, 0.5)
    strong_close_up = close_pos >= 0.80
    strong_close_down = close_pos <= 0.20

    # Pullback: price touches slow EMA, closes above fast EMA
    pb_long = (
        trend_bull &
        (df["low"] <= df["ema_slow"]) &
        (df["close"] > df["ema_fast"]) &
        ((df["close"] > df["high"].shift(1)) | strong_close_up) &
        df["range_ok"]
    )
    pb_short = (
        trend_bear &
        (df["high"] >= df["ema_slow"]) &
        (df["close"] < df["ema_fast"]) &
        ((df["close"] < df["low"].shift(1)) | strong_close_down) &
        df["range_ok"]
    )

    # ── VWAP Reversion Signals ────────────────────────────────────────────
    dist_atr = (df["close"] - df["vwap"]) / df["atr"].replace(0, np.nan)
    ema_sep = (df["ema_fast"] - df["ema_slow"]).abs() / df["atr"].replace(0, np.nan)
    neutralish = ema_sep < REV_NEUTRAL_SEP

    vwap_slope = df["vwap"] - df["vwap"].shift(5)
    vwap_flat = vwap_slope.abs() < df["atr"] * 0.5

    body_size = (df["close"] - df["open"]).abs()
    wick_ratio = np.where(bar_range > 0, (bar_range - body_size) / bar_range, 0)
    strong_rej = wick_ratio >= 0.4

    bull_rej = (df["close"] > df["open"]) & (df["close"] > (df["high"] + df["low"]) / 2) & strong_rej
    bear_rej = (df["close"] < df["open"]) & (df["close"] < (df["high"] + df["low"]) / 2) & strong_rej

    rev_long = (
        neutralish & vwap_flat & df["rev_time_ok"] &
        (dist_atr <= -REV_DIST_ATR) &
        (df["rsi"] <= REV_RSI_LOW) &
        bull_rej & mtf_bull
    )
    rev_short = (
        neutralish & vwap_flat & df["rev_time_ok"] &
        (dist_atr >= REV_DIST_ATR) &
        (df["rsi"] >= REV_RSI_HIGH) &
        bear_rej & mtf_bear
    )

    # ── Regime Gate ───────────────────────────────────────────────────────
    ema_slope = df["ema_fast"] - df["ema_fast"].shift(5)
    trend_regime = (
        (df["adx"] >= ADX_MIN) &
        (ema_slope.abs() > TICK_SIZE * 2) &
        (vwap_slope.abs() > TICK_SIZE * 2)
    )
    range_regime = (df["adx"] < REV_ADX_MAX) & neutralish

    if MODE == "trend":
        use_trend = pd.Series(True, index=df.index)
        use_rev = pd.Series(False, index=df.index)
    elif MODE == "reversion":
        use_trend = pd.Series(False, index=df.index)
        use_rev = pd.Series(True, index=df.index)
    elif MODE == "both":
        use_trend = pd.Series(True, index=df.index)
        use_rev = pd.Series(True, index=df.index)
    else:  # auto
        use_trend = trend_regime
        use_rev = range_regime

    # ── Combine Signals ───────────────────────────────────────────────────
    pb_long_sig = use_trend & pb_long
    pb_short_sig = use_trend & pb_short
    rev_long_sig = use_rev & rev_long
    rev_short_sig = use_rev & rev_short

    # Apply appropriate quality gate per module:
    # PB requires ADX >= threshold (trending); REV only needs volume (ranging)
    pb_long_final = df["allowed"] & df["quality_pb"] & pb_long_sig
    pb_short_final = df["allowed"] & df["quality_pb"] & pb_short_sig
    rev_long_final = df["allowed"] & df["quality_rev"] & rev_long_sig
    rev_short_final = df["allowed"] & df["quality_rev"] & rev_short_sig

    long_signal = pb_long_final | rev_long_final
    short_signal = pb_short_final | rev_short_final

    # ── Build Output Columns ──────────────────────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan
    df["signal_type"] = ""

    # Stop distance with floor
    stop_dist = df["atr"] * SL_ATR
    stop_dist = stop_dist.clip(lower=MIN_STOP_TICKS * TICK_SIZE)
    target_dist = df["atr"] * TP_ATR

    # Long entries
    long_mask = long_signal.fillna(False)
    df.loc[long_mask, "signal"] = 1
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "close"] - stop_dist[long_mask]
    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] + target_dist[long_mask]

    # Tag signal type
    pb_l = long_mask & pb_long_sig.fillna(False)
    rev_l = long_mask & rev_long_sig.fillna(False) & ~pb_l
    df.loc[pb_l, "signal_type"] = "pb"
    df.loc[rev_l, "signal_type"] = "rev"

    # Short entries
    short_mask = short_signal.fillna(False)
    df.loc[short_mask, "signal"] = -1
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "close"] + stop_dist[short_mask]
    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - target_dist[short_mask]

    pb_s = short_mask & pb_short_sig.fillna(False)
    rev_s = short_mask & rev_short_sig.fillna(False) & ~pb_s
    df.loc[pb_s, "signal_type"] = "pb"
    df.loc[rev_s, "signal_type"] = "rev"

    # ── Exit Signals (stop/target check on close) ─────────────────────────
    # The backtest engine fills at next open, so we check if close breaches
    # the stop or target level and emit exit_signal accordingly.
    # This is approximate — real stop/limit orders would fill at exact levels.
    # A future engine upgrade could support price-level exits directly.

    position = 0  # 0=flat, 1=long, -1=short
    entry_stop = 0.0
    entry_target = 0.0
    exit_sigs = np.zeros(n, dtype=int)

    for i in range(n):
        sig = df.iloc[i]["signal"]
        close_px = df.iloc[i]["close"]
        low_px = df.iloc[i]["low"]
        high_px = df.iloc[i]["high"]
        time_s = _parse_time(df["datetime"].iloc[i:i+1]).iloc[0]

        # Session end flatten
        if position != 0 and time_s >= SESSION_END:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # Check stop/target hits
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

        # Process new entry (only if flat after exit check)
        if position == 0 and sig != 0:
            position = sig
            entry_stop = df.iloc[i]["stop_price"]
            entry_target = df.iloc[i]["target_price"]
            if pd.isna(entry_stop) or pd.isna(entry_target):
                position = 0  # skip bad entries

    df["exit_signal"] = exit_sigs

    # ── Cleanup temp columns ──────────────────────────────────────────────
    df.drop(columns=["_date", "_session_bar", "_bars_since_open"], inplace=True)

    return df
