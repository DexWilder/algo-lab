#!/usr/bin/env python3
"""Probation Health Audit — surface dead, broken, or deteriorating probation strategies.

Runs on schedule (daily pipeline) to ensure no probation strategy sits
dead, structurally broken, or quietly deteriorating without being flagged.

Categories:
  DEAD:         0 trades past expected cadence (not sparse-exempt)
  BROKEN:       structurally unable to trade (data/runner mismatch)
  DETERIORATING: forward evidence actively failing (PF < 0.8, WR < 30%)
  SPARSE_OK:    0 trades but sparse by design (event/daily horizon)
  ACCUMULATING: producing evidence, not yet at review gate
  ON_TRACK:     sufficient evidence, within expected range

Usage:
    python3 scripts/probation_health_audit.py              # Print
    python3 scripts/probation_health_audit.py --save       # Print + save
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_probation_health.md"

NOW = datetime.now()
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")

# Strategies that are sparse by design (don't flag for 0 trades)
SPARSE_STRATEGIES = {
    "DailyTrend-MGC-Long",        # daily horizon, ~2 trades/month
    "TV-NFP-High-Low-Levels",     # monthly event (NFP)
    "PreFOMC-Drift-Equity",       # 8x/year event (FOMC)
    "ZN-Afternoon-Reversion",     # sparse session, ~1/week
    "VolManaged-EquityIndex-Futures",  # always-in (synthetic daily entries)
}

# Expected trades per month for non-sparse strategies
EXPECTED_FREQ = {
    "XB-ORB-EMA-Ladder-MNQ": 14,
    "XB-ORB-EMA-Ladder-MCL": 15,
    "XB-ORB-EMA-Ladder-MYM": 14,
}

# Days before flagging a non-sparse strategy as DEAD
DEAD_THRESHOLD_DAYS = 15


def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def audit_probation():
    """Audit all probation strategies and return categorized results."""
    reg = _load_json(str(REGISTRY_PATH))
    trades = pd.read_csv(TRADE_LOG) if TRADE_LOG.exists() else pd.DataFrame()

    probation = [s for s in reg.get("strategies", [])
                 if s.get("status") == "probation"]

    results = []
    for s in probation:
        sid = s["strategy_id"]
        fwd = trades[trades["strategy"] == sid] if not trades.empty and "strategy" in trades.columns else pd.DataFrame()
        n_trades = len(fwd)
        pnl = fwd["pnl"].sum() if n_trades else 0

        # Last trade date
        if n_trades > 0:
            last_trade = pd.to_datetime(fwd["date"].max())
            days_since = (NOW - last_trade).days
        else:
            last_trade = None
            days_since = 999

        # Win rate
        wr = (fwd["pnl"] > 0).mean() if n_trades else 0

        # Forward PF
        if n_trades > 0:
            wins_pnl = fwd[fwd["pnl"] > 0]["pnl"].sum()
            losses_pnl = abs(fwd[fwd["pnl"] < 0]["pnl"].sum())
            fwd_pf = wins_pnl / losses_pnl if losses_pnl > 0 else (99 if wins_pnl > 0 else 0)
        else:
            fwd_pf = 0

        # Promotion date
        promoted = s.get("promotion_date", s.get("last_controller_date", ""))
        if promoted:
            try:
                promo_date = pd.to_datetime(promoted)
                days_on_probation = (NOW - promo_date).days
            except Exception:
                days_on_probation = 0
        else:
            days_on_probation = 0

        # Categorize
        is_sparse = sid in SPARSE_STRATEGIES
        expected_monthly = EXPECTED_FREQ.get(sid, 5)

        if n_trades == 0 and not is_sparse and days_on_probation > DEAD_THRESHOLD_DAYS:
            category = "DEAD"
            reason = f"0 trades after {days_on_probation}d on probation (not sparse-exempt)"
        elif n_trades == 0 and is_sparse:
            category = "SPARSE_OK"
            reason = f"0 trades, sparse by design ({sid})"
        elif n_trades == 0:
            category = "ACCUMULATING"
            reason = f"0 trades, {days_on_probation}d on probation (< {DEAD_THRESHOLD_DAYS}d threshold)"
        elif n_trades >= 10 and fwd_pf < 0.80:
            category = "DETERIORATING"
            reason = f"PF {fwd_pf:.2f} < 0.80 on {n_trades} trades"
        elif n_trades >= 5 and wr < 0.30:
            category = "DETERIORATING"
            reason = f"WR {wr*100:.0f}% < 30% on {n_trades} trades"
        elif days_since > DEAD_THRESHOLD_DAYS and not is_sparse:
            category = "STALE"
            reason = f"Last trade {days_since}d ago (> {DEAD_THRESHOLD_DAYS}d)"
        else:
            category = "ON_TRACK" if n_trades >= 5 else "ACCUMULATING"
            reason = f"{n_trades} trades, ${pnl:+,.0f}, WR {wr*100:.0f}%"

        # Check for structural issues
        notes = (s.get("notes") or "").lower()
        if "structurally broken" in notes or "unable to trade" in notes:
            category = "BROKEN"
            reason = "Flagged as structurally broken in registry"

        results.append({
            "strategy_id": sid,
            "category": category,
            "reason": reason,
            "fwd_trades": n_trades,
            "fwd_pnl": round(pnl, 2),
            "fwd_pf": round(fwd_pf, 2),
            "fwd_wr": round(wr * 100, 1),
            "days_since_trade": days_since,
            "days_on_probation": days_on_probation,
            "is_xb_orb": "XB-ORB" in sid,
        })

    return results


def generate_report(results):
    lines = []
    lines.append("# Probation Health Audit")
    lines.append(f"*{TIMESTAMP}*")
    lines.append("")

    # Summary
    from collections import Counter
    cats = Counter(r["category"] for r in results)
    actionable = cats.get("DEAD", 0) + cats.get("BROKEN", 0) + cats.get("DETERIORATING", 0)

    if actionable > 0:
        lines.append(f"**{actionable} probation strategies need attention.**")
    else:
        lines.append("**All probation strategies healthy.**")
    lines.append("")

    # Category breakdown
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    for cat in ["DEAD", "BROKEN", "DETERIORATING", "STALE", "ACCUMULATING", "SPARSE_OK", "ON_TRACK"]:
        if cats.get(cat, 0) > 0:
            lines.append(f"| {cat} | {cats[cat]} |")
    lines.append("")

    # Detail table
    lines.append("| Strategy | Cat | Trades | PnL | PF | WR | Days Silent |")
    lines.append("|----------|-----|--------|-----|-----|-----|------------|")

    # Sort: problems first
    order = {"DEAD": 0, "BROKEN": 1, "DETERIORATING": 2, "STALE": 3, "ACCUMULATING": 4, "SPARSE_OK": 5, "ON_TRACK": 6}
    results.sort(key=lambda r: order.get(r["category"], 9))

    for r in results:
        pf_str = f"{r['fwd_pf']:.1f}" if r["fwd_trades"] > 0 else "—"
        wr_str = f"{r['fwd_wr']:.0f}%" if r["fwd_trades"] > 0 else "—"
        silent = f"{r['days_since_trade']}d" if r["days_since_trade"] < 999 else "—"
        lines.append(
            f"| {r['strategy_id'][:35]} | {r['category']} | {r['fwd_trades']} | "
            f"${r['fwd_pnl']:+,.0f} | {pf_str} | {wr_str} | {silent} |"
        )

    # Action items
    problems = [r for r in results if r["category"] in ("DEAD", "BROKEN", "DETERIORATING")]
    if problems:
        lines.append("")
        lines.append("### Action Required")
        for r in problems:
            lines.append(f"- **{r['strategy_id']}** [{r['category']}]: {r['reason']}")

    lines.append("")
    lines.append("---")
    lines.append("*SPARSE_OK = sparse by design (event/daily), exempt from 0-trade flags.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Probation Health Audit")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    results = audit_probation()
    report = generate_report(results)
    print(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
