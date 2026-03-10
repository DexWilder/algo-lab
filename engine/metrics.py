"""Metric computation for backtest results.

Contains both basic metrics (compute_metrics) and the full extended metrics
suite (compute_extended_metrics) used by all research scripts.
"""

import pandas as pd
import numpy as np


def compute_metrics(trades_df: pd.DataFrame) -> dict:
    """Compute basic performance metrics from a trade log.

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


# ── Extended Metrics (canonical location) ─────────────────────────────────

def compute_extended_metrics(
    trades_df: pd.DataFrame,
    equity_curve: pd.Series,
    point_value: float,
    starting_capital: float = 50_000.0,
) -> dict:
    """Compute full performance report metrics.

    Returns dict with: profit_factor, sharpe, expectancy, max_drawdown,
    win_rate, trade_count, avg_R, total_pnl, avg_win, avg_loss,
    best_trade, worst_trade, max_consecutive_wins, max_consecutive_losses,
    long_trades, short_trades, long_win_rate, short_win_rate,
    session_distribution, signal_type_distribution.
    """
    if trades_df.empty:
        return _empty_metrics()

    pnl = trades_df["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]

    # Profit factor
    gross_profit = wins.sum() if len(wins) > 0 else 0
    gross_loss = abs(losses.sum()) if len(losses) > 0 else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0

    # Win rate
    win_rate = len(wins) / len(pnl) if len(pnl) > 0 else 0

    # Sharpe (annualized — daily approximation)
    trades_with_dates = trades_df.copy()
    trades_with_dates["date"] = pd.to_datetime(trades_with_dates["exit_time"]).dt.date
    daily_pnl = trades_with_dates.groupby("date")["pnl"].sum()
    if len(daily_pnl) > 1 and daily_pnl.std() > 0:
        sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    # Expectancy (expected value per trade)
    expectancy = pnl.mean()

    # Max drawdown (from equity curve)
    eq = equity_curve.values
    running_max = np.maximum.accumulate(eq)
    drawdown = running_max - eq
    max_drawdown = drawdown.max()
    max_drawdown_pct = (max_drawdown / running_max[np.argmax(drawdown)]) * 100 if running_max[np.argmax(drawdown)] > 0 else 0

    # Avg R (average PnL / average loss magnitude as risk unit)
    avg_loss_abs = abs(losses.mean()) if len(losses) > 0 else 0
    avg_r = pnl.mean() / avg_loss_abs if avg_loss_abs > 0 else 0

    # Consecutive streaks
    max_consec_wins, max_consec_losses = _consecutive_streaks(pnl)

    # Side breakdown
    long_trades = trades_df[trades_df["side"] == "long"]
    short_trades = trades_df[trades_df["side"] == "short"]
    long_win_rate = (long_trades["pnl"] > 0).mean() if len(long_trades) > 0 else 0
    short_win_rate = (short_trades["pnl"] > 0).mean() if len(short_trades) > 0 else 0

    # Session distribution (hour of entry)
    entry_hours = pd.to_datetime(trades_df["entry_time"]).dt.hour
    session_dist = entry_hours.value_counts().sort_index().to_dict()

    # Trade duration (in bars — 5-minute bars)
    entry_times = pd.to_datetime(trades_df["entry_time"])
    exit_times = pd.to_datetime(trades_df["exit_time"])
    durations = (exit_times - entry_times).dt.total_seconds() / 300  # 5-min bars
    median_duration_bars = float(durations.median()) if len(durations) > 0 else 0
    avg_duration_bars = float(durations.mean()) if len(durations) > 0 else 0

    # ROI
    total_pnl = pnl.sum()
    roi = (total_pnl / starting_capital) * 100

    return {
        "profit_factor": round(profit_factor, 3),
        "sharpe": round(sharpe, 4),
        "expectancy": round(expectancy, 2),
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "win_rate": round(win_rate, 4),
        "trade_count": len(trades_df),
        "avg_R": round(avg_r, 3),
        "total_pnl": round(total_pnl, 2),
        "roi_pct": round(roi, 2),
        "avg_win": round(wins.mean(), 2) if len(wins) > 0 else 0,
        "avg_loss": round(losses.mean(), 2) if len(losses) > 0 else 0,
        "best_trade": round(pnl.max(), 2),
        "worst_trade": round(pnl.min(), 2),
        "max_consecutive_wins": max_consec_wins,
        "max_consecutive_losses": max_consec_losses,
        "long_trades": len(long_trades),
        "short_trades": len(short_trades),
        "long_win_rate": round(long_win_rate, 4),
        "short_win_rate": round(short_win_rate, 4),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(-gross_loss, 2),
        "session_distribution": session_dist,
        "trading_days": len(daily_pnl),
        "avg_trades_per_day": round(len(trades_df) / max(len(daily_pnl), 1), 2),
        "median_trade_duration_bars": round(median_duration_bars, 1),
        "avg_trade_duration_bars": round(avg_duration_bars, 1),
    }


def _consecutive_streaks(pnl: pd.Series) -> tuple[int, int]:
    """Compute max consecutive wins and losses."""
    max_wins = 0
    max_losses = 0
    curr_wins = 0
    curr_losses = 0

    for p in pnl:
        if p > 0:
            curr_wins += 1
            curr_losses = 0
            max_wins = max(max_wins, curr_wins)
        elif p < 0:
            curr_losses += 1
            curr_wins = 0
            max_losses = max(max_losses, curr_losses)
        else:
            curr_wins = 0
            curr_losses = 0

    return max_wins, max_losses


def _empty_metrics() -> dict:
    return {
        "profit_factor": 0, "sharpe": 0, "expectancy": 0,
        "max_drawdown": 0, "max_drawdown_pct": 0, "win_rate": 0,
        "trade_count": 0, "avg_R": 0, "total_pnl": 0, "roi_pct": 0,
        "avg_win": 0, "avg_loss": 0, "best_trade": 0, "worst_trade": 0,
        "max_consecutive_wins": 0, "max_consecutive_losses": 0,
        "long_trades": 0, "short_trades": 0,
        "long_win_rate": 0, "short_win_rate": 0,
        "gross_profit": 0, "gross_loss": 0,
        "session_distribution": {}, "trading_days": 0,
        "avg_trades_per_day": 0,
        "median_trade_duration_bars": 0,
        "avg_trade_duration_bars": 0,
    }
