#!/usr/bin/env python3
"""Challenger Stack Review — decision surface for the 3 newest probation entries.

Compact side-by-side view of Treasury-Rolldown, ZN-Afternoon-Reversion,
and VolManaged-EquityIndex with decision priority, portfolio additivity,
and operator attention recommendations.

Usage:
    python3 scripts/challenger_stack_review.py              # Print report
    python3 scripts/challenger_stack_review.py --save       # Print + save to inbox
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
SIGNAL_LOG = ROOT / "logs" / "signal_log.csv"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_challenger_stack_review.md"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

STACK = [
    {
        "sid": "Treasury-Rolldown-Carry-Spread",
        "short": "Treasury-Rolldown",
        "factor": "CARRY",
        "asset": "ZN (3-tenor spread)",
        "session": "Daily close (monthly rebal)",
        "horizon": "Monthly",
        "direction": "Both (spread)",
        "target_trades": 8,
        "target_metric": "PF > 1.1",
        "expected_velocity": "~2 ZN-leg trades/year; 12 spread observations/year",
        "time_to_gate": "~3 years (ZN-leg) or June 1 displacement via spread PnL",
        "fragility": [
            "PF 1.11 is marginal — thin edge",
            "2025-2026 segment was negative (-$15K equal-notional)",
            "Slowest evidence of any challenger",
        ],
        "portfolio_value": [
            "Fills CARRY gap (was 0 active)",
            "Fills Rates asset gap",
            "Near-zero correlation with equity portfolio",
            "June 1 displacement target: MomIgn-M2K-Short",
        ],
    },
    {
        "sid": "ZN-Afternoon-Reversion",
        "short": "ZN-Afternoon-Rev",
        "factor": "STRUCTURAL",
        "asset": "ZN",
        "session": "14:00-14:25 ET",
        "horizon": "Intraday (25m)",
        "direction": "Both (short-biased, 89% PnL)",
        "target_trades": 30,
        "target_metric": "PF > 1.1",
        "expected_velocity": "~3-4 trades/month",
        "time_to_gate": "~8 months",
        "fragility": [
            "HIGH_VOL dependent (PF 1.64 high-vol, 1.04 low-vol)",
            "Window-specific: ±15m shift kills edge",
            "2021 was a losing year (low-vol regime)",
            "~18% of weekdays excluded (sparse bars)",
        ],
        "portfolio_value": [
            "Afternoon session (zero morning overlap)",
            "Short-biased (helps 2.7:1 long ratio)",
            "Rates-native structural edge",
            "Discovered via falsification — mechanism validated",
        ],
    },
    {
        "sid": "VolManaged-EquityIndex-Futures",
        "short": "VolManaged-Equity",
        "factor": "VOLATILITY",
        "asset": "MES",
        "session": "Daily close (always-in)",
        "horizon": "Daily (continuous hold)",
        "direction": "Long only",
        "target_trades": 30,
        "target_metric": "Sharpe > 0.5",
        "expected_velocity": "~21 data points/month (every trading day)",
        "time_to_gate": "~6 weeks",
        "fragility": [
            "Long-only adds to portfolio long bias",
            "Crisis DD risk (COVID, rate hikes)",
            "MICRO/REDUCED only until crisis DD confirmed acceptable",
        ],
        "portfolio_value": [
            "Fills VOLATILITY gap (was 0 active)",
            "Unique mechanism (sizing regime, not signal timing)",
            "Rubric 22 (highest in system)",
            "Marginal Sharpe +0.089, portfolio corr 0.088",
        ],
    },
]


def load_forward_stats():
    """Load forward trade/signal data for all 3 challengers."""
    stats = {}
    trades = pd.DataFrame()
    signals = pd.DataFrame()

    if TRADE_LOG.exists():
        try:
            trades = pd.read_csv(TRADE_LOG)
            trades["date"] = pd.to_datetime(trades["date"])
        except Exception:
            pass

    if SIGNAL_LOG.exists():
        try:
            signals = pd.read_csv(SIGNAL_LOG)
            signals["date"] = pd.to_datetime(signals["date"])
        except Exception:
            pass

    for entry in STACK:
        sid = entry["sid"]
        st = trades[trades["strategy"] == sid] if not trades.empty else pd.DataFrame()
        sg = signals[signals["strategy"] == sid] if not signals.empty else pd.DataFrame()

        n = len(st)
        pnl = st["pnl"].sum() if n > 0 else 0
        w = st[st["pnl"] > 0]["pnl"].sum() if n > 0 else 0
        l = abs(st[st["pnl"] < 0]["pnl"].sum()) if n > 0 else 0
        pf = round(w / l, 2) if l > 0 else None
        maxdd = 0
        if n > 0:
            eq = st["pnl"].cumsum()
            maxdd = round((eq.cummax() - eq).max(), 2)

        # Long/short split
        longs = st[st.get("side", pd.Series()) == "long"] if "side" in st.columns and n > 0 else pd.DataFrame()
        shorts = st[st.get("side", pd.Series()) == "short"] if "side" in st.columns and n > 0 else pd.DataFrame()

        # Signal days
        signal_days = int((sg["signals_total"] > 0).sum()) if not sg.empty and "signals_total" in sg.columns else 0
        logged_days = len(sg)

        stats[sid] = {
            "trades": n, "pnl": round(pnl, 2), "pf": pf, "maxdd": maxdd,
            "long_n": len(longs), "short_n": len(shorts),
            "long_pnl": round(longs["pnl"].sum(), 2) if not longs.empty else 0,
            "short_pnl": round(shorts["pnl"].sum(), 2) if not shorts.empty else 0,
            "signal_days": signal_days, "logged_days": logged_days,
        }

    return stats


def generate_report():
    stats = load_forward_stats()

    lines = []
    lines.append("# Challenger Stack Review")
    lines.append(f"*Generated: {NOW}*")
    lines.append(f"*Tracking: 3 newest probation entries (all entered 2026-03-20)*")

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: SIDE-BY-SIDE
    # ═══════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Side-by-Side")
    lines.append("")

    headers = ["Dimension"] + [e["short"] for e in STACK]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    rows = [
        ("Factor", [e["factor"] for e in STACK]),
        ("Asset", [e["asset"] for e in STACK]),
        ("Session", [e["session"] for e in STACK]),
        ("Horizon", [e["horizon"] for e in STACK]),
        ("Direction", [e["direction"] for e in STACK]),
        ("Target", [e["target_metric"] for e in STACK]),
        ("Evidence velocity", [e["expected_velocity"] for e in STACK]),
        ("Time to gate", [e["time_to_gate"] for e in STACK]),
    ]

    # Forward evidence
    fwd_trades = []
    fwd_pnl = []
    fwd_pf = []
    for e in STACK:
        s = stats[e["sid"]]
        fwd_trades.append(f"{s['trades']} / {e['target_trades']}")
        fwd_pnl.append(f"${s['pnl']:+,.0f}" if s['trades'] > 0 else "—")
        fwd_pf.append(f"{s['pf']:.2f}" if s['pf'] is not None else "—")

    rows.append(("**Fwd trades / target**", fwd_trades))
    rows.append(("**Fwd PnL**", fwd_pnl))
    rows.append(("**Fwd PF**", fwd_pf))

    for label, values in rows:
        lines.append(f"| {label} | " + " | ".join(str(v) for v in values) + " |")

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: DECISION PRIORITY
    # ═══════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Decision Priority")
    lines.append("")

    # Fastest to learn
    lines.append("**Fastest to learn:** VolManaged-Equity")
    lines.append("- 21 data points/month — will reach 30-day gate in ~6 weeks")
    lines.append("- First strategy where we can make a promote/downgrade call")
    lines.append("")

    # Highest expected portfolio value
    lines.append("**Highest expected portfolio value:** Treasury-Rolldown")
    lines.append("- Fills 2 gaps simultaneously (CARRY + Rates)")
    lines.append("- June 1 displacement target makes it the highest-stakes decision")
    lines.append("- But: slowest evidence, so judgment will be thin at decision time")
    lines.append("")

    # Highest fragility risk
    s_zn = stats["ZN-Afternoon-Reversion"]
    lines.append("**Highest fragility risk:** ZN-Afternoon-Reversion")
    lines.append("- Window-specific (±15m kills edge)")
    lines.append("- HIGH_VOL dependent (PF 1.04 in low-vol regimes)")
    lines.append("- Most likely to degrade if market conditions change")
    lines.append("")

    # Slowest evidence
    lines.append("**Slowest evidence accumulation:** Treasury-Rolldown")
    lines.append("- ~2 ZN-leg rank changes per year")
    lines.append("- June 1 displacement decision will rely heavily on spread-level")
    lines.append("  monthly returns, not forward-runner trade count")

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: PORTFOLIO ADDITIVITY
    # ═══════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Portfolio Additivity")
    lines.append("")

    lines.append("| Strategy | Current Status | What Changes the Judgment |")
    lines.append("|----------|---------------|--------------------------|")

    for e in STACK:
        sid = e["sid"]
        s = stats[sid]

        if s["trades"] == 0:
            status = "UNKNOWN (no forward data)"
            trigger = "First forward trades — any PnL data starts the clock"
        elif s["trades"] < 10:
            status = "TOO EARLY"
            trigger = f"{10 - s['trades']} more trades to form initial judgment"
        else:
            if s["pnl"] > 0:
                status = "LIKELY ADDITIVE"
            else:
                status = "POTENTIALLY DILUTIVE"
            trigger = "Correlation check with portfolio at 20+ trades"

        lines.append(f"| {e['short']:<20s} | {status} | {trigger} |")

    lines.append("")
    lines.append("### Additivity Evidence Needed")
    lines.append("")
    lines.append("**Treasury-Rolldown:** Needs 3 monthly spread returns (Mar-May).")
    lines.append("If net positive → strong additivity case for June 1 displacement.")
    lines.append("If net negative → displacement weakens but gap-fill value persists.")
    lines.append("")
    lines.append("**ZN-Afternoon-Rev:** Needs 10+ forward trades to check short-side")
    lines.append("dependence. If shorts carry >60% of forward PnL → backtest thesis holds.")
    lines.append("If shorts flat/negative → strategy loses its primary portfolio value")
    lines.append("(short-bias diversification).")
    lines.append("")
    lines.append("**VolManaged-Equity:** Needs 30 forward days to compare vol-managed")
    lines.append("Sharpe vs unscaled baseline. If Sharpe improvement <20% → the")
    lines.append("vol-scaling mechanism is not replicating. If DD clusters with portfolio")
    lines.append("DD on same days → long-bias thesis fails.")

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: RECOMMENDATIONS
    # ═══════════════════════════════════════════════════════════
    lines.append("")
    lines.append("## Operator Attention This Week")
    lines.append("")

    lines.append("### Watch closely")
    lines.append("- **VolManaged-Equity:** Fastest feedback loop. Check daily that")
    lines.append("  the strategy is generating weight-adjusted positions. First few")
    lines.append("  days confirm the signal is replicating correctly in the forward")
    lines.append("  runner — a miscalculation here compounds daily.")
    lines.append("")
    lines.append("### Check weekly")
    lines.append("- **ZN-Afternoon-Rev:** Should generate ~1 trade/week. Confirm")
    lines.append("  signals are firing on days with sufficient afternoon ZN bars.")
    lines.append("  A full week with zero signals is normal; two weeks is a flag.")
    lines.append("")
    lines.append("### Leave alone until checkpoint")
    lines.append("- **Treasury-Rolldown:** Monthly rebalance. Next signal opportunity")
    lines.append("  is ~March 31. Nothing to monitor before then except confirming")
    lines.append("  the strategy loaded correctly (already verified).")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Challenger Stack Review")
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
