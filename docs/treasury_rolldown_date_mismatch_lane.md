# Treasury-Rolldown Date-Mismatch Investigation Lane

**Filed:** 2026-05-04 alongside `docs/2026-05-01_checkpoint.md`
**Authorized by:** May 1 checkpoint → "Investigate anomaly first" decision branch
**Authority:** T2 within the scope below; T3 changes (e.g., promotion / demotion / portfolio role) remain checkpoint-gated and out of scope.
**Status:** Open. Hold remains in effect until lane closes AND re-run checkpoint clears.

---

## Anomaly statement

The 17:10 ET launchd fire on 2026-05-01 produced no TRS-2026-05 row in `logs/spread_rebalance_log.csv`. Stdout logged `[2026-05-01] Not first business day of month — skip.` Filing-day diagnosis (`docs/2026-05-01_checkpoint.md` Section 6) confirmed two conflicting layers:

1. **Surface symptom (B.2):** `_is_first_business_day_of_month(2026-05-01, trading_days)` returns False because 2026-05-01 is not in the strategy's `trading_days` (the strategy's most recent entry_date is **2026-04-30** — last business day of April).

2. **Deeper convention conflict:** `_spread_id` derives the spread_id from the entry_date's calendar month. A signal with entry_date 2026-04-30 maps to `TRS-2026-04`, NOT `TRS-2026-05`. The seeded `TRS-2026-04` row (placeholder rebalance_date 2026-04-12 from hold-entry seeding) was implicitly named under a DIFFERENT convention — "the month the position is held" — than what the runtime script uses.

The wrapper, the strategy, and the seed are operating under three different conventions about what `TRS-{year}-{month}` means.

---

## In-scope work

The lane is authorized to do all of the following:

1. **Resolve the convention question.** Decide which of the three layers should be canonical for `TRS-{year}-{month}` naming. Recommended (subject to operator confirmation):
   - **Strategy + wrapper convention** is canonical: `TRS-{year}-{month}` = the calendar month in which the rebalance OPENED. The seeded TRS-2026-04 row's `rebalance_date` and naming were placeholders that got the convention wrong.
   - This means the next live row should be `TRS-2026-04` with `rebalance_date = 2026-04-30`, NOT `TRS-2026-05`.

2. **Fix the script's `_is_first_business_day_of_month` logic** to either:
   - (a) Pick the most recent strategy entry_date that hasn't been logged yet (then the wrapper is signal-driven, not calendar-driven), OR
   - (b) Recognize that "fire on first business day of month" should look BACK to find the most recent end-of-prior-month signal (then the wrapper's launchd schedule stays the same, but the date-matching is corrected).

3. **Reconcile or replace the seeded TRS-2026-04 row.** If strategy convention is canonical, the seed's rebalance_date should be updated to 2026-03-31 (the strategy's actual TRS-2026-03 entry; or whatever the strategy says TRS-2026-04 should be — currently `entry_date 2026-03-31` maps to TRS-2026-03 already in the seed, so the seed structure may need full re-seeding).

4. **Patch the misleading skip message.** `_is_first_business_day_of_month` returns False under two distinct conditions but prints one message. Differentiate them so future operators can disambiguate from log output alone.

5. **Update `MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`'s seed table** to reflect the resolved convention. The current note ("TRS-2026-04's rebalance_date 2026-04-12 reflects end-of-available-data at seed time") is no longer accurate if seeds are re-aligned.

6. **Re-fire the script manually with the correct date** to produce the missing rebalance row. Verify it writes cleanly under the resolved convention.

7. **Re-run `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`** end-to-end against the new row.

8. **If verification PASSES,** re-run `docs/MAY_1_CHECKPOINT_TEMPLATE.md` and re-render the checkpoint decision (which may then become "Remain in stable state" or "Resume hardening queue" or "Open lane" depending on which other criteria are met).

---

## Out-of-scope work

The lane is NOT authorized to do any of the following:

