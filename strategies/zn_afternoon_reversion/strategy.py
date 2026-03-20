"""ZN Afternoon Reversion — Fade outsized 13:45-14:00 ET moves on ZN.

Discovered as Variant B during Treasury-Cash-Close-Reversion falsification.
The parent hypothesis (cash-close reversion at 15:00) was REJECTED — this
is a distinct, earlier mechanism: pre-cash-close afternoon mean-reversion
peaking at 14:00 ET, one hour before the cash bond close.

Logic:
  - Measure the 13:45-14:00 ET move in ZN (3 bars, 15 minutes)
  - If the move exceeds IMPULSE_THRESHOLD × 20-day median magnitude,
    fade the move at 14:00 ET
  - Exit at 14:25 ET or on 60% retracement or at stop
  - Short-biased: 91% of backtest PnL comes from fading up-moves

Edge characteristics:
  - Strongest in HIGH_VOL regimes (PF 1.64 vs 1.04 in LOW_VOL)
  - Walk-forward stable: H1 PF 1.31, H2 PF 1.33
  - Window-specific: shifting ±15 or ±30 minutes degrades results
  - Tuesday is the one weak day (PF 0.87)

Data caveat: ZN 5m bars at 14:25 ET exist on ~82% of weekdays. Missing
18% are low-volume days. Results are conditioned on afternoon tradability.

Designed for: ZN on 5-minute bars.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np

# ---- Parameters ----

IMPULSE_THRESHOLD = 1.5     # Pre-close move must exceed 1.5x 20d median
LOOKBACK = 20               # Days for median move baseline
ATR_LEN = 20                # For stop calculation
SL_ATR_MULT = 1.5           # Stop distance in ATR multiples
RETRACE_PCT = 0.60          # Exit when 60% of impulse retraces

TICK_SIZE = 0.015625        # ZN tick size (1/64 of a point)

# Session times (ET)
IMPULSE_START = (13, 45)    # 13:45 ET — start of impulse window
IMPULSE_END = (13, 55)      # Close of 13:55 bar — end of impulse
ENTRY = (14, 0)             # 14:00 ET — entry (open of this bar)
EXIT = (14, 25)             # 14:25 ET — fixed time exit (close of this bar)


# ---- Helpers ----

def _compute_atr(highs, lows, closes, period=20):
    """True Range -> ATR."""
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _build_daily_sessions(df):
    """Build per-trading-day session summaries."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute

    records = []
    for tdate, grp in df.groupby("date"):
        if pd.Timestamp(tdate).dayofweek >= 5:
            continue

        start_bar = grp[(grp["hour"] == IMPULSE_START[0]) & (grp["minute"] == IMPULSE_START[1])]
        end_bar = grp[(grp["hour"] == IMPULSE_END[0]) & (grp["minute"] == IMPULSE_END[1])]
        entry_bar = grp[(grp["hour"] == ENTRY[0]) & (grp["minute"] == ENTRY[1])]
        exit_bar = grp[(grp["hour"] == EXIT[0]) & (grp["minute"] == EXIT[1])]

        if any(b.empty for b in [start_bar, end_bar, entry_bar, exit_bar]):
            continue

        impulse_move = end_bar.iloc[0]["close"] - start_bar.iloc[0]["open"]
        impulse_mag = abs(impulse_move)
        impulse_dir = np.sign(impulse_move)

        entry_price = entry_bar.iloc[0]["open"]
        exit_price = exit_bar.iloc[0]["close"]

        fade_window = grp[
            (grp["hour"] * 60 + grp["minute"] >= ENTRY[0] * 60 + ENTRY[1]) &
            (grp["hour"] * 60 + grp["minute"] <= EXIT[0] * 60 + EXIT[1])
        ]
        window_high = fade_window["high"].max() if not fade_window.empty else np.nan
        window_low = fade_window["low"].min() if not fade_window.empty else np.nan

        rth = grp[(grp["hour"] >= 8) & (grp["hour"] < 16)]
        rth_high = rth["high"].max() if not rth.empty else np.nan
        rth_low = rth["low"].min() if not rth.empty else np.nan
        rth_close = rth.iloc[-1]["close"] if not rth.empty else np.nan

        records.append({
            "trading_date": tdate,
            "impulse_move": impulse_move,
            "impulse_dir": impulse_dir,
            "impulse_mag": impulse_mag,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "window_high": window_high,
            "window_low": window_low,
            "rth_high": rth_high,
            "rth_low": rth_low,
            "rth_close": rth_close,
        })

    daily = pd.DataFrame(records)
    if daily.empty:
        return daily

    daily["trading_date"] = pd.to_datetime(daily["trading_date"])
    daily = daily.sort_values("trading_date").reset_index(drop=True)

    daily["median_mag"] = daily["impulse_mag"].rolling(
        LOOKBACK, min_periods=LOOKBACK
    ).median()
    daily["impulse_ratio"] = daily["impulse_mag"] / daily["median_mag"]

    daily["atr"] = _compute_atr(
        daily["rth_high"], daily["rth_low"], daily["rth_close"], ATR_LEN
    )

    return daily


