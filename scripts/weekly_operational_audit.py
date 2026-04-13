#!/usr/bin/env python3
"""FQL Weekly Operational Audit — management-layer bottleneck review.

Answers: where is the system stuck, drifting, or underperforming?

Runs Friday in the weekly pipeline alongside throughput_audit.py.
Not a dashboard — a diagnostic that surfaces the top 3 actions by leverage.

Sections:
  1. Harvest funnel counts + blocker breakdown
  2. Source productivity by lane
  3. Idle inventory with no next step
  4. Tooling not wired into automation
  5. Derived diagnostic flags
  6. Verifiable assertions (nothing uncategorized, nothing orphaned)
  7. Ranked top 3 actions

Usage:
    python3 scripts/weekly_operational_audit.py              # Print
    python3 scripts/weekly_operational_audit.py --save       # Print + save
"""

import argparse
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

INBOX = Path.home() / "openclaw-intake" / "inbox"
HARVEST_DIR = INBOX / "harvest"
REVIEWED_DIR = Path.home() / "openclaw-intake" / "reviewed"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
TRADE_LOG = ROOT / "logs" / "trade_log.csv"
OUTPUT_PATH = INBOX / "_weekly_operational_audit.md"

NOW = datetime.now()
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")


def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


# ── 1. Harvest funnel ────────────────────────────────────────────────────

def audit_harvest_funnel():
    """Count notes by blocker status and type."""
    clean = 0
    soft_blocked = 0
    hard_blocked = 0
    blocker_types = Counter()
    factor_counts = Counter()
    total = 0

    for d in [HARVEST_DIR, REVIEWED_DIR]:
        if not d.exists():
            continue
        for f in d.glob("*.md"):
            total += 1
            try:
                text = f.read_text()
                blocker = ""
                factor = ""
                for line in text.split("\n"):
                    if line.startswith("- blocker:"):
                        blocker = line.split(":", 1)[-1].strip().lower()
                    if line.startswith("- factor fit:"):
                        factor = line.split(":", 1)[-1].strip()

                if factor:
                    factor_counts[factor] += 1

                if blocker in ("", "none", "no", "n/a"):
                    clean += 1
                elif any(b in blocker for b in ["cftc", "cot ", "vix9d", "implied vol",
                                                 "options", "oecd", "ppp", "auction imbalance",
                                                 "order book", "when-issued", "bid-to-cover"]):
                    hard_blocked += 1
                    # Categorize
                    if "cftc" in blocker or "cot" in blocker:
                        blocker_types["CFTC/positioning data"] += 1
                    elif "vix" in blocker or "implied" in blocker:
                        blocker_types["VIX/implied vol data"] += 1
                    elif "auction" in blocker or "when-issued" in blocker:
                        blocker_types["auction/event data"] += 1
                    elif "ppp" in blocker or "oecd" in blocker:
                        blocker_types["macro data (PPP/CPI)"] += 1
                    else:
                        blocker_types["other external data"] += 1
                else:
                    soft_blocked += 1
                    blocker_types["soft (spec/definition needed)"] += 1
            except Exception:
                pass

    return {
        "total": total,
        "clean": clean,
        "soft_blocked": soft_blocked,
        "hard_blocked": hard_blocked,
        "blocker_types": dict(blocker_types.most_common()),
        "factor_counts": dict(factor_counts.most_common()),
    }


# ── 2. Source productivity ───────────────────────────────────────────────

def audit_source_productivity():
    """How many leads per source, pickup rate, note conversion."""
    manifest_path = INBOX / "source_leads" / "_manifest.json"
    if not manifest_path.exists():
        return {"runs": 0}

    data = _load_json(str(manifest_path))
    runs = data.get("runs", [])
    if not runs:
        return {"runs": 0}

    last = runs[-1]
    lifecycle = data.get("lifecycle", {})
    picked = sum(1 for v in lifecycle.values() if v.get("picked_up"))

    return {
        "runs": len(runs),
        "last_run": last.get("timestamp", "?")[:16],
        "github": last.get("github_leads", 0),
        "reddit": last.get("reddit_leads", 0),
        "youtube": last.get("youtube_leads", 0),
        "blog": last.get("blog_leads", 0),
        "digest": last.get("digest_leads", 0),
        "total_leads": last.get("total", 0),
        "picked_up": picked,
    }


# ── 3. Idle inventory ───────────────────────────────────────────────────

def audit_idle_inventory():
    """Strategies/items with no defined next step."""
    reg = _load_json(str(REGISTRY_PATH))
    idle = []

    for s in reg.get("strategies", []):
        status = s.get("status", "")
        sid = s["strategy_id"]

        # Watch/testing with no trigger
        if status in ("watch", "testing"):
            has_trigger = bool(s.get("salvage_lane") or s.get("review_date") or
                             s.get("next_action") or s.get("test_date"))
            if not has_trigger:
                idle.append({"id": sid, "status": status, "issue": "no next trigger"})

        # Monitor with no review date
        if status == "monitor":
            if not s.get("test_date") and not s.get("salvage_lane"):
                idle.append({"id": sid, "status": status, "issue": "monitor with no review plan"})

    return idle


