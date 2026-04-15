# Active Packet

**Today's bounded work.** Updated each day during the daily operating
cadence (end of prior work day or start of current).

---

## Current packet — 2026-04-15 (v1 day 1)

**Selected:** 2026-04-15
**Selected for (rationale):** First operational day of FQL Forge v1. Seed packet deliberately small (3 items) to establish rhythm and surface friction. Two items cluster around the closing-out of FXBreak-6J (this session's richest reject with full evidence) — closure + component extraction naturally pair. One item samples the open STRUCTURAL gap via fresh Tier A harvest candidate.

### Items in packet

| ID | State | Shape | Today's action | Done-for-today criterion |
|---|---|---|---|---|
| FXBreak-6J-Short-London | Rejected (2026-03-18) | intraday single-asset (retroactive) | Fill all 6 memory-payload fields per `memory_index.md`; currently only `rejection_reason` and `notes` populated | Registry entry has explicit fields for core idea, family/structure, why-failed, salvage classification, reusable parts, portfolio-role observation. Stale rule #6 and #7 cleared for this candidate. |
| FXBreak-6J-Short-London (component extraction) | paired closure | — | Identify what's reusable from FXBreak-6J even though parent is dead. Write `component_validation_history` entry for the session-transition entry logic. Mark `reusable_as_component: true` if anything genuinely survives. | At least one component documented with `type`, `context`, `result`, `reusable_in`, or honest "no reusable components — documented why" entry. |
| S&P Lunch Compression Afternoon Release | Inbox (`harvest_fresh_tier_a.json` item 2) | unknown — triage step is to classify the shape | Triage: read the candidate; classify family + expected shape per `ELITE_PROMOTION_STANDARDS.md`; decide Inbox → In Progress vs Rejected-immediately vs parked-with-note. Target fills STRUCTURAL gap. | Candidate has a triage verdict recorded. If moved to In Progress, next action named. If rejected, reason recorded. If parked, blocker type assigned. |

### Packet composition check

- [x] At least 1 closure-direction item — FXBreak-6J memory payload closes out a stale reject
- [x] At least 1 aging item — FXBreak-6J has been in Rejected since 2026-03-18 without memory payload; easily the oldest unresolved
- [x] Soft: ≤ 2 new items started today — 1 new (the S&P Lunch Compression triage)
- [x] WIP caps respected — 3 items in packet, all within In Progress ≤5 / Validation ≤3 caps

### 5-day rotation hint (heuristic, not rigid)

- [x] Closure (FXBreak-6J memory payload)
- [x] Discovery (S&P Lunch Compression triage)
- [x] Improvement (by virtue of being day 1 — all process friction gets logged)
- [ ] Validation — not hit today
- [x] Gaps (S&P Lunch Compression targets STRUCTURAL open gap)

4 of 5 dimensions touched. Validation not hit because no candidate in
Validation state today needs action. Acceptable for day 1; rolling
window will be monitored in first weekly rollup.

---

## Packet selection rules

1. **Bounded, not exhaustive.** A packet is a deliberate choice of what
   to advance today, not a list of everything touched. Items not in the
   packet stay in their queue state; they are not in-progress-by-default.

2. **Every packet includes at least one closure-direction item.**
   Otherwise the queue fills with started-never-finished work. This is
   non-negotiable — if no closure item exists, today is a closure day
   (see `cadence.md` fallback modes).

3. **Every packet includes at least one aging item.** Oldest-item-in-stage
   must advance, close, get blocked-with-plan, or get explicitly rejected.
   Prevents backlog fossilization. Hard rule — the fallback is "today is a
   backlog triage day."

4. **Done-for-today must be concrete.** "Work on candidate X" is not a
   done criterion. "Complete walk-forward matrix for X and produce
   classification" is. If done-for-today cannot be made concrete, the
   item shouldn't be in the packet.

5. **New item intake is soft-capped at 2/day.** When 2 or more new items
   enter the packet in a single day, note whether this is a deliberate
   harvest burst or queue sprawl. Anti-drift metrics catch sustained
   violations.

6. **Packet for a fallback day selects one fallback mode** (see
   `cadence.md`). That mode shapes the packet — e.g., closure day means
   every item in the packet is closure-direction.

---

## Standing template (copy when writing a new packet)

```
## [YYYY-MM-DD] Packet

Selected for: [gap / hypothesis / rotation rationale OR fallback-mode-name]

### Items

| ID | State | Shape | Today's action | Done-for-today |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

### Composition check
- [ ] ≥1 closure-direction
- [ ] ≥1 aging
- [ ] ≤2 new (or note deliberate burst)
- [ ] WIP caps respected

### Rotation dimensions hit (this packet)
[list of dimensions from the 5-dimension set]
```

---

## Packet history

v1 does not require a permanent packet-history archive beyond the daily
scorecard. The scorecard's "tomorrow" line from day N becomes the
reference for day N+1's packet selection. If longer-history packet
review is needed in v2+, an archive file will be added at that time.
