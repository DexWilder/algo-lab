#!/usr/bin/env python3
"""FQL Operator Digest — exception-only daily intelligence.

Replaces manual fql morning/summary/midweek/friday polling with a single
automated digest. Only surfaces state changes, threshold hits, and decisions.
Emits "nothing actionable" when the system is nominal.

Design:
  - Reads from existing report files and importable functions
  - Maintains state in .digest_state.json for change detection
  - Decision memos auto-generated when thresholds are hit
  - macOS notification only on ACTION/ALERT items

Usage:
    python3 scripts/operator_digest.py              # Print digest
    python3 scripts/operator_digest.py --save       # Print + save to inbox
    python3 scripts/operator_digest.py --json       # Machine-readable output
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

INBOX = Path.home() / "openclaw-intake" / "inbox"
OUTPUT_PATH = INBOX / "_daily_digest.md"
STATE_PATH = ROOT / "research" / "logs" / ".digest_state.json"
TRADE_LOG = ROOT / "logs" / "trade_log.csv"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
RECOVERY_LOG = ROOT / "research" / "logs" / "recovery_actions.log"
WATCHDOG_STATE = ROOT / "research" / "logs" / ".watchdog_state.json"

NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d")
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")
DOW = NOW.strftime("%A")


# ── Helpers ──────────────────────────────────────────────────────────────

def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def _load_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _load_state():
    return _load_json(str(STATE_PATH))


def _save_state(state):
    state["date"] = TODAY
    state["timestamp"] = TIMESTAMP
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _ensure_fresh_reports():
    """If alerts/health files are stale (>2h), regenerate them inline."""
    alerts_path = INBOX / "_alerts.md"
    health_path = INBOX / "_system_health.md"

    for path, script in [(alerts_path, "fql_alerts.py"), (health_path, "fql_doctor.py")]:
        regenerate = False
        if not path.exists():
            regenerate = True
        else:
            age_hours = (NOW.timestamp() - path.stat().st_mtime) / 3600
            if age_hours > 2:
                regenerate = True
        if regenerate:
            try:
                subprocess.run(
                    ["python3", str(ROOT / "scripts" / script), "--save"],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(ROOT)
                )
            except Exception:
                pass


# ── Health snapshot ──────────────────────────────────────────────────────

def _get_health_snapshot():
    """Get current health status for each component."""
    snapshot = {}

    # Gateway
    try:
        result = subprocess.run(
            ["curl", "-s", "--max-time", "3", "http://localhost:18789/health"],
            capture_output=True, text=True, timeout=5
        )
        snapshot["Gateway"] = "HEALTHY" if '"ok":true' in result.stdout else "DOWN"
    except Exception:
        snapshot["Gateway"] = "UNREACHABLE"

    # Claw loop
    log_dir = ROOT / "research" / "logs"
    claw_logs = sorted(log_dir.glob("claw_loop_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if claw_logs:
        age_min = (NOW.timestamp() - claw_logs[0].stat().st_mtime) / 60
        snapshot["Claw Loop"] = "HEALTHY" if age_min <= 45 else "STALE"
    else:
        snapshot["Claw Loop"] = "NO_LOGS"

    # Watchdog state (backoff = degraded)
    ws = _load_json(str(WATCHDOG_STATE))
    failures = sum(v.get("failures", 0) for v in ws.values()) if ws else 0
    snapshot["Watchdog"] = "DEGRADED" if failures > 0 else "HEALTHY"

    # Forward runner
    fwd_logs = sorted(log_dir.glob("forward_day_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if fwd_logs:
        age_hours = (NOW.timestamp() - fwd_logs[0].stat().st_mtime) / 3600
        # Only expect on weekdays
        if NOW.weekday() < 5:
            snapshot["Forward Runner"] = "HEALTHY" if age_hours <= 26 else "STALE"
        else:
            snapshot["Forward Runner"] = "HEALTHY"  # Weekend, no expectation
    else:
        snapshot["Forward Runner"] = "NO_LOGS"

    return snapshot


# ── Alert snapshot ───────────────────────────────────────────────────────

def _get_alert_snapshot():
    """Get current alert counts by level."""
    try:
        from fql_alerts import generate_alerts
        alerts = generate_alerts()
    except Exception:
        alerts = []

    counts = {"ALERT": 0, "ACTION": 0, "WARN": 0, "INFO": 0}
    for a in alerts:
        level = a.get("level", "INFO")
        counts[level] = counts.get(level, 0) + 1

    return counts, alerts


# ── Probation snapshot ───────────────────────────────────────────────────

def _get_probation_snapshot():
    """Get aging status for each probation strategy."""
    snapshot = {}
    try:
        from probation_scoreboard import compute_aging, TARGETS
    except ImportError:
        return snapshot

    reg = _load_json(str(REGISTRY_PATH))
    trades = _load_csv(str(TRADE_LOG))
    registry_map = {s["strategy_id"]: s for s in reg.get("strategies", []) if s.get("status") == "probation"}

    for sid in TARGETS:
        if sid not in registry_map:
            continue
        a = compute_aging(sid, trades, registry_map)
        st = trades[trades["strategy"] == sid] if not trades.empty and "strategy" in trades.columns else pd.DataFrame()
        snapshot[sid] = {
            "status": a["aging_status"],
            "trades": len(st),
            "pct_time": round(a["pct_time_used"]),
        }

    return snapshot


# ── Dormant inventory snapshot (fast lite-check) ─────────────────────────

def _get_dormant_snapshot():
    """Quick check: how much work is sitting idle in each pipeline stage.

    Added 2026-04-08 after discovering 24 strategies silently untested for
    2 days. This lite check runs daily in the digest so dormant work can't
    sit longer than 24h without surfacing.
    """
    snapshot = {"coded_untested": 0, "ideas_untested": 0, "harvest_unconverted": 0}

    # 1. Coded but never backtested
    strat_dir = ROOT / "strategies"
    fp_dir = ROOT / "research" / "data" / "first_pass"
    fp_names = set()
    if fp_dir.exists():
        for f in fp_dir.glob("*.json"):
            name = f.stem
            for sep in ["_2026", "_2025", "_2024", "_2023", "_2022"]:
                if sep in name:
                    name = name.split(sep)[0]
                    break
            fp_names.add(name)
    if strat_dir.exists():
        for d in strat_dir.iterdir():
            if d.is_dir() and (d / "strategy.py").exists() and d.name not in fp_names:
                snapshot["coded_untested"] += 1

    # 2. Registry ideas never tested
    reg = _load_json(str(REGISTRY_PATH))
    for s in reg.get("strategies", []):
        if s.get("status") == "idea" and not s.get("profit_factor") and not s.get("trades_6yr"):
            snapshot["ideas_untested"] += 1

    # 3. Harvest notes (uncommitted count)
    harvest_dir = Path.home() / "openclaw-intake" / "inbox" / "harvest"
    if harvest_dir.exists():
        snapshot["harvest_unconverted"] = len(list(harvest_dir.glob("*.md")))

    return snapshot


# ── Decision memos ───────────────────────────────────────────────────────

def generate_decision_memos(prev_state):
    """Generate decision memos when thresholds are crossed."""
    memos = []
    issued = set(prev_state.get("decision_memos_issued", []))
    trades = _load_csv(str(TRADE_LOG))
    reg = _load_json(str(REGISTRY_PATH))

    # 1. Strategy hits review gate
    try:
        from probation_scoreboard import compute_aging, TARGETS, compute_forward_stats
        registry_map = {s["strategy_id"]: s for s in reg.get("strategies", []) if s.get("status") == "probation"}
        for sid in TARGETS:
            if sid not in registry_map:
                continue
            a = compute_aging(sid, trades, registry_map)
            if a["aging_status"] in ("GATE_REACHED", "REVIEW_READY"):
                key = f"gate-{sid}"
                if key not in issued:
                    st = trades[trades["strategy"] == sid] if not trades.empty and "strategy" in trades.columns else pd.DataFrame()
                    n = len(st)
                    pnl = st["pnl"].sum() if n > 0 else 0
                    target = TARGETS[sid]
                    memos.append({
                        "key": key,
                        "urgency": "ACTION",
                        "title": f"{sid} reached review gate",
                        "what_changed": f"{n} trades accumulated (target: {target['trades']})",
                        "why_it_matters": f"Strategy has enough evidence for promotion decision. PnL: ${pnl:+,.0f}",
                        "options": "PROMOTE to core | EXTEND probation 8 weeks | DOWNGRADE to archive",
                    })

            # Failing threshold
            if a["aging_status"] == "FAILING":
                key = f"failing-{sid}"
                if key not in issued:
                    memos.append({
                        "key": key,
                        "urgency": "ALERT",
                        "title": f"{sid} is FAILING",
                        "what_changed": f"Evidence ratio {a['evidence_ratio']:.2f}, edge not present in forward data",
                        "why_it_matters": "Probation slot being consumed by underperformer",
                        "options": "DOWNGRADE to archive | EXTEND with conditions | INVESTIGATE signal logic",
                    })
    except ImportError:
        pass

    # 2. Claw stalls (3+ consecutive failures in watchdog)
    ws = _load_json(str(WATCHDOG_STATE))
    claw_failures = ws.get("claw_loop", {}).get("failures", 0)
    if claw_failures >= 3:
        key = "claw-stall"
        if key not in issued:
            memos.append({
                "key": key,
                "urgency": "ALERT",
                "title": "Claw control loop stalled",
                "what_changed": f"{claw_failures} consecutive failures in watchdog",
                "why_it_matters": "Discovery pipeline is offline. No new harvest notes being produced.",
                "options": "Check auth (openclaw models auth login) | Restart (fql restart) | Investigate logs",
            })

    # 3. ZN-Afternoon hits 10 trades
    if not trades.empty and "strategy" in trades.columns:
        zn = trades[trades["strategy"] == "ZN-Afternoon-Reversion"]
        if len(zn) >= 10:
            key = "zn-afternoon-10"
            if key not in issued:
                pnl = zn["pnl"].sum()
                memos.append({
                    "key": key,
                    "urgency": "REVIEW",
                    "title": "ZN-Afternoon-Reversion hit 10-trade gate",
                    "what_changed": f"10 forward trades accumulated, PnL ${pnl:+,.0f}",
                    "why_it_matters": "First meaningful sample. Short-side dependence check now possible.",
                    "options": "Run short-side analysis | Continue accumulating to 30",
                })

    # 4. VolManaged hits 30 entries
    if not trades.empty and "strategy" in trades.columns:
        vm = trades[trades["strategy"] == "VolManaged-EquityIndex-Futures"]
        if len(vm) >= 30:
            key = "volmanaged-30"
            if key not in issued:
                pnl = vm["pnl"].sum()
                memos.append({
                    "key": key,
                    "urgency": "REVIEW",
                    "title": "VolManaged-EquityIndex hit 30-entry gate",
                    "what_changed": f"30 daily weight entries, cumulative ${pnl:+,.0f}",
                    "why_it_matters": "Sharpe estimate now meaningful. Ready for contribution check.",
                    "options": "Run Sharpe check (target > 0.5) | Continue accumulating",
                })

    # 5. Energy gap persists
    gap_path = INBOX / "_portfolio_gap_dashboard.md"
    if gap_path.exists():
        gap_age = (NOW.timestamp() - gap_path.stat().st_mtime) / 86400
        try:
            text = gap_path.read_text()
            if "Energy" in text and ("GAP" in text or "0 strategies" in text.lower()):
                key = "energy-gap-persistent"
                prev_energy_cycles = prev_state.get("energy_gap_cycles", 0) + 1
                if prev_energy_cycles >= 4 and key not in issued:
                    memos.append({
                        "key": key,
                        "urgency": "REVIEW",
                        "title": "Energy gap unfilled for 4+ weekly cycles",
                        "what_changed": f"Energy slot at 0 strategies for {prev_energy_cycles} cycles",
                        "why_it_matters": "MCL settlement + HV percentile both rejected. Need fundamentally different approach.",
                        "options": "Adjust Claw targeting toward EIA/seasonal/spread ideas | Accept gap temporarily",
                    })
        except Exception:
            pass

    return memos


# ── State change detection ───────────────────────────────────────────────

def detect_state_changes(prev_state, health, alert_counts, probation, dormant=None):
    """Compare current state to previous and return changes."""
    changes = []
    dormant = dormant or {}

    # Health changes
    prev_health = prev_state.get("health", {})
    for component, status in health.items():
        prev = prev_health.get(component, "UNKNOWN")
        if prev != status:
            direction = "degraded" if status != "HEALTHY" else "recovered"
            changes.append({
                "category": "health",
                "message": f"{component}: {prev} -> {status}",
                "direction": direction,
            })

    # Alert level changes
    prev_alerts = prev_state.get("alert_counts", {})
    for level in ["ALERT", "ACTION"]:
        prev_count = prev_alerts.get(level, 0)
        curr_count = alert_counts.get(level, 0)
        if curr_count > prev_count:
            changes.append({
                "category": "alerts",
                "message": f"{level}: {prev_count} -> {curr_count} (+{curr_count - prev_count})",
                "direction": "degraded",
            })
        elif curr_count < prev_count and prev_count > 0:
            changes.append({
                "category": "alerts",
                "message": f"{level}: {prev_count} -> {curr_count} (resolved {prev_count - curr_count})",
                "direction": "recovered",
            })

    # Probation status changes
    prev_probation = prev_state.get("probation", {})
    for sid, info in probation.items():
        prev_info = prev_probation.get(sid, {})
        prev_status = prev_info.get("status", "UNKNOWN")
        if prev_status != info["status"]:
            changes.append({
                "category": "probation",
                "message": f"{sid}: {prev_status} -> {info['status']} ({info['trades']} trades)",
                "direction": "degraded" if info["status"] in ("FAILING", "STALE") else "improved",
            })

    # Recovery events today
    if Path(RECOVERY_LOG).exists():
        try:
            for line in open(RECOVERY_LOG):
                if TODAY in line and "CLEARED" in line:
                    changes.append({
                        "category": "recovery",
                        "message": line.strip().split("] ", 1)[-1] if "] " in line else line.strip(),
                        "direction": "recovered",
                    })
        except Exception:
            pass

    # Dormant inventory: flag if untested strategy backlog appears or grows.
    # Threshold: any coded-untested is actionable (should be zero after
    # twice-weekly auto-mass-screen runs). Added 2026-04-08.
    prev_dormant = prev_state.get("dormant", {})
    curr_coded_untested = dormant.get("coded_untested", 0)
    prev_coded_untested = prev_dormant.get("coded_untested", 0)
    if curr_coded_untested > 0 and curr_coded_untested != prev_coded_untested:
        changes.append({
            "category": "dormant",
            "message": (
                f"Coded untested: {prev_coded_untested} -> {curr_coded_untested} "
                f"(run: python3 research/mass_screen.py)"
            ),
            "direction": "degraded" if curr_coded_untested > prev_coded_untested else "improved",
        })
    # Harvest backlog growth
    curr_harvest = dormant.get("harvest_unconverted", 0)
    prev_harvest = prev_dormant.get("harvest_unconverted", 0)
    if curr_harvest > prev_harvest + 10:  # only flag growth of 10+
        changes.append({
            "category": "dormant",
            "message": f"Harvest backlog: {prev_harvest} -> {curr_harvest} (+{curr_harvest - prev_harvest})",
            "direction": "degraded",
        })

    return changes


# ── Digest assembly ──────────────────────────────────────────────────────

def generate_digest():
    """Assemble the daily digest."""
    _ensure_fresh_reports()

    prev_state = _load_state()
    health = _get_health_snapshot()
    alert_counts, raw_alerts = _get_alert_snapshot()
    probation = _get_probation_snapshot()
    dormant = _get_dormant_snapshot()

    changes = detect_state_changes(prev_state, health, alert_counts, probation, dormant)
    memos = generate_decision_memos(prev_state)

    # Count actionable items
    actionable = len([c for c in changes if c["direction"] == "degraded"])
    actionable += len([m for m in memos if m["urgency"] in ("ACTION", "ALERT")])

    # Build digest
    lines = []
    lines.append("# FQL Daily Digest")
    lines.append(f"*{DOW}, {TIMESTAMP}*")
    lines.append("")

    # Verdict line
    if actionable > 0:
        lines.append(f"**{actionable} item(s) need attention.**")
    else:
        lines.append("**All systems nominal. No operator action required.**")
    lines.append("")

    # State changes
    if changes:
        lines.append("## State Changes")
        lines.append("")
        for c in changes:
            icon = "!!" if c["direction"] == "degraded" else "++"
            lines.append(f"  {icon} [{c['category']}] {c['message']}")
        lines.append("")

    # Decision memos
    if memos:
        lines.append("## Decision Memos")
        lines.append("")
        for m in memos:
            lines.append(f"### [{m['urgency']}] {m['title']}")
            lines.append(f"- **What changed:** {m['what_changed']}")
            lines.append(f"- **Why it matters:** {m['why_it_matters']}")
            lines.append(f"- **Options:** {m['options']}")
            lines.append("")

    # Active alerts (only ALERT and ACTION — suppress WARN/INFO noise)
    high_alerts = [a for a in raw_alerts if a["level"] in ("ALERT", "ACTION")]
    if high_alerts and not memos:  # Don't duplicate if memos already cover it
        lines.append("## Active Alerts")
        lines.append("")
        for a in high_alerts:
            lines.append(f"  [{a['level']}] {a['message']}")
            lines.append(f"  Action: {a['action']}")
        lines.append("")

    # Compact status (always shown for reference)
    lines.append("## Status")
    lines.append("")
    health_parts = [f"{k}: {v}" for k, v in health.items()]
    lines.append(f"  Health: {' | '.join(health_parts)}")

    warn_count = alert_counts.get("WARN", 0)
    if warn_count > 0:
        lines.append(f"  Warnings: {warn_count} (see _alerts.md)")

    # Trade count
    trades = _load_csv(str(TRADE_LOG))
    if not trades.empty and "date" in trades.columns:
        today_trades = trades[trades["date"] == TODAY]
        lines.append(f"  Forward trades: {len(trades)} total, {len(today_trades)} today")

    # Dormant inventory (persistent line — visible every day)
    d = dormant
    dormant_parts = []
    if d.get("coded_untested", 0) > 0:
        dormant_parts.append(f"coded untested: {d['coded_untested']}")
    if d.get("ideas_untested", 0) > 0:
        dormant_parts.append(f"registry ideas: {d['ideas_untested']}")
    dormant_parts.append(f"harvest notes: {d.get('harvest_unconverted', 0)}")
    lines.append(f"  Dormant: {' | '.join(dormant_parts)}")

    lines.append("")
    lines.append("---")
    lines.append("*Full reports: _alerts.md, _operator_brief.md, _probation_scoreboard.md, _portfolio_gap_dashboard.md*")

    # Update state for next run
    new_state = {
        "health": health,
        "alert_counts": alert_counts,
        "probation": probation,
        "dormant": dormant,
        "decision_memos_issued": list(set(
            prev_state.get("decision_memos_issued", []) + [m["key"] for m in memos]
        )),
        "energy_gap_cycles": prev_state.get("energy_gap_cycles", 0),
    }

    # Track energy gap persistence
    gap_path = INBOX / "_portfolio_gap_dashboard.md"
    if gap_path.exists():
        try:
            text = gap_path.read_text()
            if "Energy" in text and ("GAP" in text or "0 strategies" in text.lower()):
                new_state["energy_gap_cycles"] = prev_state.get("energy_gap_cycles", 0) + 1
            else:
                new_state["energy_gap_cycles"] = 0
        except Exception:
            pass

    _save_state(new_state)

    return "\n".join(lines), actionable


def send_notification(actionable):
    """macOS notification only when there are actionable items."""
    if actionable > 0:
        body = f"{actionable} item(s) need attention"
        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{body}" with title "FQL Digest"'
            ], capture_output=True, timeout=5)
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="FQL Operator Digest")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    digest, actionable = generate_digest()

    if args.json:
        state = _load_state()
        print(json.dumps({"actionable": actionable, "state": state}, indent=2))
    else:
        print(digest)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(digest)
        send_notification(actionable)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
