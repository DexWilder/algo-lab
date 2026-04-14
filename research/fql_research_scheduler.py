#!/usr/bin/env python3
"""FQL Autonomous Research Scheduler — Job definitions and execution framework.

Orchestrates all FQL research jobs on defined cadences:
    - Daily: health check, half-life, contribution, activation matrix, decision report
    - Twice Weekly: candidate scan, code conversion, baseline backtests
    - Weekly: walk-forward matrix, cross-asset tests, param stability, registry update
    - Monthly: genome clustering, correlation matrix, full contribution analysis, half-life review
    - Quarterly: gap analysis, research targeting, harvest focus update

Usage:
    python3 research/fql_research_scheduler.py --daily       # Run daily jobs
    python3 research/fql_research_scheduler.py --weekly      # Run weekly jobs
    python3 research/fql_research_scheduler.py --monthly     # Run monthly jobs
    python3 research/fql_research_scheduler.py --status      # Show job status
    python3 research/fql_research_scheduler.py --list        # List all jobs
"""

import argparse
import importlib
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCHEDULER_LOG_PATH = ROOT / "research" / "data" / "scheduler_log.json"


# ── Job Definitions ──────────────────────────────────────────────────────────

JOBS = {
    # ── Daily (every trading day) ─────────────────────────────────────
    "daily_health_check": {
        "cadence": "daily",
        "description": "Run 60-point health check across all modules",
        "module": "research.fql_health_check",
        "function": "run_checks",
        "priority": 1,
    },
    "daily_half_life": {
        "cadence": "daily",
        "description": "Update half-life decay scores for all strategies",
        "module": "research.strategy_half_life_monitor",
        "function": "run_half_life_analysis",
        "priority": 2,
    },
    "daily_contribution": {
        "cadence": "daily",
        "description": "Compute marginal Sharpe contribution per strategy",
        "module": "research.strategy_contribution_analysis",
        "function": "main",
        "priority": 3,
        "subprocess": True,  # Uses argparse — run as subprocess
    },
    "daily_activation_matrix": {
        "cadence": "daily",
        "description": "Run Portfolio Regime Controller, save activation matrix, apply to registry",
        "module": "research.portfolio_regime_controller",
        "function": "run_controller",
        "priority": 4,
        "post_hook": "_daily_controller_post",
    },
    "daily_decision_report": {
        "cadence": "daily",
        "description": "Generate daily portfolio decision report (JSON + Markdown)",
        "module": "research.daily_portfolio_decision_report",
        "function": None,
        "priority": 5,
        "subprocess": True,
        "subprocess_args": ["--from-cache", "--save"],
    },
    "daily_drift_monitor": {
        "cadence": "daily",
        "description": "Detect forward/live behavior drift vs backtest baseline",
        "module": "research.live_drift_monitor",
        "function": "run_drift_monitor",
        "priority": 6,
        "post_hook": "_daily_drift_post",
    },

    # ── Twice Weekly ──────────────────────────────────────────────────
    "biweekly_candidate_scan": {
        "cadence": "twice_weekly",
        "description": "Scan for new strategy candidates from sources",
        "module": None,
        "function": None,
        "priority": 10,
        "status": "PLACEHOLDER",
    },
    "biweekly_batch_first_pass": {
        "cadence": "twice_weekly",
        "description": "Batch first-pass evaluation on untested strategies",
        "module": "research.batch_first_pass",
        "function": None,
        "priority": 11,
        "subprocess": False,
        "custom_runner": "_run_batch_first_pass",
    },
    "biweekly_baseline_backtest": {
        "cadence": "twice_weekly",
        "description": "Run baseline backtests on new candidates, reject junk",
        "module": "research.batch_harvest_validation",
        "function": None,
        "priority": 11,
        "subprocess": True,
    },

    # ── Weekly ────────────────────────────────────────────────────────
    "weekly_walk_forward": {
        "cadence": "weekly",
        "description": "Walk-forward matrix on validated candidates",
        "module": "research.walk_forward_matrix",
        "function": None,
        "priority": 20,
        "subprocess": True,
        "status": "MANUAL",
        "manual_reason": (
            "2026-04-14: This scheduled entry was invalid — "
            "research/walk_forward_matrix.py requires 3 positional args "
            "(<strategy_module> <asset> <mode>) and no subprocess_args "
            "were wired, so every weekly run since at least 2026-03-20 "
            "exited 1 on the usage message. A proper weekly walk-forward "
            "driver for the current live/probation portfolio does not "
            "exist yet and needs explicit design (which strategies, what "
            "parameter grid, aggregated output format for downstream "
            "consumption, interaction with tier classifications in "
            "live_drift_monitor BASELINE). Marked MANUAL until that "
            "driver is built. FOLLOW-UP: design + implement "
            "weekly_walk_forward_driver covering full-tier probation "
            "strategies at minimum."
        ),
    },
    "weekly_kill_criteria": {
        "cadence": "weekly",
        "description": "Evaluate kill criteria for all active strategies",
        "module": "research.strategy_kill_criteria",
        "function": "run_kill_review",
        "priority": 21,
    },
    "weekly_registry_update": {
        "cadence": "weekly",
        "description": "Update registry with latest scores, statuses, flags",
        "module": None,
        "function": None,
        "priority": 22,
        "status": "MANUAL",
    },
    "weekly_auto_report": {
        "cadence": "weekly",
        "description": "Generate weekly research summary",
        "module": "research.auto_report",
        "function": "generate_weekly_report",
        "priority": 23,
    },
    "weekly_integrity_monitor": {
        "cadence": "weekly",
        "description": "System integrity self-diagnostic across all subsystems",
        "module": "research.system_integrity_monitor",
        "function": None,
        "priority": 24,
        "subprocess": True,
        "subprocess_args": ["--save"],
    },

    # ── Monthly ───────────────────────────────────────────────────────
    "monthly_genome_cluster": {
        "cadence": "monthly",
        "description": "Update genome clustering and diversity scores",
        "module": "research.strategy_genome_map",
        "function": "build_genome_data",
        "priority": 30,
    },
    "monthly_full_contribution": {
        "cadence": "monthly",
        "description": "Full portfolio contribution analysis with all strategies",
        "module": "research.strategy_contribution_analysis",
        "function": None,
        "priority": 31,
        "subprocess": True,
    },
    "monthly_half_life_review": {
        "cadence": "monthly",
        "description": "Comprehensive half-life review across all windows",
        "module": "research.strategy_half_life_monitor",
        "function": "run_half_life_analysis",
        "priority": 32,
    },

    # ── Quarterly ─────────────────────────────────────────────────────
    "quarterly_gap_analysis": {
        "cadence": "quarterly",
        "description": "Identify research gaps and missing regime/asset/session coverage",
        "module": "research.harvest_scheduler",
        "function": "gap_analysis",
        "priority": 40,
    },
    "quarterly_research_targeting": {
        "cadence": "quarterly",
        "description": "Update harvest priorities based on portfolio gaps",
        "module": None,
        "function": None,
        "priority": 41,
        "status": "PLACEHOLDER",
    },
}


