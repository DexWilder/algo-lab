#!/usr/bin/env python3
"""Tail-Engine Classification Framework — criteria for sparse strategies.

The workhorse gates (in batch_first_pass.py classify()) require 500+ trades
and tight concentration metrics. Those gates correctly catch fragile
workhorse wannabes but REJECT legitimate tail engines by construction —
event-driven, session-specific, and carry-rotation strategies are sparse
by design.

This framework introduces a SECOND classification path for sparse strategies.
It does NOT replace workhorse gates — it complements them.

A strategy is classified as TAIL_ENGINE_* when:
  - Designed to fire sparsely (event/session/carry/regime)
  - OR naturally produces <500 trades on 6.7y of 5m data
  - OR has cadence_class in {"sparse_event", "monthly_rebalance", "sparse_regime"}

Tail-engine gates (different from workhorse):
  - MIN_TRADES:             8   (vs 500 for workhorse)
  - MAX_TOP3_SHARE:         0.50  (vs 0.30 — tail strategies ARE tail-dependent)
  - MAX_TOP5_SHARE:         0.70  (vs 0.45)
  - MIN_MEDIAN_TRADE:       0     (same — edge must still be distributed)
  - MAX_SINGLE_INSTANCE:    0.35  (no single event/session > 35% of PnL)
  - MIN_POSITIVE_INSTANCES: 0.60  (60%+ of event instances profitable)
  - MAX_DD_DURATION:        900 days (vs 500 — tolerate longer flats)
  - MIN_CROSS_INSTANCE_STABILITY: variance of per-instance PnL / mean < 3.0

Instance = one realization of the sparse event/session/period.
  - For event strategies: one event (e.g., one NFP release)
  - For session strategies: one session-day (e.g., one Tokyo session)
  - For carry rotation: one rebalance period

Usage:
    from tail_engine_classification import classify_tail_engine
    result = classify_tail_engine(trades_df, instance_id_col="event_date")
"""

import numpy as np
import pandas as pd


# ── Tail-engine gate thresholds ──────────────────────────────────────────

TE_MIN_TRADES = 8
TE_MAX_TOP3_SHARE = 0.50
TE_MAX_TOP5_SHARE = 0.70
TE_MIN_MEDIAN_TRADE = 0.0
TE_MAX_SINGLE_INSTANCE_SHARE = 0.35
TE_MIN_POSITIVE_INSTANCE_FRAC = 0.60
TE_MAX_DD_DURATION_DAYS = 900
TE_MAX_CV_INSTANCES = 3.0  # coefficient of variation (std/|mean|)
TE_MAX_SINGLE_YEAR_SHARE = 0.50


def compute_tail_engine_metrics(trades_df, instance_col=None):
    """Compute metrics needed for tail-engine classification.

    Parameters
    ----------
    trades_df : DataFrame with columns: entry_time, pnl, side (optional)
    instance_col : str or None
        Column name identifying the 'instance' of the sparse event.
        If None, falls back to grouping by entry_time date.

    Returns
    -------
    dict of metrics
    """
    if trades_df is None or len(trades_df) == 0:
        return {
            "trades": 0, "total_pnl": 0, "pf": 0, "median_trade": 0,
            "top3_share": 0, "top5_share": 0, "top10_share": 0,
            "max_instance_share": 0, "positive_instance_frac": 0,
            "instance_count": 0, "cv_instances": float("inf"),
            "max_dd_duration_days": 0, "max_year_share": 0,
        }

    td = trades_df.copy()
    td["entry_time"] = pd.to_datetime(td["entry_time"])
    n = len(td)
    total_pnl = float(td["pnl"].sum())

    # PF
    wins = td.loc[td["pnl"] > 0, "pnl"].sum()
    losses = abs(td.loc[td["pnl"] < 0, "pnl"].sum())
    pf = float(wins / losses) if losses > 0 else (99.0 if wins > 0 else 0.0)

    # Concentration
    median_trade = float(td["pnl"].median())
    if total_pnl > 0:
        sorted_pnl = td["pnl"].sort_values(ascending=False)
        top3 = float(sorted_pnl.head(3).sum() / total_pnl)
        top5 = float(sorted_pnl.head(5).sum() / total_pnl)
        top10 = float(sorted_pnl.head(10).sum() / total_pnl)
    else:
        top3 = top5 = top10 = 0.0

    # Instance aggregation
    if instance_col is None or instance_col not in td.columns:
        td["_instance"] = td["entry_time"].dt.date
    else:
        td["_instance"] = td[instance_col]

    instance_pnl = td.groupby("_instance")["pnl"].sum()
    instance_count = len(instance_pnl)

    if instance_count > 0 and total_pnl > 0:
        max_instance_share = float(instance_pnl.max() / total_pnl)
    else:
        max_instance_share = 0.0

    positive_instance_frac = (
        float((instance_pnl > 0).sum() / instance_count)
        if instance_count > 0 else 0.0
    )

    if instance_count >= 3:
        mean_inst = instance_pnl.mean()
        std_inst = instance_pnl.std()
        cv = float(std_inst / abs(mean_inst)) if mean_inst != 0 else float("inf")
    else:
        cv = float("inf")

    # Max year share
    td["year"] = td["entry_time"].dt.year
    yearly = td.groupby("year")["pnl"].sum()
    if yearly.sum() > 0:
        max_year_share = float(yearly.max() / yearly.sum())
    else:
        max_year_share = 0.0

    # Drawdown duration
    td_sorted = td.sort_values("entry_time")
    eq = td_sorted["pnl"].cumsum()
    peak = eq.cummax()
    underwater = eq < peak
    max_dd_days = 0
    start = None
    for i, uw in enumerate(underwater.values):
        if uw and start is None:
            start = td_sorted["entry_time"].iloc[i]
        elif not uw and start is not None:
            days = (td_sorted["entry_time"].iloc[i] - start).days
            if days > max_dd_days:
                max_dd_days = days
            start = None
    if start is not None:
        days = (td_sorted["entry_time"].iloc[-1] - start).days
        if days > max_dd_days:
            max_dd_days = days

    return {
        "trades": n,
        "total_pnl": round(total_pnl, 2),
        "pf": round(pf, 3),
        "median_trade": round(median_trade, 2),
        "top3_share": round(top3, 3),
        "top5_share": round(top5, 3),
        "top10_share": round(top10, 3),
        "max_instance_share": round(max_instance_share, 3),
        "positive_instance_frac": round(positive_instance_frac, 3),
        "instance_count": instance_count,
        "cv_instances": round(cv, 3) if cv != float("inf") else None,
        "max_dd_duration_days": max_dd_days,
        "max_year_share": round(max_year_share, 3),
    }


