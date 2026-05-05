# DRAFT — Batch Register Pre-flight: XB Hybrids (14 PASS Candidates)

**Status:** Draft / pre-flight only. Staged 2026-05-05 evening per operator authorization. **NO registry mutations yet.** Operator reviews this draft before authorizing the actual append in a separate session (preserves the 2-step surgical pattern: evidence → packet → pre-flight → operator approval → append).

**Authority:** T2 for the eventual append (operator-gated). T1 diagnostic during pre-flight.

**Scope:** 14 PASS candidates from 2026-05-05 Forge work. 13 RECOMMEND-REGISTER + 1 DEFER per evaluation below.

---

## Section 1 — Exact list of 14 PASS candidates

| # | Candidate | Source memo |
|---|---|---|
| 1 | XB-PB-EMA-Ladder-MNQ | `batch_screen_2_2026-05-05.md` |
| 2 | XB-PB-EMA-Ladder-MCL | `forge_batch_2026-05-05.md` (runner sweep) |
| 3 | XB-PB-EMA-Ladder-MYM | `forge_batch_2026-05-05.md` |
| 4 | XB-BB-EMA-Ladder-MNQ | `batch_screen_2_2026-05-05.md` |
| 5 | XB-BB-EMA-Ladder-MGC | `forge_batch_2026-05-05.md` |
| 6 | XB-BB-EMA-Ladder-MCL | `forge_batch_2026-05-05.md` |
| 7 | XB-BB-EMA-Ladder-MYM | `forge_batch_2026-05-05.md` |
| 8 | XB-VWAP-EMA-Ladder-MGC | `vwap_cross_asset_2026-05-05.md` |
| 9 | XB-VWAP-EMA-Ladder-MCL | `vwap_cross_asset_2026-05-05.md` |
| 10 | XB-VWAP-EMA-Ladder-MYM | `vwap_cross_asset_2026-05-05.md` |
| 11 | XB-ORB-EMA-Chandelier-MNQ | `tail_engine_pool_expansion_2026-05-05.md` |
| 12 | XB-ORB-EMA-TimeStop-MNQ | `tail_engine_pool_expansion_2026-05-05.md` |
| 13 | XB-BB-EMA-AfternoonOnly-MGC | `tail_engine_smoke_2026-05-05.md` |
| 14 | HYB-VolMan-Sizing-overlay-MNQ | `validation_result_HYB-VolMan-Sizing_2026-05-05.md` |

---

## Section 2 — Evidence summary per candidate

