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

def compute_features(df: pd.DataFrame) -> dict:
    """Pre-compute all indicators any component might need."""
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

    # Donchian channels
    dc_high_20 = df["high"].rolling(20, min_periods=20).max().values
    dc_low_20 = df["low"].rolling(20, min_periods=20).min().values
    dc_high_30 = df["high"].rolling(30, min_periods=30).max().values
    dc_low_30 = df["low"].rolling(30, min_periods=30).min().values

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

    return {
        "close": close, "high": high, "low": low, "open": opn, "volume": volume,
        "dates": dates, "times": times, "hours": hours, "n": n,
        "atr": atr,
        "ema8": ema8, "ema13": ema13, "ema20": ema20, "ema21": ema21, "ema50": ema50,
        "bb_upper": bb_upper, "bb_lower": bb_lower, "bb_mid": bb_mid,
        "bw_pctrank": bw_pctrank, "rsi": rsi,
        "vwap": vwap,
        "dc_high_20": dc_high_20, "dc_low_20": dc_low_20,
        "dc_high_30": dc_high_30, "dc_low_30": dc_low_30,
        "bar_trend": bar_trend,
        "in_session": in_session, "entry_ok": entry_ok, "flatten_time": flatten_time,
        "or_high": or_high, "or_low": or_low, "or_complete": or_complete,
    }


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
    """Donchian channel breakout: new N-bar high/low."""
    ch_len = params.get("channel_len", 20)
    dc_h = f[f"dc_high_{ch_len}"][i] if f"dc_high_{ch_len}" in f else f["dc_high_20"][i]
    dc_l = f[f"dc_low_{ch_len}"][i] if f"dc_low_{ch_len}" in f else f["dc_low_20"][i]
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


def filter_session_afternoon(f, i, signal, params):
    """Afternoon session only (12:00-14:45)."""
    if f["hours"][i] < 12:
        return 0
    return signal


# ═══════════════════════════════════════════════════════════════════════════
# PART 5: GENERIC SIGNAL GENERATOR
# ═══════════════════════════════════════════════════════════════════════════

ENTRY_MAP = {
    "pb_pullback": entry_pb_pullback,
    "orb_breakout": entry_orb_breakout,
    "vwap_continuation": entry_vwap_continuation,
    "donchian_breakout": entry_donchian_breakout,
    "bb_reversion": entry_bb_reversion,
}

EXIT_MAP = {
    "atr_trail": exit_atr_trail,
    "profit_ladder": exit_profit_ladder,
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
}


def generate_crossbred_signals(df, entry_name, exit_name, filter_name, params=None):
    """Generate signals from a crossbred strategy (entry + exit + filter)."""
    df = df.copy()
    params = params or {}
    f = compute_features(df)
    n = f["n"]

    entry_fn = ENTRY_MAP[entry_name]
    exit_fn = EXIT_MAP[exit_name]
    filter_fn = FILTER_MAP[filter_name]

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
