#!/usr/bin/env python3
"""FQL Batch First-Pass — Factory tool for rapid strategy evaluation.

Runs one strategy across multiple assets, modes, and a walk-forward split.
Produces a standardized JSON report with automatic classification.

This replaces the manual 50-line ad-hoc scripts used during prototyping.
It is the primary throughput tool for the strategy factory pipeline.

Classification rules:
  ADVANCE    — PF > 1.2, trades >= 30, walk-forward both halves PF > 1.0
  SALVAGE    — PF > 1.0, trades >= 20, one mode PF > 1.2 or one WF half PF > 1.3
  MONITOR    — PF > 1.0 but trades < 20, or PF > 1.2 but WF unstable
  REJECT     — PF < 1.0 on all modes, or trades >= 30 with PF < 1.1

Usage:
    # Test on specific assets
    python3 research/batch_first_pass.py --strategy fx_session_breakout --assets 6J,6E,6B

    # Test on all compatible assets (from asset_config)
    python3 research/batch_first_pass.py --strategy momentum_pullback_trend --assets all

    # Test with US-session filter
    python3 research/batch_first_pass.py --strategy momentum_pullback_trend --assets 6J --session us

    # Dry run (show what would be tested)
    python3 research/batch_first_pass.py --strategy vwap_trend --assets all --dry-run
"""

import argparse
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.backtest import run_backtest
from engine.asset_config import ASSETS, get_asset, get_assets_by_status
from research.utils.atomic_io import atomic_write_json

OUTPUT_DIR = ROOT / "research" / "data" / "first_pass"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── Classification Rules ─────────────────────────────────────────────────────
#
# Concentration-aware thresholds (added 2026-04-06 after 4/5 ADVANCE candidates
# failed deep validation due to top-N trade concentration and single-year
# dependence). First-pass must now catch these before labeling ADVANCE.
#
# Thresholds (based on validation outcomes):
#   ADVANCE:  trades ≥ 500, top-3 concentration < 30%, max year share < 40%
#   SALVAGE:  trades ≥ 100 with some directional/period edge
#   THIN:     trades ≥ 20 but < 100 — too few for concentration check to trust
#
# The xb_orb_ema_ladder result (1183 trades, top-3 = 10%) was the only
# candidate that survived deep validation. Below ~500 trades, any apparent
# edge is likely outlier-driven.

CONCENTRATION_TOP3_MAX = 0.30    # top 3 trades < 30% of PnL for ADVANCE
CONCENTRATION_TOP5_MAX = 0.45    # top 5 trades < 45% of PnL for ADVANCE
CONCENTRATION_TOP10_MAX = 0.55   # top 10 trades < 55% of PnL — added 2026-04-07
                                  # after donchian_trend (top-10=55%) and
                                  # ema_trend_rider (top-10=98%) failed validation
                                  # despite passing top-3 check
MAX_YEAR_SHARE = 0.40             # no single year > 40% of PnL for ADVANCE
MIN_MEDIAN_TRADE = 0              # median trade must be non-negative —
                                  # negative median = tail-dependent, not edge
MIN_TRADES_ADVANCE = 500          # concentration trust threshold
MIN_TRADES_ROBUST = 100           # meaningful sample for SALVAGE


def compute_concentration(trades_df):
    """Compute top-N trade concentration and single-year share.

    Returns dict with top3_share, top5_share, top10_share, max_year_share.
    """
    if trades_df is None or len(trades_df) == 0:
        return {"top3_share": 0, "top5_share": 0, "top10_share": 0, "max_year_share": 0}

    total_pnl = trades_df["pnl"].sum()
    if total_pnl <= 0:
        return {"top3_share": 0, "top5_share": 0, "top10_share": 0, "max_year_share": 0}

    sorted_pnl = trades_df["pnl"].sort_values(ascending=False)
    top3 = sorted_pnl.head(3).sum() / total_pnl
    top5 = sorted_pnl.head(5).sum() / total_pnl
    top10 = sorted_pnl.head(10).sum() / total_pnl
    median_trade = float(trades_df["pnl"].median())

    # Year concentration
    year_share = 0
    if "entry_time" in trades_df.columns:
        try:
            trades_df = trades_df.copy()
            trades_df["year"] = pd.to_datetime(trades_df["entry_time"]).dt.year
            yearly = trades_df.groupby("year")["pnl"].sum()
            if yearly.sum() > 0:
                year_share = yearly.max() / yearly.sum()
        except Exception:
            pass

    return {
        "top3_share": round(float(top3), 3),
        "top5_share": round(float(top5), 3),
        "top10_share": round(float(top10), 3),
        "max_year_share": round(float(year_share), 3),
        "median_trade": round(median_trade, 2),
    }