| # | Candidate | Asset | Entry | Filter | Exit | Session | Archetype | Trades | PF | Net PnL | Max DD | Baseline comparison |
|---|---|---|---|---|---|---|---|---:|---:|---:|---:|---|
| 1 | XB-PB-EMA-Ladder-MNQ | MNQ | pb_pullback | ema_slope | profit_ladder | all_day | workhorse | 1,463 | 1.403 | +$29,297 | -$1,732 | XB-ORB-MNQ baseline PF 1.62 |
| 2 | XB-PB-EMA-Ladder-MCL | MCL | pb_pullback | ema_slope | profit_ladder | all_day | workhorse | 1,061 | 1.311 | +$7,386 | -$1,093 | XB-PB-MNQ PF 1.403 |
| 3 | XB-PB-EMA-Ladder-MYM | MYM | pb_pullback | ema_slope | profit_ladder | all_day | tail (n<500) | 462 | 1.351 | +$4,044 | -$772 | XB-PB-MNQ PF 1.403 |
| 4 | XB-BB-EMA-Ladder-MNQ | MNQ | bb_reversion | ema_slope | profit_ladder | all_day | workhorse | 667 | 1.245 | +$8,877 | -$2,505 | XB-ORB-MNQ baseline |
| 5 | XB-BB-EMA-Ladder-MGC | MGC | bb_reversion | ema_slope | profit_ladder | all_day | tail | 289 | 1.522 | +$4,146 | -$637 | XB-BB-MNQ PF 1.245 |
| 6 | XB-BB-EMA-Ladder-MCL | MCL | bb_reversion | ema_slope | profit_ladder | all_day | tail | 459 | 1.232 | +$2,474 | -$874 | XB-BB-MNQ PF 1.245 |
| 7 | XB-BB-EMA-Ladder-MYM | MYM | bb_reversion | ema_slope | profit_ladder | all_day | tail | 234 | 1.785 | +$3,877 | -$343 | XB-BB-MNQ PF 1.245 |
| 8 | XB-VWAP-EMA-Ladder-MGC | MGC | vwap_continuation | ema_slope | profit_ladder | all_day | tail | 368 | 1.219 | +$2,669 | -$1,870 | XB-VWAP-MNQ PF 1.056 (KILL) |
| 9 | XB-VWAP-EMA-Ladder-MCL | MCL | vwap_continuation | ema_slope | profit_ladder | all_day | workhorse | 502 | 1.283 | +$3,207 | -$1,407 | XB-VWAP-MNQ PF 1.056 |
| 10 | XB-VWAP-EMA-Ladder-MYM | MYM | vwap_continuation | ema_slope | profit_ladder | all_day | tail | 271 | 1.488 | +$3,164 | -$637 | XB-VWAP-MNQ PF 1.056 |
| 11 | XB-ORB-EMA-Chandelier-MNQ | MNQ | orb_breakout | ema_slope | chandelier | all_day | workhorse | 1,198 | 1.571 | +$32,471 | -$1,651 | XB-ORB-MNQ profit_ladder PF 1.62 |
| 12 | XB-ORB-EMA-TimeStop-MNQ | MNQ | orb_breakout | ema_slope | time_stop | all_day | tail | 1,198 | 1.486 | +$26,858 | -$1,862 | XB-ORB-MNQ profit_ladder PF 1.62 |
| 13 | XB-BB-EMA-AfternoonOnly-MGC | MGC | bb_reversion | session_afternoon | profit_ladder | afternoon | tail | 376 | 1.207 | +$1,783 | -$2,272 | XB-BB-MGC all-day PF 1.522 |
| 14 | HYB-VolMan-Sizing-overlay-MNQ | MNQ | orb_breakout | ema_slope | profit_ladder + inverse_vol_sizing overlay | all_day | workhorse | 1,198 | 1.612 | +$57,478 | -$2,399 | XB-ORB-MNQ baseline PF 1.62 |

---

## Section 3 — Proposed registry fields

All 13 RECOMMEND-REGISTER candidates share the same template (per the 2026-04-28 batch register pattern); HYB-VolMan-Sizing-overlay-MNQ stays DEFER.

### Common template (per-candidate values fill the ?)

```yaml
strategy_id: <as listed in §1>
strategy_name: null
status: idea  # always idea on first entry; T3 promotion separate
family: crossbreed_breakout  # matches existing XB-ORB-EMA-Ladder family
asset: <as listed>
session: <all_day | afternoon>
direction: both
source: forge_hybrid_generation_2026-05-05
source_category: internal
rule_summary: "<entry> entry + <filter> filter + <exit> exit on <asset>. stop_mult=2.0. Cheap-screen PASS on 2026-05-05; PF=<X.XXX>, n=<N>, max_DD=<$Y>."
notes: "Hybrid generated via Forge runner sweep 2026-05-05. Cheap-screen verdict <PASS|PASS-tail-engine>. Validated against XB-ORB-EMA-Ladder family donor pattern."
last_review_date: <append date>
review_priority: HIGH
lifecycle_stage: discovery
state_history: []
harvest_batch: forge_hybrid_generation_2026-05-05
batch_priority: <ordered by PF desc within family>
convergent_sources: []
relationships:
  parent: XB-ORB-EMA-Ladder-MNQ  # the original proven workhorse
  children: []
  related: [other XB-PB / XB-BB / XB-VWAP / XB-ORB-Chandelier / XB-ORB-TimeStop variants]
  salvaged_from: null
  components_used: ["<entry>", "<filter>", "<exit>"]  # explicit donor attribution
component_type: full_strategy
created_date: <append date>
triage_date: <append date>
triage_reason: hybrid_generation_lane_validation
triage_route: hybrid_generation_lane
session_tag: <session>
regime_tag: unclassified
reusable_as_component: false
extractable_components: []
crossbreeding_eligible: false
why_not_now: awaiting_full_validation_battery_post_phase_0
```

