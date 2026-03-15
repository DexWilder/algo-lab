"""Full Validation Battery — generic strategy robustness testing.

Runs a 6-test validation battery on any strategy:
1. Walk-forward time splits (year splits + rolling windows)
2. Regime stability (18-cell composite grid)
3. Asset robustness (MNQ, MES, MGC)
4. Timeframe robustness (5m, 10m, 15m from 1m data)
5. Monte Carlo / Bootstrap (10K resamples, DSR, ruin, top-trade removal)
6. Parameter stability (+-20% perturbation grid)

Promotion criteria (ALL must pass):
- Walk-forward: both year splits PF > 1.0, >=75% rolling windows PF > 1.0
- Regime: no cell with >=10 trades has PF < 0.5
- Asset: >=2 of 3 assets PF > 1.0
- Timeframe: PF > 1.0 on >=2 of 3 timeframes
- Bootstrap PF 95% CI lower bound > 1.0
- DSR > 0.95
- Monte Carlo P(ruin at $2K DD) < 5%
- Top-trade removal PF > 1.0
- Parameter stability: >=60% of combos PF > 1.0

LOW_SAMPLE handling: slices with <15 trades are flagged but not counted as hard
failures in gates (exception: PF < 0.5 across multiple LOW_SAMPLE slices -> CAUTION).

Usage:
    python3 research/validation/run_validation_battery.py \\
        --strategy vwap_trend --asset MNQ --mode long

    python3 research/validation/run_validation_battery.py \\
        --strategy donchian_trend --asset MNQ --mode long \\
        --grinding --exit-variant profit_ladder
"""

import argparse
import importlib.util
import inspect
import json
import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.statistics import bootstrap_metrics, deflated_sharpe_ratio

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DATABENTO_DIR = PROJECT_ROOT / "data" / "databento"

STARTING_CAPITAL = 50_000.0
SEED = 42
N_SIMULATIONS = 10_000
N_TRIALS = 81  # standard lab assumption
LOW_SAMPLE_THRESHOLD = 15

RUIN_FLOORS = [1000, 2000, 3000, 4000, 5000]

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
    "M2K": {"point_value": 5.0, "tick_size": 0.10},
    "MCL": {"point_value": 100.0, "tick_size": 0.01},
    "ZN":  {"point_value": 1000.0, "tick_size": 0.015625},
    "ZB":  {"point_value": 1000.0, "tick_size": 0.03125},
}

# Asset families for robustness testing — test against similar markets
ASSET_FAMILIES = {
    "MES": ["MNQ", "MGC"],
    "MNQ": ["MES", "MGC"],
    "MGC": ["MES", "MNQ"],
    "M2K": ["MES", "MNQ"],   # other equity indices
    "MCL": ["MGC", "MES"],   # commodity + index
    "ZN":  ["ZB", "MES"],    # other bond + index
    "ZB":  ["ZN", "MES"],    # other bond + index
}

# Parameter grids per strategy
PARAM_GRIDS = {
    "vwap_trend": {
        "ATR_TRAIL_MULT": [2.0, 2.5, 3.0],
        "VWAP_PROXIMITY": [0.3, 0.5, 0.8],
        "CONSEC_CROSS": [1, 2, 3],
        "MIN_HOLD_BARS": [5, 10, 15],
    },
    "donchian_trend": {
        "CHANNEL_LEN": [20, 30, 40],
        "ATR_TRAIL_MULT": [2.5, 3.0, 3.5],
        "ATR_STOP_MULT": [2.0, 2.5, 3.0],
    },
    "bb_equilibrium": {
        "BB_LENGTH": [15, 20, 25],
        "BB_MULT": [1.5, 2.0, 2.5],
        "RSI_OVERSOLD": [30, 35, 40],
        "ATR_STOP_MULT": [1.0, 1.5, 2.0],
    },
    "xb_pb_ema_timestop": {
        "STOP_MULT": [1.0, 1.5, 2.0],
        "TRAIL_MULT": [1.5, 2.0, 2.5],
        "MAX_BARS": [20, 30, 40],
        "PB_PROXIMITY": [0.3, 0.5, 0.7],
    },
    "xb_orb_ema_ladder": {
        "STOP_MULT": [0.3, 0.5, 0.7],
        "TARGET_MULT": [3.0, 4.0, 5.0],
        "TRAIL_MULT": [2.0, 2.5, 3.0],
    },
    "orb_enhanced": {
        "OR_BARS": [5, 6, 7],
        "ATR_STOP_MULT": [1.2, 1.5, 1.8],
        "RANGE_MAX_MULT": [1.6, 2.0, 2.4],
        "VOL_CONFIRM_MULT": [1.0, 1.2, 1.4],
    },
    "vwap_mean_reversion": {
        "VWAP_OUTER_SIGMA": [1.6, 2.0, 2.4],
        "RSI_OVERSOLD": [25, 30, 35],
        "RSI_OVERBOUGHT": [65, 70, 75],
        "ATR_STOP_MULT": [1.2, 1.5, 1.8],
    },
    "momentum_ignition": {
        "VOL_SURGE_MULT": [1.5, 2.0, 2.5],
        "RSI_LONG_THRESH": [55, 60, 65],
        "ATR_STOP_MULT": [1.2, 1.5, 1.8],
        "ATR_TARGET_MULT": [3.0, 4.0, 5.0],
    },
    "close_vwap_reversion": {
        "VWAP_DEV_MULT": [1.6, 1.8, 2.0, 2.2, 2.4],
        "RSI_OVERSOLD": [25, 30, 35],
        "ATR_STOP_MULT": [1.2, 1.5, 1.8],
    },
    "orb_009": {
        "VOL_MULT": [1.2, 1.5, 1.8],
        "TP_MULT": [1.5, 2.0, 2.5],
        "BE_PCT": [0.4, 0.5, 0.6],
        "CANDLE_STRENGTH": [0.25, 0.30, 0.35],
    },
    "pb_trend": {
        "SL_ATR": [1.2, 1.5, 1.8],
        "TP_ATR": [1.8, 2.1, 2.5],
        "ADX_MIN": [12.0, 14.0, 16.0],
        "VOL_MULT": [0.8, 1.0, 1.2],
    },
}

