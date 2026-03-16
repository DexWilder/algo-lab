"""Paper Trading Engine — Full 6-strategy pipeline orchestrator.

Simulates live operation by running the validated portfolio through:
    Strategy signals → Strategy Controller → Prop Controller → Execution Logger

Produces daily state snapshots, trade logs, and kill-switch enforcement
matching what live operation would produce.

Usage:
    from engine.paper_trading_engine import PaperTradingEngine

    engine = PaperTradingEngine()
    results = engine.run()
"""

import importlib.util
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.strategy_controller import StrategyController
from engine.strategy_universe import build_portfolio_config
from controllers.prop_controller import load_prop_config, PropController
from execution.signal_logger import (
    PaperTradeLogger, SignalEvent, TradeEvent, ControllerState,
)

try:
    from backtests.run_baseline import ASSET_CONFIG
except ImportError:
    ASSET_CONFIG = {
        "MES": {"point_value": 5.0, "tick_size": 0.25, "commission_per_side": 0.62, "slippage_ticks": 1},
        "MNQ": {"point_value": 2.0, "tick_size": 0.25, "commission_per_side": 0.62, "slippage_ticks": 1},
        "MGC": {"point_value": 10.0, "tick_size": 0.10, "commission_per_side": 0.62, "slippage_ticks": 1},
    }

PROCESSED_DIR = ROOT / "data" / "processed"
CONFIGS_DIR = ROOT / "controllers" / "prop_configs"
OUTPUT_DIR = ROOT / "research" / "phase17_paper_trading"


# ── Kill Switch ──────────────────────────────────────────────────────────────

@dataclass
class KillSwitchState:
    """Portfolio-level kill switch state."""
    active: bool = False
    reason: str = ""
    triggered_at: str = ""

    # Thresholds
    daily_loss_limit: float = 800.0        # portfolio-level daily loss limit
    trailing_dd_limit: float = 4000.0      # portfolio trailing DD limit
    consecutive_loss_limit: int = 8        # halt after N consecutive losers
    correlated_loss_threshold: float = 500.0  # halt if 3+ strategies lose on same day

    # Tracking
    daily_pnl: float = 0.0
    equity_hwm: float = 0.0
    current_equity: float = 0.0
    consecutive_losses: int = 0
    strategies_losing_today: list = field(default_factory=list)


class PortfolioKillSwitch:
    """Portfolio-level risk management and kill switch.

    Enforces:
    1. Daily portfolio loss limit
    2. Portfolio trailing drawdown limit
    3. Consecutive loss circuit breaker
    4. Correlated loss detection (multiple strategies losing same day)
    """

    def __init__(self, starting_equity: float = 50_000.0,
                 daily_loss_limit: float = 800.0,
                 trailing_dd_limit: float = 4000.0,
                 consecutive_loss_limit: int = 8,
                 correlated_loss_threshold: float = 500.0):
        self.state = KillSwitchState(
            daily_loss_limit=daily_loss_limit,
            trailing_dd_limit=trailing_dd_limit,
            consecutive_loss_limit=consecutive_loss_limit,
            correlated_loss_threshold=correlated_loss_threshold,
            equity_hwm=starting_equity,
            current_equity=starting_equity,
        )

    def check(self, daily_pnl_by_strategy: dict, date: str) -> Optional[str]:
        """Check all kill conditions after a trading day.

        Returns reason string if kill switch fires, None otherwise.
        Kill switch is an alert — it fires once per event, then resets.
        Only counts days with actual trades as trading days for consecutive loss tracking.
        """
        total_daily = sum(daily_pnl_by_strategy.values())
        has_trades = any(v != 0 for v in daily_pnl_by_strategy.values())
        self.state.daily_pnl = total_daily
        self.state.current_equity += total_daily
        self.state.equity_hwm = max(self.state.equity_hwm, self.state.current_equity)

        # Reset active flag each day (alert mode, not permanent stop)
        self.state.active = False

        # 1. Daily portfolio loss limit
        if total_daily <= -self.state.daily_loss_limit:
            return self._trigger(
                f"Daily loss limit: ${total_daily:,.0f} exceeds "
                f"-${self.state.daily_loss_limit:,.0f}", date
            )

        # 2. Portfolio trailing drawdown
        dd = self.state.equity_hwm - self.state.current_equity
        if dd >= self.state.trailing_dd_limit:
            return self._trigger(
                f"Trailing DD: ${dd:,.0f} exceeds ${self.state.trailing_dd_limit:,.0f}",
                date
            )

        # 3. Consecutive losses (only count actual trading days)
        if has_trades:
            if total_daily < 0:
                self.state.consecutive_losses += 1
            else:
                self.state.consecutive_losses = 0

        if self.state.consecutive_losses >= self.state.consecutive_loss_limit:
            reason = self._trigger(
                f"Consecutive losing trading days: {self.state.consecutive_losses}", date
            )
            # Reset counter after firing so it doesn't fire every day
            self.state.consecutive_losses = 0
            return reason

        # 4. Correlated loss detection
        losing_strats = [
            k for k, v in daily_pnl_by_strategy.items() if v < 0
        ]
        if (len(losing_strats) >= 3
                and total_daily <= -self.state.correlated_loss_threshold):
            self.state.strategies_losing_today = losing_strats
            return self._trigger(
                f"Correlated loss: {len(losing_strats)} strategies lost "
                f"${total_daily:,.0f} on same day", date
            )

        return None

    def _trigger(self, reason: str, date: str) -> str:
        self.state.active = True
        self.state.reason = reason
        self.state.triggered_at = date
        return reason

    def reset_daily(self):
        """Reset daily tracking (called at start of each day)."""
        self.state.daily_pnl = 0.0
        self.state.strategies_losing_today = []

    def get_state(self) -> dict:
        return asdict(self.state)


