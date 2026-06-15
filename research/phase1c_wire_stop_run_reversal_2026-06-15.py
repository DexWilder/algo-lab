"""Phase 1C Wiring — WH-MNQ-stop_run_reversal (operator-approved 2026-06-15).

Atomic registry transition to paper-wire the PRIMARY daily workhorse, exactly
as specified in docs/fql_forge/paper_packet_drafts/PHASE1C_WIRING_REQUEST_*.

Approved controls:
  - 1 MNQ only · status=probation · controller_action=PROBATION
  - executable_state=EXECUTABLE · execution_config.exit_variant=null (donchian trap avoided)
  - promotion_date=2026-06-14 (clean positive approval evidence)
  - max-DD kill: $1,500 realized drawdown from paper-start equity (closed-trade equity)
  - all Phase 1A kill switches active · SLA 30 trades or 30 sessions

Boundaries: ONLY this entry is added. No change to Phase 1D/FOMC, Wave 2/3,
Lane B, live/prop, Ladder-MGC, Chandelier books, ATRTrail-MES, or any unrelated
registry/scheduler/portfolio state. (Drift-monitor BASELINE edited separately.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json  # noqa: E402

REG = ROOT / "research" / "data" / "strategy_registry.json"
SID = "WH-MNQ-stop_run_reversal-ema_slope-PL"

ENTRY = {
    "strategy_id": SID,
    "strategy_name": "xb_stop_run_reversal_ema_ladder",
    "family": "crossbreed_meanreversion",
    "asset": "MNQ",
    "session": "all_day",
    "direction": "both",
    "source": "lane_a_wave1_forge_workhorse_2026-06-13",
    "rule_summary": "Stop-run reversal (liquidity sweep + reclaim) + EMA-slope filter + profit_ladder exit. Intraday-flat daily workhorse.",
    "status": "probation",
    "controller_action": "PROBATION",
    "executable_state": "EXECUTABLE",
    "controller_state": "ACTIVE",
    "lifecycle_stage": "forward_validation",
    "portfolio_role": "workhorse",
    "promotion_date": "2026-06-14",
    "paper_ready": True,
    "promotion_eligible": True,
    "validation_score": 9.0,
    "trades_6yr": 1414,
    "profit_factor": 1.477,
    "created_date": "2026-06-13",
    "state_entered_date": "2026-06-15",
    "last_review_date": "2026-06-15",
    "kill_flag": False,
    "kill_switches": {
        "max_dd_realized_usd": 1500,
        "max_dd_basis": "realized drawdown from paper-start equity, measured on closed-trade equity for this book",
        "rolling12_era3_pf_min": 1.0,
        "mon_pf_min_first6_mondays": 0.9,
        "h13_bucket_pf_min": 0.85,
    },
    "forward_sla": "30 forward trades OR 30 sessions, whichever later",
    "monitors": [
        "MON_WEAKNESS_MONITOR",
        "H13_KNIFE_EDGE_MONITOR",
        "ACTIVE_EXPOSURE_WARNING_XB_ORB_PROBATION",
    ],
    "execution_config": {
        "preferred_window": ["09:30", "14:30"],
        "allowed_window": ["09:30", "15:15"],
        "conviction_threshold_inside": 2,
        "conviction_threshold_outside": 2,
        "priority": 9,
        "avoid_regimes": [],
        "preferred_regimes": [],
        "exit_variant": None,
    },
    "notes": (
        "Lane A Wave 1 PRIMARY daily workhorse. Paper-wired 2026-06-15 (Phase 1C). "
        "Baseline n=1414, PF 1.477, median $15.51, largest loss -$1457 (audit window). "
        "Port verified byte-identical to DATA_AUDIT_GREEN (commit b90c501, signal hash "
        "d2d31c3f0e7e86bb). DSCL in-repo verified Databento-backed (d8ea1b6). Org-hygiene "
        "clean + fail-closed gate (09d61ad). exit_variant=null is REQUIRED (runner "
        "profit_ladder branch = donchian trap). 1 MNQ paper. Live/prop BLOCKED until DSCL §7."
    ),
    "state_history": [{
        "date": "2026-06-15", "from": "VALIDATED", "to": "PROBATION",
        "trigger": "Phase 1C paper wiring (operator-approved); port-verified + DSCL + org-hygiene gates clear",
    }],
}


def run():
    print("Phase 1C Wiring — WH-MNQ-stop_run_reversal (2026-06-15)\n", flush=True)
    reg = json.loads(REG.read_text())
    existing = {s["strategy_id"] for s in reg["strategies"]}
    if SID in existing:
        print(f"ABORT: {SID} already exists in registry — no action.", flush=True)
        return "ABORT_ALREADY_EXISTS"

    reg["strategies"].append(ENTRY)
    atomic_write_json(REG, reg)
    print(f"Added registry entry: {SID}", flush=True)
    print(f"  strategy_count: {len(existing)} -> {len(reg['strategies'])}", flush=True)

    # ── Verification ─────────────────────────────────────────────────────────
    import importlib
    import engine.strategy_universe as su
    importlib.reload(su)
    approved, reason = su.execution_approval_check(ENTRY)
    cfg = su.build_portfolio_config(include_probation=True)
    active = cfg["strategies"]
    in_runner = SID in active
    ev = active.get(SID, {})
    mnq_books = [k for k, v in active.items() if v.get("asset") == "MNQ"]
    mnq_workhorse = [m for m in mnq_books if m != "TV-NFP-High-Low-Levels"]
    excluded = ["XB-ORB-EMA-Chandelier-MNQ", "XB-PB-EMA-Chandelier-MNQ",
                "XB-ORB-EMA-ATRTrail-MES", "XB-ORB-EMA-Ladder-MGC"]
    excl_ok = {e: (e not in active) for e in excluded}

    print("\n=== VERIFICATION ===", flush=True)
    print(f"  execution-approval gate: approved={approved} reason={reason}", flush=True)
    print(f"  in runner universe: {in_runner}", flush=True)
    print(f"  exit_variant in runner config: {ev.get('exit_variant')!r} (expect None)", flush=True)
    print(f"  mode/asset: {ev.get('mode')}/{ev.get('asset')}", flush=True)
    print(f"  active MNQ workhorse books: {sorted(mnq_workhorse)} (count={len(mnq_workhorse)}, cap<=2)", flush=True)
    print(f"  excluded books still excluded: {excl_ok}", flush=True)
    print(f"  fail_closed_exclusions: {cfg.get('_fail_closed_exclusions')}", flush=True)
    print(f"  in get_eval_strategies (scorecard/controller visibility): "
          f"{SID in [t[0] for t in su.get_eval_strategies()]}", flush=True)

    ok = (approved and in_runner and ev.get("exit_variant") is None
          and len(mnq_workhorse) <= 2 and all(excl_ok.values()))
    print(f"\n  VERDICT: {'PHASE1C_WIRED_OK' if ok else 'WIRING_NEEDS_REVIEW'}", flush=True)
    return "PHASE1C_WIRED_OK" if ok else "WIRING_NEEDS_REVIEW"


if __name__ == "__main__":
    v = run()
    sys.exit(0 if v == "PHASE1C_WIRED_OK" else 1)