# Profit Ladder rung variants for Donchian
LADDER_RUNGS = {
    "default": [(1.0, 0.25), (2.0, 1.0), (3.0, 2.0)],
    "tight":   [(0.75, 0.25), (1.5, 0.75), (2.5, 1.5)],
    "wide":    [(1.5, 0.5), (2.5, 1.25), (4.0, 2.5)],
}


# ── Helpers ─────────────────────────────────────────────────────────────────

def load_strategy(name):
    """Load a strategy module by name."""
    path = PROJECT_ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset, timeframe="5m"):
    """Load processed OHLCV data."""
    path = PROCESSED_DIR / f"{asset}_{timeframe}.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_1m_data(asset):
    """Load 1-minute data from databento directory."""
    path = DATABENTO_DIR / f"{asset}_1m.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def resample_bars(df_1m, freq_minutes):
    """Resample 1m data to Nm bars."""
    df = df_1m.copy()
    df = df.set_index("datetime")
    resampled = df.resample(f"{freq_minutes}min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }).dropna(subset=["open"])
    resampled = resampled.reset_index()
    return resampled


def generate_signals(mod, df, asset=None, mode=None):
    """Run generate_signals with optional asset/mode kwargs."""
    if hasattr(mod, "TICK_SIZE") and asset:
        mod.TICK_SIZE = ASSET_CONFIG.get(asset, {}).get("tick_size", 0.25)
    sig = inspect.signature(mod.generate_signals)
    kwargs = {}
    if "asset" in sig.parameters and asset:
        kwargs["asset"] = asset
    if "mode" in sig.parameters and mode:
        kwargs["mode"] = mode
    return mod.generate_signals(df, **kwargs)


def run_strategy(strategy_name, df, asset, mode, point_value,
                 exit_variant=None, grinding=False, ladder_rungs=None):
    """Run a strategy backtest with optional exit variant and GRINDING filter.

    Returns (trades_df, result_dict).
    """
    mod = load_strategy(strategy_name)
    acfg = ASSET_CONFIG.get(asset, ASSET_CONFIG["MNQ"])

    if exit_variant == "profit_ladder" and strategy_name == "donchian_trend":
        # Use exit_evolution's pipeline
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        # Patch tick size on the underlying module
        mod.TICK_SIZE = acfg["tick_size"]
        data = donchian_entries(df)
        rungs = ladder_rungs or LADDER_RUNGS["default"]
        signals_df = apply_profit_ladder(data, params={"rungs": rungs})
    else:
        signals_df = generate_signals(mod, df, asset=asset, mode=mode)

    result = run_backtest(
        df, signals_df,
        mode=mode,
        point_value=point_value,
        symbol=asset,
    )

    trades_df = result["trades_df"]

    # Apply GRINDING filter post-hoc if requested
    if grinding and not trades_df.empty:
        trades_df = _filter_grinding(trades_df, df)
        # Recalculate equity with filtered trades
        result["trades_df"] = trades_df

    return trades_df, result


def _filter_grinding(trades_df, df):
    """Filter trades to GRINDING days only."""
    engine = RegimeEngine()
    daily_regimes = engine.get_daily_regimes(df)

    grinding_dates = set(
        daily_regimes.loc[
            daily_regimes["trend_persistence"] == "GRINDING", "_date"
        ].values
    )

    trades = trades_df.copy()
    trades["_trade_date"] = pd.to_datetime(trades["entry_time"]).dt.date
    filtered = trades[trades["_trade_date"].isin(grinding_dates)].drop(
        columns=["_trade_date"]
    )
    return filtered.reset_index(drop=True)


def compute_metrics(trades_df):
    """Compute standard metrics from trades."""
    if trades_df.empty:
        return {"trades": 0, "pf": 0.0, "sharpe": 0.0, "pnl": 0.0,
                "maxdd": 0.0, "wr": 0.0}

    pnl = trades_df["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = wins.sum() if len(wins) else 0
    gross_loss = abs(losses.sum()) if len(losses) else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (
        100.0 if gross_profit > 0 else 0)

    trades_c = trades_df.copy()
    trades_c["_date"] = pd.to_datetime(trades_c["exit_time"]).dt.date
    daily = trades_c.groupby("_date")["pnl"].sum()
    if len(daily) > 1 and daily.std() > 0:
        sharpe = daily.mean() / daily.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    equity = STARTING_CAPITAL + np.cumsum(pnl.values)
    peak = np.maximum.accumulate(equity)
    maxdd = (peak - equity).max()

    return {
        "trades": len(trades_df),
        "pf": round(pf, 4),
        "sharpe": round(sharpe, 4),
        "pnl": round(pnl.sum(), 2),
        "maxdd": round(maxdd, 2),
        "wr": round(len(wins) / len(pnl) * 100, 1),
    }


def low_sample(n_trades):
    """Check if trade count is below LOW_SAMPLE threshold."""
    return n_trades < LOW_SAMPLE_THRESHOLD


def get_daily_pnl(trades_df):
    """Get daily PnL series from trades."""
    if trades_df.empty:
        return pd.Series(dtype=float)
    t = trades_df.copy()
    t["_date"] = pd.to_datetime(t["exit_time"]).dt.date
    daily = t.groupby("_date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


# ── Test 1: Walk-Forward Time Splits ───────────────────────────────────────

def test_walk_forward(strategy_name, asset, mode, point_value,
                      exit_variant=None, grinding=False):
    """Year splits + rolling 6-month windows."""
    print("\n  1. WALK-FORWARD TIME SPLITS")
    print("  " + "-" * 60)

    df = load_data(asset)

    # ── Year splits ──────────────────────────────────────────────────
    df["_dt"] = pd.to_datetime(df["datetime"])
    periods = {
        "2024": (pd.Timestamp("2024-01-01"), pd.Timestamp("2025-01-01")),
        "2025": (pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")),
        "2026": (pd.Timestamp("2026-01-01"), pd.Timestamp("2027-01-01")),
    }

    year_results = {}
    for label, (start, end) in periods.items():
        subset = df[(df["_dt"] >= start) & (df["_dt"] < end)].drop(
            columns=["_dt"]).copy().reset_index(drop=True)
        if len(subset) < 100:
            print(f"  {label}: insufficient data ({len(subset)} bars)")
            year_results[label] = {"trades": 0, "pf": 0, "sharpe": 0,
                                   "pnl": 0, "low_sample": True}
            continue

        trades, _ = run_strategy(strategy_name, subset, asset, mode,
                                 point_value, exit_variant, grinding)
        m = compute_metrics(trades)
        ls = low_sample(m["trades"])
        m["low_sample"] = ls
        year_results[label] = m
        flag = " [LOW_SAMPLE]" if ls else ""
        print(f"  {label}: {m['trades']} trades, PF={m['pf']:.3f}, "
              f"Sharpe={m['sharpe']:.2f}, PnL=${m['pnl']:,.2f}{flag}")

    # Gate: Both Period A and B must have PF > 1.0 (2026 reported only)
    gated_periods = ["2024", "2025"]
    year_pass_count = 0
    year_gated_count = 0
    for p in gated_periods:
        r = year_results.get(p, {})
        if r.get("trades", 0) == 0:
            continue
        year_gated_count += 1
        if r.get("low_sample"):
            # LOW_SAMPLE: report but don't count as failure
            if r.get("pf", 0) > 1.0:
                year_pass_count += 1
            continue
        if r.get("pf", 0) > 1.0:
            year_pass_count += 1

    if year_gated_count == 0:
        year_splits_pass = False
    else:
        # If all non-LOW_SAMPLE periods pass, it passes
        year_splits_pass = year_pass_count >= year_gated_count

    # ── Rolling windows ──────────────────────────────────────────────
    print()
    windows = [
        ("W1", "2024-02-01", "2024-08-01", "2024-08-01", "2025-02-01"),
        ("W2", "2024-08-01", "2025-02-01", "2025-02-01", "2025-08-01"),
        ("W3", "2025-02-01", "2025-08-01", "2025-08-01", "2026-02-01"),
    ]

    rolling_results = {}
    rolling_pass_count = 0
    rolling_total = 0
    for wlabel, _ts, _te, test_s, test_e in windows:
        test_start = pd.Timestamp(test_s)
        test_end = pd.Timestamp(test_e)
        subset = df[(df["_dt"] >= test_start) & (df["_dt"] < test_end)].drop(
            columns=["_dt"]).copy().reset_index(drop=True)

        if len(subset) < 100:
            print(f"  {wlabel} test: insufficient data")
            rolling_results[wlabel] = {"trades": 0, "pf": 0}
            continue

        trades, _ = run_strategy(strategy_name, subset, asset, mode,
                                 point_value, exit_variant, grinding)
        m = compute_metrics(trades)
        ls = low_sample(m["trades"])
        m["low_sample"] = ls
        rolling_results[wlabel] = m
        rolling_total += 1
        if m["pf"] > 1.0:
            rolling_pass_count += 1
        flag = " [LOW_SAMPLE]" if ls else ""
        print(f"  {wlabel} test: {m['trades']} trades, PF={m['pf']:.3f}, "
              f"PnL=${m['pnl']:,.2f}{flag}")

    rolling_pass = (rolling_pass_count / rolling_total >= 0.75
                    if rolling_total > 0 else False)

    df.drop(columns=["_dt"], inplace=True, errors="ignore")

    print(f"\n  Year splits pass: {'YES' if year_splits_pass else 'NO'}")
    print(f"  Rolling >=75% pass: {'YES' if rolling_pass else 'NO'} "
          f"({rolling_pass_count}/{rolling_total})")

    return {
        "year_splits": year_results,
        "year_splits_pass": year_splits_pass,
        "rolling_windows": rolling_results,
        "rolling_pass_count": rolling_pass_count,
        "rolling_total": rolling_total,
        "rolling_pass": rolling_pass,
    }


# ── Test 2: Regime Stability ──────────────────────────────────────────────

def test_regime_stability(strategy_name, asset, mode, point_value,
                          exit_variant=None, grinding=False):
    """Regime grid breakdown — no catastrophic cells."""
    print("\n  2. REGIME STABILITY")
    print("  " + "-" * 60)

    df = load_data(asset)
    engine = RegimeEngine()
    daily_regimes = engine.get_daily_regimes(df)

    trades, _ = run_strategy(strategy_name, df, asset, mode, point_value,
                             exit_variant, grinding)

    if trades.empty:
        print("  No trades.")
        return {"passes": False, "grid": {}}

    # Merge regime info onto trades
    trades_c = trades.copy()
    trades_c["_trade_date"] = pd.to_datetime(trades_c["entry_time"]).dt.date
    merged = trades_c.merge(daily_regimes, left_on="_trade_date",
                            right_on="_date", how="left")

    # Build composite key: vol_regime × trend_regime × rv_regime
    merged["regime_cell"] = (merged["vol_regime"].fillna("UNK") + "_" +
                             merged["trend_regime"].fillna("UNK") + "_" +
                             merged["rv_regime"].fillna("UNK"))

    grid = {}
    catastrophic_cells = []
    caution_low_sample = []

    for cell, group in merged.groupby("regime_cell"):
        pnl = group["pnl"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        gp = wins.sum() if len(wins) else 0
        gl = abs(losses.sum()) if len(losses) else 0
        pf = gp / gl if gl > 0 else (100.0 if gp > 0 else 0)
        cell_data = {
            "trades": len(group),
            "pf": round(pf, 4),
            "pnl": round(pnl.sum(), 2),
            "low_sample": low_sample(len(group)),
        }
        grid[cell] = cell_data

        if len(group) >= 10 and pf < 0.5:
            catastrophic_cells.append(cell)
        elif low_sample(len(group)) and pf < 0.5:
            caution_low_sample.append(cell)

    # GRINDING vs CHOPPY breakdown
    grinding_data = {}
    for persist, grp in merged.groupby("trend_persistence"):
        if persist not in ("GRINDING", "CHOPPY"):
            continue
        pnl = grp["pnl"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        gp = wins.sum() if len(wins) else 0
        gl = abs(losses.sum()) if len(losses) else 0
        pf = gp / gl if gl > 0 else (100.0 if gp > 0 else 0)
        grinding_data[persist] = {
            "trades": len(grp), "pf": round(pf, 4), "pnl": round(pnl.sum(), 2)
        }

    # Print grid
    for cell in sorted(grid.keys()):
        d = grid[cell]
        flag = ""
        if cell in catastrophic_cells:
            flag = " *** CATASTROPHIC ***"
        elif d["low_sample"]:
            flag = " [LOW_SAMPLE]"
        print(f"  {cell:>35s}  {d['trades']:>4} trades  PF={d['pf']:.3f}  "
              f"PnL=${d['pnl']:>8,.2f}{flag}")

    if grinding_data:
        print()
        for k, v in grinding_data.items():
            print(f"  {k}: {v['trades']} trades, PF={v['pf']:.3f}, "
                  f"PnL=${v['pnl']:,.2f}")

    passes = len(catastrophic_cells) == 0
    caution = len(caution_low_sample) >= 3  # Multiple LOW_SAMPLE failures

    print(f"\n  Catastrophic cells (>=10 trades, PF<0.5): "
          f"{len(catastrophic_cells)}")
    print(f"  Regime stability: {'PASS' if passes else 'FAIL'}"
          f"{' [CAUTION: multiple low-PF LOW_SAMPLE cells]' if caution else ''}")

    return {
        "grid": grid,
        "catastrophic_cells": catastrophic_cells,
        "grinding_breakdown": grinding_data,
        "caution_low_sample": caution,
        "passes": passes,
    }


# ── Test 3: Asset Robustness ─────────────────────────────────────────────

def test_asset_robustness(strategy_name, mode, point_value_primary,
                          exit_variant=None, grinding=False, primary_asset=None):
    """Run on related assets — at least 2 of 3 profitable."""
    print("\n  3. ASSET ROBUSTNESS")
    print("  " + "-" * 60)

    assets = ASSET_FAMILIES.get(primary_asset, ["MNQ", "MES", "MGC"])
    asset_results = {}
    profitable_count = 0

    for asset in assets:
        try:
            df = load_data(asset)
        except FileNotFoundError:
            print(f"  {asset}: data not found, skipping")
            asset_results[asset] = {"trades": 0, "pf": 0, "skipped": True}
            continue

        acfg = ASSET_CONFIG[asset]
        trades, _ = run_strategy(strategy_name, df, asset, mode,
                                 acfg["point_value"], exit_variant, grinding)
        m = compute_metrics(trades)
        ls = low_sample(m["trades"])
        m["low_sample"] = ls
        asset_results[asset] = m

        if m["pf"] > 1.0 and m["trades"] > 0:
            profitable_count += 1

        flag = " [LOW_SAMPLE]" if ls else ""
        print(f"  {asset}: {m['trades']} trades, PF={m['pf']:.3f}, "
              f"Sharpe={m['sharpe']:.2f}, PnL=${m['pnl']:,.2f}{flag}")

    passes = profitable_count >= 2
    print(f"\n  Profitable assets: {profitable_count}/3")
    print(f"  Asset robustness: {'PASS' if passes else 'FAIL'}")

    return {
        "assets": asset_results,
        "profitable_count": profitable_count,
        "passes": passes,
    }


# ── Test 4: Timeframe Robustness ─────────────────────────────────────────

def test_timeframe_robustness(strategy_name, asset, mode, point_value,
                              exit_variant=None, grinding=False):
    """Test on 5m (existing), 10m, 15m from 1m data."""
    print("\n  4. TIMEFRAME ROBUSTNESS")
    print("  " + "-" * 60)

    timeframes = {"5m": 5, "10m": 10, "15m": 15}
    tf_results = {}
    profitable_count = 0

    # Load 1m data for resampling
    try:
        df_1m = load_1m_data(asset)
    except FileNotFoundError:
        print(f"  1m data not found for {asset}, using 5m only")
        df_1m = None

    for tf_label, tf_min in timeframes.items():
        if tf_label == "5m":
            df_tf = load_data(asset)
        elif df_1m is not None:
            df_tf = resample_bars(df_1m, tf_min)
        else:
            print(f"  {tf_label}: skipped (no 1m data)")
            tf_results[tf_label] = {"trades": 0, "pf": 0, "skipped": True}
            continue

        trades, _ = run_strategy(strategy_name, df_tf, asset, mode,
                                 point_value, exit_variant, grinding)
        m = compute_metrics(trades)
        ls = low_sample(m["trades"])
        m["low_sample"] = ls
        tf_results[tf_label] = m

        if m["pf"] > 1.0 and m["trades"] > 0:
            profitable_count += 1

        flag = " [LOW_SAMPLE]" if ls else ""
        print(f"  {tf_label}: {m['trades']} trades, PF={m['pf']:.3f}, "
              f"Sharpe={m['sharpe']:.2f}, PnL=${m['pnl']:,.2f}{flag}")

    passes = profitable_count >= 2
    print(f"\n  Profitable timeframes: {profitable_count}/{len(timeframes)}")
    print(f"  Timeframe robustness: {'PASS' if passes else 'FAIL'}")

    return {
        "timeframes": tf_results,
        "profitable_count": profitable_count,
        "passes": passes,
    }


# ── Test 5: Monte Carlo / Bootstrap ──────────────────────────────────────

def test_monte_carlo_bootstrap(strategy_name, asset, mode, point_value,
                               exit_variant=None, grinding=False):
    """Bootstrap CI, DSR, Monte Carlo ruin, top-trade removal."""
    print("\n  5. MONTE CARLO / BOOTSTRAP")
    print("  " + "-" * 60)

    df = load_data(asset)
    trades, _ = run_strategy(strategy_name, df, asset, mode, point_value,
                             exit_variant, grinding)

    if trades.empty or len(trades) < 5:
        print("  Insufficient trades.")
        return {
            "bootstrap_pass": False, "dsr_pass": False,
            "mc_pass": False, "top_trade_pass": False,
        }

    trade_pnls = trades["pnl"].values
    daily = get_daily_pnl(trades)

    # ── Bootstrap ────────────────────────────────────────────────────
    print("  Bootstrap (10K resamples)...")
    boot = bootstrap_metrics(trade_pnls, seed=SEED)
    bootstrap_pass = boot["pf"]["ci_low"] > 1.0

    print(f"    PF point est: {boot['pf']['point_estimate']:.3f}")
    print(f"    PF 95% CI: [{boot['pf']['ci_low']:.3f}, "
          f"{boot['pf']['ci_high']:.3f}]")
    print(f"    CI low > 1.0: {'YES' if bootstrap_pass else 'NO'}")

    # ── DSR ──────────────────────────────────────────────────────────
    if len(daily) > 1 and daily.std() > 0:
        observed_sharpe = float(daily.mean() / daily.std() * np.sqrt(252))
    else:
        observed_sharpe = 0.0

    dsr_result = deflated_sharpe_ratio(
        observed_sharpe=observed_sharpe,
        n_trials=N_TRIALS,
        n_observations=len(daily),
        returns=daily.values,
    )
    dsr_pass = dsr_result["dsr"] > 0.95

    print(f"\n    Observed Sharpe: {dsr_result['observed_sharpe']:.4f}")
    print(f"    DSR: {dsr_result['dsr']:.4f}")
    print(f"    DSR > 0.95: {'YES' if dsr_pass else 'NO'}")

    # ── Monte Carlo ──────────────────────────────────────────────────
    print(f"\n    Monte Carlo ({N_SIMULATIONS:,} reshuffles)...")
    rng = np.random.default_rng(SEED)
    n_trades = len(trade_pnls)
    max_drawdowns = np.zeros(N_SIMULATIONS)

    for i in range(N_SIMULATIONS):
        shuffled = rng.permutation(trade_pnls)
        equity = STARTING_CAPITAL + np.cumsum(shuffled)
        peak = np.maximum.accumulate(equity)
        max_drawdowns[i] = (peak - equity).max()

    ruin_probs = {}
    for floor in RUIN_FLOORS:
        prob = (max_drawdowns >= floor).mean() * 100
        ruin_probs[f"${floor:,}"] = round(prob, 2)
        print(f"    P(ruin at ${floor:,}): {prob:.1f}%")

    mc_pass = ruin_probs.get("$2,000", 100) < 5

    # ── Top-trade removal ────────────────────────────────────────────
    top_idx = np.argmax(trade_pnls)
    top_trade_pnl = trade_pnls[top_idx]
    pnl_without = np.delete(trade_pnls, top_idx)
    wins_w = pnl_without[pnl_without > 0].sum()
    losses_w = abs(pnl_without[pnl_without < 0].sum())
    pf_without = wins_w / losses_w if losses_w > 0 else (
        100.0 if wins_w > 0 else 0)
    top_trade_pass = pf_without > 1.0

    top_pct = (top_trade_pnl / trade_pnls.sum() * 100
               if trade_pnls.sum() != 0 else 0)
    print(f"\n    Top trade: ${top_trade_pnl:.2f} "
          f"({top_pct:.1f}% of total PnL)")
    print(f"    PF without top: {pf_without:.3f}")
    print(f"    PF > 1.0 after removal: "
          f"{'YES' if top_trade_pass else 'NO'}")

    return {
        "bootstrap": {
            "pf": boot["pf"],
            "sharpe": boot["sharpe"],
            "max_dd": boot["max_dd"],
            "n_trades": boot["n_trades"],
            "passes": bootstrap_pass,
        },
        "dsr": {
            "dsr": dsr_result["dsr"],
            "observed_sharpe": dsr_result["observed_sharpe"],
            "expected_max_sharpe": dsr_result["expected_max_sharpe"],
            "passes": dsr_pass,
        },
        "monte_carlo": {
            "n_simulations": N_SIMULATIONS,
            "ruin_probability": ruin_probs,
            "median_maxdd": round(float(np.median(max_drawdowns)), 2),
            "p95_maxdd": round(float(np.percentile(max_drawdowns, 95)), 2),
            "passes": mc_pass,
        },
        "top_trade": {
            "top_trade_pnl": round(top_trade_pnl, 2),
            "top_trade_pct": round(top_pct, 1),
            "pf_without_top": round(pf_without, 4),
            "passes": top_trade_pass,
        },
        "bootstrap_pass": bootstrap_pass,
        "dsr_pass": dsr_pass,
        "mc_pass": mc_pass,
        "top_trade_pass": top_trade_pass,
    }


# ── Test 6: Parameter Stability ──────────────────────────────────────────

def test_parameter_stability(strategy_name, asset, mode, point_value,
                             exit_variant=None, grinding=False):
    """+-20% perturbation grid on key parameters."""
    print("\n  6. PARAMETER STABILITY")
    print("  " + "-" * 60)

    df = load_data(asset)
    param_grid = PARAM_GRIDS.get(strategy_name, {})

    if not param_grid:
        print(f"  No parameter grid defined for {strategy_name}")
        return {"passes": False, "pct_profitable": 0, "total_combinations": 0}

    # For Donchian + profit_ladder, also iterate over rung variants
    use_rungs = (exit_variant == "profit_ladder" and
                 strategy_name == "donchian_trend")

    param_names = list(param_grid.keys())
    combinations = list(product(*param_grid.values()))

    if use_rungs:
        rung_variants = list(LADDER_RUNGS.items())
    else:
        rung_variants = [("default", None)]

    profitable = 0
    total = 0
    best = {"pf": 0, "params": None}
    worst = {"pf": 999, "params": None}
    all_results = []

    for combo in combinations:
        for rung_name, rung_val in rung_variants:
            total += 1
            # Load fresh module
            mod = load_strategy(strategy_name)
            acfg = ASSET_CONFIG.get(asset, ASSET_CONFIG["MNQ"])
            if hasattr(mod, "TICK_SIZE"):
                mod.TICK_SIZE = acfg["tick_size"]

            # Set parameters
            for pname, pval in zip(param_names, combo):
                setattr(mod, pname, pval)

            try:
                if use_rungs:
                    from research.exit_evolution import donchian_entries, apply_profit_ladder
                    data = donchian_entries(df)
                    rungs = rung_val or LADDER_RUNGS["default"]
                    # Also set params on the underlying donchian entries
                    # (donchian_entries loads its own module, so we need to
                    # patch the module-level vars before calling)
                    dmod = data  # entries are already computed with defaults
                    # Re-compute entries with perturbed params
                    mod2 = load_strategy(strategy_name)
                    mod2.TICK_SIZE = acfg["tick_size"]
                    for pname, pval in zip(param_names, combo):
                        setattr(mod2, pname, pval)
                    original_signals = generate_signals(mod2, df.copy(), asset=asset, mode=mode)

                    # Rebuild entry data with new params
                    from research.exit_evolution import ATR_STOP_MULT as EE_STOP_MULT
                    sig_arr = original_signals["signal"].values
                    stop_arr_orig = original_signals["stop_price"].values
                    close_arr = df["close"].values
                    high_arr = df["high"].values
                    low_arr = df["low"].values

                    # Recompute ATR matching strategy
                    low_channel = df["low"].rolling(
                        window=combo[param_names.index("CHANNEL_LEN")]
                        if "CHANNEL_LEN" in param_names
                        else 30,
                        min_periods=1
                    ).min().shift(1)
                    prev_close = df["close"].shift(1)
                    tr = pd.concat([
                        df["high"] - df["low"],
                        (df["high"] - prev_close).abs(),
                        (low_channel - prev_close).abs(),
                    ], axis=1).max(axis=1)
                    atr_arr = tr.ewm(span=14, adjust=False).mean().values

                    dt = pd.to_datetime(df["datetime"])
                    time_str = dt.dt.strftime("%H:%M")
                    in_session = ((time_str >= "09:30") &
                                  (time_str < "15:45"))

                    entries = []
                    stop_mult = (combo[param_names.index("ATR_STOP_MULT")]
                                 if "ATR_STOP_MULT" in param_names
                                 else EE_STOP_MULT)
                    for idx in range(len(sig_arr)):
                        if sig_arr[idx] != 0:
                            ep = close_arr[idx]
                            ba = atr_arr[idx]
                            init_stop = stop_arr_orig[idx]
                            if np.isnan(init_stop):
                                if sig_arr[idx] == 1:
                                    init_stop = ep - ba * stop_mult
                                else:
                                    init_stop = ep + ba * stop_mult
                            entries.append({
                                "bar_idx": idx,
                                "direction": int(sig_arr[idx]),
                                "entry_price": ep,
                                "atr_at_entry": ba,
                                "initial_stop": init_stop,
                            })

                    data_dict = {
                        "entries": entries,
                        "original_signals": original_signals,
                        "atr": atr_arr,
                        "close": close_arr,
                        "high": high_arr,
                        "low": low_arr,
                        "time": time_str.values,
                        "dates": dt.dt.date.values,
                        "in_session": in_session.values,
                        "n": len(df),
                        "df": df.copy(),
                    }

                    # Apply profit ladder with perturbed trail mult
                    trail_mult = (combo[param_names.index("ATR_TRAIL_MULT")]
                                  if "ATR_TRAIL_MULT" in param_names
                                  else 3.0)
                    signals_df = apply_profit_ladder(
                        data_dict,
                        params={"rungs": rungs, "atr_trail_mult": trail_mult}
                    )
                else:
                    signals_df = generate_signals(mod, df.copy(), asset=asset, mode=mode)

                result = run_backtest(
                    df, signals_df,
                    mode=mode,
                    point_value=point_value,
                    symbol=asset,
                )
                trades_out = result["trades_df"]

                if grinding and not trades_out.empty:
                    trades_out = _filter_grinding(trades_out, df)

                m = compute_metrics(trades_out)

            except Exception as e:
                m = {"trades": 0, "pf": 0, "sharpe": 0, "pnl": 0,
                     "maxdd": 0, "wr": 0}

            params_dict = dict(zip(param_names, combo))
            if use_rungs:
                params_dict["rung_variant"] = rung_name
            all_results.append({**params_dict, **m})

            if m["pf"] > 1.0 and m["trades"] > 0:
                profitable += 1
            if m["pf"] > best["pf"] and m["trades"] > 0:
                best = {"pf": m["pf"], "params": params_dict.copy()}
            if m["trades"] > 0 and m["pf"] < worst["pf"]:
                worst = {"pf": m["pf"], "params": params_dict.copy()}

    pct = profitable / total * 100 if total > 0 else 0
    print(f"  Tested: {total} combinations")
    print(f"  Profitable (PF > 1.0): {profitable}/{total} ({pct:.0f}%)")
    if best["params"]:
        print(f"  Best PF: {best['pf']:.3f} ({best['params']})")
    if worst["params"]:
        print(f"  Worst PF: {worst['pf']:.3f} ({worst['params']})")

    passes = pct >= 60
    print(f"  >= 60% profitable: {'YES' if passes else 'NO'}")

    return {
        "total_combinations": total,
        "profitable": profitable,
        "pct_profitable": round(pct, 1),
        "passes": passes,
        "best": {"pf": round(best["pf"], 4),
                 "params": best["params"]},
        "worst": {"pf": round(worst["pf"], 4),
                  "params": worst["params"]},
    }


# ── Stability Score ──────────────────────────────────────────────────────

def compute_stability_score(results):
    """Compute 0-10 stability score from test results."""
    score = 0.0

    # Walk-forward year splits: +1 (both), +0.5 (one)
    wf = results.get("walk_forward", {})
    if wf.get("year_splits_pass"):
        score += 1.0
    else:
        # Check if at least one year split passes
        yr = wf.get("year_splits", {})
        passes = sum(1 for k, v in yr.items()
                     if k in ("2024", "2025") and v.get("pf", 0) > 1.0
                     and v.get("trades", 0) > 0)
        if passes >= 1:
            score += 0.5

    # Walk-forward rolling >=75%: +1
    if wf.get("rolling_pass"):
        score += 1.0

    # Regime stability: +1
    if results.get("regime_stability", {}).get("passes"):
        score += 1.0

    # Asset robustness: +1 (>=2), +0.5 (1)
    ar = results.get("asset_robustness", {})
    pc = ar.get("profitable_count", 0)
    if pc >= 2:
        score += 1.0
    elif pc >= 1:
        score += 0.5

    # Timeframe robustness: +1 (>=2), +0.5 (1)
    tr = results.get("timeframe_robustness", {})
    tpc = tr.get("profitable_count", 0)
    if tpc >= 2:
        score += 1.0
    elif tpc >= 1:
        score += 0.5

    # Bootstrap PF CI > 1.0: +1
    mc = results.get("monte_carlo_bootstrap", {})
    if mc.get("bootstrap_pass"):
        score += 1.0

    # DSR > 0.95: +1
    if mc.get("dsr_pass"):
        score += 1.0

    # Monte Carlo P(ruin $2K) < 5%: +1
    if mc.get("mc_pass"):
        score += 1.0

    # Parameter stability: +1 (>=60%), +0.5 bonus if >=80%
    ps = results.get("parameter_stability", {})
    pct = ps.get("pct_profitable", 0)
    if pct >= 60:
        score += 1.0
        if pct >= 80:
            score += 0.5

    # Top-trade removal PF > 1.0: +0.5
    if mc.get("top_trade_pass"):
        score += 0.5

    return round(score, 1)


def count_hard_failures(results):
    """Count number of hard gate failures."""
    failures = 0
    wf = results.get("walk_forward", {})
    if not wf.get("year_splits_pass"):
        failures += 1
    if not wf.get("rolling_pass"):
        failures += 1
    if not results.get("regime_stability", {}).get("passes"):
        failures += 1
    if not results.get("asset_robustness", {}).get("passes"):
        failures += 1
    if not results.get("timeframe_robustness", {}).get("passes"):
        failures += 1
    mc = results.get("monte_carlo_bootstrap", {})
    if not mc.get("bootstrap_pass"):
        failures += 1
    if not mc.get("dsr_pass"):
        failures += 1
    if not mc.get("mc_pass"):
        failures += 1
    if not mc.get("top_trade_pass"):
        failures += 1
    if not results.get("parameter_stability", {}).get("passes"):
        failures += 1
    return failures


def build_deployment_summary(results, strategy_name, asset, mode):
    """Build actionable deployment guidance from results."""
    summary = {"strategy": strategy_name, "primary_asset": asset,
               "primary_mode": mode}

    # Best/worst asset
    ar = results.get("asset_robustness", {}).get("assets", {})
    if ar:
        valid = {k: v for k, v in ar.items()
                 if v.get("trades", 0) > 0 and not v.get("skipped")}
        if valid:
            best_asset = max(valid.items(), key=lambda x: x[1].get("pf", 0))
            worst_asset = min(valid.items(), key=lambda x: x[1].get("pf", 0))
            summary["strongest_asset"] = (
                f"{best_asset[0]} (PF={best_asset[1]['pf']:.2f}, "
                f"{best_asset[1]['trades']} trades)")
            summary["weakest_asset"] = (
                f"{worst_asset[0]} (PF={worst_asset[1]['pf']:.2f}, "
                f"{worst_asset[1]['trades']} trades)")

    # Best/worst timeframe
    tr = results.get("timeframe_robustness", {}).get("timeframes", {})
    if tr:
        valid = {k: v for k, v in tr.items()
                 if v.get("trades", 0) > 0 and not v.get("skipped")}
        if valid:
            best_tf = max(valid.items(), key=lambda x: x[1].get("pf", 0))
            worst_tf = min(valid.items(), key=lambda x: x[1].get("pf", 0))
            summary["strongest_timeframe"] = (
                f"{best_tf[0]} (PF={best_tf[1]['pf']:.2f})")
            summary["weakest_timeframe"] = (
                f"{worst_tf[0]} (PF={worst_tf[1]['pf']:.2f})")

    # Best/worst regimes
    grid = results.get("regime_stability", {}).get("grid", {})
    if grid:
        valid = {k: v for k, v in grid.items() if v.get("trades", 0) >= 5}
        if valid:
            sorted_cells = sorted(valid.items(),
                                  key=lambda x: x[1].get("pf", 0),
                                  reverse=True)
            best_regimes = [c[0] for c in sorted_cells[:3] if c[1]["pf"] > 1.0]
            avoid_regimes = [c[0] for c in sorted_cells[-3:]
                             if c[1]["pf"] < 1.0]
            summary["best_regimes"] = best_regimes
            summary["avoid_regimes"] = avoid_regimes

    summary["recommended_profile"] = f"{asset} 5m {mode}, regime-gated"
    return summary


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Full Validation Battery — generic strategy robustness")
    parser.add_argument("--strategy", required=True,
                        help="Strategy name (e.g. vwap_trend, donchian_trend)")
    parser.add_argument("--asset", default="MNQ",
                        help="Primary asset (default: MNQ)")
    parser.add_argument("--mode", default="long",
                        help="Trade mode: long, short, both (default: long)")
    parser.add_argument("--exit-variant", default=None,
                        help="Exit variant (e.g. profit_ladder)")
    parser.add_argument("--grinding", action="store_true",
                        help="Filter trades to GRINDING days only")
    args = parser.parse_args()

    strategy = args.strategy
    asset = args.asset.upper()
    mode = args.mode
    exit_variant = args.exit_variant
    grinding = args.grinding
    acfg = ASSET_CONFIG.get(asset, ASSET_CONFIG["MNQ"])
    point_value = acfg["point_value"]

    label = f"{strategy} {asset}-{mode.capitalize()}"
    if exit_variant:
        label += f" [{exit_variant}]"
    if grinding:
        label += " [GRINDING]"

    print("=" * 70)
    print(f"  FULL VALIDATION BATTERY — {label}")
    print("=" * 70)

    # ── Baseline sanity check ────────────────────────────────────────
    print("\n  BASELINE SANITY CHECK")
    print("  " + "-" * 60)
    df_base = load_data(asset)
    trades_base, _ = run_strategy(strategy, df_base, asset, mode,
                                  point_value, exit_variant, grinding)
    m_base = compute_metrics(trades_base)
    print(f"  {m_base['trades']} trades, PF={m_base['pf']:.3f}, "
          f"Sharpe={m_base['sharpe']:.2f}, PnL=${m_base['pnl']:,.2f}, "
          f"MaxDD=${m_base['maxdd']:,.2f}")

    results = {"baseline": m_base}

    # ── Run all 6 tests ──────────────────────────────────────────────
    results["walk_forward"] = test_walk_forward(
        strategy, asset, mode, point_value, exit_variant, grinding)

    results["regime_stability"] = test_regime_stability(
        strategy, asset, mode, point_value, exit_variant, grinding)

    results["asset_robustness"] = test_asset_robustness(
        strategy, mode, point_value, exit_variant, grinding,
        primary_asset=asset)

    results["timeframe_robustness"] = test_timeframe_robustness(
        strategy, asset, mode, point_value, exit_variant, grinding)

    results["monte_carlo_bootstrap"] = test_monte_carlo_bootstrap(
        strategy, asset, mode, point_value, exit_variant, grinding)

    results["parameter_stability"] = test_parameter_stability(
        strategy, asset, mode, point_value, exit_variant, grinding)

    # ── Stability Score + Promotion ──────────────────────────────────
    score = compute_stability_score(results)
    failures = count_hard_failures(results)
    results["stability_score"] = score
    results["hard_failures"] = failures

    if score >= 7.0 and failures == 0:
        promotion = "PROMOTE TO PARENT STRATEGY"
    elif 5.0 <= score < 7.0 or (1 <= failures <= 2):
        promotion = "CONDITIONAL - REVIEW NEEDED"
    else:
        promotion = "REJECT - NOT READY"
    results["promotion"] = promotion

    # ── Deployment Summary ───────────────────────────────────────────
    deployment = build_deployment_summary(results, strategy, asset, mode)
    results["deployment_summary"] = deployment

    # ── Print Validation Matrix ──────────────────────────────────────
    wf = results["walk_forward"]
    rs = results["regime_stability"]
    ar = results["asset_robustness"]
    tr = results["timeframe_robustness"]
    mc = results["monte_carlo_bootstrap"]
    ps = results["parameter_stability"]

    # Year split details
    yr = wf.get("year_splits", {})
    yr_detail = " ".join(
        f"{k}={v.get('pf', 0):.2f}" for k, v in sorted(yr.items())
        if v.get("trades", 0) > 0 and k in ("2024", "2025"))

    # Rolling detail
    roll_detail = (f"{wf.get('rolling_pass_count', 0)}/"
                   f"{wf.get('rolling_total', 0)} windows PF>1.0")

    print(f"\n{'=' * 70}")
    print(f"  VALIDATION MATRIX - {label}")
    print(f"{'=' * 70}")
    print(f"  {'Test':<32} {'Result':<8} {'Details'}")
    print(f"  {'-'*32} {'-'*8} {'-'*28}")

    def _row(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        print(f"  {name:<32} {status:<8} {detail}")

    _row("Walk-Forward (year splits)",
         wf.get("year_splits_pass"), yr_detail)
    _row("Walk-Forward (rolling)",
         wf.get("rolling_pass"), roll_detail)
    _row("Regime Stability",
         rs.get("passes"),
         f"{len(rs.get('catastrophic_cells', []))} catastrophic cells")
    _row("Asset Robustness",
         ar.get("passes"),
         f"{ar.get('profitable_count', 0)}/3 assets PF>1.0")
    _row("Timeframe Robustness",
         tr.get("passes"),
         f"{tr.get('profitable_count', 0)}/3 TFs PF>1.0")
    _row("Bootstrap PF CI",
         mc.get("bootstrap_pass"),
         f"CI low={mc.get('bootstrap', {}).get('pf', {}).get('ci_low', 0):.3f}")
    _row("DSR",
         mc.get("dsr_pass"),
         f"DSR={mc.get('dsr', {}).get('dsr', 0):.4f}")
    _row("Monte Carlo",
         mc.get("mc_pass"),
         f"P($2K)={mc.get('monte_carlo', {}).get('ruin_probability', {}).get('$2,000', 0)}%")
    _row("Top-Trade Removal",
         mc.get("top_trade_pass"),
         f"PF={mc.get('top_trade', {}).get('pf_without_top', 0):.3f} after removal")
    _row("Parameter Stability",
         ps.get("passes"),
         f"{ps.get('pct_profitable', 0):.0f}% profitable")

    print(f"\n  STABILITY SCORE: {score}/10")
    print(f"  HARD FAILURES: {failures}")
    print(f"  PROMOTION: {promotion}")

    # ── Deployment Summary ───────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"  DEPLOYMENT SUMMARY - {strategy}")
    print(f"{'=' * 70}")
    for k, v in deployment.items():
        if k in ("strategy",):
            continue
        label_k = k.replace("_", " ").title()
        if isinstance(v, list):
            v = ", ".join(v) if v else "none"
        print(f"  {label_k + ':':<24} {v}")

    # ── Save JSON ────────────────────────────────────────────────────
    out_name = f"{strategy}_{asset}_{mode}_validation.json"
    out_path = OUTPUT_DIR / out_name

    # Clean non-serializable data
    def _clean(obj):
        if isinstance(obj, dict):
            return {k: _clean(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean(v) for v in obj]
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return round(float(obj), 6)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj

    with open(out_path, "w") as f:
        json.dump(_clean(results), f, indent=2, default=str)

    print(f"\n  Saved to: {out_path}")
    print(f"{'=' * 70}")

    return results


if __name__ == "__main__":
    main()
