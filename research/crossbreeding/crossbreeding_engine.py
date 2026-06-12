"""Strategy Crossbreeding Engine — Generate hybrids from validated parent components.

Recombines proven entry/exit/filter modules from parent strategies into new
candidate strategies. Only uses components from validated parents (PB, ORB,
VWAP Trend, BB Equilibrium, Donchian).

Pipeline position: after Portfolio Genome Analysis, before Validation Battery.

Usage:
    python3 research/crossbreeding/crossbreeding_engine.py
    python3 research/crossbreeding/crossbreeding_engine.py --recipe 3
    python3 research/crossbreeding/crossbreeding_engine.py --asset MGC
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: FEATURE COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════

# Feature cache (added 2026-06-05 per operator approval #80; minimum-viable
# in-memory memoization). Keyed by (n_bars, first_datetime, last_datetime) so
# the same data file produces the same key even when read via pd.read_csv in
# different scripts. Cache hit/miss logged for diagnostic visibility. Fail-
# closed: if any key field is unavailable, skip cache and recompute.
_FEATURE_CACHE: dict[tuple, dict] = {}
_FEATURE_CACHE_HITS = 0
_FEATURE_CACHE_MISSES = 0


def _feature_cache_key(df: pd.DataFrame):
    try:
        first_dt = str(df["datetime"].iloc[0])
        last_dt = str(df["datetime"].iloc[-1])
        return (len(df), first_dt, last_dt)
    except Exception:
        return None


def feature_cache_stats() -> dict:
    return {
        "hits": _FEATURE_CACHE_HITS,
        "misses": _FEATURE_CACHE_MISSES,
        "cached_keys": len(_FEATURE_CACHE),
    }


def feature_cache_clear():
    global _FEATURE_CACHE_HITS, _FEATURE_CACHE_MISSES
    _FEATURE_CACHE.clear()
    _FEATURE_CACHE_HITS = 0
    _FEATURE_CACHE_MISSES = 0


def compute_features(df: pd.DataFrame) -> dict:
    """Pre-compute all indicators any component might need.

    Includes in-memory cache (added 2026-06-05 per #80): same data file →
    reuse computed features across multiple backtests in a single Python
    session. Critical for prop-stress sweeps that re-run backtests with
    only cost/slippage params changed."""
    global _FEATURE_CACHE_HITS, _FEATURE_CACHE_MISSES
    key = _feature_cache_key(df)
    if key is not None and key in _FEATURE_CACHE:
        _FEATURE_CACHE_HITS += 1
        return _FEATURE_CACHE[key]
    _FEATURE_CACHE_MISSES += 1
    # ── original feature computation begins below ────────────────────────────
    dt = pd.to_datetime(df["datetime"])
    n = len(df)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    opn = df["open"].values
    volume = df["volume"].values if "volume" in df.columns else np.ones(n)

    dates = dt.dt.date.values
    times = dt.dt.strftime("%H:%M").values
    hours = dt.dt.hour.values

    # ATR
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean().values

    # EMAs
    ema8 = df["close"].ewm(span=8, adjust=False).mean().values
    ema13 = df["close"].ewm(span=13, adjust=False).mean().values
    ema20 = df["close"].ewm(span=20, adjust=False).mean().values
    ema21 = df["close"].ewm(span=21, adjust=False).mean().values
    ema50 = df["close"].ewm(span=50, adjust=False).mean().values

    # Bollinger Bands
    sma20 = df["close"].rolling(20, min_periods=20).mean()
    std20 = df["close"].rolling(20, min_periods=20).std(ddof=0)
    bb_upper = (sma20 + 2.0 * std20).values
    bb_lower = (sma20 - 2.0 * std20).values
    bb_mid = sma20.values
    bandwidth = ((sma20 + 2.0 * std20 - (sma20 - 2.0 * std20)) / sma20).values
    bw_series = pd.Series(bandwidth)
    bw_pctrank = bw_series.rolling(100, min_periods=20).apply(
        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False
    ).values

    # RSI
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss_s = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss_s.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = (100 - (100 / (1 + rs))).values

    # Session VWAP
    tp = (high + low + close) / 3.0
    vwap = np.full(n, np.nan)
    cum_tp_vol = 0.0
    cum_vol = 0.0
    current_date = None
    for i in range(n):
        if dates[i] != current_date:
            current_date = dates[i]
            cum_tp_vol = 0.0
            cum_vol = 0.0
        vol = max(volume[i], 1.0)
        cum_tp_vol += tp[i] * vol
        cum_vol += vol
        vwap[i] = cum_tp_vol / cum_vol

    # ATR percentile rank (vol-regime gate, added 2026-06-02 per operator approval
    # of the concentration-mutation Plan B build). 500-bar rolling window ≈ 40
    # sessions of 5min data; long enough to define "high" vs "low" vol regimes
    # without lagging multi-quarter shifts.
    atr_series = pd.Series(atr)
    atr_pctrank = atr_series.rolling(500, min_periods=100).apply(
        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False
    ).values

    # Prior-day high/low/close (added 2026-06-04 — Core Daily Hunt unlock).
    # For each bar, look up the previous trading day's session extremes. Fail-
    # closed: NaN for the first day. Computed once and cached per bar via
    # date-aligned lookup.
    df_pd = df.copy()
    df_pd["_date"] = dates
    daily_high = df_pd.groupby("_date")["high"].max()
    daily_low = df_pd.groupby("_date")["low"].min()
    daily_close = df_pd.groupby("_date")["close"].last()
    prev_high_map = daily_high.shift(1).to_dict()
    prev_low_map = daily_low.shift(1).to_dict()
    prev_close_map = daily_close.shift(1).to_dict()
    prev_day_high = np.array([prev_high_map.get(d, np.nan) for d in dates])
    prev_day_low = np.array([prev_low_map.get(d, np.nan) for d in dates])
    prev_day_close = np.array([prev_close_map.get(d, np.nan) for d in dates])

    # Prev-day range stats (added 2026-06-10 per operator decision #127).
    # Used by entry_abnormal_range_followup: detects when prior trading day
    # had an abnormally large range (top quintile of 60-day distribution).
    daily_range = daily_high - daily_low
    daily_midpoint = (daily_high + daily_low) / 2
    daily_range_pctrank = daily_range.rolling(60, min_periods=30).apply(
        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False
    )
    prev_range_map = daily_range.shift(1).to_dict()
    prev_midpoint_map = daily_midpoint.shift(1).to_dict()
    prev_pctrank_map = daily_range_pctrank.shift(1).to_dict()
    prev_day_range = np.array([prev_range_map.get(d, np.nan) for d in dates])
    prev_day_midpoint = np.array([prev_midpoint_map.get(d, np.nan) for d in dates])
    prev_day_range_pctrank_60 = np.array(
        [prev_pctrank_map.get(d, np.nan) for d in dates])

    # Hurst proxy via variance ratio (added 2026-06-03 per operator approval
    # of the hurst_stable filter build). Computed on log-returns; rolling
    # 256-bar window. H ≈ 0.5 = random walk; H < 0.5 = mean-reverting; H > 0.5
    # = trending. Variance-ratio proxy: H_proxy = 1 + log(var(k-step) / (k * var(1-step))) / (2 log(k)).
    # Cheap to compute (single pass per window) and stable enough for filter gating.
    log_ret = np.log(close / np.roll(close, 1))
    log_ret[0] = 0
    def _hurst_window(arr):
        arr = arr[~np.isnan(arr)]
        if len(arr) < 50:
            return np.nan
        var1 = np.var(arr, ddof=0)
        if var1 == 0:
            return np.nan
        # 4-step aggregated variance
        k = 4
        agg = np.add.reduceat(arr[:len(arr) - len(arr) % k],
                              np.arange(0, len(arr) - len(arr) % k, k))
        var_k = np.var(agg, ddof=0) if len(agg) > 1 else np.nan
        if not np.isfinite(var_k) or var_k <= 0:
            return np.nan
        # H_proxy formula
        return 0.5 + 0.5 * (np.log(var_k / (k * var1)) / np.log(k))
    hurst = pd.Series(log_ret).rolling(256, min_periods=128).apply(
        _hurst_window, raw=True
    ).values

    # Donchian channels
    dc_high_20 = df["high"].rolling(20, min_periods=20).max().values
    dc_low_20 = df["low"].rolling(20, min_periods=20).min().values
    dc_high_30 = df["high"].rolling(30, min_periods=30).max().values
    dc_low_30 = df["low"].rolling(30, min_periods=30).min().values

    # Range-compression pctrank (added 2026-06-08 per operator decision #94 Hybrid D-A).
    # Normalized 20-bar trading range divided by close, percentile-ranked over 100 bars.
    # Used by entry_range_compression_break to detect post-compression breakout setups.
    # Low pctrank = current range is tight relative to its recent history = "coiled".
    range_20 = (pd.Series(dc_high_20) - pd.Series(dc_low_20)) / pd.Series(close)
    range_20_pctrank = range_20.rolling(100, min_periods=50).apply(
        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False
    ).values

    # Vol-of-vol regime (added 2026-06-08 per operator decision #106 Hybrid D-A-2).
    # Captures vol-regime-SHIFT moments rather than static low-vol setups (which RCB does).
    # vol_of_vol = 60-bar rolling stdev of ATR; pctrank over 240-bar window.
    # Used by entry_volatility_regime_compound to detect regime transitions.
    atr_s = pd.Series(atr)
    vol_of_vol = atr_s.rolling(60, min_periods=30).std().values
    vol_of_vol_s = pd.Series(vol_of_vol)
    vol_of_vol_pctrank = vol_of_vol_s.rolling(240, min_periods=120).apply(
        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False
    ).values

    # Keltner channels + BB-KC squeeze state (added 2026-06-08 per operator decision #111
    # Hybrid D-A-3). Bollinger-Keltner squeeze is BB inside KC; release fires when
    # squeeze ends. Used by entry_bb_keltner_squeeze.
    # KC = EMA20 +/- 1.5*ATR (standard TTM squeeze convention).
    kc_mult = 1.5
    kc_upper = ema20 + kc_mult * atr
    kc_lower = ema20 - kc_mult * atr
    # Squeeze active when BB is inside KC
    squeeze_on = (bb_upper < kc_upper) & (bb_lower > kc_lower)
    # NaN-aware: if any of BB/KC inputs NaN, squeeze undefined → False
    squeeze_on = squeeze_on & ~(
        np.isnan(bb_upper) | np.isnan(bb_lower)
        | np.isnan(kc_upper) | np.isnan(kc_lower)
    )

    # Daily EMA slope (for macro trend filter)
    df_temp = df.copy()
    df_temp["_date"] = dates
    daily_close = df_temp.groupby("_date")["close"].last()
    daily_ema20 = daily_close.ewm(span=20, adjust=False).mean()
    daily_slope = daily_ema20.diff()
    date_trend = {}
    for d in daily_ema20.index:
        s = daily_slope.get(d, 0)
        date_trend[d] = 0 if pd.isna(s) else (1 if s > 0 else -1)
    bar_trend = np.array([date_trend.get(d, 0) for d in dates])

    # Session boundaries
    in_session = (times >= "09:30") & (times < "15:45")
    entry_ok = in_session & (times >= "09:45") & (times < "14:45")
    flatten_time = times >= "15:30"

    # Opening range (first 6 bars = 30min of session)
    or_high = np.full(n, np.nan)
    or_low = np.full(n, np.nan)
    or_complete = np.zeros(n, dtype=bool)
    sess_bar = 0
    cur_date = None
    cur_or_h = -np.inf
    cur_or_l = np.inf
    for i in range(n):
        if dates[i] != cur_date:
            cur_date = dates[i]
            sess_bar = 0
            cur_or_h = -np.inf
            cur_or_l = np.inf
        if in_session[i]:
            sess_bar += 1
            if sess_bar <= 6:
                cur_or_h = max(cur_or_h, high[i])
                cur_or_l = min(cur_or_l, low[i])
            if sess_bar > 6:
                or_complete[i] = True
        or_high[i] = cur_or_h
        or_low[i] = cur_or_l

    features = {
        "close": close, "high": high, "low": low, "open": opn, "volume": volume,
        "dates": dates, "times": times, "hours": hours, "n": n,
        "atr": atr,
        "ema8": ema8, "ema13": ema13, "ema20": ema20, "ema21": ema21, "ema50": ema50,
        "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_mid": bb_mid,
        "bw_pctrank": bw_pctrank, "atr_pctrank": atr_pctrank, "range_20_pctrank": range_20_pctrank,
        "vol_of_vol": vol_of_vol, "vol_of_vol_pctrank": vol_of_vol_pctrank,
        "kc_upper": kc_upper, "kc_lower": kc_lower, "squeeze_on": squeeze_on,
        "hurst": hurst, "rsi": rsi,
        "prev_day_high": prev_day_high, "prev_day_low": prev_day_low, "prev_day_close": prev_day_close,
        "prev_day_range": prev_day_range, "prev_day_midpoint": prev_day_midpoint,
        "prev_day_range_pctrank_60": prev_day_range_pctrank_60,
        "vwap": vwap,
        "dc_high_20": dc_high_20, "dc_low_20": dc_low_20,
        "dc_high_30": dc_high_30, "dc_low_30": dc_low_30,
        "bar_trend": bar_trend,
        "in_session": in_session, "entry_ok": entry_ok, "flatten_time": flatten_time,
        "or_high": or_high, "or_low": or_low, "or_complete": or_complete,
    }
    if key is not None:
        _FEATURE_CACHE[key] = features
    return features


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: ENTRY COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

def entry_pb_pullback(f, i, state, params):
    """PB-style pullback entry: price pulls back to fast EMA in trend."""
    if f["ema21"][i] > f["ema50"][i] and not state["long_traded_today"]:
        proximity = abs(f["close"][i] - f["ema8"][i]) / f["atr"][i]
        if proximity < params.get("pb_proximity", 0.5):
            if f["close"][i] > f["close"][i-1]:  # Bullish bounce
                stop = f["close"][i] - f["atr"][i] * params.get("stop_mult", 1.5)
                target = f["close"][i] + f["atr"][i] * params.get("target_mult", 3.0)
                return 1, stop, target
    if f["ema21"][i] < f["ema50"][i] and not state["short_traded_today"]:
        proximity = abs(f["close"][i] - f["ema8"][i]) / f["atr"][i]
        if proximity < params.get("pb_proximity", 0.5):
            if f["close"][i] < f["close"][i-1]:  # Bearish bounce
                stop = f["close"][i] + f["atr"][i] * params.get("stop_mult", 1.5)
                target = f["close"][i] - f["atr"][i] * params.get("target_mult", 3.0)
                return -1, stop, target
    return 0, 0, 0


def entry_orb_breakout(f, i, state, params):
    """ORB-style breakout: price breaks opening range after first 30min."""
    if not f["or_complete"][i]:
        return 0, 0, 0
    or_h = f["or_high"][i]
    or_l = f["or_low"][i]
    if np.isnan(or_h) or np.isinf(or_h):
        return 0, 0, 0
    if f["close"][i] > or_h and not state["long_traded_today"]:
        stop = or_l - f["atr"][i] * params.get("stop_mult", 0.5)
        target = f["close"][i] + f["atr"][i] * params.get("target_mult", 3.0)
        return 1, stop, target
    if f["close"][i] < or_l and not state["short_traded_today"]:
        stop = or_h + f["atr"][i] * params.get("stop_mult", 0.5)
        target = f["close"][i] - f["atr"][i] * params.get("target_mult", 3.0)
        return -1, stop, target
    return 0, 0, 0


def entry_vwap_continuation(f, i, state, params):
    """VWAP continuation: pullback to VWAP in trend direction."""
    vwap_dist = (f["close"][i] - f["vwap"][i]) / f["atr"][i]
    prox = params.get("vwap_proximity", 0.5)
    if np.isnan(f["vwap"][i]):
        return 0, 0, 0
    # Long: price was above VWAP, pulled back near it, bouncing
    if (not state["long_traded_today"]
            and f["ema21"][i] > f["ema50"][i]
            and abs(vwap_dist) < prox
            and f["close"][i] > f["open"][i]
            and f["close"][i] > f["close"][i-1]):
        stop = f["close"][i] - f["atr"][i] * params.get("stop_mult", 2.0)
        target = f["close"][i] + f["atr"][i] * params.get("target_mult", 3.0)
        return 1, stop, target
    # Short: below VWAP, pulled back up, rejecting
    if (not state["short_traded_today"]
            and f["ema21"][i] < f["ema50"][i]
            and abs(vwap_dist) < prox
            and f["close"][i] < f["open"][i]
            and f["close"][i] < f["close"][i-1]):
        stop = f["close"][i] + f["atr"][i] * params.get("stop_mult", 2.0)
        target = f["close"][i] - f["atr"][i] * params.get("target_mult", 3.0)
        return -1, stop, target
    return 0, 0, 0


def entry_donchian_breakout(f, i, state, params):
    """Donchian channel breakout: new N-bar high/low.

    Bug fix 2026-05-28: previously compared `close[i]` to `dc_high_{ch_len}[i]`,
    but the feature `dc_high_N[i]` includes the current bar's high in the rolling
    max — so the breakout condition `close > dc_high[i]` was logically impossible
    (the max of a window including high[i] is always >= high[i] >= close[i]).
    Result: Donchian primitive produced 0 trades on every asset (Phase 5 + 6
    diagnostic). Standard Donchian formulation compares to PRIOR window's
    extreme, so we now read [i-1]. Guard against i == 0.
    """
    if i == 0:
        return 0, 0, 0
    ch_len = params.get("channel_len", 20)
    key_h = f"dc_high_{ch_len}" if f"dc_high_{ch_len}" in f else "dc_high_20"
    key_l = f"dc_low_{ch_len}" if f"dc_low_{ch_len}" in f else "dc_low_20"
    dc_h = f[key_h][i-1]
    dc_l = f[key_l][i-1]
    if np.isnan(dc_h) or np.isnan(dc_l):
        return 0, 0, 0
    if f["close"][i] > dc_h and not state["long_traded_today"]:
        stop = f["close"][i] - f["atr"][i] * params.get("stop_mult", 2.5)
        target = f["close"][i] + f["atr"][i] * params.get("target_mult", 4.0)
        return 1, stop, target
    if f["close"][i] < dc_l and not state["short_traded_today"]:
        stop = f["close"][i] + f["atr"][i] * params.get("stop_mult", 2.5)
        target = f["close"][i] - f["atr"][i] * params.get("target_mult", 4.0)
        return -1, stop, target
    return 0, 0, 0


def entry_prior_day_break(f, i, state, params):
    """Prior-day high/low breakout (added 2026-06-04 Core Daily Hunt unlock).
    LONG when close > prev_day_high; SHORT when close < prev_day_low.
    Fail-closed on missing prev-day data."""
    if i == 0:
        return 0, 0, 0
    ph = f["prev_day_high"][i]
    pl = f["prev_day_low"][i]
    if np.isnan(ph) or np.isnan(pl) or np.isnan(f["atr"][i]) or f["atr"][i] == 0:
        return 0, 0, 0
    close = f["close"][i]
    prev_close = f["close"][i-1]
    # Long: close breaks above prev high; require fresh break (prev bar was at-or-below)
    if (not state["long_traded_today"]
            and close > ph and prev_close <= ph):
        stop = close - f["atr"][i] * params.get("stop_mult", 2.0)
        target = close + f["atr"][i] * params.get("target_mult", 4.0)
        return 1, stop, target
    if (not state["short_traded_today"]
            and close < pl and prev_close >= pl):
        stop = close + f["atr"][i] * params.get("stop_mult", 2.0)
        target = close - f["atr"][i] * params.get("target_mult", 4.0)
        return -1, stop, target
    return 0, 0, 0


def entry_prior_day_fade(f, i, state, params):
    """Prior-day high/low fade (reversion). Fires when price overshoots prev
    high/low then closes back inside. LONG on close back above prev high after
    overshoot below (rare); SHORT on close back below prev low after overshoot
    above (rare). v1: simplified — fades a break-then-reject in same bar."""
    if i == 0:
        return 0, 0, 0
    ph = f["prev_day_high"][i]
    pl = f["prev_day_low"][i]
    if np.isnan(ph) or np.isnan(pl) or np.isnan(f["atr"][i]) or f["atr"][i] == 0:
        return 0, 0, 0
    high = f["high"][i]; low = f["low"][i]; close = f["close"][i]
    # Short fade: bar pierced above prev high but closed below it
    if (not state["short_traded_today"]
            and high > ph and close < ph):
        stop = close + f["atr"][i] * params.get("stop_mult", 1.5)
        target = close - f["atr"][i] * params.get("target_mult", 2.5)
        return -1, stop, target
    # Long fade: bar pierced below prev low but closed above it
    if (not state["long_traded_today"]
            and low < pl and close > pl):
        stop = close - f["atr"][i] * params.get("stop_mult", 1.5)
        target = close + f["atr"][i] * params.get("target_mult", 2.5)
        return 1, stop, target
    return 0, 0, 0


def entry_vol_expansion(f, i, state, params):
    """Vol-expansion entry (added 2026-06-04 per operator approval).

    Fires when atr_pctrank crosses ABOVE `vx_high` from below (default 70) AND
    a confirmation condition is met. Direction:
      - LONG if close > ema20 AND close > prior bar close (vol expansion to the upside)
      - SHORT if close < ema20 AND close < prior bar close (vol expansion to the downside)
    Otherwise no entry.

    Defaults are conservative; vx_high is configurable via params for sweep testing.
    """
    if i < 1:
        return 0, 0, 0
    pct = f["atr_pctrank"][i]
    pct_prev = f["atr_pctrank"][i-1]
    if np.isnan(pct) or np.isnan(pct_prev):
        return 0, 0, 0
    vx_high = params.get("vx_high", 70)
    # Must cross UP through threshold (was below, now above)
    if not (pct_prev < vx_high <= pct):
        return 0, 0, 0
    close, prev_close, ema20 = f["close"][i], f["close"][i-1], f["ema20"][i]
    if np.isnan(ema20) or np.isnan(f["atr"][i]) or f["atr"][i] == 0:
        return 0, 0, 0
    # Long: above ema20 + bullish bar
    if (not state["long_traded_today"]
            and close > ema20 and close > prev_close):
        stop = close - f["atr"][i] * params.get("stop_mult", 2.0)
        target = close + f["atr"][i] * params.get("target_mult", 4.0)
        return 1, stop, target
    # Short: below ema20 + bearish bar
    if (not state["short_traded_today"]
            and close < ema20 and close < prev_close):
        stop = close + f["atr"][i] * params.get("stop_mult", 2.0)
        target = close - f["atr"][i] * params.get("target_mult", 4.0)
        return -1, stop, target
    return 0, 0, 0


def entry_abnormal_range_followup(f, i, state, params):
    """Abnormal-range-day follow-up entry (added 2026-06-10 per operator decision #127).

    Mechanism: at the open of session N+1, if PRIOR DAY's total range (high-low)
    was abnormally large (top quintile of 60-day distribution, pctrank >= 80),
    enter a position aligned with prior-day direction (continuation mode) or
    against it (fade mode).

    Prior-day direction is determined by close vs midpoint of prior-day range:
      - close above midpoint = bullish day
      - close below midpoint = bearish day

    Continuation mode trades in the direction of yesterday's close:
      - bullish abnormal day → LONG today
      - bearish abnormal day → SHORT today

    Fade mode trades against:
      - bullish abnormal day → SHORT today
      - bearish abnormal day → LONG today

    Different from all 5 tested mechanism families (compression, vol-regime,
    squeeze, gap-fade, sweep-reversal) — operates on DAILY range pctrank and
    triggers on FOLLOWING day's session open.

    Fail-closed:
      - i < 1: no signal
      - Not in session, or beyond session_open_bars from start: no signal
      - NaN in prev_day_range_pctrank_60, prev_day_close, or prev_day_midpoint: no signal
      - pctrank < threshold (not abnormal): no signal
      - Zero ATR: no signal
      - Unknown mode: no signal

    Params (all optional, conservative defaults):
      mode: "continuation" or "fade" (default "continuation")
      pctrank_threshold: 80          — top quintile of 60-day range distribution
      session_open_bars: 3           — fire within first N bars of session
      stop_mult: 1.5                 — ATR multiplier for stop
      target_mult: 3.0               — ATR multiplier for target
    """
    if i < 1:
        return 0, 0, 0
    # Bug fix 2026-06-10 per #130: use entry_ok instead of in_session.
    # entry_ok = in_session & times >= 09:45; the signal generator filters
    # at the entry_ok layer so any "first N session bars" detection that
    # uses in_session before 09:45 will be silently blocked.
    if not f["entry_ok"][i]:
        return 0, 0, 0
    # Count consecutive entry_ok bars ending at i; must be early
    session_open_bars = params.get("session_open_bars", 3)
    n_consecutive = 0
    j = i
    while j >= 0 and f["entry_ok"][j]:
        n_consecutive += 1
        j -= 1
        if n_consecutive > session_open_bars:
            return 0, 0, 0
    if n_consecutive == 0:
        return 0, 0, 0
    pctrank = f["prev_day_range_pctrank_60"][i]
    prev_close = f["prev_day_close"][i]
    prev_mid = f["prev_day_midpoint"][i]
    if np.isnan(pctrank) or np.isnan(prev_close) or np.isnan(prev_mid):
        return 0, 0, 0
    threshold = params.get("pctrank_threshold", 80)
    if pctrank < threshold:
        return 0, 0, 0
    yesterday_bullish = prev_close > prev_mid
    yesterday_bearish = prev_close < prev_mid
    if not (yesterday_bullish or yesterday_bearish):
        return 0, 0, 0
    mode = params.get("mode", "continuation")
    if mode == "continuation":
        long_signal = yesterday_bullish
        short_signal = yesterday_bearish
    elif mode == "fade":
        long_signal = yesterday_bearish
        short_signal = yesterday_bullish
    else:
        return 0, 0, 0
    close = f["close"][i]
    atr_i = f["atr"][i]
    if np.isnan(atr_i) or atr_i == 0:
        return 0, 0, 0
    if long_signal and not state["long_traded_today"]:
        stop = close - atr_i * params.get("stop_mult", 1.5)
        target = close + atr_i * params.get("target_mult", 3.0)
        return 1, stop, target
    if short_signal and not state["short_traded_today"]:
        stop = close + atr_i * params.get("stop_mult", 1.5)
        target = close - atr_i * params.get("target_mult", 3.0)
        return -1, stop, target
    return 0, 0, 0


def entry_stop_run_reversal(f, i, state, params):
    """Stop-run reversal entry (added 2026-06-09 per operator decision #118 chain + SMP-3).

    Mechanism: detects liquidity sweeps + reversals. When price sweeps through
    prior N-bar swing high (or low) AND reclaims the level within the same bar
    (close back below swept high / above swept low), enter in REVERSAL direction.

    Sweep-up + reclaim → SHORT (against the failed breakout)
    Sweep-down + reclaim → LONG (against the failed breakdown)

    Different from RCB/VRC/BBKC/gap_fill — targets the "stop-hunting" pattern
    documented in market microstructure literature: institutional flows often
    push price beyond visible stops, then reverse once the liquidity is swept.

    Filter pre-flight check (#120):
    - Thesis: reversal (against the direction of the sweep)
    - ema_slope INCOMPATIBLE — filter rejects against-trend trades, but
      reversal entries are by construction against the prior move
    - First batch should use filter=none, vol_regime high, or session_morning

    Fail-closed:
      - i < 1: no signal
      - NaN in dc_high_20[i-1] or dc_low_20[i-1]: no signal
      - Zero ATR: no signal

    Params (all optional, conservative defaults):
      sweep_buffer: 0.0          — extra threshold beyond dc level (in ATR units)
      stop_mult: 1.5             — ATR multiplier for stop
      target_mult: 3.0           — ATR multiplier for target
    """
    if i < 1:
        return 0, 0, 0
    swing_h = f["dc_high_20"][i-1]
    swing_l = f["dc_low_20"][i-1]
    if np.isnan(swing_h) or np.isnan(swing_l):
        return 0, 0, 0
    high_i = f["high"][i]
    low_i = f["low"][i]
    close_i = f["close"][i]
    atr_i = f["atr"][i]
    if np.isnan(atr_i) or atr_i == 0:
        return 0, 0, 0
    sweep_buffer = params.get("sweep_buffer", 0.0)
    sweep_h = swing_h + sweep_buffer * atr_i
    sweep_l = swing_l - sweep_buffer * atr_i
    # Sweep-up + reclaim → SHORT
    if (high_i > sweep_h and close_i < swing_h
            and not state["short_traded_today"]):
        stop = high_i + atr_i * params.get("stop_mult", 1.5)
        target = close_i - atr_i * params.get("target_mult", 3.0)
        return -1, stop, target
    # Sweep-down + reclaim → LONG
    if (low_i < sweep_l and close_i > swing_l
            and not state["long_traded_today"]):
        stop = low_i - atr_i * params.get("stop_mult", 1.5)
        target = close_i + atr_i * params.get("target_mult", 3.0)
        return 1, stop, target
    return 0, 0, 0


def entry_gap_fill_trigger(f, i, state, params):
    """Gap-fill fade entry (added 2026-06-09 per operator decision #116).

    Mechanism: at the open of the RTH session, if price has gapped beyond
    `min_gap_atr` × ATR from the prior session close, enter in the FADE
    direction (toward prior close):
      - Gap UP → SHORT toward prev_day_close
      - Gap DOWN → LONG toward prev_day_close

    Different from range_compression_break / bb_keltner_squeeze (which are
    intraday vol-contraction-then-expansion mechanisms) — gap_fill is a
    structural overnight repricing mean-reversion mechanism. Should fire
    rarely (only on large gaps in first N bars of session).

    Fail-closed:
      - i < 1: no signal
      - Not in session (or not within first N session bars): no signal
      - NaN prev_day_close / ATR: no signal
      - Zero ATR: no signal
      - Gap < threshold: no signal

    Params (all optional, conservative defaults):
      min_gap_atr: 0.5         — minimum gap as multiple of ATR
      session_open_bars: 3     — fire within first N bars of session only
      stop_mult: 1.5           — ATR multiplier for stop
      target_to_close: True    — target = prev_day_close (natural fade target)
      target_mult: 3.0         — used only if target_to_close = False
    """
    if i < 1:
        return 0, 0, 0
    # Bug fix 2026-06-10 per #131: use entry_ok instead of in_session.
    # entry_ok = in_session & times >= 09:45; the signal generator filters
    # at the entry_ok layer so any "first N session bars" detection that
    # uses in_session before 09:45 will be silently blocked.
    if not f["entry_ok"][i]:
        return 0, 0, 0
    # Count consecutive entry_ok bars ending at i (= bars into entry window)
    session_open_bars = params.get("session_open_bars", 3)
    n_consecutive = 0
    j = i
    while j >= 0 and f["entry_ok"][j]:
        n_consecutive += 1
        j -= 1
        if n_consecutive > session_open_bars:
            return 0, 0, 0
    if n_consecutive == 0:
        return 0, 0, 0
    prev_close = f["prev_day_close"][i]
    if np.isnan(prev_close):
        return 0, 0, 0
    close = f["close"][i]
    atr_i = f["atr"][i]
    if np.isnan(atr_i) or atr_i == 0:
        return 0, 0, 0
    gap = close - prev_close
    min_gap_dollar = params.get("min_gap_atr", 0.5) * atr_i
    if abs(gap) < min_gap_dollar:
        return 0, 0, 0
    target_to_close = params.get("target_to_close", True)
    # Gap UP → fade short
    if gap > 0:
        if state["short_traded_today"]:
            return 0, 0, 0
        stop = close + atr_i * params.get("stop_mult", 1.5)
        target = prev_close if target_to_close else (close - atr_i * params.get("target_mult", 3.0))
        return -1, stop, target
    # Gap DOWN → fade long
    if state["long_traded_today"]:
        return 0, 0, 0
    stop = close - atr_i * params.get("stop_mult", 1.5)
    target = prev_close if target_to_close else (close + atr_i * params.get("target_mult", 3.0))
    return 1, stop, target


def entry_bb_keltner_squeeze(f, i, state, params):
    """Bollinger-Keltner squeeze release (added 2026-06-08 per operator decision #111).

    Mechanism: when the Bollinger bands are inside the Keltner channels
    ("squeeze on"), volatility is contracted. When the squeeze releases
    (BB expands back outside KC), historical research suggests a strong
    directional move often follows. Enter at the release in the direction
    of the momentum signal (ema20 slope: rising = long, falling = short).

    Different from RCB and VRC:
      - RCB: single-bar compression-then-break (Bollinger range pctrank)
      - VRC: regime-shift in vol-of-vol (now archived)
      - BB-KC squeeze: structural compression of BB inside KC, release fires
        the entry. Classic TTM-squeeze methodology.

    Fail-closed:
      - i < 1: no signal
      - NaN in squeeze_on (i or i-1): no signal
      - NaN in ATR / ema20: no signal
      - Zero ATR: no signal

    Params (all optional with conservative defaults):
      min_squeeze_bars: 3      — squeeze must have been on for >= this many bars
      stop_mult: 1.5           — ATR multiplier for stop
      target_mult: 3.0         — ATR multiplier for target
    """
    if i < 1:
        return 0, 0, 0
    sq_now = f["squeeze_on"][i]
    sq_prev = f["squeeze_on"][i-1]
    if np.isnan(sq_now) or np.isnan(sq_prev):
        return 0, 0, 0
    # Release condition: was on, now off
    if not (sq_prev and not sq_now):
        return 0, 0, 0
    # Verify sufficient squeeze history
    min_bars = params.get("min_squeeze_bars", 3)
    bars_back = min(i, min_bars)
    count_on = 0
    for j in range(i - bars_back, i):
        sj = f["squeeze_on"][j]
        if not np.isnan(sj) and sj:
            count_on += 1
    if count_on < min_bars:
        return 0, 0, 0
    close = f["close"][i]
    if np.isnan(f["atr"][i]) or f["atr"][i] == 0:
        return 0, 0, 0
    if np.isnan(f["ema20"][i]):
        return 0, 0, 0
    # Direction by ema20 slope (price vs ema20)
    if (not state["long_traded_today"]
            and close > f["ema20"][i]):
        stop = close - f["atr"][i] * params.get("stop_mult", 1.5)
        target = close + f["atr"][i] * params.get("target_mult", 3.0)
        return 1, stop, target
    if (not state["short_traded_today"]
            and close < f["ema20"][i]):
        stop = close + f["atr"][i] * params.get("stop_mult", 1.5)
        target = close - f["atr"][i] * params.get("target_mult", 3.0)
        return -1, stop, target
    return 0, 0, 0


def entry_volatility_regime_compound(f, i, state, params):
    """Vol-regime-compound entry (added 2026-06-08 per operator decision #106 Hybrid D-A-2).

    Mechanism: rolling stdev of ATR (vol-of-vol) was in LOW percentile of its
    own history within the last `transition_window_bars` bars, AND is now in
    HIGH percentile. Captures the regime-SHIFT moment — when the market
    transitions from quiet vol environment to expanding vol environment.

    This is different from `range_compression_break`:
      - RCB: single-bar compression trigger (low-vol → break in next bar)
      - vol_regime_compound: regime transition (sustained vol shift, multi-bar)

    Direction is detected via ema21 vs ema50 (matching pb_pullback convention).
    Compatible with all filters via composition (filter applied on top).

    Fail-closed:
      - i < 1 or NaN in vol_of_vol_pctrank → no signal
      - Zero ATR → no signal
      - Missing ema21/ema50 → no signal

    Params (all optional with conservative defaults):
      regime_low_pct_max: 25        — max percentile defining "low vol regime"
      regime_high_pct_min: 75       — min percentile defining "high vol regime"
      transition_window_bars: 5     — bars back to look for low-vol baseline
      stop_mult: 1.5                — ATR multiplier for stop
      target_mult: 3.0              — ATR multiplier for target
    """
    if i < 1:
        return 0, 0, 0
    low_pct_max = params.get("regime_low_pct_max", 25)
    high_pct_min = params.get("regime_high_pct_min", 75)
    transition_window = params.get("transition_window_bars", 5)
    pct_now = f["vol_of_vol_pctrank"][i]
    # Fail-closed: must have a valid current-bar vol-regime measurement
    if np.isnan(pct_now) or pct_now < high_pct_min:
        return 0, 0, 0
    # Look back transition_window bars for a low-vol regime baseline
    was_low = False
    start = max(0, i - transition_window)
    for j in range(start, i):
        pct_j = f["vol_of_vol_pctrank"][j]
        if not np.isnan(pct_j) and pct_j <= low_pct_max:
            was_low = True
            break
    if not was_low:
        return 0, 0, 0
    close = f["close"][i]
    if np.isnan(f["atr"][i]) or f["atr"][i] == 0:
        return 0, 0, 0
    if np.isnan(f["ema21"][i]) or np.isnan(f["ema50"][i]):
        return 0, 0, 0
    # Direction by ema21 vs ema50 (matching pb_pullback convention)
    if (not state["long_traded_today"]
            and f["ema21"][i] > f["ema50"][i]):
        stop = close - f["atr"][i] * params.get("stop_mult", 1.5)
        target = close + f["atr"][i] * params.get("target_mult", 3.0)
        return 1, stop, target
    if (not state["short_traded_today"]
            and f["ema21"][i] < f["ema50"][i]):
        stop = close + f["atr"][i] * params.get("stop_mult", 1.5)
        target = close - f["atr"][i] * params.get("target_mult", 3.0)
        return -1, stop, target
    return 0, 0, 0


def entry_range_compression_break(f, i, state, params):
    """Range-compression break (added 2026-06-08 per operator decision #94 Hybrid D-A).

    Mechanism: the 20-bar trading range was in a low percentile of its own
    100-bar history ("compression" / "coiled") on the prior bar, and the
    current bar closes outside the prior bar's 20-bar range ("break" /
    "expansion"). Captures the post-volatility-contraction breakout pattern
    often called "squeeze break" or "coil expansion".

    This is a tail-frequency signal — fires rarely (only after compression)
    rather than at every session open like ORB. Designed to test a
    DIFFERENT market condition than the existing primitive set, which the
    08c+08d wipeout proved is exhausted for non-ORB workhorse discovery.

    Fail-closed: NaN in `range_20_pctrank` (early bars before 50-bar warm-up)
    or NaN in `dc_high_20` / `dc_low_20` → no signal. Zero ATR → no signal.

    Params (all optional with conservative defaults):
      compression_pct_max: 30  — max percentile to qualify as compressed
      stop_mult: 1.5            — ATR multiplier for stop
      target_mult: 3.0          — ATR multiplier for target
    """
    if i < 1:
        return 0, 0, 0
    compression_max_pct = params.get("compression_pct_max", 30)
    pct_prev = f["range_20_pctrank"][i-1]
    # Fail-closed: must have a valid prior-bar compression measurement
    if np.isnan(pct_prev) or pct_prev > compression_max_pct:
        return 0, 0, 0
    # Break check: close[i] vs prior bar's 20-bar range
    range_h = f["dc_high_20"][i-1]
    range_l = f["dc_low_20"][i-1]
    if np.isnan(range_h) or np.isnan(range_l):
        return 0, 0, 0
    close = f["close"][i]
    if np.isnan(f["atr"][i]) or f["atr"][i] == 0:
        return 0, 0, 0
    # LONG: close breaks above prior 20-bar high
    if (not state["long_traded_today"]
            and close > range_h):
        stop = close - f["atr"][i] * params.get("stop_mult", 1.5)
        target = close + f["atr"][i] * params.get("target_mult", 3.0)
        return 1, stop, target
    # SHORT: close breaks below prior 20-bar low
    if (not state["short_traded_today"]
            and close < range_l):
        stop = close + f["atr"][i] * params.get("stop_mult", 1.5)
        target = close - f["atr"][i] * params.get("target_mult", 3.0)
        return -1, stop, target
    return 0, 0, 0


def entry_bb_reversion(f, i, state, params):
    """BB stretch reversion: price touched outer band, now bouncing back inside."""
    if np.isnan(f["bb_upper"][i]) or np.isnan(f["rsi"][i]):
        return 0, 0, 0
    rsi_os = params.get("rsi_oversold", 35)
    rsi_ob = params.get("rsi_overbought", 65)
    # Long: prior bar below lower band, current bar closes back above
    if (not state["long_traded_today"]
            and i > 0 and f["low"][i-1] <= f["bb_lower"][i-1]
            and f["close"][i] > f["bb_lower"][i]
            and f["rsi"][i] < rsi_os):
        stop = f["close"][i] - f["atr"][i] * params.get("stop_mult", 1.5)
        target = f["bb_mid"][i]
        return 1, stop, target
    # Short: prior bar above upper band, current bar closes back below
    if (not state["short_traded_today"]
            and i > 0 and f["high"][i-1] >= f["bb_upper"][i-1]
            and f["close"][i] < f["bb_upper"][i]
            and f["rsi"][i] > rsi_ob):
        stop = f["close"][i] + f["atr"][i] * params.get("stop_mult", 1.5)
        target = f["bb_mid"][i]
        return -1, stop, target
    return 0, 0, 0


# ═══════════════════════════════════════════════════════════════════════════
# PART 3: EXIT COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

def exit_atr_trail(f, i, state, params):
    """ATR trailing stop exit."""
    pos = state["position"]
    mult = params.get("trail_mult", 2.5)
    if pos == 1:
        if f["high"][i] > state["highest"]:
            state["highest"] = f["high"][i]
            new_trail = state["highest"] - f["atr"][i] * mult
            if new_trail > state["trailing_stop"]:
                state["trailing_stop"] = new_trail
        if f["low"][i] <= state["trailing_stop"]:
            return 1
    elif pos == -1:
        if f["low"][i] < state["lowest"]:
            state["lowest"] = f["low"][i]
            new_trail = state["lowest"] + f["atr"][i] * mult
            if new_trail < state["trailing_stop"]:
                state["trailing_stop"] = new_trail
        if f["high"][i] >= state["trailing_stop"]:
            return -1
    return 0


def _compute_ladder_lock_r(current_r, target_mult, trail_mult):
    """Compute the highest lock level reached, given current R and ladder params.

    Configurable ladder formula:
      At milestone kR (k = 1, 2, ..., floor(target_mult)), lock at:
        lock_r = max(0, k - (1.0 / trail_mult))

    Interpretation:
      trail_mult = 1.0 → lock_r = k - 1 → locks at 0R/1R/2R/3R (breakeven then tight)
      trail_mult = 2.0 → lock_r = k - 0.5 → tighter: locks at 0.5R/1.5R/2.5R/...
      trail_mult = 0.5 → lock_r = k - 2 → looser: locks at 0R/0R/1R/2R/... (clamped)

    target_mult controls ladder length; larger values add higher milestones.
    """
    if current_r < 1.0:
        return 0.0
    spread = 1.0 / trail_mult
    lock_r = 0.0
    max_k = int(min(target_mult, current_r)) + 1  # +1 to be inclusive
    for k in range(1, max_k + 1):
        if current_r >= k and k <= target_mult:
            candidate = max(0.0, k - spread)
            if candidate > lock_r:
                lock_r = candidate
    return lock_r


def exit_profit_ladder(f, i, state, params):
    """Ratcheting stops at R-milestones.

    Two modes, selected by `ladder_style` param (defaults to "classic"):

    1. "classic" (DEFAULT — preserves original hardcoded behavior):
         1R → lock 0.25R, 2R → lock 1R, 3R → lock 2R

    2. "configurable" (NEW — exposes target_mult and trail_mult as real dials):
         Uses _compute_ladder_lock_r() formula:
         At milestone kR for k=1..target_mult: lock at max(0, k - 1/trail_mult) * R

         - target_mult: ladder length (default 3.0 = 3 milestones; 5.0 = 5 milestones)
         - trail_mult: lock tightness (higher = tighter)

    IMPORTANT: "classic" mode exists to preserve the live xb_orb_ema_ladder
    probation variant unchanged. The bug fix is opt-in via
    ladder_style="configurable" to avoid disrupting forward evidence accumulation.
    """
    pos = state["position"]
    entry_price = state["entry_price"]
    initial_risk = state["initial_risk"]
    if initial_risk <= 0:
        return exit_atr_trail(f, i, state, params)

    ladder_style = params.get("ladder_style", "classic")

    if pos == 1:
        if f["high"][i] > state["highest"]:
            state["highest"] = f["high"][i]
        current_r = (state["highest"] - entry_price) / initial_risk

        if ladder_style == "classic":
            if current_r >= 3.0:
                lock_price = entry_price + initial_risk * 2.0
            elif current_r >= 2.0:
                lock_price = entry_price + initial_risk * 1.0
            elif current_r >= 1.0:
                lock_price = entry_price + initial_risk * 0.25
            else:
                lock_price = state["trailing_stop"]
        else:  # configurable
            target_mult = params.get("target_mult", 3.0)
            trail_mult = params.get("trail_mult", 1.0)
            lock_r = _compute_ladder_lock_r(current_r, target_mult, trail_mult)
            if lock_r > 0:
                lock_price = entry_price + initial_risk * lock_r
            else:
                lock_price = state["trailing_stop"]

        state["trailing_stop"] = max(state["trailing_stop"], lock_price)
        if f["low"][i] <= state["trailing_stop"]:
            return 1

    elif pos == -1:
        if f["low"][i] < state["lowest"]:
            state["lowest"] = f["low"][i]
        current_r = (entry_price - state["lowest"]) / initial_risk

        if ladder_style == "classic":
            if current_r >= 3.0:
                lock_price = entry_price - initial_risk * 2.0
            elif current_r >= 2.0:
                lock_price = entry_price - initial_risk * 1.0
            elif current_r >= 1.0:
                lock_price = entry_price - initial_risk * 0.25
            else:
                lock_price = state["trailing_stop"]
        else:  # configurable
            target_mult = params.get("target_mult", 3.0)
            trail_mult = params.get("trail_mult", 1.0)
            lock_r = _compute_ladder_lock_r(current_r, target_mult, trail_mult)
            if lock_r > 0:
                lock_price = entry_price - initial_risk * lock_r
            else:
                lock_price = state["trailing_stop"]

        state["trailing_stop"] = min(state["trailing_stop"], lock_price)
        if f["high"][i] >= state["trailing_stop"]:
            return -1
    return 0


def exit_midline_target(f, i, state, params):
    """Exit at BB midline (SMA20) or VWAP — mean reversion target."""
    pos = state["position"]
    min_hold = params.get("min_hold", 3)
    if state["bars_in_trade"] < min_hold:
        return exit_atr_trail(f, i, state, params)
    target_type = params.get("midline_type", "bb")
    target = f["bb_mid"][i] if target_type == "bb" else f["vwap"][i]
    if np.isnan(target):
        return exit_atr_trail(f, i, state, params)
    if pos == 1 and f["high"][i] >= target:
        return 1
    elif pos == -1 and f["low"][i] <= target:
        return -1
    return exit_atr_trail(f, i, state, params)


def exit_chandelier(f, i, state, params):
    """Chandelier exit: highest high / lowest low - ATR × mult."""
    pos = state["position"]
    mult = params.get("chandelier_mult", 3.0)
    if pos == 1:
        if f["high"][i] > state["highest"]:
            state["highest"] = f["high"][i]
        chandelier_stop = state["highest"] - f["atr"][i] * mult
        state["trailing_stop"] = max(state["trailing_stop"], chandelier_stop)
        if f["low"][i] <= state["trailing_stop"]:
            return 1
    elif pos == -1:
        if f["low"][i] < state["lowest"]:
            state["lowest"] = f["low"][i]
        chandelier_stop = state["lowest"] + f["atr"][i] * mult
        state["trailing_stop"] = min(state["trailing_stop"], chandelier_stop)
        if f["high"][i] >= state["trailing_stop"]:
            return -1
    return 0


def exit_time_stop(f, i, state, params):
    """Max bars in trade, then exit. Falls back to ATR trail otherwise."""
    max_bars = params.get("max_bars", 40)
    if state["bars_in_trade"] >= max_bars:
        return 1 if state["position"] == 1 else -1
    return exit_atr_trail(f, i, state, params)


def exit_fixed_ratio(f, i, state, params):
    """Fixed R-ratio exit (added 2026-06-05 per operator approval #69).

    Exits at `ratio × initial_risk` in profit direction OR at initial stop.
    No trailing; clean fixed-target / fixed-stop. Good for testing reward-risk
    ratios as a direct lever (1:1, 1:2, 1:3 etc.).
    """
    pos = state["position"]
    ratio = params.get("ratio", 2.0)
    risk = state["initial_risk"]
    entry = state["entry_price"]
    stop = state["trailing_stop"]
    if pos == 1:
        target = entry + ratio * risk
        if f["low"][i] <= stop:
            return 1
        if f["high"][i] >= target:
            return 1
    elif pos == -1:
        target = entry - ratio * risk
        if f["high"][i] >= stop:
            return -1
        if f["low"][i] <= target:
            return -1
    return 0


# ═══════════════════════════════════════════════════════════════════════════
# PART 4: FILTER COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

def filter_none(f, i, signal, params):
    """No filter — allow all entries."""
    return signal


def filter_ema_slope(f, i, signal, params):
    """Daily EMA slope: longs in uptrend, shorts in downtrend."""
    if signal == 1 and f["bar_trend"][i] != 1:
        return 0
    if signal == -1 and f["bar_trend"][i] != -1:
        return 0
    return signal


def filter_vwap_slope(f, i, signal, params):
    """VWAP direction: longs when price above VWAP, shorts below."""
    if np.isnan(f["vwap"][i]):
        return 0
    if signal == 1 and f["close"][i] < f["vwap"][i]:
        return 0
    if signal == -1 and f["close"][i] > f["vwap"][i]:
        return 0
    return signal


def filter_bandwidth_squeeze(f, i, signal, params):
    """BB bandwidth below percentile threshold — only trade in compression."""
    threshold = params.get("bw_threshold", 50)
    if np.isnan(f["bw_pctrank"][i]) or f["bw_pctrank"][i] > threshold:
        return 0
    return signal


def filter_session_morning(f, i, signal, params):
    """Morning session only (09:45-12:00)."""
    if f["hours"][i] >= 12:
        return 0
    return signal


def filter_vol_regime(f, i, signal, params):
    """Vol-regime gate via ATR percentile rank (added 2026-06-02).

    Pass the signal only when atr_pctrank ∈ [vr_low_pct, vr_high_pct].
    - vr_low_pct=70, vr_high_pct=100 → high-vol-only
    - vr_low_pct=0,  vr_high_pct=30  → low-vol-only
    - vr_low_pct=30, vr_high_pct=70  → mid-vol-only
    Defaults pass everything (no-op), so registering this filter alone with no
    params is safe — the filter only restricts when the params are set.
    """
    pct = f["atr_pctrank"][i]
    if np.isnan(pct):
        return 0
    low = params.get("vr_low_pct", 0)
    high = params.get("vr_high_pct", 100)
    if pct < low or pct > high:
        return 0
    return signal


def filter_ema_slope_vol_high(f, i, signal, params):
    """Stacked filter: ema_slope AND atr_pctrank >= vr_threshold.
    Composes the proven trio's trend gate with a vol-expansion gate; built for
    the concentration-mutation Plan B lane (added 2026-06-02). Default
    threshold 70th percentile."""
    # Trend leg (same as filter_ema_slope)
    if signal == 1 and f["bar_trend"][i] != 1:
        return 0
    if signal == -1 and f["bar_trend"][i] != -1:
        return 0
    # Vol leg
    pct = f["atr_pctrank"][i]
    if np.isnan(pct):
        return 0
    if pct < params.get("vr_threshold", 70):
        return 0
    return signal


def filter_ema_slope_vol_low(f, i, signal, params):
    """Stacked filter: ema_slope AND atr_pctrank <= vr_threshold.
    Mirror of filter_ema_slope_vol_high — restricts to low-vol regimes (default
    30th percentile). Useful for candidates whose edge concentrates in calm
    periods rather than expansion."""
    if signal == 1 and f["bar_trend"][i] != 1:
        return 0
    if signal == -1 and f["bar_trend"][i] != -1:
        return 0
    pct = f["atr_pctrank"][i]
    if np.isnan(pct):
        return 0
    if pct > params.get("vr_threshold", 30):
        return 0
    return signal


def filter_hurst_stable_mr(f, i, signal, params):
    """Hurst-stability filter for mean-reverting candidates (added 2026-06-03).

    Pass the signal only when the Hurst proxy is below `hurst_threshold_high`
    (default 0.45), indicating mean-reverting behavior. Optionally requires
    the prior window's hurst was ALSO < threshold ("stable MR regime", per
    harvest note 2026-06-03_11). Defaults are conservative.
    """
    h = f["hurst"][i]
    if np.isnan(h):
        return 0
    threshold_high = params.get("hurst_threshold_high", 0.45)
    if h >= threshold_high:
        return 0
    # Optional stability check: require prior window also MR
    if params.get("hurst_require_stable", False):
        # Look back 128 bars (half the rolling window) — that's the prior estimate cycle
        i_prev = max(i - 128, 0)
        h_prev = f["hurst"][i_prev]
        if np.isnan(h_prev) or h_prev >= threshold_high:
            return 0
    return signal


def filter_hurst_stable_trend(f, i, signal, params):
    """Hurst-stability filter for trend-following candidates.

    Pass only when Hurst proxy > `hurst_threshold_low` (default 0.55),
    indicating persistent/trending behavior. Mirror of MR gate.
    """
    h = f["hurst"][i]
    if np.isnan(h):
        return 0
    threshold_low = params.get("hurst_threshold_low", 0.55)
    if h <= threshold_low:
        return 0
    return signal


def filter_session_afternoon(f, i, signal, params):
    """Afternoon session only (12:00-14:45)."""
    if f["hours"][i] < 12:
        return 0
    return signal


def filter_session_close(f, i, signal, params):
    """Close-window session only (last ~75min of regular session: 14:30-15:45 ET).
    Operator gap-fill 2026-06-04 — close-momentum candidates."""
    h = f["hours"][i]
    if h < 14:
        return 0
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# PART 5: GENERIC SIGNAL GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

def entry_opening_drive_exhaustion(f, i, state, params):
    """Opening drive exhaustion: trade reversals of overextended opening drives.

    Mechanism (workhorse, mean-reversion):
      - Measure opening drive as displacement from session open to current
        intraday extreme: drive_strength = (extreme - open_of_day) / atr
      - Exhaustion when drive_strength exceeds threshold (default 2.0 ATR)
        AND price has stalled (no new extreme in last N bars)
      - Entry: REVERSE direction (mean-reversion to session VWAP / open)

    Different from orb_failure_reversal: that primitive looks at ORB-range
    BREAKOUT failure; this looks at MAGNITUDE-based exhaustion.

    Built 2026-06-12 per operator NEEDS_PRIMITIVE #4 (daily workhorse queue).
    """
    if not f["or_complete"][i]:
        return 0, 0, 0
    if np.isnan(f["atr"][i]) or f["atr"][i] <= 0:
        return 0, 0, 0

    cur_date = state.get("current_date")
    if state.get("drive_date_marker") != cur_date:
        state["drive_date_marker"] = cur_date
        state["session_open"] = f["open"][i]
        state["session_high"] = f["high"][i]
        state["session_low"] = f["low"][i]
        state["bars_since_new_high"] = 0
        state["bars_since_new_low"] = 0
        state["up_exhaustion_armed"] = False
        state["dn_exhaustion_armed"] = False

    if f["high"][i] > state["session_high"]:
        state["session_high"] = f["high"][i]
        state["bars_since_new_high"] = 0
    else:
        state["bars_since_new_high"] += 1

    if f["low"][i] < state["session_low"]:
        state["session_low"] = f["low"][i]
        state["bars_since_new_low"] = 0
    else:
        state["bars_since_new_low"] += 1

    atr_i = f["atr"][i]
    exhaustion_atr = params.get("exhaustion_atr_mult", 2.0)
    stall_bars = params.get("stall_bars", 3)

    up_drive = (state["session_high"] - state["session_open"]) / atr_i
    dn_drive = (state["session_open"] - state["session_low"]) / atr_i

    # Arm exhaustion when drive exceeds threshold AND has stalled
    if (up_drive >= exhaustion_atr
            and state["bars_since_new_high"] >= stall_bars):
        state["up_exhaustion_armed"] = True
    if (dn_drive >= exhaustion_atr
            and state["bars_since_new_low"] >= stall_bars):
        state["dn_exhaustion_armed"] = True

    close_i = f["close"][i]
    close_prev = f["close"][i - 1] if i > 0 else close_i

    # SHORT: upside exhaustion + reversal confirmation
    if (state["up_exhaustion_armed"]
            and close_i < close_prev
            and not state["short_traded_today"]):
        stop = state["session_high"] + atr_i * params.get("stop_mult", 0.5)
        target = close_i - atr_i * params.get("target_mult", 1.5)
        return -1, stop, target

    # LONG: downside exhaustion + reversal confirmation
    if (state["dn_exhaustion_armed"]
            and close_i > close_prev
            and not state["long_traded_today"]):
        stop = state["session_low"] - atr_i * params.get("stop_mult", 0.5)
        target = close_i + atr_i * params.get("target_mult", 1.5)
        return 1, stop, target

    return 0, 0, 0


def entry_vwap_reclaim(f, i, state, params):
    """VWAP reclaim / rejection: trade crosses of session VWAP.

    Mechanism (workhorse):
      - LONG when prev_close was below vwap AND current close crosses above
        vwap (price reclaiming VWAP, momentum shifting up).
      - SHORT when prev_close was above vwap AND current close crosses below
        vwap (VWAP rejected from above, momentum shifting down).

    Different from entry_vwap_continuation which trades pullbacks NEAR VWAP
    in the EMA-trend direction. This trades the CROSS itself.

    Built 2026-06-12 per operator NEEDS_PRIMITIVE #3 (daily workhorse queue).
    """
    if i == 0:
        return 0, 0, 0
    vwap_i = f["vwap"][i]
    vwap_prev = f["vwap"][i - 1]
    if np.isnan(vwap_i) or np.isnan(vwap_prev):
        return 0, 0, 0
    if np.isnan(f["atr"][i]) or f["atr"][i] <= 0:
        return 0, 0, 0
    close_i = f["close"][i]
    close_prev = f["close"][i - 1]
    atr_i = f["atr"][i]

    # Distance from VWAP at the cross — require meaningful displacement before
    # the cross to filter noise
    dist_prev = abs(close_prev - vwap_prev) / atr_i
    min_displacement = params.get("min_vwap_displacement_atr", 0.20)

    # LONG: reclaim from below
    if (close_prev < vwap_prev and close_i > vwap_i
            and dist_prev >= min_displacement
            and not state["long_traded_today"]):
        stop = close_i - atr_i * params.get("stop_mult", 1.0)
        target = close_i + atr_i * params.get("target_mult", 2.0)
        return 1, stop, target

    # SHORT: rejection from above
    if (close_prev > vwap_prev and close_i < vwap_i
            and dist_prev >= min_displacement
            and not state["short_traded_today"]):
        stop = close_i + atr_i * params.get("stop_mult", 1.0)
        target = close_i - atr_i * params.get("target_mult", 2.0)
        return -1, stop, target

    return 0, 0, 0


def entry_first_impulse_pullback(f, i, state, params):
    """First-impulse pullback continuation: trade pullbacks in direction of
    the opening impulse (post-ORB directional move).

    Mechanism (workhorse):
      - After ORB period (9:30-10:00 ET) completes, track running high/low.
      - Establish "impulse direction" once one side dominates by >= 1.5x ATR.
      - Look for pullback retracement to 50% of impulse range.
      - Enter in impulse direction when pullback level reached AND close starts
        reversing back toward impulse extreme.

    Built 2026-06-12 per operator NEEDS_PRIMITIVE #6 (daily workhorse queue).
    """
    if not f["or_complete"][i]:
        return 0, 0, 0
    or_h = f["or_high"][i]
    or_l = f["or_low"][i]
    if np.isnan(or_h) or np.isnan(or_l):
        return 0, 0, 0
    if np.isnan(f["atr"][i]) or f["atr"][i] <= 0:
        return 0, 0, 0

    # Per-day state tracking (engine only resets long/short_traded_today)
    cur_date = state.get("current_date")
    if state.get("impulse_date_marker") != cur_date:
        state["impulse_date_marker"] = cur_date
        state["impulse_high"] = f["high"][i]
        state["impulse_low"] = f["low"][i]
        state["impulse_anchor"] = (or_h + or_l) / 2.0
        state["impulse_direction"] = 0
        state["pullback_low_seen"] = float("inf")
        state["pullback_high_seen"] = float("-inf")

    # Update running impulse extremes
    if f["high"][i] > state["impulse_high"]:
        state["impulse_high"] = f["high"][i]
    if f["low"][i] < state["impulse_low"]:
        state["impulse_low"] = f["low"][i]

    up_strength = state["impulse_high"] - state["impulse_anchor"]
    dn_strength = state["impulse_anchor"] - state["impulse_low"]
    atr_i = f["atr"][i]

    # Establish impulse direction (only once per day, when one side dominates)
    if state["impulse_direction"] == 0:
        if up_strength >= atr_i * params.get("impulse_atr_mult", 1.0) and up_strength > dn_strength * 1.3:
            state["impulse_direction"] = 1
        elif dn_strength >= atr_i * params.get("impulse_atr_mult", 1.0) and dn_strength > up_strength * 1.3:
            state["impulse_direction"] = -1

    if state["impulse_direction"] == 0:
        return 0, 0, 0

    close_i = f["close"][i]
    close_prev = f["close"][i - 1] if i > 0 else close_i

    if state["impulse_direction"] == 1:
        # UP impulse: wait for pullback to 50% retracement, then bounce
        pullback_50 = state["impulse_high"] - 0.5 * up_strength
        if close_i < state["pullback_low_seen"]:
            state["pullback_low_seen"] = close_i
        # Trigger LONG: pullback reached 50%, current close > prev close (bounce starts)
        if (state["pullback_low_seen"] <= pullback_50
                and close_i > close_prev
                and not state["long_traded_today"]):
            stop = state["pullback_low_seen"] - atr_i * params.get("stop_mult", 0.5)
            target = state["impulse_high"] + up_strength * params.get("target_mult", 0.5)
            return 1, stop, target
    elif state["impulse_direction"] == -1:
        # DOWN impulse
        pullback_50 = state["impulse_low"] + 0.5 * dn_strength
        if close_i > state["pullback_high_seen"]:
            state["pullback_high_seen"] = close_i
        # Trigger SHORT: pullback reached 50%, current close < prev close (rejection)
        if (state["pullback_high_seen"] >= pullback_50
                and close_i < close_prev
                and not state["short_traded_today"]):
            stop = state["pullback_high_seen"] + atr_i * params.get("stop_mult", 0.5)
            target = state["impulse_low"] - dn_strength * params.get("target_mult", 0.5)
            return -1, stop, target

    return 0, 0, 0


def entry_orb_failure_reversal(f, i, state, params):
    """ORB failure reversal: trades the FAILED breakout, not the breakout itself.

    Mean-reversion mechanism. After ORB (9:30-10:00 ET) completes:
      - Track whether close has broken above or_high (upside breakout) or
        below or_low (downside breakout) at any bar today.
      - If a breakout occurred and the NEXT bar's close reverses back inside
        the ORB range, trigger an entry in the REVERSE direction.

    Built 2026-06-12 per operator NEEDS_PRIMITIVE #7 (daily workhorse queue).
    """
    if not f["or_complete"][i]:
        return 0, 0, 0
    or_h = f["or_high"][i]
    or_l = f["or_low"][i]
    if np.isnan(or_h) or np.isnan(or_l):
        return 0, 0, 0

    # Track per-day breakout state ourselves (engine only resets long/short_traded_today)
    cur_date = state.get("current_date")
    if state.get("orb_fail_date_marker") != cur_date:
        state["orb_fail_date_marker"] = cur_date
        state["orb_upside_broken"] = False
        state["orb_downside_broken"] = False

    close_i = f["close"][i]
    close_prev = f["close"][i - 1] if i > 0 else close_i

    # Detect breakouts (cumulative within day)
    if close_i > or_h or close_prev > or_h:
        state["orb_upside_broken"] = True
    if close_i < or_l or close_prev < or_l:
        state["orb_downside_broken"] = True

    # Detect FAILURE = reversal back into ORB range from outside
    # SHORT entry: upside breakout occurred, prev_close above or_h, current close back below or_h
    if (state["orb_upside_broken"] and close_prev > or_h and close_i < or_h
            and not state["short_traded_today"]):
        stop = or_h + f["atr"][i] * params.get("stop_mult", 1.0)
        target = or_l - f["atr"][i] * params.get("target_mult", 1.0)
        return -1, stop, target
    # LONG entry: downside breakout occurred, prev_close below or_l, current close back above or_l
    if (state["orb_downside_broken"] and close_prev < or_l and close_i > or_l
            and not state["long_traded_today"]):
        stop = or_l - f["atr"][i] * params.get("stop_mult", 1.0)
        target = or_h + f["atr"][i] * params.get("target_mult", 1.0)
        return 1, stop, target

    return 0, 0, 0


ENTRY_MAP = {
    "pb_pullback": entry_pb_pullback,
    "orb_breakout": entry_orb_breakout,
    "vwap_continuation": entry_vwap_continuation,
    "donchian_breakout": entry_donchian_breakout,
    "bb_reversion": entry_bb_reversion,
    "vol_expansion": entry_vol_expansion,
    "prior_day_break": entry_prior_day_break,
    "prior_day_fade": entry_prior_day_fade,
    "range_compression_break": entry_range_compression_break,
    "volatility_regime_compound": entry_volatility_regime_compound,
    "bb_keltner_squeeze": entry_bb_keltner_squeeze,
    "gap_fill_trigger": entry_gap_fill_trigger,
    "stop_run_reversal": entry_stop_run_reversal,
    "abnormal_range_followup": entry_abnormal_range_followup,
    "orb_failure_reversal": entry_orb_failure_reversal,
    "first_impulse_pullback": entry_first_impulse_pullback,
    "vwap_reclaim": entry_vwap_reclaim,
    "opening_drive_exhaustion": entry_opening_drive_exhaustion,
}

EXIT_MAP = {
    "atr_trail": exit_atr_trail,
    "profit_ladder": exit_profit_ladder,
    "fixed_ratio": exit_fixed_ratio,
    "midline_target": exit_midline_target,
    "chandelier": exit_chandelier,
    "time_stop": exit_time_stop,
}

FILTER_MAP = {
    "none": filter_none,
    "ema_slope": filter_ema_slope,
    "vwap_slope": filter_vwap_slope,
    "bandwidth_squeeze": filter_bandwidth_squeeze,
    "session_morning": filter_session_morning,
    "session_afternoon": filter_session_afternoon,
    # Vol-regime primitives (added 2026-06-02 per concentration-mutation Plan B)
    "vol_regime": filter_vol_regime,
    "ema_slope_vol_high": filter_ema_slope_vol_high,
    "ema_slope_vol_low": filter_ema_slope_vol_low,
    # Hurst-stability primitives (added 2026-06-03 per VALUE/MR unlock)
    "hurst_stable_mr": filter_hurst_stable_mr,
    "hurst_stable_trend": filter_hurst_stable_trend,
    # Session-close window (added 2026-06-04 per Core Daily Hunt gap)
    "session_close": filter_session_close,
}


class UnknownFilterError(ValueError):
    """Raised when filter_name references a primitive not in FILTER_MAP.
    Fail-closed per FQL Evidence Law — see CLAUDE.md."""


def _resolve_filter(filter_name):
    """Resolve filter_name (str or list) into a single callable.

    Single string: behaves identically to pre-2026-06-03 — returns the function
    from FILTER_MAP.

    List/tuple: returns an AND-combined composite. The composite calls each
    member filter in declared order and short-circuits when any returns 0,
    matching the per-bar gate semantics every existing filter uses. The
    composite signature matches the single-filter signature (f, i, signal, params)
    so callers don't change.

    Fail-closed: any unknown filter name raises UnknownFilterError before any
    signal generation begins (no silent skip).
    """
    if isinstance(filter_name, (list, tuple)):
        names = list(filter_name)
        if not names:
            raise UnknownFilterError("filter_name is an empty list; specify at least one filter or 'none'")
        unknown = [n for n in names if n not in FILTER_MAP]
        if unknown:
            raise UnknownFilterError(f"unknown filter(s): {unknown}; registered: {sorted(FILTER_MAP)}")
        funcs = [FILTER_MAP[n] for n in names]

        def composite(f, i, signal, params):
            for fn in funcs:
                signal = fn(f, i, signal, params)
                if signal == 0:
                    return 0
            return signal
        composite.__name__ = "filter_stack[" + "+".join(names) + "]"
        composite._stack_names = names
        return composite
    # Single string
    if filter_name not in FILTER_MAP:
        raise UnknownFilterError(f"unknown filter {filter_name!r}; registered: {sorted(FILTER_MAP)}")
    return FILTER_MAP[filter_name]


def generate_crossbred_signals(df, entry_name, exit_name, filter_name, params=None):
    """Generate signals from a crossbred strategy (entry + exit + filter[s]).

    `filter_name` accepts either a single registered filter name (str) or an
    ordered list of registered filter names (AND-combined). Unknown filter
    names raise UnknownFilterError before any signal generation runs.
    """
    df = df.copy()
    params = params or {}
    f = compute_features(df)
    n = f["n"]

    if entry_name not in ENTRY_MAP:
        raise UnknownFilterError(f"unknown entry {entry_name!r}; registered: {sorted(ENTRY_MAP)}")
    if exit_name not in EXIT_MAP:
        raise UnknownFilterError(f"unknown exit {exit_name!r}; registered: {sorted(EXIT_MAP)}")
    entry_fn = ENTRY_MAP[entry_name]
    exit_fn = EXIT_MAP[exit_name]
    filter_fn = _resolve_filter(filter_name)

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    state = {
        "position": 0, "entry_price": 0.0, "initial_risk": 0.0,
        "trailing_stop": 0.0, "target_price": 0.0,
        "highest": 0.0, "lowest": 0.0, "bars_in_trade": 0,
        "long_traded_today": False, "short_traded_today": False,
        "current_date": None,
    }

    for i in range(1, n):
        bar_date = f["dates"][i]

        # Day reset
        if bar_date != state["current_date"]:
            if state["position"] != 0:
                exit_sigs[i] = 1 if state["position"] == 1 else -1
                state["position"] = 0
            state["current_date"] = bar_date
            state["long_traded_today"] = False
            state["short_traded_today"] = False

        if not f["in_session"][i]:
            continue
        if np.isnan(f["atr"][i]) or f["atr"][i] == 0:
            continue

        # Pre-close flatten
        if state["position"] != 0 and f["flatten_time"][i]:
            exit_sigs[i] = 1 if state["position"] == 1 else -1
            state["position"] = 0
            continue

        # Exits
        if state["position"] != 0:
            state["bars_in_trade"] += 1
            exit_sig = exit_fn(f, i, state, params)
            if exit_sig != 0:
                exit_sigs[i] = exit_sig
                state["position"] = 0
                continue

        # Entries
        if state["position"] == 0 and f["entry_ok"][i]:
            signal, stop, target = entry_fn(f, i, state, params)
            signal = filter_fn(f, i, signal, params)

            if signal != 0:
                signals_arr[i] = signal
                stop_arr[i] = stop
                target_arr[i] = target
                state["position"] = signal
                state["entry_price"] = f["close"][i]
                state["initial_risk"] = abs(f["close"][i] - stop)
                state["trailing_stop"] = stop
                state["target_price"] = target
                state["highest"] = f["high"][i]
                state["lowest"] = f["low"][i]
                state["bars_in_trade"] = 0
                if signal == 1:
                    state["long_traded_today"] = True
                else:
                    state["short_traded_today"] = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    return df


# ═══════════════════════════════════════════════════════════════════════════
# PART 6: RECIPE DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════

RECIPES = [
    # ── Targeting cleaner breakouts ──────────────────────────────────
    {
        "id": 1, "name": "ORB + EMA trend + profit ladder",
        "target_gap": "trend_continuation",
        "entry": "orb_breakout", "exit": "profit_ladder", "filter": "ema_slope",
        "params": {"stop_mult": 0.5, "target_mult": 4.0, "trail_mult": 2.5},
    },
    {
        "id": 2, "name": "ORB + VWAP slope + ATR trail",
        "target_gap": "breakout",
        "entry": "orb_breakout", "exit": "atr_trail", "filter": "vwap_slope",
        "params": {"stop_mult": 0.5, "target_mult": 3.0, "trail_mult": 2.0},
    },
    {
        "id": 3, "name": "ORB + squeeze filter + chandelier",
        "target_gap": "volatility_compression",
        "entry": "orb_breakout", "exit": "chandelier", "filter": "bandwidth_squeeze",
        "params": {"stop_mult": 0.5, "target_mult": 3.0, "chandelier_mult": 3.0, "bw_threshold": 40},
    },

    # ── Targeting trend improvements ─────────────────────────────────
    {
        "id": 4, "name": "Donchian + EMA slope + profit ladder",
        "target_gap": "trend_follower",
        "entry": "donchian_breakout", "exit": "profit_ladder", "filter": "ema_slope",
        "params": {"stop_mult": 2.5, "target_mult": 5.0, "trail_mult": 3.0},
    },
    {
        "id": 5, "name": "Donchian + VWAP slope + chandelier",
        "target_gap": "trend_follower",
        "entry": "donchian_breakout", "exit": "chandelier", "filter": "vwap_slope",
        "params": {"stop_mult": 2.5, "target_mult": 4.0, "chandelier_mult": 3.5},
    },
    {
        "id": 6, "name": "VWAP cont + EMA slope + profit ladder",
        "target_gap": "trend_continuation",
        "entry": "vwap_continuation", "exit": "profit_ladder", "filter": "ema_slope",
        "params": {"stop_mult": 2.0, "target_mult": 3.5, "trail_mult": 2.5, "vwap_proximity": 0.5},
    },

    # ── Targeting mean reversion ─────────────────────────────────────
    {
        "id": 7, "name": "BB reversion + EMA slope + midline (BB)",
        "target_gap": "mean_reversion",
        "entry": "bb_reversion", "exit": "midline_target", "filter": "ema_slope",
        "params": {"stop_mult": 1.5, "trail_mult": 2.0, "midline_type": "bb", "min_hold": 3},
    },
    {
        "id": 8, "name": "BB reversion + VWAP slope + midline (VWAP)",
        "target_gap": "mean_reversion",
        "entry": "bb_reversion", "exit": "midline_target", "filter": "vwap_slope",
        "params": {"stop_mult": 1.5, "trail_mult": 2.0, "midline_type": "vwap", "min_hold": 3},
    },
    {
        "id": 9, "name": "BB reversion + squeeze + ATR trail",
        "target_gap": "mean_reversion",
        "entry": "bb_reversion", "exit": "atr_trail", "filter": "bandwidth_squeeze",
        "params": {"stop_mult": 1.5, "trail_mult": 2.0, "bw_threshold": 50},
    },

    # ── Targeting session structure ──────────────────────────────────
    {
        "id": 10, "name": "ORB + morning session + ATR trail",
        "target_gap": "session_structure",
        "entry": "orb_breakout", "exit": "atr_trail", "filter": "session_morning",
        "params": {"stop_mult": 0.5, "target_mult": 3.0, "trail_mult": 2.0},
    },
    {
        "id": 11, "name": "BB reversion + morning + midline",
        "target_gap": "session_structure",
        "entry": "bb_reversion", "exit": "midline_target", "filter": "session_morning",
        "params": {"stop_mult": 1.5, "trail_mult": 2.0, "midline_type": "bb", "min_hold": 3},
    },
    {
        "id": 12, "name": "VWAP cont + afternoon + profit ladder",
        "target_gap": "session_structure",
        "entry": "vwap_continuation", "exit": "profit_ladder", "filter": "session_afternoon",
        "params": {"stop_mult": 2.0, "target_mult": 3.0, "trail_mult": 2.5, "vwap_proximity": 0.5},
    },

    # ── Cross-family hybrids ─────────────────────────────────────────
    {
        "id": 13, "name": "PB pullback + VWAP slope + profit ladder",
        "target_gap": "pullback_scalper",
        "entry": "pb_pullback", "exit": "profit_ladder", "filter": "vwap_slope",
        "params": {"stop_mult": 1.5, "target_mult": 3.0, "trail_mult": 2.0, "pb_proximity": 0.5},
    },
    {
        "id": 14, "name": "PB pullback + squeeze + chandelier",
        "target_gap": "volatility_compression",
        "entry": "pb_pullback", "exit": "chandelier", "filter": "bandwidth_squeeze",
        "params": {"stop_mult": 1.5, "target_mult": 3.0, "chandelier_mult": 3.0, "pb_proximity": 0.5, "bw_threshold": 40},
    },
    {
        "id": 15, "name": "PB pullback + EMA slope + time stop",
        "target_gap": "pullback_scalper",
        "entry": "pb_pullback", "exit": "time_stop", "filter": "ema_slope",
        "params": {"stop_mult": 1.5, "target_mult": 2.5, "trail_mult": 2.0, "max_bars": 30, "pb_proximity": 0.5},
    },
    {
        "id": 16, "name": "VWAP cont + squeeze + midline (VWAP)",
        "target_gap": "volatility_compression",
        "entry": "vwap_continuation", "exit": "midline_target", "filter": "bandwidth_squeeze",
        "params": {"stop_mult": 2.0, "trail_mult": 2.0, "midline_type": "vwap", "min_hold": 3, "bw_threshold": 50, "vwap_proximity": 0.5},
    },
    {
        "id": 17, "name": "Donchian + squeeze + profit ladder",
        "target_gap": "volatility_compression",
        "entry": "donchian_breakout", "exit": "profit_ladder", "filter": "bandwidth_squeeze",
        "params": {"stop_mult": 2.5, "target_mult": 5.0, "trail_mult": 3.0, "bw_threshold": 30},
    },

    # ── Counter-trend / exotic ───────────────────────────────────────
    {
        "id": 18, "name": "BB reversion + no filter + profit ladder",
        "target_gap": "counter_trend",
        "entry": "bb_reversion", "exit": "profit_ladder", "filter": "none",
        "params": {"stop_mult": 1.5, "trail_mult": 2.0},
    },
    {
        "id": 19, "name": "BB reversion + morning + profit ladder",
        "target_gap": "counter_trend",
        "entry": "bb_reversion", "exit": "profit_ladder", "filter": "session_morning",
        "params": {"stop_mult": 1.5, "trail_mult": 2.0},
    },
    {
        "id": 20, "name": "ORB + EMA slope + time stop",
        "target_gap": "session_structure",
        "entry": "orb_breakout", "exit": "time_stop", "filter": "ema_slope",
        "params": {"stop_mult": 0.5, "target_mult": 3.0, "trail_mult": 2.0, "max_bars": 50},
    },
]


# ═══════════════════════════════════════════════════════════════════════════
# PART 7: BATCH RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def run_recipe(df, recipe, config, symbol, mode="both"):
    """Run a single crossbred recipe and return results."""
    signals_df = generate_crossbred_signals(
        df, recipe["entry"], recipe["exit"], recipe["filter"], recipe["params"]
    )
    result = run_backtest(
        df, signals_df, mode=mode,
        point_value=config["point_value"], symbol=symbol,
    )
    trades_df = result["trades_df"]
    if trades_df.empty or len(trades_df) < 5:
        return None

    metrics = compute_extended_metrics(trades_df, result["equity_curve"], config["point_value"])
    return {
        "recipe": recipe,
        "metrics": metrics,
        "trades_df": trades_df,
    }


def main():
    parser = argparse.ArgumentParser(description="Strategy Crossbreeding Engine")
    parser.add_argument("--recipe", type=int, help="Run single recipe by ID")
    parser.add_argument("--asset", default=None, help="Single asset (default: all 3)")
    args = parser.parse_args()

    assets = [args.asset] if args.asset else ["MES", "MNQ", "MGC"]
    recipes = [r for r in RECIPES if r["id"] == args.recipe] if args.recipe else RECIPES
    modes = ["both", "long", "short"]

    print(f"\n{'='*78}")
    print(f"  STRATEGY CROSSBREEDING ENGINE — {len(recipes)} recipes × {len(assets)} assets")
    print(f"{'='*78}")

    all_results = []

    for recipe in recipes:
        best_result = None
        best_key = None

        for symbol in assets:
            data_path = PROCESSED_DIR / f"{symbol}_5m.csv"
            if not data_path.exists():
                continue
            config = ASSET_CONFIG[symbol]
            df = pd.read_csv(data_path)
            df["datetime"] = pd.to_datetime(df["datetime"])

            for mode in modes:
                res = run_recipe(df, recipe, config, symbol, mode)
                if res is None:
                    continue
                m = res["metrics"]
                key = f"{symbol}-{mode}"
                if m["trade_count"] >= 20 and m["profit_factor"] > 1.0:
                    if best_result is None or m["profit_factor"] > best_result["metrics"]["profit_factor"]:
                        best_result = res
                        best_key = key

        if best_result:
            m = best_result["metrics"]
            med_hold = m.get("median_trade_duration_bars", 0)
            all_results.append({
                "recipe_id": recipe["id"],
                "name": recipe["name"],
                "target_gap": recipe["target_gap"],
                "best_combo": best_key,
                "pf": m["profit_factor"],
                "sharpe": m["sharpe"],
                "trades": m["trade_count"],
                "pnl": m["total_pnl"],
                "maxdd": m["max_drawdown"],
                "wr": m["win_rate"],
                "med_hold": med_hold,
            })

    # ── Results Table ──────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  CROSSBREEDING RESULTS")
    print(f"{'='*78}")

    if not all_results:
        print("  No recipes produced qualified results (≥20 trades, PF > 1.0)")
        return

    print(f"  {'#':>2} {'Name':<38} {'Combo':<10} {'PF':>5} {'Sh':>5} "
          f"{'Tr':>4} {'PnL':>8} {'Hold':>5}")
    print(f"  {'-'*2} {'-'*38} {'-'*10} {'-'*5} {'-'*5} "
          f"{'-'*4} {'-'*8} {'-'*5}")

    for r in sorted(all_results, key=lambda x: x["pf"], reverse=True):
        print(f"  {r['recipe_id']:>2} {r['name']:<38} {r['best_combo']:<10} "
              f"{r['pf']:>5.2f} {r['sharpe']:>5.2f} "
              f"{r['trades']:>4} {'${:,.0f}'.format(r['pnl']):>8} "
              f"{r['med_hold']:>4.0f}b")

    # ── Quality gate ───────────────────────────────────────────────────
    promoted = [r for r in all_results if r["pf"] > 1.3 and r["sharpe"] > 1.5]

    print(f"\n  QUALITY GATE (PF > 1.3, Sharpe > 1.5):")
    if promoted:
        for r in sorted(promoted, key=lambda x: x["pf"], reverse=True):
            print(f"    PASS: #{r['recipe_id']} {r['name']} — PF={r['pf']:.2f}, "
                  f"Sharpe={r['sharpe']:.2f}, {r['trades']} trades [{r['target_gap']}]")
    else:
        print(f"    No recipes passed quality gate")

    # ── Save results ───────────────────────────────────────────────────
    output = {
        "total_recipes": len(recipes),
        "total_qualified": len(all_results),
        "total_promoted": len(promoted),
        "results": all_results,
        "promoted": promoted,
    }
    output_path = OUTPUT_DIR / "crossbreeding_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved to {output_path}")

    return all_results


if __name__ == "__main__":
    main()