# ── 4. Unwired tooling ──────────────────────────────────────────────────

def audit_unwired_tooling():
    """Scripts/commands that exist but aren't called by any automation."""
    scripts_dir = ROOT / "scripts"
    daily_sh = (scripts_dir / "run_fql_daily.sh").read_text() if (scripts_dir / "run_fql_daily.sh").exists() else ""
    weekly_sh = (scripts_dir / "run_fql_weekly.sh").read_text() if (scripts_dir / "run_fql_weekly.sh").exists() else ""
    twice_sh = (scripts_dir / "run_fql_twice_weekly.sh").read_text() if (scripts_dir / "run_fql_twice_weekly.sh").exists() else ""
    all_automation = daily_sh + weekly_sh + twice_sh

    unwired = []
    for f in scripts_dir.glob("*.py"):
        name = f.stem
        # Skip if it's a helper/utility, not an independent tool
        if name.startswith("_") or name in ("lead_scorer", "component_search", "monitor"):
            continue
        if name not in all_automation and f"scripts/{name}" not in all_automation:
            unwired.append(name)

    return unwired


# ── 5. Derived diagnostic flags ─────────────────────────────────────────

def compute_diagnostic_flags(harvest, source, idle):
    """Higher-level flags that combine multiple signals."""
    flags = []

    # High harvest productivity but low testability
    if harvest["total"] > 100 and harvest["clean"] < 10:
        ratio = harvest["clean"] / harvest["total"] * 100
        flags.append(f"HIGH HARVEST / LOW TESTABILITY: {harvest['total']} notes but only {harvest['clean']} clean ({ratio:.0f}%)")

    # Inventory accumulating in limbo
    if len(idle) > 5:
        flags.append(f"LIMBO ACCUMULATION: {len(idle)} strategies in watch/testing/monitor with no next step")

    # Data bottleneck larger than strategy bottleneck
    if harvest["hard_blocked"] > harvest["clean"] * 5:
        flags.append(f"DATA BOTTLENECK: {harvest['hard_blocked']} hard-blocked notes vs {harvest['clean']} clean — data limits, not ideas, are the constraint")

    # Automation exists but isn't compounding
    # (detected if source helpers run but pickup rate is 0)
    if source.get("total_leads", 0) > 30 and source.get("picked_up", 0) == 0:
        flags.append(f"SOURCE PIPELINE STALLED: {source['total_leads']} leads fetched but 0 picked up by Claw")

    return flags


# ── 6. Verifiable assertions ────────────────────────────────────────────

def check_assertions():
    """Explicit checks that nothing is orphaned, uncategorized, or drifting."""
    reg = _load_json(str(REGISTRY_PATH))
    assertions = []

    # 1. No uncategorized strategy states
    valid_states = {"idea", "testing", "watch", "monitor", "probation", "core",
                    "rejected", "archived", "broken"}
    for s in reg.get("strategies", []):
        status = s.get("status", "")
        if status not in valid_states:
            assertions.append(f"FAIL: {s['strategy_id']} has unknown status '{status}'")

    # 2. No probation without controller_action
    for s in reg.get("strategies", []):
        if s.get("status") == "probation" and not s.get("controller_action"):
            assertions.append(f"FAIL: {s['strategy_id']} is probation but has no controller_action")

    # 3. Queued components have routing tags
    # (notes tagged as "next phase" in disposition should have a mechanism for review)
    # This is a soft check — we note it but don't fail

    # 4. No strategy code without first_pass AND not BROKEN
    strat_dir = ROOT / "strategies"
    fp_dir = ROOT / "research" / "data" / "first_pass"
    fp_names = set()
    for f in fp_dir.glob("*.json"):
        name = f.stem
        for sep in ["_2026", "_2025", "_2024"]:
            if sep in name:
                name = name.split(sep)[0]
                break
        fp_names.add(name)

    for d in strat_dir.iterdir():
        if d.is_dir() and (d / "strategy.py").exists() and d.name not in fp_names:
            try:
                if "\nBROKEN = True" in (d / "strategy.py").read_text():
                    continue
            except Exception:
                pass
            assertions.append(f"FAIL: {d.name} has code but no first_pass result")

    if not assertions:
        assertions.append("PASS: all strategies categorized, all probation has controller_action, all code has first_pass or BROKEN flag")

    return assertions


# ── 7. Ranked actions ────────────────────────────────────────────────────

