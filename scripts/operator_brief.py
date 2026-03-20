#!/usr/bin/env python3
"""FQL Operator Brief — single daily front page.

Reads from the existing report stack and compresses into the most
decision-useful points. This is the one document to read each day.

Usage:
    python3 scripts/operator_brief.py              # Print
    python3 scripts/operator_brief.py --save       # Print + save to inbox
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

INBOX = Path.home() / "openclaw-intake" / "inbox"
OUTPUT_PATH = INBOX / "_operator_brief.md"

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
SIGNAL_LOG = ROOT / "logs" / "signal_log.csv"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
RECOVERY_LOG = ROOT / "research" / "logs" / "recovery_actions.log"
WATCHDOG_STATE = ROOT / "research" / "logs" / ".watchdog_state.json"
ACCOUNT_STATE = ROOT / "state" / "account_state.json"

NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d")
DOW = NOW.strftime("%A")
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")


# ── Data loaders ──

def _read_inbox(filename):
    p = INBOX / filename
    return p.read_text() if p.exists() else None


def _load_json(path):
    if not Path(path).exists():
        return {}
    try:
        return json.load(open(path))
    except Exception:
        return {}


def _load_csv(path):
    if not Path(path).exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


# ── Section builders ──

def section_health():
    """System health: gateway, claw loop, services."""
    lines = []

    # Gateway
    import subprocess
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "3", "http://localhost:18789/health"],
            capture_output=True, text=True, timeout=5
        )
        if '"ok":true' in result.stdout:
            gw = "OK"
        else:
            gw = "**DOWN**"
    except Exception:
        gw = "**UNREACHABLE**"

    # Claw loop freshness
    log_dir = ROOT / "research" / "logs"
    claw_logs = sorted(log_dir.glob("claw_loop_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if claw_logs:
        age_min = int((NOW.timestamp() - claw_logs[0].stat().st_mtime) / 60)
        claw = f"OK ({age_min}m ago)" if age_min <= 45 else f"**STALE ({age_min}m)**"
    else:
        claw = "**NO LOGS**"

    # Recovery actions today
    recovery_today = 0
    if Path(RECOVERY_LOG).exists():
        try:
            for line in open(RECOVERY_LOG):
                if TODAY in line:
                    recovery_today += 1
        except Exception:
            pass

    # Backoff state
    state = _load_json(WATCHDOG_STATE)
    failures = sum(v.get("failures", 0) for v in state.values()) if state else 0

    lines.append("## System Health")
    lines.append("")
    lines.append(f"- Gateway: {gw}")
    lines.append(f"- Claw loop: {claw}")
    lines.append(f"- Recovery actions today: {recovery_today}")
    if failures > 0:
        components = ", ".join(f"{k}={v['failures']}" for k, v in state.items() if v.get("failures", 0) > 0)
        lines.append(f"- **Backoff active:** {components}")
    else:
        lines.append(f"- Consecutive failures: 0")

    return lines


def section_forward_evidence():
    """New forward evidence since yesterday."""
    lines = []
    trades = _load_csv(TRADE_LOG)

    lines.append("## Forward Evidence")
    lines.append("")

    if trades.empty:
        lines.append("No forward trades recorded yet.")
        return lines

    trades["date"] = pd.to_datetime(trades["date"])
    today_trades = trades[trades["date"].dt.strftime("%Y-%m-%d") == TODAY]
    yesterday = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday_trades = trades[trades["date"].dt.strftime("%Y-%m-%d") == yesterday]

    recent = pd.concat([today_trades, yesterday_trades])
    if recent.empty:
        lines.append("No new trades today or yesterday.")
    else:
        lines.append(f"Last 24h: {len(recent)} trades, ${recent['pnl'].sum():+,.0f}")
        for _, t in recent.iterrows():
            lines.append(f"  - {t['strategy']}: {t.get('side','?')} on {t['asset']}, ${t['pnl']:+,.0f}")

    # Account state
    acct = _load_json(ACCOUNT_STATE)
    if acct:
        equity = acct.get("equity", 0)
        hwm = acct.get("equity_hwm", 0)
        dd = hwm - equity
        lines.append("")
        lines.append(f"Equity: ${equity:,.0f} | DD from HWM: ${dd:,.0f} | Cumulative PnL: ${acct.get('cumulative_pnl', 0):+,.0f}")

    return lines


def section_probation():
    """Probation movement — who's progressing, who's stuck."""
    lines = []
    lines.append("## Probation & Challengers")
    lines.append("")

    reg = _load_json(REGISTRY_PATH)
    if not reg:
        lines.append("Registry unavailable.")
        return lines

    trades = _load_csv(TRADE_LOG)

    # Import aging logic from scoreboard
    sys.path.insert(0, str(ROOT / "scripts"))
    from probation_scoreboard import compute_aging, TARGETS, EXPECTED_FREQ

    probation = [s for s in reg.get("strategies", []) if s.get("status") == "probation"]
    registry_map = {s["strategy_id"]: s for s in probation}

    # Categorize by aging status
    on_track = []
    too_early = []
    healthy_slow = []
    under_evidenced = []
    stale = []
    failing = []
    gate = []

    for s in probation:
        sid = s["strategy_id"]
        a = compute_aging(sid, trades, registry_map)
        st = trades[trades["strategy"] == sid] if not trades.empty and "strategy" in trades.columns else pd.DataFrame()
        n = len(st)
        pnl = st["pnl"].sum() if n > 0 else 0

        label = f"{sid}: {n} trades" + (f", ${pnl:+,.0f}" if n > 0 else "") + f" ({a['weeks_in_probation']:.0f}w/{a['max_weeks']}w)"

        status = a["aging_status"]
        if status == "TOO_EARLY":
            too_early.append(label)
        elif status == "HEALTHY_SLOW":
            healthy_slow.append(label)
        elif status == "ON_TRACK":
            on_track.append(label)
        elif status == "UNDER_EVIDENCED":
            under_evidenced.append(label)
        elif status == "STALE":
            stale.append(label)
        elif status == "FAILING":
            failing.append(label)
        elif status in ("GATE_REACHED", "REVIEW_READY"):
            gate.append(label)

    # Print in urgency order
    if failing:
        lines.append(f"**FAILING ({len(failing)}):** enough evidence, edge not present")
        for f in failing:
            lines.append(f"  - {f}")
    if stale:
        lines.append(f"**STALE ({len(stale)}):** should have trades by now but doesn't")
        for s in stale:
            lines.append(f"  - {s}")
    if gate:
        lines.append(f"**GATE REACHED ({len(gate)}):** ready for promote/downgrade decision")
        for g in gate:
            lines.append(f"  - {g}")
    if under_evidenced:
        lines.append(f"**Under-evidenced ({len(under_evidenced)}):** fewer trades than expected")
        for u in under_evidenced:
            lines.append(f"  - {u}")
    if on_track:
        lines.append(f"**On track ({len(on_track)}):** evidence accumulating as expected")
        for o in on_track:
            lines.append(f"  - {o}")
    if healthy_slow:
        lines.append(f"**Healthy/slow ({len(healthy_slow)}):** sparse cadence, patience required")
        for h in healthy_slow:
            lines.append(f"  - {h}")
    if too_early:
        lines.append(f"**Too early ({len(too_early)}):** entered recently, no judgment yet")
        for t in too_early:
            lines.append(f"  - {t}")

    # Flagged: vitality/half-life concerns (separate from aging)
    flagged = []
    for s in probation:
        sid = s["strategy_id"]
        flags = []
        hl = s.get("half_life_status")
        if hl in ("DECAYING", "ARCHIVE_CANDIDATE"):
            flags.append(f"half-life {hl}")
        vit = s.get("edge_vitality_tier")
        if vit in ("FADING", "DEAD"):
            flags.append(f"vitality {vit}")
        if flags:
            flagged.append(f"{sid}: {', '.join(flags)}")

    if flagged:
        lines.append(f"**Edge health flags ({len(flagged)}):**")
        for f in flagged:
            lines.append(f"  - {f}")

    return lines


def section_attention():
    """Today's attention priority."""
    lines = []
    lines.append("## Today's Attention")
    lines.append("")

    # Day-specific guidance
    if DOW == "Friday":
        lines.append("- **Friday review:** Check weekly scorecard, Claw cluster report,")
        lines.append("  portfolio gap dashboard refresh")
    elif DOW == "Monday":
        lines.append("- **Monday intake:** Scan Claw harvest outputs, dedupe, tag, accept/reject")

    lines.append("- **VolManaged-Equity:** Check that daily weight-adjusted positions are")
    lines.append("  generating. First days confirm signal replication in forward runner.")
    lines.append("- **ZN-Afternoon-Rev:** Expect ~1 trade this week. Zero is normal;")
    lines.append("  check signal log for afternoon ZN bar availability.")
    lines.append("- **Treasury-Rolldown:** Leave alone until ~March 31 (next monthly rebalance).")

    return lines


