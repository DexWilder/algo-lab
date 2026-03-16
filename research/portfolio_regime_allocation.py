"""FQL Portfolio Regime Allocation -- Per-strategy per-session sizing tiers.

Sits AFTER the Portfolio Regime Controller's activation scoring and state
machine decisions. Takes the controller's recommended_action and adjusts
it into a multi-tier allocation based on contribution, counterfactual,
crowding, and session drift signals.

Allocation is purely additive -- it NEVER overrides hard restrictions.
If the controller says OFF, allocation stays OFF.

5-stage pipeline:
    1. Base tier from controller action
    2. Contribution/counterfactual adjustments
    3. Crowding dampening
    4. Session-specific allocation
    5. Final validation

Usage:
    from research.portfolio_regime_allocation import AllocationEngine

    engine = AllocationEngine(config)
    allocations = engine.compute_allocations(
        activation_matrix=matrix,
        contribution_signals=contrib,
        counterfactual=cf_data,
        session_drift_signals=drift,
        crowding_signals=crowding,
    )
"""

import json
from datetime import datetime
from pathlib import Path

from research.allocation_tiers import (
    OFF, MICRO, REDUCED, BASE, BOOST, MAX_ALLOWED,
    ACTION_TO_BASE_TIER, TIER_NAMES, TIER_VALUES,
    tier_name, tier_up, tier_down, clamp_tier,
)
from research.reason_codes import ReasonCode
from research.utils.atomic_io import atomic_write_json

ROOT = Path(__file__).resolve().parent.parent
ALLOCATION_MATRIX_PATH = ROOT / "research" / "data" / "allocation_matrix.json"

SESSIONS = ["morning", "midday", "afternoon"]