def rank_actions(harvest, source, idle, flags, assertions):
    """Produce top 3 ranked actions by leverage."""
    actions = []

    # Data bottleneck
    if harvest["hard_blocked"] > 20:
        actions.append((90, f"DATA: {harvest['hard_blocked']} notes blocked by missing data feeds. Accept this limitation or plan data expansion phase."))

    # Limbo strategies
    if len(idle) > 0:
        actions.append((80, f"LIMBO: {len(idle)} strategies in watch/testing/monitor with no next step. Archive or define trigger."))

    # Source pipeline
    if source.get("picked_up", 0) == 0 and source.get("total_leads", 0) > 0:
        actions.append((75, "SOURCE: leads being fetched but not picked up by Claw. Check task instructions."))

    # Testability ratio
    if harvest["total"] > 0 and harvest["clean"] / harvest["total"] < 0.05:
        actions.append((70, f"TESTABILITY: only {harvest['clean']}/{harvest['total']} notes are clean. Claw retargeting needed."))

    # Assertion failures
    fails = [a for a in assertions if a.startswith("FAIL")]
    if fails:
        actions.append((95, f"ASSERTIONS: {len(fails)} assertion failure(s) — investigate immediately"))

    # Forward evidence pace
    if TRADE_LOG.exists():
        trades = pd.read_csv(TRADE_LOG)
        xb = trades[trades["strategy"].str.contains("XB-ORB", na=False)] if "strategy" in trades.columns else pd.DataFrame()
        if len(xb) < 5:
            actions.append((60, f"FORWARD: only {len(xb)} XB-ORB trades so far. Patience required — accumulating."))

    actions.sort(key=lambda x: -x[0])
    return actions[:3]


# ── Report ───────────────────────────────────────────────────────────────

def generate_report():
    harvest = audit_harvest_funnel()
    source = audit_source_productivity()
    idle = audit_idle_inventory()
    unwired = audit_unwired_tooling()
    flags = compute_diagnostic_flags(harvest, source, idle)
    assertions = check_assertions()
    top_actions = rank_actions(harvest, source, idle, flags, assertions)

    lines = []
    lines.append("# FQL Weekly Operational Audit")
    lines.append(f"*{TIMESTAMP}*")
    lines.append("")

    # Top 3 actions
    lines.append("## Top 3 Actions by Leverage")
    lines.append("")
    if top_actions:
        for i, (score, action) in enumerate(top_actions, 1):
            lines.append(f"**{i}.** {action}")
    else:
        lines.append("No high-leverage actions identified. System is clean.")
    lines.append("")

    # Diagnostic flags
    if flags:
        lines.append("## Diagnostic Flags")
        lines.append("")
        for f in flags:
            lines.append(f"- ⚠️ {f}")
        lines.append("")

    # Harvest funnel
    lines.append("## Harvest Funnel")
    lines.append(f"  Total: {harvest['total']} | Clean: {harvest['clean']} | Soft-blocked: {harvest['soft_blocked']} | Hard-blocked: {harvest['hard_blocked']}")
    if harvest["blocker_types"]:
        lines.append("  Blockers:")
        for bt, count in harvest["blocker_types"].items():
            lines.append(f"    {bt}: {count}")
    lines.append(f"  Factors: {harvest['factor_counts']}")
    lines.append("")

    # Source productivity
    lines.append("## Source Productivity")
    if source["runs"] > 0:
        lines.append(f"  Last run: {source.get('last_run', '?')}")
        lines.append(f"  Leads: github={source.get('github',0)} reddit={source.get('reddit',0)} youtube={source.get('youtube',0)} blog={source.get('blog',0)} digest={source.get('digest',0)}")
        lines.append(f"  Picked up by Claw: {source.get('picked_up', 0)}")
    else:
        lines.append("  No source helper runs found.")
    lines.append("")

    # Idle inventory
    lines.append(f"## Idle Inventory ({len(idle)} items)")
    if idle:
        for item in idle:
            lines.append(f"  - {item['id']} [{item['status']}]: {item['issue']}")
    else:
        lines.append("  None — all strategies have defined next steps.")
    lines.append("")

    # Assertions
    lines.append("## Verifiable Assertions")
    for a in assertions:
        icon = "✅" if a.startswith("PASS") else "❌"
        lines.append(f"  {icon} {a}")
    lines.append("")

    # Unwired tooling
    if unwired:
        lines.append(f"## Unwired Scripts ({len(unwired)})")
        lines.append("  Scripts that exist but aren't called by daily/weekly/twice-weekly pipelines:")
        for s in sorted(unwired)[:10]:
            lines.append(f"    {s}.py")
        lines.append("")

    lines.append("---")
    lines.append("*Weekly audit surfaces bottlenecks and drift. Daily digest surfaces exceptions.*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Weekly Operational Audit")
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
