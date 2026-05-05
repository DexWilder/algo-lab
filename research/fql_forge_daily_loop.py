#!/usr/bin/env python3
"""FQL Forge Daily Loop — autonomous evidence generation, dry-run/report-only.

Per `docs/fql_forge/forge_automation_design.md`:
- Autonomous evidence generation. Human-gated system mutation.
- Phase A: manual CLI only (this script).
- Phase B (later): scheduled via launchd; plist provided as .disabled.

Allowed: read candidates, run cheap screens, classify, write reports.
NOT allowed: registry append, promotion, portfolio/runtime/scheduler changes,
broad optimization.

Tripwires (auto-halt; writes _TRIPWIRE_*.md and exits non-zero):
  - 3 consecutive runs with zero PASS candidates (across reports history)
  - any candidate with system-blowup loss (PnL < -10% of starting capital)
  - reports dir > 30 days of files (operator-review backlog)
  - any harness exception during a candidate run
  - total batch runtime > 5 minutes

Usage:
    python3 research/fql_forge_daily_loop.py --dry-run --top 5
    python3 research/fql_forge_daily_loop.py --top 3
    python3 research/fql_forge_daily_loop.py --check-tripwires
"""

import argparse
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import the batch runner's internals — single source of truth for candidate
# definitions, verdict logic, metrics computation.
from research.fql_forge_batch_runner import (  # noqa: E402
    CANDIDATES, _xb_swap, _metrics, _verdict,
)

REPORTS_DIR = ROOT / "research" / "data" / "fql_forge" / "reports"
QUEUE_FILE = REPORTS_DIR / "forge_queue.md"

# Tripwire thresholds
TRIPWIRE_NO_PASS_RUN_LIMIT = 3
TRIPWIRE_BLOWUP_PCT = -0.10  # -10% of starting capital (assume $50k)
ASSUMED_STARTING_CAPITAL = 50000
TRIPWIRE_REPORTS_AGE_DAYS = 30
TRIPWIRE_RUNTIME_MAX_SEC = 300  # 5 min


def _select_candidates(n: int):
    """Pick top N candidates. Phase A: simple top-N; future phases can rank by
    gap priority, novelty, source quality, etc."""
    return list(CANDIDATES.items())[:n]


def _check_tripwires_pre_run() -> tuple[bool, str | None]:
    """Pre-run tripwire checks. Returns (clear_to_run, halt_reason_or_None)."""
    if not REPORTS_DIR.exists():
        return True, None

    # Tripwire: existing _TRIPWIRE_*.md files mean operator hasn't cleared
    existing_tripwires = list(REPORTS_DIR.glob("_TRIPWIRE_*.md"))
    if existing_tripwires:
        return False, f"unresolved tripwire(s): {[t.name for t in existing_tripwires]}"

    # Tripwire: reports dir age
    reports = sorted(REPORTS_DIR.glob("forge_daily_*.md"))
    if reports:
        oldest = reports[0]
        age_days = (datetime.now() - datetime.fromtimestamp(oldest.stat().st_mtime)).days
        if age_days > TRIPWIRE_REPORTS_AGE_DAYS:
            return False, f"reports dir backlog ({age_days}d old; >{TRIPWIRE_REPORTS_AGE_DAYS}d threshold)"

    # Tripwire: 3 consecutive zero-PASS runs (read recent JSON files)
    json_reports = sorted(REPORTS_DIR.glob("forge_daily_*.json"))
    if len(json_reports) >= TRIPWIRE_NO_PASS_RUN_LIMIT:
        recent = json_reports[-TRIPWIRE_NO_PASS_RUN_LIMIT:]
        zero_pass_count = 0
        for jpath in recent:
            try:
                data = json.loads(jpath.read_text())
                if data.get("verdict_counts", {}).get("PASS", 0) == 0:
                    zero_pass_count += 1
            except Exception:
                pass
        if zero_pass_count == TRIPWIRE_NO_PASS_RUN_LIMIT:
            return False, f"{TRIPWIRE_NO_PASS_RUN_LIMIT} consecutive runs with zero PASS — candidate pool or harness degraded"

    return True, None


