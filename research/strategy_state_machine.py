"""FQL Strategy State Machine — Formal lifecycle states and transition rules.

Every strategy has a current state, prior state, and transition history.
Transitions are driven by objective signals (activation score, kill flags,
half-life status, contribution data).

States:
    VALIDATED    — Passed validation battery, not yet paper-traded
    PAPER        — In paper/forward testing
    ACTIVE       — Full-size live deployment
    ACTIVE_REDUCED — Live but reduced allocation (dilutive, redundant, or decaying)
    PROBATION    — Meaningful weakness detected, under review
    DISABLED     — Taken offline pending resolution
    ARCHIVED     — Removed from active universe, preserved in registry
    RESURRECTION_CANDIDATE — Archived strategy showing renewed viability

Usage:
    from research.strategy_state_machine import StrategyStateMachine, VALID_STATES

    sm = StrategyStateMachine()
    result = sm.evaluate_transition("ACTIVE", signals)
    # result = {"new_state": "PROBATION", "reason_codes": [...], "trigger": "..."}
"""

from datetime import datetime

from research.reason_codes import ReasonCode

# ── Valid States ─────────────────────────────────────────────────────────────

VALID_STATES = [
    "VALIDATED",
    "PAPER",
    "ACTIVE",
    "ACTIVE_REDUCED",
    "PROBATION",
    "DISABLED",
    "ARCHIVED",
    "RESURRECTION_CANDIDATE",
]

# ── Valid Transitions ────────────────────────────────────────────────────────
# Maps current_state -> set of allowed next states.

VALID_TRANSITIONS = {
    "VALIDATED": {"PAPER", "ACTIVE", "PROBATION", "ARCHIVED"},
    "PAPER": {"ACTIVE", "PROBATION", "DISABLED", "ARCHIVED"},
    "ACTIVE": {"ACTIVE_REDUCED", "PROBATION", "DISABLED"},
    "ACTIVE_REDUCED": {"ACTIVE", "PROBATION", "DISABLED"},
    "PROBATION": {"ACTIVE", "ACTIVE_REDUCED", "DISABLED", "ARCHIVED"},
    "DISABLED": {"PROBATION", "ARCHIVED"},
    "ARCHIVED": {"RESURRECTION_CANDIDATE"},
    "RESURRECTION_CANDIDATE": {"PAPER", "PROBATION", "ARCHIVED"},
}


# ── State mapping from registry status to state machine states ───────────────

REGISTRY_STATUS_TO_STATE = {
    "core": "ACTIVE",
    "probation": "PROBATION",
    "testing": "PAPER",
    "idea": "VALIDATED",
    "rejected": "ARCHIVED",
    "retired": "ARCHIVED",
}


