"""Backtest runner — event-driven fill-at-next-open engine.

Supports configurable transaction costs (commission + slippage).
"""

import pandas as pd
import numpy as np


# ── Symbol defaults for micro futures ─────────────────────────────────────────

SYMBOL_DEFAULTS = {
    "MES": {"commission_per_side": 0.62, "tick_size": 0.25, "slippage_ticks": 1},
    "MNQ": {"commission_per_side": 0.62, "tick_size": 0.25, "slippage_ticks": 1},
    "MGC": {"commission_per_side": 0.62, "tick_size": 0.10, "slippage_ticks": 1},
    "ES":  {"commission_per_side": 1.24, "tick_size": 0.25, "slippage_ticks": 1},
    "NQ":  {"commission_per_side": 1.24, "tick_size": 0.25, "slippage_ticks": 1},
    "GC":  {"commission_per_side": 1.24, "tick_size": 0.10, "slippage_ticks": 1},
}


def get_cost_params(symbol=None, commission_per_side=None, slippage_ticks=None, tick_size=None):
    """Resolve transaction cost parameters from symbol defaults + overrides."""
    defaults = SYMBOL_DEFAULTS.get(symbol, {}) if symbol else {}
    return {
        "commission_per_side": commission_per_side if commission_per_side is not None else defaults.get("commission_per_side", 0.0),
        "slippage_ticks": slippage_ticks if slippage_ticks is not None else defaults.get("slippage_ticks", 0),
        "tick_size": tick_size if tick_size is not None else defaults.get("tick_size", 0.25),
    }


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    mode: str = "both",
    point_value: float = 5.0,
    contracts: int = 1,
    starting_capital: float = 50_000.0,
    symbol: str = None,
    commission_per_side: float = None,
    slippage_ticks: int = None,
    tick_size: float = None,
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
    symbol : str, optional
        Symbol name (e.g. 'MES') to load default cost params.
    commission_per_side : float, optional
        Commission per contract per side in dollars. Overrides symbol default.
    slippage_ticks : int, optional
        Number of ticks of adverse slippage per fill. Overrides symbol default.
    tick_size : float, optional
        Price value of one tick. Overrides symbol default.

    Returns
    -------
    dict
        Keys: trades_df, equity_curve, stats.
    """
    # --- Resolve cost parameters ---
    costs = get_cost_params(symbol, commission_per_side, slippage_ticks, tick_size)
    comm = costs["commission_per_side"]
    slip_ticks = costs["slippage_ticks"]
    t_size = costs["tick_size"]
    slippage_points = slip_ticks * t_size

    # Round-trip commission per contract
    rt_commission = comm * 2 * contracts

    # --- Merge signals onto price data defensively ---
    merged = df[["datetime", "open", "high", "low", "close"]].copy()
    merged["signal"] = signals["signal"].fillna(0).astype(int).values
    merged["exit_signal"] = signals["exit_signal"].fillna(0).astype(int).values
    merged = merged.reset_index(drop=True)

    # --- Mode filtering: zero out irrelevant signals ---
    if mode == "long":
        merged.loc[merged["signal"] == -1, "signal"] = 0
        merged.loc[merged["exit_signal"] == -1, "exit_signal"] = 0
    elif mode == "short":
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
    pending_action = None

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
                # Adverse slippage: buy higher
                entry_price = fill_price + slippage_points
                entry_time = datetimes[i]

            elif action == "open_short":
                position = -1
                # Adverse slippage: sell lower
                entry_price = fill_price - slippage_points
                entry_time = datetimes[i]

            elif action == "close":
                # Adverse slippage on exit
                if position == 1:
                    exit_fill = fill_price - slippage_points  # sell lower
                else:
                    exit_fill = fill_price + slippage_points  # buy higher
                pnl = _calc_pnl(position, entry_price, exit_fill,
                                point_value, contracts) - rt_commission
                trades.append(_make_trade(
                    entry_time, datetimes[i],
                    "long" if position == 1 else "short",
                    entry_price, exit_fill, pnl, contracts,
                ))
                realized_total += pnl
                position = 0
                entry_price = 0.0
                entry_time = None

            elif action == "reverse_long":
                # Close short with adverse slippage (buy higher)
                exit_fill = fill_price + slippage_points
                pnl = _calc_pnl(position, entry_price, exit_fill,
                                point_value, contracts) - rt_commission
                trades.append(_make_trade(
                    entry_time, datetimes[i],
                    "short", entry_price, exit_fill, pnl, contracts,
                ))
                realized_total += pnl
                # Open long with adverse slippage (buy higher)
                position = 1
                entry_price = fill_price + slippage_points
                entry_time = datetimes[i]

            elif action == "reverse_short":
                # Close long with adverse slippage (sell lower)
                exit_fill = fill_price - slippage_points
                pnl = _calc_pnl(position, entry_price, exit_fill,
                                point_value, contracts) - rt_commission
                trades.append(_make_trade(
                    entry_time, datetimes[i],
                    "long", entry_price, exit_fill, pnl, contracts,
                ))
                realized_total += pnl
                # Open short with adverse slippage (sell lower)
                position = -1
                entry_price = fill_price - slippage_points
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
        if i >= n - 1:
            continue

        sig = sigs[i]
        ext = exits[i]

        if position == 0:
            if sig == 1:
                pending_action = "open_long"
            elif sig == -1:
                pending_action = "open_short"

        elif position == 1:
            if sig == -1:
                pending_action = "reverse_short"
            elif ext == 1:
                pending_action = "close"

        elif position == -1:
            if sig == 1:
                pending_action = "reverse_long"
            elif ext == -1:
                pending_action = "close"

    # --- Force close any open position at last bar's close ---
    if position != 0 and n > 0:
        close_price = closes[-1]
        if position == 1:
            exit_fill = close_price - slippage_points
        else:
            exit_fill = close_price + slippage_points
        pnl = _calc_pnl(position, entry_price, exit_fill,
                         point_value, contracts) - rt_commission
        trades.append(_make_trade(
            entry_time, datetimes[-1],
            "long" if position == 1 else "short",
            entry_price, exit_fill, pnl, contracts,
        ))
        realized_total += pnl
        equity[-1] = starting_capital + realized_total

    # --- Build output ---
    trades_df = pd.DataFrame(trades, columns=[
        "entry_time", "exit_time", "side", "entry_price",
        "exit_price", "pnl", "contracts",
    ])

    equity_curve = pd.Series(equity, index=merged.index, name="equity")

    total_commission = rt_commission * len(trades)
    total_slippage = slippage_points * point_value * contracts * 2 * len(trades)

    stats = {
        "total_trades": len(trades),
        "starting_capital": starting_capital,
        "ending_capital": equity[-1] if n > 0 else starting_capital,
        "total_pnl": realized_total,
        "point_value": point_value,
        "contracts": contracts,
        "mode": mode,
        "costs": {
            "commission_per_side": comm,
            "slippage_ticks": slip_ticks,
            "tick_size": t_size,
            "total_commission": round(total_commission, 2),
            "total_slippage": round(total_slippage, 2),
            "total_friction": round(total_commission + total_slippage, 2),
        },
    }

    return {"trades_df": trades_df, "equity_curve": equity_curve, "stats": stats}


def _calc_pnl(position, entry_price, exit_price, point_value, contracts):
    """Calculate PnL for a closed trade (before commission)."""
    if position == 1:
        return (exit_price - entry_price) * point_value * contracts
    else:  # position == -1
        return (entry_price - exit_price) * point_value * contracts


def _make_trade(entry_time, exit_time, side, entry_price, exit_price, pnl, contracts):
    """Return a trade tuple matching trades_df column order."""
    return (entry_time, exit_time, side, entry_price, exit_price, round(pnl, 2), contracts)
