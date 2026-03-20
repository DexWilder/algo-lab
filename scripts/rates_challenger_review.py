#!/usr/bin/env python3
"""Rates Challenger Review — compact side-by-side view of ZN probation strategies.

Shows Treasury-Rolldown-Carry-Spread and ZN-Afternoon-Reversion together
with forward evidence, contribution, overlap, and monitoring flags.

Usage:
    python3 scripts/rates_challenger_review.py              # Print report
    python3 scripts/rates_challenger_review.py --save       # Print + save to inbox
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
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_rates_challenger_review.md"

TODAY = datetime.now().strftime("%Y-%m-%d")
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")

CHALLENGERS = {
    "Treasury-Rolldown-Carry-Spread": {
        "short_name": "Treasury-Rolldown",
        "factor": "CARRY",
        "mechanism": "Monthly carry ranking across ZN/ZF/ZB tenors",
        "session": "Daily close (monthly rebalance)",
        "horizon": "Monthly",
        "bias": "Both (spread)",
        "target_trades": 8,
        "target_pf": 1.1,
    },
    "ZN-Afternoon-Reversion": {
        "short_name": "ZN-Afternoon-Rev",
        "factor": "STRUCTURAL",
        "mechanism": "Fade outsized 13:45-14:00 impulse at 14:00",
        "session": "14:00-14:25 ET",
        "horizon": "Intraday (25m)",
        "bias": "Both (short-biased)",
        "target_trades": 30,
        "target_pf": 1.1,
    },
}


def load_forward_trades():
    """Load forward trade log and filter to ZN challengers."""
    if not TRADE_LOG.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(TRADE_LOG)
    except Exception:
        return pd.DataFrame()
    if df.empty or "strategy" not in df.columns:
        return df
    return df[df["strategy"].isin(CHALLENGERS.keys())].copy()


def load_forward_signals():
    """Load signal log for ZN challengers."""
    if not SIGNAL_LOG.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(SIGNAL_LOG)
    except Exception:
        return pd.DataFrame()
    if df.empty or "strategy" not in df.columns:
        return df
    return df[df["strategy"].isin(CHALLENGERS.keys())].copy()


def load_registry_info():
    """Load registry entries for challengers."""
    if not REGISTRY_PATH.exists():
        return {}
    reg = json.load(open(REGISTRY_PATH))
    result = {}
    for s in reg.get("strategies", []):
        if s["strategy_id"] in CHALLENGERS:
            result[s["strategy_id"]] = s
    return result


def compute_stats(trades, strategy_id):
    """Compute forward stats for one strategy."""
    st = trades[trades["strategy"] == strategy_id] if not trades.empty else pd.DataFrame()
    if st.empty:
        return {
            "trades": 0, "pnl": 0, "pf": None, "wr": None,
            "long_trades": 0, "long_pnl": 0,
            "short_trades": 0, "short_pnl": 0,
            "first_trade": None, "last_trade": None,
            "days_active": 0,
        }

    n = len(st)
    pnl = st["pnl"].sum()
    winners = st[st["pnl"] > 0]["pnl"].sum()
    losers = abs(st[st["pnl"] < 0]["pnl"].sum())
    pf = round(winners / losers, 2) if losers > 0 else None
    wr = round((st["pnl"] > 0).sum() / n * 100, 1)

    longs = st[st["side"] == "long"] if "side" in st.columns else pd.DataFrame()
    shorts = st[st["side"] == "short"] if "side" in st.columns else pd.DataFrame()

    dates = pd.to_datetime(st["date"])
    first = dates.min().strftime("%Y-%m-%d") if not dates.empty else None
    last = dates.max().strftime("%Y-%m-%d") if not dates.empty else None
    days = (dates.max() - dates.min()).days + 1 if len(dates) > 1 else 1

    return {
        "trades": n,
        "pnl": round(pnl, 2),
        "pf": pf,
        "wr": wr,
        "long_trades": len(longs),
        "long_pnl": round(longs["pnl"].sum(), 2) if not longs.empty else 0,
        "short_trades": len(shorts),
        "short_pnl": round(shorts["pnl"].sum(), 2) if not shorts.empty else 0,
        "first_trade": first,
        "last_trade": last,
        "days_active": days,
    }


def compute_overlap(trades):
    """Check PnL overlap between the two challengers on same-day trades."""
    if trades.empty:
        return {"shared_days": 0, "correlation": None}

    trades = trades.copy()
    trades["date"] = pd.to_datetime(trades["date"])

    daily_pnl = trades.pivot_table(
        index="date", columns="strategy", values="pnl", aggfunc="sum"
    )

    sids = list(CHALLENGERS.keys())
    if len(sids) < 2:
        return {"shared_days": 0, "correlation": None}

    if sids[0] in daily_pnl.columns and sids[1] in daily_pnl.columns:
        both = daily_pnl.dropna(subset=sids)
        shared = len(both)
        if shared >= 5:
            corr = round(both[sids[0]].corr(both[sids[1]]), 3)
        else:
            corr = None
        return {"shared_days": shared, "correlation": corr}

    return {"shared_days": 0, "correlation": None}


def count_missing_bar_days():
    """Count recent days where ZN afternoon bars were missing (no signal possible)."""
    sig_df = load_forward_signals()
    if sig_df.empty:
        return {"zn_afternoon_no_signal_days": 0, "note": "No signal log data"}

    zn_aft = sig_df[sig_df["strategy"] == "ZN-Afternoon-Reversion"]
    if zn_aft.empty:
        return {"zn_afternoon_no_signal_days": 0, "note": "Strategy not yet in signal log"}

    total_days = len(zn_aft)
    zero_signal = (zn_aft["signals_total"] == 0).sum()
    return {
        "total_logged_days": total_days,
        "zero_signal_days": int(zero_signal),
        "note": f"{zero_signal}/{total_days} days had zero signals (expected: ~18% due to sparse bars)"
    }


def generate_report():
    """Generate the full rates challenger review."""
    trades = load_forward_trades()
    registry = load_registry_info()
    overlap = compute_overlap(trades)
    missing = count_missing_bar_days()

    lines = []
    lines.append("# Rates Challenger Review")
    lines.append(f"*Generated: {NOW}*")
    lines.append("")

    # ── Side-by-side summary ──
    lines.append("## Forward Evidence")
    lines.append("")
    lines.append("| Metric | Treasury-Rolldown | ZN-Afternoon-Rev |")
    lines.append("|--------|-------------------|------------------|")

    stats = {}
    for sid in CHALLENGERS:
        stats[sid] = compute_stats(trades, sid)

    cfg = CHALLENGERS
    sids = list(CHALLENGERS.keys())
    s0, s1 = stats[sids[0]], stats[sids[1]]
    c0, c1 = cfg[sids[0]], cfg[sids[1]]

    def fmt_pf(pf):
        return f"{pf:.2f}" if pf is not None else "—"

    def fmt_pnl(pnl):
        return f"${pnl:+,.0f}" if pnl else "$0"

    lines.append(f"| **Factor** | {c0['factor']} | {c1['factor']} |")
    lines.append(f"| **Session** | {c0['session']} | {c1['session']} |")
    lines.append(f"| **Horizon** | {c0['horizon']} | {c1['horizon']} |")
    lines.append(f"| **Bias** | {c0['bias']} | {c1['bias']} |")
    lines.append(f"| Forward trades | {s0['trades']} / {c0['target_trades']} target | {s1['trades']} / {c1['target_trades']} target |")
    lines.append(f"| Forward PnL | {fmt_pnl(s0['pnl'])} | {fmt_pnl(s1['pnl'])} |")
    lines.append(f"| Forward PF | {fmt_pf(s0['pf'])} (target >{c0['target_pf']}) | {fmt_pf(s1['pf'])} (target >{c1['target_pf']}) |")
    lines.append(f"| Win rate | {s0['wr']}% | {s1['wr']}% |" if s0['wr'] else f"| Win rate | — | — |")
    lines.append(f"| Long trades / PnL | {s0['long_trades']} / {fmt_pnl(s0['long_pnl'])} | {s1['long_trades']} / {fmt_pnl(s1['long_pnl'])} |")
    lines.append(f"| Short trades / PnL | {s0['short_trades']} / {fmt_pnl(s0['short_pnl'])} | {s1['short_trades']} / {fmt_pnl(s1['short_pnl'])} |")
    lines.append(f"| First forward trade | {s0['first_trade'] or '—'} | {s1['first_trade'] or '—'} |")
    lines.append(f"| Last forward trade | {s0['last_trade'] or '—'} | {s1['last_trade'] or '—'} |")

    # ── Short-side dependence flag for ZN-Afternoon-Reversion ──
    lines.append("")
    lines.append("## Short-Side Dependence (ZN-Afternoon-Reversion)")
    lines.append("")
    if s1["trades"] >= 5:
        short_pct = (s1["short_pnl"] / s1["pnl"] * 100) if s1["pnl"] != 0 else 0
        lines.append(f"- Short PnL share: {short_pct:.0f}% (backtest was 89%)")
        if s1["short_pnl"] <= 0 and s1["trades"] >= 10:
            lines.append(f"- **FLAG:** Short side is NOT carrying the edge in forward. Investigate.")
        elif short_pct < 60 and s1["trades"] >= 15:
            lines.append(f"- **NOTE:** Short bias weaker than backtest. Monitor.")
        else:
            lines.append(f"- Short bias consistent with backtest expectations.")
    else:
        lines.append(f"- Insufficient forward trades ({s1['trades']}) to assess short-side dependence.")

    # ── Overlap / Conflict ──
    lines.append("")
    lines.append("## Overlap / Conflict")
    lines.append("")
    lines.append(f"- Shared trading days: {overlap['shared_days']}")
    if overlap["correlation"] is not None:
        corr = overlap["correlation"]
        lines.append(f"- Daily PnL correlation: {corr:.3f}")
        if abs(corr) > 0.35:
            lines.append(f"- **FLAG:** Correlation > 0.35 — strategies may be redundant")
        else:
            lines.append(f"- Correlation within acceptable range (< 0.35)")
    else:
        lines.append(f"- Correlation: insufficient shared data")
    lines.append(f"- Mechanism overlap: NONE (carry ranking vs impulse reversion)")
    lines.append(f"- Session overlap: NONE (monthly rebalance vs 14:00-14:25 intraday)")

    # ── Missing bar / liquidity notes ──
    lines.append("")
    lines.append("## Missing-Bar / Liquidity Notes")
    lines.append("")
    lines.append(f"- {missing['note']}")
    lines.append(f"- Days with zero signals are expected (~18% of weekdays lack ZN bars at 14:00-14:25).")
    lines.append(f"- Zero-signal days are NOT system failures. They are data-sparse days where the strategy correctly stands aside.")

    # ── Regime notes ──
    lines.append("")
    lines.append("## Regime Notes")
    lines.append("")
    lines.append("| Regime | Treasury-Rolldown | ZN-Afternoon-Rev |")
    lines.append("|--------|-------------------|------------------|")
    lines.append("| HIGH_VOL | Neutral (carry spread) | **Strong** (PF 1.64 backtest) |")
    lines.append("| NORMAL | Neutral | Moderate (PF 1.13 backtest) |")
    lines.append("| LOW_VOL | Neutral | **Weak** (PF 1.04 backtest) |")
    lines.append("")
    lines.append("Treasury-Rolldown is regime-neutral (carry doesn't depend on vol).")
    lines.append("ZN-Afternoon-Reversion is vol-activated — expect quiet periods in calm markets.")

    # ── Next checkpoints ──
    lines.append("")
    lines.append("## Next Checkpoints")
    lines.append("")
    lines.append(f"| Strategy | Checkpoint | Date | Criterion |")
    lines.append(f"|----------|-----------|------|-----------|")
    lines.append(f"| Treasury-Rolldown | First rebalance signal | ~2026-03-31 | Signal generated? |")
    lines.append(f"| Treasury-Rolldown | June 1 displacement | 2026-06-01 | Forward PnL positive → displace MomIgn |")
    lines.append(f"| ZN-Afternoon-Rev | First 10 trades | ~2026-06-01 | Short bias holding? Direction? |")
    lines.append(f"| ZN-Afternoon-Rev | 30-trade review | ~2026-10-01 | PF > 1.1? Promote / continue / downgrade |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Rates Challenger Review")
    parser.add_argument("--save", action="store_true",
                        help="Save to openclaw-intake inbox")
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