### Per-candidate components_used vector (the Item 2 plumbing test)

| # | strategy_id | components_used |
|---|---|---|
| 1 | XB-PB-EMA-Ladder-MNQ | `["pb_pullback", "ema_slope", "profit_ladder"]` |
| 2 | XB-PB-EMA-Ladder-MCL | same as #1 |
| 3 | XB-PB-EMA-Ladder-MYM | same as #1 |
| 4 | XB-BB-EMA-Ladder-MNQ | `["bb_reversion", "ema_slope", "profit_ladder"]` |
| 5 | XB-BB-EMA-Ladder-MGC | same as #4 |
| 6 | XB-BB-EMA-Ladder-MCL | same as #4 |
| 7 | XB-BB-EMA-Ladder-MYM | same as #4 |
| 8 | XB-VWAP-EMA-Ladder-MGC | `["vwap_continuation", "ema_slope", "profit_ladder"]` |
| 9 | XB-VWAP-EMA-Ladder-MCL | same as #8 |
| 10 | XB-VWAP-EMA-Ladder-MYM | same as #8 |
| 11 | XB-ORB-EMA-Chandelier-MNQ | `["orb_breakout", "ema_slope", "chandelier"]` ← new exit donor entry |
| 12 | XB-ORB-EMA-TimeStop-MNQ | `["orb_breakout", "ema_slope", "time_stop"]` ← new exit donor entry |
| 13 | XB-BB-EMA-AfternoonOnly-MGC | `["bb_reversion", "session_afternoon", "profit_ladder"]` ← session_afternoon as filter |

If approved, **13 entries simultaneously populate `relationships.components_used` for the first time at scale** — moves Item 2's broader plumbing question from "designed but empty" to "designed and flowing." Does NOT move the strict cross-pollination criterion (still 0/2; that requires `relationships.salvaged_from` populated, which today's salvages all failed).

### Sibling-family / parent-family note

The 13 RECOMMEND-REGISTER candidates form 4 sibling families under the proven XB-ORB-EMA-Ladder parent:

- **XB-PB sibling family:** #1, #2, #3 (pb_pullback entry, proven trio remainder)
- **XB-BB sibling family:** #4, #5, #6, #7 (bb_reversion entry)
- **XB-VWAP sibling family:** #8, #9, #10 (vwap_continuation entry)
- **XB-ORB-exit-alt sibling family:** #11, #12 (chandelier and time_stop exits)
- **XB-BB-AfternoonOnly oddball:** #13 (different filter; keep in BB family but flag)

---

## Section 4 — Duplication / correlation risk notes

| Pair / cluster | Risk | Note |
|---|---|---|
| XB-PB cross-asset (4 entries) | LOW within family | Same entry/filter/exit, different assets; behavior decorrelated by asset |
| XB-BB cross-asset (4 entries) | LOW within family | Same |
| XB-VWAP cross-asset (3 entries) | LOW within family | Same |
| XB-ORB-Chandelier-MNQ vs existing XB-ORB-EMA-Ladder-MNQ (probation) | **MEDIUM** | Same entry/filter/asset; only exit differs. Forward behavior likely 80%+ correlated. Operator may want to register as A/B test alongside parent rather than as full sister strategy. |
| XB-ORB-TimeStop-MNQ vs existing XB-ORB-EMA-Ladder-MNQ | **MEDIUM** | Same. Same A/B framing applies. |
| XB-BB-AfternoonOnly-MGC vs XB-BB-EMA-Ladder-MGC (this batch) | **MEDIUM** | Subset of trades from #5; weaker PF (1.207 vs 1.522). Operator may register only #5 (the all-day version) and SKIP #13 |
| HYB-VolMan-Sizing-overlay-MNQ vs XB-ORB-EMA-Ladder-MNQ | **HIGH** | Same trade signals; only sizing differs. 90%+ correlated. **Already DEFER recommendation.** |

