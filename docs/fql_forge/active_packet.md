# Active Packet

**Today's bounded work.** Updated each day during the daily operating
cadence (end of prior work day or start of current).

---

## Current packet — [DATE]

**Selected: [UTC date]**
**Selected for (gap/hypothesis/rotation rationale):** _________

### Items in packet

| ID | State | Shape | Today's action | Done-for-today criterion |
|---|---|---|---|---|
| — | — | — | — | — |

### Packet composition check

- [ ] At least 1 closure-direction item (moving toward Validated or Rejected)
- [ ] At least 1 aging item (oldest-in-stage; see `stale_checks.md`)
- [ ] Soft: ≤ 2 new items started today
- [ ] WIP caps respected (In Progress ≤5, Validation ≤3)

### 5-day rotation hint (heuristic, not rigid)

Across any rolling 5-day window, packets should usually touch at least
3 of these 5 dimensions:

- [ ] Discovery (harvest, triage, convert)
- [ ] Validation (deep testing, framework application)
- [ ] Closure (memory payload, rejection writeup, salvage classification)
- [ ] Gaps (gap-directed item selection)
- [ ] Improvement (process log, stale-threshold review, source expansion)

**If the rolling window touches fewer than 3 dimensions, note why in the
weekly rollup.** Not an automatic failure — a flag worth explaining.

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
