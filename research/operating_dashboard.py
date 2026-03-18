#!/usr/bin/env python3
"""FQL Operating Mode Dashboard — Single-pane system state view.

Read-only advisory dashboard. Does not modify any files or logic.

Usage:
    python3 research/operating_dashboard.py
"""

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "research" / "data"
LOGS_DIR = ROOT / "logs"
STATE_DIR = ROOT / "state"

PROBATION_TARGETS = {
    "DailyTrend-MGC-Long": {"target": 15, "factor": "MOMENTUM", "tier": "REDUCED"},
    "MomPB-6J-Long-US": {"target": 30, "factor": "MOMENTUM", "tier": "REDUCED"},
    "FXBreak-6J-Short-London": {"target": 50, "factor": "STRUCTURAL", "tier": "MICRO"},
    "PreFOMC-Drift-Equity": {"target": 8, "factor": "EVENT", "tier": "MICRO"},
    "TV-NFP-High-Low-Levels": {"target": 8, "factor": "EVENT", "tier": "MICRO"},
}

CLOSED_FAMILIES = [
    "mean_reversion x equity_index (5 failures)",
    "ict x any (2 failures)",
    "gap_fade / gap_reversal (3 failures)",
    "overnight equity premium (2 tests, both ~PF 1.09)",
]

QUEUE = [
    "THEME-VolGated-Structural-Intraday (future theme)",
    "Treasury-CPI-Day re-test (after longer history)",
    "Treasury-12M-TSM re-test (after longer history)",
]

BEST_BLOCKED_UNLOCK = {
    "action": "Longer rates history (pre-2019)",
    "unlocks": "Treasury-CPI-Day regime validation, Treasury-12M-TSM symmetric test",
    "status": "Backfill to 2019 complete. Need pre-2019 for full cycle coverage.",
}


def main():
    W = 70
    print()
    print("=" * W)
    print("  FQL OPERATING MODE DASHBOARD")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * W)

    # ── 1. Probation Portfolio ──
    print(f"\n  PROBATION PORTFOLIO (5 strategies)")
    print(f"  {'-' * (W-4)}")

    trade_log = LOGS_DIR / "trade_log.csv"
    trade_counts = {}
    if trade_log.exists():
        try:
            df = pd.read_csv(trade_log)
            if "strategy" in df.columns:
                for sid in PROBATION_TARGETS:
                    trade_counts[sid] = int((df["strategy"] == sid).sum())
        except Exception:
            pass

    for sid, info in PROBATION_TARGETS.items():
        fwd = trade_counts.get(sid, 0)
        target = info["target"]
        pct = min(100, round(fwd / target * 100)) if target else 0
        bar = "#" * (pct // 5) + "." * (20 - pct // 5)
        print(f"  {sid}")
        print(f"    [{bar}] {fwd}/{target} ({pct}%)  {info['factor']}  {info['tier']}")

    # ── 2. Factor Coverage ──
    print(f"\n  FACTOR COVERAGE")
    print(f"  {'-' * (W-4)}")
    factors = Counter(v["factor"] for v in PROBATION_TARGETS.values())
    all_factors = {"MOMENTUM": 0, "STRUCTURAL": 0, "EVENT": 0, "CARRY": 0, "VOLATILITY": 0}
    all_factors.update(factors)
    for f, count in sorted(all_factors.items()):
        status = f"{count} in probation" if count > 0 else "GAP"
        icon = ">>" if count > 0 else "--"
        print(f"  {icon} {f:<14s} {status}")

    # ── 3. Watch Items ──
    print(f"\n  WATCH ITEMS")
    print(f"  {'-' * (W-4)}")
    reg_path = DATA_DIR / "strategy_registry.json"
    if reg_path.exists():
        reg = json.load(open(reg_path))
        for s in reg["strategies"]:
            if s.get("status") == "probation" and s.get("watch_items"):
                print(f"  {s['strategy_id']}:")
                for item in s["watch_items"]:
                    print(f"    ! {item}")

    # ── 4. Family Closures ──
    print(f"\n  CLOSED FAMILIES (do not harvest)")
    print(f"  {'-' * (W-4)}")
    for family in CLOSED_FAMILIES:
        print(f"  X {family}")

    # ── 5. Next Blocked Unlock ──
    print(f"\n  NEXT BLOCKED UNLOCK")
    print(f"  {'-' * (W-4)}")
    print(f"  Action: {BEST_BLOCKED_UNLOCK['action']}")
    print(f"  Unlocks: {BEST_BLOCKED_UNLOCK['unlocks']}")
    print(f"  Status: {BEST_BLOCKED_UNLOCK['status']}")

    # ── 6. Queue ──
    print(f"\n  CONVERSION QUEUE")
    print(f"  {'-' * (W-4)}")
    if QUEUE:
        for i, item in enumerate(QUEUE, 1):
            print(f"  #{i}  {item}")
    else:
        print(f"  (empty — system at natural pause)")

    # ── 7. Registry Summary ──
    print(f"\n  REGISTRY")
    print(f"  {'-' * (W-4)}")
    if reg_path.exists():
        reg = json.load(open(reg_path))
        statuses = Counter(s.get("status") for s in reg["strategies"])
        total = len(reg["strategies"])
        print(f"  Total: {total}  |  " + "  ".join(f"{k}:{v}" for k, v in statuses.most_common()))

    print(f"\n{'=' * W}")


if __name__ == "__main__":
    main()
