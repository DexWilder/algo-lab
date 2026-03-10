"""BB Equilibrium Evolution — Variant testing to improve walk-forward stability.

BB Equilibrium is the gold MR parent candidate (MGC-Long PF=3.53, Sharpe=3.50).
Its weakness: walk-forward instability (2024 PF=0.88, 2025 PF=2.02).

This script tests 4 evolution variants:
1) Volatility-gated: only trade when ATR percentile > threshold
2) Trend-aware: daily EMA filter for gold macro direction
3) Time-of-day filtered: restrict to best reversion hours
4) Extreme-only: wider BB mult (2.5σ/3σ) for higher-conviction entries

Goal: improve walk-forward stability while preserving PF > 2.

Usage:
    python3 research/bb_eq_evolution.py
"""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.regime_engine import RegimeEngine
from backtests.run_baseline import compute_extended_metrics, ASSET_CONFIG


PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SYMBOL = "MGC"
MODE = "long"


def load_strategy(name: str):
    module_path = PROJECT_ROOT / "strategies" / name / "strategy.py"
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_and_evaluate(df, signals_df, label, config, regime_daily=None):
    """Run backtest + compute metrics + walk-forward splits."""
    result = run_backtest(
        df, signals_df, mode=MODE,
        point_value=config["point_value"], symbol=SYMBOL,
    )
    trades_df = result["trades_df"]
    if trades_df.empty:
        return None

    metrics = compute_extended_metrics(trades_df, result["equity_curve"], config["point_value"])

    # Walk-forward: year splits
    trades_df["entry_date"] = pd.to_datetime(trades_df["entry_time"]).dt.date
    trades_df["year"] = pd.to_datetime(trades_df["entry_time"]).dt.year

    year_metrics = {}
    for year in [2024, 2025]:
        yt = trades_df[trades_df["year"] == year]
        if len(yt) >= 5:
            wins = (yt["pnl"] > 0).sum()
            losses = (yt["pnl"] <= 0).sum()
            gross_profit = yt.loc[yt["pnl"] > 0, "pnl"].sum()
            gross_loss = abs(yt.loc[yt["pnl"] <= 0, "pnl"].sum())
            pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
            year_metrics[year] = {
                "trades": len(yt),
                "pf": round(pf, 2),
                "pnl": round(yt["pnl"].sum(), 0),
                "wr": round((yt["pnl"] > 0).mean() * 100, 1),
            }
        else:
            year_metrics[year] = {"trades": len(yt), "pf": 0, "pnl": 0, "wr": 0}

    # Regime merge for analysis
    if regime_daily is not None:
        rd = regime_daily.copy()
        rd["_date_date"] = pd.to_datetime(rd["_date"]).dt.date
        trades_merged = trades_df.merge(
            rd[["_date_date", "vol_regime", "trend_regime", "rv_regime",
                "trend_persistence", "composite_regime"]],
            left_on="entry_date", right_on="_date_date", how="left",
        )
    else:
        trades_merged = trades_df

    # Time-of-day breakdown
    trades_df["entry_hour"] = pd.to_datetime(trades_df["entry_time"]).dt.hour
    hour_pnl = trades_df.groupby("entry_hour")["pnl"].agg(["sum", "count"]).to_dict("index")

    return {
        "label": label,
        "metrics": metrics,
        "year_metrics": year_metrics,
        "trades_df": trades_merged,
        "hour_pnl": hour_pnl,
    }


# ── Variant Generators ─────────────────────────────────────────────────────

def variant_baseline(df, strategy):
    """Unmodified BB Equilibrium."""
    return strategy.generate_signals(df)


def variant_vol_gated(df, strategy, atr_pct_threshold=40):
    """Only trade when ATR percentile > threshold (enough volatility for reversion)."""
    signals = strategy.generate_signals(df)

    # Compute ATR percentile ranking
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=14, adjust=False).mean()
    atr_pctrank = atr.rolling(window=252, min_periods=50).apply(
        lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False
    )

    # Mask out signals where ATR percentile is too low
    mask = atr_pctrank < atr_pct_threshold
    signals.loc[mask, "signal"] = 0
    signals.loc[mask, "stop_price"] = np.nan
    signals.loc[mask, "target_price"] = np.nan

    return signals


