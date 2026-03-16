"""Tests for the canonical strategy universe adapter.

Covers:
- Registry to portfolio config translation
- Fallback behavior when registry missing/corrupt
- Action-to-eligibility filtering
- Stale/corrupt registry handling
- Freshness checks
- Execution config shape
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.strategy_universe import (
    build_portfolio_config,
    get_eval_strategies,
    get_active_strategy_ids,
    get_avoid_regimes,
    check_freshness,
    ACTION_ELIGIBILITY,
    _build_strategy_exec_config,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_registry(tmp_path):
    """Create a minimal registry JSON for testing."""
    registry = {
        "_schema_version": "2.0",
        "_generated": "2026-03-15",
        "strategies": [
            {
                "strategy_id": "TEST-A",
                "strategy_name": "test_strat_a",
                "family": "trend",
                "asset": "MNQ",
                "session": "morning",
                "direction": "long",
                "status": "core",
                "controller_state": "ACTIVE",
                "controller_action": "FULL_ON",
                "activation_score": 0.85,
                "last_controller_date": "2026-03-15",
                "execution_config": {
                    "avoid_regimes": ["RANGING"],
                    "preferred_regimes": ["TRENDING"],
                    "preferred_window": ["09:30", "12:00"],
                    "allowed_window": ["09:30", "14:00"],
                    "conviction_threshold_outside": 2,
                    "grinding_filter": False,
                    "exit_variant": None,
                    "priority": 6,
                },
            },
            {
                "strategy_id": "TEST-B",
                "strategy_name": "test_strat_b",
                "family": "reversion",
                "asset": "MGC",
                "session": "afternoon",
                "direction": "short",
                "status": "core",
                "controller_state": "ACTIVE_REDUCED",
                "controller_action": "REDUCED_ON",
                "activation_score": 0.60,
                "last_controller_date": "2026-03-15",
                "execution_config": {
                    "avoid_regimes": ["LOW_VOL"],
                    "preferred_regimes": ["HIGH_VOL"],
                    "preferred_window": ["12:00", "15:00"],
                    "allowed_window": ["10:00", "15:15"],
                    "conviction_threshold_outside": 3,
                    "grinding_filter": False,
                    "exit_variant": None,
                    "priority": 4,
                },
            },
            {
                "strategy_id": "TEST-C",
                "strategy_name": "test_strat_c",
                "family": "momentum",
                "asset": "MES",
                "session": "morning",
                "direction": "long",
                "status": "probation",
                "controller_state": "PROBATION",
                "controller_action": "PROBATION",
                "activation_score": 0.42,
                "last_controller_date": "2026-03-15",
            },
            {
                "strategy_id": "TEST-D",
                "strategy_name": "test_strat_d",
                "family": "vol",
                "asset": "MCL",
                "session": "all_day",
                "direction": "short",
                "status": "rejected",
                "controller_state": "ARCHIVED",
                "controller_action": "ARCHIVE_REVIEW",
                "activation_score": 0.10,
                "last_controller_date": "2026-03-15",
            },
        ],
    }
    reg_path = tmp_path / "strategy_registry.json"
    reg_path.write_text(json.dumps(registry, indent=2))
    return reg_path, registry


# ── Action Eligibility ────────────────────────────────────────────────────

class TestActionEligibility:

    def test_full_on_eligible(self):
        assert ACTION_ELIGIBILITY["FULL_ON"] is True

    def test_reduced_on_eligible(self):
        assert ACTION_ELIGIBILITY["REDUCED_ON"] is True

    def test_probation_not_eligible(self):
        assert ACTION_ELIGIBILITY["PROBATION"] is False

    def test_off_not_eligible(self):
        assert ACTION_ELIGIBILITY["OFF"] is False

    def test_disable_not_eligible(self):
        assert ACTION_ELIGIBILITY["DISABLE"] is False


# ── Build Portfolio Config ────────────────────────────────────────────────

class TestBuildPortfolioConfig:

    def test_builds_from_registry(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            config = build_portfolio_config()

        assert "strategies" in config
        assert "TEST-A" in config["strategies"]
        assert "TEST-B" in config["strategies"]
        # TEST-C (PROBATION) and TEST-D (ARCHIVE_REVIEW) should be excluded
        assert "TEST-C" not in config["strategies"]
        assert "TEST-D" not in config["strategies"]

    def test_include_probation_flag(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            config = build_portfolio_config(include_probation=True)

        assert "TEST-C" in config["strategies"]
        assert "TEST-D" not in config["strategies"]

    def test_config_shape_matches_legacy(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            config = build_portfolio_config()

        assert "max_simultaneous_positions" in config
        assert "max_positions_per_asset" in config
        assert "cluster_window_minutes" in config

        strat = config["strategies"]["TEST-A"]
        required_keys = [
            "name", "asset", "mode", "grinding_filter", "exit_variant",
            "avoid_regimes", "preferred_regimes", "preferred_window",
            "allowed_window", "conviction_threshold_outside", "priority",
        ]
        for key in required_keys:
            assert key in strat, f"Missing key: {key}"

    def test_timing_windows_are_tuples(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            config = build_portfolio_config()

        strat = config["strategies"]["TEST-A"]
        assert isinstance(strat["preferred_window"], tuple)
        assert isinstance(strat["allowed_window"], tuple)

    def test_source_metadata(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            config = build_portfolio_config()

        assert config.get("_source") == "strategy_registry"
        assert "_freshness" in config


# ── Fallback Behavior ─────────────────────────────────────────────────────

class TestFallback:

    def test_falls_back_on_missing_registry(self, tmp_path):
        missing = tmp_path / "nonexistent.json"
        with patch("engine.strategy_universe.REGISTRY_PATH", missing):
            config = build_portfolio_config()

        # Should get the hardcoded PORTFOLIO_CONFIG
        from engine.strategy_controller import PORTFOLIO_CONFIG
        assert config["strategies"] == PORTFOLIO_CONFIG["strategies"]

    def test_falls_back_on_corrupt_registry(self, tmp_path):
        corrupt = tmp_path / "bad.json"
        corrupt.write_text("{corrupt json data!!")
        with patch("engine.strategy_universe.REGISTRY_PATH", corrupt):
            config = build_portfolio_config()

        from engine.strategy_controller import PORTFOLIO_CONFIG
        assert config["strategies"] == PORTFOLIO_CONFIG["strategies"]


# ── Freshness Checks ─────────────────────────────────────────────────────

class TestFreshnessChecks:

    def test_fresh_registry(self, sample_registry):
        _, registry = sample_registry
        result = check_freshness(registry)

        assert result["fresh"] is True
        assert result["warning"] is None
        assert result["schema_version"] == "2.0"

    def test_stale_registry(self):
        registry = {
            "_schema_version": "2.0",
            "strategies": [
                {"last_controller_date": "2026-01-01"},
            ],
        }
        result = check_freshness(registry)

        assert result["fresh"] is False
        assert "days old" in result["warning"]

    def test_missing_controller_dates(self):
        registry = {
            "_schema_version": "2.0",
            "strategies": [
                {"strategy_id": "X", "status": "core"},
            ],
        }
        result = check_freshness(registry)

        assert result["fresh"] is False
        assert "No controller decisions" in result["warning"]

    def test_stale_registry_triggers_fallback(self, tmp_path):
        registry = {
            "_schema_version": "2.0",
            "strategies": [
                {
                    "strategy_id": "OLD",
                    "strategy_name": "old_strat",
                    "asset": "MES",
                    "direction": "long",
                    "status": "core",
                    "controller_action": "FULL_ON",
                    "last_controller_date": "2025-01-01",
                },
            ],
        }
        reg_path = tmp_path / "stale.json"
        reg_path.write_text(json.dumps(registry))
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            config = build_portfolio_config()

        # Should fall back to hardcoded PORTFOLIO_CONFIG
        from engine.strategy_controller import PORTFOLIO_CONFIG
        assert config["strategies"] == PORTFOLIO_CONFIG["strategies"]


# ── Eval Strategies ───────────────────────────────────────────────────────

class TestGetEvalStrategies:

    def test_returns_core_and_probation(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            evals = get_eval_strategies()

        ids = [e[0] for e in evals]
        assert "TEST-A" in ids      # core
        assert "TEST-C" in ids      # probation
        assert "TEST-D" not in ids  # rejected

    def test_tuple_shape(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            evals = get_eval_strategies()

        for entry in evals:
            assert len(entry) == 4  # (id, name, asset, direction)


# ── Avoid Regimes ─────────────────────────────────────────────────────────

class TestGetAvoidRegimes:

    def test_returns_avoid_regimes(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            avoids = get_avoid_regimes("TEST-A")

        assert avoids == ["RANGING"]

    def test_returns_empty_for_unknown(self, sample_registry):
        reg_path, _ = sample_registry
        with patch("engine.strategy_universe.REGISTRY_PATH", reg_path):
            avoids = get_avoid_regimes("NONEXISTENT")

        assert avoids == []


# ── Exec Config Builder ──────────────────────────────────────────────────

class TestBuildStrategyExecConfig:

    def test_uses_execution_config_fields(self):
        strategy = {
            "strategy_id": "X",
            "strategy_name": "test",
            "asset": "MES",
            "direction": "long",
            "session": "morning",
            "activation_score": 0.75,
            "execution_config": {
                "avoid_regimes": ["RANGING"],
                "preferred_regimes": ["TRENDING"],
                "preferred_window": ["10:00", "12:00"],
                "allowed_window": ["09:30", "14:00"],
                "conviction_threshold_outside": 3,
                "grinding_filter": True,
                "exit_variant": "profit_ladder",
                "priority": 7,
            },
        }
        result = _build_strategy_exec_config(strategy)

        assert result["name"] == "test"
        assert result["avoid_regimes"] == ["RANGING"]
        assert result["grinding_filter"] is True
        assert result["priority"] == 7
        assert result["preferred_window"] == ("10:00", "12:00")

    def test_uses_session_defaults_when_no_exec_config(self):
        strategy = {
            "strategy_id": "Y",
            "strategy_name": "minimal",
            "asset": "MGC",
            "direction": "short",
            "session": "afternoon",
            "activation_score": 0.5,
        }
        result = _build_strategy_exec_config(strategy)

        assert result["name"] == "minimal"
        assert result["preferred_window"] == ("12:00", "15:00")
        assert result["allowed_window"] == ("10:00", "15:15")
        assert result["grinding_filter"] is False
        assert result["avoid_regimes"] == []