class AllocationEngine:
    """Compute per-strategy per-session allocation tiers."""

    def __init__(self, config: dict):
        self.config = config
        self.alloc_cfg = config.get("allocation", {})
        self.max_boost = self.alloc_cfg.get("max_boost_above_base", 2)

    def compute_allocations(
        self,
        activation_matrix: list,
        contribution_signals: dict = None,
        counterfactual: dict = None,
        session_drift_signals: dict = None,
        crowding_signals: dict = None,
    ) -> dict:
        """Compute allocation tiers for all strategies.

        Returns dict keyed by strategy_id, each containing:
            - base_tier / base_tier_name
            - target_tier / target_tier_name (after adjustments, before session split)
            - sessions: {session: {tier, tier_name, reason_codes}}
            - adjustments: list of {stage, direction, reason}
            - hard_restricted: bool
            - reason_codes: list
        """
        contribution_signals = contribution_signals or {}
        counterfactual = counterfactual or {}
        session_drift_signals = session_drift_signals or {}
        crowding_signals = crowding_signals or {}

        allocations = {}

        for entry in activation_matrix:
            sid = entry["strategy_id"]
            action = entry["recommended_action"]
            state = entry.get("new_state", entry.get("current_state", "ACTIVE"))

            alloc = self._allocate_strategy(
                sid, action, state, entry, contribution_signals,
                counterfactual, session_drift_signals, crowding_signals,
            )
            allocations[sid] = alloc

        # Stage 3: Crowding dampening (cross-strategy, must run after individual allocations)
        self._apply_crowding(allocations, activation_matrix, crowding_signals)

        # Stage 5: Final validation
        self._validate(allocations, activation_matrix)

        return allocations

    def _allocate_strategy(
        self, sid, action, state, entry, contribution, counterfactual,
        session_drift, crowding,
    ) -> dict:
        """Compute allocation for a single strategy."""
        adjustments = []
        reason_codes = []

        # ---- Stage 1: Base tier from controller action ----
        hard_restricted = action in ("OFF", "DISABLE", "ARCHIVE_REVIEW") or \
                          state in ("DISABLED", "ARCHIVED")

        base_tier = ACTION_TO_BASE_TIER.get(action, OFF)
        reason_codes.append(ReasonCode.ALLOC_BASE_FROM_ACTION)

        if hard_restricted:
            reason_codes.append(ReasonCode.ALLOC_HARD_RESTRICTED)
            return self._build_result(
                sid, base_tier, OFF, hard_restricted, reason_codes, adjustments,
                session_drift,
            )

        current_tier = base_tier

        # ---- Stage 2a: Contribution adjustments ----
        contrib_cfg = self.alloc_cfg.get("contribution", {})
        contrib_data = contribution.get(sid, {})
        verdict = contrib_data.get("verdict", entry.get("_signals", {}).get(
            "contribution_verdict", "NEUTRAL"
        ))
        marginal_sharpe = contrib_data.get("marginal_sharpe")

        if verdict == "DILUTIVE":
            cap_name = contrib_cfg.get("dilutive_cap_tier", "REDUCED")
            cap = TIER_VALUES.get(cap_name, REDUCED)
            if current_tier > cap:
                current_tier = cap
                adjustments.append({
                    "stage": "contribution",
                    "direction": "CAP",
                    "reason": f"Dilutive contribution, capped at {cap_name}",
                })
                reason_codes.append(ReasonCode.ALLOC_CONTRIB_DILUTIVE_CAP)
        elif verdict == "ADDS VALUE" or (marginal_sharpe is not None and marginal_sharpe > contrib_cfg.get("boost_marginal_sharpe", 0.10)):
            current_tier = tier_up(current_tier, 1)
            adjustments.append({
                "stage": "contribution",
                "direction": "UP",
                "reason": f"Strong contribution (marginal_sharpe={marginal_sharpe})",
            })
            reason_codes.append(ReasonCode.ALLOC_CONTRIB_BOOST)

        # ---- Stage 2b: Counterfactual adjustments ----
        cf_cfg = self.alloc_cfg.get("counterfactual", {})
        cf_data = counterfactual.get(sid, {})
        cf_score = cf_data.get("counterfactual_score")
        cf_rec = cf_data.get("recommendation")

        if cf_score is not None:
            if cf_rec == "REMOVE":
                cap_name = cf_cfg.get("remove_cap_tier", "MICRO")
                cap = TIER_VALUES.get(cap_name, MICRO)
                current_tier = min(current_tier, cap)
                adjustments.append({
                    "stage": "counterfactual",
                    "direction": "CAP",
                    "reason": f"CF recommendation=REMOVE (score={cf_score:.2f})",
                })
                reason_codes.append(ReasonCode.ALLOC_CF_REMOVE_CAP)
            elif cf_score >= cf_cfg.get("boost_threshold", 0.30):
                current_tier = tier_up(current_tier, 1)
                adjustments.append({
                    "stage": "counterfactual",
                    "direction": "UP",
                    "reason": f"Positive CF score={cf_score:.2f}",
                })
                reason_codes.append(ReasonCode.ALLOC_CF_BOOST)
            elif cf_score < cf_cfg.get("cap_threshold", -0.15):
                current_tier = tier_down(current_tier, 1)
                adjustments.append({
                    "stage": "counterfactual",
                    "direction": "DOWN",
                    "reason": f"Negative CF score={cf_score:.2f}",
                })
                reason_codes.append(ReasonCode.ALLOC_CF_CAP)

        # ---- Enforce max boost above base ----
        if current_tier > base_tier + self.max_boost:
            current_tier = base_tier + self.max_boost
            adjustments.append({
                "stage": "max_boost_cap",
                "direction": "CAP",
                "reason": f"Capped at {self.max_boost} tiers above base",
            })
            reason_codes.append(ReasonCode.ALLOC_MAX_BOOST_CAP)

        return self._build_result(
            sid, base_tier, current_tier, hard_restricted, reason_codes,
            adjustments, session_drift,
        )

    def _build_result(
        self, sid, base_tier, global_tier, hard_restricted, reason_codes,
        adjustments, session_drift_signals,
    ) -> dict:
        """Build the allocation result dict with per-session tiers."""
        # ---- Stage 4: Session-specific allocation ----
        sessions = {}
        sess_cfg = self.alloc_cfg.get("sessions", {})
        drift_data = session_drift_signals.get(sid, {})
        restricted_sessions = drift_data.get("restricted_sessions", [])
        session_details = drift_data.get("session_details", {})

        primary_session = drift_data.get("primary_session")
        primary_blocked = False

        for sess in SESSIONS:
            sess_tier = global_tier
            sess_codes = []

            if hard_restricted:
                sess_tier = OFF
                sess_codes.append(ReasonCode.ALLOC_HARD_RESTRICTED)
            else:
                # Check session-level drift
                sess_info = session_details.get(sess, {})
                severity = sess_info.get("severity", "NORMAL")

                if severity == "ALARM" or sess in restricted_sessions:
                    alarm_tier_name = sess_cfg.get("alarm_action", "OFF")
                    sess_tier = TIER_VALUES.get(alarm_tier_name, OFF)
                    sess_codes.append(ReasonCode.ALLOC_SESSION_BLOCK)
                    adjustments.append({
                        "stage": "session_drift",
                        "session": sess,
                        "direction": "BLOCK",
                        "reason": f"ALARM in {sess}",
                    })
                    if sess == primary_session:
                        primary_blocked = True
                elif severity == "DRIFT":
                    steps = sess_cfg.get("drift_steps_down", 1)
                    sess_tier = tier_down(sess_tier, steps)
                    sess_codes.append(ReasonCode.ALLOC_SESSION_REDUCE)
                    adjustments.append({
                        "stage": "session_drift",
                        "session": sess,
                        "direction": "DOWN",
                        "reason": f"DRIFT in {sess}",
                    })

            sessions[sess] = {
                "tier": sess_tier,
                "tier_name": tier_name(sess_tier),
                "reason_codes": sess_codes,
            }

        # If primary session is blocked, cap global tier
        if primary_blocked and not hard_restricted:
            cap_name = sess_cfg.get("primary_session_blocked_cap", "MICRO")
            cap = TIER_VALUES.get(cap_name, MICRO)
            if global_tier > cap:
                global_tier = cap
                reason_codes.append(ReasonCode.ALLOC_PRIMARY_SESSION_BLOCKED)
                adjustments.append({
                    "stage": "primary_session_blocked",
                    "direction": "CAP",
                    "reason": f"Primary session ({primary_session}) is blocked",
                })
                # Recompute non-blocked session tiers with capped global
                for sess in SESSIONS:
                    if sessions[sess]["tier"] > global_tier:
                        # Only cap non-blocked sessions
                        if ReasonCode.ALLOC_SESSION_BLOCK not in sessions[sess]["reason_codes"]:
                            sessions[sess]["tier"] = global_tier
                            sessions[sess]["tier_name"] = tier_name(global_tier)

        return {
            "strategy_id": sid,
            "base_tier": base_tier,
            "base_tier_name": tier_name(base_tier),
            "target_tier": global_tier,
            "target_tier_name": tier_name(global_tier),
            "final_tier": global_tier,
            "final_tier_name": tier_name(global_tier),
            "sessions": sessions,
            "hard_restricted": hard_restricted,
            "reason_codes": reason_codes,
            "adjustments": adjustments,
        }

    def _apply_crowding(self, allocations, activation_matrix, crowding_signals):
        """Stage 3: Cross-strategy crowding dampening."""
        crowd_cfg = self.alloc_cfg.get("crowding", {})
        threshold = crowd_cfg.get("exposure_crowd_threshold", 3)
        cap_name = crowd_cfg.get("exposure_crowd_cap", "BASE")
        cap = TIER_VALUES.get(cap_name, BASE)

        # Group active strategies by exposure cluster
        exposure_groups = {}
        for entry in activation_matrix:
            sid = entry["strategy_id"]
            alloc = allocations.get(sid)
            if not alloc or alloc["hard_restricted"]:
                continue
            exposure = entry.get("primary_exposure", "unknown")
            exposure_groups.setdefault(exposure, []).append(sid)

        # Cap crowded clusters
        for exposure, sids in exposure_groups.items():
            if len(sids) >= threshold:
                for sid in sids:
                    alloc = allocations[sid]
                    if alloc["target_tier"] > cap:
                        alloc["target_tier"] = cap
                        alloc["final_tier"] = cap
                        alloc["target_tier_name"] = tier_name(cap)
                        alloc["final_tier_name"] = tier_name(cap)
                        alloc["reason_codes"].append(ReasonCode.ALLOC_CROWDING_CAP)
                        alloc["adjustments"].append({
                            "stage": "crowding",
                            "direction": "CAP",
                            "reason": f"{exposure}: {len(sids)} strategies, capped at {cap_name}",
                        })
                        # Cap sessions too
                        for sess_data in alloc["sessions"].values():
                            if sess_data["tier"] > cap:
                                sess_data["tier"] = cap
                                sess_data["tier_name"] = tier_name(cap)

    def _validate(self, allocations, activation_matrix):
        """Stage 5: Final validation and consistency checks."""
        for entry in activation_matrix:
            sid = entry["strategy_id"]
            alloc = allocations.get(sid)
            if not alloc:
                continue

            # OFF strategy must have all OFF sessions
            if alloc["hard_restricted"]:
                alloc["final_tier"] = OFF
                alloc["final_tier_name"] = tier_name(OFF)
                for sess_data in alloc["sessions"].values():
                    sess_data["tier"] = OFF
                    sess_data["tier_name"] = tier_name(OFF)

            # Ensure final_tier reflects any crowding adjustments
            alloc["final_tier"] = alloc["target_tier"]
            alloc["final_tier_name"] = tier_name(alloc["target_tier"])


def save_allocation_matrix(allocations: dict, report_date: str):
    """Save allocation matrix to JSON."""
    # Build summary
    tier_dist = {}
    for alloc in allocations.values():
        name = alloc["final_tier_name"]
        tier_dist[name] = tier_dist.get(name, 0) + 1

    output = {
        "report_date": report_date,
        "allocation_version": "1.0",
        "strategies": {
            sid: {
                "base_tier": alloc["base_tier_name"],
                "target_tier": alloc["target_tier_name"],
                "final_tier": alloc["final_tier_name"],
                "sessions": alloc["sessions"],
                "adjustments": alloc["adjustments"],
                "hard_restricted": alloc["hard_restricted"],
                "reason_codes": alloc["reason_codes"],
            }
            for sid, alloc in allocations.items()
        },
        "summary": {
            "total_strategies": len(allocations),
            "tier_distribution": tier_dist,
        },
    }

    ALLOCATION_MATRIX_PATH.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(ALLOCATION_MATRIX_PATH, output)
    print(f"Allocation matrix saved: {ALLOCATION_MATRIX_PATH}")
    return output
