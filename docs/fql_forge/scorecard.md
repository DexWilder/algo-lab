# Scorecard

**Append-only daily proof-of-life + weekly Friday rollup.**

The scorecard is the single most important operational artifact.
Without it, there is no record of whether the machine is running.

**Rule:** append a dated block every day, regardless of how little
happened. Four consecutive days with thin entries is itself a signal.

---

## Daily entry format

Append at end of each work day. Five lines minimum:

```
## [YYYY-MM-DD]
- Advanced: <state transition(s) — e.g., "ABC: Inbox → In Progress; XYZ: Validation → Rejected">
- Produced artifact: <concrete thing that now exists — failure writeup, extracted component, validation report, memory payload, triage decision, OR "none — triage-only day" OR "none — blocked on [blocker type]">
- State change: <queue counts or notable transitions — e.g., "In Progress 3→4, Validation 2→2, Rejected +1">
- Stale cleared: <items aged past threshold that got advanced/closed — count or specific IDs, OR "none">
- Tomorrow: <next packet sketch or "continue [candidate]" or "[fallback mode name] day">
```

**Why "Produced artifact" is a separate line:** a day can be productive
without a validated-passed strategy. Failure writeups, extracted
components, rejection-with-reasons, and completed memory payloads are
all real compounding outputs. Validated passes are one kind of
artifact, not the only kind.

---

## Weekly Friday rollup format

