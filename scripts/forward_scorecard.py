"""Forward Test Scorecard — daily/weekly health assessment.

READ-ONLY tool. Does NOT modify any frozen execution files.

Compares forward performance to backtest expectations and flags drift.

Reads from:
    logs/trade_log.csv
    logs/daily_report.csv
    logs/signal_log.csv
    logs/kill_switch_events.csv  (optional)
    state/account_state.json

Usage:
    python3 scripts/forward_scorecard.py
    python3 scripts/forward_scorecard.py --period weekly
    python3 scripts/forward_scorecard.py --period daily
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Backtest reference values (Phase 16 controller simulation)
# ---------------------------------------------------------------------------
BACKTEST_REF = {
    "daily_trade_freq": 1.1,        # trades per trading day
    "win_rate": 0.52,               # 52%
    "trade_retention": 0.70,        # 70% kept by controller
    "monthly_positive_rate": 0.84,  # 84%
    "mean_daily_pnl": 52.40,       # dollars
    "sharpe_annualized": 4.04,
}

# All strategies in the portfolio
STRATEGIES = [
    "PB-MGC-Short",
    "ORB-MGC-Long",
    "VWAP-MNQ-Long",
    "XB-PB-EMA-MES-Short",
    "BB-EQ-MGC-Long",
    "Donchian-MNQ-Long",
]

# Strategies on probation (0-trade silence is OK for these)
PROBATION_STRATEGIES = {"Donchian-MNQ-Long"}

TOTAL_STRATEGIES = len(STRATEGIES)

# ---------------------------------------------------------------------------
# Drift thresholds
# ---------------------------------------------------------------------------
# Trade frequency: ratio to backtest
FREQ_OK_LOW, FREQ_OK_HIGH = 0.5, 2.0
FREQ_FLAG_LOW, FREQ_FLAG_HIGH = 0.25, 3.0

# Win rate: percentage-point deviation
WR_OK_PP = 15
WR_WATCH_PP = 25

# Trade retention: percentage-point deviation
RET_OK_PP = 15

# Strategy silence: days without trades before WATCH
SILENCE_WATCH_DAYS = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(name: str, parse_dates=None) -> pd.DataFrame | None:
    """Load a CSV from logs/, return None if missing or empty."""
    path = ROOT / "logs" / name
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=parse_dates)
        return df if len(df) > 0 else None
    except Exception:
        return None


def load_account_state() -> dict | None:
    """Load state/account_state.json."""
    path = ROOT / "state" / "account_state.json"
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def fmt_pnl(val: float) -> str:
    """Format PnL with sign and dollar."""
    if val >= 0:
        return f"+${val:,.2f}"
    return f"-${abs(val):,.2f}"


def fmt_pct(val: float) -> str:
    """Format as percentage."""
    return f"{val:.1f}%"


def drift_status_freq(forward_freq: float) -> str:
    """Classify trade frequency drift."""
    bt = BACKTEST_REF["daily_trade_freq"]
    ratio = forward_freq / bt if bt > 0 else 0
    if FREQ_OK_LOW <= ratio <= FREQ_OK_HIGH:
        return "OK"
    if ratio < FREQ_FLAG_LOW or ratio > FREQ_FLAG_HIGH:
        return "FLAG"
    return "WATCH"


def drift_status_wr(forward_wr: float) -> str:
    """Classify win rate drift (inputs as 0-1 decimals)."""
    diff_pp = abs(forward_wr - BACKTEST_REF["win_rate"]) * 100
    if diff_pp <= WR_OK_PP:
        return "OK"
    if diff_pp <= WR_WATCH_PP:
        return "WATCH"
    return "FLAG"


def drift_status_retention(forward_ret: float) -> str:
    """Classify retention drift (inputs as 0-1 decimals)."""
    diff_pp = abs(forward_ret - BACKTEST_REF["trade_retention"]) * 100
    if diff_pp <= RET_OK_PP:
        return "OK"
    return "WATCH"


def drift_status_pnl(forward_mean_pnl: float) -> str:
    """Classify mean daily PnL drift."""
    if forward_mean_pnl < 0:
        return "WATCH"
    return "OK"


def compute_verdict(statuses: list[str]) -> str:
    """Determine overall verdict from list of status strings."""
    flags = sum(1 for s in statuses if s == "FLAG")
    watches = sum(1 for s in statuses if s == "WATCH")
    if flags > 0:
        return "ALARM"
    if watches >= 3:
        return "DRIFTING"
    if watches >= 1:
        return "WATCH"
    return "ON TRACK"


def filter_period(df: pd.DataFrame, date_col: str, period: str) -> pd.DataFrame:
    """Filter dataframe to requested period."""
    if df is None or len(df) == 0:
        return df
    df = df.copy()
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
    else:
        return df

    today = pd.Timestamp.now().normalize()

    if period == "daily":
        return df[df[date_col] >= today]
    elif period == "weekly":
        # Current ISO week
        start_of_week = today - timedelta(days=today.weekday())
        return df[df[date_col] >= start_of_week]
    # "all" — no filtering
    return df


# ---------------------------------------------------------------------------
# Scorecard sections
# ---------------------------------------------------------------------------

def section_summary(trades: pd.DataFrame | None,
                    daily: pd.DataFrame | None,
                    signals: pd.DataFrame | None,
                    ks_events: pd.DataFrame | None,
                    n_days: int) -> list[str]:
    """Build the SUMMARY section. Returns list of status strings for verdict."""
    statuses = []
    print()
    print("  SUMMARY")
    print("  " + "\u2500" * 34)

    # Days run
    print(f"  Days run:             {n_days}")

    # Total trades
    n_trades = len(trades) if trades is not None else 0
    print(f"  Total trades:         {n_trades}")

    # Win rate
    if trades is not None and n_trades > 0:
        wins = (trades["pnl"] > 0).sum()
        wr = wins / n_trades
        wr_status = drift_status_wr(wr)
        statuses.append(wr_status)
        bt_wr = BACKTEST_REF["win_rate"] * 100
        print(f"  Win rate:             {fmt_pct(wr * 100):<13}(backtest: {bt_wr:.0f}%)     {wr_status}")
    else:
        print(f"  Win rate:             \u2014")

    # Daily trade frequency
    if n_days > 0 and n_trades > 0:
        freq = n_trades / n_days
        freq_status = drift_status_freq(freq)
        statuses.append(freq_status)
        bt_freq = BACKTEST_REF["daily_trade_freq"]
        print(f"  Daily trade freq:     {freq:.2f:<13}(backtest: {bt_freq})     {freq_status}")
    else:
        print(f"  Daily trade freq:     \u2014")

    # Controller filtered %
    if signals is not None and len(signals) > 0:
        total_raw = signals["signals_total"].sum()
        total_kept = signals["signals_kept"].sum()
        if total_raw > 0:
            retention = total_kept / total_raw
            filtered_pct = (1 - retention) * 100
            ret_status = drift_status_retention(retention)
            statuses.append(ret_status)
            bt_filtered = (1 - BACKTEST_REF["trade_retention"]) * 100
            print(f"  Controller filtered:  {fmt_pct(filtered_pct):<13}(backtest: {bt_filtered:.0f}%)     {ret_status}")
        else:
            print(f"  Controller filtered:  \u2014")
    else:
        print(f"  Controller filtered:  \u2014")

    # Kill switch events
    n_ks = len(ks_events) if ks_events is not None else 0
    ks_status = "FLAG" if n_ks > 0 else "OK"
    statuses.append(ks_status)
    print(f"  Kill switch events:   {n_ks:<28}{ks_status}")

    # Cumulative PnL
    if daily is not None and len(daily) > 0 and "cumulative_pnl" in daily.columns:
        cum_pnl = daily["cumulative_pnl"].iloc[-1]
        print(f"  Cumulative PnL:       {fmt_pnl(cum_pnl)}")
    elif trades is not None and n_trades > 0:
        cum_pnl = trades["pnl"].sum()
        print(f"  Cumulative PnL:       {fmt_pnl(cum_pnl)}")
    else:
        print(f"  Cumulative PnL:       \u2014")

    return statuses


def section_drift(trades: pd.DataFrame | None,
                  daily: pd.DataFrame | None,
                  signals: pd.DataFrame | None,
                  n_days: int) -> list[str]:
    """Build the DRIFT CHECK section. Returns status strings."""
    statuses = []
    print()
    print("  DRIFT CHECK")
    print("  " + "\u2500" * 34)
    print(f"  {'Metric':<22}{'Forward':<11}{'Backtest':<11}{'Drift':<9}{'Status'}")
    print(f"  {'\u2500'*22} {'\u2500'*10} {'\u2500'*10} {'\u2500'*8} {'\u2500'*6}")

    n_trades = len(trades) if trades is not None else 0

    # Trade frequency
    if n_days > 0 and n_trades > 0:
        freq = n_trades / n_days
        bt = BACKTEST_REF["daily_trade_freq"]
        pct_diff = ((freq - bt) / bt) * 100
        status = drift_status_freq(freq)
        statuses.append(status)
        drift_str = f"{pct_diff:+.0f}%"
        print(f"  {'Trade frequency':<22}{freq:.2f}/day{'':<4}{bt:.2f}/day{'':<4}{drift_str:<9}{status}")
    else:
        print(f"  {'Trade frequency':<22}{'\u2014':<11}{BACKTEST_REF['daily_trade_freq']:.2f}/day{'':<4}{'\u2014':<9}\u2014")

    # Win rate
    if trades is not None and n_trades > 0:
        wr = (trades["pnl"] > 0).sum() / n_trades
        bt_wr = BACKTEST_REF["win_rate"]
        diff_pp = (wr - bt_wr) * 100
        status = drift_status_wr(wr)
        statuses.append(status)
        drift_str = f"{diff_pp:+.0f}pp"
        print(f"  {'Win rate':<22}{fmt_pct(wr*100):<11}{fmt_pct(bt_wr*100):<11}{drift_str:<9}{status}")
    else:
        print(f"  {'Win rate':<22}{'\u2014':<11}{fmt_pct(BACKTEST_REF['win_rate']*100):<11}{'\u2014':<9}\u2014")

    # Trade retention
    if signals is not None and len(signals) > 0:
        total_raw = signals["signals_total"].sum()
        total_kept = signals["signals_kept"].sum()
        if total_raw > 0:
            ret = total_kept / total_raw
            bt_ret = BACKTEST_REF["trade_retention"]
            diff_pp = (ret - bt_ret) * 100
            status = drift_status_retention(ret)
            statuses.append(status)
            drift_str = f"{diff_pp:+.0f}pp"
            print(f"  {'Trade retention':<22}{fmt_pct(ret*100):<11}{fmt_pct(bt_ret*100):<11}{drift_str:<9}{status}")
        else:
            print(f"  {'Trade retention':<22}{'\u2014':<11}{fmt_pct(BACKTEST_REF['trade_retention']*100):<11}{'\u2014':<9}\u2014")
    else:
        print(f"  {'Trade retention':<22}{'\u2014':<11}{fmt_pct(BACKTEST_REF['trade_retention']*100):<11}{'\u2014':<9}\u2014")

    # Mean daily PnL
    if daily is not None and len(daily) > 0 and "daily_pnl" in daily.columns:
        mean_pnl = daily["daily_pnl"].mean()
        bt_pnl = BACKTEST_REF["mean_daily_pnl"]
        status = drift_status_pnl(mean_pnl)
        statuses.append(status)
        drift_str = "drift" if mean_pnl < 0 else "OK"
        print(f"  {'Mean daily PnL':<22}{fmt_pnl(mean_pnl):<11}${bt_pnl:.2f}{'':<4}{drift_str:<9}{status}")
    elif trades is not None and n_days > 0:
        mean_pnl = trades["pnl"].sum() / n_days
        bt_pnl = BACKTEST_REF["mean_daily_pnl"]
        status = drift_status_pnl(mean_pnl)
        statuses.append(status)
        drift_str = "drift" if mean_pnl < 0 else "OK"
        print(f"  {'Mean daily PnL':<22}{fmt_pnl(mean_pnl):<11}${bt_pnl:.2f}{'':<4}{drift_str:<9}{status}")
    else:
        print(f"  {'Mean daily PnL':<22}{'\u2014':<11}${BACKTEST_REF['mean_daily_pnl']:.2f}{'':<4}{'\u2014':<9}\u2014")

    # Strategies active
    if daily is not None and len(daily) > 0 and "active_strategies" in daily.columns:
        latest_active = daily["active_strategies"].iloc[-1]
        if isinstance(latest_active, str):
            try:
                latest_active = int(latest_active)
            except ValueError:
                latest_active = latest_active.count(",") + 1 if latest_active else 0
        status = "WATCH" if latest_active < TOTAL_STRATEGIES else "OK"
        statuses.append(status)
        diff = latest_active - TOTAL_STRATEGIES
        drift_str = f"{diff:+d}" if diff != 0 else "0"
        print(f"  {'Strategies active':<22}{latest_active}/{TOTAL_STRATEGIES}{'':<7}{TOTAL_STRATEGIES}/{TOTAL_STRATEGIES}{'':<4}{drift_str:<9}{status}")
    else:
        print(f"  {'Strategies active':<22}{'\u2014':<11}{TOTAL_STRATEGIES}/{TOTAL_STRATEGIES}{'':<4}{'\u2014':<9}\u2014")

    return statuses


def section_strategy_breakdown(trades: pd.DataFrame | None, n_days: int):
    """Build the STRATEGY BREAKDOWN section."""
    print()
    print("  STRATEGY BREAKDOWN")
    print("  " + "\u2500" * 34)
    print(f"  {'Strategy':<26}{'Trades':<8}{'WR':<7}{'PnL':<10}{'Status'}")
    print(f"  {'\u2500'*26}{'\u2500'*8}{'\u2500'*7}{'\u2500'*10}{'\u2500'*6}")

    for strat in STRATEGIES:
        if trades is not None and len(trades) > 0 and "strategy" in trades.columns:
            strat_trades = trades[trades["strategy"] == strat]
            n = len(strat_trades)
        else:
            n = 0

        if n > 0:
            wins = (strat_trades["pnl"] > 0).sum()
            wr = wins / n
            pnl = strat_trades["pnl"].sum()
            # Determine status
            if strat in PROBATION_STRATEGIES:
                status = "OK (probation)"
            else:
                status = "OK"
            print(f"  {strat:<26}{n:<8}{fmt_pct(wr*100):<7}{fmt_pnl(pnl):<10}{status}")
        else:
            # Zero trades
            if strat in PROBATION_STRATEGIES:
                status = "OK (probation)"
            elif n_days >= SILENCE_WATCH_DAYS:
                status = "WATCH"
            else:
                status = "OK"
            print(f"  {strat:<26}{0:<8}{'\u2014':<7}{'$0':<10}{status}")


def section_weekly_view(trades: pd.DataFrame | None,
                        daily: pd.DataFrame | None,
                        ks_events: pd.DataFrame | None):
    """Build the WEEKLY VIEW section (if enough data for at least 1 full week)."""
    if trades is None or len(trades) == 0:
        return

    trades = trades.copy()
    if "date" in trades.columns:
        trades["date"] = pd.to_datetime(trades["date"])
        trades["week"] = trades["date"].dt.isocalendar().week.astype(int)
        trades["year"] = trades["date"].dt.isocalendar().year.astype(int)
        trades["yw"] = trades["date"].dt.strftime("%G-W%V")
    else:
        return

    weeks = sorted(trades["yw"].unique())
    if len(weeks) == 0:
        return

    # Build KS events by week
    ks_by_week = {}
    if ks_events is not None and len(ks_events) > 0 and "date" in ks_events.columns:
        ks_events = ks_events.copy()
        ks_events["date"] = pd.to_datetime(ks_events["date"])
        ks_events["yw"] = ks_events["date"].dt.strftime("%G-W%V")
        ks_by_week = ks_events.groupby("yw").size().to_dict()

    # Build DD by week from daily report
    dd_by_week = {}
    if daily is not None and len(daily) > 0 and "trailing_dd" in daily.columns:
        daily_copy = daily.copy()
        daily_copy["date"] = pd.to_datetime(daily_copy["date"])
        daily_copy["yw"] = daily_copy["date"].dt.strftime("%G-W%V")
        dd_by_week = daily_copy.groupby("yw")["trailing_dd"].max().to_dict()

    print()
    print("  WEEKLY VIEW")
    print("  " + "\u2500" * 34)
    print(f"  {'Week':<13}{'Trades':<8}{'WR':<7}{'PnL':<10}{'DD':<8}{'KS'}")
    print(f"  {'\u2500'*13}{'\u2500'*8}{'\u2500'*7}{'\u2500'*10}{'\u2500'*8}{'\u2500'*4}")

    for wk in weeks:
        wk_trades = trades[trades["yw"] == wk]
        n = len(wk_trades)
        wins = (wk_trades["pnl"] > 0).sum()
        wr = wins / n if n > 0 else 0
        pnl = wk_trades["pnl"].sum()
        dd = dd_by_week.get(wk, 0)
        ks_count = ks_by_week.get(wk, 0)
        ks_str = "OK" if ks_count == 0 else f"{ks_count}x"
        dd_str = fmt_pnl(dd) if dd != 0 else "$0"

        print(f"  {wk:<13}{n:<8}{fmt_pct(wr*100):<7}{fmt_pnl(pnl):<10}{dd_str:<8}{ks_str}")


def section_verdict(all_statuses: list[str]):
    """Print the VERDICT section."""
    verdict = compute_verdict(all_statuses)

    print()
    print("  VERDICT")
    print("  " + "\u2500" * 34)
    print(f"  Overall: {verdict}")
    print()
    print("  ON TRACK: all metrics within tolerance of backtest")
    print("  WATCH: 1-2 metrics drifting (expected early \u2014 small sample)")
    print("  DRIFTING: 3+ metrics significantly off")
    print("  ALARM: kill switch or structural failure")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Forward Test Scorecard")
    parser.add_argument(
        "--period",
        choices=["daily", "weekly", "all"],
        default="all",
        help="Period to evaluate (default: all available data)",
    )
    args = parser.parse_args()
    period = args.period

    # Load data
    trades = load_csv("trade_log.csv", parse_dates=["date"])
    daily = load_csv("daily_report.csv", parse_dates=["date"])
    signals = load_csv("signal_log.csv", parse_dates=["date"])
    ks_events = load_csv("kill_switch_events.csv", parse_dates=["date"])

    # Check if we have any data at all
    if trades is None and daily is None:
        print()
        print("=" * 70)
        print("  FORWARD TEST SCORECARD")
        print("=" * 70)
        print()
        print("  No data found. Expected files in:")
        print(f"    {ROOT / 'logs' / 'trade_log.csv'}")
        print(f"    {ROOT / 'logs' / 'daily_report.csv'}")
        print()
        print("  Forward testing has not started or log files are missing.")
        print("=" * 70)
        return

    # Apply period filter
    if trades is not None:
        trades = filter_period(trades, "date", period)
    if daily is not None:
        daily = filter_period(daily, "date", period)
    if signals is not None:
        signals = filter_period(signals, "date", period)
    if ks_events is not None:
        ks_events = filter_period(ks_events, "date", period)

    # Determine date range and trading days
    dates_seen = set()
    if trades is not None and len(trades) > 0 and "date" in trades.columns:
        dates_seen.update(pd.to_datetime(trades["date"]).dt.date)
    if daily is not None and len(daily) > 0 and "date" in daily.columns:
        dates_seen.update(pd.to_datetime(daily["date"]).dt.date)

    if len(dates_seen) == 0:
        n_days = 0
        date_min_str = "\u2014"
        date_max_str = "\u2014"
    else:
        sorted_dates = sorted(dates_seen)
        n_days = len(sorted_dates)
        date_min_str = sorted_dates[0].strftime("%Y-%m-%d")
        date_max_str = sorted_dates[-1].strftime("%Y-%m-%d")

    # Header
    print()
    print("=" * 70)
    print("  FORWARD TEST SCORECARD")
    if n_days > 0:
        print(f"  Period: {date_min_str} to {date_max_str} ({n_days} trading day{'s' if n_days != 1 else ''})")
    else:
        print(f"  Period: no trading days in selected range ({period})")
    print("=" * 70)

    # Build scorecard
    all_statuses = []

    statuses = section_summary(trades, daily, signals, ks_events, n_days)
    all_statuses.extend(statuses)

    statuses = section_drift(trades, daily, signals, n_days)
    all_statuses.extend(statuses)

    section_strategy_breakdown(trades, n_days)

    section_weekly_view(trades, daily, ks_events)

    section_verdict(all_statuses)

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
