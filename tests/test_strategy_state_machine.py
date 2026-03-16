"""Regression tests for FQL Strategy State Machine.

Tests cover all 9 priority transition paths, guard rails for invalid
transitions, priority ordering, and reason code determinism.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.strategy_state_machine import StrategyStateMachine, VALID_STATES, VALID_TRANSITIONS
from research.reason_codes import ReasonCode


@pytest.fixture
def sm():
    return StrategyStateMachine()


# ── Priority 1: Hard Kill ──────────────────────────────────────────────────

class TestPriority1HardKill:

    def test_multi_flag_hard_kill_from_active(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "kill_flags": ["redundancy", "decay"],
            "activation_score": 0.60,
        })
        assert result["new_state"] == "DISABLED"
        assert result["changed"] is True
        assert ReasonCode.KILL_TRIGGER_HARD in result["reason_codes"]

    def test_archive_candidate_plus_dilutive(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "half_life_status": "ARCHIVE_CANDIDATE",
            "contribution_verdict": "DILUTIVE",
            "kill_flags": [],
        })
        assert result["new_state"] == "DISABLED"
        assert result["changed"] is True
        assert ReasonCode.HALF_LIFE_DEAD in result["reason_codes"]
        assert ReasonCode.PORTFOLIO_DILUTION in result["reason_codes"]

    def test_hard_kill_from_paper(self, sm):
        result = sm.evaluate_transition("PAPER", {
            "kill_flags": ["decay", "redundancy"],
        })
        assert result["new_state"] == "DISABLED"
        assert result["changed"] is True

    def test_hard_kill_from_probation(self, sm):
        result = sm.evaluate_transition("PROBATION", {
            "kill_flags": ["decay", "dilution"],
        })
        assert result["new_state"] == "DISABLED"
        assert result["changed"] is True

    def test_hard_kill_not_from_disabled(self, sm):
        """DISABLED is not in the hard-kill from-states."""
        result = sm.evaluate_transition("DISABLED", {
            "kill_flags": ["decay", "redundancy"],
        })
        # Priority 8 (disabled->archived) might fire, but not hard kill
        assert result["new_state"] != "DISABLED" or result["changed"] is False


# ── Priority 2: Decay to Probation ────────────────────────────────────────

class TestPriority2Decay:

    def test_decay_probation_from_active(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "half_life_status": "DECAYING",
            "activation_score": 0.40,
            "kill_flags": [],
        })
        assert result["new_state"] == "PROBATION"
        assert result["changed"] is True
        assert ReasonCode.HALF_LIFE_DECAY in result["reason_codes"]
        assert ReasonCode.PROBATION_ENTRY in result["reason_codes"]

    def test_decay_blocked_by_high_score(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "half_life_status": "DECAYING",
            "activation_score": 0.50,
            "kill_flags": [],
            "contribution_verdict": "NEUTRAL",
        })
        # Score 0.50 >= 0.45 threshold, so decay-to-probation should not fire
        assert result["new_state"] != "PROBATION" or result["changed"] is False


# ── Priority 3: Dilution to Reduced ───────────────────────────────────────

class TestPriority3Dilution:

    def test_dilution_reduces_active(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "contribution_verdict": "DILUTIVE",
            "half_life_status": "HEALTHY",
            "kill_flags": [],
            "activation_score": 0.60,
        })
        assert result["new_state"] == "ACTIVE_REDUCED"
        assert result["changed"] is True
        assert ReasonCode.PORTFOLIO_DILUTION in result["reason_codes"]

    def test_dilution_not_from_active_reduced(self, sm):
        """Priority 3 only triggers from ACTIVE, not ACTIVE_REDUCED."""
        result = sm.evaluate_transition("ACTIVE_REDUCED", {
            "contribution_verdict": "DILUTIVE",
            "half_life_status": "HEALTHY",
            "kill_flags": [],
            "activation_score": 0.60,
        })
        # Should not transition — already reduced
        assert result["changed"] is False


# ── Priority 4: Soft Kill to Probation ────────────────────────────────────

class TestPriority4SoftKill:

    def test_soft_kill_probation(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "kill_flags": ["redundancy"],
            "activation_score": 0.45,
            "half_life_status": "HEALTHY",
            "contribution_verdict": "NEUTRAL",
        })
        assert result["new_state"] == "PROBATION"
        assert result["changed"] is True
        assert ReasonCode.KILL_TRIGGER_SOFT in result["reason_codes"]

    def test_soft_kill_blocked_by_high_score(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "kill_flags": ["redundancy"],
            "activation_score": 0.55,
            "half_life_status": "HEALTHY",
            "contribution_verdict": "NEUTRAL",
        })
        # Score 0.55 >= 0.50 threshold, soft kill should not fire
        assert result["new_state"] != "PROBATION" or result["changed"] is False


# ── Priority 5: Recovery from Probation ───────────────────────────────────

class TestPriority5Recovery:

    def test_probation_recovery(self, sm):
        result = sm.evaluate_transition("PROBATION", {
            "activation_score": 0.70,
            "half_life_status": "HEALTHY",
            "kill_flags": [],
        })
        assert result["new_state"] == "ACTIVE"
        assert result["changed"] is True
        assert ReasonCode.HALF_LIFE_STRENGTHENING in result["reason_codes"]

    def test_probation_no_recovery_with_flags(self, sm):
        result = sm.evaluate_transition("PROBATION", {
            "activation_score": 0.70,
            "half_life_status": "HEALTHY",
            "kill_flags": ["redundancy"],
        })
        assert result["changed"] is False

    def test_probation_no_recovery_low_score(self, sm):
        result = sm.evaluate_transition("PROBATION", {
            "activation_score": 0.60,
            "half_life_status": "HEALTHY",
            "kill_flags": [],
        })
        assert result["changed"] is False


# ── Priority 6: Recovery from Reduced ─────────────────────────────────────

class TestPriority6ReducedRecovery:

    def test_reduced_recovery(self, sm):
        result = sm.evaluate_transition("ACTIVE_REDUCED", {
            "contribution_verdict": "ADDS VALUE",
            "activation_score": 0.70,
            "kill_flags": [],
            "half_life_status": "HEALTHY",
        })
        assert result["new_state"] == "ACTIVE"
        assert result["changed"] is True
        assert ReasonCode.PORTFOLIO_ADDS_VALUE in result["reason_codes"]

    def test_reduced_no_recovery_still_dilutive(self, sm):
        result = sm.evaluate_transition("ACTIVE_REDUCED", {
            "contribution_verdict": "DILUTIVE",
            "activation_score": 0.70,
            "kill_flags": [],
            "half_life_status": "HEALTHY",
        })
        assert result["changed"] is False


# ── Priority 7: Stale Probation to Disabled ───────────────────────────────

class TestPriority7StaleProbation:

    def test_stale_probation_disabled(self, sm):
        result = sm.evaluate_transition("PROBATION", {
            "days_in_current_state": 95,
            "activation_score": 0.30,
            "kill_flags": [],
            "half_life_status": "DECAYING",
        })
        assert result["new_state"] == "DISABLED"
        assert result["changed"] is True
        assert ReasonCode.ARCHIVE_CANDIDATE in result["reason_codes"]

    def test_probation_not_stale_yet(self, sm):
        result = sm.evaluate_transition("PROBATION", {
            "days_in_current_state": 60,
            "activation_score": 0.30,
            "kill_flags": [],
            "half_life_status": "DECAYING",
        })
        # 60 days < 90 day threshold
        assert result["new_state"] != "DISABLED"


# ── Priority 8: Disabled to Archived ──────────────────────────────────────

class TestPriority8DisabledArchive:

    def test_disabled_to_archived(self, sm):
        result = sm.evaluate_transition("DISABLED", {
            "days_in_current_state": 35,
            "activation_score": 0.20,
            "kill_flags": [],
        })
        assert result["new_state"] == "ARCHIVED"
        assert result["changed"] is True

    def test_disabled_not_archived_too_soon(self, sm):
        result = sm.evaluate_transition("DISABLED", {
            "days_in_current_state": 20,
            "activation_score": 0.20,
        })
        assert result["changed"] is False


# ── Priority 9: Resurrection ──────────────────────────────────────────────

class TestPriority9Resurrection:

    def test_resurrection_from_archived(self, sm):
        result = sm.evaluate_transition("ARCHIVED", {
            "half_life_status": "HEALTHY",
            "recent_sharpe": 1.5,
        })
        assert result["new_state"] == "RESURRECTION_CANDIDATE"
        assert result["changed"] is True
        assert ReasonCode.RESURRECTION_SIGNAL in result["reason_codes"]

    def test_no_resurrection_poor_sharpe(self, sm):
        result = sm.evaluate_transition("ARCHIVED", {
            "half_life_status": "HEALTHY",
            "recent_sharpe": 0.5,
        })
        assert result["changed"] is False

    def test_no_resurrection_decaying(self, sm):
        result = sm.evaluate_transition("ARCHIVED", {
            "half_life_status": "DECAYING",
            "recent_sharpe": 1.5,
        })
        assert result["changed"] is False


# ── Guard Rails ───────────────────────────────────────────────────────────

class TestGuardRails:

    def test_invalid_transition_blocked(self, sm):
        """Verify _result blocks transitions not in VALID_TRANSITIONS."""
        # Directly test the guard: ACTIVE -> ARCHIVED is not valid
        result = sm._result("ACTIVE", "ARCHIVED", ["TEST"], "test trigger")
        assert "BLOCKED" in result["trigger"]
        assert result["changed"] is False
        assert result["new_state"] == "ACTIVE"

    def test_unknown_state(self, sm):
        result = sm.evaluate_transition("NONEXISTENT_STATE", {
            "activation_score": 0.50,
        })
        assert result["changed"] is False
        assert result["new_state"] == "NONEXISTENT_STATE"

    def test_no_transition_returns_same_state(self, sm):
        result = sm.evaluate_transition("ACTIVE", {
            "activation_score": 0.70,
            "half_life_status": "HEALTHY",
            "kill_flags": [],
            "contribution_verdict": "ADDS VALUE",
        })
        assert result["changed"] is False
        assert result["new_state"] == "ACTIVE"


# ── Priority Ordering ─────────────────────────────────────────────────────

class TestPriorityOrdering:

    def test_hard_kill_beats_decay(self, sm):
        """When both P1 and P2 conditions are met, P1 wins."""
        result = sm.evaluate_transition("ACTIVE", {
            "kill_flags": ["decay", "redundancy"],  # P1: hard kill
            "half_life_status": "DECAYING",          # P2: decay
            "activation_score": 0.30,
        })
        assert result["new_state"] == "DISABLED"
        assert ReasonCode.KILL_TRIGGER_HARD in result["reason_codes"]

    def test_decay_beats_dilution(self, sm):
        """When both P2 and P3 conditions are met from ACTIVE, P2 wins."""
        result = sm.evaluate_transition("ACTIVE", {
            "half_life_status": "DECAYING",        # P2
            "activation_score": 0.40,
            "contribution_verdict": "DILUTIVE",    # P3
            "kill_flags": [],
        })
        assert result["new_state"] == "PROBATION"  # P2: decay->probation
        assert ReasonCode.HALF_LIFE_DECAY in result["reason_codes"]

    def test_dilution_beats_soft_kill(self, sm):
        """P3 (dilution) evaluated before P4 (soft kill) from ACTIVE."""
        result = sm.evaluate_transition("ACTIVE", {
            "contribution_verdict": "DILUTIVE",
            "half_life_status": "HEALTHY",
            "kill_flags": ["redundancy"],
            "activation_score": 0.45,
        })
        # P3 fires: ACTIVE -> ACTIVE_REDUCED (dilution with healthy HL)
        assert result["new_state"] == "ACTIVE_REDUCED"
        assert ReasonCode.PORTFOLIO_DILUTION in result["reason_codes"]
