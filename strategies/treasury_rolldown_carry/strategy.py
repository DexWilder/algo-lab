"""Treasury Rolldown Carry Spread — Rank tenors by carry, trade the spread.

Tests whether APPROXIMATE rates carry from carry_lookup.py produces a
useful spread signal. This is a carry-factor strategy, not momentum.

Logic:
  - Load daily prices for ZN, ZF, ZB
  - At each monthly rebalance, compute carry scores via carry_lookup
  - Rank tenors by carry score
  - Long the highest-carry tenor, short the lowest-carry tenor
  - Middle tenor stays flat
  - Two sizing variants:
    EQUAL_NOTIONAL: 1 contract per side (baseline)
    DV01_APPROX: rough duration-weight to reduce directional exposure

Signal quality: APPROXIMATE (duration-weighted 60-day return, not true
yield/rolldown). Honestly labeled — this is a test of whether that
approximation is good enough to create a tradeable spread signal.

Designed for: ZN, ZF, ZB as a 3-tenor spread.
PLATFORM-AGNOSTIC: Pure signal logic only.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ---- Parameters ----

CARRY_LOOKBACK = 60          # Days for carry score (matches carry_lookup default)
SIZING_MODE = "equal"        # "equal" or "dv01" — toggle for variant testing
USE_STOP = False             # No stop on spread strategies

# DV01 approximations for rough duration weighting
# Units: dollar price change per 1 basis point yield change per contract
DV01 = {
    "ZN": 78.0,    # 10-Year Note
    "ZF": 47.0,    # 5-Year Note
    "ZB": 195.0,   # 30-Year Bond
}

TENORS = ["ZN", "ZF", "ZB"]
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

TICK_SIZE = 0.015625  # ZN default, overridden per asset in spread PnL


# ---- Helpers ----

def _resample_daily(df):
    """Resample 5m bars to daily OHLCV."""
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["date"] = df["datetime"].dt.date
    daily = df.groupby("date").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).reset_index()
    daily["datetime"] = pd.to_datetime(daily["date"])
    return daily


def _load_tenor_data(tenor):
    """Load and resample a single tenor's data to daily bars."""
    path = DATA_DIR / f"{tenor}_5m.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    time_diff = df["datetime"].diff().median()
    if time_diff < pd.Timedelta(hours=1):
        return _resample_daily(df)
    return df


def _compute_carry_score(close_series, maturity_years, lookback=60):
    """Compute APPROXIMATE carry score for a tenor.

    Duration-weighted 60-day trailing return. Same formula as
    engine/carry_lookup.py _rates_carry_score() but inline here
    to avoid import dependency issues in batch testing.

    Returns a Series of carry scores aligned to the close series index.
    """
    trailing_ret = close_series.pct_change(lookback)
    duration_factor = maturity_years / 10.0
    return trailing_ret * duration_factor


MATURITY = {"ZN": 10, "ZF": 5, "ZB": 30}
POINT_VALUE = {"ZN": 1000.0, "ZF": 1000.0, "ZB": 1000.0}


# ---- Spread Signal Generator ----

