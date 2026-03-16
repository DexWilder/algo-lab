"""Strategy Controller — Regime-aware portfolio coordination layer.

Sits between strategy signal generation and execution/backtest.
Decides which strategies are active, applies soft timing preferences,
coordinates portfolio-level exposure, and prevents clustered risk.

Architecture:
    Strategy signals → StrategyController → filtered trades → PropController → Execution

Usage:
    from engine.strategy_controller import StrategyController, PORTFOLIO_CONFIG

    controller = StrategyController(PORTFOLIO_CONFIG)
    result = controller.simulate(data_cache, regime_daily_cache)
"""

import numpy as np
import pandas as pd


# ── Portfolio Configuration (LEGACY FALLBACK) ────────────────────────────────
# DEPRECATED: Use engine.strategy_universe.build_portfolio_config() instead.
# This hardcoded config is retained as a safety fallback if the strategy
# registry is unavailable or corrupted. The canonical source of truth is
# research/data/strategy_registry.json.

PORTFOLIO_CONFIG = {
    # ── Global portfolio limits ──────────────────────────────────────────
    "max_simultaneous_positions": 4,     # max open positions across all strategies
    "max_positions_per_asset": 2,        # max open positions on same underlying
    "cluster_window_minutes": 15,        # entries within this window count as clustered
    "max_cluster_entries": 2,            # max entries allowed within cluster window

    # ── Strategy definitions ─────────────────────────────────────────────
    "strategies": {
        "PB-MGC-Short": {
            "name": "pb_trend",
            "asset": "MGC",
            "mode": "short",
            "grinding_filter": False,
            "exit_variant": None,

            # Regime gate (from validated profiles)
            "avoid_regimes": ["LOW_VOL", "NORMAL_RV", "LOW_RV"],
            "preferred_regimes": ["TRENDING", "HIGH_RV"],

            # Soft timing preference
            "preferred_window": ("08:30", "12:00"),
            "allowed_window": ("08:30", "15:15"),
            "conviction_threshold_outside": 3,  # need 3+ regime factors aligned

            # Priority (higher = preferred when conflicts arise)
            "priority": 5,
        },

        "ORB-MGC-Long": {
            "name": "orb_009",
            "asset": "MGC",
            "mode": "long",
            "grinding_filter": False,
            "exit_variant": None,

            "avoid_regimes": ["RANGING"],
            "preferred_regimes": ["HIGH_VOL", "TRENDING", "HIGH_RV"],

            "preferred_window": ("10:00", "12:00"),
            "allowed_window": ("10:00", "15:00"),
            "conviction_threshold_outside": 2,

            "priority": 5,
        },

        "VWAP-MNQ-Long": {
            "name": "vwap_trend",
            "asset": "MNQ",
            "mode": "long",
            "grinding_filter": False,
            "exit_variant": None,

            "avoid_regimes": ["RANGING"],
            "preferred_regimes": ["TRENDING", "LOW_VOL", "NORMAL_RV"],

            "preferred_window": ("10:00", "13:00"),
            "allowed_window": ("10:00", "14:30"),
            "conviction_threshold_outside": 2,

            "priority": 6,  # highest-validated strategy
        },

        "XB-PB-EMA-MES-Short": {
            "name": "xb_pb_ema_timestop",
            "asset": "MES",
            "mode": "short",
            "grinding_filter": False,
            "exit_variant": None,

            "avoid_regimes": ["LOW_VOL", "RANGING"],
            "preferred_regimes": ["TRENDING", "HIGH_VOL", "HIGH_RV"],

            "preferred_window": ("09:30", "12:00"),
            "allowed_window": ("09:30", "15:00"),
            "conviction_threshold_outside": 3,

            "priority": 4,
        },

        "BB-EQ-MGC-Long": {
            "name": "bb_equilibrium",
            "asset": "MGC",
            "mode": "long",
            "grinding_filter": False,
            "exit_variant": None,

            # Gold Snapback: profits in TRENDING (trend-snapback), not RANGING
            "avoid_regimes": ["RANGING", "LOW_RV"],
            "preferred_regimes": ["TRENDING", "HIGH_RV", "NORMAL_RV"],

            "preferred_window": ("09:45", "14:45"),
            "allowed_window": ("09:45", "14:45"),
            "conviction_threshold_outside": 3,

            "priority": 4,
        },

        "Donchian-MNQ-Long-GRINDING": {
            "name": "donchian_trend",
            "asset": "MNQ",
            "mode": "long",
            "grinding_filter": True,
            "exit_variant": "profit_ladder",

            "avoid_regimes": [],  # GRINDING filter handles regime gating
            "preferred_regimes": ["TRENDING", "HIGH_VOL"],

            # Probation: higher conviction required everywhere
            "preferred_window": ("09:30", "14:00"),
            "allowed_window": ("09:30", "14:00"),
            "conviction_threshold_outside": 4,

            "priority": 3,  # probation — lowest priority
        },
    },
}