# ── Post-Hooks ───────────────────────────────────────────────────────────────

def _daily_controller_post(run_result):
    """After controller run: save matrix, apply to registry, print report."""
    from research.portfolio_regime_controller import (
        save_activation_matrix, apply_to_registry, print_report,
    )
    results = run_result
    if results:
        save_activation_matrix(results)
        apply_to_registry(results)
        print_report(results)


def _daily_drift_post(run_result):
    """After drift monitor: save log and print report."""
    from research.live_drift_monitor import save_drift_log, print_drift_report
    if run_result:
        save_drift_log(run_result)
        print_drift_report(run_result)


def _run_batch_first_pass(run_result=None):
    """Run batch_first_pass on strategies with status=testing that haven't been batch-evaluated."""
    import json as _json
    from research.batch_first_pass import run_first_pass, OUTPUT_DIR

    reg_path = ROOT / "research" / "data" / "strategy_registry.json"
    registry = _json.load(open(reg_path))

    # Find existing first-pass reports to avoid re-testing
    existing_reports = set()
    if OUTPUT_DIR.exists():
        for f in OUTPUT_DIR.glob("*.json"):
            try:
                data = _json.load(open(f))
                existing_reports.add(data.get("strategy", ""))
            except Exception:
                pass

    # Find strategies with status=testing that have a strategy.py file
    candidates = []
    for s in registry.get("strategies", []):
        if s.get("status") != "testing":
            continue
        strat_name = s.get("strategy_name", "")
        if not strat_name:
            continue
        strat_path = ROOT / "strategies" / strat_name / "strategy.py"
        if not strat_path.exists():
            continue
        # Skip if already batch-evaluated
        if strat_name in existing_reports:
            continue
        # Skip if already has batch_first_pass data in registry
        if s.get("batch_first_pass"):
            continue
        candidates.append(s)

    if not candidates:
        print("  No untested strategies found for batch first-pass")
        return {"tested": 0}

    print(f"  Found {len(candidates)} untested strategies")

    # Determine compatible assets for each strategy
    all_data_assets = [sym for sym in ["MES", "MNQ", "MGC", "M2K", "MCL",
                                        "ZN", "ZB", "ZF", "6E", "6J", "6B"]
                       if (ROOT / "data" / "processed" / f"{sym}_5m.csv").exists()]

    tested = 0
    for s in candidates[:5]:  # Cap at 5 per run to control runtime
        strat_name = s["strategy_name"]
        asset = s.get("asset", "")
        session = None

        # Determine which assets to test
        if asset and asset in all_data_assets:
            test_assets = [asset]
            # Add family assets if available
            from engine.asset_config import get_asset_family
            family = get_asset_family(asset)
            test_assets.extend([a for a in family if a in all_data_assets])
            test_assets = list(dict.fromkeys(test_assets))  # dedupe preserving order
        else:
            test_assets = all_data_assets

        # Check for session restriction
        if s.get("session", "").startswith("us"):
            session = "us"

        print(f"  Testing {strat_name} on {','.join(test_assets)}"
              f"{' [' + session + ']' if session else ''}")

        try:
            report = run_first_pass(strat_name, test_assets, session)

            # Save report
            from research.utils.atomic_io import atomic_write_json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            session_tag = f"_{session}" if session else ""
            out_path = OUTPUT_DIR / f"{strat_name}{session_tag}_{timestamp}.json"
            atomic_write_json(out_path, report)

            best = report.get("best_result", {})
            cls = report.get("overall_classification", "REJECT")
            print(f"    -> {cls}: best={best.get('asset','?')} PF={best.get('pf',0):.2f}")
            tested += 1
        except Exception as e:
            print(f"    -> ERROR: {e}")

    return {"tested": tested}


