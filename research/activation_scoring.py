"""FQL Activation Scoring Model — Per-strategy composite score.

Combines 9 weighted sub-scores into a single activation score [0, 1].
Each sub-score is normalized to [0, 1] and explicitly interpretable.

Sub-scores:
    1. Regime Fit (0.20)      — current regime vs strategy specialization
    2. Half-Life (0.20)       — edge trend (strengthening/stable/decaying)
    3. Contribution (0.15)    — portfolio Sharpe improvement or dilution
    4. Redundancy (0.10)      — overlap with other active strategies
    5. Health (0.10)          — automated integrity checks
    6. Kill Criteria (0.10)   — triggered warnings or kills
    7. Time-of-Day (0.05)     — session alignment
    8. Asset Fit (0.05)       — asset conditions match
    9. Recent Stability (0.05)— short-window robustness

Usage:
    from research.activation_scoring import ActivationScorer

    scorer = ActivationScorer(config)
    result = scorer.score_strategy(strategy_signals)
"""

import yaml
from pathlib import Path

from research.reason_codes import ReasonCode

CONFIG_PATH = Path(__file__).parent / "controller_config.yaml"


def load_config() -> dict:
    """Load controller configuration from YAML."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


class ActivationScorer:
    """Compute composite activation score for a strategy."""

    def __init__(self, config: dict = None):
        self.config = config or load_config()
        self.weights = self.config["scoring_weights"]

    def score_strategy(self, signals: dict) -> dict:
        """Compute activation score and reason codes for a single strategy.

        Parameters
        ----------
        signals : dict
            Input signals (see score_* methods for required keys).

        Returns
        -------
        dict with:
            - activation_score: float (0-1)
            - sub_scores: dict of individual dimension scores
            - reason_codes: list of ReasonCode strings
            - recommended_action: str
            - confidence: float (0-1, based on data completeness)
        """
        sub_scores = {}
        reason_codes = []

        # Score each dimension
        sub_scores["regime_fit"], rc = self._score_regime_fit(signals)
        reason_codes.extend(rc)

        sub_scores["half_life"], rc = self._score_half_life(signals)
        reason_codes.extend(rc)

        sub_scores["contribution"], rc = self._score_contribution(signals)
        reason_codes.extend(rc)

        sub_scores["redundancy"], rc = self._score_redundancy(signals)
        reason_codes.extend(rc)

        sub_scores["health"], rc = self._score_health(signals)
        reason_codes.extend(rc)

        sub_scores["kill_criteria"], rc = self._score_kill_criteria(signals)
        reason_codes.extend(rc)

        sub_scores["time_of_day"], rc = self._score_time_of_day(signals)
        reason_codes.extend(rc)

        sub_scores["asset_fit"], rc = self._score_asset_fit(signals)
        reason_codes.extend(rc)

        sub_scores["recent_stability"], rc = self._score_recent_stability(signals)
        reason_codes.extend(rc)

        # Weighted composite
        activation_score = sum(
            sub_scores[dim] * self.weights[dim]
            for dim in self.weights
        )
        activation_score = round(min(1.0, max(0.0, activation_score)), 4)

        # Map to action
        recommended_action = self._map_to_action(activation_score)

        # Confidence based on data completeness
        data_fields = [
            "regime_fit_level", "half_life_status", "marginal_sharpe",
            "max_correlation", "health_status", "kill_flags",
        ]
        present = sum(1 for f in data_fields if f in signals and signals[f] is not None)
        confidence = round(present / len(data_fields), 2)

        return {
            "activation_score": activation_score,
            "sub_scores": sub_scores,
            "reason_codes": reason_codes,
            "recommended_action": recommended_action,
            "confidence": confidence,
        }

    # ── Individual Dimension Scorers ─────────────────────────────────────

    def _score_regime_fit(self, signals: dict) -> tuple[float, list]:
        """Score regime fit: how well current regime matches strategy niche."""
        cfg = self.config["regime_fit"]
        level = signals.get("regime_fit_level", "neutral")

        score_map = {
            "preferred": cfg["preferred_match_score"],
            "allowed": cfg["allowed_match_score"],
            "neutral": cfg["neutral_score"],
            "avoid": cfg["avoid_score"],
        }
        score = score_map.get(level, cfg["neutral_score"])

        codes = []
        if score >= 0.8:
            codes.append(ReasonCode.REGIME_MATCH_HIGH)
        elif score >= 0.5:
            codes.append(ReasonCode.REGIME_MATCH_MODERATE)
        elif score > 0.0:
            codes.append(ReasonCode.REGIME_MATCH_LOW)
        else:
            codes.append(ReasonCode.REGIME_MISMATCH)

        return score, codes

    def _score_half_life(self, signals: dict) -> tuple[float, list]:
        """Score half-life trend: strengthening/stable/decaying."""
        cfg = self.config["half_life"]
        status = signals.get("half_life_status", "HEALTHY")

        score = cfg.get(status, 0.5)
        codes = []

        if status == "HEALTHY":
            trend = signals.get("sharpe_trend", "STABLE")
            if trend == "IMPROVING":
                codes.append(ReasonCode.HALF_LIFE_STRENGTHENING)
            else:
                codes.append(ReasonCode.HALF_LIFE_STABLE)
        elif status == "MONITOR":
            codes.append(ReasonCode.HALF_LIFE_MONITOR)
        elif status == "DECAYING":
            codes.append(ReasonCode.HALF_LIFE_DECAY)
        elif status == "ARCHIVE_CANDIDATE":
            codes.append(ReasonCode.HALF_LIFE_DEAD)

        return score, codes

    def _score_contribution(self, signals: dict) -> tuple[float, list]:
        """Score portfolio contribution: adds value / neutral / dilutive."""
        cfg = self.config["contribution"]
        marginal = signals.get("marginal_sharpe", 0.0)

        if marginal > cfg["strong_positive_threshold"]:
            score = 1.0
            codes = [ReasonCode.PORTFOLIO_ADDS_VALUE]
        elif marginal > cfg["weak_positive_threshold"]:
            score = 0.7
            codes = [ReasonCode.PORTFOLIO_ADDS_VALUE]
        elif marginal > cfg["dilutive_threshold"]:
            score = 0.4
            codes = [ReasonCode.PORTFOLIO_NEUTRAL]
        else:
            score = 0.0
            codes = [ReasonCode.PORTFOLIO_DILUTION]

        return score, codes

    def _score_redundancy(self, signals: dict) -> tuple[float, list]:
        """Score redundancy: overlap with active strategies."""
        cfg = self.config["redundancy"]
        max_corr = signals.get("max_correlation", 0.0)
        same_cluster = signals.get("same_exposure_cluster", False)

        if max_corr > cfg["high_correlation_threshold"]:
            score = 0.2
        elif max_corr > cfg["moderate_correlation_threshold"]:
            score = 0.5
        else:
            score = 1.0

        if same_cluster:
            score = max(0.0, score - cfg["same_cluster_penalty"])

        codes = []
        if score < 0.5:
            codes.append(ReasonCode.REDUNDANT_CLUSTER)
        else:
            codes.append(ReasonCode.LOW_REDUNDANCY)

        return round(score, 2), codes

    def _score_health(self, signals: dict) -> tuple[float, list]:
        """Score health check status."""
        status = signals.get("health_status", "PASS")
        if status == "PASS":
            return 1.0, [ReasonCode.HEALTH_PASS]
        elif status == "WARN":
            return 0.6, [ReasonCode.HEALTH_WARN]
        else:
            return 0.0, [ReasonCode.HEALTH_FAIL]

    def _score_kill_criteria(self, signals: dict) -> tuple[float, list]:
        """Score kill criteria state."""
        cfg = self.config["kill_criteria"]
        flags = signals.get("kill_flags", [])

        if len(flags) == 0:
            return cfg["no_flags_score"], [ReasonCode.KILL_NONE]
        elif len(flags) == 1:
            return cfg["soft_flag_score"], [ReasonCode.KILL_TRIGGER_SOFT]
        else:
            return cfg["hard_flag_score"], [ReasonCode.KILL_TRIGGER_HARD]

    def _score_time_of_day(self, signals: dict) -> tuple[float, list]:
        """Score time-of-day fit."""
        level = signals.get("time_fit", "match")
        if level == "match":
            return 1.0, [ReasonCode.TIME_WINDOW_MATCH]
        elif level == "partial":
            return 0.5, [ReasonCode.TIME_WINDOW_PARTIAL]
        else:
            return 0.0, [ReasonCode.TIME_WINDOW_MISMATCH]

    def _score_asset_fit(self, signals: dict) -> tuple[float, list]:
        """Score asset suitability."""
        fit = signals.get("asset_fit", "good")
        if fit == "good":
            return 1.0, [ReasonCode.ASSET_FIT_GOOD]
        else:
            return 0.3, [ReasonCode.ASSET_FIT_POOR]

    def _score_recent_stability(self, signals: dict) -> tuple[float, list]:
        """Score short-window robustness."""
        recent_sharpe = signals.get("recent_sharpe", 1.0)
        cfg = self.config["recent_stability"]

        if recent_sharpe <= cfg["sharpe_collapse_threshold"]:
            return 0.0, [ReasonCode.RECENT_COLLAPSE]
        elif recent_sharpe <= cfg["sharpe_volatile_threshold"]:
            return 0.4, [ReasonCode.RECENT_VOLATILE]
        else:
            return 1.0, [ReasonCode.RECENT_STABLE]

    # ── Action Mapping ───────────────────────────────────────────────────

    def _map_to_action(self, score: float) -> str:
        """Map composite score to recommended action."""
        thresholds = self.config["action_thresholds"]
        if score >= thresholds["FULL_ON"]:
            return "FULL_ON"
        elif score >= thresholds["REDUCED_ON"]:
            return "REDUCED_ON"
        elif score >= thresholds["PROBATION"]:
            return "PROBATION"
        elif score >= thresholds["OFF"]:
            return "OFF"
        elif score >= thresholds["DISABLE"]:
            return "DISABLE"
        else:
            return "ARCHIVE_REVIEW"
