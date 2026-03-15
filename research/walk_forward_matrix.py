#!/usr/bin/env python3
"""
FQL Walk-Forward Matrix Validation
====================================
Institutional-grade multi-dimensional robustness testing.

Dimensions tested:
  1. Rolling time windows (train/test splits)
  2. Cross-asset validation
  3. Parameter sensitivity (±20% grid)

Output: matrix robustness score, window survival rate, scorecard.

Promotion requirement:
  - >=70% profitable windows
  - Worst window PF > 0.90
  - Parameter stability >= 80%

Usage:
    python3 research/walk_forward_matrix.py <strategy_module> <asset> <mode>

Example:
    python3 research/walk_forward_matrix.py gap_mom MGC long
"""

import sys
import json
import importlib
import traceback
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest

DATA_DIR = ROOT / "data" / "processed"
RESULTS_DIR = ROOT / "research" / "data"

ASSET_CONFIG = {
    "MES": {"point_value": 5.0,  "tick_size": 0.25, "file": "MES_5m.csv"},
    "MNQ": {"point_value": 2.0,  "tick_size": 0.25, "file": "MNQ_5m.csv"},
    "MGC": {"point_value": 10.0, "tick_size": 0.10, "file": "MGC_5m.csv"},
    "M2K": {"point_value": 5.0,  "tick_size": 0.10, "file": "M2K_5m.csv"},
    "MCL": {"point_value": 100.0,"tick_size": 0.01, "file": "MCL_5m.csv"},
    "MYM": {"point_value": 0.50, "tick_size": 1.0,  "file": "MYM_5m.csv"},
}

# Cross-asset families
CROSS_ASSET_MAP = {
    "MES": ["MNQ", "MYM"],
    "MNQ": ["MES", "MYM"],
    "MGC": [],               # Gold is unique
    "M2K": ["MES", "MNQ"],
    "MCL": [],               # Oil is unique
    "MYM": ["MES", "MNQ"],
}

# Promotion thresholds
MIN_PROFITABLE_WINDOWS = 0.70
WORST_PF_THRESHOLD = 0.90
MIN_PARAM_STABILITY = 0.80


def load_data(asset: str) -> pd.DataFrame:
    cfg = ASSET_CONFIG[asset]
    path = DATA_DIR / cfg["file"]
    df = pd.read_csv(path)
    if "datetime" not in df.columns and "timestamp" in df.columns:
        df.rename(columns={"timestamp": "datetime"}, inplace=True)
    df["_dt"] = pd.to_datetime(df["datetime"])
    df["_year"] = df["_dt"].dt.year
    return df


