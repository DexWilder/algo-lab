"""Phase 1C 24h post-wiring verification — WH-MNQ-stop_run_reversal.

LOCAL verification-only check (runs against local forward-runner output, which a
remote agent cannot see). Promotion-protocol 24h post-wiring verification for the
book wired 2026-06-15 (commit 52eb93c).

Verdicts:
  PHASE1C_24H_VERIFY_OK      — all 8 checks pass
  PHASE1C_24H_VERIFY_PENDING — forward runner has not run since wiring (no live output yet)
  PHASE1C_24H_VERIFY_FAIL    — a surface is missing/contradictory; rollback STAGED (not auto-executed)

ROLLBACK SAFETY: on FAIL this script does NOT auto-execute a destructive registry
rollback (unattended registry reverts are a bad-automation smell). It writes the
FAIL packet with exact rollback steps + a pre-failure backup path and raises a
loud ALERT for human confirmation. Run with --execute-rollback to actually revert.

Boundaries: no new strategy work, no unrelated mutation. Read-only except for
writing the verdict packet (and, only with --execute-rollback, the staged revert).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SID = "WH-MNQ-stop_run_reversal-ema_slope-PL"
WIRING_COMMIT = "52eb93c"
REG = ROOT / "research" / "data" / "strategy_registry.json"
LOG_DIR = ROOT / "logs"
EXCLUDED = ["XB-ORB-EMA-Ladder-MGC", "XB-ORB-EMA-Chandelier-MNQ",
            "XB-PB-EMA-Chandelier-MNQ", "XB-ORB-EMA-ATRTrail-MES"]


def _grep_logs() -> dict:
    """Check whether SID appears in actual forward-runner output logs."""
    hits = {}
    for name in ("signal_log.csv", "trade_log.csv", "daily_report.csv"):
        p = LOG_DIR / name
        found = False
        if p.exists():
            try:
                found = SID in p.read_text(errors="ignore")
            except Exception:
                found = False
        hits[name] = {"exists": p.exists(), "contains_book": found}
    return hits


def run(execute_rollback: bool = False) -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    import engine.strategy_universe as su
    from research.live_drift_monitor import BASELINE, STRATEGY_PROMOTED_DATES

    reg = json.loads(REG.read_text())
    entry = next((s for s in reg["strategies"] if s["strategy_id"] == SID), None)
    cfg = su.build_portfolio_config(include_probation=True)
    active = cfg["strategies"]
    log_hits = _grep_logs()

    checks = {}
    # 1. appears in actual forward-runner output (not just config)
    in_logs = any(v["contains_book"] for v in log_hits.values())
    checks["1_in_live_forward_output"] = {"pass": in_logs, "detail": log_hits}
    # 2. paper/probation only, 1 MNQ
    checks["2_paper_probation_1mnq"] = {
        "pass": bool(entry) and entry.get("status") == "probation"
        and entry.get("controller_action") == "PROBATION" and entry.get("asset") == "MNQ",
        "detail": {"status": entry and entry.get("status"),
                   "controller_action": entry and entry.get("controller_action")}}
    # 3. exit_variant null / not donchian
    ev = active.get(SID, {})
    checks["3_exit_variant_null"] = {
        "pass": entry and entry.get("execution_config", {}).get("exit_variant") is None
        and ev.get("exit_variant") is None,
        "detail": {"registry": entry and entry.get("execution_config", {}).get("exit_variant"),
                   "runner": ev.get("exit_variant")}}
    # 4. MNQ workhorse count 2 of <=2
    mnq_wh = sorted([k for k, v in active.items()
                     if v.get("asset") == "MNQ" and k != "TV-NFP-High-Low-Levels"])
    checks["4_mnq_workhorse_count"] = {"pass": len(mnq_wh) <= 2 and SID in mnq_wh, "detail": mnq_wh}
    # 5. excluded books still excluded
    excl = {e: e not in active for e in EXCLUDED}
    checks["5_excluded_books_excluded"] = {"pass": all(excl.values()), "detail": excl}
    # 6. drift monitor + scorecard recognition
    in_drift = SID in BASELINE["strategies"] and SID in STRATEGY_PROMOTED_DATES
    in_eval = SID in [t[0] for t in su.get_eval_strategies()]
    checks["6_monitor_scorecard_recognized"] = {"pass": in_drift and in_eval,
                                                "detail": {"drift": in_drift, "eval_set": in_eval}}
    # 7. no live/prop route
    live_route = bool(entry) and (entry.get("execution_path") == "live"
                                   or entry.get("live_enabled") is True)
    checks["7_no_live_prop_route"] = {"pass": not live_route, "detail": {"live_route": live_route}}

    all_non_log_pass = all(checks[k]["pass"] for k in checks if k != "1_in_live_forward_output")

    # Verdict logic
    if not in_logs:
        # forward runner has not produced output with the book yet
        verdict = "PHASE1C_24H_VERIFY_PENDING" if all_non_log_pass else "PHASE1C_24H_VERIFY_FAIL"
    else:
        verdict = "PHASE1C_24H_VERIFY_OK" if all(c["pass"] for c in checks.values()) else "PHASE1C_24H_VERIFY_FAIL"

    backup = None
    if verdict == "PHASE1C_24H_VERIFY_FAIL":
        backup = f"/tmp/strategy_registry_pre_phase1c_rollback_{today}.json"
        shutil.copy(REG, backup)
        if execute_rollback:
            subprocess.run(["git", "-C", str(ROOT), "revert", "--no-edit", WIRING_COMMIT], check=False)

    # ── Packet ───────────────────────────────────────────────────────────────
    lines = [f"# Phase 1C 24h Verify — {SID} — {today}", "",
             f"> Verdict: **{verdict}**", ""]
    for k, c in checks.items():
        lines.append(f"- [{'PASS' if c['pass'] else 'FAIL' if k!='1_in_live_forward_output' or in_logs else 'PENDING'}] {k}: {c['detail']}")
    if verdict == "PHASE1C_24H_VERIFY_PENDING":
        lines += ["", "Forward runner has not produced live output containing the book yet. "
                  "All config/registry/monitor surfaces are correct; awaiting a forward-day run. "
                  "Re-run after the next forward-day run. No rollback."]
    if verdict == "PHASE1C_24H_VERIFY_FAIL":
        lines += ["", "## ⚠️ FAIL — rollback STAGED (not auto-executed)",
                  f"- Pre-failure registry backup: `{backup}`",
                  f"- To roll back: `git revert --no-edit {WIRING_COMMIT}` (registry entry + drift-monitor) — or re-run this script with --execute-rollback.",
                  "- HUMAN CONFIRMATION REQUIRED before destructive rollback."]
    out = ROOT / "docs" / "fql_forge" / f"PHASE1C_24H_VERIFY_{today}.md"
    out.write_text("\n".join(lines) + "\n")

    print(f"VERDICT: {verdict}")
    for k, c in checks.items():
        print(f"  {k}: {'PASS' if c['pass'] else 'no'}  {c['detail']}")
    print(f"Wrote: {out}")
    if backup:
        print(f"Rollback backup: {backup} (rollback NOT executed unless --execute-rollback)")
    return verdict


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute-rollback", action="store_true",
                    help="Actually execute the git revert on FAIL (default: stage only)")
    args = ap.parse_args()
    v = run(execute_rollback=args.execute_rollback)
    sys.exit(0 if v in ("PHASE1C_24H_VERIFY_OK", "PHASE1C_24H_VERIFY_PENDING") else 1)
