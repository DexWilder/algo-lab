# Autonomous Runner Safety Contract (2026-07-02)

> Unattended nonstop is valuable ONLY if it runs the FULL loop safely. A scheduled runner that "only runs tests" recreates
> the blind-automation failure class we just fixed. This contract is the precondition for any scheduled/unattended Forge.
> **Status: NOT YET ACTIVE. Proceed turn-by-turn for 1–2 more clean cycles first; then activate if the loop stays clean.**

## Hard prohibitions (fail-closed)
- **Report-only ONLY.** No capital-facing mutation, ever.
- No registry / scheduler / portfolio / paper / live / sizing changes.
- No candidate promotion past SCREEN_PASS (ladder operator-gated at FAMILY_CONFIRMED+; PAPER_APPROVED+ operator-only).
- **No WH / primary / validated / paper-ready language.**
- No `DATA_BLOCKED` without a certificate; no `FAMILY_EXHAUSTED` without data-tier proof.
- No analyzing a data file still being written (provenance rule).
- No terminal-only discoveries (everything → inbound/queue/ledger).
- Obey data-spend threshold: **≤$25/pull, ≤$100/day**, report-only; anything larger → surface to operator, do not pull.

## Full loop — MANDATORY every packet (no shortcuts)
`queue → preflight → data-validation (validate_data_file) → expression-validation → artifact-detectors → test →
adversarial-review → trial-ledger (+failure_class) → learning_state (post_run_learning_hook) → family-map/tier-matrix →
candidate-ladder (if relevant) → dashboard → guardrails → self-audit → commit/push → backlog 0`.
If ANY step is skipped or fails → **stop the batch, surface an exception**, do not continue.

## Stop / surface conditions (exception-driven output only)
Emit a concise report ONLY when: (a) a candidate reaches packet-grade threshold; (b) a blocker/P0 appears; (c) the scheduled
batch completes; (d) operator action is required (e.g., data-spend > threshold, capital-adjacent decision). Otherwise silent.
**Hard stop** if guardrails return P0 or self-audit returns BROKEN → halt, surface, await operator.

## Run parameters (to set at activation)
- **Batch size:** N packets per run (default 3–5 RUN_NOW items).
- **Cadence:** e.g., every 2–4h or daily (operator sets).
- **Max data spend:** ≤$25/run, ≤$100/day (hard).
- **Output report path:** `research/logs/autonomous_run_<ts>.md` + inbound entry.
- **Commit/push proof:** every completed packet-cycle commits; backlog must be 0 at run end.
- **Rollback / no-op on failure:** if a test errors, record failure artifact, skip item, continue; if the loop can't close
  (guardrail/self-audit fail), no-op the remaining batch and surface. Never leave partial uncommitted mutation.

## WH1 weighting (mission focus)
Every batch must be **WH1-weighted** (MNQ/MES/MYM index workhorse). Diversifier lanes (e.g. spreadMR_GC) run but must not
dominate. The runner reads `mission_class` (see MISSION_CLASSIFICATION) and prioritizes INDEX_DIRECT > INDEX_REGIME_INPUT >
DIVERSIFIER > LOW_PRIORITY_ARCHIVE.

## Activation checklist (all must be true)
- [ ] 1–2 turn-by-turn cycles ran the full loop clean AFTER the mid-pull-race fix.
- [ ] guardrails P0=0, self-audit CLEAN, backlog 0 sustained.
- [ ] mission_class present on all RUN_NOW items.
- [ ] this contract committed.
- [ ] operator explicitly authorizes scheduled activation (cadence + batch size).
