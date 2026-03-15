#!/usr/bin/env python3
"""
FQL Strategy Kill Criteria Framework
=======================================
Automated kill/archive flags for strategies based on 4 professional criteria.

Kill Triggers:
  1. Portfolio Dilution — marginal Sharpe < 0
  2. Edge Redundancy — correlation > 0.35 with same asset/direction/family
  3. Live Edge Decay — forward Sharpe < 0.5 over 50+ trades, or drawdown > 95th pct
  4. Regime Failure — strategy fails in preferred regimes

Registry Fields Added:
  kill_flag: null | "dilution" | "redundancy" | "decay" | "regime_failure"
  kill_details: descriptive string
  last_review_date: ISO date

Usage:
    python3 research/strategy_kill_criteria.py              # Full kill review
    python3 research/strategy_kill_criteria.py --apply       # Apply flags to registry
    python3 research/strategy_kill_criteria.py --json        # JSON output
"""

import argparse
import importlib.util
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest

# ── Constants ─────────────────────────────────────────────────────────────────

DATA_DIR = ROOT / "data" / "processed"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "MGC": {"point_value": 10.0, "tick_size": 0.10,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "M2K": {"point_value": 5.0, "tick_size": 0.10,
            "commission_per_side": 0.62, "slippage_ticks": 1},
    "MCL": {"point_value": 100.0, "tick_size": 0.01,
            "commission_per_side": 0.62, "slippage_ticks": 1},
}

# Strategies to evaluate (core + probation from v0.17 + newly promoted)
# Format: (strategy_id, module_name, asset, mode, family)
EVAL_STRATEGIES = [
    ("VWAP-MNQ-Long", "vwap_trend", "MNQ", "long", "trend"),
    ("XB-PB-EMA-MES-Short", "xb_pb_ema_timestop", "MES", "short", "pullback"),
    ("ORB-MGC-Long", "orb_009", "MGC", "long", "breakout"),
    ("BB-EQ-MGC-Long", "bb_equilibrium", "MGC", "long", "mean_reversion"),
    ("PB-MGC-Short", "pb_trend", "MGC", "short", "pullback"),
    ("Donchian-MNQ-Long", "donchian_trend", "MNQ", "long", "breakout"),
    # Newly promoted probation
    ("NoiseBoundary-MNQ-Long", "noise_boundary", "MNQ", "long", "breakout"),
    ("RangeExpansion-MCL-Short", "range_expansion", "MCL", "short", "vol_expansion"),
    ("GapMom-MGC-Long", "gap_mom", "MGC", "long", "breakout"),
    ("GapMom-MNQ-Long", "gap_mom", "MNQ", "long", "breakout"),
]


# ── Strategy Loading ─────────────────────────────────────────────────────────