def section_decisions():
    """Human decisions needed."""
    lines = []
    lines.append("## Decisions Needed")
    lines.append("")

    decisions = []

    # Check for strategies near promotion gate
    reg = _load_json(REGISTRY_PATH)
    trades = _load_csv(TRADE_LOG)
    if reg and not trades.empty and "strategy" in trades.columns:
        for s in reg.get("strategies", []):
            if s.get("status") != "probation":
                continue
            sid = s["strategy_id"]
            st = trades[trades["strategy"] == sid]
            n = len(st)
            # Near gate?
            targets = {"DailyTrend-MGC-Long": 15, "MomPB-6J-Long-US": 30,
                       "FXBreak-6J-Short-London": 50, "NoiseBoundary-MNQ-Long": 30,
                       "ZN-Afternoon-Reversion": 30, "VolManaged-EquityIndex-Futures": 30}
            target = targets.get(sid, 30)
            if n >= target * 0.8 and n > 0:
                pnl = st["pnl"].sum()
                decisions.append(f"**{sid}:** {n}/{target} trades — approaching review gate (PnL ${pnl:+,.0f})")

    # Check for stale strategies (no trades in 2+ weeks for intraday)
    if reg and not trades.empty:
        trades["date"] = pd.to_datetime(trades["date"])
        for s in reg.get("strategies", []):
            if s.get("status") != "probation":
                continue
            sid = s["strategy_id"]
            ec = s.get("event_cadence", {})
            if ec.get("cadence_class") == "sparse_event":
                continue  # Don't flag sparse event strategies
            if sid in ("Treasury-Rolldown-Carry-Spread",):
                continue  # Monthly strategy
            st = trades[trades["strategy"] == sid]
            if not st.empty:
                last = st["date"].max()
                gap = (NOW - last).days
                if gap > 14:
                    decisions.append(f"**{sid}:** No trades in {gap} days — investigate")

    # Harvest backlog
    harvest_dir = INBOX / "harvest"
    if harvest_dir.exists():
        count = len(list(harvest_dir.glob("*.md")))
        if count > 40:
            decisions.append(f"**Harvest backlog:** {count} notes pending — intake needed")

    if decisions:
        for d in decisions:
            lines.append(f"- {d}")
    else:
        lines.append("- None requiring immediate action.")

    return lines


def generate_report():
    lines = []
    lines.append("# FQL Operator Brief")
    lines.append(f"*{DOW}, {TIMESTAMP}*")
    lines.append("")

    for section_fn in [section_health, section_forward_evidence, section_probation,
                       section_attention, section_decisions]:
        lines.extend(section_fn())
        lines.append("")

    lines.append("---")
    lines.append("*Detail reports: _probation_scoreboard.md, _challenger_stack_review.md,*")
    lines.append("*_rates_challenger_review.md, _portfolio_gap_dashboard.md, _recovery_status.md*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Operator Brief")
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
