#!/usr/bin/env python3
"""FQL Execution Quality Monitor — Detect execution-related performance degradation.

Distinguishes true edge drift from execution friction by tracking:
    - Signal retention rate (generated vs taken vs blocked)
    - Controller blocking patterns (regime, timing, prop)
    - Modeled slippage impact per strategy
    - Trade retention by regime and session
    - Missing trade opportunity cost

Current Phase: PAPER TRADING
    - No real broker fills yet — tracks simulated execution quality
    - Extension points marked for broker integration (Phase 7)

Future Phase: LIVE EXECUTION
    - Expected entry vs actual fill (slippage)
    - Fill delay / latency effects
    - Partial fills, missed trades
    - Broker/data mismatch events

Usage:
    python3 execution/execution_quality_monitor.py           # Full report
    python3 execution/execution_quality_monitor.py --json    # JSON output
    python3 execution/execution_quality_monitor.py --save    # Save report + log
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Paths ────────────────────────────────────────────────────────────────────

FORWARD_DIR = ROOT / "research" / "phase17_paper_trading"
DAILY_STATES_PATH = FORWARD_DIR / "daily_states.json"
DAILY_LOGS_DIR = FORWARD_DIR / "daily_logs"
EXEC_LOG_PATH = ROOT / "execution" / "data" / "execution_quality_log.json"
REPORTS_DIR = ROOT / "research" / "reports"

# ── Modeled Slippage (from paper trading engine) ─────────────────────────────

ASSET_SLIPPAGE = {
    "MES": {"tick_size": 0.25, "point_value": 5.0, "slippage_ticks": 1},
    "MNQ": {"tick_size": 0.25, "point_value": 2.0, "slippage_ticks": 1},
    "MGC": {"tick_size": 0.10, "point_value": 10.0, "slippage_ticks": 1},
    "MCL": {"tick_size": 0.01, "point_value": 1000.0, "slippage_ticks": 1},
    "M2K": {"tick_size": 0.10, "point_value": 5.0, "slippage_ticks": 1},
}

# Strategy -> asset mapping
STRATEGY_ASSETS = {
    "VWAP-MNQ-Long": "MNQ",
    "XB-PB-EMA-MES-Short": "MES",
    "ORB-MGC-Long": "MGC",
    "BB-EQ-MGC-Long": "MGC",
    "PB-MGC-Short": "MGC",
    "Donchian-MNQ-Long-GRINDING": "MNQ",
}


# ── Data Loading ─────────────────────────────────────────────────────────────

def load_daily_states() -> list:
    """Load daily state snapshots."""
    if not DAILY_STATES_PATH.exists():
        return []
    with open(DAILY_STATES_PATH) as f:
        return json.load(f)


def load_daily_logs() -> list:
    """Load all daily log files for signal-level analysis."""
    logs = []
    if not DAILY_LOGS_DIR.exists():
        return logs

    for log_file in sorted(DAILY_LOGS_DIR.glob("*.json")):
        try:
            with open(log_file) as f:
                data = json.load(f)
            data["_file_date"] = log_file.stem
            logs.append(data)
        except (json.JSONDecodeError, KeyError):
            continue

    return logs


# ── Signal Retention Analysis ────────────────────────────────────────────────

def analyze_signal_retention(daily_states: list) -> dict:
    """Analyze signal generation vs execution rates."""
    if not daily_states:
        return {"status": "NO_DATA"}

    total_generated = 0
    total_taken = 0
    total_blocked = 0
    block_reasons = defaultdict(int)
    strategy_blocks = defaultdict(lambda: defaultdict(int))
    daily_retention = []

    for state in daily_states:
        gen = state.get("signals_generated", 0)
        taken = state.get("signals_taken", 0)
        blocked = state.get("signals_blocked", 0)

        total_generated += gen
        total_taken += taken
        total_blocked += blocked

        if gen > 0:
            daily_retention.append(taken / gen)

        # Track blocking reasons per strategy
        for strat, reason in state.get("blocked_strategies", {}).items():
            strategy_blocks[strat][reason] += 1
            block_reasons[reason] += 1

    retention_rate = total_taken / total_generated if total_generated > 0 else 0
    expected_retention = 0.70  # Phase 17 baseline: 70%

    return {
        "total_signals_generated": total_generated,
        "total_signals_taken": total_taken,
        "total_signals_blocked": total_blocked,
        "retention_rate": round(retention_rate, 3),
        "expected_retention": expected_retention,
        "retention_delta": round(retention_rate - expected_retention, 3),
        "avg_daily_retention": round(np.mean(daily_retention), 3) if daily_retention else 0,
        "block_reasons": dict(block_reasons),
        "strategy_blocks": {k: dict(v) for k, v in strategy_blocks.items()},
        "severity": _classify_retention(retention_rate, expected_retention),
    }


def _classify_retention(actual: float, expected: float) -> str:
    """Classify retention quality."""
    delta = actual - expected
    if delta < -0.15:
        return "ALARM"  # 15pp below baseline
    elif delta < -0.08:
        return "DEGRADED"
    elif delta > 0.10:
        return "OVER_FILTERING"  # Surprisingly high — check if controller is too loose
    return "NORMAL"


# ── Slippage Impact Analysis ─────────────────────────────────────────────────

def analyze_slippage_impact(daily_states: list) -> dict:
    """Estimate slippage impact on portfolio performance.

    In paper trading, slippage is modeled (1 tick per side).
    This calculates the theoretical cost and its share of edge.
    """
    strategy_trades = defaultdict(int)
    strategy_pnl = defaultdict(float)

    for state in daily_states:
        for trade in state.get("trades_completed", []):
            strat = trade.get("strategy", "unknown")
            strategy_trades[strat] += 1
            strategy_pnl[strat] += trade.get("pnl", 0)

    slippage_analysis = {}
    total_slippage_cost = 0

    for strat, n_trades in strategy_trades.items():
        asset = STRATEGY_ASSETS.get(strat, "MNQ")
        asset_config = ASSET_SLIPPAGE.get(asset, ASSET_SLIPPAGE["MNQ"])

        # Cost per round-trip: 2 sides × slippage_ticks × tick_size × point_value
        cost_per_trade = (
            2 * asset_config["slippage_ticks"]
            * asset_config["tick_size"]
            * asset_config["point_value"]
        )
        total_cost = cost_per_trade * n_trades
        total_slippage_cost += total_cost

        gross_pnl = strategy_pnl.get(strat, 0)
        # Slippage as % of gross edge (PnL + slippage = theoretical PnL)
        theoretical_pnl = gross_pnl + total_cost
        slippage_pct = total_cost / theoretical_pnl if theoretical_pnl > 0 else 0

        slippage_analysis[strat] = {
            "trades": n_trades,
            "asset": asset,
            "cost_per_trade": round(cost_per_trade, 2),
            "total_slippage_cost": round(total_cost, 2),
            "net_pnl": round(gross_pnl, 2),
            "slippage_pct_of_edge": round(slippage_pct, 3),
            "severity": "ALARM" if slippage_pct > 0.30 else "WARN" if slippage_pct > 0.20 else "NORMAL",
        }

    return {
        "total_slippage_cost": round(total_slippage_cost, 2),
        "strategies": slippage_analysis,
    }


# ── Controller Blocking Analysis ─────────────────────────────────────────────

def analyze_blocking_patterns(daily_states: list) -> dict:
    """Analyze how the strategy controller affects trade execution."""
    regime_blocks = defaultdict(int)
    regime_days = defaultdict(int)
    strategy_regime_blocks = defaultdict(lambda: defaultdict(int))

    for state in daily_states:
        regime = state.get("regime", {})
        vol = regime.get("vol_regime", "NORMAL")
        regime_days[vol] += 1

        for strat, reason in state.get("blocked_strategies", {}).items():
            if "regime" in reason.lower():
                regime_blocks[vol] += 1
                strategy_regime_blocks[strat][vol] += 1

    return {
        "regime_days": dict(regime_days),
        "regime_blocks": dict(regime_blocks),
        "strategy_regime_blocks": {k: dict(v) for k, v in strategy_regime_blocks.items()},
    }


# ── Opportunity Cost ─────────────────────────────────────────────────────────

def analyze_opportunity_cost(daily_states: list, daily_logs: list) -> dict:
    """Estimate PnL impact of blocked signals.

    Compares signals that were generated but blocked vs those that were taken,
    to estimate whether the controller is correctly filtering.
    """
    blocked_count = 0
    taken_count = 0
    taken_pnl = 0
    blocked_strats = defaultdict(int)

    for state in daily_states:
        taken_count += state.get("signals_taken", 0)
        blocked = state.get("signals_blocked", 0)
        blocked_count += blocked

        # Track which strategies were blocked
        for strat, reason in state.get("blocked_strategies", {}).items():
            blocked_strats[strat] += 1

        # Sum PnL from executed trades
        for trade in state.get("trades_completed", []):
            taken_pnl += trade.get("pnl", 0)

    avg_pnl_per_taken = taken_pnl / taken_count if taken_count > 0 else 0

    # Estimated opportunity cost (blocked signals × avg PnL if executed)
    # This is a rough upper bound — blocked signals may have been worse
    estimated_opportunity = blocked_count * avg_pnl_per_taken

    return {
        "total_blocked_signals": blocked_count,
        "total_taken_signals": taken_count,
        "taken_total_pnl": round(taken_pnl, 2),
        "avg_pnl_per_taken": round(avg_pnl_per_taken, 2),
        "estimated_opportunity_cost": round(estimated_opportunity, 2),
        "most_blocked_strategies": dict(sorted(blocked_strats.items(), key=lambda x: -x[1])[:5]),
        "note": "Opportunity cost is an upper bound — blocked signals may have underperformed",
    }


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_execution_quality_monitor() -> dict:
    """Run full execution quality analysis."""
    daily_states = load_daily_states()
    daily_logs = load_daily_logs()
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    retention = analyze_signal_retention(daily_states)
    slippage = analyze_slippage_impact(daily_states)
    blocking = analyze_blocking_patterns(daily_states)
    opportunity = analyze_opportunity_cost(daily_states, daily_logs)

    # Overall severity
    severities = [retention.get("severity", "NORMAL")]
    for s in slippage.get("strategies", {}).values():
        severities.append(s.get("severity", "NORMAL"))

    if "ALARM" in severities:
        overall = "ALARM"
    elif "DEGRADED" in severities or "WARN" in severities:
        overall = "DEGRADED"
    else:
        overall = "NORMAL"

    return {
        "report_date": report_date,
        "execution_phase": "PAPER_TRADING",
        "overall_status": overall,
        "forward_days": len(daily_states),
        "signal_retention": retention,
        "slippage_impact": slippage,
        "controller_blocking": blocking,
        "opportunity_cost": opportunity,
        # Extension points for live execution (Phase 7)
        "live_execution": {
            "status": "NOT_AVAILABLE",
            "note": "Broker fill data not yet available — paper trading only",
            "future_metrics": [
                "expected_entry_vs_actual_fill",
                "expected_exit_vs_actual_exit",
                "fill_delay_latency",
                "partial_fills",
                "broker_data_mismatch",
            ],
        },
    }


# ── Terminal Report ──────────────────────────────────────────────────────────

def print_execution_report(results: dict):
    """Print formatted execution quality report."""
    W = 75
    SEP = "=" * W
    THIN = "-" * 55

    print()
    print(SEP)
    print("  FQL EXECUTION QUALITY MONITOR")
    print(f"  {results['report_date']}  |  Phase: {results['execution_phase']}")
    print(f"  Overall: {results['overall_status']}  |  {results['forward_days']} days analyzed")
    print(SEP)

    # ── Signal Retention ──
    ret = results["signal_retention"]
    if ret.get("status") != "NO_DATA":
        print(f"\n  SIGNAL RETENTION")
        print(f"  {THIN}")
        print(f"  Signals generated: {ret['total_signals_generated']}")
        print(f"  Signals taken:     {ret['total_signals_taken']}")
        print(f"  Signals blocked:   {ret['total_signals_blocked']}")
        print(f"  Retention rate:    {ret['retention_rate']:.1%} (baseline: {ret['expected_retention']:.0%})")
        print(f"  Delta:             {ret['retention_delta']:+.1%}")
        print(f"  Status:            {ret['severity']}")

        if ret.get("block_reasons"):
            print(f"\n  Block reasons:")
            for reason, count in sorted(ret["block_reasons"].items(), key=lambda x: -x[1]):
                print(f"    {reason}: {count}")

        if ret.get("strategy_blocks"):
            print(f"\n  Per-strategy blocking:")
            for strat, reasons in sorted(ret["strategy_blocks"].items()):
                total = sum(reasons.values())
                reason_str = ", ".join(f"{r}:{c}" for r, c in reasons.items())
                print(f"    {strat}: {total} blocks ({reason_str})")

    # ── Slippage Impact ──
    slip = results["slippage_impact"]
    print(f"\n  SLIPPAGE IMPACT (modeled)")
    print(f"  {THIN}")
    print(f"  Total modeled slippage cost: ${slip['total_slippage_cost']:.2f}")
    print(f"\n  {'Strategy':<28s} {'Trades':>6s} {'$/trade':>8s} {'Total':>10s} {'% Edge':>8s} {'Status':>8s}")
    print(f"  {'-' * 72}")
    for strat, data in sorted(slip["strategies"].items(), key=lambda x: -x[1]["total_slippage_cost"]):
        print(f"  {strat:<28s} {data['trades']:>6d} ${data['cost_per_trade']:>6.2f} "
              f"${data['total_slippage_cost']:>8.2f} {data['slippage_pct_of_edge']:>7.1%} {data['severity']:>8s}")

    # ── Controller Blocking ──
    block = results["controller_blocking"]
    print(f"\n  CONTROLLER BLOCKING BY REGIME")
    print(f"  {THIN}")
    for regime, days in sorted(block.get("regime_days", {}).items()):
        blocks = block.get("regime_blocks", {}).get(regime, 0)
        rate = blocks / days if days > 0 else 0
        print(f"  {regime:<15s} {days:>4d} days  {blocks:>4d} regime blocks  ({rate:.0%} block rate)")

    # ── Opportunity Cost ──
    opp = results["opportunity_cost"]
    print(f"\n  OPPORTUNITY COST")
    print(f"  {THIN}")
    print(f"  Blocked signals:        {opp['total_blocked_signals']}")
    print(f"  Avg PnL per taken:      ${opp['avg_pnl_per_taken']:.2f}")
    print(f"  Est. opportunity cost:  ${opp['estimated_opportunity_cost']:.2f}")
    print(f"  Note: {opp['note']}")

    if opp.get("most_blocked_strategies"):
        print(f"\n  Most blocked strategies:")
        for strat, count in opp["most_blocked_strategies"].items():
            print(f"    {strat}: {count} blocks")

    # ── Live Execution Status ──
    live = results.get("live_execution", {})
    if live.get("status") == "NOT_AVAILABLE":
        print(f"\n  LIVE EXECUTION METRICS")
        print(f"  {THIN}")
        print(f"  Status: {live['note']}")
        print(f"  Pending metrics: {', '.join(live['future_metrics'][:3])}...")

    print()
    print(SEP)


# ── Persistence ──────────────────────────────────────────────────────────────

def save_execution_log(results: dict):
    """Append execution quality results to persistent log."""
    log = []
    if EXEC_LOG_PATH.exists():
        try:
            with open(EXEC_LOG_PATH) as f:
                log = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            log = []

    log.append({
        "date": results["report_date"],
        "overall_status": results["overall_status"],
        "forward_days": results["forward_days"],
        "retention_rate": results["signal_retention"].get("retention_rate"),
        "retention_severity": results["signal_retention"].get("severity"),
        "total_slippage_cost": results["slippage_impact"].get("total_slippage_cost"),
    })

    if len(log) > 365:
        log = log[-365:]

    EXEC_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXEC_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Execution Quality Monitor")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", action="store_true", help="Save report + log")
    args = parser.parse_args()

    results = run_execution_quality_monitor()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_execution_report(results)

    if args.save:
        save_execution_log(results)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = REPORTS_DIR / f"execution_quality_{timestamp}.json"
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Report saved: {path}")
        print(f"Log updated: {EXEC_LOG_PATH}")


if __name__ == "__main__":
    main()
