# Pine Script to Python Conversion Prompt

Use this prompt template when asking an LLM to convert a TradingView Pine Script strategy into a Python strategy module for algo-lab.

---

## Prompt Template

```
Convert the following TradingView Pine Script strategy into a Python module that follows the algo-lab strategy contract.

## Contract Rules

1. The module must expose exactly one function: `generate_signals(df: pd.DataFrame) -> pd.DataFrame`
2. Input `df` has columns: datetime, open, high, low, close, volume (sorted ascending)
3. Return the same DataFrame with two added columns:
   - `signal`: 1 = long entry, -1 = short entry, 0 = no signal
   - `exit_signal`: 1 = exit long, -1 = exit short, 0 = no exit
4. Use `from engine.indicators import crossover, crossunder` for cross detection
5. No side effects — no file I/O, no API calls, no global state
6. NaN rows from indicator warmup must have signal=0 and exit_signal=0
7. Always work on a copy: `df = df.copy()`
8. Signals fire on bar close; the engine fills at next bar open (do not implement fill logic)

## Indicator Mapping (Pine → Python)

| Pine Script               | Python (pandas)                                    |
|----------------------------|----------------------------------------------------|
| ta.sma(close, 14)         | df["close"].rolling(window=14).mean()              |
| ta.ema(close, 14)         | df["close"].ewm(span=14, adjust=False).mean()      |
| ta.rsi(close, 14)         | (custom RSI calculation or ta-lib)                 |
| ta.crossover(a, b)        | crossover(series_a, series_b)                      |
| ta.crossunder(a, b)       | crossunder(series_a, series_b)                     |
| ta.highest(high, 20)      | df["high"].rolling(window=20).max()                |
| ta.lowest(low, 20)        | df["low"].rolling(window=20).min()                 |
| ta.atr(14)                | (custom ATR calculation)                           |
| ta.macd(close, 12, 26, 9) | (custom MACD calculation)                          |
| ta.stoch(close,high,low,k,d,s) | (custom Stochastic calculation)              |
| strategy.entry("Long",...)| df.loc[condition, "signal"] = 1                    |
| strategy.entry("Short",...)|df.loc[condition, "signal"] = -1                    |
| strategy.close("Long")    | df.loc[condition, "exit_signal"] = 1               |
| strategy.close("Short")   | df.loc[condition, "exit_signal"] = -1              |

## Pine Script to Convert

<paste Pine Script here>

## Output

Return ONLY the Python code. No explanations. The file should be ready to save as `strategy.py`.
```

---

## Concrete Example

### Input: SMA Crossover Pine Script

```pine
//@version=5
strategy("SMA Crossover", overlay=true)

fastLen = input.int(10, "Fast SMA Length")
slowLen = input.int(30, "Slow SMA Length")

fast = ta.sma(close, fastLen)
slow = ta.sma(close, slowLen)

if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)

if ta.crossunder(fast, slow)
    strategy.close("Long")
    strategy.entry("Short", strategy.short)

if ta.crossover(fast, slow)
    strategy.close("Short")

plot(fast, color=color.blue)
plot(slow, color=color.red)
```

### Output: Python strategy.py

```python
import pandas as pd
from engine.indicators import crossover, crossunder


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
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
```
