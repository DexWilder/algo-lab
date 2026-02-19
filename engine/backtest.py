"""Backtest runner — Phase 2 implementation."""

import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    mode: str = "both",
) -> dict:
    """Run a backtest on signal data.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV data conforming to the data contract.
    signals : pd.DataFrame
        DataFrame with 'signal' and 'exit_signal' columns (output of
        a strategy's generate_signals()).
    mode : str
        One of 'long', 'short', or 'both'.

    Returns
    -------
    dict
        Keys: trades_df (pd.DataFrame), equity_curve (pd.Series), stats (dict).

    Raises
    ------
    NotImplementedError
        Phase 2 — not yet implemented.
    """
    raise NotImplementedError(
        "run_backtest() is a Phase 2 feature. "
        "See docs/ROADMAP.md for implementation plan."
    )