def classify_tail_engine(trades_df, instance_col=None, min_pf=1.15):
    """Apply tail-engine classification gates.

    Returns (classification, reasons, metrics) tuple.

    Classifications:
      - TAIL_ENGINE_STRONG: passes all gates with PF >= 1.30
      - TAIL_ENGINE_VIABLE: passes all gates with PF >= min_pf
      - TAIL_ENGINE_MONITOR: PF >= 1.0 but one gate marginal
      - TAIL_ENGINE_REJECT: fails multiple gates
    """
    m = compute_tail_engine_metrics(trades_df, instance_col)
    reasons = []
    failures = []

    # Hard gates
    if m["trades"] < TE_MIN_TRADES:
        failures.append(f"trades {m['trades']} < {TE_MIN_TRADES}")
    if m["median_trade"] < TE_MIN_MEDIAN_TRADE:
        failures.append(f"median trade ${m['median_trade']:.2f} < 0 (tail-dependent)")
    if m["top3_share"] > TE_MAX_TOP3_SHARE:
        failures.append(f"top-3 {m['top3_share']*100:.0f}% > {TE_MAX_TOP3_SHARE*100:.0f}%")
    if m["top5_share"] > TE_MAX_TOP5_SHARE:
        failures.append(f"top-5 {m['top5_share']*100:.0f}% > {TE_MAX_TOP5_SHARE*100:.0f}%")
    if m["max_instance_share"] > TE_MAX_SINGLE_INSTANCE_SHARE:
        failures.append(f"single instance {m['max_instance_share']*100:.0f}% > {TE_MAX_SINGLE_INSTANCE_SHARE*100:.0f}%")
    if m["positive_instance_frac"] < TE_MIN_POSITIVE_INSTANCE_FRAC:
        failures.append(f"positive instances {m['positive_instance_frac']*100:.0f}% < {TE_MIN_POSITIVE_INSTANCE_FRAC*100:.0f}%")
    if m["max_dd_duration_days"] > TE_MAX_DD_DURATION_DAYS:
        failures.append(f"max DD {m['max_dd_duration_days']}d > {TE_MAX_DD_DURATION_DAYS}d")
    if m["max_year_share"] > TE_MAX_SINGLE_YEAR_SHARE:
        failures.append(f"single year {m['max_year_share']*100:.0f}% > {TE_MAX_SINGLE_YEAR_SHARE*100:.0f}%")
    if m["cv_instances"] is not None and m["cv_instances"] > TE_MAX_CV_INSTANCES:
        failures.append(f"instance CV {m['cv_instances']:.2f} > {TE_MAX_CV_INSTANCES}")

    if m["pf"] < 1.0:
        failures.append(f"PF {m['pf']} < 1.0")

    if failures:
        return "TAIL_ENGINE_REJECT", failures, m

    # Passed all gates. Rank by PF.
    if m["pf"] >= 1.30:
        reasons.append(f"PF {m['pf']}, {m['trades']} trades across {m['instance_count']} instances")
        reasons.append(
            f"top3={m['top3_share']*100:.0f}%, top5={m['top5_share']*100:.0f}%, "
            f"max instance={m['max_instance_share']*100:.0f}%, "
            f"positive instances={m['positive_instance_frac']*100:.0f}%"
        )
        return "TAIL_ENGINE_STRONG", reasons, m
    elif m["pf"] >= min_pf:
        reasons.append(f"PF {m['pf']} meets min threshold {min_pf}")
        return "TAIL_ENGINE_VIABLE", reasons, m
    else:
        reasons.append(f"PF {m['pf']} positive but below {min_pf}")
        return "TAIL_ENGINE_MONITOR", reasons, m


