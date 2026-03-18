"""EOD Sentiment Flip -- Filtered overnight hold based on close-session scoring.

Score end-of-day positioning at 15:55 ET using three components,
then take a directional overnight hold only when the score is
clearly bullish or bearish. Flat when neutral.

Logic:
  - Score = close_vs_prior_range + close_vs_prior_close + close_location_value
  - Score >= threshold → long overnight
  - Score <= -threshold → short overnight
  - Neutral → no trade
  - Exit at next RTH open (~09:35 ET)

Designed for: MES, MNQ on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

EVAL_HOUR = 15
EVAL_MIN = 55
EXIT_HOUR = 9
EXIT_MIN = 35

# Score threshold for entry
SCORE_THRESHOLD = 1.0       # Toggle: 1.0 or 1.5

USE_STOP = False
ATR_LEN = 20
SL_ATR_MULT = 1.5

TICK_SIZE = 0.25  # MES default


# ---- Helpers ----

def _atr(high, low, close, period):
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


# ---- Signal Generator ----

def generate_signals(df, asset=None, mode="both"):
    df = df.copy()
    n = len(df)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    # Build daily OHLC for prior-day reference (RTH only: 09:30-16:00)
    rth = df[(df["hour"] * 100 + df["minute"] >= 930) &
             (df["hour"] * 100 + df["minute"] <= 1600)]
    daily = rth.groupby("date").agg(
        d_open=("open", "first"),
        d_high=("high", "max"),
        d_low=("low", "min"),
        d_close=("close", "last"),
    ).reset_index()
    daily["prev_high"] = daily["d_high"].shift(1)
    daily["prev_low"] = daily["d_low"].shift(1)
    daily["prev_close"] = daily["d_close"].shift(1)
    daily_map = daily.set_index("date").to_dict("index")

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hour = df["hour"].values
    minute = df["minute"].values
    dates = df["date"].values
    atr = df["atr"].values

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    entry_date = None

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_atr = atr[i]
        bar_date = dates[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # ---- Exit: next day RTH open ----
        if position != 0:
            should_exit = False

            # Stop
            if USE_STOP:
                if position == 1 and bar_low <= stop_price:
                    should_exit = True
                elif position == -1 and bar_high >= stop_price:
                    should_exit = True

            # Exit at next day's open
            if bar_date != entry_date and time_val >= EXIT_HOUR * 100 + EXIT_MIN:
                should_exit = True

            if should_exit:
                exit_sigs[i] = position
                position = 0
                continue

        # ---- Entry: evaluate score at 15:55 ----
        if position == 0 and h == EVAL_HOUR and m == EVAL_MIN:
            day_info = daily_map.get(bar_date)
            if not day_info:
                continue
            if day_info.get("prev_high") is None or np.isnan(day_info["prev_high"]):
                continue

            prev_high = day_info["prev_high"]
            prev_low = day_info["prev_low"]
            prev_close = day_info["prev_close"]
            today_high = day_info["d_high"]
            today_low = day_info["d_low"]

            # Component 1: Close vs prior day's range
            if bar_close > prev_high:
                score1 = 1.0
            elif bar_close > (prev_high + prev_low) / 2:
                score1 = 0.5
            elif bar_close > prev_low:
                score1 = -0.5
            else:
                score1 = -1.0

            # Component 2: Close vs prior close
            if bar_close > prev_close:
                score2 = 0.5
            else:
                score2 = -0.5

            # Component 3: Close location value
            today_range = today_high - today_low
            if today_range > 0:
                clv = (bar_close - today_low) / today_range
                if clv > 0.7:
                    score3 = 0.5
                elif clv < 0.3:
                    score3 = -0.5
                else:
                    score3 = 0.0
            else:
                score3 = 0.0

            composite = score1 + score2 + score3

            # Entry decision
            if composite >= SCORE_THRESHOLD and allow_long:
                entry_price = bar_close
                stop_price = bar_close - bar_atr * SL_ATR_MULT if USE_STOP else 0
                signals[i] = 1
                stop_arr[i] = stop_price if USE_STOP else np.nan
                position = 1
                entry_date = bar_date

            elif composite <= -SCORE_THRESHOLD and allow_short:
                entry_price = bar_close
                stop_price = bar_close + bar_atr * SL_ATR_MULT if USE_STOP else 0
                signals[i] = -1
                stop_arr[i] = stop_price if USE_STOP else np.nan
                position = -1
                entry_date = bar_date

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date", "hour", "minute", "atr"], inplace=True)
    return df
