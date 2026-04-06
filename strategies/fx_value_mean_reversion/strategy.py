"""FX Relative Value Mean-Reversion Basket — first VALUE strategy for FQL.

Cross-sectional FX mean reversion: at each month-end, compute the
cumulative return of each currency future relative to the basket average.
Short currencies above average (overvalued), long currencies below
(undervalued). Position size proportional to deviation magnitude.

This is a VALUE strategy, not MOMENTUM or CARRY. The signal is relative
cheapness/richness measured by price deviation from a multi-currency
average — the idea is that extreme deviations revert.

Source: Quantpedia — "How to Build Mean Reversion Strategies in Currencies"
Harvest note: 2026-04-06_02_fx_mean_reversion_linear_anchor.md

Assets: 6J (JPY), 6E (EUR), 6B (GBP) — all available in FQL data.
Rebalance: Monthly (last trading day).
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Parameters ──
LOOKBACK = 60           # Trading days for cumulative return calculation
REBALANCE = "monthly"   # Last trading day of each month
MIN_DEVIATION = 0.005   # Minimum deviation from average to trade (0.5%)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"
CURRENCIES = ["6J", "6E", "6B"]

# Point values for PnL calculation
POINT_VALUE = {
    "6J": 125000.0,   # JPY futures: 12.5M yen per contract
    "6E": 125000.0,   # EUR futures: 125K EUR per contract
    "6B": 62500.0,    # GBP futures: 62.5K GBP per contract
}


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


def _load_currency_data():
    """Load and resample all currency futures to daily."""
    data = {}
    for ccy in CURRENCIES:
        path = DATA_DIR / f"{ccy}_5m.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df["datetime"] = pd.to_datetime(df["datetime"])
        daily = _resample_daily(df)
        data[ccy] = daily.set_index("date")
    return data


def generate_spread_signals():
    """Generate cross-sectional mean-reversion signals.

    Returns a DataFrame with columns:
        date, positions (dict of ccy→weight), basket_return, spread_pnl
    """
    data = _load_currency_data()
    if len(data) < 2:
        return pd.DataFrame()

    # Align on common dates
    common_dates = sorted(
        set.intersection(*[set(d.index) for d in data.values()])
    )

    # Build close price DataFrame
    closes = pd.DataFrame({
        ccy: data[ccy].loc[common_dates, "close"]
        for ccy in CURRENCIES if ccy in data
    }, index=common_dates)

    # Compute cumulative returns (rolling LOOKBACK-day return)
    cum_returns = closes.pct_change(LOOKBACK)

    # Identify month-end rebalance dates
    dates_dt = pd.to_datetime(closes.index)
    months = dates_dt.to_period("M")
    is_month_end = months != pd.Series(months).shift(-1).values

    records = []

    for i, date in enumerate(common_dates):
        if i < LOOKBACK + 1:
            continue
        if not is_month_end[i]:
            continue

        # Get cumulative returns for each currency
        returns = {ccy: cum_returns.loc[date, ccy] for ccy in closes.columns}

        # Skip if any NaN
        if any(np.isnan(v) for v in returns.values()):
            continue

        # Compute basket average
        avg_return = np.mean(list(returns.values()))

        # Compute deviations from average
        deviations = {ccy: ret - avg_return for ccy, ret in returns.items()}

        # Position: short overvalued (positive deviation), long undervalued (negative)
        # Weight proportional to deviation magnitude
        total_abs_dev = sum(abs(d) for d in deviations.values())
        if total_abs_dev < MIN_DEVIATION * len(deviations):
            continue  # Deviations too small to trade

        positions = {}
        for ccy, dev in deviations.items():
            # Negative deviation = undervalued = long
            # Positive deviation = overvalued = short
            weight = -dev / total_abs_dev if total_abs_dev > 0 else 0
            positions[ccy] = round(weight, 4)

        # Compute next-month PnL
        next_rebal_idx = None
        for j in range(i + 1, len(common_dates)):
            if is_month_end[j]:
                next_rebal_idx = j
                break
        if next_rebal_idx is None:
            next_rebal_idx = len(common_dates) - 1

        entry_date = common_dates[i]
        exit_date = common_dates[next_rebal_idx]

        # PnL per currency
        spread_pnl = 0
        for ccy in closes.columns:
            entry_price = closes.loc[entry_date, ccy]
            exit_price = closes.loc[exit_date, ccy]
            ccy_return = (exit_price - entry_price) / entry_price
            # PnL = weight * return * notional (simplified to 1 contract equivalent)
            spread_pnl += positions[ccy] * ccy_return * POINT_VALUE.get(ccy, 100000)

        records.append({
            "entry_date": entry_date,
            "exit_date": exit_date,
            "positions": positions,
            "avg_return": round(avg_return, 6),
            "spread_pnl": round(spread_pnl, 2),
        })

    return pd.DataFrame(records)


def generate_signals(df, asset=None, mode="both"):
    """Standard interface for batch_first_pass compatibility.

    For this cross-sectional strategy, the 'asset' parameter selects
    which currency to report signals for. The signal is the position
    weight for that currency at each rebalance.
    """
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Resample to daily
    time_diff = df["datetime"].diff().median()
    if time_diff < pd.Timedelta(hours=1):
        daily = _resample_daily(df)
    else:
        daily = df.copy()

    n = len(daily)
    if n < LOOKBACK + 30:
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

    if not asset:
        asset = "6E"

    daily_dates = daily["date"] if "date" in daily.columns else daily["datetime"].dt.date
    signals = np.zeros(n, dtype=int)
    exit_signals = np.zeros(n, dtype=int)

    # Map spread positions to daily signals for this asset
    position = 0
    for _, row in spread_df.iterrows():
        entry = row["entry_date"]
        pos = row["positions"].get(asset, 0)
        if pos > 0:
            new_pos = 1
        elif pos < 0:
            new_pos = -1
        else:
            new_pos = 0

        # Find the daily bar matching this date
        for idx in range(n):
            d = daily_dates.iloc[idx] if hasattr(daily_dates, "iloc") else daily_dates[idx]
            if d == entry:
                if new_pos != position:
                    if position != 0:
                        exit_signals[idx] = position
                    if new_pos != 0:
                        signals[idx] = new_pos
                    position = new_pos
                break

    daily["signal"] = signals
    daily["exit_signal"] = exit_signals
    daily["stop_price"] = np.nan
    daily["target_price"] = np.nan

    drop = ["date"]
    daily.drop(columns=[c for c in drop if c in daily.columns], inplace=True, errors="ignore")
    return daily
