# May 1 Checkpoint Template

**Purpose:** Decision-framing wrapper for the Treasury-Rolldown 2026-05-01
first-live-rebalance checkpoint. Reads the raw verification output from
`docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` and produces exactly one
of four decisions.

**Relationship to other docs:**
- `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` = facts (7 checks, pass/warn/fail per check)
- **This document** = synthesis (reads the facts, decides what to do next)
- `docs/HOLD_STATE_CHECKLIST.md` = governs the hold this checkpoint is designed to exit
- `docs/GOLDEN_SNAPSHOT_2026-04-14.md` = the "before" reference for comparison

---

## Execution timing

This checkpoint runs **after 2026-05-01's first eligible Treasury-Rolldown
rebalance fire.** Do not execute this template before:

1. The launchd agent has fired on 2026-05-01 (or the next business day)
2. `logs/spread_rebalance_log.csv` has been inspected for the new row (or its absence)
3. `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` has been executed and its outcome table filled in

Premature checkpoint execution is a hold breach per `docs/HOLD_STATE_CHECKLIST.md`.

---

## Section 1 — Monthly path execution integrity

Inputs: verification checks 1–3 from `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`.

| Check | Source | Outcome |
|---|---|---|
| Launchd fired cleanly | `research/logs/treasury_rolldown_monthly_stdout.log` | ☐ OK  ☐ WARN  ☐ FAIL |
| Exactly one new row written (no duplicate) | `logs/spread_rebalance_log.csv` TRS-2026-05 count | ☐ OK  ☐ WARN  ☐ FAIL |
| Idempotency verified | Re-run `--dry-run --date 2026-05-01` returns "already logged" | ☐ OK  ☐ WARN  ☐ FAIL |

**Summary:** ☐ clean · ☐ clean-with-warn · ☐ broken

---

## Section 2 — Spread log integrity

Inputs: verification checks 2, 4, 5 + `docs/SPREAD_LOG_AUDIT_PROCEDURE.md` verdict.

| Check | Outcome |
|---|---|
| Row matches `generate_spread_signals()` expectation | ☐ OK  ☐ WARN  ☐ FAIL |
| `realized_pnl_prior_spread` reconciles against seeded TRS-2026-04 | ☐ OK  ☐ WARN  ☐ FAIL |
| Schema integrity (14 columns, no corruption) per audit procedure | ☐ OK  ☐ WARN  ☐ FAIL |
| Spread identity preserved (`spread_id`, legs, prices populated) | ☐ OK  ☐ WARN  ☐ FAIL |

**Summary:** ☐ clean · ☐ clean-with-warn · ☐ broken

---

## Section 3 — Out-of-band probation handling quality

Inputs: verification checks 6, 7.

