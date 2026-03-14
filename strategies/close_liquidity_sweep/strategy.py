"""Close-Session Liquidity Sweep — Fade false breakouts/breakdowns in final hour.

Family: volatility_expansion / close_session
Target: MES, MNQ, M2K on 5m bars
Window: 15:15-15:50 ET — captures institutional liquidity sweeps before settlement
Logic: Detect sweep of session/prior-day extremes, fade the move when price closes
       back inside the level. Volume confirmation required.

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────────

# Entry window
ENTRY_START = "15:15"
ENTRY_END = "15:50"
TIME_EXIT = "15:55"          # Force close all positions

# Sweep detection
VOL_MULT = 1.5               # Sweep bar volume must exceed this × 20-bar MA
VOL_MA_LEN = 20              # Volume MA lookback
ATR_LEN = 14                 # ATR period for stops and targets

# Risk/reward
ATR_STOP_BUFFER = 0.5        # Extra ATR beyond sweep extreme for stop
ATR_TARGET_MULT = 2.0        # Target = 2.0 × ATR from entry

# Trade management
COOLDOWN_BARS = 8            # Minimum bars between trades
MAX_TRADES_PER_SESSION = 1   # Max sweep trades per session

TICK_SIZE = 0.25              # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# ── Signal Generator ────────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate closing liquidity sweep signals.

    Detects false breakouts/breakdowns of session or prior-day extremes
    in the 15:15-15:50 ET window and fades them.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── ATR ────────────────────────────────────────────────────────────────
    df["_atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    # ── Volume MA ──────────────────────────────────────────────────────────
    has_volume = df["volume"].sum() > 0
    if has_volume:
        df["_vol_ma"] = df["volume"].rolling(window=VOL_MA_LEN).mean()
    else:
        df["_vol_ma"] = np.nan

    # ── Build session high/low and prior day high/low ─────────────────────
    # We need running session high/low and completed prior-day levels.
    # Compute per bar in a forward pass.

    session_high = np.full(n, np.nan)
    session_low = np.full(n, np.nan)
    prior_day_high = np.full(n, np.nan)
    prior_day_low = np.full(n, np.nan)

    current_date = None
    cur_sh = np.nan
    cur_sl = np.nan
    prev_dh = np.nan
    prev_dl = np.nan
    # Track the completed session's high/low to become "prior day" on next date change
    completed_dh = np.nan
    completed_dl = np.nan

    dates = df["_date"].values
    highs = df["high"].values
    lows = df["low"].values

    for i in range(n):
        bar_date = dates[i]

        if bar_date != current_date:
            # New session — save prior session levels
            if current_date is not None:
                completed_dh = cur_sh
                completed_dl = cur_sl
            prev_dh = completed_dh
            prev_dl = completed_dl
            current_date = bar_date
            cur_sh = highs[i]
            cur_sl = lows[i]
        else:
            cur_sh = max(cur_sh, highs[i])
            cur_sl = min(cur_sl, lows[i])

        session_high[i] = cur_sh
        session_low[i] = cur_sl
        prior_day_high[i] = prev_dh
        prior_day_low[i] = prev_dl

    df["_session_high"] = session_high
    df["_session_low"] = session_low
    df["_prior_day_high"] = prior_day_high
    df["_prior_day_low"] = prior_day_low

    # ── Detect sweeps ─────────────────────────────────────────────────────
    # Entry window mask
    in_window = (time_str >= ENTRY_START) & (time_str < ENTRY_END)

    # Volume filter
    if has_volume:
        vol_ok = df["volume"] > (df["_vol_ma"] * VOL_MULT)
    else:
        vol_ok = pd.Series(True, index=df.index)

    closes = df["close"].values
    opens = df["open"].values
    atr_vals = df["_atr"].values

    # Pre-compute raw sweep conditions per bar
    # We also check the "next bar completes" pattern via the loop below.
    # For vectorized part: single-bar sweep (wick through, close back inside)
    #
    # Long sweep (false breakdown): low breaks below level, close back above
    # Short sweep (false breakout): high breaks above level, close back below

    raw_long_sweep = np.zeros(n, dtype=bool)
    raw_short_sweep = np.zeros(n, dtype=bool)

    for i in range(n):
        if not in_window.iloc[i]:
            continue
        if not vol_ok.iloc[i]:
            continue
        if np.isnan(atr_vals[i]):
            continue

        sl = session_low[i]
        sh = session_high[i]
        pdl = prior_day_low[i]
        pdh = prior_day_high[i]

        bar_low = lows[i]
        bar_high = highs[i]
        bar_close = closes[i]

        # For session low sweep: use the session low as of the PREVIOUS bar
        # (otherwise the current bar's low IS the session low by definition).
        # Use prior bar's session low.
        if i > 0 and dates[i] == dates[i - 1]:
            prev_sl = session_low[i - 1]
            prev_sh = session_high[i - 1]
        else:
            prev_sl = np.nan
            prev_sh = np.nan

        # Long sweep: bar low breaks below a key level, bar close back above it
        # Check session low (prior bar's running session low) and prior day low
        long_level_broken = False
        if not np.isnan(prev_sl) and bar_low < prev_sl and bar_close > prev_sl:
            long_level_broken = True
        if not np.isnan(pdl) and bar_low < pdl and bar_close > pdl:
            long_level_broken = True

        if long_level_broken:
            raw_long_sweep[i] = True

        # Short sweep: bar high breaks above a key level, bar close back below it
        short_level_broken = False
        if not np.isnan(prev_sh) and bar_high > prev_sh and bar_close < prev_sh:
            short_level_broken = True
        if not np.isnan(pdh) and bar_high > pdh and bar_close < pdh:
            short_level_broken = True

        if short_level_broken:
            raw_short_sweep[i] = True

    # Also check two-bar sweep: bar[i-1] broke the level, bar[i] closes back inside
    # (the "next bar completes" variant)
    for i in range(1, n):
        if not in_window.iloc[i]:
            continue
        if not vol_ok.iloc[i - 1]:  # Volume on the sweep bar (bar i-1)
            continue
        if np.isnan(atr_vals[i]):
            continue
        if dates[i] != dates[i - 1]:
            continue

        bar_close = closes[i]

        # Previous bar's session low (level as of bar i-2 if available)
        if i >= 2 and dates[i - 2] == dates[i - 1]:
            prev_prev_sl = session_low[i - 2]
            prev_prev_sh = session_high[i - 2]
        else:
            prev_prev_sl = np.nan
            prev_prev_sh = np.nan

        pdl = prior_day_low[i]
        pdh = prior_day_high[i]

        # Two-bar long sweep: bar[i-1] broke below, bar[i] closes above
        two_bar_long = False
        if not np.isnan(prev_prev_sl) and lows[i - 1] < prev_prev_sl and bar_close > prev_prev_sl:
            two_bar_long = True
        if not np.isnan(pdl) and lows[i - 1] < pdl and bar_close > pdl:
            two_bar_long = True

        if two_bar_long and not raw_long_sweep[i]:
            raw_long_sweep[i] = True

        # Two-bar short sweep: bar[i-1] broke above, bar[i] closes below
        two_bar_short = False
        if not np.isnan(prev_prev_sh) and highs[i - 1] > prev_prev_sh and bar_close < prev_prev_sh:
            two_bar_short = True
        if not np.isnan(pdh) and highs[i - 1] > pdh and bar_close < pdh:
            two_bar_short = True

        if two_bar_short and not raw_short_sweep[i]:
            raw_short_sweep[i] = True

    # ── Build raw signals and stop/target ──────────────────────────────────
    df["signal"] = 0
    df["exit_signal"] = 0
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    for i in range(n):
        atr_val = atr_vals[i]
        if np.isnan(atr_val) or atr_val <= 0:
            continue

        if raw_long_sweep[i]:
            df.iat[i, df.columns.get_loc("signal")] = 1
            # Stop below sweep extreme + ATR buffer
            sweep_low = lows[i]
            if i > 0 and dates[i] == dates[i - 1]:
                sweep_low = min(lows[i], lows[i - 1])
            df.iat[i, df.columns.get_loc("stop_price")] = sweep_low - ATR_STOP_BUFFER * atr_val
            df.iat[i, df.columns.get_loc("target_price")] = closes[i] + ATR_TARGET_MULT * atr_val

        elif raw_short_sweep[i]:
            df.iat[i, df.columns.get_loc("signal")] = -1
            # Stop above sweep extreme + ATR buffer
            sweep_high = highs[i]
            if i > 0 and dates[i] == dates[i - 1]:
                sweep_high = max(highs[i], highs[i - 1])
            df.iat[i, df.columns.get_loc("stop_price")] = sweep_high + ATR_STOP_BUFFER * atr_val
            df.iat[i, df.columns.get_loc("target_price")] = closes[i] - ATR_TARGET_MULT * atr_val

    # ── Exit loop: enforce cooldown, max trades, stop/target, time exit ───
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    entry_price = 0.0
    current_date = None
    trades_today = 0
    last_trade_bar = -COOLDOWN_BARS  # Allow first trade immediately
    signals_arr = df["signal"].values.copy()
    exit_sigs = np.zeros(n, dtype=int)

    for i in range(n):
        bar_date = dates[i]
        time_s = time_str.iloc[i]

        # Day reset
        if bar_date != current_date:
            current_date = bar_date
            trades_today = 0

        sig = signals_arr[i]

        # Enforce max trades per session
        if sig != 0 and trades_today >= MAX_TRADES_PER_SESSION:
            signals_arr[i] = 0
            sig = 0

        # Enforce cooldown
        if sig != 0 and (i - last_trade_bar) < COOLDOWN_BARS:
            signals_arr[i] = 0
            sig = 0

        # Time exit — force close at TIME_EXIT
        if position != 0 and time_s >= TIME_EXIT:
            exit_sigs[i] = position  # +1 or -1 to indicate which side exits
            position = 0
            continue

        # Check stop/target while in position
        if position == 1:
            if lows[i] <= entry_stop:
                exit_sigs[i] = 1
                position = 0
            elif highs[i] >= entry_target:
                exit_sigs[i] = 1
                position = 0
        elif position == -1:
            if highs[i] >= entry_stop:
                exit_sigs[i] = -1
                position = 0
            elif lows[i] <= entry_target:
                exit_sigs[i] = -1
                position = 0

        # Open new position
        if position == 0 and sig != 0:
            stop_p = df.iat[i, df.columns.get_loc("stop_price")]
            target_p = df.iat[i, df.columns.get_loc("target_price")]
            if not np.isnan(stop_p) and not np.isnan(target_p):
                position = sig
                entry_stop = stop_p
                entry_target = target_p
                entry_price = closes[i]
                trades_today += 1
                last_trade_bar = i
            else:
                signals_arr[i] = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs

    # ── Cleanup ────────────────────────────────────────────────────────────
    drop_cols = [c for c in df.columns if c.startswith("_")]
    df.drop(columns=drop_cols, inplace=True, errors="ignore")

    return df