def classify(pf, trades, wf_h1_pf, wf_h2_pf, mode_results, concentration=None):
    """Apply deterministic classification rules with concentration checks.

    Returns (classification, reasons) tuple.
    """
    reasons = []
    conc = concentration or {}
    top3 = conc.get("top3_share", 0)
    top5 = conc.get("top5_share", 0)
    top10 = conc.get("top10_share", 0)
    year_share = conc.get("max_year_share", 0)
    median_trade = conc.get("median_trade", 0)

    # Check if any single mode shows strong edge
    any_mode_above_1_2 = any(m["pf"] > 1.2 and m["trades"] >= 15 for m in mode_results)

    # ── ADVANCE: strong across the board AND concentration-clean ──
    if (pf > 1.2 and trades >= MIN_TRADES_ADVANCE
            and wf_h1_pf > 1.0 and wf_h2_pf > 1.0):
        # Concentration checks (ordered: cheapest first)
        if median_trade < MIN_MEDIAN_TRADE:
            reasons.append(
                f"Median trade ${median_trade:.2f} < 0 — edge is tail-dependent, "
                f"not distributed. Demoted to SALVAGE."
            )
            return "SALVAGE", reasons
        if top3 > CONCENTRATION_TOP3_MAX:
            reasons.append(
                f"Top-3 concentration {top3*100:.0f}% > {CONCENTRATION_TOP3_MAX*100:.0f}% — "
                f"edge is outlier-driven, demoted to SALVAGE"
            )
            return "SALVAGE", reasons
        if top5 > CONCENTRATION_TOP5_MAX:
            reasons.append(
                f"Top-5 concentration {top5*100:.0f}% > {CONCENTRATION_TOP5_MAX*100:.0f}% — "
                f"demoted to SALVAGE"
            )
            return "SALVAGE", reasons
        if top10 > CONCENTRATION_TOP10_MAX:
            reasons.append(
                f"Top-10 concentration {top10*100:.0f}% > {CONCENTRATION_TOP10_MAX*100:.0f}% — "
                f"only a handful of trades drive returns. Demoted to SALVAGE."
            )
            return "SALVAGE", reasons
        if year_share > MAX_YEAR_SHARE:
            reasons.append(
                f"Single year = {year_share*100:.0f}% of PnL (> {MAX_YEAR_SHARE*100:.0f}%) — "
                f"regime dependent, demoted to SALVAGE"
            )
            return "SALVAGE", reasons
        reasons.append(f"PF {pf:.2f} > 1.2 with {trades} trades")
        reasons.append(f"Walk-forward stable: H1={wf_h1_pf:.2f}, H2={wf_h2_pf:.2f}")
        reasons.append(
            f"Concentration clean: top3={top3*100:.0f}%, top5={top5*100:.0f}%, "
            f"top10={top10*100:.0f}%, max year={year_share*100:.0f}%, "
            f"median trade ${median_trade:.2f}"
        )
        return "ADVANCE", reasons

    # ── ADVANCE_THIN: good numbers but low trade count — flag for caution ──
    if (pf > 1.2 and trades >= 30 and trades < MIN_TRADES_ADVANCE
            and wf_h1_pf > 1.0 and wf_h2_pf > 1.0):
        reasons.append(
            f"PF {pf:.2f}, {trades} trades (< {MIN_TRADES_ADVANCE} trust threshold). "
            f"Top-3={top3*100:.0f}%, max year={year_share*100:.0f}%. "
            f"Likely outlier-driven — validate deeply before promotion."
        )
        return "SALVAGE", reasons

    # ── SALVAGE: partial edge worth one follow-up ──
    if pf > 1.0 and trades >= 20:
        if any_mode_above_1_2:
            reasons.append(f"Overall PF {pf:.2f}, directional split shows PF > 1.2")
            return "SALVAGE", reasons
        if wf_h1_pf > 1.3 or wf_h2_pf > 1.3:
            reasons.append(f"Period-specific edge: H1={wf_h1_pf:.2f}, H2={wf_h2_pf:.2f}")
            return "SALVAGE", reasons

    # ── MONITOR: signal but insufficient data ──
    if pf > 1.0 and trades < 20:
        reasons.append(f"PF {pf:.2f} > 1.0 but only {trades} trades — insufficient sample")
        return "MONITOR", reasons
    if pf > 1.2 and (wf_h1_pf < 0.8 or wf_h2_pf < 0.8):
        reasons.append(f"PF {pf:.2f} > 1.2 but walk-forward unstable: H1={wf_h1_pf:.2f}, H2={wf_h2_pf:.2f}")
        return "MONITOR", reasons

    # ── REJECT: no viable edge ──
    if trades >= 30 and pf < 1.1:
        reasons.append(f"Sufficient trades ({trades}) but PF {pf:.2f} < 1.1")
    elif pf < 1.0:
        reasons.append(f"Negative edge: PF {pf:.2f}")
    else:
        reasons.append(f"PF {pf:.2f}, {trades} trades — below all advancement thresholds")
    return "REJECT", reasons