def variant_trend_aware(df, strategy, ema_period=20, require_trend=True):
    """Daily EMA filter: longs only when gold in uptrend, shorts in downtrend.

    Gold mean-reversion works best within a macro trend:
    - Uptrend dips revert upward (better for longs)
    - Downtrend rallies revert downward (better for shorts)
    """
    signals = strategy.generate_signals(df)

    # Compute daily close for EMA
    dt = pd.to_datetime(df["datetime"])
    df_copy = df.copy()
    df_copy["_date"] = dt.dt.date
    daily_close = df_copy.groupby("_date")["close"].last()
    daily_ema = daily_close.ewm(span=ema_period, adjust=False).mean()
    daily_slope = daily_ema.diff()

    # Map daily trend back to bars
    date_trend = {}
    for d in daily_ema.index:
        slope = daily_slope.get(d, 0)
        if pd.isna(slope):
            date_trend[d] = 0
        elif slope > 0:
            date_trend[d] = 1   # uptrend
        else:
            date_trend[d] = -1  # downtrend

    bar_dates = dt.dt.date
    bar_trend = bar_dates.map(date_trend).fillna(0).astype(int).values

    # Filter: longs only in uptrend, shorts only in downtrend
    for i in range(len(signals)):
        sig = signals["signal"].iloc[i]
        if sig == 1 and bar_trend[i] != 1:
            signals.iloc[i, signals.columns.get_loc("signal")] = 0
            signals.iloc[i, signals.columns.get_loc("stop_price")] = np.nan
            signals.iloc[i, signals.columns.get_loc("target_price")] = np.nan
        elif sig == -1 and bar_trend[i] != -1:
            signals.iloc[i, signals.columns.get_loc("signal")] = 0
            signals.iloc[i, signals.columns.get_loc("stop_price")] = np.nan
            signals.iloc[i, signals.columns.get_loc("target_price")] = np.nan

    return signals


def variant_time_filtered(df, strategy, best_hours=(10, 11, 12, 13)):
    """Restrict entries to hours with strongest reversion PnL."""
    signals = strategy.generate_signals(df)

    dt = pd.to_datetime(df["datetime"])
    hours = dt.dt.hour.values

    for i in range(len(signals)):
        if signals["signal"].iloc[i] != 0 and hours[i] not in best_hours:
            signals.iloc[i, signals.columns.get_loc("signal")] = 0
            signals.iloc[i, signals.columns.get_loc("stop_price")] = np.nan
            signals.iloc[i, signals.columns.get_loc("target_price")] = np.nan

    return signals