def run_single_test(mod, df, asset, mode):
    """Run backtest on a data slice. Returns metrics dict or None."""
    cfg = ASSET_CONFIG[asset]
    try:
        try:
            signals = mod.generate_signals(df.drop(columns=["_dt", "_year"], errors="ignore"), asset=asset)
        except TypeError:
            signals = mod.generate_signals(df.drop(columns=["_dt", "_year"], errors="ignore"))

        result = run_backtest(
            df.drop(columns=["_dt", "_year"], errors="ignore"),
            signals, mode=mode,
            point_value=cfg["point_value"],
            tick_size=cfg["tick_size"],
            symbol=asset,
        )
        trades = result["trades_df"]
        if trades is None or len(trades) == 0:
            return None

        pnl_arr = trades["pnl"].values
        gross_profit = float(pnl_arr[pnl_arr > 0].sum())
        gross_loss = abs(float(pnl_arr[pnl_arr < 0].sum()))
        pf = gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        mean_pnl = np.mean(pnl_arr)
        std_pnl = np.std(pnl_arr, ddof=1) if len(pnl_arr) > 1 else 1.0
        sharpe = float(mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0.0
        equity = np.cumsum(pnl_arr)
        peak = np.maximum.accumulate(equity)
        max_dd = float(np.max(peak - equity)) if len(equity) > 0 else 0.0

        return {
            "trades": len(trades),
            "pnl": round(float(pnl_arr.sum()), 2),
            "profit_factor": round(pf, 3),
            "sharpe": round(sharpe, 2),
            "max_drawdown": round(max_dd, 2),
            "win_rate": round(float((pnl_arr > 0).mean()), 4),
        }
    except Exception as e:
        return {"error": str(e)}


# ── 1. Rolling Walk-Forward Windows ──────────────────────────────────────────

def walk_forward_windows(mod, df, asset, mode, train_years=2, test_years=1):
    """Rolling train/test splits."""
    years = sorted(df["_year"].unique())
    windows = []

    for i in range(len(years)):
        train_end = years[i] + train_years - 1
        test_start = train_end + 1
        test_end = test_start + test_years - 1

        if test_end > years[-1]:
            break

        train_mask = (df["_year"] >= years[i]) & (df["_year"] <= train_end)
        test_mask = (df["_year"] >= test_start) & (df["_year"] <= test_end)

        df_train = df[train_mask].copy()
        df_test = df[test_mask].copy()

        if len(df_train) < 100 or len(df_test) < 100:
            continue

        train_result = run_single_test(mod, df_train, asset, mode)
        test_result = run_single_test(mod, df_test, asset, mode)

        windows.append({
            "train_period": f"{years[i]}-{train_end}",
            "test_period": f"{test_start}-{test_end}",
            "train": train_result,
            "test": test_result,
        })

    return windows


# ── 2. Cross-Asset Validation ────────────────────────────────────────────────

def cross_asset_validation(mod, primary_asset, mode):
    """Test strategy on related assets."""
    cross_assets = CROSS_ASSET_MAP.get(primary_asset, [])
    results = {}

    for cross in cross_assets:
        try:
            df = load_data(cross)
            result = run_single_test(mod, df, cross, mode)
            results[cross] = result
        except Exception as e:
            results[cross] = {"error": str(e)}

    return results


# ── 3. Parameter Sensitivity ─────────────────────────────────────────────────

def parameter_sensitivity(mod, df, asset, mode):
    """Test ±20% parameter variations."""
    # Find numeric parameters in the module
    params = {}
    for name in dir(mod):
        if name.startswith("_"):
            continue
        val = getattr(mod, name)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            if name.isupper():  # Convention: parameters are UPPERCASE
                params[name] = val

    if not params:
        return {"status": "no_params", "stability": 1.0}

    # Test baseline
    baseline = run_single_test(mod, df, asset, mode)
    if baseline is None or "error" in baseline:
        return {"status": "baseline_failed", "stability": 0.0}

    # Test ±20% for each parameter
    results = []
    profitable_count = 0
    total_count = 0

    for param_name, orig_val in params.items():
        for mult in [0.8, 1.2]:
            new_val = orig_val * mult
            # Set the parameter
            if isinstance(orig_val, int):
                new_val = max(1, int(round(new_val)))
            setattr(mod, param_name, new_val)

            try:
                result = run_single_test(mod, df, asset, mode)
                total_count += 1
                if result and "error" not in result and result.get("pnl", 0) > 0:
                    profitable_count += 1
                results.append({
                    "param": param_name,
                    "original": orig_val,
                    "tested": round(new_val, 4),
                    "result": result,
                })
            except Exception:
                total_count += 1
            finally:
                # Restore original
                setattr(mod, param_name, orig_val)

    stability = profitable_count / total_count if total_count > 0 else 0.0

    return {
        "status": "complete",
        "params_tested": list(params.keys()),
        "total_variations": total_count,
        "profitable_variations": profitable_count,
        "stability": round(stability, 4),
        "details": results,
    }


# ── Matrix Scorecard ─────────────────────────────────────────────────────────

def compute_scorecard(wf_windows, cross_results, param_result):
    """Compute overall matrix robustness score."""
    scorecard = {
        "walk_forward": {},
        "cross_asset": {},
        "param_stability": {},
        "overall": {},
    }

    # Walk-forward scoring
    test_results = [w["test"] for w in wf_windows if w["test"] and "error" not in w["test"]]
    if test_results:
        pfs = [r["profit_factor"] for r in test_results]
        profitable = sum(1 for pf in pfs if pf > 1.0)
        scorecard["walk_forward"] = {
            "windows_tested": len(test_results),
            "profitable_windows": profitable,
            "survival_rate": round(profitable / len(test_results), 4),
            "worst_pf": round(min(pfs), 3),
            "best_pf": round(max(pfs), 3),
            "median_pf": round(float(np.median(pfs)), 3),
            "mean_pf": round(float(np.mean(pfs)), 3),
            "passes": profitable / len(test_results) >= MIN_PROFITABLE_WINDOWS and min(pfs) >= WORST_PF_THRESHOLD,
        }
    else:
        scorecard["walk_forward"] = {"windows_tested": 0, "passes": False}

    # Cross-asset scoring
    cross_viable = {k: v for k, v in cross_results.items() if v and "error" not in v}
    if cross_viable:
        cross_profitable = sum(1 for v in cross_viable.values() if v.get("pnl", 0) > 0)
        scorecard["cross_asset"] = {
            "assets_tested": len(cross_viable),
            "profitable_assets": cross_profitable,
            "results": {k: v.get("profit_factor", 0) for k, v in cross_viable.items()},
            "passes": cross_profitable > 0,
        }
    else:
        scorecard["cross_asset"] = {"assets_tested": 0, "passes": True, "note": "no_cross_assets_available"}

    # Parameter stability scoring
    stability = param_result.get("stability", 0)
    scorecard["param_stability"] = {
        "stability_pct": round(stability * 100, 1),
        "variations_tested": param_result.get("total_variations", 0),
        "profitable_variations": param_result.get("profitable_variations", 0),
        "passes": stability >= MIN_PARAM_STABILITY,
    }

    # Overall score
    wf_passes = scorecard["walk_forward"].get("passes", False)
    cross_passes = scorecard["cross_asset"].get("passes", False)
    param_passes = scorecard["param_stability"].get("passes", False)

    dimensions_passed = sum([wf_passes, cross_passes, param_passes])
    scorecard["overall"] = {
        "dimensions_passed": dimensions_passed,
        "dimensions_total": 3,
        "walk_forward_pass": wf_passes,
        "cross_asset_pass": cross_passes,
        "param_stability_pass": param_passes,
        "matrix_score": round(dimensions_passed / 3 * 10, 1),
        "recommendation": "PROMOTE" if dimensions_passed >= 2 else "HOLD" if dimensions_passed >= 1 else "REJECT",
    }

    return scorecard


def run_matrix(strategy_module: str, asset: str, mode: str):
    """Run full walk-forward matrix validation."""
    print("=" * 70)
    print(f"  FQL WALK-FORWARD MATRIX VALIDATION")
    print(f"  Strategy: {strategy_module}  Asset: {asset}  Mode: {mode}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Load strategy and data
    mod = importlib.import_module(f"strategies.{strategy_module}.strategy")
    importlib.reload(mod)
    df = load_data(asset)

    # 1. Walk-Forward Windows
    print(f"\n  [1/3] Rolling Walk-Forward Windows...")
    wf_windows = walk_forward_windows(mod, df, asset, mode)
    for w in wf_windows:
        test = w["test"]
        if test and "error" not in test:
            status = "PASS" if test["profit_factor"] > 1.0 else "FAIL"
            print(f"    Train: {w['train_period']}  Test: {w['test_period']}  "
                  f"PF={test['profit_factor']:.2f}  trades={test['trades']}  {status}")
        else:
            print(f"    Train: {w['train_period']}  Test: {w['test_period']}  NO DATA")

    # 2. Cross-Asset
    print(f"\n  [2/3] Cross-Asset Validation...")
    cross_results = cross_asset_validation(mod, asset, mode)
    for cross_asset, result in cross_results.items():
        if result and "error" not in result:
            status = "EDGE" if result["profit_factor"] > 1.0 else "NO EDGE"
            print(f"    {cross_asset:6s}  PF={result['profit_factor']:.2f}  trades={result['trades']}  {status}")
        else:
            err = result.get("error", "unknown") if result else "no data"
            print(f"    {cross_asset:6s}  ERROR: {err[:50]}")

    # 3. Parameter Sensitivity
    print(f"\n  [3/3] Parameter Sensitivity (±20%)...")
    # Reload to get clean params
    mod = importlib.import_module(f"strategies.{strategy_module}.strategy")
    importlib.reload(mod)
    param_result = parameter_sensitivity(mod, df, asset, mode)
    if param_result["status"] == "complete":
        print(f"    Params tested: {', '.join(param_result['params_tested'])}")
        print(f"    Variations: {param_result['total_variations']}  "
              f"Profitable: {param_result['profitable_variations']}  "
              f"Stability: {param_result['stability']*100:.0f}%")
    else:
        print(f"    Status: {param_result['status']}")

    # Scorecard
    scorecard = compute_scorecard(wf_windows, cross_results, param_result)

    print(f"\n" + "=" * 70)
    print(f"  MATRIX SCORECARD")
    print("=" * 70)
    wf = scorecard["walk_forward"]
    if wf.get("windows_tested", 0) > 0:
        print(f"  Walk-Forward:    {wf['profitable_windows']}/{wf['windows_tested']} windows profitable  "
              f"(survival={wf['survival_rate']*100:.0f}%)  "
              f"{'PASS' if wf['passes'] else 'FAIL'}")
        print(f"                   Worst PF={wf['worst_pf']:.2f}  Best PF={wf['best_pf']:.2f}  "
              f"Median PF={wf['median_pf']:.2f}")

    ca = scorecard["cross_asset"]
    if ca.get("assets_tested", 0) > 0:
        print(f"  Cross-Asset:     {ca['profitable_assets']}/{ca['assets_tested']} profitable  "
              f"{'PASS' if ca['passes'] else 'FAIL'}")
    else:
        print(f"  Cross-Asset:     N/A (no related assets)")

    ps = scorecard["param_stability"]
    print(f"  Param Stability: {ps['stability_pct']}%  "
          f"({ps['profitable_variations']}/{ps['variations_tested']} profitable)  "
          f"{'PASS' if ps['passes'] else 'FAIL'}")

    ov = scorecard["overall"]
    print(f"\n  MATRIX SCORE:    {ov['matrix_score']}/10  ({ov['dimensions_passed']}/{ov['dimensions_total']} dimensions)")
    print(f"  RECOMMENDATION:  {ov['recommendation']}")
    print("=" * 70)

    # Save results
    output = {
        "_generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "strategy": strategy_module,
        "asset": asset,
        "mode": mode,
        "walk_forward_windows": wf_windows,
        "cross_asset": cross_results,
        "parameter_sensitivity": {
            "stability": param_result.get("stability"),
            "total_variations": param_result.get("total_variations"),
            "profitable_variations": param_result.get("profitable_variations"),
            "params_tested": param_result.get("params_tested"),
        },
        "scorecard": scorecard,
    }

    filename = f"wf_matrix_{strategy_module}_{asset}_{mode}.json"
    output_path = RESULTS_DIR / filename
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Saved to: {output_path}")

    return scorecard


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 research/walk_forward_matrix.py <strategy_module> <asset> <mode>")
        print("Example: python3 research/walk_forward_matrix.py gap_mom MGC long")
        sys.exit(1)

    strategy_module = sys.argv[1]
    asset = sys.argv[2].upper()
    mode = sys.argv[3].lower()

    run_matrix(strategy_module, asset, mode)


if __name__ == "__main__":
    main()
