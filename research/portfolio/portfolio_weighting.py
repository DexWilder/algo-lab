"""Portfolio Risk-Weight Optimization + Stress Testing.

Tests 5 position sizing schemes on the 5-strategy deployable portfolio:
1. Equal weight (baseline)
2. Volatility targeting per strategy
3. Risk parity (equal risk contribution)
4. Kelly fraction (capped at half-Kelly)
5. Drawdown-adjusted weighting

Also runs stress tests:
- Leave-one-out (remove each strategy)
- Remove best N trades
- Shuffle trade order (Monte Carlo)

Usage:
    python3 research/portfolio/portfolio_weighting.py
"""

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
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
     "label": "PB", "grinding_filter": False, "exit_variant": None},
    {"name": "orb_009", "asset": "MGC", "mode": "long",
     "label": "ORB", "grinding_filter": False, "exit_variant": None},
    {"name": "vwap_trend", "asset": "MNQ", "mode": "long",
     "label": "VWAP", "grinding_filter": False, "exit_variant": None},
    {"name": "xb_pb_ema_timestop", "asset": "MES", "mode": "short",
     "label": "XB-PB", "grinding_filter": False, "exit_variant": None},
    {"name": "donchian_trend", "asset": "MNQ", "mode": "long",
     "label": "DONCH", "grinding_filter": True, "exit_variant": "profit_ladder"},
]


# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING (reused from phase12_portfolio.py)
# ═══════════════════════════════════════════════════════════════════════════

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
    asset = strat["asset"]
    config = ASSET_CONFIG[asset]

    df = pd.read_csv(PROCESSED_DIR / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])

    mod = load_strategy(strat["name"])
    if hasattr(mod, "TICK_SIZE"):
        mod.TICK_SIZE = config["tick_size"]
    signals = mod.generate_signals(df)

    if strat.get("exit_variant") == "profit_ladder":
        from research.exit_evolution import donchian_entries, apply_profit_ladder
        data = donchian_entries(df)
        pl_signals_df = apply_profit_ladder(data)
        result = run_backtest(
            df, pl_signals_df, mode=strat["mode"],
            point_value=config["point_value"], symbol=asset,
        )
        trades = result["trades_df"]
    else:
        result = run_backtest(
            df, signals, mode=strat["mode"],
            point_value=config["point_value"], symbol=asset,
        )
        trades = result["trades_df"]

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
    return daily, trades


# ═══════════════════════════════════════════════════════════════════════════
# PORTFOLIO METRICS
# ═══════════════════════════════════════════════════════════════════════════

def compute_portfolio(daily_dict: dict, weights: dict) -> pd.Series:
    """Combine daily PnL streams with weights."""
    df = pd.DataFrame(daily_dict).fillna(0)
    for label in df.columns:
        df[label] = df[label] * weights.get(label, 1.0)
    return df.sum(axis=1).sort_index()


def port_stats(port_daily: pd.Series, label: str = "") -> dict:
    """Compute portfolio statistics."""
    total_pnl = port_daily.sum()
    if port_daily.std() == 0:
        return {"label": label, "total_pnl": 0, "sharpe": 0, "calmar": 0,
                "maxdd": 0, "monthly_pct": 0}

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
        "label": label,
        "total_pnl": total_pnl,
        "sharpe": sharpe,
        "calmar": calmar,
        "maxdd": maxdd,
        "monthly_pct": monthly_pct,
        "profitable_months": f"{profitable}/{total}",
        "losing_months": total - profitable,
    }


