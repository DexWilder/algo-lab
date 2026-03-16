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

    # ── Session Drift ────────────────────────────────────────────────────
    SESSION_DRIFT_NORMAL = "SESSION_DRIFT_NORMAL"
    SESSION_DRIFT_DEGRADED = "SESSION_DRIFT_DEGRADED"
    SESSION_DRIFT_BROKEN = "SESSION_DRIFT_BROKEN"
    SESSION_CONCENTRATION = "SESSION_CONCENTRATION"

    # ── Lifecycle / Resurrection ──────────────────────────────────────────
    RESURRECTION_SIGNAL = "RESURRECTION_SIGNAL"
    PROBATION_ENTRY = "PROBATION_ENTRY"
    ARCHIVE_CANDIDATE = "ARCHIVE_CANDIDATE"

    # ── Allocation Tiers ────────────────────────────────────────────────
    ALLOC_BASE_FROM_ACTION = "ALLOC_BASE_FROM_ACTION"
    ALLOC_CONTRIB_BOOST = "ALLOC_CONTRIB_BOOST"
    ALLOC_CONTRIB_DILUTIVE_CAP = "ALLOC_CONTRIB_DILUTIVE_CAP"
    ALLOC_CF_BOOST = "ALLOC_CF_BOOST"
    ALLOC_CF_CAP = "ALLOC_CF_CAP"
    ALLOC_CF_REMOVE_CAP = "ALLOC_CF_REMOVE_CAP"
    ALLOC_CROWDING_CAP = "ALLOC_CROWDING_CAP"
    ALLOC_CROWDING_WEAKER = "ALLOC_CROWDING_WEAKER"
    ALLOC_SESSION_BLOCK = "ALLOC_SESSION_BLOCK"
    ALLOC_SESSION_REDUCE = "ALLOC_SESSION_REDUCE"
    ALLOC_PRIMARY_SESSION_BLOCKED = "ALLOC_PRIMARY_SESSION_BLOCKED"
    ALLOC_HARD_RESTRICTED = "ALLOC_HARD_RESTRICTED"
    ALLOC_MAX_BOOST_CAP = "ALLOC_MAX_BOOST_CAP"


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
    ReasonCode.SESSION_DRIFT_NORMAL: "No session-specific degradation detected",
    ReasonCode.SESSION_DRIFT_DEGRADED: "Session-specific edge degradation — deployment restricted",
    ReasonCode.SESSION_DRIFT_BROKEN: "Session edge structurally broken — block deployment in affected session",
    ReasonCode.SESSION_CONCENTRATION: "Portfolio trade volume concentrated in one session window",
    ReasonCode.RESURRECTION_SIGNAL: "Archived strategy showing renewed strength",
    ReasonCode.PROBATION_ENTRY: "Strategy entering probation for review",
    ReasonCode.ARCHIVE_CANDIDATE: "Strategy flagged for potential archival",
    ReasonCode.ALLOC_BASE_FROM_ACTION: "Base allocation tier derived from controller action",
    ReasonCode.ALLOC_CONTRIB_BOOST: "Tier boosted due to strong portfolio contribution",
    ReasonCode.ALLOC_CONTRIB_DILUTIVE_CAP: "Tier capped due to dilutive contribution",
    ReasonCode.ALLOC_CF_BOOST: "Tier boosted by positive counterfactual score",
    ReasonCode.ALLOC_CF_CAP: "Tier reduced by negative counterfactual score",
    ReasonCode.ALLOC_CF_REMOVE_CAP: "Tier capped at MICRO due to counterfactual REMOVE recommendation",
    ReasonCode.ALLOC_CROWDING_CAP: "Tier capped due to exposure cluster crowding",
    ReasonCode.ALLOC_CROWDING_WEAKER: "Tier reduced as weaker strategy in crowded cluster",
    ReasonCode.ALLOC_SESSION_BLOCK: "Session forced to OFF due to ALARM-level drift",
    ReasonCode.ALLOC_SESSION_REDUCE: "Session tier reduced due to DRIFT-level degradation",
    ReasonCode.ALLOC_PRIMARY_SESSION_BLOCKED: "Global tier capped because primary session is blocked",
    ReasonCode.ALLOC_HARD_RESTRICTED: "Strategy is OFF due to hard restriction (DISABLED/ARCHIVED)",
    ReasonCode.ALLOC_MAX_BOOST_CAP: "Tier boost capped at maximum allowed above base",
}
