"""Market regime detection — ATR percentile rank volatility classifier.

Labels each trading day as low / medium / high volatility based on where
the rolling ATR sits within its historical distribution.

Usage:
    from engine.regime import classify_regimes, regime_breakdown

    regimes = classify_regimes(df)  # adds 'regime' column
    breakdown = regime_breakdown(trades_df, regimes)  # per-regime metrics
"""

import numpy as np
import pandas as pd


# ── Regime Classification ─────────────────────────────────────────────────────

def classify_regimes(
    df: pd.DataFrame,
    atr_period: int = 20,
    lookback: int = 252,
    low_pct: float = 33.3,
    high_pct: float = 66.7,
) -> pd.DataFrame:
    """Classify each bar's date into a volatility regime.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV data with 'datetime', 'high', 'low', 'close' columns.
    atr_period : int
        ATR rolling window (default 20 bars).
    lookback : int
        Historical window for percentile ranking (default 252 trading days).
    low_pct : float
        Percentile threshold below which regime is 'low' (default 33.3).
    high_pct : float
        Percentile threshold above which regime is 'high' (default 66.7).

    Returns
    -------
    pd.DataFrame
        Original df with added columns:
        - 'atr': rolling ATR
        - 'atr_pctrank': percentile rank of ATR within lookback window (0-100)
        - 'regime': 'low', 'medium', or 'high'
        - '_date': date column for joining with trades
    """
    out = df.copy()
    out["_date"] = pd.to_datetime(out["datetime"]).dt.date

    # True Range
    high = out["high"].values
    low = out["low"].values
    close = out["close"].values
    tr = np.maximum(high - low,
                    np.maximum(np.abs(high - np.roll(close, 1)),
                               np.abs(low - np.roll(close, 1))))
    tr[0] = high[0] - low[0]

    # Rolling ATR
    out["_tr"] = tr
    out["atr"] = out["_tr"].rolling(atr_period, min_periods=1).mean()

    # Daily ATR (use last bar of each day)
    daily_atr = out.groupby("_date")["atr"].last()

    # Percentile rank within rolling lookback
    pct_ranks = daily_atr.rolling(lookback, min_periods=20).apply(
        lambda x: (x.iloc[-1] >= x).sum() / len(x) * 100, raw=False
    )

    # Classify
    def _label(pct):
        if pd.isna(pct):
            return "medium"  # default during warmup
        if pct <= low_pct:
            return "low"
        if pct >= high_pct:
            return "high"
        return "medium"

    daily_regime = pct_ranks.map(_label)
    daily_regime_df = pd.DataFrame({
        "_date": daily_regime.index,
        "regime": daily_regime.values,
        "atr_pctrank": pct_ranks.values,
    })

    # Map back to bars
    out = out.merge(daily_regime_df, on="_date", how="left")
    out["regime"] = out["regime"].fillna("medium")
    out["atr_pctrank"] = out["atr_pctrank"].fillna(50.0)

    out.drop(columns=["_tr"], inplace=True)
    return out


# ── Regime Breakdown for Trades ───────────────────────────────────────────────

def regime_breakdown(
    trades_df: pd.DataFrame,
    regime_df: pd.DataFrame,
    point_value: float = 5.0,
    starting_capital: float = 50_000.0,
) -> pd.DataFrame:
    """Compute performance metrics per regime bucket.

    Parameters
    ----------
    trades_df : pd.DataFrame
        Trade log with 'entry_time', 'pnl' columns.
    regime_df : pd.DataFrame
        Output of classify_regimes() with '_date' and 'regime' columns.

    Returns
    -------
    pd.DataFrame with one row per regime (low, medium, high)
        containing: trades, pf, sharpe, pnl, maxdd, wr, exp.
    """
    if trades_df.empty:
        return pd.DataFrame()

    trades = trades_df.copy()
    trades["_date"] = pd.to_datetime(trades["entry_time"]).dt.date

    # Get unique daily regime mapping
    daily_regime = regime_df.groupby("_date")["regime"].first().reset_index()
    trades = trades.merge(daily_regime, on="_date", how="left")
    trades["regime"] = trades["regime"].fillna("medium")

    rows = []
    for regime in ["low", "medium", "high"]:
        subset = trades[trades["regime"] == regime]
        if subset.empty:
            rows.append({
                "regime": regime, "trades": 0, "pf": 0, "sharpe": 0,
                "pnl": 0, "maxdd": 0, "wr": 0, "exp": 0,
                "avg_pnl": 0, "pct_of_trades": 0,
            })
            continue

        pnl = subset["pnl"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        gross_profit = wins.sum() if len(wins) else 0
        gross_loss = abs(losses.sum()) if len(losses) else 0
        pf = gross_profit / gross_loss if gross_loss > 0 else (100.0 if gross_profit > 0 else 0)

        # Sharpe from daily PnL
        daily_pnl = subset.groupby("_date")["pnl"].sum()
        if len(daily_pnl) > 1 and daily_pnl.std() > 0:
            sharpe = daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)
        else:
            sharpe = 0.0

        # MaxDD
        equity = starting_capital + np.cumsum(pnl.values)
        peak = np.maximum.accumulate(equity)
        maxdd = (peak - equity).max()

        rows.append({
            "regime": regime,
            "trades": len(subset),
            "pf": round(pf, 3),
            "sharpe": round(sharpe, 4),
            "pnl": round(pnl.sum(), 2),
            "maxdd": round(maxdd, 2),
            "wr": round(len(wins) / len(pnl) * 100, 1),
            "exp": round(pnl.mean(), 2),
            "avg_pnl": round(pnl.mean(), 2),
            "pct_of_trades": round(len(subset) / len(trades) * 100, 1),
        })

    return pd.DataFrame(rows)
