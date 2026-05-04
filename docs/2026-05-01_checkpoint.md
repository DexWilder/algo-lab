# May 1 Checkpoint — Filed 2026-05-04

**Date executed:** 2026-05-04 (filing day; verification fired 2026-05-01 17:10 ET as scheduled)
**Reviewer:** operator + Claude (joint)
**Decision:** **Do not expand; investigate anomaly first**

This document is the filed version of the checkpoint per `docs/MAY_1_CHECKPOINT_TEMPLATE.md`. It merges Thursday's pre-flight (`_DRAFT_2026-05-01_checkpoint_outline.md`) with Friday's actual verification outcomes.

**Why filed Monday, not Friday:** Friday's launchd fire produced the predicted B.2 anomaly (no TRS-2026-05 row written). Per the operating discipline, the operator did NOT render a "basically fine" checkpoint when the prerequisites failed. Filing waited until Monday for clean diagnosis + decision rendering.

---

## Section 1 — Monthly path execution integrity

| Check | Source | Outcome |
|---|---|---|
| Launchd fired cleanly | `research/logs/treasury_rolldown_monthly_stdout.log` line `[2026-05-01] Not first business day of month — skip.` | **FAIL** — agent fired but produced no row |
| Exactly one new row written | `logs/spread_rebalance_log.csv` TRS-2026-05 count = 0 | **FAIL** — no TRS-2026-05 row exists |
| Idempotency verified | Re-run `--dry-run --date 2026-05-01` returns same skip message | **N/A** — there's nothing to be idempotent about because the initial write never happened |

**Summary:** **broken** — Section 1 prerequisites failed. The launchd fire executed but the script's date-matching logic did not produce a write.

---

## Section 2 — Spread log integrity

| Check | Outcome |
|---|---|
| Row matches `generate_spread_signals()` expectation | **N/A** — no TRS-2026-05 row to compare; root cause IS that no row exists |
| `realized_pnl_prior_spread` reconciles against seeded TRS-2026-04 | **N/A** |
| Schema integrity (14 columns, no corruption) | **OK** — schema intact, 2 seeded rows + header |
| Spread identity preserved (legs, prices populated) | **OK** — for the 2 seeded rows |

**Summary:** **broken on the new-row dimensions** (because no new row exists); existing seeded rows clean.

---

## Section 3 — Out-of-band probation handling quality

| Check | Outcome |
|---|---|
| No spillover into `logs/trade_log.csv` | **OK** — empty grep for both `Treasury-Rolldown-Carry-Spread` and `TRS-2026` |
| Drift monitor still treats Treasury-Rolldown as `excluded_from_strategy_drift` | **WARN** — Treasury-Rolldown does NOT appear in the EXCLUDED block (only VolManaged-EquityIndex-Futures does). Treasury-Rolldown also does NOT appear in UNCATALOGUED LIVE. The monitor appears to surface only strategies with trade evidence; with 0 spread rows, Treasury-Rolldown is invisible. Pre-flight Section B.3 anticipated this. |
| Registry `execution_path` field reads `"out_of_band_monthly_batch"` | **OK** (assumed; not changed during the failed fire) |
| `controller_action` still `OFF` | **OK** (assumed; not changed during the failed fire) |

**Summary:** **clean-with-warn** on the isolation dimensions (no spillover, no controller action change). The drift-monitor invisibility is a documentation/expectation mismatch, not a real isolation breach.

---

## Section 4 — Divergence summary vs Golden Snapshot 2026-04-14

