"""Tests for Item #3.5 silent-default hardening pass.

Per FQL evidence law: any missing assumption that can change a trading
decision must fail closed. These tests exercise the new Invalid* exception
paths for the 5 silent-default sites caught during the cost integrity reset:

  Site 1: engine/io.py    — missing metrics fields
  Site 2: engine/regime_engine.py    — missing avoid_regimes key
  Site 3: engine/strategy_universe.py / strategy_controller.py — permissive metadata
  Site 4: engine/carry_lookup.py — missing currency or rate
  Site 5: runner asset coverage vs asset_config

Each site lands as its own atomic commit. Tests grow as sites land.
"""

import pytest


# ── Site 1: engine/io.py InvalidMetrics ──────────────────────────────────────

class TestSite1_InvalidMetrics:
    """_make_row must fail closed when required metrics are missing or None.

    Pre-Site-1 behavior: metrics.get(field, 0) silently substituted zero.
    A failed backtest with missing fields looked like "neutral strategy
    with zero drawdown" instead of "this result is invalid."
    """

    def test_raises_when_all_metrics_missing(self):
        from engine.io import _make_row, InvalidMetrics
        with pytest.raises(InvalidMetrics) as exc_info:
            _make_row("test_strat", "long", {})
        msg = str(exc_info.value)
        # Must name the actual missing fields, not be generic
        for field in ("roi", "max_drawdown", "sharpe", "expected_value", "trades"):
            assert field in msg, f"error message should name missing field {field!r}"

    def test_raises_when_one_metric_missing(self):
        from engine.io import _make_row, InvalidMetrics
        partial = {"roi": 0.10, "max_drawdown": -0.05, "sharpe": 1.2, "expected_value": 50.0}
        # trades intentionally absent
        with pytest.raises(InvalidMetrics) as exc_info:
            _make_row("test_strat", "long", partial)
        assert "trades" in str(exc_info.value)
        # Must NOT name fields that ARE present
        assert "roi" not in str(exc_info.value)

    def test_raises_when_metric_value_is_none(self):
        """Explicit None is treated the same as missing — both are 'no signal'."""
        from engine.io import _make_row, InvalidMetrics
        bad = {
            "roi": 0.10, "max_drawdown": -0.05, "sharpe": 1.2,
            "expected_value": 50.0, "trades": None,
        }
        with pytest.raises(InvalidMetrics) as exc_info:
            _make_row("test_strat", "long", bad)
        assert "trades" in str(exc_info.value)

    def test_accepts_complete_metrics_including_zero_values(self):
        """Explicit zero is fine (e.g., zero-trade backtest); missing is not."""
        from engine.io import _make_row
        full = {
            "roi": 0.0, "max_drawdown": 0.0, "sharpe": 0.0,
            "expected_value": 0.0, "trades": 0,
        }
        row = _make_row("zero_trade_strat", "long", full)
        assert row["name"] == "zero_trade_strat"
        assert row["mode"] == "long"
        assert row["trades"] == 0
        # Zero is allowed; the rule is fail-closed on ABSENT or None, not on zero.

    def test_accepts_full_metrics(self):
        from engine.io import _make_row
        full = {
            "roi": 0.15, "max_drawdown": -0.08, "sharpe": 1.45,
            "expected_value": 75.50, "trades": 250,
        }
        row = _make_row("real_strat", "both", full)
        assert row["roi"] == 0.15
        assert row["trades"] == 250

    def test_compute_metrics_output_is_acceptable_to_make_row(self):
        """Integration: compute_metrics output must pass _make_row validation.

        Regression guard — if anyone refactors compute_metrics to omit a field,
        this test catches it before that field starts getting silent zero defaults
        somewhere downstream.
        """
        import pandas as pd
        from engine.metrics import compute_metrics
        from engine.io import _make_row

        empty_trades = pd.DataFrame(columns=[
            "entry_time", "exit_time", "side", "entry_price",
            "exit_price", "pnl", "contracts",
        ])
        metrics = compute_metrics(empty_trades)
        row = _make_row("regression_check", "long", metrics)
        assert row is not None


# ── Site 2: engine/regime_engine.py InvalidRegimeProfile ─────────────────────

class TestSite2_InvalidRegimeProfile:
    """get_active_strategies must fail closed when a profile is missing
    'avoid_regimes' — even an empty list is acceptable, but a missing key is not.

    Pre-Site-2 behavior: profile.get('avoid_regimes', []) silently meant
    "trades all regimes" for any profile missing the key — strategies could
    trade in regimes their author intended to skip.
    """

    def _engine(self):
        from engine.regime_engine import RegimeEngine
        return RegimeEngine()

    def test_raises_when_avoid_regimes_key_absent(self):
        from engine.regime_engine import InvalidRegimeProfile
        eng = self._engine()
        profiles = {
            "good_strat": {"avoid_regimes": [], "preferred_regimes": []},
            "bad_strat": {"preferred_regimes": []},  # missing avoid_regimes
        }
        date_regime = {"vol_regime": "LOW_VOL", "trend_regime": "UP", "rv_regime": "MID"}
        with pytest.raises(InvalidRegimeProfile) as exc_info:
            eng.get_active_strategies(date_regime, profiles)
        assert "bad_strat" in str(exc_info.value)
        assert "avoid_regimes" in str(exc_info.value)

    def test_accepts_explicit_empty_avoid_regimes(self):
        """Explicit `[]` means 'intentionally trades all regimes' — allowed."""
        eng = self._engine()
        profiles = {
            "trades_everything": {"avoid_regimes": [], "preferred_regimes": []},
        }
        date_regime = {"vol_regime": "HIGH_VOL", "trend_regime": "DOWN", "rv_regime": "HIGH"}
        active = eng.get_active_strategies(date_regime, profiles)
        assert "trades_everything" in active

    def test_filters_out_strategies_with_matching_avoid_regime(self):
        """Sanity: normal filtering still works."""
        eng = self._engine()
        profiles = {
            "avoids_high_vol": {"avoid_regimes": ["HIGH_VOL"], "preferred_regimes": []},
            "trades_high_vol": {"avoid_regimes": [], "preferred_regimes": []},
        }
        date_regime = {"vol_regime": "HIGH_VOL", "trend_regime": "UP", "rv_regime": "MID"}
        active = eng.get_active_strategies(date_regime, profiles)
        assert "avoids_high_vol" not in active
        assert "trades_high_vol" in active

    def test_empty_profiles_dict_returns_empty(self):
        eng = self._engine()
        active = eng.get_active_strategies(
            {"vol_regime": "LOW_VOL", "trend_regime": "UP", "rv_regime": "MID"},
            {},
        )
        assert active == []
