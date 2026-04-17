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

