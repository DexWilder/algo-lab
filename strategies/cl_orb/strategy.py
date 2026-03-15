"""CL-ORB — Crude Oil Opening Range Breakout (Long Only).

Source: ScienceDirect academic research — "remarkable success of ORB in US crude oil futures"
Asset: MCL (micro crude oil futures)
Family: ORB
Side: Long only

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# -- Parameters ---------------------------------------------------------------

ATR_PERIOD = 14
TICK_SIZE = 0.01              # MCL tick size

OR_START = "09:00"            # CL main session open (ET)
OR_END = "09:30"              # Opening range complete
EXIT_TIME = "14:00"           # Flatten before afternoon session

TP_MULT = 2.5                 # Target = entry + OR_range * 2.5
OR_MIN_ATR = 0.3              # OR must be > 0.3 * ATR
OR_MAX_ATR = 1.5              # OR must be < 1.5 * ATR
VOL_MA_LEN = 20               # Volume MA lookback


# -- Helpers ------------------------------------------------------------------

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


# -- Signal Generator ---------------------------------------------------------

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate CL Opening Range Breakout signals (long only).

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # -- ATR (EWM) ------------------------------------------------------------
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"] - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    df["_atr"] = tr.ewm(span=ATR_PERIOD, adjust=False).mean()

    # -- Volume MA -------------------------------------------------------------
    df["_vol_ma"] = df["volume"].rolling(window=VOL_MA_LEN).mean()

    # -- Build Opening Range per day ------------------------------------------
    in_or = (time_str >= OR_START) & (time_str < OR_END)

    or_bars = df[in_or].copy()
    if or_bars.empty:
        df["signal"] = 0
        df["exit_signal"] = 0
        df["stop_price"] = np.nan
        df["target_price"] = np.nan
        for col in [c for c in df.columns if c.startswith("_")]:
            df.drop(columns=[col], inplace=True, errors="ignore")
        return df

    or_stats = or_bars.groupby("_date").agg(
        or_high=("high", "max"),
        or_low=("low", "min"),
    )
    or_stats["or_range"] = or_stats["or_high"] - or_stats["or_low"]
    df = df.merge(or_stats, left_on="_date", right_index=True, how="left")

    # -- Output arrays --------------------------------------------------------
    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # -- Bar-by-bar loop with position tracking --------------------------------
    position = 0
    entry_stop = 0.0
    entry_target = 0.0
    current_date = None
    traded_today = False

    for i in range(n):
        bar_date = df.iloc[i]["_date"]
        time_s = time_str.iloc[i]
        high_px = df.iloc[i]["high"]
        low_px = df.iloc[i]["low"]
        close_px = df.iloc[i]["close"]
        atr_val = df.iloc[i]["_atr"]
        vol_val = df.iloc[i]["volume"]
        vol_ma = df.iloc[i]["_vol_ma"]
        or_h = df.iloc[i]["or_high"] if pd.notna(df.iloc[i].get("or_high")) else np.nan
        or_l = df.iloc[i]["or_low"] if pd.notna(df.iloc[i].get("or_low")) else np.nan
        or_rng = df.iloc[i]["or_range"] if pd.notna(df.iloc[i].get("or_range")) else np.nan

        # -- Day reset with forced exit ---------------------------------------
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            traded_today = False

        # -- EOD flatten at EXIT_TIME -----------------------------------------
        if position != 0 and time_s >= EXIT_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # -- Check stop / target while in position ----------------------------
        if position == 1:
            if low_px <= entry_stop:
                exit_sigs[i] = 1
                position = 0
                continue
            if high_px >= entry_target:
                exit_sigs[i] = 1
                position = 0
                continue

        # -- Entry logic (long only) ------------------------------------------
        if position == 0 and not traded_today:
            # Must be after OR completes, before exit time
            if time_s >= OR_END and time_s < EXIT_TIME:
                # Opening range data must exist
                if not (np.isnan(or_h) or np.isnan(or_l) or np.isnan(or_rng)):
                    # Filter: OR range meaningful relative to ATR
                    if pd.notna(atr_val) and atr_val > 0:
                        or_ok = (or_rng > OR_MIN_ATR * atr_val) and (or_rng < OR_MAX_ATR * atr_val)
                    else:
                        or_ok = False

                    # Filter: Volume confirmation
                    if pd.notna(vol_ma) and vol_ma > 0:
                        vol_ok = vol_val > vol_ma
                    else:
                        vol_ok = True  # no volume data, pass through

                    # Breakout above OR high
                    if close_px > or_h and or_ok and vol_ok:
                        signals[i] = 1
                        stop_arr[i] = or_l
                        target_arr[i] = close_px + or_rng * TP_MULT
                        position = 1
                        entry_stop = or_l
                        entry_target = close_px + or_rng * TP_MULT
                        traded_today = True

    # -- Write arrays back to df ----------------------------------------------
    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr

    # -- Drop temp columns ----------------------------------------------------
    temp_cols = [c for c in df.columns if c.startswith("_")] + [
        "or_high", "or_low", "or_range",
    ]
    df.drop(columns=[c for c in temp_cols if c in df.columns], inplace=True, errors="ignore")

    return df
