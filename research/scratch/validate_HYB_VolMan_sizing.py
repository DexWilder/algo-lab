#!/usr/bin/env python3
"""HYB-VolMan-Workhorse-SizingOverlay validation runner.

Per docs/fql_forge/_DRAFT_validation_plan_HYB-VolMan-Sizing.md.

Steps:
 1. Reconstruct XB-ORB-EMA-Ladder-MNQ baseline trade list (run strategy on MNQ 5m data)
 2. Run A: baseline 1-contract sizing PnL
 3. Run B: inverse-vol-sized PnL on same trade list
 4. Compute comparative metrics
 5. Prop-sim layer (FTMO-style)

Output: prints verdict + metrics. No registry mutation. No file writes
beyond stdout. The result memo is a separate file produced by the
operator-facing wrapper, not this script.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from strategies.xb_orb_ema_ladder.strategy import generate_signals  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402
from backtests.run_baseline import ASSET_CONFIG  # noqa: E402

ASSET = "MNQ"
DATA_PATH = ROOT / "data" / "processed" / f"{ASSET}_5m.csv"
REGISTRY_TRADES_6YR = 1183
REGISTRY_PF = 1.62

# Inverse-vol sizing config (per validation plan §4.3)
ATR_LOOKBACK_DAYS = 20  # 20-day daily-bar ATR for vol estimation
TARGET_DOLLAR_VOL_AT_AVG_ATR = None  # set after computing avg ATR
MAX_CONTRACTS = 3  # cap per plan §4.3


def step1_reproduce_baseline():
    """Run XB-ORB-EMA-Ladder-MNQ on MNQ 5m data, get trade list."""
    print("=" * 70)
    print("STEP 1 — Reproduce XB-ORB-EMA-Ladder-MNQ baseline")
    print("=" * 70)

    df = pd.read_csv(DATA_PATH)
    # Normalize datetime column to "timestamp"
    if "datetime" in df.columns:
        df["timestamp"] = pd.to_datetime(df["datetime"])
    elif "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    elif "date" in df.columns:
        df["timestamp"] = pd.to_datetime(df["date"])
    print(f"  Loaded {len(df):,} bars from {DATA_PATH.name}")
    print(f"  Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")

    signals_df = generate_signals(df)
    config = ASSET_CONFIG[ASSET]
    result = run_backtest(
        df, signals_df, mode="both",
        point_value=config["point_value"], symbol=ASSET,
    )
    trades_df = result["trades_df"]
    print(f"  Trades produced: {len(trades_df)}")
    print(f"  Registry trades_6yr: {REGISTRY_TRADES_6YR}")

    if len(trades_df) == 0:
        print("  ERROR: zero trades produced — extraction broken. HALT.")
        sys.exit(1)

    # Reproduction sanity check
    delta_pct = abs(len(trades_df) - REGISTRY_TRADES_6YR) / REGISTRY_TRADES_6YR * 100
    print(f"  Trade-count delta: {delta_pct:.1f}%")

    gross_profit = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    pf_delta_pct = abs(pf - REGISTRY_PF) / REGISTRY_PF * 100
    print(f"  Computed PF: {pf:.3f}  Registry PF: {REGISTRY_PF}")
    print(f"  PF delta: {pf_delta_pct:.1f}%")

    if delta_pct > 5 or pf_delta_pct > 10:
        print(f"  WARN: reproduction delta exceeds ±5% trades / ±10% PF")
        print(f"        Continuing but flagging in result memo")
    else:
        print(f"  OK: reproduction within tolerance")

    return df, trades_df, result["equity_curve"], config


def compute_atr(daily_df, lookback):
    """Wilder ATR on daily bars."""
    high = daily_df["high"]
    low = daily_df["low"]
    close = daily_df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(lookback).mean()


def step2_run_a_baseline(trades_df, config):
    """Run A: PnL with fixed 1-contract sizing (already in trades_df['pnl'])."""
    print("\n" + "=" * 70)
    print("STEP 2 — Run A (baseline 1-contract sizing)")
    print("=" * 70)
    pnl_a = trades_df["pnl"].values
    contracts_a = np.ones(len(pnl_a))  # all 1
    return pnl_a, contracts_a


def step3_run_b_overlay(df, trades_df, config):
    """Run B: same trades, sized via inverse-vol overlay."""
    print("\n" + "=" * 70)
    print("STEP 3 — Run B (inverse-vol sizing overlay)")
    print("=" * 70)

    # Build daily bars from 5m for ATR
    df = df.copy()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    daily = df.groupby("date").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    ).reset_index()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["atr20"] = compute_atr(daily, ATR_LOOKBACK_DAYS)

    # Map each trade's entry date to its prior-day ATR
    # entry_time is timestamp; convert to date for lookup
    trades = trades_df.copy()
    trades["entry_date"] = pd.to_datetime(trades["entry_time"]).dt.normalize()
    daily_indexed = daily.set_index("date")["atr20"]

    def get_prior_atr(entry_dt):
        # Use the most recent daily ATR strictly before entry_dt
        prior = daily_indexed.loc[daily_indexed.index < entry_dt]
        return float(prior.iloc[-1]) if len(prior) > 0 and not pd.isna(prior.iloc[-1]) else np.nan

    trades["entry_atr20"] = trades["entry_date"].apply(get_prior_atr)
    valid_atr = trades["entry_atr20"].dropna()
    if len(valid_atr) == 0:
        print("  ERROR: no valid ATR values — HALT")
        sys.exit(1)

    avg_atr = valid_atr.mean()
    print(f"  Average 20-day ATR over trades: {avg_atr:.3f}")

    # Calibrate target_dollar_vol so average contract count ≈ 1
    # contract_count = round(target_$vol / (atr * point_value))
    point_value = config["point_value"]
    target_dollar_vol = avg_atr * point_value  # = baseline notional vol per contract
    print(f"  point_value (MNQ): {point_value}")
    print(f"  target_dollar_vol (calibrated): {target_dollar_vol:.2f}")

    # Compute contracts per trade
    contracts_b = np.zeros(len(trades))
    for i, (_, row) in enumerate(trades.iterrows()):
        atr = row["entry_atr20"]
        if pd.isna(atr) or atr <= 0:
            contracts_b[i] = 1  # fallback
            continue
        c = round(target_dollar_vol / (atr * point_value))
        c = max(1, min(MAX_CONTRACTS, c))
        contracts_b[i] = c

    avg_c = contracts_b.mean()
    print(f"  Average contract count Run B: {avg_c:.2f}")
    print(f"  Distribution: 1c={int((contracts_b==1).sum())} 2c={int((contracts_b==2).sum())} 3c={int((contracts_b==3).sum())}")

    # Apply sizing to PnL: scale baseline pnl per trade
    # Baseline pnl was for 1 contract, so multiply by contracts_b
    # Fees: assume 1 fee per contract per side ≈ 2 × per_contract_fee × contracts
    # Slippage already in baseline pnl per contract; scales with contract count
    baseline_pnl = trades["pnl"].values
    pnl_b = baseline_pnl * contracts_b
    return pnl_b, contracts_b


def metrics(pnl, label):
    pnl = np.asarray(pnl)
    n = len(pnl)
    net = pnl.sum()
    gp = pnl[pnl > 0].sum()
    gl = abs(pnl[pnl < 0].sum())
    pf = gp / gl if gl > 0 else float("inf")
    median = float(np.median(pnl))
    var = float(np.var(pnl))
    std = float(np.std(pnl))
    worst = float(pnl.min())
    p5 = float(np.percentile(pnl, 5))
    win_rate = float((pnl > 0).mean())
    # Equity curve / max DD
    equity = np.cumsum(pnl)
    running_max = np.maximum.accumulate(equity)
    dd = equity - running_max
    max_dd_dollar = float(dd.min())
    # Sharpe annualized — approximate using per-trade SD; trades irregular but rough proxy
    # Use trades/year ≈ n / 6 (6yr window)
    trades_per_year = n / 6
    sharpe = (pnl.mean() / std * np.sqrt(trades_per_year)) if std > 0 else float("nan")
    return {
        "label": label,
        "n_trades": n,
        "net_pnl": net,
        "pf": pf,
        "median_trade": median,
        "win_rate": win_rate,
        "variance_per_trade": var,
        "worst_trade": worst,
        "tail_5pct": p5,
        "max_dd_dollar": max_dd_dollar,
        "sharpe_annualized": sharpe,
        "equity_final": float(equity[-1]) if n else 0,
    }


def step4_compare(metrics_a, metrics_b):
    print("\n" + "=" * 70)
    print("STEP 4 — Comparative metrics")
    print("=" * 70)
    print(f"{'Metric':30s} | {'Run A (1ct)':>15s} | {'Run B (overlay)':>16s} | {'Δ':>10s}")
    print("-" * 78)
    keys = ["n_trades","net_pnl","pf","median_trade","win_rate",
            "variance_per_trade","worst_trade","tail_5pct","max_dd_dollar","sharpe_annualized","equity_final"]
    for k in keys:
        a, b = metrics_a[k], metrics_b[k]
        if isinstance(a, float):
            delta = b - a
            print(f"{k:30s} | {a:>15.3f} | {b:>16.3f} | {delta:>+10.3f}")
        else:
            print(f"{k:30s} | {a:>15} | {b:>16} | {'':>10}")


def step5_propsim(pnl_a, pnl_b, trades_df, account_size=50000, max_dd_pct=0.05, daily_loss_pct=0.025, profit_target_pct=0.08):
    """Simulate FTMO-style prop firm rules."""
    print("\n" + "=" * 70)
    print("STEP 5 — Prop-sim (FTMO-style: $50k acct, 5% trailing DD, 2.5% daily, 8% target)")
    print("=" * 70)

    trades_df = trades_df.copy().reset_index(drop=True)
    trades_df["entry_date"] = pd.to_datetime(trades_df["entry_time"]).dt.normalize()
    trades_df["exit_date"] = pd.to_datetime(trades_df["exit_time"]).dt.normalize()
    n = len(trades_df)

    def simulate(pnl_array):
        # Walk-forward evaluations starting at every month boundary
        starts = pd.date_range(
            trades_df["entry_date"].min().to_period("M").to_timestamp(),
            trades_df["entry_date"].max(), freq="MS"
        )
        passes, fails, neither = 0, 0, 0
        days_to_pass_list = []
        for s in starts:
            equity = account_size
            peak = account_size
            current_day = None
            day_pnl = 0
            outcome = "neither"
            for i, row in trades_df.iterrows():
                if row["entry_date"] < s:
                    continue
                p = pnl_array[i]
                # Daily-loss tracking
                if current_day is None or row["entry_date"] != current_day:
                    if current_day is not None and day_pnl < -daily_loss_pct * account_size:
                        outcome = "fail-daily"
                        break
                    current_day = row["entry_date"]
                    day_pnl = 0
                day_pnl += p
                equity += p
                peak = max(peak, equity)
                # Trailing DD check
                if (peak - equity) > max_dd_pct * account_size:
                    outcome = "fail-dd"
                    break
                # Profit target check
                if equity - account_size >= profit_target_pct * account_size:
                    outcome = "pass"
                    days_to_pass_list.append((row["entry_date"] - s).days)
                    break
            if outcome == "pass":
                passes += 1
            elif outcome.startswith("fail"):
                fails += 1
            else:
                neither += 1
        total = passes + fails + neither
        return {
            "evaluations": total,
            "passes": passes,
            "fails": fails,
            "neither": neither,
            "pass_rate": passes / total if total else 0,
            "avg_days_to_pass": float(np.mean(days_to_pass_list)) if days_to_pass_list else float("nan"),
        }

    sim_a = simulate(pnl_a)
    sim_b = simulate(pnl_b)
    print(f"\n  Run A (1ct):     {sim_a}")
    print(f"  Run B (overlay): {sim_b}")
    print(f"\n  Pass-rate delta: {(sim_b['pass_rate']-sim_a['pass_rate'])*100:+.1f} percentage points")
    return sim_a, sim_b


def step6_verdict(m_a, m_b, sim_a, sim_b):
    print("\n" + "=" * 70)
    print("STEP 6 — Verdict")
    print("=" * 70)

    median_change_pct = (m_b["median_trade"] - m_a["median_trade"]) / abs(m_a["median_trade"]) * 100 if m_a["median_trade"] != 0 else 0
    sharpe_change_pct = (m_b["sharpe_annualized"] - m_a["sharpe_annualized"]) / abs(m_a["sharpe_annualized"]) * 100 if m_a["sharpe_annualized"] != 0 else 0
    dd_change_pct = (m_b["max_dd_dollar"] - m_a["max_dd_dollar"]) / abs(m_a["max_dd_dollar"]) * 100 if m_a["max_dd_dollar"] != 0 else 0
    pass_rate_delta_pp = (sim_b["pass_rate"] - sim_a["pass_rate"]) * 100

    # Note: max_dd_dollar is negative; "improves" means LESS negative i.e. closer to zero
    # So improvement = b - a > 0 (less negative)
    dd_improved_pct = (m_a["max_dd_dollar"] - m_b["max_dd_dollar"]) / abs(m_a["max_dd_dollar"]) * 100  # positive = improvement

    print(f"  Median trade change:   {median_change_pct:+.1f}%   (target: within ±10%)")
    print(f"  Sharpe change:         {sharpe_change_pct:+.1f}%   (target: improves ≥15%)")
    print(f"  Max DD ($) improvement: {dd_improved_pct:+.1f}%   (target: improves ≥10%)")
    print(f"  Prop-sim pass-rate Δ:  {pass_rate_delta_pp:+.1f}pp  (target: improves ≥5pp)")

    median_ok = abs(median_change_pct) <= 10
    sharpe_ok = sharpe_change_pct >= 15
    dd_ok = dd_improved_pct >= 10
    propsim_ok = pass_rate_delta_pp >= 5

    print(f"\n  Criteria met: median={median_ok}  sharpe={sharpe_ok}  dd={dd_ok}  propsim={propsim_ok}")

    if abs(median_change_pct) > 15:
        verdict = "FAIL"
        reason = f"median trade degraded {median_change_pct:.1f}% (>15% threshold)"
    elif median_ok and sharpe_ok and dd_ok and propsim_ok:
        verdict = "PASS"
        reason = "all four criteria met"
    elif median_ok and (sharpe_ok or dd_ok or propsim_ok):
        verdict = "PASS-with-WARN"
        reason = "median preserved; partial improvement on other criteria"
    else:
        verdict = "FAIL"
        reason = "criteria not met"

    print(f"\n  VERDICT: {verdict}")
    print(f"  Reason: {reason}")
    return verdict, reason


def main():
    df, trades_df, _equity_a, config = step1_reproduce_baseline()
    pnl_a, contracts_a = step2_run_a_baseline(trades_df, config)
    pnl_b, contracts_b = step3_run_b_overlay(df, trades_df, config)
    m_a = metrics(pnl_a, "A")
    m_b = metrics(pnl_b, "B")
    step4_compare(m_a, m_b)
    sim_a, sim_b = step5_propsim(pnl_a, pnl_b, trades_df)
    verdict, reason = step6_verdict(m_a, m_b, sim_a, sim_b)

    # Emit machine-readable summary at end
    summary = {
        "verdict": verdict,
        "reason": reason,
        "metrics_a": m_a,
        "metrics_b": m_b,
        "propsim_a": sim_a,
        "propsim_b": sim_b,
        "avg_contracts_b": float(contracts_b.mean()),
        "contract_dist_b": {
            "1c": int((contracts_b==1).sum()),
            "2c": int((contracts_b==2).sum()),
            "3c": int((contracts_b==3).sum()),
        },
    }
    print("\n" + "=" * 70)
    print("MACHINE-READABLE SUMMARY")
    print("=" * 70)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
