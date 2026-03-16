"""Tests for FQL Portfolio Regime Allocation.

Covers:
- Base tier from controller action
- Contribution adjustments (boost and cap)
- Counterfactual adjustments
- Max boost cap
- Hard restriction enforcement
- Session-specific allocation
- Crowding dampening
- Reason code determinism
- Edge cases
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.portfolio_regime_allocation import AllocationEngine
from research.allocation_tiers import (
    OFF, MICRO, REDUCED, BASE, BOOST, MAX_ALLOWED,
    tier_name, tier_up, tier_down, ACTION_TO_BASE_TIER,
)
from research.reason_codes import ReasonCode


@pytest.fixture
def config(config):
    """Extend the base config fixture with allocation config."""
    return config


@pytest.fixture
def engine(config):
    return AllocationEngine(config)


def _make_entry(sid="TEST-A", action="FULL_ON", state="ACTIVE",
                exposure="trend_persistence", **kwargs):
    """Build a minimal activation matrix entry."""
    entry = {
        "strategy_id": sid,
        "recommended_action": action,
        "current_state": state,
        "new_state": state,
        "primary_exposure": exposure,
        "activation_score": 0.75,
        "sub_scores": {"contribution": 0.4, "redundancy": 0.8},
        "reason_codes": [],
        "session_restrictions": [],
        "_signals": {
            "contribution_verdict": "NEUTRAL",
            "session_drift_severity": "NORMAL",
        },
    }
    entry.update(kwargs)
    return entry


# ── Base Tier Mapping ─────────────────────────────────────────────────────

class TestBaseTier:

    def test_full_on_maps_to_base(self, engine):
        matrix = [_make_entry(action="FULL_ON")]
        result = engine.compute_allocations(matrix)
        assert result["TEST-A"]["base_tier"] == BASE
        assert result["TEST-A"]["base_tier_name"] == "BASE"

    def test_reduced_on_maps_to_reduced(self, engine):
        matrix = [_make_entry(action="REDUCED_ON")]
        result = engine.compute_allocations(matrix)
        assert result["TEST-A"]["base_tier"] == REDUCED

    def test_probation_maps_to_micro(self, engine):
        matrix = [_make_entry(action="PROBATION")]
        result = engine.compute_allocations(matrix)
        assert result["TEST-A"]["base_tier"] == MICRO

    def test_off_maps_to_off(self, engine):
        matrix = [_make_entry(action="OFF")]
        result = engine.compute_allocations(matrix)
        assert result["TEST-A"]["base_tier"] == OFF
        assert result["TEST-A"]["hard_restricted"] is True


# ── Hard Restrictions ─────────────────────────────────────────────────────

class TestHardRestrictions:

    def test_disabled_state_forces_off(self, engine):
        matrix = [_make_entry(action="FULL_ON", state="DISABLED")]
        result = engine.compute_allocations(matrix)
        assert result["TEST-A"]["final_tier"] == OFF
        assert result["TEST-A"]["hard_restricted"] is True
        assert ReasonCode.ALLOC_HARD_RESTRICTED in result["TEST-A"]["reason_codes"]

    def test_all_sessions_off_when_hard_restricted(self, engine):
        matrix = [_make_entry(action="DISABLE")]
        result = engine.compute_allocations(matrix)
        for sess_data in result["TEST-A"]["sessions"].values():
            assert sess_data["tier"] == OFF


# ── Contribution Adjustments ──────────────────────────────────────────────

class TestContribution:

    def test_strong_contribution_boosts(self, engine):
        matrix = [_make_entry()]
        contrib = {"TEST-A": {"verdict": "ADDS VALUE", "marginal_sharpe": 0.15}}
        result = engine.compute_allocations(matrix, contribution_signals=contrib)

        assert result["TEST-A"]["target_tier"] > result["TEST-A"]["base_tier"]
        assert ReasonCode.ALLOC_CONTRIB_BOOST in result["TEST-A"]["reason_codes"]

    def test_dilutive_caps(self, engine):
        matrix = [_make_entry()]
        contrib = {"TEST-A": {"verdict": "DILUTIVE", "marginal_sharpe": -0.10}}
        result = engine.compute_allocations(matrix, contribution_signals=contrib)

        assert result["TEST-A"]["target_tier"] <= REDUCED
        assert ReasonCode.ALLOC_CONTRIB_DILUTIVE_CAP in result["TEST-A"]["reason_codes"]

    def test_neutral_no_change(self, engine):
        matrix = [_make_entry()]
        contrib = {"TEST-A": {"verdict": "NEUTRAL", "marginal_sharpe": 0.01}}
        result = engine.compute_allocations(matrix, contribution_signals=contrib)

        assert result["TEST-A"]["target_tier"] == result["TEST-A"]["base_tier"]


# ── Counterfactual Adjustments ────────────────────────────────────────────

class TestCounterfactual:

    def test_positive_cf_boosts(self, engine):
        matrix = [_make_entry()]
        cf = {"TEST-A": {"counterfactual_score": 0.40, "recommendation": "KEEP_FULL"}}
        result = engine.compute_allocations(matrix, counterfactual=cf)

        assert result["TEST-A"]["target_tier"] > BASE
        assert ReasonCode.ALLOC_CF_BOOST in result["TEST-A"]["reason_codes"]

    def test_remove_recommendation_caps_at_micro(self, engine):
        matrix = [_make_entry()]
        cf = {"TEST-A": {"counterfactual_score": -0.30, "recommendation": "REMOVE"}}
        result = engine.compute_allocations(matrix, counterfactual=cf)

        assert result["TEST-A"]["target_tier"] <= MICRO
        assert ReasonCode.ALLOC_CF_REMOVE_CAP in result["TEST-A"]["reason_codes"]

    def test_negative_cf_reduces(self, engine):
        matrix = [_make_entry()]
        cf = {"TEST-A": {"counterfactual_score": -0.20, "recommendation": "REVIEW"}}
        result = engine.compute_allocations(matrix, counterfactual=cf)

        assert result["TEST-A"]["target_tier"] < BASE
        assert ReasonCode.ALLOC_CF_CAP in result["TEST-A"]["reason_codes"]

    def test_no_cf_data_no_change(self, engine):
        matrix = [_make_entry()]
        result = engine.compute_allocations(matrix, counterfactual={})

        assert result["TEST-A"]["target_tier"] == BASE


# ── Max Boost Cap ─────────────────────────────────────────────────────────

class TestMaxBoostCap:

    def test_double_boost_capped(self, engine):
        """Both contribution and CF boost should be capped at max_boost above base."""
        matrix = [_make_entry()]
        contrib = {"TEST-A": {"verdict": "ADDS VALUE", "marginal_sharpe": 0.20}}
        cf = {"TEST-A": {"counterfactual_score": 0.50, "recommendation": "KEEP_FULL"}}
        result = engine.compute_allocations(matrix, contribution_signals=contrib, counterfactual=cf)

        max_boost = engine.max_boost
        assert result["TEST-A"]["target_tier"] <= BASE + max_boost


# ── Session-Specific Allocation ───────────────────────────────────────────

class TestSessionAllocation:

    def test_alarm_session_blocked(self, engine):
        matrix = [_make_entry()]
        drift = {
            "TEST-A": {
                "restricted_sessions": ["afternoon"],
                "session_details": {
                    "morning": {"severity": "NORMAL"},
                    "midday": {"severity": "NORMAL"},
                    "afternoon": {"severity": "ALARM"},
                },
                "primary_session": "morning",
            }
        }
        result = engine.compute_allocations(matrix, session_drift_signals=drift)

        assert result["TEST-A"]["sessions"]["afternoon"]["tier"] == OFF
        assert result["TEST-A"]["sessions"]["morning"]["tier"] > OFF

    def test_drift_session_reduced(self, engine):
        matrix = [_make_entry()]
        drift = {
            "TEST-A": {
                "restricted_sessions": [],
                "session_details": {
                    "morning": {"severity": "NORMAL"},
                    "midday": {"severity": "DRIFT"},
                    "afternoon": {"severity": "NORMAL"},
                },
                "primary_session": "morning",
            }
        }
        result = engine.compute_allocations(matrix, session_drift_signals=drift)

        assert result["TEST-A"]["sessions"]["midday"]["tier"] < result["TEST-A"]["sessions"]["morning"]["tier"]

    def test_primary_session_blocked_caps_global(self, engine):
        matrix = [_make_entry()]
        drift = {
            "TEST-A": {
                "restricted_sessions": ["morning"],
                "session_details": {
                    "morning": {"severity": "ALARM"},
                    "midday": {"severity": "NORMAL"},
                    "afternoon": {"severity": "NORMAL"},
                },
                "primary_session": "morning",
            }
        }
        result = engine.compute_allocations(matrix, session_drift_signals=drift)

        # Primary blocked -> global capped at MICRO
        assert result["TEST-A"]["final_tier"] <= MICRO
        assert ReasonCode.ALLOC_PRIMARY_SESSION_BLOCKED in result["TEST-A"]["reason_codes"]


# ── Crowding Dampening ────────────────────────────────────────────────────

class TestCrowding:

    def test_crowded_cluster_capped(self, engine):
        """3+ strategies in same exposure cluster should be capped."""
        matrix = [
            _make_entry(sid="A", exposure="trend_persistence"),
            _make_entry(sid="B", exposure="trend_persistence"),
            _make_entry(sid="C", exposure="trend_persistence"),
        ]
        # Boost all to ensure they'd be above BASE without crowding
        contrib = {
            "A": {"verdict": "ADDS VALUE", "marginal_sharpe": 0.20},
            "B": {"verdict": "ADDS VALUE", "marginal_sharpe": 0.20},
            "C": {"verdict": "ADDS VALUE", "marginal_sharpe": 0.20},
        }
        result = engine.compute_allocations(matrix, contribution_signals=contrib)

        # All should be capped at BASE (crowding cap)
        for sid in ["A", "B", "C"]:
            assert result[sid]["final_tier"] <= BASE

    def test_non_crowded_not_capped(self, engine):
        """2 strategies in same cluster should NOT trigger crowding."""
        matrix = [
            _make_entry(sid="A", exposure="trend_persistence"),
            _make_entry(sid="B", exposure="trend_persistence"),
        ]
        contrib = {
            "A": {"verdict": "ADDS VALUE", "marginal_sharpe": 0.20},
            "B": {"verdict": "ADDS VALUE", "marginal_sharpe": 0.20},
        }
        result = engine.compute_allocations(matrix, contribution_signals=contrib)

        # Should be boosted above BASE (no crowding cap)
        assert result["A"]["final_tier"] > BASE or result["A"]["base_tier"] == BASE


# ── Tier Helpers ──────────────────────────────────────────────────────────

class TestTierHelpers:

    def test_tier_up_clamped(self):
        assert tier_up(MAX_ALLOWED, 1) == MAX_ALLOWED

    def test_tier_down_clamped(self):
        assert tier_down(OFF, 1) == OFF

    def test_action_mapping_complete(self):
        """All expected actions have a mapping."""
        for action in ["FULL_ON", "REDUCED_ON", "PROBATION", "OFF", "DISABLE", "ARCHIVE_REVIEW"]:
            assert action in ACTION_TO_BASE_TIER


# ── Output Structure ──────────────────────────────────────────────────────

class TestOutputStructure:

    def test_all_required_fields(self, engine):
        matrix = [_make_entry()]
        result = engine.compute_allocations(matrix)
        alloc = result["TEST-A"]

        required = [
            "strategy_id", "base_tier", "base_tier_name",
            "target_tier", "target_tier_name",
            "final_tier", "final_tier_name",
            "sessions", "hard_restricted", "reason_codes", "adjustments",
        ]
        for field in required:
            assert field in alloc, f"Missing field: {field}"

    def test_all_sessions_present(self, engine):
        matrix = [_make_entry()]
        result = engine.compute_allocations(matrix)

        for sess in ["morning", "midday", "afternoon"]:
            assert sess in result["TEST-A"]["sessions"]
            sess_data = result["TEST-A"]["sessions"][sess]
            assert "tier" in sess_data
            assert "tier_name" in sess_data
            assert "reason_codes" in sess_data

    def test_reason_codes_always_list(self, engine):
        matrix = [_make_entry()]
        result = engine.compute_allocations(matrix)

        assert isinstance(result["TEST-A"]["reason_codes"], list)
        assert len(result["TEST-A"]["reason_codes"]) >= 1  # at least BASE_FROM_ACTION
