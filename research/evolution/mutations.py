"""Reusable mutation components extracted from donor strategies.

Stateless indicator functions that add columns to a DataFrame
without touching position state. Used by the evolution scheduler to
inject donor components into parent strategies.

Sources:
- compute_compression: ORION-VOL (ana_gagua) — tightness + flatness filters
- compute_squeeze: BBKC-SQUEEZE (LazyBear) — BB inside KC detection
- compute_momentum_state: BBKC-SQUEEZE — linreg momentum color states
- compute_sweep: ICT-010 (tradeforopp) — session range sweep bias
- compute_ema_alignment: Multi-EMA trend continuation (Batch 2)
- compute_range_fade: Bollinger band range fade signals (Batch 2)
"""

import numpy as np
import pandas as pd


# ── Shared Helpers ──────────────────────────────────────────────────────────

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    """Average True Range (EMA-smoothed)."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def _stdev(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).std(ddof=0)


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)


def _linreg_slope(series: pd.Series, length: int) -> pd.Series:
    """Rolling linear regression slope."""
    result = np.full(len(series), np.nan)
    vals = series.values
    x = np.arange(length, dtype=float)
    x_mean = x.mean()
    ss_xx = np.sum((x - x_mean) ** 2)
    for i in range(length - 1, len(vals)):
        window = vals[i - length + 1:i + 1]
        if np.any(np.isnan(window)):
            continue
        y_mean = window.mean()
        ss_xy = np.sum((x - x_mean) * (window - y_mean))
        if ss_xx == 0:
            result[i] = 0.0
        else:
            result[i] = ss_xy / ss_xx
    return pd.Series(result, index=series.index)


def _linreg(series: pd.Series, length: int) -> pd.Series:
    """Rolling linear regression value at current bar (offset=0)."""
    result = np.full(len(series), np.nan)
    vals = series.values
    x = np.arange(length, dtype=float)
    x_mean = x.mean()
    ss_xx = np.sum((x - x_mean) ** 2)
    for i in range(length - 1, len(vals)):
        window = vals[i - length + 1:i + 1]
        if np.any(np.isnan(window)):
            continue
        y_mean = window.mean()
        ss_xy = np.sum((x - x_mean) * (window - y_mean))
        if ss_xx == 0:
            result[i] = y_mean
        else:
            slope = ss_xy / ss_xx
            intercept = y_mean - slope * x_mean
            result[i] = slope * (length - 1) + intercept
    return pd.Series(result, index=series.index)


# ── Mutation Functions ──────────────────────────────────────────────────────

def compute_compression(
    df: pd.DataFrame,
    lookback: int = 15,
    atr_period: int = 14,
    atr_mult: float = 2.5,
    slope_thresh: float = 0.2,
) -> pd.DataFrame:
    """ORION-VOL compression filter — detects volatility compression zones.

    Adds column:
        compression_active (bool) — True when range is tight AND slope is flat.

    Typical distribution: ~5-20% of bars are compressed.
    """
    df = df.copy()
    atr = _atr(df["high"], df["low"], df["close"], atr_period)

    # Rolling box range
    box_range = (
        df["high"].rolling(window=lookback, min_periods=lookback).max()
        - df["low"].rolling(window=lookback, min_periods=lookback).min()
    )

    # Tightness: range < atr_mult * ATR
    is_tight = box_range < (atr_mult * atr)

    # Flatness: normalized slope < threshold
    slope = _linreg_slope(df["close"], lookback)
    norm_slope = slope.abs() / atr.replace(0, np.nan)
    is_flat = norm_slope < slope_thresh

    df["compression_active"] = (is_tight & is_flat).fillna(False)
    return df


def compute_squeeze(
    df: pd.DataFrame,
    bb_len: int = 14,
    bb_mult: float = 2.0,
    kc_len: int = 16,
    kc_mult: float = 1.5,
) -> pd.DataFrame:
    """BBKC squeeze detection — BB inside KC = squeeze, BB exits KC = release.

    Adds columns:
        squeeze_on (bool) — BB inside KC (compression phase).
        squeeze_release (bool) — First bar where BB exits KC (expansion trigger).

    squeeze_release is rarer than squeeze_on (edge event).
    """
    df = df.copy()

    # Bollinger Bands
    bb_basis = _sma(df["close"], bb_len)
    bb_dev = bb_mult * _stdev(df["close"], bb_len)
    upper_bb = bb_basis + bb_dev
    lower_bb = bb_basis - bb_dev

    # Keltner Channel
    kc_ma = _sma(df["close"], kc_len)
    kc_range = _true_range(df["high"], df["low"], df["close"])
    kc_rangema = _sma(kc_range, kc_len)
    upper_kc = kc_ma + kc_rangema * kc_mult
    lower_kc = kc_ma - kc_rangema * kc_mult

    # Squeeze states
    sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)

    df["squeeze_on"] = sqz_on.fillna(False)
    # Release = first bar where squeeze turns off
    df["squeeze_release"] = (sqz_off & ~sqz_off.shift(1, fill_value=False)).fillna(False)
    return df


def compute_momentum_state(
    df: pd.DataFrame,
    kc_len: int = 16,
) -> pd.DataFrame:
    """BBKC momentum color states — direction + acceleration of squeeze momentum.

    Adds columns:
        mom_lime (bool) — momentum > 0 and rising (bullish acceleration)
        mom_green (bool) — momentum > 0 and falling (bullish deceleration)
        mom_red (bool) — momentum < 0 and falling (bearish acceleration)
        mom_maroon (bool) — momentum < 0 and rising (bearish deceleration)

    Exactly one state is True per bar (after warmup).
    """
    df = df.copy()

    # Momentum histogram: linreg(close - midline, kc_len)
    hh = df["high"].rolling(window=kc_len, min_periods=kc_len).max()
    ll = df["low"].rolling(window=kc_len, min_periods=kc_len).min()
    donchian_mid = (hh + ll) / 2
    sma_close = _sma(df["close"], kc_len)
    midline = (donchian_mid + sma_close) / 2
    delta = df["close"] - midline

    mom = _linreg(delta, kc_len)
    mom_prev = mom.shift(1)

    df["mom_lime"] = ((mom > 0) & (mom > mom_prev)).fillna(False)
    df["mom_green"] = ((mom > 0) & (mom <= mom_prev)).fillna(False)
    df["mom_red"] = ((mom < 0) & (mom < mom_prev)).fillna(False)
    df["mom_maroon"] = ((mom < 0) & (mom >= mom_prev)).fillna(False)
    return df


def compute_sweep(
    df: pd.DataFrame,
    range_minutes: int = 30,
    session_start: str = "09:30",
) -> pd.DataFrame:
    """ICT-010 session range sweep bias — detects sweep of opening range.

    Adds column:
        sweep_bias (int) — 1 if low swept (bullish), -1 if high swept (bearish), 0 otherwise.

    sweep_bias is set on the bar where the sweep occurs and persists for
    the rest of the session day (forward-filled within each date).
    """
    df = df.copy()
    dt = pd.to_datetime(df["datetime"])
    df["_sweep_date"] = dt.dt.date
    time_str = dt.dt.strftime("%H:%M")

    # Compute range end time
    start_min = int(session_start.split(":")[0]) * 60 + int(session_start.split(":")[1])
    end_min = start_min + range_minutes
    range_end = f"{end_min // 60:02d}:{end_min % 60:02d}"

    # Build session range per day
    in_range = (time_str >= session_start) & (time_str < range_end)
    range_bars = df[in_range]

    if range_bars.empty:
        df["sweep_bias"] = 0
        df.drop(columns=["_sweep_date"], inplace=True)
        return df

    range_stats = range_bars.groupby("_sweep_date").agg(
        _range_high=("high", "max"),
        _range_low=("low", "min"),
    )
    df = df.merge(range_stats, left_on="_sweep_date", right_index=True, how="left")

    # Detect sweeps bar-by-bar (after range period)
    after_range = time_str >= range_end
    sweep_bias_arr = np.zeros(len(df), dtype=int)
    current_date = None
    day_bias = 0

    for i in range(len(df)):
        d = df.iloc[i]["_sweep_date"]
        if d != current_date:
            current_date = d
            day_bias = 0

        if not after_range.iloc[i] or day_bias != 0:
            sweep_bias_arr[i] = day_bias
            continue

        r_high = df.iloc[i]["_range_high"]
        r_low = df.iloc[i]["_range_low"]
        if pd.isna(r_high) or pd.isna(r_low):
            continue

        low_px = df.iloc[i]["low"]
        high_px = df.iloc[i]["high"]
        close_px = df.iloc[i]["close"]

        # Low sweep: wick below range_low, close above → bullish
        if low_px < r_low and close_px > r_low:
            day_bias = 1
        # High sweep: wick above range_high, close below → bearish
        elif high_px > r_high and close_px < r_high:
            day_bias = -1

        sweep_bias_arr[i] = day_bias

    df["sweep_bias"] = sweep_bias_arr
    df.drop(columns=["_sweep_date", "_range_high", "_range_low"], inplace=True, errors="ignore")
    return df


def compute_ema_alignment(
    df: pd.DataFrame,
    fast: int = 9,
    slow: int = 21,
    trend: int = 50,
) -> pd.DataFrame:
    """Multi-EMA trend alignment for continuation entries.

    Detects when EMAs are stacked in order (fast > slow > trend) AND
    the fast EMA is moving in trend direction. Targets HIGH_VOL_TRENDING_LOW_RV
    regime where sustained directional grinds dominate.

    Adds columns:
        ema_aligned_long (bool) — fast > slow > trend, fast rising
        ema_aligned_short (bool) — fast < slow < trend, fast falling

    Typical distribution: ~25-40% of bars aligned in one direction.
    """
    df = df.copy()
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    ema_trend = df["close"].ewm(span=trend, adjust=False).mean()

    fast_rising = ema_fast > ema_fast.shift(1)
    fast_falling = ema_fast < ema_fast.shift(1)

    df["ema_aligned_long"] = (
        (ema_fast > ema_slow) & (ema_slow > ema_trend) & fast_rising
    ).fillna(False)
    df["ema_aligned_short"] = (
        (ema_fast < ema_slow) & (ema_slow < ema_trend) & fast_falling
    ).fillna(False)

    return df


def compute_range_fade(
    df: pd.DataFrame,
    bb_len: int = 20,
    bb_mult: float = 2.0,
    bounce_bars: int = 3,
) -> pd.DataFrame:
    """Bollinger Band range fade signals for mean reversion.

    Detects when price reaches range extremes and starts reverting.
    Targets RANGING regime cells where breakout/trend strategies fail.

    Adds columns:
        range_fade_long (bool) — price touched lower BB and closed higher than open
        range_fade_short (bool) — price touched upper BB and closed lower than open
        in_range (bool) — price within BB ±1σ (inner bands)

    Typical distribution: range_fade_long/short ~3-8% of bars.
    """
    df = df.copy()

    bb_basis = _sma(df["close"], bb_len)
    bb_dev = _stdev(df["close"], bb_len)

    upper_bb = bb_basis + bb_mult * bb_dev
    lower_bb = bb_basis - bb_mult * bb_dev
    inner_upper = bb_basis + bb_dev
    inner_lower = bb_basis - bb_dev

    # Touch lower band AND bullish close (close > open = bounce)
    touched_lower = df["low"] <= lower_bb
    bullish_close = df["close"] > df["open"]

    # Touch upper band AND bearish close (close < open = fade)
    touched_upper = df["high"] >= upper_bb
    bearish_close = df["close"] < df["open"]

    df["range_fade_long"] = (touched_lower & bullish_close).fillna(False)
    df["range_fade_short"] = (touched_upper & bearish_close).fillna(False)
    df["in_range"] = ((df["close"] >= inner_lower) & (df["close"] <= inner_upper)).fillna(False)

    return df
