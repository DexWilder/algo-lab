"""Forward Validation Analyzer — compare paper trading results to backtest expectations.

READ-ONLY analysis tool. Does not modify any execution files.

Reads from:
    logs/trade_log.csv
    logs/daily_report.csv
    logs/signal_log.csv
    state/account_state.json

Usage:
    python3 research/forward_validation_analyzer.py
    python3 research/forward_validation_analyzer.py --days 30
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Backtest expectations (Phase 16 controller simulation)
# ---------------------------------------------------------------------------
EXPECTED = {
    "trade_freq_per_day": 1.1,        # 391 trades / 355 days
    "win_rate": 0.52,
    "sharpe": 4.04,
    "monthly_positive_rate": 0.84,
    "trade_retention": 0.70,          # 391 kept / 560 raw
    "strategy_shares": {              # approximate % of total trades
        "PB-MGC-Short":              0.25,
        "ORB-MGC-Long":              0.20,
        "VWAP-MNQ-Long":             0.20,
        "XB-PB-EMA-MES-Short":       0.15,
        "BB-EQ-MGC-Long":            0.10,
        "Donchian-MNQ-Long-GRINDING": 0.10,
    },
}

# Thresholds for flagging
THRESH_TRADE_FREQ_LOW = 0.50   # flag if below 50% of expected
THRESH_TRADE_FREQ_HIGH = 2.00  # flag if above 200% of expected
THRESH_WIN_RATE_PP = 10        # flag if off by >10 percentage points
THRESH_RETENTION_PP = 15       # flag if retention off by >15pp
THRESH_STRATEGY_SHARE_PP = 10  # flag if strategy share off by >10pp

# Expected regime distribution (approximate from backtest)
EXPECTED_REGIME_DIST = {
    "LOW_VOL":    0.35,
    "NORMAL":     0.45,
    "HIGH_VOL":   0.20,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_csv(path: Path, parse_dates=None) -> pd.DataFrame | None:
    """Load a CSV, return None if missing."""
    if not path.exists():
        print(f"  [MISSING] {path.relative_to(ROOT)}")
        return None
    df = pd.read_csv(path, parse_dates=parse_dates)
    print(f"  [OK]      {path.relative_to(ROOT)}  ({len(df)} rows)")
    return df


def classify(value, expected, low_thresh, high_thresh=None):
    """Return PASS / WATCH / FLAG based on deviation."""
    if high_thresh is None:
        high_thresh = low_thresh
    diff = abs(value - expected)
    if diff <= low_thresh:
        return "PASS"
    elif diff <= high_thresh:
        return "WATCH"
    return "FLAG"


def fmt_pct(v):
    return f"{v * 100:.1f}%"


def section(title):
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def analyze_trade_frequency(trades: pd.DataFrame, trading_days: int):
    section("TRADE FREQUENCY")

    total = len(trades)
    freq = total / trading_days if trading_days > 0 else 0
    ratio = freq / EXPECTED["trade_freq_per_day"] if EXPECTED["trade_freq_per_day"] > 0 else 0

    status = "PASS"
    if ratio < THRESH_TRADE_FREQ_LOW or ratio > THRESH_TRADE_FREQ_HIGH:
        status = "FLAG"
    elif ratio < 0.70 or ratio > 1.50:
        status = "WATCH"

    print(f"  Total trades:      {total}")
    print(f"  Trading days:      {trading_days}")
    print(f"  Frequency:         {freq:.2f} trades/day  (expected {EXPECTED['trade_freq_per_day']:.1f})")
    print(f"  Ratio to expected: {ratio:.2f}x")
    print(f"  Status:            [{status}]")
    return status


def analyze_win_rate(trades: pd.DataFrame):
    section("WIN RATE")

    wins = (trades["pnl"] > 0).sum()
    total = len(trades)
    wr = wins / total if total > 0 else 0
    diff_pp = (wr - EXPECTED["win_rate"]) * 100

    status = "PASS" if abs(diff_pp) <= THRESH_WIN_RATE_PP else "FLAG"
    if status == "PASS" and abs(diff_pp) > 5:
        status = "WATCH"

    print(f"  Wins / Total:      {wins} / {total}")
    print(f"  Win rate:          {fmt_pct(wr)}  (expected {fmt_pct(EXPECTED['win_rate'])})")
    print(f"  Deviation:         {diff_pp:+.1f}pp")
    print(f"  Status:            [{status}]")
    return status


def analyze_strategy_mix(trades: pd.DataFrame):
    section("STRATEGY MIX")

    counts = trades["strategy"].value_counts()
    total = len(trades)
    statuses = []

    for strat, exp_share in EXPECTED["strategy_shares"].items():
        actual = counts.get(strat, 0)
        actual_share = actual / total if total > 0 else 0
        diff_pp = (actual_share - exp_share) * 100

        if actual == 0:
            status = "FLAG"
        elif abs(diff_pp) > THRESH_STRATEGY_SHARE_PP:
            status = "FLAG"
        elif abs(diff_pp) > 5:
            status = "WATCH"
        else:
            status = "PASS"

        statuses.append(status)
        print(f"  {strat:35s}  {fmt_pct(actual_share):>6s}  (exp {fmt_pct(exp_share):>6s})  "
              f"diff {diff_pp:+5.1f}pp  [{status}]")

    # Check for unexpected strategies
    expected_names = set(EXPECTED["strategy_shares"].keys())
    unexpected = set(counts.index) - expected_names
    if unexpected:
        print(f"\n  Unexpected strategies: {', '.join(sorted(unexpected))}")

    worst = "FLAG" if "FLAG" in statuses else ("WATCH" if "WATCH" in statuses else "PASS")
    return worst


def analyze_signal_retention(signals: pd.DataFrame):
    section("SIGNAL RETENTION (Controller Filtering)")

    total_raw = signals["signals_total"].sum()
    total_kept = signals["signals_kept"].sum()
    retention = total_kept / total_raw if total_raw > 0 else 0
    diff_pp = (retention - EXPECTED["trade_retention"]) * 100

    regime_blocked = signals["regime_blocked"].sum()
    timing_blocked = signals["timing_blocked"].sum()
    conviction_override = signals["conviction_override"].sum() if "conviction_override" in signals.columns else 0

    status = "PASS" if abs(diff_pp) <= THRESH_RETENTION_PP else "FLAG"
    if status == "PASS" and abs(diff_pp) > 8:
        status = "WATCH"

    print(f"  Raw signals:       {total_raw}")
    print(f"  Kept signals:      {total_kept}")
    print(f"  Retention:         {fmt_pct(retention)}  (expected {fmt_pct(EXPECTED['trade_retention'])})")
    print(f"  Deviation:         {diff_pp:+.1f}pp")
    print(f"  Regime blocked:    {regime_blocked}")
    print(f"  Timing blocked:    {timing_blocked}")
    print(f"  Conviction override: {conviction_override}")
    print(f"  Status:            [{status}]")
    return status


def analyze_regime_distribution(daily: pd.DataFrame):
    section("REGIME DISTRIBUTION")

    if "regime" not in daily.columns:
        print("  [SKIP] No regime column in daily report")
        return "SKIP"

    counts = daily["regime"].value_counts(normalize=True)
    statuses = []

    for regime, exp_share in EXPECTED_REGIME_DIST.items():
        actual_share = counts.get(regime, 0)
        diff_pp = (actual_share - exp_share) * 100

        status = "PASS" if abs(diff_pp) <= 15 else "WATCH"
        statuses.append(status)
        print(f"  {regime:15s}  {fmt_pct(actual_share):>6s}  (exp {fmt_pct(exp_share):>6s})  "
              f"diff {diff_pp:+5.1f}pp  [{status}]")

    # Show any regimes not in expected list
    unexpected = set(counts.index) - set(EXPECTED_REGIME_DIST.keys())
    for regime in sorted(unexpected):
        print(f"  {regime:15s}  {fmt_pct(counts[regime]):>6s}  (not in expected)")

    worst = "FLAG" if "FLAG" in statuses else ("WATCH" if "WATCH" in statuses else "PASS")
    return worst


def analyze_daily_pnl(daily: pd.DataFrame):
    section("DAILY P&L SUMMARY")

    if "daily_pnl" not in daily.columns:
        print("  [SKIP] No daily_pnl column")
        return "SKIP"

    total_pnl = daily["daily_pnl"].sum()
    avg_daily = daily["daily_pnl"].mean()
    pos_days = (daily["daily_pnl"] > 0).sum()
    total_days = len(daily)
    daily_pos_rate = pos_days / total_days if total_days > 0 else 0

    # Monthly positive rate
    if "date" in daily.columns:
        daily["_month"] = pd.to_datetime(daily["date"]).dt.to_period("M")
        monthly = daily.groupby("_month")["daily_pnl"].sum()
        months_pos = (monthly > 0).sum()
        months_total = len(monthly)
        monthly_pos_rate = months_pos / months_total if months_total > 0 else 0
        daily.drop(columns=["_month"], inplace=True)
    else:
        monthly_pos_rate = None

    # Trailing DD
    max_dd = daily["trailing_dd"].min() if "trailing_dd" in daily.columns else None

    print(f"  Total P&L:         ${total_pnl:,.2f}")
    print(f"  Avg daily P&L:     ${avg_daily:,.2f}")
    print(f"  Positive days:     {pos_days}/{total_days} ({fmt_pct(daily_pos_rate)})")

    status = "PASS"
    if monthly_pos_rate is not None:
        diff_pp = (monthly_pos_rate - EXPECTED["monthly_positive_rate"]) * 100
        m_status = "PASS" if abs(diff_pp) <= 15 else ("WATCH" if abs(diff_pp) <= 25 else "FLAG")
        print(f"  Monthly positive:  {months_pos}/{months_total} ({fmt_pct(monthly_pos_rate)})  "
              f"(exp {fmt_pct(EXPECTED['monthly_positive_rate'])})  [{m_status}]")
        status = m_status

    if max_dd is not None:
        print(f"  Max trailing DD:   ${max_dd:,.2f}")

    print(f"  Status:            [{status}]")
    return status


def analyze_account_state(state_path: Path):
    section("ACCOUNT STATE")

    if not state_path.exists():
        print(f"  [MISSING] {state_path.relative_to(ROOT)}")
        return "SKIP"

    with open(state_path) as f:
        state = json.load(f)

    for key, val in state.items():
        if isinstance(val, float):
            print(f"  {key:25s}  {val:,.2f}")
        else:
            print(f"  {key:25s}  {val}")

    return "INFO"


def analyze_kill_switch(daily: pd.DataFrame):
    section("KILL SWITCH ACTIVATIONS")

    if "kill_switch" not in daily.columns:
        print("  [SKIP] No kill_switch column")
        return "SKIP"

    activations = daily[daily["kill_switch"] == True]  # noqa: E712
    count = len(activations)

    if count == 0:
        print("  No kill switch activations")
        status = "PASS"
    else:
        print(f"  Kill switch activated {count} time(s):")
        for _, row in activations.iterrows():
            date_str = row.get("date", "?")
            dd = row.get("trailing_dd", "?")
            print(f"    {date_str}  trailing_dd={dd}")
        status = "WATCH" if count <= 2 else "FLAG"

    print(f"  Status:            [{status}]")
    return status


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Forward validation analyzer")
    parser.add_argument("--days", type=int, default=0,
                        help="Analyze last N days only (default: all)")
    args = parser.parse_args()

    print("=" * 60)
    print("  FORWARD VALIDATION ANALYZER")
    print("  Comparing paper trading results to backtest expectations")
    print("=" * 60)

    # ---- Load files ----
    section("LOADING DATA")
    trade_log = load_csv(ROOT / "logs" / "trade_log.csv", parse_dates=["date"])
    daily_report = load_csv(ROOT / "logs" / "daily_report.csv", parse_dates=["date"])
    signal_log = load_csv(ROOT / "logs" / "signal_log.csv", parse_dates=["date"])
    state_path = ROOT / "state" / "account_state.json"

    missing = []
    if trade_log is None:
        missing.append("trade_log.csv")
    if daily_report is None:
        missing.append("daily_report.csv")

    if missing:
        print(f"\n  Cannot proceed without: {', '.join(missing)}")
        print("  Ensure the paper trading system is logging to logs/")
        sys.exit(1)

    # ---- Filter by --days ----
    if args.days > 0:
        cutoff = pd.Timestamp.now() - pd.Timedelta(days=args.days)
        trade_log = trade_log[trade_log["date"] >= cutoff]
        daily_report = daily_report[daily_report["date"] >= cutoff]
        if signal_log is not None:
            signal_log = signal_log[signal_log["date"] >= cutoff]
        print(f"\n  Filtered to last {args.days} days (since {cutoff.date()})")

    trading_days = daily_report["date"].nunique() if "date" in daily_report.columns else len(daily_report)

    # ---- Run analyses ----
    results = {}
    results["Trade Frequency"] = analyze_trade_frequency(trade_log, trading_days)
    results["Win Rate"] = analyze_win_rate(trade_log)
    results["Strategy Mix"] = analyze_strategy_mix(trade_log)

    if signal_log is not None:
        results["Signal Retention"] = analyze_signal_retention(signal_log)

    results["Regime Distribution"] = analyze_regime_distribution(daily_report)
    results["Daily P&L"] = analyze_daily_pnl(daily_report)
    results["Kill Switch"] = analyze_kill_switch(daily_report)
    results["Account State"] = analyze_account_state(state_path)

    # ---- Summary ----
    section("SUMMARY")
    flags = []
    watches = []

    for name, status in results.items():
        if status == "FLAG":
            flags.append(name)
        elif status == "WATCH":
            watches.append(name)

    for name, status in results.items():
        icon = {"PASS": "+", "WATCH": "~", "FLAG": "!", "SKIP": "-", "INFO": "i"}
        print(f"  [{icon.get(status, '?')}] {status:5s}  {name}")

    print()
    if flags:
        print(f"  *** {len(flags)} FLAG(s): {', '.join(flags)}")
        print("      Action: investigate immediately")
    if watches:
        print(f"  ~~~ {len(watches)} WATCH(es): {', '.join(watches)}")
        print("      Action: monitor, may resolve with more data")
    if not flags and not watches:
        print("  All metrics within expected ranges.")

    print()


if __name__ == "__main__":
    main()