| Check | Outcome |
|---|---|
| No spillover into `logs/trade_log.csv` | ☐ OK  ☐ WARN  ☐ FAIL |
| Drift monitor still treats Treasury-Rolldown as `excluded_from_strategy_drift` | ☐ OK  ☐ WARN  ☐ FAIL |
| Registry `execution_path` field still reads `"out_of_band_monthly_batch"` | ☐ OK  ☐ WARN  ☐ FAIL |
| `controller_action` still `OFF` (intraday runner doesn't attempt MYM-style hosting) | ☐ OK  ☐ WARN  ☐ FAIL |

**Summary:** ☐ clean · ☐ clean-with-warn · ☐ broken

---

## Section 4 — Divergence summary (compare to `docs/GOLDEN_SNAPSHOT_2026-04-14.md`)

What changed between 2026-04-14 and the checkpoint date?

| Dimension | Golden snapshot | Checkpoint state | Delta |
|---|---|---|---|
| Active core count | 3 | | |
| Active probation (intraday) count | 6 | | |
| Active probation (out-of-band) count | 1 | | |
| Registry divergences contained | 8 | | |
| Launchd agents loaded | 10 | | |
| MYM data state | resolved (2026-04-14) | | |
| Other symbols with data-pipeline gaps | none | | |
| Unpushed commits | 0 | | |
| HEAD commit | `434a4a0` | | |

**Expected delta shape:** most rows unchanged; `HEAD commit` advances by at most a handful of docs-only commits (hold-allowed). Anything beyond that should surface as an anomaly in Section 6.

---

## Section 5 — Health stack freshness

| Layer | State as of checkpoint |
|---|---|
| `research/logs/.watchdog_state.json` (shell recovery) | ☐ fresh (<30 min)  ☐ stale |
| `research/data/watchdog_state.json` (SAFE_MODE) | ☐ fresh (<30 hr)  ☐ stale |
| `research/data/live_drift_log.json` (drift monitor) | ☐ fresh (<30 hr)  ☐ stale |
| `research/reports/health_check_*.json` (hygiene) | ☐ fresh (<30 hr)  ☐ stale |
| SAFE_MODE gate verdict | ☐ inactive  ☐ active (blocking) |

**Summary:** ☐ all fresh · ☐ some stale · ☐ critical stale

---

## Section 6 — Anomaly log

List anything observed in this checkpoint that was not predicted by the hold window or the verification procedure. Examples:

- Unexpected new strategies in the runner universe
- Scheduler jobs with new ERROR rates
- Data freshness regressions on symbols other than MYM
- Registry field changes outside the hold-allowed categories
- Launchd agents that silently unloaded
- Divergences that were not in the golden snapshot's 8-item contained list

(Leave empty if nothing anomalous.)

---

## Decision output

Based on Sections 1–6, render **exactly one** decision. The summary lines below are the decision criteria; pick the one whose criteria are fully satisfied.

### ☐ Remain in stable state

**Criteria:** Sections 1, 2, 3, 5 all "clean" or "clean-with-warn"; Section 4 deltas are docs-only; Section 6 anomaly log is empty; overall hold discipline was maintained.

**Action:** Hold continues for one more Treasury-Rolldown cycle (until TRS-2026-06). No new lanes, no hardening queue yet. Confidence is being built one cycle at a time.

### ☐ Open fresh FX/STRUCTURAL design lane

**Criteria:** All of "Remain in stable state" criteria met, PLUS this is at least the second clean cycle (not the first), PLUS operator judgment agrees the portfolio is stable enough to accept new research exposure.

**Action:** Open a new research lane for FX or STRUCTURAL gap-fill. Lane scope becomes a separate design pass — this decision authorizes the exploration, not the implementation. Hold on runtime code continues until the lane produces a concrete candidate.

### ☐ Resume hardening queue

**Criteria:** All of "Remain in stable state" criteria met, PLUS operator judgment that governance/tooling debt accumulated during the hold deserves priority over new research.

**Action:** Begin the hardening queue in the pre-defined order: 3 → 5 → 1 → 2 → 4. Each item has its scope pre-staged per `docs/GOLDEN_SNAPSHOT_2026-04-14.md`. The hardening is itself a series of controlled commits, not a lane change.

### ☐ Do not expand; investigate anomaly first

**Criteria:** Any of:
- Section 1, 2, or 3 contains a FAIL
- Section 5 has critical-stale health layer
- Section 6 anomaly log has any entry that can't be explained by normal hold-window activity
- Treasury-Rolldown produced a row but the row has internal inconsistencies

**Action:** Hold remains in effect. Open a narrow investigation lane **for the specific anomaly only.** Do not use this outcome as permission to open unrelated research. Fix the anomaly, verify with a follow-up check, then re-run this checkpoint template.

---

## Post-decision actions

Regardless of decision, always:

1. **Commit this filled-in template** to the repo with message `Checkpoint 2026-05-01: [decision]`.
2. **Update `docs/PORTFOLIO_TRUTH_TABLE.md`** to reflect the post-checkpoint state (next checkpoint date, any new probation/archive transitions, any lane status changes).
3. **Update `docs/HOLD_STATE_CHECKLIST.md`** if the hold is exiting (mark the exit, record the outcome).
4. **If opening a new lane:** create the lane's scope doc before any code is written; link it from CLAUDE.md Key Documentation.
5. **If starting hardening:** pick up item #3 from the hardening queue as first target; scope per `docs/GOLDEN_SNAPSHOT_2026-04-14.md`'s hardening queue section.

---

## Reviewer attestation

- **Reviewer:** _________________________
- **Checkpoint date executed:** _________________________
- **Decision rendered:** _________________________
- **Rationale (one paragraph):** _________________________

---

*This template converts verification facts into a decision. The decision
is not "how did Treasury-Rolldown perform" — that's a separate strategic
question for the second cycle. The decision is "did the out-of-band path
work, and what does the system earn the right to do next?"*
