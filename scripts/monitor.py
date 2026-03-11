#!/usr/bin/env python3
"""Forward Testing Monitor — Lightweight daily health check.

Reads logs and state files to show a quick summary of system health.
Run after each forward paper trading session.

Usage:
    python3 scripts/monitor.py              # today's summary
    python3 scripts/monitor.py --history 7  # last 7 days
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"


def load_account_state() -> dict:
    path = STATE_DIR / "account_state.json"
    if path.exists():
        return json.load(open(path))
    return {}


def load_csv(name: str) -> pd.DataFrame:
    path = LOGS_DIR / name
    if path.exists() and path.stat().st_size > 0:
        return pd.read_csv(path)
    return pd.DataFrame()


def print_header():
    print()
    print("=" * 70)
    print("  FORWARD PAPER TRADING MONITOR")
    print("=" * 70)


def print_account_status(state: dict):
    print(f"\n  ACCOUNT STATUS")
    print(f"  {'-'*40}")
    equity = state.get("equity", 0)
    cum_pnl = state.get("cumulative_pnl", 0)
    hwm = state.get("equity_hwm", 0)
    dd = hwm - equity
    consec = state.get("consecutive_losses", 0)
    runs = state.get("run_count", 0)
    last_run = state.get("last_run", "never")

    print(f"  Equity:            ${equity:,.2f}")
    print(f"  Cumulative PnL:    ${cum_pnl:+,.2f}")
    print(f"  Equity HWM:        ${hwm:,.2f}")
    print(f"  Trailing DD:       ${dd:,.2f}")
    print(f"  Consecutive losses: {consec}")
    print(f"  Total trades:      {state.get('total_trades', 0)}")
    print(f"  Run count:         {runs}")
    print(f"  Last run:          {last_run}")

    # Last processed bars
    bars = state.get("last_processed_bar", {})
    if bars:
        print(f"\n  Last processed bars:")
        for asset, ts in bars.items():
            print(f"    {asset}: {ts}")


def print_daily_report(daily: pd.DataFrame, n_days: int = 5):
    if daily.empty:
        print(f"\n  No daily reports yet.")
        return

    print(f"\n  DAILY REPORT (last {min(n_days, len(daily))} days)")
    print(f"  {'-'*68}")
    print(f"  {'Date':<12} {'Equity':>10} {'Daily PnL':>10} {'Trades':>7} "
          f"{'Active':>7} {'Regime':<22} {'KS':<6}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*7} {'-'*7} {'-'*22} {'-'*6}")

    for _, row in daily.tail(n_days).iterrows():
        ks = "OK" if row.get("kill_switch", "OK") == "OK" else "ALERT"
        regime = str(row.get("regime", ""))[:22]
        print(f"  {row['date']:<12} ${row['equity']:>9,.2f} ${row['daily_pnl']:>+9,.2f} "
              f"{int(row.get('trades_controlled', 0)):>7} "
              f"{int(row.get('active_strategies', 0)):>7} "
              f"{regime:<22} {ks:<6}")

    # Summary stats
    total_days = len(daily)
    total_pnl = daily["daily_pnl"].sum()
    win_days = (daily["daily_pnl"] > 0).sum()
    loss_days = (daily["daily_pnl"] < 0).sum()
    flat_days = (daily["daily_pnl"] == 0).sum()

    print(f"\n  Summary: {total_days} days | "
          f"Win={win_days} Loss={loss_days} Flat={flat_days} | "
          f"Total PnL: ${total_pnl:+,.2f}")


def print_recent_trades(trades: pd.DataFrame, n: int = 10):
    if trades.empty:
        print(f"\n  No trades logged yet.")
        return

    print(f"\n  RECENT TRADES (last {min(n, len(trades))})")
    print(f"  {'-'*68}")
    print(f"  {'Date':<12} {'Strategy':<28} {'Side':<6} {'PnL':>10}")
    print(f"  {'-'*12} {'-'*28} {'-'*6} {'-'*10}")

    for _, row in trades.tail(n).iterrows():
        print(f"  {row['date']:<12} {row['strategy']:<28} "
              f"{row.get('side', ''):>6} ${row['pnl']:>+9,.2f}")

    # Per-strategy summary
    if len(trades) >= 3:
        print(f"\n  PER-STRATEGY SUMMARY")
        print(f"  {'-'*50}")
        strat_summary = trades.groupby("strategy").agg(
            trades=("pnl", "count"),
            total_pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            wins=("pnl", lambda x: (x > 0).sum()),
        )
        for strat, row in strat_summary.iterrows():
            wr = row["wins"] / row["trades"] * 100 if row["trades"] > 0 else 0
            print(f"  {strat:<28} {int(row['trades']):>3} trades "
                  f"${row['total_pnl']:>+8,.2f}  WR={wr:.0f}%")


def print_signal_log(signals: pd.DataFrame, n: int = 5):
    if signals.empty:
        return

    print(f"\n  RECENT SIGNALS (last {min(n, len(signals))} days)")
    print(f"  {'-'*68}")

    # Get last N unique dates
    dates = signals["date"].unique()[-n:]
    recent = signals[signals["date"].isin(dates)]

    for date in dates:
        day = recent[recent["date"] == date]
        total = day["signals_total"].sum()
        kept = day["signals_kept"].sum()
        blocked = day["regime_blocked"].sum() + day["timing_blocked"].sum()
        conv = day["conviction_override"].sum()
        print(f"  {date}: {total} signals → {kept} kept, "
              f"{blocked} blocked, {conv} conviction overrides")


def print_kill_switch(ks_events: pd.DataFrame):
    if ks_events.empty:
        print(f"\n  KILL SWITCH: No events logged. System healthy.")
        return

    print(f"\n  KILL SWITCH EVENTS ({len(ks_events)} total)")
    print(f"  {'-'*50}")
    for _, row in ks_events.tail(5).iterrows():
        print(f"  {row['date']}: {row['reason']}")


def main():
    parser = argparse.ArgumentParser(description="Forward Testing Monitor")
    parser.add_argument("--history", type=int, default=7,
                        help="Number of days to show (default: 7)")
    args = parser.parse_args()

    print_header()

    # Account status
    state = load_account_state()
    if not state:
        print("\n  No account state found. Run run_forward_paper.py first.")
        return
    print_account_status(state)

    # Daily report
    daily = load_csv("daily_report.csv")
    print_daily_report(daily, args.history)

    # Recent trades
    trades = load_csv("trade_log.csv")
    print_recent_trades(trades)

    # Signal log
    signals = load_csv("signal_log.csv")
    print_signal_log(signals)

    # Kill switch
    ks = load_csv("kill_switch_events.csv")
    print_kill_switch(ks)

    print(f"\n{'='*70}")
    print(f"  END MONITOR")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
