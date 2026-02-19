"""Metric computation for backtest results."""

import pandas as pd
import numpy as np


def compute_metrics(trades_df: pd.DataFrame) -> dict:
    """Compute performance metrics from a trade log.

    Parameters
    ----------
    trades_df : pd.DataFrame
        Trade log with columns: entry_time, exit_time, side, entry_price,
        exit_price, pnl, contracts.

    Returns
    -------
    dict
        Keys: roi, max_drawdown, sharpe, expected_value, trades.
    """
    if trades_df.empty:
        return {
            "roi": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "expected_value": 0.0,
            "trades": 0,
        }

    pnl = trades_df["pnl"]
    cumulative = pnl.cumsum()

    # ROI as percentage of starting capital ($50,000 for Apex 50K)
    starting_capital = 50_000
    roi = (cumulative.iloc[-1] / starting_capital) * 100

    # Max drawdown
    running_max = cumulative.cummax()
    drawdown = running_max - cumulative
    max_drawdown = drawdown.max()

    # Sharpe ratio (annualized, assuming 5m bars ~ 78 bars/day, 252 days/year)
    if pnl.std() != 0:
        sharpe = (pnl.mean() / pnl.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Expected value per trade
    expected_value = pnl.mean()

    return {
        "roi": round(roi, 4),
        "max_drawdown": round(max_drawdown, 2),
        "sharpe": round(sharpe, 4),
        "expected_value": round(expected_value, 2),
        "trades": len(trades_df),
    }