class StrategyStateMachine:
    """Evaluate state transitions based on objective signals.

    Does not mutate state — returns recommended transitions.
    The controller applies transitions after review.
    """

    def evaluate_transition(self, current_state: str, signals: dict) -> dict:
        """Determine if a state transition should occur.

        Parameters
        ----------
        current_state : str
            Current state from VALID_STATES.
        signals : dict
            Objective data driving the decision:
            - activation_score: float (0-1)
            - half_life_status: str (HEALTHY/MONITOR/DECAYING/ARCHIVE_CANDIDATE)
            - kill_flags: list of str (trigger names)
            - contribution_verdict: str (ADDS VALUE/NEUTRAL/DILUTIVE)
            - marginal_sharpe: float
            - health_status: str (PASS/WARN/FAIL)
            - recent_sharpe: float (6-month Sharpe)
            - regime_fit_score: float (0-1)
            - days_in_current_state: int

        Returns
        -------
        dict with:
            - new_state: str (same as current if no transition)
            - changed: bool
            - reason_codes: list of str
            - trigger: str (human-readable trigger description)
        """
        if current_state not in VALID_STATES:
            return {
                "new_state": current_state,
                "changed": False,
                "reason_codes": [],
                "trigger": f"Unknown state: {current_state}",
            }

        activation_score = signals.get("activation_score", 0.5)
        half_life = signals.get("half_life_status", "HEALTHY")
        kill_flags = signals.get("kill_flags", [])
        contribution = signals.get("contribution_verdict", "NEUTRAL")
        marginal_sharpe = signals.get("marginal_sharpe", 0.0)
        health = signals.get("health_status", "PASS")
        recent_sharpe = signals.get("recent_sharpe", 1.0)
        days_in_state = signals.get("days_in_current_state", 0)

        reason_codes = []
        new_state = current_state

        # ── Priority 1: Hard kill (multi-flag kill or dead + dilutive) ────
        # NOTE: Health failures reduce activation scores but do NOT trigger
        # hard kills — health is a system-level signal, not per-strategy.
        is_hard_kill = (
            len(kill_flags) >= 2
            or (half_life == "ARCHIVE_CANDIDATE" and contribution == "DILUTIVE")
        )

        if is_hard_kill and current_state in ("ACTIVE", "ACTIVE_REDUCED", "PAPER", "PROBATION"):
            new_state = "DISABLED"
            reason_codes.append(ReasonCode.KILL_TRIGGER_HARD)
            if health == "FAIL":
                reason_codes.append(ReasonCode.HEALTH_FAIL)
            if half_life == "ARCHIVE_CANDIDATE":
                reason_codes.append(ReasonCode.HALF_LIFE_DEAD)
            if contribution == "DILUTIVE":
                reason_codes.append(ReasonCode.PORTFOLIO_DILUTION)
            trigger = f"Hard kill: {len(kill_flags)} flags, health={health}, HL={half_life}"
            return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 2: Decay → probation ────────────────────────────────
        if current_state in ("ACTIVE", "ACTIVE_REDUCED"):
            if half_life in ("DECAYING", "ARCHIVE_CANDIDATE") and activation_score < 0.45:
                new_state = "PROBATION"
                reason_codes.append(ReasonCode.HALF_LIFE_DECAY)
                reason_codes.append(ReasonCode.PROBATION_ENTRY)
                trigger = f"Edge decay: HL={half_life}, score={activation_score:.2f}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 3: Dilution → reduced ───────────────────────────────
        if current_state == "ACTIVE":
            if contribution == "DILUTIVE" and half_life in ("HEALTHY", "MONITOR"):
                new_state = "ACTIVE_REDUCED"
                reason_codes.append(ReasonCode.PORTFOLIO_DILUTION)
                trigger = f"Dilutive: marginal_sharpe={marginal_sharpe:+.3f}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 4: Soft kill → probation ────────────────────────────
        if current_state in ("ACTIVE", "ACTIVE_REDUCED"):
            if len(kill_flags) == 1 and activation_score < 0.50:
                new_state = "PROBATION"
                reason_codes.append(ReasonCode.KILL_TRIGGER_SOFT)
                reason_codes.append(ReasonCode.PROBATION_ENTRY)
                trigger = f"Soft kill: {kill_flags[0]}, score={activation_score:.2f}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 5: Recovery from probation ──────────────────────────
        if current_state == "PROBATION":
            if activation_score >= 0.65 and half_life == "HEALTHY" and len(kill_flags) == 0:
                new_state = "ACTIVE"
                reason_codes.append(ReasonCode.HALF_LIFE_STRENGTHENING)
                trigger = f"Recovery: score={activation_score:.2f}, HL={half_life}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 6: Recovery from reduced ────────────────────────────
        if current_state == "ACTIVE_REDUCED":
            if contribution != "DILUTIVE" and activation_score >= 0.65:
                new_state = "ACTIVE"
                reason_codes.append(ReasonCode.PORTFOLIO_ADDS_VALUE)
                trigger = f"No longer dilutive: score={activation_score:.2f}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 7: Probation → disabled (stale) ────────────────────
        if current_state == "PROBATION":
            if days_in_state > 90 and activation_score < 0.35:
                new_state = "DISABLED"
                reason_codes.append(ReasonCode.ARCHIVE_CANDIDATE)
                trigger = f"Stale probation: {days_in_state}d, score={activation_score:.2f}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 8: Disabled → archived ──────────────────────────────
        if current_state == "DISABLED":
            if days_in_state > 30 and activation_score < 0.25:
                new_state = "ARCHIVED"
                reason_codes.append(ReasonCode.ARCHIVE_CANDIDATE)
                trigger = f"Archive: disabled {days_in_state}d, score={activation_score:.2f}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── Priority 9: Resurrection ─────────────────────────────────────
        if current_state == "ARCHIVED":
            if half_life in ("HEALTHY", "MONITOR") and recent_sharpe > 1.0:
                new_state = "RESURRECTION_CANDIDATE"
                reason_codes.append(ReasonCode.RESURRECTION_SIGNAL)
                trigger = f"Resurrection signal: HL={half_life}, recent_sharpe={recent_sharpe:.2f}"
                return self._result(current_state, new_state, reason_codes, trigger)

        # ── No transition ────────────────────────────────────────────────
        return {
            "new_state": current_state,
            "changed": False,
            "reason_codes": [],
            "trigger": "No transition — current state appropriate",
        }

    def _result(self, old: str, new: str, codes: list, trigger: str) -> dict:
        allowed = VALID_TRANSITIONS.get(old, set())
        if new not in allowed and new != old:
            return {
                "new_state": old,
                "changed": False,
                "reason_codes": codes,
                "trigger": f"BLOCKED: {old}->{new} not allowed. {trigger}",
            }
        return {
            "new_state": new,
            "changed": old != new,
            "reason_codes": codes,
            "trigger": trigger,
        }

    @staticmethod
    def create_state_history_entry(
        strategy_id: str,
        old_state: str,
        new_state: str,
        reason_codes: list,
        trigger: str,
    ) -> dict:
        """Create a state transition log entry."""
        return {
            "strategy_id": strategy_id,
            "timestamp": datetime.now().isoformat(),
            "from_state": old_state,
            "to_state": new_state,
            "reason_codes": reason_codes,
            "trigger": trigger,
        }