- Open the FX/STRUCTURAL design lane
- Start hot lane Phase 0 Track A
- Begin donor catalog consolidation
- Build `hybrid_generator.py` skeleton or any other Phase 0 / Phase 1 / Phase 2 work
- Add new launchd jobs
- Add new schema fields to the strategy registry
- Modify any other strategy's code (only `run_treasury_rolldown_spread.py` and possibly `strategies/treasury_rolldown_carry/strategy.py`)
- Render the stale-probation batch review (deferred to next clean checkpoint per `docs/2026-05-01_checkpoint.md` Section 7)
- Any unrelated research or refactoring opportunistically discovered during the fix
- Auto-promote Treasury-Rolldown out of probation regardless of fix outcome

If any in-scope work surfaces an opportunity for out-of-scope improvement, **log it for a future checkpoint and proceed only with the in-scope item.** Scope creep is a hold breach.

---

## Acceptance criteria (lane closes when ALL pass)

1. ☐ Convention question resolved with one written canonical decision (in this doc or a small companion)
2. ☐ Wrapper script fixed so it produces a row when the strategy has a fresh signal
3. ☐ Patched skip-message differentiates the two failure modes
4. ☐ Re-fire produces a row whose `spread_id`, `rebalance_date`, legs, and prices match the strategy's signal output
5. ☐ Idempotency verified: re-running the script after the row exists returns "already logged"
6. ☐ Seeded TRS-2026-04 row reconciled (kept-as-is with documentation, OR updated, OR replaced — explicit decision logged)
7. ☐ `MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` seed table updated to match
8. ☐ All 7 verification checks PASS or PASS-with-warn on the new row
9. ☐ Re-run `MAY_1_CHECKPOINT_TEMPLATE.md` produces a non-anomaly decision branch (Remain / Open lane / Hardening)
10. ☐ Filed re-run checkpoint committed

Until all 10 are ☑, the hold extension persists.

---

## Approach (suggested sequence — operator confirms order)

1. **Decide convention** (operator + Claude joint discussion). 30 minutes max. Document the decision in this lane doc as an addendum.
2. **Code the script fix** (small diff — likely <50 LOC). Branch + isolated commit. Run unit tests if any exist; otherwise pipe-test with `--dry-run`.
3. **Reconcile the seed** per the convention decision. Likely a single-row update or a re-seed (both are auditable).
4. **Update `MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`** (just the seed table + the note about the placeholder).
5. **Manually re-fire** the script with appropriate `--date`. Inspect the resulting row.
6. **Run all 7 verification checks** against the new state. Fill outcome table.
7. **Re-run checkpoint template.** Render the new decision. File and commit.
8. **Mark this lane closed** by updating the acceptance criteria checkboxes and adding a closing note.

---

## What today (2026-05-04) does and does not include

**Today:**
- ✓ Filed `docs/2026-05-01_checkpoint.md` (the anomaly checkpoint)
- ✓ Filed this lane scope doc
- ✗ No code changes
- ✗ No re-fire
- ✗ No convention decision rendered yet (operator needs to think through the trade-offs)

**Lane-active days (TBD, post-2026-05-04):**
- Convention decision (Step 1)
- Code fix (Step 2)
- Seed reconciliation (Step 3)
- Doc update (Step 4)
- Re-fire + verification (Steps 5-7)
- Re-run checkpoint (Steps 7-8)
- Lane closure

---

## Status log

| Date | Event |
|---|---|
| 2026-05-01 17:10 | Launchd fire produced skip message — anomaly observed |
| 2026-05-04 (filing day) | B.2 root cause + deeper convention conflict diagnosed; lane opened |
| _____ | Convention decision rendered |
| _____ | Script fix committed |
| _____ | Re-fire produces TRS row |
| _____ | Verification re-run PASSES |
| _____ | Checkpoint re-run produces non-anomaly decision |
| _____ | Lane closed |

---

## What this lane is NOT

- Not a redesign of the Treasury-Rolldown strategy (the strategy's signal logic is correct as-is)
- Not a license to broaden into other probation strategy work
- Not a deferral of hot lane Phase 0 — Phase 0 is GATED on this lane closing AND a clean re-run checkpoint
- Not optional — the May 1 checkpoint cannot exit anomaly state until this lane closes

---

*Filed 2026-05-04. Hold continues until acceptance criteria all ☑ and the re-run checkpoint clears.*