def classify_with_tail_engine(pf, trades, wf_h1_pf, wf_h2_pf, mode_results,
                               concentration=None, trades_df=None):
    """Enhanced classify that routes sparse strategies through tail-engine gates.

    Routing rules (applied in order):
      1. trades >= 500 → PURE workhorse path (classify()).
         This is the intended workhorse archetype; tail-engine inapplicable.

      2. trades < 500 AND workhorse path yields ADVANCE → impossible
         (workhorse ADVANCE requires trades >= 500). Skip.

      3. trades < 500 → evaluate BOTH paths and return the STRICTER verdict.
         - This prevents sparse strategies from cheesing the directional-split
           SALVAGE pathway when they genuinely fail tail-engine concentration
           gates (the SPX Lunch Compression case).
         - If tail-engine REJECTs and workhorse SALVAGEs, return REJECT.
         - If tail-engine STRONG and workhorse SALVAGE, return STRONG.
         - This is the "AND" gate: sparse strategies must pass whichever
           gate is appropriate for their actual trade profile.

    Rationale: sparse strategies are tail-engine by definition. The workhorse
    path can give them lenient "SALVAGE" via directional split even when
    their concentration profile is unsurvivable. Always apply tail-engine
    gates when trades < 500.
    """
    # Workhorse classification (existing logic)
    wh_cls, wh_reasons = classify(pf, trades, wf_h1_pf, wf_h2_pf, mode_results, concentration)

    # If trades >= 500, workhorse-only (intended workhorse archetype)
    if trades >= 500:
        return wh_cls, wh_reasons

    # Sparse strategy: apply tail-engine gates in parallel
    if trades_df is None or len(trades_df) < 8:
        return wh_cls, wh_reasons

    try:
        from research.tail_engine_classification import classify_tail_engine
        te_cls, te_reasons, te_metrics = classify_tail_engine(trades_df)
    except Exception:
        return wh_cls, wh_reasons

    # Strictness ordering
    te_tier = {
        "TAIL_ENGINE_STRONG": 1,
        "TAIL_ENGINE_VIABLE": 2,
        "TAIL_ENGINE_MONITOR": 3,
        "TAIL_ENGINE_REJECT": 4,
    }
    wh_tier = {"ADVANCE": 1, "SALVAGE": 2, "MONITOR": 3, "REJECT": 4}
    te_rank = te_tier.get(te_cls, 5)
    wh_rank = wh_tier.get(wh_cls, 5)

    # Return the STRICTER (higher rank = worse) verdict.
    # This ensures sparse strategies can't dodge tail-engine rejection.
    if te_rank >= wh_rank:
        # Tail-engine is stricter or equal — use tail-engine verdict
        combined_reasons = [f"[tail-engine path — {te_metrics['trades']} trades < 500 workhorse threshold]"]
        combined_reasons.extend(te_reasons)
        if te_rank > wh_rank:
            combined_reasons.append(f"(stricter than workhorse verdict '{wh_cls}')")
        return te_cls, combined_reasons
    else:
        # Workhorse is stricter — use workhorse verdict
        combined_reasons = list(wh_reasons)
        combined_reasons.append(f"(stricter than tail-engine verdict '{te_cls}')")
        return wh_cls, combined_reasons


# ── Metrics ──────────────────────────────────────────────────────────────────

