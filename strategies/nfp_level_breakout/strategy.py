"""NFP Level Breakout -- Multi-day hold based on NFP-derived levels.

The NFP release (first Friday of each month, 08:30 ET) creates a
high-volatility session whose high and low become persistent structural
levels. A confirmed breakout beyond these levels signals a sustained
directional move.

Logic:
  - Record NFP-day high and low (08:30-16:00 ET on NFP Friday)
  - Long: N consecutive daily closes above NFP high
  - Short: N consecutive daily closes below NFP low
  - One entry per NFP cycle (levels reset each month)
  - Exit: before next NFP or at stop

Designed for: MES, MNQ on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

# Confirmation
CONFIRM_CLOSES = 2          # Toggle: 1 or 2 consecutive closes beyond level

# Stop variant: "midpoint" or "atr"
STOP_TYPE = "midpoint"
ATR_LEN = 20
SL_ATR_MULT = 1.5

# Exit before next NFP
EXIT_DAYS_BEFORE_NFP = 1

TICK_SIZE = 0.25  # MES default

# NFP dates: first Friday of each month (2019-2026)
# These are the actual NFP release dates
NFP_DATES = [
    # 2019
    "2019-01-04", "2019-02-01", "2019-03-08", "2019-04-05",
    "2019-05-03", "2019-06-07", "2019-07-05", "2019-08-02",
    "2019-09-06", "2019-10-04", "2019-11-01", "2019-12-06",
    # 2020
    "2020-01-10", "2020-02-07", "2020-03-06", "2020-04-03",
    "2020-05-08", "2020-06-05", "2020-07-02", "2020-08-07",
    "2020-09-04", "2020-10-02", "2020-11-06", "2020-12-04",
    # 2021
    "2021-01-08", "2021-02-05", "2021-03-05", "2021-04-02",
    "2021-05-07", "2021-06-04", "2021-07-02", "2021-08-06",
    "2021-09-03", "2021-10-08", "2021-11-05", "2021-12-03",
    # 2022
    "2022-01-07", "2022-02-04", "2022-03-04", "2022-04-01",
    "2022-05-06", "2022-06-03", "2022-07-08", "2022-08-05",
    "2022-09-02", "2022-10-07", "2022-11-04", "2022-12-02",
    # 2023
    "2023-01-06", "2023-02-03", "2023-03-10", "2023-04-07",
    "2023-05-05", "2023-06-02", "2023-07-07", "2023-08-04",
    "2023-09-01", "2023-10-06", "2023-11-03", "2023-12-08",
    # 2024
    "2024-01-05", "2024-02-02", "2024-03-08", "2024-04-05",
    "2024-05-03", "2024-06-07", "2024-07-05", "2024-08-02",
    "2024-09-06", "2024-10-04", "2024-11-01", "2024-12-06",
    # 2025
    "2025-01-10", "2025-02-07", "2025-03-07", "2025-04-04",
    "2025-05-02", "2025-06-06", "2025-07-03", "2025-08-01",
    "2025-09-05", "2025-10-03", "2025-11-07", "2025-12-05",
    # 2026
    "2026-01-09", "2026-02-06", "2026-03-06", "2026-04-03",
    "2026-05-01", "2026-06-05", "2026-07-02", "2026-08-07",
    "2026-09-04", "2026-10-02", "2026-11-06", "2026-12-04",
]


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
    df["date_str"] = df["datetime"].dt.strftime("%Y-%m-%d")
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute
    df["atr"] = _atr(df["high"], df["low"], df["close"], ATR_LEN)

    # Build daily OHLC
    daily = df.groupby("date").agg(
        daily_open=("open", "first"),
        daily_high=("high", "max"),
        daily_low=("low", "min"),
        daily_close=("close", "last"),
    ).reset_index()
    daily["date_str"] = daily["date"].astype(str)

    # Build NFP levels
    nfp_set = set(NFP_DATES)
    nfp_levels = {}  # date_str -> (nfp_high, nfp_low, next_nfp_date)

    # For each NFP date, compute the session high/low (08:30-16:00)
    sorted_nfp = sorted(NFP_DATES)
    for idx, nfp_date in enumerate(sorted_nfp):
        nfp_bars = df[(df["date_str"] == nfp_date) &
                      (df["hour"] * 100 + df["minute"] >= 830) &
                      (df["hour"] * 100 + df["minute"] <= 1600)]
        if nfp_bars.empty:
            continue
        nfp_high = float(nfp_bars["high"].max())
        nfp_low = float(nfp_bars["low"].min())
        next_nfp = sorted_nfp[idx + 1] if idx + 1 < len(sorted_nfp) else "2099-12-31"

        # Store levels for all dates from NFP+1 until next NFP
        nfp_levels[nfp_date] = {
            "high": nfp_high,
            "low": nfp_low,
            "midpoint": (nfp_high + nfp_low) / 2,
            "next_nfp": next_nfp,
        }

    # Map each trading day to its active NFP levels
    daily_nfp = {}
    current_levels = None
    for _, row in daily.iterrows():
        ds = row["date_str"]
        if ds in nfp_levels:
            current_levels = nfp_levels[ds]
        if current_levels and ds > list(nfp_levels.keys())[0] if nfp_levels else False:
            daily_nfp[ds] = current_levels

    # Track consecutive closes above/below NFP levels on daily bars
    allow_long = mode in ("long", "both")
    allow_short = mode in ("short", "both")

    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    position = 0
    entry_price = 0.0
    stop_price = 0.0
    current_nfp_date = ""
    traded_this_cycle = False
    consec_above = 0
    consec_below = 0
    prev_date = None

    close_vals = df["close"].values
    high_vals = df["high"].values
    low_vals = df["low"].values
    hour_vals = df["hour"].values
    minute_vals = df["minute"].values
    date_str_vals = df["date_str"].values
    atr_vals = df["atr"].values

    # Build daily close lookup
    daily_close_map = dict(zip(daily["date_str"], daily["daily_close"]))

    for i in range(n):
        bar_date = date_str_vals[i]
        h = hour_vals[i]
        m = minute_vals[i]
        bar_close = close_vals[i]
        bar_high = high_vals[i]
        bar_low = low_vals[i]
        bar_atr = atr_vals[i]
        time_val = h * 100 + m

        if np.isnan(bar_atr) or bar_atr == 0:
            continue

        # Get active NFP levels for this date
        levels = daily_nfp.get(bar_date)
        if not levels:
            continue

        # Reset cycle on NFP day
        if bar_date in nfp_set and bar_date != current_nfp_date:
            current_nfp_date = bar_date
            traded_this_cycle = False
            consec_above = 0
            consec_below = 0
            if position != 0:
                exit_sigs[i] = position
                position = 0
            continue

        # Exit before next NFP
        next_nfp = levels["next_nfp"]
        if next_nfp != "2099-12-31":
            next_nfp_dt = pd.Timestamp(next_nfp)
            exit_by = (next_nfp_dt - pd.Timedelta(days=EXIT_DAYS_BEFORE_NFP)).strftime("%Y-%m-%d")
            if bar_date >= exit_by and position != 0:
                exit_sigs[i] = position
                position = 0
                continue

        # Manage position
        if position == 1:
            if STOP_TYPE == "midpoint" and bar_low <= stop_price:
                exit_sigs[i] = 1; position = 0; continue
            elif STOP_TYPE == "atr" and bar_low <= stop_price:
                exit_sigs[i] = 1; position = 0; continue

        elif position == -1:
            if STOP_TYPE == "midpoint" and bar_high >= stop_price:
                exit_sigs[i] = -1; position = 0; continue
            elif STOP_TYPE == "atr" and bar_high >= stop_price:
                exit_sigs[i] = -1; position = 0; continue

        # Track consecutive daily closes (update once per day at close)
        if time_val == 1555 and bar_date != current_nfp_date:
            dc = daily_close_map.get(bar_date)
            if dc is not None:
                if dc > levels["high"]:
                    consec_above += 1
                    consec_below = 0
                elif dc < levels["low"]:
                    consec_below += 1
                    consec_above = 0
                else:
                    consec_above = 0
                    consec_below = 0

        # Entry logic (at close, after confirmation)
        if position == 0 and not traded_this_cycle and time_val == 1555:
            nfp_high = levels["high"]
            nfp_low = levels["low"]
            nfp_mid = levels["midpoint"]

            if allow_long and consec_above >= CONFIRM_CLOSES:
                entry_price = bar_close
                if STOP_TYPE == "midpoint":
                    stop_price = nfp_mid
                else:
                    stop_price = bar_close - bar_atr * SL_ATR_MULT
                signals[i] = 1
                stop_arr[i] = stop_price
                position = 1
                traded_this_cycle = True
                continue

            if allow_short and consec_below >= CONFIRM_CLOSES:
                entry_price = bar_close
                if STOP_TYPE == "midpoint":
                    stop_price = nfp_mid
                else:
                    stop_price = bar_close + bar_atr * SL_ATR_MULT
                signals[i] = -1
                stop_arr[i] = stop_price
                position = -1
                traded_this_cycle = True
                continue

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date", "date_str", "hour", "minute", "atr"], inplace=True)
    return df
