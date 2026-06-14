"""Organizational Hygiene / Elite Classification Audit — 2026-06-13.

Operator-authorized system-wide governance audit. The Chandelier/ATRTrail issue
(Track 2 EXPERIMENTAL_FORWARD_CLOCK books trading as status=probation+REDUCED_ON
without formal promotion) may be systemic. Classify EVERY registered strategy and
flag any that is executable / runner-included / controller-enabled / exposure-
consuming WITHOUT formal approval evidence.

Classes:
  ELITE_APPROVED_PAPER            — in runner WITH approval evidence (core tier,
                                    or promotion_date, or CLAUDE.md documented set)
  CANDIDATE_REVIEW_ONLY          — validated/probation-ish, NOT in runner, awaiting review
  EXPERIMENTAL_FORWARD_CLOCK_SHADOW — Track 2 experimental, NOT in runner (properly shadowed)
  RESEARCH_ONLY                  — discovery/first_pass/validation/idea, not executing
  RETIRED_OR_KILLED              — status rejected/archived
  GOVERNANCE_MISMATCH            — in runner / exposure-consuming WITHOUT approval evidence
                                   (the activation-risk bucket — the thing we are hunting)

Boundaries: report-only. No registry/runner mutation. No deactivation performed
here — findings are surfaced for explicit operator authorization (same gated
rhythm as the MNQ cleanup).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.strategy_universe import build_portfolio_config  # noqa: E402

REG = ROOT / "research" / "data" / "strategy_registry.json"

# Approval allowlist from CLAUDE.md "Probation Portfolio" + core tier convention.
CLAUDE_DOCUMENTED = {
    "XB-ORB-EMA-Ladder-MNQ", "XB-ORB-EMA-Ladder-MCL", "XB-ORB-EMA-Ladder-MYM",
    "DailyTrend-MGC-Long", "ZN-Afternoon-Reversion", "TV-NFP-High-Low-Levels",
    "VolManaged-EquityIndex-Futures", "Treasury-Rolldown-Carry-Spread",
}
DEAD = {"rejected", "archived"}


def has_module(strategy_name) -> bool:
    if not strategy_name:
        return False
    return (ROOT / "strategies" / strategy_name / "strategy.py").exists()


def track_tag(notes: str) -> str:
    n = (notes or "").lower()
    if "experimental_forward_clock" in n or "track 2" in n:
        return "TRACK2_EXPERIMENTAL"
    if "track 1" in n:
        return "TRACK1"
    if "research_only" in n:
        return "RESEARCH_ONLY_TAG"
    return ""


def approval_evidence(s: dict) -> dict:
    sid = s["strategy_id"]
    prom = bool(s.get("promotion_date") or s.get("promoted_date"))
    core = s.get("status") == "core"
    documented = sid in CLAUDE_DOCUMENTED
    return {
        "promotion_date": prom,
        "core_tier": core,
        "claude_documented": documented,
        "has_any": prom or core or documented,
    }


def classify(s: dict, in_runner: bool) -> tuple[str, list[str]]:
    flags = []
    status = s.get("status")
    ev = approval_evidence(s)
    tag = track_tag(s.get("notes", ""))

    if status in DEAD:
        return "RETIRED_OR_KILLED", flags

    if in_runner:
        if ev["has_any"]:
            cls = "ELITE_APPROVED_PAPER"
            if ev["core_tier"] and not ev["promotion_date"]:
                flags.append("core_tier_no_promotion_date_doc")
            if ev["promotion_date"] and not ev["claude_documented"] and not ev["core_tier"]:
                flags.append("in_runner_promoted_but_not_in_CLAUDE.md_table (doc-lag)")
            return cls, flags
        # in runner, NO approval evidence -> the activation-risk mismatch
        flags.append("EXECUTABLE+RUNNER_INCLUDED+EXPOSURE_CONSUMING_WITHOUT_APPROVAL")
        if tag == "TRACK2_EXPERIMENTAL":
            flags.append("track2_experimental_running_as_probation (paper_ready=false)")
        return "GOVERNANCE_MISMATCH", flags

    # not in runner
    if tag == "TRACK2_EXPERIMENTAL":
        return "EXPERIMENTAL_FORWARD_CLOCK_SHADOW", flags
    if status in {"probation", "testing", "watch"} or s.get("lifecycle_stage") == "watch":
        return "CANDIDATE_REVIEW_ONLY", flags
    return "RESEARCH_ONLY", flags


def run():
    print("Organizational Hygiene / Elite Classification Audit — 2026-06-13\n", flush=True)
    reg = json.loads(REG.read_text())
    strategies = reg["strategies"]
    cfg = build_portfolio_config(include_probation=True)
    active = set(cfg["strategies"].keys())
    fail_closed = cfg.get("_fail_closed_exclusions", [])

    # Contradictory-approval state: promotion_date set BUT paper_ready/promotion_eligible False.
    contradictory = []
    for s in strategies:
        prom = s.get("promotion_date") or s.get("promoted_date")
        if prom and (s.get("paper_ready") is False or s.get("promotion_eligible") is False):
            contradictory.append({"strategy_id": s["strategy_id"], "promotion_date": prom,
                                  "paper_ready": s.get("paper_ready"),
                                  "promotion_eligible": s.get("promotion_eligible"),
                                  "in_runner": s["strategy_id"] in active})

    results = {}
    buckets = {}
    mismatches = []
    for s in strategies:
        sid = s["strategy_id"]
        in_runner = sid in active
        cls, flags = classify(s, in_runner)
        rec = {
            "strategy_id": sid, "asset": s.get("asset"), "status": s.get("status"),
            "controller_action": s.get("controller_action"),
            "executable_state": s.get("executable_state"),
            "lifecycle_stage": s.get("lifecycle_stage"),
            "portfolio_role": s.get("portfolio_role"),
            "promotion_date": s.get("promotion_date") or s.get("promoted_date"),
            "in_runner": in_runner, "has_module": has_module(s.get("strategy_name")),
            "track_tag": track_tag(s.get("notes", "")),
            "classification": cls, "flags": flags,
        }
        results[sid] = rec
        buckets.setdefault(cls, []).append(sid)
        if cls == "GOVERNANCE_MISMATCH":
            mismatches.append(rec)

    print(f"Total strategies: {len(strategies)} | active in runner: {len(active)}\n", flush=True)
    print("=== CLASS COUNTS ===", flush=True)
    for cls in ("ELITE_APPROVED_PAPER", "CANDIDATE_REVIEW_ONLY",
                "EXPERIMENTAL_FORWARD_CLOCK_SHADOW", "RESEARCH_ONLY",
                "RETIRED_OR_KILLED", "GOVERNANCE_MISMATCH"):
        print(f"  {cls:36s} {len(buckets.get(cls, []))}", flush=True)

    print("\n=== ELITE_APPROVED_PAPER (active, approved) ===", flush=True)
    for sid in sorted(buckets.get("ELITE_APPROVED_PAPER", [])):
        r = results[sid]
        fl = f" FLAGS={r['flags']}" if r["flags"] else ""
        print(f"  {sid:40s} {r['asset']:4s} {r['status']}/{r['controller_action']} prom={r['promotion_date']}{fl}", flush=True)

    print("\n=== *** GOVERNANCE_MISMATCH (activation-risk — running without approval) *** ===", flush=True)
    if not mismatches:
        print("  NONE — no remaining activation-risk mismatches.", flush=True)
    for r in mismatches:
        print(f"  !! {r['strategy_id']:38s} {r['asset']:4s} {r['status']}/{r['controller_action']} "
              f"lifecycle={r['lifecycle_stage']} tag={r['track_tag']}", flush=True)
        for f in r["flags"]:
            print(f"        - {f}", flush=True)

    print("\n=== EXPERIMENTAL_FORWARD_CLOCK_SHADOW (Track 2, not in runner) ===", flush=True)
    for sid in sorted(buckets.get("EXPERIMENTAL_FORWARD_CLOCK_SHADOW", [])):
        print(f"  {sid}", flush=True)

    print("\n=== FAIL-CLOSED GATE EXCLUSIONS (controller-eligible but blocked) ===", flush=True)
    for e in fail_closed:
        print(f"  {e['strategy_id']:40s} action={e.get('controller_action')} reason={e['reason']}", flush=True)
    if not fail_closed:
        print("  (none)", flush=True)

    print("\n=== CONTRADICTORY APPROVAL STATE (promotion_date + paper_ready/promotion_eligible=False) ===", flush=True)
    for c in contradictory:
        print(f"  {c['strategy_id']:40s} prom={c['promotion_date']} paper_ready={c['paper_ready']} "
              f"in_runner={c['in_runner']}", flush=True)
    if not contradictory:
        print("  (none)", flush=True)

    clean = len(mismatches) == 0
    # Phase 1C activation-risk gate: nothing executing without approval.
    # Contradictory books are a hygiene item (safely gated, NOT executing) — surfaced, not blocking.
    verdict = "ORG_HYGIENE_CLEAN" if clean else "ORG_HYGIENE_MISMATCHES_FOUND"
    print(f"\n  ACTIVATION-RISK MISMATCHES: {len(mismatches)}", flush=True)
    print(f"  CONTRADICTORY-APPROVAL (gated, non-executing, needs operator decision): {len(contradictory)}", flush=True)
    print(f"  VERDICT: {verdict}", flush=True)
    print(f"  Phase 1C gate: {'PASS (activation-risk) — no book executes without approval' if clean else 'BLOCKED'}"
          f"{' | residual hygiene: '+str(len(contradictory))+' contradictory book(s) to resolve' if contradictory else ''}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "org_hygiene_elite_classification_audit_2026-06-13.json"
    out.write_text(json.dumps({
        "purpose": "System-wide elite classification + governance-mismatch audit",
        "boundaries": "report-only; no registry/runner mutation; no deactivation performed",
        "total_strategies": len(strategies), "active_in_runner": len(active),
        "class_counts": {k: len(v) for k, v in buckets.items()},
        "buckets": {k: sorted(v) for k, v in buckets.items()},
        "governance_mismatches": mismatches,
        "fail_closed_gate_exclusions": fail_closed,
        "contradictory_approval_state": contradictory,
        "all_results": results,
        "verdict": verdict,
        "phase1c_activation_risk_gate": "PASS" if clean else "BLOCKED",
        "residual_hygiene_contradictory_count": len(contradictory),
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    return verdict


if __name__ == "__main__":
    v = run()
    sys.exit(0 if v == "ORG_HYGIENE_CLEAN" else 1)
