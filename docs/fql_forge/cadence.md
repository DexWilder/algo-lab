# Cadence

**4 cadence layers + 6 fallback work modes + day-14 v1 exit gate.**

Structure without rhythm drifts. Cadence is what keeps FQL Forge
running consistently instead of working in bursts.

---

## Cadence layers

### Layer 1 — Daily operating cadence

**Fires:** end of each work day (or start of next).

**Order matters** — stale review first, because stale items influence
today's packet choice.

1. **Stale review.** Scan `stale_checks.md` rules 2, 4, 5, 8, 9 against current queue state. If any fire, note which and route today toward clearing.
2. **Active packet review.** Read `active_packet.md` for yesterday's "tomorrow" line and yesterday's packet. Assess which items still belong in today's packet.
3. **Packet selection.** Apply packet composition rules: ≥1 closure-direction item, ≥1 aging item, ≤2 new items (soft), WIP caps respected. If no elite candidate ready OR primary track stalled, pick a fallback mode.
4. **Advance packet.** Do the actual work. Convert, test, validate, refine, extract, reject.
5. **Close or block aging item.** Oldest-item rule — at least one aging item resolves (advance / close / block with plan / reject).
6. **Update memory.** Any closure today must have its 6-field memory payload started. If closure happened today, complete the payload today (don't wait on the 3-day deadline).
7. **Append proof-of-life.** Write today's entry to `scorecard.md` per the 5-line daily format. Four lines minimum even on thin days — thin is honest, empty is missing.

**Time budget:** designed for ≤30 minutes excluding the actual work in
step 4.

### Layer 2 — Weekly review cadence

**Fires:** end of Friday, after the day's regular daily cadence.
Aligned with existing Friday research batch in `fql_research_scheduler.py`.

1. **Scorecard weekly rollup.** Append the weekly rollup block per `scorecard.md` format.
2. **Source yield review.** Update `source_map.md` with this week's per-source harvest → validation → component rates.
3. **Gap review.** Cross-reference `docs/PORTFOLIO_TRUTH_TABLE.md` open gaps against this week's packet rationale. What gaps were addressed? Which were not?
4. **Blocker taxonomy summary.** Count blockers by type. Whatever type dominates is the current choking point.
5. **Kill list / demotion.** Identify candidates to archive, stale ideas to demote, source lanes producing low signal.
6. **Improvement log entry.** Write the mandatory weekly entry in `improvement_log.md`.
7. **Choose next week's search emphasis.** One priority gap + one priority source. Written into the rollup's "Next week's search emphasis" section.
8. **Integrity self-check (bundled; see Layer 4 below).**

**Time budget:** designed for ≤60 minutes.

### Layer 3 — Biweekly source expansion cadence

**Fires:** every alternating Friday after the weekly cadence.

1. **Source map status snapshot.** Review all lanes currently harvested, yield leaders, yield laggards.
2. **Standing question answered.** *What source surfaces are we not harvesting yet that may contain differentiated strategy ideas or components?* Minimum 1 concrete proposal.
3. **New source test.** Choose one source class not currently harvested (podcasts, interviews, transcripts, newsletters, archives, new platforms), test it with minimum harvest + evaluation, log the test plan.
4. **Update `source_map.md`** with the test record.

**Time budget:** designed for ≤45 minutes.

### Layer 4 — Integrity self-check cadence

**Fires:** bundled with Layer 2 (weekly Friday) by default. Standalone
expanded run on day 14 (v1 exit gate).

Weekly checklist:
- [ ] Scorecard written every day this week (no missing days)
- [ ] All 9 stale rules reviewed; any firings have been acted on
- [ ] Memory payloads complete for every closure within 3-day deadline (v1-launch-date scope per stale rule #7)
- [ ] All blockers have types assigned from the 6-type taxonomy
- [ ] Oldest-item rule satisfied every day (each daily packet advanced ≥1 aging item)
- [ ] No "machine not trying" signal (no 2+ consecutive days with zero artifacts AND zero state changes AND zero stale cleared)
- [ ] Docs/process definitions still match actual behavior
- [ ] Anti-drift metrics within expected ranges (or explained)
- [ ] Fallback-mode usage rate not exceeding 40% (or explained)
- [ ] **Ghost-candidate scan** (added 2026-04-15 per improvement log): any `strategies/*/strategy.py` + `research/data/first_pass/*.json` pair without a matching `research/data/strategy_registry.json` entry? Manual scan in v1 until v2+ audit helper automates. Any ghosts discovered get full-memory-payload triage treatment, same as spx_lunch_compression precedent.

Observable pressure signals to scan (from `stale_checks.md`):
- Under-pressure: empty packets, no new inbox items, no closures, fallback use >40%
- Over-pressure: packet cap exceeded, same candidate touched 3+ days without change, net stale rising
- Process drift: scorecard entries missing required lines, rotation hitting <3 dimensions without explanation, blocker types absent

---

## 6 fallback work modes

When the primary track is blocked, no elite candidate is queue-ready,
or anti-drift signals suggest a shift, the daily packet defaults to one
fallback mode. Every day has productive work; no day is "empty."

### 1. Closure day
Advance items toward final state + complete memory payloads. Focus on:
- Items in Validation needing verdicts
- Items in Rejected missing reasons or salvage classifications
- Items in Validated with incomplete memory payloads
- Items stale on rules 3 (validation), 5 (rejection reason), 6 (salvage), 7 (memory payload)

### 2. Memory cleanup day
Fill missing payload fields, normalize memory index entries. Focus on:
- All candidates with closed state but incomplete 6-field payload
- Component extraction for parents that closed without it
- `component_validation_history` entries missing `reusable_in`

### 3. Source expansion day
(Also the Layer 3 cadence; fires explicitly biweekly. Valid as fallback
on any day between cadence firings.) Focus on:
- Testing a new source class
- Expanding harvest in an under-explored existing lane
- Answering the standing question

### 4. Backlog triage day
Work the oldest inbox items. Focus on:
- Items in Inbox past stale rule #1 (7 days without triage)
- Clearing harvested-but-uncatalogued items from drop-zones (rule #9)
- Dedupe and cluster aging inbox contents

### 5. Component extraction day
Mine validated and rejected strategies for reusable parts. Focus on:
- `component_validation_history` extensions
- Crossbreeding candidate identification
- Updating `extractable_components` registry fields

### 6. Process hardening day
Improvement log action items, stale-threshold review, queue definition
clarifications. Focus on:
- Implementing v1 refinements proposed in `improvement_log.md`
- Calibrating stale thresholds that fire too often or not at all
- Sharpening blocker taxonomy assignments if ambiguity observed

---

## Fallback mode discipline

**Pick one fallback per day** — not a vague "mix." The mode shapes the
packet. Closure day means every packet item is closure-direction.
Backlog triage day means every packet item is inbox-aged.

**Fallback usage tracking.** The weekly rollup counts days in each mode
(primary track vs each fallback). Fallback rate over 40% sustained is
an integrity-cadence flag — it means the primary track isn't
functional and the machine is drifting into comfort work.

**Comfort-work warning.** Closure days and memory-cleanup days are the
most "comfortable" fallbacks (clear scope, low judgment load). If they
are chosen disproportionately, investigate: is the primary track
actually blocked, or is it being avoided?

---

## Day 14 — v1 exit gate

**Fires:** 2026-04-28 (14 days after 2026-04-14 v1 launch).

Expanded integrity cadence run. Standard weekly checklist PLUS these
data-driven calibration questions:

### Quantitative calibration questions
1. **Closure ratio** — what was the realized closure ratio across the 2-week window?
2. **Packet size** — what was the average packet size (items worked per day)?
3. **Fallback-mode usage rate** — what % of days ran as fallback, broken down by mode?
4. **Memory-completion lag** — average days from closure to memory payload complete? % within the 3-day deadline?
5. **Dominant blocker type** — which blocker type accumulated most?
6. **Stale rule firing rate** — per rule, how often fired; per firing, was the action obvious?
7. **Rotation dimensions hit** — across the 2-week window, did 3+ of 5 dimensions get touched weekly?

### Yes/no process checks
- Are daily scorecards actually being written? (count of missing days)
- Are stale items being cleared?
- Is closure happening regularly?
- Is memory being updated consistently?
- Are blockers visible by type?
- Is queue growth controlled?
- Did the standing question on source expansion get answered both biweekly cycles?

### Decision output — exactly one of

- **PASS — advance to v2.** Begin hardening queue or refinement as appropriate. FQL Forge operational kernel proven.
- **REFINE v1.** Specific thresholds, rules, or structures need adjustment before v2. Identify exact changes in improvement log and run another 2-week window.
- **RESTRUCTURE v1.** The kernel itself didn't work. Return to design phase with specific failure-mode observations.

### Reviewer attestation
- Reviewer: _________________
- Date executed: _________________
- Decision rendered: _________________
- Rationale (one paragraph): _________________

---

## Cadence coexistence with existing automation

FQL Forge's cadences are **review-and-decide events** run by the
operator. They coexist with automation in `research/fql_research_scheduler.py`:

- FQL Forge daily cadence fires at end of work day (human-timed)
- `daily_system_watchdog`, `daily_health_check`, etc. fire via launchd on their own schedule
- FQL Forge weekly Friday cadence runs **after** the automated Friday research batch completes
- FQL Forge does not modify scheduler JOBS — that's a Lane A surface

The two run in parallel. FQL Forge consumes outputs from automation
(e.g., scheduler reports, drift monitor state) but does not write to
automated pipelines.

---

## Cadence is what makes v1 a machine

Without cadence, we have queues, stale rules, metrics, and memory
payloads — but no rhythm that connects them into consistent execution.
Cadence converts structure into operation. A day in FQL Forge has a
shape. A week has a shape. Two weeks has a checkpoint. That shape is
the machine.
