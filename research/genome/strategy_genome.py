"""Strategy Genome — Automated behavioral fingerprint for every strategy.

Computes a behavioral profile ("genome") from backtest results.
Unlike DNA (structural, hand-curated), genomes are auto-computed from trades.

DNA = what the strategy IS (architecture)
Genome = what the strategy DOES (behavior)

Usage:
    python3 research/genome/strategy_genome.py                    # All strategies
    python3 research/genome/strategy_genome.py --strategy pb_trend  # Single strategy
"""

import argparse
import importlib.util
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
GENOME_DIR = Path(__file__).resolve().parent
STRATEGIES_DIR = PROJECT_ROOT / "strategies"

# Strategies to profile and their best known combos
STRATEGY_PROFILES = {
    "pb_trend":       {"asset": "MGC", "mode": "short", "status": "parent"},
    "orb_009":        {"asset": "MGC", "mode": "long",  "status": "parent"},
    "vwap_trend":     {"asset": "MNQ", "mode": "long",  "status": "parent"},
    "vix_channel":    {"asset": "MES", "mode": "both",  "status": "candidate"},
    "donchian_trend": {"asset": "MNQ", "mode": "long",  "status": "probation"},
    "bb_equilibrium": {"asset": "MGC", "mode": "long",  "status": "probation"},
    "vwap_mr_gold":   {"asset": "MGC", "mode": "long",  "status": "candidate"},
    "session_reversion_gold": {"asset": "MGC", "mode": "long", "status": "candidate"},
    "bb_compression_gold":    {"asset": "MGC", "mode": "long", "status": "rejected"},
    "ema_trend_rider": {"asset": "MNQ", "mode": "long", "status": "rejected"},
}