def load_strategy_module(name: str):
    """Load a strategy module from strategies/<name>/strategy.py."""
    path = ROOT / "strategies" / name / "strategy.py"
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    """Load processed 5m OHLCV data for an asset."""
    csv_path = DATA_DIR / f"{asset}_5m.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Data file not found: {csv_path}")
    df = pd.read_csv(csv_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


# ── Core Functions ────────────────────────────────────────────────────────────

def get_strategy_trades(strategy_id: str, module_name: str,
                        asset: str, mode: str) -> pd.DataFrame:
    """Load data, generate signals, run backtest, return trades with date column."""
    df = load_data(asset)
    config = ASSET_CONFIG[asset]

    mod = load_strategy_module(module_name)
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    kwargs = {}
    if "asset" in sig.parameters:
        kwargs["asset"] = asset
    signals = mod.generate_signals(df.copy(), **kwargs)

    result = run_backtest(
        df, signals,
        mode=mode,
        point_value=config["point_value"],
        symbol=asset,
    )

    trades = result["trades_df"]
    if trades.empty:
        trades["date"] = pd.Series(dtype="object")
        return trades

    trades = trades.copy()
    trades["date"] = pd.to_datetime(trades["entry_time"]).dt.date
    return trades


def build_daily_pnl_matrix(strategies: list[tuple]) -> pd.DataFrame:
    """Build a DataFrame of daily PnL per strategy.

    Parameters
    ----------
    strategies : list of (strategy_id, module_name, asset, mode, ...) tuples
        Only the first 4 elements are used.

    Returns
    -------
    pd.DataFrame with strategy_ids as columns, dates as index, daily PnL as
    values (0 for no-trade days). Uses union of all trading dates.
    """
    daily_series = {}
    for strat in strategies:
        strategy_id, module_name, asset, mode = strat[0], strat[1], strat[2], strat[3]
        try:
            trades = get_strategy_trades(strategy_id, module_name, asset, mode)
            if trades.empty:
                daily_series[strategy_id] = pd.Series(dtype=float)
                continue
            daily_pnl = trades.groupby("date")["pnl"].sum()
            daily_pnl.index = pd.to_datetime(daily_pnl.index)
            daily_series[strategy_id] = daily_pnl
        except Exception as e:
            print(f"  WARNING: Failed to load {strategy_id}: {e}")
            daily_series[strategy_id] = pd.Series(dtype=float)

    if not daily_series:
        return pd.DataFrame()

    matrix = pd.DataFrame(daily_series)
    matrix = matrix.fillna(0.0)
    matrix = matrix.sort_index()
    return matrix


def _compute_sharpe(daily_pnl: pd.Series) -> float:
    """Annualized Sharpe from a daily PnL series."""
    if daily_pnl.empty or daily_pnl.std() == 0:
        return 0.0
    return float((daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252))


def _max_drawdown(daily_pnl: pd.Series) -> float:
    """Max drawdown from a daily PnL series (as positive value)."""
    cum = daily_pnl.cumsum()
    peak = cum.cummax()
    dd = peak - cum
    return float(dd.max()) if len(dd) > 0 else 0.0


# ── Kill Criteria Checks ─────────────────────────────────────────────────────

def check_portfolio_dilution(daily_matrix: pd.DataFrame) -> list[dict]:
    """Check if removing any strategy improves portfolio Sharpe.

    Flag if marginal Sharpe contribution < 0.
    """
    flags = []
    if daily_matrix.empty:
        return flags

    portfolio_pnl = daily_matrix.sum(axis=1)
    full_sharpe = _compute_sharpe(portfolio_pnl)

    for strategy_id in daily_matrix.columns:
        without = daily_matrix.drop(columns=[strategy_id]).sum(axis=1)
        without_sharpe = _compute_sharpe(without)
        marginal = full_sharpe - without_sharpe

        if marginal < 0:
            flags.append({
                "strategy_id": strategy_id,
                "trigger": "dilution",
                "marginal_sharpe": round(marginal, 4),
                "detail": f"Removing improves portfolio Sharpe by {abs(marginal):.3f}",
            })

    return flags


def check_edge_redundancy(daily_matrix: pd.DataFrame,
                          strategies: list[tuple]) -> list[dict]:
    """Check for redundant strategy pairs (corr > 0.35, same asset/direction/family).

    Flags the weaker strategy (lower standalone Sharpe) in each pair.
    """
    flags = []
    if daily_matrix.empty:
        return flags

    # Build lookup: strategy_id -> (asset, mode, family)
    meta = {}
    for strat in strategies:
        strategy_id, _, asset, mode, family = strat[0], strat[1], strat[2], strat[3], strat[4]
        meta[strategy_id] = (asset, mode, family)

    # Standalone Sharpe per strategy
    sharpes = {sid: _compute_sharpe(daily_matrix[sid]) for sid in daily_matrix.columns}

    flagged_ids = set()
    cols = list(daily_matrix.columns)

    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            sid_a, sid_b = cols[i], cols[j]
            if sid_a not in meta or sid_b not in meta:
                continue

            asset_a, mode_a, family_a = meta[sid_a]
            asset_b, mode_b, family_b = meta[sid_b]

            # Must match on all three dimensions
            if asset_a != asset_b or mode_a != mode_b or family_a != family_b:
                continue

            corr = daily_matrix[sid_a].corr(daily_matrix[sid_b])
            if corr > 0.35:
                # Flag the weaker one
                if sharpes.get(sid_a, 0) >= sharpes.get(sid_b, 0):
                    weaker, stronger = sid_b, sid_a
                else:
                    weaker, stronger = sid_a, sid_b

                if weaker not in flagged_ids:
                    flagged_ids.add(weaker)
                    flags.append({
                        "strategy_id": weaker,
                        "trigger": "redundancy",
                        "correlated_with": stronger,
                        "correlation": round(corr, 4),
                        "detail": (
                            f"Redundant with {stronger} "
                            f"(corr={corr:.3f}, same {asset_a}/{mode_a}/{family_a})"
                        ),
                    })

    return flags


def check_edge_decay(strategies: list[tuple]) -> list[dict]:
    """Check for edge decay by comparing historical vs recent performance.

    Splits trades into first 2/3 (historical) and last 1/3 (recent).
    Flags if recent Sharpe < 0.5 and historical Sharpe > 1.0, or if recent
    max drawdown > 2x historical max drawdown.
    """
    flags = []

    for strat in strategies:
        strategy_id, module_name, asset, mode = strat[0], strat[1], strat[2], strat[3]
        try:
            trades = get_strategy_trades(strategy_id, module_name, asset, mode)
        except Exception as e:
            print(f"  WARNING: Could not load {strategy_id} for decay check: {e}")
            continue

        if trades.empty or len(trades) < 10:
            continue

        # Split into historical (first 2/3) and recent (last 1/3)
        split_idx = int(len(trades) * 2 / 3)
        hist_trades = trades.iloc[:split_idx]
        recent_trades = trades.iloc[split_idx:]

        hist_daily = hist_trades.groupby("date")["pnl"].sum()
        recent_daily = recent_trades.groupby("date")["pnl"].sum()

        hist_sharpe = _compute_sharpe(hist_daily)
        recent_sharpe = _compute_sharpe(recent_daily)

        hist_dd = _max_drawdown(hist_daily)
        recent_dd = _max_drawdown(recent_daily)

        # Check Sharpe decay
        if recent_sharpe < 0.5 and hist_sharpe > 1.0:
            flags.append({
                "strategy_id": strategy_id,
                "trigger": "decay",
                "historical_sharpe": round(hist_sharpe, 4),
                "recent_sharpe": round(recent_sharpe, 4),
                "detail": f"Edge decaying: Sharpe {hist_sharpe:.2f} -> {recent_sharpe:.2f}",
            })
        # Check drawdown blow-up
        elif hist_dd > 0 and recent_dd > 2 * hist_dd:
            flags.append({
                "strategy_id": strategy_id,
                "trigger": "decay",
                "historical_sharpe": round(hist_sharpe, 4),
                "recent_sharpe": round(recent_sharpe, 4),
                "detail": (
                    f"Drawdown blow-up: historical DD=${hist_dd:.0f}, "
                    f"recent DD=${recent_dd:.0f} (>{2 * hist_dd:.0f} threshold)"
                ),
            })

    return flags


def check_regime_failure(strategies: list[tuple]) -> list[dict]:
    """Check if strategies have negative PnL in their preferred regimes.

    Requires the genome map STRATEGIES and regime engine. If imports fail,
    skips gracefully.
    """
    flags = []

    # Try to import genome map and regime engine
    try:
        from research.strategy_genome_map import STRATEGIES as GENOME_STRATEGIES
        from engine.regime_engine import RegimeEngine
    except ImportError as e:
        print(f"  NOTE: Regime check skipped — engine not available ({e})")
        return flags

    # Build lookup: strategy_id -> preferred regimes
    regime_prefs = {}
    for gs in GENOME_STRATEGIES:
        preferred = gs.get("regime_preferred", [])
        if preferred:
            regime_prefs[gs["id"]] = preferred

    for strat in strategies:
        strategy_id, module_name, asset, mode = strat[0], strat[1], strat[2], strat[3]

        preferred = regime_prefs.get(strategy_id, [])
        if not preferred:
            continue

        try:
            df = load_data(asset)
        except Exception:
            continue

        # Compute regimes
        try:
            re = RegimeEngine()
            regime_df = re.classify(df)
            regime_col = "regime" if "regime" in regime_df.columns else None
            if regime_col is None:
                continue
        except Exception as e:
            print(f"  WARNING: Regime engine failed for {asset}: {e}")
            continue

        # Get trades
        try:
            trades = get_strategy_trades(strategy_id, module_name, asset, mode)
        except Exception:
            continue

        if trades.empty:
            continue

        # Map each trade to its regime
        trades = trades.copy()
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        regime_df["datetime"] = pd.to_datetime(regime_df["datetime"])
        regime_df = regime_df.set_index("datetime")

        trade_regimes = []
        for _, row in trades.iterrows():
            entry_dt = row["entry_dt"]
            # Find closest regime bar at or before entry
            mask = regime_df.index <= entry_dt
            if mask.any():
                regime_val = regime_df.loc[mask].iloc[-1][regime_col]
                trade_regimes.append(regime_val)
            else:
                trade_regimes.append("UNKNOWN")

        trades["regime"] = trade_regimes

        # Check PnL in preferred regimes
        failed_regimes = []
        for regime in preferred:
            regime_trades = trades[trades["regime"] == regime]
            if regime_trades.empty:
                continue
            if regime_trades["pnl"].sum() < 0:
                failed_regimes.append(regime)

        if len(failed_regimes) > len(preferred) / 2:
            flags.append({
                "strategy_id": strategy_id,
                "trigger": "regime_failure",
                "detail": (
                    f"Negative PnL in {len(failed_regimes)}/{len(preferred)} "
                    f"preferred regimes: {failed_regimes}"
                ),
            })

    return flags


# ── Review Orchestration ─────────────────────────────────────────────────────

def run_kill_review() -> dict:
    """Run all 4 kill criteria checks and return structured results."""
    print("Loading strategies and building daily PnL matrix...")
    daily_matrix = build_daily_pnl_matrix(EVAL_STRATEGIES)

    all_flags = []

    print("Check 1/4: Portfolio dilution...")
    all_flags.extend(check_portfolio_dilution(daily_matrix))

    print("Check 2/4: Edge redundancy...")
    all_flags.extend(check_edge_redundancy(daily_matrix, EVAL_STRATEGIES))

    print("Check 3/4: Edge decay...")
    all_flags.extend(check_edge_decay(EVAL_STRATEGIES))

    print("Check 4/4: Regime failure...")
    all_flags.extend(check_regime_failure(EVAL_STRATEGIES))

    # Build summary
    all_ids = [s[0] for s in EVAL_STRATEGIES]
    flagged_ids = {f["strategy_id"] for f in all_flags}
    clean_ids = [sid for sid in all_ids if sid not in flagged_ids]

    summary = {
        "dilution": [f["strategy_id"] for f in all_flags if f["trigger"] == "dilution"],
        "redundancy": [f["strategy_id"] for f in all_flags if f["trigger"] == "redundancy"],
        "decay": [f["strategy_id"] for f in all_flags if f["trigger"] == "decay"],
        "regime_failure": [f["strategy_id"] for f in all_flags if f["trigger"] == "regime_failure"],
        "clean": clean_ids,
    }

    return {
        "review_date": datetime.now().strftime("%Y-%m-%d"),
        "strategies_reviewed": len(EVAL_STRATEGIES),
        "flags": all_flags,
        "summary": summary,
    }


# ── Registry Integration ─────────────────────────────────────────────────────

def apply_to_registry(flags: list[dict]):
    """Apply kill flags to the strategy registry JSON.

    For flagged strategies: sets kill_flag, kill_details, last_review_date.
    For clean strategies: sets kill_flag to null, updates last_review_date.
    """
    if not REGISTRY_PATH.exists():
        print(f"  WARNING: Registry not found at {REGISTRY_PATH}")
        return

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d")

    # Build flag lookup: strategy_id -> first flag
    flag_lookup = {}
    for flag in flags:
        sid = flag["strategy_id"]
        if sid not in flag_lookup:
            flag_lookup[sid] = flag

    for entry in registry.get("strategies", []):
        sid = entry.get("strategy_id", "")
        if sid in flag_lookup:
            flag = flag_lookup[sid]
            entry["kill_flag"] = flag["trigger"]
            entry["kill_details"] = flag["detail"]
            entry["last_review_date"] = today
        else:
            entry["kill_flag"] = None
            entry["last_review_date"] = today

    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)

    print(f"  Registry updated: {len(flag_lookup)} flags applied, {REGISTRY_PATH}")


