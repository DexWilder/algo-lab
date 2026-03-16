"""Shared test fixtures for FQL test suite."""

import numpy as np
import pandas as pd
import pytest
import yaml
from pathlib import Path


CONFIG_PATH = Path(__file__).parent.parent / "research" / "controller_config.yaml"


@pytest.fixture
def config():
    """Load the real controller config — tests break if config changes."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture
def perfect_signals():
    """All scoring dimensions at best values."""
    return {
        "regime_fit_level": "preferred",
        "half_life_status": "HEALTHY",
        "sharpe_trend": "IMPROVING",
        "marginal_sharpe": 0.20,
        "max_correlation": 0.10,
        "same_exposure_cluster": False,
        "health_status": "PASS",
        "kill_flags": [],
        "session_drift_severity": "NORMAL",
        "session_concentration": False,
        "time_fit": "match",
        "asset_fit": "good",
        "recent_sharpe": 2.0,
    }


@pytest.fixture
def worst_signals():
    """All scoring dimensions at worst values."""
    return {
        "regime_fit_level": "avoid",
        "half_life_status": "ARCHIVE_CANDIDATE",
        "sharpe_trend": "DECLINING",
        "marginal_sharpe": -0.20,
        "max_correlation": 0.80,
        "same_exposure_cluster": True,
        "health_status": "FAIL",
        "kill_flags": ["redundancy", "decay"],
        "session_drift_severity": "ALARM",
        "session_concentration": True,
        "time_fit": "mismatch",
        "asset_fit": "poor",
        "recent_sharpe": -0.5,
    }


@pytest.fixture
def make_ohlcv():
    """Factory for synthetic OHLCV DataFrames.

    Parameters
    ----------
    n_days : int
        Number of trading days.
    trend : str
        "up", "down", or "flat".
    vol : str
        "low", "normal", or "high".
    bars_per_day : int
        5-minute bars per session (default 78 = 6.5 hours).
    seed : int
        Random seed for reproducibility.
    """
    def _make(n_days=300, trend="flat", vol="normal", bars_per_day=78, seed=42):
        rng = np.random.RandomState(seed)
        n_bars = n_days * bars_per_day

        vol_scale = {"low": 0.002, "normal": 0.005, "high": 0.012}[vol]
        trend_drift = {"up": 0.0003, "down": -0.0003, "flat": 0.0}[trend]

        returns = rng.normal(trend_drift, vol_scale, n_bars)
        price = 4500.0 * np.exp(np.cumsum(returns))

        noise = rng.uniform(0.5, 2.0, n_bars) * vol_scale * 4500
        high = price + noise
        low = price - noise
        close = price + rng.normal(0, vol_scale * 1000, n_bars)
        open_ = np.roll(close, 1)
        open_[0] = 4500.0

        dates = pd.bdate_range("2023-01-03", periods=n_days)
        datetimes = []
        for d in dates:
            for b in range(bars_per_day):
                datetimes.append(d + pd.Timedelta(minutes=5 * b + 9 * 60 + 30))

        df = pd.DataFrame({
            "datetime": datetimes[:n_bars],
            "open": open_[:n_bars],
            "high": high[:n_bars],
            "low": low[:n_bars],
            "close": close[:n_bars],
            "volume": rng.randint(100, 5000, n_bars),
        })
        return df

    return _make