def generate_spread_signals():
    """Generate spread signals across all three tenors.

    This is the primary function for this strategy. It loads all three
    tenor datasets, computes the carry ranking, and produces a spread
    trade table.

    Returns a DataFrame with columns:
        date, long_tenor, short_tenor, flat_tenor,
        long_carry, short_carry, spread_carry,
        long_return, short_return, spread_pnl,
        sizing_mode, rank_changed
    """
    # Load all three tenors
    tenor_data = {}
    for t in TENORS:
        daily = _load_tenor_data(t)
        if daily is None:
            raise ValueError(f"Cannot load data for {t}")
        daily = daily.set_index("date")
        tenor_data[t] = daily

    # Align on common dates
    common_dates = sorted(
        set(tenor_data["ZN"].index) &
        set(tenor_data["ZF"].index) &
        set(tenor_data["ZB"].index)
    )

    # Build aligned close price DataFrame
    closes = pd.DataFrame({
        t: tenor_data[t].loc[common_dates, "close"]
        for t in TENORS
    }, index=common_dates)

    # Compute carry scores
    carry_scores = pd.DataFrame({
        t: _compute_carry_score(closes[t], MATURITY[t], CARRY_LOOKBACK)
        for t in TENORS
    }, index=common_dates)

    # Identify month-end rebalance dates
    dates_dt = pd.to_datetime(closes.index)
    months = dates_dt.to_period("M")
    is_month_end = months != pd.Series(months).shift(-1).values

    # Build trade log
    records = []
    prev_long = None
    prev_short = None

    for i, date in enumerate(common_dates):
        if i < CARRY_LOOKBACK + 1:
            continue
        if not is_month_end[i]:
            continue

        # Get carry scores for this date
        scores = {t: carry_scores.loc[date, t] for t in TENORS}

        # Skip if any score is NaN
        if any(np.isnan(v) for v in scores.values()):
            continue

        # Rank: highest carry = long, lowest = short
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        long_tenor = ranked[0][0]
        flat_tenor = ranked[1][0]
        short_tenor = ranked[2][0]

        rank_changed = (long_tenor != prev_long) or (short_tenor != prev_short)
        prev_long = long_tenor
        prev_short = short_tenor

        # Compute next-month return for each leg
        # Find the next month-end (or end of data)
        next_rebal_idx = None
        for j in range(i + 1, len(common_dates)):
            if is_month_end[j]:
                next_rebal_idx = j
                break
        if next_rebal_idx is None:
            next_rebal_idx = len(common_dates) - 1

        entry_date = common_dates[i]
        exit_date = common_dates[next_rebal_idx]

        entry_long = closes.loc[entry_date, long_tenor]
        exit_long = closes.loc[exit_date, long_tenor]
        entry_short = closes.loc[entry_date, short_tenor]
        exit_short = closes.loc[exit_date, short_tenor]

        long_return = (exit_long - entry_long) / entry_long
        short_return = (exit_short - entry_short) / entry_short

        # PnL computation
        long_pv = POINT_VALUE[long_tenor]
        short_pv = POINT_VALUE[short_tenor]

        if SIZING_MODE == "dv01":
            # Rough DV01 normalization: size inversely to DV01
            # Normalize to ZN as base (DV01=78)
            base_dv01 = DV01["ZN"]
            long_contracts = base_dv01 / DV01[long_tenor]
            short_contracts = base_dv01 / DV01[short_tenor]
        else:
            long_contracts = 1.0
            short_contracts = 1.0

        long_pnl = (exit_long - entry_long) * long_pv * long_contracts
        short_pnl = -(exit_short - entry_short) * short_pv * short_contracts
        spread_pnl = long_pnl + short_pnl

        records.append({
            "entry_date": entry_date,
            "exit_date": exit_date,
            "long_tenor": long_tenor,
            "short_tenor": short_tenor,
            "flat_tenor": flat_tenor,
            "long_carry": scores[long_tenor],
            "short_carry": scores[short_tenor],
            "spread_carry": scores[long_tenor] - scores[short_tenor],
            "long_pnl": round(long_pnl, 2),
            "short_pnl": round(short_pnl, 2),
            "spread_pnl": round(spread_pnl, 2),
            "sizing_mode": SIZING_MODE,
            "long_contracts": round(long_contracts, 2),
            "short_contracts": round(short_contracts, 2),
            "rank_changed": rank_changed,
        })

    return pd.DataFrame(records)


# ---- Standard Interface (for single-asset batch_first_pass compatibility) ----

def generate_signals(df, asset=None, mode="both"):
    """Standard interface for batch_first_pass compatibility.

    For this spread strategy, the 'asset' parameter selects which tenor
    to report signals for (the spread still uses all three internally).
    The signal is +1 when this tenor is the long leg, -1 when it's the
    short leg, and 0 when it's the flat leg.

    This allows batch_first_pass to evaluate each tenor's contribution
    independently while the actual spread logic runs across all three.
    """
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Resample to daily
    if len(df) > 0:
        time_diff = df["datetime"].diff().median()
        if time_diff < pd.Timedelta(hours=1):
            daily = _resample_daily(df)
        else:
            daily = df.copy()
    else:
        return df

    n = len(daily)
    if n < CARRY_LOOKBACK + 30:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Run the full spread logic
    try:
        spread_df = generate_spread_signals()
    except Exception:
        daily["signal"] = 0
        daily["exit_signal"] = 0
        daily["stop_price"] = np.nan
        daily["target_price"] = np.nan
        return daily

    # Map spread assignments back to daily bars for this asset
    if not asset:
        asset = "ZN"  # default

    daily_dates = daily["date"] if "date" in daily.columns else daily["datetime"].dt.date
    signals = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)

    # Build a date→signal map from spread results
    date_signal = {}
    for _, row in spread_df.iterrows():
        entry = row["entry_date"]
        if row["long_tenor"] == asset:
            date_signal[entry] = 1
        elif row["short_tenor"] == asset:
            date_signal[entry] = -1
        else:
            date_signal[entry] = 0

    # Apply signals to daily bars
    position = 0
    for i in range(n):
        d = daily_dates.iloc[i] if hasattr(daily_dates, "iloc") else daily_dates[i]
        if d in date_signal:
            new_pos = date_signal[d]
            if new_pos != position:
                if position != 0:
                    exit_sigs[i] = position
                if new_pos != 0:
                    signals[i] = new_pos
                position = new_pos

    daily["signal"] = signals
    daily["exit_signal"] = exit_sigs
    daily["stop_price"] = np.nan
    daily["target_price"] = np.nan

    drop = ["date"]
    daily.drop(columns=[c for c in drop if c in daily.columns], inplace=True, errors="ignore")
    return daily
