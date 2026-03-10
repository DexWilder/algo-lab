"""Phase 12 — 5-Strategy Portfolio Simulation.

Tests deployable portfolio of:
1. PB-MGC-Short (core parent)
2. ORB-MGC-Long (core parent)
3. VWAP-Trend MNQ-Long (Phase 11 parent)
4. XB-PB-EMA-TimeStop MES-Short (Phase 12 parent)
5. Donchian MNQ-Long GRINDING+PL (probation)

Compares against 3-strategy baseline (PB + ORB + VWAP Trend).

Tasks:
- Combined equity curve + portfolio metrics
- Pairwise correlation matrix
- Monte Carlo simulation at portfolio level
- Regime PnL heatmap (per-strategy + total per cell)
- Monthly consistency analysis

Usage:
    python3 research/phase12_portfolio.py
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
from engine.statistics import bootstrap_metrics
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG

PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = Path(__file__).resolve().parent
STARTING_CAPITAL = 50_000.0

STRATEGIES = [
    {"name": "pb_trend", "asset": "MGC", "mode": "short",
     "label": "PB-MGC-Short", "grinding_filter": False,
     "exit_variant": None},
    {"name": "orb_009", "asset": "MGC", "mode": "long",
     "label": "ORB-MGC-Long", "grinding_filter": False,
     "exit_variant": None},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long",
     "label": "VWAP-MNQ-Long", "grinding_filter": False,
     "exit_variant": None},
    {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short",
     "label": "XB-PB-EMA-MES-Short", "grinding_filter": False,
     "exit_variant": None},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long",
     "label": "Donchian-MNQ-Long-GRINDING", "grinding_filter": True,
     "exit_variant": "profit_ladder"},
]


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


def run_strategy(strat: dict, engine: RegimeEngine) -> tuple:
    """Run a single strategy, return (daily_pnl, trades_df, metrics)."""
    asset = strat["asset"]
    config = ASSET_CONFIG[asset]

    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    mod = load_strategy(strat["name"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]
    signals = mod.generate_signals(df)

    # Apply Profit Ladder exit if specified
    if strat.get("exit_variant") == "profit_ladder":
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        data = donchian_entries(df)
        pl_signals_df = apply_profit_ladder(data)
        result = run_backtest(
            df, pl_signals_df,
            mode=strat["mode"],
            point_value=config["point_value"],
            symbol=asset,
        )
        trades = result["trades_df"]
    else:
        result = run_backtest(
            df, signals,
            mode=strat["mode"],
            point_value=config["point_value"],
            symbol=asset,
        )
        trades = result["trades_df"]

    # GRINDING filter
    if strat.get("grinding_filter") and not trades.empty:
        regime_daily = engine.get_daily_regimes(df)
        regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
        regime_daily["_date_date"] = regime_daily["_date"].dt.date

        trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.date
        trades = trades.merge(
            regime_daily[["_date_date", "trend_persistence"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )
        trades = trades[trades["trend_persistence"] == "GRINDING"]
        trades = trades.drop(
            columns=["entry_date", "_date_date", "trend_persistence"],
            errors="ignore",
        )

    daily = get_daily_pnl(trades)

    eq = pd.Series(STARTING_CAPITAL + np.cumsum(
        np.concatenate([[0], trades["pnl"].values if not trades.empty else []])
    ))
    metrics = (
        compute_extended_metrics(trades, eq, config["point_value"])
        if not trades.empty else {}
    )

    return daily, trades, metrics, df


def portfolio_metrics(port_daily: pd.Series, label: str, trade_count: int) -> dict:
    total_pnl = port_daily.sum()
    sharpe = (port_daily.mean() / port_daily.std() * np.sqrt(252)
              if port_daily.std() > 0 else 0)

    equity = STARTING_CAPITAL + port_daily.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    maxdd = dd.max()
    calmar = total_pnl / maxdd if maxdd > 0 else 0

    monthly = port_daily.resample("ME").sum()
    profitable_months = (monthly > 0).sum()
    total_months = len(monthly)
    monthly_pct = profitable_months / total_months * 100 if total_months > 0 else 0

    return {
        "label": label,
        "total_pnl": total_pnl,
        "sharpe": sharpe,
        "calmar": calmar,
        "maxdd": maxdd,
        "trades": trade_count,
        "profitable_months_str": f"{profitable_months}/{total_months} ({monthly_pct:.0f}%)",
        "profitable_months_pct": monthly_pct,
        "trading_days": len(port_daily[port_daily != 0]),
    }


def monte_carlo_portfolio(port_daily: pd.Series, n_sims: int = 10_000,
                          seed: int = 42) -> dict:
    """Monte Carlo simulation on portfolio daily PnL."""
    rng = np.random.default_rng(seed)
    daily_arr = port_daily.values
    n_days = len(daily_arr)
    if n_days == 0:
        return {}

    ruin_counts = {floor: 0 for floor in [1000, 2000, 3000, 4000, 5000]}
    max_dds = []

    for _ in range(n_sims):
        shuffled = rng.choice(daily_arr, size=n_days, replace=True)
        equity = STARTING_CAPITAL + np.cumsum(shuffled)
        peak = np.maximum.accumulate(equity)
        dd = peak - equity
        sim_maxdd = dd.max()
        max_dds.append(sim_maxdd)
        for floor, count in ruin_counts.items():
            if sim_maxdd >= floor:
                ruin_counts[floor] += 1

    max_dds = np.array(max_dds)
    return {
        "ruin_probs": {f"${k}": v / n_sims * 100 for k, v in ruin_counts.items()},
        "median_maxdd": float(np.median(max_dds)),
        "p95_maxdd": float(np.percentile(max_dds, 95)),
        "p99_maxdd": float(np.percentile(max_dds, 99)),
        "n_sims": n_sims,
    }


def regime_heatmap(all_trades: dict, strategies: list, engine: RegimeEngine,
                   data_cache: dict) -> pd.DataFrame:
    """Build regime PnL heatmap: strategies × regime cells."""
    rows = []
    for strat in strategies:
        label = strat["label"]
        trades = all_trades[label]
        if trades.empty:
            continue

        asset = strat["asset"]
        df = data_cache[asset]
        regime_daily = engine.get_daily_regimes(df)
        regime_daily["_date"] = pd.to_datetime(regime_daily["_date"])
        regime_daily["_date_date"] = regime_daily["_date"].dt.date

        t = trades.copy()
        t["entry_date"] = pd.to_datetime(t["entry_time"]).dt.date
        t = t.merge(
            regime_daily[["_date_date", "composite_regime", "rv_regime"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )
        t["full_regime"] = t["composite_regime"] + "_" + t["rv_regime"].fillna("UNKNOWN")

        for cell, grp in t.groupby("full_regime"):
            rows.append({
                "strategy": label,
                "regime": cell,
                "trades": len(grp),
                "pnl": grp["pnl"].sum(),
                "wr": (grp["pnl"] > 0).mean(),
            })

    return pd.DataFrame(rows)


def main():
    engine = RegimeEngine()

    print("=" * 78)
    print("  PHASE 12 — 5-STRATEGY PORTFOLIO SIMULATION")
    print("=" * 78)

    # ── Run all strategies ─────────────────────────────────────────────
    daily_pnls = {}
    all_trades = {}
    strat_metrics = {}
    total_trades_map = {}
    data_cache = {}

    for strat in STRATEGIES:
        label = strat["label"]
        print(f"\n  Running {label}...")
        daily, trades, metrics, df_raw = run_strategy(strat, engine)
        daily_pnls[label] = daily
        all_trades[label] = trades
        strat_metrics[label] = metrics
        total_trades_map[label] = len(trades)
        data_cache[strat["asset"]] = df_raw
        tc = len(trades)
        pf = metrics.get("profit_factor", 0)
        pnl = metrics.get("total_pnl", 0)
        sh = metrics.get("sharpe", 0)
        print(f"    {tc} trades, PF={pf:.2f}, Sharpe={sh:.2f}, PnL=${pnl:,.0f}")

    # ── Build portfolios ───────────────────────────────────────────────
    all_labels = [s["label"] for s in STRATEGIES]

    # 3-strategy baseline (parents only)
    base3_labels = ["PB-MGC-Short", "ORB-MGC-Long", "VWAP-MNQ-Long"]
    base3_df = pd.DataFrame({l: daily_pnls[l] for l in base3_labels}).fillna(0)
    base3_daily = base3_df.sum(axis=1).sort_index()
    base3_trades = sum(total_trades_map[l] for l in base3_labels)

    # 4-strategy (add XB-PB-EMA)
    four_labels = base3_labels + ["XB-PB-EMA-MES-Short"]
    four_df = pd.DataFrame({l: daily_pnls[l] for l in four_labels}).fillna(0)
    four_daily = four_df.sum(axis=1).sort_index()
    four_trades = sum(total_trades_map[l] for l in four_labels)

    # 5-strategy full
    full_df = pd.DataFrame({l: daily_pnls[l] for l in all_labels}).fillna(0)
    full_daily = full_df.sum(axis=1).sort_index()
    full_trades = sum(total_trades_map[l] for l in all_labels)

    # ── Compute metrics ────────────────────────────────────────────────
    base3_m = portfolio_metrics(base3_daily, "3-Strat Baseline", base3_trades)
    four_m = portfolio_metrics(four_daily, "4-Strat (+XB-PB-EMA)", four_trades)
    full_m = portfolio_metrics(full_daily, "5-Strat (Full)", full_trades)

    # ── PORTFOLIO COMPARISON ───────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  PORTFOLIO COMPARISON")
    print(f"{'='*78}")

    headers = ["Metric", "3-Strat Baseline", "4-Strat (+MES)", "5-Strat (Full)"]
    print(f"\n  {headers[0]:<22} {headers[1]:>18} {headers[2]:>18} {headers[3]:>18}")
    print(f"  {'-'*22} {'-'*18} {'-'*18} {'-'*18}")

    for key, fmt in [
        ("total_pnl", "${:,.0f}"),
        ("sharpe", "{:.2f}"),
        ("calmar", "{:.2f}"),
        ("maxdd", "${:,.0f}"),
        ("trades", "{:,}"),
        ("profitable_months_str", "{}"),
        ("trading_days", "{:,}"),
    ]:
        label = key.replace("_str", "").replace("_", " ").title()
        v1 = fmt.format(base3_m[key])
        v2 = fmt.format(four_m[key])
        v3 = fmt.format(full_m[key])
        print(f"  {label:<22} {v1:>18} {v2:>18} {v3:>18}")

    # ── PAIRWISE CORRELATION MATRIX ────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  DAILY PNL CORRELATION MATRIX (5 STRATEGIES)")
    print(f"{'='*78}\n")

    corr = full_df.corr()
    short_labels = {
        "PB-MGC-Short": "PB",
        "ORB-MGC-Long": "ORB",
        "VWAP-MNQ-Long": "VWAP",
        "XB-PB-EMA-MES-Short": "XB-PB",
        "Donchian-MNQ-Long-GRINDING": "DONCH",
    }

    header = "  " + " " * 8
    for l in all_labels:
        header += f"{short_labels[l]:>8}"
    print(header)

    for l1 in all_labels:
        row = f"  {short_labels[l1]:<8}"
        for l2 in all_labels:
            val = corr.loc[l1, l2]
            row += f"{val:>8.3f}"
        print(row)

    # Max off-diagonal correlation
    mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
    max_corr = corr.where(mask).max().max()
    max_pair = None
    for l1 in all_labels:
        for l2 in all_labels:
            if l1 != l2 and corr.loc[l1, l2] == max_corr:
                max_pair = (short_labels[l1], short_labels[l2])
                break
    print(f"\n  Max off-diagonal: r={max_corr:.3f} ({max_pair[0]} vs {max_pair[1]})"
          if max_pair else "")

    # ── PER-STRATEGY CONTRIBUTION ──────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  PER-STRATEGY CONTRIBUTION")
    print(f"{'='*78}\n")

    print(f"  {'Strategy':<35} {'PnL':>10} {'%':>7} {'Trades':>8} "
          f"{'PF':>6} {'Sharpe':>7}")
    print(f"  {'-'*35} {'-'*10} {'-'*7} {'-'*8} {'-'*6} {'-'*7}")

    for label in all_labels:
        daily = daily_pnls[label]
        pnl = daily.sum()
        trades_n = total_trades_map[label]
        pct = pnl / full_m["total_pnl"] * 100 if full_m["total_pnl"] != 0 else 0
        pf = strat_metrics[label].get("profit_factor", 0)
        sh = strat_metrics[label].get("sharpe", 0)
        print(f"  {label:<35} ${pnl:>8,.0f} {pct:>6.1f}% {trades_n:>8} "
              f"{pf:>6.2f} {sh:>7.2f}")

    print(f"  {'-'*35} {'-'*10}")
    print(f"  {'TOTAL':<35} ${full_m['total_pnl']:>8,.0f}")

    # ── MONTE CARLO (PORTFOLIO LEVEL) ──────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  MONTE CARLO SIMULATION (10K RESHUFFLES)")
    print(f"{'='*78}\n")

    for label, daily in [("3-Strat Baseline", base3_daily),
                         ("5-Strat Full", full_daily)]:
        mc = monte_carlo_portfolio(daily)
        print(f"  {label}:")
        print(f"    Median MaxDD:  ${mc['median_maxdd']:,.0f}")
        print(f"    95th pct MaxDD: ${mc['p95_maxdd']:,.0f}")
        print(f"    99th pct MaxDD: ${mc['p99_maxdd']:,.0f}")
        for floor_label, prob in mc["ruin_probs"].items():
            status = "PASS" if prob < 5 else "FAIL"
            print(f"    P(ruin at {floor_label}): {prob:.1f}% [{status}]")
        print()

    # ── BOOTSTRAP CI (PORTFOLIO LEVEL) ─────────────────────────────────
    print(f"  BOOTSTRAP CONFIDENCE INTERVALS (10K resamples)")
    print(f"  {'-'*60}")

    # Combine all trades for portfolio-level bootstrap
    all_port_trades = pd.concat(
        [all_trades[l] for l in all_labels if not all_trades[l].empty],
        ignore_index=True,
    )
    if not all_port_trades.empty:
        bs = bootstrap_metrics(all_port_trades["pnl"].values)
        print(f"    Portfolio PF:  {bs['pf']['point_estimate']:.3f}")
        print(f"    PF 95% CI:    [{bs['pf']['ci_low']:.3f}, {bs['pf']['ci_high']:.3f}]")
        print(f"    CI low > 1.0: {'YES' if bs['pf']['ci_low'] > 1.0 else 'NO'}")

    # ── REGIME PNL HEATMAP ─────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  REGIME PNL HEATMAP (PORTFOLIO)")
    print(f"{'='*78}\n")

    regime_df = regime_heatmap(all_trades, STRATEGIES, engine, data_cache)

    if not regime_df.empty:
        # Portfolio total by regime cell
        port_regime = regime_df.groupby("regime").agg(
            trades=("trades", "sum"),
            pnl=("pnl", "sum"),
        ).sort_values("pnl", ascending=False)

        print(f"  {'Regime Cell':<40} {'Trades':>7} {'PnL':>10} {'Avg':>8}")
        print(f"  {'-'*40} {'-'*7} {'-'*10} {'-'*8}")

        for cell, row in port_regime.iterrows():
            avg = row["pnl"] / row["trades"] if row["trades"] > 0 else 0
            print(f"  {cell:<40} {row['trades']:>7} ${row['pnl']:>8,.0f} "
                  f"${avg:>7,.0f}")

        total_pnl = port_regime["pnl"].sum()
        total_trades = port_regime["trades"].sum()
        print(f"  {'-'*40} {'-'*7} {'-'*10}")
        print(f"  {'TOTAL':<40} {total_trades:>7} ${total_pnl:>8,.0f}")

        # Concentration risk
        print(f"\n  CONCENTRATION RISK:")
        for cell, row in port_regime.head(3).iterrows():
            pct = row["pnl"] / total_pnl * 100 if total_pnl > 0 else 0
            print(f"    {cell}: {pct:.1f}% of total PnL")

        # Per-strategy regime breakdown (top 5 cells only)
        print(f"\n  PER-STRATEGY REGIME CONTRIBUTION (top 5 cells):")
        top_cells = port_regime.head(5).index.tolist()
        header_strats = [short_labels[l] for l in all_labels]
        print(f"  {'Cell':<35} " + " ".join(f"{s:>8}" for s in header_strats))
        print(f"  {'-'*35} " + " ".join("-" * 8 for _ in header_strats))

        for cell in top_cells:
            row_str = f"  {cell:<35}"
            for label in all_labels:
                cell_data = regime_df[
                    (regime_df["strategy"] == label) & (regime_df["regime"] == cell)
                ]
                if len(cell_data) > 0:
                    pnl = cell_data["pnl"].values[0]
                    row_str += f" ${pnl:>7,.0f}"
                else:
                    row_str += f" {'---':>8}"

            print(row_str)

    # ── MONTHLY BREAKDOWN ──────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  MONTHLY PNL BREAKDOWN")
    print(f"{'='*78}\n")

    monthly_base = base3_daily.resample("ME").sum()
    monthly_full = full_daily.resample("ME").sum()

    print(f"  {'Month':<12} {'3-Strat':>10} {'5-Strat':>10} {'Delta':>10}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}")

    for dt in monthly_full.index:
        base_val = monthly_base.get(dt, 0)
        full_val = monthly_full[dt]
        delta = full_val - base_val
        month_str = dt.strftime("%Y-%m")
        print(f"  {month_str:<12} {'${:,.0f}'.format(base_val):>10} "
              f"{'${:,.0f}'.format(full_val):>10} "
              f"{'${:+,.0f}'.format(delta):>10}")

    base_neg = (monthly_base < 0).sum()
    full_neg = (monthly_full < 0).sum()
    print(f"\n  Losing months: 3-Strat={base_neg}, 5-Strat={full_neg}")

    # ── DRAWDOWN ANALYSIS ──────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  DRAWDOWN ANALYSIS")
    print(f"{'='*78}\n")

    for label, daily in [("3-Strat Baseline", base3_daily),
                         ("4-Strat (+MES)", four_daily),
                         ("5-Strat Full", full_daily)]:
        equity = STARTING_CAPITAL + daily.cumsum()
        peak = equity.cummax()
        dd = peak - equity
        maxdd = dd.max()
        maxdd_date = dd.idxmax() if len(dd) > 0 else "N/A"
        maxdd_pct = maxdd / STARTING_CAPITAL * 100
        print(f"  {label}:")
        print(f"    MaxDD: ${maxdd:,.0f} ({maxdd_pct:.2f}%) on {maxdd_date}")
        if maxdd > 0:
            maxdd_idx = dd.idxmax()
            recovery = equity[maxdd_idx:][equity[maxdd_idx:] >= peak[maxdd_idx]]
            if len(recovery) > 0:
                recovery_date = recovery.index[0]
                recovery_days = (recovery_date - maxdd_idx).days
                print(f"    Recovery: {recovery_days} calendar days")
            else:
                print(f"    Recovery: not yet recovered")
        print()

    # ── VERDICT ────────────────────────────────────────────────────────
    print(f"{'='*78}")
    print(f"  PORTFOLIO VERDICT")
    print(f"{'='*78}\n")

    improved_sharpe = full_m["sharpe"] > base3_m["sharpe"]
    improved_calmar = full_m["calmar"] > base3_m["calmar"]
    improved_months = full_m["profitable_months_pct"] >= base3_m["profitable_months_pct"]
    lower_dd = full_m["maxdd"] <= base3_m["maxdd"] * 1.2  # Allow 20% more DD
    more_pnl = full_m["total_pnl"] > base3_m["total_pnl"]

    checks = [
        ("PnL improvement", more_pnl, f"${base3_m['total_pnl']:,.0f} → ${full_m['total_pnl']:,.0f}"),
        ("Sharpe improvement", improved_sharpe, f"{base3_m['sharpe']:.2f} → {full_m['sharpe']:.2f}"),
        ("Calmar improvement", improved_calmar, f"{base3_m['calmar']:.2f} → {full_m['calmar']:.2f}"),
        ("DD within 120% of base", lower_dd, f"${base3_m['maxdd']:,.0f} → ${full_m['maxdd']:,.0f}"),
        ("Monthly consistency", improved_months, f"{base3_m['profitable_months_str']} → {full_m['profitable_months_str']}"),
    ]

    passes = sum(1 for _, v, _ in checks if v)
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}: {detail}")

    print(f"\n  Score: {passes}/5")
    if passes >= 4:
        print(f"  VERDICT: DEPLOYABLE PORTFOLIO CANDIDATE")
    elif passes >= 3:
        print(f"  VERDICT: PROMISING — review failures before deployment")
    else:
        print(f"  VERDICT: NOT READY — baseline is better")

    print(f"\n{'='*78}")
    print(f"  DONE")
    print(f"{'='*78}")

    # ── Save results JSON ──────────────────────────────────────────────
    results = {
        "baseline_3strat": {k: v for k, v in base3_m.items() if k != "label"},
        "portfolio_4strat": {k: v for k, v in four_m.items() if k != "label"},
        "portfolio_5strat": {k: v for k, v in full_m.items() if k != "label"},
        "correlation_matrix": corr.to_dict(),
        "per_strategy": {
            label: {
                "pnl": daily_pnls[label].sum(),
                "trades": total_trades_map[label],
                "pf": strat_metrics[label].get("profit_factor", 0),
                "sharpe": strat_metrics[label].get("sharpe", 0),
            }
            for label in all_labels
        },
    }
    out_path = OUTPUT_DIR / "phase12_portfolio_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Saved to: {out_path}")


if __name__ == "__main__":
    main()