def compute_metrics(trades_df):
    """Compute standard metrics from trades DataFrame."""
    if trades_df.empty:
        return {"trades": 0, "pnl": 0, "pf": 0, "sharpe": 0, "maxdd": 0, "wr": 0, "avg_pnl": 0}

    n = len(trades_df)
    pnl = trades_df["pnl"].sum()
    wins = trades_df[trades_df["pnl"] > 0]
    losses = trades_df[trades_df["pnl"] < 0]
    gw = wins["pnl"].sum() if len(wins) else 0
    gl = abs(losses["pnl"].sum()) if len(losses) else 0
    pf = gw / gl if gl > 0 else (99.0 if gw > 0 else 0.0)
    wr = len(wins) / n * 100

    daily_pnl = trades_df.groupby(
        pd.to_datetime(trades_df["entry_time"]).dt.date
    )["pnl"].sum()
    sharpe = (daily_pnl.mean() / daily_pnl.std() * np.sqrt(252)
              if len(daily_pnl) > 1 and daily_pnl.std() > 0 else 0)

    eq = 50000 + trades_df["pnl"].cumsum()
    maxdd = (eq.cummax() - eq).max()

    return {
        "trades": n,
        "pnl": round(float(pnl), 2),
        "pf": round(float(pf), 3),
        "sharpe": round(float(sharpe), 2),
        "maxdd": round(float(maxdd), 2),
        "wr": round(float(wr), 1),
        "avg_pnl": round(float(pnl / n), 2),
    }


# ── Strategy Loader ──────────────────────────────────────────────────────────

def load_strategy(strategy_name, tick_size):
    """Load a strategy module by name."""
    path = ROOT / "strategies" / strategy_name / "strategy.py"
    if not path.exists():
        raise FileNotFoundError(f"Strategy not found: {path}")
    spec = importlib.util.spec_from_file_location(strategy_name, path)
    mod = importlib.util.module_from_spec(spec)
    mod.TICK_SIZE = tick_size
    spec.loader.exec_module(mod)
    return mod


def _call_generate_signals(mod, df, mode="both", asset=None):
    """Call generate_signals with interface detection.

    Handles both old-style (df) and new-style (df, asset, mode) signatures.
    """
    import inspect
    sig = inspect.signature(mod.generate_signals)
    params = set(sig.parameters.keys())

    kwargs = {}
    if "asset" in params and asset:
        kwargs["asset"] = asset
    if "mode" in params:
        kwargs["mode"] = mode

    return mod.generate_signals(df, **kwargs)


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_data(asset, session_filter=None):
    """Load 5m data for an asset, optionally filtering to a session."""
    path = ROOT / "data" / "processed" / f"{asset}_5m.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])

    if session_filter == "us":
        df = df[df["datetime"].dt.hour.between(8, 16)].reset_index(drop=True)
    elif session_filter == "london":
        df = df[df["datetime"].dt.hour.between(3, 11)].reset_index(drop=True)
    elif session_filter == "tokyo":
        df = df[(df["datetime"].dt.hour >= 18) | (df["datetime"].dt.hour < 3)].reset_index(drop=True)

    return df


# ── Core Runner ──────────────────────────────────────────────────────────────