# ── Report Output ─────────────────────────────────────────────────────────────

def print_report(results: dict):
    """Print a formatted terminal report of kill review results."""
    summary = results["summary"]
    flags = results["flags"]

    print()
    print("STRATEGY KILL REVIEW")
    print("=" * 60)
    print(f"Review Date: {results['review_date']}")
    print(f"Strategies Reviewed: {results['strategies_reviewed']}")
    print()

    if not flags:
        print("No kill flags triggered. All strategies passed.")
        print()
        return

    print("KILL FLAGS")
    print("-" * 60)

    # Group flags by trigger for ordered output
    trigger_order = [
        ("dilution", "[RED] DILUTION"),
        ("decay", "[RED] EDGE DECAY"),
        ("regime_failure", "[YELLOW] REGIME FAILURE"),
        ("redundancy", "[YELLOW] REDUNDANCY"),
    ]

    for trigger_key, label in trigger_order:
        trigger_flags = [f for f in flags if f["trigger"] == trigger_key]
        for flag in trigger_flags:
            print(f"  {label}: {flag['strategy_id']}")
            if trigger_key == "dilution":
                print(f"    Marginal Sharpe: {flag['marginal_sharpe']:.4f}")
            elif trigger_key == "redundancy":
                print(f"    Correlated with: {flag['correlated_with']}")
                print(f"    Correlation: {flag['correlation']:.4f}")
            elif trigger_key == "decay":
                if "historical_sharpe" in flag:
                    print(f"    Historical Sharpe: {flag['historical_sharpe']:.2f}")
                    print(f"    Recent Sharpe: {flag['recent_sharpe']:.2f}")
            print(f"    {flag['detail']}")
            print()

    clean = summary.get("clean", [])
    if clean:
        print(f"[GREEN] CLEAN: {len(clean)} strategies passed all checks")
        print(f"  {', '.join(clean)}")
        print()

    # Recommendations
    print("RECOMMENDATIONS")
    print("-" * 60)

    # Strategies flagged for multiple triggers
    flag_counts = {}
    for flag in flags:
        sid = flag["strategy_id"]
        flag_counts.setdefault(sid, []).append(flag["trigger"])

    for sid, triggers in flag_counts.items():
        if len(triggers) > 1:
            print(f"  - {sid}: MULTI-FLAG ({', '.join(triggers)}) — strong archive candidate")
        elif "dilution" in triggers:
            # Check if also redundant with something
            redundancy_flags = [f for f in flags if f["strategy_id"] == sid and f["trigger"] == "redundancy"]
            if redundancy_flags:
                corr_with = redundancy_flags[0]["correlated_with"]
                print(f"  - {sid}: Consider archiving — dilutive and redundant with {corr_with}")
            else:
                print(f"  - {sid}: Consider archiving — dilutive to portfolio Sharpe")
        elif "decay" in triggers:
            print(f"  - {sid}: Monitor closely — edge decaying, consider reducing allocation")
        elif "regime_failure" in triggers:
            print(f"  - {sid}: Review regime gates — underperforming in preferred regimes")
        elif "redundancy" in triggers:
            redundancy_flag = [f for f in flags if f["strategy_id"] == sid and f["trigger"] == "redundancy"][0]
            print(f"  - {sid}: Evaluate vs {redundancy_flag['correlated_with']} — keep the stronger edge")

    if not flag_counts:
        print("  No recommendations — all strategies healthy.")

    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FQL Strategy Kill Criteria — automated kill/archive flags"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply kill flags to the strategy registry JSON"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON instead of formatted report"
    )
    args = parser.parse_args()

    results = run_kill_review()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_report(results)

    if args.apply:
        apply_to_registry(results["flags"])
        print("Kill flags applied to registry.")


if __name__ == "__main__":
    main()