def variant_extreme_only(df, strategy, bb_mult=2.5):
    """Wider BB mult for higher-conviction entries (only extreme deviations)."""
    # Temporarily change BB_MULT
    orig_mult = strategy.BB_MULT
    strategy.BB_MULT = bb_mult
    signals = strategy.generate_signals(df)
    strategy.BB_MULT = orig_mult
    return signals


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    config = ASSET_CONFIG[SYMBOL]
    data_path = PROCESSED_DIR / f"{SYMBOL}_5m.csv"
    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    strategy = load_strategy("bb_equilibrium")
    strategy.TICK_SIZE = config["tick_size"]

    engine = RegimeEngine()
    regime_daily = engine.get_daily_regimes(df)

    # ── Run baseline first to identify best hours ──────────────────────────
    print(f"\n{'='*74}")
    print(f"  BB EQUILIBRIUM EVOLUTION — {SYMBOL}-{MODE.upper()}")
    print(f"{'='*74}")

    baseline = run_and_evaluate(df, variant_baseline(df, strategy),
                                "BASELINE", config, regime_daily)

    if baseline is None:
        print("  ERROR: Baseline produced no trades")
        return

    # Identify best hours from baseline
    print(f"\n  HOUR-OF-DAY ANALYSIS (baseline):")
    print(f"  {'Hour':>6} {'Trades':>7} {'PnL':>10}")
    print(f"  {'-'*6} {'-'*7} {'-'*10}")
    best_hours = []
    for hour in sorted(baseline["hour_pnl"].keys()):
        data = baseline["hour_pnl"][hour]
        pnl = data["sum"]
        count = data["count"]
        marker = " *" if pnl > 0 and count >= 5 else ""
        if pnl > 0 and count >= 5:
            best_hours.append(hour)
        print(f"  {hour:>6} {int(count):>7} {'${:,.0f}'.format(pnl):>10}{marker}")

    if not best_hours:
        best_hours = [10, 11, 12, 13]  # Default

    # ── Run all variants ───────────────────────────────────────────────────
    variants = [
        ("BASELINE", lambda: variant_baseline(df, strategy)),
        ("VOL-GATED (>30pct)", lambda: variant_vol_gated(df, strategy, 30)),
        ("VOL-GATED (>50pct)", lambda: variant_vol_gated(df, strategy, 50)),
        ("TREND-AWARE (EMA20)", lambda: variant_trend_aware(df, strategy, 20)),
        ("TREND-AWARE (EMA50)", lambda: variant_trend_aware(df, strategy, 50)),
        (f"TIME-FILTERED {best_hours}", lambda: variant_time_filtered(df, strategy, best_hours)),
        ("EXTREME-ONLY (2.5σ)", lambda: variant_extreme_only(df, strategy, 2.5)),
        ("EXTREME-ONLY (3.0σ)", lambda: variant_extreme_only(df, strategy, 3.0)),
    ]

    # Compound variants
    def compound_vol_trend():
        """Vol-gated + trend-aware."""
        signals = variant_vol_gated(df, strategy, 40)
        dt = pd.to_datetime(df["datetime"])
        df_copy = df.copy()
        df_copy["_date"] = dt.dt.date
        daily_close = df_copy.groupby("_date")["close"].last()
        daily_ema = daily_close.ewm(span=20, adjust=False).mean()
        daily_slope = daily_ema.diff()
        date_trend = {}
        for d in daily_ema.index:
            slope = daily_slope.get(d, 0)
            if pd.isna(slope):
                date_trend[d] = 0
            elif slope > 0:
                date_trend[d] = 1
            else:
                date_trend[d] = -1
        bar_dates = dt.dt.date
        bar_trend = bar_dates.map(date_trend).fillna(0).astype(int).values
        for i in range(len(signals)):
            sig = signals["signal"].iloc[i]
            if sig == 1 and bar_trend[i] != 1:
                signals.iloc[i, signals.columns.get_loc("signal")] = 0
                signals.iloc[i, signals.columns.get_loc("stop_price")] = np.nan
                signals.iloc[i, signals.columns.get_loc("target_price")] = np.nan
            elif sig == -1 and bar_trend[i] != -1:
                signals.iloc[i, signals.columns.get_loc("signal")] = 0
                signals.iloc[i, signals.columns.get_loc("stop_price")] = np.nan
                signals.iloc[i, signals.columns.get_loc("target_price")] = np.nan
        return signals

    def compound_vol_time():
        """Vol-gated + time-filtered."""
        signals = variant_vol_gated(df, strategy, 40)
        dt = pd.to_datetime(df["datetime"])
        hours = dt.dt.hour.values
        for i in range(len(signals)):
            if signals["signal"].iloc[i] != 0 and hours[i] not in best_hours:
                signals.iloc[i, signals.columns.get_loc("signal")] = 0
                signals.iloc[i, signals.columns.get_loc("stop_price")] = np.nan
                signals.iloc[i, signals.columns.get_loc("target_price")] = np.nan
        return signals

    variants.extend([
        ("COMPOUND: VOL+TREND", compound_vol_trend),
        ("COMPOUND: VOL+TIME", compound_vol_time),
    ])

    results = []
    for label, gen_fn in variants:
        signals_df = gen_fn()
        res = run_and_evaluate(df, signals_df, label, config, regime_daily)
        if res:
            results.append(res)
        else:
            results.append({
                "label": label,
                "metrics": {"trade_count": 0, "profit_factor": 0, "sharpe": 0,
                            "total_pnl": 0, "max_drawdown": 0, "win_rate": 0,
                            "median_trade_duration_bars": 0},
                "year_metrics": {2024: {"trades": 0, "pf": 0}, 2025: {"trades": 0, "pf": 0}},
            })

    # ── Results Matrix ─────────────────────────────────────────────────────
    print(f"\n{'='*74}")
    print(f"  EVOLUTION MATRIX — BB EQUILIBRIUM {SYMBOL}-{MODE.upper()}")
    print(f"{'='*74}")
    print(f"  {'Variant':<28} {'Trades':>6} {'PF':>6} {'Sharpe':>7} "
          f"{'PnL':>9} {'MaxDD':>8} {'2024':>8} {'2025':>8} {'WF':>4}")
    print(f"  {'-'*28} {'-'*6} {'-'*6} {'-'*7} {'-'*9} {'-'*8} {'-'*8} {'-'*8} {'-'*4}")

    for r in results:
        m = r["metrics"]
        ym = r["year_metrics"]
        tc = m["trade_count"]
        if tc == 0:
            print(f"  {r['label']:<28} {'0':>6} {'—':>6} {'—':>7} {'—':>9} {'—':>8} {'—':>8} {'—':>8} {'—':>4}")
            continue

        pf_2024 = f"{ym[2024]['pf']:.2f}" if ym[2024]["trades"] >= 5 else "—"
        pf_2025 = f"{ym[2025]['pf']:.2f}" if ym[2025]["trades"] >= 5 else "—"

        # Walk-forward pass: both years PF > 1.0
        wf_pass = "—"
        if ym[2024]["trades"] >= 5 and ym[2025]["trades"] >= 5:
            if ym[2024]["pf"] >= 1.0 and ym[2025]["pf"] >= 1.0:
                wf_pass = "PASS"
            else:
                wf_pass = "FAIL"

        med_hold = m.get("median_trade_duration_bars", 0)
        print(f"  {r['label']:<28} {tc:>6} {m['profit_factor']:>6.2f} "
              f"{m['sharpe']:>7.2f} "
              f"{'${:,.0f}'.format(m['total_pnl']):>9} "
              f"{'${:,.0f}'.format(m['max_drawdown']):>8} "
              f"{pf_2024:>8} {pf_2025:>8} {wf_pass:>4}")

    # ── Identify best variant ──────────────────────────────────────────────
    print(f"\n{'='*74}")
    print(f"  ANALYSIS")
    print(f"{'='*74}")

    # Best WF-passing variant (highest PF among those that pass WF)
    wf_passing = []
    for r in results:
        m = r["metrics"]
        ym = r["year_metrics"]
        if (m["trade_count"] >= 20
                and ym[2024].get("trades", 0) >= 5 and ym[2025].get("trades", 0) >= 5
                and ym[2024]["pf"] >= 1.0 and ym[2025]["pf"] >= 1.0):
            wf_passing.append(r)

    if wf_passing:
        best_wf = max(wf_passing, key=lambda r: r["metrics"]["profit_factor"])
        m = best_wf["metrics"]
        ym = best_wf["year_metrics"]
        print(f"\n  BEST WALK-FORWARD STABLE VARIANT: {best_wf['label']}")
        print(f"    PF: {m['profit_factor']:.2f}")
        print(f"    Trades: {m['trade_count']}")
        print(f"    Sharpe: {m['sharpe']:.2f}")
        print(f"    PnL: ${m['total_pnl']:,.0f}")
        print(f"    2024 PF: {ym[2024]['pf']:.2f} ({ym[2024]['trades']} trades)")
        print(f"    2025 PF: {ym[2025]['pf']:.2f} ({ym[2025]['trades']} trades)")
        print(f"    Walk-forward: STABLE")
    else:
        print(f"\n  NO VARIANT PASSES WALK-FORWARD GATE")
        print(f"  Best overall by PF (≥20 trades):")
        qualified = [r for r in results if r["metrics"]["trade_count"] >= 20]
        if qualified:
            best = max(qualified, key=lambda r: r["metrics"]["profit_factor"])
            m = best["metrics"]
            ym = best["year_metrics"]
            print(f"    {best['label']}: PF={m['profit_factor']:.2f}, "
                  f"2024={ym[2024]['pf']:.2f}, 2025={ym[2025]['pf']:.2f}")

    # Best PF > 2 that passes WF
    pf2_wf = [r for r in wf_passing if r["metrics"]["profit_factor"] >= 2.0]
    if pf2_wf:
        best = max(pf2_wf, key=lambda r: r["metrics"]["profit_factor"])
        print(f"\n  GOAL MET: {best['label']} — PF={best['metrics']['profit_factor']:.2f}, WF STABLE")
    elif wf_passing:
        best = max(wf_passing, key=lambda r: r["metrics"]["profit_factor"])
        print(f"\n  PARTIAL: Walk-forward stable but PF < 2.0: {best['label']} "
              f"PF={best['metrics']['profit_factor']:.2f}")
    else:
        print(f"\n  GOAL NOT MET: No variant achieves PF > 2.0 + walk-forward stability")
        print(f"  Recommendation: BB Equilibrium remains on PROBATION")
        print(f"  The 2024 underperformance may be a regime-dependent structural feature")

    print()


if __name__ == "__main__":
    main()
