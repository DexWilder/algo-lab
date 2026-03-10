"""Regime Coverage Map Generator — Phase 9.5.

Generates a machine-readable JSON showing exactly which regime cells are
covered/exposed by the current portfolio. Used by the evolution scheduler's
portfolio fitness function and by future harvesting to identify gaps.

Coverage classification:
  STRONG:  ≥2 strategies active AND ≥30 trades total AND avg PF ≥ 1.3
  COVERED: 1+ strategy active AND ≥15 trades AND avg PF ≥ 1.0
  THIN:    1 strategy active AND (<15 trades OR PF < 1.3)
  MISSING: 0 strategies active in this cell

Usage:
    python3 research/regime/regime_coverage_map.py                # Full generation
    python3 research/regime/regime_coverage_map.py --json-only    # Skip markdown
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
PROFILES_PATH = PROJECT_ROOT / "research" / "regime" / "strategy_regime_profiles.json"
OUTPUT_JSON = PROJECT_ROOT / "research" / "regime" / "regime_coverage.json"
OUTPUT_MD = PROJECT_ROOT / "research" / "regime" / "regime_coverage_report.md"

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
}

# Validated/candidate strategies for coverage analysis
STRATEGIES = {
    "PB-MGC-Short": {
        "module_path": PROJECT_ROOT / "strategies" / "pb_trend" / "strategy.py",
        "asset": "MGC",
        "mode": "short",
    },
    "ORB-009-MGC-Long": {
        "module_path": PROJECT_ROOT / "strategies" / "orb_009" / "strategy.py",
        "asset": "MGC",
        "mode": "long",
    },
    "VIX-Channel-MES-Both": {
        "module_path": PROJECT_ROOT / "strategies" / "vix_channel" / "strategy.py",
        "asset": "MES",
        "mode": "both",
    },
}

# Regime factor values
VOL_REGIMES = ["LOW_VOL", "NORMAL", "HIGH_VOL"]
TREND_REGIMES = ["TRENDING", "RANGING"]
RV_REGIMES = ["LOW_RV", "NORMAL_RV", "HIGH_RV"]


def load_module(name: str, path: Path):
    """Dynamically load a strategy module."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset: str) -> pd.DataFrame:
    """Load processed 5m CSV for an asset."""
    path = PROCESSED_DIR / f"{asset}_5m.csv"
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def run_strategy_backtest(name: str, cfg: dict) -> pd.DataFrame:
    """Run backtest for a strategy, return trades_df."""
    asset = cfg["asset"]
    mode = cfg["mode"]
    acfg = ASSET_CONFIG[asset]

    df = load_data(asset)
    mod = load_module(name, cfg["module_path"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = acfg["tick_size"]

    sig = inspect.signature(mod.generate_signals)
    if "asset" in sig.parameters:
        signals = mod.generate_signals(df, asset=asset)
    else:
        signals = mod.generate_signals(df)

    result = run_backtest(
        df, signals,
        mode=mode,
        point_value=acfg["point_value"],
        symbol=asset,
    )
    return result["trades_df"]


def classify_coverage(n_strategies: int, total_trades: int, avg_pf: float) -> str:
    """Classify a regime cell's coverage level."""
    if n_strategies == 0:
        return "MISSING"
    if n_strategies >= 2 and total_trades >= 30 and avg_pf >= 1.3:
        return "STRONG"
    if total_trades >= 15 and avg_pf >= 1.0:
        return "COVERED"
    return "THIN"


def gap_priority(coverage: str, days_pct: float) -> str:
    """Determine gap priority based on coverage and frequency."""
    if coverage == "MISSING":
        return "high" if days_pct >= 2.0 else "low"
    if coverage == "THIN":
        return "medium"
    return "none"


def generate_regime_coverage(
    strategies: dict | None = None,
    profiles: dict | None = None,
    data_dir: Path | None = None,
) -> dict:
    """Generate regime coverage map with per-cell statistics.

    Parameters
    ----------
    strategies : dict | None
        Strategy definitions {name: {module_path, asset, mode}}.
        Defaults to STRATEGIES.
    profiles : dict | None
        Strategy regime profiles. Loaded from disk if None.
    data_dir : Path | None
        Path to processed data directory. Defaults to PROCESSED_DIR.

    Returns
    -------
    dict : Complete coverage map with cells and summary.
    """
    if strategies is None:
        strategies = STRATEGIES
    if profiles is None and PROFILES_PATH.exists():
        with open(PROFILES_PATH) as f:
            profiles = json.load(f)
    if data_dir is None:
        data_dir = PROCESSED_DIR

    print("=" * 60)
    print("  REGIME COVERAGE MAP GENERATOR")
    print("=" * 60)

    # Step 1: Run backtests and collect trades per strategy
    all_trades = {}
    for name, cfg in strategies.items():
        print(f"\n  Running: {name} ({cfg['asset']}-{cfg['mode']})")
        try:
            trades_df = run_strategy_backtest(name, cfg)
            all_trades[name] = {
                "trades_df": trades_df,
                "asset": cfg["asset"],
            }
            print(f"    Trades: {len(trades_df)}")
        except Exception as e:
            print(f"    ERROR: {e}")

    # Step 2: Get regime labels for each asset
    engine = RegimeEngine()
    asset_regimes = {}  # {asset: {date: {vol_regime, trend_regime, rv_regime}}}

    assets_needed = set(cfg["asset"] for cfg in strategies.values())
    for asset in assets_needed:
        print(f"\n  Classifying regimes for {asset}...")
        df = load_data(asset)
        daily = engine.get_daily_regimes(df)
        daily["_date"] = pd.to_datetime(daily["_date"]).dt.date

        regime_lookup = {}
        for _, row in daily.iterrows():
            regime_lookup[row["_date"]] = {
                "vol_regime": row["vol_regime"],
                "trend_regime": row["trend_regime"],
                "rv_regime": row["rv_regime"],
            }
        asset_regimes[asset] = regime_lookup
        print(f"    {len(regime_lookup)} trading days classified")

    # Step 3: Merge trades with regime labels
    # For each strategy, tag each trade with its regime cell
    strategy_trade_regimes = {}  # {strategy: [{cell_key, pnl}, ...]}
    for name, data in all_trades.items():
        trades_df = data["trades_df"]
        asset = data["asset"]
        regime_lookup = asset_regimes.get(asset, {})

        tagged = []
        for _, trade in trades_df.iterrows():
            trade_date = pd.to_datetime(trade["exit_time"]).date()
            regime = regime_lookup.get(trade_date)
            if regime:
                cell_key = f"{regime['vol_regime']}_{regime['trend_regime']}_{regime['rv_regime']}"
                tagged.append({
                    "cell_key": cell_key,
                    "pnl": trade["pnl"],
                    "vol_regime": regime["vol_regime"],
                    "trend_regime": regime["trend_regime"],
                    "rv_regime": regime["rv_regime"],
                })
        strategy_trade_regimes[name] = tagged

    # Step 4: Count total days across all assets (use reference asset MES)
    ref_asset = "MES" if "MES" in asset_regimes else list(asset_regimes.keys())[0]
    ref_regimes = asset_regimes[ref_asset]
    total_days = len(ref_regimes)

    # Count days per cell
    cell_day_counts = {}
    for date, regime in ref_regimes.items():
        cell_key = f"{regime['vol_regime']}_{regime['trend_regime']}_{regime['rv_regime']}"
        cell_day_counts[cell_key] = cell_day_counts.get(cell_key, 0) + 1

    # Step 5: Build per-cell statistics
    cells = []
    for vol in VOL_REGIMES:
        for trend in TREND_REGIMES:
            for rv in RV_REGIMES:
                cell_key = f"{vol}_{trend}_{rv}"
                days = cell_day_counts.get(cell_key, 0)
                pct = round(days / total_days * 100, 1) if total_days > 0 else 0.0

                # Find strategies active in this cell and their trades
                active_strategies = []
                total_trades_in_cell = 0
                total_pnl_in_cell = 0.0
                gross_win = 0.0
                gross_loss = 0.0

                for strat_name, tagged_trades in strategy_trade_regimes.items():
                    strat_trades = [t for t in tagged_trades if t["cell_key"] == cell_key]
                    if strat_trades:
                        active_strategies.append(strat_name)
                        total_trades_in_cell += len(strat_trades)
                        for t in strat_trades:
                            total_pnl_in_cell += t["pnl"]
                            if t["pnl"] > 0:
                                gross_win += t["pnl"]
                            else:
                                gross_loss += abs(t["pnl"])

                # Compute average PF in cell
                avg_pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (
                    float("inf") if gross_win > 0 else 0.0
                )
                # Cap infinite PF for classification
                avg_pf_capped = min(avg_pf, 99.0) if avg_pf != float("inf") else 99.0

                coverage = classify_coverage(
                    len(active_strategies), total_trades_in_cell, avg_pf_capped
                )
                priority = gap_priority(coverage, pct)

                cell_data = {
                    "vol_regime": vol,
                    "trend_regime": trend,
                    "rv_regime": rv,
                    "cell_key": cell_key,
                    "days": days,
                    "pct_of_total": pct,
                    "strategies_active": active_strategies,
                    "total_trades_in_cell": total_trades_in_cell,
                    "total_pnl_in_cell": round(total_pnl_in_cell, 2),
                    "avg_pf_in_cell": avg_pf_capped if avg_pf != float("inf") else "inf",
                    "coverage": coverage,
                    "gap_priority": priority,
                }
                cells.append(cell_data)

    # Step 6: Build summary
    covered_count = sum(1 for c in cells if c["coverage"] == "STRONG")
    covered_count += sum(1 for c in cells if c["coverage"] == "COVERED")
    thin_count = sum(1 for c in cells if c["coverage"] == "THIN")
    missing_count = sum(1 for c in cells if c["coverage"] == "MISSING")
    strong_count = sum(1 for c in cells if c["coverage"] == "STRONG")

    gap_cells = [
        c["cell_key"] for c in cells
        if c["coverage"] in ("MISSING", "THIN")
    ]

    result = {
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "total_days": total_days,
        "strategies_analyzed": list(strategies.keys()),
        "factors": {
            "vol_regime": VOL_REGIMES,
            "trend_regime": TREND_REGIMES,
            "rv_regime": RV_REGIMES,
        },
        "cells": cells,
        "summary": {
            "strong": strong_count,
            "covered": covered_count,
            "thin": thin_count,
            "missing": missing_count,
            "gap_cells": gap_cells,
        },
    }

    return result


def save_coverage_json(coverage: dict, path: Path | None = None):
    """Save coverage map to JSON."""
    if path is None:
        path = OUTPUT_JSON

    # Make avg_pf serializable
    def _default(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, float) and (obj == float("inf") or obj != obj):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} not serializable")

    path.write_text(json.dumps(coverage, indent=2, default=_default))
    print(f"\n  Coverage JSON saved: {path}")


def generate_coverage_markdown(coverage: dict, path: Path | None = None):
    """Generate human-readable markdown from coverage map."""
    if path is None:
        path = OUTPUT_MD

    lines = [
        "# Regime Coverage Map",
        "",
        f"*Generated: {coverage['generated']}*",
        f"*Total trading days: {coverage['total_days']}*",
        f"*Strategies analyzed: {', '.join(coverage['strategies_analyzed'])}*",
        "",
        "---",
        "",
        "## Coverage Summary",
        "",
        f"| Level | Count |",
        f"|-------|-------|",
        f"| STRONG | {coverage['summary']['strong']} |",
        f"| COVERED | {coverage['summary']['covered']} |",
        f"| THIN | {coverage['summary']['thin']} |",
        f"| MISSING | {coverage['summary']['missing']} |",
        "",
        "## Coverage Matrix",
        "",
        "| Vol | Trend | RV | Days | % | Strategies | Trades | PF | Coverage | Priority |",
        "|-----|-------|----|------|---|------------|--------|----|----------|----------|",
    ]

    for cell in sorted(coverage["cells"], key=lambda c: -c["days"]):
        strats = ", ".join(cell["strategies_active"]) if cell["strategies_active"] else "—"
        pf = cell["avg_pf_in_cell"]
        pf_str = f"{pf:.2f}" if isinstance(pf, (int, float)) and pf != float("inf") else str(pf)
        lines.append(
            f"| {cell['vol_regime']} | {cell['trend_regime']} | {cell['rv_regime']} | "
            f"{cell['days']} | {cell['pct_of_total']}% | {strats} | "
            f"{cell['total_trades_in_cell']} | {pf_str} | "
            f"**{cell['coverage']}** | {cell['gap_priority']} |"
        )

    # Gap analysis
    gap_cells = [c for c in coverage["cells"] if c["coverage"] in ("MISSING", "THIN")]
    if gap_cells:
        lines.extend([
            "",
            "## Gap Analysis",
            "",
            "### MISSING Cells (zero strategy coverage)",
            "",
        ])
        missing = [c for c in gap_cells if c["coverage"] == "MISSING"]
        if missing:
            for c in missing:
                lines.append(f"- **{c['cell_key']}** — {c['days']} days ({c['pct_of_total']}%)")
        else:
            lines.append("None")

        lines.extend([
            "",
            "### THIN Cells (insufficient coverage)",
            "",
        ])
        thin = [c for c in gap_cells if c["coverage"] == "THIN"]
        if thin:
            for c in thin:
                strats = ", ".join(c["strategies_active"])
                lines.append(f"- **{c['cell_key']}** — {c['days']} days ({c['pct_of_total']}%), "
                            f"covered by: {strats}, trades: {c['total_trades_in_cell']}")
        else:
            lines.append("None")

    lines.extend([
        "",
        "---",
        "*Generated by regime_coverage_map.py — Phase 9.5*",
    ])

    path.write_text("\n".join(lines))
    print(f"  Coverage report saved: {path}")


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Regime Coverage Map Generator")
    parser.add_argument("--json-only", action="store_true",
                        help="Only generate JSON, skip markdown report")
    args = parser.parse_args()

    coverage = generate_regime_coverage()
    save_coverage_json(coverage)

    if not args.json_only:
        generate_coverage_markdown(coverage)

    # Print summary
    s = coverage["summary"]
    print(f"\n  Summary: {s['strong']} STRONG, {s['covered']} COVERED, "
          f"{s['thin']} THIN, {s['missing']} MISSING")
    if s["gap_cells"]:
        print(f"  Gap cells: {', '.join(s['gap_cells'][:5])}"
              f"{'...' if len(s['gap_cells']) > 5 else ''}")
    print("=" * 60)


if __name__ == "__main__":
    main()
