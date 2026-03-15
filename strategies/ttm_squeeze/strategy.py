"""TTM-SQUEEZE — Bollinger Band / Keltner Channel Squeeze Breakout.

Fills the MISSING volatility expansion family in the portfolio.
Type: tail engine — fires rarely during extreme compression, catches expansion moves.

Logic:
- Squeeze detection: BB(20, 2.0) fully inside KC(20, 1.5x ATR)
- Minimum squeeze duration: 6 consecutive bars
- Entry: first bar where BB exits KC (squeeze fires)
- Direction: momentum histogram (linear regression of close - midline)
- Long: momentum > 0 AND rising
- Short: momentum < 0 AND falling
- Volume confirmation: bar volume > 1.2x 20-bar SMA
- Stop: 2.0x ATR(14) from entry
- Target: 4.0x ATR(14) from entry (2:1 R:R minimum)
- Trailing: profit ladder at 1.5R→1R, 3R→2R
- Time exit: 15:55 (never hold overnight)
- Cooldown: 20 bars (avoid re-triggering on same squeeze)
- Max 1 trade per session per direction

Expected behavior:
- Win rate 35-50% (breakout strategy with large winners)
- 2-5 trades per week
- Top 10% of trades should contribute 40%+ of PnL (tail engine)
- Near-zero correlation with existing portfolio (different trigger)

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ---------------------------------------------------------------

BB_LENGTH = 20             # Bollinger Band lookback
BB_MULT = 2.0              # BB standard deviation multiplier
KC_LENGTH = 20             # Keltner Channel lookback
KC_ATR_MULT = 1.5          # KC ATR multiplier (squeeze threshold)

ATR_PERIOD = 14            # ATR for stops/targets
ATR_STOP_MULT = 2.0        # Stop distance = ATR x mult
ATR_TARGET_MULT = 4.0      # Target distance = ATR x mult

MOM_LENGTH = 12            # Momentum oscillator lookback (linreg period)
MIN_SQUEEZE_BARS = 6       # Minimum consecutive squeeze bars before valid fire

VOL_CONFIRM_MULT = 1.2     # Bar volume > mult x 20-bar avg
VOL_AVG_PERIOD = 20        # Volume average lookback
COOLDOWN_BARS = 20         # Min bars between trades

# Profit ladder rungs: (threshold in R, new stop in R from entry)
PROFIT_LADDER = [(1.5, 1.0), (3.0, 2.0)]

ENTRY_START = "09:45"      # Earliest entry (avoid first 15 min)
ENTRY_CUTOFF = "15:30"     # Latest entry
TIME_EXIT = "15:55"        # Force close

TICK_SIZE = 0.25           # Patched per asset by runner


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_linreg_momentum(close: np.ndarray, length: int) -> np.ndarray:
    """Compute linear regression value of close relative to midline.

    This is the TTM Squeeze momentum oscillator:
    LinReg(close - avg(highest_high, lowest_low, sma), length)
    """
    n = len(close)
    mom = np.full(n, np.nan)
    if n < length:
        return mom

    # Rolling highest high and lowest low (using close as proxy for simplicity)
    # Standard TTM uses Donchian midline
    for i in range(length - 1, n):
        window = close[i - length + 1:i + 1]
        midline = (np.max(window) + np.min(window) + np.mean(window)) / 3.0
        delta = close[i] - midline

        # Linear regression of the delta series
        if i >= 2 * length - 2:
            y = np.array([close[j] - (np.max(close[j - length + 1:j + 1]) +
                          np.min(close[j - length + 1:j + 1]) +
                          np.mean(close[j - length + 1:j + 1])) / 3.0
                          for j in range(i - length + 1, i + 1)])
            x = np.arange(length, dtype=float)
            # Simple linreg: slope * (length-1) + intercept = predicted last value
            x_mean = x.mean()
            y_mean = y.mean()
            ss_xy = np.sum((x - x_mean) * (y - y_mean))
            ss_xx = np.sum((x - x_mean) ** 2)
            if ss_xx > 0:
                slope = ss_xy / ss_xx
                intercept = y_mean - slope * x_mean
                mom[i] = slope * (length - 1) + intercept
            else:
                mom[i] = y_mean
        else:
            mom[i] = delta

    return mom


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame, asset: str = None) -> pd.DataFrame:
    """Generate TTM Squeeze breakout signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Entry window ----------------------------------------------------------
    entry_ok = (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # -- Bollinger Bands -------------------------------------------------------
    close_arr = df["close"].values
    bb_sma = pd.Series(close_arr).rolling(BB_LENGTH, min_periods=BB_LENGTH).mean().values
    bb_std = pd.Series(close_arr).rolling(BB_LENGTH, min_periods=BB_LENGTH).std().values
    bb_upper = bb_sma + BB_MULT * bb_std
    bb_lower = bb_sma - BB_MULT * bb_std

    # -- Keltner Channels ------------------------------------------------------
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)

    kc_atr = tr.ewm(span=KC_LENGTH, adjust=False).mean().values
    kc_mid = pd.Series(close_arr).ewm(span=KC_LENGTH, adjust=False).mean().values
    kc_upper = kc_mid + KC_ATR_MULT * kc_atr
    kc_lower = kc_mid - KC_ATR_MULT * kc_atr

    # -- Squeeze detection -----------------------------------------------------
    # Squeeze ON: BB fully inside KC
    squeeze_on = (bb_upper < kc_upper) & (bb_lower > kc_lower)

    # Count consecutive squeeze bars
    squeeze_count = np.zeros(n, dtype=int)
    for i in range(1, n):
        if squeeze_on[i]:
            squeeze_count[i] = squeeze_count[i - 1] + 1
        else:
            squeeze_count[i] = 0

    # Squeeze fires: first bar where squeeze turns OFF after being ON for MIN_SQUEEZE_BARS+
    squeeze_fire = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if not squeeze_on[i] and squeeze_count[i - 1] >= MIN_SQUEEZE_BARS:
            squeeze_fire[i] = True

    # -- Momentum oscillator ---------------------------------------------------
    momentum = _compute_linreg_momentum(close_arr, MOM_LENGTH)

    # Momentum direction: rising or falling
    mom_rising = np.zeros(n, dtype=bool)
    mom_falling = np.zeros(n, dtype=bool)
    for i in range(1, n):
        if not np.isnan(momentum[i]) and not np.isnan(momentum[i - 1]):
            mom_rising[i] = momentum[i] > momentum[i - 1]
            mom_falling[i] = momentum[i] < momentum[i - 1]

    # -- ATR for stops/targets -------------------------------------------------
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # -- Volume confirmation ---------------------------------------------------
    volume = df["volume"].values if "volume" in df.columns else np.ones(n)
    vol_sma = pd.Series(volume).rolling(VOL_AVG_PERIOD, min_periods=VOL_AVG_PERIOD).mean().values
    vol_ok = volume > VOL_CONFIRM_MULT * vol_sma

    # -- Pre-compute arrays ----------------------------------------------------
    high_arr = df["high"].values
    low_arr = df["low"].values
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

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False
            bars_since_last_trade = COOLDOWN_BARS

        # Skip if indicators not ready
        if np.isnan(bar_atr) or np.isnan(bb_upper[i]) or np.isnan(kc_upper[i]):
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

            # Profit ladder: adjust stop based on max favorable excursion
            if initial_risk > 0:
                r_multiple = (high_arr[i] - entry_price) / initial_risk
                for threshold, new_stop_r in PROFIT_LADDER:
                    if r_multiple >= threshold:
                        ladder_stop = entry_price + new_stop_r * initial_risk
                        if ladder_stop > stop_price:
                            stop_price = ladder_stop

            # Target hit
            if high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0
                continue

            # Stop hit
            if low_arr[i] <= stop_price:
                exit_sigs[i] = 1
                position = 0
                continue

        elif position == -1:
            bars_since_last_trade += 1

            # Profit ladder for shorts
            if initial_risk > 0:
                r_multiple = (entry_price - low_arr[i]) / initial_risk
                for threshold, new_stop_r in PROFIT_LADDER:
                    if r_multiple >= threshold:
                        ladder_stop = entry_price - new_stop_r * initial_risk
                        if ladder_stop < stop_price:
                            stop_price = ladder_stop

            # Target hit
            if low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0
                continue

            # Stop hit
            if high_arr[i] >= stop_price:
                exit_sigs[i] = -1
                position = 0
                continue

        # -- Entry logic -------------------------------------------------------
        if (position == 0 and entry_ok_arr[i]
                and bars_since_last_trade >= COOLDOWN_BARS
                and squeeze_fire[i] and vol_ok[i]):

            # -- Long: momentum positive and rising ----------------------------
            if (not long_traded_today
                    and not np.isnan(momentum[i])
                    and momentum[i] > 0 and mom_rising[i]):

                initial_stop = close_arr[i] - bar_atr * ATR_STOP_MULT
                initial_target = close_arr[i] + bar_atr * ATR_TARGET_MULT
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

            # -- Short: momentum negative and falling --------------------------
            elif (not short_traded_today
                  and not np.isnan(momentum[i])
                  and momentum[i] < 0 and mom_falling[i]):

                initial_stop = close_arr[i] + bar_atr * ATR_STOP_MULT
                initial_target = close_arr[i] - bar_atr * ATR_TARGET_MULT
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

        bars_since_last_trade += 1

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