def load_strategy(name: str):
    module_path = STRATEGIES_DIR / name / "strategy.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compute_genome(strategy_name: str, profile: dict) -> dict:
    """Compute full behavioral genome for a strategy."""
    asset = profile["asset"]
    mode = profile["mode"]

    data_path = PROCESSED_DIR / f"{asset}_5m.csv"
    if not data_path.exists():
        return None

    strategy = load_strategy(strategy_name)
    if strategy is None:
        return None

    config = ASSET_CONFIG[asset]
    strategy.TICK_SIZE = config["tick_size"]

    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Check if strategy accepts asset kwarg
    sig = inspect.signature(strategy.generate_signals)
    if "asset" in sig.parameters:
        signals_df = strategy.generate_signals(df, asset=asset)
    else:
        signals_df = strategy.generate_signals(df)

    result = run_backtest(
        df, signals_df, mode=mode,
        point_value=config["point_value"], symbol=asset,
    )

    trades_df = result["trades_df"]
    if trades_df.empty or len(trades_df) < 10:
        return None

    equity_curve = result["equity_curve"]
    metrics = compute_extended_metrics(trades_df, equity_curve, config["point_value"])

    # ── 1. Hold Characteristics ────────────────────────────────────────
    durations = trades_df["duration_bars"].values if "duration_bars" in trades_df.columns else np.array([])
    if len(durations) == 0:
        # Compute from entry/exit times
        entry_times = pd.to_datetime(trades_df["entry_time"])
        exit_times = pd.to_datetime(trades_df["exit_time"])
        durations = ((exit_times - entry_times).dt.total_seconds() / 300).values  # 5min bars

    hold = {
        "median_hold_bars": float(np.median(durations)) if len(durations) > 0 else 0,
        "avg_hold_bars": float(np.mean(durations)) if len(durations) > 0 else 0,
        "hold_std_bars": float(np.std(durations)) if len(durations) > 0 else 0,
        "hold_skew": float(pd.Series(durations).skew()) if len(durations) > 3 else 0,
        "hold_class": _classify_hold(float(np.median(durations)) if len(durations) > 0 else 0),
    }

    # ── 2. Trade Structure ─────────────────────────────────────────────
    pnl_arr = trades_df["pnl"].values
    wins = pnl_arr[pnl_arr > 0]
    losses = pnl_arr[pnl_arr <= 0]
    total_pnl = pnl_arr.sum()

    # Profit skew: ratio of top-10% PnL to total
    sorted_pnl = np.sort(pnl_arr)[::-1]
    top_10_pct = max(1, len(sorted_pnl) // 10)
    top_pnl = sorted_pnl[:top_10_pct].sum()
    profit_skew = top_pnl / total_pnl if total_pnl > 0 else 0

    # Tail dependency: max single trade as % of total PnL
    max_trade_pnl = pnl_arr.max() if len(pnl_arr) > 0 else 0
    max_trade_pct = max_trade_pnl / total_pnl if total_pnl > 0 else 0

    # PF after removing best trade
    pnl_no_best = np.delete(pnl_arr, np.argmax(pnl_arr)) if len(pnl_arr) > 1 else pnl_arr
    wins_nb = pnl_no_best[pnl_no_best > 0].sum()
    losses_nb = abs(pnl_no_best[pnl_no_best <= 0].sum())
    pf_no_best = wins_nb / losses_nb if losses_nb > 0 else float("inf")

    # Trading days
    entry_dates = pd.to_datetime(trades_df["entry_time"]).dt.date
    n_trading_days = entry_dates.nunique()
    trades_per_day = len(trades_df) / n_trading_days if n_trading_days > 0 else 0

    trade_structure = {
        "trade_count": int(len(trades_df)),
        "trades_per_day": round(trades_per_day, 2),
        "win_rate": round((pnl_arr > 0).mean(), 3),
        "profit_factor": round(metrics["profit_factor"], 2),
        "avg_win": round(float(wins.mean()), 2) if len(wins) > 0 else 0,
        "avg_loss": round(float(losses.mean()), 2) if len(losses) > 0 else 0,
        "payoff_ratio": round(abs(float(wins.mean()) / float(losses.mean())), 2) if len(losses) > 0 and losses.mean() != 0 else 0,
        "profit_skew": round(profit_skew, 3),
        "max_trade_pct_of_pnl": round(max_trade_pct, 3),
        "pf_after_best_removed": round(pf_no_best, 2) if np.isfinite(pf_no_best) else 999,
        "tail_dependent": max_trade_pct > 0.25,
        "sharpe": round(metrics["sharpe"], 2),
        "total_pnl": round(total_pnl, 2),
        "max_drawdown": round(metrics["max_drawdown"], 2),
    }

    # ── 3. Market Sensitivity ──────────────────────────────────────────
    engine = RegimeEngine()
    regime_daily = engine.get_daily_regimes(df)
    rd = regime_daily.copy()
    rd["_date_date"] = pd.to_datetime(rd["_date"]).dt.date

    trades_merged = trades_df.copy()
    trades_merged["entry_date"] = pd.to_datetime(trades_merged["entry_time"]).dt.date
    trades_merged = trades_merged.merge(
        rd[["_date_date", "vol_regime", "trend_regime", "rv_regime",
            "trend_persistence", "composite_regime"]],
        left_on="entry_date", right_on="_date_date", how="left",
    )

    # Volatility sensitivity
    vol_pnl = trades_merged.groupby("vol_regime")["pnl"].agg(["sum", "count"])
    high_vol_pnl = vol_pnl.loc["HIGH_VOL", "sum"] if "HIGH_VOL" in vol_pnl.index else 0
    low_vol_pnl = vol_pnl.loc["LOW_VOL", "sum"] if "LOW_VOL" in vol_pnl.index else 0
    vol_sensitivity = _sensitivity_score(high_vol_pnl, low_vol_pnl, total_pnl)

    # Trend sensitivity
    trend_pnl = trades_merged.groupby("trend_regime")["pnl"].agg(["sum", "count"])
    trending_pnl = trend_pnl.loc["TRENDING", "sum"] if "TRENDING" in trend_pnl.index else 0
    ranging_pnl = trend_pnl.loc["RANGING", "sum"] if "RANGING" in trend_pnl.index else 0
    trend_sensitivity = _sensitivity_score(trending_pnl, ranging_pnl, total_pnl)

    # RV sensitivity
    rv_pnl = trades_merged.groupby("rv_regime")["pnl"].agg(["sum", "count"])
    high_rv_pnl = rv_pnl.loc["HIGH_RV", "sum"] if "HIGH_RV" in rv_pnl.index else 0
    low_rv_pnl = rv_pnl.loc["LOW_RV", "sum"] if "LOW_RV" in rv_pnl.index else 0
    rv_sensitivity = _sensitivity_score(high_rv_pnl, low_rv_pnl, total_pnl)

    # Persistence sensitivity
    persist_pnl = trades_merged.groupby("trend_persistence")["pnl"].agg(["sum", "count"])
    grinding_pnl = persist_pnl.loc["GRINDING", "sum"] if "GRINDING" in persist_pnl.index else 0
    choppy_pnl = persist_pnl.loc["CHOPPY", "sum"] if "CHOPPY" in persist_pnl.index else 0

    market_sensitivity = {
        "volatility_sensitivity": vol_sensitivity,
        "vol_label": _label_sensitivity(vol_sensitivity, "high_vol", "low_vol"),
        "trend_sensitivity": trend_sensitivity,
        "trend_label": _label_sensitivity(trend_sensitivity, "trending", "ranging"),
        "rv_sensitivity": rv_sensitivity,
        "rv_label": _label_sensitivity(rv_sensitivity, "high_rv", "low_rv"),
        "grinding_pnl": round(grinding_pnl, 2),
        "choppy_pnl": round(choppy_pnl, 2),
        "grinding_dependent": grinding_pnl > 0.5 * total_pnl if total_pnl > 0 else False,
    }

    # ── 4. Regime Performance ──────────────────────────────────────────
    trades_merged["regime_cell"] = (
        trades_merged["composite_regime"].fillna("UNKNOWN") + "_" +
        trades_merged["rv_regime"].fillna("UNKNOWN")
    )

    regime_groups = trades_merged.groupby("regime_cell")["pnl"].agg(["sum", "count", "mean"])
    regime_groups = regime_groups.sort_values("sum", ascending=False)

    pnl_by_cell = {}
    for cell, row in regime_groups.iterrows():
        pnl_by_cell[cell] = {
            "pnl": round(row["sum"], 2),
            "trades": int(row["count"]),
            "avg_pnl": round(row["mean"], 2),
        }

    best_regime = regime_groups.index[0] if len(regime_groups) > 0 else "NONE"
    worst_regime = regime_groups.index[-1] if len(regime_groups) > 0 else "NONE"

    # Regime dependence: Herfindahl index on absolute PnL shares
    if total_pnl != 0 and len(regime_groups) > 0:
        abs_shares = (regime_groups["sum"].abs() / regime_groups["sum"].abs().sum()) ** 2
        herfindahl = abs_shares.sum()
    else:
        herfindahl = 1.0

    regime_perf = {
        "pnl_by_regime_cell": pnl_by_cell,
        "best_regime": best_regime,
        "worst_regime": worst_regime,
        "regime_dependence_score": round(herfindahl, 3),
        "regime_concentrated": herfindahl > 0.3,
    }

    # ── 5. Session Analysis ────────────────────────────────────────────
    trades_merged["entry_hour"] = pd.to_datetime(trades_merged["entry_time"]).dt.hour
    hour_groups = trades_merged.groupby("entry_hour")["pnl"].agg(["sum", "count"])
    session_profile = {}
    for hour, row in hour_groups.iterrows():
        session_profile[int(hour)] = {
            "pnl": round(row["sum"], 2),
            "trades": int(row["count"]),
        }

    best_hour = hour_groups["sum"].idxmax() if len(hour_groups) > 0 else None
    worst_hour = hour_groups["sum"].idxmin() if len(hour_groups) > 0 else None

    # ── 6. Year Stability ──────────────────────────────────────────────
    trades_merged["year"] = pd.to_datetime(trades_merged["entry_time"]).dt.year
    year_stability = {}
    for year in trades_merged["year"].unique():
        yt = trades_merged[trades_merged["year"] == year]
        if len(yt) >= 5:
            gp = yt.loc[yt["pnl"] > 0, "pnl"].sum()
            gl = abs(yt.loc[yt["pnl"] <= 0, "pnl"].sum())
            pf = gp / gl if gl > 0 else float("inf")
            year_stability[int(year)] = {
                "trades": len(yt),
                "pf": round(pf, 2) if np.isfinite(pf) else 999,
                "pnl": round(yt["pnl"].sum(), 2),
                "wr": round((yt["pnl"] > 0).mean(), 3),
            }

    # ── Assemble Genome ────────────────────────────────────────────────
    genome = {
        "strategy": strategy_name,
        "asset": asset,
        "mode": mode,
        "status": profile["status"],
        "engine_type": _classify_engine(hold, trade_structure, market_sensitivity),
        "hold_characteristics": hold,
        "trade_structure": trade_structure,
        "market_sensitivity": market_sensitivity,
        "regime_performance": regime_perf,
        "session_profile": session_profile,
        "best_hour": int(best_hour) if best_hour is not None else None,
        "worst_hour": int(worst_hour) if worst_hour is not None else None,
        "year_stability": year_stability,
    }

    return genome


# ── Classification Helpers ──────────────────────────────────────────────────

def _classify_hold(median_bars: float) -> str:
    if median_bars <= 5:
        return "scalper"
    elif median_bars <= 20:
        return "intraday_swing"
    elif median_bars <= 60:
        return "day_trade"
    else:
        return "position"


def _sensitivity_score(high_pnl: float, low_pnl: float, total_pnl: float) -> float:
    """Returns -1 to +1: positive = prefers 'high' factor, negative = prefers 'low'."""
    if total_pnl == 0 or (high_pnl == 0 and low_pnl == 0):
        return 0.0
    diff = high_pnl - low_pnl
    denom = abs(high_pnl) + abs(low_pnl)
    if denom == 0:
        return 0.0
    return round(diff / denom, 3)


def _label_sensitivity(score: float, high_label: str, low_label: str) -> str:
    if score > 0.3:
        return f"strong_{high_label}"
    elif score > 0.1:
        return f"moderate_{high_label}"
    elif score < -0.3:
        return f"strong_{low_label}"
    elif score < -0.1:
        return f"moderate_{low_label}"
    return "neutral"


def _classify_engine(hold: dict, structure: dict, sensitivity: dict) -> str:
    """Classify strategy into an engine type based on behavioral metrics."""
    median = hold["median_hold_bars"]
    wr = structure["win_rate"]
    trend = sensitivity["trend_sensitivity"]

    if median <= 5 and wr > 0.4:
        return "pullback_scalper"
    elif median <= 10 and trend > 0.2:
        return "momentum_scalper"
    elif median > 40 and trend > 0.2:
        return "trend_follower"
    elif median > 20 and trend > 0.1:
        return "trend_continuation"
    elif wr > 0.50 and trend < -0.1:
        return "mean_reversion"
    elif median <= 15 and structure.get("payoff_ratio", 0) > 1.5:
        return "breakout"
    elif trend < -0.2:
        return "counter_trend"
    else:
        return "hybrid"


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Strategy Genome Builder")
    parser.add_argument("--strategy", help="Single strategy to profile")
    args = parser.parse_args()

    if args.strategy:
        strategies = {args.strategy: STRATEGY_PROFILES.get(args.strategy, {"asset": "MES", "mode": "both", "status": "unknown"})}
    else:
        strategies = STRATEGY_PROFILES

    all_genomes = {}

    print(f"\n{'='*70}")
    print(f"  STRATEGY GENOME BUILDER")
    print(f"{'='*70}")

    for name, profile in strategies.items():
        print(f"\n  Computing genome: {name} ({profile['asset']}-{profile['mode']})...")
        genome = compute_genome(name, profile)
        if genome:
            all_genomes[name] = genome
            m = genome["trade_structure"]
            h = genome["hold_characteristics"]
            print(f"    Engine: {genome['engine_type']}")
            print(f"    Trades: {m['trade_count']}, PF: {m['profit_factor']}, "
                  f"Sharpe: {m['sharpe']}")
            print(f"    Hold: {h['median_hold_bars']:.0f}b ({h['hold_class']})")
            print(f"    Trend: {genome['market_sensitivity']['trend_label']}, "
                  f"Vol: {genome['market_sensitivity']['vol_label']}")
        else:
            print(f"    SKIP: No data or insufficient trades")

    # Save genomes
    output_path = GENOME_DIR / "strategy_genomes.json"
    with open(output_path, "w") as f:
        json.dump(all_genomes, f, indent=2, default=str)
    print(f"\n  Saved {len(all_genomes)} genomes to {output_path}")

    # ── Summary Table ──────────────────────────────────────────────────
    if all_genomes:
        print(f"\n{'='*70}")
        print(f"  GENOME SUMMARY")
        print(f"{'='*70}")
        print(f"  {'Strategy':<22} {'Engine':<20} {'Hold':>6} {'PF':>6} "
              f"{'Trades':>6} {'Trend':>10} {'Vol':>10}")
        print(f"  {'-'*22} {'-'*20} {'-'*6} {'-'*6} "
              f"{'-'*6} {'-'*10} {'-'*10}")

        for name, g in sorted(all_genomes.items(), key=lambda x: x[1]["trade_structure"]["profit_factor"], reverse=True):
            m = g["trade_structure"]
            h = g["hold_characteristics"]
            ms = g["market_sensitivity"]
            engine = g["engine_type"]
            print(f"  {name:<22} {engine:<20} "
                  f"{h['median_hold_bars']:>5.0f}b "
                  f"{m['profit_factor']:>6.2f} "
                  f"{m['trade_count']:>6} "
                  f"{ms['trend_sensitivity']:>+10.3f} "
                  f"{ms['volatility_sensitivity']:>+10.3f}")

    return all_genomes


if __name__ == "__main__":
    main()
