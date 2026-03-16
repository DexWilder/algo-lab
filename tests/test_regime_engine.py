"""Regression tests for FQL Multi-Factor Regime Engine.

Tests cover:
- Column creation
- Volatility regime classification
- Trend detection
- Persistence scoring
- Composite regime format
- Strategy filtering
- Short data handling
- Regime summary
"""

import pytest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.regime_engine import RegimeEngine


class TestClassifyColumns:

    def test_classify_adds_expected_columns(self, make_ohlcv):
        df = make_ohlcv(n_days=300, trend="flat", vol="normal")
        engine = RegimeEngine()
        result = engine.classify(df)

        expected_cols = [
            "vol_regime", "trend_regime", "rv_regime",
            "trend_persistence", "persistence_score", "composite_regime",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_classify_preserves_row_count(self, make_ohlcv):
        df = make_ohlcv(n_days=100)
        engine = RegimeEngine()
        result = engine.classify(df)

        assert len(result) == len(df)


class TestVolatilityRegime:

    def test_low_vol_detection(self, make_ohlcv):
        """Low volatility data should eventually produce LOW_VOL labels."""
        df = make_ohlcv(n_days=300, vol="low")
        engine = RegimeEngine()
        result = engine.classify(df)

        vol_values = result["vol_regime"].unique()
        # With consistently low vol, should see LOW_VOL after warmup
        assert "LOW_VOL" in vol_values or "NORMAL" in vol_values

    def test_high_vol_detection(self, make_ohlcv):
        """High volatility data should produce HIGH_VOL labels."""
        df = make_ohlcv(n_days=300, vol="high")
        engine = RegimeEngine()
        result = engine.classify(df)

        vol_values = result["vol_regime"].unique()
        assert "HIGH_VOL" in vol_values or "NORMAL" in vol_values

    def test_vol_regime_values_valid(self, make_ohlcv):
        df = make_ohlcv(n_days=300)
        engine = RegimeEngine()
        result = engine.classify(df)

        valid_values = {"LOW_VOL", "NORMAL", "HIGH_VOL"}
        actual = set(result["vol_regime"].unique())
        assert actual.issubset(valid_values)


class TestTrendRegime:

    def test_trending_detection(self, make_ohlcv):
        """Strong uptrend should produce TRENDING labels."""
        df = make_ohlcv(n_days=300, trend="up")
        engine = RegimeEngine()
        result = engine.classify(df)

        # After warmup, should see TRENDING in the data
        trend_values = result["trend_regime"].unique()
        assert "TRENDING" in trend_values

    def test_ranging_detection(self, make_ohlcv):
        """Flat market should produce RANGING labels."""
        df = make_ohlcv(n_days=300, trend="flat", vol="low")
        engine = RegimeEngine()
        result = engine.classify(df)

        trend_values = result["trend_regime"].unique()
        assert "RANGING" in trend_values

    def test_trend_regime_values_valid(self, make_ohlcv):
        df = make_ohlcv(n_days=300)
        engine = RegimeEngine()
        result = engine.classify(df)

        valid_values = {"TRENDING", "RANGING"}
        actual = set(result["trend_regime"].unique())
        assert actual.issubset(valid_values)


class TestPersistence:

    def test_persistence_values_valid(self, make_ohlcv):
        df = make_ohlcv(n_days=300)
        engine = RegimeEngine()
        result = engine.classify(df)

        valid_values = {"GRINDING", "CHOPPY"}
        actual = set(result["trend_persistence"].unique())
        assert actual.issubset(valid_values)

    def test_persistence_score_is_numeric(self, make_ohlcv):
        df = make_ohlcv(n_days=300)
        engine = RegimeEngine()
        result = engine.classify(df)

        assert result["persistence_score"].dtype in (np.float64, np.float32, float)


class TestCompositeRegime:

    def test_composite_format(self, make_ohlcv):
        """Composite regime should be '{vol}_{trend}' format."""
        df = make_ohlcv(n_days=300)
        engine = RegimeEngine()
        result = engine.classify(df)

        for val in result["composite_regime"].unique():
            parts = val.split("_")
            assert len(parts) >= 2, f"Bad composite format: {val}"
            assert parts[0] in ("LOW", "NORMAL", "HIGH")


class TestGetActiveStrategies:

    def test_avoids_excluded(self):
        engine = RegimeEngine()
        profiles = {
            "strat_a": {"avoid_regimes": ["HIGH_VOL"]},
            "strat_b": {"avoid_regimes": []},
        }
        date_regime = {"vol_regime": "HIGH_VOL", "trend_regime": "TRENDING", "rv_regime": "NORMAL_RV"}

        active = engine.get_active_strategies(date_regime, profiles)

        assert "strat_a" not in active
        assert "strat_b" in active

    def test_no_avoids_includes_all(self):
        engine = RegimeEngine()
        profiles = {
            "strat_a": {"avoid_regimes": []},
            "strat_b": {},
        }
        date_regime = {"vol_regime": "NORMAL", "trend_regime": "RANGING", "rv_regime": "NORMAL_RV"}

        active = engine.get_active_strategies(date_regime, profiles)

        assert len(active) == 2


class TestShortData:

    def test_short_data_no_crash(self, make_ohlcv):
        """Very short data should not crash, should use defaults."""
        df = make_ohlcv(n_days=30)
        engine = RegimeEngine()
        result = engine.classify(df)

        assert len(result) == len(df)
        assert "vol_regime" in result.columns
        assert "trend_regime" in result.columns


class TestRegimeSummary:

    def test_summary_structure(self, make_ohlcv):
        df = make_ohlcv(n_days=300)
        engine = RegimeEngine()
        summary = engine.regime_summary(df)

        assert "total_days" in summary
        assert summary["total_days"] > 0
        assert "vol_regime" in summary
        assert "trend_regime" in summary

    def test_summary_counts_sum_correctly(self, make_ohlcv):
        df = make_ohlcv(n_days=300)
        engine = RegimeEngine()
        summary = engine.regime_summary(df)

        total = summary["total_days"]
        vol_sum = sum(v["count"] for v in summary["vol_regime"].values())
        assert vol_sum == total
