#!/usr/bin/env python3
"""
Forward Health Report — READ-ONLY daily health summary.

Reads from logs/ and state/ to print a terminal report.
Does NOT modify any files.

Usage:
    python3 scripts/forward_health_report.py
    python3 scripts/forward_health_report.py --date 2026-03-11
"""

import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LOGS = ROOT / "logs"
STATE = ROOT / "state"

TRADE_LOG = LOGS / "trade_log.csv"
DAILY_REPORT = LOGS / "daily_report.csv"
SIGNAL_LOG = LOGS / "signal_log.csv"
KILL_SWITCH_EVENTS = LOGS / "kill_switch_events.csv"
ACCOUNT_STATE = STATE / "account_state.json"

WIDTH = 70
DIVIDER = "=" * WIDTH
SECTION_RULE = "\u2500" * 35


# ── helpers ──────────────────────────────────────────────────────────

def read_csv(path: Path) -> list[dict]:
    """Return list of row-dicts, or [] if file missing/empty."""
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    """Return parsed JSON dict, or {} if file missing."""
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def fmt_dollar(val) -> str:
    """Format a number as $X,XXX.XX with sign handling."""
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "N/A"
    if v < 0:
        return f"-${abs(v):,.2f}"
    return f"${v:,.2f}"


def resolve_target_date(rows: list[dict], requested: str | None) -> str | None:
    """Return the target date string — either the requested one or the most recent in rows."""
    if requested:
        return requested
    if not rows:
        return None
    dates = sorted({r.get("date", "") for r in rows if r.get("date")})
    return dates[-1] if dates else None


# ── section builders ─────────────────────────────────────────────────

def build_account_section(daily_row: dict, account: dict) -> list[str]:
    equity = daily_row.get("equity") or account.get("equity")
    cum_pnl = daily_row.get("cumulative_pnl") or account.get("cumulative_pnl")
    trailing_dd = daily_row.get("trailing_dd") or account.get("trailing_dd", 0)
    hwm = account.get("equity_hwm")
    if hwm is None and equity is not None and trailing_dd is not None:
        try:
            hwm = float(equity) + float(trailing_dd)
        except (TypeError, ValueError):
            hwm = None

    lines = [
        "  ACCOUNT",
        f"  {SECTION_RULE}",
        f"  Equity:              {fmt_dollar(equity)}",
        f"  Cumulative PnL:      {fmt_dollar(cum_pnl)}",
        f"  Trailing DD:         {fmt_dollar(trailing_dd)}",
        f"  Equity HWM:          {fmt_dollar(hwm)}",
    ]
    return lines


def build_activity_section(daily_row: dict, signal_rows: list[dict]) -> list[str]:
    trades_raw = daily_row.get("trades_raw", 0)
    trades_ctrl = daily_row.get("trades_controlled", 0)
    active = daily_row.get("active_strategies", "?")

    sig_total = sum(int(r.get("signals_total", 0)) for r in signal_rows)
    sig_kept = sum(int(r.get("signals_kept", 0)) for r in signal_rows)
    regime_blk = sum(int(r.get("regime_blocked", 0)) for r in signal_rows)
    timing_blk = sum(int(r.get("timing_blocked", 0)) for r in signal_rows)

    total_strats = 6  # current portfolio size

    lines = [
        "  TODAY'S ACTIVITY",
        f"  {SECTION_RULE}",
        f"  Trades today:        {trades_ctrl or trades_raw}",
        f"  Strategies active:   {active}/{total_strats}",
        f"  Signals generated:   {sig_total}",
        f"  Signals kept:        {sig_kept}",
        f"  Regime blocked:      {regime_blk}",
        f"  Timing blocked:      {timing_blk}",
    ]
    return lines


def build_strategies_section(trade_rows: list[dict]) -> list[str]:
    lines = [
        "  STRATEGIES FIRING",
        f"  {SECTION_RULE}",
    ]
    if not trade_rows:
        lines.append("  (no trades today)")
        return lines

    strat_data: dict[str, dict] = {}
    for r in trade_rows:
        name = r.get("strategy", "unknown")
        try:
            pnl = float(r.get("pnl", 0))
        except (TypeError, ValueError):
            pnl = 0.0
        if name not in strat_data:
            strat_data[name] = {"count": 0, "pnl": 0.0}
        strat_data[name]["count"] += 1
        strat_data[name]["pnl"] += pnl

    for name, d in sorted(strat_data.items()):
        ct = d["count"]
        trade_word = "trade" if ct == 1 else "trades"
        lines.append(f"  {name + ':':23s}{ct} {trade_word}, {fmt_dollar(d['pnl'])}")

    return lines


def build_controller_section(daily_row: dict, signal_rows: list[dict]) -> list[str]:
    regime = daily_row.get("regime", "N/A")
    rv = daily_row.get("rv_regime", "N/A")
    persistence = daily_row.get("persistence", "N/A")

    sig_total = sum(int(r.get("signals_total", 0)) for r in signal_rows)
    sig_kept = sum(int(r.get("signals_kept", 0)) for r in signal_rows)
    if sig_total > 0:
        pct = int(round(sig_kept / sig_total * 100))
        retention = f"{pct}% ({sig_kept}/{sig_total})"
    else:
        retention = "N/A"

    lines = [
        "  CONTROLLER STATUS",
        f"  {SECTION_RULE}",
        f"  Regime:              {regime}",
        f"  RV regime:           {rv}",
        f"  Persistence:         {persistence}",
        f"  Trade retention:     {retention}",
    ]
    return lines


