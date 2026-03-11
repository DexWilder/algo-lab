"""Phase 14: Gold MR Refinement — Build the 6th Parent.

Refines 4 gold MR candidates (Session VWAP Fade, BB Range MR, VWAP Dev MR,
BB Equilibrium) into one production-quality Gold MR parent for the 6-strategy
portfolio.

8-step pipeline:
1. Parameter refinement grid (~99 combos)
2. Best variant selection with Prop Speed Score
3. Cross-correlation (4×4 matrix)
4. Regime + duration fingerprint
5. Validation battery (top 1-2 candidates)
6. Portfolio impact (6-strategy)
7. Fast pass potential test
8. Final ranking & promotion decision

Usage:
    python3 research/phase14_gold_mr_refinement.py
"""

import importlib.util
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.metrics import compute_extended_metrics
from engine.regime_engine import RegimeEngine
from engine.statistics import bootstrap_metrics, deflated_sharpe_ratio

PROCESSED_DIR = ROOT / "data" / "processed"
DATABENTO_DIR = ROOT / "data" / "databento"
OUTPUT_DIR = Path(__file__).resolve().parent

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
}

STARTING_CAPITAL = 50_000.0
SEED = 42
N_SIMULATIONS = 10_000
N_TRIALS = 81
LOW_SAMPLE_THRESHOLD = 15

# ── Candidate strategies ─────────────────────────────────────────────────

GOLD_MR_CANDIDATES = [
    {
        "name": "session_vwap_fade",
        "label": "Sess-VWAP-Fade",
        "param_grid": {
            "FADE_MULT": [1.5, 2.0, 2.5],
            "ENTRY_CUTOFF": ["11:30", "12:30", "13:30"],
            "SESSION_EXTREME_CUSHION": [0.3, 0.5, 0.8],
        },
    },
    {
        "name": "bb_range_mr",
        "label": "BB-Range-MR",
        "param_grid": {
            "EMA_CONVERGENCE": [0.8, 1.5, 2.5],
            "BW_MAX_PCT": [40, 60, 80],
            "RSI_OVERSOLD": [30, 35, 40],
        },
        # Mirror RSI_OVERBOUGHT = 100 - RSI_OVERSOLD
        "rsi_mirror": True,
    },
    {
        "name": "vwap_dev_mr",
        "label": "VWAP-Dev-MR",
        "param_grid": {
            "DEVIATION_MULT": [1.5, 2.0, 2.5],
            "ENTRY_CUTOFF": ["12:30", "14:30"],
            "ADX_THRESHOLD": [20, 25, 30],
        },
    },
    {
        "name": "bb_equilibrium",
        "label": "BB-Equilibrium",
        "param_grid": {
            "TREND_EMA_PERIOD": [10, 20, 50],
            "BW_MAX_PCT": [30, 50, 70],
            "BB_MULT": [1.5, 2.0, 2.5],
        },
    },
]

# ── Existing portfolio parents (for correlation + portfolio sim) ─────────

PORTFOLIO_PARENTS = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short", "label": "PB",
     "grinding_filter": False, "exit_variant": None},
    {"name": "orb_009", "asset": "MGC", "mode": "long", "label": "ORB",
     "grinding_filter": False, "exit_variant": None},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long", "label": "VWAP",
     "grinding_filter": False, "exit_variant": None},
    {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short", "label": "XB-PB",
     "grinding_filter": False, "exit_variant": None},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long", "label": "DONCH",
     "grinding_filter": True, "exit_variant": "profit_ladder"},
]

VOL_WEIGHTS = {"PB": 1.214, "ORB": 1.093, "VWAP": 0.758, "XB-PB": 1.228, "DONCH": 0.707}

