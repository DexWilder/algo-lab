"""Common indicator helpers used by strategy modules."""

import pandas as pd


def crossover(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Detect where series_a crosses above series_b.

    Returns a boolean Series that is True on bars where series_a was below
    (or equal to) series_b on the previous bar and is now above series_b.
    """
    prev_a = series_a.shift(1)
    prev_b = series_b.shift(1)
    return (prev_a <= prev_b) & (series_a > series_b)


def crossunder(series_a: pd.Series, series_b: pd.Series) -> pd.Series:
    """Detect where series_a crosses below series_b.

    Returns a boolean Series that is True on bars where series_a was above
    (or equal to) series_b on the previous bar and is now below series_b.
    """
    prev_a = series_a.shift(1)
    prev_b = series_b.shift(1)
    return (prev_a >= prev_b) & (series_a < series_b)
