# Operator Review Packet — 12 PASS Candidates Ready for Registry Append

**Filed:** 2026-05-05 (end-of-day capture per operator's "value is making sure winners are captured cleanly" direction)
**Authority:** T2 for registry append (operator decision)
**Scope:** all candidates that PASSed cheap-screen today, packaged for surgical operator decision

---

## TL;DR

12 candidates passed cheap-screen today across 3 workhorse families and one sizing overlay. Operator review needed: which to register as `idea` entries, which to defer, which to retire.

**Recommendation in one line:** register the 11 cross-asset workhorse extensions (XB-PB / XB-BB / XB-VWAP families); defer HYB-VolMan-Sizing-overlay (today's PASS-with-WARN was bounded by ceiling effect; needs different baseline test before registry).

---

## Full PASS list (sortable for review)

| # | Candidate | Family | Asset | n | PF | Median | Net PnL | Max DD | Recommend |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | XB-PB-EMA-Ladder-MNQ | PB workhorse | MNQ | 1,463 | 1.403 | +$7.26 | +$29,297 | -$1,732 | **REGISTER** ★ strongest PB result |
| 2 | XB-PB-EMA-Ladder-MCL | PB workhorse | MCL | 1,061 | 1.311 | +$6.00 | +$7,386 | -$1,093 | **REGISTER** (energy gap fill) |
| 3 | XB-PB-EMA-Ladder-MYM | PB workhorse | MYM | 462 | 1.351 | +$3.00 | +$4,044 | -$772 | **REGISTER** (n<500 → tail-engine archetype) |
| 4 | XB-BB-EMA-Ladder-MNQ | BB workhorse | MNQ | 667 | 1.245 | +$3.26 | +$8,877 | -$2,505 | **REGISTER** ★ strongest BB on MNQ |
| 5 | XB-BB-EMA-Ladder-MGC | BB workhorse | MGC | 289 | 1.522 | n/a | +$4,146 | -$637 | **REGISTER** ★ tail-engine very strong |
| 6 | XB-BB-EMA-Ladder-MCL | BB workhorse | MCL | 459 | 1.232 | n/a | +$2,474 | -$874 | **REGISTER** (energy gap fill, tail-engine) |
| 7 | XB-BB-EMA-Ladder-MYM | BB workhorse | MYM | 234 | **1.785** | +$9.00 | +$3,877 | -$343 | **REGISTER** ★★ HIGHEST PF of the day, tail-engine |
| 8 | XB-VWAP-EMA-Ladder-MGC | VWAP workhorse | MGC | 368 | 1.219 | -$0.24 | +$2,669 | -$1,870 | **REGISTER** (tail-engine; WATCH if median trade matters) |
| 9 | XB-VWAP-EMA-Ladder-MCL | VWAP workhorse | MCL | 502 | 1.283 | +$3.50 | +$3,207 | -$1,407 | **REGISTER** (energy gap fill) |
| 10 | XB-VWAP-EMA-Ladder-MYM | VWAP workhorse | MYM | 271 | 1.488 | +$9.00 | +$3,164 | -$637 | **REGISTER** (tail-engine, strong PF) |
| 11 | HYB-VolMan-Sizing-overlay-MNQ | Sizing overlay on XB-ORB-MNQ | MNQ | 1,198 | 1.612 | n/a | +$57,478 | -$2,399 | **DEFER** — PASS-with-WARN; ceiling effect; re-test on weaker baseline first |

(Item 12 = the original XB-ORB-MNQ baseline reproduction itself — already in registry as `probation`, no append needed.)

---

## Recommended registration metadata (for the 11 REGISTER candidates)

If operator approves, each entry would populate the following fields. This is the spec — actual append happens in a separate batch register pre-flight per the established discipline.

```yaml
strategy_id: <name above>
strategy_name: null
status: idea
family: crossbreed_workhorse  # consistent across the 3 sister families
asset: <MNQ|MCL|MYM|MGC>
session: all_day  # matches XB-ORB-EMA-Ladder family
direction: both
source: forge_hybrid_generation_2026-05-05
source_category: internal
rule_summary: "<entry_name> entry + ema_slope filter + profit_ladder exit. Stop_mult 2.0, target_mult 4.0, trail_mult 2.5 (target/trail currently ignored by exit_profit_ladder). Cheap-screen verdict PASS on YYYY-MM-DD."
notes: "Hybrid generated via runner sweep 2026-05-05. Cheap-screen PF=<X.XXX>, n=<N>, max_DD=<$Y>. Validated against XB-ORB-EMA-Ladder family donor pattern. Operator approved registration <date>."
last_review_date: <append date>
review_priority: HIGH
lifecycle_stage: discovery
state_history: []
harvest_batch: forge_hybrid_generation_2026-05-05
batch_priority: <ordered by PF desc>
convergent_sources: []
relationships:
  parent: XB-ORB-EMA-Ladder-MNQ  # the original proven workhorse
  children: []
  related: [other XB-PB / XB-BB / XB-VWAP variants in this batch]
  salvaged_from: null
  components_used: ["<entry_name>", "ema_slope", "profit_ladder"]  # explicit donor attribution
component_type: full_strategy
created_date: <append date>
triage_date: <append date>
triage_reason: hybrid_generation_lane_validation
triage_route: hybrid_generation_lane
session_tag: all_day
regime_tag: unclassified
reusable_as_component: false
extractable_components: []
crossbreeding_eligible: false
why_not_now: awaiting_full_validation_battery_post_phase_0
```

**The critical fields per Item 2's plumbing test:** `relationships.components_used` populated for the first time in registry history (across 11 entries simultaneously) and `triage_route: hybrid_generation_lane` exercised for real. If approved, this single batch register would move Item 2's broader plumbing question (does the catalog actually carry traffic?) from "designed but empty" to "designed and flowing."

**It does NOT move the cross-pollination criterion (still 0/2)** — that requires `relationships.salvaged_from` populated, which today's salvage attempts all failed to deliver.

---

## Deferral rationale for HYB-VolMan-Sizing-overlay-MNQ

PASS-with-WARN today. Headline metrics looked strong (PF 1.612, +$57k), but:
- It's the SAME entry/filter/exit as XB-ORB-EMA-Ladder-MNQ (already in registry as probation), with only sizing changed
- Ceiling effect bounded the test — XB-ORB-MNQ's prop-sim pass rate is already 96.4%, leaving no room for the overlay to demonstrate value
- Registering it now would create a second probation entry that's 90%+ correlated with the existing XB-ORB-MNQ — violates portfolio-utility decorrelation principle from `post_may1_build_sequence.md` §4.2
- Better path: re-test inverse_vol_sizing on a weaker baseline parent (DailyTrend-MGC if recoverable, OR construct a deliberately-weak baseline) where the overlay's value can show

**Recommend:** mark `inverse_vol_sizing` as portable-validated in donor catalog; do NOT register XB-ORB-MNQ-VolMan-overlay as a sister strategy.

---

## What this packet does NOT do

- Does NOT mutate the registry (operator approves; then a separate batch register pre-flight executes the append per the established 04-28 batch register pattern)
- Does NOT change runtime / portfolio / scheduler / checkpoint / hold state
- Does NOT promote any of these to probation (they enter as `status: idea`; promotion is a separate later T3 decision)
- Does NOT activate Phase 0 (still gated on TRS-2026-06 second clean cycle)
- Does NOT register the WATCH candidates (XB-PB-MES/MGC, XB-BB-MES, XB-VWAP-MES) — they wait for either calibration improvement or operator decision to register-with-watch-tag

---

## Three operator decisions required

1. **Registration approval (yes/no/partial).** All 11, subset, or none?
2. **Batch register pre-flight authorization.** If yes, when to stage the pre-flight (recommend tomorrow morning; same surgical pattern as Tuesday 2026-04-28's batch register).
3. **Lane A status.** No change unless operator explicitly authorizes — these enter as `idea` only; no portfolio addition, no controller change, no scheduler change.

---

## Related artifacts (today's evidence trail)

| File | Content |
|---|---|
| `docs/fql_forge/hybrid_candidates_2026-05-05.md` | Original 5 hybrid candidate recipes |
| `docs/fql_forge/_DRAFT_validation_plan_HYB-VolMan-Sizing.md` | HYB-VolMan validation plan |
| `docs/fql_forge/_DRAFT_validation_plan_HYB-FX-SessionTransition.md` | HYB-FX validation plan |
| `docs/fql_forge/validation_result_HYB-VolMan-Sizing_2026-05-05.md` | HYB-VolMan PASS-with-WARN result |
| `docs/fql_forge/validation_result_HYB-FX-SessionTransition_*.md` | HYB-FX 1.5× / 1.0× / 0.75× calibration sequence |
| `docs/fql_forge/batch_screen_2026-05-05.md` | Batch #1: 3 KILL + 1 RETEST |
| `docs/fql_forge/batch_screen_2_2026-05-05.md` | Batch #2: 2 PASS + 2 KILL |
| `docs/fql_forge/calibration_watch_2026-05-05.md` | WATCH calibration follow-up |
| `docs/fql_forge/filter_sweep_2026-05-05.md` | ema_slope load-bearing finding |
| `docs/fql_forge/vwap_cross_asset_2026-05-05.md` | VWAP MNQ-specific finding |
| `docs/fql_forge/day_summary_2026-05-05.md` | Day summary as of mid-day |
| **`docs/fql_forge/operator_review_packet_2026-05-05.md`** | **This file — operator decision interface** |
| `research/fql_forge_batch_runner.py` | The batch runner (CLI tool, dry-run/report-only) |
| `research/scratch/batch_*_2026-05-05.py`, `validate_HYB_*.py` | Scratch validation scripts |

---

## End-of-day suggested next move

After operator reviews this packet:
- If approve registration → tomorrow's Forge session opens with batch register pre-flight (same surgical pattern as 2026-04-28's 34-entry append)
- If defer → tomorrow's session can run additional sweeps (filter alt on different parents, tail-engine candidates, more cross-asset extensions)
- If decline → preserve evidence; revisit at next clean checkpoint

**Day-end recommendation:** close today here. The day produced 31 candidate evaluations, 3 architecture answers, 12 PASS candidates, and a working batch runner. That's substantial real evidence. Tomorrow's first move depends on operator decision on this packet.

---

*Filed 2026-05-05. Lane B / Forge. The 12 PASS candidates are operator-review-eligible. No Lane A surfaces touched.*