# ── Daily State Tracker ──────────────────────────────────────────────────────

@dataclass
class DailyState:
    """Complete state snapshot for one trading day."""
    date: str
    regime: dict = field(default_factory=dict)
    active_strategies: list = field(default_factory=list)
    blocked_strategies: dict = field(default_factory=dict)  # {strat: reason}
    signals_generated: int = 0
    signals_taken: int = 0
    signals_blocked: int = 0
    trades_completed: list = field(default_factory=list)
    daily_pnl_by_strategy: dict = field(default_factory=dict)
    portfolio_daily_pnl: float = 0.0
    cumulative_pnl: float = 0.0
    equity: float = 0.0
    equity_hwm: float = 0.0
    trailing_dd: float = 0.0
    kill_switch_status: str = "OK"
    notes: list = field(default_factory=list)


# ── Paper Trading Engine ─────────────────────────────────────────────────────

class PaperTradingEngine:
    """Orchestrates the full 6-strategy paper trading pipeline.

    Runs historical data through the complete stack:
    1. Load strategies and generate signals
    2. Run backtests to get trade lists
    3. Apply Strategy Controller (regime + timing + coordination)
    4. Apply Prop Controller (trailing DD, daily limits, phases)
    5. Apply Portfolio Kill Switch
    6. Log daily state and produce audit trail
    """

    def __init__(
        self,
        portfolio_config: dict = None,
        prop_config_path: str = None,
        starting_equity: float = 50_000.0,
        output_dir: Path = None,
    ):
        self.config = portfolio_config or build_portfolio_config()
        self.starting_equity = starting_equity
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Components
        self.regime_engine = RegimeEngine()
        self.strategy_controller = StrategyController(self.config)
        self.kill_switch = PortfolioKillSwitch(starting_equity=starting_equity)
        self.logger = PaperTradeLogger(
            log_dir=self.output_dir / "daily_logs"
        )

        # Prop controller (optional)
        self.prop_controller = None
        if prop_config_path:
            config = load_prop_config(prop_config_path)
            self.prop_controller = PropController(config)

        # State
        self.daily_states: list[DailyState] = []

    def _load_strategy(self, name: str):
        path = ROOT / "strategies" / name / "strategy.py"
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def _get_daily_pnl(self, trades: pd.DataFrame) -> pd.Series:
        if trades.empty:
            return pd.Series(dtype=float)
        tmp = trades.copy()
        tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
        daily = tmp.groupby("date")["pnl"].sum()
        daily.index = pd.to_datetime(daily.index)
        return daily

    def run(self) -> dict:
        """Execute the full paper trading simulation.

        Returns dict with:
            - daily_states: list of DailyState dicts
            - portfolio_summary: aggregate metrics
            - kill_switch_state: final kill switch state
            - prop_result: prop controller result (if configured)
            - trade_audit: per-strategy trade audit
        """
        strat_configs = self.config["strategies"]

        # ── Step 1: Generate all baseline trades ─────────────────────────
        print("  Step 1: Generating baseline signals and trades...")
        data_cache = {}
        regime_daily_cache = {}
        baseline_trades = {}

        for strat_key, strat in strat_configs.items():
            asset = strat["asset"]
            config = ASSET_CONFIG[asset]

            if asset not in data_cache:
                df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
                df["datetime"] = pd.to_datetime(df["datetime"])
                data_cache[asset] = df
                regime_daily_cache[asset] = self.regime_engine.get_daily_regimes(df)

            df = data_cache[asset]
            mod = self._load_strategy(strat["name"])
            if hasattr(mod, "TICK_SIZE"):
                mod.TICK_SIZE = config["tick_size"]

            if strat.get("exit_variant") == "profit_ladder":
                from research.exit_evolution import donchian_entries, apply_profit_ladder
                data = donchian_entries(df)
                signals = apply_profit_ladder(data)
            else:
                signals = mod.generate_signals(df)

            result = run_backtest(
                df, signals,
                mode=strat["mode"],
                point_value=config["point_value"],
                symbol=asset,
            )
            trades = result["trades_df"]

            # Apply GRINDING filter for Donchian
            if strat.get("grinding_filter") and not trades.empty:
                rd = regime_daily_cache[asset].copy()
                rd["_date"] = pd.to_datetime(rd["_date"])
                rd["_date_date"] = rd["_date"].dt.date
                trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
                trades = trades.merge(
                    rd[["_date_date", "trend_persistence"]],
                    left_on="entry_date", right_on="_date_date", how="left",
                )
                trades = trades[trades["trend_persistence"] == "GRINDING"]
                trades = trades.drop(
                    columns=["entry_date", "_date_date", "trend_persistence"],
                    errors="ignore",
                ).reset_index(drop=True)

            baseline_trades[strat_key] = trades
            tc = len(trades)
            pnl = trades["pnl"].sum() if not trades.empty else 0
            print(f"    {strat_key}: {tc} trades, PnL=${pnl:,.0f}")

        # ── Step 2: Apply Strategy Controller ────────────────────────────
        print("\n  Step 2: Applying strategy controller...")
        ctrl_result = self.strategy_controller.simulate(
            baseline_trades, regime_daily_cache
        )
        controlled_trades = ctrl_result["filtered_trades"]
        filter_stats = ctrl_result["filter_stats"]

        total_base = sum(len(t) for t in baseline_trades.values())
        total_ctrl = sum(len(t) for t in controlled_trades.values())
        print(f"    Trades: {total_base} baseline → {total_ctrl} controlled")

        # ── Step 3: Build daily state timeline ───────────────────────────
        print("\n  Step 3: Building daily state timeline...")

        # Collect all trading dates
        all_dates = set()
        daily_pnl_by_strat = {}

        for strat_key, trades in controlled_trades.items():
            daily = self._get_daily_pnl(trades)
            daily_pnl_by_strat[strat_key] = daily
            all_dates.update(daily.index)

        # Also add dates from baseline (to track blocked days)
        for strat_key, trades in baseline_trades.items():
            daily = self._get_daily_pnl(trades)
            all_dates.update(daily.index)

        all_dates = sorted(all_dates)
        cumulative_pnl = 0.0
        equity = self.starting_equity

        # Build regime lookup per asset per date
        regime_lookup = {}
        for asset, rd in regime_daily_cache.items():
            rd_copy = rd.copy()
            rd_copy["_date"] = pd.to_datetime(rd_copy["_date"])
            for _, row in rd_copy.iterrows():
                date_key = row["_date"].date()
                if date_key not in regime_lookup:
                    regime_lookup[date_key] = {}
                regime_lookup[date_key][asset] = {
                    "vol_regime": row["vol_regime"],
                    "trend_regime": row["trend_regime"],
                    "rv_regime": row["rv_regime"],
                    "trend_persistence": row["trend_persistence"],
                }

        # ── Step 4: Process each day ─────────────────────────────────────
        for date in all_dates:
            date_date = date.date() if hasattr(date, "date") else date

            # Get regime for this date (use MES as reference)
            day_regime = regime_lookup.get(date_date, {})
            regime_summary = {}
            for asset in ["MES", "MNQ", "MGC"]:
                if asset in day_regime:
                    regime_summary = day_regime[asset]
                    break

            # Determine active/blocked strategies
            active = []
            blocked = {}
            for strat_key in strat_configs:
                allowed, reason = self.strategy_controller.should_allow_entry(
                    strat_key, "10:00", regime_summary
                )
                if allowed:
                    active.append(strat_key)
                else:
                    blocked[strat_key] = reason

            # Compute daily PnL
            day_pnl_map = {}
            for strat_key in strat_configs:
                daily = daily_pnl_by_strat.get(strat_key, pd.Series(dtype=float))
                if date in daily.index:
                    day_pnl_map[strat_key] = daily[date]

            portfolio_daily = sum(day_pnl_map.values())
            cumulative_pnl += portfolio_daily
            equity = self.starting_equity + cumulative_pnl
            equity_hwm = max(
                self.kill_switch.state.equity_hwm,
                equity,
            )
            trailing_dd = equity_hwm - equity

            # Check kill switch
            self.kill_switch.reset_daily()
            kill_reason = self.kill_switch.check(day_pnl_map, str(date_date))

            # Count signals
            base_count = sum(
                1 for sk in strat_configs
                if not baseline_trades[sk].empty
                and date_date in pd.to_datetime(
                    baseline_trades[sk]["entry_time"]
                ).dt.date.values
            )
            ctrl_count = sum(
                1 for sk in strat_configs
                if not controlled_trades[sk].empty
                and date_date in pd.to_datetime(
                    controlled_trades[sk]["entry_time"]
                ).dt.date.values
            )

            # Build trades list for this day
            day_trades = []
            for strat_key, trades in controlled_trades.items():
                if trades.empty:
                    continue
                t = trades.copy()
                t["exit_date"] = pd.to_datetime(t["exit_time"]).dt.date
                day_t = t[t["exit_date"] == date_date]
                for _, row in day_t.iterrows():
                    day_trades.append({
                        "strategy": strat_key,
                        "entry_time": str(row["entry_time"]),
                        "exit_time": str(row["exit_time"]),
                        "side": row.get("side", ""),
                        "pnl": float(row["pnl"]),
                    })

            # Create daily state
            state = DailyState(
                date=str(date_date),
                regime=regime_summary,
                active_strategies=active,
                blocked_strategies=blocked,
                signals_generated=base_count,
                signals_taken=ctrl_count,
                signals_blocked=base_count - ctrl_count,
                trades_completed=day_trades,
                daily_pnl_by_strategy={k: float(v) for k, v in day_pnl_map.items()},
                portfolio_daily_pnl=float(portfolio_daily),
                cumulative_pnl=float(cumulative_pnl),
                equity=float(equity),
                equity_hwm=float(equity_hwm),
                trailing_dd=float(trailing_dd),
                kill_switch_status=kill_reason or "OK",
            )

            if kill_reason:
                state.notes.append(f"KILL SWITCH: {kill_reason}")

            self.daily_states.append(state)

            # Log to PaperTradeLogger
            self.logger.start_day(str(date_date), regime_summary)
            for trade in day_trades:
                self.logger.log_trade(TradeEvent(
                    strategy=trade["strategy"],
                    entry_time=trade["entry_time"],
                    entry_price=0,  # not tracked in aggregated view
                    exit_time=trade["exit_time"],
                    exit_price=0,
                    direction=trade.get("side", ""),
                    pnl=trade["pnl"],
                    exit_reason="backtest",
                ))
            self.logger.log_controller_state(ControllerState(
                equity=equity,
                trailing_floor=equity_hwm - self.kill_switch.state.trailing_dd_limit,
                phase="paper",
                daily_pnl=portfolio_daily,
                cumulative_pnl=cumulative_pnl,
            ))
            self.logger.end_day()

        print(f"    Processed {len(all_dates)} trading days")

        # ── Step 5: Apply Prop Controller (optional) ─────────────────────
        prop_result = None
        if self.prop_controller:
            print("\n  Step 5: Applying prop controller...")
            all_ctrl_trades = pd.concat(
                [t for t in controlled_trades.values() if not t.empty],
                ignore_index=True,
            ).sort_values("exit_time").reset_index(drop=True)

            if not all_ctrl_trades.empty:
                prop_result = self.prop_controller.simulate(all_ctrl_trades)
                status = "PASSED" if prop_result["passed"] else "BUSTED"
                print(f"    Prop result: {status}")
                if prop_result.get("locked"):
                    print(f"    Locked on: {prop_result['lock_date']}")

        # ── Step 6: Build summary ────────────────────────────────────────
        print("\n  Step 6: Building summary...")

        portfolio_daily_series = pd.Series(
            {pd.Timestamp(s.date): s.portfolio_daily_pnl for s in self.daily_states}
        ).sort_index()

        total_pnl = portfolio_daily_series.sum()
        sharpe = (
            portfolio_daily_series.mean() / portfolio_daily_series.std() * np.sqrt(252)
            if portfolio_daily_series.std() > 0 else 0
        )
        eq = self.starting_equity + portfolio_daily_series.cumsum()
        peak = eq.cummax()
        dd = peak - eq
        maxdd = dd.max()
        calmar = total_pnl / maxdd if maxdd > 0 else 0

        monthly = portfolio_daily_series.resample("ME").sum()
        profitable_months = (monthly > 0).sum()
        total_months = len(monthly)

        # Active strategy distribution
        active_counts = {}
        for s in self.daily_states:
            for strat in s.active_strategies:
                active_counts[strat] = active_counts.get(strat, 0) + 1

        # Kill switch events
        kill_events = [
            {"date": s.date, "reason": s.kill_switch_status}
            for s in self.daily_states
            if s.kill_switch_status != "OK"
        ]

        summary = {
            "total_pnl": float(total_pnl),
            "sharpe": float(sharpe),
            "calmar": float(calmar),
            "maxdd": float(maxdd),
            "maxdd_date": str(dd.idxmax()) if len(dd) > 0 else "",
            "total_trades_baseline": total_base,
            "total_trades_controlled": total_ctrl,
            "trade_retention_pct": total_ctrl / total_base * 100 if total_base > 0 else 0,
            "trading_days": len(all_dates),
            "profitable_months": f"{profitable_months}/{total_months}",
            "monthly_pct": profitable_months / total_months * 100 if total_months > 0 else 0,
            "active_strategy_days": active_counts,
            "kill_switch_events": kill_events,
            "per_strategy_pnl": {
                sk: float(daily_pnl_by_strat.get(sk, pd.Series(dtype=float)).sum())
                for sk in strat_configs
            },
            "per_strategy_trades": {
                sk: len(controlled_trades[sk])
                for sk in strat_configs
            },
            "filter_stats": {k: v for k, v in filter_stats.items()},
        }

        # ── Step 7: Save results ─────────────────────────────────────────
        results = {
            "summary": summary,
            "kill_switch_final": self.kill_switch.get_state(),
            "prop_result": (
                {k: v for k, v in prop_result.items()
                 if k != "filtered_trades_df"}
                if prop_result else None
            ),
        }

        results_path = self.output_dir / "phase17_results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Save daily states
        states_path = self.output_dir / "daily_states.json"
        with open(states_path, "w") as f:
            json.dump([asdict(s) for s in self.daily_states], f, indent=2)

        # Save equity curve CSV
        eq_df = pd.DataFrame([
            {
                "date": s.date,
                "equity": s.equity,
                "daily_pnl": s.portfolio_daily_pnl,
                "cumulative_pnl": s.cumulative_pnl,
                "trailing_dd": s.trailing_dd,
                "active_strategies": len(s.active_strategies),
                "trades": len(s.trades_completed),
                "kill_switch": s.kill_switch_status,
            }
            for s in self.daily_states
        ])
        eq_df.to_csv(self.output_dir / "equity_curve.csv", index=False)

        return results
