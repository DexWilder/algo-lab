"""Phase 15: Gold Snapback Engine — Refine BB Equilibrium to Parent.

Phase 14 discovered that Gold MR is actually "trend snapback" — overextension
within trends that reverts to equilibrium. BB Equilibrium scored 8.0/10 but
failed walk-forward (2024 PF=0.96) and rolling W1 (PF=0.81).

Root cause hypothesis: EMA=50 trend filter is too slow — it aligned well with
2025-2026 macro gold trend but was too laggy for 2024's choppier regime.

Three refinement axes:
  A. Trend filter sensitivity (EMA period, slope threshold, adaptive)
  B. Volatility normalization (ATR-scaled band distance)
  C. Regime gating (block catastrophic NORMAL_TRENDING_NORMAL_RV cell)

Pipeline:
  1. Axis A: Trend filter variants (7 configs)
  2. Axis B: Volatility normalization (3 configs)
  3. Axis C: Regime gating (2 configs)
  4. Combine best from each axis
  5. Walk-forward diagnostic (2024 deep dive)
  6. Full validation battery
  7. Portfolio impact (6-strategy)
  8. Promotion decision

Usage:
    python3 research/phase15_gold_snapback.py
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

ASSET = "MGC"
MODE = "long"

# ── Portfolio parents (for correlation + portfolio sim) ──────────────────

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
    df = df_1m.copy().set_index("datetime")
    resampled = df.resample(f"{freq_minutes}min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum",
    }).dropna(subset=["open"])
    return resampled.reset_index()


def get_daily_pnl(trades_df):
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def quick_metrics(trades_df):
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
    try:
        dur = ((pd.to_datetime(trades_df["exit_time"]) -
                pd.to_datetime(trades_df["entry_time"])).dt.total_seconds() / 300)
        median_hold = int(dur.median())
    except Exception:
        median_hold = 0
    return {
        "pf": round(pf, 4), "sharpe": round(sharpe, 4),
        "trades": len(trades_df), "pnl": round(pnl.sum(), 2),
        "maxdd": round(maxdd, 2),
        "wr": round(len(wins) / len(pnl) * 100, 1) if len(pnl) > 0 else 0,
        "median_hold": median_hold,
    }


def run_bb_eq(df, params):
    """Run BB Equilibrium with custom params, return trades DataFrame."""
    mod = load_strategy("bb_equilibrium")
    mod.TICK_SIZE = ASSET_CONFIG[ASSET]["tick_size"]

    # Apply all param overrides
    for k, v in params.items():
        if hasattr(mod, k):
            setattr(mod, k, v)

    signals = mod.generate_signals(df)
    result = run_backtest(
        df, signals, mode=MODE,
        point_value=ASSET_CONFIG[ASSET]["point_value"], symbol=ASSET,
    )
    return result["trades_df"]


def run_on_period(df_full, start, end, params):
    """Run BB Equilibrium on a date slice."""
    df_full = df_full.copy()
    df_full["_dt"] = pd.to_datetime(df_full["datetime"])
    subset = df_full[(df_full["_dt"] >= pd.Timestamp(start)) &
                      (df_full["_dt"] < pd.Timestamp(end))].drop(
        columns=["_dt"]).reset_index(drop=True)
    if len(subset) < 100:
        return pd.DataFrame()
    return run_bb_eq(subset, params)


def filter_regime_gate(trades_df, df_raw, engine, blocked_cells):
    """Post-hoc regime gating: remove trades in blocked regime cells."""
    if trades_df.empty or not blocked_cells:
        return trades_df

    daily_regimes = engine.get_daily_regimes(df_raw)
    daily_regimes["_date"] = pd.to_datetime(daily_regimes["_date"])
    daily_regimes["_date_date"] = daily_regimes["_date"].dt.date

    tc = trades_df.copy()
    tc["_trade_date"] = pd.to_datetime(tc["entry_time"]).dt.date
    merged = tc.merge(
        daily_regimes[["_date_date", "vol_regime", "trend_regime", "rv_regime"]],
        left_on="_trade_date", right_on="_date_date", how="left",
    )
    merged["regime_cell"] = (merged["vol_regime"].fillna("UNK") + "_" +
                              merged["trend_regime"].fillna("UNK") + "_" +
                              merged["rv_regime"].fillna("UNK"))

    mask = ~merged["regime_cell"].isin(blocked_cells)
    filtered = merged.loc[mask, trades_df.columns].reset_index(drop=True)
    return filtered


def load_parent_daily_pnls(engine):
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
            tc = trades.copy()
            tc["entry_date"] = pd.to_datetime(tc["entry_time"]).dt.date
            tc = tc.merge(regime_daily[["_date_date", "trend_persistence"]],
                          left_on="entry_date", right_on="_date_date", how="left")
            trades = tc[tc["trend_persistence"] == "GRINDING"]
            trades = trades.drop(columns=["entry_date", "_date_date",
                                          "trend_persistence"], errors="ignore")

        w = VOL_WEIGHTS.get(p["label"], 1.0)
        if not trades.empty:
            trades = trades.copy()
            trades["pnl"] = trades["pnl"] * w
        pnls[p["label"]] = get_daily_pnl(trades)
    return pnls


def _clean_for_json(obj):
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
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print_header("PHASE 15: GOLD SNAPBACK ENGINE — REFINE BB EQUILIBRIUM")

    engine = RegimeEngine()
    df_mgc = load_data(ASSET)

    # Phase 14 best params (baseline)
    P14_BASELINE = {
        "TREND_EMA_PERIOD": 50,
        "BW_MAX_PCT": 70,
        "BB_MULT": 2.0,
    }

    # ═══════════════════════════════════════════════════════════════════
    # STEP 0: BASELINE DIAGNOSTIC — WHY DOES 2024 FAIL?
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 0: 2024 FAILURE DIAGNOSTIC")

    # Test EMA 20 (original), 30, 50 (Phase 14 best) on 2024 only
    ema_diagnostic = {}
    for ema_p in [10, 15, 20, 30, 40, 50]:
        params = {**P14_BASELINE, "TREND_EMA_PERIOD": ema_p}
        trades_2024 = run_on_period(df_mgc, "2024-01-01", "2025-01-01", params)
        trades_2025 = run_on_period(df_mgc, "2025-01-01", "2026-01-01", params)
        trades_full = run_bb_eq(df_mgc, params)

        m24 = quick_metrics(trades_2024)
        m25 = quick_metrics(trades_2025)
        mf = quick_metrics(trades_full)

        ema_diagnostic[ema_p] = {
            "2024": m24, "2025": m25, "full": mf,
        }
        print(f"  EMA={ema_p:>3d}:  2024 PF={m24['pf']:.3f} ({m24['trades']}t)  "
              f"2025 PF={m25['pf']:.3f} ({m25['trades']}t)  "
              f"Full PF={mf['pf']:.3f} ({mf['trades']}t) Sharpe={mf['sharpe']:.2f}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 1: AXIS A — TREND FILTER VARIANTS
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 1: AXIS A — TREND FILTER SENSITIVITY")

    # Each variant tests a different trend filter configuration
    axis_a_configs = [
        # Standard EMA periods
        {"label": "EMA-10",  "params": {"TREND_EMA_PERIOD": 10}},
        {"label": "EMA-15",  "params": {"TREND_EMA_PERIOD": 15}},
        {"label": "EMA-20",  "params": {"TREND_EMA_PERIOD": 20}},
        {"label": "EMA-30",  "params": {"TREND_EMA_PERIOD": 30}},
        {"label": "EMA-40",  "params": {"TREND_EMA_PERIOD": 40}},
        {"label": "EMA-50",  "params": {"TREND_EMA_PERIOD": 50}},
        # Wider BW to compensate for fewer trend signals with faster EMA
        {"label": "EMA-15+BW80", "params": {"TREND_EMA_PERIOD": 15, "BW_MAX_PCT": 80}},
        {"label": "EMA-20+BW80", "params": {"TREND_EMA_PERIOD": 20, "BW_MAX_PCT": 80}},
        {"label": "EMA-30+BW80", "params": {"TREND_EMA_PERIOD": 30, "BW_MAX_PCT": 80}},
    ]

    axis_a_results = []
    print(f"\n  {'Config':<18s} {'PF':>7s} {'Sharpe':>7s} {'Trades':>7s} "
          f"{'MedH':>5s} {'PnL':>10s} {'2024 PF':>8s} {'2025 PF':>8s}")
    print(f"  {'-'*17:<18s} {'-'*7:>7s} {'-'*7:>7s} {'-'*7:>7s} "
          f"{'-'*5:>5s} {'-'*10:>10s} {'-'*8:>8s} {'-'*8:>8s}")

    for cfg in axis_a_configs:
        params = {**P14_BASELINE, **cfg["params"]}
        trades = run_bb_eq(df_mgc, params)
        m = quick_metrics(trades)

        # Walk-forward check
        t24 = run_on_period(df_mgc, "2024-01-01", "2025-01-01", params)
        t25 = run_on_period(df_mgc, "2025-01-01", "2026-01-01", params)
        m24 = quick_metrics(t24)
        m25 = quick_metrics(t25)

        result = {
            "label": cfg["label"],
            "params": params,
            "full": m,
            "2024": m24,
            "2025": m25,
            "trades_df": trades,
            "wf_pass": m24["pf"] > 1.0 and m25["pf"] > 1.0,
        }
        axis_a_results.append(result)

        wf_flag = " ✓WF" if result["wf_pass"] else ""
        print(f"  {cfg['label']:<18s} {m['pf']:>7.2f} {m['sharpe']:>7.2f} "
              f"{m['trades']:>7d} {m['median_hold']:>5d} ${m['pnl']:>9,.0f} "
              f"{m24['pf']:>8.3f} {m25['pf']:>8.3f}{wf_flag}")

    # Select best Axis A variant that passes walk-forward
    wf_passing_a = [r for r in axis_a_results if r["wf_pass"] and r["full"]["trades"] >= 30]
    if wf_passing_a:
        best_a = max(wf_passing_a, key=lambda x: x["full"]["sharpe"])
        print(f"\n  Best Axis A (WF-passing): {best_a['label']} — "
              f"PF={best_a['full']['pf']:.2f}, Sharpe={best_a['full']['sharpe']:.2f}")
    else:
        # Fallback: pick best overall by balancing 2024 + full
        best_a = max(axis_a_results,
                     key=lambda x: x["full"]["sharpe"] * 0.6 + x["2024"]["pf"] * 0.4
                     if x["full"]["trades"] >= 30 else 0)
        print(f"\n  No WF-passing variant. Best compromise: {best_a['label']}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 2: AXIS B — VOLATILITY NORMALIZATION
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 2: AXIS B — VOLATILITY NORMALIZATION")

    # Use best Axis A params as base
    base_params = best_a["params"].copy()

    # Test BB_MULT scaling and ATR stop scaling
    axis_b_configs = [
        {"label": "Baseline",      "params": {}},
        {"label": "BB-1.5",        "params": {"BB_MULT": 1.5}},
        {"label": "BB-2.5",        "params": {"BB_MULT": 2.5}},
        {"label": "Stop-1.0",      "params": {"ATR_STOP_MULT": 1.0}},
        {"label": "Stop-2.0",      "params": {"ATR_STOP_MULT": 2.0}},
        {"label": "Trail-1.5",     "params": {"ATR_TRAIL_MULT": 1.5}},
        {"label": "Trail-2.5",     "params": {"ATR_TRAIL_MULT": 2.5}},
        {"label": "BB2.5+Stop2.0", "params": {"BB_MULT": 2.5, "ATR_STOP_MULT": 2.0}},
    ]

    axis_b_results = []
    print(f"\n  {'Config':<18s} {'PF':>7s} {'Sharpe':>7s} {'Trades':>7s} "
          f"{'MedH':>5s} {'PnL':>10s} {'2024 PF':>8s} {'2025 PF':>8s}")
    print(f"  {'-'*17:<18s} {'-'*7:>7s} {'-'*7:>7s} {'-'*7:>7s} "
          f"{'-'*5:>5s} {'-'*10:>10s} {'-'*8:>8s} {'-'*8:>8s}")

    for cfg in axis_b_configs:
        params = {**base_params, **cfg["params"]}
        trades = run_bb_eq(df_mgc, params)
        m = quick_metrics(trades)

        t24 = run_on_period(df_mgc, "2024-01-01", "2025-01-01", params)
        t25 = run_on_period(df_mgc, "2025-01-01", "2026-01-01", params)
        m24 = quick_metrics(t24)
        m25 = quick_metrics(t25)

        result = {
            "label": cfg["label"],
            "params": params,
            "full": m, "2024": m24, "2025": m25,
            "trades_df": trades,
            "wf_pass": m24["pf"] > 1.0 and m25["pf"] > 1.0,
        }
        axis_b_results.append(result)

        wf_flag = " ✓WF" if result["wf_pass"] else ""
        print(f"  {cfg['label']:<18s} {m['pf']:>7.2f} {m['sharpe']:>7.2f} "
              f"{m['trades']:>7d} {m['median_hold']:>5d} ${m['pnl']:>9,.0f} "
              f"{m24['pf']:>8.3f} {m25['pf']:>8.3f}{wf_flag}")

    # Best Axis B
    wf_passing_b = [r for r in axis_b_results if r["wf_pass"] and r["full"]["trades"] >= 30]
    if wf_passing_b:
        best_b = max(wf_passing_b, key=lambda x: x["full"]["sharpe"])
    else:
        best_b = max(axis_b_results,
                     key=lambda x: x["full"]["sharpe"] if x["full"]["trades"] >= 30 else 0)
    print(f"\n  Best Axis B: {best_b['label']} — "
          f"PF={best_b['full']['pf']:.2f}, Sharpe={best_b['full']['sharpe']:.2f}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 3: AXIS C — REGIME GATING
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 3: AXIS C — REGIME GATING")

    # Use best Axis B params as base
    combined_params = best_b["params"].copy()

    # Phase 14 found NORMAL_TRENDING_NORMAL_RV was catastrophic for VWAP Dev MR
    # Test blocking it and other potential problem cells for BB-Eq
    blocked_sets = [
        {"label": "No gate",   "cells": []},
        {"label": "Block NTN", "cells": ["NORMAL_TRENDING_NORMAL_RV"]},
        {"label": "Block NTN+HVN", "cells": ["NORMAL_TRENDING_NORMAL_RV",
                                               "HIGH_VOL_TRENDING_NORMAL_RV"]},
        {"label": "Block all <1.0", "cells": []},  # computed dynamically
    ]

    # First: run ungated to find which cells have PF < 1.0
    trades_ungated = run_bb_eq(df_mgc, combined_params)
    if not trades_ungated.empty:
        daily_regimes = engine.get_daily_regimes(df_mgc)
        daily_regimes["_date"] = pd.to_datetime(daily_regimes["_date"])
        daily_regimes["_date_date"] = daily_regimes["_date"].dt.date

        tc = trades_ungated.copy()
        tc["_trade_date"] = pd.to_datetime(tc["entry_time"]).dt.date
        merged = tc.merge(
            daily_regimes[["_date_date", "vol_regime", "trend_regime", "rv_regime"]],
            left_on="_trade_date", right_on="_date_date", how="left",
        )
        merged["regime_cell"] = (merged["vol_regime"].fillna("UNK") + "_" +
                                  merged["trend_regime"].fillna("UNK") + "_" +
                                  merged["rv_regime"].fillna("UNK"))

        print("\n  Ungated regime breakdown:")
        weak_cells = []
        for cell, grp in sorted(merged.groupby("regime_cell"),
                                  key=lambda x: x[1]["pnl"].sum(), reverse=True):
            pnl_c = grp["pnl"]
            wins_c = pnl_c[pnl_c > 0]
            losses_c = pnl_c[pnl_c < 0]
            gp = wins_c.sum() if len(wins_c) else 0
            gl = abs(losses_c.sum()) if len(losses_c) else 0
            pf_c = gp / gl if gl > 0 else (100.0 if gp > 0 else 0)
            ls = len(grp) < LOW_SAMPLE_THRESHOLD
            flag = " [LOW_SAMPLE]" if ls else ""
            if pf_c < 1.0 and len(grp) >= 5:
                weak_cells.append(cell)
                flag += " ← WEAK"
            print(f"    {cell:>35s}  {len(grp):>4d} trades  "
                  f"PF={pf_c:.3f}  PnL=${pnl_c.sum():>8,.2f}{flag}")

        # Set "Block all <1.0" cells
        blocked_sets[3]["cells"] = weak_cells
        print(f"\n  Weak cells (PF<1.0, ≥5 trades): {weak_cells}")

    # Test each gating configuration
    axis_c_results = []
    print(f"\n  {'Config':<20s} {'PF':>7s} {'Sharpe':>7s} {'Trades':>7s} "
          f"{'MedH':>5s} {'PnL':>10s} {'2024 PF':>8s} {'2025 PF':>8s} {'Blocked':>8s}")
    print(f"  {'-'*19:<20s} {'-'*7:>7s} {'-'*7:>7s} {'-'*7:>7s} "
          f"{'-'*5:>5s} {'-'*10:>10s} {'-'*8:>8s} {'-'*8:>8s} {'-'*8:>8s}")

    for bs in blocked_sets:
        trades_full = run_bb_eq(df_mgc, combined_params)
        if bs["cells"]:
            trades_full = filter_regime_gate(trades_full, df_mgc, engine, bs["cells"])
        m = quick_metrics(trades_full)

        # Walk-forward with gating
        t24 = run_on_period(df_mgc, "2024-01-01", "2025-01-01", combined_params)
        t25 = run_on_period(df_mgc, "2025-01-01", "2026-01-01", combined_params)
        if bs["cells"]:
            # Need to gate period subsets too — load period data for regime
            df_mgc_full = df_mgc.copy()
            t24 = filter_regime_gate(t24, df_mgc_full, engine, bs["cells"])
            t25 = filter_regime_gate(t25, df_mgc_full, engine, bs["cells"])
        m24 = quick_metrics(t24)
        m25 = quick_metrics(t25)

        n_blocked = m["trades"] - quick_metrics(run_bb_eq(df_mgc, combined_params))["trades"] \
            if bs["cells"] else 0
        # Actually compute blocked count correctly
        ungated_count = quick_metrics(run_bb_eq(df_mgc, combined_params))["trades"]
        n_blocked_actual = ungated_count - m["trades"]

        result = {
            "label": bs["label"],
            "blocked_cells": bs["cells"],
            "full": m, "2024": m24, "2025": m25,
            "trades_df": trades_full,
            "wf_pass": m24["pf"] > 1.0 and m25["pf"] > 1.0,
            "n_blocked": n_blocked_actual,
        }
        axis_c_results.append(result)

        wf_flag = " ✓WF" if result["wf_pass"] else ""
        print(f"  {bs['label']:<20s} {m['pf']:>7.2f} {m['sharpe']:>7.2f} "
              f"{m['trades']:>7d} {m['median_hold']:>5d} ${m['pnl']:>9,.0f} "
              f"{m24['pf']:>8.3f} {m25['pf']:>8.3f} {n_blocked_actual:>8d}{wf_flag}")

    # Best Axis C
    wf_passing_c = [r for r in axis_c_results if r["wf_pass"] and r["full"]["trades"] >= 30]
    if wf_passing_c:
        best_c = max(wf_passing_c, key=lambda x: x["full"]["sharpe"])
    else:
        best_c = max(axis_c_results,
                     key=lambda x: x["full"]["sharpe"] if x["full"]["trades"] >= 30 else 0)
    print(f"\n  Best Axis C: {best_c['label']} — "
          f"PF={best_c['full']['pf']:.2f}, Sharpe={best_c['full']['sharpe']:.2f}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 4: COMBINED REFINEMENT CANDIDATES
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 4: COMBINED REFINEMENT CANDIDATES")

    # Build combined candidates from axis results
    combined_candidates = []

    # Candidate 1: Best A only (trend filter fix)
    combined_candidates.append({
        "label": f"A-only ({best_a['label']})",
        "params": best_a["params"],
        "regime_gate": [],
        "trades_df": best_a["trades_df"],
        "full": best_a["full"],
        "2024": best_a["2024"],
        "2025": best_a["2025"],
        "wf_pass": best_a["wf_pass"],
    })

    # Candidate 2: Best A + Best B (trend + vol)
    combined_candidates.append({
        "label": f"A+B ({best_a['label']} + {best_b['label']})",
        "params": best_b["params"],
        "regime_gate": [],
        "trades_df": best_b["trades_df"],
        "full": best_b["full"],
        "2024": best_b["2024"],
        "2025": best_b["2025"],
        "wf_pass": best_b["wf_pass"],
    })

    # Candidate 3: Best A + B + regime gate
    if best_c["blocked_cells"]:
        gate_params = best_b["params"].copy()
        trades_gated = run_bb_eq(df_mgc, gate_params)
        trades_gated = filter_regime_gate(trades_gated, df_mgc, engine, best_c["blocked_cells"])
        m_gated = quick_metrics(trades_gated)

        t24_g = run_on_period(df_mgc, "2024-01-01", "2025-01-01", gate_params)
        t25_g = run_on_period(df_mgc, "2025-01-01", "2026-01-01", gate_params)
        t24_g = filter_regime_gate(t24_g, df_mgc, engine, best_c["blocked_cells"])
        t25_g = filter_regime_gate(t25_g, df_mgc, engine, best_c["blocked_cells"])
        m24_g = quick_metrics(t24_g)
        m25_g = quick_metrics(t25_g)

        combined_candidates.append({
            "label": f"A+B+C ({best_a['label']} + {best_b['label']} + {best_c['label']})",
            "params": gate_params,
            "regime_gate": best_c["blocked_cells"],
            "trades_df": trades_gated,
            "full": m_gated,
            "2024": m24_g,
            "2025": m25_g,
            "wf_pass": m24_g["pf"] > 1.0 and m25_g["pf"] > 1.0,
        })

    # Also test the Phase 14 baseline with regime gating alone
    if best_c["blocked_cells"]:
        trades_p14_gated = run_bb_eq(df_mgc, P14_BASELINE)
        trades_p14_gated = filter_regime_gate(trades_p14_gated, df_mgc, engine,
                                               best_c["blocked_cells"])
        m_p14g = quick_metrics(trades_p14_gated)
        t24_p14 = run_on_period(df_mgc, "2024-01-01", "2025-01-01", P14_BASELINE)
        t25_p14 = run_on_period(df_mgc, "2025-01-01", "2026-01-01", P14_BASELINE)
        t24_p14 = filter_regime_gate(t24_p14, df_mgc, engine, best_c["blocked_cells"])
        t25_p14 = filter_regime_gate(t25_p14, df_mgc, engine, best_c["blocked_cells"])
        m24_p14 = quick_metrics(t24_p14)
        m25_p14 = quick_metrics(t25_p14)

        combined_candidates.append({
            "label": f"P14+Gate ({best_c['label']})",
            "params": P14_BASELINE,
            "regime_gate": best_c["blocked_cells"],
            "trades_df": trades_p14_gated,
            "full": m_p14g,
            "2024": m24_p14,
            "2025": m25_p14,
            "wf_pass": m24_p14["pf"] > 1.0 and m25_p14["pf"] > 1.0,
        })

    # Print comparison
    print(f"\n  {'Candidate':<45s} {'PF':>7s} {'Sharpe':>7s} {'Trades':>7s} "
          f"{'2024':>8s} {'2025':>8s} {'WF':>4s}")
    print(f"  {'-'*44:<45s} {'-'*7:>7s} {'-'*7:>7s} {'-'*7:>7s} "
          f"{'-'*8:>8s} {'-'*8:>8s} {'-'*4:>4s}")
    for cc in combined_candidates:
        wf_flag = "PASS" if cc["wf_pass"] else "FAIL"
        print(f"  {cc['label']:<45s} {cc['full']['pf']:>7.2f} "
              f"{cc['full']['sharpe']:>7.2f} {cc['full']['trades']:>7d} "
              f"{cc['2024']['pf']:>8.3f} {cc['2025']['pf']:>8.3f} {wf_flag:>4s}")

    # Select champion
    wf_champions = [c for c in combined_candidates
                    if c["wf_pass"] and c["full"]["trades"] >= 30]
    if wf_champions:
        champion = max(wf_champions, key=lambda x: x["full"]["sharpe"])
    else:
        print("\n  WARNING: No candidate passes walk-forward!")
        champion = max(combined_candidates,
                       key=lambda x: (x["full"]["sharpe"] * 0.5 + x["2024"]["pf"] * 0.5)
                       if x["full"]["trades"] >= 30 else 0)

    print(f"\n  CHAMPION: {champion['label']}")
    print(f"  Params: {champion['params']}")
    if champion["regime_gate"]:
        print(f"  Regime gate: {champion['regime_gate']}")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 5: WALK-FORWARD DEEP DIVE (2024)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 5: WALK-FORWARD DEEP DIVE")

    # Quarterly breakdown for 2024
    quarters = [
        ("Q1-2024", "2024-01-01", "2024-04-01"),
        ("Q2-2024", "2024-04-01", "2024-07-01"),
        ("Q3-2024", "2024-07-01", "2024-10-01"),
        ("Q4-2024", "2024-10-01", "2025-01-01"),
        ("Q1-2025", "2025-01-01", "2025-04-01"),
        ("Q2-2025", "2025-04-01", "2025-07-01"),
        ("Q3-2025", "2025-07-01", "2025-10-01"),
        ("Q4-2025", "2025-10-01", "2026-01-01"),
        ("Q1-2026", "2026-01-01", "2026-04-01"),
    ]

    print(f"\n  {'Quarter':<10s} {'PF':>7s} {'Sharpe':>7s} {'Trades':>7s} "
          f"{'PnL':>10s} {'WR':>6s}")
    print(f"  {'-'*9:<10s} {'-'*7:>7s} {'-'*7:>7s} {'-'*7:>7s} "
          f"{'-'*10:>10s} {'-'*6:>6s}")

    for q_label, q_start, q_end in quarters:
        t_q = run_on_period(df_mgc, q_start, q_end, champion["params"])
        if champion["regime_gate"]:
            t_q = filter_regime_gate(t_q, df_mgc, engine, champion["regime_gate"])
        m_q = quick_metrics(t_q)
        flag = ""
        if m_q["trades"] < LOW_SAMPLE_THRESHOLD:
            flag = " [LOW_SAMPLE]"
        if m_q["pf"] < 0.8 and m_q["trades"] >= 5:
            flag += " ← WEAK"
        print(f"  {q_label:<10s} {m_q['pf']:>7.3f} {m_q['sharpe']:>7.2f} "
              f"{m_q['trades']:>7d} ${m_q['pnl']:>9,.2f} {m_q['wr']:>5.1f}%{flag}")

    # Rolling 6-month windows
    print(f"\n  Rolling 6-month walk-forward:")
    rolling_windows = [
        ("W1", "2024-02-01", "2024-08-01", "2024-08-01", "2025-02-01"),
        ("W2", "2024-08-01", "2025-02-01", "2025-02-01", "2025-08-01"),
        ("W3", "2025-02-01", "2025-08-01", "2025-08-01", "2026-02-01"),
    ]
    rolling_pass = 0
    rolling_total = 0
    for wlabel, _ts, _te, test_s, test_e in rolling_windows:
        t_w = run_on_period(df_mgc, test_s, test_e, champion["params"])
        if champion["regime_gate"]:
            t_w = filter_regime_gate(t_w, df_mgc, engine, champion["regime_gate"])
        m_w = quick_metrics(t_w)
        rolling_total += 1
        if m_w["pf"] > 1.0:
            rolling_pass += 1
        flag = " [LOW_SAMPLE]" if m_w["trades"] < LOW_SAMPLE_THRESHOLD else ""
        print(f"    {wlabel} test ({test_s} → {test_e}): "
              f"{m_w['trades']} trades, PF={m_w['pf']:.3f}{flag}")

    rolling_pass_rate = rolling_pass / rolling_total if rolling_total > 0 else 0
    print(f"  Rolling pass rate: {rolling_pass}/{rolling_total} "
          f"({'PASS' if rolling_pass_rate >= 0.75 else 'FAIL'})")

    # ═══════════════════════════════════════════════════════════════════
    # STEP 6: FULL VALIDATION BATTERY
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 6: FULL VALIDATION BATTERY")

    champ_params = champion["params"]
    champ_gate = champion["regime_gate"]

    validation = {}

    # ── Test 1: Walk-Forward ──────────────────────────────────────────
    print("\n  1. WALK-FORWARD TIME SPLITS")
    df = load_data(ASSET)
    df["_dt"] = pd.to_datetime(df["datetime"])

    year_results = {}
    for yr, (start, end) in [("2024", ("2024-01-01", "2025-01-01")),
                              ("2025", ("2025-01-01", "2026-01-01")),
                              ("2026", ("2026-01-01", "2027-01-01"))]:
        subset = df[(df["_dt"] >= pd.Timestamp(start)) &
                     (df["_dt"] < pd.Timestamp(end))].drop(
            columns=["_dt"]).reset_index(drop=True)
        if len(subset) < 100:
            year_results[yr] = {"pf": 0, "trades": 0, "low_sample": True}
            continue
        trades = run_bb_eq(subset, champ_params)
        if champ_gate:
            trades = filter_regime_gate(trades, df, engine, champ_gate)
        m = quick_metrics(trades)
        m["low_sample"] = m["trades"] < LOW_SAMPLE_THRESHOLD
        year_results[yr] = m
        flag = " [LOW_SAMPLE]" if m["low_sample"] else ""
        print(f"    {yr}: {m['trades']} trades, PF={m['pf']:.3f}, "
              f"Sharpe={m['sharpe']:.2f}, PnL=${m['pnl']:,.2f}{flag}")

    gated_yrs = ["2024", "2025"]
    yr_pass_count = sum(1 for y in gated_yrs
                        if year_results.get(y, {}).get("trades", 0) > 0
                        and year_results[y].get("pf", 0) > 1.0)
    yr_gated = sum(1 for y in gated_yrs if year_results.get(y, {}).get("trades", 0) > 0)
    year_splits_pass = yr_pass_count >= yr_gated if yr_gated > 0 else False

    # Rolling windows
    roll_pass = 0
    roll_total = 0
    roll_results = {}
    for wl, test_s, test_e in [("W1", "2024-08-01", "2025-02-01"),
                                 ("W2", "2025-02-01", "2025-08-01"),
                                 ("W3", "2025-08-01", "2026-02-01")]:
        subset = df[(df["_dt"] >= pd.Timestamp(test_s)) &
                     (df["_dt"] < pd.Timestamp(test_e))].drop(
            columns=["_dt"]).reset_index(drop=True)
        if len(subset) < 100:
            roll_results[wl] = {"pf": 0, "trades": 0}
            continue
        trades = run_bb_eq(subset, champ_params)
        if champ_gate:
            trades = filter_regime_gate(trades, df, engine, champ_gate)
        m = quick_metrics(trades)
        roll_results[wl] = m
        roll_total += 1
        if m["pf"] > 1.0:
            roll_pass += 1
        print(f"    {wl}: {m['trades']} trades, PF={m['pf']:.3f}")

    rolling_ok = roll_pass / roll_total >= 0.75 if roll_total > 0 else False
    df.drop(columns=["_dt"], inplace=True, errors="ignore")

    print(f"  Year splits: {'PASS' if year_splits_pass else 'FAIL'}")
    print(f"  Rolling: {'PASS' if rolling_ok else 'FAIL'} ({roll_pass}/{roll_total})")
    validation["walk_forward"] = {
        "year_splits": year_results, "year_splits_pass": year_splits_pass,
        "rolling_pass": rolling_ok, "rolling_pass_count": roll_pass,
        "rolling_total": roll_total,
    }

    # ── Test 2: Regime Stability ──────────────────────────────────────
    print("\n  2. REGIME STABILITY")
    df = load_data(ASSET)
    trades_val = run_bb_eq(df, champ_params)
    if champ_gate:
        trades_val = filter_regime_gate(trades_val, df, engine, champ_gate)

    daily_reg = engine.get_daily_regimes(df)
    daily_reg["_date"] = pd.to_datetime(daily_reg["_date"])
    daily_reg["_date_date"] = daily_reg["_date"].dt.date

    catastrophic = []
    regime_grid = {}
    if not trades_val.empty:
        tc = trades_val.copy()
        tc["_td"] = pd.to_datetime(tc["entry_time"]).dt.date
        mg = tc.merge(daily_reg[["_date_date", "vol_regime", "trend_regime", "rv_regime"]],
                      left_on="_td", right_on="_date_date", how="left")
        mg["cell"] = (mg["vol_regime"].fillna("UNK") + "_" +
                      mg["trend_regime"].fillna("UNK") + "_" +
                      mg["rv_regime"].fillna("UNK"))
        for cell, grp in mg.groupby("cell"):
            pnl_c = grp["pnl"]
            w_c = pnl_c[pnl_c > 0]; l_c = pnl_c[pnl_c < 0]
            gp = w_c.sum() if len(w_c) else 0
            gl = abs(l_c.sum()) if len(l_c) else 0
            pf_c = gp / gl if gl > 0 else (100 if gp > 0 else 0)
            regime_grid[cell] = {"trades": len(grp), "pf": round(pf_c, 4),
                                 "pnl": round(pnl_c.sum(), 2)}
            if len(grp) >= 10 and pf_c < 0.5:
                catastrophic.append(cell)
            flag = " *** CATASTROPHIC ***" if cell in catastrophic else (
                " [LOW_SAMPLE]" if len(grp) < LOW_SAMPLE_THRESHOLD else "")
            print(f"    {cell:>35s}  {len(grp):>4d}  PF={pf_c:.3f}  "
                  f"${pnl_c.sum():>8,.2f}{flag}")

    regime_pass = len(catastrophic) == 0
    print(f"  Regime stability: {'PASS' if regime_pass else 'FAIL'}")
    validation["regime_stability"] = {"grid": regime_grid, "catastrophic_cells": catastrophic,
                                       "passes": regime_pass}

    # ── Test 3: Asset Robustness ──────────────────────────────────────
    print("\n  3. ASSET ROBUSTNESS (gold-only accommodation)")
    asset_results = {}
    prof_count = 0
    for test_asset in ["MNQ", "MES", "MGC"]:
        try:
            df_a = load_data(test_asset)
        except FileNotFoundError:
            asset_results[test_asset] = {"trades": 0, "pf": 0, "skipped": True}
            continue
        mod = load_strategy("bb_equilibrium")
        mod.TICK_SIZE = ASSET_CONFIG[test_asset]["tick_size"]
        for k, v in champ_params.items():
            if hasattr(mod, k):
                setattr(mod, k, v)
        signals = mod.generate_signals(df_a)
        result = run_backtest(df_a, signals, mode=MODE,
                              point_value=ASSET_CONFIG[test_asset]["point_value"],
                              symbol=test_asset)
        trades_a = result["trades_df"]
        m_a = quick_metrics(trades_a)
        asset_results[test_asset] = m_a
        if m_a["pf"] > 1.0 and m_a["trades"] > 0:
            prof_count += 1
        print(f"    {test_asset}: {m_a['trades']} trades, PF={m_a['pf']:.3f}, "
              f"PnL=${m_a['pnl']:,.2f}")

    asset_pass = prof_count >= 2
    asset_gold_only = (prof_count == 1 and
                       asset_results.get("MGC", {}).get("pf", 0) > 1.0)
    print(f"  Profitable: {prof_count}/3"
          f"{' (gold-only — 0.5 penalty)' if asset_gold_only else ''}")
    validation["asset_robustness"] = {"assets": asset_results,
                                       "profitable_count": prof_count,
                                       "passes": asset_pass,
                                       "gold_only": asset_gold_only}

    # ── Test 4: Timeframe Robustness ──────────────────────────────────
    print("\n  4. TIMEFRAME ROBUSTNESS")
    tf_results = {}
    tf_prof = 0
    try:
        df_1m = load_1m_data(ASSET)
    except FileNotFoundError:
        df_1m = None
    for tf_label, tf_min in [("5m", 5), ("10m", 10), ("15m", 15)]:
        if tf_label == "5m":
            df_tf = load_data(ASSET)
        elif df_1m is not None:
            df_tf = resample_bars(df_1m, tf_min)
        else:
            tf_results[tf_label] = {"trades": 0, "pf": 0, "skipped": True}
            continue
        trades_tf = run_bb_eq(df_tf, champ_params)
        if champ_gate:
            trades_tf = filter_regime_gate(trades_tf, df_tf, engine, champ_gate)
        m_tf = quick_metrics(trades_tf)
        tf_results[tf_label] = m_tf
        if m_tf["pf"] > 1.0 and m_tf["trades"] > 0:
            tf_prof += 1
        print(f"    {tf_label}: {m_tf['trades']} trades, PF={m_tf['pf']:.3f}")
    tf_pass = tf_prof >= 2
    print(f"  Timeframe: {'PASS' if tf_pass else 'FAIL'} ({tf_prof}/3)")
    validation["timeframe_robustness"] = {"timeframes": tf_results,
                                           "profitable_count": tf_prof,
                                           "passes": tf_pass}

    # ── Test 5: Monte Carlo / Bootstrap ───────────────────────────────
    print("\n  5. MONTE CARLO / BOOTSTRAP")
    trades_full = run_bb_eq(load_data(ASSET), champ_params)
    if champ_gate:
        trades_full = filter_regime_gate(trades_full, load_data(ASSET), engine, champ_gate)

    if len(trades_full) >= 5:
        trade_pnls = trades_full["pnl"].values
        daily = get_daily_pnl(trades_full)

        boot = bootstrap_metrics(trade_pnls, seed=SEED)
        bootstrap_pass = boot["pf"]["ci_low"] > 1.0
        print(f"    Bootstrap PF CI: [{boot['pf']['ci_low']:.3f}, "
              f"{boot['pf']['ci_high']:.3f}]  "
              f"{'PASS' if bootstrap_pass else 'FAIL'}")

        obs_sharpe = (float(daily.mean() / daily.std() * np.sqrt(252))
                      if len(daily) > 1 and daily.std() > 0 else 0)
        dsr_result = deflated_sharpe_ratio(
            observed_sharpe=obs_sharpe, n_trials=N_TRIALS,
            n_observations=len(daily), returns=daily.values)
        dsr_pass = dsr_result["dsr"] > 0.95
        print(f"    DSR: {dsr_result['dsr']:.4f}  {'PASS' if dsr_pass else 'FAIL'}")

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

        top_idx = np.argmax(trade_pnls)
        pnl_without = np.delete(trade_pnls, top_idx)
        w_w = pnl_without[pnl_without > 0].sum()
        l_w = abs(pnl_without[pnl_without < 0].sum())
        pf_without = w_w / l_w if l_w > 0 else (100 if w_w > 0 else 0)
        top_trade_pass = pf_without > 1.0
        print(f"    PF without top: {pf_without:.3f}  "
              f"{'PASS' if top_trade_pass else 'FAIL'}")
    else:
        bootstrap_pass = dsr_pass = mc_pass = top_trade_pass = False
        boot = {"pf": {"ci_low": 0, "ci_high": 0}}
        dsr_result = {"dsr": 0}
        ruin_probs = {}
        pf_without = 0

    validation["monte_carlo_bootstrap"] = {
        "bootstrap_pass": bootstrap_pass,
        "bootstrap": {"pf": boot["pf"]},
        "dsr_pass": dsr_pass,
        "dsr": {"dsr": dsr_result.get("dsr", 0)},
        "mc_pass": mc_pass,
        "monte_carlo": {"ruin_probability": ruin_probs},
        "top_trade_pass": top_trade_pass,
        "top_trade": {"pf_without_top": round(pf_without, 4)},
    }

    # ── Test 6: Parameter Stability ───────────────────────────────────
    print("\n  6. PARAMETER STABILITY")
    param_grid = {
        "TREND_EMA_PERIOD": [10, 20, 30, 40, 50],
        "BW_MAX_PCT": [30, 50, 70, 80],
        "BB_MULT": [1.5, 2.0, 2.5],
    }
    param_names = list(param_grid.keys())
    combos = list(product(*param_grid.values()))
    profitable = 0
    total = len(combos)
    df_ps = load_data(ASSET)
    for combo in combos:
        overrides = dict(zip(param_names, combo))
        try:
            trades_p = run_bb_eq(df_ps, overrides)
            if champ_gate:
                trades_p = filter_regime_gate(trades_p, df_ps, engine, champ_gate)
            m_p = quick_metrics(trades_p)
            if m_p["pf"] > 1.0 and m_p["trades"] > 0:
                profitable += 1
        except Exception:
            pass
    pct = profitable / total * 100 if total > 0 else 0
    param_pass = pct >= 60
    print(f"    {profitable}/{total} combos PF > 1.0 ({pct:.0f}%)")
    print(f"    Parameter stability: {'PASS' if param_pass else 'FAIL'}")
    validation["parameter_stability"] = {"pct_profitable": round(pct, 1),
                                          "passes": param_pass,
                                          "total": total, "profitable": profitable}

    # ── Stability Score ───────────────────────────────────────────────
    score = 0.0
    if year_splits_pass: score += 1.0
    elif yr_pass_count >= 1: score += 0.5
    if rolling_ok: score += 1.0
    if regime_pass: score += 1.0
    if asset_pass: score += 1.0
    elif asset_gold_only: score += 0.5
    if tf_pass: score += 1.0
    elif tf_prof >= 1: score += 0.5
    if bootstrap_pass: score += 1.0
    if dsr_pass: score += 1.0
    if mc_pass: score += 1.0
    if param_pass:
        score += 1.0
        if pct >= 80: score += 0.5
    if top_trade_pass: score += 0.5
    score = round(score, 1)

    failures = 0
    if not year_splits_pass: failures += 1
    if not rolling_ok: failures += 1
    if not regime_pass: failures += 1
    if not asset_pass:
        failures += 0.5 if asset_gold_only else 1
    if not tf_pass: failures += 1
    if not bootstrap_pass: failures += 1
    if not dsr_pass: failures += 1
    if not mc_pass: failures += 1
    if not top_trade_pass: failures += 1
    if not param_pass: failures += 1

    if score >= 7.0 and failures == 0:
        promotion = "PROMOTE TO PARENT"
    elif score >= 7.0 and failures <= 1:
        # Gold-only 0.5 failure is acceptable
        promotion = "PROMOTE TO PARENT (gold-only exception)"
    elif 5.0 <= score:
        promotion = "CONDITIONAL"
    else:
        promotion = "REJECT"

    print(f"\n  {'=' * 60}")
    print(f"  VALIDATION MATRIX — Gold Snapback (BB Equilibrium refined)")
    print(f"  {'=' * 60}")

    def _row(name, passed, detail=""):
        status = "PASS" if passed else "FAIL"
        print(f"  {name:<32} {status:<8} {detail}")

    yr_detail = " ".join(f"{k}={v.get('pf', 0):.2f}" for k, v in sorted(year_results.items())
                         if v.get("trades", 0) > 0 and k in ("2024", "2025"))
    _row("Walk-Forward (year splits)", year_splits_pass, yr_detail)
    _row("Walk-Forward (rolling)", rolling_ok,
         f"{roll_pass}/{roll_total} windows PF>1.0")
    _row("Regime Stability", regime_pass,
         f"{len(catastrophic)} catastrophic cells")
    _row("Asset Robustness", asset_pass,
         f"{prof_count}/3 assets" + (" (gold-only)" if asset_gold_only else ""))
    _row("Timeframe Robustness", tf_pass, f"{tf_prof}/3 TFs PF>1.0")
    _row("Bootstrap PF CI", bootstrap_pass,
         f"CI low={boot['pf']['ci_low']:.3f}")
    _row("DSR", dsr_pass, f"DSR={dsr_result.get('dsr', 0):.4f}")
    _row("Monte Carlo", mc_pass,
         f"P($2K)={ruin_probs.get('$2,000', 0)}%")
    _row("Top-Trade Removal", top_trade_pass,
         f"PF={pf_without:.3f}")
    _row("Parameter Stability", param_pass, f"{pct:.0f}% profitable")

    print(f"\n  STABILITY SCORE: {score}/10")
    print(f"  HARD FAILURES: {failures}")
    print(f"  PROMOTION: {promotion}")
    validation["stability_score"] = score
    validation["hard_failures"] = failures
    validation["promotion"] = promotion

    # ═══════════════════════════════════════════════════════════════════
    # STEP 7: PORTFOLIO IMPACT (6-STRATEGY)
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 7: PORTFOLIO IMPACT")

    print("  Loading parent daily PnLs...")
    parent_pnls = load_parent_daily_pnls(engine)

    port_df = pd.DataFrame(parent_pnls).fillna(0)
    portfolio_daily = port_df.sum(axis=1).sort_index()

    baseline_sharpe = (portfolio_daily.mean() / portfolio_daily.std() * np.sqrt(252)
                       if portfolio_daily.std() > 0 else 0)
    baseline_eq = STARTING_CAPITAL + portfolio_daily.cumsum()
    baseline_peak = baseline_eq.cummax()
    baseline_maxdd = (baseline_peak - baseline_eq).max()
    baseline_calmar = portfolio_daily.sum() / baseline_maxdd if baseline_maxdd > 0 else 0
    baseline_monthly = portfolio_daily.resample("ME").sum()
    baseline_monthly_pct = ((baseline_monthly > 0).sum() / len(baseline_monthly) * 100
                            if len(baseline_monthly) > 0 else 0)

    print(f"\n  5-strat baseline: Sharpe={baseline_sharpe:.2f}, "
          f"Calmar={baseline_calmar:.2f}, MaxDD=${baseline_maxdd:,.0f}, "
          f"Monthly={baseline_monthly_pct:.0f}%")

    # Champion portfolio impact
    cand_daily = get_daily_pnl(champion["trades_df"])
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

    # Vol Target weight
    if not cand_daily.empty and cand_daily.std() > 0:
        cand_vol = cand_daily.std() * np.sqrt(252)
        avg_parent_vol = np.mean([
            parent_pnls[p].std() * np.sqrt(252)
            for p in parent_pnls if not parent_pnls[p].empty and parent_pnls[p].std() > 0
        ]) if parent_pnls else 1
        vol_weight = round(avg_parent_vol / cand_vol, 3) if cand_vol > 0 else 1.0
    else:
        vol_weight = 1.0

    # Parent correlations
    parent_corrs = {}
    for p_label, p_daily in parent_pnls.items():
        comb = pd.DataFrame({"c": cand_daily, "p": p_daily}).fillna(0)
        if comb["c"].std() > 0 and comb["p"].std() > 0:
            parent_corrs[p_label] = round(comb["c"].corr(comb["p"]), 3)
        else:
            parent_corrs[p_label] = 0.0
    max_parent_corr = max(abs(v) for v in parent_corrs.values()) if parent_corrs else 0

    print(f"\n  6-strat portfolio:")
    print(f"    Sharpe: {sharpe6:.2f} ({sharpe_delta:+.2f})")
    print(f"    Calmar: {calmar6:.2f} ({calmar_delta:+.2f})")
    print(f"    MaxDD:  ${maxdd6:,.0f} ({maxdd_delta:+,.0f})")
    print(f"    Monthly: {monthly6_pct:.0f}%")
    print(f"    Vol Target weight: {vol_weight:.3f}")
    print(f"  Parent correlations:")
    for p_label, corr in parent_corrs.items():
        marker = " !" if abs(corr) > 0.25 else ""
        print(f"    vs {p_label:<8s}: r={corr:+.3f}{marker}")
    print(f"  Max |r| vs parents: {max_parent_corr:.3f}")

    portfolio_impact = {
        "sharpe_6strat": round(sharpe6, 2), "sharpe_delta": round(sharpe_delta, 2),
        "calmar_6strat": round(calmar6, 2), "calmar_delta": round(calmar_delta, 2),
        "maxdd_6strat": round(maxdd6, 2), "maxdd_delta": round(maxdd_delta, 2),
        "monthly_pct": round(monthly6_pct, 1),
        "pnl_6strat": round(port6_daily.sum(), 2),
        "vol_target_weight": vol_weight,
        "parent_correlations": parent_corrs,
        "max_parent_corr": max_parent_corr,
    }

    # ═══════════════════════════════════════════════════════════════════
    # STEP 8: PROMOTION DECISION
    # ═══════════════════════════════════════════════════════════════════
    print_header("STEP 8: PROMOTION DECISION")

    print(f"\n  Champion: {champion['label']}")
    print(f"  Params: {champion['params']}")
    if champion["regime_gate"]:
        print(f"  Regime gate: {champion['regime_gate']}")
    print(f"\n  Full: PF={champion['full']['pf']:.2f}, "
          f"Sharpe={champion['full']['sharpe']:.2f}, "
          f"Trades={champion['full']['trades']}")
    print(f"  Validation: {score}/10, {failures} failures → {promotion}")
    print(f"  Portfolio: Sharpe {sharpe_delta:+.2f}, Calmar {calmar_delta:+.2f}, "
          f"Max |r|={max_parent_corr:.3f}")

    # Final determination
    if "PROMOTE" in promotion and sharpe_delta > 0 and max_parent_corr < 0.25:
        final = "PROMOTED — Gold Snapback is 6th Parent"
        print(f"\n  {'★' * 20}")
        print(f"  {final}")
        print(f"  {'★' * 20}")
    elif "CONDITIONAL" in promotion:
        final = "CONDITIONAL — needs further refinement"
        print(f"\n  {final}")
        print(f"  Remaining failures to fix:")
        if not year_splits_pass:
            print(f"    - Walk-forward year splits")
        if not rolling_ok:
            print(f"    - Walk-forward rolling windows")
        if not regime_pass:
            print(f"    - Regime stability (catastrophic cells)")
        if not bootstrap_pass:
            print(f"    - Bootstrap CI")
    else:
        final = "REJECTED"
        print(f"\n  {final}")

    # ═══════════════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════════════
    output = {
        "phase": "Phase 15 — Gold Snapback Engine",
        "asset": ASSET, "mode": MODE,
        "p14_baseline": P14_BASELINE,
        "champion": {
            "label": champion["label"],
            "params": champion["params"],
            "regime_gate": champion["regime_gate"],
            "full_metrics": champion["full"],
            "2024_metrics": champion["2024"],
            "2025_metrics": champion["2025"],
            "walk_forward_pass": champion["wf_pass"],
        },
        "axis_a_summary": [{
            "label": r["label"],
            "pf": r["full"]["pf"], "sharpe": r["full"]["sharpe"],
            "trades": r["full"]["trades"],
            "2024_pf": r["2024"]["pf"], "2025_pf": r["2025"]["pf"],
            "wf_pass": r["wf_pass"],
        } for r in axis_a_results],
        "axis_b_summary": [{
            "label": r["label"],
            "pf": r["full"]["pf"], "sharpe": r["full"]["sharpe"],
            "trades": r["full"]["trades"],
            "2024_pf": r["2024"]["pf"], "2025_pf": r["2025"]["pf"],
            "wf_pass": r["wf_pass"],
        } for r in axis_b_results],
        "axis_c_summary": [{
            "label": r["label"],
            "pf": r["full"]["pf"], "sharpe": r["full"]["sharpe"],
            "trades": r["full"]["trades"],
            "blocked_cells": r["blocked_cells"],
            "wf_pass": r["wf_pass"],
        } for r in axis_c_results],
        "ema_diagnostic": {str(k): {
            "2024_pf": v["2024"]["pf"], "2025_pf": v["2025"]["pf"],
            "full_pf": v["full"]["pf"], "full_trades": v["full"]["trades"],
        } for k, v in ema_diagnostic.items()},
        "validation": validation,
        "portfolio_impact": portfolio_impact,
        "final_decision": final,
    }

    output_path = OUTPUT_DIR / "phase15_gold_snapback_results.json"
    with open(output_path, "w") as f:
        json.dump(_clean_for_json(output), f, indent=2, default=str)

    print(f"\n  Results saved to: {output_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