def build_kill_switch_section(daily_row: dict, ks_rows: list[dict], trade_rows: list[dict]) -> list[str]:
    ks_triggered = str(daily_row.get("kill_switch", "")).lower() in ("true", "1", "yes")

    # Consecutive losses: count trailing losses in today's trades
    consec = 0
    if trade_rows:
        for r in reversed(trade_rows):
            try:
                if float(r.get("pnl", 0)) < 0:
                    consec += 1
                else:
                    break
            except (TypeError, ValueError):
                break

    lines = [
        "  KILL SWITCH",
        f"  {SECTION_RULE}",
        f"  Status:              {'TRIGGERED' if ks_triggered else 'OK'}",
        f"  Consecutive losses:  {consec}",
    ]

    if ks_rows:
        latest = ks_rows[-1]
        lines.append(f"  Last event:          {latest.get('date', '?')} — {latest.get('reason', '?')}")

    return lines


def build_data_freshness_section(daily_row: dict, account: dict) -> list[str]:
    run_count = daily_row.get("run_count", account.get("run_count", "N/A"))

    # Try to get bar timestamps from account state
    bar_ts = account.get("last_bar_times", {})

    lines = [
        "  DATA FRESHNESS",
        f"  {SECTION_RULE}",
        "  Last processed bars:",
    ]
    if bar_ts:
        for sym in sorted(bar_ts):
            lines.append(f"    {sym}: {bar_ts[sym]}")
    else:
        for sym in ("MES", "MNQ", "MGC"):
            lines.append(f"    {sym}: N/A")

    lines.append(f"  Run count:           {run_count}")
    last_run = account.get("last_run", daily_row.get("date", "N/A"))
    lines.append(f"  Last run:            {last_run}")

    return lines


# ── health status ────────────────────────────────────────────────────

def compute_status(daily_row: dict, ks_rows: list[dict],
                   trade_rows: list[dict], account: dict,
                   target_date: str) -> str:
    """Return HEALTHY, WARNING, or CRITICAL."""
    ks_triggered = str(daily_row.get("kill_switch", "")).lower() in ("true", "1", "yes")

    try:
        trailing_dd = float(daily_row.get("trailing_dd", 0))
    except (TypeError, ValueError):
        trailing_dd = 0.0

    # Data staleness: check if target date is > 2 days old
    stale = False
    try:
        td = datetime.strptime(target_date, "%Y-%m-%d").date()
        if (datetime.now().date() - td).days > 2:
            stale = True
    except (TypeError, ValueError):
        pass

    # CRITICAL checks
    if ks_triggered:
        return "CRITICAL"
    if trailing_dd > 2000:
        return "CRITICAL"
    if stale:
        return "CRITICAL"

    # Consecutive losses
    consec = 0
    if trade_rows:
        for r in reversed(trade_rows):
            try:
                if float(r.get("pnl", 0)) < 0:
                    consec += 1
                else:
                    break
            except (TypeError, ValueError):
                break

    trades_today = len(trade_rows)

    # WARNING checks
    if trades_today == 0:
        return "WARNING"
    if trailing_dd > 1000:
        return "WARNING"
    if consec >= 4:
        return "WARNING"

    return "HEALTHY"


# ── main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Forward system health report (read-only)")
    parser.add_argument("--date", type=str, default=None,
                        help="Target date YYYY-MM-DD (default: most recent in logs)")
    args = parser.parse_args()

    # Load all data
    daily_rows = read_csv(DAILY_REPORT)
    trade_rows_all = read_csv(TRADE_LOG)
    signal_rows_all = read_csv(SIGNAL_LOG)
    ks_rows_all = read_csv(KILL_SWITCH_EVENTS)
    account = read_json(ACCOUNT_STATE)

    # Resolve date
    target_date = resolve_target_date(daily_rows, args.date)
    if target_date is None:
        print(DIVIDER)
        print("  SYSTEM HEALTH REPORT")
        print("  No data found — logs are empty or missing.")
        print(DIVIDER)
        return

    # Filter to target date
    daily_row = {}
    for r in daily_rows:
        if r.get("date") == target_date:
            daily_row = r
            break

    trade_rows = [r for r in trade_rows_all if r.get("date") == target_date]
    signal_rows = [r for r in signal_rows_all if r.get("date") == target_date]
    ks_rows = [r for r in ks_rows_all if r.get("date") == target_date]

    status = compute_status(daily_row, ks_rows, trade_rows, account, target_date)

    # Print report
    print()
    print(DIVIDER)
    print("  SYSTEM HEALTH REPORT")
    print(f"  {target_date}")
    print(DIVIDER)
    print()
    print(f"  STATUS: {status}")
    print()

    for section in [
        build_account_section(daily_row, account),
        build_activity_section(daily_row, signal_rows),
        build_strategies_section(trade_rows),
        build_controller_section(daily_row, signal_rows),
        build_kill_switch_section(daily_row, ks_rows, trade_rows),
        build_data_freshness_section(daily_row, account),
    ]:
        for line in section:
            print(line)
        print()

    print(DIVIDER)
    print()


if __name__ == "__main__":
    main()