def _write_tripwire(reason: str):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fname = REPORTS_DIR / f"_TRIPWIRE_{date.today().isoformat()}_{reason.split()[0]}.md"
    fname.write_text(
        f"# Tripwire fired — {date.today().isoformat()}\n\n"
        f"**Reason:** {reason}\n\n"
        f"**What this means:** the daily loop self-halted. No registry / "
        f"runtime / portfolio changes occurred. Future runs will not auto-resume "
        f"until this file is removed.\n\n"
        f"**Operator action:** review the cause; fix the underlying issue; "
        f"delete this file when ready to resume.\n"
    )
    print(f"[TRIPWIRE] {reason}")
    print(f"[TRIPWIRE] wrote: {fname}")


def _run_one(cid: str, info: dict):
    """Run one candidate; return (metrics, verdict, runtime_seconds, error_or_None)."""
    start = time.time()
    try:
        m = info["runner"]()
        v = _verdict(m, info["archetype"])
        rt = time.time() - start
        return m, v, rt, None
    except Exception as e:
        rt = time.time() - start
        return _metrics(None, cid), "RETEST", rt, str(e)


def _detect_blowup(m: dict) -> bool:
    """System-blowup tripwire: PnL < -10% of assumed starting capital."""
    return m.get("net", 0) < TRIPWIRE_BLOWUP_PCT * ASSUMED_STARTING_CAPITAL


def _write_reports(rows, run_mode: str, runtime_total: float):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    md_path = REPORTS_DIR / f"forge_daily_{today}.md"
    json_path = REPORTS_DIR / f"forge_daily_{today}.json"

    counts = {"PASS": 0, "WATCH": 0, "KILL": 0, "RETEST": 0}
    for _, _, _, v, _ in rows:
        counts[v] = counts.get(v, 0) + 1

    # Markdown report
    md = [f"# FQL Forge Daily — {today}\n"]
    md.append(f"**Run mode:** {run_mode}")
    md.append(f"**Total runtime:** {runtime_total:.1f}s")
    md.append(f"**Candidates tested:** {len(rows)}")
    md.append(f"**Verdict counts:** {counts}\n")
    md.append("## Per-candidate results\n")
    md.append("| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Runtime | Verdict |")
    md.append("|---|---|---|---:|---:|---:|---:|---:|---|")
    for cid, info, m, v, rt in rows:
        md.append(f"| {cid} | {info['asset']} | {info['gap']} | {m['n']} | "
                  f"{m['pf']:.3f} | {m['net']:.0f} | {m['max_dd']:.0f} | {rt:.1f}s | {v} |")
    md.append("")
    md.append("## Architecture trends\n")
    pass_assets = [info["asset"] for cid, info, m, v, rt in rows if v == "PASS"]
    md.append(f"- PASS assets in this batch: {pass_assets if pass_assets else '(none)'}")
    md.append(f"- Per the donor catalog, ema_slope + profit_ladder remain co-validated load-bearing pair.")
    md.append("")
    md.append("## Next-batch recommendation\n")
    untested_today = [cid for cid in CANDIDATES if cid not in [r[0] for r in rows]]
    if untested_today:
        md.append(f"- Next safe candidates to screen ({len(untested_today)} untested in this run): {untested_today[:3]}{'...' if len(untested_today) > 3 else ''}")
    else:
        md.append("- All registered candidates screened. Next session: extend candidate registry OR test on different baseline.")
    md.append("")
    md.append("## Safety affirmation\n")
    md.append("- No registry mutation\n- No Lane A surfaces touched\n- No runtime/scheduler/portfolio/checkpoint changes\n- Operator approves all promotions / appends\n")
    md_path.write_text("\n".join(md))

    # JSON report
    payload = {
        "date": today,
        "run_mode": run_mode,
        "candidates_tested": len(rows),
        "verdict_counts": counts,
        "runtime_total_sec": runtime_total,
        "results": [
            {"candidate": cid, "asset": info["asset"], "gap": info["gap"],
             "metrics": m, "verdict": v, "runtime_sec": rt}
            for cid, info, m, v, rt in rows
        ],
        "next_batch_recommendation": untested_today[:5],
        "tripwires_fired": [],
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str))

    # Update queue file (rolling)
    queue_lines = [f"# FQL Forge Queue (rolling, last updated {today})\n"]
    queue_lines.append(f"**Latest verdict counts:** {counts}\n")
    queue_lines.append("**Next safe Forge actions:**\n")
    for cid in untested_today[:5]:
        queue_lines.append(f"- {cid} ({CANDIDATES[cid]['gap']}, asset={CANDIDATES[cid]['asset']})")
    if not untested_today:
        queue_lines.append("- All registered candidates screened recently. Consider extending candidate registry or testing on alternative baselines.")
    queue_lines.append("")
    queue_lines.append("**Pending operator decisions:**")
    queue_lines.append("- Review latest daily report for any new PASS candidates eligible for batch register pre-flight")
    queue_lines.append("- See `docs/fql_forge/operator_review_packet_*.md` for prior PASS candidates pending decision")
    QUEUE_FILE.write_text("\n".join(queue_lines))

    return md_path, json_path


