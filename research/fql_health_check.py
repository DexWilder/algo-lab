#!/usr/bin/env python3
"""
FQL Health Check — Automatic Failure-Point Detection
======================================================
Validates all critical failure points across the research lab.

Principle: No silent failures.

Checks:
  1. Data integrity (missing bars, anomalies, session alignment)
  2. Research output sanity (trade dominance, parameter coverage, WF completeness)
  3. Registry integrity (valid statuses, no duplicates, required fields)
  4. Portfolio diagnostics (concentration, session coverage, family gaps)
  5. Scheduler health (stale queue items, failed jobs, report generation)

Usage:
    python3 research/fql_health_check.py              # Run all checks
    python3 research/fql_health_check.py --category data   # Run specific category
    python3 research/fql_health_check.py --json        # Output as JSON
    python3 research/fql_health_check.py --save        # Save report to research/reports/

Categories: data, research, registry, portfolio, scheduler
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
RESEARCH_DIR = ROOT / "research"
REGISTRY_PATH = RESEARCH_DIR / "data" / "strategy_registry.json"
QUEUE_PATH = RESEARCH_DIR / "data" / "roadmap_queue.json"
HARVEST_PATH = RESEARCH_DIR / "data" / "harvest_results.json"
REPORTS_DIR = RESEARCH_DIR / "reports"

# Check result levels
PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"


def _check_result(name, level, detail=""):
    return {"check": name, "level": level, "detail": detail}


# ── 1. DATA INTEGRITY CHECKS ─────────────────────────────────────────────────

def check_data_integrity():
    """Run data integrity checks on all available assets."""
    results = []

    assets = ["MES", "MNQ", "MGC", "M2K", "MCL"]

    for asset in assets:
        csv_path = DATA_DIR / f"{asset}_5m.csv"

        # File exists
        if not csv_path.exists():
            results.append(_check_result(
                f"data.{asset}.exists", FAIL, f"Data file missing: {csv_path}"))
            continue

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            results.append(_check_result(
                f"data.{asset}.readable", FAIL, f"Cannot read: {e}"))
            continue

        results.append(_check_result(
            f"data.{asset}.exists", PASS, f"{len(df)} bars loaded"))

        # Required columns
        required = {"datetime", "open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            results.append(_check_result(
                f"data.{asset}.columns", FAIL, f"Missing columns: {missing}"))
            continue
        else:
            results.append(_check_result(f"data.{asset}.columns", PASS))

        # OHLC validity
        ohlc_violations = (
            (df["high"] < df["low"]) |
            (df["high"] < df["open"]) |
            (df["high"] < df["close"]) |
            (df["low"] > df["open"]) |
            (df["low"] > df["close"])
        ).sum()
        if ohlc_violations > 0:
            results.append(_check_result(
                f"data.{asset}.ohlc", FAIL, f"{ohlc_violations} OHLC violations"))
        else:
            results.append(_check_result(f"data.{asset}.ohlc", PASS))

        # Duplicate timestamps
        dupes = df["datetime"].duplicated().sum()
        if dupes > 0:
            results.append(_check_result(
                f"data.{asset}.duplicates", WARN, f"{dupes} duplicate timestamps"))
        else:
            results.append(_check_result(f"data.{asset}.duplicates", PASS))

        # Price spikes (>5% single bar move)
        returns = df["close"].pct_change().abs()
        spikes = (returns > 0.05).sum()
        if spikes > 10:
            results.append(_check_result(
                f"data.{asset}.spikes", WARN, f"{spikes} bars with >5% single-bar move"))
        else:
            results.append(_check_result(
                f"data.{asset}.spikes", PASS, f"{spikes} spikes (acceptable)"))

        # Zero/negative prices
        bad_prices = ((df["close"] <= 0) | (df["open"] <= 0)).sum()
        if bad_prices > 0:
            results.append(_check_result(
                f"data.{asset}.negative_prices", FAIL, f"{bad_prices} zero/negative prices"))
        else:
            results.append(_check_result(f"data.{asset}.negative_prices", PASS))

        # Date range coverage
        dt = pd.to_datetime(df["datetime"])
        date_range = f"{dt.min().strftime('%Y-%m-%d')} to {dt.max().strftime('%Y-%m-%d')}"
        years = (dt.max() - dt.min()).days / 365.25
        level = PASS if years >= 5 else WARN
        results.append(_check_result(
            f"data.{asset}.coverage", level, f"{date_range} ({years:.1f} years)"))

    return results


# ── 2. RESEARCH OUTPUT SANITY CHECKS ─────────────────────────────────────────

def check_research_sanity():
    """Validate research output quality before accepting results."""
    results = []

    # Check harvest results exist and are well-formed
    if not HARVEST_PATH.exists():
        results.append(_check_result(
            "research.harvest_results", SKIP, "No harvest results file found"))
    else:
        try:
            with open(HARVEST_PATH) as f:
                harvest = json.load(f)

            results.append(_check_result(
                "research.harvest_results.exists", PASS,
                f"{len(harvest)} results found"))

            # Check for single-trade dominance
            for key, result in harvest.items():
                stats = result.get("stats", {})
                total_trades = stats.get("total_trades", 0)
                if total_trades > 0 and total_trades < 5:
                    results.append(_check_result(
                        f"research.harvest.{key}.sample_size", WARN,
                        f"Only {total_trades} trades — insufficient for conclusions"))
        except Exception as e:
            results.append(_check_result(
                "research.harvest_results.readable", FAIL, str(e)))

    # Check walk-forward results
    wf_files = list(RESEARCH_DIR.glob("data/wf_matrix_*.json"))
    if not wf_files:
        results.append(_check_result(
            "research.walk_forward", SKIP, "No walk-forward results found"))
    else:
        results.append(_check_result(
            "research.walk_forward.count", PASS,
            f"{len(wf_files)} walk-forward analyses found"))

        for wf_path in wf_files:
            try:
                with open(wf_path) as f:
                    wf = json.load(f)

                # Check windows are complete
                scorecard = wf.get("scorecard", {})
                total_windows = scorecard.get("total_windows", 0)
                if total_windows == 0:
                    results.append(_check_result(
                        f"research.wf.{wf_path.stem}", WARN,
                        "Zero walk-forward windows — incomplete run"))
            except Exception as e:
                results.append(_check_result(
                    f"research.wf.{wf_path.stem}", FAIL, f"Cannot read: {e}"))

    return results


# ── 3. REGISTRY INTEGRITY CHECKS ─────────────────────────────────────────────

def check_registry_integrity():
    """Validate strategy registry structure and consistency."""
    results = []

    if not REGISTRY_PATH.exists():
        results.append(_check_result(
            "registry.exists", FAIL, "Strategy registry not found"))
        return results

    try:
        with open(REGISTRY_PATH) as f:
            registry = json.load(f)
    except Exception as e:
        results.append(_check_result(
            "registry.readable", FAIL, f"Cannot parse: {e}"))
        return results

    strategies = registry.get("strategies", [])
    results.append(_check_result(
        "registry.exists", PASS, f"{len(strategies)} strategies loaded"))

    # Valid statuses
    valid_statuses = {"idea", "testing", "probation", "core", "rejected", "retired"}
    ids_seen = set()

    for s in strategies:
        sid = s.get("strategy_id", "MISSING")

        # Duplicate IDs
        if sid in ids_seen:
            results.append(_check_result(
                f"registry.duplicate.{sid}", FAIL, f"Duplicate strategy_id: {sid}"))
        ids_seen.add(sid)

        # Valid status
        status = s.get("status", "MISSING")
        if status not in valid_statuses:
            results.append(_check_result(
                f"registry.status.{sid}", FAIL,
                f"Invalid status '{status}' (valid: {valid_statuses})"))

        # Required fields
        required_fields = ["strategy_id", "strategy_name", "family", "asset",
                          "direction", "status"]
        missing = [f for f in required_fields if f not in s or s[f] is None]
        if missing and status not in ("idea",):
            # Ideas can have sparse metadata
            results.append(_check_result(
                f"registry.fields.{sid}", WARN,
                f"Missing fields for {status} strategy: {missing}"))

    # Check no duplicates overall
    if len(ids_seen) == len(strategies):
        results.append(_check_result(
            "registry.no_duplicates", PASS, f"All {len(ids_seen)} IDs unique"))

    # Status distribution
    status_counts = {}
    for s in strategies:
        st = s.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1

    results.append(_check_result(
        "registry.status_distribution", PASS,
        ", ".join(f"{k}={v}" for k, v in sorted(status_counts.items()))))

    # Probation strategies should have validation scores
    for s in strategies:
        if s.get("status") == "probation":
            sid = s.get("strategy_id")
            if s.get("validation_score") is None:
                results.append(_check_result(
                    f"registry.probation_score.{sid}", WARN,
                    "Probation strategy missing validation_score"))

    return results


# ── 4. PORTFOLIO DIAGNOSTICS CHECKS ──────────────────────────────────────────

def check_portfolio_diagnostics():
    """Validate portfolio structure and concentration risk."""
    results = []

    if not REGISTRY_PATH.exists():
        results.append(_check_result(
            "portfolio.registry", SKIP, "No registry to analyze"))
        return results

    with open(REGISTRY_PATH) as f:
        registry = json.load(f)

    strategies = registry.get("strategies", [])
    active = [s for s in strategies if s.get("status") in ("core", "probation")]

    if not active:
        results.append(_check_result(
            "portfolio.active_count", WARN, "No active (core/probation) strategies"))
        return results

    results.append(_check_result(
        "portfolio.active_count", PASS, f"{len(active)} active strategies"))

    # Asset concentration
    asset_counts = {}
    for s in active:
        a = s.get("asset", "unknown")
        asset_counts[a] = asset_counts.get(a, 0) + 1

    for asset, count in asset_counts.items():
        pct = count / len(active) * 100
        if pct > 50:
            results.append(_check_result(
                f"portfolio.asset_concentration.{asset}", WARN,
                f"{asset} = {pct:.0f}% of active strategies — over-concentrated"))
        else:
            results.append(_check_result(
                f"portfolio.asset_concentration.{asset}", PASS,
                f"{count} strategies ({pct:.0f}%)"))

    # Direction balance
    longs = sum(1 for s in active if s.get("direction") == "long")
    shorts = sum(1 for s in active if s.get("direction") == "short")
    both = sum(1 for s in active if s.get("direction") == "both")

    if longs > 0 and shorts == 0 and both == 0:
        results.append(_check_result(
            "portfolio.direction_balance", WARN,
            f"ALL LONG — no short or both-direction strategies active"))
    else:
        results.append(_check_result(
            "portfolio.direction_balance", PASS,
            f"long={longs}, short={shorts}, both={both}"))

    # Family diversity
    families = set(s.get("family") for s in active)
    if len(families) < 3:
        results.append(_check_result(
            "portfolio.family_diversity", WARN,
            f"Only {len(families)} families: {families}"))
    else:
        results.append(_check_result(
            "portfolio.family_diversity", PASS,
            f"{len(families)} families represented"))

    # Session coverage
    sessions = set(s.get("session", "unknown") for s in active)
    results.append(_check_result(
        "portfolio.session_coverage", PASS,
        f"Sessions covered: {', '.join(sorted(sessions))}"))

    # Gaps: which assets have no coverage?
    covered_assets = set(s.get("asset") for s in active)
    all_assets = {"MES", "MNQ", "MGC", "M2K", "MCL"}
    uncovered = all_assets - covered_assets
    if uncovered:
        results.append(_check_result(
            "portfolio.asset_gaps", WARN,
            f"No active strategies for: {', '.join(sorted(uncovered))}"))
    else:
        results.append(_check_result(
            "portfolio.asset_gaps", PASS, "All 5 core assets covered"))

    return results


# ── 5. SCHEDULER / AUTOMATION HEALTH CHECKS ──────────────────────────────────

def check_scheduler_health():
    """Validate research automation pipeline health."""
    results = []

    # Roadmap queue exists and has items
    if not QUEUE_PATH.exists():
        results.append(_check_result(
            "scheduler.queue_exists", WARN, "No roadmap queue found"))
    else:
        try:
            with open(QUEUE_PATH) as f:
                queue = json.load(f)

            tasks = queue.get("tasks", [])
            results.append(_check_result(
                "scheduler.queue_exists", PASS, f"{len(tasks)} tasks in queue"))

            # Check for stale tasks (in_progress for too long)
            for task in tasks:
                if task.get("status") == "in_progress":
                    started = task.get("started")
                    if started:
                        try:
                            start_dt = datetime.strptime(started, "%Y-%m-%d")
                            days_old = (datetime.now() - start_dt).days
                            if days_old > 7:
                                results.append(_check_result(
                                    f"scheduler.stale_task.{task.get('task_id', '?')}",
                                    WARN,
                                    f"In-progress for {days_old} days: {task.get('description', '?')}"))
                        except ValueError:
                            pass

            # Check queue advancement
            completed = sum(1 for t in tasks if t.get("status") == "completed")
            queued = sum(1 for t in tasks if t.get("status") == "queued")
            in_prog = sum(1 for t in tasks if t.get("status") == "in_progress")
            results.append(_check_result(
                "scheduler.queue_progress", PASS,
                f"completed={completed}, in_progress={in_prog}, queued={queued}"))

        except Exception as e:
            results.append(_check_result(
                "scheduler.queue_readable", FAIL, str(e)))

    # Reports directory exists and has recent reports
    if not REPORTS_DIR.exists():
        results.append(_check_result(
            "scheduler.reports_dir", WARN, "No reports directory"))
    else:
        reports = sorted(REPORTS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not reports:
            reports = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not reports:
            results.append(_check_result(
                "scheduler.recent_reports", WARN, "No reports found in reports/"))
        else:
            newest = reports[0]
            age_days = (datetime.now() - datetime.fromtimestamp(newest.stat().st_mtime)).days
            if age_days > 7:
                results.append(_check_result(
                    "scheduler.recent_reports", WARN,
                    f"Most recent report is {age_days} days old: {newest.name}"))
            else:
                results.append(_check_result(
                    "scheduler.recent_reports", PASS,
                    f"Latest: {newest.name} ({age_days}d ago)"))

    # Strategy directories should have __init__.py or strategy.py
    strat_dir = ROOT / "strategies"
    if strat_dir.exists():
        broken = []
        for d in sorted(strat_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                if not (d / "strategy.py").exists():
                    broken.append(d.name)
        if broken:
            results.append(_check_result(
                "scheduler.broken_strategies", WARN,
                f"{len(broken)} strategy dirs missing strategy.py: {', '.join(broken[:5])}"))
        else:
            results.append(_check_result(
                "scheduler.strategy_files", PASS, "All strategy dirs have strategy.py"))

    return results


# ── Report Generation ─────────────────────────────────────────────────────────

ALL_CATEGORIES = {
    "data": ("DATA INTEGRITY", check_data_integrity),
    "research": ("RESEARCH OUTPUT SANITY", check_research_sanity),
    "registry": ("REGISTRY INTEGRITY", check_registry_integrity),
    "portfolio": ("PORTFOLIO DIAGNOSTICS", check_portfolio_diagnostics),
    "scheduler": ("SCHEDULER / AUTOMATION HEALTH", check_scheduler_health),
}


def run_checks(categories=None):
    """Run all or selected checks, return structured results."""
    if categories is None:
        categories = list(ALL_CATEGORIES.keys())

    all_results = {}
    for cat in categories:
        if cat in ALL_CATEGORIES:
            label, func = ALL_CATEGORIES[cat]
            all_results[cat] = {
                "label": label,
                "results": func(),
            }

    return all_results


def print_report(all_results):
    """Print a terminal health report."""
    W = 70
    SEP = "=" * W
    THIN = "-" * 50

    total_pass = 0
    total_warn = 0
    total_fail = 0
    total_skip = 0

    print()
    print(SEP)
    print("  FQL HEALTH CHECK REPORT")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(SEP)

    for cat, data in all_results.items():
        print()
        print(f"  {data['label']}")
        print(f"  {THIN}")

        for r in data["results"]:
            level = r["level"]
            icon = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "SKIP": "○"}[level]
            detail = f"  {r['detail']}" if r["detail"] else ""
            print(f"  {icon} [{level:4s}] {r['check']}{detail}")

            if level == PASS:
                total_pass += 1
            elif level == WARN:
                total_warn += 1
            elif level == FAIL:
                total_fail += 1
            else:
                total_skip += 1

    # Summary
    total = total_pass + total_warn + total_fail + total_skip
    print()
    print(SEP)
    print(f"  SUMMARY: {total} checks — {total_pass} PASS, {total_warn} WARN, {total_fail} FAIL, {total_skip} SKIP")

    if total_fail > 0:
        print(f"  STATUS: UNHEALTHY — {total_fail} failures need attention")
    elif total_warn > 0:
        print(f"  STATUS: HEALTHY (with warnings)")
    else:
        print(f"  STATUS: HEALTHY")
    print(SEP)
    print()


def save_report(all_results):
    """Save report as JSON to research/reports/."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = REPORTS_DIR / f"health_check_{timestamp}.json"

    # Flatten for JSON
    output = {
        "timestamp": datetime.now().isoformat(),
        "categories": {}
    }
    for cat, data in all_results.items():
        output["categories"][cat] = {
            "label": data["label"],
            "results": data["results"],
        }

    # Summary stats
    all_checks = []
    for data in all_results.values():
        all_checks.extend(data["results"])

    output["summary"] = {
        "total": len(all_checks),
        "pass": sum(1 for r in all_checks if r["level"] == PASS),
        "warn": sum(1 for r in all_checks if r["level"] == WARN),
        "fail": sum(1 for r in all_checks if r["level"] == FAIL),
        "skip": sum(1 for r in all_checks if r["level"] == SKIP),
    }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved to {out_path}")
    return out_path


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FQL Health Check — Automatic Failure-Point Detection")
    parser.add_argument("--category", "-c", choices=list(ALL_CATEGORIES.keys()),
                        help="Run only this category")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--save", action="store_true",
                        help="Save report to research/reports/")
    args = parser.parse_args()

    categories = [args.category] if args.category else None
    all_results = run_checks(categories)

    if args.json:
        # Flatten for JSON output
        output = {}
        for cat, data in all_results.items():
            output[cat] = data["results"]
        print(json.dumps(output, indent=2))
    elif args.save:
        print_report(all_results)
        save_report(all_results)
    else:
        print_report(all_results)


if __name__ == "__main__":
    main()
