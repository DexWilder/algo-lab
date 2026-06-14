"""Governance Remediation — 2026-06-13 (operator-authorized items #1 + #3-core).

#1: Deactivate XB-ORB-EMA-ATRTrail-MES (3rd Track 2 EXPERIMENTAL_FORWARD_CLOCK
    book, MES) using the same durable treatment as the MNQ Chandelier cleanup.
#3-core: Backfill approval provenance for the 3 core-tier books, citing evidence
    that already exists in repo/history; mark the missing discrete promotion_date
    explicitly as a LEGACY_CORE_PROVENANCE_GAP (do NOT invent provenance).

NOT done here (surfaced for operator decision, see packet):
  - XB-ORB-EMA-Ladder-MGC CLAUDE.md doc-lag fix: WITHHELD. The fail-closed gate
    revealed it is paper_ready=False + promotion_eligible=False despite having a
    promotion_date — a contradictory state, NOT cleanly approved. Documenting it
    as approved would be wrong. Left untouched (gate blocks it; safe).

Boundaries: no strategy-logic changes; no live/prop; no OpenClaw/asset_config;
no scheduler-config. Durable deactivation = status out of EVAL_STATES + OFF.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json  # noqa: E402

REG = ROOT / "research" / "data" / "strategy_registry.json"
TODAY = "2026-06-13"

CORE_PROVENANCE = {
    "ORB-MGC-Long": "Core/deployed tier (status=core, lifecycle=deployed, role=core). Documented in "
                    "docs/TARGET_PORTFOLIO.md + docs/PORTFOLIO_TRUTH_TABLE.md + docs/audits/phase_5_regime_portfolio.md "
                    "+ phase_6_deployment.md. source=internal_research, created 2026-04-10.",
    "PB-MGC-Short": "Core/deployed tier (status=core, lifecycle=deployed, role=core). git 0328aad "
                    "'Phase 15: BB Equilibrium PROMOTED to 6th Parent'; robustness tests git 7e3555e. "
                    "Documented in docs/TARGET_PORTFOLIO.md + docs/PORTFOLIO_TRUTH_TABLE.md. source=lucid_v6_extraction.",
    "XB-PB-EMA-MES-Short": "Core/deployed tier (status=core, lifecycle=deployed, role=enhancer). "
                           "source=crossbreeding_phase12, created 2026-04-10. Documented in docs/TARGET_PORTFOLIO.md "
                           "+ docs/PORTFOLIO_TRUTH_TABLE.md (only MES core strategy).",
}


def run():
    print("Governance Remediation — 2026-06-13 (items #1 + #3-core)\n", flush=True)
    reg = json.loads(REG.read_text())
    byid = {s["strategy_id"]: s for s in reg["strategies"]}

    # ── #1: Deactivate XB-ORB-EMA-ATRTrail-MES ───────────────────────────────
    sid = "XB-ORB-EMA-ATRTrail-MES"
    s = byid[sid]
    before = {k: s.get(k) for k in ("status", "controller_action", "controller_state", "lifecycle_stage")}
    s["status"] = "watch"
    s["controller_action"] = "OFF"
    s["controller_state"] = "VALIDATED"
    s["prior_state"] = before["controller_state"]
    s["lifecycle_stage"] = "watch"
    s["paper_execution"] = "DEACTIVATED"
    s["deactivation_date"] = TODAY
    s["deactivation_reason"] = (
        "Governance cleanup (org-hygiene audit, operator-authorized item #1, 2026-06-13). "
        "3rd Track 2 EXPERIMENTAL_FORWARD_CLOCK book (paper_ready=false, promotion_eligible=false, "
        "no promotion_date) found trading as status=probation+REDUCED_ON. Never promoted into paper "
        "probation. Same pattern as the 2 MNQ Chandelier books; missed by the MNQ-scoped cleanup. "
        "Frozen pending explicit operator governance. Records preserved; reactivatable."
    )
    s.setdefault("state_history", []).append({
        "date": TODAY, "from": before["controller_state"], "to": "DEACTIVATED_GOVERNANCE",
        "trigger": "Org-hygiene remediation (operator item #1) — undocumented Track 2 MES book frozen",
    })
    note = s.get("notes", "") or ""
    s["notes"] = (note + " | 2026-06-13 DEACTIVATED from paper execution (governance cleanup; "
                  "Track 2 / paper_ready=false; never promoted; records preserved).").strip()
    print(f"#1 ATRTrail-MES: {before} -> status=watch action=OFF lifecycle=watch", flush=True)

    # ── #3-core: provenance backfill (cite existing evidence; mark legacy gap) ─
    for csid, prov in CORE_PROVENANCE.items():
        cs = byid[csid]
        cs["approval_provenance"] = prov
        cs["approval_provenance_status"] = (
            "LEGACY_CORE_DOCUMENTED — approval evidence exists in repo/docs/git (see approval_provenance); "
            "discrete promotion_date predates the field convention (LEGACY_CORE_PROVENANCE_GAP, not invented)."
        )
        print(f"#3 {csid}: approval_provenance backfilled (LEGACY_CORE_DOCUMENTED)", flush=True)

    atomic_write_json(REG, reg)
    print("\nRegistry written atomically.", flush=True)

    # ── Verify against runner ────────────────────────────────────────────────
    import importlib
    import engine.strategy_universe as su
    importlib.reload(su)
    cfg = su.build_portfolio_config(include_probation=True)
    active = set(cfg["strategies"].keys())
    print("\n=== VERIFICATION ===", flush=True)
    print(f"  ATRTrail-MES execution-eligible: {sid in active} (expect False)", flush=True)
    print(f"  Ladder-MGC execution-eligible:   {'XB-ORB-EMA-Ladder-MGC' in active} (expect False — gated, contradictory)", flush=True)
    print(f"  active runner books: {len(active)}", flush=True)
    print(f"  core books still active: {[c for c in CORE_PROVENANCE if c in active]} (expect all 3)", flush=True)
    print(f"  fail_closed_exclusions: {cfg.get('_fail_closed_exclusions')}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "governance_remediation_2026-06-13.json"
    out.write_text(json.dumps({
        "item_1_deactivated": sid,
        "item_3_core_provenance_backfilled": list(CORE_PROVENANCE),
        "withheld_ladder_mgc_doclag": "WITHHELD — contradictory (promotion_date + paper_ready=false); surfaced for operator decision",
        "active_runner_books": sorted(active),
        "fail_closed_exclusions": cfg.get("_fail_closed_exclusions"),
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
