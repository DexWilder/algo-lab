"""Larry Williams Oops -- Fade gaps beyond prior day's range.

When the market gaps beyond yesterday's high or low at the open,
enter on the reclaim back into the prior range. Trail at intraday
extreme, flatten at session close.

Logic:
  - Gap down Oops: open < yesterday's low -> buy stop at yesterday's low + filter
  - Gap up Oops: open > yesterday's high -> sell stop at yesterday's high - filter
  - Entry window: first 2 hours of RTH (no entry if gap holds)
  - Exit: trail at session extreme or fixed target (prior close / range midpoint)
  - Flatten at session close, no overnight hold

Designed for: MES, MNQ, MGC on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Entry filter
FILTER_ATR_MULT = 0.1       # Buffer above/below reclaim level
ATR_LEN = 20

# Entry window (hours after RTH open)
ENTRY_WINDOW_HOURS = 2

# Session times (ET) — adjusted per asset at runtime
RTH_OPEN_HOUR = 9
RTH_OPEN_MIN = 30
FLATTEN_HOUR = 15
FLATTEN_MIN = 55

# Exit variant: "trail" or "target"
# trail: trail at intraday extreme (session low for longs, high for shorts)
# target: exit at prior day's close (mean-reversion target)
EXIT_VARIANT = "trail"

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

    # Build RTH-only daily OHLC for prior-day reference
    # Use RTH bars only (not overnight) for accurate gap detection
    rth_mask = (df["hour"] * 100 + df["minute"] >= RTH_OPEN_HOUR * 100 + RTH_OPEN_MIN) & \
               (df["hour"] * 100 + df["minute"] <= FLATTEN_HOUR * 100 + FLATTEN_MIN)
    rth_df = df[rth_mask]
    daily = rth_df.groupby("date").agg(
        d_open=("open", "first"),
        d_high=("high", "max"),
        d_low=("low", "min"),
        d_close=("close", "last"),
    ).reset_index()

    # Map prior day's high, low, close to each bar
    daily["prev_high"] = daily["d_high"].shift(1)
    daily["prev_low"] = daily["d_low"].shift(1)
    daily["prev_close"] = daily["d_close"].shift(1)
    daily_map = daily.set_index("date")[["d_open", "prev_high", "prev_low", "prev_close"]].to_dict("index")

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    open_ = df["open"].values
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
    trail_stop = 0.0
    target_price = 0.0
    session_low = 0.0
    session_high = 0.0
    current_date = None
    oops_type = 0       # 1 = gap down (long), -1 = gap up (short)
    reclaim_level = 0.0
    oops_armed = False
    traded_today = False

    for i in range(n):
        h = hour[i]
        m = minute[i]
        bar_close = close[i]
        bar_high = high[i]
        bar_low = low[i]
        bar_open = open_[i]
        bar_atr = atr[i]
        bar_date = dates[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # ---- New day reset ----
        if bar_date != current_date:
            current_date = bar_date
            oops_armed = False
            oops_type = 0
            traded_today = False
            session_low = bar_low
            session_high = bar_high

            # Check for Oops gap at open
            day_info = daily_map.get(bar_date)
            if day_info and day_info["prev_high"] is not None and not np.isnan(day_info["prev_high"]):
                prev_high = day_info["prev_high"]
                prev_low = day_info["prev_low"]
                prev_close = day_info["prev_close"]
                day_open = day_info["d_open"]

                filter_size = bar_atr * FILTER_ATR_MULT

                # Gap down Oops: open below prior low
                if day_open < prev_low and allow_long:
                    oops_type = 1
                    reclaim_level = prev_low + filter_size
                    target_price = prev_close if EXIT_VARIANT == "target" else 0
                    oops_armed = True

                # Gap up Oops: open above prior high
                elif day_open > prev_high and allow_short:
                    oops_type = -1
                    reclaim_level = prev_high - filter_size
                    target_price = prev_close if EXIT_VARIANT == "target" else 0
                    oops_armed = True

        # Track session extremes
        if bar_high > session_high:
            session_high = bar_high
        if bar_low < session_low:
            session_low = bar_low

        # ---- Flatten at session close ----
        if time_val >= FLATTEN_HOUR * 100 + FLATTEN_MIN:
            if position != 0:
                exit_sigs[i] = position
                position = 0
            oops_armed = False
            continue

        # ---- Manage position ----
        if position == 1:
            # Update trail stop
            trail_stop = session_low

            # Trail stop hit
            if bar_low <= trail_stop and EXIT_VARIANT == "trail":
                exit_sigs[i] = 1; position = 0; continue

            # Target hit
            if EXIT_VARIANT == "target" and target_price > 0 and bar_high >= target_price:
                exit_sigs[i] = 1; position = 0; continue

        elif position == -1:
            trail_stop = session_high

            if bar_high >= trail_stop and EXIT_VARIANT == "trail":
                exit_sigs[i] = -1; position = 0; continue

            if EXIT_VARIANT == "target" and target_price > 0 and bar_low <= target_price:
                exit_sigs[i] = -1; position = 0; continue

        # ---- Entry: Oops reclaim within window ----
        if position == 0 and oops_armed and not traded_today:
            entry_deadline = (RTH_OPEN_HOUR + ENTRY_WINDOW_HOURS) * 100 + RTH_OPEN_MIN
            if time_val > entry_deadline:
                oops_armed = False
                continue

            # Only enter during RTH
            if time_val < RTH_OPEN_HOUR * 100 + RTH_OPEN_MIN:
                continue

            # Gap down Oops: long on reclaim above prior low
            if oops_type == 1 and bar_close > reclaim_level:
                entry_price = bar_close
                session_low = bar_low  # Reset trail reference
                signals[i] = 1
                stop_arr[i] = session_low
                if EXIT_VARIANT == "target":
                    target_arr[i] = target_price
                position = 1
                traded_today = True
                oops_armed = False
                continue

            # Gap up Oops: short on reclaim below prior high
            if oops_type == -1 and bar_close < reclaim_level:
                entry_price = bar_close
                session_high = bar_high
                signals[i] = -1
                stop_arr[i] = session_high
                if EXIT_VARIANT == "target":
                    target_arr[i] = target_price
                position = -1
                traded_today = True
                oops_armed = False
                continue

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date", "hour", "minute", "atr"], inplace=True)
    return df
