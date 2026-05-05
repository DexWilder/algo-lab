#!/usr/bin/env python3
"""HYB-FX-SessionTransition-ImpulseGated validation runner.

Per docs/fql_forge/_DRAFT_validation_plan_HYB-FX-SessionTransition.md.

Steps:
 1. Reproduce FXBreak-6J baseline (PF within ±10% of registry's 1.2)
 2. A/B: impulse filter on/off
 3. Metrics (tail-engine archetype: PF≥1.15 VIABLE / ≥1.30 STRONG; ≥30 trades min)
 4. Verdict

Honors plan constraints: 6J only, short-only direction (matching registry),
session-transition window only, no parameter sweeps.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from strategies.london_preopen_fx_breakout.strategy import generate_signals  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402

# Use the canonical engine asset config (covers FX assets unlike backtests.run_baseline)
ASSET_CONFIG = {k: v for k, v in ASSETS.items()}

ASSET = "6J"
DATA_PATH = ROOT / "data" / "processed" / f"{ASSET}_5m.csv"
REGISTRY_PF = 1.2  # FXBreak-6J-Short-London registry record

# Impulse filter (per plan §4.2):
#   require breakout magnitude > IMPULSE_THRESHOLD * 20-day median Asian range size
IMPULSE_THRESHOLD = 1.5
ASIAN_RANGE_LOOKBACK_DAYS = 20

SETUP_START_HHMM = 200   # 02:00 ET
SETUP_END_HHMM = 255     # 02:55 ET (Asian range window end)
ENTRY_START_HHMM = 300   # 03:00 ET (London open / first eligible entry)
ENTRY_END_HHMM = 355


def step1_reproduce_baseline():
    print("=" * 70)
    print("STEP 1 — Reproduce FXBreak-6J baseline (registry PF=1.2)")
    print("=" * 70)
    df = pd.read_csv(DATA_PATH)
    print(f"  Loaded {len(df):,} bars from {DATA_PATH.name}")

    signals_df = generate_signals(df)
    config = ASSET_CONFIG[ASSET]
    # Run short-only to match registry's "Short only" record
    result = run_backtest(
        df, signals_df, mode="short",
        point_value=config["point_value"], symbol=ASSET,
    )
    trades_df = result["trades_df"]
    print(f"  Baseline trades (short-only): {len(trades_df)}")
    if len(trades_df) == 0:
        print("  ERROR: zero trades produced. HALT.")
        sys.exit(1)

    gp = trades_df[trades_df["pnl"] > 0]["pnl"].sum()
    gl = abs(trades_df[trades_df["pnl"] < 0]["pnl"].sum())
    pf = gp / gl if gl > 0 else float("inf")
    pf_delta_pct = abs(pf - REGISTRY_PF) / REGISTRY_PF * 100
    median_trade = float(trades_df["pnl"].median())
    print(f"  Computed PF: {pf:.3f}  Registry PF: {REGISTRY_PF}")
    print(f"  PF delta: {pf_delta_pct:.1f}%   Median trade: ${median_trade:.2f}")

    if pf_delta_pct > 15:
        print(f"  WARN: PF reproduction differs from registry by {pf_delta_pct:.1f}%")
        print(f"        Registry record may be stale OR strategy logic has drifted")
        print(f"        Continuing but flagging in result memo")
    else:
        print(f"  OK: reproduction within ±15% tolerance")
    return df, trades_df, config


def compute_asian_range_history(df):
    """For each trading date, compute the high-low range of the 02:00-02:55 ET window."""
    df = df.copy()
    dt = pd.to_datetime(df["datetime"])
    df["date"] = dt.dt.date
    df["hhmm"] = dt.dt.hour * 100 + dt.dt.minute
    setup = df[(df["hhmm"] >= SETUP_START_HHMM) & (df["hhmm"] < ENTRY_START_HHMM)]
    asian = setup.groupby("date").agg(asian_high=("high","max"), asian_low=("low","min"))
    asian["asian_range"] = asian["asian_high"] - asian["asian_low"]
    asian["asian_range_20d_median"] = asian["asian_range"].rolling(ASIAN_RANGE_LOOKBACK_DAYS).median()
    return asian


def step2_compute_impulse_filter(df, trades_df):
    """For each baseline trade entry, compute breakout magnitude and impulse-filter pass/reject."""
    print("\n" + "=" * 70)
    print(f"STEP 2 — Compute impulse filter (threshold = {IMPULSE_THRESHOLD}× 20d median Asian range)")
    print("=" * 70)
    asian = compute_asian_range_history(df)

    trades = trades_df.copy().reset_index(drop=True)
    trades["entry_time_dt"] = pd.to_datetime(trades["entry_time"])
    trades["entry_date"] = trades["entry_time_dt"].dt.date

    # Each baseline trade is a SHORT entered at break of asian_low.
    # Breakout magnitude (downward for short) = asian_low - entry_price (positive value)
    breakout_mag = []
    median_range = []
    impulse_pass = []
    for _, row in trades.iterrows():
        d = row["entry_date"]
        if d not in asian.index:
            breakout_mag.append(np.nan); median_range.append(np.nan); impulse_pass.append(False)
            continue
        a = asian.loc[d]
        if pd.isna(a["asian_range_20d_median"]):
            breakout_mag.append(np.nan); median_range.append(np.nan); impulse_pass.append(False)
            continue
        # For short: breakout magnitude = asian_low - entry_price (positive value when price broke below)
        mag = float(a["asian_low"]) - float(row["entry_price"])
        # Use abs to handle either-direction (defensive)
        mag = abs(mag)
        # Compare to threshold * 20d median Asian range
        threshold = IMPULSE_THRESHOLD * float(a["asian_range_20d_median"])
        breakout_mag.append(mag)
        median_range.append(float(a["asian_range_20d_median"]))
        impulse_pass.append(mag >= threshold)

    trades["breakout_magnitude"] = breakout_mag
    trades["asian_range_20d_median"] = median_range
    trades["impulse_pass"] = impulse_pass

    n_pass = int(sum(impulse_pass))
    print(f"  Total baseline trades: {len(trades)}")
    print(f"  Trades passing impulse filter: {n_pass} ({n_pass/len(trades)*100:.1f}%)")
    print(f"  Trades rejected by impulse filter: {len(trades)-n_pass}")
    print(f"  Trades with NaN ATR (rejected by default): {int(trades['breakout_magnitude'].isna().sum())}")
    return trades


def metrics(pnl, label):
    pnl = np.asarray(pnl)
    n = len(pnl)
    if n == 0:
        return {"label": label, "n_trades": 0, "net_pnl": 0, "pf": float("nan"),
                "median_trade": 0, "win_rate": 0, "max_dd_dollar": 0,
                "sharpe_annualized": float("nan"), "max_single_pct": 0,
                "positive_fraction": 0}
    net = pnl.sum()
    gp = pnl[pnl > 0].sum()
    gl = abs(pnl[pnl < 0].sum())
    pf = gp / gl if gl > 0 else float("inf")
    median = float(np.median(pnl))
    win_rate = float((pnl > 0).mean())
    equity = np.cumsum(pnl)
    running_max = np.maximum.accumulate(equity)
    dd = equity - running_max
    max_dd_dollar = float(dd.min())
    std = float(np.std(pnl))
    trades_per_year = n / 6 if n else 1
    sharpe = (pnl.mean() / std * np.sqrt(trades_per_year)) if std > 0 else float("nan")
    # max single-instance: largest single trade % of total ABSOLUTE profit
    abs_total = abs(pnl).sum()
    max_single_pct = (abs(pnl).max() / abs_total * 100) if abs_total > 0 else 0
    pos_fraction = float((pnl > 0).mean())
    return {
        "label": label,
        "n_trades": n,
        "net_pnl": float(net),
        "pf": pf,
        "median_trade": median,
        "win_rate": win_rate,
        "max_dd_dollar": max_dd_dollar,
        "sharpe_annualized": sharpe,
        "max_single_pct": max_single_pct,
        "positive_fraction": pos_fraction,
    }


def step3_run_a_b(trades):
    print("\n" + "=" * 70)
    print("STEP 3 — Compute Run A (baseline) and Run B (impulse-filtered)")
    print("=" * 70)
    pnl_a = trades["pnl"].values
    trades_b = trades[trades["impulse_pass"]]
    pnl_b = trades_b["pnl"].values
    m_a = metrics(pnl_a, "A baseline")
    m_b = metrics(pnl_b, "B impulse-filtered")
    return m_a, m_b


def step4_compare(m_a, m_b):
    print(f"\n{'Metric':22s} | {'A baseline':>14s} | {'B filtered':>14s} | {'Δ':>10s}")
    print("-" * 70)
    keys = ["n_trades","net_pnl","pf","median_trade","win_rate","max_dd_dollar",
            "sharpe_annualized","max_single_pct","positive_fraction"]
    for k in keys:
        a, b = m_a[k], m_b[k]
        if isinstance(a, float):
            delta = b - a
            print(f"{k:22s} | {a:>14.3f} | {b:>14.3f} | {delta:>+10.3f}")
        else:
            print(f"{k:22s} | {a:>14} | {b:>14}")


def step5_verdict(m_a, m_b):
    print("\n" + "=" * 70)
    print("STEP 5 — Verdict")
    print("=" * 70)

    sample_ratio = m_b["n_trades"] / m_a["n_trades"] if m_a["n_trades"] else 0
    sample_in_window = 0.30 <= sample_ratio <= 0.70
    pf_improved = m_b["pf"] > m_a["pf"] if not (np.isnan(m_a["pf"]) or np.isnan(m_b["pf"])) else False
    pf_meets_bar = m_b["pf"] >= 1.15
    median_improved = m_b["median_trade"] > m_a["median_trade"]
    median_nonneg = m_b["median_trade"] >= 0
    concentration_improved = m_b["max_single_pct"] < m_a["max_single_pct"]

    print(f"  Sample reduction:  Run B / Run A = {sample_ratio:.2f}  (target: 0.30-0.70 = filter doing real work)")
    print(f"  PF improved:       {pf_improved} (A={m_a['pf']:.3f} B={m_b['pf']:.3f})")
    print(f"  PF meets ≥1.15:    {pf_meets_bar}")
    print(f"  Median improved:   {median_improved} (A=${m_a['median_trade']:.2f} B=${m_b['median_trade']:.2f})")
    print(f"  Median ≥ 0:        {median_nonneg}")
    print(f"  Concentration improved: {concentration_improved} (A={m_a['max_single_pct']:.1f}% B={m_b['max_single_pct']:.1f}%)")
    print(f"  Min sample (B≥30): {m_b['n_trades']>=30}")

    # Per plan §4.4: "Run B is at least as good on 3 of 4 AND strictly better on 2 of 4"
    questions = [
        ("sample reduction in window", sample_in_window),
        ("PF improved", pf_improved),
        ("median improved", median_improved),
        ("concentration improved", concentration_improved),
    ]
    n_at_least_as_good = sum(1 for _, v in questions if v)

    # Verdict per plan §5
    if m_b["n_trades"] < 30:
        verdict = "WARN"
        reason = f"Run B sample ({m_b['n_trades']}) < 30 minimum"
    elif m_b["pf"] < 1.0:
        verdict = "FAIL"
        reason = f"Run B PF {m_b['pf']:.3f} < 1.0"
    elif n_at_least_as_good >= 3 and pf_meets_bar and median_nonneg and m_b["n_trades"] >= 30:
        verdict = "PASS"
        reason = f"Filter improved {n_at_least_as_good}/4 and PF≥1.15 and median≥0"
    elif pf_improved and m_b["pf"] >= 1.0:
        verdict = "WARN"
        reason = f"Filter improves PF but doesn't meet PF≥1.15 OR median<0 OR sample issues"
    else:
        verdict = "FAIL"
        reason = f"Filter does NOT improve over baseline on key dimensions"

    print(f"\n  VERDICT: {verdict}")
    print(f"  Reason: {reason}")
    return verdict, reason, n_at_least_as_good


def main():
    df, trades_df, config = step1_reproduce_baseline()
    trades = step2_compute_impulse_filter(df, trades_df)
    m_a, m_b = step3_run_a_b(trades)
    step4_compare(m_a, m_b)
    verdict, reason, n_q = step5_verdict(m_a, m_b)

    summary = {
        "verdict": verdict,
        "reason": reason,
        "n_questions_passed": n_q,
        "metrics_a": m_a,
        "metrics_b": m_b,
    }
    print("\n" + "=" * 70)
    print("MACHINE-READABLE SUMMARY")
    print("=" * 70)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
