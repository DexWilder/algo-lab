# Governance Remediation + Fail-Closed Execution Gate — 2026-06-13

> **Authority:** Operator-approved items #1 (deactivate ATRTrail-MES), #2 (fail-closed `build_portfolio_config` patch), #3 (hygiene fixes).
> **Status:** COMPLETE. **Org-hygiene VERDICT: ORG_HYGIENE_CLEAN** — activation-risk mismatches **1 → 0**. One residual *contradictory-approval* book (Ladder-MGC), safely gated (non-executing), surfaced for your decision.
> **Core principle codified:** **controller intent is NOT approval evidence.**

## Item #2 — Fail-closed execution-approval gate (the durable fix)

Patched `engine/strategy_universe.py`. New `execution_approval_check()` is consulted in `build_portfolio_config` **after** controller-eligibility but **before** a book is added to the runner — so it fires precisely when `controller_action` would have executed a book without approval:

- **Hard blocks (never execute, regardless of controller_action or promotion_date):** `EXPERIMENTAL_FORWARD_CLOCK` / Track 2 · `paper_ready=false` · `promotion_eligible=false`.
- **Positive approval required:** `status=core` OR `promotion_date` present OR membership in the CLAUDE.md-documented `APPROVED_EXECUTION_ALLOWLIST`. Otherwise → `BLOCKED_NO_APPROVAL_EVIDENCE`.
- **Fails closed with an audit reason** (logged + returned in `config["_fail_closed_exclusions"]`), never silently.

**Tests:** added `TestExecutionApprovalGate` (6 tests, all pass) proving experimental/paper_ready=false are blocked even with a promotion_date and REDUCED_ON, and that controller_action alone is not approval. The 6 pre-existing `test_strategy_universe` failures are unrelated (stale-date fixtures) and are **identical pre- and post-patch** — my patch introduces zero new failures.

## Item #1 — XB-ORB-EMA-ATRTrail-MES deactivated

Durable treatment (same as Chandelier): `status: probation→watch`, `controller_action: REDUCED_ON→OFF`, `lifecycle→watch`, `controller_state→VALIDATED`, `deactivation_reason` + `state_history` appended, notes appended. **Records preserved, reactivatable.** Now out of EVAL_STATES (controller can't revert) and gate-blocked as belt-and-suspenders.

## Item #3 — Hygiene

- **3 core books** (`ORB-MGC-Long`, `PB-MGC-Short`, `XB-PB-EMA-MES-Short`): backfilled `approval_provenance` citing **existing** evidence (status=core/lifecycle=deployed; docs/TARGET_PORTFOLIO.md + PORTFOLIO_TRUTH_TABLE.md + phase_5/6 deployment audits; PB-MGC-Short git `0328aad` "PROMOTED to 6th Parent"). Missing discrete `promotion_date` explicitly marked `LEGACY_CORE_PROVENANCE_GAP` — **not invented**.
- **XB-ORB-EMA-Ladder-MGC CLAUDE.md doc-lag fix: WITHHELD.** ⚠️ See below — the premise was invalidated.

## ⚠️ New finding surfaced by the gate — Ladder-MGC contradictory approval state

You authorized adding Ladder-MGC to the CLAUDE.md probation table as a clean "doc-lag" book. The fail-closed gate revealed it is **not** cleanly approved: it has `promotion_date=2026-05-28` **but also `paper_ready=False` AND `promotion_eligible=False`** (set by the same 2026-05-28 Phase 3 sprint). Documenting it as approved would contradict its own fields, so I **withheld** that change and left the record untouched. The gate blocks it (`BLOCKED_PAPER_READY_FALSE`) — safely non-executing.

This is the **only** contradictory-approval book in the registry (full scan confirmed). The other 3 Ladder books (MNQ/MCL/MYM) are clean (`paper_ready=None`, proper April promotions).

**Your decision needed for Ladder-MGC** (it is safely gated meanwhile):
- (a) It IS genuinely paper-ready (same validated `xb_orb_ema_ladder` code, cross-asset to gold) → clear `paper_ready`/`promotion_eligible`, then it executes and gets added to the CLAUDE.md table; or
- (b) It is NOT paper-ready (the flags are the truth; the promotion_date was premature) → formally deactivate it (status→watch) like the Track 2 books; or
- (c) Leave gated pending a proper validation/promotion review.

## Operator-requested deliverables

| Deliverable | Result |
|---|---|
| Before/after mismatch count | **1 → 0** |
| Proof ATRTrail-MES no longer execution-eligible | ✅ `build_portfolio_config` excludes it (status=watch/OFF) — verified |
| Proof gate blocks paper_ready=false / experimental even if REDUCED_ON | ✅ unit tests + live: Ladder-MGC (REDUCED_ON, paper_ready=false) → `BLOCKED_PAPER_READY_FALSE`; ATRTrail (REDUCED_ON, Track 2) → `BLOCKED_EXPERIMENTAL_FORWARD_CLOCK` |
| ORG_HYGIENE_CLEAN or precise blocker | **ORG_HYGIENE_CLEAN** (activation-risk = 0). Residual hygiene: 1 contradictory book (Ladder-MGC), gated/non-executing, awaiting your (a/b/c) decision |

## Final classification (166 strategies)

| Class | Count |
|---|---|
| ELITE_APPROVED_PAPER | 11 (all active, all with approval evidence) |
| CANDIDATE_REVIEW_ONLY | 2 |
| EXPERIMENTAL_FORWARD_CLOCK_SHADOW | 3 (the 3 Track 2 books, all now shadowed/non-executing) |
| RESEARCH_ONLY | 86 |
| RETIRED_OR_KILLED | 64 |
| **GOVERNANCE_MISMATCH** | **0** |

Active runner = 11 books, every one carrying positive approval evidence.

## Phase 1C gate

**Activation-risk gate: PASS** — no book executes without approval, and the leak class is now structurally impossible (`build_portfolio_config` fails closed). Per your instruction I am **stopping before wiring** `WH-MNQ-stop_run_reversal`. Remaining before I'd request Phase 1C wiring: your decision on the Ladder-MGC contradiction (a/b/c) — it's non-blocking for activation-risk (it's gated), but it's the last open governance item.

## Cross-reference
- `engine/strategy_universe.py` (gate) · `tests/test_strategy_universe.py` (TestExecutionApprovalGate)
- `research/governance_remediation_2026-06-13.py` + `.json`
- `research/org_hygiene_elite_classification_audit_2026-06-13.py` + `.json`
- `docs/fql_forge/ORG_HYGIENE_ELITE_CLASSIFICATION_AUDIT_2026-06-13.md`
- `docs/fql_forge/MNQ_EXPOSURE_RATIONALIZATION_2026-06-13.md`
