# XB-ORB-EMA-Ladder-MGC — Approval Review (OPEN) — 2026-06-14

> **Authority:** Operator decision (c) — leave gated pending validation/promotion review.
> **Status:** OPEN. Ladder-MGC remains **OFF / fail-closed / non-execution-eligible** until this review resolves.
> **Do NOT, until resolved:** activate it · clear `paper_ready`/`promotion_eligible` · add it to the CLAUDE.md approved table · clear/keep the `promotion_date` (the contradiction is preserved deliberately).
> Registry annotation: `governance_review` block on the entry (non-resolving). Contradictory fields left exactly as found.

## The contradiction

| Field | Value |
|---|---|
| `promotion_date` | `2026-05-28` |
| `paper_ready` | `False` |
| `promotion_eligible` | `False` |
| `status` / `controller_action` | `probation` / `REDUCED_ON` (but gated out of the runner by the fail-closed approval gate) |

A `promotion_date` implies paper approval; `paper_ready=false` + `promotion_eligible=false` say the opposite. Both were set by the same 2026-05-28 Phase 3 Offensive Forge Sprint v2.

## Preliminary evidence (does NOT resolve the review)

From `docs/reports/2026-05-28_offensive_sprint_v2_phase3.json`, the Ladder-MGC row:
- **`gate_verdict = PASS_TO_FORWARD_CLOCK`** (advanced to a *forward clock*, NOT promoted to paper), `archetype=WORKHORSE`, `blocker_reason=None`.
- Metrics: n=652, PF 1.601, median $8.76, max_dd -$1,026.92, win_rate 55.5%, sharpe 1.53.
- Notes: *"Track 1 forward-clock candidate… all gates clean. Reuses the xb_orb_ema_ladder strategy module."*

**Reading (tentative):** `paper_ready=false`/`promotion_eligible=false` appear to reflect the *true* state (forward-clock only). The `promotion_date=2026-05-28` looks like the **erroneous** field — a `PASS_TO_FORWARD_CLOCK` verdict should not stamp a paper `promotion_date`. Also: n=652 is well below the canonical workhorses (MNQ 1414 / MCL 898), and MGC-Ladder is not in the validated MNQ/MCL/MYM probation set, though CLAUDE.md notes the family is "cross-asset confirmed on all 4 equity-index micros" and "validated on … MGC".

## Review questions to resolve

1. Is the `2026-05-28` `promotion_date` legitimate paper-approval evidence, or stale/incorrect metadata from the sprint's bookkeeping?
2. Does Ladder-MGC meet the workhorse paper-promotion bar on its own merits (robustness GREEN, data-audit GREEN, concentration gates, cost-aware PF) under the current Packet Standard V1 — i.e., run it through the same gauntlet stop_run_reversal passed?
3. If approved → backfill correct, consistent metadata (clear the false flags, document promotion) + add to CLAUDE.md. If not → formally deactivate (status→watch) like the Track 2 books and null the erroneous `promotion_date`.

## Resolution paths (for a future, evidence-backed decision — not now)
- **APPROVE:** full V1 robustness + data-audit pass → clear `paper_ready`/`promotion_eligible`, keep `promotion_date`, add to CLAUDE.md, activate (within MGC exposure limits).
- **REJECT/DEMOTE:** does not meet the bar → `status→watch`, `controller_action→OFF`, null the erroneous `promotion_date`, mark RESEARCH_ONLY / forward-clock-shadow.

Until then: **gated, non-executing.** No mission impact (it is not in the runner).

## Cross-reference
- `docs/fql_forge/GOVERNANCE_REMEDIATION_2026-06-13.md`
- `docs/fql_forge/ORG_HYGIENE_ELITE_CLASSIFICATION_AUDIT_2026-06-13.md`
- `docs/reports/2026-05-28_offensive_sprint_v2_phase3.json`
- registry: `XB-ORB-EMA-Ladder-MGC.governance_review`