class StrategyController:
    """Regime-aware strategy activation and portfolio coordination.

    Core responsibilities:
    1. Regime gate: block strategies in their avoid_regimes
    2. Soft timing: prefer signals in preferred_window, allow outside with conviction
    3. Portfolio coordination: cap simultaneous positions, limit asset overlap, prevent clusters
    4. Conviction scoring: count aligned regime factors per strategy per day
    """

    def __init__(self, config: dict):
        self.config = config
        self.strategies = config["strategies"]
        self.max_positions = config["max_simultaneous_positions"]
        self.max_per_asset = config["max_positions_per_asset"]
        self.cluster_window = config["cluster_window_minutes"]
        self.max_cluster = config["max_cluster_entries"]

    # ── Regime Gating ────────────────────────────────────────────────────

    def is_regime_allowed(self, strat_key: str, day_regime: dict) -> bool:
        """Check if a strategy is allowed in the current regime."""
        strat = self.strategies[strat_key]
        avoid = set(strat.get("avoid_regimes", []))
        if not avoid:
            return True

        current = set()
        for key in ["vol_regime", "trend_regime", "rv_regime"]:
            if key in day_regime:
                current.add(day_regime[key])

        return not (avoid & current)

    def conviction_score(self, strat_key: str, day_regime: dict) -> int:
        """Score how many preferred regime factors are currently active (0-4)."""
        strat = self.strategies[strat_key]
        preferred = set(strat.get("preferred_regimes", []))
        if not preferred:
            return 2  # neutral — no preference defined

        score = 0
        for key in ["vol_regime", "trend_regime", "rv_regime", "trend_persistence"]:
            if key in day_regime and day_regime[key] in preferred:
                score += 1
        return score

    # ── Soft Timing ──────────────────────────────────────────────────────

    def is_in_preferred_window(self, strat_key: str, time_str: str) -> bool:
        """Check if current time is within the strategy's preferred window."""
        strat = self.strategies[strat_key]
        start, end = strat["preferred_window"]
        return start <= time_str < end

    def is_in_allowed_window(self, strat_key: str, time_str: str) -> bool:
        """Check if current time is within the strategy's allowed (wider) window."""
        strat = self.strategies[strat_key]
        start, end = strat["allowed_window"]
        return start <= time_str < end

    def should_allow_entry(self, strat_key: str, time_str: str,
                           day_regime: dict) -> tuple[bool, str]:
        """Determine if an entry should be allowed based on timing + conviction.

        Returns (allowed, reason).
        """
        if not self.is_regime_allowed(strat_key, day_regime):
            return False, "regime_blocked"

        in_preferred = self.is_in_preferred_window(strat_key, time_str)
        in_allowed = self.is_in_allowed_window(strat_key, time_str)

        if in_preferred:
            return True, "preferred_window"

        if in_allowed:
            conv = self.conviction_score(strat_key, day_regime)
            threshold = self.strategies[strat_key]["conviction_threshold_outside"]
            if conv >= threshold:
                return True, f"conviction_override_{conv}"
            return False, f"low_conviction_{conv}_need_{threshold}"

        return False, "outside_allowed_window"

    # ── Portfolio Coordination ───────────────────────────────────────────

    def filter_trades_by_portfolio(self, all_trades: dict) -> dict:
        """Apply portfolio-level coordination to filter overlapping trades.

        Takes {strat_key: trades_df} and returns filtered version.
        Enforces:
        - Max simultaneous positions
        - Max per-asset overlap
        - Cluster prevention (too many entries in short window)

        Trades are merged into a unified timeline, then conflicts resolved
        by strategy priority.
        """
        # Collect all trades with strategy metadata
        trade_list = []
        for strat_key, trades in all_trades.items():
            if trades.empty:
                continue
            strat = self.strategies[strat_key]
            t = trades.copy()
            t["strat_key"] = strat_key
            t["asset"] = strat["asset"]
            t["priority"] = strat["priority"]
            t["entry_dt"] = pd.to_datetime(t["entry_time"])
            t["exit_dt"] = pd.to_datetime(t["exit_time"])
            trade_list.append(t)

        if not trade_list:
            return all_trades

        unified = pd.concat(trade_list, ignore_index=True)
        unified = unified.sort_values("entry_dt").reset_index(drop=True)

        # Track active positions and filter
        kept_indices = set()
        active_positions = []  # list of (exit_dt, asset, strat_key)

        for idx, row in unified.iterrows():
            entry_dt = row["entry_dt"]

            # Expire completed positions
            active_positions = [
                (exit_dt, asset, sk)
                for exit_dt, asset, sk in active_positions
                if exit_dt > entry_dt
            ]

            # Check max simultaneous positions
            if len(active_positions) >= self.max_positions:
                continue

            # Check max per-asset
            asset_count = sum(1 for _, a, _ in active_positions if a == row["asset"])
            if asset_count >= self.max_per_asset:
                continue

            # Check cluster (entries within window)
            cluster_start = entry_dt - pd.Timedelta(minutes=self.cluster_window)
            recent_entries = [
                i for i in kept_indices
                if unified.loc[i, "entry_dt"] >= cluster_start
            ]
            if len(recent_entries) >= self.max_cluster:
                # Allow only if this strategy has higher priority than lowest in cluster
                cluster_priorities = [unified.loc[i, "priority"] for i in recent_entries]
                if row["priority"] <= min(cluster_priorities):
                    continue

            kept_indices.add(idx)
            active_positions.append((row["exit_dt"], row["asset"], row["strat_key"]))

        # Rebuild per-strategy filtered trades
        kept = unified.loc[sorted(kept_indices)]
        result = {}
        for strat_key in all_trades:
            strat_kept = kept[kept["strat_key"] == strat_key]
            if strat_kept.empty:
                result[strat_key] = pd.DataFrame(columns=all_trades[strat_key].columns)
            else:
                # Drop controller columns
                drop_cols = ["strat_key", "asset", "priority", "entry_dt", "exit_dt"]
                result[strat_key] = strat_kept.drop(
                    columns=[c for c in drop_cols if c in strat_kept.columns],
                    errors="ignore",
                ).reset_index(drop=True)

        return result

    # ── Trade-Level Regime + Timing Filter ───────────────────────────────

    def filter_trades_by_regime_and_timing(
        self,
        strat_key: str,
        trades: pd.DataFrame,
        regime_daily: pd.DataFrame,
    ) -> tuple[pd.DataFrame, dict]:
        """Filter individual trades by regime gate and soft timing.

        Returns (filtered_trades, filter_stats).
        """
        if trades.empty:
            return trades, {"total": 0, "kept": 0, "regime_blocked": 0,
                            "timing_blocked": 0, "conviction_override": 0}

        t = trades.copy()
        t["entry_dt"] = pd.to_datetime(t["entry_time"])
        t["entry_date"] = t["entry_dt"].dt.date
        t["entry_time_str"] = t["entry_dt"].dt.strftime("%H:%M")

        # Merge regime
        regime_daily = regime_daily.copy()
        regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
        regime_daily["_date_date"] = regime_daily["_date"].dt.date

        t = t.merge(
            regime_daily[["_date_date", "vol_regime", "trend_regime",
                          "rv_regime", "trend_persistence"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )

        stats = {"total": len(t), "kept": 0, "regime_blocked": 0,
                 "timing_blocked": 0, "conviction_override": 0,
                 "preferred_window": 0}

        keep_mask = []
        for _, row in t.iterrows():
            day_regime = {
                "vol_regime": row.get("vol_regime", "NORMAL"),
                "trend_regime": row.get("trend_regime", "RANGING"),
                "rv_regime": row.get("rv_regime", "NORMAL_RV"),
                "trend_persistence": row.get("trend_persistence", "CHOPPY"),
            }
            allowed, reason = self.should_allow_entry(
                strat_key, row["entry_time_str"], day_regime
            )
            keep_mask.append(allowed)

            if not allowed:
                if reason == "regime_blocked":
                    stats["regime_blocked"] += 1
                else:
                    stats["timing_blocked"] += 1
            else:
                stats["kept"] += 1
                if reason == "preferred_window":
                    stats["preferred_window"] += 1
                elif reason.startswith("conviction_override"):
                    stats["conviction_override"] += 1

        filtered = t[keep_mask]

        # Drop merge columns
        drop_cols = ["entry_dt", "entry_date", "entry_time_str", "_date_date",
                     "vol_regime", "trend_regime", "rv_regime", "trend_persistence"]
        filtered = filtered.drop(
            columns=[c for c in drop_cols if c in filtered.columns],
            errors="ignore",
        ).reset_index(drop=True)

        return filtered, stats

    # ── Full Simulation ──────────────────────────────────────────────────

    def simulate(
        self,
        baseline_trades: dict,
        regime_daily_cache: dict,
    ) -> dict:
        """Run full controller simulation.

        Parameters
        ----------
        baseline_trades : dict
            {strat_key: trades_df} from always-on backtest.
        regime_daily_cache : dict
            {asset: regime_daily_df} from RegimeEngine.get_daily_regimes().

        Returns
        -------
        dict with:
            - filtered_trades: {strat_key: trades_df} after all controller filters
            - filter_stats: per-strategy filtering statistics
            - portfolio_stats: coordination filtering statistics
        """
        # Step 1: Per-strategy regime + timing filter
        regime_filtered = {}
        filter_stats = {}

        for strat_key in self.strategies:
            trades = baseline_trades.get(strat_key, pd.DataFrame())
            asset = self.strategies[strat_key]["asset"]
            regime_daily = regime_daily_cache.get(asset, pd.DataFrame())

            # Apply GRINDING filter for Donchian before controller
            if self.strategies[strat_key].get("grinding_filter") and not trades.empty:
                rd = regime_daily.copy()
                rd["_date"] = pd.to_datetime(rd["_date"])
                rd["_date_date"] = rd["_date"].dt.date
                t = trades.copy()
                t["entry_date"] = pd.to_datetime(t["entry_time"]).dt.date
                t = t.merge(
                    rd[["_date_date", "trend_persistence"]],
                    left_on="entry_date", right_on="_date_date", how="left",
                )
                trades = t[t["trend_persistence"] == "GRINDING"].drop(
                    columns=["entry_date", "_date_date", "trend_persistence"],
                    errors="ignore",
                ).reset_index(drop=True)

            filtered, stats = self.filter_trades_by_regime_and_timing(
                strat_key, trades, regime_daily
            )
            regime_filtered[strat_key] = filtered
            filter_stats[strat_key] = stats

        # Step 2: Portfolio coordination
        pre_coord_counts = {k: len(v) for k, v in regime_filtered.items()}
        coordinated = self.filter_trades_by_portfolio(regime_filtered)
        post_coord_counts = {k: len(v) for k, v in coordinated.items()}

        portfolio_stats = {
            strat_key: {
                "pre_coordination": pre_coord_counts[strat_key],
                "post_coordination": post_coord_counts[strat_key],
                "coordination_filtered": (
                    pre_coord_counts[strat_key] - post_coord_counts[strat_key]
                ),
            }
            for strat_key in self.strategies
        }

        return {
            "filtered_trades": coordinated,
            "filter_stats": filter_stats,
            "portfolio_stats": portfolio_stats,
        }
