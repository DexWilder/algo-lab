"""SPX Lunch Compression Afternoon Release.

Source: Harvest note 2026-03-20_07_spx_lunch_compression_afternoon_release.md
Factor: STRUCTURAL (afternoon session microstructure)

Logic:
  1. Define lunch window 12:00-13:30 ET
  2. Compression regime: lunch range < 20th percentile of prior 60 sessions
     AND price stays within 0.35 * 14-day intraday ATR of VWAP during lunch
  3. Entry: first 5-min close after 13:30 ET that breaks the lunch range by
     >= 0.10 * daily ATR in the direction of the break
  4. Exit: 15:25 ET OR price re-enters lunch range for 2 consecutive 5-min bars

Tests both directions. Long when breakout above lunch high, short when below low.

PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# Parameters
LUNCH_START_HHMM = 1200
LUNCH_END_HHMM = 1330
ENTRY_END_HHMM = 1500
EXIT_HHMM = 1525

LUNCH_RANGE_LOOKBACK = 60      # sessions
LUNCH_RANGE_PCTILE = 20        # 20th percentile
VWAP_PROXIMITY_ATR = 0.35      # 0.35 × 14-day intraday ATR
BREAKOUT_ATR_MULT = 0.10       # 0.10 × daily ATR breakout threshold
ATR_LOOKBACK_DAYS = 14

TICK_SIZE = 0.25  # MES default; patched per asset by runner


def _compute_session_features(df):
    """Compute date, hhmm, and session-aligned features."""
    dt = pd.to_datetime(df["datetime"])
    df = df.copy()
    df["date"] = dt.dt.date
    df["hhmm"] = dt.dt.hour * 100 + dt.dt.minute
    return df


def _vwap_per_day(df):
    """Cumulative VWAP within each session day."""
    typ = (df["high"] + df["low"] + df["close"]) / 3
    pv = typ * df["volume"]
    pv_cum = pv.groupby(df["date"]).cumsum()
    v_cum = df["volume"].groupby(df["date"]).cumsum()
    return (pv_cum / v_cum.replace(0, np.nan)).ffill()


def _daily_atr(df, period=14):
    """14-day ATR computed from daily OHLC."""
    daily = df.groupby("date").agg(
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    ).reset_index()
    prev_close = daily["close"].shift(1)
    tr = pd.concat([
        daily["high"] - daily["low"],
        (daily["high"] - prev_close).abs(),
        (daily["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    daily["atr"] = tr.ewm(span=period, adjust=False).mean()
    return dict(zip(daily["date"], daily["atr"]))


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate SPX lunch compression breakout signals."""
    df = _compute_session_features(df)
    n = len(df)

    df["vwap"] = _vwap_per_day(df)
    daily_atr = _daily_atr(df, period=ATR_LOOKBACK_DAYS)

    # Per-day lunch range (12:00-13:30 inclusive)
    lunch_mask = (df["hhmm"] >= LUNCH_START_HHMM) & (df["hhmm"] < LUNCH_END_HHMM)
    lunch_bars = df[lunch_mask]
    lunch_per_day = lunch_bars.groupby("date").agg(
        lunch_high=("high", "max"),
        lunch_low=("low", "min"),
        lunch_vwap=("vwap", "last"),
    )
    lunch_per_day["lunch_range"] = lunch_per_day["lunch_high"] - lunch_per_day["lunch_low"]
    lunch_per_day["lunch_mid"] = (lunch_per_day["lunch_high"] + lunch_per_day["lunch_low"]) / 2

    # 60-session percentile threshold (rolling)
    lunch_per_day["range_pctile_thresh"] = (
        lunch_per_day["lunch_range"]
        .rolling(LUNCH_RANGE_LOOKBACK, min_periods=20)
        .quantile(LUNCH_RANGE_PCTILE / 100.0)
    )

    # Compression flag (range below threshold)
    lunch_per_day["compressed"] = (
        lunch_per_day["lunch_range"] <= lunch_per_day["range_pctile_thresh"]
    )

    # Compute VWAP-proximity check during lunch on a per-day basis
    proximity_ok = {}
    for d, group in lunch_bars.groupby("date"):
        atr = daily_atr.get(d, np.nan)
        if np.isnan(atr) or atr == 0:
            proximity_ok[d] = False
            continue
        # Check max distance from VWAP during lunch
        vwap = group["vwap"]
        max_dist = (group["close"] - vwap).abs().max()
        proximity_ok[d] = bool(max_dist <= VWAP_PROXIMITY_ATR * atr)

    lunch_per_day["proximity_ok"] = lunch_per_day.index.map(proximity_ok)
    lunch_per_day["regime_ok"] = lunch_per_day["compressed"] & lunch_per_day["proximity_ok"]

    # Build per-bar signal arrays
    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    hhmm_arr = df["hhmm"].values
    date_arr = df["date"].values

    # State machine
    position = 0
    entry_price = 0.0
    entry_lunch_high = 0.0
    entry_lunch_low = 0.0
    bars_inside_lunch = 0  # consecutive 5-min bars where price re-entered the lunch range
    daily_atr_today = 0.0

    for i in range(n):
        d = date_arr[i]
        t = hhmm_arr[i]

        # Reset state at start of day
        # (no need — continuous 5m bars; we'll just check t conditions)

        # Manage position
        if position != 0:
            # Re-entry to lunch range = 2 consecutive bars
            if position == 1:
                # Long: exit if price re-enters range
                if low[i] <= entry_lunch_high:  # touching back into the lunch zone
                    bars_inside_lunch += 1
                else:
                    bars_inside_lunch = 0
            elif position == -1:
                if high[i] >= entry_lunch_low:
                    bars_inside_lunch += 1
                else:
                    bars_inside_lunch = 0

            if bars_inside_lunch >= 2:
                exit_sigs[i] = position
                position = 0
                bars_inside_lunch = 0
                continue

            # Time exit at 15:25
            if t >= EXIT_HHMM:
                exit_sigs[i] = position
                position = 0
                bars_inside_lunch = 0
                continue

        # Entry: only when flat, after 13:30, before 15:00
        if position == 0 and t >= LUNCH_END_HHMM and t < ENTRY_END_HHMM:
            if d not in lunch_per_day.index:
                continue
            row = lunch_per_day.loc[d]
            if not row["regime_ok"]:
                continue
            atr = daily_atr.get(d, np.nan)
            if np.isnan(atr) or atr == 0:
                continue

            lunch_h = row["lunch_high"]
            lunch_l = row["lunch_low"]
            breakout_thresh = BREAKOUT_ATR_MULT * atr

            # Long breakout
            if close[i] > lunch_h + breakout_thresh:
                position = 1
                entry_price = close[i]
                entry_lunch_high = lunch_h
                entry_lunch_low = lunch_l
                signals[i] = 1
                stop_arr[i] = lunch_l
                target_arr[i] = close[i] + (lunch_h - lunch_l)
                bars_inside_lunch = 0
            # Short breakdown
            elif close[i] < lunch_l - breakout_thresh:
                position = -1
                entry_price = close[i]
                entry_lunch_high = lunch_h
                entry_lunch_low = lunch_l
                signals[i] = -1
                stop_arr[i] = lunch_h
                target_arr[i] = close[i] - (lunch_h - lunch_l)
                bars_inside_lunch = 0

    df["signal"] = signals
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["date", "hhmm", "vwap"], inplace=True)
    return df