def monte_carlo(port_daily: pd.Series, n_sims: int = 10_000, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    daily_arr = port_daily.values
    n = len(daily_arr)
    if n == 0:
        return {}

    ruin = {k: 0 for k in [1000, 2000, 3000, 4000]}
    max_dds = []
    for _ in range(n_sims):
        shuffled = rng.choice(daily_arr, size=n, replace=True)
        eq = STARTING_CAPITAL + np.cumsum(shuffled)
        pk = np.maximum.accumulate(eq)
        dd = (pk - eq).max()
        max_dds.append(dd)
        for floor in ruin:
            if dd >= floor:
                ruin[floor] += 1

    return {
        "ruin_probs": {f"${k}": v / n_sims * 100 for k, v in ruin.items()},
        "median_maxdd": float(np.median(max_dds)),
        "p95_maxdd": float(np.percentile(max_dds, 95)),
        "p99_maxdd": float(np.percentile(max_dds, 99)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# WEIGHTING SCHEMES
# ═══════════════════════════════════════════════════════════════════════════

def weight_equal(daily_dict: dict) -> dict:
    """Equal weight — 1.0 for all."""
    return {k: 1.0 for k in daily_dict}


def weight_vol_target(daily_dict: dict, target_vol: float = 0.10) -> dict:
    """Volatility targeting — scale each strategy to same annualized vol."""
    weights = {}
    for label, daily in daily_dict.items():
        ann_vol = daily.std() * np.sqrt(252)
        if ann_vol > 0:
            weights[label] = target_vol / ann_vol
        else:
            weights[label] = 0.0
    # Normalize so average weight = 1.0
    avg = np.mean(list(weights.values()))
    if avg > 0:
        weights = {k: v / avg for k, v in weights.items()}
    return weights


def weight_risk_parity(daily_dict: dict) -> dict:
    """Risk parity — equal risk contribution (inverse volatility)."""
    vols = {}
    for label, daily in daily_dict.items():
        vols[label] = daily.std() * np.sqrt(252) if daily.std() > 0 else 1e-6

    inv_vols = {k: 1.0 / v for k, v in vols.items()}
    total = sum(inv_vols.values())
    n = len(daily_dict)
    # Scale so sum of weights = n (so average = 1.0)
    weights = {k: v / total * n for k, v in inv_vols.items()}
    return weights


def weight_kelly(daily_dict: dict, fraction: float = 0.5) -> dict:
    """Half-Kelly sizing — based on each strategy's edge/variance ratio."""
    weights = {}
    for label, daily in daily_dict.items():
        mean = daily.mean()
        var = daily.var()
        if var > 0 and mean > 0:
            full_kelly = mean / var
            # Cap at 2.0 to prevent extreme sizing
            weights[label] = min(full_kelly * fraction * daily.std() * np.sqrt(252), 2.0)
        else:
            weights[label] = 0.5  # Floor for strategies with weak signal
    # Normalize so average = 1.0
    avg = np.mean(list(weights.values()))
    if avg > 0:
        weights = {k: v / avg for k, v in weights.items()}
    return weights


def weight_dd_adjusted(daily_dict: dict) -> dict:
    """Drawdown-adjusted — inverse of max drawdown (reward smooth equity)."""
    dds = {}
    for label, daily in daily_dict.items():
        eq = STARTING_CAPITAL + daily.cumsum()
        pk = eq.cummax()
        dd = (pk - eq).max()
        dds[label] = max(dd, 1.0)

    inv_dds = {k: 1.0 / v for k, v in dds.items()}
    total = sum(inv_dds.values())
    n = len(daily_dict)
    weights = {k: v / total * n for k, v in inv_dds.items()}
    return weights


SCHEMES = [
    ("Equal Weight", weight_equal),
    ("Vol Target", weight_vol_target),
    ("Risk Parity", weight_risk_parity),
    ("Half-Kelly", weight_kelly),
    ("DD-Adjusted", weight_dd_adjusted),
]


# ═══════════════════════════════════════════════════════════════════════════
# STRESS TESTS
# ═══════════════════════════════════════════════════════════════════════════

def stress_leave_one_out(daily_dict: dict, best_weights: dict) -> list:
    """Remove each strategy and measure portfolio degradation."""
    results = []
    full = compute_portfolio(daily_dict, best_weights)
    full_stats = port_stats(full, "Full")

    for removed in daily_dict:
        remaining = {k: v for k, v in daily_dict.items() if k != removed}
        rem_weights = {k: v for k, v in best_weights.items() if k != removed}
        port = compute_portfolio(remaining, rem_weights)
        s = port_stats(port, f"Without {removed}")
        s["removed"] = removed
        s["sharpe_delta"] = s["sharpe"] - full_stats["sharpe"]
        s["pnl_delta"] = s["total_pnl"] - full_stats["total_pnl"]
        results.append(s)

    return results


def stress_remove_best_trades(all_trades: dict, daily_dict: dict,
                               weights: dict, n_remove: int = 5) -> list:
    """Remove top N trades by PnL and recompute portfolio."""
    # Combine all trades with strategy labels
    combined = []
    for label, trades in all_trades.items():
        if trades.empty:
            continue
        t = trades.copy()
        t["strategy"] = label
        combined.append(t)

    if not combined:
        return []

    all_t = pd.concat(combined, ignore_index=True)
    all_t = all_t.sort_values("pnl", ascending=False)

    results = []
    for n in [1, 3, 5]:
        if n > len(all_t):
            continue
        top_n = all_t.head(n)
        # Rebuild daily PnL without top trades
        modified_daily = {}
        for label in daily_dict:
            trades = all_trades[label]
            if trades.empty:
                modified_daily[label] = daily_dict[label]
                continue
            # Remove trades that match the top-N (by index won't work, use PnL + time)
            top_for_strat = top_n[top_n["strategy"] == label]
            if top_for_strat.empty:
                modified_daily[label] = daily_dict[label]
                continue
            remaining = trades[~trades.index.isin(top_for_strat.index)]
            modified_daily[label] = get_daily_pnl(remaining)

        port = compute_portfolio(modified_daily, weights)
        s = port_stats(port, f"Remove top {n}")
        s["removed_pnl"] = top_n.head(n)["pnl"].sum()
        removed_strats = top_n.head(n)["strategy"].value_counts().to_dict()
        s["removed_from"] = removed_strats
        results.append(s)

    return results


def stress_shuffle_order(all_trades: dict, weights: dict,
                          n_sims: int = 5_000, seed: int = 42) -> dict:
    """Shuffle trade order within each strategy, compute distribution of outcomes."""
    rng = np.random.default_rng(seed)

    # Get per-trade PnL arrays for each strategy
    trade_arrays = {}
    for label, trades in all_trades.items():
        if not trades.empty:
            trade_arrays[label] = trades["pnl"].values * weights.get(label, 1.0)

    sharpes = []
    max_dds = []
    total_pnls = []

    for _ in range(n_sims):
        # Shuffle each strategy's trades independently
        sim_dailies = {}
        for label, pnl_arr in trade_arrays.items():
            shuffled = rng.permutation(pnl_arr)
            # Create synthetic daily: one trade per "day"
            sim_dailies[label] = pd.Series(shuffled)

        # Combine into portfolio — align by index
        combined = pd.DataFrame(sim_dailies).fillna(0).sum(axis=1)
        total_pnl = combined.sum()
        total_pnls.append(total_pnl)

        std = combined.std()
        if std > 0:
            sharpes.append(combined.mean() / std * np.sqrt(252))
        else:
            sharpes.append(0)

        eq = STARTING_CAPITAL + combined.cumsum().values
        pk = np.maximum.accumulate(eq)
        max_dds.append((pk - eq).max())

    return {
        "sharpe_median": float(np.median(sharpes)),
        "sharpe_p5": float(np.percentile(sharpes, 5)),
        "sharpe_p95": float(np.percentile(sharpes, 95)),
        "maxdd_median": float(np.median(max_dds)),
        "maxdd_p95": float(np.percentile(max_dds, 95)),
        "pnl_median": float(np.median(total_pnls)),
        "pnl_p5": float(np.percentile(total_pnls, 5)),
        "pnl_p95": float(np.percentile(total_pnls, 95)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    engine = RegimeEngine()

    print("=" * 78)
    print("  PORTFOLIO RISK-WEIGHT OPTIMIZATION + STRESS TESTING")
    print("=" * 78)

    # ── Load all strategy data ─────────────────────────────────────────
    daily_pnls = {}
    all_trades = {}

    for strat in STRATEGIES:
        label = strat["label"]
        print(f"  Loading {label}...")
        daily, trades = run_strategy(strat, engine)
        daily_pnls[label] = daily
        all_trades[label] = trades
        print(f"    {len(trades)} trades, PnL=${daily.sum():,.0f}")

    # ══════════════════════════════════════════════════════════════════
    # PART 1: WEIGHTING SCHEMES
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*78}")
    print(f"  PART 1: POSITION SIZING COMPARISON")
    print(f"{'='*78}\n")

    scheme_results = {}
    scheme_weights = {}

    for name, fn in SCHEMES:
        if fn == weight_vol_target:
            w = fn(daily_pnls, target_vol=0.10)
        elif fn == weight_kelly:
            w = fn(daily_pnls, fraction=0.5)
        else:
            w = fn(daily_pnls)

        port = compute_portfolio(daily_pnls, w)
        s = port_stats(port, name)
        mc = monte_carlo(port)
        s["mc_ruin_2k"] = mc["ruin_probs"]["$2000"]
        s["mc_p95_dd"] = mc["p95_maxdd"]
        scheme_results[name] = s
        scheme_weights[name] = w

    # Print weights
    print(f"  WEIGHTS PER STRATEGY:")
    print(f"  {'Scheme':<18}", end="")
    for strat in STRATEGIES:
        print(f" {strat['label']:>8}", end="")
    print()
    print(f"  {'-'*18}", end="")
    for _ in STRATEGIES:
        print(f" {'-'*8}", end="")
    print()

    for name, _ in SCHEMES:
        w = scheme_weights[name]
        print(f"  {name:<18}", end="")
        for strat in STRATEGIES:
            print(f" {w.get(strat['label'], 1.0):>8.3f}", end="")
        print()

    # Print comparison table
    print(f"\n  PERFORMANCE COMPARISON:")
    print(f"  {'Scheme':<18} {'PnL':>10} {'Sharpe':>7} {'Calmar':>7} "
          f"{'MaxDD':>8} {'Monthly':>8} {'MC $2K':>7} {'MC p95':>8}")
    print(f"  {'-'*18} {'-'*10} {'-'*7} {'-'*7} "
          f"{'-'*8} {'-'*8} {'-'*7} {'-'*8}")

    for name, _ in SCHEMES:
        s = scheme_results[name]
        print(f"  {name:<18} ${s['total_pnl']:>8,.0f} {s['sharpe']:>7.2f} "
              f"{s['calmar']:>7.2f} ${s['maxdd']:>6,.0f} {s['monthly_pct']:>7.0f}% "
              f"{s['mc_ruin_2k']:>6.1f}% ${s['mc_p95_dd']:>6,.0f}")

    # Find best scheme by Sharpe
    best_scheme = max(scheme_results.items(), key=lambda x: x[1]["sharpe"])
    best_name = best_scheme[0]
    best_w = scheme_weights[best_name]

    print(f"\n  BEST SCHEME: {best_name} (Sharpe={best_scheme[1]['sharpe']:.2f})")

    # ══════════════════════════════════════════════════════════════════
    # PART 2: STRESS TESTS
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*78}")
    print(f"  PART 2: STRESS TESTS (using {best_name} weights)")
    print(f"{'='*78}")

    # ── Leave-one-out ──────────────────────────────────────────────────
    print(f"\n  LEAVE-ONE-OUT:")
    print(f"  {'Removed':<12} {'PnL':>10} {'Sharpe':>7} {'Calmar':>7} "
          f"{'MaxDD':>8} {'Sh Delta':>9}")
    print(f"  {'-'*12} {'-'*10} {'-'*7} {'-'*7} {'-'*8} {'-'*9}")

    loo_results = stress_leave_one_out(daily_pnls, best_w)
    for s in loo_results:
        print(f"  {s['removed']:<12} ${s['total_pnl']:>8,.0f} {s['sharpe']:>7.2f} "
              f"{s['calmar']:>7.2f} ${s['maxdd']:>6,.0f} {s['sharpe_delta']:>+8.2f}")

    full_port = compute_portfolio(daily_pnls, best_w)
    full_s = port_stats(full_port, "Full")
    print(f"  {'FULL':<12} ${full_s['total_pnl']:>8,.0f} {full_s['sharpe']:>7.2f} "
          f"{full_s['calmar']:>7.2f} ${full_s['maxdd']:>6,.0f} {'---':>9}")

    # Most critical strategy
    most_critical = max(loo_results, key=lambda x: abs(x["sharpe_delta"]))
    print(f"\n  Most critical: removing {most_critical['removed']} "
          f"hurts Sharpe by {most_critical['sharpe_delta']:+.2f}")

    # ── Remove best trades ─────────────────────────────────────────────
    print(f"\n  REMOVE BEST TRADES:")
    print(f"  {'Test':<20} {'PnL':>10} {'Sharpe':>7} {'Calmar':>7} "
          f"{'Removed PnL':>12}")
    print(f"  {'-'*20} {'-'*10} {'-'*7} {'-'*7} {'-'*12}")

    rbt_results = stress_remove_best_trades(all_trades, daily_pnls, best_w)
    for s in rbt_results:
        print(f"  {s['label']:<20} ${s['total_pnl']:>8,.0f} {s['sharpe']:>7.2f} "
              f"{s['calmar']:>7.2f} ${s['removed_pnl']:>10,.0f}")
        if s.get("removed_from"):
            strats = ", ".join(f"{k}({v})" for k, v in s["removed_from"].items())
            print(f"    from: {strats}")

    all_positive = all(s["total_pnl"] > 0 for s in rbt_results)
    all_pf_above_1 = all(s["sharpe"] > 0 for s in rbt_results)
    print(f"\n  Portfolio survives removing top 5 trades: "
          f"{'YES' if all_positive else 'NO'}")

    # ── Shuffle order (Monte Carlo) ────────────────────────────────────
    print(f"\n  TRADE ORDER SHUFFLE (5K simulations):")
    shuffle = stress_shuffle_order(all_trades, best_w)
    print(f"    Sharpe: median={shuffle['sharpe_median']:.2f}, "
          f"5th={shuffle['sharpe_p5']:.2f}, 95th={shuffle['sharpe_p95']:.2f}")
    print(f"    MaxDD:  median=${shuffle['maxdd_median']:,.0f}, "
          f"95th=${shuffle['maxdd_p95']:,.0f}")
    print(f"    PnL:    median=${shuffle['pnl_median']:,.0f}, "
          f"5th=${shuffle['pnl_p5']:,.0f}, 95th=${shuffle['pnl_p95']:,.0f}")

    # ══════════════════════════════════════════════════════════════════
    # PART 3: RECOMMENDED DEPLOYMENT PROFILE
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'='*78}")
    print(f"  RECOMMENDED DEPLOYMENT PROFILE")
    print(f"{'='*78}\n")

    print(f"  Sizing scheme: {best_name}")
    print(f"  Weights:")
    for strat in STRATEGIES:
        label = strat["label"]
        w_val = best_w.get(label, 1.0)
        full_label = f"{strat['name']} ({strat['asset']}-{strat['mode']})"
        print(f"    {label:<8} = {w_val:.3f}x  ({full_label})")

    print(f"\n  Expected performance:")
    bs = best_scheme[1]
    print(f"    Sharpe:           {bs['sharpe']:.2f}")
    print(f"    Calmar:           {bs['calmar']:.2f}")
    print(f"    MaxDD:            ${bs['maxdd']:,.0f}")
    print(f"    MC P($2K ruin):   {bs['mc_ruin_2k']:.1f}%")
    print(f"    Monthly win rate: {bs['monthly_pct']:.0f}%")
    print(f"    Trades:           500")

    # Fragility assessment
    min_loo_sharpe = min(s["sharpe"] for s in loo_results)
    survives_top5 = all_positive
    shuffle_sharpe_p5 = shuffle["sharpe_p5"]

    print(f"\n  Fragility assessment:")
    print(f"    Worst leave-one-out Sharpe:  {min_loo_sharpe:.2f} "
          f"({'PASS' if min_loo_sharpe > 1.5 else 'CAUTION'})")
    print(f"    Survives top-5 removal:      "
          f"{'YES' if survives_top5 else 'NO'}")
    print(f"    Shuffle 5th-pct Sharpe:      {shuffle_sharpe_p5:.2f} "
          f"({'PASS' if shuffle_sharpe_p5 > 1.0 else 'CAUTION'})")

    robust = min_loo_sharpe > 1.5 and survives_top5 and shuffle_sharpe_p5 > 1.0
    print(f"\n  VERDICT: {'ROBUST — READY FOR DEPLOYMENT' if robust else 'REVIEW NEEDED'}")

    print(f"\n{'='*78}")

    # ── Save results ───────────────────────────────────────────────────
    results = {
        "schemes": {
            name: {
                "weights": {k: round(v, 4) for k, v in scheme_weights[name].items()},
                "sharpe": round(scheme_results[name]["sharpe"], 3),
                "calmar": round(scheme_results[name]["calmar"], 3),
                "maxdd": round(scheme_results[name]["maxdd"], 2),
                "total_pnl": round(scheme_results[name]["total_pnl"], 2),
                "monthly_pct": round(scheme_results[name]["monthly_pct"], 1),
                "mc_ruin_2k": round(scheme_results[name]["mc_ruin_2k"], 2),
            }
            for name, _ in SCHEMES
        },
        "best_scheme": best_name,
        "best_weights": {k: round(v, 4) for k, v in best_w.items()},
        "stress_tests": {
            "leave_one_out": [
                {"removed": s["removed"], "sharpe": round(s["sharpe"], 3),
                 "pnl": round(s["total_pnl"], 2)}
                for s in loo_results
            ],
            "remove_best_trades": [
                {"label": s["label"], "sharpe": round(s["sharpe"], 3),
                 "pnl": round(s["total_pnl"], 2)}
                for s in rbt_results
            ],
            "shuffle_order": shuffle,
        },
        "verdict": "ROBUST" if robust else "REVIEW",
    }

    out_path = OUTPUT_DIR / "portfolio_weighting_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Saved to: {out_path}")


if __name__ == "__main__":
    main()
