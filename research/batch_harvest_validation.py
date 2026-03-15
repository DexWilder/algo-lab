#!/usr/bin/env python3
"""
FQL Batch Harvest Validation
=============================
Tests all harvest candidates across assets and directions.
Outputs results to research/data/harvest_results.json and updates the strategy registry.

Usage:
    python3 research/batch_harvest_validation.py
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
RESULTS_PATH = ROOT / "research" / "data" / "harvest_results.json"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"

# ── Asset configs ──────────────────────────────────────────────────────────────

ASSET_CONFIG = {
    "MES": {"point_value": 5.0,  "tick_size": 0.25, "file": "MES_5m.csv"},
    "MNQ": {"point_value": 2.0,  "tick_size": 0.25, "file": "MNQ_5m.csv"},
    "MGC": {"point_value": 10.0, "tick_size": 0.10, "file": "MGC_5m.csv"},
    "M2K": {"point_value": 5.0,  "tick_size": 0.10, "file": "M2K_5m.csv"},
    "MCL": {"point_value": 100.0,"tick_size": 0.01, "file": "MCL_5m.csv"},
    "MYM": {"point_value": 0.50, "tick_size": 1.0,  "file": "MYM_5m.csv"},
}

# ── Candidates to test ────────────────────────────────────────────────────────
# (strategy_module, display_name, assets_to_test, modes_to_test)

CANDIDATES = [
    ("session_vwap_fade",      "SessionVWAPFade",    ["MES", "MNQ", "MGC", "M2K", "MCL"], ["long", "short"]),
    ("session_reversion_gold", "SessionRevGold",     ["MGC"],                               ["long", "short"]),
    ("rvwap_mr",               "RVWAP-MR",           ["MES", "MNQ", "MGC", "M2K", "MCL"], ["long", "short"]),
    ("vix_channel",            "VIXChannel",         ["MES", "MNQ", "M2K"],                ["long", "short"]),
    ("orion_vol",              "ORION-VolBreakout",  ["MES", "MNQ", "M2K"],                ["long", "short"]),
    ("bbkc_squeeze",           "BBKC-Squeeze",       ["MES", "MNQ", "MGC", "M2K", "MCL"], ["long", "short"]),
    ("close_liquidity_sweep",  "CloseLiqSweep",      ["MES", "MNQ", "M2K"],                ["long", "short"]),
    ("close_momentum",         "CloseMomentum",      ["MES", "MNQ", "MGC", "M2K"],         ["long", "short"]),
    ("gap_mom",                "GapMom",             ["MES", "MNQ", "MGC", "M2K"],         ["long", "short"]),
    ("range_expansion",        "RangeExpansion",     ["MES", "MNQ", "MGC", "M2K", "MCL"], ["long", "short"]),
]

# ── Research gate minimums ────────────────────────────────────────────────────
MIN_TRADES = 15       # Absolute minimum (tail engines)
MIN_PF = 1.25         # Profit factor
MIN_SHARPE = 1.4      # Annualized Sharpe


def load_data(asset: str) -> pd.DataFrame:
    """Load 5m OHLCV data for an asset."""
    cfg = ASSET_CONFIG[asset]
    path = DATA_DIR / cfg["file"]
    df = pd.read_csv(path)
    if "datetime" not in df.columns and "timestamp" in df.columns:
        df.rename(columns={"timestamp": "datetime"}, inplace=True)
    return df


def test_candidate(module_name: str, asset: str, mode: str) -> dict:
    """Run a single candidate on an asset/mode combo."""
    try:
        # Import strategy
        mod = importlib.import_module(f"strategies.{module_name}.strategy")
        importlib.reload(mod)  # Ensure fresh load

        # Load data
        df = load_data(asset)
        cfg = ASSET_CONFIG[asset]

        # Generate signals
        try:
            signals = mod.generate_signals(df, asset=asset)
        except TypeError:
            signals = mod.generate_signals(df)

        # Run backtest
        result = run_backtest(
            df, signals,
            mode=mode,
            point_value=cfg["point_value"],
            tick_size=cfg["tick_size"],
            symbol=asset,
        )

        trades = result["trades_df"]
        stats = result["stats"]

        if trades is None or (hasattr(trades, "empty") and trades.empty) or len(trades) == 0:
            return {"status": "no_trades", "trades": 0}

        trade_count = len(trades)
        pnl = float(trades["pnl"].sum()) if "pnl" in trades.columns else 0.0
        gross_profit = float(trades[trades["pnl"] > 0]["pnl"].sum()) if trade_count > 0 else 0.0
        gross_loss = abs(float(trades[trades["pnl"] < 0]["pnl"].sum())) if trade_count > 0 else 0.0
        pf = gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        win_rate = float((trades["pnl"] > 0).mean()) if trade_count > 0 else 0.0

        # Calculate Sharpe and max drawdown from trades (not in stats dict)
        pnl_series = trades["pnl"].values
        equity = np.cumsum(pnl_series)
        peak = np.maximum.accumulate(equity)
        drawdowns = peak - equity
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        mean_pnl = np.mean(pnl_series)
        std_pnl = np.std(pnl_series, ddof=1) if len(pnl_series) > 1 else 1.0
        sharpe = float(mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0.0

        # Calculate avg win/loss
        wins = trades[trades["pnl"] > 0]
        losses = trades[trades["pnl"] < 0]
        avg_win = float(wins["pnl"].mean()) if len(wins) > 0 else 0.0
        avg_loss = float(losses["pnl"].mean()) if len(losses) > 0 else 0.0

        # Pass research gate?
        passes_gate = (
            trade_count >= MIN_TRADES
            and pf >= MIN_PF
            and sharpe >= MIN_SHARPE
        )

        return {
            "status": "pass" if passes_gate else "fail",
            "trades": trade_count,
            "pnl": round(pnl, 2),
            "profit_factor": round(pf, 3),
            "sharpe": round(sharpe, 3),
            "win_rate": round(win_rate, 4),
            "max_drawdown": round(max_dd, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "passes_gate": passes_gate,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()[-500:],
        }


def main():
    print("=" * 70)
    print("  FQL BATCH HARVEST VALIDATION")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    all_results = {}
    passes = []
    fails = []
    errors = []

    for module_name, display_name, assets, modes in CANDIDATES:
        print(f"\n  Testing {display_name} ({module_name})...")
        strategy_results = {}

        for asset in assets:
            for mode in modes:
                combo = f"{asset}-{mode}"
                print(f"    {combo:20s}", end="  ", flush=True)

                result = test_candidate(module_name, asset, mode)

                if result["status"] == "error":
                    print(f"ERROR: {result['error'][:60]}")
                    errors.append(f"{display_name} {combo}")
                elif result["status"] == "no_trades":
                    print("no trades")
                elif result["passes_gate"]:
                    print(f"PASS  PF={result['profit_factor']:.2f}  Sharpe={result['sharpe']:.2f}  trades={result['trades']}  PnL=${result['pnl']:,.0f}")
                    passes.append(f"{display_name} {combo}")
                else:
                    reason = []
                    if result["trades"] < MIN_TRADES:
                        reason.append(f"trades={result['trades']}")
                    if result["profit_factor"] < MIN_PF:
                        reason.append(f"PF={result['profit_factor']:.2f}")
                    if result["sharpe"] < MIN_SHARPE:
                        reason.append(f"Sharpe={result['sharpe']:.2f}")
                    print(f"FAIL  {', '.join(reason)}  PnL=${result['pnl']:,.0f}")
                    fails.append(f"{display_name} {combo}")

                strategy_results[combo] = result

        all_results[display_name] = {
            "module": module_name,
            "results": strategy_results,
            "best_combo": None,
            "best_pf": 0,
        }

        # Find best combo
        viable = {k: v for k, v in strategy_results.items()
                  if v.get("status") == "pass" and v.get("passes_gate")}
        if viable:
            best_key = max(viable, key=lambda k: viable[k]["profit_factor"])
            all_results[display_name]["best_combo"] = best_key
            all_results[display_name]["best_pf"] = viable[best_key]["profit_factor"]

    # Summary
    print("\n" + "=" * 70)
    print("  HARVEST VALIDATION SUMMARY")
    print("=" * 70)
    print(f"\n  PASSED RESEARCH GATE ({len(passes)}):")
    for p in passes:
        print(f"    + {p}")
    print(f"\n  FAILED ({len(fails)}):")
    for f in fails[:10]:
        print(f"    - {f}")
    if len(fails) > 10:
        print(f"    ... and {len(fails) - 10} more")
    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    ! {e}")

    # Best combos
    print(f"\n  BEST COMBOS (pipeline candidates):")
    print("  " + "-" * 55)
    for name, data in sorted(all_results.items(), key=lambda x: -x[1].get("best_pf", 0)):
        if data["best_combo"]:
            combo = data["best_combo"]
            r = data["results"][combo]
            print(f"  {name:25s}  {combo:15s}  PF={r['profit_factor']:.2f}  Sharpe={r['sharpe']:.2f}  trades={r['trades']}")

    # Save results
    output = {
        "_generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "_gate": {"min_trades": MIN_TRADES, "min_pf": MIN_PF, "min_sharpe": MIN_SHARPE},
        "results": all_results,
        "summary": {
            "passed": passes,
            "failed_count": len(fails),
            "error_count": len(errors),
        },
    }
    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Results saved to: {RESULTS_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
