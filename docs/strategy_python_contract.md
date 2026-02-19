# Strategy Python Contract

## Overview

Every strategy in `strategies/<name>/strategy.py` must follow this contract exactly. This ensures the engine can discover, load, and run any strategy uniformly.

## Required Function

```python
def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate trading signals from OHLCV data.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV data conforming to the data contract:
        columns = [datetime, open, high, low, close, volume]
        Sorted ascending by datetime, default integer index.

    Returns
    -------
    pd.DataFrame
        The original DataFrame with two additional columns:
        - 'signal': int — 1 for long entry, -1 for short entry, 0 for no signal
        - 'exit_signal': int — 1 for exit long, -1 for exit short, 0 for no exit
    """
```

## Rules

1. **Single entry point**: The module must expose exactly one public function: `generate_signals(df)`
2. **No side effects**: Do not read files, make API calls, or modify global state
3. **Pure DataFrame in, DataFrame out**: Accept a DataFrame, return a DataFrame
4. **Add only `signal` and `exit_signal` columns**: Do not remove or rename existing columns. You may add intermediate indicator columns (e.g., `sma_fast`, `sma_slow`) but `signal` and `exit_signal` are required.
5. **Signal values**:
   - `signal`:  `1` = long entry, `-1` = short entry, `0` = no signal
   - `exit_signal`: `1` = exit long, `-1` = exit short, `0` = no exit
6. **NaN handling**: Initial rows where indicators are warming up should have `signal=0` and `exit_signal=0`
7. **Bar timing assumption**: Signals fire on bar close. The engine fills at the next bar's open price.

## Indicator Helpers

Use helpers from `engine.indicators` for common operations:

```python
from engine.indicators import crossover, crossunder

# crossover(series_a, series_b) -> pd.Series[bool]
# True on bars where series_a crosses above series_b

# crossunder(series_a, series_b) -> pd.Series[bool]
# True on bars where series_a crosses below series_b
```

## Example Implementation

```python
import pandas as pd
from engine.indicators import crossover, crossunder


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Calculate indicators
    df["sma_fast"] = df["close"].rolling(window=10).mean()
    df["sma_slow"] = df["close"].rolling(window=30).mean()

    # Generate signals
    df["signal"] = 0
    df["exit_signal"] = 0

    long_entry = crossover(df["sma_fast"], df["sma_slow"])
    short_entry = crossunder(df["sma_fast"], df["sma_slow"])

    df.loc[long_entry, "signal"] = 1
    df.loc[short_entry, "signal"] = -1

    # Exit on opposite crossover
    df.loc[short_entry, "exit_signal"] = 1   # exit long
    df.loc[long_entry, "exit_signal"] = -1   # exit short

    return df
```

## meta.json

Each strategy directory must also contain a `meta.json` file. See `docs/meta_template.json` for the schema.