POST_HOOKS = {
    "_daily_controller_post": _daily_controller_post,
    "_daily_drift_post": _daily_drift_post,
}

CUSTOM_RUNNERS = {
    "_run_batch_first_pass": _run_batch_first_pass,
}


# ── Job Runner ───────────────────────────────────────────────────────────────

def run_job(job_name: str, job_def: dict) -> dict:
    """Execute a single job and return result metadata.

    Supports two execution modes:
    - Direct import: call function from module (default)
    - Subprocess: run module as `python3 -m module` (for modules with argparse)
    """
    start = datetime.now()
    result = {
        "job": job_name,
        "cadence": job_def["cadence"],
        "started": start.isoformat(),
        "status": "SKIPPED",
    }

    if job_def.get("status") in ("PLACEHOLDER", "MANUAL"):
        result["status"] = job_def["status"]
        result["message"] = f"Job not yet automated: {job_def['description']}"
        return result

    module_name = job_def.get("module")
    func_name = job_def.get("function")
    use_subprocess = job_def.get("subprocess", False)

    if not module_name:
        result["status"] = "ERROR"
        result["message"] = "Missing module definition"
        return result

    try:
        print(f"  Running {job_name}...")

        # Custom runner (for complex multi-step jobs)
        custom_runner = job_def.get("custom_runner")
        if custom_runner and custom_runner in CUSTOM_RUNNERS:
            run_result = CUSTOM_RUNNERS[custom_runner]()
            result["status"] = "SUCCESS"
            result["finished"] = datetime.now().isoformat()
            result["duration_sec"] = (datetime.now() - start).total_seconds()
            return result

        if use_subprocess:
            # Run as subprocess to avoid argparse conflicts
            cmd = [sys.executable, "-m", module_name]
            cmd.extend(job_def.get("subprocess_args", []))
            timeout = job_def.get("subprocess_timeout", 1800)  # 30 min default
            proc = subprocess.run(
                cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"Exit code {proc.returncode}: {proc.stderr[-500:]}")
            result["status"] = "SUCCESS"
        else:
            if not func_name:
                result["status"] = "ERROR"
                result["message"] = "Missing function definition (not subprocess mode)"
                return result
            mod = importlib.import_module(module_name)
            func = getattr(mod, func_name)
            run_result = func()
            result["status"] = "SUCCESS"

            # Execute post-hook if defined
            hook_name = job_def.get("post_hook")
            if hook_name and hook_name in POST_HOOKS:
                POST_HOOKS[hook_name](run_result)

    except Exception as e:
        result["status"] = "ERROR"
        result["message"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"  ERROR in {job_name}: {e}")

    result["finished"] = datetime.now().isoformat()
    result["duration_sec"] = (datetime.now() - start).total_seconds()
    return result


