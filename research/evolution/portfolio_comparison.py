"""Portfolio Comparison — Evaluate evolution candidates against baseline.

Tests whether vix_atr_stops and/or pb_relaxed_filters improve
the existing PB + ORB 2-strategy portfolio.

Portfolios tested:
  1. Baseline: PB-Trend MGC-Short + ORB-009 MGC-Long
  2. +vix_atr:  Baseline + vix_atr_stops MNQ-Long
  3. +pb_relax: Baseline + pb_relaxed_filters MES-Short
  4. All 4:     Baseline + both candidates
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest

# ── Asset config ─────────────────────────────────────────────────────────────

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25},
    "MGC": {"point_value": 10.0, "tick_size": 0.10},
}

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ── Strategy definitions ─────────────────────────────────────────────────────

STRATEGIES = {
    "PB-Trend MGC-Short": {
        "module_path": PROJECT_ROOT / "strategies" / "pb_trend" / "strategy.py",
        "asset": "MGC",
        "mode": "short",
    },
    "ORB-009 MGC-Long": {
        "module_path": PROJECT_ROOT / "strategies" / "orb_009" / "strategy.py",
        "asset": "MGC",
        "mode": "long",
    },
    "vix_atr_stops MNQ-Long": {
        "module_path": PROJECT_ROOT / "research" / "evolution" / "generated_candidates" / "vix_atr_stops" / "strategy.py",
        "asset": "MNQ",
        "mode": "long",
    },
    "pb_relaxed_filters MES-Short": {
        "module_path": PROJECT_ROOT / "research" / "evolution" / "generated_candidates" / "pb_relaxed_filters" / "strategy.py",
        "asset": "MES",
        "mode": "short",
    },
}

PORTFOLIOS = {
    "Baseline (PB+ORB)":    ["PB-Trend MGC-Short", "ORB-009 MGC-Long"],
    "+vix_atr_stops":        ["PB-Trend MGC-Short", "ORB-009 MGC-Long", "vix_atr_stops MNQ-Long"],
    "+pb_relaxed_filters":   ["PB-Trend MGC-Short", "ORB-009 MGC-Long", "pb_relaxed_filters MES-Short"],
    "All 4 strategies":      ["PB-Trend MGC-Short", "ORB-009 MGC-Long", "vix_atr_stops MNQ-Long", "pb_relaxed_filters MES-Short"],
}


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def build_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    """Convert trades to a daily PnL series indexed by date."""
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def compute_portfolio_metrics(daily_pnl: pd.Series) -> dict:
    """Compute portfolio-level metrics from a combined daily PnL series."""
    if daily_pnl.empty or len(daily_pnl) < 2:
        return {
            "total_pnl": 0, "sharpe": 0, "calmar": 0,
            "max_dd": 0, "profitable_months_pct": 0,
            "trading_days": 0, "avg_daily_pnl": 0,
        }

    total_pnl = daily_pnl.sum()
    trading_days = len(daily_pnl)

    # Sharpe (annualized)
    mean_d = daily_pnl.mean()
    std_d = daily_pnl.std()
    sharpe = (mean_d / std_d) * np.sqrt(252) if std_d > 0 else 0.0

    # Max drawdown from cumulative equity
    cum_pnl = daily_pnl.cumsum()
    running_max = cum_pnl.cummax()
    drawdown = running_max - cum_pnl
    max_dd = drawdown.max()

    # Calmar (annualized PnL / max drawdown)
    date_range = (daily_pnl.index[-1] - daily_pnl.index[0]).days
    years = max(date_range / 365.25, 0.01)
    annualized_pnl = total_pnl / years
    calmar = annualized_pnl / max_dd if max_dd > 0 else 0.0

    # Profitable months %
    monthly = daily_pnl.resample("ME").sum()
    profitable_months = (monthly > 0).sum()
    total_months = len(monthly)
    profitable_months_pct = (profitable_months / total_months * 100) if total_months > 0 else 0

    return {
        "total_pnl": round(total_pnl, 2),
        "sharpe": round(sharpe, 4),
        "calmar": round(calmar, 4),
        "max_dd": round(max_dd, 2),
        "profitable_months_pct": round(profitable_months_pct, 1),
        "trading_days": trading_days,
        "avg_daily_pnl": round(mean_d, 2),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  PORTFOLIO COMPARISON — Evolution Candidates vs Baseline")
    print("=" * 70)

    # Step 1: Run all 4 individual backtests
    daily_pnl_series = {}
    individual_stats = {}

    for name, cfg in STRATEGIES.items():
        asset = cfg["asset"]
        mode = cfg["mode"]
        acfg = ASSET_CONFIG[asset]

        print(f"\n  Running: {name}  ({asset}, {mode})")

        # Load data
        df = load_data(asset)
        print(f"    Data: {len(df):,} bars, {df['datetime'].dt.date.nunique()} days")

        # Load strategy and patch tick size
        mod = load_module(name, cfg["module_path"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = acfg["tick_size"]

        # Generate signals
        signals = mod.generate_signals(df)
        sig_counts = signals["signal"].value_counts()
        print(f"    Signals: {sig_counts.get(1, 0)} long, {sig_counts.get(-1, 0)} short")

        # Run backtest
        result = run_backtest(
            df, signals,
            mode=mode,
            point_value=acfg["point_value"],
            symbol=asset,
        )

        trades_df = result["trades_df"]
        stats = result["stats"]
        print(f"    Trades: {stats['total_trades']}  |  PnL: ${stats['total_pnl']:,.2f}")

        # Build daily PnL
        dpnl = build_daily_pnl(trades_df)
        daily_pnl_series[name] = dpnl

        # Individual metrics
        individual_stats[name] = {
            "trades": stats["total_trades"],
            "pnl": stats["total_pnl"],
            "asset": asset,
            "mode": mode,
        }

    # Step 2: Individual strategy summary
    print("\n" + "=" * 70)
    print("  INDIVIDUAL STRATEGY RESULTS")
    print("=" * 70)
    print(f"  {'Strategy':<32} {'Asset':<5} {'Mode':<6} {'Trades':>7} {'PnL':>12}")
    print(f"  {'-'*32} {'-'*5} {'-'*6} {'-'*7} {'-'*12}")
    for name, s in individual_stats.items():
        print(f"  {name:<32} {s['asset']:<5} {s['mode']:<6} {s['trades']:>7} ${s['pnl']:>10,.2f}")

    # Step 3: Compute portfolio metrics
    print("\n" + "=" * 70)
    print("  PORTFOLIO COMPARISON")
    print("=" * 70)

    portfolio_results = {}
    for port_name, strat_names in PORTFOLIOS.items():
        # Combine daily PnL across strategies (union of all dates, fill missing with 0)
        combined = pd.DataFrame({s: daily_pnl_series[s] for s in strat_names})
        combined = combined.fillna(0)
        portfolio_daily = combined.sum(axis=1).sort_index()

        metrics = compute_portfolio_metrics(portfolio_daily)
        portfolio_results[port_name] = {
            "metrics": metrics,
            "daily_pnl": portfolio_daily,
            "components": combined,
        }

    # Print comparison table
    header = f"  {'Portfolio':<25} {'PnL':>12} {'Sharpe':>8} {'Calmar':>8} {'MaxDD':>10} {'Mo%+':>6} {'Days':>6} {'AvgD$':>8}"
    print(header)
    print(f"  {'-'*25} {'-'*12} {'-'*8} {'-'*8} {'-'*10} {'-'*6} {'-'*6} {'-'*8}")

    baseline_metrics = portfolio_results["Baseline (PB+ORB)"]["metrics"]
    for port_name, res in portfolio_results.items():
        m = res["metrics"]
        print(f"  {port_name:<25} "
              f"${m['total_pnl']:>10,.2f} "
              f"{m['sharpe']:>8.2f} "
              f"{m['calmar']:>8.2f} "
              f"${m['max_dd']:>8,.2f} "
              f"{m['profitable_months_pct']:>5.1f}% "
              f"{m['trading_days']:>6} "
              f"${m['avg_daily_pnl']:>6,.2f}")

    # Step 4: Delta vs baseline
    print("\n" + "=" * 70)
    print("  DELTA vs BASELINE")
    print("=" * 70)
    print(f"  {'Portfolio':<25} {'dPnL':>12} {'dSharpe':>9} {'dCalmar':>9} {'dMaxDD':>10} {'dMo%+':>7}")
    print(f"  {'-'*25} {'-'*12} {'-'*9} {'-'*9} {'-'*10} {'-'*7}")

    for port_name, res in portfolio_results.items():
        if port_name == "Baseline (PB+ORB)":
            continue
        m = res["metrics"]
        dpnl = m["total_pnl"] - baseline_metrics["total_pnl"]
        dsharp = m["sharpe"] - baseline_metrics["sharpe"]
        dcalm = m["calmar"] - baseline_metrics["calmar"]
        ddd = m["max_dd"] - baseline_metrics["max_dd"]  # positive = worse
        dmo = m["profitable_months_pct"] - baseline_metrics["profitable_months_pct"]

        # Indicators: + for improvement, - for degradation
        dd_indicator = "(worse)" if ddd > 0 else "(better)" if ddd < 0 else ""

        print(f"  {port_name:<25} "
              f"${dpnl:>+10,.2f} "
              f"{dsharp:>+9.2f} "
              f"{dcalm:>+9.2f} "
              f"${ddd:>+8,.2f} {dd_indicator:<8}"
              f"{dmo:>+6.1f}%")

    # Step 5: Correlation matrix
    print("\n" + "=" * 70)
    print("  DAILY PnL CORRELATION MATRIX")
    print("=" * 70)

    # Build correlation from all 4 strategies
    all_daily = pd.DataFrame({
        name: daily_pnl_series[name] for name in STRATEGIES
    }).fillna(0)

    # Use shorter labels for readability
    short_labels = {
        "PB-Trend MGC-Short": "PB-Short",
        "ORB-009 MGC-Long": "ORB-Long",
        "vix_atr_stops MNQ-Long": "VIX-Long",
        "pb_relaxed_filters MES-Short": "PBR-Short",
    }
    all_daily.columns = [short_labels.get(c, c) for c in all_daily.columns]

    corr = all_daily.corr()
    # Print as formatted table
    cols = corr.columns.tolist()
    header = f"  {'':>12}" + "".join(f"{c:>12}" for c in cols)
    print(header)
    for row_name in cols:
        row_str = f"  {row_name:>12}"
        for col_name in cols:
            val = corr.loc[row_name, col_name]
            row_str += f"{val:>12.3f}"
        print(row_str)

    # Step 6: Verdict
    print("\n" + "=" * 70)
    print("  VERDICT")
    print("=" * 70)

    for port_name in ["+vix_atr_stops", "+pb_relaxed_filters", "All 4 strategies"]:
        m = portfolio_results[port_name]["metrics"]
        b = baseline_metrics

        improvements = []
        degradations = []

        if m["sharpe"] > b["sharpe"]:
            improvements.append(f"Sharpe +{m['sharpe'] - b['sharpe']:.2f}")
        else:
            degradations.append(f"Sharpe {m['sharpe'] - b['sharpe']:.2f}")

        if m["calmar"] > b["calmar"]:
            improvements.append(f"Calmar +{m['calmar'] - b['calmar']:.2f}")
        else:
            degradations.append(f"Calmar {m['calmar'] - b['calmar']:.2f}")

        if m["max_dd"] < b["max_dd"]:
            improvements.append(f"MaxDD ${b['max_dd'] - m['max_dd']:,.0f} better")
        else:
            degradations.append(f"MaxDD ${m['max_dd'] - b['max_dd']:,.0f} worse")

        if m["profitable_months_pct"] > b["profitable_months_pct"]:
            improvements.append(f"Mo%+ +{m['profitable_months_pct'] - b['profitable_months_pct']:.1f}%")

        verdict = "IMPROVES" if len(improvements) >= 2 else "MIXED" if improvements else "DEGRADES"
        print(f"\n  {port_name}:")
        print(f"    Verdict: {verdict}")
        if improvements:
            print(f"    Better:  {', '.join(improvements)}")
        if degradations:
            print(f"    Worse:   {', '.join(degradations)}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