def print_tail_engine_report(name, classification, reasons, metrics):
    """Print a readable tail-engine classification report."""
    print()
    print(f"=== {name} — {classification} ===")
    print()
    print(f"  Trades: {metrics['trades']}  Instances: {metrics['instance_count']}")
    print(f"  PF: {metrics['pf']}  Total PnL: ${metrics['total_pnl']:.0f}  Median trade: ${metrics['median_trade']:.2f}")
    print()
    print(f"  Concentration:")
    print(f"    top-3:  {metrics['top3_share']*100:.1f}%  (tail-engine limit: {TE_MAX_TOP3_SHARE*100:.0f}%)")
    print(f"    top-5:  {metrics['top5_share']*100:.1f}%  (tail-engine limit: {TE_MAX_TOP5_SHARE*100:.0f}%)")
    print(f"    top-10: {metrics['top10_share']*100:.1f}%")
    print()
    print(f"  Instance stability:")
    print(f"    max single instance: {metrics['max_instance_share']*100:.1f}%  (limit: {TE_MAX_SINGLE_INSTANCE_SHARE*100:.0f}%)")
    print(f"    positive instances:  {metrics['positive_instance_frac']*100:.1f}%  (min: {TE_MIN_POSITIVE_INSTANCE_FRAC*100:.0f}%)")
    if metrics['cv_instances'] is not None:
        print(f"    coefficient of variation: {metrics['cv_instances']:.2f}  (max: {TE_MAX_CV_INSTANCES})")
    print()
    print(f"  Risk profile:")
    print(f"    max DD duration: {metrics['max_dd_duration_days']}d  (limit: {TE_MAX_DD_DURATION_DAYS}d)")
    print(f"    max year share: {metrics['max_year_share']*100:.1f}%  (limit: {TE_MAX_SINGLE_YEAR_SHARE*100:.0f}%)")
    print()
    if classification == "TAIL_ENGINE_REJECT":
        print(f"  FAILURES:")
        for r in reasons:
            print(f"    - {r}")
    else:
        print(f"  Reasons:")
        for r in reasons:
            print(f"    - {r}")
    print()


# ── Cadence classification (helper to decide which gate to apply) ────────

def infer_cadence(trades_df, strategy_registry_entry=None):
    """Decide whether to apply workhorse or tail-engine gates.

    Priority:
      1. Explicit registry field event_cadence.cadence_class
      2. Trade count: <500 over 6+ years → tail-engine
      3. Trade cadence: if >1 trade per week avg → workhorse, else tail-engine
    """
    if strategy_registry_entry:
        ec = strategy_registry_entry.get("event_cadence", {})
        cc = ec.get("cadence_class")
        if cc in ("sparse_event", "monthly_rebalance", "sparse_regime", "session_only"):
            return "tail_engine"
        if cc in ("continuous", "intraday_grinder"):
            return "workhorse"

    if trades_df is None or len(trades_df) == 0:
        return "tail_engine"  # Default for empty

    n = len(trades_df)
    if n < 500:
        return "tail_engine"

    # Check weeks in sample
    td = trades_df.copy()
    td["entry_time"] = pd.to_datetime(td["entry_time"])
    weeks = (td["entry_time"].max() - td["entry_time"].min()).days / 7.0
    if weeks < 1:
        return "tail_engine"
    trades_per_week = n / weeks
    return "workhorse" if trades_per_week >= 1.0 else "tail_engine"


if __name__ == "__main__":
    # Quick self-test
    print("Tail-Engine Classification Framework")
    print("====================================")
    print()
    print("Gates:")
    print(f"  MIN_TRADES: {TE_MIN_TRADES}")
    print(f"  MAX_TOP3_SHARE: {TE_MAX_TOP3_SHARE}")
    print(f"  MAX_TOP5_SHARE: {TE_MAX_TOP5_SHARE}")
    print(f"  MAX_SINGLE_INSTANCE_SHARE: {TE_MAX_SINGLE_INSTANCE_SHARE}")
    print(f"  MIN_POSITIVE_INSTANCE_FRAC: {TE_MIN_POSITIVE_INSTANCE_FRAC}")
    print(f"  MAX_DD_DURATION_DAYS: {TE_MAX_DD_DURATION_DAYS}")
    print(f"  MAX_CV_INSTANCES: {TE_MAX_CV_INSTANCES}")
    print(f"  MAX_SINGLE_YEAR_SHARE: {TE_MAX_SINGLE_YEAR_SHARE}")