At end of Friday (after the day's regular scorecard entry), append a
weekly rollup block:

```
## [YYYY-MM-DD] Weekly Rollup (week of [start] → [end])

### Throughput
- Validated artifacts produced this week: <count + one-liners>
- Items conclusively resolved: <count — validated + rejected + salvage-routed>
- Items opened: <count — new into Inbox + In Progress>
- Closure ratio: resolved / opened = <ratio>
- Reusable components added to memory: <count + list>

### Queue health
- Inbox: <count> items, oldest <Xd>
- In Progress: <count>, oldest <Xd>, blocked <count>
- Validation: <count>, oldest <Xd>, blocked <count>
- Validated awaiting promotion: <count>
- Rejected this week: <count>, memory-payload-complete: <X/N>

### Anti-drift snapshot
- Harvest-to-closure ratio: <number>
- Avg queue age by state: Inbox <X>d | In Progress <X>d | Validation <X>d
- % active items with concrete next action: <X>%
- % closed items with memory payload complete: <X>%

### Fallback-mode usage
- Days run as primary-track: <N>
- Days run as fallback: <N>, breakdown by mode: <closure X, memory Y, …>
- Fallback usage rate: <X>% (flag if >40% sustained — see integrity cadence)

### Rotation dimensions hit this week
- Discovery: <Y/N + count>
- Validation: <Y/N + count>
- Closure: <Y/N + count>
- Gaps: <Y/N + count>
- Improvement: <Y/N + count>
- If <3 dimensions: why? <note>

### Blocker taxonomy summary
- data missing: <N>
- conversion issue: <N>
- framework mismatch: <N>
- unclear hypothesis: <N>
- validation capacity: <N>
- external dependency: <N>

### Source yield (from source_map.md)
- Best source lane this week: <name> — <N items reaching Validation or beyond>
- Weakest source lane: <name> — <noise rate>
- Unreviewed source classes: <list if any>

### Gap review
- Open portfolio gaps (from PORTFOLIO_TRUTH_TABLE.md): <list>
- Packets that addressed a gap this week: <N>
- Gaps not addressed: <list>

### Kill list / demotion
- Candidates archived this week: <list + reasons>
- Source lanes demoted: <list if any>
- Recurring manual work flagged for templating: <list>

### Next week's search emphasis
- Priority gap: <one or "broad harvest">
- Priority source: <one>
- Committed closures: <list of items targeted to close>

### Integrity self-check (bundled; see cadence.md)
- [ ] Scorecards written every day this week
- [ ] Stale thresholds fired as expected
- [ ] Memory payloads complete for all closures within 3 days
- [ ] Blockers all have types assigned
- [ ] Oldest-item rule satisfied each day
- [ ] No "machine not trying" signals (no 2+ day streaks of zero artifacts AND zero state changes AND zero stale cleared)
- [ ] Docs/process definitions still match actual behavior

### Improvement log entry
(See improvement_log.md for detail; one-line summary here.)
```

---

## Biweekly source expansion rollup

On alternating Fridays, after the weekly rollup, append:

```
## [YYYY-MM-DD] Source Expansion Review

### Source map status
- Lanes currently harvested: <list from source_map.md>
- Yield leaders (this 2-week window): <ranked>
- Yield laggards: <ranked; consider demotion>

### Standing question response
- What source surfaces are we not harvesting yet that may contain differentiated strategy ideas or components?
- <answer with at least 1 concrete proposal>

### New source test this cycle
- Source: <name/type>
- Hypothesis: <why this surface may yield differentiated ideas>
- Test plan: <what minimum harvest + evaluation looks like>
- Verdict threshold: <what would earn permanent lane status>
```

---

## Thin-entry policy

Not every day produces an artifact. That is acceptable — triage days,
blocked days, and pure-intake days exist. But:

- **4 consecutive thin entries** (no artifact, no state change, no stale cleared) triggers an integrity-cadence flag. The machine is not trying.
- **2 consecutive empty entries** (genuinely nothing logged) is a hold breach or an operator absence — investigate the gap.

Thin is not the same as empty. Thin is honest. Empty is missing.

---

# Daily entries (append-only below this line)

## 2026-04-15
- Advanced: FXBreak-6J-Short-London memory payload completed (packet item 1); FXBreak-6J component_validation_history populated (packet item 2); SPX-Lunch-Compression-Afternoon-Release triaged → REJECT with full memory payload (packet item 3). Three distinct commits: 421bded, a8d6f96, pending-this-commit.
- Produced artifact: 3 closed packet items; 1 new registry entry created (SPX-Lunch-Compression-Afternoon-Release); 4 component_validation_history entries written across 2 strategies; 1 new failure pattern discovered (GHOST CANDIDATE) + logged + added to weekly integrity cadence.
- State change: Rejected +1 (SPX-Lunch-Compression). Two entries (FXBreak-6J, SPX-Lunch-Compression) now satisfy stale rule #7 (memory payload complete). Registry entry count 116→117.
- Stale cleared: rule #7 cleared for 2 items this session (FXBreak-6J via packet item 1; SPX-Lunch-Compression via packet item 3's creation with complete payload). Pre-v1 rule-#7 backlog: 28→26 remaining for memory-cleanup fallback days.
- Tomorrow: inaugural packet is fully executed. Tomorrow's packet candidates: (a) clear the 2 rule-#5 rejected-without-reason firings (fallback closure); (b) informal ghost-candidate scan across `strategies/*/strategy.py` before Friday rollup; (c) continue whatever fresh discovery shows up. Keep packet bounded; today was closure-heavy, tomorrow lean into discovery/validation balance.
- Operating rule observed and confirmed: *Do not open a new primary item mid-day unless one current packet item is fully closed or explicitly blocked.* Held today — all 3 items were in the committed packet from start; no mid-day expansion occurred.
- Post-packet fallback closure (one item, deliberate): cleared both rule-#5 rejected-without-reason firings (Overnight-Z-VolRatio-OpenDrive → `no_edge_decomposition_failed`; Treasury-Cash-Close-Reversion-Window → `falsification_thesis_failed`). Both reasons sourced from each item's existing `notes` narrative — no new evidence introduced, no scope creep. Rule-#5 backlog: 2 → 0.

## 2026-04-16
- Advanced: ghost-candidate scan completed (33 ghosts found, pattern confirmed systemic). Ghost-pattern rule formalized in cadence.md + queues.md. Ghost inventory created. All 5 SALVAGE-classified ghosts triaged individually → all 5 REJECT on closer inspection.
- Produced artifact: `docs/fql_forge/ghost_inventory.md` (new, standing reference); formalized ghost-pattern standing policy; 5 triage verdicts with documented reasons + salvage classifications; 1 glob-matching bug identified and documented.
- State change: individual_triage queue 5→0 (all resolved to REJECT). batch_register_reject queue confirmed at 26 (including vol_compression_breakout reclassified from SALVAGE to REJECT due to scan bug). monitor_pending stays at 2.
- Stale cleared: ghost-candidate pattern itself was the aging item (1 case day-1 → 33 cases day-2 → formalized as standing policy). Individual triage backlog cleared to zero same-day.
- Tomorrow: candidates for next packet include (a) batch-register a first tranche of the 26 REJECT ghosts as memory-closure fallback work, or (b) fresh harvest / discovery from inbox / source lanes if the pipeline has new items. Friday's weekly rollup is tomorrow — that's the first real operating-picture review. Keep tomorrow's packet lean; the rollup itself takes real time.

## 2026-04-17
- Advanced: Friday proactive sequence executed in order — cluster-assignment verification, review stack (weekly_scorecard + weekly_intake_digest + operating_dashboard), and Forge v1 first weekly rollup (this entry + rollup block below). Two cluster reports read and cross-validated via spot-check of 4 flagged notes.
- Produced artifact: verification finding — full-batch spot-check of all 8 closed-family ALERTs from `scripts/fql_alerts.py` shows **8/8 false positives** (FP 8 / TP 0). Notes target non-equity assets (energy, FX, rates-relative-value), non-morning sessions (overnight, close, pre-London, afternoon), and non-closed-family mechanisms (imbalance, profile rejection, compression breakout, basis arbitrage). Several notes explicitly disclaim the closed family in their distinctness field. Operating conclusion: *the current closed-family detector is unsuitable for rejection decisions without manual verification.* Action taken: batch-dismissed all 8 alerts; no notes rejected. Plus this weekly rollup.
- State change: no Forge-queue movement today (rollup day); registry stays at 117. Forward runner this week: +$1,656.65 / 31 trades / no DD. Scorecard weekly rollup saved as `research/reports/weekly_scorecard_20260417.json`; intake digest saved as `research/reports/intake_digest_20260417.json`.
- Stale cleared: none today — rollup day, not closure-focused.
- Tomorrow: weekend. Next operational day Monday 2026-04-20 → scan Claw outputs from `~/openclaw-intake/inbox/harvest/` and `inbox/refinement/` per CLAUDE.md Monday cadence; triage new notes; possibly begin batch-register of the 26 REJECT ghosts as memory-closure fallback work. Keep Monday packet lean given weekend intake accumulation.
- Control-gap finding logged: 4 probation strategies at 0 forward trades (DailyTrend-MGC-Long, MomPB-6J-Long-US, PreFOMC-Drift-Equity, TV-NFP-High-Low-Levels), not just MGC-Long. Exception pipeline design case-2 scenario is systemic, not isolated. Added to improvement_log.md.

## 2026-04-17 Weekly Rollup (week of 2026-04-14 → 2026-04-17)

*First Forge v1 weekly rollup. Partial week — Forge shipped Monday 2026-04-14; operating days 04-15/04-16/04-17 = 3 primary-track days.*

### Throughput
- Validated artifacts produced this week (12):
  1. Forge v1 documentation (10 docs, ship day)
  2. FXBreak-6J-Short-London memory payload completed
  3. FXBreak-6J component_validation_history populated
  4. SPX-Lunch-Compression-Afternoon-Release triaged REJECT + full memory payload
  5. 2 rule-5 rejected-without-reason firings cleared (fallback closure)
  6. Ghost-candidate scan (33 ghosts, pattern formalized)
  7. `docs/fql_forge/ghost_inventory.md` standing reference
  8. 5 SALVAGE→REJECT triages with memory payloads
  9. Forge always-on kernel design v1
  10. Exception pipeline design v1 + decision lock-in
  11. Cluster verification finding (detector false-positive rate 4/4)
  12. This weekly rollup
- Items conclusively resolved: 7 packet items + 26 ghost-REJECTs pending batch-register
- Items opened: 1 new registry entry (SPX-Lunch-Compression) + 2 sister design docs
- Closure ratio: 7/3 = 2.33 (closure-dominant — healthy)
- Reusable components added to memory: 4 component_validation_history entries across 2 strategies; ghost inventory; kernel design; pipeline design

### Queue health
- Forge sub-queues (tracked in daily entries): individual_triage 0, batch_register_reject 26, monitor_pending 2
- Operator-facing 5-state view: Inbox (new 04-17 intake 15) / In Progress (0 mid-day) / Validation (0) / Validated (FXBreak-6J payload) / Rejected (+6 this week — 1 SPX-Lunch + 5 ghosts)
- Harvest intake backlog (Claw upstream, not Forge): 217 notes (+15 overnight)
- Rejected this week with memory-payload-complete: 6/6 ✓

### Anti-drift snapshot (first-week baseline — bootstrap caveat per kernel design §6.7)
- Harvest-to-closure ratio (this week): 7 closed / 3 opened = 2.33
- Avg queue age by state: not formally tracked (v1.1 refinement candidate — add queue age stamps)
- % active items with concrete next action: 100% (every day had a defined packet)
- % closed items with memory payload complete: 100% (6/6)

### Fallback-mode usage
- Days run as primary-track: 3 (04-15, 04-16, 04-17)
- Days run as fallback: 0
- Fallback usage rate: 0% — well below the 40% flag threshold, but first-week small sample
- Note: 04-15 had a *deliberate post-packet* fallback closure (rule-5 backlog 2→0). Primary-track classification holds — fallback was additive, not substitute

### Rotation dimensions hit this week
- Discovery: Y (ghost scan, 33 instances; cluster verification)
- Validation: Partial (triages performed; no full validation-battery runs — acceptable for first week during hold)
- Closure: Y (7 items + 26 batch-pending)
- Gaps: Y (FXBreak-6J addressed FX-short-London family partially)
- Improvement: Y (ghost-pattern rule formalized; kernel + pipeline designs shipped; control-gap diagnosis)
- All 5 dimensions hit ✓

### Blocker taxonomy summary (from intake digest)
- data missing: 2 (pre-2019 rates backfill; CTD mapping for treasury basis)
- conversion issue: 0
- framework mismatch: 0
- unclear hypothesis: 1 (Commodity-Carry-TailRisk-Overlay)
- validation capacity: 0
- external dependency: 1 (TV-VIX-Term-Structure-Hedge — tail-risk/hedge controls)
- sample size: 1 (CrudeOil-OPEC-Announcement-Regime)
- **Dominant choking point:** data missing (50% of blockers). Pre-2019 rates backfill unlocks the Treasury-CPI-Day re-test and Treasury-12M-TSM symmetric test per dashboard.

### Source yield (from source_map.md + cluster reports)
- Best source lane this week: academic (22 registry entries carry this tag; 3 of next 5 conversion candidates sourced academic)
- Weakest source lane: internal / expansion (3 registry entries each — thin)
- Cluster report source mix (raw counts, 153 notes): refinement 77, web 23, github 19, reddit 10, exchange 4, edu 2, gov 2
- **Flag:** refinement is dominating intake (50%+ of fresh notes are internal derivatives). External source diversity needs a push. Claw's Report 1 flagged this explicitly; Report 2 said "acceptable" among external-only mix — both true simultaneously.
- Unreviewed source classes: none this window

### Gap review (vs `docs/PORTFOLIO_TRUTH_TABLE.md` + dashboard)
- Open factor gaps: CARRY (no probation), STRUCTURAL (no probation), VOLATILITY (no probation), VALUE (1 idea, blocked)
- Claw cluster depth this week: Treasury auction/rates (very large), FX value/PPP (medium-large), Commodity carry (large), Energy-native crude (very large), Tokyo/pre-London FX (very large), Afternoon Treasury structural (medium-large), Close-session short-bias (large)
- Packets that addressed a gap this week: 1 (FXBreak-6J partial — structural)
- **Gaps NOT addressed this week:** CARRY, VOLATILITY, VALUE. Claw generated notes in these areas but none converted to Forge packet work.
- Cluster-to-conversion bottleneck: Claw produces volume; Forge packets convert 1 item/day max. At current throughput, large clusters (very-large Treasury auction) will take weeks to drain.

### Kill list / demotion
- 4 probation strategies at 0 forward trades (NO_EVIDENCE): DailyTrend-MGC-Long (32d), MomPB-6J-Long-US, PreFOMC-Drift-Equity, TV-NFP-High-Low-Levels
- **Hold-window:** cannot demote during hold per HOLD_STATE_CHECKLIST.md. Flagged for May 1 checkpoint review.
- **Systemic finding:** case-2 (stale probation) is not isolated to MGC-Long; it's 4-way. Strengthens case for exception pipeline STRATEGY_BEHAVIOR sub-classifier. Logged to improvement_log.md.
- Source lanes demoted: none
- Recurring manual work flagged for templating: closed-family detector false-positive review (happens every digest; needs pipeline)

### Next week's search emphasis (2026-04-20 → 2026-04-24)
- **Priority gap:** CARRY + VALUE (both untouched this week; factor coverage is weakest here)
- **Priority source:** external non-refinement (per Claw cluster-report finding that refinement is dominating)
- **Committed closures:** begin batch-register first tranche of 26 REJECT ghosts as memory-closure fallback; cluster consolidation pass per Claw's merge recommendations (Tokyo/pre-London → 4 canonical; Close-session short-bias → 3 canonical; Afternoon Treasury failed-break → collapsed set)

### Integrity self-check
- [x] Scorecards written every operating day this week (04-15, 04-16, 04-17; 04-14 was ship day, no daily entry required)
- [x] Stale thresholds fired as expected (rule-5 backlog cleared 2→0; rule-7 backlog tracked)
- [x] Memory payloads complete for all closures within 3 days (6/6, 100%)
- [x] Blockers all have types assigned (5 blockers, 5 types)
- [x] Oldest-item rule satisfied each day
- [x] No "machine not trying" signals (3 consecutive productive days; no zero-artifact streaks)
- [x] Docs/process definitions still match actual behavior (ghost-pattern rule added to cadence.md; closed-family detector behavior doesn't match advertised policy — flagged as detector quality issue, not doc issue)

### Improvement log entry
One-line summary (detail in `improvement_log.md`): First Forge v1 week produced 12 validated artifacts and uncovered a real control-gap (closed-family detector 4/4 false positive rate; case-2 is systemic across 4 probation strategies). Next week: CARRY + VALUE gap push, external-source rebalance, ghost batch-register; May 1 checkpoint will handle stale-probation demotion decisions.

## 2026-04-20
- Advanced: Friday proactive-sequence follow-through. Confirmed Forward Runner STALE state change was weekend calendar-day noise (last fire Friday 17:04; forward-day is weekday-only; self-cleared today at 17:00). Updated MAY_1_STALE_PROBATION_BATCH_REVIEW anchor list 4→5 after ZN-Afternoon-Reversion flipped UNDER_EVIDENCED → STALE. Refreshed `inbox/_family_queue.md` from month-stale 2026-03-18 version (4 families had "zero candidates" claims that contradicted current cluster reports — Afternoon Session Structural, Energy-Native MCL, Tokyo/pre-London, Close-Session Short all now crowded). Full triage pass on 38 weekend Claw notes (30 harvest + 8 refinement) using Friday's priority filter + 5-gate crowded-family screen.
- Produced artifact: `research/data/harvest_triage/2026-04-20.md` (new structured triage record with policy-rules section); MAY_1_STALE_PROBATION_BATCH_REVIEW updates including registry-truth ambiguity flag for MomPB-6J-Long-US / PreFOMC-Drift-Equity; major `_family_queue.md` refresh; commits 1e8bfe1 + 5cf3613.
- State change: no Forge-queue movement (operator-cadence day, not closure-focused). Registry stays at 117. Stale-probation count 4→5. 38 notes dispositioned: 18 ACCEPT HIGH PRIORITY (100% in VALUE/CARRY/Treasury-auction), 9 ACCEPT COMPONENT, 3 NEEDS REVIEW, 8 DEPRIORITIZE.
- Stale cleared: none today (policy/refresh day, not closure).
- Tomorrow: Tuesday = observation day. Twice-weekly batch_first_pass + mass_screen fires at 18:00 ET automatically. Watch for Claw intake response to `_family_queue.md` refresh as first reinforcement-signal data point.

## 2026-04-21
- Advanced: light triage of 15 overnight Claw notes using Monday's exact policy rules (no rule changes). Goal was measurement + reinforcement signal, not deep processing. Confirmed Forward Runner returned HEALTHY at Monday 17:04 fire. No new stale-probation flips overnight (count still 5).
- Produced artifact: `research/data/harvest_triage/2026-04-21.md`; commit 5014310. Aggregate comparison vs Monday's 38-note batch: ACCEPT HIGH 47%→13%, DEPRIORITIZE 21%→33%, NEEDS REVIEW 8%→33%. Signal captured: head of batch adapting to priority shift (positions 1–4 are all VALUE/CARRY-targeted; VALUE specifically got 4 attempts), tail still fills to budget with pile-on patterns. Mixed result, not a verdict — first reinforcement cycle is rarely complete.
- State change: no Forge-queue movement. Registry stays at 117. Forward Runner: STALE → HEALTHY (Monday 17:04 fire cleared weekend freshness flag as predicted). No new stale-probation count change.
- Stale cleared: none today (measurement day).
- Tomorrow: Wednesday = another observation day. Watch question narrowed: *will tail pile-on rate drop without stronger suppression, or does `_family_queue.md` need explicit "do not generate" language?* Decision point Friday rollup; no intervention before then.

## 2026-04-22
- Advanced: 3rd-cycle light triage of 15 overnight Claw notes, same policy rules. Twice-weekly batch_first_pass fired Tuesday 18:00 as scheduled but produced no new first_pass files (expected — hold window = no new strategy code for mass_screen to pick up; not an issue today, flag as smell-#9 candidate for post-hold). No new stale-probation flips (count still 5; MGC-Long 37d, ZN 33d).
- Produced artifact: `research/data/harvest_triage/2026-04-22.md`. 3-day series now complete: DEPRIORITIZE rate 21% → 33% → 47% (worsening). Head-of-batch still shifts to VALUE/CARRY/Treasury-auction (3 ACCEPT HIGH today: curve regime-switch carry, auction tail-shock, pre-auction concession follow-through). Tail now contains 6 pattern clusters that are 3+ cycles deep without any suppression (random-entry baselines 3×, support-bounce exits 4×, pre-London breakouts 4×, dual-thrust 3×, hidden-instability filters 3×, kalman VALUE now saturating at 5×).
- State change: no Forge-queue movement. Registry stays at 117. One positive adaptation signal: 04-22_09 reframed 04-21_08's closed-family-risk framing into explicit non-equity scoping — proves NEEDS REVIEW flags drive behavior on individual notes.
- Stale cleared: none today (measurement day).
- Tomorrow: Thursday = observation continuation; Friday = decision point. Evidence now strongly suggests Claw reprioritizes but does not suppress. Friday likely escalates to explicit "Do not generate" language in `_family_queue.md` naming the specific repeated patterns, or a suppression block in `_priorities.md` (higher-effort, requires `claw_control_loop.py` change). No intervention until Friday rollup renders the decision.
- Also produced (user-directed hold-safe progress): `research/data/harvest_triage/_AUDIT_2026-04-22_registry_gap.md`. Real diagnostic finding — 38 triage accepts this week (23 HIGH canonical + 15 COMPONENT) sit in triage files with zero registry reflection. Registry last touched 2026-04-14 (7+ days stale). harvest_manifest last_scan timestamp is 2026-03-17. Structural mismatch between industrial-scale triage (15-38 decisions/day) and artisanal packet-workflow registry appends (1-3/day). Direct manifestation of `bad_automation_smells.md` smell #4 (queue growth masking lack of closure). Committed as Friday decision input. 4 options staged (A batch-register, B absorb gradually, C redefine triage as authoritative, D hybrid).

## 2026-04-23
- Advanced: 4th-cycle compressed triage of 15 overnight notes. Same policy rules, lighter format (aggregate + pattern table only). Watch question conclusively answered. VolManaged-EquityIndex-Futures hit 30-trade review gate (ACTION-level alert) — recorded as May 1 checkpoint input; continuation is the default during hold per T3 authority rule, no action today.
- Produced artifact: `research/data/harvest_triage/2026-04-23.md`. 4-day DEPRIORITIZE rate trend: 21% → 33% → 47% → **60%** — monotonic worsening every single day. Every repeated pattern cluster from prior days reappeared on Thursday; the random-entry meta-robustness baseline is now 4 straight DEPs (04-19, 04-21, 04-22, 04-23 — perfect non-suppression signal). Today's dispositions: 1 HIGH (Donchian non-equity), 2 COMPONENT (ADX gate, Hurst filter), 3 NEEDS REVIEW, 9 DEPRIORITIZE.
- State change: no Forge-queue movement. Registry stays at 117. No new stale-probation flips (count still 5; MGC-Long 38d, ZN 34d). VolManaged reached review gate — flagged.
- Stale cleared: none today (observation day).
- Tomorrow: Friday = triple-decision render day. (1) Explicit suppression layer in `_family_queue.md` — evidence forces it. (2) Harvest→registry coordination A/B/C/D — audit committed Wednesday. (3) VolManaged disposition under hold rules (continuation-defer vs early checkpoint). Plus normal Friday weekly rollup cadence (scorecard + intake digest + operating dashboard + Forge v1 Layer 2).

## 2026-04-24
- Advanced: Friday full packet rendered. Forward-testing foreground check (equity $50,578.66 +$140 from Thursday, HWM $50,841.57, drawdown -$263, consecutive losses 0 — 04-21 MNQ streak broken by 04-22 MNQ +$249.76). Weekly review stack executed (weekly_scorecard/weekly_intake_digest/operating_dashboard saved). Week-ending cluster review read (independently confirms the suppression case from Claw's own angle — names same 8 pattern clusters as "main risk"). Three decisions rendered.
- Produced artifact: (1) `inbox/_family_queue.md` updated with explicit 8-pattern suppression layer + 5-gate escape criteria (Decision 1); (2) Decision 2 rendered option D (hybrid: batch-register 23 HIGH canonicals as scheduled Monday/Tuesday packet work next week; absorb 15 COMPONENT items gradually via future packets; documented in this scorecard rollup); (3) Decision 3 rendered VolManaged continuation-defer to May 1 checkpoint per T3 hold rules; (4) Forge Layer 2 weekly rollup + Layer 3 biweekly source expansion blocks below.
- State change: registry stays at 117 (decisions rendered, remediation scheduled not executed — hold-compliant). Forward equity +$140 overnight. Consecutive losses 0. VolManaged 30→31 trades. Harvest backlog 288→303 (+15 today, +86 over the week).
- Stale cleared: none today (decision-render day).
- Tomorrow: weekend + Monday. Claw output scan + triage per normal Monday cadence. Suppression layer's first reinforcement test will be Mon/Tue/Wed batches. May 1 checkpoint is 7 operational days out.

## 2026-04-24 Weekly Rollup (week of 2026-04-20 → 2026-04-24)

*Second proper Forge weekly rollup. First full week post-ship.*

### Throughput
- Structured triage artifacts (4 cycles): `harvest_triage/2026-04-20.md` (38 notes), `2026-04-21.md` (15), `2026-04-22.md` (15), `2026-04-23.md` (15) — 83 notes triaged with policy rules applied
- Audit artifact: `harvest_triage/_AUDIT_2026-04-22_registry_gap.md` (structural finding)
- Governance decisions rendered today: 3 (suppression, harvest→registry option D, VolManaged continuation-defer)
- `_family_queue.md` refreshed Monday (4 families flipped zero-candidates → overcrowded) + suppression layer added Friday
- Forward-testing artifacts: 6 new trades logged (4/22 MNQ +249/MYM -109/VolManaged +0.02; 4/23 none in log yet)

### Queue health
- Harvest backlog: 217 → 303 (+86 over week; Claw continuing discovery at ~15/day)
- Registry: 117 throughout week (**zero change — the coordination gap**)
- Stale probation count: 4 → 5 (ZN-Afternoon-Reversion flipped Monday)
- Forge sub-queues: `batch_register_reject` still 26 (ghost inventory unchanged); `individual_triage` 0; `monitor_pending` 2
- This week's HIGH PRIORITY accepts in triage files: 23 (18 Mon + 2 Tue + 3 Wed + 1 Thu — pending registry append)
- This week's COMPONENT accepts: 15 (pending gradual absorption)

### Anti-drift snapshot
- **Harvest-to-closure ratio: 0 / 86 = 0.00 (worst of series).** Forge-queue closures this week = 0 because industrial triage displaced packet-based closure. This is the registry-gap finding expressed numerically.
- % closed items with memory payload: N/A (no closures)
- Pile-on rate trend (tail quality): 21% → 33% → 47% → 60% (monotonic up; motivated Decision 1)

### Fallback-mode usage
- Days run primary-track: 5 (Mon-Fri, all produced intended artifacts)
- Days run fallback: 0
- Fallback usage rate: 0% (same as last week; watch threshold remains 40%)

### Rotation dimensions hit this week
- Discovery: Y (4 triage passes, cluster review, audit)
- Validation: N (no validation-battery runs — acceptable under hold; no promotion pipeline active)
- Closure: **N — structural gap.** Industrial triage does not count as closure; registry didn't move.
- Gaps: Y (VALUE/CARRY intake surfaced; 6 ACCEPT HIGH across week)
- Improvement: Y (3 decisions rendered, suppression layer shipped, audit captured)
- **3/5 dimensions hit.** Missing Validation (hold-expected) and Closure (gap documented, Option D scheduled for next week).

### Blocker taxonomy summary
- Unchanged from last week. 18 blocked ideas in registry.
- Per 04-19 Claw blocker mapping: strategy_ambiguity + proxy_data remain the most-clearable; data + sample_size + execution remain hard.

### Source yield (per 2026-04-24 cluster review)
- Best lanes this week: GitHub + Reddit (dominant on relative-value spread, London-open breakout, and regime-gate fragments)
- Weakest: academic / digest (under-represented; highest-value notes but few in count)
- Concentration risk: rising. Source diversity is "good enough" but over-leaning on forum/repo synthesis.
- No source lanes demoted.

### Gap review
- VALUE: still 1 idea in registry; but 8+ VALUE notes in intake this week with 2 ACCEPT HIGH — real intake progress, registry not reflecting
- CARRY: 8 ideas in registry; 11+ CARRY notes in intake this week with 3 ACCEPT HIGH
- STRUCTURAL / VOLATILITY: factor dashboard still GAP; some component-level progress via filters
- Gaps clearly addressed by intake priorities; registry movement is the blocker (Decision 2)

### Kill list / demotion
- 5 stale probation strategies: DailyTrend-MGC-Long (39d), ZN-Afternoon-Reversion (35d), MomPB-6J-Long-US (0 trades), PreFOMC-Drift-Equity (0 trades), TV-NFP-High-Low-Levels (0 trades). All defer to May 1 batch review.
- VolManaged-EquityIndex-Futures: review gate reached (31 trades). Continuation-defer to May 1 (Decision 3).
- No archives this week (hold rules prevent).

### Three decisions rendered (today)
**Decision 1 — Explicit suppression layer in `_family_queue.md`:**
8 pattern clusters named for "Do NOT generate" list: dual-thrust non-equity, London/pre-London FX breakout variants, random-entry baselines, FX support-bounce quick-exit variants, hidden-instability filters retargeted, Kalman/stationarity/half-life VALUE saturation, fee/slippage gates, parallel consensus filters. Each note in these families must pass at least one of 5 gates (new factor / new asset-session / blocker-clearing / canonical split / materially different implementation). Executed: `_family_queue.md` updated.

**Decision 2 — Harvest→registry coordination: Option D (hybrid)**
23 HIGH-priority canonical accepts batch-registered as dedicated Monday/Tuesday packet work next week (2026-04-27 / 2026-04-28). 15 COMPONENT accepts absorbed gradually via future packet work when relevant. Registry append is T2 authority per `docs/authority_ladder.md` (additive, no status changes) — allowed during hold. Scheduled, not executed today — keeps Friday documentation-only.

**Decision 3 — VolManaged review-gate: Continuation-defer to May 1**
Probation strategy hit 30+ trades and review gate. Under hold rules, promotion/downgrade/archive is T3 authority requiring checkpoint. Continuation is the default during hold. VolManaged review becomes an explicit input to the May 1 checkpoint (alongside the stale-probation batch review). No action today.

### Next week's search emphasis (2026-04-27 → 2026-05-01)
- **Priority gap:** VALUE + CARRY (continue; well-aligned with intake)
- **Priority source:** academic + digest (rebalance from GitHub/Reddit concentration per cluster report)
- **Committed closures:** batch-register 23 HIGH canonicals Monday/Tuesday per Decision 2
- **Committed reviews:** first post-suppression-layer triage cycle Monday AM; validate whether suppression is landing

### Integrity self-check
- [x] Scorecards written every operating day (5/5 this week)
- [x] Stale thresholds firing appropriately (5 stale flags, all legitimate per Claw judgment)
- [ ] Memory payloads complete for all closures: N/A this week (no closures — the gap)
- [x] Blockers typed (18 blocked, 9 blocker types)
- [ ] Oldest-item rule: N/A (no packet execution this week; industrial triage pattern)
- [x] No "machine not trying" signals (4 triage cycles + audit + 3 decisions rendered = machine clearly working)
- [x] Docs match behavior (updated `_family_queue.md`, `MAY_1_STALE_PROBATION_BATCH_REVIEW.md`, added suppression layer, added audit file)

### Improvement log entry
Week exposed the industrial-triage vs packet-closure mismatch in concrete numbers (0 closure ratio, 86 intake over week). Three decisions rendered Friday closed the 4-day watch cycle with minimal intervention. Claw's own cluster review independently validated the suppression case — cross-evidence agreement reduces operator-judgment risk.

## 2026-04-24 Source Expansion Review (Layer 3, first biweekly)

*Forge v1 shipped 2026-04-14. First Friday rollup 2026-04-17 was partial-week seed. Today is the first proper biweekly cadence fire.*

### Source map status
- **Lanes currently harvested (9 active):** openclaw_tactical, openclaw_strategic, tradingview_scan, academic_review, youtube_practitioner, github_quant_repos, reddit_forums, microstructure_specialists; legacy_revival OFF
- **Yield leaders (2-week window):** GitHub (dominant on quant-repo logic), Reddit (dominant on regime-gate and FX microstructure fragments), openclaw_tactical (highest-quality synthesis)
- **Yield laggards:** academic / digest — produced the highest-value macro-value and carry sleeves this week but only ~4 items; under-represented in overall mix
- **Unreviewed source classes:** none open; source map coverage is complete for currently active lanes

### Standing question response
> *What source surfaces are we not harvesting yet that may contain differentiated strategy ideas or components?*

**This cycle's answer (observational, per operator constraint — no new lane opening):**
Source concentration is rising within the existing GitHub + Reddit lanes, not because new surfaces are missing but because the rebalance across existing lanes is uneven. The actionable issue is WEIGHTING, not COVERAGE.

Two weeks of observation suggests:
- Academic / digest lanes produce disproportionately high-value notes (VALUE + CARRY canonicals) per note, but low volume
- GitHub / Reddit produce disproportionately many notes per note-value, skewing the intake distribution
- Forum/repo synthesis risk: Claw may be converging on a narrower mechanism space by over-reading GitHub/Reddit

### New source test this cycle
**None.** Per operator constraint for today's biweekly: this rollup is observational. No new lane opened. Concrete proposal for next biweekly (2026-05-08, post-hold): evaluate whether an explicit per-lane weighting mechanism should exist in `harvest_engine.py` or `claw_control_loop.py` to prevent concentration drift — logged as post-May-1 design candidate (smell #11 candidate per yesterday's note: *governance throughput masking operational visibility* has a cousin, *harvest volume masking yield concentration*).

### Verdict threshold (for future "open new lane" decisions)
When a candidate source lane is proposed in future biweeklies, it earns permanent status if it produces at least 2 notes per week over 4 weeks AND at least 1 ACCEPT-HIGH disposition in that window. Lower than that = demote. Established today as the new-lane bar for v1.1.

---

## 2026-04-27
- Advanced: First post-suppression triage cycle. Combined batch — 15 untriaged Friday 04-24 notes + 11 weekend 04-26 notes = 26 total. **Suppression layer landed cleanly.** Pile-on rate dropped 60% → 15% in one cycle (45-point drop). Combined ACCEPT rate 20% → 73%. Of the 8 suppressed clusters: 5 had ZERO instances; 2 had only borderline NEEDS REVIEW cases (different role within family); 1 had a single DEPRIORITIZE (consensus-screen, only 2 cycles deep at suppression time). Read 04-26 blocker mapping: blocked count unchanged at 18; same priority order strategy_ambiguity > proxy_data > instrument_definition; nothing requires immediate _priorities.md / _family_queue.md updates.
- Produced artifact: `research/data/harvest_triage/2026-04-27.md`. Aggregate dispositions: 10 ACCEPT HIGH (38%), 9 ACCEPT COMPONENT (35%), 3 NEEDS REVIEW (12%), 4 DEPRIORITIZE (15%). Replaced volume concentrated in Treasury-auction (6 notes, priority), VALUE canonicals (5 notes), CARRY-ambiguity-clearing canonicals (4 notes), useful operational components (4 notes). Exactly the desired shift.
- State change: registry stays at 117 (Decision 2 batch register scheduled for Tuesday). Forward equity $50,205.94 (-$372 vs Friday morning, traceable to 04-23 MNQ -$446 single trade). Forward Runner: HEALTHY → STALE (weekend calendar-day artifact, self-clears today at 17:00 — same pattern as last Monday). Harvest backlog 303 → 314 today. Stale probation count still 5 (MGC 42d, ZN 38d). VolManaged 32 trades.
- Stale cleared: none today (triage day).
- Tomorrow: Tuesday — execute Decision 2 batch register. Pending count grew from Friday's 23 HIGH + 15 COMPONENT to **33 HIGH + 24 COMPONENT** with today's adds. Batch will size to 33 HIGH canonical registry appends (T2 authority, hold-compliant). Components absorbed gradually per option D. Suppression layer review clause: *"if pile-on drops, list stays"* — confirmed. No further suppression intervention needed.
- Decision 1 (suppression) status: **CONFIRMED EFFECTIVE.** Friday 2026-05-01 rollup review of the suppression list becomes a confirmation, not a remediation.