def run_cadence(cadence: str) -> list:
    """Run all jobs for a given cadence."""
    jobs = {k: v for k, v in JOBS.items() if v["cadence"] == cadence}
    jobs_sorted = sorted(jobs.items(), key=lambda x: x[1]["priority"])

    print(f"\nFQL Research Scheduler — {cadence.upper()} jobs")
    print(f"  {len(jobs_sorted)} jobs queued")
    print("=" * 50)

    results = []
    for name, defn in jobs_sorted:
        result = run_job(name, defn)
        results.append(result)
        print(f"  [{result['status']:>11s}] {name}")

    # Log results
    _append_log(results)

    # Summary
    success = sum(1 for r in results if r["status"] == "SUCCESS")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    skipped = sum(1 for r in results if r["status"] in ("SKIPPED", "PLACEHOLDER", "MANUAL"))
    print(f"\nDone: {success} success, {errors} errors, {skipped} skipped")

    return results


def _append_log(results: list):
    """Append job results to scheduler log."""
    log = []
    if SCHEDULER_LOG_PATH.exists():
        try:
            with open(SCHEDULER_LOG_PATH) as f:
                log = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            log = []

    log.extend(results)

    # Keep last 500 entries
    if len(log) > 500:
        log = log[-500:]

    SCHEDULER_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    from research.utils.atomic_io import atomic_write_json
    atomic_write_json(SCHEDULER_LOG_PATH, log)


# ── Status & Listing ─────────────────────────────────────────────────────────

def print_status():
    """Print last run status for each job."""
    print("\nFQL Research Scheduler — Job Status")
    print("=" * 60)

    if not SCHEDULER_LOG_PATH.exists():
        print("  No scheduler log found. No jobs have been run yet.")
        return

    with open(SCHEDULER_LOG_PATH) as f:
        log = json.load(f)

    # Get latest result per job
    latest = {}
    for entry in log:
        job = entry.get("job", "unknown")
        latest[job] = entry

    for cadence in ["daily", "twice_weekly", "weekly", "monthly", "quarterly"]:
        jobs = {k: v for k, v in JOBS.items() if v["cadence"] == cadence}
        if not jobs:
            continue
        print(f"\n  {cadence.upper()}")
        print(f"  {'-' * 55}")
        for name in sorted(jobs):
            last = latest.get(name, {})
            status = last.get("status", "NEVER_RUN")
            when = last.get("finished", "—")[:16]
            print(f"  {name:<35s} {status:<12s} {when}")


def print_job_list():
    """Print all defined jobs."""
    print("\nFQL Research Scheduler — All Jobs")
    print("=" * 70)

    for cadence in ["daily", "twice_weekly", "weekly", "monthly", "quarterly"]:
        jobs = {k: v for k, v in JOBS.items() if v["cadence"] == cadence}
        if not jobs:
            continue
        print(f"\n  {cadence.upper()}")
        print(f"  {'-' * 65}")
        for name, defn in sorted(jobs.items(), key=lambda x: x[1]["priority"]):
            built = "BUILT" if defn.get("module") and defn.get("status") != "PLACEHOLDER" else "TODO"
            print(f"  [{built:>5s}] {name:<35s} {defn['description']}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Autonomous Research Scheduler")
    parser.add_argument("--daily", action="store_true", help="Run daily jobs")
    parser.add_argument("--twice-weekly", action="store_true", help="Run twice-weekly jobs")
    parser.add_argument("--weekly", action="store_true", help="Run weekly jobs")
    parser.add_argument("--monthly", action="store_true", help="Run monthly jobs")
    parser.add_argument("--quarterly", action="store_true", help="Run quarterly jobs")
    parser.add_argument("--status", action="store_true", help="Show last run status")
    parser.add_argument("--list", action="store_true", help="List all jobs")
    args = parser.parse_args()

    if args.status:
        print_status()
    elif args.list:
        print_job_list()
    elif args.daily:
        run_cadence("daily")
    elif args.twice_weekly:
        run_cadence("twice_weekly")
    elif args.weekly:
        run_cadence("weekly")
    elif args.monthly:
        run_cadence("monthly")
    elif args.quarterly:
        run_cadence("quarterly")
    else:
        print_job_list()
        print("\nUse --daily, --weekly, etc. to run jobs for a cadence.")
        print("Use --status to see last run results.")


if __name__ == "__main__":
    main()
