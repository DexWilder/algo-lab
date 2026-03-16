#!/usr/bin/env python3
"""FQL Portfolio Regime Controller — Adaptive portfolio decision engine.

Integrates all FQL research modules to produce per-strategy activation
decisions.  Reads: regime engine, genome map, contribution analysis,
half-life monitor, kill criteria, health check.

Output: activation matrix with scores, states, actions, and reason codes.

Usage:
    python3 research/portfolio_regime_controller.py               # Full decision report
    python3 research/portfolio_regime_controller.py --json         # JSON output
    python3 research/portfolio_regime_controller.py --save         # Save to reports/
    python3 research/portfolio_regime_controller.py --apply        # Apply state changes to registry
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.reason_codes import ReasonCode, REASON_DESCRIPTIONS
from research.strategy_state_machine import (
    StrategyStateMachine,
    REGISTRY_STATUS_TO_STATE,
    VALID_STATES,
)
from research.activation_scoring import ActivationScorer, load_config
from research.utils.atomic_io import atomic_write_json, backup_rotate

# ── Paths ────────────────────────────────────────────────────────────────────

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
TRANSITION_LOG_PATH = ROOT / "research" / "data" / "strategy_transition_log.json"
ACTIVATION_MATRIX_PATH = ROOT / "research" / "data" / "portfolio_activation_matrix.json"
REPORTS_DIR = ROOT / "research" / "reports"

# ── Import genome map data ───────────────────────────────────────────────────

from research.strategy_genome_map import STRATEGIES as GENOME_STRATEGIES, EXPOSURE_TYPES

# ── Strategy universe — derived from canonical registry ───────────────────────
# Falls back to hardcoded list if registry is unavailable.

def _load_eval_strategies():
    """Load eval strategies from registry, with hardcoded fallback."""
    try:
        from engine.strategy_universe import get_eval_strategies
        strategies = get_eval_strategies()
        if strategies:
            return strategies
    except Exception:
        pass
    # Fallback: hardcoded list
    return [
        ("VWAP-MNQ-Long", "vwap_trend", "MNQ", "long"),
        ("XB-PB-EMA-MES-Short", "xb_pb_ema_timestop", "MES", "short"),
        ("ORB-MGC-Long", "orb_009", "MGC", "long"),
        ("BB-EQ-MGC-Long", "bb_equilibrium", "MGC", "long"),
        ("PB-MGC-Short", "pb_trend", "MGC", "short"),
        ("Donchian-MNQ-Long-GRINDING", "donchian_trend", "MNQ", "long"),
        ("NoiseBoundary-MNQ-Long", "noise_boundary", "MNQ", "long"),
        ("RangeExpansion-MCL-Short", "range_expansion", "MCL", "short"),
        ("GapMom-MGC-Long", "gap_mom", "MGC", "long"),
        ("GapMom-MNQ-Long", "gap_mom", "MNQ", "long"),
    ]

EVAL_STRATEGIES = _load_eval_strategies()


# ── Data Loaders ─────────────────────────────────────────────────────────────

def load_registry() -> dict:
    """Load strategy registry JSON."""
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def load_transition_log() -> list:
    """Load existing transition log or return empty list."""
    if TRANSITION_LOG_PATH.exists():
        with open(TRANSITION_LOG_PATH) as f:
            return json.load(f)
    return []


def _get_genome_data(strategy_id: str) -> dict | None:
    """Get genome map entry for a strategy.

    Handles ID variants (e.g., Donchian-MNQ-Long-GRINDING -> Donchian-MNQ-Long).
    """
    for g in GENOME_STRATEGIES:
        if g["id"] == strategy_id:
            return g
    # Try without trailing suffix (e.g., -GRINDING)
    base_id = strategy_id.rsplit("-", 1)[0] if "-" in strategy_id else strategy_id
    for g in GENOME_STRATEGIES:
        if g["id"] == base_id:
            return g
    return None


def _get_registry_entry(registry: dict, strategy_id: str) -> dict | None:
    """Get registry entry for a strategy."""
    for s in registry.get("strategies", []):
        if s.get("strategy_id") == strategy_id:
            return s
    return None


# ── Signal Gathering ─────────────────────────────────────────────────────────

def gather_regime_signals() -> dict:
    """Get current regime state for each asset.

    Returns {asset: {vol_regime, trend_regime, rv_regime, trend_persistence}}.
    """
    from engine.regime_engine import RegimeEngine

    re = RegimeEngine()
    data_dir = ROOT / "data" / "processed"
    regime_states = {}

    for asset in ["MES", "MNQ", "MGC", "M2K", "MCL"]:
        csv_path = data_dir / f"{asset}_5m.csv"
        if not csv_path.exists():
            continue
        df = pd.read_csv(csv_path)
        df["datetime"] = pd.to_datetime(df["datetime"])

        daily = re.get_daily_regimes(df)
        if daily.empty:
            continue

        latest = daily.iloc[-1]
        regime_states[asset] = {
            "vol_regime": latest.get("vol_regime", "NORMAL"),
            "trend_regime": latest.get("trend_regime", "RANGING"),
            "rv_regime": latest.get("rv_regime", "NORMAL_RV"),
            "trend_persistence": latest.get("trend_persistence", "CHOPPY"),
        }

    return regime_states


def gather_half_life_signals() -> dict:
    """Run half-life analysis and return per-strategy results.

    Returns {strategy_id: {status, decay_score, sharpe_trend, recent_sharpe}}.
    """
    from research.strategy_half_life_monitor import (
        get_strategy_trades, compute_rolling_metrics,
        compute_decay_score, get_status, _sharpe_trend,
    )

    results = {}
    for strat in EVAL_STRATEGIES:
        strategy_id, module_name, asset, mode = strat
        try:
            trades = get_strategy_trades(strategy_id, module_name, asset, mode)
            rolling = compute_rolling_metrics(trades)
            decay = compute_decay_score(rolling)
            status = get_status(decay)
            trend = _sharpe_trend(rolling)

            # Get 6-month Sharpe
            six_mo = rolling.get("6m", {})
            recent_sharpe = six_mo.get("sharpe", 0.0) if six_mo.get("trades", 0) >= 10 else rolling["full"]["sharpe"]

            results[strategy_id] = {
                "status": status,
                "decay_score": decay,
                "sharpe_trend": trend,
                "recent_sharpe": recent_sharpe,
                "full_sharpe": rolling["full"]["sharpe"],
            }
        except Exception as e:
            results[strategy_id] = {
                "status": "ERROR",
                "decay_score": 0.5,
                "sharpe_trend": "ERROR",
                "recent_sharpe": 0.0,
                "full_sharpe": 0.0,
                "error": str(e),
            }

    return results


def gather_contribution_signals() -> dict:
    """Run contribution analysis and return per-strategy results.

    Returns {strategy_id: {marginal_sharpe, correlation, verdict}}.
    """
    from research.strategy_contribution_analysis import (
        build_daily_pnl_matrix, compute_contribution,
        PORTFOLIO_STRATEGIES, PROBATION_CANDIDATES,
    )

    all_strategies = list(PORTFOLIO_STRATEGIES) + list(PROBATION_CANDIDATES)
    print("  Building daily PnL matrix for contribution analysis...")
    matrix = build_daily_pnl_matrix(all_strategies)

    if matrix.empty:
        return {}

    contributions = compute_contribution(matrix)
    results = {}
    for c in contributions:
        results[c["strategy_id"]] = {
            "marginal_sharpe": c["marginal_sharpe"],
            "correlation": c["correlation"],
            "verdict": c["verdict"],
        }

    return results


def gather_kill_signals(registry: dict) -> dict:
    """Get kill flags from registry (already applied in prior run).

    Returns {strategy_id: [list of kill_flag strings]}.
    """
    results = {}
    for s in registry.get("strategies", []):
        sid = s.get("strategy_id", "")
        flag = s.get("kill_flag")
        results[sid] = [flag] if flag else []
    return results


def gather_health_signals() -> dict:
    """Run health checks and return per-strategy health status.

    Returns {"overall": "PASS"/"WARN"/"FAIL", "details": [...]}.
    """
    from research.fql_health_check import run_checks

    all_results = run_checks()
    total_fail = 0
    total_warn = 0
    for cat, data in all_results.items():
        for r in data["results"]:
            if r["level"] == "FAIL":
                total_fail += 1
            elif r["level"] == "WARN":
                total_warn += 1

    if total_fail > 0:
        overall = "FAIL"
    elif total_warn > 3:
        overall = "WARN"
    else:
        overall = "PASS"

    return {"overall": overall, "fail_count": total_fail, "warn_count": total_warn}


def gather_redundancy_signals() -> dict:
    """Compute per-strategy redundancy using genome map exposure clusters.

    Returns {strategy_id: {max_correlation, same_exposure_cluster}}.
    """
    from research.strategy_contribution_analysis import (
        build_daily_pnl_matrix, PORTFOLIO_STRATEGIES, PROBATION_CANDIDATES,
    )

    all_strategies = list(PORTFOLIO_STRATEGIES) + list(PROBATION_CANDIDATES)
    matrix = build_daily_pnl_matrix(all_strategies)

    results = {}
    for strat in EVAL_STRATEGIES:
        sid = strat[0]
        genome = _get_genome_data(sid)
        primary_exp = genome.get("primary_exposure", "unknown") if genome else "unknown"

        # Max correlation with other strategies
        max_corr = 0.0
        if sid in matrix.columns:
            for other in matrix.columns:
                if other != sid:
                    corr = matrix[sid].corr(matrix[other])
                    if not np.isnan(corr):
                        max_corr = max(max_corr, abs(corr))

        # Check same exposure cluster
        same_cluster = False
        for other_genome in GENOME_STRATEGIES:
            if other_genome["id"] != sid:
                if other_genome.get("primary_exposure") == primary_exp:
                    same_cluster = True
                    break

        results[sid] = {
            "max_correlation": round(max_corr, 4),
            "same_exposure_cluster": same_cluster,
        }

    return results


# ── Session Drift Signal Gathering ────────────────────────────────────────────

DRIFT_LOG_PATH = ROOT / "research" / "data" / "live_drift_log.json"


def gather_session_drift_signals() -> dict:
    """Load latest session drift data from drift monitor log.

    Returns per-strategy session drift signals:
        {strategy_id: {
            worst_severity: "NORMAL"/"DRIFT"/"ALARM",
            session_concentration: bool,
            restricted_sessions: [{session, severity, reason}],
        }}
    """
    if not DRIFT_LOG_PATH.exists():
        return {}

    try:
        with open(DRIFT_LOG_PATH) as f:
            log = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

    if not log:
        return {}

    latest = log[-1]
    session_drift = latest.get("session_drift", {})
    if not session_drift or session_drift.get("status") == "NO_DATA":
        return {}

    strategy_sessions = session_drift.get("strategy_sessions", {})
    concentration_warnings = session_drift.get("concentration_warnings", [])

    # Determine which sessions have concentration issues
    concentrated_sessions = {w["session"] for w in concentration_warnings}

    results = {}
    for strat_name, sessions in strategy_sessions.items():
        worst_severity = "NORMAL"
        restricted = []

        for session_name, data in sessions.items():
            sev = data.get("severity", "NORMAL")
            if sev == "INSUFFICIENT_DATA":
                continue

            if sev == "ALARM":
                worst_severity = "ALARM"
                restricted.append({
                    "session": session_name,
                    "severity": "ALARM",
                    "action": "BLOCK",
                    "reason": f"Edge broken in {session_name} (WR delta {data.get('wr_delta', 0):+.1%}, PnL ratio {data.get('pnl_ratio', 0):.2f})",
                })
            elif sev == "DRIFT" and worst_severity != "ALARM":
                worst_severity = "DRIFT"
                restricted.append({
                    "session": session_name,
                    "severity": "DRIFT",
                    "action": "REDUCE",
                    "reason": f"Degraded in {session_name} (WR delta {data.get('wr_delta', 0):+.1%})",
                })

        results[strat_name] = {
            "worst_severity": worst_severity,
            "session_concentration": bool(concentrated_sessions),
            "restricted_sessions": restricted,
        }

    return results


# ── Regime Fit Assessment ────────────────────────────────────────────────────

def assess_regime_fit(strategy_id: str, regime_states: dict) -> str:
    """Assess how well current regime fits strategy specialization.

    Returns: "preferred", "allowed", "neutral", or "avoid".
    """
    genome = _get_genome_data(strategy_id)
    if not genome:
        return "neutral"

    asset = genome.get("asset", "MNQ")
    regime = regime_states.get(asset, {})
    if not regime:
        return "neutral"

    # Build current regime components
    current = set()
    for key in ["vol_regime", "trend_regime", "rv_regime", "trend_persistence"]:
        if key in regime:
            current.add(regime[key])

    # Check preferred regimes
    preferred = set(genome.get("regime_preferred", []))
    niche = set(genome.get("regime_niche", []))

    # Build composite for matching
    vol = regime.get("vol_regime", "NORMAL")
    trend = regime.get("trend_regime", "RANGING")
    rv = regime.get("rv_regime", "NORMAL_RV")
    composite = f"{vol}_{trend}_{rv}"

    if composite in preferred:
        return "preferred"

    # Check niche keywords
    for n in niche:
        if n == "BROAD":
            return "allowed"
        if n in current:
            return "allowed"

    # Check if current regime is avoided
    # Use canonical strategy universe for avoid_regimes
    from engine.strategy_universe import get_avoid_regimes
    avoid_regimes_list = get_avoid_regimes(strategy_id)
    if not avoid_regimes_list:
        # Try base ID without -GRINDING suffix
        base_id = strategy_id.rsplit("-", 1)[0] if strategy_id.endswith("-GRINDING") else strategy_id
        avoid_regimes_list = get_avoid_regimes(base_id)
    avoid_regimes = set(avoid_regimes_list)
    if avoid_regimes & current:
        return "avoid"

    return "neutral"


def assess_time_fit(strategy_id: str) -> str:
    """Assess time-of-day fit for the strategy.

    For daily controller decisions, we check the current time against
    the strategy's preferred session. Returns "match", "partial", "mismatch".
    """
    genome = _get_genome_data(strategy_id)
    if not genome:
        return "match"

    session = genome.get("session", "all_day")
    if session == "all_day":
        return "match"

    # For daily decisions, check if we're in a trading period at all
    now = datetime.now()
    hour = now.hour
    if 9 <= hour <= 16:
        return "match"

    return "partial"


# ── Main Controller Logic ────────────────────────────────────────────────────

def run_controller(skip_heavy: bool = False) -> dict:
    """Run the full Portfolio Regime Controller.

    Parameters
    ----------
    skip_heavy : bool
        If True, skip slow computations (backtests for contribution/redundancy).
        Uses cached/registry data only.

    Returns
    -------
    dict with:
        - report_date: ISO date
        - regime_snapshot: current regime per asset
        - activation_matrix: list of per-strategy decisions
        - state_transitions: list of state changes
        - portfolio_summary: aggregate portfolio health
    """
    config = load_config()
    registry = load_registry()
    state_machine = StrategyStateMachine()
    scorer = ActivationScorer(config)

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\nFQL Portfolio Regime Controller — {report_date}")
    print("=" * 60)

    # ── Phase 1: Gather signals ──────────────────────────────────────
    print("\n[1/6] Gathering regime signals...")
    regime_states = gather_regime_signals()

    print("[2/6] Running half-life analysis...")
    half_life_signals = gather_half_life_signals()

    print("[3/6] Gathering kill criteria from registry...")
    kill_signals = gather_kill_signals(registry)

    print("[4/6] Running health checks...")
    health_signals = gather_health_signals()

    if not skip_heavy:
        print("[5/7] Running contribution analysis (backtests)...")
        contribution_signals = gather_contribution_signals()

        print("[6/7] Computing redundancy signals...")
        redundancy_signals = gather_redundancy_signals()
    else:
        print("[5/7] Skipping contribution analysis (--fast mode)...")
        contribution_signals = {}
        print("[6/7] Skipping redundancy analysis (--fast mode)...")
        redundancy_signals = {}

    print("[7/7] Loading session drift signals...")
    session_drift_signals = gather_session_drift_signals()
    if session_drift_signals:
        print(f"  Session drift loaded for {len(session_drift_signals)} strategies")
    else:
        print("  No session drift data available yet — defaults to NO_DATA")

    # ── Phase 2: Score each strategy ─────────────────────────────────
    print("\nScoring strategies...")
    activation_matrix = []
    state_transitions = []

    for strat in EVAL_STRATEGIES:
        strategy_id = strat[0]
        asset = strat[2]

        genome = _get_genome_data(strategy_id)
        reg_entry = _get_registry_entry(registry, strategy_id)

        # Determine current state
        reg_status = reg_entry.get("status", "idea") if reg_entry else "idea"
        current_state = reg_entry.get("controller_state") if reg_entry else None
        if not current_state or current_state not in VALID_STATES:
            current_state = REGISTRY_STATUS_TO_STATE.get(reg_status, "VALIDATED")

        # Build signals dict for scorer
        hl = half_life_signals.get(strategy_id, {})
        contrib = contribution_signals.get(strategy_id, {})
        redund = redundancy_signals.get(strategy_id, {})
        kills = kill_signals.get(strategy_id, [])

        # Session drift signals
        sd = session_drift_signals.get(strategy_id, {})

        signals = {
            "regime_fit_level": assess_regime_fit(strategy_id, regime_states),
            "half_life_status": hl.get("status", "HEALTHY"),
            "sharpe_trend": hl.get("sharpe_trend", "STABLE"),
            "decay_score": hl.get("decay_score", 0.0),
            "recent_sharpe": hl.get("recent_sharpe", 1.0),
            "marginal_sharpe": contrib.get("marginal_sharpe", 0.0),
            "contribution_verdict": contrib.get("verdict", "NEUTRAL"),
            "max_correlation": redund.get("max_correlation", 0.0),
            "same_exposure_cluster": redund.get("same_exposure_cluster", False),
            "health_status": health_signals.get("overall", "PASS"),
            "kill_flags": kills,
            "session_drift_severity": sd.get("worst_severity", "NO_DATA"),
            "session_concentration": sd.get("session_concentration", False),
            "time_fit": assess_time_fit(strategy_id),
            "asset_fit": "good",  # Default — future: check asset-specific conditions
        }

        # Score
        score_result = scorer.score_strategy(signals)

        # Evaluate state transition
        transition_signals = {
            **signals,
            "activation_score": score_result["activation_score"],
            "days_in_current_state": _days_in_state(reg_entry),
        }
        transition = state_machine.evaluate_transition(current_state, transition_signals)

        if transition["changed"]:
            state_transitions.append(
                StrategyStateMachine.create_state_history_entry(
                    strategy_id,
                    current_state,
                    transition["new_state"],
                    transition["reason_codes"],
                    transition["trigger"],
                )
            )

        # Build activation matrix entry
        entry = {
            "strategy_id": strategy_id,
            "asset": asset,
            "family": genome.get("family", "unknown") if genome else "unknown",
            "primary_exposure": genome.get("primary_exposure", "unknown") if genome else "unknown",
            "current_state": current_state,
            "new_state": transition["new_state"],
            "state_changed": transition["changed"],
            "activation_score": score_result["activation_score"],
            "sub_scores": score_result["sub_scores"],
            "recommended_action": score_result["recommended_action"],
            "situation": score_result.get("situation", "HEALTHY"),
            "reason_codes": score_result["reason_codes"],
            "transition_trigger": transition["trigger"],
            "confidence": score_result["confidence"],
            "uncertainty": score_result.get("uncertainty", False),
            "warnings": _build_warnings(signals, score_result, genome),
            "review_priority": _compute_review_priority(score_result, transition),
            # Session restrictions (deployment-level instructions)
            "session_restrictions": sd.get("restricted_sessions", []),
            # Raw signals for registry persistence
            "_signals": {
                "half_life_status": signals["half_life_status"],
                "contribution_verdict": signals["contribution_verdict"],
                "health_status": signals["health_status"],
                "genome_cluster": genome.get("primary_exposure", "unknown") if genome else "unknown",
                "session_drift_severity": signals["session_drift_severity"],
            },
        }
        activation_matrix.append(entry)

    # ── Phase 3: Portfolio summary ───────────────────────────────────
    active_count = sum(1 for e in activation_matrix if e["recommended_action"] in ("FULL_ON", "REDUCED_ON"))
    probation_count = sum(1 for e in activation_matrix if e["recommended_action"] == "PROBATION")
    disabled_count = sum(1 for e in activation_matrix if e["recommended_action"] in ("OFF", "DISABLE", "ARCHIVE_REVIEW"))

    portfolio_summary = {
        "total_strategies": len(activation_matrix),
        "active": active_count,
        "probation": probation_count,
        "disabled_or_off": disabled_count,
        "state_changes": len(state_transitions),
        "health_status": health_signals.get("overall", "PASS"),
        "avg_activation_score": round(
            np.mean([e["activation_score"] for e in activation_matrix]), 4
        ),
    }

    # ── Phase 4: Allocation tiers ───────────────────────────────────
    print("\nComputing allocation tiers...")
    from research.portfolio_regime_allocation import AllocationEngine, save_allocation_matrix

    alloc_engine = AllocationEngine(config)

    # Build contribution signals from activation matrix data
    contrib_signals = {}
    for e in activation_matrix:
        sid = e["strategy_id"]
        signals = e.get("_signals", {})
        contrib_signals[sid] = {
            "verdict": signals.get("contribution_verdict", "NEUTRAL"),
            "marginal_sharpe": e.get("sub_scores", {}).get("contribution", 0.5),
        }

    # Build session drift signals from activation matrix data
    drift_signals = {}
    for e in activation_matrix:
        sid = e["strategy_id"]
        signals = e.get("_signals", {})
        genome = _get_genome_data(sid)
        drift_signals[sid] = {
            "restricted_sessions": e.get("session_restrictions", []),
            "session_details": {},
            "primary_session": genome.get("session", "all_day") if genome else "all_day",
        }
        # Map worst severity to session details
        severity = signals.get("session_drift_severity", "NORMAL")
        for sess in ["morning", "midday", "afternoon"]:
            if sess in e.get("session_restrictions", []):
                drift_signals[sid]["session_details"][sess] = {"severity": "ALARM"}
            else:
                drift_signals[sid]["session_details"][sess] = {"severity": "NORMAL"}

    # Load counterfactual data (cached, no re-computation)
    cf_data = {}
    cf_log_path = ROOT / "research" / "data" / "counterfactual_log.json"
    if cf_log_path.exists():
        try:
            cf_log = json.load(open(cf_log_path))
            if cf_log:
                latest = cf_log[-1]
                for sid, cf_entry in latest.get("strategies", {}).items():
                    cf_data[sid] = cf_entry
        except Exception:
            pass

    # Build crowding signals from activation matrix
    crowding = {}
    for e in activation_matrix:
        crowding[e["strategy_id"]] = {
            "primary_exposure": e.get("primary_exposure", "unknown"),
            "max_correlation": e.get("sub_scores", {}).get("redundancy", 1.0),
        }

    allocations = alloc_engine.compute_allocations(
        activation_matrix=activation_matrix,
        contribution_signals=contrib_signals,
        counterfactual=cf_data,
        session_drift_signals=drift_signals,
        crowding_signals=crowding,
    )

    # Attach allocation to activation matrix entries
    for e in activation_matrix:
        sid = e["strategy_id"]
        if sid in allocations:
            e["allocation"] = allocations[sid]

    # Save allocation matrix
    alloc_output = save_allocation_matrix(allocations, report_date)

    # Print allocation summary
    dist = alloc_output["summary"]["tier_distribution"]
    tier_str = "  ".join(f"{k}: {v}" for k, v in sorted(dist.items()))
    print(f"  Allocation tiers: {tier_str}")

    return {
        "report_date": report_date,
        "regime_snapshot": regime_states,
        "activation_matrix": activation_matrix,
        "state_transitions": state_transitions,
        "portfolio_summary": portfolio_summary,
        "health_signals": health_signals,
        "allocation_summary": alloc_output["summary"],
    }


# ── Helper Functions ─────────────────────────────────────────────────────────

def _days_in_state(reg_entry: dict | None) -> int:
    """Estimate days in current state from registry data."""
    if not reg_entry:
        return 0
    # Use last_review_date or probation_start_date if available
    for field in ["state_entered_date", "probation_start_date", "last_review_date"]:
        date_str = reg_entry.get(field)
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return (datetime.now() - dt).days
            except ValueError:
                pass
    return 30  # Default assumption


def _build_warnings(signals: dict, score_result: dict, genome: dict | None) -> list:
    """Build list of warning strings."""
    warnings = []

    if signals.get("half_life_status") in ("DECAYING", "ARCHIVE_CANDIDATE"):
        warnings.append(f"Edge decaying: HL status={signals['half_life_status']}")

    if signals.get("contribution_verdict") == "DILUTIVE":
        warnings.append(f"Portfolio dilution: marginal_sharpe={signals.get('marginal_sharpe', 0):.3f}")

    if signals.get("kill_flags"):
        warnings.append(f"Kill flags: {', '.join(signals['kill_flags'])}")

    if signals.get("regime_fit_level") == "avoid":
        warnings.append("Current regime in avoid list")

    if score_result["activation_score"] < 0.40:
        warnings.append(f"Low activation score: {score_result['activation_score']:.2f}")

    if signals.get("max_correlation", 0) > 0.50:
        warnings.append(f"High redundancy: max_corr={signals['max_correlation']:.3f}")

    if signals.get("session_drift_severity") == "ALARM":
        warnings.append("Session drift ALARM — edge broken in one or more sessions")
    elif signals.get("session_drift_severity") == "DRIFT":
        warnings.append("Session drift detected — degraded in one or more sessions")

    if signals.get("session_concentration"):
        warnings.append("Morning session concentration >60% — diversification risk")

    return warnings


def _compute_review_priority(score_result: dict, transition: dict) -> str:
    """Assign review priority: HIGH / MEDIUM / LOW."""
    if transition["changed"]:
        return "HIGH"
    if score_result["activation_score"] < 0.40:
        return "HIGH"
    if score_result["activation_score"] < 0.55:
        return "MEDIUM"
    return "LOW"


# ── Registry Update ──────────────────────────────────────────────────────────

def apply_to_registry(results: dict):
    """Apply controller decisions to the strategy registry.

    Updates: controller_state, controller_action, activation_score,
    controller_reason_codes, last_controller_date, state_history.
    """
    registry = load_registry()
    today = datetime.now().strftime("%Y-%m-%d")

    for entry in results["activation_matrix"]:
        sid = entry["strategy_id"]
        for reg_strat in registry.get("strategies", []):
            if reg_strat.get("strategy_id") == sid:
                # Core controller fields
                prior_state = reg_strat.get("controller_state")
                reg_strat["controller_state"] = entry["new_state"]
                reg_strat["prior_state"] = prior_state or entry["current_state"]
                reg_strat["controller_action"] = entry["recommended_action"]
                reg_strat["activation_score"] = entry["activation_score"]
                reg_strat["controller_reason_codes"] = entry["reason_codes"]
                reg_strat["last_controller_date"] = today
                reg_strat["review_priority"] = entry["review_priority"]

                # Diagnostic status fields (from raw signals)
                raw = entry.get("_signals", {})
                reg_strat["half_life_status"] = raw.get("half_life_status")
                reg_strat["contribution_status"] = raw.get("contribution_verdict")
                reg_strat["health_status"] = raw.get("health_status")
                reg_strat["genome_cluster"] = raw.get("genome_cluster")

                # Resurrection flag
                reg_strat["resurrection_flag"] = (
                    entry["new_state"] == "RESURRECTION_CANDIDATE"
                )

                # Ensure state_history exists (empty if no transitions yet)
                if "state_history" not in reg_strat:
                    reg_strat["state_history"] = []

                # Update state history
                if entry["state_changed"]:
                    history = reg_strat.get("state_history", [])
                    history.append({
                        "date": today,
                        "from": entry["current_state"],
                        "to": entry["new_state"],
                        "trigger": entry["transition_trigger"],
                    })
                    reg_strat["state_history"] = history
                    reg_strat["state_entered_date"] = today

                    # Set probation_start_date if entering probation
                    if entry["new_state"] == "PROBATION":
                        reg_strat["probation_start_date"] = today

                    # Set archive_date if entering archived
                    if entry["new_state"] == "ARCHIVED":
                        reg_strat["archive_date"] = today

                break

    # Update schema version
    registry["_schema_version"] = "2.0"
    registry["_generated"] = today

    backup_rotate(REGISTRY_PATH, keep=5)
    atomic_write_json(REGISTRY_PATH, registry)

    print(f"\nRegistry updated: {REGISTRY_PATH}")

    # Save transition log
    if results["state_transitions"]:
        log = load_transition_log()
        log.extend(results["state_transitions"])
        atomic_write_json(TRANSITION_LOG_PATH, log)
        print(f"Transition log updated: {TRANSITION_LOG_PATH}")


def save_activation_matrix(results: dict):
    """Save activation matrix to JSON."""
    atomic_write_json(ACTIVATION_MATRIX_PATH, results)
    print(f"Activation matrix saved: {ACTIVATION_MATRIX_PATH}")


# ── Terminal Report ──────────────────────────────────────────────────────────

def print_report(results: dict):
    """Print formatted controller decision report."""
    W = 75
    SEP = "=" * W
    THIN = "-" * 55

    print()
    print(SEP)
    print("  FQL PORTFOLIO REGIME CONTROLLER")
    print(f"  {results['report_date']}")
    print(SEP)

    # ── Regime Snapshot ──
    print()
    print("  CURRENT REGIME SNAPSHOT")
    print(f"  {THIN}")
    for asset, regime in sorted(results["regime_snapshot"].items()):
        vol = regime.get("vol_regime", "?")
        trend = regime.get("trend_regime", "?")
        rv = regime.get("rv_regime", "?")
        persist = regime.get("trend_persistence", "?")
        print(f"  {asset:<6s} {vol:<10s} {trend:<10s} {rv:<12s} {persist}")

    # ── Portfolio Summary ──
    summary = results["portfolio_summary"]
    print()
    print("  PORTFOLIO SUMMARY")
    print(f"  {THIN}")
    print(f"  Total strategies:       {summary['total_strategies']}")
    print(f"  Active (FULL+REDUCED):  {summary['active']}")
    print(f"  Probation:              {summary['probation']}")
    print(f"  Disabled/Off:           {summary['disabled_or_off']}")
    print(f"  State changes today:    {summary['state_changes']}")
    print(f"  Avg activation score:   {summary['avg_activation_score']:.3f}")
    print(f"  Health status:          {summary['health_status']}")

    # ── State Transitions ──
    if results["state_transitions"]:
        print()
        print("  STATE TRANSITIONS")
        print(f"  {THIN}")
        for t in results["state_transitions"]:
            print(f"  {t['strategy_id']}: {t['from_state']} -> {t['to_state']}")
            print(f"    Trigger: {t['trigger']}")
            print(f"    Codes:   {', '.join(t['reason_codes'])}")

    # ── Activation Matrix ──
    print()
    print("  ACTIVATION MATRIX")
    print(f"  {THIN}")
    header = f"  {'Strategy':<28s} {'Score':>6s} {'Action':<14s} {'State':<10s} {'Situation':<16s} {'Pri':<4s}"
    print(header)
    print(f"  {'-' * 80}")

    # Sort by activation score descending
    sorted_matrix = sorted(
        results["activation_matrix"],
        key=lambda x: x["activation_score"],
        reverse=True,
    )

    for e in sorted_matrix:
        sid = e["strategy_id"]
        if len(sid) > 27:
            sid = sid[:24] + "..."
        score = f"{e['activation_score']:.3f}"
        action = e["recommended_action"]
        state = e["new_state"]
        situation = e.get("situation", "HEALTHY")
        priority = e["review_priority"]
        uncertain = "*" if e.get("uncertainty") else " "

        # Color indicators
        if action == "FULL_ON":
            indicator = "[+]"
        elif action == "REDUCED_ON":
            indicator = "[~]"
        elif action == "PROBATION":
            indicator = "[?]"
        else:
            indicator = "[-]"

        print(f"  {sid:<28s} {score:>6s}{uncertain}{indicator} {action:<12s} {state:<10s} {situation:<16s} {priority:<4s}")

    # ── Uncertainty note ──
    uncertain_entries = [e for e in sorted_matrix if e.get("uncertainty")]
    if uncertain_entries:
        print()
        print(f"  * = borderline score (within 0.05 of action threshold)")
        for e in uncertain_entries:
            print(f"    {e['strategy_id']}: {e['activation_score']:.3f} near threshold")

    # ── Crowding Diagnostics ──
    print()
    print("  CROWDING DIAGNOSTICS")
    print(f"  {THIN}")

    # Genome cluster concentration (active strategies only)
    cluster_counts = {}
    session_counts = {}
    asset_counts = {}
    family_counts = {}
    for e in sorted_matrix:
        if e["recommended_action"] in ("FULL_ON", "REDUCED_ON"):
            exp = e.get("primary_exposure", "unknown")
            cluster_counts.setdefault(exp, []).append(e["strategy_id"])
            asset_counts.setdefault(e["asset"], []).append(e["strategy_id"])
            fam = e.get("family", "unknown")
            family_counts.setdefault(fam, []).append(e["strategy_id"])
            # Session from genome
            genome = _get_genome_data(e["strategy_id"])
            sess = genome.get("session", "all_day") if genome else "all_day"
            session_counts.setdefault(sess, []).append(e["strategy_id"])

    for label, counts, warn_at in [
        ("Exposure", cluster_counts, 3),
        ("Asset", asset_counts, 3),
        ("Family", family_counts, 3),
        ("Session", session_counts, 4),
    ]:
        crowded = {k: v for k, v in counts.items() if len(v) >= warn_at}
        if crowded:
            for k, strats in crowded.items():
                print(f"  ! {label} [{k}]: {len(strats)} active — {', '.join(strats)}")
        else:
            max_k = max(counts, key=lambda k: len(counts[k])) if counts else "none"
            max_n = len(counts.get(max_k, [])) if counts else 0
            print(f"  {label}: OK (max {max_n} in {max_k})")

    # ── Session Restrictions ──
    has_restrictions = any(e.get("session_restrictions") for e in sorted_matrix)
    if has_restrictions:
        print()
        print("  SESSION RESTRICTIONS")
        print(f"  {THIN}")
        for e in sorted_matrix:
            restrictions = e.get("session_restrictions", [])
            if restrictions:
                for r in restrictions:
                    action_tag = "BLOCK" if r["severity"] == "ALARM" else "REDUCE"
                    print(f"  ! {e['strategy_id']}: [{action_tag}] {r['session']} — {r['reason']}")
    else:
        print()
        print("  SESSION RESTRICTIONS")
        print(f"  {THIN}")
        print("  No session-specific restrictions active")

    # ── Warnings ──
    all_warnings = []
    for e in results["activation_matrix"]:
        for w in e.get("warnings", []):
            all_warnings.append(f"{e['strategy_id']}: {w}")

    if all_warnings:
        print()
        print("  WARNINGS")
        print(f"  {THIN}")
        for w in all_warnings:
            print(f"  ! {w}")

    # ── Sub-Score Breakdown ──
    print()
    print("  SUB-SCORE BREAKDOWN")
    print(f"  {THIN}")
    dims = ["regime_fit", "half_life", "contribution", "redundancy",
            "health", "kill_criteria", "session_drift", "time_of_day", "asset_fit", "recent_stability"]
    header2 = f"  {'Strategy':<22s} " + " ".join(f"{d[:7]:>7s}" for d in dims)
    print(header2)
    print(f"  {'-' * 96}")

    for e in sorted_matrix:
        sid = e["strategy_id"]
        if len(sid) > 21:
            sid = sid[:18] + "..."
        scores = e["sub_scores"]
        vals = " ".join(f"{scores.get(d, 0):>7.2f}" for d in dims)
        print(f"  {sid:<22s} {vals}")

    # ── Reason Codes Detail ──
    print()
    print("  REASON CODES (per strategy)")
    print(f"  {THIN}")
    for e in sorted_matrix:
        codes = e.get("reason_codes", [])
        if codes:
            important = [c for c in codes if not c.endswith("_PASS") and not c.endswith("_MATCH")
                         and c not in (ReasonCode.KILL_NONE, ReasonCode.LOW_REDUNDANCY,
                                       ReasonCode.TIME_WINDOW_MATCH, ReasonCode.ASSET_FIT_GOOD,
                                       ReasonCode.RECENT_STABLE, ReasonCode.HEALTH_PASS,
                                       ReasonCode.SESSION_DRIFT_NORMAL)]
            if important:
                print(f"  {e['strategy_id']}")
                for code in important:
                    desc = REASON_DESCRIPTIONS.get(code, code)
                    print(f"    {code}: {desc}")

    print()
    print(SEP)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FQL Portfolio Regime Controller — adaptive portfolio decisions"
    )
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--save", action="store_true",
                        help="Save report and activation matrix")
    parser.add_argument("--apply", action="store_true",
                        help="Apply state changes to registry")
    parser.add_argument("--fast", action="store_true",
                        help="Skip heavy backtests (contribution/redundancy)")
    args = parser.parse_args()

    results = run_controller(skip_heavy=args.fast)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results)

    if args.save:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        save_activation_matrix(results)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        report_path = REPORTS_DIR / f"controller_decision_{timestamp}.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Report saved: {report_path}")

    if args.apply:
        apply_to_registry(results)


if __name__ == "__main__":
    main()
