"""Exit Evolution Engine — Donchian Trend Exit Variants.

Tests exit optimizations to reduce regime bleed while preserving trend-following edge.
Entry logic is frozen — uses the original strategy module's generate_signals() to
guarantee identical entries. Each exit variant applies different exit rules.

Variants:
  0: Baseline (ATR trail — control, exact reproduction of original strategy)
  1: Chandelier Exit (rolling N-bar high trail)
  2: Time Stop (exit if no progress after N bars)
  3: Trailing EMA (exit on sustained EMA cross in profit)
  4: Profit Ladder (ratcheting stop at R-milestones)
  5: Vol-Contraction Time Stop (exit when ATR contracts + no progress)

Usage:
    python3 research/exit_evolution.py                       # all variants
    python3 research/exit_evolution.py --variant chandelier   # single variant
    python3 research/exit_evolution.py --no-portfolio         # skip portfolio impact
"""

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"
STARTING_CAPITAL = 50_000.0

# Constants from original strategy (for exit variants that need them)
ATR_STOP_MULT = 2.5
FLATTEN_TIME = "15:30"
SESSION_START = "09:30"
SESSION_END = "15:45"


# ═══════════════════════════════════════════════════════════════════════════════
# Part 1: Shared Entry Logic (uses original strategy module)
# ═══════════════════════════════════════════════════════════════════════════════

