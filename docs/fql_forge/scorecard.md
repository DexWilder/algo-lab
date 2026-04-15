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