def generate_signals(df, mode="both"):
    """Generate signals on 5-minute OHLCV data.

    Returns a daily-resampled DataFrame with signal/exit_signal columns.
    """
    daily = _build_daily_sessions(df)

    if daily.empty:
        return pd.DataFrame({
            "datetime": pd.Series(dtype="datetime64[ns]"),
            "open": pd.Series(dtype=float),
            "high": pd.Series(dtype=float),
            "low": pd.Series(dtype=float),
            "close": pd.Series(dtype=float),
            "volume": pd.Series(dtype=float),
            "signal": pd.Series(dtype=int),
            "exit_signal": pd.Series(dtype=int),
            "stop_price": pd.Series(dtype=float),
            "target_price": pd.Series(dtype=float),
        })

    n = len(daily)
    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)
    stop_prices = np.full(n, np.nan)
    target_prices = np.full(n, np.nan)

    position = 0

    for i in range(LOOKBACK + 1, n):
        row = daily.iloc[i]

        if np.isnan(row["entry_price"]) or np.isnan(row["exit_price"]):
            continue
        if np.isnan(row["atr"]) or row["atr"] <= 0:
            continue
        if row["impulse_dir"] == 0:
            continue

        if position != 0:
            exit_signals[i] = position
            position = 0

        if np.isnan(row["impulse_ratio"]) or np.isnan(row["median_mag"]):
            continue
        if row["impulse_ratio"] <= IMPULSE_THRESHOLD:
            continue

        fade_dir = -int(row["impulse_dir"])

        if mode == "long" and fade_dir != 1:
            continue
        if mode == "short" and fade_dir != -1:
            continue

        signals[i] = fade_dir
        position = fade_dir

        atr = row["atr"]
        if fade_dir == 1:
            stop_prices[i] = row["entry_price"] - SL_ATR_MULT * atr
        else:
            stop_prices[i] = row["entry_price"] + SL_ATR_MULT * atr

        retrace_amt = row["impulse_mag"] * RETRACE_PCT
        if fade_dir == 1:
            target_prices[i] = row["entry_price"] + retrace_amt
        else:
            target_prices[i] = row["entry_price"] - retrace_amt

    if position != 0 and n > 0:
        exit_signals[n - 1] = position

    return pd.DataFrame({
        "datetime": daily["trading_date"],
        "open": daily["entry_price"],
        "high": daily["window_high"],
        "low": daily["window_low"],
        "close": daily["exit_price"],
        "volume": pd.Series(0, index=range(n)),
        "signal": signals,
        "exit_signal": exit_signals,
        "stop_price": stop_prices,
        "target_price": target_prices,
    })