# Validation parameter grids (for Step 5)
VALIDATION_PARAM_GRIDS = {
    "session_vwap_fade": {
        "FADE_MULT": [1.5, 2.0, 2.5],
        "ENTRY_CUTOFF": ["11:30", "12:30", "13:30"],
        "SESSION_EXTREME_CUSHION": [0.3, 0.5, 0.8],
    },
    "bb_range_mr": {
        "EMA_CONVERGENCE": [0.8, 1.5, 2.5],
        "BW_MAX_PCT": [40, 60, 80],
        "RSI_OVERSOLD": [30, 35, 40],
    },
    "vwap_dev_mr": {
        "DEVIATION_MULT": [1.5, 2.0, 2.5],
        "ENTRY_CUTOFF": ["12:30", "14:30"],
        "ADX_THRESHOLD": [20, 25, 30],
    },
    "bb_equilibrium": {
        "TREND_EMA_PERIOD": [10, 20, 50],
        "BW_MAX_PCT": [30, 50, 70],
        "BB_MULT": [1.5, 2.0, 2.5],
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset, timeframe="5m"):
    path = PROCESSED_DIR / f"{asset}_{timeframe}.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_1m_data(asset):
    path = DATABENTO_DIR / f"{asset}_1m.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def resample_bars(df_1m, freq_minutes):
    df = df_1m.copy()
    df = df.set_index("datetime")
    resampled = df.resample(f"{freq_minutes}min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna(subset=["open"])
    return resampled.reset_index()


def get_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def quick_metrics(trades_df):
    """Lightweight metrics for parameter grid scanning."""
    if trades_df.empty:
        return {"pf": 0, "sharpe": 0, "trades": 0, "pnl": 0, "maxdd": 0,
                "wr": 0, "median_hold": 0}

    pnl = trades_df["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gp = wins.sum() if len(wins) else 0
    gl = abs(losses.sum()) if len(losses) else 0
    pf = gp / gl if gl > 0 else (100.0 if gp > 0 else 0)

    tc = trades_df.copy()
    tc["_date"] = pd.to_datetime(tc["exit_time"]).dt.date
    daily = tc.groupby("_date")["pnl"].sum()
    sharpe = (daily.mean() / daily.std() * np.sqrt(252)
              if len(daily) > 1 and daily.std() > 0 else 0)

    equity = STARTING_CAPITAL + np.cumsum(pnl.values)
    peak = np.maximum.accumulate(equity)
    maxdd = (peak - equity).max()

    # Duration
    try:
        dur = ((pd.to_datetime(trades_df["exit_time"]) -
                pd.to_datetime(trades_df["entry_time"])).dt.total_seconds() / 300)
        median_hold = int(dur.median())
    except Exception:
        median_hold = 0

    return {
        "pf": round(pf, 4),
        "sharpe": round(sharpe, 4),
        "trades": len(trades_df),
        "pnl": round(pnl.sum(), 2),
        "maxdd": round(maxdd, 2),
        "wr": round(len(wins) / len(pnl) * 100, 1) if len(pnl) > 0 else 0,
        "median_hold": median_hold,
    }


def run_combo(name, asset, mode, param_overrides=None, rsi_mirror=False):
    """Run a single strategy-asset-mode combo with optional param overrides."""
    config = ASSET_CONFIG[asset]
    df = load_data(asset)

    mod = load_strategy(name)
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]

    if param_overrides:
        for k, v in param_overrides.items():
            setattr(mod, k, v)
        # Mirror RSI_OVERBOUGHT if needed
        if rsi_mirror and "RSI_OVERSOLD" in param_overrides:
            setattr(mod, "RSI_OVERBOUGHT", 100 - param_overrides["RSI_OVERSOLD"])

    signals = mod.generate_signals(df)
    result = run_backtest(df, signals, mode=mode,
                          point_value=config["point_value"], symbol=asset)
    trades = result["trades_df"]
    equity = result.get("equity_curve", pd.Series(dtype=float))
    return trades, equity, df


def compute_regime_breakdown(trades_df, df_raw, engine):
    """Tag each trade with regime cell and compute regime stats."""
    if trades_df.empty:
        return {}, 0, 0.0, 0.0, 0.0

    regime_daily = engine.get_daily_regimes(df_raw)
    regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
    regime_daily["_date_date"] = regime_daily["_date"].dt.date

    trades = trades_df.copy()
    trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
    trades = trades.merge(
        regime_daily[["_date_date", "composite_regime", "rv_regime", "trend_regime"]],
        left_on="entry_date", right_on="_date_date", how="left",
    )
    trades["full_regime"] = (trades["composite_regime"].fillna("UNK") + "_" +
                             trades["rv_regime"].fillna("UNK"))

    breakdown = {}
    for regime, grp in trades.groupby("full_regime"):
        breakdown[regime] = {
            "trades": len(grp),
            "pnl": round(grp["pnl"].sum(), 2),
            "win_rate": round((grp["pnl"] > 0).mean() * 100, 1),
        }

    # RANGING stats
    ranging_mask = trades["trend_regime"] == "RANGING"
    ranging_trades = ranging_mask.sum()
    ranging_pnl = trades.loc[ranging_mask, "pnl"].sum() if ranging_trades > 0 else 0.0
    total_pnl = trades["pnl"].sum()

    # RANGING_EDGE_SCORE
    if total_pnl > 0 and ranging_trades > 0:
        pnl_ratio = ranging_pnl / total_pnl
        trade_adj = min(1.0, ranging_trades / 20.0)
        ranging_edge_score = pnl_ratio * trade_adj
    else:
        ranging_edge_score = 0.0

    # TRENDING bleed
    trending_mask = trades["trend_regime"] == "TRENDING"
    trending_pnl = trades.loc[trending_mask, "pnl"].sum() if trending_mask.sum() > 0 else 0.0
    trending_bleed_ratio = trending_pnl / total_pnl if total_pnl != 0 else 0.0

    return (breakdown, int(ranging_trades), round(ranging_pnl, 2),
            round(ranging_edge_score, 3), round(trending_bleed_ratio, 3))


def load_parent_daily_pnls(engine: RegimeEngine) -> dict:
    """Load daily PnL for all 5 portfolio parents."""
    pnls = {}
    for p in PORTFOLIO_PARENTS:
        config = ASSET_CONFIG[p["asset"]]
        df = load_data(p["asset"])

        if p.get("exit_variant") == "profit_ladder":
            from research.exit_evolution import donchian_entries, apply_profit_ladder
            mod = load_strategy(p["name"])
            mod.TICK_SIZE = config["tick_size"]
            data = donchian_entries(df)
            pl_signals_df = apply_profit_ladder(data)
            result = run_backtest(df, pl_signals_df, mode=p["mode"],
                                  point_value=config["point_value"], symbol=p["asset"])
            trades = result["trades_df"]
        else:
            mod = load_strategy(p["name"])
            if hasattr(mod, "TICK_SIZE"):
                mod.TICK_SIZE = config["tick_size"]
            signals = mod.generate_signals(df)
            result = run_backtest(df, signals, mode=p["mode"],
                                  point_value=config["point_value"], symbol=p["asset"])
            trades = result["trades_df"]

        if p.get("grinding_filter") and not trades.empty:
            regime_daily = engine.get_daily_regimes(df)
            regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
            regime_daily["_date_date"] = regime_daily["_date"].dt.date
            trades_c = trades.copy()
            trades_c["entry_date"] = pd.to_datetime(trades_c["entry_time"]).dt.date
            trades_c = trades_c.merge(
                regime_daily[["_date_date", "trend_persistence"]],
                left_on="entry_date", right_on="_date_date", how="left",
            )
            trades = trades_c[trades_c["trend_persistence"] == "GRINDING"]
            trades = trades.drop(columns=["entry_date", "_date_date",
                                          "trend_persistence"], errors="ignore")

        w = VOL_WEIGHTS.get(p["label"], 1.0)
        if not trades.empty:
            trades = trades.copy()
            trades["pnl"] = trades["pnl"] * w

        pnls[p["label"]] = get_daily_pnl(trades)
    return pnls


def _clean_for_json(obj):
    """Convert numpy types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_for_json(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return round(float(obj), 6)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS (inline, adapted from run_validation_battery.py)
# ═══════════════════════════════════════════════════════════════════════════

def _run_strategy_on_data(name, df, asset, mode, param_overrides=None, rsi_mirror=False):
    """Run strategy on provided DataFrame (for walk-forward slicing)."""
    config = ASSET_CONFIG[asset]
    mod = load_strategy(name)
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]
    if param_overrides:
        for k, v in param_overrides.items():
            setattr(mod, k, v)
        if rsi_mirror and "RSI_OVERSOLD" in param_overrides:
            setattr(mod, "RSI_OVERBOUGHT", 100 - param_overrides["RSI_OVERSOLD"])
    signals = mod.generate_signals(df)
    result = run_backtest(df, signals, mode=mode,
                          point_value=config["point_value"], symbol=asset)
    return result["trades_df"]


def run_validation_battery(name, asset, mode, best_params=None, rsi_mirror=False):
    """Run the full 6-test, 10-criterion validation battery.

    Returns (results_dict, stability_score, hard_failures, promotion_label).
    """
    config = ASSET_CONFIG[asset]
    pv = config["point_value"]
    results = {}

    # ── Baseline ──────────────────────────────────────────────────────
    print("\n    BASELINE SANITY CHECK")
    trades_base, _, df_base = run_combo(name, asset, mode, best_params, rsi_mirror)
    m_base = quick_metrics(trades_base)
    print(f"    {m_base['trades']} trades, PF={m_base['pf']:.3f}, "
          f"Sharpe={m_base['sharpe']:.2f}, PnL=${m_base['pnl']:,.2f}")
    results["baseline"] = m_base

    # ── Test 1: Walk-Forward ──────────────────────────────────────────
    print("\n    1. WALK-FORWARD TIME SPLITS")
    df = load_data(asset)
    df["_dt"] = pd.to_datetime(df["datetime"])

    year_periods = {
        "2024": (pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")),
        "2025": (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")),
        "2026": (pd.Timestamp("2026-01-01"), pd.Timestamp("2027-01-01")),
    }
    year_results = {}
    for label, (start, end) in year_periods.items():
        subset = df[(df["_dt"] >= start) & (df["_dt"] < end)].drop(
            columns=["_dt"]).copy().reset_index(drop=True)
        if len(subset) < 100:
            year_results[label] = {"trades": 0, "pf": 0, "low_sample": True}
            continue
        trades = _run_strategy_on_data(name, subset, asset, mode, best_params, rsi_mirror)
        m = quick_metrics(trades)
        m["low_sample"] = m["trades"] < LOW_SAMPLE_THRESHOLD
        year_results[label] = m
        flag = " [LOW_SAMPLE]" if m["low_sample"] else ""
        print(f"    {label}: {m['trades']} trades, PF={m['pf']:.3f}, "
              f"Sharpe={m['sharpe']:.2f}, PnL=${m['pnl']:,.2f}{flag}")

    gated = ["2024", "2025"]
    year_pass_count = sum(1 for p in gated
                          if year_results.get(p, {}).get("trades", 0) > 0
                          and year_results[p].get("pf", 0) > 1.0)
    year_gated_count = sum(1 for p in gated
                           if year_results.get(p, {}).get("trades", 0) > 0)
    year_splits_pass = year_pass_count >= year_gated_count if year_gated_count > 0 else False

    # Rolling windows
    windows = [
        ("W1", "2024-08-01", "2025-02-01"),
        ("W2", "2025-02-01", "2025-08-01"),
        ("W3", "2025-08-01", "2026-02-01"),
    ]
    rolling_pass_count = 0
    rolling_total = 0
    rolling_results = {}
    for wlabel, test_s, test_e in windows:
        subset = df[(df["_dt"] >= pd.Timestamp(test_s)) &
                     (df["_dt"] < pd.Timestamp(test_e))].drop(
            columns=["_dt"]).copy().reset_index(drop=True)
        if len(subset) < 100:
            rolling_results[wlabel] = {"trades": 0, "pf": 0}
            continue
        trades = _run_strategy_on_data(name, subset, asset, mode, best_params, rsi_mirror)
        m = quick_metrics(trades)
        rolling_results[wlabel] = m
        rolling_total += 1
        if m["pf"] > 1.0:
            rolling_pass_count += 1
        flag = " [LOW_SAMPLE]" if m["trades"] < LOW_SAMPLE_THRESHOLD else ""
        print(f"    {wlabel} test: {m['trades']} trades, PF={m['pf']:.3f}{flag}")

    rolling_pass = (rolling_pass_count / rolling_total >= 0.75
                    if rolling_total > 0 else False)
    df.drop(columns=["_dt"], inplace=True, errors="ignore")

    print(f"    Year splits: {'PASS' if year_splits_pass else 'FAIL'}")
    print(f"    Rolling >=75%: {'PASS' if rolling_pass else 'FAIL'} "
          f"({rolling_pass_count}/{rolling_total})")
    results["walk_forward"] = {
        "year_splits": year_results,
        "year_splits_pass": year_splits_pass,
        "rolling_pass": rolling_pass,
        "rolling_pass_count": rolling_pass_count,
        "rolling_total": rolling_total,
    }

    # ── Test 2: Regime Stability ──────────────────────────────────────
    print("\n    2. REGIME STABILITY")
    engine = RegimeEngine()
    df = load_data(asset)
    daily_regimes = engine.get_daily_regimes(df)
    trades_all, _, _ = run_combo(name, asset, mode, best_params, rsi_mirror)

    if not trades_all.empty:
        tc = trades_all.copy()
        tc["_trade_date"] = pd.to_datetime(tc["entry_time"]).dt.date
        merged = tc.merge(daily_regimes, left_on="_trade_date",
                          right_on="_date", how="left")
        merged["regime_cell"] = (merged["vol_regime"].fillna("UNK") + "_" +
                                 merged["trend_regime"].fillna("UNK") + "_" +
                                 merged["rv_regime"].fillna("UNK"))
        catastrophic_cells = []
        grid = {}
        for cell, group in merged.groupby("regime_cell"):
            pnl = group["pnl"]
            wins_c = pnl[pnl > 0]
            losses_c = pnl[pnl < 0]
            gp = wins_c.sum() if len(wins_c) else 0
            gl = abs(losses_c.sum()) if len(losses_c) else 0
            pf_cell = gp / gl if gl > 0 else (100.0 if gp > 0 else 0)
            grid[cell] = {"trades": len(group), "pf": round(pf_cell, 4),
                          "pnl": round(pnl.sum(), 2)}
            if len(group) >= 10 and pf_cell < 0.5:
                catastrophic_cells.append(cell)
            flag = ""
            if cell in catastrophic_cells:
                flag = " *** CATASTROPHIC ***"
            elif len(group) < LOW_SAMPLE_THRESHOLD:
                flag = " [LOW_SAMPLE]"
            print(f"    {cell:>35s}  {len(group):>4} trades  "
                  f"PF={pf_cell:.3f}  PnL=${pnl.sum():>8,.2f}{flag}")

        regime_pass = len(catastrophic_cells) == 0
    else:
        regime_pass = False
        grid = {}
        catastrophic_cells = []

    print(f"    Regime stability: {'PASS' if regime_pass else 'FAIL'}")
    results["regime_stability"] = {
        "grid": grid, "catastrophic_cells": catastrophic_cells,
        "passes": regime_pass,
    }

    # ── Test 3: Asset Robustness (gold-only accommodation) ────────────
    print("\n    3. ASSET ROBUSTNESS (gold-only accommodation)")
    asset_results = {}
    profitable_count = 0
    for test_asset in ["MNQ", "MES", "MGC"]:
        try:
            df_a = load_data(test_asset)
        except FileNotFoundError:
            asset_results[test_asset] = {"trades": 0, "pf": 0, "skipped": True}
            continue
        acfg = ASSET_CONFIG[test_asset]
        trades_a = _run_strategy_on_data(name, df_a, test_asset, mode,
                                          best_params, rsi_mirror)
        m_a = quick_metrics(trades_a)
        asset_results[test_asset] = m_a
        if m_a["pf"] > 1.0 and m_a["trades"] > 0:
            profitable_count += 1
        flag = " [LOW_SAMPLE]" if m_a["trades"] < LOW_SAMPLE_THRESHOLD else ""
        print(f"    {test_asset}: {m_a['trades']} trades, PF={m_a['pf']:.3f}, "
              f"PnL=${m_a['pnl']:,.2f}{flag}")

    # Gold-only: 1/3 assets acceptable (0.5 penalty instead of 1.0)
    asset_pass = profitable_count >= 2
    asset_gold_only = profitable_count == 1 and asset_results.get("MGC", {}).get("pf", 0) > 1.0
    print(f"    Profitable: {profitable_count}/3"
          f"{' (gold-only — 0.5 penalty)' if asset_gold_only else ''}")
    results["asset_robustness"] = {
        "assets": asset_results, "profitable_count": profitable_count,
        "passes": asset_pass, "gold_only": asset_gold_only,
    }

    # ── Test 4: Timeframe Robustness ──────────────────────────────────
    print("\n    4. TIMEFRAME ROBUSTNESS")
    tf_results = {}
    tf_profitable = 0
    try:
        df_1m = load_1m_data(asset)
    except FileNotFoundError:
        df_1m = None
        print(f"    1m data not found for {asset}, using 5m only")

    for tf_label, tf_min in [("5m", 5), ("10m", 10), ("15m", 15)]:
        if tf_label == "5m":
            df_tf = load_data(asset)
        elif df_1m is not None:
            df_tf = resample_bars(df_1m, tf_min)
        else:
            tf_results[tf_label] = {"trades": 0, "pf": 0, "skipped": True}
            continue
        trades_tf = _run_strategy_on_data(name, df_tf, asset, mode,
                                           best_params, rsi_mirror)
        m_tf = quick_metrics(trades_tf)
        tf_results[tf_label] = m_tf
        if m_tf["pf"] > 1.0 and m_tf["trades"] > 0:
            tf_profitable += 1
        flag = " [LOW_SAMPLE]" if m_tf["trades"] < LOW_SAMPLE_THRESHOLD else ""
        print(f"    {tf_label}: {m_tf['trades']} trades, PF={m_tf['pf']:.3f}{flag}")

    tf_pass = tf_profitable >= 2
    print(f"    Timeframe: {'PASS' if tf_pass else 'FAIL'} ({tf_profitable}/3)")
    results["timeframe_robustness"] = {
        "timeframes": tf_results, "profitable_count": tf_profitable,
        "passes": tf_pass,
    }

    # ── Test 5: Monte Carlo / Bootstrap ───────────────────────────────
    print("\n    5. MONTE CARLO / BOOTSTRAP")
    trades_full, _, _ = run_combo(name, asset, mode, best_params, rsi_mirror)

    if len(trades_full) >= 5:
        trade_pnls = trades_full["pnl"].values
        daily = get_daily_pnl(trades_full)

        # Bootstrap
        boot = bootstrap_metrics(trade_pnls, seed=SEED)
        bootstrap_pass = boot["pf"]["ci_low"] > 1.0
        print(f"    Bootstrap PF CI: [{boot['pf']['ci_low']:.3f}, "
              f"{boot['pf']['ci_high']:.3f}]  "
              f"{'PASS' if bootstrap_pass else 'FAIL'}")

        # DSR
        obs_sharpe = (float(daily.mean() / daily.std() * np.sqrt(252))
                      if len(daily) > 1 and daily.std() > 0 else 0)
        dsr_result = deflated_sharpe_ratio(
            observed_sharpe=obs_sharpe, n_trials=N_TRIALS,
            n_observations=len(daily), returns=daily.values,
        )
        dsr_pass = dsr_result["dsr"] > 0.95
        print(f"    DSR: {dsr_result['dsr']:.4f}  "
              f"{'PASS' if dsr_pass else 'FAIL'}")

        # Monte Carlo ruin
        rng = np.random.default_rng(SEED)
        max_drawdowns = np.zeros(N_SIMULATIONS)
        for i in range(N_SIMULATIONS):
            shuffled = rng.permutation(trade_pnls)
            eq = STARTING_CAPITAL + np.cumsum(shuffled)
            pk = np.maximum.accumulate(eq)
            max_drawdowns[i] = (pk - eq).max()
        ruin_probs = {}
        for floor in [1000, 2000, 3000, 4000, 5000]:
            prob = (max_drawdowns >= floor).mean() * 100
            ruin_probs[f"${floor:,}"] = round(prob, 2)
        mc_pass = ruin_probs.get("$2,000", 100) < 5
        print(f"    P(ruin $2K): {ruin_probs.get('$2,000', 0):.1f}%  "
              f"{'PASS' if mc_pass else 'FAIL'}")

        # Top-trade removal
        top_idx = np.argmax(trade_pnls)
        top_pnl = trade_pnls[top_idx]
        pnl_without = np.delete(trade_pnls, top_idx)
        w_w = pnl_without[pnl_without > 0].sum()
        l_w = abs(pnl_without[pnl_without < 0].sum())
        pf_without = w_w / l_w if l_w > 0 else (100.0 if w_w > 0 else 0)
        top_trade_pass = pf_without > 1.0
        print(f"    PF without top trade: {pf_without:.3f}  "
              f"{'PASS' if top_trade_pass else 'FAIL'}")
    else:
        bootstrap_pass = dsr_pass = mc_pass = top_trade_pass = False
        boot = {"pf": {"ci_low": 0, "ci_high": 0}}
        dsr_result = {"dsr": 0}
        ruin_probs = {}
        pf_without = 0
        top_pnl = 0

    results["monte_carlo_bootstrap"] = {
        "bootstrap_pass": bootstrap_pass,
        "bootstrap": {"pf": boot["pf"]},
        "dsr_pass": dsr_pass,
        "dsr": {"dsr": dsr_result.get("dsr", 0)},
        "mc_pass": mc_pass,
        "monte_carlo": {"ruin_probability": ruin_probs},
        "top_trade_pass": top_trade_pass,
        "top_trade": {"pf_without_top": round(pf_without, 4),
                      "top_trade_pnl": round(float(top_pnl), 2)},
    }

    # ── Test 6: Parameter Stability (use Step 1 grid) ─────────────────
    print("\n    6. PARAMETER STABILITY")
    param_grid = VALIDATION_PARAM_GRIDS.get(name, {})
    if param_grid:
        param_names = list(param_grid.keys())
        combinations = list(product(*param_grid.values()))
        profitable = 0
        total = len(combinations)
        df_ps = load_data(asset)
        for combo in combinations:
            overrides = dict(zip(param_names, combo))
            # Mirror RSI for bb_range_mr
            is_rsi_mirror = rsi_mirror
            try:
                trades_p = _run_strategy_on_data(
                    name, df_ps, asset, mode, overrides, is_rsi_mirror)
                m_p = quick_metrics(trades_p)
                if m_p["pf"] > 1.0 and m_p["trades"] > 0:
                    profitable += 1
            except Exception:
                pass

        pct = profitable / total * 100 if total > 0 else 0
        param_pass = pct >= 60
        print(f"    {profitable}/{total} combos PF > 1.0 ({pct:.0f}%)")
        print(f"    Parameter stability: {'PASS' if param_pass else 'FAIL'}")
    else:
        pct = 0
        param_pass = False
        total = 0
        profitable = 0
        print(f"    No parameter grid for {name}")

    results["parameter_stability"] = {
        "pct_profitable": round(pct, 1), "passes": param_pass,
        "total_combinations": total, "profitable": profitable,
    }

    # ── Stability Score ───────────────────────────────────────────────
    score = 0.0
    # Walk-forward year splits
    if year_splits_pass:
        score += 1.0
    elif year_pass_count >= 1:
        score += 0.5
    # Rolling
    if rolling_pass:
        score += 1.0
    # Regime
    if regime_pass:
        score += 1.0
    # Asset (gold-only accommodation: 0.5 instead of 0)
    if asset_pass:
        score += 1.0
    elif asset_gold_only:
        score += 0.5
    # Timeframe
    if tf_pass:
        score += 1.0
    elif tf_profitable >= 1:
        score += 0.5
    # Bootstrap
    if bootstrap_pass:
        score += 1.0
    # DSR
    if dsr_pass:
        score += 1.0
    # MC
    if mc_pass:
        score += 1.0
    # Parameter
    if param_pass:
        score += 1.0
        if pct >= 80:
            score += 0.5
    # Top-trade removal
    if top_trade_pass:
        score += 0.5

    score = round(score, 1)

    # Hard failures (gold-only asset failure counts as 0.5)
    failures = 0
    if not year_splits_pass:
        failures += 1
    if not rolling_pass:
        failures += 1
    if not regime_pass:
        failures += 1
    if not asset_pass:
        if asset_gold_only:
            failures += 0.5  # Gold-only accommodation
        else:
            failures += 1
    if not tf_pass:
        failures += 1
    if not bootstrap_pass:
        failures += 1
    if not dsr_pass:
        failures += 1
    if not mc_pass:
        failures += 1
    if not top_trade_pass:
        failures += 1
    if not param_pass:
        failures += 1

    results["stability_score"] = score
    results["hard_failures"] = failures

    if score >= 7.0 and failures == 0:
        promotion = "PROMOTE"
    elif 5.0 <= score or (0 < failures <= 2):
        promotion = "CONDITIONAL"
    else:
        promotion = "REJECT"
    results["promotion"] = promotion

    print(f"\n    STABILITY SCORE: {score}/10")
    print(f"    HARD FAILURES: {failures}")
    print(f"    PROMOTION: {promotion}")

    return results, score, failures, promotion


# ═══════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print_header("PHASE 14: GOLD MR REFINEMENT — BUILD THE 6TH PARENT")
    engine = RegimeEngine()

    # ═══════════════════════════════════════════════════════════════════
    # STEP 1: PARAMETER REFINEMENT GRID
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 1: PARAMETER REFINEMENT GRID")

    ASSET = "MGC"
    MODE = "long"

    all_grid_results = {}  # {label: [list of combo results]}

    for cand in GOLD_MR_CANDIDATES:
        label = cand["label"]
        name = cand["name"]
        grid = cand["param_grid"]
        rsi_mirror = cand.get("rsi_mirror", False)

        param_names = list(grid.keys())
        combos = list(product(*grid.values()))
        print(f"\n  ── {label} ({len(combos)} combos) ──")
        print(f"  {'#':>3s} ", end="")
        for pn in param_names:
            print(f"{pn:>18s} ", end="")
        print(f"{'PF':>7s} {'Sharpe':>7s} {'Trades':>7s} {'MedH':>5s} {'PnL':>10s}")

        combo_results = []
        for ci, combo in enumerate(combos, 1):
            overrides = dict(zip(param_names, combo))
            try:
                trades, _, _ = run_combo(name, ASSET, MODE, overrides, rsi_mirror)
                m = quick_metrics(trades)
            except Exception as e:
                m = {"pf": 0, "sharpe": 0, "trades": 0, "median_hold": 0,
                     "pnl": 0, "maxdd": 0, "wr": 0}

            combo_results.append({**overrides, **m, "label": label, "name": name,
                                   "_trades_df": trades})

            print(f"  {ci:>3d} ", end="")
            for pn in param_names:
                val = overrides[pn]
                print(f"{str(val):>18s} ", end="")
            pf_s = f"{m['pf']:.2f}" if m['trades'] >= 10 else f"{m['pf']:.2f}*"
            print(f"{pf_s:>7s} {m['sharpe']:>7.2f} {m['trades']:>7d} "
                  f"{m['median_hold']:>5d} ${m['pnl']:>9,.0f}")

        all_grid_results[label] = combo_results

    # ═══════════════════════════════════════════════════════════════════
    # STEP 2: BEST VARIANT SELECTION (with Prop Speed Score)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 2: BEST VARIANT SELECTION")

    # Calculate trading months from data
    df_mgc = load_data(ASSET)
    date_range = (pd.to_datetime(df_mgc["datetime"]).max() -
                  pd.to_datetime(df_mgc["datetime"]).min())
    trading_months = max(date_range.days / 30.44, 1)

    best_variants = {}

    for label, results_list in all_grid_results.items():
        # Filter to minimum 30 trades
        qualifying = [r for r in results_list if r["trades"] >= 30]
        if not qualifying:
            print(f"\n  {label}: NO qualifying variants (all <30 trades)")
            continue

        # Compute Prop Speed Score for each qualifying variant
        # Use cached trades from Step 1 to avoid re-running backtests
        df_mgc_raw = load_data(ASSET)  # for regime breakdown
        for r in qualifying:
            tpm = r["trades"] / trading_months
            inv_dd = 1 / max(r["maxdd"], 1)
            # Monthly consistency from cached trades
            cached_trades = r.get("_trades_df", pd.DataFrame())
            daily_pnl = get_daily_pnl(cached_trades)
            if not daily_pnl.empty:
                monthly = daily_pnl.resample("ME").sum()
                monthly_consistency = (monthly > 0).sum() / len(monthly) if len(monthly) > 0 else 0
            else:
                monthly_consistency = 0

            # Normalize components for scoring
            prop_speed = (tpm * 0.4 + inv_dd * 0.3 + monthly_consistency * 0.3)
            r["trades_per_month"] = round(tpm, 2)
            r["monthly_consistency"] = round(monthly_consistency, 3)
            r["prop_speed_score"] = round(prop_speed, 4)

            # RANGING_EDGE_SCORE from cached trades
            _, _, _, res, _ = compute_regime_breakdown(cached_trades, df_mgc_raw, engine)
            r["ranging_edge_score"] = res

        # Parameter stability: % of all combos with PF > 1.0
        all_with_trades = [r for r in results_list if r["trades"] > 0]
        pf_above_1 = sum(1 for r in all_with_trades if r["pf"] > 1.0)
        param_stability_pct = round(pf_above_1 / len(all_with_trades) * 100, 1) if all_with_trades else 0

        # Normalize for composite score
        pf_vals = [r["pf"] for r in qualifying]
        sharpe_vals = [r["sharpe"] for r in qualifying]
        trade_vals = [r["trades"] for r in qualifying]
        speed_vals = [r["prop_speed_score"] for r in qualifying]
        res_vals = [r["ranging_edge_score"] for r in qualifying]

        def _norm(v, vals):
            mn, mx = min(vals), max(vals)
            return (v - mn) / (mx - mn) if mx > mn else 0.5

        for r in qualifying:
            composite = (
                _norm(r["pf"], pf_vals) * 0.35 +
                _norm(r["sharpe"], sharpe_vals) * 0.25 +
                _norm(r["trades"], trade_vals) * 0.15 +
                _norm(r["prop_speed_score"], speed_vals) * 0.15 +
                _norm(r["ranging_edge_score"], res_vals) * 0.10
            )
            r["composite_score"] = round(composite, 4)

        # Pick best
        qualifying.sort(key=lambda x: x["composite_score"], reverse=True)
        best = qualifying[0]
        best["param_stability_pct"] = param_stability_pct
        # Store cached trades for Steps 3-4 (avoid re-running)
        best["_cached_trades"] = best.pop("_trades_df", pd.DataFrame())
        best_variants[label] = best

        cand_info = [c for c in GOLD_MR_CANDIDATES if c["label"] == label][0]
        param_keys = list(cand_info["param_grid"].keys())

        print(f"\n  ── {label} ──")
        print(f"  Best variant: {', '.join(f'{k}={best[k]}' for k in param_keys)}")
        print(f"  PF={best['pf']:.2f}, Sharpe={best['sharpe']:.2f}, "
              f"Trades={best['trades']}, MedHold={best['median_hold']}bars")
        print(f"  Prop Speed Score: {best['prop_speed_score']:.4f} "
              f"(TPM={best['trades_per_month']:.1f}, "
              f"MthConsist={best['monthly_consistency']:.0%})")
        print(f"  RANGING_EDGE_SCORE: {best['ranging_edge_score']:.3f}")
        print(f"  Param stability: {param_stability_pct:.0f}% of combos PF>1.0")
        print(f"  Composite score: {best['composite_score']:.4f}")

    if not best_variants:
        print("\n  NO VIABLE CANDIDATES — Phase 14 complete.")
        return

    # ═══════════════════════════════════════════════════════════════════
    # STEP 3: CROSS-CORRELATION (4×4 MATRIX)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 3: CROSS-CORRELATION MATRIX")

    # Get daily PnLs for each best variant (use cached trades)
    variant_daily = {}
    for label, bv in best_variants.items():
        cached = bv.get("_cached_trades", pd.DataFrame())
        variant_daily[label] = get_daily_pnl(cached)

    # Print 4×4 matrix
    labels = list(best_variants.keys())
    print(f"\n  {'':>18s}", end="")
    for l in labels:
        print(f"  {l:>16s}", end="")
    print()

    corr_matrix = {}
    for l1 in labels:
        print(f"  {l1:>18s}", end="")
        corr_matrix[l1] = {}
        for l2 in labels:
            if l1 == l2:
                corr = 1.0
            else:
                combined = pd.DataFrame({
                    "a": variant_daily.get(l1, pd.Series(dtype=float)),
                    "b": variant_daily.get(l2, pd.Series(dtype=float)),
                }).fillna(0)
                if combined["a"].std() > 0 and combined["b"].std() > 0:
                    corr = combined["a"].corr(combined["b"])
                else:
                    corr = 0.0
            corr_matrix[l1][l2] = round(corr, 3)
            marker = " !" if abs(corr) > 0.4 and l1 != l2 else ""
            print(f"  {corr:>+16.3f}{marker}", end="")
        print()

    # Flag redundant pairs
    print("\n  Redundancy check (|r| > 0.4):")
    redundant_pairs = []
    for i, l1 in enumerate(labels):
        for l2 in labels[i+1:]:
            r_val = abs(corr_matrix[l1][l2])
            if r_val > 0.4:
                redundant_pairs.append((l1, l2, r_val))
                print(f"    {l1} <-> {l2}: |r|={r_val:.3f} — REDUNDANT")
    if not redundant_pairs:
        print("    No redundant pairs found.")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 4: REGIME + DURATION FINGERPRINT
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 4: REGIME + DURATION FINGERPRINT")

    df_mgc_step4 = load_data(ASSET)
    for label, bv in best_variants.items():
        trades = bv.get("_cached_trades", pd.DataFrame())

        breakdown, rng_trades, rng_pnl, rng_edge, trend_bleed = \
            compute_regime_breakdown(trades, df_mgc_step4, engine)

        median_hold = bv["median_hold"]
        mr_dna = 5 <= median_hold <= 20

        print(f"\n  ── {label} ──")
        print(f"  Duration: {median_hold} bars "
              f"{'(MR DNA OK)' if mr_dna else '(WRONG DNA)'}")
        print(f"  RANGING: {rng_trades} trades, ${rng_pnl:,.0f}")
        print(f"  RANGING_EDGE_SCORE: {rng_edge:.3f}")
        print(f"  TRENDING bleed: {trend_bleed:.3f}")

        sorted_cells = sorted(breakdown.items(),
                               key=lambda x: x[1]["pnl"], reverse=True)
        print(f"  Top 5 regime cells:")
        for cell, data in sorted_cells[:5]:
            is_ranging = "RANGING" in cell
            marker = " ★" if is_ranging else ""
            print(f"    {cell:<35s} {data['trades']:>4d} trades  "
                  f"${data['pnl']:>8,.0f}{marker}")

        bv["regime_breakdown"] = breakdown
        bv["ranging_trades"] = rng_trades
        bv["ranging_pnl"] = rng_pnl
        bv["ranging_edge_score"] = rng_edge
        bv["trending_bleed"] = trend_bleed
        bv["mr_dna_ok"] = mr_dna

    # ═══════════════════════════════════════════════════════════════════
    # STEP 5: VALIDATION BATTERY (TOP 1-2 CANDIDATES)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 5: VALIDATION BATTERY")

    # Rank candidates by composite score for validation
    ranked = sorted(best_variants.items(),
                     key=lambda x: x[1]["composite_score"], reverse=True)

    # Validate top 2 (or fewer if only that many exist)
    validation_results = {}
    for label, bv in ranked[:2]:
        cand_info = [c for c in GOLD_MR_CANDIDATES if c["label"] == label][0]
        overrides = {k: bv[k] for k in cand_info["param_grid"].keys()}

        print(f"\n  ── VALIDATING: {label} ──")
        print(f"  Params: {overrides}")

        vr, score, failures, promotion = run_validation_battery(
            bv["name"], ASSET, MODE, overrides,
            cand_info.get("rsi_mirror", False))

        validation_results[label] = {
            "results": vr,
            "stability_score": score,
            "hard_failures": failures,
            "promotion": promotion,
        }
        bv["validation_score"] = score
        bv["validation_failures"] = failures
        bv["validation_promotion"] = promotion

    # ═══════════════════════════════════════════════════════════════════
    # STEP 6: PORTFOLIO IMPACT (6-STRATEGY)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 6: PORTFOLIO IMPACT (6-STRATEGY)")

    print("  Loading parent daily PnLs...")
    parent_pnls = load_parent_daily_pnls(engine)

    # Baseline 5-strat portfolio
    port_df = pd.DataFrame(parent_pnls).fillna(0)
    portfolio_daily = port_df.sum(axis=1).sort_index()

    baseline_sharpe = (portfolio_daily.mean() / portfolio_daily.std() * np.sqrt(252)
                       if portfolio_daily.std() > 0 else 0)
    baseline_eq = STARTING_CAPITAL + portfolio_daily.cumsum()
    baseline_peak = baseline_eq.cummax()
    baseline_maxdd = (baseline_peak - baseline_eq).max()
    baseline_calmar = (portfolio_daily.sum() / baseline_maxdd
                       if baseline_maxdd > 0 else 0)
    baseline_monthly = portfolio_daily.resample("ME").sum()
    baseline_monthly_pct = ((baseline_monthly > 0).sum() / len(baseline_monthly) * 100
                            if len(baseline_monthly) > 0 else 0)

    print(f"\n  5-strat baseline: Sharpe={baseline_sharpe:.2f}, "
          f"Calmar={baseline_calmar:.2f}, MaxDD=${baseline_maxdd:,.0f}, "
          f"Monthly={baseline_monthly_pct:.0f}%")

    for label, bv in best_variants.items():
        cand_daily = variant_daily.get(label, pd.Series(dtype=float))
        if cand_daily.empty:
            continue

        # 6-strat portfolio
        combined = pd.DataFrame({"port": portfolio_daily, "cand": cand_daily}).fillna(0)
        port6_daily = combined.sum(axis=1).sort_index()

        sharpe6 = (port6_daily.mean() / port6_daily.std() * np.sqrt(252)
                   if port6_daily.std() > 0 else 0)
        eq6 = STARTING_CAPITAL + port6_daily.cumsum()
        peak6 = eq6.cummax()
        maxdd6 = (peak6 - eq6).max()
        calmar6 = port6_daily.sum() / maxdd6 if maxdd6 > 0 else 0
        monthly6 = port6_daily.resample("ME").sum()
        monthly6_pct = ((monthly6 > 0).sum() / len(monthly6) * 100
                        if len(monthly6) > 0 else 0)

        sharpe_delta = sharpe6 - baseline_sharpe
        calmar_delta = calmar6 - baseline_calmar
        maxdd_delta = maxdd6 - baseline_maxdd

        # Vol Target weight (inverse-vol sizing)
        if not cand_daily.empty and cand_daily.std() > 0:
            cand_vol = cand_daily.std() * np.sqrt(252)
            avg_parent_vol = np.mean([
                parent_pnls[p].std() * np.sqrt(252)
                for p in parent_pnls if not parent_pnls[p].empty
                and parent_pnls[p].std() > 0
            ]) if parent_pnls else 1
            vol_target_weight = round(avg_parent_vol / cand_vol, 3) if cand_vol > 0 else 1.0
        else:
            vol_target_weight = 1.0

        # Correlation vs each parent
        parent_corrs = {}
        for p_label, p_daily in parent_pnls.items():
            comb = pd.DataFrame({"c": cand_daily, "p": p_daily}).fillna(0)
            if comb["c"].std() > 0 and comb["p"].std() > 0:
                parent_corrs[p_label] = round(comb["c"].corr(comb["p"]), 3)
            else:
                parent_corrs[p_label] = 0.0

        max_parent_corr = max(abs(v) for v in parent_corrs.values()) if parent_corrs else 0

        bv["portfolio_impact"] = {
            "sharpe_6strat": round(sharpe6, 2),
            "sharpe_delta": round(sharpe_delta, 2),
            "calmar_6strat": round(calmar6, 2),
            "calmar_delta": round(calmar_delta, 2),
            "maxdd_6strat": round(maxdd6, 2),
            "maxdd_delta": round(maxdd_delta, 2),
            "monthly_pct": round(monthly6_pct, 1),
            "pnl_6strat": round(port6_daily.sum(), 2),
            "vol_target_weight": vol_target_weight,
        }
        bv["parent_correlations"] = parent_corrs
        bv["max_parent_corr"] = max_parent_corr

        print(f"\n  ── {label} ──")
        print(f"  6-strat: Sharpe={sharpe6:.2f} ({sharpe_delta:+.2f}), "
              f"Calmar={calmar6:.2f} ({calmar_delta:+.2f})")
        print(f"  MaxDD=${maxdd6:,.0f} ({maxdd_delta:+,.0f}), "
              f"Monthly={monthly6_pct:.0f}%")
        print(f"  Vol Target weight: {vol_target_weight:.3f}")
        print(f"  Parent correlations:")
        for p_label, corr in parent_corrs.items():
            marker = " !" if abs(corr) > 0.25 else ""
            print(f"    vs {p_label:<8s}: r={corr:+.3f}{marker}")
        print(f"  Max |r| vs parents: {max_parent_corr:.3f}")
        print(f"  Portfolio impact: "
              f"{'POSITIVE' if sharpe_delta > 0 else 'NEGATIVE'}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 7: FAST PASS POTENTIAL TEST
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 7: FAST PASS POTENTIAL TEST")

    EVAL_TARGET = 3000     # $3K profit target
    EVAL_DD = 2000         # $2K trailing DD bust
    TIME_HORIZONS = [1, 3, 5]

    for label, bv in best_variants.items():
        cand_daily = variant_daily.get(label, pd.Series(dtype=float))
        if cand_daily.empty or len(cand_daily) < 5:
            bv["fast_pass"] = {"pass_probability": 0, "median_days_to_pass": 999,
                                "bust_probability": 100, "is_fast_pass_candidate": False}
            print(f"\n  {label}: insufficient data for fast pass test")
            continue

        daily_vals = cand_daily.values
        rng = np.random.default_rng(SEED)
        n_sims = N_SIMULATIONS

        # Monte Carlo: simulate equity paths by reshuffling daily PnLs
        pass_counts = {h: 0 for h in TIME_HORIZONS}
        bust_counts = {h: 0 for h in TIME_HORIZONS}
        days_to_pass = []

        for _ in range(n_sims):
            # Simulate up to max horizon days
            max_horizon = max(TIME_HORIZONS)
            sim_days = rng.choice(daily_vals, size=max_horizon, replace=True)
            equity = np.cumsum(sim_days)

            # Track trailing drawdown
            peak = np.maximum.accumulate(equity)
            trailing_dd = peak - equity

            # Find first pass and first bust
            passed_day = None
            busted_day = None
            for d in range(max_horizon):
                if passed_day is None and equity[d] >= EVAL_TARGET:
                    passed_day = d + 1
                if busted_day is None and trailing_dd[d] >= EVAL_DD:
                    busted_day = d + 1

            if passed_day is not None:
                days_to_pass.append(passed_day)

            for h in TIME_HORIZONS:
                # Check if passed within h days (before bust)
                p_in_h = passed_day is not None and passed_day <= h
                b_in_h = busted_day is not None and busted_day <= h
                if p_in_h and (not b_in_h or passed_day <= busted_day):
                    pass_counts[h] += 1
                if b_in_h and (not p_in_h or busted_day < passed_day):
                    bust_counts[h] += 1

        pass_probs = {h: round(pass_counts[h] / n_sims * 100, 1) for h in TIME_HORIZONS}
        bust_probs = {h: round(bust_counts[h] / n_sims * 100, 1) for h in TIME_HORIZONS}
        med_days = round(float(np.median(days_to_pass)), 1) if days_to_pass else 999

        is_fast_pass = pass_probs.get(5, 0) > 45 and med_days < 5

        bv["fast_pass"] = {
            "pass_probability": pass_probs,
            "bust_probability": bust_probs,
            "median_days_to_pass": med_days,
            "is_fast_pass_candidate": is_fast_pass,
        }

        print(f"\n  ── {label} ──")
        print(f"  Eval: ${EVAL_TARGET:,} target, ${EVAL_DD:,} trailing DD")
        for h in TIME_HORIZONS:
            print(f"    {h}-day: pass={pass_probs[h]:.1f}%, bust={bust_probs[h]:.1f}%")
        print(f"  Median days to pass: {med_days:.1f}")
        print(f"  FAST_PASS_CANDIDATE: {'YES' if is_fast_pass else 'NO'}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 8: FINAL RANKING & PROMOTION DECISION
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 8: FINAL RANKING & PROMOTION DECISION")

    final_rankings = []

    for label, bv in best_variants.items():
        # Composite production parent score
        val_score = bv.get("validation_score", 0)
        pi = bv.get("portfolio_impact", {})
        sharpe_delta = pi.get("sharpe_delta", 0)
        max_p_corr = bv.get("max_parent_corr", 1.0)

        # Validation score (50%)
        val_component = val_score / 10.0

        # Portfolio impact (30%) — scale sharpe delta
        port_component = max(0, min(1, sharpe_delta / 0.5))

        # Correlation bonus (20%) — lower is better
        corr_component = max(0, 1.0 - max_p_corr / 0.35)

        production_score = round(
            val_component * 0.50 +
            port_component * 0.30 +
            corr_component * 0.20, 4)

        # Production Parent label
        val_failures = bv.get("validation_failures", 99)
        if (val_score >= 7.0 and val_failures == 0 and
                sharpe_delta > 0 and max_p_corr < 0.25):
            prod_label = "PROMOTE TO PARENT"
        elif (5.0 <= val_score or sharpe_delta <= 0 < pi.get("calmar_delta", 0)):
            prod_label = "PROBATION"
        else:
            prod_label = "REJECT"

        # Fast Pass label
        fp = bv.get("fast_pass", {})
        fp_label = "FAST_PASS_CANDIDATE" if fp.get("is_fast_pass_candidate") else "—"

        bv["production_score"] = production_score
        bv["production_label"] = prod_label
        bv["fast_pass_label"] = fp_label

        final_rankings.append({
            "label": label,
            "bv": bv,
            "production_score": production_score,
            "prod_label": prod_label,
            "fp_label": fp_label,
        })

    # Sort by production score
    final_rankings.sort(key=lambda x: x["production_score"], reverse=True)

    # Print ranking table
    print(f"\n  {'Rank':>4s} {'Strategy':<18s} {'PF':>6s} {'Sharpe':>7s} "
          f"{'Trades':>7s} {'ValScore':>9s} {'Failures':>9s} {'dSharpe':>8s} "
          f"{'|r|max':>7s} {'ProdScore':>10s} {'Label':<20s} {'FastPass':<18s}")
    print(f"  {'-'*4:>4s} {'-'*17:<18s} {'-'*6:>6s} {'-'*7:>7s} "
          f"{'-'*7:>7s} {'-'*9:>9s} {'-'*9:>9s} {'-'*8:>8s} "
          f"{'-'*7:>7s} {'-'*10:>10s} {'-'*19:<20s} {'-'*17:<18s}")

    for rank, fr in enumerate(final_rankings, 1):
        bv = fr["bv"]
        pi = bv.get("portfolio_impact", {})
        print(f"  {rank:>4d} {fr['label']:<18s} {bv['pf']:>6.2f} "
              f"{bv['sharpe']:>7.2f} {bv['trades']:>7d} "
              f"{bv.get('validation_score', 0):>9.1f} "
              f"{bv.get('validation_failures', '-'):>9} "
              f"{pi.get('sharpe_delta', 0):>+8.2f} "
              f"{bv.get('max_parent_corr', 0):>7.3f} "
              f"{fr['production_score']:>10.4f} "
              f"{fr['prod_label']:<20s} {fr['fp_label']:<18s}")

    # Summary
    print(f"\n  {'─' * 60}")
    promoted = [fr for fr in final_rankings if fr["prod_label"] == "PROMOTE TO PARENT"]
    probation = [fr for fr in final_rankings if fr["prod_label"] == "PROBATION"]
    fast_pass = [fr for fr in final_rankings if fr["fp_label"] == "FAST_PASS_CANDIDATE"]

    if promoted:
        print(f"  PROMOTED TO PARENT: {', '.join(f['label'] for f in promoted)}")
    elif probation:
        print(f"  PROBATION: {', '.join(f['label'] for f in probation)}")
    else:
        print(f"  NO PROMOTION — all candidates rejected or insufficient")

    if fast_pass:
        print(f"  FAST_PASS_CANDIDATE: {', '.join(f['label'] for f in fast_pass)}")

    # ═══════════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════════
    output = {
        "phase": "Phase 14 — Gold MR Refinement",
        "asset": ASSET,
        "mode": MODE,
        "trading_months": round(trading_months, 1),
        "candidates": {},
        "cross_correlation": corr_matrix,
        "baseline_portfolio": {
            "sharpe": round(baseline_sharpe, 2),
            "calmar": round(baseline_calmar, 2),
            "maxdd": round(baseline_maxdd, 2),
            "monthly_pct": round(baseline_monthly_pct, 1),
        },
        "ranking": [],
        "promotion_summary": {
            "promoted": [f["label"] for f in promoted] if promoted else [],
            "probation": [f["label"] for f in probation] if probation else [],
            "fast_pass_candidates": [f["label"] for f in fast_pass] if fast_pass else [],
        },
    }

    for fr in final_rankings:
        label = fr["label"]
        bv = fr["bv"]
        cand_info = [c for c in GOLD_MR_CANDIDATES if c["label"] == label][0]
        optimal_params = {k: bv[k] for k in cand_info["param_grid"].keys()}

        output["candidates"][label] = {
            "strategy_name": bv["name"],
            "optimal_params": optimal_params,
            "pf": bv["pf"],
            "sharpe": bv["sharpe"],
            "trades": bv["trades"],
            "pnl": bv["pnl"],
            "maxdd": bv["maxdd"],
            "median_hold": bv["median_hold"],
            "trades_per_month": bv.get("trades_per_month", 0),
            "monthly_consistency": bv.get("monthly_consistency", 0),
            "prop_speed_score": bv.get("prop_speed_score", 0),
            "ranging_edge_score": bv.get("ranging_edge_score", 0),
            "composite_score": bv.get("composite_score", 0),
            "param_stability_pct": bv.get("param_stability_pct", 0),
            "mr_dna_ok": bv.get("mr_dna_ok", False),
            "ranging_trades": bv.get("ranging_trades", 0),
            "ranging_pnl": bv.get("ranging_pnl", 0),
            "trending_bleed": bv.get("trending_bleed", 0),
            "validation_score": bv.get("validation_score", 0),
            "validation_failures": bv.get("validation_failures", 0),
            "validation_promotion": bv.get("validation_promotion", ""),
            "portfolio_impact": bv.get("portfolio_impact", {}),
            "parent_correlations": bv.get("parent_correlations", {}),
            "max_parent_corr": bv.get("max_parent_corr", 0),
            "fast_pass": bv.get("fast_pass", {}),
            "production_score": fr["production_score"],
            "production_label": fr["prod_label"],
            "fast_pass_label": fr["fp_label"],
        }
        output["ranking"].append({
            "strategy": label,
            "production_score": fr["production_score"],
            "production_label": fr["prod_label"],
            "fast_pass_label": fr["fp_label"],
        })

    output_path = OUTPUT_DIR / "phase14_gold_mr_refinement_results.json"
    with open(output_path, "w") as f:
        json.dump(_clean_for_json(output), f, indent=2, default=str)

    print(f"\n  Results saved to: {output_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
