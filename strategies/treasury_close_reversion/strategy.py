"""Treasury Cash-Close Reversion Window — Fade the pre-close impulse.

Tests whether an outsized 14:45-15:00 ET move in ZN (Treasury 10Y)
reverses in the post-cash-close window (15:00-15:25 ET).

Supports 3 falsification variants via module-level flags:
  VARIANT = "A"  — true close-window reversion (14:45-15:00 → 15:00-15:25)
  VARIANT = "B"  — generic afternoon control  (13:45-14:00 → 14:00-14:25)
  VARIANT = "C"  — unconditional close fade   (no impulse filter, 15:00-15:25)

Data caveat: ZN 5m bars at 15:25 ET exist on ~80% of weekdays. Missing
20% are low-volume days. Results are conditioned on close-window
tradability.

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

# Variant flag — set before calling generate_signals
VARIANT = "A"               # "A", "B", or "C"

# Variant-specific session windows (hour, minute)
_VARIANT_CONFIG = {
    "A": {
        "impulse_start": (14, 45),   # 14:45 ET
        "impulse_end":   (14, 55),   # close of 14:55 bar
        "entry":         (15, 0),    # 15:00 ET
        "exit":          (15, 25),   # 15:25 ET
        "use_filter":    True,
    },
    "B": {
        "impulse_start": (13, 45),   # 13:45 ET — 1 hour earlier
        "impulse_end":   (13, 55),   # close of 13:55 bar
        "entry":         (14, 0),    # 14:00 ET
        "exit":          (14, 25),   # 14:25 ET
        "use_filter":    True,
    },
    "C": {
        "impulse_start": (14, 45),   # Still measure 14:45-15:00 move
        "impulse_end":   (14, 55),   # ... for direction only
        "entry":         (15, 0),    # 15:00 ET
        "exit":          (15, 25),   # 15:25 ET
        "use_filter":    False,      # No threshold — always trade
    },
}


# ---- Helpers ----

def _compute_atr(highs, lows, closes, period=20):
    """True Range → ATR."""
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def _build_daily_sessions(df, variant_cfg):
    """Build per-trading-day session summaries for the specified variant.

    Returns a DataFrame indexed by trading date with:
        impulse_move, impulse_dir, entry_price, exit_price,
        retrace_target, rth_high, rth_low, rth_close
    """
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute

    imp_start_h, imp_start_m = variant_cfg["impulse_start"]
    imp_end_h, imp_end_m = variant_cfg["impulse_end"]
    entry_h, entry_m = variant_cfg["entry"]
    exit_h, exit_m = variant_cfg["exit"]

    records = []
    for tdate, grp in df.groupby("date"):
        # Skip weekends
        if pd.Timestamp(tdate).dayofweek >= 5:
            continue

        # Impulse start bar (open)
        start_bar = grp[
            (grp["hour"] == imp_start_h) & (grp["minute"] == imp_start_m)
        ]
        if start_bar.empty:
            continue

        # Impulse end bar (close)
        end_bar = grp[
            (grp["hour"] == imp_end_h) & (grp["minute"] == imp_end_m)
        ]
        if end_bar.empty:
            continue

        # Entry bar (open)
        entry_bar = grp[
            (grp["hour"] == entry_h) & (grp["minute"] == entry_m)
        ]
        if entry_bar.empty:
            continue

        # Exit bar (close)
        exit_bar = grp[
            (grp["hour"] == exit_h) & (grp["minute"] == exit_m)
        ]
        if exit_bar.empty:
            continue

        impulse_open = start_bar.iloc[0]["open"]
        impulse_close = end_bar.iloc[0]["close"]
        impulse_move = impulse_close - impulse_open
        impulse_dir = np.sign(impulse_move)
        impulse_mag = abs(impulse_move)

        entry_price = entry_bar.iloc[0]["open"]
        exit_price = exit_bar.iloc[0]["close"]

        # High/low between entry and exit for stop checking
        fade_window = grp[
            (grp["hour"] * 60 + grp["minute"] >= entry_h * 60 + entry_m) &
            (grp["hour"] * 60 + grp["minute"] <= exit_h * 60 + exit_m)
        ]
        window_high = fade_window["high"].max() if not fade_window.empty else np.nan
        window_low = fade_window["low"].min() if not fade_window.empty else np.nan

        # RTH bars for ATR
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

    # Rolling median of impulse magnitude
    daily["median_mag"] = daily["impulse_mag"].rolling(
        LOOKBACK, min_periods=LOOKBACK
    ).median()
    daily["impulse_ratio"] = daily["impulse_mag"] / daily["median_mag"]

    # ATR from daily RTH
    daily["atr"] = _compute_atr(
        daily["rth_high"], daily["rth_low"], daily["rth_close"], ATR_LEN
    )

    return daily


# ---- Signal Generator (standard interface) ----

def generate_signals(df, mode="both"):
    """Generate signals on 5-minute OHLCV data.

    Returns a daily-resampled DataFrame with signal/exit_signal columns.
    Uses the module-level VARIANT flag to select the falsification variant.

    Parameters
    ----------
    df : DataFrame with columns [datetime, open, high, low, close, volume]
    mode : "both", "long", or "short"
    """
    variant_cfg = _VARIANT_CONFIG[VARIANT]
    daily = _build_daily_sessions(df, variant_cfg)

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

        # Exit previous position (each trade is intraday)
        if position != 0:
            exit_signals[i] = position
            position = 0

        # Filter check (variants A/B use threshold, C does not)
        if variant_cfg["use_filter"]:
            if np.isnan(row["impulse_ratio"]) or np.isnan(row["median_mag"]):
                continue
            if row["impulse_ratio"] <= IMPULSE_THRESHOLD:
                continue

        # Fade direction: opposite of impulse
        fade_dir = -int(row["impulse_dir"])

        if mode == "long" and fade_dir != 1:
            continue
        if mode == "short" and fade_dir != -1:
            continue

        # Entry
        signals[i] = fade_dir
        position = fade_dir

        # Stop
        atr = row["atr"]
        if fade_dir == 1:
            stop_prices[i] = row["entry_price"] - SL_ATR_MULT * atr
        else:
            stop_prices[i] = row["entry_price"] + SL_ATR_MULT * atr

        # Retracement target
        retrace_amt = row["impulse_mag"] * RETRACE_PCT
        if fade_dir == 1:
            target_prices[i] = row["entry_price"] + retrace_amt
        else:
            target_prices[i] = row["entry_price"] - retrace_amt

    # Final exit
    if position != 0 and n > 0:
        exit_signals[n - 1] = position

    result = pd.DataFrame({
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

    return result
