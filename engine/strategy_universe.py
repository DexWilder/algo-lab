"""Canonical Strategy Universe — single source of truth for strategy definitions.

Reads from the strategy registry (research/data/strategy_registry.json) and
provides all strategy lists, execution configs, and portfolio configs that
were previously hardcoded across multiple files.

The portfolio regime controller WRITES to the registry.
This module READS from it and builds execution-time configs.

Usage:
    from engine.strategy_universe import build_portfolio_config, get_eval_strategies

    # Execution time: build config for StrategyController
    config = build_portfolio_config()
    controller = StrategyController(config)

    # Research time: get list of strategies to evaluate
    eval_strategies = get_eval_strategies()
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"

# ── Action-to-Execution Eligibility Mapping ──────────────────────────────────
# Explicit: which controller actions make a strategy eligible for execution.
ACTION_ELIGIBILITY = {
    "FULL_ON": True,
    "REDUCED_ON": True,
    "PROBATION": False,     # excluded from live execution by default
    "OFF": False,
    "DISABLE": False,
    "ARCHIVE_REVIEW": False,
}

# Controller states that are eligible for evaluation
EVAL_STATES = {"core", "probation", "testing"}

# ── Session → Timing Window Defaults ─────────────────────────────────────────
SESSION_WINDOWS = {
    "morning":   {"preferred": ("09:30", "12:00"), "allowed": ("09:30", "13:00")},
    "midday":    {"preferred": ("10:00", "13:00"), "allowed": ("09:30", "14:30")},
    "afternoon": {"preferred": ("12:00", "15:00"), "allowed": ("10:00", "15:15")},
    "all_day":   {"preferred": ("09:30", "14:30"), "allowed": ("09:30", "15:15")},
}

# ── Staleness Threshold ──────────────────────────────────────────────────────
MAX_CONTROLLER_AGE_DAYS = 5  # warn if controller decisions are older than this


def _load_registry():
    """Load the strategy registry JSON. Returns None on failure."""
    try:
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load strategy registry: {e}")
        return None


def check_freshness(registry: dict) -> dict:
    """Check if controller decisions in the registry are fresh enough to trust.

    Returns dict with:
        - fresh: bool
        - last_controller_date: str or None
        - age_days: int or None
        - schema_version: str
        - warning: str or None
    """
    strategies = registry.get("strategies", [])
    schema_version = registry.get("_schema_version", "unknown")

    # Find most recent controller date
    last_date = None
    for s in strategies:
        lcd = s.get("last_controller_date")
        if lcd and (last_date is None or lcd > last_date):
            last_date = lcd

    result = {
        "fresh": True,
        "last_controller_date": last_date,
        "age_days": None,
        "schema_version": schema_version,
        "warning": None,
    }

    if last_date is None:
        result["fresh"] = False
        result["warning"] = "No controller decisions found in registry"
        return result

    try:
        last_dt = datetime.strptime(last_date, "%Y-%m-%d")
        age = (datetime.now() - last_dt).days
        result["age_days"] = age
        if age > MAX_CONTROLLER_AGE_DAYS:
            result["fresh"] = False
            result["warning"] = (
                f"Controller decisions are {age} days old "
                f"(threshold: {MAX_CONTROLLER_AGE_DAYS} days)"
            )
    except ValueError:
        result["fresh"] = False
        result["warning"] = f"Could not parse last_controller_date: {last_date}"

    return result


def get_all_strategies() -> list:
    """Return all strategies from the registry."""
    registry = _load_registry()
    if registry is None:
        return []
    return registry.get("strategies", [])


def get_active_strategy_ids() -> list:
    """Return IDs of strategies with execution-eligible controller actions."""
    strategies = get_all_strategies()
    return [
        s["strategy_id"]
        for s in strategies
        if ACTION_ELIGIBILITY.get(s.get("controller_action", "OFF"), False)
    ]


def get_eval_strategies() -> list:
    """Return strategies eligible for controller evaluation.

    Returns list of tuples: (strategy_id, strategy_name, asset, direction)
    Matches the shape of the old EVAL_STRATEGIES constant.
    """
    strategies = get_all_strategies()
    result = []
    for s in strategies:
        if s.get("status") in EVAL_STATES:
            result.append((
                s["strategy_id"],
                s["strategy_name"],
                s["asset"],
                s["direction"],
            ))
    return result


def get_avoid_regimes(strategy_id: str) -> list:
    """Get avoid_regimes for a strategy from its execution_config.

    Falls back to empty list if not found.
    """
    strategies = get_all_strategies()
    for s in strategies:
        if s["strategy_id"] == strategy_id:
            exec_cfg = s.get("execution_config", {})
            return exec_cfg.get("avoid_regimes", [])
    return []


def _build_strategy_exec_config(strategy: dict) -> dict:
    """Build a single strategy's execution config from registry data.

    Produces the same dict shape as entries in PORTFOLIO_CONFIG["strategies"].
    """
    exec_cfg = strategy.get("execution_config", {})
    session = strategy.get("session", "all_day")
    windows = SESSION_WINDOWS.get(session, SESSION_WINDOWS["all_day"])

    return {
        "name": strategy["strategy_name"],
        "asset": strategy["asset"],
        "mode": strategy["direction"],
        "grinding_filter": exec_cfg.get("grinding_filter", False),
        "exit_variant": exec_cfg.get("exit_variant", None),
        "avoid_regimes": exec_cfg.get("avoid_regimes", []),
        "preferred_regimes": exec_cfg.get("preferred_regimes", []),
        "preferred_window": tuple(exec_cfg.get(
            "preferred_window", windows["preferred"]
        )),
        "allowed_window": tuple(exec_cfg.get(
            "allowed_window", windows["allowed"]
        )),
        "conviction_threshold_outside": exec_cfg.get(
            "conviction_threshold_outside", 2
        ),
        "priority": exec_cfg.get(
            "priority",
            int(strategy.get("activation_score", 0.5) * 10)
        ),
    }


def build_portfolio_config(include_probation=False) -> dict:
    """Build a PORTFOLIO_CONFIG-shaped dict from the strategy registry.

    This replaces the hardcoded PORTFOLIO_CONFIG constant. The StrategyController
    class accepts this dict unchanged.

    Parameters
    ----------
    include_probation : bool
        If True, include PROBATION-action strategies. Default False.

    Returns
    -------
    dict in PORTFOLIO_CONFIG format, or falls back to hardcoded config.
    """
    registry = _load_registry()

    if registry is None:
        logger.warning("Registry unavailable — falling back to hardcoded PORTFOLIO_CONFIG")
        from engine.strategy_controller import PORTFOLIO_CONFIG
        return PORTFOLIO_CONFIG

    # Check freshness
    freshness = check_freshness(registry)
    if not freshness["fresh"]:
        logger.warning(f"Registry stale: {freshness['warning']} — falling back to hardcoded config")
        from engine.strategy_controller import PORTFOLIO_CONFIG
        return PORTFOLIO_CONFIG

    # Build strategy configs from eligible strategies
    strategies = {}
    for s in registry.get("strategies", []):
        action = s.get("controller_action", "OFF")
        eligible = ACTION_ELIGIBILITY.get(action, False)

        if not eligible and include_probation and action == "PROBATION":
            eligible = True

        if not eligible:
            continue

        # Must have execution_config or be buildable from registry fields
        strategy_id = s["strategy_id"]
        strategies[strategy_id] = _build_strategy_exec_config(s)

    if not strategies:
        logger.warning("No eligible strategies found in registry — falling back to hardcoded config")
        from engine.strategy_controller import PORTFOLIO_CONFIG
        return PORTFOLIO_CONFIG

    return {
        "max_simultaneous_positions": 4,
        "max_positions_per_asset": 2,
        "cluster_window_minutes": 15,
        "max_cluster_entries": 2,
        "strategies": strategies,
        "_source": "strategy_registry",
        "_freshness": freshness,
    }
