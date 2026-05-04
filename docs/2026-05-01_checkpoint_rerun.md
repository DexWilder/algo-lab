# May 1 Checkpoint — Re-Run after Investigation Lane Closure

**Filed:** 2026-05-04
**Reviewer:** Operator (Chase) + Claude (joint)
**Decision:** **Remain in stable state** (PASS-with-warn)

This is the re-run checkpoint per `docs/MAY_1_CHECKPOINT_TEMPLATE.md`, executed after the date-mismatch investigation lane (`docs/treasury_rolldown_date_mismatch_lane.md`) produced its scoped fix. Companion to the original anomaly checkpoint at `docs/2026-05-01_checkpoint.md`, which remains as historical record of the failed first attempt.

**What changed since the original checkpoint:**
- Wrapper fix committed (`933e6a2`): Option 2 convention adopted (TRS-YYYY-MM = hold month); `_spread_id` now derives next-month with year-wrap; `run_monthly_rebalance` rewritten to look back to prior calendar month
- Manual post-fix re-fire executed under lane authority (commit context preserved in row's `notes` field)
- All 7 verification checks executed against the new TRS-2026-05 row

---

## Section 1 — Monthly path execution integrity

| Check | Source | Outcome |
|---|---|---|
| Launchd fired cleanly | Original 2026-05-01 fire SKIPPED per B.2 anomaly; row written by manual post-fix re-fire (lane authority, commit `933e6a2`). Documented in row's `notes` field. | **OK** (with manual-refire context) |
| Exactly one new row written | `logs/spread_rebalance_log.csv`: 4 lines, TRS-2026-05 count = 1, TRS-2026-04 count = 1, TRS-2026-03 count = 1 | **OK** |
| Idempotency verified | Re-run `--dry-run --date 2026-05-01` returns `[2026-05-01] TRS-2026-05 already logged (rebalance_date 2026-04-30) — skip.` New non-misleading message confirms idempotency-by-spread_id works. | **OK** |

**Summary:** **clean**.

---

## Section 2 — Spread log integrity

| Check | Outcome |
|---|---|
| Row matches `generate_spread_signals()` expectation | **OK** — rebalance_date matches (2026-04-30), long matches (ZF), short matches (ZB) |
| `realized_pnl_prior_spread` reconciles against seeded TRS-2026-04 | **PASS-with-WARN** — previous_long/short legs match TRS-2026-04 (ZF/ZB ✓), realized_pnl_prior = $507.81 (non-zero, sign-consistent). WARN: `days_held_prior_spread=30` reflects strategy convention (signal entry 2026-03-31 → 2026-04-30) while seed TRS-2026-04 has placeholder rebalance_date 2026-04-12. Cosmetic only — does not affect any operational behavior. See Section 7. |
| Schema integrity (14 cols) | **OK** — all 14 columns present, no corruption |
| Spread identity preserved | **OK** — spread_id, legs, prices populated for all 3 rows |

**Summary:** **clean-with-warn** (Check 5 WARN, documented).

---

## Section 3 — Out-of-band probation handling quality

| Check | Outcome |
|---|---|
| No spillover into `logs/trade_log.csv` | **OK** — both greps empty |
| Drift monitor excludes Treasury-Rolldown | **WARN** — Treasury-Rolldown does not appear in EXCLUDED block (only VolManaged-EquityIndex-Futures does). Treasury-Rolldown also NOT in UNCATALOGUED LIVE (which would be FAIL). Pre-existing condition (B.3 from Thursday pre-flight) — drift monitor reads `trade_log.csv`, not `spread_rebalance_log.csv`. Not caused by the fix; not in this lane's scope. See Section 7. |
| Registry `execution_path` field unchanged | **OK** (no registry changes during the lane) |
| Controller_action still OFF | **OK** (no controller changes) |

**Summary:** **clean-with-warn** (Check 7 WARN, documented).

---

## Section 4 — Divergence summary vs Golden Snapshot 2026-04-14

| Dimension | Snapshot | Now | Delta |
|---|---|---|---|
| Active core count | 3 | 3 | 0 |
| Active probation (intraday) | 6 | 5 | -1 (already-known archive of MomPB-6J / NoiseBoundary) |
| Active probation (out-of-band) | 1 | 1 | 0 |
| Registry divergences contained | 8 | 8 | 0 |
| Launchd agents loaded | 10 | 10 | 0 |
| MYM data state | resolved | resolved | 0 |
| Other data-pipeline gaps | none | none | 0 |
| Unpushed commits | 0 | 0 | 0 |
| HEAD commit | `434a4a0` (snapshot) | `933e6a2` (lane fix) | docs + 1 narrow code commit per investigation lane authority |

**Expected delta shape:** docs-only HEAD advance during hold + 1 narrow lane-authorized code commit. **Confirmed.**

---

## Section 5 — Health stack freshness

| Layer | State |
|---|---|
| `research/logs/.watchdog_state.json` | **fresh** |
| `research/data/watchdog_state.json` | **fresh** (last write 2026-05-01 17:30) |
| `research/data/live_drift_log.json` | **fresh** |
| `research/reports/health_check_*.json` | **fresh** |
| SAFE_MODE gate verdict | **inactive** |

**Summary:** **all fresh**.

---

## Section 6 — Anomaly log

The original B.2 anomaly is **resolved** by the lane's wrapper fix. No new anomalies surfaced during the re-fire or the 7-check verification.

Two **known WARNs** carried forward as future follow-up items (NOT anomalies, NOT blockers):

1. **Seed/strategy date convention mismatch on TRS-2026-04** (Check 5 WARN). Seed has placeholder rebalance_date 2026-04-12; strategy now produces signals on calendar-end. The new TRS-2026-05 row's `days_held_prior_spread=30` reflects strategy view; strict date-arithmetic from the seed would say 18 days. Cosmetic. Per lane scope item 6: explicit decision to keep seed as-is, since the placeholder origin is already documented in `MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` seed table caption.

2. **Drift monitor doesn't surface Treasury-Rolldown** (Check 7 WARN). Monitor reads `trade_log.csv`, not `spread_rebalance_log.csv`. Treasury-Rolldown rows in spread log are invisible to the monitor. Pre-existing architectural gap, not introduced by this lane. Documented as a follow-up consideration; not in scope to fix here.

---

## Section 7 — Companion review: stale-probation batch review

**Status: still deferred.** Per the operator's Monday direction (carried forward from `docs/2026-05-01_checkpoint.md` Section 7): the stale-probation review is a separate decision surface and was deliberately not rendered today even when this re-run checkpoint clears. Reasons:

- The stale-probation review classifications are interlinked with checkpoint context, and Friday's NFP data point (TV-NFP) deserves to fold into the same review naturally
- Filing it today as a separate item adds operator-time without changing operational truth
- Better to render it at the next clean checkpoint cycle, when its decision-surface is fresh

The pre-flight draft `_DRAFT_2026-05-01_stale_probation_batch_review.md` remains staged.

---

## Decision

### ☑ Remain in stable state

**Criteria satisfied** (per `MAY_1_CHECKPOINT_TEMPLATE.md` Decision section):
- Sections 1, 5 all clean ✓
- Sections 2, 3 clean-with-warn (documented WARNs are pre-known and out of this lane's scope) ✓
- Section 4 deltas are docs-only + 1 lane-authorized narrow commit ✓
- Section 6 anomaly log is empty (the original anomaly is resolved; remaining items are documented WARNs, not anomalies) ✓
- Hold discipline maintained — code change scope was strictly bounded by lane authority

**Other branches NOT taken:**
- "Open fresh FX/STRUCTURAL design lane" — explicitly **NOT eligible** at this checkpoint per `MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` PASS-with-warn note: *"Do NOT open new lanes until WARNs are resolved."* Even if all WARNs were resolved, this branch requires "at least the second clean cycle" and this is the first.
- "Resume hardening queue" — not needed; operator has not flagged hardening priority over current cadence
- "Do not expand; investigate anomaly first" — no remaining anomaly; the original anomaly is closed

**Action:** Hold continues for one more Treasury-Rolldown cycle (until TRS-2026-06 fires next month). No new lanes opened. Confidence is being built one clean cycle at a time.

### What this decision authorizes:

- Hot lane Phase 0 Track A **does NOT start today** — would require "at least second clean cycle" eligibility, and even then it's a separate operator decision
- The investigation lane is **closed** (all 10 acceptance criteria met; see lane status log)
- The operating system continues per existing cadence
- Stale-probation review remains deferred to next clean checkpoint cycle
- The two WARNs become tracked follow-up items (documented here; NOT new lanes)

---

## Post-decision actions

1. ✓ This filed re-run checkpoint committed
2. ✓ Investigation lane status log updated to "lane closed"
3. **`docs/PORTFOLIO_TRUTH_TABLE.md`** — to update next-checkpoint section (target: TRS-2026-06 next month) — DEFERRED to a follow-up commit, not gating
4. **`docs/HOLD_STATE_CHECKLIST.md`** — to update: hold continues per "Remain in stable state" — DEFERRED to a follow-up commit, not gating
5. The original `docs/2026-05-01_checkpoint.md` (anomaly checkpoint) remains as historical record alongside this re-run

---

## Reviewer attestation

- **Reviewer:** Operator (Chase) + Claude (joint synthesis)
- **Checkpoint date executed:** 2026-05-04 (re-run after lane closure; original 2026-05-01 fire date preserved in row's `rebalance_date` and notes)
- **Decision rendered:** Remain in stable state
- **Rationale (one paragraph):** The investigation lane (`docs/treasury_rolldown_date_mismatch_lane.md`) closed cleanly with all 10 acceptance criteria met. The wrapper fix (commit `933e6a2`) implements the Option 2 convention; manual post-fix re-fire produced a TRS-2026-05 row whose content matches strategy signals exactly. All 7 verification checks resulted in 5 PASS + 2 WARN + 0 FAIL. Both WARNs are pre-known, documented, and out of the date-mismatch lane's scope. Hold discipline was maintained throughout — the only code change was the narrow lane-authorized wrapper fix. The system has earned the right to continue operating; it has not earned the right to open new lanes (one clean cycle is not yet "at least the second clean cycle").

---

*Filed 2026-05-04 alongside the original anomaly checkpoint. Hold continues until next monthly cycle clears (TRS-2026-06 fires first business day of June 2026 = 2026-06-01 Monday). Investigation lane closed.*
