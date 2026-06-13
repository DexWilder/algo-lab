# Organizational Hygiene / Elite Classification Audit — 2026-06-13

> **Authority:** Operator — full system-wide governance audit before any new paper activation; the Chandelier issue may be systemic.
> **Status:** COMPLETE. **VERDICT: ORG_HYGIENE_MISMATCHES_FOUND (1).** **Phase 1C gate: BLOCKED** until the one remaining mismatch is resolved (operator-authorized).
> **Artifacts:** `research/org_hygiene_elite_classification_audit_2026-06-13.py` + `research/data/fql_forge/reports/org_hygiene_elite_classification_audit_2026-06-13.json`.
> **Boundaries:** report-only · no registry/runner mutation · **no deactivation performed** — findings surfaced for explicit authorization (same gated rhythm as the MNQ cleanup).

## 1. The hypothesis was correct — the issue was systemic

Three Track 2 `EXPERIMENTAL_FORWARD_CLOCK` candidates were wired on **2026-05-28** (Offensive Forge Sprints v1 + v2) as `status=probation + REDUCED_ON + EXECUTABLE` despite `paper_ready=false, promotion_eligible=false, promotion_date=None`. At the runner level that is **indistinguishable from an approved probation book** (`build_portfolio_config` picks them up). The MNQ cap caught two; the audit caught the third (on MES):

| Track 2 book | Asset | Caught by | State now |
|---|---|---|---|
| XB-ORB-EMA-Chandelier-MNQ | MNQ | MNQ cap → cleanup ✅ | EXPERIMENTAL_FORWARD_CLOCK_SHADOW (deactivated) |
| XB-PB-EMA-Chandelier-MNQ | MNQ | MNQ cap → cleanup ✅ | EXPERIMENTAL_FORWARD_CLOCK_SHADOW (deactivated) |
| **XB-ORB-EMA-ATRTrail-MES** | **MES** | **this audit** ⚠️ | **GOVERNANCE_MISMATCH — still active** |

## 2. Classification of all 166 strategies

| Class | Count |
|---|---|
| ELITE_APPROVED_PAPER | 12 |
| CANDIDATE_REVIEW_ONLY | 1 |
| EXPERIMENTAL_FORWARD_CLOCK_SHADOW | 2 |
| RESEARCH_ONLY | 86 |
| RETIRED_OR_KILLED | 64 |
| **GOVERNANCE_MISMATCH** | **1** |

Rubric: `RETIRED_OR_KILLED` = status rejected/archived. In-runner → `ELITE_APPROVED_PAPER` if approval evidence (core tier, `promotion_date`, or CLAUDE.md probation table); else `GOVERNANCE_MISMATCH`. Not-in-runner → `EXPERIMENTAL_FORWARD_CLOCK_SHADOW` (Track 2), `CANDIDATE_REVIEW_ONLY` (probation/testing/watch), or `RESEARCH_ONLY`.

## 3. ⚠️ The one remaining activation-risk mismatch

**`XB-ORB-EMA-ATRTrail-MES`** — `probation / REDUCED_ON / EXECUTABLE`, `lifecycle=discovery`, `role=None`, `promotion_date=None`, notes: *"Track 2 EXPERIMENTAL_FORWARD_CLOCK… paper_ready=false, promotion_eligible=false"* (source: offensive_forge_sprint_v2_phase3_2026-05-28; wired via commit `2e1537f`).

It is **executable + runner-included + controller-enabled + exposure-consuming without approval evidence** — the exact Chandelier pattern. **Recommendation:** apply the identical durable deactivation (status→`watch`, controller_action→`OFF`, lifecycle→`watch`, documented reason + state_history; records preserved). This needs your explicit authorization — it's a MES book, outside the MNQ cleanup I was authorized for, so I have **not** touched it.

## 4. ELITE_APPROVED_PAPER (12 active, approved) — with minor doc-hygiene flags

All 12 active books have approval evidence. Two non-blocking hygiene flags:

- **`XB-ORB-EMA-Ladder-MGC`** — promoted 2026-05-28 (Track 1, governed) but **not in the CLAUDE.md probation table** (doc-lag). Recommend adding it to the CLAUDE.md Probation Portfolio.
- **3 core-tier books** (`ORB-MGC-Long`, `PB-MGC-Short`, `XB-PB-EMA-MES-Short`) — `status=core, lifecycle=deployed`, but **no `promotion_date`**. These are deliberately-established core strategies (not mismatches), but they lack explicit promotion provenance in the registry. Recommend backfilling an approval record for each.

The 8 documented probation/legacy books (XB-ORB-Ladder MNQ/MCL/MYM, DailyTrend-MGC, ZN-Afternoon-Reversion, TV-NFP, VolManaged, Treasury-Rolldown) are all in the CLAUDE.md set — clean.

## 5. Root cause + proposed fail-closed patch (for your approval)

**Root cause:** the 2026-05-28 sprint scripts wired Track 2 experimental candidates with `status=probation + controller_action=REDUCED_ON`. `build_portfolio_config` gates execution on `status not in {rejected,archived}` + `controller_action` eligibility — it has **no positive check for approval evidence**. So a Track 2 "shadow" book is executed exactly like an approved probation book.

**Proposed fail-closed patch (NOT yet applied — needs your OK, it touches the core runner gate `engine/strategy_universe.py`):**
> `build_portfolio_config` should refuse to include any strategy that lacks **positive approval evidence** — e.g. require `promotion_date` present OR `portfolio_role` set OR membership in an explicit approved-execution allowlist — and **exclude (fail-closed) any `EXPERIMENTAL_FORWARD_CLOCK` / `paper_ready=false` strategy** regardless of `controller_action`. Track 2 forward-clocks would then need an explicit, separate execution path rather than masquerading as probation. This mirrors the existing `PENDING_EXECUTABLE_MODULE` fail-closed gate.

This would make the Chandelier/ATRTrail class of leak structurally impossible going forward.

## 6. Phase 1C gate

**BLOCKED.** Per your sequence, stop_run_reversal wiring waits until the audit "confirms no remaining activation-risk mismatches." It found one. To clear the gate:
1. Authorize deactivation of `XB-ORB-EMA-ATRTrail-MES` (same treatment as Chandelier).
2. (Recommended) authorize the fail-closed `build_portfolio_config` patch so this can't recur.
3. (Optional hygiene) CLAUDE.md doc-lag fix for Ladder-MGC + core-book approval backfills.

Then I'll re-run the audit to confirm `ORG_HYGIENE_CLEAN` and return with a clean Phase 1C approval request.

## 7. Cross-reference
- `docs/fql_forge/MNQ_EXPOSURE_RATIONALIZATION_2026-06-13.md`
- `docs/fql_forge/DSCL_SOURCE_VERIFICATION_MNQ_2026-06-13.md`
- `docs/fql_forge/paper_packet_drafts/WAVE1_PHASE1A_PORT_VERIFICATION_2026-06-13.md`
- mismatch provenance: commit `2e1537f`, `docs/reports/2026-05-28_offensive_sprint_v2_phase3.json`
