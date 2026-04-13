#!/usr/bin/env python3
"""XB-ORB Portfolio Monitor — one-view probation dashboard.

Shows all XB-ORB workhorse variants in a single compact view:
- Forward trades and PnL per asset
- Behavioral alignment status
- Probation progress toward review gates
- Last signal date

Usage:
    python3 scripts/xb_orb_portfolio_monitor.py          # Print
    python3 scripts/xb_orb_portfolio_monitor.py --save    # Print + save
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_xb_orb_portfolio.md"

VARIANTS = {
    "XB-ORB-EMA-Ladder-MNQ": {"asset": "MNQ", "bt_pf": 1.62, "bt_wr": 0.61, "bt_trades": 1183},
    "XB-ORB-EMA-Ladder-MCL": {"asset": "MCL", "bt_pf": 1.33, "bt_wr": 0.57, "bt_trades": 898},
    "XB-ORB-EMA-Ladder-MYM": {"asset": "MYM", "bt_pf": 1.67, "bt_wr": 0.56, "bt_trades": 340},
}

REVIEW_GATES = [20, 30, 50, 100]

NOW = datetime.now()
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")


def generate_report():
    lines = []
    lines.append("# XB-ORB Portfolio Monitor")
    lines.append(f"*{TIMESTAMP}*")
    lines.append("")

    # Load forward trades
    if TRADE_LOG.exists():
        trades = pd.read_csv(TRADE_LOG)
    else:
        trades = pd.DataFrame()

    # Portfolio summary line
    xb_trades = trades[trades["strategy"].str.contains("XB-ORB", na=False)] if not trades.empty else pd.DataFrame()
    total_fwd = len(xb_trades)
    total_pnl = xb_trades["pnl"].sum() if total_fwd else 0

    asset_summaries = []
    for strat_id, info in VARIANTS.items():
        fwd = xb_trades[xb_trades["strategy"] == strat_id] if total_fwd else pd.DataFrame()
        n = len(fwd)
        pnl = fwd["pnl"].sum() if n else 0
        asset_summaries.append(f"{info['asset']} {n}t ${pnl:+,.0f}")

    lines.append(f"**Portfolio: {total_fwd} trades, ${total_pnl:+,.0f}** | {' | '.join(asset_summaries)}")
    lines.append("")

    # Per-variant detail table
    lines.append("| Variant | Asset | BT PF | Fwd Trades | Fwd PnL | Fwd WR | BT WR | Flags | Next Gate | Status |")
    lines.append("|---------|-------|-------|-----------|---------|--------|-------|-------|-----------|--------|")

    for strat_id, info in VARIANTS.items():
        fwd = xb_trades[xb_trades["strategy"] == strat_id] if total_fwd else pd.DataFrame()
        n = len(fwd)
        pnl = fwd["pnl"].sum() if n else 0
        wr = (fwd["pnl"] > 0).mean() * 100 if n else 0

        # Determine next review gate
        next_gate = None
        for g in REVIEW_GATES:
            if n < g:
                next_gate = g
                break
        gate_str = f"{n}/{next_gate}" if next_gate else f"{n}/DONE"

        # Last signal date
        if n > 0:
            last_date = fwd["date"].iloc[-1]
        else:
            last_date = "—"

        # Probation status
        if n < 20:
            status = "ACCUMULATING"
        elif n < 30:
            status = "NEAR_REVIEW"
        else:
            # Check forward metrics
            fwd_pf = 0
            if n > 0:
                wins_pnl = fwd[fwd["pnl"] > 0]["pnl"].sum()
                losses_pnl = abs(fwd[fwd["pnl"] < 0]["pnl"].sum())
                fwd_pf = wins_pnl / losses_pnl if losses_pnl > 0 else 99
            if fwd_pf < 0.90:
                status = "DOWNGRADE_WARN"
            elif fwd_pf >= 1.15:
                status = "ON_TRACK"
            else:
                status = "MARGINAL"

        # Behavioral flags (placeholder — reads from behavior tracker if available)
        flags = "0/0"  # will be populated by behavior tracker integration

        wr_str = f"{wr:.0f}%" if n else "—"
        lines.append(
            f"| {strat_id.split('-')[-1]} | {info['asset']} | {info['bt_pf']:.2f} | "
            f"{n} | ${pnl:+,.0f} | {wr_str} | {info['bt_wr']*100:.0f}% | "
            f"{flags} | {gate_str} | {status} |"
        )

    lines.append("")

    # Recent trades
    if total_fwd > 0:
        lines.append("### Recent XB-ORB Trades")
        lines.append("")
        recent = xb_trades.tail(10)
        lines.append(f"{'Date':<12s} {'Asset':<5s} {'Side':<6s} {'PnL':>8s}")
        lines.append(f"{'-'*12} {'-'*5} {'-'*6} {'-'*8}")
        for _, t in recent.iterrows():
            asset = VARIANTS.get(t["strategy"], {}).get("asset", "?")
            lines.append(f"{t['date']:<12s} {asset:<5s} {t['side']:<6s} ${t['pnl']:>+6.0f}")
        lines.append("")

    # Framework reference
    lines.append("---")
    lines.append("*Review gates: 20/30/50/100 trades. Promotion PF ≥ 1.15. See docs/XB_ORB_PROBATION_FRAMEWORK.md*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="XB-ORB Portfolio Monitor")
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
