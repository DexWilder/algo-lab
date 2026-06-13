"""MNQ Exposure Rationalization — 2026-06-13 (Option 1, operator-authorized).

Narrow governance cleanup BEFORE Phase 1C wiring. The constraint-11 MNQ cap
revealed two undocumented MNQ daily books trading in paper despite never being
promoted into paper probation (Track 2 EXPERIMENTAL_FORWARD_CLOCK, paper_ready
=false, promotion_eligible=false, promotion_date=None):

  - XB-ORB-EMA-Chandelier-MNQ
  - XB-PB-EMA-Chandelier-MNQ

Action: deactivate them from active paper execution, preserve all records.

Durable deactivation (defeats the documented silent controller revert):
  - status -> "watch"  (OUT of EVAL_STATES={core,probation,testing}, so
    portfolio_regime_controller.get_eval_strategies() no longer evaluates them
    and cannot rewrite controller_action back to REDUCED_ON/PROBATION)
  - controller_action -> "OFF" (ACTION_ELIGIBILITY OFF=False -> excluded by
    build_portfolio_config even with include_probation=True)
  - lifecycle_stage -> "watch"; controller_state -> non-active
  - records preserved (notes, validation, state_history appended; NOT deleted)

Kept active: XB-ORB-EMA-Ladder-MNQ (canonical documented probation workhorse).
Kept separate: TV-NFP-High-Low-Levels (sparse event MNQ exposure, not a daily
workhorse — left untouched, still carries MNQ exposure, documented).

Boundaries: no stop_run_reversal wiring, no FOMC, no Wave 2/3, no live/prop,
no OpenClaw/asset_config, no strategy logic changes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json  # noqa: E402

REG_PATH = ROOT / "research" / "data" / "strategy_registry.json"
TODAY = "2026-06-13"

DEACTIVATE = ["XB-ORB-EMA-Chandelier-MNQ", "XB-PB-EMA-Chandelier-MNQ"]
KEEP_ACTIVE = ["XB-ORB-EMA-Ladder-MNQ"]
KEEP_SEPARATE = ["TV-NFP-High-Low-Levels"]

SNAP_FIELDS = ("status", "controller_action", "controller_state",
               "lifecycle_stage", "executable_state", "asset", "strategy_name")


def snapshot(s: dict) -> dict:
    return {f: s.get(f) for f in SNAP_FIELDS}


def active_mnq_report(tag: str) -> dict:
    """Recompute what the forward runner would actually trade (fresh import)."""
    import importlib
    import engine.strategy_universe as su
    importlib.reload(su)
    cfg = su.build_portfolio_config(include_probation=True)
    strats = cfg.get("strategies", {})
    mnq = {sid: s for sid, s in strats.items() if s.get("asset") == "MNQ"}
    # classify daily-workhorse vs sparse-event by known IDs
    sparse_event_ids = {"TV-NFP-High-Low-Levels"}
    daily = [sid for sid in mnq if sid not in sparse_event_ids]
    sparse = [sid for sid in mnq if sid in sparse_event_ids]
    return {
        "tag": tag,
        "total_active_books_all_assets": len(strats),
        "active_mnq_books_total": len(mnq),
        "active_mnq_daily_workhorse": sorted(daily),
        "active_mnq_sparse_event": sorted(sparse),
        "runtime_max_positions_per_asset": cfg.get("max_positions_per_asset"),
    }


def run():
    print("MNQ Exposure Rationalization — 2026-06-13\n", flush=True)

    before_runner = active_mnq_report("BEFORE")
    print("BEFORE (active MNQ books in runner):", json.dumps(before_runner, indent=2), flush=True)

    reg = json.loads(REG_PATH.read_text())
    byid = {s["strategy_id"]: s for s in reg["strategies"]}

    before_entries = {}
    for sid in DEACTIVATE + KEEP_ACTIVE + KEEP_SEPARATE:
        if sid in byid:
            before_entries[sid] = snapshot(byid[sid])

    # ── Deactivate the two undocumented Chandelier MNQ books ──────────────────
    changes = {}
    for sid in DEACTIVATE:
        s = byid[sid]
        prior = snapshot(s)
        s["status"] = "watch"
        s["controller_action"] = "OFF"
        s["controller_state"] = "VALIDATED"   # controller default for non-eval status
        s["prior_state"] = prior["controller_state"]
        s["lifecycle_stage"] = "watch"
        s["paper_execution"] = "DEACTIVATED"
        s["deactivation_date"] = TODAY
        s["deactivation_reason"] = (
            "Governance cleanup (MNQ exposure rationalization, operator Option 1, 2026-06-13). "
            "Undocumented active MNQ exposure: wired 2026-05-28 as Track 2 EXPERIMENTAL_FORWARD_CLOCK "
            "(paper_ready=false, promotion_eligible=false, promotion_date=None) but running as "
            "status=probation+REDUCED_ON. Never promoted into paper probation. Frozen pending explicit "
            "operator governance. Records preserved; not deleted; reactivatable."
        )
        s.setdefault("state_history", []).append({
            "date": TODAY,
            "from": prior["controller_state"],
            "to": "DEACTIVATED_GOVERNANCE",
            "trigger": "MNQ exposure rationalization (operator Option 1) — undocumented Track 2 MNQ book frozen",
        })
        note = s.get("notes", "") or ""
        s["notes"] = (note + " | 2026-06-13 DEACTIVATED from paper execution (governance cleanup; "
                      "undocumented MNQ exposure; never promoted into probation; records preserved).").strip()
        changes[sid] = {"before": prior, "after": snapshot(s)}

    # ── Atomic write ─────────────────────────────────────────────────────────
    atomic_write_json(REG_PATH, reg)
    print("\nRegistry written atomically.", flush=True)

    after_runner = active_mnq_report("AFTER")
    print("\nAFTER (active MNQ books in runner):", json.dumps(after_runner, indent=2), flush=True)

    # ── Assertions (fail-closed) ─────────────────────────────────────────────
    after_set = set(after_runner["active_mnq_daily_workhorse"] + after_runner["active_mnq_sparse_event"])
    deactivated_ok = all(sid not in after_set for sid in DEACTIVATE)
    kept_ok = all(sid in after_set for sid in KEEP_ACTIVE)
    sep_ok = all(sid in after_set for sid in KEEP_SEPARATE)
    stop_run_absent = "WH-MNQ-stop_run_reversal-ema_slope-PL" not in after_set
    print("\n=== VERIFICATION ===", flush=True)
    print(f"  two Chandelier books removed from runner: {deactivated_ok}", flush=True)
    print(f"  XB-ORB-EMA-Ladder-MNQ kept active:        {kept_ok}", flush=True)
    print(f"  TV-NFP-High-Low-Levels kept (separate):   {sep_ok}", flush=True)
    print(f"  stop_run_reversal still NOT wired:         {stop_run_absent}", flush=True)
    print(f"  active MNQ daily-workhorse books: {before_runner['active_mnq_daily_workhorse']} "
          f"-> {after_runner['active_mnq_daily_workhorse']}", flush=True)

    ok = deactivated_ok and kept_ok and sep_ok and stop_run_absent
    verdict = "MNQ_EXPOSURE_RATIONALIZED" if ok else "CLEANUP_INCOMPLETE_REVIEW"
    print(f"\n  VERDICT: {verdict}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / \
        "mnq_exposure_rationalization_2026-06-13.json"
    out.write_text(json.dumps({
        "purpose": "MNQ exposure rationalization before Phase 1C (operator Option 1)",
        "boundaries": "no stop_run wiring; no FOMC; no Wave 2/3; no live/prop; no OpenClaw/asset_config; no strategy logic changes",
        "deactivated": DEACTIVATE,
        "kept_active": KEEP_ACTIVE,
        "kept_separate_sparse_event": KEEP_SEPARATE,
        "registry_field_changes": changes,
        "runner_before": before_runner,
        "runner_after": after_runner,
        "verification": {
            "chandelier_removed": deactivated_ok,
            "ladder_kept": kept_ok,
            "tvnfp_kept_separate": sep_ok,
            "stop_run_not_wired": stop_run_absent,
        },
        "verdict": verdict,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    return verdict


if __name__ == "__main__":
    v = run()
    sys.exit(0 if v == "MNQ_EXPOSURE_RATIONALIZED" else 1)
