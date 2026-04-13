#!/usr/bin/env python3
"""XB-ORB Forward Behavior Tracker — live vs backtest alignment diagnostic.

Compares each forward trade against the backtest distribution to detect
qualitative drift before statistical tests become meaningful.

Checks per trade:
  - Entry hour fit (is entry within backtest entry-hour distribution?)
  - Hold duration fit (is duration within backtest IQR?)
  - PnL magnitude fit (is outcome within backtest p10-p90?)
  - Direction mix tracking (cumulative long/short ratio vs backtest)
  - Win/loss pattern (running WR vs backtest WR)

Runs on whatever forward trades exist — designed to compound from 1 trade.

Usage:
    python3 scripts/forward_behavior_tracker.py              # Print
    python3 scripts/forward_behavior_tracker.py --save       # Print + save
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
from engine.asset_config import get_asset

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_forward_behavior.md"

XB_ORB_STRATEGIES = {
    "XB-ORB-EMA-Ladder-MNQ": "MNQ",
    "XB-ORB-EMA-Ladder-MCL": "MCL",
    "XB-ORB-EMA-Ladder-MYM": "MYM",
}

NOW = datetime.now()
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")


def _load_backtest_profile(asset):
    """Run backtest on full history and compute profile stats."""
    cfg = get_asset(asset)
    spec = importlib.util.spec_from_file_location(
        "strat", ROOT / "strategies/xb_orb_ema_ladder/strategy.py"
    )
    mod = importlib.util.module_from_spec(spec)
    mod.TICK_SIZE = cfg["tick_size"]
    spec.loader.exec_module(mod)

    df = pd.read_csv(ROOT / f"data/processed/{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    signals = mod.generate_signals(df.copy())
    result = run_backtest(
        df, signals, mode="both",
        point_value=cfg["point_value"],
        tick_size=cfg["tick_size"],
        commission_per_side=cfg["commission_per_side"],
        slippage_ticks=cfg["slippage_ticks"],
    )
    bt = result["trades_df"]
    if len(bt) == 0:
        return None

    bt["entry_time"] = pd.to_datetime(bt["entry_time"])
    bt["exit_time"] = pd.to_datetime(bt["exit_time"])
    bt["hold_min"] = (bt["exit_time"] - bt["entry_time"]).dt.total_seconds() / 60
    bt["entry_hour"] = bt["entry_time"].dt.hour

    long_count = (bt["side"] == "long").sum()
    short_count = (bt["side"] == "short").sum()

    return {
        "trades": len(bt),
        "pf": float(bt[bt["pnl"] > 0]["pnl"].sum() / abs(bt[bt["pnl"] < 0]["pnl"].sum())),
        "wr": float((bt["pnl"] > 0).mean()),
        "hold_min_p25": float(bt["hold_min"].quantile(0.25)),
        "hold_min_median": float(bt["hold_min"].median()),
        "hold_min_p75": float(bt["hold_min"].quantile(0.75)),
        "pnl_p10": float(bt["pnl"].quantile(0.10)),
        "pnl_median": float(bt["pnl"].median()),
        "pnl_p90": float(bt["pnl"].quantile(0.90)),
        "entry_hour_mode": int(bt["entry_hour"].mode().iloc[0]),
        "entry_hour_dist": bt["entry_hour"].value_counts().to_dict(),
        "long_frac": float(long_count / len(bt)),
        "short_frac": float(short_count / len(bt)),
    }


def _assess_trade(trade, profile):
    """Score a single forward trade against the backtest profile."""
    flags = []

    # Entry hour
    entry_hour = pd.to_datetime(trade["entry_time"]).hour
    if entry_hour not in profile["entry_hour_dist"]:
        flags.append(f"entry_hour {entry_hour} NEVER seen in backtest")
    elif profile["entry_hour_dist"].get(entry_hour, 0) < 10:
        flags.append(f"entry_hour {entry_hour} rare in backtest (<10 trades)")

    # Hold duration
    hold_min = (pd.to_datetime(trade["exit_time"]) - pd.to_datetime(trade["entry_time"])).total_seconds() / 60
    if hold_min < profile["hold_min_p25"] * 0.5:
        flags.append(f"hold {hold_min:.0f}min < 50% of p25 ({profile['hold_min_p25']:.0f})")
    elif hold_min > profile["hold_min_p75"] * 1.5:
        flags.append(f"hold {hold_min:.0f}min > 150% of p75 ({profile['hold_min_p75']:.0f})")

    # PnL magnitude
    pnl = trade["pnl"]
    if pnl < profile["pnl_p10"] * 1.5:
        flags.append(f"loss ${pnl:.0f} beyond p10 (${profile['pnl_p10']:.0f})")
    elif pnl > profile["pnl_p90"] * 2:
        flags.append(f"win ${pnl:.0f} beyond 2x p90 (${profile['pnl_p90']:.0f})")

    status = "ALIGNED" if not flags else "FLAG"
    return {
        "entry_hour": entry_hour,
        "hold_min": hold_min,
        "pnl": pnl,
        "status": status,
        "flags": flags,
    }


def generate_report():
    """Generate the forward behavior tracking report."""
    if not TRADE_LOG.exists():
        return "No trade log found."

    trades_df = pd.read_csv(TRADE_LOG)
    lines = []
    lines.append("# XB-ORB Forward Behavior Tracker")
    lines.append(f"*{TIMESTAMP}*")
    lines.append("")

    for strat_id, asset in XB_ORB_STRATEGIES.items():
        fwd = trades_df[trades_df["strategy"] == strat_id]
        if len(fwd) == 0:
            lines.append(f"## {strat_id} ({asset})")
            lines.append("No forward trades yet.")
            lines.append("")
            continue

        # Load backtest profile
        try:
            data_path = ROOT / f"data/processed/{asset}_5m.csv"
            if not data_path.exists():
                lines.append(f"## {strat_id} ({asset})")
                lines.append(f"No data file for {asset}.")
                lines.append("")
                continue
            profile = _load_backtest_profile(asset)
        except Exception as e:
            lines.append(f"## {strat_id} ({asset})")
            lines.append(f"Error loading backtest profile: {e}")
            lines.append("")
            continue

        if profile is None:
            continue

        lines.append(f"## {strat_id} ({asset})")
        lines.append(f"Forward trades: {len(fwd)} | Backtest trades: {profile['trades']}")
        lines.append("")

        # Per-trade assessment
        lines.append("### Trade-by-Trade")
        lines.append(f"{'Date':<12s} {'Side':<6s} {'PnL':>8s} {'Hold':>6s} {'Hour':>5s} {'Status'}")
        lines.append(f"{'-'*12} {'-'*6} {'-'*8} {'-'*6} {'-'*5} {'-'*20}")

        assessments = []
        for _, t in fwd.iterrows():
            a = _assess_trade(t, profile)
            assessments.append(a)
            flag_str = "; ".join(a["flags"]) if a["flags"] else ""
            lines.append(
                f"{t['date']:<12s} {t['side']:<6s} ${a['pnl']:>+6.0f} "
                f"{a['hold_min']:>5.0f}m {a['entry_hour']:>4d}h "
                f"{a['status']}{' — ' + flag_str if flag_str else ''}"
            )

        # Cumulative metrics
        lines.append("")
        lines.append("### Cumulative Alignment")
        total_pnl = fwd["pnl"].sum()
        fwd_wr = (fwd["pnl"] > 0).mean()
        fwd_long_frac = (fwd["side"] == "long").mean() if "side" in fwd.columns else 0
        aligned = sum(1 for a in assessments if a["status"] == "ALIGNED")

        lines.append(f"  PnL: ${total_pnl:+,.0f} | WR: {fwd_wr*100:.0f}% (backtest: {profile['wr']*100:.0f}%)")
        lines.append(f"  Long%: {fwd_long_frac*100:.0f}% (backtest: {profile['long_frac']*100:.0f}%)")
        lines.append(f"  Aligned trades: {aligned}/{len(assessments)}")

        flagged = [a for a in assessments if a["status"] == "FLAG"]
        if flagged:
            lines.append(f"  Flagged trades: {len(flagged)}")
            for a in flagged:
                lines.append(f"    - {'; '.join(a['flags'])}")
        else:
            lines.append("  No behavioral flags.")

        # Rolling drift scoreboard (append-only, compounds per trade)
        if len(assessments) >= 2:
            lines.append("")
            lines.append("### Drift Scoreboard")
            hold_times = [a["hold_min"] for a in assessments]
            entry_hours = [a["entry_hour"] for a in assessments]
            pnls = [a["pnl"] for a in assessments]

            avg_hold = sum(hold_times) / len(hold_times)
            hold_drift = avg_hold - profile["hold_min_median"]
            hold_drift_pct = hold_drift / profile["hold_min_median"] * 100

            avg_entry_hr = sum(entry_hours) / len(entry_hours)
            entry_hr_drift = avg_entry_hr - profile["entry_hour_mode"]

            # Frequency: trades per calendar day
            fwd_dates = pd.to_datetime(fwd["entry_time"])
            if len(fwd_dates) > 1:
                fwd_span_days = (fwd_dates.max() - fwd_dates.min()).days
                fwd_freq = len(fwd) / max(fwd_span_days, 1) * 30.44
            else:
                fwd_freq = float("nan")

            lines.append(f"  {'Metric':<25s} {'Forward':>10s} {'Backtest':>10s} {'Drift':>10s}")
            lines.append(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10}")
            lines.append(f"  {'Avg hold (min)':<25s} {avg_hold:>10.0f} {profile['hold_min_median']:>10.0f} {hold_drift_pct:>+9.0f}%")
            lines.append(f"  {'Avg entry hour':<25s} {avg_entry_hr:>10.1f} {profile['entry_hour_mode']:>10d} {entry_hr_drift:>+10.1f}")
            lines.append(f"  {'Win rate':<25s} {fwd_wr*100:>9.0f}% {profile['wr']*100:>9.0f}% {(fwd_wr-profile['wr'])*100:>+9.0f}pp")
            lines.append(f"  {'Long%':<25s} {fwd_long_frac*100:>9.0f}% {profile['long_frac']*100:>9.0f}% {(fwd_long_frac-profile['long_frac'])*100:>+9.0f}pp")
            if not pd.isna(fwd_freq):
                lines.append(f"  {'Trades/month':<25s} {fwd_freq:>10.1f} {'~14':>10s} {'—':>10s}")
            lines.append("")
            lines.append("  *Drift is expected to be noisy with <20 trades. Track trend, not level.*")
        lines.append("")

    # Overall verdict
    lines.append("---")
    lines.append(f"*Backtest profiles computed from full history. Flags indicate outlier trades,*")
    lines.append(f"*not necessarily problems. With <20 trades, expect high variance.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="XB-ORB Forward Behavior Tracker")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    report = generate_report()
    print(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
