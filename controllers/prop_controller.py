"""Generic Prop Controller — applies prop firm risk rules to strategy signals.

This controller sits between strategy signals and execution.
It enforces trailing drawdown, daily loss limits, contract caps,
consistency rules, and phase-based sizing.

Usage:
    config = load_prop_config("controllers/prop_configs/lucid_100k.json")
    controller = PropController(config)
    filtered = controller.apply(trades_df, equity_curve)

The controller NEVER modifies strategy entry/exit logic.
It only filters, sizes, and halts based on account rules.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PropConfig:
    """Prop firm configuration loaded from JSON."""
    name: str
    account_size: float
    trailing_drawdown: float | None = None
    trailing_type: str | None = None  # "eod" or "realtime"
    daily_loss_limit: float | None = None
    max_contracts: int = 1
    consistency_rule: float | None = None
    profit_target: float | None = None
    lock_profit: float | None = None
    lock_behavior: str | None = None
    risk_per_trade_pct: float | None = None
    max_portfolio_risk_pct: float | None = None
    phases: dict | None = None
    notes: str = ""


def load_prop_config(path: str | Path) -> PropConfig:
    """Load a prop config from JSON file."""
    with open(path) as f:
        data = json.load(f)
    return PropConfig(**{k: v for k, v in data.items() if k in PropConfig.__dataclass_fields__})


class PropController:
    """Applies prop firm risk rules to backtest results.

    This is a post-backtest evaluator. It takes a completed backtest
    (trades + equity curve) and determines:
    - Would this have survived the prop rules?
    - Where would halts have occurred?
    - What's the pass/fail probability?
    - What's the payout probability?

    Future: Pre-trade filtering (skip signals when guardrails hit).
    """

    def __init__(self, config: PropConfig):
        self.config = config

    def evaluate(self, trades_df, equity_curve) -> dict:
        """Evaluate a backtest result against prop rules.

        Returns a dict with:
        - passed: bool
        - busted: bool
        - bust_bar: int or None
        - max_drawdown: float
        - trailing_floor_history: list
        - daily_pnl: list
        - halted_days: list
        - consistency_ok: bool or None
        - notes: list of observations
        """
        # Stub — will be implemented in Phase 3
        return {
            "passed": None,
            "busted": None,
            "bust_bar": None,
            "max_drawdown": None,
            "trailing_floor_history": [],
            "daily_pnl": [],
            "halted_days": [],
            "consistency_ok": None,
            "notes": ["PropController.evaluate() not yet implemented — Phase 3"],
        }
