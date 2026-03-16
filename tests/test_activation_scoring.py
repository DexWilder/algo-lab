"""Regression tests for FQL Activation Scoring Model.

Tests cover:
- Composite score correctness
- Decay enforcement caps
- Situation classification
- Confidence and uncertainty detection
- Reason code determinism
- Individual dimension scoring
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.activation_scoring import ActivationScorer
from research.reason_codes import ReasonCode


class TestCompositeScore:
    """Test the weighted composite scoring pipeline."""

    def test_perfect_strategy_scores_high(self, config, perfect_signals):
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(perfect_signals)

        assert result["activation_score"] >= 0.90
        assert result["recommended_action"] == "FULL_ON"
        assert result["situation"] == "HEALTHY"

    def test_worst_case_scores_low(self, config, worst_signals):
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(worst_signals)

        # Capped by archive_candidate_cap (0.42), then further reduced
        assert result["activation_score"] <= 0.20
        assert result["recommended_action"] in ("DISABLE", "ARCHIVE_REVIEW")

    def test_weighted_sum_correctness(self, config, perfect_signals):
        """Manually verify weighted sum matches expected value."""
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(perfect_signals)
        weights = config["scoring_weights"]

        # Perfect signals should produce all 1.0 sub-scores
        manual_sum = sum(
            result["sub_scores"][dim] * weights[dim]
            for dim in weights
        )
        manual_sum = round(min(1.0, max(0.0, manual_sum)), 4)

        assert result["activation_score"] == manual_sum

    def test_empty_signals_uses_defaults(self, config):
        """Empty signals dict should not crash, uses sensible defaults."""
        scorer = ActivationScorer(config)
        result = scorer.score_strategy({})

        assert 0.0 <= result["activation_score"] <= 1.0
        assert result["recommended_action"] in (
            "FULL_ON", "REDUCED_ON", "PROBATION", "OFF", "DISABLE", "ARCHIVE_REVIEW"
        )


class TestDecayEnforcement:
    """Test hard caps on activation score for decaying edges."""

    def test_archive_candidate_cap(self, config, perfect_signals):
        """ARCHIVE_CANDIDATE should cap score at 0.42 regardless of other signals."""
        signals = {**perfect_signals, "half_life_status": "ARCHIVE_CANDIDATE"}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        cap = config["decay_enforcement"]["archive_candidate_cap"]
        assert result["activation_score"] <= cap
        assert ReasonCode.HALF_LIFE_DEAD in result["reason_codes"]

    def test_decaying_cap(self, config, perfect_signals):
        """DECAYING should cap score at 0.52."""
        signals = {**perfect_signals, "half_life_status": "DECAYING"}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        cap = config["decay_enforcement"]["decaying_cap"]
        assert result["activation_score"] <= cap
        assert ReasonCode.HALF_LIFE_DECAY in result["reason_codes"]

    def test_healthy_not_capped(self, config, perfect_signals):
        """HEALTHY half-life should not be capped."""
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(perfect_signals)

        assert result["activation_score"] > config["decay_enforcement"]["decaying_cap"]


class TestSituationClassification:
    """Test the _classify_situation logic."""

    def test_regime_mismatch(self, config, perfect_signals):
        signals = {**perfect_signals, "regime_fit_level": "avoid"}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert result["situation"] == "REGIME_MISMATCH"

    def test_redundant(self, config, perfect_signals):
        signals = {
            **perfect_signals,
            "max_correlation": 0.80,
            "same_exposure_cluster": True,
        }
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert result["situation"] == "REDUNDANT"
        assert ReasonCode.REDUNDANT_CLUSTER in result["reason_codes"]

    def test_structural_fail(self, config, perfect_signals):
        signals = {
            **perfect_signals,
            "half_life_status": "ARCHIVE_CANDIDATE",
            "kill_flags": ["decay"],
        }
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert result["situation"] == "STRUCTURAL_FAIL"

    def test_edge_decay(self, config, perfect_signals):
        signals = {
            **perfect_signals,
            "half_life_status": "DECAYING",
            "kill_flags": [],
        }
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert result["situation"] == "EDGE_DECAY"

    def test_healthy_situation(self, config, perfect_signals):
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(perfect_signals)

        assert result["situation"] == "HEALTHY"


class TestConfidenceAndUncertainty:
    """Test data completeness and borderline detection."""

    def test_full_confidence(self, config, perfect_signals):
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(perfect_signals)

        assert result["confidence"] == 1.0

    def test_partial_confidence(self, config):
        # Only provide 4 of 6 data fields
        signals = {
            "regime_fit_level": "preferred",
            "half_life_status": "HEALTHY",
            "marginal_sharpe": 0.10,
            "max_correlation": 0.10,
            # missing: health_status, kill_flags
        }
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert result["confidence"] == pytest.approx(4 / 6, abs=0.02)

    def test_uncertainty_near_threshold(self, config):
        """Score near FULL_ON boundary should flag uncertainty."""
        # Craft signals to land near 0.70
        signals = {
            "regime_fit_level": "allowed",    # 0.6
            "half_life_status": "HEALTHY",    # 1.0
            "marginal_sharpe": 0.06,          # 1.0
            "max_correlation": 0.10,          # 1.0
            "same_exposure_cluster": False,
            "health_status": "PASS",          # 1.0
            "kill_flags": [],                 # 1.0
            "session_drift_severity": "NORMAL",  # 1.0
            "time_fit": "match",              # 1.0
            "asset_fit": "good",              # 1.0
            "recent_sharpe": 2.0,             # 1.0
        }
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        # Score should be near a threshold — if it's within 0.05 of any, uncertainty=True
        thresholds = [config["action_thresholds"][k] for k in config["action_thresholds"]]
        near_threshold = any(abs(result["activation_score"] - t) < 0.05 for t in thresholds)
        assert result["uncertainty"] == near_threshold


class TestReasonCodeDeterminism:
    """Verify expected reason codes for representative scenarios."""

    def test_preferred_regime_emits_high_match(self, config, perfect_signals):
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(perfect_signals)

        assert ReasonCode.REGIME_MATCH_HIGH in result["reason_codes"]

    def test_avoid_regime_emits_mismatch(self, config, perfect_signals):
        signals = {**perfect_signals, "regime_fit_level": "avoid"}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert ReasonCode.REGIME_MISMATCH in result["reason_codes"]

    def test_dilutive_contribution_emits_dilution(self, config, perfect_signals):
        signals = {**perfect_signals, "marginal_sharpe": -0.10}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert ReasonCode.PORTFOLIO_DILUTION in result["reason_codes"]

    def test_session_concentration_emits_code(self, config, perfect_signals):
        signals = {**perfect_signals, "session_concentration": True}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert ReasonCode.SESSION_CONCENTRATION in result["reason_codes"]

    def test_session_drift_alarm_emits_broken(self, config, perfect_signals):
        signals = {**perfect_signals, "session_drift_severity": "ALARM"}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert ReasonCode.SESSION_DRIFT_BROKEN in result["reason_codes"]

    def test_recent_collapse_emits_code(self, config, perfect_signals):
        signals = {**perfect_signals, "recent_sharpe": -1.0}
        scorer = ActivationScorer(config)
        result = scorer.score_strategy(signals)

        assert ReasonCode.RECENT_COLLAPSE in result["reason_codes"]


class TestContributionThresholds:
    """Parametrize contribution scoring at key thresholds."""

    @pytest.mark.parametrize("sharpe,expected_score,expected_code", [
        (0.10, 1.0, ReasonCode.PORTFOLIO_ADDS_VALUE),
        (0.02, 0.7, ReasonCode.PORTFOLIO_ADDS_VALUE),
        (-0.02, 0.4, ReasonCode.PORTFOLIO_NEUTRAL),
        (-0.10, 0.0, ReasonCode.PORTFOLIO_DILUTION),
    ])
    def test_contribution_score_and_code(self, config, sharpe, expected_score, expected_code):
        scorer = ActivationScorer(config)
        score, codes = scorer._score_contribution({"marginal_sharpe": sharpe})

        assert score == expected_score
        assert expected_code in codes


class TestSessionDrift:
    """Test session drift scoring with concentration penalty."""

    def test_normal_no_concentration(self, config):
        scorer = ActivationScorer(config)
        score, codes = scorer._score_session_drift({
            "session_drift_severity": "NORMAL",
            "session_concentration": False,
        })
        assert score == 1.0
        assert ReasonCode.SESSION_DRIFT_NORMAL in codes

    def test_normal_with_concentration(self, config):
        scorer = ActivationScorer(config)
        penalty = config["session_drift"]["concentration_penalty"]
        score, codes = scorer._score_session_drift({
            "session_drift_severity": "NORMAL",
            "session_concentration": True,
        })
        assert score == pytest.approx(1.0 - penalty, abs=0.01)
        assert ReasonCode.SESSION_CONCENTRATION in codes

    def test_alarm_severity(self, config):
        scorer = ActivationScorer(config)
        score, codes = scorer._score_session_drift({
            "session_drift_severity": "ALARM",
            "session_concentration": False,
        })
        assert score == 0.0
        assert ReasonCode.SESSION_DRIFT_BROKEN in codes
