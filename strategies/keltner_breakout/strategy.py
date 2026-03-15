"""KELTNER-BREAKOUT — Keltner Channel Breakout with RSI + ADX Confirmation.

Target asset: M2K (Russell 2000 micro futures), 5-minute bars, long-side focus.
Based on QuantifiedStrategies Keltner Breakout (77% documented win rate).

Logic:
- Entry (long): close breaks above upper KC (EMA20 + 2*ATR)
  + RSI(14) > 50 (momentum confirmation)
  + ADX(14) > 20 (trending market confirmation)
  + Time between 09:45-14:30 ET
- Stop: tighter of middle KC band (20 EMA) or entry - 2*ATR
- Target: entry + 3*ATR
- Exit: EOD flatten at 15:30, or close drops below middle band
- Max 1 trade per day

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ----------------------------------------------------------------

KC_EMA_LEN = 20           # Keltner Channel EMA period
ATR_PERIOD = 14            # ATR period for channel width and stops
KC_MULT = 2.0              # Channel width = EMA +/- ATR * mult
RSI_PERIOD = 14            # RSI lookback
RSI_THRESHOLD = 50         # Minimum RSI for long entry
ADX_PERIOD = 14            # ADX lookback
ADX_THRESHOLD = 20         # Minimum ADX for entry (trending)
ATR_STOP_MULT = 2.0        # Stop distance = ATR * mult (alternative stop)
ATR_TARGET_MULT = 3.0      # Target distance = ATR * mult

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "09:45"
ENTRY_END = "14:30"
FLATTEN_TIME = "15:30"     # Pre-close flatten

TICK_SIZE = 0.10           # M2K tick size; patched per asset by runner


# -- Helpers -------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _compute_rsi(close_arr, period=14):
    """RSI via Wilder smoothing (ewm alpha=1/period)."""
    delta = pd.Series(close_arr).diff()
    gain = delta.where(delta > 0, 0.0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss
    rsi = 100 - 100 / (1 + rs)
    return rsi.values


def _compute_adx(high_arr, low_arr, close_arr, period=14):
    """ADX via standard DI+/DI- smoothing."""
    high_s = pd.Series(high_arr)
    low_s = pd.Series(low_arr)
    close_s = pd.Series(close_arr)

    prev_high = high_s.shift(1)
    prev_low = low_s.shift(1)

    # Directional movement
    up_move = high_s - prev_high
    down_move = prev_low - low_s

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0))
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0))

    # True range
    prev_close = close_s.shift(1)
    tr = pd.concat([
        high_s - low_s,
        (high_s - prev_close).abs(),
        (low_s - prev_close).abs(),
    ], axis=1).max(axis=1)

    # Smooth with ewm
    atr_smooth = tr.ewm(span=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(span=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(span=period, adjust=False).mean()

    # DI+ and DI-
    plus_di = 100 * plus_dm_smooth / atr_smooth
    minus_di = 100 * minus_dm_smooth / atr_smooth

    # DX and ADX
    di_sum = plus_di + minus_di
    di_sum = di_sum.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    adx = dx.ewm(span=period, adjust=False).mean()

    return adx.values


# -- Signal Generator ----------------------------------------------------------

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate Keltner Channel breakout signals with RSI + ADX confirmation.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- Session boundaries ----------------------------------------------------
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = (time_str >= ENTRY_START) & (time_str < ENTRY_END)

    # -- Keltner Channel -------------------------------------------------------
    ema = df["close"].ewm(span=KC_EMA_LEN, adjust=False).mean()

    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean()

    # Shift by 1 to avoid look-ahead
    upper_kc = (ema + atr * KC_MULT).shift(1)
    middle_kc = ema.shift(1)

    # -- RSI -------------------------------------------------------------------
    rsi_arr = _compute_rsi(df["close"].values, RSI_PERIOD)

    # -- ADX -------------------------------------------------------------------
    adx_arr = _compute_adx(
        df["high"].values, df["low"].values, df["close"].values, ADX_PERIOD
    )

    # -- Pre-compute arrays for stateful loop ----------------------------------
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values
    upper_kc_arr = upper_kc.values
    middle_kc_arr = middle_kc.values
    atr_arr = atr.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Stateful entry/exit loop ----------------------------------------------
    position = 0
    entry_price = 0.0
    stop_price = 0.0
    current_date = None
    traded_today = False

    for i in range(n):
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr_arr[i]

        # -- Day reset ---------------------------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1
                position = 0
            current_date = bar_date
            traded_today = False

        if not in_session_arr[i]:
            continue

        # -- Pre-close flatten -------------------------------------------------
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1
            position = 0
            continue

        # -- Check exits for open position -------------------------------------
        if position == 1:
            # Exit 1: close drops below middle KC band
            if close_arr[i] < middle_kc_arr[i]:
                exit_sigs[i] = 1
                position = 0
                continue

            # Exit 2: stop hit (low touches stop)
            if low_arr[i] <= stop_price:
                exit_sigs[i] = 1
                position = 0
                continue

        # -- Entry (long only) -------------------------------------------------
        if position == 0 and entry_ok_arr[i] and not traded_today:
            upper = upper_kc_arr[i]
            mid = middle_kc_arr[i]

            if np.isnan(upper) or np.isnan(mid) or np.isnan(bar_atr):
                continue
            if np.isnan(rsi_arr[i]) or np.isnan(adx_arr[i]):
                continue

            # Long breakout with confirmation
            if (close_arr[i] > upper
                    and rsi_arr[i] > RSI_THRESHOLD
                    and adx_arr[i] > ADX_THRESHOLD):

                entry_px = close_arr[i]

                # Stop: tighter of middle band or entry - 2*ATR
                stop_mid = mid
                stop_atr = entry_px - bar_atr * ATR_STOP_MULT
                stop_px = max(stop_mid, stop_atr)

                # Target: entry + 3*ATR
                target_px = entry_px + bar_atr * ATR_TARGET_MULT

                signals_arr[i] = 1
                stop_arr[i] = stop_px
                target_arr[i] = target_px

                position = 1
                entry_price = entry_px
                stop_price = stop_px
                traded_today = True

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
