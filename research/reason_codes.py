"""FQL Reason Codes — Explicit tags for controller decisions.

Every controller decision carries one or more reason codes instead of
free-text commentary.  Downstream automation and reports consume these
directly.

Usage:
    from research.reason_codes import ReasonCode, REASON_DESCRIPTIONS
"""


class ReasonCode:
    """Namespace of all controller reason codes."""

    # ── Regime Fit ────────────────────────────────────────────────────────
    REGIME_MATCH_HIGH = "REGIME_MATCH_HIGH"
    REGIME_MATCH_MODERATE = "REGIME_MATCH_MODERATE"
    REGIME_MATCH_LOW = "REGIME_MATCH_LOW"
    REGIME_MISMATCH = "REGIME_MISMATCH"

    # ── Half-Life / Edge Decay ────────────────────────────────────────────
    HALF_LIFE_STRENGTHENING = "HALF_LIFE_STRENGTHENING"
    HALF_LIFE_STABLE = "HALF_LIFE_STABLE"
    HALF_LIFE_MONITOR = "HALF_LIFE_MONITOR"
    HALF_LIFE_DECAY = "HALF_LIFE_DECAY"
    HALF_LIFE_DEAD = "HALF_LIFE_DEAD"

    # ── Portfolio Contribution ────────────────────────────────────────────
    PORTFOLIO_ADDS_VALUE = "PORTFOLIO_ADDS_VALUE"
    PORTFOLIO_NEUTRAL = "PORTFOLIO_NEUTRAL"
    PORTFOLIO_DILUTION = "PORTFOLIO_DILUTION"

    # ── Redundancy / Clustering ───────────────────────────────────────────
    REDUNDANT_CLUSTER = "REDUNDANT_CLUSTER"
    LOW_REDUNDANCY = "LOW_REDUNDANCY"

    # ── Health ────────────────────────────────────────────────────────────
    HEALTH_PASS = "HEALTH_PASS"
    HEALTH_WARN = "HEALTH_WARN"
    HEALTH_FAIL = "HEALTH_FAIL"

    # ── Kill Criteria ─────────────────────────────────────────────────────
    KILL_NONE = "KILL_NONE"
    KILL_TRIGGER_SOFT = "KILL_TRIGGER_SOFT"
    KILL_TRIGGER_HARD = "KILL_TRIGGER_HARD"

    # ── Time-of-Day ───────────────────────────────────────────────────────
    TIME_WINDOW_MATCH = "TIME_WINDOW_MATCH"
    TIME_WINDOW_PARTIAL = "TIME_WINDOW_PARTIAL"
    TIME_WINDOW_MISMATCH = "TIME_WINDOW_MISMATCH"

    # ── Asset ─────────────────────────────────────────────────────────────
    ASSET_FIT_GOOD = "ASSET_FIT_GOOD"
    ASSET_FIT_POOR = "ASSET_FIT_POOR"

    # ── Recent Stability ──────────────────────────────────────────────────
    RECENT_STABLE = "RECENT_STABLE"
    RECENT_VOLATILE = "RECENT_VOLATILE"
    RECENT_COLLAPSE = "RECENT_COLLAPSE"

    # ── Lifecycle / Resurrection ──────────────────────────────────────────
    RESURRECTION_SIGNAL = "RESURRECTION_SIGNAL"
    PROBATION_ENTRY = "PROBATION_ENTRY"
    ARCHIVE_CANDIDATE = "ARCHIVE_CANDIDATE"


REASON_DESCRIPTIONS = {
    ReasonCode.REGIME_MATCH_HIGH: "Current regime strongly matches strategy specialization",
    ReasonCode.REGIME_MATCH_MODERATE: "Current regime partially matches strategy niche",
    ReasonCode.REGIME_MATCH_LOW: "Current regime weakly aligns with strategy",
    ReasonCode.REGIME_MISMATCH: "Current regime does not match strategy specialization",
    ReasonCode.HALF_LIFE_STRENGTHENING: "Edge metrics improving in recent windows",
    ReasonCode.HALF_LIFE_STABLE: "Edge metrics stable across windows",
    ReasonCode.HALF_LIFE_MONITOR: "Minor edge deterioration detected",
    ReasonCode.HALF_LIFE_DECAY: "Significant edge decay in recent windows",
    ReasonCode.HALF_LIFE_DEAD: "Edge has collapsed — no viable signal remaining",
    ReasonCode.PORTFOLIO_ADDS_VALUE: "Strategy improves portfolio Sharpe/Calmar",
    ReasonCode.PORTFOLIO_NEUTRAL: "Marginal contribution near zero",
    ReasonCode.PORTFOLIO_DILUTION: "Strategy dilutes portfolio risk-adjusted returns",
    ReasonCode.REDUNDANT_CLUSTER: "High overlap with another active strategy in same cluster",
    ReasonCode.LOW_REDUNDANCY: "Low correlation with existing portfolio strategies",
    ReasonCode.HEALTH_PASS: "All automated integrity checks pass",
    ReasonCode.HEALTH_WARN: "Health check warnings — review needed",
    ReasonCode.HEALTH_FAIL: "Health check failures — data or config issue",
    ReasonCode.KILL_NONE: "No kill criteria triggered",
    ReasonCode.KILL_TRIGGER_SOFT: "Soft kill warning — one criterion flagged",
    ReasonCode.KILL_TRIGGER_HARD: "Hard kill — multiple criteria flagged or severe decay",
    ReasonCode.TIME_WINDOW_MATCH: "Current session matches preferred trading window",
    ReasonCode.TIME_WINDOW_PARTIAL: "Current session in allowed but not preferred window",
    ReasonCode.TIME_WINDOW_MISMATCH: "Outside strategy's trading window",
    ReasonCode.ASSET_FIT_GOOD: "Asset conditions match strategy design",
    ReasonCode.ASSET_FIT_POOR: "Asset conditions unfavorable for strategy",
    ReasonCode.RECENT_STABLE: "Short-window performance consistent with expectations",
    ReasonCode.RECENT_VOLATILE: "Short-window performance noisy but not collapsed",
    ReasonCode.RECENT_COLLAPSE: "Short-window performance severely deteriorated",
    ReasonCode.RESURRECTION_SIGNAL: "Archived strategy showing renewed strength",
    ReasonCode.PROBATION_ENTRY: "Strategy entering probation for review",
    ReasonCode.ARCHIVE_CANDIDATE: "Strategy flagged for potential archival",
}
