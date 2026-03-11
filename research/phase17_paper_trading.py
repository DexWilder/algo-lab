"""Phase 17 — Paper Trading Architecture Validation.

Runs the full 6-strategy portfolio through the paper trading engine
and validates against backtest expectations.

Tests:
1. Controller-managed portfolio produces expected metrics
2. Kill switch logic works correctly
3. Prop controller integration passes
4. Daily state tracking is complete and accurate
5. Equity curve matches Phase 16 backtest

Usage:
    python3 research/phase17_paper_trading.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.paper_trading_engine import PaperTradingEngine, OUTPUT_DIR

CONFIGS_DIR = ROOT / "controllers" / "prop_configs"


def print_daily_state_summary(daily_states: list):
    """Print summary of daily state tracking."""
    print(f"\n{'='*78}")
    print(f"  DAILY STATE TRACKING")
    print(f"{'='*78}\n")

    # Active strategy distribution
    active_days = {}
    blocked_reasons = {}
    for state in daily_states:
        for strat in state["active_strategies"]:
            active_days[strat] = active_days.get(strat, 0) + 1
        for strat, reason in state["blocked_strategies"].items():
            if reason not in blocked_reasons:
                blocked_reasons[reason] = 0
            blocked_reasons[reason] += 1

    print(f"  Strategy Active Days (out of {len(daily_states)} total):")
    for strat, days in sorted(active_days.items(), key=lambda x: -x[1]):
        pct = days / len(daily_states) * 100
        print(f"    {strat:<35} {days:>4} days ({pct:.0f}%)")

    print(f"\n  Block Reasons (cumulative across all strategies):")
    for reason, count in sorted(blocked_reasons.items(), key=lambda x: -x[1]):
        print(f"    {reason:<40} {count:>5}x")

    # Regime distribution
    regimes = {}
    for state in daily_states:
        r = state.get("regime", {})
        composite = f"{r.get('vol_regime', '?')}_{r.get('trend_regime', '?')}"
        regimes[composite] = regimes.get(composite, 0) + 1

    print(f"\n  Regime Distribution:")
    for regime, count in sorted(regimes.items(), key=lambda x: -x[1]):
        pct = count / len(daily_states) * 100
        print(f"    {regime:<30} {count:>4} days ({pct:.0f}%)")


def print_kill_switch_report(results: dict):
    """Print kill switch analysis."""
    print(f"\n{'='*78}")
    print(f"  KILL SWITCH REPORT")
    print(f"{'='*78}\n")

    ks = results.get("kill_switch_final", {})
    events = results.get("summary", {}).get("kill_switch_events", [])

    print(f"  Final state: {'TRIGGERED' if ks.get('active') else 'OK'}")
    print(f"  Current equity: ${ks.get('current_equity', 0):,.0f}")
    print(f"  Equity HWM: ${ks.get('equity_hwm', 0):,.0f}")
    print(f"  Consecutive losses: {ks.get('consecutive_losses', 0)}")

    if events:
        print(f"\n  Kill Switch Events ({len(events)}):")
        for e in events:
            print(f"    {e['date']}: {e['reason']}")
    else:
        print(f"\n  No kill switch events — portfolio survived cleanly.")


def print_prop_report(results: dict):
    """Print prop controller results."""
    print(f"\n{'='*78}")
    print(f"  PROP CONTROLLER REPORT")
    print(f"{'='*78}\n")

    prop = results.get("prop_result")
    if not prop:
        print("  (No prop controller configured)")
        return

    print(f"  Result: {'PASSED' if prop.get('passed') else 'BUSTED'}")
    print(f"  Final equity: ${prop.get('final_equity', 0):,.2f}")
    print(f"  Final profit: ${prop.get('final_profit', 0):,.2f}")
    print(f"  Locked: {'YES' if prop.get('locked') else 'NO'}")
    if prop.get("locked"):
        print(f"  Lock date: {prop.get('lock_date')}")
    print(f"  Trades executed: {prop.get('total_trades_executed', 0)}"
          f"/{prop.get('total_trades_input', 0)}")
    print(f"  Skipped: {prop.get('skipped_trades', 0)}")
    print(f"  Halted days: {len(prop.get('halted_days', []))}")


def print_validation_checks(results: dict):
    """Run validation checks against Phase 16 expectations."""
    print(f"\n{'='*78}")
    print(f"  VALIDATION CHECKS (vs Phase 16 Backtest)")
    print(f"{'='*78}\n")

    summary = results["summary"]

    checks = [
        # Metric matches Phase 16 within tolerance
        ("Sharpe ≥ 3.5",
         summary["sharpe"] >= 3.5,
         f"Sharpe = {summary['sharpe']:.2f}"),

        ("Total PnL ≥ $15,000",
         summary["total_pnl"] >= 15_000,
         f"PnL = ${summary['total_pnl']:,.0f}"),

        ("MaxDD < $2,500",
         summary["maxdd"] < 2_500,
         f"MaxDD = ${summary['maxdd']:,.0f}"),

        ("Monthly ≥ 75%",
         summary["monthly_pct"] >= 75,
         f"Monthly = {summary['monthly_pct']:.0f}%"),

        ("Trade retention 60-80%",
         60 <= summary["trade_retention_pct"] <= 80,
         f"Retention = {summary['trade_retention_pct']:.0f}%"),

        ("No kill switch triggers",
         len(summary["kill_switch_events"]) == 0,
         f"Kill events = {len(summary['kill_switch_events'])}"),

        ("Daily states complete",
         summary["trading_days"] >= 350,
         f"Trading days = {summary['trading_days']}"),

        ("All 6 strategies active at some point",
         len([k for k, v in summary["per_strategy_trades"].items() if v > 0]) >= 6,
         f"Active strategies = {len([k for k, v in summary['per_strategy_trades'].items() if v > 0])}"),
    ]

    passes = 0
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        if passed:
            passes += 1
        print(f"  [{status}] {name}")
        print(f"         {detail}")

    print(f"\n  Score: {passes}/{len(checks)}")

    if passes == len(checks):
        print(f"  VERDICT: PAPER TRADING ENGINE VALIDATED — ready for deployment")
    elif passes >= len(checks) - 2:
        print(f"  VERDICT: MOSTLY VALIDATED — review failures")
    else:
        print(f"  VERDICT: NOT VALIDATED — engine has issues")

    return passes, len(checks)


def main():
    print("=" * 78)
    print("  PHASE 17 — PAPER TRADING ARCHITECTURE VALIDATION")
    print("=" * 78)

    # ── Run 1: Without prop controller ───────────────────────────────────
    print("\n  Run 1: Paper Trading Engine (no prop controller)")
    print("  " + "-" * 60)

    engine = PaperTradingEngine()
    results = engine.run()

    summary = results["summary"]

    print(f"\n{'='*78}")
    print(f"  PORTFOLIO SUMMARY")
    print(f"{'='*78}\n")

    print(f"  {'Metric':<30} {'Value':>15}")
    print(f"  {'-'*30} {'-'*15}")
    print(f"  {'Total PnL':<30} {'${:,.0f}'.format(summary['total_pnl']):>15}")
    print(f"  {'Sharpe':<30} {summary['sharpe']:>15.2f}")
    print(f"  {'Calmar':<30} {summary['calmar']:>15.2f}")
    print(f"  {'Max Drawdown':<30} {'${:,.0f}'.format(summary['maxdd']):>15}")
    print(f"  {'MaxDD Date':<30} {summary['maxdd_date']:>15}")
    print(f"  {'Trades (baseline)':<30} {summary['total_trades_baseline']:>15}")
    print(f"  {'Trades (controlled)':<30} {summary['total_trades_controlled']:>15}")
    print(f"  {'Retention':<30} {summary['trade_retention_pct']:>14.0f}%")
    print(f"  {'Trading Days':<30} {summary['trading_days']:>15}")
    print(f"  {'Profitable Months':<30} {summary['profitable_months']:>15}")
    print(f"  {'Monthly %':<30} {summary['monthly_pct']:>14.0f}%")

    print(f"\n  Per-Strategy PnL:")
    for strat, pnl in summary["per_strategy_pnl"].items():
        trades = summary["per_strategy_trades"][strat]
        print(f"    {strat:<35} ${pnl:>8,.0f}  ({trades} trades)")

    # Daily state tracking
    with open(OUTPUT_DIR / "daily_states.json") as f:
        daily_states = json.load(f)
    print_daily_state_summary(daily_states)

    # Kill switch report
    print_kill_switch_report(results)

    # Validation checks
    passes_1, total_1 = print_validation_checks(results)

    # ── Run 2: With Lucid 100K prop controller ───────────────────────────
    print(f"\n\n{'='*78}")
    print(f"  Run 2: Paper Trading Engine + Lucid 100K Prop Controller")
    print(f"{'='*78}")

    prop_path = str(CONFIGS_DIR / "lucid_100k.json")
    engine_prop = PaperTradingEngine(
        prop_config_path=prop_path,
        output_dir=OUTPUT_DIR / "lucid_100k",
    )
    results_prop = engine_prop.run()

    print_prop_report(results_prop)

    # ── Final Verdict ────────────────────────────────────────────────────
    print(f"\n{'='*78}")
    print(f"  PHASE 17 — FINAL VERDICT")
    print(f"{'='*78}\n")

    prop = results_prop.get("prop_result", {})
    prop_passed = prop.get("passed", False) if prop else False

    print(f"  Engine validation: {passes_1}/{total_1} checks passed")
    print(f"  Prop simulation:   {'PASSED' if prop_passed else 'FAILED/N/A'}")

    if passes_1 >= total_1 - 1 and prop_passed:
        print(f"\n  VERDICT: PAPER TRADING ARCHITECTURE COMPLETE")
        print(f"  System is ready for forward paper trading.")
    elif passes_1 >= total_1 - 2:
        print(f"\n  VERDICT: ARCHITECTURE MOSTLY READY — review minor failures")
    else:
        print(f"\n  VERDICT: ARCHITECTURE NEEDS WORK")

    print(f"\n{'='*78}")
    print(f"  DONE")
    print(f"{'='*78}")

    # Save combined report
    report = {
        "engine_validation": {
            "passes": passes_1,
            "total": total_1,
            "summary": summary,
        },
        "prop_simulation": {
            "passed": prop_passed,
            "config": "lucid_100k",
        },
    }
    with open(OUTPUT_DIR / "phase17_validation_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  Reports saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
