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


# ── Site 4: engine/carry_lookup.py InvalidCarryConfig ────────────────────────

class TestSite4_InvalidCarryConfig:
    """_fx_carry_score must fail closed when carry config is inconsistent.

    Distinguishes:
      - asset not in fx_pairs → returns (None, "NOT_AVAILABLE") (legitimate)
      - fx_pairs references currency not in policy_rates → raises
      - policy_rates entry has None/missing rate → raises

    Pre-fix: both error cases collapsed into "(None, NOT_AVAILABLE)" which
    looked identical to legitimate asset-absence — config errors became
    invisible to operators.
    """

    def test_asset_not_in_fx_pairs_returns_not_available(self):
        """Legitimate absence — equity micro, not an FX pair. Not a config error."""
        from engine.carry_lookup import _fx_carry_score
        rates = {
            "fx_pairs": {"6J": {"domestic": "USD", "foreign": "JPY"}},
            "policy_rates": {"USD": {"rate": 0.045}, "JPY": {"rate": -0.001}},
        }
        score, label = _fx_carry_score("MES", rates)
        assert score is None
        assert label == "NOT_AVAILABLE"

    def test_raises_when_pair_currency_missing_from_policy(self):
        """fx_pairs references currency we don't track. Config error."""
        from engine.carry_lookup import _fx_carry_score, InvalidCarryConfig
        rates = {
            "fx_pairs": {"6J": {"domestic": "USD", "foreign": "JPY"}},
            "policy_rates": {"USD": {"rate": 0.045}},  # JPY missing
        }
        with pytest.raises(InvalidCarryConfig) as exc_info:
            _fx_carry_score("6J", rates)
        assert "JPY" in str(exc_info.value)
        assert "policy_rates" in str(exc_info.value)

    def test_raises_when_policy_rate_is_none(self):
        """Currency present but rate explicitly None. Config error."""
        from engine.carry_lookup import _fx_carry_score, InvalidCarryConfig
        rates = {
            "fx_pairs": {"6E": {"domestic": "USD", "foreign": "EUR"}},
            "policy_rates": {"USD": {"rate": 0.045}, "EUR": {"rate": None}},
        }
        with pytest.raises(InvalidCarryConfig) as exc_info:
            _fx_carry_score("6E", rates)
        assert "EUR" in str(exc_info.value)
        assert "rate" in str(exc_info.value)

    def test_valid_pair_returns_real_carry(self):
        """Sanity: normal path still works."""
        from engine.carry_lookup import _fx_carry_score
        rates = {
            "fx_pairs": {"6J": {"domestic": "USD", "foreign": "JPY"}},
            "policy_rates": {"USD": {"rate": 0.045}, "JPY": {"rate": -0.001}},
        }
        score, label = _fx_carry_score("6J", rates)
        assert score is not None
        assert label == "REAL"
        # Carry for long 6J = JPY rate - USD rate = -0.001 - 0.045 = -0.046
        assert abs(score - (-0.046)) < 1e-9

    def test_production_carry_rates_resolve_cleanly(self):
        """Standing guard: live engine/carry_rates.json must produce no config errors."""
        import json
        from pathlib import Path
        from engine.carry_lookup import _fx_carry_score
        rates_path = Path(__file__).parent.parent / "engine" / "carry_rates.json"
        with open(rates_path) as f:
            rates = json.load(f)
        # Every FX pair in production data must resolve without raising
        for asset in rates.get("fx_pairs", {}):
            score, label = _fx_carry_score(asset, rates)
            assert score is not None and label == "REAL", (
                f"{asset} should produce a REAL carry score from production rates"
            )


# ── Site 5: runner asset coverage ────────────────────────────────────────────

class TestSite5_RunnerAssetCoverage:
    """Forge batch runner must enumerate assets from engine/asset_config.py.

    Pre-fix risk: if CANDIDATES referenced an asset not in ASSETS, the
    runner would crash mid-batch on a KeyError. The standing test asserts
    every candidate asset IS in ASSETS so the runner cannot silently drift
    from the trading universe.
    """

    def test_every_candidate_asset_is_in_asset_config(self):
        from research.fql_forge_batch_runner import CANDIDATES
        from engine.asset_config import ASSETS
        universe = set(ASSETS.keys())
        for cid, info in CANDIDATES.items():
            asset = info.get("asset") if isinstance(info, dict) else None
            if asset is None:
                continue
            assert asset in universe, (
                f"Candidate {cid!r} references asset {asset!r} which is not "
                f"in engine/asset_config.py::ASSETS. Add the asset to "
                f"asset_config (with cost defaults) or remove the candidate."
            )

    def test_batch_runner_imports_asset_config(self):
        """Sanity: the import is what binds the runner to the source of truth."""
        import research.fql_forge_batch_runner as runner
        assert hasattr(runner, "ASSETS"), (
            "fql_forge_batch_runner must import ASSETS from engine.asset_config "
            "as its enumeration source — see Site 5 of Item #3.5."
        )
