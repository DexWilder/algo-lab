"""Phase 16 — Strategy Controller Simulation.

Compares baseline always-on portfolio vs controller-managed portfolio.
Tests regime gating, soft timing preferences, and portfolio coordination.

Portfolio (6 strategies):
1. PB-MGC-Short (core parent)
2. ORB-MGC-Long (core parent)
3. VWAP-MNQ-Long (core parent)
4. XB-PB-EMA-MES-Short (core parent)
5. BB-EQ-MGC-Long / Gold Snapback (core parent)
6. Donchian-MNQ-Long-GRINDING (probation)

Usage:
    python3 research/phase16_strategy_controller.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from engine.strategy_controller import StrategyController, PORTFOLIO_CONFIG
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent
STARTING_CAPITAL = 50_000.0


def load_strategy(name: str):
    path = ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_daily_pnl(trades_df: pd.DataFrame) -> pd.Series:
    if trades_df.empty:
        return pd.Series(dtype=float)
    tmp = trades_df.copy()
    tmp["date"] = pd.to_datetime(tmp["exit_time"]).dt.date
    daily = tmp.groupby("date")["pnl"].sum()
    daily.index = pd.to_datetime(daily.index)
    return daily


def portfolio_metrics(port_daily: pd.Series, trade_count: int) -> dict:
    if port_daily.empty or port_daily.std() == 0:
        return {"total_pnl": 0, "sharpe": 0, "calmar": 0, "maxdd": 0,
                "trades": 0, "monthly_pct": 0, "trading_days": 0}

    total_pnl = port_daily.sum()
    sharpe = port_daily.mean() / port_daily.std() * np.sqrt(252)

    equity = STARTING_CAPITAL + port_daily.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    maxdd = dd.max()
    calmar = total_pnl / maxdd if maxdd > 0 else 0

    monthly = port_daily.resample("ME").sum()
    profitable = (monthly > 0).sum()
    total = len(monthly)
    monthly_pct = profitable / total * 100 if total > 0 else 0

    return {
        "total_pnl": total_pnl,
        "sharpe": sharpe,
        "calmar": calmar,
        "maxdd": maxdd,
        "trades": trade_count,
        "profitable_months": f"{profitable}/{total}",
        "monthly_pct": monthly_pct,
        "trading_days": len(port_daily[port_daily != 0]),
    }


def monte_carlo(port_daily: pd.Series, n_sims: int = 10_000,
                seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    arr = port_daily.values
    n = len(arr)
    if n == 0:
        return {}

    ruin_thresholds = [1000, 2000, 3000, 4000]
    ruin_counts = {t: 0 for t in ruin_thresholds}
    max_dds = []

    for _ in range(n_sims):
        shuffled = rng.choice(arr, size=n, replace=True)
        eq = STARTING_CAPITAL + np.cumsum(shuffled)
        pk = np.maximum.accumulate(eq)
        sim_dd = (pk - eq).max()
        max_dds.append(sim_dd)
        for t in ruin_thresholds:
            if sim_dd >= t:
                ruin_counts[t] += 1

    max_dds = np.array(max_dds)
    return {
        "ruin_probs": {f"${t}": ruin_counts[t] / n_sims * 100 for t in ruin_thresholds},
        "median_maxdd": float(np.median(max_dds)),
        "p95_maxdd": float(np.percentile(max_dds, 95)),
        "p99_maxdd": float(np.percentile(max_dds, 99)),
    }


def run_all_strategies_baseline(engine: RegimeEngine) -> tuple:
    """Run all strategies always-on (no controller filtering).

    Returns (baseline_trades, daily_pnls, strat_metrics, data_cache, regime_daily_cache).
    """
    strat_configs = PORTFOLIO_CONFIG["strategies"]
    baseline_trades = {}
    daily_pnls = {}
    strat_metrics = {}
    data_cache = {}
    regime_daily_cache = {}

    for strat_key, strat in strat_configs.items():
        asset = strat["asset"]
        config = ASSET_CONFIG[asset]

        # Load data (cache by asset)
        if asset not in data_cache:
            df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
            df["datetime"] = pd.to_datetime(df["datetime"])
            data_cache[asset] = df
            regime_daily_cache[asset] = engine.get_daily_regimes(df)
        df = data_cache[asset]

        # Load & run strategy
        mod = load_strategy(strat["name"])
        if hasattr(mod, "TICK_SIZE"):
            mod.TICK_SIZE = config["tick_size"]

        # Handle exit variants
        if strat.get("exit_variant") == "profit_ladder":
            from research.exit_evolution import donchian_entries, apply_profit_ladder
            data = donchian_entries(df)
            signals = apply_profit_ladder(data)
        else:
            signals = mod.generate_signals(df)

        result = run_backtest(
            df, signals,
            mode=strat["mode"],
            point_value=config["point_value"],
            symbol=asset,
        )
        trades = result["trades_df"]

        # Apply GRINDING filter at baseline level for Donchian
        if strat.get("grinding_filter") and not trades.empty:
            rd = regime_daily_cache[asset].copy()
            rd["_date"] = pd.to_datetime(rd["_date"])
            rd["_date_date"] = rd["_date"].dt.date
            trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
            trades = trades.merge(
                rd[["_date_date", "trend_persistence"]],
                left_on="entry_date", right_on="_date_date", how="left",
            )
            trades = trades[trades["trend_persistence"] == "GRINDING"]
            trades = trades.drop(
                columns=["entry_date", "_date_date", "trend_persistence"],
                errors="ignore",
            ).reset_index(drop=True)

        baseline_trades[strat_key] = trades
        daily_pnls[strat_key] = get_daily_pnl(trades)

        eq = pd.Series(STARTING_CAPITAL + np.cumsum(
            np.concatenate([[0], trades["pnl"].values if not trades.empty else []])
        ))
        strat_metrics[strat_key] = (
            compute_extended_metrics(trades, eq, config["point_value"])
            if not trades.empty else {}
        )

    return baseline_trades, daily_pnls, strat_metrics, data_cache, regime_daily_cache


def build_portfolio_daily(daily_pnls: dict) -> pd.Series:
    """Combine per-strategy daily PnLs into portfolio daily PnL."""
    if not daily_pnls:
        return pd.Series(dtype=float)
    combined = pd.DataFrame(daily_pnls).fillna(0)
    return combined.sum(axis=1).sort_index()


def time_distribution(trades_dict: dict) -> dict:
    """Analyze entry time distribution by hour."""
    all_entries = []
    for strat_key, trades in trades_dict.items():
        if trades.empty:
            continue
        t = trades.copy()
        t["hour"] = pd.to_datetime(t["entry_time"]).dt.hour
        all_entries.append(t[["hour"]])

    if not all_entries:
        return {}

    combined = pd.concat(all_entries, ignore_index=True)
    dist = combined["hour"].value_counts().sort_index()
    return {str(h): int(c) for h, c in dist.items()}


def print_comparison(baseline_m: dict, controlled_m: dict):
    """Print side-by-side comparison table."""
    print(f"\n  {'Metric':<25} {'Baseline':>15} {'Controlled':>15} {'Delta':>12}")
    print(f"  {'-'*25} {'-'*15} {'-'*15} {'-'*12}")

    rows = [
        ("Total PnL", "total_pnl", "${:,.0f}", "${:+,.0f}"),
        ("Sharpe", "sharpe", "{:.2f}", "{:+.2f}"),
        ("Calmar", "calmar", "{:.2f}", "{:+.2f}"),
        ("Max Drawdown", "maxdd", "${:,.0f}", "${:+,.0f}"),
        ("Trades", "trades", "{:,}", "{:+,}"),
        ("Monthly %", "monthly_pct", "{:.0f}%", "{:+.0f}%"),
        ("Trading Days", "trading_days", "{:,}", "{:+,}"),
    ]

    for label, key, fmt, delta_fmt in rows:
        b = baseline_m[key]
        c = controlled_m[key]
        delta = c - b
        # For MaxDD, negative delta is good
        print(f"  {label:<25} {fmt.format(b):>15} {fmt.format(c):>15} "
              f"{delta_fmt.format(delta):>12}")


def main():
    engine = RegimeEngine()
    controller = StrategyController(PORTFOLIO_CONFIG)

    print("=" * 78)
    print("  PHASE 16 — STRATEGY CONTROLLER SIMULATION")
    print("=" * 78)

    # ── Step 1: Run baseline (always-on) ─────────────────────────────────
    print("\n  Step 1: Running baseline (always-on) portfolio...")
    (baseline_trades, baseline_daily, baseline_metrics,
     data_cache, regime_daily_cache) = run_all_strategies_baseline(engine)

    for strat_key, metrics in baseline_metrics.items():
        tc = metrics.get("trade_count", len(baseline_trades[strat_key]))
        pf = metrics.get("profit_factor", 0)
        pnl = metrics.get("total_pnl", 0)
        print(f"    {strat_key}: {tc} trades, PF={pf:.2f}, PnL=${pnl:,.0f}")

    baseline_port_daily = build_portfolio_daily(baseline_daily)
    baseline_port_trades = sum(len(t) for t in baseline_trades.values())
    baseline_port_m = portfolio_metrics(baseline_port_daily, baseline_port_trades)

    print(f"\n  Baseline portfolio: {baseline_port_trades} trades, "
          f"Sharpe={baseline_port_m['sharpe']:.2f}, "
          f"PnL=${baseline_port_m['total_pnl']:,.0f}")

    # ── Step 2: Run controller simulation ────────────────────────────────
    print(f"\n  Step 2: Running controller simulation...")
    ctrl_result = controller.simulate(baseline_trades, regime_daily_cache)

    controlled_trades = ctrl_result["filtered_trades"]
    filter_stats = ctrl_result["filter_stats"]
    portfolio_stats = ctrl_result["portfolio_stats"]

    # ── Step 3: Per-strategy filter report ───────────────────────────────
    print(f"\n{'='*78}")
    print(f"  PER-STRATEGY FILTER REPORT")
    print(f"{'='*78}\n")

    print(f"  {'Strategy':<30} {'Total':>6} {'Kept':>6} {'Regime':>8} "
          f"{'Timing':>8} {'Conv':>6} {'Coord':>6}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*8} {'-'*8} {'-'*6} {'-'*6}")

    total_baseline = 0
    total_kept = 0

    for strat_key in PORTFOLIO_CONFIG["strategies"]:
        fs = filter_stats[strat_key]
        ps = portfolio_stats[strat_key]
        total = fs["total"]
        kept_post_regime = fs["kept"]
        final = ps["post_coordination"]
        coord_filtered = ps["coordination_filtered"]

        total_baseline += total
        total_kept += final

        print(f"  {strat_key:<30} {total:>6} {final:>6} "
              f"{fs['regime_blocked']:>8} {fs['timing_blocked']:>8} "
              f"{fs['conviction_override']:>6} {coord_filtered:>6}")

    pct_kept = total_kept / total_baseline * 100 if total_baseline > 0 else 0
    print(f"  {'-'*30} {'-'*6} {'-'*6}")
    print(f"  {'TOTAL':<30} {total_baseline:>6} {total_kept:>6} "
          f"({pct_kept:.0f}% kept)")

    # ── Step 4: Controlled portfolio metrics ─────────────────────────────
    controlled_daily = {}
    for strat_key, trades in controlled_trades.items():
        controlled_daily[strat_key] = get_daily_pnl(trades)

    ctrl_port_daily = build_portfolio_daily(controlled_daily)
    ctrl_port_trades = sum(len(t) for t in controlled_trades.values())
    ctrl_port_m = portfolio_metrics(ctrl_port_daily, ctrl_port_trades)

    # ── Step 5: Side-by-side comparison ──────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  PORTFOLIO COMPARISON: BASELINE vs CONTROLLER")
    print(f"{'='*78}")

    print_comparison(baseline_port_m, ctrl_port_m)

    # ── Step 6: Per-strategy PnL impact ──────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  PER-STRATEGY PNL IMPACT")
    print(f"{'='*78}\n")

    print(f"  {'Strategy':<30} {'Base PnL':>10} {'Ctrl PnL':>10} "
          f"{'Delta':>10} {'Base Tr':>8} {'Ctrl Tr':>8}")
    print(f"  {'-'*30} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")

    for strat_key in PORTFOLIO_CONFIG["strategies"]:
        b_pnl = baseline_daily.get(strat_key, pd.Series(dtype=float)).sum()
        c_pnl = controlled_daily.get(strat_key, pd.Series(dtype=float)).sum()
        delta = c_pnl - b_pnl
        b_tc = len(baseline_trades[strat_key])
        c_tc = len(controlled_trades[strat_key])
        print(f"  {strat_key:<30} ${b_pnl:>8,.0f} ${c_pnl:>8,.0f} "
              f"${delta:>+8,.0f} {b_tc:>8} {c_tc:>8}")

    # ── Step 7: Correlation matrix (controlled) ──────────────────────────
    print(f"\n{'='*78}")
    print(f"  CORRELATION MATRIX (CONTROLLED)")
    print(f"{'='*78}\n")

    ctrl_df = pd.DataFrame(controlled_daily).fillna(0)
    if ctrl_df.shape[1] > 1:
        corr = ctrl_df.corr()
        short = {k: k.split("-")[0][:5] for k in PORTFOLIO_CONFIG["strategies"]}

        header = "  " + " " * 8
        for k in PORTFOLIO_CONFIG["strategies"]:
            header += f"{short[k]:>8}"
        print(header)

        for k1 in PORTFOLIO_CONFIG["strategies"]:
            row = f"  {short[k1]:<8}"
            for k2 in PORTFOLIO_CONFIG["strategies"]:
                if k1 in corr.columns and k2 in corr.columns:
                    row += f"{corr.loc[k1, k2]:>8.3f}"
                else:
                    row += f"{'N/A':>8}"
            print(row)

    # ── Step 8: Entry time distribution ──────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  ENTRY TIME DISTRIBUTION")
    print(f"{'='*78}\n")

    base_dist = time_distribution(baseline_trades)
    ctrl_dist = time_distribution(controlled_trades)

    print(f"  {'Hour':>6} {'Baseline':>10} {'Controlled':>12} {'Delta':>8}")
    print(f"  {'-'*6} {'-'*10} {'-'*12} {'-'*8}")

    all_hours = sorted(set(list(base_dist.keys()) + list(ctrl_dist.keys())))
    for h in all_hours:
        b = base_dist.get(h, 0)
        c = ctrl_dist.get(h, 0)
        d = c - b
        print(f"  {h:>6} {b:>10} {c:>12} {d:>+8}")

    # ── Step 9: Monthly comparison ───────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  MONTHLY BREAKDOWN")
    print(f"{'='*78}\n")

    if not baseline_port_daily.empty and not ctrl_port_daily.empty:
        b_monthly = baseline_port_daily.resample("ME").sum()
        c_monthly = ctrl_port_daily.resample("ME").sum()

        # Align
        all_months = b_monthly.index.union(c_monthly.index)
        b_monthly = b_monthly.reindex(all_months, fill_value=0)
        c_monthly = c_monthly.reindex(all_months, fill_value=0)

        print(f"  {'Month':<10} {'Baseline':>10} {'Controlled':>12} {'Delta':>10}")
        print(f"  {'-'*10} {'-'*10} {'-'*12} {'-'*10}")

        for dt in all_months:
            b = b_monthly[dt]
            c = c_monthly[dt]
            d = c - b
            print(f"  {dt.strftime('%Y-%m'):<10} ${b:>8,.0f} ${c:>10,.0f} ${d:>+8,.0f}")

        b_neg = (b_monthly < 0).sum()
        c_neg = (c_monthly < 0).sum()
        print(f"\n  Losing months: Baseline={b_neg}, Controlled={c_neg}")

    # ── Step 10: Drawdown analysis ───────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  DRAWDOWN ANALYSIS")
    print(f"{'='*78}\n")

    for label, daily in [("Baseline", baseline_port_daily),
                         ("Controlled", ctrl_port_daily)]:
        if daily.empty:
            continue
        equity = STARTING_CAPITAL + daily.cumsum()
        peak = equity.cummax()
        dd = peak - equity
        maxdd = dd.max()
        maxdd_date = dd.idxmax()
        print(f"  {label}:")
        print(f"    MaxDD: ${maxdd:,.0f} on {maxdd_date}")

        if maxdd > 0:
            recovery = equity[maxdd_date:][equity[maxdd_date:] >= peak[maxdd_date]]
            if len(recovery) > 0:
                rec_days = (recovery.index[0] - maxdd_date).days
                print(f"    Recovery: {rec_days} calendar days")
            else:
                print(f"    Recovery: not yet recovered")

    # ── Step 11: Clustered drawdown analysis ─────────────────────────────
    print(f"\n{'='*78}")
    print(f"  CLUSTERED DRAWDOWN REDUCTION")
    print(f"{'='*78}\n")

    # Find worst 5-day drawdowns
    for label, daily in [("Baseline", baseline_port_daily),
                         ("Controlled", ctrl_port_daily)]:
        if daily.empty:
            continue
        rolling_5d = daily.rolling(5).sum()
        worst_5d = rolling_5d.nsmallest(5)
        print(f"  {label} — Worst 5-day drawdowns:")
        for dt, val in worst_5d.items():
            print(f"    {dt.strftime('%Y-%m-%d')}: ${val:,.0f}")
        print()

    # ── Step 12: Monte Carlo ─────────────────────────────────────────────
    print(f"{'='*78}")
    print(f"  MONTE CARLO SIMULATION (10K reshuffles)")
    print(f"{'='*78}\n")

    for label, daily in [("Baseline", baseline_port_daily),
                         ("Controlled", ctrl_port_daily)]:
        if daily.empty:
            continue
        mc = monte_carlo(daily)
        print(f"  {label}:")
        print(f"    Median MaxDD:  ${mc['median_maxdd']:,.0f}")
        print(f"    95th pct:      ${mc['p95_maxdd']:,.0f}")
        print(f"    99th pct:      ${mc['p99_maxdd']:,.0f}")
        for t_label, prob in mc["ruin_probs"].items():
            status = "PASS" if prob < 5 else "FAIL"
            print(f"    P(ruin at {t_label}): {prob:.1f}% [{status}]")
        print()

    # ── Step 13: Verdict ─────────────────────────────────────────────────
    print(f"{'='*78}")
    print(f"  CONTROLLER VERDICT")
    print(f"{'='*78}\n")

    checks = [
        ("PnL preserved (≥90% of baseline)",
         ctrl_port_m["total_pnl"] >= baseline_port_m["total_pnl"] * 0.90,
         f"${baseline_port_m['total_pnl']:,.0f} → ${ctrl_port_m['total_pnl']:,.0f}"),

        ("Sharpe improved or preserved",
         ctrl_port_m["sharpe"] >= baseline_port_m["sharpe"] * 0.95,
         f"{baseline_port_m['sharpe']:.2f} → {ctrl_port_m['sharpe']:.2f}"),

        ("MaxDD reduced",
         ctrl_port_m["maxdd"] <= baseline_port_m["maxdd"],
         f"${baseline_port_m['maxdd']:,.0f} → ${ctrl_port_m['maxdd']:,.0f}"),

        ("Monthly consistency preserved",
         ctrl_port_m["monthly_pct"] >= baseline_port_m["monthly_pct"] - 5,
         f"{baseline_port_m['monthly_pct']:.0f}% → {ctrl_port_m['monthly_pct']:.0f}%"),

        ("Trade reduction < 40%",
         ctrl_port_m["trades"] >= baseline_port_m["trades"] * 0.60,
         f"{baseline_port_m['trades']} → {ctrl_port_m['trades']}"),
    ]

    passes = 0
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if passed:
            passes += 1
        print(f"  [{status}] {name}")
        print(f"         {detail}")

    print(f"\n  Score: {passes}/5")
    if passes >= 4:
        print(f"  VERDICT: CONTROLLER IMPROVES PORTFOLIO — deploy to prop simulation")
    elif passes >= 3:
        print(f"  VERDICT: PROMISING — tune parameters and re-test")
    else:
        print(f"  VERDICT: CONTROLLER HURTS PORTFOLIO — review configuration")

    print(f"\n{'='*78}")
    print(f"  DONE")
    print(f"{'='*78}")

    # ── Save results ─────────────────────────────────────────────────────
    results = {
        "baseline": {k: v for k, v in baseline_port_m.items()},
        "controlled": {k: v for k, v in ctrl_port_m.items()},
        "filter_stats": {k: v for k, v in filter_stats.items()},
        "portfolio_stats": {k: v for k, v in portfolio_stats.items()},
        "per_strategy_pnl": {
            strat_key: {
                "baseline_pnl": float(baseline_daily.get(strat_key,
                    pd.Series(dtype=float)).sum()),
                "controlled_pnl": float(controlled_daily.get(strat_key,
                    pd.Series(dtype=float)).sum()),
                "baseline_trades": len(baseline_trades[strat_key]),
                "controlled_trades": len(controlled_trades[strat_key]),
            }
            for strat_key in PORTFOLIO_CONFIG["strategies"]
        },
        "time_distribution": {
            "baseline": base_dist,
            "controlled": ctrl_dist,
        },
        "verdict_score": passes,
    }

    out_path = OUTPUT_DIR / "phase16_strategy_controller_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved to: {out_path}")


if __name__ == "__main__":
    main()