def run_first_pass(strategy_name, assets, session_filter=None):
    """Run first-pass evaluation across assets and modes.

    Returns structured report dict.
    """
    report = {
        "strategy": strategy_name,
        "run_date": datetime.now().isoformat(),
        "session_filter": session_filter,
        "asset_results": {},
        "best_result": None,
        "overall_classification": "REJECT",
        "overall_reasons": [],
    }

    all_results = []

    for asset in assets:
        cfg = get_asset(asset)
        df = load_data(asset, session_filter)
        if df is None or len(df) < 1000:
            report["asset_results"][asset] = {"error": "No data or insufficient bars"}
            continue

        try:
            mod = load_strategy(strategy_name, cfg["tick_size"])
        except Exception as e:
            report["asset_results"][asset] = {"error": str(e)}
            continue

        asset_report = {"asset": asset, "bars": len(df), "modes": {}, "walk_forward": {}}

        # Run each mode
        mode_results = []
        both_trades_df = None  # Save "both" trades for concentration check
        signal_raw_counts = {}  # raw signal count pre-backtest (for silent failure detection)
        for mode in ["both", "long", "short"]:
            try:
                signals = _call_generate_signals(mod, df.copy(), mode=mode, asset=asset)
                # Handle daily-resampling strategies: if signals has fewer
                # rows than input data, use signals as both df and signals
                bt_df = signals if len(signals) < len(df) else df

                # Silent-failure guard: count raw signals BEFORE backtest.
                # If generate_signals returned zero non-zero signals, the
                # strategy is either genuinely quiet or silently broken
                # (e.g., interface mismatch ignoring mode=). We track this.
                if "signal" in signals.columns:
                    raw_sig_count = int((signals["signal"] != 0).sum())
                else:
                    raw_sig_count = 0
                signal_raw_counts[mode] = raw_sig_count

                r = run_backtest(
                    bt_df, signals, mode=mode,
                    point_value=cfg["point_value"],
                    tick_size=cfg["tick_size"],
                    commission_per_side=cfg["commission_per_side"],
                    slippage_ticks=cfg["slippage_ticks"],
                )
                m = compute_metrics(r["trades_df"])
                m["mode"] = mode
                m["raw_signals"] = raw_sig_count
                asset_report["modes"][mode] = m
                mode_results.append(m)
                if mode == "both":
                    both_trades_df = r["trades_df"]
            except Exception as e:
                asset_report["modes"][mode] = {"error": str(e), "trades": 0, "pf": 0}
                mode_results.append({"pf": 0, "trades": 0, "mode": mode})
                signal_raw_counts[mode] = 0

        # Silent failure flag: zero raw signals across ALL modes on a sufficient
        # sample. This catches the 2026-04-06 interface-mismatch bug where
        # batch_first_pass was passing mode= to strategies that didn't accept it,
        # and the failure was silently caught as "REJECT 0 trades".
        total_raw = sum(signal_raw_counts.values())
        if total_raw == 0 and len(df) >= 10000:
            asset_report["silent_failure_suspected"] = True
            asset_report["silent_failure_reason"] = (
                f"Strategy produced ZERO signals across all modes on {len(df)} bars. "
                f"Likely causes: interface mismatch (mode=/asset= param ignored), "
                f"broken signal logic, or data column issue. Inspect generate_signals() "
                f"signature and output shape."
            )

        # Walk-forward on "both" mode
        mid = len(df) // 2
        wf = {}
        for label, sub in [("H1", df.iloc[:mid]), ("H2", df.iloc[mid:])]:
            try:
                mod = load_strategy(strategy_name, cfg["tick_size"])
                sub_reset = sub.copy().reset_index(drop=True)
                signals = _call_generate_signals(mod, sub_reset, mode="both", asset=asset)
                bt_df = signals if len(signals) < len(sub_reset) else sub_reset
                r = run_backtest(
                    bt_df, signals, mode="both",
                    point_value=cfg["point_value"],
                    tick_size=cfg["tick_size"],
                    commission_per_side=cfg["commission_per_side"],
                    slippage_ticks=cfg["slippage_ticks"],
                )
                wf[label] = compute_metrics(r["trades_df"])
            except Exception as e:
                wf[label] = {"error": str(e), "pf": 0, "trades": 0}
        asset_report["walk_forward"] = wf

        # Concentration metrics from "both" mode
        concentration = compute_concentration(both_trades_df)
        asset_report["concentration"] = concentration

        # Classify this asset — uses tail-engine gates as fallback for sparse strategies
        both = asset_report["modes"].get("both", {"pf": 0, "trades": 0})
        h1_pf = wf.get("H1", {}).get("pf", 0)
        h2_pf = wf.get("H2", {}).get("pf", 0)
        cls, reasons = classify_with_tail_engine(
            both.get("pf", 0), both.get("trades", 0),
            h1_pf, h2_pf, mode_results,
            concentration=concentration,
            trades_df=both_trades_df,
        )
        asset_report["classification"] = cls
        asset_report["classification_reasons"] = reasons

        # Auto per-event decomposition for composite event strategies.
        # Triggered when strategy module declares EVENT_CLASSIFIER.
        # Diagnostic discovered 2026-04-08 during Macro Event Box salvage.
        event_classifier = getattr(mod, "EVENT_CLASSIFIER", None)
        if (event_classifier is not None
                and both_trades_df is not None
                and len(both_trades_df) >= 20):
            try:
                from research.tail_engine_classification import decompose_by_event_type
                decomposition = decompose_by_event_type(both_trades_df, event_classifier)
                asset_report["event_decomposition"] = decomposition
            except Exception as e:
                asset_report["event_decomposition_error"] = str(e)

        report["asset_results"][asset] = asset_report
        all_results.append((asset, cls, both.get("pf", 0), both.get("trades", 0)))

    # Overall classification: best asset determines overall
    cls_rank = {"ADVANCE": 4, "SALVAGE": 3, "MONITOR": 2, "REJECT": 1}
    if all_results:
        best = max(all_results, key=lambda x: (cls_rank.get(x[1], 0), x[2]))
        report["best_result"] = {
            "asset": best[0],
            "classification": best[1],
            "pf": best[2],
            "trades": best[3],
        }
        report["overall_classification"] = best[1]
        report["overall_reasons"] = report["asset_results"][best[0]].get("classification_reasons", [])

    return report