def main():
    ap = argparse.ArgumentParser(description="FQL Forge daily loop — dry-run/report-only")
    ap.add_argument("--top", type=int, default=5, help="Top N candidates to run")
    ap.add_argument("--dry-run", action="store_true", help="No-op safety flag (everything is dry-run by design)")
    ap.add_argument("--check-tripwires", action="store_true", help="Check tripwires and exit (no run)")
    args = ap.parse_args()

    print(f"FQL Forge Daily Loop — {date.today().isoformat()} — {('DRY-RUN' if args.dry_run else 'REPORT-ONLY')}")
    print("=" * 78)

    # Pre-run tripwire check
    clear, halt_reason = _check_tripwires_pre_run()
    if not clear:
        _write_tripwire(halt_reason)
        print(f"[HALT] tripwire fired: {halt_reason}")
        sys.exit(1)

    if args.check_tripwires:
        print("[OK] no tripwires; clear to run")
        return

    # Select and run
    selection = _select_candidates(args.top)
    print(f"Selected {len(selection)} candidate(s)")

    rows = []
    start_total = time.time()
    for cid, info in selection:
        m, v, rt, err = _run_one(cid, info)
        if err:
            _write_tripwire(f"harness_exception: {cid}: {err}")
            sys.exit(1)
        if _detect_blowup(m):
            _write_tripwire(f"blowup_loss: {cid} netPnL={m['net']:.0f} (< {TRIPWIRE_BLOWUP_PCT*100}% of ${ASSUMED_STARTING_CAPITAL})")
            sys.exit(1)
        rows.append((cid, info, m, v, rt))
        print(f"  [{cid}] n={m['n']} PF={m['pf']:.3f} netPnL=${m['net']:.0f} → {v} ({rt:.1f}s)")

    runtime_total = time.time() - start_total
    if runtime_total > TRIPWIRE_RUNTIME_MAX_SEC:
        _write_tripwire(f"runtime_overrun: {runtime_total:.0f}s > {TRIPWIRE_RUNTIME_MAX_SEC}s")
        sys.exit(1)

    md_path, json_path = _write_reports(rows, "dry-run" if args.dry_run else "report-only", runtime_total)

    # Summary
    counts = {"PASS": 0, "WATCH": 0, "KILL": 0, "RETEST": 0}
    for _, _, _, v, _ in rows:
        counts[v] = counts.get(v, 0) + 1
    print(f"\n[RESULT] {counts} (total runtime {runtime_total:.1f}s)")
    print(f"[REPORT] {md_path.name}")
    print(f"[REPORT] {json_path.name}")
    print(f"[QUEUE]  {QUEUE_FILE.name} (updated)")
    print("\n[SAFETY] No registry mutation. No Lane A surfaces touched. Operator approves any append.")


if __name__ == "__main__":
    main()