| Dimension | Golden snapshot | Checkpoint state | Delta |
|---|---|---|---|
| Active core count | 3 | 3 | 0 |
| Active probation (intraday) count | 6 | 5 (after MomPB-6J / NoiseBoundary archive) | -1 (already-known archive) |
| Active probation (out-of-band) count | 1 | 1 | 0 |
| Registry divergences contained | 8 | 8+ (now includes B.2) | +1 (today's anomaly) |
| Launchd agents loaded | 10 | 10 (all 9 FQL + openclaw gateway) | 0 |
| MYM data state | resolved | resolved | 0 |
| Other symbols with data-pipeline gaps | none | none | 0 |
| Unpushed commits | 0 | 0 | 0 |
| HEAD commit | `434a4a0` | `e2a2848` (last commit pre-checkpoint) | docs-only advance per hold |

**Expected delta shape (per template):** docs-only HEAD advance. **Confirmed** — the only HEAD movement during the hold was documentation commits (gate verdict, batch register, hot lane architecture, build sequence, outside-intel doc, elite operating principles, settings.json + SessionStart hook).

---

## Section 5 — Health stack freshness (as of filing 2026-05-04)

| Layer | State |
|---|---|
| `research/logs/.watchdog_state.json` (shell recovery) | **fresh** (watchdog ran 2026-05-01 17:30; weekend gap normal — agent runs every 5 min on weekdays per CLAUDE.md, weekends quieter) |
| `research/data/watchdog_state.json` (SAFE_MODE) | **fresh** (last write 2026-05-01 17:30) |
| `research/data/live_drift_log.json` (drift monitor) | **fresh** (verified Thursday) |
| `research/reports/health_check_*.json` (hygiene) | **fresh** (Friday's daily pipeline ran clean) |
| SAFE_MODE gate verdict | **inactive** (no SAFE_MODE active) |

**Summary:** **all fresh**.

---

## Section 6 — Anomaly log

**Single material anomaly:**

**B.2 Strategy/wrapper date-matching mismatch — confirmed, deeper than originally diagnosed.**

Pre-flight (Thursday) diagnosed the surface symptom: strategy fires on month-END (entry_date 2026-04-30), wrapper expects month-START (execution_date 2026-05-01) → script's `_is_first_business_day_of_month` returns False → silent skip with misleading message.

**Filing-day diagnosis (Monday) revealed a deeper layer:** even if the wrapper picked up entry_date 2026-04-30, the resulting spread_id would be `TRS-2026-04` (because `_spread_id` derives from the entry_date's calendar month). This would conflict with the seeded `TRS-2026-04` row (which used a placeholder rebalance_date of 2026-04-12 at seed time).

**Two distinct conventions are in conflict:**

| Layer | Convention | Implication |
|---|---|---|
| Strategy (`generate_spread_signals`) | Rebalance happens on month-END; the entry_date is the LAST trading day of the month | A rebalance opening on 2026-04-30 is "April's rebalance" |
| Spread log seed (per `MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` table) | TRS-2026-05 means "the May rebalance" — i.e., spread_id is named for the month the position is HELD | A rebalance opening on 2026-04-30 to be held through May is "May's rebalance" |
| Wrapper script (`_spread_id`) | `f'TRS-{rebalance_date.year}-{rebalance_date.month:02d}'` | Uses the date itself; matches strategy convention, NOT seed convention |

The seeded TRS-2026-04 with rebalance_date 2026-04-12 was a placeholder at hold-entry time (data ended 2026-04-14). It implicitly used the seed convention, but the wrapper script uses the strategy convention. **This convention conflict was hidden until the first live fire.**

No other anomalies. Hold discipline was maintained throughout — all commits since 2026-04-14 are documentation/preparation only, no runtime changes.

---

## Section 7 — Companion review: stale-probation batch review

Status: **deferred to next clean checkpoint.** Per the operator's Monday direction: "do not let the stale review cosmetically complete a checkpoint day that was structurally blocked." The pre-flight draft at `_DRAFT_2026-05-01_stale_probation_batch_review.md` remains uncommitted. Friday's NFP fire data point (and any other Friday/weekend evidence) will fold into the review when it is rendered alongside the next clean checkpoint.

---

## Decision

### ☑ Do not expand; investigate anomaly first

**Criteria satisfied** (per `MAY_1_CHECKPOINT_TEMPLATE.md` Decision section):
- Section 1 contains FAIL ✓
- Section 2 contains FAIL on new-row dimensions ✓
- Section 6 has unexplained anomaly (B.2 + the deeper convention conflict) ✓
- Treasury-Rolldown produced NO row → "internal inconsistencies" criterion does not apply, but the FAIL on Sections 1+2 alone satisfies the branch

**Other branches NOT eligible:**
- "Remain in stable state" — fails Sections 1, 2 cleanliness
- "Open fresh FX/STRUCTURAL design lane" — fails the prerequisite that "Remain" criteria are met
- "Resume hardening queue" — fails the same prerequisite

**Action:** Hold remains in effect. A narrow investigation lane is opened for the **specific anomaly only** (B.2 + the convention conflict). Per template line 154: "Do not use this outcome as permission to open unrelated research." The investigation lane scope is staged at `docs/treasury_rolldown_date_mismatch_lane.md` (filed alongside this checkpoint).

**What does NOT happen as a result of this decision:**
- Hot lane Phase 0 Track A does NOT start today (gated on a clean checkpoint, which we do not have)
- Donor catalog consolidation does NOT begin
- No Phase 0 build work, no new launchd jobs, no schema changes
- No unrelated research lanes
- No rendering of stale-probation review as a "checkpoint completion" cosmetic
- No FX/STRUCTURAL gap-fill exploration

**What DOES happen:**
- Investigation lane proceeds per its scope doc
- Hold continues
- Once the anomaly is fixed AND verified (TRS-2026-05 successfully writes on a re-fire AND the convention is reconciled), this checkpoint template can be re-run

---

## Post-decision actions

1. ✓ This filed checkpoint committed to repo with message `Checkpoint 2026-05-01: Investigate anomaly first`
2. **`docs/PORTFOLIO_TRUTH_TABLE.md`** — to update with: hold extension, anomaly status, next-checkpoint condition (when investigation lane closes cleanly)
3. **`docs/HOLD_STATE_CHECKLIST.md`** — to update: hold does NOT exit on 2026-05-01; new exit condition is "investigation lane closes + re-run checkpoint clears"
4. **No new lane scope docs** beyond the investigation lane
5. **Pre-flight draft cleanup:** `_DRAFT_2026-05-01_checkpoint_outline.md` may be deleted (its purpose was pre-flight; this filed checkpoint replaces it). The companion `_DRAFT_2026-05-01_stale_probation_batch_review.md` remains staged for the next clean checkpoint cycle.

---

## Reviewer attestation

- **Reviewer:** Operator (Chase) + Claude (joint synthesis)
- **Checkpoint date executed:** 2026-05-01 (verification fire) → 2026-05-04 (filing)
- **Decision rendered:** Do not expand; investigate anomaly first
- **Rationale (one paragraph):** The 17:10 ET launchd fire on 2026-05-01 returned the misleading "Not first business day of month — skip" message that Thursday's pre-flight Section B.2 specifically anticipated. No TRS-2026-05 row was written. Monday filing-day diagnosis confirmed the root cause — strategy/wrapper convention mismatch — and revealed an additional layer (spread_id naming convention conflict between seed and runtime). Sections 1 and 2 are FAIL; Section 3 is clean-with-warn (drift monitor invisibility is a documentation gap, not an isolation breach); Sections 4 and 5 are clean (hold discipline preserved). The "Investigate anomaly first" decision is the only template branch consistent with the evidence. Hot lane Phase 0 work is explicitly gated until the investigation closes and a re-run checkpoint clears.

---

*Filed 2026-05-04 alongside `docs/treasury_rolldown_date_mismatch_lane.md` (the narrow investigation scope). Hold remains in effect. The next checkpoint runs after the investigation lane closes cleanly.*
