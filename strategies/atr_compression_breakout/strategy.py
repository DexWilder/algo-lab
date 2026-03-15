"""ATR-COMPRESSION-BREAKOUT — Volatility Dead Zone Expansion Strategy.

Fills the MISSING volatility expansion family in the portfolio.
Type: tail engine — fires only from extreme ATR compression ("dead zone").

Logic:
- ATR ratio = ATR(fast) / ATR(slow) measures relative volatility compression
- Dead zone: ATR ratio < 0.75 (extreme compression, coiled spring)
- Entry: price breaks above/below 10-bar high/low while in dead zone
- Confirmation: ATR must have increased 20%+ from its compression low
- Volume confirmation: bar volume > 1.3x 20-bar SMA
- Stop: 2.0x the CONTRACTED ATR value (tighter risk, better R:R)
- Target: 5.0x contracted ATR (asymmetric payoff)
- Trailing: profit ladder at 2R→1R, 4R→2.5R
- Time exit: 15:55 (never hold overnight)
- Cooldown: 25 bars (avoid re-triggering on same compression event)
- Max 1 trade per session per direction

Key insight from research:
- Using the contracted ATR for stops gives naturally tighter risk
- Dead zone entries are rare but produce outsized moves when they fire
- Works best on M2K (Russell) due to violent liquidity bursts

Expected behavior:
- Win rate 35-45% (breakout from compression)
- 1-3 trades per week (very selective)
- Top 10% of trades should contribute 50%+ of PnL
- Near-zero correlation with existing portfolio

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ---------------------------------------------------------------

ATR_FAST = 5               # Fast ATR period
ATR_SLOW = 50              # Slow ATR period
ATR_RATIO_DEAD = 0.75      # Dead zone threshold (extreme compression)
ATR_EXPANSION_PCT = 0.20   # ATR must increase 20% from low to confirm expansion

BREAKOUT_LOOKBACK = 10     # N-bar high/low breakout lookback
ATR_STOP_PERIOD = 14       # ATR period for stop calculation
ATR_STOP_MULT = 2.0        # Stop = contracted_ATR x mult
ATR_TARGET_MULT = 5.0      # Target = contracted_ATR x mult

VOL_CONFIRM_MULT = 1.3     # Bar volume > mult x 20-bar avg
VOL_AVG_PERIOD = 20        # Volume average lookback
COOLDOWN_BARS = 25         # Min bars between trades

# Profit ladder rungs: (threshold in R, new stop in R from entry)
PROFIT_LADDER = [(2.0, 1.0), (4.0, 2.5)]

ENTRY_START = "09:45"      # Earliest entry
ENTRY_CUTOFF = "15:30"     # Latest entry
TIME_EXIT = "15:55"        # Force close

TICK_SIZE = 0.25           # Patched per asset by runner


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate ATR compression breakout signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Entry window ----------------------------------------------------------
    entry_ok = (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # -- True Range and ATR ----------------------------------------------------
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)

    atr_fast = tr.ewm(span=ATR_FAST, adjust=False).mean().values
    atr_slow = tr.ewm(span=ATR_SLOW, adjust=False).mean().values
    atr_stop = tr.ewm(span=ATR_STOP_PERIOD, adjust=False).mean().values

    # -- ATR Ratio (compression detector) --------------------------------------
    atr_ratio = np.where(atr_slow > 0, atr_fast / atr_slow, 1.0)

    # -- Dead zone detection ---------------------------------------------------
    in_dead_zone = atr_ratio < ATR_RATIO_DEAD

    # Track ATR compression low (rolling minimum of fast ATR during dead zone)
    atr_compression_low = np.full(n, np.nan)
    current_low = np.inf
    for i in range(n):
        if in_dead_zone[i]:
            current_low = min(current_low, atr_fast[i])
            atr_compression_low[i] = current_low
        else:
            # Keep the last compression low for a few bars after exit
            if not np.isnan(atr_compression_low[i - 1]) if i > 0 else False:
                atr_compression_low[i] = atr_compression_low[i - 1]
            current_low = np.inf

    # ATR expansion confirmation: ATR increased 20%+ from compression low
    atr_expanded = np.zeros(n, dtype=bool)
    for i in range(n):
        if not np.isnan(atr_compression_low[i]) and atr_compression_low[i] > 0:
            pct_increase = (atr_fast[i] - atr_compression_low[i]) / atr_compression_low[i]
            atr_expanded[i] = pct_increase >= ATR_EXPANSION_PCT

    # -- N-bar high/low breakout -----------------------------------------------
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values

    # Rolling N-bar high and low (excluding current bar)
    n_bar_high = np.full(n, np.nan)
    n_bar_low = np.full(n, np.nan)
    for i in range(BREAKOUT_LOOKBACK, n):
        n_bar_high[i] = np.max(high_arr[i - BREAKOUT_LOOKBACK:i])
        n_bar_low[i] = np.min(low_arr[i - BREAKOUT_LOOKBACK:i])

    breakout_long = close_arr > n_bar_high
    breakout_short = close_arr < n_bar_low

    # -- Volume confirmation ---------------------------------------------------
    volume = df["volume"].values if "volume" in df.columns else np.ones(n)
    vol_sma = pd.Series(volume).rolling(VOL_AVG_PERIOD, min_periods=VOL_AVG_PERIOD).mean().values
    vol_ok = volume > VOL_CONFIRM_MULT * vol_sma

    # -- Pre-compute arrays ----------------------------------------------------
    time_arr = time_str.values
    dates_arr = df["_date"].values
    entry_ok_arr = entry_ok.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful loop ---------------------------------------------------------
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    initial_risk = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    bars_since_last_trade = COOLDOWN_BARS
    was_in_dead_zone = False  # Track if we recently exited dead zone

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False
            bars_since_last_trade = COOLDOWN_BARS
            was_in_dead_zone = False

        # Track dead zone transitions
        if in_dead_zone[i]:
            was_in_dead_zone = True

        # Skip if indicators not ready
        if (np.isnan(atr_fast[i]) or np.isnan(atr_slow[i])
                or np.isnan(n_bar_high[i])):
            bars_since_last_trade += 1
            continue

        # -- Time exit ---------------------------------------------------------
        if position != 0 and bar_time >= TIME_EXIT:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            bars_since_last_trade = 0
            continue

        # -- Check exits for open position -------------------------------------
        if position == 1:
            bars_since_last_trade += 1

            # Profit ladder
            if initial_risk > 0:
                r_multiple = (high_arr[i] - entry_price) / initial_risk
                for threshold, new_stop_r in PROFIT_LADDER:
                    if r_multiple >= threshold:
                        ladder_stop = entry_price + new_stop_r * initial_risk
                        if ladder_stop > stop_price:
                            stop_price = ladder_stop

            if high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0
                continue

            if low_arr[i] <= stop_price:
                exit_sigs[i] = 1
                position = 0
                continue

        elif position == -1:
            bars_since_last_trade += 1

            if initial_risk > 0:
                r_multiple = (entry_price - low_arr[i]) / initial_risk
                for threshold, new_stop_r in PROFIT_LADDER:
                    if r_multiple >= threshold:
                        ladder_stop = entry_price - new_stop_r * initial_risk
                        if ladder_stop < stop_price:
                            stop_price = ladder_stop

            if low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
                continue

            if high_arr[i] >= stop_price:
                exit_sigs[i] = -1
                position = 0
                continue

        # -- Entry logic -------------------------------------------------------
        # Must have been in dead zone recently AND ATR is now expanding
        if (position == 0 and entry_ok_arr[i]
                and bars_since_last_trade >= COOLDOWN_BARS
                and was_in_dead_zone and atr_expanded[i] and vol_ok[i]):

            # Use the contracted ATR for stops (key insight: tighter risk)
            contracted_atr = atr_compression_low[i]
            if np.isnan(contracted_atr) or contracted_atr <= 0:
                contracted_atr = atr_stop[i]

            # -- Long: breakout above N-bar high -------------------------------
            if not long_traded_today and breakout_long[i]:
                initial_stop = close_arr[i] - contracted_atr * ATR_STOP_MULT
                initial_target = close_arr[i] + contracted_atr * ATR_TARGET_MULT
                risk = close_arr[i] - initial_stop

                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = initial_target
                position = 1
                entry_price = close_arr[i]
                stop_price = initial_stop
                target_price = initial_target
                initial_risk = risk
                long_traded_today = True
                bars_since_last_trade = 0
                was_in_dead_zone = False

            # -- Short: breakout below N-bar low -------------------------------
            elif not short_traded_today and breakout_short[i]:
                initial_stop = close_arr[i] + contracted_atr * ATR_STOP_MULT
                initial_target = close_arr[i] - contracted_atr * ATR_TARGET_MULT
                risk = initial_stop - close_arr[i]

                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = initial_target
                position = -1
                entry_price = close_arr[i]
                stop_price = initial_stop
                target_price = initial_target
                initial_risk = risk
                short_traded_today = True
                bars_since_last_trade = 0
                was_in_dead_zone = False

        bars_since_last_trade += 1

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