def load_donchian_module():
    """Load the original donchian_trend strategy module."""
    path = ROOT / "strategies" / "donchian_trend" / "strategy.py"
    spec = importlib.util.spec_from_file_location("donchian_trend", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def donchian_entries(df: pd.DataFrame) -> dict:
    """Run original strategy and extract entry metadata.

    Uses the original generate_signals() to guarantee identical entries.
    Returns dict with shared data for all exit variants.
    """
    mod = load_donchian_module()
    mod.TICK_SIZE = 0.25  # MNQ

    # Run original strategy to get the authoritative signal array
    original_signals = mod.generate_signals(df.copy())

    # Extract entry bars from signal array
    sig_arr = original_signals["signal"].values
    stop_arr_orig = original_signals["stop_price"].values

    # Compute ATR matching the original strategy's formula exactly
    # (original uses low_channel in TR — line 82-83 of strategy.py)
    df_c = df.copy()
    low_channel = df_c["low"].rolling(window=30, min_periods=30).min().shift(1)
    prev_close = df_c["close"].shift(1)
    tr = pd.concat([
        df_c["high"] - df_c["low"],
        (df_c["high"] - prev_close).abs(),
        (low_channel - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean()
    atr_arr = atr.values

    dt = pd.to_datetime(df_c["datetime"])
    time_str = dt.dt.strftime("%H:%M")
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)

    entries = []
    for i in range(len(sig_arr)):
        if sig_arr[i] != 0:
            direction = int(sig_arr[i])
            entry_price = df_c["close"].iloc[i]
            bar_atr = atr_arr[i]
            initial_stop = stop_arr_orig[i]
            if np.isnan(initial_stop):
                # Compute from ATR if missing
                if direction == 1:
                    initial_stop = entry_price - bar_atr * ATR_STOP_MULT
                else:
                    initial_stop = entry_price + bar_atr * ATR_STOP_MULT
            entries.append({
                "bar_idx": i,
                "direction": direction,
                "entry_price": entry_price,
                "atr_at_entry": bar_atr,
                "initial_stop": initial_stop,
            })

    return {
        "entries": entries,
        "original_signals": original_signals,
        "atr": atr_arr,
        "close": df_c["close"].values,
        "high": df_c["high"].values,
        "low": df_c["low"].values,
        "time": time_str.values,
        "dates": dt.dt.date.values,
        "in_session": in_session.values,
        "n": len(df_c),
        "df": df_c,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Part 2: Exit Variant Functions
# ═══════════════════════════════════════════════════════════════════════════════

def apply_baseline(data: dict, params: dict = None) -> pd.DataFrame:
    """Variant 0: Baseline — returns the original strategy's signals exactly."""
    # The original generate_signals() already has perfect entry+exit logic.
    # Return it directly to guarantee exact reproduction.
    return data["original_signals"][["datetime", "open", "high", "low", "close",
                                      "signal", "exit_signal", "stop_price",
                                      "target_price"]].copy()


def apply_chandelier(data: dict, params: dict = None) -> pd.DataFrame:
    """Variant 1: Chandelier Exit — trail from rolling N-bar high/low."""
    p = {"lookback": 10, "atr_mult": 3.0, **(params or {})}
    lookback = p["lookback"]
    atr_mult = p["atr_mult"]

    n = data["n"]
    entries = data["entries"]
    close = data["close"]
    high = data["high"]
    low = data["low"]
    atr = data["atr"]
    time_arr = data["time"]
    dates = data["dates"]
    in_session = data["in_session"]

    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    entry_map = {e["bar_idx"]: e for e in entries}

    position = 0
    trailing_stop = 0.0
    entry_bar_idx = 0
    current_date = None

    for i in range(n):
        bar_date = dates[i]
        if bar_date != current_date:
            if position != 0:
                exit_signals[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date

        if not in_session[i]:
            continue

        if position != 0 and time_arr[i] >= FLATTEN_TIME:
            exit_signals[i] = 1 if position == 1 else -1
            position = 0
            continue

        if position == 1:
            lb_start = max(entry_bar_idx, i - lookback + 1)
            rolling_high = np.max(high[lb_start:i + 1])
            new_trail = rolling_high - atr[i] * atr_mult
            if new_trail > trailing_stop:
                trailing_stop = new_trail
            if low[i] <= trailing_stop:
                exit_signals[i] = 1
                position = 0

        elif position == -1:
            lb_start = max(entry_bar_idx, i - lookback + 1)
            rolling_low = np.min(low[lb_start:i + 1])
            new_trail = rolling_low + atr[i] * atr_mult
            if new_trail < trailing_stop:
                trailing_stop = new_trail
            if high[i] >= trailing_stop:
                exit_signals[i] = -1
                position = 0

        if position == 0 and i in entry_map:
            e = entry_map[i]
            signals[i] = e["direction"]
            stop_arr[i] = e["initial_stop"]
            position = e["direction"]
            trailing_stop = e["initial_stop"]
            entry_bar_idx = i

    df_out = data["df"][["datetime", "open", "high", "low", "close"]].copy()
    df_out["signal"] = signals
    df_out["exit_signal"] = exit_signals
    df_out["stop_price"] = stop_arr
    df_out["target_price"] = target_arr
    return df_out


def apply_time_stop(data: dict, params: dict = None) -> pd.DataFrame:
    """Variant 2: Time Stop — exit if trade hasn't progressed after N bars."""
    p = {"max_bars": 20, "profit_threshold_r": 0.5, "atr_trail_mult": 3.0,
         **(params or {})}
    max_bars = p["max_bars"]
    threshold_r = p["profit_threshold_r"]
    trail_mult = p["atr_trail_mult"]

    n = data["n"]
    entries = data["entries"]
    close = data["close"]
    high = data["high"]
    low = data["low"]
    atr = data["atr"]
    time_arr = data["time"]
    dates = data["dates"]
    in_session = data["in_session"]

    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    entry_map = {e["bar_idx"]: e for e in entries}

    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    highest_since = 0.0
    lowest_since = 0.0
    entry_bar_idx = 0
    initial_risk = 0.0
    current_date = None

    for i in range(n):
        bar_date = dates[i]
        if bar_date != current_date:
            if position != 0:
                exit_signals[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date

        if not in_session[i]:
            continue

        if position != 0 and time_arr[i] >= FLATTEN_TIME:
            exit_signals[i] = 1 if position == 1 else -1
            position = 0
            continue

        if position == 1:
            bars_held = i - entry_bar_idx
            unrealized = close[i] - entry_price

            if bars_held >= max_bars and unrealized < threshold_r * initial_risk:
                exit_signals[i] = 1
                position = 0
                continue

            if high[i] > highest_since:
                highest_since = high[i]
                new_trail = highest_since - atr[i] * trail_mult
                if new_trail > trailing_stop:
                    trailing_stop = new_trail
            if low[i] <= trailing_stop:
                exit_signals[i] = 1
                position = 0

        elif position == -1:
            bars_held = i - entry_bar_idx
            unrealized = entry_price - close[i]

            if bars_held >= max_bars and unrealized < threshold_r * initial_risk:
                exit_signals[i] = -1
                position = 0
                continue

            if low[i] < lowest_since:
                lowest_since = low[i]
                new_trail = lowest_since + atr[i] * trail_mult
                if new_trail < trailing_stop:
                    trailing_stop = new_trail
            if high[i] >= trailing_stop:
                exit_signals[i] = -1
                position = 0

        if position == 0 and i in entry_map:
            e = entry_map[i]
            signals[i] = e["direction"]
            stop_arr[i] = e["initial_stop"]
            position = e["direction"]
            entry_price = e["entry_price"]
            trailing_stop = e["initial_stop"]
            highest_since = high[i]
            lowest_since = low[i]
            entry_bar_idx = i
            initial_risk = e["atr_at_entry"] * ATR_STOP_MULT

    df_out = data["df"][["datetime", "open", "high", "low", "close"]].copy()
    df_out["signal"] = signals
    df_out["exit_signal"] = exit_signals
    df_out["stop_price"] = stop_arr
    df_out["target_price"] = target_arr
    return df_out


def apply_trailing_ema(data: dict, params: dict = None) -> pd.DataFrame:
    """Variant 3: Trailing EMA — exit on sustained EMA cross while in profit."""
    p = {"ema_period": 20, "min_hold_bars": 15, "consec_cross": 3,
         "atr_trail_mult": 3.0, **(params or {})}
    ema_period = p["ema_period"]
    min_hold = p["min_hold_bars"]
    consec_needed = p["consec_cross"]
    trail_mult = p["atr_trail_mult"]

    n = data["n"]
    entries = data["entries"]
    close = data["close"]
    high = data["high"]
    low = data["low"]
    atr = data["atr"]
    time_arr = data["time"]
    dates = data["dates"]
    in_session = data["in_session"]

    ema = pd.Series(close).ewm(span=ema_period, adjust=False).mean().values

    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    entry_map = {e["bar_idx"]: e for e in entries}

    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    highest_since = 0.0
    lowest_since = 0.0
    entry_bar_idx = 0
    consec_cross_count = 0
    current_date = None

    for i in range(n):
        bar_date = dates[i]
        if bar_date != current_date:
            if position != 0:
                exit_signals[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date

        if not in_session[i]:
            continue

        if position != 0 and time_arr[i] >= FLATTEN_TIME:
            exit_signals[i] = 1 if position == 1 else -1
            position = 0
            continue

        if position == 1:
            bars_held = i - entry_bar_idx
            unrealized = close[i] - entry_price
            in_profit = unrealized > 0

            if bars_held >= min_hold and in_profit:
                if close[i] < ema[i]:
                    consec_cross_count += 1
                else:
                    consec_cross_count = 0
                if consec_cross_count >= consec_needed:
                    exit_signals[i] = 1
                    position = 0
                    consec_cross_count = 0
                    continue
            else:
                consec_cross_count = 0

            if high[i] > highest_since:
                highest_since = high[i]
                new_trail = highest_since - atr[i] * trail_mult
                if new_trail > trailing_stop:
                    trailing_stop = new_trail
            if low[i] <= trailing_stop:
                exit_signals[i] = 1
                position = 0
                consec_cross_count = 0

        elif position == -1:
            bars_held = i - entry_bar_idx
            unrealized = entry_price - close[i]
            in_profit = unrealized > 0

            if bars_held >= min_hold and in_profit:
                if close[i] > ema[i]:
                    consec_cross_count += 1
                else:
                    consec_cross_count = 0
                if consec_cross_count >= consec_needed:
                    exit_signals[i] = -1
                    position = 0
                    consec_cross_count = 0
                    continue
            else:
                consec_cross_count = 0

            if low[i] < lowest_since:
                lowest_since = low[i]
                new_trail = lowest_since + atr[i] * trail_mult
                if new_trail < trailing_stop:
                    trailing_stop = new_trail
            if high[i] >= trailing_stop:
                exit_signals[i] = -1
                position = 0
                consec_cross_count = 0

        if position == 0 and i in entry_map:
            e = entry_map[i]
            signals[i] = e["direction"]
            stop_arr[i] = e["initial_stop"]
            position = e["direction"]
            entry_price = e["entry_price"]
            trailing_stop = e["initial_stop"]
            highest_since = high[i]
            lowest_since = low[i]
            entry_bar_idx = i
            consec_cross_count = 0

    df_out = data["df"][["datetime", "open", "high", "low", "close"]].copy()
    df_out["signal"] = signals
    df_out["exit_signal"] = exit_signals
    df_out["stop_price"] = stop_arr
    df_out["target_price"] = target_arr
    return df_out


def apply_profit_ladder(data: dict, params: dict = None) -> pd.DataFrame:
    """Variant 4: Profit Ladder — ratcheting stop at R-milestones."""
    p = {
        "rungs": [(1.0, 0.25), (2.0, 1.0), (3.0, 2.0)],
        "atr_trail_mult": 3.0,
        **(params or {}),
    }
    rungs = p["rungs"]
    trail_mult = p["atr_trail_mult"]

    n = data["n"]
    entries = data["entries"]
    close = data["close"]
    high = data["high"]
    low = data["low"]
    atr = data["atr"]
    time_arr = data["time"]
    dates = data["dates"]
    in_session = data["in_session"]

    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    entry_map = {e["bar_idx"]: e for e in entries}

    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    highest_since = 0.0
    lowest_since = 0.0
    initial_risk = 0.0
    current_rung = -1
    current_date = None

    for i in range(n):
        bar_date = dates[i]
        if bar_date != current_date:
            if position != 0:
                exit_signals[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date

        if not in_session[i]:
            continue

        if position != 0 and time_arr[i] >= FLATTEN_TIME:
            exit_signals[i] = 1 if position == 1 else -1
            position = 0
            continue

        if position == 1:
            unrealized = close[i] - entry_price
            unrealized_r = unrealized / initial_risk if initial_risk > 0 else 0

            for rung_idx, (trigger_r, lock_r) in enumerate(rungs):
                if rung_idx > current_rung and unrealized_r >= trigger_r:
                    locked_stop = entry_price + lock_r * initial_risk
                    if locked_stop > trailing_stop:
                        trailing_stop = locked_stop
                    current_rung = rung_idx

            if high[i] > highest_since:
                highest_since = high[i]
                new_trail = highest_since - atr[i] * trail_mult
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            if low[i] <= trailing_stop:
                exit_signals[i] = 1
                position = 0

        elif position == -1:
            unrealized = entry_price - close[i]
            unrealized_r = unrealized / initial_risk if initial_risk > 0 else 0

            for rung_idx, (trigger_r, lock_r) in enumerate(rungs):
                if rung_idx > current_rung and unrealized_r >= trigger_r:
                    locked_stop = entry_price - lock_r * initial_risk
                    if locked_stop < trailing_stop:
                        trailing_stop = locked_stop
                    current_rung = rung_idx

            if low[i] < lowest_since:
                lowest_since = low[i]
                new_trail = lowest_since + atr[i] * trail_mult
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            if high[i] >= trailing_stop:
                exit_signals[i] = -1
                position = 0

        if position == 0 and i in entry_map:
            e = entry_map[i]
            signals[i] = e["direction"]
            stop_arr[i] = e["initial_stop"]
            position = e["direction"]
            entry_price = e["entry_price"]
            trailing_stop = e["initial_stop"]
            highest_since = high[i]
            lowest_since = low[i]
            initial_risk = e["atr_at_entry"] * ATR_STOP_MULT
            current_rung = -1

    df_out = data["df"][["datetime", "open", "high", "low", "close"]].copy()
    df_out["signal"] = signals
    df_out["exit_signal"] = exit_signals
    df_out["stop_price"] = stop_arr
    df_out["target_price"] = target_arr
    return df_out


def apply_vol_contraction(data: dict, params: dict = None) -> pd.DataFrame:
    """Variant 5: Vol-Contraction Time Stop — exit when ATR contracts + no progress."""
    p = {"max_bars": 20, "profit_threshold_r": 0.5, "atr_trail_mult": 3.0,
         "atr_contraction_pct": 30, **(params or {})}
    max_bars = p["max_bars"]
    threshold_r = p["profit_threshold_r"]
    trail_mult = p["atr_trail_mult"]
    contraction_pct = p["atr_contraction_pct"]

    n = data["n"]
    entries = data["entries"]
    close = data["close"]
    high = data["high"]
    low = data["low"]
    atr = data["atr"]
    time_arr = data["time"]
    dates = data["dates"]
    in_session = data["in_session"]

    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    entry_map = {e["bar_idx"]: e for e in entries}

    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    highest_since = 0.0
    lowest_since = 0.0
    entry_bar_idx = 0
    initial_risk = 0.0
    atr_at_entry = 0.0
    current_date = None

    for i in range(n):
        bar_date = dates[i]
        if bar_date != current_date:
            if position != 0:
                exit_signals[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date

        if not in_session[i]:
            continue

        if position != 0 and time_arr[i] >= FLATTEN_TIME:
            exit_signals[i] = 1 if position == 1 else -1
            position = 0
            continue

        if position == 1:
            bars_held = i - entry_bar_idx
            unrealized = close[i] - entry_price

            if bars_held >= max_bars:
                atr_contracted = atr[i] < atr_at_entry * (1 - contraction_pct / 100)
                below_threshold = unrealized < threshold_r * initial_risk
                if atr_contracted and below_threshold:
                    exit_signals[i] = 1
                    position = 0
                    continue

            if high[i] > highest_since:
                highest_since = high[i]
                new_trail = highest_since - atr[i] * trail_mult
                if new_trail > trailing_stop:
                    trailing_stop = new_trail
            if low[i] <= trailing_stop:
                exit_signals[i] = 1
                position = 0

        elif position == -1:
            bars_held = i - entry_bar_idx
            unrealized = entry_price - close[i]

            if bars_held >= max_bars:
                atr_contracted = atr[i] < atr_at_entry * (1 - contraction_pct / 100)
                below_threshold = unrealized < threshold_r * initial_risk
                if atr_contracted and below_threshold:
                    exit_signals[i] = -1
                    position = 0
                    continue

            if low[i] < lowest_since:
                lowest_since = low[i]
                new_trail = lowest_since + atr[i] * trail_mult
                if new_trail < trailing_stop:
                    trailing_stop = new_trail
            if high[i] >= trailing_stop:
                exit_signals[i] = -1
                position = 0

        if position == 0 and i in entry_map:
            e = entry_map[i]
            signals[i] = e["direction"]
            stop_arr[i] = e["initial_stop"]
            position = e["direction"]
            entry_price = e["entry_price"]
            trailing_stop = e["initial_stop"]
            highest_since = high[i]
            lowest_since = low[i]
            entry_bar_idx = i
            initial_risk = e["atr_at_entry"] * ATR_STOP_MULT
            atr_at_entry = e["atr_at_entry"]

    df_out = data["df"][["datetime", "open", "high", "low", "close"]].copy()
    df_out["signal"] = signals
    df_out["exit_signal"] = exit_signals
    df_out["stop_price"] = stop_arr
    df_out["target_price"] = target_arr
    return df_out


# ═══════════════════════════════════════════════════════════════════════════════
# Variant Registry
# ═══════════════════════════════════════════════════════════════════════════════

VARIANTS = {
    "baseline": {"fn": apply_baseline, "label": "Baseline (ATR Trail)", "params": {}},
    "chandelier": {"fn": apply_chandelier, "label": "Chandelier Exit", "params": {}},
    "time_stop": {"fn": apply_time_stop, "label": "Time Stop", "params": {}},
    "trailing_ema": {"fn": apply_trailing_ema, "label": "Trailing EMA", "params": {}},
    "profit_ladder": {"fn": apply_profit_ladder, "label": "Profit Ladder", "params": {}},
    "vol_contraction": {"fn": apply_vol_contraction, "label": "Vol-Contract Time Stop", "params": {}},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Part 3: Evaluation Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def run_variant(variant_name: str, df: pd.DataFrame, entry_data: dict,
                regime_daily: pd.DataFrame) -> dict:
    """Run a single variant through backtest + regime analysis.

    Returns dict with raw and grinding results.
    """
    vdef = VARIANTS[variant_name]
    signals_df = vdef["fn"](entry_data, vdef["params"])

    asset = "MNQ"
    config = ASSET_CONFIG[asset]

    result = run_backtest(
        df, signals_df,
        mode="long",
        point_value=config["point_value"],
        symbol=asset,
    )
    trades = result["trades_df"]

    if trades.empty:
        return {"raw": None, "grinding": None}

    # Tag trades with regime
    trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
    rd = regime_daily.copy()
    rd["_date"] = pd.to_datetime(rd["_date"])
    rd["_date_date"] = rd["_date"].dt.date

    trades = trades.merge(
        rd[["_date_date", "vol_regime", "trend_regime", "rv_regime",
            "trend_persistence", "composite_regime"]],
        left_on="entry_date", right_on="_date_date", how="left",
    )
    trades["regime_cell"] = trades["composite_regime"] + "_" + trades["rv_regime"]

    out = {}

    # --- RAW (no filter) ---
    eq_raw = pd.Series(
        STARTING_CAPITAL + np.cumsum(np.concatenate([[0], trades["pnl"].values])),
        name="equity",
    )
    metrics_raw = compute_extended_metrics(trades, eq_raw, config["point_value"])
    metrics_raw["variant"] = variant_name

    cell_pnl = trades.groupby("regime_cell")["pnl"].agg(["sum", "count"]).rename(
        columns={"sum": "pnl", "count": "trades"})
    bleed_cells = cell_pnl[cell_pnl["pnl"] < 0]
    total_bleed = bleed_cells["pnl"].sum()
    bleed_count = int(bleed_cells["trades"].sum())
    worst_cell = bleed_cells["pnl"].idxmin() if len(bleed_cells) > 0 else "N/A"
    worst_cell_pnl = bleed_cells["pnl"].min() if len(bleed_cells) > 0 else 0

    daily_raw = _daily_pnl(trades)

    out["raw"] = {
        "metrics": metrics_raw,
        "trades": trades.copy(),
        "daily_pnl": daily_raw,
        "cell_pnl": cell_pnl,
        "total_bleed": total_bleed,
        "bleed_count": bleed_count,
        "worst_cell": worst_cell,
        "worst_cell_pnl": worst_cell_pnl,
    }

    # --- GRINDING filter ---
    grinding_trades = trades[trades["trend_persistence"] == "GRINDING"].copy()
    if grinding_trades.empty:
        out["grinding"] = None
    else:
        eq_grind = pd.Series(
            STARTING_CAPITAL + np.cumsum(
                np.concatenate([[0], grinding_trades["pnl"].values])),
            name="equity",
        )
        metrics_grind = compute_extended_metrics(
            grinding_trades, eq_grind, config["point_value"])
        metrics_grind["variant"] = variant_name
        daily_grind = _daily_pnl(grinding_trades)

        out["grinding"] = {
            "metrics": metrics_grind,
            "trades": grinding_trades,
            "daily_pnl": daily_grind,
        }

    return out


def _daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


# ═══════════════════════════════════════════════════════════════════════════════
# Part 4: Portfolio Impact
# ═══════════════════════════════════════════════════════════════════════════════

def _load_strategy_module(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_portfolio_base_dailies() -> tuple:
    """Run PB, ORB, VWAP and return their daily PnL series (cached per run)."""
    strats = [
        {"name": "pb_trend", "asset": "MGC", "mode": "short", "label": "PB"},
        {"name": "orb_009", "asset": "MGC", "mode": "long", "label": "ORB"},
        {"name": "vwap_trend", "asset": "MNQ", "mode": "long", "label": "VWAP"},
    ]
    dailies = {}
    total_trades = {}
    for s in strats:
        config = ASSET_CONFIG[s["asset"]]
        df = pd.read_csv(PROCESSED_DIR / f"{s['asset']}_5m.csv")
        df["datetime"] = pd.to_datetime(df["datetime"])

        mod = _load_strategy_module(s["name"])
        mod.TICK_SIZE = config["tick_size"]
        signals = mod.generate_signals(df)

        result = run_backtest(
            df, signals, mode=s["mode"],
            point_value=config["point_value"], symbol=s["asset"],
        )
        dailies[s["label"]] = _daily_pnl(result["trades_df"])
        total_trades[s["label"]] = len(result["trades_df"])

    return dailies, total_trades


def portfolio_impact(variant_results: dict, base_dailies: dict,
                     base_trades: dict) -> dict:
    """Compute portfolio metrics swapping each variant's Donchian component."""
    impacts = {}
    for vname, vdata in variant_results.items():
        grind = vdata.get("grinding")
        if grind is None:
            impacts[vname] = None
            continue

        donch_daily = grind["daily_pnl"]
        all_daily = {**base_dailies, "DONCH": donch_daily}
        port_df = pd.DataFrame(all_daily).fillna(0)
        port_daily = port_df.sum(axis=1).sort_index()

        total_pnl = port_daily.sum()
        sharpe = (port_daily.mean() / port_daily.std() * np.sqrt(252)
                  if port_daily.std() > 0 else 0)
        equity = STARTING_CAPITAL + port_daily.cumsum()
        peak = equity.cummax()
        dd = peak - equity
        maxdd = dd.max()
        calmar = total_pnl / maxdd if maxdd > 0 else 0

        monthly = port_daily.resample("ME").sum()
        profitable = (monthly > 0).sum()
        total_months = len(monthly)

        corr = {}
        for label, daily in base_dailies.items():
            aligned = pd.DataFrame({"donch": donch_daily, label: daily}).fillna(0)
            if len(aligned) > 5:
                corr[label] = aligned["donch"].corr(aligned[label])

        trade_count = sum(base_trades.values()) + len(grind["trades"])

        impacts[vname] = {
            "total_pnl": total_pnl,
            "sharpe": round(sharpe, 2),
            "calmar": round(calmar, 2),
            "maxdd": round(maxdd, 2),
            "profitable_months": f"{profitable}/{total_months} ({profitable/total_months*100:.0f}%)" if total_months > 0 else "0/0",
            "trades": trade_count,
            "correlation": corr,
        }

    return impacts


# ═══════════════════════════════════════════════════════════════════════════════
# Part 5: Comparison Output
# ═══════════════════════════════════════════════════════════════════════════════

def print_results(variant_results: dict, portfolio_impacts: dict = None):
    """Print all 7 comparison tables."""
    variant_names = list(variant_results.keys())

    # ── Table 1: Core Metrics (Raw) ───────────────────────────────────────
    print(f"\n{'='*100}")
    print(f"  TABLE 1: CORE METRICS (RAW — ALL TRADES)")
    print(f"{'='*100}")

    headers = ["Variant", "Trades", "PF", "WR%", "Sharpe", "PnL", "MaxDD", "MedHold", "AvgHold"]
    print(f"\n  {headers[0]:<24}" + "".join(f"{h:>10}" for h in headers[1:]))
    print(f"  {'-'*24}" + f"{'-'*10}" * (len(headers) - 1))

    for vname in variant_names:
        raw = variant_results[vname].get("raw")
        if raw is None:
            print(f"  {VARIANTS[vname]['label']:<24}  {'— no trades —':>50}")
            continue
        m = raw["metrics"]
        med = m.get("median_trade_duration_bars", 0)
        avg = m.get("avg_trade_duration_bars", 0)
        print(f"  {VARIANTS[vname]['label']:<24}"
              f"{m['trade_count']:>10}"
              f"{m['profit_factor']:>10.2f}"
              f"{m['win_rate']*100:>9.1f}%"
              f"{m['sharpe']:>10.2f}"
              f"{'${:,.0f}'.format(m['total_pnl']):>10}"
              f"{'${:,.0f}'.format(m['max_drawdown']):>10}"
              f"{med:>9.0f}b"
              f"{avg:>9.0f}b")

    # ── Table 2: Core Metrics (GRINDING) ──────────────────────────────────
    print(f"\n{'='*100}")
    print(f"  TABLE 2: CORE METRICS (GRINDING-FILTERED)")
    print(f"{'='*100}")

    print(f"\n  {headers[0]:<24}" + "".join(f"{h:>10}" for h in headers[1:]))
    print(f"  {'-'*24}" + f"{'-'*10}" * (len(headers) - 1))

    for vname in variant_names:
        grind = variant_results[vname].get("grinding")
        if grind is None:
            print(f"  {VARIANTS[vname]['label']:<24}  {'— no trades —':>50}")
            continue
        m = grind["metrics"]
        med = m.get("median_trade_duration_bars", 0)
        avg = m.get("avg_trade_duration_bars", 0)
        print(f"  {VARIANTS[vname]['label']:<24}"
              f"{m['trade_count']:>10}"
              f"{m['profit_factor']:>10.2f}"
              f"{m['win_rate']*100:>9.1f}%"
              f"{m['sharpe']:>10.2f}"
              f"{'${:,.0f}'.format(m['total_pnl']):>10}"
              f"{'${:,.0f}'.format(m['max_drawdown']):>10}"
              f"{med:>9.0f}b"
              f"{avg:>9.0f}b")

    # ── Table 3: Bleed Cell Impact ────────────────────────────────────────
    print(f"\n{'='*100}")
    print(f"  TABLE 3: BLEED CELL IMPACT (RAW — UNGATED)")
    print(f"{'='*100}")

    bleed_headers = ["Variant", "TotalBleed", "BleedTrades", "WorstCell", "WorstPnL"]
    print(f"\n  {bleed_headers[0]:<24}" + "".join(f"{h:>14}" for h in bleed_headers[1:]))
    print(f"  {'-'*24}" + f"{'-'*14}" * (len(bleed_headers) - 1))

    for vname in variant_names:
        raw = variant_results[vname].get("raw")
        if raw is None:
            continue
        print(f"  {VARIANTS[vname]['label']:<24}"
              f"{'${:,.0f}'.format(raw['total_bleed']):>14}"
              f"{raw['bleed_count']:>14}"
              f"{raw['worst_cell']:>14}"
              f"{'${:,.0f}'.format(raw['worst_cell_pnl']):>14}")

    # ── Table 4: Regime Grid ──────────────────────────────────────────────
    print(f"\n{'='*100}")
    print(f"  TABLE 4: REGIME CELL PNL (RAW)")
    print(f"{'='*100}")

    vol_states = ["LOW_VOL", "NORMAL", "HIGH_VOL"]
    trend_states = ["TRENDING", "RANGING"]
    rv_states = ["LOW_RV", "NORMAL_RV", "HIGH_RV"]

    all_cells = []
    for vol in vol_states:
        for trend in trend_states:
            for rv in rv_states:
                all_cells.append(f"{vol}_{trend}_{rv}")

    short_names = {v: VARIANTS[v]["label"][:8] for v in variant_names}
    header = f"  {'Regime Cell':<30}" + "".join(f"{short_names[v]:>12}" for v in variant_names)
    print(f"\n{header}")
    print(f"  {'-'*30}" + f"{'-'*12}" * len(variant_names))

    for cell in all_cells:
        row = f"  {cell:<30}"
        has_data = False
        for vname in variant_names:
            raw = variant_results[vname].get("raw")
            if raw is not None and cell in raw["cell_pnl"].index:
                pnl = raw["cell_pnl"].loc[cell, "pnl"]
                row += f"{'${:,.0f}'.format(pnl):>12}"
                has_data = True
            else:
                row += f"{'—':>12}"
        if has_data:
            print(row)

    # ── Table 5: Portfolio Impact ─────────────────────────────────────────
    if portfolio_impacts:
        print(f"\n{'='*100}")
        print(f"  TABLE 5: PORTFOLIO IMPACT (4-STRAT, GRINDING-GATED DONCHIAN)")
        print(f"{'='*100}")

        port_headers = ["Variant", "PnL", "Sharpe", "Calmar", "MaxDD", "ProfMo", "Trades"]
        print(f"\n  {port_headers[0]:<24}" + "".join(f"{h:>14}" for h in port_headers[1:]))
        print(f"  {'-'*24}" + f"{'-'*14}" * (len(port_headers) - 1))

        for vname in variant_names:
            pi = portfolio_impacts.get(vname)
            if pi is None:
                print(f"  {VARIANTS[vname]['label']:<24}  {'— no data —':>50}")
                continue
            print(f"  {VARIANTS[vname]['label']:<24}"
                  f"{'${:,.0f}'.format(pi['total_pnl']):>14}"
                  f"{pi['sharpe']:>14.2f}"
                  f"{pi['calmar']:>14.2f}"
                  f"{'${:,.0f}'.format(pi['maxdd']):>14}"
                  f"{pi['profitable_months']:>14}"
                  f"{pi['trades']:>14}")

        # ── Table 6: Correlation Matrix ───────────────────────────────────
        print(f"\n{'='*100}")
        print(f"  TABLE 6: CORRELATION MATRIX (BEST VARIANT vs PORTFOLIO)")
        print(f"{'='*100}\n")

        valid_impacts = {v: p for v, p in portfolio_impacts.items() if p is not None}
        if valid_impacts:
            best_v = max(valid_impacts, key=lambda v: valid_impacts[v]["sharpe"])
            print(f"  Best variant by portfolio Sharpe: {VARIANTS[best_v]['label']}")
            corr = valid_impacts[best_v].get("correlation", {})
            for label, r in corr.items():
                print(f"    vs {label}: r = {r:.3f}")

    # ── Table 7: Duration Fingerprint ─────────────────────────────────────
    print(f"\n{'='*100}")
    print(f"  TABLE 7: DURATION FINGERPRINT (RAW)")
    print(f"{'='*100}")

    dur_headers = ["Variant", "p10", "p25", "p50", "p75", "p90", "mean", "WARNING"]
    print(f"\n  {dur_headers[0]:<24}" + "".join(f"{h:>8}" for h in dur_headers[1:]))
    print(f"  {'-'*24}" + f"{'-'*8}" * (len(dur_headers) - 1))

    for vname in variant_names:
        raw = variant_results[vname].get("raw")
        if raw is None:
            continue
        trades = raw["trades"]
        if trades.empty:
            continue

        entry_times = pd.to_datetime(trades["entry_time"])
        exit_times = pd.to_datetime(trades["exit_time"])
        durations = (exit_times - entry_times).dt.total_seconds() / 300

        p10 = np.percentile(durations, 10)
        p25 = np.percentile(durations, 25)
        p50 = np.percentile(durations, 50)
        p75 = np.percentile(durations, 75)
        p90 = np.percentile(durations, 90)
        mean = durations.mean()
        warning = "DEGEN!" if p50 < 30 else ""

        print(f"  {VARIANTS[vname]['label']:<24}"
              f"{p10:>7.0f}b"
              f"{p25:>7.0f}b"
              f"{p50:>7.0f}b"
              f"{p75:>7.0f}b"
              f"{p90:>7.0f}b"
              f"{mean:>7.0f}b"
              f"{warning:>8}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Exit Evolution Engine — Donchian Trend")
    parser.add_argument("--variant", default=None,
                        choices=list(VARIANTS.keys()),
                        help="Run single variant (default: all)")
    parser.add_argument("--no-portfolio", action="store_true",
                        help="Skip portfolio impact analysis")
    args = parser.parse_args()

    print("=" * 100)
    print("  EXIT EVOLUTION ENGINE — DONCHIAN TREND EXIT VARIANTS")
    print("=" * 100)

    # Load MNQ data
    data_path = PROCESSED_DIR / "MNQ_5m.csv"
    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    print(f"\n  Data: {len(df):,} bars, {df['datetime'].dt.date.nunique()} days")
    print(f"  Range: {df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]}")

    # Generate entries using original strategy (guarantees identical entries)
    print(f"\n  Generating shared entries (via original strategy module)...")
    entry_data = donchian_entries(df)
    n_entries = len(entry_data["entries"])
    n_long = sum(1 for e in entry_data["entries"] if e["direction"] == 1)
    n_short = sum(1 for e in entry_data["entries"] if e["direction"] == -1)
    print(f"  Entries: {n_entries} total ({n_long} long, {n_short} short)")

    # Regime engine
    print(f"  Computing regime data...")
    engine = RegimeEngine()
    regime_daily = engine.get_daily_regimes(df)

    # Select variants to run
    if args.variant:
        variant_names = [args.variant]
        if args.variant != "baseline":
            variant_names = ["baseline"] + variant_names
    else:
        variant_names = list(VARIANTS.keys())

    # Run all variants
    variant_results = {}
    for vname in variant_names:
        print(f"\n  Running variant: {VARIANTS[vname]['label']}...")
        result = run_variant(vname, df, entry_data, regime_daily)
        variant_results[vname] = result

        raw = result.get("raw")
        grind = result.get("grinding")
        if raw:
            m = raw["metrics"]
            print(f"    Raw:      {m['trade_count']} trades, PF={m['profit_factor']:.3f}, "
                  f"Sharpe={m['sharpe']:.2f}, PnL=${m['total_pnl']:,.0f}, "
                  f"MedHold={m.get('median_trade_duration_bars',0):.0f}b, "
                  f"Bleed=${raw['total_bleed']:,.0f}")
        if grind:
            m = grind["metrics"]
            print(f"    GRINDING: {m['trade_count']} trades, PF={m['profit_factor']:.3f}, "
                  f"Sharpe={m['sharpe']:.2f}, PnL=${m['total_pnl']:,.0f}")

    # Portfolio impact
    portfolio_impacts = None
    if not args.no_portfolio:
        print(f"\n  Computing portfolio impact...")
        print(f"    Running PB, ORB, VWAP strategies...")
        base_dailies, base_trades = get_portfolio_base_dailies()
        portfolio_impacts = portfolio_impact(variant_results, base_dailies, base_trades)

    # Print all comparison tables
    print_results(variant_results, portfolio_impacts)

    # ── Final Recommendation ──────────────────────────────────────────────
    print(f"\n{'='*100}")
    print(f"  RECOMMENDATION")
    print(f"{'='*100}")

    baseline_bleed = variant_results.get("baseline", {}).get("raw", {}).get("total_bleed", 0)
    best_bleed_name = "baseline"
    best_bleed_val = baseline_bleed

    for vname in variant_names:
        raw = variant_results[vname].get("raw")
        if raw and raw["total_bleed"] > best_bleed_val:
            best_bleed_val = raw["total_bleed"]
            best_bleed_name = vname

    bleed_reduction = best_bleed_val - baseline_bleed

    baseline_grind = variant_results.get("baseline", {}).get("grinding")
    baseline_grind_pf = baseline_grind["metrics"]["profit_factor"] if baseline_grind else 0

    best_grind = variant_results.get(best_bleed_name, {}).get("grinding")
    best_grind_pf = best_grind["metrics"]["profit_factor"] if best_grind else 0

    print(f"\n  Best bleed reducer: {VARIANTS[best_bleed_name]['label']}")
    print(f"    Bleed: ${baseline_bleed:,.0f} → ${best_bleed_val:,.0f} "
          f"(${bleed_reduction:+,.0f})")
    print(f"    GRINDING PF: {baseline_grind_pf:.3f} → {best_grind_pf:.3f}")

    if portfolio_impacts:
        baseline_pi = portfolio_impacts.get("baseline")
        best_pi = portfolio_impacts.get(best_bleed_name)
        if baseline_pi and best_pi:
            print(f"    Portfolio Sharpe: {baseline_pi['sharpe']:.2f} → {best_pi['sharpe']:.2f}")
            print(f"    Portfolio Calmar: {baseline_pi['calmar']:.2f} → {best_pi['calmar']:.2f}")

    print(f"\n{'='*100}")
    print(f"  DONE")
    print(f"{'='*100}")


if __name__ == "__main__":
    main()
