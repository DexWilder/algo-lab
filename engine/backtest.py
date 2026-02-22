"""Backtest runner — event-driven fill-at-next-open engine."""

import pandas as pd
import numpy as np


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    mode: str = "both",
    point_value: float = 5.0,
    contracts: int = 1,
    starting_capital: float = 50_000.0,
) -> dict:
    """Run a backtest on signal data.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV data conforming to the data contract.
    signals : pd.DataFrame
        DataFrame with 'signal' and 'exit_signal' columns.
    mode : str
        One of 'long', 'short', or 'both'.
    point_value : float
        Dollar value per point (MES=5.0, ES=50.0).
    contracts : int
        Number of contracts per trade.
    starting_capital : float
        Starting account balance.

    Returns
    -------
    dict
        Keys: trades_df, equity_curve, stats.
    """
    # --- Merge signals onto price data defensively ---
    merged = df[["datetime", "open", "high", "low", "close"]].copy()
    merged["signal"] = signals["signal"].fillna(0).astype(int).values
    merged["exit_signal"] = signals["exit_signal"].fillna(0).astype(int).values
    merged = merged.reset_index(drop=True)

    # --- Mode filtering: zero out irrelevant signals ---
    if mode == "long":
        # No short entries (signal=-1) or exit-short (exit_signal=-1)
        merged.loc[merged["signal"] == -1, "signal"] = 0
        merged.loc[merged["exit_signal"] == -1, "exit_signal"] = 0
    elif mode == "short":
        # No long entries (signal=1) or exit-long (exit_signal=1)
        merged.loc[merged["signal"] == 1, "signal"] = 0
        merged.loc[merged["exit_signal"] == 1, "exit_signal"] = 0

    n = len(merged)
    opens = merged["open"].values
    closes = merged["close"].values
    datetimes = merged["datetime"].values
    sigs = merged["signal"].values
    exits = merged["exit_signal"].values

    # --- State machine ---
    position = 0        # 0=flat, 1=long, -1=short
    entry_price = 0.0
    entry_time = None
    pending_action = None  # ("open_long"|"open_short"|"close"|"reverse_long"|"reverse_short", bar_index)

    trades = []
    equity = np.full(n, starting_capital, dtype=float)
    unrealized = 0.0
    realized_total = 0.0

    for i in range(n):
        fill_price = opens[i]

        # --- Step 1: Execute pending fill at this bar's open ---
        if pending_action is not None:
            action = pending_action
            pending_action = None

            if action == "open_long":
                position = 1
                entry_price = fill_price
                entry_time = datetimes[i]

            elif action == "open_short":
                position = -1
                entry_price = fill_price
                entry_time = datetimes[i]

            elif action == "close":
                pnl = _calc_pnl(position, entry_price, fill_price,
                                point_value, contracts)
                trades.append(_make_trade(
                    entry_time, datetimes[i],
                    "long" if position == 1 else "short",
                    entry_price, fill_price, pnl, contracts,
                ))
                realized_total += pnl
                position = 0
                entry_price = 0.0
                entry_time = None

            elif action == "reverse_long":
                # Close short, then open long at same price
                pnl = _calc_pnl(position, entry_price, fill_price,
                                point_value, contracts)
                trades.append(_make_trade(
                    entry_time, datetimes[i],
                    "short", entry_price, fill_price, pnl, contracts,
                ))
                realized_total += pnl
                position = 1
                entry_price = fill_price
                entry_time = datetimes[i]

            elif action == "reverse_short":
                # Close long, then open short at same price
                pnl = _calc_pnl(position, entry_price, fill_price,
                                point_value, contracts)
                trades.append(_make_trade(
                    entry_time, datetimes[i],
                    "long", entry_price, fill_price, pnl, contracts,
                ))
                realized_total += pnl
                position = -1
                entry_price = fill_price
                entry_time = datetimes[i]

        # --- Step 2: Mark-to-market equity at this bar's close ---
        if position == 1:
            unrealized = (closes[i] - entry_price) * point_value * contracts
        elif position == -1:
            unrealized = (entry_price - closes[i]) * point_value * contracts
        else:
            unrealized = 0.0

        equity[i] = starting_capital + realized_total + unrealized

        # --- Step 3: Read signals, set pending action for next bar ---
        # Skip signals on the last bar (no next bar to fill)
        if i >= n - 1:
            continue

        sig = sigs[i]
        ext = exits[i]

        if position == 0:
            # Flat: look for entry signals
            if sig == 1:
                pending_action = "open_long"
            elif sig == -1:
                pending_action = "open_short"

        elif position == 1:
            # Long: check for reversal first, then exit
            if sig == -1:
                pending_action = "reverse_short"
            elif ext == 1:
                pending_action = "close"

        elif position == -1:
            # Short: check for reversal first, then exit
            if sig == 1:
                pending_action = "reverse_long"
            elif ext == -1:
                pending_action = "close"

    # --- Force close any open position at last bar's close ---
    if position != 0 and n > 0:
        close_price = closes[-1]
        pnl = _calc_pnl(position, entry_price, close_price,
                         point_value, contracts)
        trades.append(_make_trade(
            entry_time, datetimes[-1],
            "long" if position == 1 else "short",
            entry_price, close_price, pnl, contracts,
        ))
        realized_total += pnl
        equity[-1] = starting_capital + realized_total

    # --- Build output ---
    trades_df = pd.DataFrame(trades, columns=[
        "entry_time", "exit_time", "side", "entry_price",
        "exit_price", "pnl", "contracts",
    ])

    equity_curve = pd.Series(equity, index=merged.index, name="equity")

    stats = {
        "total_trades": len(trades),
        "starting_capital": starting_capital,
        "ending_capital": equity[-1] if n > 0 else starting_capital,
        "total_pnl": realized_total,
        "point_value": point_value,
        "contracts": contracts,
        "mode": mode,
    }

    return {"trades_df": trades_df, "equity_curve": equity_curve, "stats": stats}


def _calc_pnl(position, entry_price, exit_price, point_value, contracts):
    """Calculate PnL for a closed trade."""
    if position == 1:
        return (exit_price - entry_price) * point_value * contracts
    else:  # position == -1
        return (entry_price - exit_price) * point_value * contracts


def _make_trade(entry_time, exit_time, side, entry_price, exit_price, pnl, contracts):
    """Return a trade tuple matching trades_df column order."""
    return (entry_time, exit_time, side, entry_price, exit_price, round(pnl, 2), contracts)