# ── Output ───────────────────────────────────────────────────────────────────

def print_report(report):
    """Print formatted terminal report."""
    W = 70
    print()
    print("=" * W)
    print(f"  FQL FIRST-PASS: {report['strategy']}")
    print(f"  {report['run_date'][:19]}")
    if report["session_filter"]:
        print(f"  Session filter: {report['session_filter']}")
    print("=" * W)

    for asset, ar in report["asset_results"].items():
        if "error" in ar:
            print(f"\n  {asset}: ERROR — {ar['error']}")
            continue

        cls = ar.get("classification", "?")
        icon = {"ADVANCE": "+", "SALVAGE": "~", "MONITOR": "?", "REJECT": "X"}.get(cls, "!")
        print(f"\n  [{icon}] {asset} — {cls}")

        # Silent failure warning — loud so it can't be missed
        if ar.get("silent_failure_suspected"):
            print(f"  {'':4s}*** SILENT FAILURE SUSPECTED ***")
            print(f"  {'':4s}{ar.get('silent_failure_reason', '')}")
        print(f"  {'':4s}{'Mode':<7s} {'Trades':>7s} {'PnL':>10s} {'PF':>6s} {'Sharpe':>7s} {'WR':>5s}")
        print(f"  {'':4s}{'-' * 45}")
        for mode in ["both", "long", "short"]:
            m = ar["modes"].get(mode, {})
            if "error" in m:
                print(f"  {'':4s}{mode:<7s} ERROR")
                continue
            print(f"  {'':4s}{mode:<7s} {m['trades']:>7d} {m['pnl']:>10,.0f} {m['pf']:>6.2f} {m['sharpe']:>7.2f} {m['wr']:>4.0f}%")

        wf = ar.get("walk_forward", {})
        h1 = wf.get("H1", {})
        h2 = wf.get("H2", {})
        print(f"  {'':4s}WF: H1={h1.get('pf', 0):.2f} ({h1.get('trades', 0)}t)  H2={h2.get('pf', 0):.2f} ({h2.get('trades', 0)}t)")

        for reason in ar.get("classification_reasons", []):
            print(f"  {'':4s}  > {reason}")

        # Per-event decomposition (when strategy has EVENT_CLASSIFIER)
        decomp = ar.get("event_decomposition")
        if decomp:
            try:
                from research.tail_engine_classification import print_event_decomposition
                print_event_decomposition(f"{report['strategy']} on {asset}", decomp)
            except Exception:
                pass

    best = report.get("best_result")
    if best:
        print(f"\n{'=' * W}")
        print(f"  OVERALL: {report['overall_classification']}")
        print(f"  Best: {best['asset']} — PF {best['pf']:.2f}, {best['trades']} trades")
        print(f"{'=' * W}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FQL Batch First-Pass — rapid strategy evaluation")
    parser.add_argument("--strategy", required=True,
                        help="Strategy directory name (e.g., fx_session_breakout)")
    parser.add_argument("--assets", required=True,
                        help="Comma-separated assets or 'all' for all with data")
    parser.add_argument("--session", default=None, choices=["us", "london", "tokyo"],
                        help="Session filter (optional)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be tested, don't run")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON only")
    args = parser.parse_args()

    # Resolve assets
    if args.assets.lower() == "all":
        # All assets with data files
        assets = [sym for sym in ASSETS
                  if (ROOT / "data" / "processed" / f"{sym}_5m.csv").exists()]
    else:
        assets = [a.strip().upper() for a in args.assets.split(",")]

    if args.dry_run:
        print(f"Strategy: {args.strategy}")
        print(f"Assets: {', '.join(assets)}")
        print(f"Session: {args.session or 'none'}")
        print(f"Modes: both, long, short")
        print(f"Walk-forward: 50/50 split per asset")
        print(f"Output: {OUTPUT_DIR}/")
        return

    # Run
    report = run_first_pass(args.strategy, assets, args.session)

    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    session_tag = f"_{args.session}" if args.session else ""
    filename = f"{args.strategy}{session_tag}_{timestamp}.json"
    out_path = OUTPUT_DIR / filename
    atomic_write_json(out_path, report)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print_report(report)
        print(f"\n  Report saved: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
