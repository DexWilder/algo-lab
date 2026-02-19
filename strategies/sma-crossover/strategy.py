"""SMA Crossover strategy — reference implementation.

Converted from strategy.pine following the strategy Python contract.
See docs/strategy_python_contract.md for the full contract specification.
"""

import pandas as pd
from engine.indicators import crossover, crossunder


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate long/short signals based on SMA crossover.

    Goes long when the 10-period SMA crosses above the 30-period SMA.
    Goes short when the 10-period SMA crosses below the 30-period SMA.
    Exits are triggered by the opposite crossover.
    """
    df = df.copy()

    # Parameters (from Pine input defaults)
    fast_len = 10
    slow_len = 30

    # Calculate indicators
    df["sma_fast"] = df["close"].rolling(window=fast_len).mean()
    df["sma_slow"] = df["close"].rolling(window=slow_len).mean()

    # Initialize signal columns
    df["signal"] = 0
    df["exit_signal"] = 0

    # Detect crossovers
    long_entry = crossover(df["sma_fast"], df["sma_slow"])
    short_entry = crossunder(df["sma_fast"], df["sma_slow"])

    # Long entry on fast crossing above slow
    df.loc[long_entry, "signal"] = 1

    # Short entry on fast crossing below slow
    df.loc[short_entry, "signal"] = -1

    # Exit long when fast crosses below slow
    df.loc[short_entry, "exit_signal"] = 1

    # Exit short when fast crosses above slow
    df.loc[long_entry, "exit_signal"] = -1

    return df
