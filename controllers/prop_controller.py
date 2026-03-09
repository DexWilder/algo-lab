"""Generic Prop Controller — applies prop firm risk rules to strategy signals.

This controller sits between strategy signals and execution.
It enforces trailing drawdown, daily loss limits, contract caps,
consistency rules, and phase-based sizing.

Usage:
    config = load_prop_config("controllers/prop_configs/lucid_100k.json")
    controller = PropController(config)
    result = controller.simulate(trades_df)

The controller NEVER modifies strategy entry/exit logic.
It only filters, sizes, and halts based on account rules.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


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

    Walks through trades chronologically, enforcing:
    - Trailing drawdown (EOD high-water mark)
    - Daily loss limits (per-phase or global)
    - Contract caps (per-phase or global)
    - Profit lock (floor stops trailing after lock threshold)
    - Phase transitions (P1 → P2 with different rules)
    """

    def __init__(self, config: PropConfig):
        self.config = config

    def _get_phase(self, cumulative_profit):
        """Determine which phase we're in based on cumulative profit."""
        if not self.config.phases:
            return None, {
                "max_contracts": self.config.max_contracts,
                "max_daily_loss": self.config.daily_loss_limit,
                "max_trades_per_day": None,
            }

        sorted_keys = sorted(self.config.phases.keys())

        for phase_key in sorted_keys:
            phase = self.config.phases[phase_key]
            low = phase["profit_range"][0]
            high = phase["profit_range"][1]
            if high is None:
                high = float("inf")
            if low <= cumulative_profit < high:
                return phase_key, phase

        # If profit is below first phase's lower bound (e.g., negative),
        # stay in the first phase
        first_key = sorted_keys[0]
        first_phase = self.config.phases[first_key]
        if cumulative_profit < first_phase["profit_range"][0]:
            return first_key, first_phase

        # Default to last phase (profit above all ranges)
        last_key = sorted_keys[-1]
        return last_key, self.config.phases[last_key]

    def simulate(self, trades_df, starting_equity=None):
        """Walk through trades chronologically, enforcing all prop rules.

        Parameters
        ----------
        trades_df : pd.DataFrame
            Trade log with entry_time, exit_time, side, pnl, contracts columns.
        starting_equity : float, optional
            Override starting equity (default: config.account_size).

        Returns
        -------
        dict with:
            passed: bool - did the account survive?
            busted: bool - did trailing DD bust the account?
            bust_date: str or None - date of bust
            final_equity: float
            final_profit: float
            trailing_floor_final: float
            locked: bool - did profit lock engage?
            lock_date: str or None
            phase_transitions: list of dicts
            halted_days: list of dates where trading was stopped
            skipped_trades: int - trades filtered by rules
            skipped_by_daily_loss: int
            skipped_by_contract_cap: int
            filtered_trades_df: DataFrame of trades that would have executed
            daily_summaries: list of per-day accounting
            notes: list of observations
        """
        if trades_df.empty:
            return self._empty_result(starting_equity)

        cfg = self.config
        equity = starting_equity or cfg.account_size
        trailing_dd = cfg.trailing_drawdown or float("inf")

        # State
        cumulative_profit = 0.0
        eod_hwm = equity  # end-of-day high water mark
        trailing_floor = equity - trailing_dd
        locked = False
        lock_date = None
        busted = False
        bust_date = None
        current_phase_key = None

        # Tracking
        phase_transitions = []
        halted_days = []
        daily_summaries = []
        filtered_trades = []
        skipped_daily_loss = 0
        skipped_contract_cap = 0
        skipped_total = 0
        notes = []

        # Organize trades by date
        trades = trades_df.copy()
        trades["_exit_date"] = pd.to_datetime(trades["exit_time"]).dt.date

        for date, day_trades in trades.groupby("_exit_date"):
            if busted:
                skipped_total += len(day_trades)
                continue

            # Determine current phase
            phase_key, phase_rules = self._get_phase(cumulative_profit)
            if phase_key != current_phase_key:
                if current_phase_key is not None:
                    phase_transitions.append({
                        "date": str(date),
                        "from": current_phase_key,
                        "to": phase_key,
                        "profit_at_transition": round(cumulative_profit, 2),
                    })
                    notes.append(f"Phase transition {current_phase_key}→{phase_key} on {date} at ${cumulative_profit:.2f}")
                current_phase_key = phase_key

            # Phase constraints
            max_daily_loss = phase_rules.get("max_daily_loss")
            max_trades = phase_rules.get("max_trades_per_day")
            max_contracts = phase_rules.get("max_contracts", cfg.max_contracts)

            day_pnl = 0.0
            day_trades_taken = 0
            day_halted = False

            for _, trade in day_trades.iterrows():
                # Check daily loss limit
                if max_daily_loss and day_pnl <= -max_daily_loss:
                    skipped_daily_loss += 1
                    skipped_total += 1
                    if not day_halted:
                        day_halted = True
                        halted_days.append(str(date))
                        notes.append(f"Daily loss halt on {date}: ${day_pnl:.2f} hit ${-max_daily_loss:.2f} limit")
                    continue

                # Check trade count limit
                if max_trades and day_trades_taken >= max_trades:
                    skipped_total += 1
                    continue

                # Check contract cap
                trade_contracts = trade.get("contracts", 1)
                if trade_contracts > max_contracts:
                    skipped_contract_cap += 1
                    skipped_total += 1
                    continue

                # Execute trade
                pnl = trade["pnl"]
                day_pnl += pnl
                cumulative_profit += pnl
                equity += pnl
                day_trades_taken += 1
                filtered_trades.append(trade)

                # Check realtime bust (intraday)
                if cfg.trailing_type == "realtime" and equity < trailing_floor:
                    busted = True
                    bust_date = str(date)
                    notes.append(f"BUSTED (realtime) on {date}: equity ${equity:.2f} < floor ${trailing_floor:.2f}")
                    break

            # End of day processing
            if not busted:
                # EOD trailing drawdown update
                if cfg.trailing_type == "eod":
                    if equity > eod_hwm:
                        eod_hwm = equity
                        if not locked:
                            trailing_floor = eod_hwm - trailing_dd

                    # Check EOD bust
                    if equity < trailing_floor:
                        busted = True
                        bust_date = str(date)
                        notes.append(f"BUSTED (EOD) on {date}: equity ${equity:.2f} < floor ${trailing_floor:.2f}")

                # Check profit lock
                if not locked and cfg.lock_profit and cumulative_profit >= cfg.lock_profit:
                    locked = True
                    lock_date = str(date)
                    # Lock floor: starting + lock_profit - trailing_dd
                    lock_floor = (starting_equity or cfg.account_size) + cfg.lock_profit - trailing_dd
                    trailing_floor = max(trailing_floor, lock_floor)
                    notes.append(f"LOCKED on {date}: profit ${cumulative_profit:.2f} >= ${cfg.lock_profit}. "
                                 f"Floor locked at ${trailing_floor:.2f}")

            daily_summaries.append({
                "date": str(date),
                "trades_taken": day_trades_taken,
                "trades_skipped": len(day_trades) - day_trades_taken,
                "day_pnl": round(day_pnl, 2),
                "cumulative_profit": round(cumulative_profit, 2),
                "equity": round(equity, 2),
                "trailing_floor": round(trailing_floor, 2),
                "eod_hwm": round(eod_hwm, 2),
                "phase": current_phase_key,
                "halted": day_halted,
                "busted": busted,
            })

        # Build filtered trades DataFrame
        if filtered_trades:
            filtered_df = pd.DataFrame(filtered_trades)
            filtered_df = filtered_df.drop(columns=["_exit_date"], errors="ignore")
        else:
            filtered_df = pd.DataFrame(columns=trades_df.columns)

        # Check profit target
        hit_target = False
        if cfg.profit_target and cumulative_profit >= cfg.profit_target:
            hit_target = True
            notes.append(f"Hit profit target: ${cumulative_profit:.2f} >= ${cfg.profit_target}")

        passed = not busted

        return {
            "passed": passed,
            "busted": busted,
            "bust_date": bust_date,
            "final_equity": round(equity, 2),
            "final_profit": round(cumulative_profit, 2),
            "trailing_floor_final": round(trailing_floor, 2),
            "eod_hwm": round(eod_hwm, 2),
            "locked": locked,
            "lock_date": lock_date,
            "hit_profit_target": hit_target,
            "phase_transitions": phase_transitions,
            "halted_days": halted_days,
            "total_trades_input": len(trades_df),
            "total_trades_executed": len(filtered_df),
            "skipped_trades": skipped_total,
            "skipped_by_daily_loss": skipped_daily_loss,
            "skipped_by_contract_cap": skipped_contract_cap,
            "filtered_trades_df": filtered_df,
            "daily_summaries": daily_summaries,
            "notes": notes,
        }

    def evaluate(self, trades_df, equity_curve=None):
        """Evaluate a backtest result against prop rules.

        Convenience wrapper around simulate(). Passes through to simulate()
        and returns the same result dict.
        """
        return self.simulate(trades_df)

    def _empty_result(self, starting_equity=None):
        equity = starting_equity or self.config.account_size
        return {
            "passed": True,
            "busted": False,
            "bust_date": None,
            "final_equity": equity,
            "final_profit": 0.0,
            "trailing_floor_final": equity - (self.config.trailing_drawdown or 0),
            "eod_hwm": equity,
            "locked": False,
            "lock_date": None,
            "hit_profit_target": False,
            "phase_transitions": [],
            "halted_days": [],
            "total_trades_input": 0,
            "total_trades_executed": 0,
            "skipped_trades": 0,
            "skipped_by_daily_loss": 0,
            "skipped_by_contract_cap": 0,
            "filtered_trades_df": pd.DataFrame(),
            "daily_summaries": [],
            "notes": ["No trades to evaluate"],
        }