**Cross-family correlation:** PB / BB / VWAP entries trade different signals on the same assets — meaningfully decorrelated by entry mechanism. Cross-family registration creates real diversification.

---

## Section 5 — Portfolio utility classification

| # | Candidate | Classification |
|---|---|---|
| 1-3 | XB-PB cross-asset (MNQ, MCL, MYM) | **Workhorse extension** + asset diversification (3 assets) |
| 4-7 | XB-BB cross-asset (MNQ, MGC, MCL, MYM) | **Workhorse extension** (4) + asset diversification + entry diversification |
| 8-10 | XB-VWAP cross-asset (MGC, MCL, MYM) | **Tail-engine candidates** (mostly tail-archetype n) + asset diversification |
| 11 | XB-ORB-Chandelier-MNQ | **Exit-diversification** (chandelier alt) — but high correlation with existing parent |
| 12 | XB-ORB-TimeStop-MNQ | **Exit-diversification** (time-stop alt) — same caveat |
| 13 | XB-BB-AfternoonOnly-MGC | **Duplicate-defer** (subset of #5 with weaker PF) |
| 14 | HYB-VolMan-Sizing-overlay-MNQ | **Duplicate-defer** (sizing overlay; high correlation with existing XB-ORB-MNQ) |

---

## Section 6 — Append risk per candidate

| # | Candidate | Risk |
|---|---|---|
| 1 | XB-PB-EMA-Ladder-MNQ | LOW |
| 2 | XB-PB-EMA-Ladder-MCL | LOW |
| 3 | XB-PB-EMA-Ladder-MYM | LOW |
| 4 | XB-BB-EMA-Ladder-MNQ | LOW |
| 5 | XB-BB-EMA-Ladder-MGC | LOW |
| 6 | XB-BB-EMA-Ladder-MCL | LOW |
| 7 | XB-BB-EMA-Ladder-MYM | LOW |
| 8 | XB-VWAP-EMA-Ladder-MGC | LOW |
| 9 | XB-VWAP-EMA-Ladder-MCL | LOW |
| 10 | XB-VWAP-EMA-Ladder-MYM | LOW |
| 11 | XB-ORB-EMA-Chandelier-MNQ | **MEDIUM** (correlation with existing XB-ORB-MNQ probation) |
| 12 | XB-ORB-EMA-TimeStop-MNQ | **MEDIUM** (same) |
| 13 | XB-BB-EMA-AfternoonOnly-MGC | **MEDIUM** (subset of #5 with weaker PF) |
| 14 | HYB-VolMan-Sizing-overlay-MNQ | **HIGH** (already DEFER) |

---

## Section 7 — Final recommendation per candidate

| # | Candidate | Recommendation | Reason |
|---|---|---|---|
| 1 | XB-PB-EMA-Ladder-MNQ | **REGISTER** | Strong workhorse PASS; cross-asset PB family anchor |
| 2 | XB-PB-EMA-Ladder-MCL | **REGISTER** | Energy gap fill; PB family |
| 3 | XB-PB-EMA-Ladder-MYM | **REGISTER** | PB family asset coverage |
| 4 | XB-BB-EMA-Ladder-MNQ | **REGISTER** | BB family anchor |
| 5 | XB-BB-EMA-Ladder-MGC | **REGISTER** ★ | Strong tail-engine PF (1.522) |
| 6 | XB-BB-EMA-Ladder-MCL | **REGISTER** | Energy gap fill (BB version) |
| 7 | XB-BB-EMA-Ladder-MYM | **REGISTER** ★★ | Highest PF of the day (1.785) |
| 8 | XB-VWAP-EMA-Ladder-MGC | **REGISTER** | VWAP family asset coverage |
| 9 | XB-VWAP-EMA-Ladder-MCL | **REGISTER** | Energy gap fill (VWAP version) |
| 10 | XB-VWAP-EMA-Ladder-MYM | **REGISTER** | VWAP family asset coverage |
| 11 | XB-ORB-EMA-Chandelier-MNQ | **REGISTER** | Validates exit-substitutability finding (chandelier ≈ profit_ladder); operator may want to keep separate registry entry to track A/B with parent |
| 12 | XB-ORB-EMA-TimeStop-MNQ | **REGISTER** | Same — exit-alt evidence; A/B value alongside parent |
| 13 | XB-BB-EMA-AfternoonOnly-MGC | **DEFER** | Subset of #5 with weaker PF (1.207 vs 1.522). Information value preserved in source memo; registration would add a noisy duplicate |
| 14 | HYB-VolMan-Sizing-overlay-MNQ | **DEFER** | Same as morning packet recommendation: 90%+ correlated with XB-ORB-MNQ (already in probation); ceiling effect bounded today's test; better to re-test on weaker baseline parent before registry |

**Net: 12 REGISTER + 2 DEFER.**

(Reduces from 14 PASSes total to 12 register-recommended after correlation/duplication review.)

---

## Section 8 — What this draft is NOT (operator constraints)

- Not a registry mutation (NO writes to `strategy_registry.json` today)
- Not a Lane A change (no runtime / portfolio / scheduler / checkpoint / hold-state)
- Not a promotion (all candidates enter as `status: idea` only; T3 promotion is a separate later decision)
- Not Phase 0 activation (still gated on TRS-2026-06 second clean cycle)
- Not committed yet — this is a `_DRAFT_` prefix file; lives uncommitted until operator approves the append in a separate session

---

## Section 9 — Operator decision required

1. **Approve registration of 12 candidates as listed?** (full / subset / none)
2. **Confirm DEFER for HYB-VolMan-Sizing-overlay-MNQ?** (or override to register)
3. **Confirm DEFER for XB-BB-EMA-AfternoonOnly-MGC?** (or override; cleaner option: omit from registry, keep evidence in smoke memo)
4. **Authorize batch register execution session** (likely tomorrow — same surgical pattern as 2026-04-28 batch register)

---

## Section 10 — If approved: append execution sequence

(For the SESSION AFTER this pre-flight is approved — not today)

```python
# Tomorrow's batch register session, scaffolded from 2026-04-28 pattern:

# 1. Load registry
# 2. For each of 12 approved candidates, build entry from common template (§3)
# 3. Append entries to strategies array
# 4. Update _generated field
# 5. atomic_write_json save
# 6. Verify count delta = +12
# 7. Spot-check 2-3 random entries for shape
# 8. Run operating_dashboard.py to confirm clean read
# 9. Single bundled commit: "Batch register 2026-05-XX — append 12 forge hybrid candidates"
```

Same discipline, different content. Fully transcription-mode, no design.

---

## Section 11 — Companion artifacts (full evidence trail)

| Memo | Content |
|---|---|
| `docs/fql_forge/hybrid_candidates_2026-05-05.md` | Original 5 candidate recipes |
| `docs/fql_forge/batch_screen_2_2026-05-05.md` | XB-PB-MNQ + XB-BB-MNQ first PASSes |
| `docs/fql_forge/forge_batch_2026-05-05.md` | Runner sweep cross-asset |
| `docs/fql_forge/vwap_cross_asset_2026-05-05.md` | VWAP cross-asset closeout |
| `docs/fql_forge/tail_engine_pool_expansion_2026-05-05.md` | Chandelier/TimeStop discovery |
| `docs/fql_forge/tail_engine_smoke_2026-05-05.md` | Remaining 5 smoke tests + BB-Aft-MGC PASS |
| `docs/fql_forge/operator_review_packet_2026-05-05.md` | Earlier 11-candidate packet (this supersedes it) |
| `research/fql_forge_batch_runner.py` | Runner with rotation logic + 19-candidate pool |
| `research/fql_forge_daily_loop.py` | Phase B autonomous loop (live) |

---

*Filed 2026-05-05. Draft only. No registry mutation. Operator approves before append in a separate session.*
