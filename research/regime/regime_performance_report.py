"""Phase 8 — Regime Performance Report.

For each validated/candidate strategy, run historical performance segmented
by regime states from the multi-factor RegimeEngine.

Outputs:
- Per-regime PF, Sharpe, trade count, monthly consistency
- Per-regime recommendation: active / neutral / avoid
- Auto-generated strategy_regime_profiles.json

Usage:
    python3 research/regime/regime_performance_report.py
"""

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

OUTPUT_DIR = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# All strategies to analyze (validated + candidate)
STRATEGIES = [
    {
        "name": "pb_trend",
        "asset": "MGC",
        "mode": "short",
        "label": "PB-MGC-Short",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
    {
        "name": "orb_009",
        "asset": "MGC",
        "mode": "long",
        "label": "ORB-009-MGC-Long",
        "point_value": 10.0,
        "tick_size": 0.10,
    },
    {
        "name": "vix_channel",
        "asset": "MES",
        "mode": "both",
        "label": "VIX-Channel-MES-Both",
        "point_value": 5.0,
        "tick_size": 0.25,
    },
]

STARTING_CAPITAL = 50_000.0


def load_strategy(name):
    path = PROJECT_ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_data(asset):
    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def compute_regime_metrics(trades_subset, all_trades_count):
    """Compute standard metrics for a subset of trades."""
    if trades_subset.empty:
        return {
            "trades": 0, "pf": 0, "sharpe": 0, "pnl": 0, "maxdd": 0,
            "wr": 0, "exp": 0, "pct_of_trades": 0,
            "profitable_months": 0, "total_months": 0, "monthly_consistency": 0,
        }

    pnl = trades_subset["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gross_profit = wins.sum() if len(wins) else 0
    gross_loss = abs(losses.sum()) if len(losses) else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (100.0 if gross_profit > 0 else 0)

    # Sharpe from daily PnL
    daily = trades_subset.groupby("_date")["pnl"].sum()
    if len(daily) > 1 and daily.std() > 0:
        sharpe = daily.mean() / daily.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    # MaxDD
    equity = STARTING_CAPITAL + np.cumsum(pnl.values)
    peak = np.maximum.accumulate(equity)
    maxdd = (peak - equity).max()

    # Monthly consistency
    trades_subset = trades_subset.copy()
    trades_subset["_month"] = pd.to_datetime(trades_subset["_date"]).dt.to_period("M")
    monthly_pnl = trades_subset.groupby("_month")["pnl"].sum()
    profitable_months = (monthly_pnl > 0).sum()
    total_months = len(monthly_pnl)
    monthly_pct = round(profitable_months / total_months * 100, 1) if total_months > 0 else 0

    return {
        "trades": len(trades_subset),
        "pf": round(pf, 3),
        "sharpe": round(sharpe, 4),
        "pnl": round(pnl.sum(), 2),
        "maxdd": round(maxdd, 2),
        "wr": round(len(wins) / len(pnl) * 100, 1),
        "exp": round(pnl.mean(), 2),
        "pct_of_trades": round(len(trades_subset) / all_trades_count * 100, 1)
            if all_trades_count > 0 else 0,
        "profitable_months": profitable_months,
        "total_months": total_months,
        "monthly_consistency": monthly_pct,
    }


def recommend(pf):
    """Per-regime recommendation based on PF."""
    if pf >= 1.3:
        return "active"
    elif pf >= 1.0:
        return "neutral"
    else:
        return "avoid"


def main():
    print("=" * 70)
    print("  PHASE 8 — REGIME PERFORMANCE REPORT")
    print("  (Multi-factor RegimeEngine segmentation)")
    print("=" * 70)

    engine = RegimeEngine()
    all_results = {}
    profiles = {}

    # Markdown report lines
    md_lines = [
        "# Regime Performance Report",
        "",
        "*Phase 8 — Multi-factor regime segmentation for all validated strategies.*",
        "",
        "## Regime Engine Factors",
        "",
        "| Factor | Computation | States |",
        "|--------|-------------|--------|",
        "| Volatility | ATR percentile (20-bar ATR, 252-day lookback) | LOW_VOL / NORMAL / HIGH_VOL |",
        "| Trend | 20-day EMA slope sign + magnitude | TRENDING / RANGING |",
        "| Realized Vol | 14-day rolling stdev of returns × √252 | LOW_RV / NORMAL_RV / HIGH_RV |",
        "",
    ]

    for strat in STRATEGIES:
        label = strat["label"]
        print(f"\n{'─' * 70}")
        print(f"  {label}")
        print(f"{'─' * 70}")

        # Load and classify
        mod = load_strategy(strat["name"])
        df = load_data(strat["asset"])

        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = strat["tick_size"]

        df_classified = engine.classify(df)

        sig = inspect.signature(mod.generate_signals)
        if "asset" in sig.parameters:
            signals = mod.generate_signals(df_classified, asset=strat["asset"])
        else:
            signals = mod.generate_signals(df_classified)

        result = run_backtest(
            df_classified, signals,
            mode=strat["mode"],
            point_value=strat["point_value"],
            symbol=strat["asset"],
        )

        trades = result["trades_df"]
        if trades.empty:
            print(f"  No trades for {label}")
            continue

        trades = trades.copy()
        trades["_date"] = pd.to_datetime(trades["entry_time"]).dt.date

        # Get daily regime mapping
        daily_regimes = df_classified.groupby("_date")[
            ["vol_regime", "trend_regime", "rv_regime", "composite_regime"]
        ].last().reset_index()
        trades = trades.merge(daily_regimes, on="_date", how="left")

        n_total = len(trades)

        # ── Analyze by each factor ───────────────────────────────────────
        strat_result = {"label": label, "asset": strat["asset"], "mode": strat["mode"]}
        preferred = []
        avoid = []

        md_lines.extend([
            f"## {label}",
            "",
            f"**Asset:** {strat['asset']} | **Mode:** {strat['mode']} | **Total trades:** {n_total}",
            "",
        ])

        for factor, states in [
            ("vol_regime", ["LOW_VOL", "NORMAL", "HIGH_VOL"]),
            ("trend_regime", ["TRENDING", "RANGING"]),
            ("rv_regime", ["LOW_RV", "NORMAL_RV", "HIGH_RV"]),
        ]:
            factor_results = {}
            print(f"\n  {factor}:")
            print(f"  {'State':<12} {'Trades':>7} {'PF':>7} {'Sharpe':>8} {'PnL':>10} "
                  f"{'WR':>6} {'Mo%':>6} {'Action':>8}")
            print(f"  {'─' * 72}")

            md_lines.extend([
                f"### {factor}",
                "",
                f"| State | Trades | PF | Sharpe | PnL | WR | Monthly% | Action |",
                f"|-------|--------|-----|--------|-----|-----|---------|--------|",
            ])

            for state in states:
                subset = trades[trades[factor] == state]
                m = compute_regime_metrics(subset, n_total)
                action = recommend(m["pf"])

                if m["trades"] > 0:
                    if action == "active":
                        preferred.append(state)
                    elif action == "avoid":
                        avoid.append(state)

                factor_results[state] = {**m, "recommendation": action}

                print(f"  {state:<12} {m['trades']:>7} {m['pf']:>7.2f} {m['sharpe']:>8.2f} "
                      f"${m['pnl']:>9.2f} {m['wr']:>5.1f}% {m['monthly_consistency']:>5.1f}% "
                      f"{action:>8}")
                md_lines.append(
                    f"| {state} | {m['trades']} | {m['pf']:.2f} | {m['sharpe']:.2f} | "
                    f"${m['pnl']:.0f} | {m['wr']:.0f}% | {m['monthly_consistency']:.0f}% | "
                    f"**{action}** |"
                )

            strat_result[factor] = factor_results
            md_lines.append("")

        all_results[label] = strat_result

        # Build profile
        # Deduplicate preferred/avoid lists
        preferred = list(set(preferred))
        avoid = list(set(avoid))
        profiles[label] = {
            "asset": strat["asset"],
            "mode": strat["mode"],
            "preferred_regimes": preferred,
            "avoid_regimes": avoid,
            "source": "regime_performance_report",
        }

        print(f"\n  Profile: preferred={preferred}, avoid={avoid}")
        md_lines.extend([
            f"**Profile:** Preferred = {preferred}, Avoid = {avoid}",
            "",
            "---",
            "",
        ])

    # ── Regime distribution summary ──────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  REGIME DISTRIBUTION (MES data)")
    print(f"{'=' * 70}")

    df_mes = load_data("MES")
    summary = engine.regime_summary(df_mes)

    md_lines.extend([
        "## Regime Distribution (MES)",
        "",
    ])

    for factor, states in summary.items():
        if factor == "total_days":
            print(f"  Total trading days: {states}")
            md_lines.append(f"**Total trading days:** {states}")
            continue
        print(f"\n  {factor}:")
        md_lines.extend([f"### {factor}", "", "| State | Days | % |", "|-------|------|---|"])
        for state, info in states.items():
            print(f"    {state}: {info['count']} days ({info['pct']}%)")
            md_lines.append(f"| {state} | {info['count']} | {info['pct']}% |")
        md_lines.append("")

    # ── Save profiles JSON ───────────────────────────────────────────────────
    with open(OUTPUT_DIR / "strategy_regime_profiles.json", "w") as f:
        json.dump(profiles, f, indent=2)

    print(f"\n  Profiles saved to: {OUTPUT_DIR / 'strategy_regime_profiles.json'}")

    # ── Save full results ────────────────────────────────────────────────────
    with open(OUTPUT_DIR / "regime_performance_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    # ── Save markdown report ─────────────────────────────────────────────────
    md_lines.extend([
        "",
        "---",
        f"*Generated by regime_performance_report.py*",
    ])

    with open(OUTPUT_DIR / "regime_performance_report.md", "w") as f:
        f.write("\n".join(md_lines))

    print(f"  Report saved to: {OUTPUT_DIR / 'regime_performance_report.md'}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
