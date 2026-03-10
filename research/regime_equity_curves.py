"""Regime Equity Curves — Per-regime PnL analysis for 4-strategy portfolio.

Shows where each strategy makes/loses money across regime states.
Reveals which regime cells are still bleeding and which strategy type would fix them.

Usage:
    python3 research/regime_equity_curves.py
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import ASSET_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"

STRATEGIES = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short", "label": "PB-MGC-Short"},
    {"name": "orb_009", "asset": "MGC", "mode": "long", "label": "ORB-MGC-Long"},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long", "label": "VWAP-MNQ-Long"},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long", "label": "Donchian-MNQ-Long"},
]


def load_strategy(name):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_and_tag(strat, engine):
    """Run strategy, merge regime data onto trades."""
    asset = strat["asset"]
    config = ASSET_CONFIG[asset]
    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    mod = load_strategy(strat["name"])
    mod.TICK_SIZE = config["tick_size"]
    signals = mod.generate_signals(df)

    result = run_backtest(df, signals, mode=strat["mode"],
                         point_value=config["point_value"], symbol=asset)
    trades = result["trades_df"]

    if trades.empty:
        return trades

    # Get regime data
    regime_daily = engine.get_daily_regimes(df)
    regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
    regime_daily["_date_date"] = regime_daily["_date"].dt.date

    trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
    trades = trades.merge(
        regime_daily[["_date_date", "vol_regime", "trend_regime", "rv_regime",
                      "trend_persistence", "composite_regime"]],
        left_on="entry_date", right_on="_date_date", how="left",
    )
    trades["regime_cell"] = trades["composite_regime"] + "_" + trades["rv_regime"]
    trades["strategy"] = strat["label"]
    return trades


def main():
    engine = RegimeEngine()

    print("=" * 80)
    print("  REGIME EQUITY CURVES — 4-STRATEGY PORTFOLIO")
    print("=" * 80)

    # Run all strategies
    all_trades = []
    for strat in STRATEGIES:
        print(f"  Running {strat['label']}...")
        trades = run_and_tag(strat, engine)
        if not trades.empty:
            all_trades.append(trades)

    combined = pd.concat(all_trades, ignore_index=True)
    print(f"\n  Total trades: {len(combined)}")

    # ── 1. Portfolio PnL by composite regime ─────────────────────────
    print(f"\n{'='*80}")
    print(f"  PORTFOLIO PNL BY COMPOSITE REGIME (vol × trend)")
    print(f"{'='*80}\n")

    comp_groups = combined.groupby("composite_regime").agg(
        trades=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda x: (x > 0).mean()),
    ).sort_values("pnl", ascending=False)

    print(f"  {'Composite Regime':<25} {'Trades':>7} {'PnL':>10} {'AvgPnL':>8} {'WR%':>7}")
    print(f"  {'-'*25} {'-'*7} {'-'*10} {'-'*8} {'-'*7}")
    for regime, row in comp_groups.iterrows():
        print(f"  {regime:<25} {int(row['trades']):>7} "
              f"{'${:,.0f}'.format(row['pnl']):>10} "
              f"{'${:,.0f}'.format(row['avg_pnl']):>8} "
              f"{row['win_rate']*100:>6.1f}%")

    # ── 2. Portfolio PnL by full regime cell (18-cell grid) ──────────
    print(f"\n{'='*80}")
    print(f"  PORTFOLIO PNL BY REGIME CELL (vol × trend × rv) — 18-CELL GRID")
    print(f"{'='*80}\n")

    cell_groups = combined.groupby("regime_cell").agg(
        trades=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda x: (x > 0).mean()),
    ).sort_values("pnl", ascending=False)

    print(f"  {'Regime Cell':<35} {'Trades':>7} {'PnL':>10} {'AvgPnL':>8} {'WR%':>7}")
    print(f"  {'-'*35} {'-'*7} {'-'*10} {'-'*8} {'-'*7}")
    for cell, row in cell_groups.iterrows():
        marker = " <<<" if row["pnl"] < -200 else ""
        print(f"  {cell:<35} {int(row['trades']):>7} "
              f"{'${:,.0f}'.format(row['pnl']):>10} "
              f"{'${:,.0f}'.format(row['avg_pnl']):>8} "
              f"{row['win_rate']*100:>6.1f}%{marker}")

    # ── 3. Per-strategy contribution by regime ───────────────────────
    print(f"\n{'='*80}")
    print(f"  PER-STRATEGY PNL BY COMPOSITE REGIME")
    print(f"{'='*80}\n")

    strat_regime = combined.groupby(["composite_regime", "strategy"]).agg(
        trades=("pnl", "count"),
        pnl=("pnl", "sum"),
    ).reset_index()

    regimes_ordered = comp_groups.index.tolist()
    strat_labels = [s["label"] for s in STRATEGIES]

    # Header
    header = f"  {'Regime':<22}"
    for sl in strat_labels:
        short = sl.split("-")[0][:6]
        header += f" {short:>10}"
    header += f" {'TOTAL':>10}"
    print(header)
    print(f"  {'-'*22}" + f" {'-'*10}" * (len(strat_labels) + 1))

    for regime in regimes_ordered:
        row_str = f"  {regime:<22}"
        total = 0
        for sl in strat_labels:
            subset = strat_regime[(strat_regime["composite_regime"] == regime) &
                                  (strat_regime["strategy"] == sl)]
            pnl = subset["pnl"].sum() if len(subset) > 0 else 0
            total += pnl
            row_str += f" {'${:,.0f}'.format(pnl):>10}"
        row_str += f" {'${:,.0f}'.format(total):>10}"
        print(row_str)

    # ── 4. Trend persistence breakdown ───────────────────────────────
    print(f"\n{'='*80}")
    print(f"  PORTFOLIO PNL BY TREND PERSISTENCE")
    print(f"{'='*80}\n")

    for persist in ["GRINDING", "CHOPPY"]:
        subset = combined[combined["trend_persistence"] == persist]
        print(f"  {persist}:")
        print(f"    Total: {len(subset)} trades, PnL=${subset['pnl'].sum():,.0f}, "
              f"WR={( subset['pnl']>0).mean()*100:.1f}%")

        # Per-strategy within persistence
        for sl in strat_labels:
            s = subset[subset["strategy"] == sl]
            if len(s) > 0:
                print(f"      {sl}: {len(s)} trades, ${s['pnl'].sum():,.0f}")
        print()

    # ── 5. The bleed cells — where is the portfolio losing? ──────────
    print(f"{'='*80}")
    print(f"  BLEED ANALYSIS — NEGATIVE REGIME CELLS")
    print(f"{'='*80}\n")

    bleed_cells = cell_groups[cell_groups["pnl"] < 0].sort_values("pnl")
    total_bleed = bleed_cells["pnl"].sum()
    total_profit = cell_groups[cell_groups["pnl"] > 0]["pnl"].sum()

    print(f"  Total portfolio profit from positive cells: ${total_profit:,.0f}")
    print(f"  Total portfolio bleed from negative cells:  ${total_bleed:,.0f}")
    print(f"  Net portfolio PnL:                          ${total_profit + total_bleed:,.0f}")
    print(f"\n  Bleed cells (ordered by severity):\n")

    for cell, row in bleed_cells.iterrows():
        pct_of_bleed = row["pnl"] / total_bleed * 100 if total_bleed != 0 else 0
        # Which strategies contribute to this cell?
        cell_strats = combined[combined["regime_cell"] == cell]
        contributors = cell_strats.groupby("strategy")["pnl"].sum().sort_values()

        print(f"  {cell}")
        print(f"    PnL: ${row['pnl']:,.0f} ({pct_of_bleed:.1f}% of total bleed)")
        print(f"    Trades: {int(row['trades'])}, WR: {row['win_rate']*100:.1f}%")
        for strat_name, strat_pnl in contributors.items():
            short_name = strat_name.split("-")[0]
            print(f"      {short_name}: ${strat_pnl:,.0f}")
        print()

    # ── 6. Regime coverage heatmap ───────────────────────────────────
    print(f"{'='*80}")
    print(f"  REGIME COVERAGE HEATMAP")
    print(f"{'='*80}\n")

    vol_states = ["LOW_VOL", "NORMAL", "HIGH_VOL"]
    trend_states = ["TRENDING", "RANGING"]
    rv_states = ["LOW_RV", "NORMAL_RV", "HIGH_RV"]

    print(f"  {'':>20}", end="")
    for rv in rv_states:
        print(f" {rv:>12}", end="")
    print()

    for vol in vol_states:
        for trend in trend_states:
            composite = f"{vol}_{trend}"
            print(f"  {composite:<20}", end="")
            for rv in rv_states:
                cell = f"{composite}_{rv}"
                if cell in cell_groups.index:
                    pnl = cell_groups.loc[cell, "pnl"]
                    trades = int(cell_groups.loc[cell, "trades"])
                    if pnl >= 500:
                        marker = f"${pnl:,.0f}"
                    elif pnl >= 0:
                        marker = f"${pnl:,.0f}"
                    else:
                        marker = f"${pnl:,.0f}"
                    print(f" {marker:>12}", end="")
                else:
                    print(f" {'—':>12}", end="")
            print()
        print()

    print("=" * 80)
    print("  DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
